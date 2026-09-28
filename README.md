# Vitalia — Julia, assistante juridique sourcée

Plateforme legal tech de recherche juridique sourcée (RAG) sur le droit africain.
**MVP : fiscalité du Bénin.** Domaines prévus ensuite : Social, Comptabilité, ONG et association, puis OHADA/UEMOA.

> Principe : **« No source, no legal claim. »** Julia ne présente jamais une connaissance générale du modèle comme une règle vérifiée.

## État d'avancement

| Étape | Contenu | Statut |
|---|---|---|
| 1 | Analyse et architecture | ✅ |
| 2 | Structure du projet, configuration, interfaces, manifeste du corpus | ✅ (ce dépôt) |
| 3 | Landing page Vitalia | à venir |
| 4 | Interface de chat Julia | à venir |
| 5 | Backend FastAPI + schéma de base | à venir |
| 6 | Pipeline d'ingestion (CGI, puis OCR) | à venir |
| 7-9 | RAG, DeepSeek, citations vérifiées | à venir |
| 10 | Test sur le corpus fiscal réel + jeu d'évaluation | à venir |

## Démarrage rapide

```bash
cp .env.example .env            # puis renseigner DEEPSEEK_API_KEY et POSTGRES_PASSWORD
docker compose up --build       # PostgreSQL+pgvector (5432) et API (8000)
curl http://localhost:8000/api/health
```

Sans Docker (développement) :

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
python -m pytest -q             # 16 tests
```

## Corpus

1. Décompresser `ressources pédagogique pour vitalia` dans `data/raw/` (non versionné).
2. Le manifeste `data/metadata/corpus_manifest.yaml` décrit les 48 fichiers : domaine, niveau de source,
   type, version, présence d'une couche texte, doublons. Il se régénère avec :
   ```bash
   python scripts/build_manifest.py "data/raw/ressources pédagogique pour vitalia"
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
Frontend (Next.js)  →  FastAPI  →  RAG Orchestrator
  Query Analyzer → Retriever (pgvector + plein texte + filtres) → Reranker
  → Context Builder → LLMProvider → Citation Verifier
PostgreSQL + pgvector  ←  Pipeline d'ingestion (manifeste → extraction/OCR → parseur d'articles → embeddings)
```

Interfaces interchangeables (`backend/rag/*/base.py`) :
`LLMProvider` (DeepSeek maintenant, Claude en phase 4), `Embedder` (BGE-M3 local), `Reranker` (noop puis bge-reranker-v2-m3),
`Retriever`.

### Règles de conception

- Le LLM ne renvoie que des **identifiants de passages** ; les extraits affichés sont relus en base, jamais générés.
- Le **refus** est codé dans l'orchestrateur (seuil de pertinence), pas seulement dans le prompt.
- DeepSeek : le mode *thinking* est actif par défaut côté fournisseur ; il est **désactivé explicitement** (`DEEPSEEK_THINKING`).
  Les anciens noms `deepseek-chat` / `deepseek-reasoner` sont retirés : utiliser `deepseek-flash`.
- Pas de score de confiance affiché à l'utilisateur tant qu'il n'est pas calibré.
- Passages issus de l'OCR signalés à l'utilisateur (« vérifier sur l'original »).
- Contenu des documents et des extraits = donnée, jamais instruction (protection contre l'injection de prompt).

## Structure

```
backend/   api · core (config, enums) · models (schémas) · services · rag/{ingestion,chunking,embeddings,retrieval,reranking,generation,verification}
frontend/  app · components · services · styles           (étapes 3-4)
data/      raw (non versionné) · processed · metadata/corpus_manifest.yaml
scripts/   build_manifest.py
tests/     test_core.py · test_manifest.py · eval/questions_fiscal_bj.yaml (à compléter avec un fiscaliste)
docker/    Dockerfile.api · initdb/01-extensions.sql
```

## Avertissement

Vitalia est un outil d'aide à la recherche. Il ne remplace pas le conseil d'un professionnel du droit ou de la fiscalité.
Vérifier les droits de réutilisation des textes (notamment Droit-Afrique.com et le Journal officiel OHADA) avant toute diffusion publique.
