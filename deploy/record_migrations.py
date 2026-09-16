#!/usr/bin/env python
"""Record every committed migration as applied, without running it.

Used once, by the reconcile-migrations workflow, to rebuild a migration record
whose files were lost. Not part of a deploy.

Why record rather than apply: the tables already exist -- they were built by the
migrations whose files are gone -- and every migration now committed either
creates one of those tables or alters a related_name or a choices list, neither
of which touches the database. `migrate --fake-initial` would be the usual tool,
but it checks history consistency before doing anything and refuses while the
local apps' rows are missing: admin.0001_initial depends on
profiles.0001_initial. So the rows go in first, and `migrate` runs afterwards to
confirm there is nothing left to do.

Run from the Django directory with DJANGO_SETTINGS_MODULE set.
"""
import os
import pathlib
import sys

# Run by absolute path, so Python puts THIS file's directory on sys.path, not
# the Django project's. Django needs to import the settings module, which
# lives beside manage.py in the working directory.
sys.path.insert(0, os.getcwd())

import django

django.setup()

from django.db import connection  # noqa: E402  (must follow django.setup())
from django.db.migrations.recorder import MigrationRecorder  # noqa: E402


def main():
    recorder = MigrationRecorder(connection)
    recorder.ensure_schema()
    already = {(app, name) for app, name in recorder.applied_migrations()}

    recorded = 0
    for path in sorted(pathlib.Path(".").glob("*/migrations/[0-9]*.py")):
        app, name = path.parts[0], path.stem
        if (app, name) in already:
            continue
        recorder.record_applied(app, name)
        print("      recorded %s.%s" % (app, name))
        recorded += 1

    print("%d migration(s) recorded" % recorded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
