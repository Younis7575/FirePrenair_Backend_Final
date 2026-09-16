#!/usr/bin/env python
"""Record the committed migrations whose tables already exist; leave the rest.

Used once, by the reconcile-migrations workflow, to rebuild a migration record
whose files were lost. Not part of a deploy.

The live tables were built by migrations whose files no longer exist anywhere,
so Django's record has to be rebuilt from the files committed now. Most of those
migrations describe tables the database already has, and marking them applied is
simply telling Django the truth. But not all of them: one creates a table that
was never built, and recording everything blindly would bury that -- Django
would believe the table existed and every page touching it would fail. The first
attempt did exactly that, and the schema check caught it.

So the rule is per app, in order: record a migration while every table it would
create is already there, and stop at the first one that would create something
missing. `migrate` then applies that migration, and the ones after it, for real.

`migrate --fake-initial` would be the usual tool, but it checks history
consistency before doing anything and refuses while the local apps' rows are
missing -- admin.0001_initial depends on profiles.0001_initial.

Run from the Django directory with DJANGO_SETTINGS_MODULE set.
"""
import os
import sys

# Run by absolute path, so Python puts THIS file's directory on sys.path, not
# the Django project's. Django needs to import the settings module, which
# lives beside manage.py in the working directory.
sys.path.insert(0, os.getcwd())

import django

django.setup()

from django.db import connection  # noqa: E402  (must follow django.setup())
from django.db.migrations.loader import MigrationLoader  # noqa: E402
from django.db.migrations.operations.models import CreateModel  # noqa: E402
from django.db.migrations.recorder import MigrationRecorder  # noqa: E402


def existing_tables():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema()"
        )
        return {row[0] for row in cur.fetchall()}


def tables_created_by(app_label, migration):
    """The table names this migration's CreateModel operations would build."""
    tables = []
    for operation in migration.operations:
        if not isinstance(operation, CreateModel):
            continue
        db_table = (operation.options or {}).get("db_table")
        tables.append(db_table or "%s_%s" % (app_label, operation.name.lower()))
    return tables


def main():
    recorder = MigrationRecorder(connection)
    recorder.ensure_schema()
    already = {(app, name) for app, name in recorder.applied_migrations()}

    # Disk only: the graph would otherwise be built against a record we are in
    # the middle of rebuilding.
    loader = MigrationLoader(None, ignore_no_migrations=True)
    apps_on_disk = sorted({app for app, _ in loader.disk_migrations})

    have = existing_tables()
    recorded = 0

    for app in apps_on_disk:
        names = sorted(name for a, name in loader.disk_migrations if a == app)
        for name in names:
            migration = loader.disk_migrations[(app, name)]
            missing = [t for t in tables_created_by(app, migration) if t not in have]
            if missing:
                print(
                    "      %s.%s would create %s — leaving it for migrate"
                    % (app, name, ", ".join(missing))
                )
                break
            if (app, name) in already:
                continue
            recorder.record_applied(app, name)
            print("      recorded %s.%s" % (app, name))
            recorded += 1

    print("%d migration(s) recorded" % recorded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
