"""Migrations SQL numérotées, appliquées une seule fois chacune.

Usage : `python -m backend.db.migrate` (lit JULIA_DATABASE_URL). L'API les applique aussi au
démarrage en mode postgres.
"""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_LOCK_ID = 7_274_272  # verrou consultatif : deux processus ne migrent jamais en même temps


def migrate(database_url: str) -> list[str]:
    applied_now: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_ID,))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if path.stem in applied:
                    continue
                with conn.transaction():
                    conn.execute(path.read_text(encoding="utf-8"))
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
                applied_now.append(path.stem)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    return applied_now


def main() -> None:
    from backend.app.config import Settings

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = Settings()
    if not settings.database_url:
        raise SystemExit("JULIA_DATABASE_URL n'est pas défini.")
    applied = migrate(settings.database_url)
    logger.info("Migrations appliquées : %s", ", ".join(applied) if applied else "aucune, schéma à jour")


if __name__ == "__main__":
    main()
