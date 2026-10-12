# Pipeline d'ingestion (étapes 1 à 4)

Les scripts numérotés des issues #2 à #5 vivent ici. Ils transforment les PDF de `data/raw/` en fichiers
`LegalChunk`, que le backend indexe. Le backend ne dépend d'aucun de ces scripts : seule compte la
conformité des fichiers de sortie au contrat.

## Conventions

| Étape | Script | Sortie |
|---|---|---|
| 1. Ingestion (#2) | `01_extract_text.py`, `02_ocr.py` | `data/processed/01_text/<document_id>.json` |
| 2. Nettoyage, structure (#3) | `03_clean_text.py`, `04_structure_documents.py`, `05_extract_metadata.py` | `data/processed/04_structured/<document_id>.json` |
| 3. Découpage (#4) | `06_chunk_documents.py` | `data/processed/06_chunks/<document_id>.jsonl` |
| 4. Étiquetage (#5, #13) | `07_label_chunks.py` | `data/processed/chunks/<document_id>.jsonl` |
| 5-6. Indexation (#6, #7) | `python -m backend.indexing` | PostgreSQL |

- Le `document_id` est l'`id` du manifeste `data/metadata/corpus_manifest.yaml`, sans exception.
- Une ligne JSONL = un `LegalChunk` ([`contracts/legal_chunk.py`](../contracts/legal_chunk.py)).
- Le `chunk_id` est stable d'une exécution à l'autre (par exemple `<document_id>:art-224` ou
  `<document_id>:<ordinal>`), pour que les traces et les évaluations restent comparables.
- `status`, `source_level`, `country` et `document_type` recopient le manifeste.
- `is_ocr` vaut `true` pour tout texte issu de l'OCR : l'interface invite alors à vérifier sur l'original.
- Les étapes sont rejouables : relancer un script écrase sa sortie pour le document traité.

## Vérifier puis indexer

```bash
python -m backend.indexing --chunks "data/processed/chunks/*.jsonl" --dry-run   # validation seule
python -m backend.indexing --chunks "data/processed/chunks/*.jsonl"             # embeddings + base
```

Dépendances : `pip install -r requirements-pipeline.txt` (et Tesseract installé sur la machine pour l'OCR).
