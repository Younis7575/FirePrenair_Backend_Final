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
[ "$FREE_MB" -ge "$MIN_FREE_MB" ] || die "Only ${FREE_MB}MB free, need ${MIN_FREE_MB}MB. Free space first (old backups, pip cache, journal logs) and re-run."

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
# NOTE: migrations are excluded by .gitignore ('*migrations/'), so they are not
# shipped with the code and have to be generated here. That is how this project
# already works, but it means each environment invents its own history — see
# deploy/SETUP.md, "Known risks". The database is Postgres and already holds a
# migration history, so makemigrations only ever writes files that are new.
log "Applying migrations"
python manage.py makemigrations --noinput || { rollback; die "makemigrations failed"; }
python manage.py migrate --noinput || { rollback; die "migrate failed"; }

# No --clear: static files live in S3 (django-storages), and --clear calls
# clear_dir("") -> storage.exists("") -> S3 head_object with an empty Key,
# which S3 rejects outright:
#   ParamValidationError: Invalid length for parameter Key, value: 0
# It is also the wrong thing to want here — it would try to wipe the bucket
# prefix before re-uploading. collectstatic overwrites changed files anyway.
log "Collecting static files"
python manage.py collectstatic --noinput || { rollback; die "collectstatic failed"; }

log "Django deployment check"
python manage.py check --deploy || true   # advisory only

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
