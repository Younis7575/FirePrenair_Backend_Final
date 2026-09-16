#!/usr/bin/env python
"""Compare every model field against the columns the database actually has.

Django's migration record says which migrations it believes have run. It does
not say whether the tables carry the columns the models expect -- and after a
faked or reconciled history they might not. Run from the Django directory with
DJANGO_SETTINGS_MODULE set.

Exit code 0 when the schema fits, 1 when it does not, so a caller can decide
whether that is fatal.
"""
import os
import sys

# Run by absolute path, so Python puts THIS file's directory on sys.path, not
# the Django project's. Django needs to import the settings module, which
# lives beside manage.py in the working directory.
sys.path.insert(0, os.getcwd())

import django

django.setup()

from django.apps import apps  # noqa: E402  (must follow django.setup())
from django.db import connection  # noqa: E402


def columns_in_database():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema()"
        )
        have = {}
        for table, column in cur.fetchall():
            have.setdefault(table, set()).add(column)
    return have


def main():
    have = columns_in_database()

    problems = []
    for model in apps.get_models():
        table = model._meta.db_table
        if table not in have:
            problems.append("missing table  %s" % table)
            continue
        for field in model._meta.local_fields:
            if field.column not in have[table]:
                problems.append("missing column %s.%s" % (table, field.column))

    print("tables in database: %d" % len(have))
    if not problems:
        print("Schema matches the models.")
        return 0

    print("!!! %d mismatch(es) between the models and the database:" % len(problems))
    for problem in problems[:40]:
        print("      %s" % problem)
    if len(problems) > 40:
        print("      ... and %d more" % (len(problems) - 40))
    print("    The code expects columns the database does not have. Pages that")
    print("    touch them will fail. That needs a real migration, not a fake one.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
