"""Save a copy of the StudyMate database (and optionally the uploaded files) to this computer.

Supabase's free plan keeps no backups you can restore yourself, so run this
now and then, and before anything risky such as a big migration:

    backend\\.venv\\Scripts\\python scripts\\backup.py
    backend\\.venv\\Scripts\\python scripts\\backup.py --files     # lecture files too

It writes backups/studymate-<date>.zip: one JSON file per table plus the
schema version, readable by scripts/restore.py. Only reads; changes nothing.
Reads DATABASE_URL (and, for --files, SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY) from .env. Prints no secret values. The backups
folder is git-ignored: it holds everyone's data, so keep it private.
"""

import argparse
import base64
import json
import sys
import uuid
import zipfile
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import httpx
import sqlalchemy as sa
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
FORMAT_VERSION = 1


def to_json(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, memoryview)):
        return {"$bytes": base64.b64encode(bytes(value)).decode()}
    raise TypeError(f"Cannot save a {type(value).__name__}")


def dump_tables(engine: sa.Engine, archive: zipfile.ZipFile) -> dict[str, int]:
    counts = {}
    metadata = sa.MetaData()
    metadata.reflect(bind=engine, schema="public")
    with engine.connect() as conn:
        version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
        for table in metadata.sorted_tables:
            if table.name == "alembic_version":
                continue
            rows = [dict(row._mapping) for row in conn.execute(sa.select(table))]
            archive.writestr(f"tables/{table.name}.json", json.dumps(rows, default=to_json))
            counts[table.name] = len(rows)
    archive.writestr(
        "manifest.json",
        json.dumps(
            {
                "format": FORMAT_VERSION,
                "schema_version": version,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "tables": counts,
            },
            indent=2,
        ),
    )
    return counts


def dump_files(env: dict, engine: sa.Engine, archive: zipfile.ZipFile) -> int:
    base = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = env.get("STORAGE_BUCKET") or "lecture-files"
    if not (base and key):
        sys.exit("--files needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    with engine.connect() as conn:
        paths = [row[0] for row in conn.execute(sa.text("SELECT storage_path FROM lecture_documents"))]
    saved = 0
    with httpx.Client(headers={"Authorization": f"Bearer {key}", "apikey": key}, timeout=120) as client:
        for path in paths:
            response = client.get(f"{base}/storage/v1/object/{bucket}/{path}")
            if response.status_code == 200:
                archive.writestr(f"files/{path}", response.content)
                saved += 1
            else:
                print(f"   skipped a file that could not be read ({response.status_code})")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--files", action="store_true", help="also save the uploaded lecture files")
    parser.add_argument("--out", type=Path, default=ROOT / "backups", help="folder to write into")
    parser.add_argument("--database-url", help="back up this database instead of DATABASE_URL in .env")
    args = parser.parse_args()

    env = dotenv_values(ROOT / ".env")
    url = args.database_url or env.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is missing from .env")
    engine = sa.create_engine(url)

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"studymate-{datetime.now():%Y-%m-%d-%H%M}.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        counts = dump_tables(engine, archive)
        files = dump_files(env, engine, archive) if args.files else 0
    engine.dispose()

    print(f"Saved {sum(counts.values()):,} rows from {len(counts)} tables", end="")
    print(f" and {files} files" if args.files else "", end="")
    print(f" to {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")
    print(f"   students: {counts.get('users', 0)}, documents: {counts.get('lecture_documents', 0)}, "
          f"question sets: {counts.get('assessments', 0)}")


if __name__ == "__main__":
    main()
