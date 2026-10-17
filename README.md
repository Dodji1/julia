# Vitalia — Julia, assistante juridique sourcée

Plateforme legal tech de recherche juridique sourcée (RAG) sur le droit africain.
**MVP : fiscalité du Bénin.** Domaines prévus ensuite : Social, Comptabilité, ONG et association, puis OHADA/UEMOA.

> Principe : **« No source, no legal claim. »** Julia ne présente jamais une connaissance générale du modèle comme une règle vérifiée.

## État d'avancement

| Étape | Contenu | Statut |
|---|---|---|
| 1 | Analyse et architecture | ✅ |
| 2 | Structure du projet, configuration, interfaces, manifeste du corpus | ✅ (ce dépôt) |
| 3 | Landing page Vitalia | ✅ V0 React |
| 4 | Interface de chat Julia | ✅ branchée sur l'API réelle |
| 5 | Backend FastAPI + schéma de base | ✅ V0 ([docs/backend.md](docs/backend.md)) |
| 6 | Pipeline d'ingestion (CGI, puis OCR) | à venir — contrat de sortie : [pipeline/README.md](pipeline/README.md) |
| 7-9 | RAG, DeepSeek, citations vérifiées | moteur et gardes ✅ ; qualité à régler sur le corpus réel |
| 10 | Test sur le corpus fiscal réel + jeu d'évaluation | à venir |

## Démarrage rapide

```bash
python -m venv .venv && source .venv/bin/activate    # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                  # JULIA_ENGINE=fake par défaut : ni base ni LLM
uvicorn backend.app.main:create_app --factory --reload
# → http://localhost:8000/api/docs
python -m pytest -q
```

Moteur réel : `docker compose up -d db` (PostgreSQL + pgvector sur le port 55432), indexation des chunks,
puis `JULIA_ENGINE=postgres` et `JULIA_LLM_API_KEY`. Détails dans [docs/backend.md](docs/backend.md).

Frontend :

```bash
cd frontend
cp .env.example .env            # mock par défaut ; utiliser VITE_API_MODE=live avec FastAPI
npm ci
npm run dev                     # http://localhost:5173
npm test
npm run build
```

Le contrat de l'API est [`docs/api/openapi.json`](docs/api/openapi.json), généré depuis le backend. En mode
`live`, Vite transmet `/api` à FastAPI sur `http://127.0.0.1:8000`. La version compilée (`npm run build`)
peut aussi être servie directement par l'API : `JULIA_FRONTEND_DIST=frontend/dist`.

## Corpus

1. Décompresser `ressources pédagogique pour julia` dans `data/raw/` (non versionné).
2. Le manifeste `data/metadata/corpus_manifest.yaml` décrit les 48 fichiers : domaine, niveau de source,
   type, version, présence d'une couche texte, doublons. Il se régénère avec :
   ```bash
   python scripts/build_manifest.py "data/raw/ressources pédagogique pour julia"
   ```
3. **À faire : relire les niveaux de source** (`level_confirmed: false` partout). Ce sont des propositions heuristiques.

Constats sur le corpus : 21 PDF sont des scans (OCR requis), 2 doublons exacts, CGI 2026 (en vigueur) et
CGI 2025 (archivé) coexistent, 31 documents fiscaux dans le périmètre MVP.

## Hiérarchie des sources

| Niveau | Nature | Exemples |
|---|---|---|
| 1 | Texte officiel applicable | CGI, lois, arrêtés, actes uniformes |
| 2 | Publication officielle de l'administration | notes circulaires, procédures DGI |
| 3 | Sources institutionnelles | guides, doctrine administrative |
| 4 | Documentation secondaire | republications, compilations annotées |

## Architecture

```
Frontend (React + Vite)  →  FastAPI  →  RAG Orchestrator
  Query Analyzer → Retriever (pgvector + plein texte + filtres) → Reranker
  → Context Builder → LLMProvider → Citation Verifier
PostgreSQL + pgvector  ←  Pipeline d'ingestion (manifeste → extraction/OCR → parseur d'articles → embeddings)
```

Interfaces interchangeables (`backend/rag/interfaces.py`) :
`LLMProvider` (DeepSeek maintenant, Claude en phase 4), `Embedder` (BGE-M3 local), `Reranker` (noop puis bge-reranker-v2-m3),
`Retriever`.

### Règles de conception

- Le LLM ne renvoie que des **identifiants de passages** ; les extraits affichés sont relus en base, jamais générés.
- Le **refus** est codé dans l'orchestrateur (seuil de pertinence), pas seulement dans le prompt.
- DeepSeek : le mode *thinking* est actif par défaut côté fournisseur ; il est **désactivé explicitement** (`JULIA_LLM_EXTRA_BODY`).
  Les anciens noms `deepseek-chat` / `deepseek-reasoner` sont retirés : utiliser `deepseek-flash`.
- Pas de score de confiance affiché à l'utilisateur tant qu'il n'est pas calibré.
- Passages issus de l'OCR signalés à l'utilisateur (« vérifier sur l'original »).
- Contenu des documents et des extraits = donnée, jamais instruction (protection contre l'injection de prompt).

## Structure

```
backend/   app (FastAPI, routes, schémas = contrat API) · rag (orchestrateur, gardes, LLM, modèles)
           db (migrations SQL, recherche hybride) · indexing (JSONL LegalChunk → PostgreSQL)
contracts/ legal_chunk.py — format partagé entre pipeline et backend (#12)
pipeline/  scripts d'ingestion 01 → 07 (équipe RAG)
frontend/  React · composants · client API typé · tests    (étapes 3-4)
data/      raw (non versionné) · processed · metadata/corpus_manifest.yaml
scripts/   export_openapi.py (régénère docs/api/openapi.json)
tests/     backend (unitaires, API) · db (intégration PostgreSQL)
docker/    Dockerfile.api
docs/      backend.md · api/openapi.json (contrat publié pour le frontend)
```

## Avertissement

julia est un outil d'aide à la recherche. Il ne remplace pas le conseil d'un professionnel du droit ou de la fiscalité.
Vérifier les droits de réutilisation des textes (notamment le Journal officiel OHADA) avant toute diffusion publique.
