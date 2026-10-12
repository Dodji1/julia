# Backend Julia — API et moteur RAG

## Rôle

Le backend reçoit la question, retrouve les passages pertinents, fait rédiger la réponse par le LLM et
vérifie chaque citation avant de répondre. Il ne lit que la base : l'ingestion (étapes 1 à 4) produit des
fichiers `LegalChunk`, que la commande d'indexation charge dans PostgreSQL.

```
Pipeline d'ingestion (équipe RAG)          Backend                                   Frontend
PDF → texte → structure → LegalChunk  ──►  indexation ──► PostgreSQL + pgvector ──► API ──► React
               (JSONL, contrat B)                                          (OpenAPI, contrat A)
```

## Démarrer

```bash
python -m venv .venv && .venv/Scripts/activate     # Linux/macOS : source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

# Mode fake : sans base ni LLM, réponses de démonstration conformes au contrat
uvicorn backend.app.main:create_app --factory --reload
# → http://localhost:8000/api/docs

# Mode postgres
docker compose up -d db                              # PostgreSQL + pgvector sur le port 55432
pip install -r requirements-ml.txt                   # BGE-M3 (PyTorch), ou JULIA_EMBEDDING_MODEL=test/hashing
python -m backend.indexing --chunks "data/processed/chunks/*.jsonl"
JULIA_ENGINE=postgres uvicorn backend.app.main:create_app --factory --reload
```

Le frontend en mode `live` passe par le proxy Vite (`/api` → `localhost:8000`).

## Une requête `POST /api/v1/answers`

```
question + filtres
 → limites de débit (navigateur, IP, budget du jour)
 → analyse : articles cités, années (une année passée inclut les textes archivés)
 → recherche hybride PostgreSQL, filtrée (domaine, textes applicables au Bénin, statut) :
     vectorielle ∪ plein texte français sans accents ∪ article exact → fusion RRF
 → reranker (aucun en V0 ; bge-reranker-v2-m3 activable)
 → GARDE 1 : aucun passage au-dessus de JULIA_MIN_RELEVANCE → refus, sans appel au LLM
 → contexte : passages <passage id="P1">…</passage>, présentés comme des données
 → LLM (DeepSeek, JSON, réflexion désactivée ; second fournisseur en secours ; 1 nouvel essai si JSON invalide)
 → GARDE 2 : on ne garde que les [Pn] qui existent, renumérotés [1], [2]…
     une réponse « answered » sans citation valide devient un refus
 → sources : extrait = texte du chunk en base (jamais généré), URL du PDF à la page
 → trace en base (rag_traces), en tâche de fond
```

Fichiers : [`backend/rag/engine.py`](../backend/rag/engine.py) (orchestrateur),
[`citations.py`](../backend/rag/citations.py) (garde 2), [`db/retriever.py`](../backend/db/retriever.py)
(recherche hybride), [`prompts/answer_system.md`](../backend/rag/prompts/answer_system.md) (règles #8).

## Contrat A : l'API

Le contrat publié est [`docs/api/openapi.json`](api/openapi.json), généré depuis le code
(`python scripts/export_openapi.py`) ; un test échoue s'il n'est pas à jour.

| Route | Rôle |
|---|---|
| `POST /api/v1/answers` | Réponse sourcée, refus ou demande de précision |
| `GET /api/v1/documents` | Corpus couvert (titre, niveau, statut, version) |
| `GET /api/v1/documents/{id}` | Métadonnées d'un document |
| `GET /api/v1/documents/{id}/file` | PDF original ; `#page=N` ouvre à la page |
| `POST /api/v1/search` | Recherche sans LLM, réservée à l'équipe (`X-Admin-Token`) |
| `POST /api/v1/feedback` | Pouce levé ou baissé sur une réponse |
| `GET /api/health` | État de l'API, de la base et version du corpus |

Par rapport à `frontend-contract.yaml` (contrat du frontend V0), rien n'est renommé ni supprimé. Ajouts :
- dans chaque source : `chunk_id`, `location` (Livre › Chapitre › Section), `source_level`, `document_type` ;
- en-tête facultatif `X-Client-Id` (identifiant aléatoire stocké dans le navigateur) : la limite de débit
  porte sur le navigateur, car toute la salle du congrès partage la même IP ;
- erreurs `429` (`RATE_LIMITED`, `DAILY_QUOTA_EXCEEDED`, avec `Retry-After`) et `503` (`LLM_UNAVAILABLE`).

## Contrat B : `LegalChunk` et indexation

Le modèle est défini dans [`contracts/legal_chunk.py`](../contracts/legal_chunk.py) (issue #12). Le
pipeline écrit un JSONL par document. Avant d'indexer, on valide sans base :

```bash
python -m backend.indexing --chunks "data/processed/chunks/*.jsonl" --dry-run
```

La commande refuse un chunk dont le `document_id` est absent du manifeste, qui contredit le manifeste
(statut, niveau, pays, type), qui vise un doublon, ou dont l'identifiant est déjà pris. Les embeddings sont
calculés par la même fabrique que l'API (`build_embedder`) : indexation et requête utilisent forcément le
même modèle.

## Ce que l'équipe RAG fait évoluer sans toucher à l'API

| Levier | Où |
|---|---|
| Règles de réponse (#8) | `backend/rag/prompts/answer_system.md` |
| Seuil de refus | `JULIA_MIN_RELEVANCE` (à calibrer sur le jeu d'évaluation) |
| Nombre de passages | `JULIA_RETRIEVE_K`, `JULIA_CONTEXT_K` |
| Reranker | `JULIA_RERANKER=cross_encoder` (recalibrer le seuil) |
| Nouvelle stratégie de recherche | une classe qui respecte `Retriever` dans `backend/rag/interfaces.py` |
| Analyse de la question | `backend/rag/analyzer.py` |

`POST /api/v1/search` et la table `rag_traces` servent à mesurer l'effet de chaque changement.

## Tests

```bash
pytest                                   # tests unitaires et API (sans base)
docker compose exec db createdb -U julia julia_test
JULIA_TEST_DATABASE_URL=postgresql://julia:julia-dev@127.0.0.1:55432/julia_test pytest -m db
```

Sous Windows, utiliser `127.0.0.1` et non `localhost` dans les URL de base : `localhost` tente d'abord IPv6,
que Docker n'écoute pas, et chaque connexion perd 15 secondes.

## Choix de conception

- **Une seule instance PostgreSQL** : documents, chunks et vecteurs dans des tables séparées (#6), une seule
  requête pour filtrer, chercher et fusionner, aucun risque de désynchronisation entre chunk et vecteur.
- **Pas de framework RAG** (LangChain, LlamaIndex) : les gardes et la renumérotation des citations sont
  spécifiques, et on veut lire exactement ce qui est envoyé au LLM.
- **Pas de streaming en V0** : la garde 2 s'applique à la réponse complète.
- **Une question à la fois en V0** : `conversation_id` est renvoyé mais pas encore lu.
- **Un seul processus API** : les limites de débit sont en mémoire.
