"""Put a backup made by scripts/backup.py into an empty database.

For a disaster: the Supabase project was lost or wiped and a new, empty one
replaces it. First bring the new database to the same schema version as the
backup (the restore says which), then load the rows:

    cd backend
    set DATABASE_URL=<new database's session pooler string>
    .venv\\Scripts\\python -m alembic upgrade <schema version>
    cd ..
    backend\\.venv\\Scripts\\python scripts\\restore.py backups\\studymate-....zip --database-url <same string> --yes

It refuses a database that already has students in it, so it can never
overwrite live data. Uploaded files in the backup (from --files) are not put
back here; upload them to the new storage bucket from the files/ folder.
"""

import argparse
import base64
import json
import sys
import zipfile
from pathlib import Path

import sqlalchemy as sa


def from_json(row: dict) -> dict:
    return {
        key: base64.b64decode(value["$bytes"]) if isinstance(value, dict) and set(value) == {"$bytes"} else value
        for key, value in row.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("backup", type=Path)
    parser.add_argument("--database-url", required=True, help="the EMPTY database to fill")
    parser.add_argument("--yes", action="store_true", help="confirm writing into that database")
    args = parser.parse_args()

    with zipfile.ZipFile(args.backup) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        engine = sa.create_engine(args.database_url)
        with engine.connect() as conn:
            try:
                version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
            except sa.exc.ProgrammingError:
                version = None
        if version != manifest["schema_version"]:
            sys.exit(
                f"The backup is from schema version {manifest['schema_version']}, the database is at {version}. "
                f"Run `alembic upgrade {manifest['schema_version']}` on it first."
            )

        metadata = sa.MetaData()
        metadata.reflect(bind=engine, schema="public")
        users = metadata.tables.get("public.users") if "public.users" in metadata.tables else metadata.tables.get("users")
        with engine.connect() as conn:
            if users is not None and conn.execute(sa.select(sa.func.count()).select_from(users)).scalar():
                sys.exit("That database already has students in it. Restore only into an empty one.")

        if not args.yes:
            sys.exit(f"Would restore {sum(manifest['tables'].values()):,} rows. Add --yes to go ahead.")

        names = set(archive.namelist())
        with engine.begin() as conn:
            for table in metadata.sorted_tables:
                member = f"tables/{table.name}.json"
                if table.name == "alembic_version" or member not in names:
                    continue
                rows = [from_json(row) for row in json.loads(archive.read(member))]
                columns = {column.name for column in table.columns}
                rows = [{k: v for k, v in row.items() if k in columns} for row in rows]
                for start in range(0, len(rows), 500):
                    conn.execute(table.insert(), rows[start : start + 500])
                print(f"   {table.name}: {len(rows)}")
        engine.dispose()
    print("Restored.")


if __name__ == "__main__":
    main()
