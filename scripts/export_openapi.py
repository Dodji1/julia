"""Régénère `docs/api/openapi.json`, le contrat publié pour le frontend.

Usage : python scripts/export_openapi.py
Un test échoue si le fichier versionné n'est plus à jour.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "docs" / "api" / "openapi.json"


def render_openapi() -> str:
    from backend.app.config import Settings
    from backend.app.main import create_app

    schema = create_app(Settings(_env_file=None)).openapi()
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> None:
    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_text(render_openapi(), encoding="utf-8")
    print(f"Écrit : {OPENAPI_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
