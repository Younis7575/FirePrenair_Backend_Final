#!/usr/bin/env bash
#
# FirePrenair backend deploy — runs ON the EC2 host, invoked by GitHub Actions.
#
# Written defensively because this box serves the live site:
#   * the PostgreSQL database and uploaded media are NOT in git, so a pull
#     cannot clobber them — but we dump the database first anyway;
#   * the disk was 88.9% full of 6.7GB when this was written, so we refuse to
#     start a deploy that could fill it;
#   * a failed restart rolls back to the previous commit rather than leaving
#     the site down.
#
# Every path/name comes from the environment so nothing is guessed:
#   APP_DIR              e.g. /home/ubuntu/Fireprenair-main
#   SERVICE_NAME         systemd unit that runs daphne, e.g. fireprenair
#   DJANGO_DIR           Django project dir (manage.py lives here)
#   VENV_DIR             virtualenv dir
#   DJANGO_SETTINGS_MODULE  e.g. prenair.production_settings
#   HEALTH_URL           what to curl after restart
set -Eeuo pipefail

APP_DIR="${APP_DIR:?APP_DIR not set}"
SERVICE_NAME="${SERVICE_NAME:?SERVICE_NAME not set}"
DJANGO_DIR="${DJANGO_DIR:-$APP_DIR/prenair}"
VENV_DIR="${VENV_DIR:-$DJANGO_DIR/venv}"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-prenair.production_settings}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/}"
MIN_FREE_MB="${MIN_FREE_MB:-900}"

export DJANGO_SETTINGS_MODULE

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31m!!! %s\033[0m\n' "$*" >&2; exit 1; }

# ── 1. Refuse to start if the disk cannot take it ────────────────────────────
log "Checking disk"
FREE_MB=$(df -Pm "$APP_DIR" | awk 'NR==2 {print $4}')
df -h "$APP_DIR" | tail -1

# The box sits around 86% full, so a deploy used to stall waiting for somebody
# to log in and delete caches by hand. Reclaim the throwaway things first --
# none of this is data -- and only then decide whether there is room.
if [ "$FREE_MB" -lt "$MIN_FREE_MB" ]; then
  log "Only ${FREE_MB}MB free — reclaiming caches and old logs"
  rm -rf "$HOME/.cache/pip" 2>/dev/null || true
  sudo apt-get clean 2>/dev/null || true
  sudo journalctl --vacuum-size=100M >/dev/null 2>&1 || true
  git -C "$APP_DIR" gc --prune=now --quiet 2>/dev/null || true
  FREE_MB=$(df -Pm "$APP_DIR" | awk 'NR==2 {print $4}')
  log "Now ${FREE_MB}MB free"
fi

[ "$FREE_MB" -ge "$MIN_FREE_MB" ] || die "Only ${FREE_MB}MB free, need ${MIN_FREE_MB}MB, and automatic cleanup could not reclaim enough. The disk needs to grow."

# ── 2. Record where we can roll back to ──────────────────────────────────────
cd "$APP_DIR"
PREVIOUS_SHA=$(git rev-parse HEAD)
log "Current commit $PREVIOUS_SHA"

# ── 3. Back up the PostgreSQL database ───────────────────────────────────────
# Credentials come from the server's own .env (DB_NAME/DB_USER/...), the same
# file production_settings.py reads. They are never passed in from CI.
BACKUP_DIR="$HOME/fireprenair-backups"
mkdir -p "$BACKUP_DIR"
# Read the DB_* values out of .env WITHOUT executing it. Sourcing it with '.'
# assumes the file is valid shell, and a Django .env generally is not: a line
# like `DJANGO_SECRET_KEY = "..."` makes the shell try to run
# DJANGO_SECRET_KEY as a command, which is exactly how this failed first time.
if [ -f "$DJANGO_DIR/.env" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in \#*|'') continue ;; esac
    key=$(printf '%s' "${line%%=*}" | tr -d '[:space:]')
    case "$key" in
      DB_NAME|DB_USER|DB_PASSWORD|DB_HOST|DB_PORT) ;;
      *) continue ;;
    esac
    val=${line#*=}
    # strip surrounding whitespace, then a matching pair of quotes
    val=$(printf '%s' "$val" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
                                   -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/")
    export "$key=$val"
  done < "$DJANGO_DIR/.env"
fi
if command -v pg_dump >/dev/null 2>&1 && [ -n "${DB_NAME:-}" ]; then
  STAMP=$(date +%Y%m%d-%H%M%S)
  log "Dumping database $DB_NAME -> $BACKUP_DIR/db-$STAMP.sql.gz"
  PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
      -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
      -U "${DB_USER:-postgres}" -d "$DB_NAME" \
      | gzip > "$BACKUP_DIR/db-$STAMP.sql.gz" \
    || die "pg_dump failed — refusing to deploy without a backup"
  # Keep the last 7 so backups cannot be what fills the disk.
  ls -1t "$BACKUP_DIR"/db-*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
else
  die "pg_dump unavailable or DB_NAME unset — refusing to deploy without a backup. Run deploy/bootstrap.sh."
fi

# ── 4. Pull ──────────────────────────────────────────────────────────────────
log "Fetching latest code"
git fetch --prune origin
git reset --hard "origin/${DEPLOY_BRANCH:-main}"
NEW_SHA=$(git rev-parse HEAD)
log "Now at $NEW_SHA"

rollback() {
  log "Rolling back to $PREVIOUS_SHA"
  cd "$APP_DIR" && git reset --hard "$PREVIOUS_SHA"
  sudo systemctl restart "$SERVICE_NAME" || true
}

# ── 5. Dependencies ──────────────────────────────────────────────────────────
cd "$DJANGO_DIR"
[ -d "$VENV_DIR" ] || die "No virtualenv at $VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

log "Installing requirements"
pip install --quiet --no-cache-dir -r requirements.txt || { rollback; die "pip install failed"; }

# ── 6. Migrations ────────────────────────────────────────────────────────────
# These run on every deploy, because a release whose code reaches the server
# but whose schema does not is not a release -- it is an outage waiting for the
# first request to the new page.
#
# Two rules make that safe to automate:
#
#   * --fake-initial. The project's apps were migrated at some point and the
#     migration files were then lost (they were gitignored), so the live
#     database holds the tables while Django's record of them is empty.
#     --fake-initial recognises a table that already exists and marks the
#     initial migration applied instead of trying to create it again. Once the
#     record is straight, later migrations apply normally.
#   * makemigrations is never run here. Migration files are authored and
#     reviewed in the repository, not generated on the production host from
#     whatever state that host happens to be in. CI fails the build if a model
#     change arrives without one.
#
# Deploy #13 is why both rules exist: it ran makemigrations on the server and
# applied the result to a SQLite file that did not hold the live data.
#
# The database is dumped in step 3 above, before any of this.
log "Applying migrations"
python manage.py migrate --fake-initial --noinput || { rollback; die "migrate failed — a dump taken before this deploy is in $BACKUP_DIR"; }

# Migrating fixes Django's *record* of the schema. It cannot tell you whether
# the tables really carry the columns the models expect -- and after a
# --fake-initial they might not. Say so plainly instead of waiting for a 500.
log "Checking the database matches the models"
python - <<'PYEOF' || true
import django
django.setup()
from django.apps import apps
from django.db import connection

with connection.cursor() as cur:
    cur.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema()"
    )
    have = {}
    for table, column in cur.fetchall():
        have.setdefault(table, set()).add(column)

problems = []
for model in apps.get_models():
    table = model._meta.db_table
    if table not in have:
        problems.append("missing table  %s" % table)
        continue
    for field in model._meta.local_fields:
        if field.column not in have[table]:
            problems.append("missing column %s.%s" % (table, field.column))

if problems:
    print("!!! %d schema mismatch(es) between the models and the database:" % len(problems))
    for p in problems[:25]:
        print("      %s" % p)
    if len(problems) > 25:
        print("      ... and %d more" % (len(problems) - 25))
    print("    The code expects columns the database does not have. Pages that")
    print("    touch them will fail. That needs a real migration, not a fake one.")
else:
    print("Schema matches the models.")
PYEOF

# ── 6b. Settings the server is missing ───────────────────────────────────────
# .env cannot be in git, so a release that starts reading a new setting would
# otherwise fail at runtime. .env.example is the committed list of key names.
if [ -f .env.example ] && [ -f .env ]; then
  log "Checking .env against .env.example"
  MISSING=$(comm -23 \
    <(grep -oE '^[A-Z0-9_]+=' .env.example | tr -d '=' | sort -u) \
    <(grep -oE '^[A-Z0-9_]+=' .env         | tr -d '=' | sort -u))
  if [ -n "$MISSING" ]; then
    log "WARNING: .env is missing $(echo "$MISSING" | wc -l | tr -d ' ') key(s) the code may read:"
    echo "$MISSING" | sed 's/^/      /'
  else
    echo "  .env has every key in .env.example"
  fi
fi

log "Collecting static files"
python manage.py collectstatic --noinput || { rollback; die "collectstatic failed"; }

log "Django deployment check"
python manage.py check --deploy || true   # advisory only

# ── 6c. nginx configuration ──────────────────────────────────────────────────
# The site's nginx config used to be edited by hand on the box, which is how it
# came to disagree with the repository -- and how a `git reset --hard` could
# silently undo it. Keep the snippets in git and push them out from here.
#
# This never rewrites the server block itself beyond adding one include line,
# and it will not reload nginx unless `nginx -t` passes, so a bad snippet
# leaves the running config untouched.
NGINX_SRC="$APP_DIR/deploy/nginx"
NGINX_SITE=$(readlink -f /etc/nginx/sites-enabled/fireprenair 2>/dev/null || true)
if [ -d "$NGINX_SRC" ] && [ -n "$NGINX_SITE" ] && [ -f "$NGINX_SITE" ]; then
  log "Syncing nginx snippets"
  NGINX_CHANGED=0
  sudo mkdir -p /etc/nginx/snippets
  for f in "$NGINX_SRC"/*.conf; do
    [ -f "$f" ] || continue
    dest="/etc/nginx/snippets/fireprenair-$(basename "$f")"
    if ! sudo cmp -s "$f" "$dest" 2>/dev/null; then
      sudo cp "$f" "$dest" && NGINX_CHANGED=1 && echo "  updated $dest"
    fi
    inc="include snippets/$(basename "$dest");"
    if ! grep -qF "$inc" "$NGINX_SITE"; then
      sudo cp "$NGINX_SITE" "$NGINX_SITE.bak-$(date +%s)"
      awk -v inc="    $inc" '!d && /^    location \/static\/ \{/ {print inc; print ""; d=1} {print}' \
        "$NGINX_SITE" > /tmp/fireprenair-site.conf \
        && sudo cp /tmp/fireprenair-site.conf "$NGINX_SITE" \
        && NGINX_CHANGED=1 && echo "  added $inc to $(basename "$NGINX_SITE")"
    fi
  done
  if [ "$NGINX_CHANGED" = 1 ]; then
    if sudo nginx -t >/dev/null 2>&1; then
      sudo systemctl reload nginx && log "nginx reloaded"
    else
      log "WARNING: nginx -t failed — config NOT reloaded, the old one is still serving"
      sudo nginx -t || true
    fi
  else
    echo "  nginx config already up to date"
  fi
fi

# ── 7. Restart and verify ────────────────────────────────────────────────────
log "Restarting $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
sleep 5
sudo systemctl is-active --quiet "$SERVICE_NAME" || { sudo journalctl -u "$SERVICE_NAME" -n 40 --no-pager; rollback; die "$SERVICE_NAME did not come back up"; }

log "Health check $HEALTH_URL"
for i in $(seq 1 10); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -H "Host: fireprenair.com" "$HEALTH_URL" || echo 000)
  [ "$CODE" = "200" ] || [ "$CODE" = "302" ] && { log "Healthy (HTTP $CODE)"; exit 0; }
  echo "  attempt $i: HTTP $CODE — retrying"
  sleep 3
done

sudo journalctl -u "$SERVICE_NAME" -n 40 --no-pager
rollback
die "Health check never returned 200/302 — rolled back to $PREVIOUS_SHA"
