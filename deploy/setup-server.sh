#!/usr/bin/env bash
#
# ONE command to prepare the server for the CI/CD pipeline.
#
#   bash deploy/setup-server.sh
#
# It detects everything itself, makes the two changes the pipeline needs, and
# prints the exact values to paste into GitHub. Safe to re-run.
set -uo pipefail

banner() { printf '\n\033[1;36m%s\033[0m\n' "$*"; }
ok()     { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
warn()   { printf '  \033[1;33m!\033[0m %s\n' "$*"; }
bad()    { printf '  \033[1;31m✗\033[0m %s\n' "$*"; }

banner "1/4  Finding the app"

SERVICE=$(systemctl list-units --type=service --state=running --no-legend \
  | grep -iE 'daphne|gunicorn|uvicorn|fireprenair' | head -1 | awk '{print $1}' | sed 's/\.service$//')

if [ -z "${SERVICE:-}" ]; then
  bad "Could not find the app's systemd service."
  echo "     Running services were:"
  systemctl list-units --type=service --state=running --no-legend | awk '{print "       " $1}'
  echo "     Re-run as:  SERVICE=<name> bash deploy/setup-server.sh"
  [ -n "${SERVICE_OVERRIDE:-}" ] && SERVICE="$SERVICE_OVERRIDE" || exit 1
fi
SERVICE="${SERVICE_OVERRIDE:-$SERVICE}"
ok "service: $SERVICE"

WORKDIR=$(systemctl show -p WorkingDirectory --value "$SERVICE" 2>/dev/null)
EXECSTART=$(systemctl show -p ExecStart --value "$SERVICE" 2>/dev/null)

DJANGO_DIR="$WORKDIR"
[ -f "${DJANGO_DIR:-}/manage.py" ] || DJANGO_DIR=$(find /home /var/www /opt /srv -maxdepth 5 -name manage.py -not -path '*/venv/*' 2>/dev/null | head -1 | xargs -r dirname)
[ -n "${DJANGO_DIR:-}" ] && ok "django dir: $DJANGO_DIR" || bad "could not find manage.py"

APP_DIR=$(git -C "${DJANGO_DIR:-/}" rev-parse --show-toplevel 2>/dev/null || dirname "${DJANGO_DIR:-/}")
ok "git checkout: $APP_DIR"

VENV_DIR=""
for c in "$DJANGO_DIR/venv" "$DJANGO_DIR/.venv" "$APP_DIR/venv" "$APP_DIR/.venv"; do
  [ -x "$c/bin/python" ] && { VENV_DIR="$c"; break; }
done
if [ -z "$VENV_DIR" ] && [ -n "$EXECSTART" ]; then
  P=$(echo "$EXECSTART" | grep -oE '/[^ ]*/bin/(python|daphne)' | head -1)
  [ -n "$P" ] && VENV_DIR=$(dirname "$(dirname "$P")")
fi
[ -n "$VENV_DIR" ] && ok "virtualenv: $VENV_DIR" || bad "could not find the virtualenv"

# Read what the service actually uses. Do NOT fall back to a plausible-looking
# value: this script previously defaulted to prenair.production_settings, which
# hid the fact that the unit sets nothing and asgi.py therefore falls back to
# prenair.settings -- the development settings, on SQLite, with DEBUG=True.
# Migrations then ran against the wrong database entirely.
SETTINGS=$(systemctl show -p Environment --value "$SERVICE" 2>/dev/null | tr ' ' '\n' | grep '^DJANGO_SETTINGS_MODULE=' | cut -d= -f2)
if [ -n "$SETTINGS" ]; then
  ok "settings: $SETTINGS (from the systemd unit)"
else
  SETTINGS=$(grep -oE "setdefault\(['\"]DJANGO_SETTINGS_MODULE['\"], *['\"][^'\"]+" "$DJANGO_DIR/prenair/asgi.py" 2>/dev/null | sed "s/.*['\"]//")
  SETTINGS="${SETTINGS:-prenair.settings}"
  warn "the unit sets no DJANGO_SETTINGS_MODULE — asgi.py falls back to: $SETTINGS"
fi

# Which database is that settings module actually pointing at? Getting this
# wrong means migrating one database while the app reads another.
DB_ENGINE=$(cd "$DJANGO_DIR" && DJANGO_SETTINGS_MODULE="$SETTINGS" "$VENV_DIR/bin/python" -c \
  "import django;django.setup();from django.conf import settings;print(settings.DATABASES['default']['ENGINE'].rsplit('.',1)[-1])" 2>/dev/null | tail -1)
[ -n "$DB_ENGINE" ] && ok "database: $DB_ENGINE" || warn "could not determine the database backend"
if [ "$DB_ENGINE" = "sqlite3" ]; then
  warn "the live app is on SQLite. production_settings.py (Postgres, DEBUG=False)
    is not what is running -- see deploy/SETUP.md, \"Known risks\"."
fi

banner "2/4  Granting CI permission to restart $SERVICE (and nothing else)"
DEPLOY_USER="${SUDO_USER:-$(id -un)}"
SUDOERS=/etc/sudoers.d/fireprenair-deploy
sudo tee "$SUDOERS" >/dev/null <<EOF
# Added by deploy/setup-server.sh. Deliberately narrow: no general sudo.
$DEPLOY_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart $SERVICE, /bin/systemctl restart $SERVICE.service
$DEPLOY_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-active $SERVICE, /bin/systemctl is-active $SERVICE.service
$DEPLOY_USER ALL=(ALL) NOPASSWD: /usr/bin/journalctl -u $SERVICE *
EOF
sudo chmod 440 "$SUDOERS"
# A malformed sudoers file can lock you out of sudo entirely.
if sudo visudo -cf "$SUDOERS" >/dev/null 2>&1; then
  sudo -n systemctl is-active "$SERVICE" >/dev/null 2>&1 && ok "passwordless restart works" || warn "grant written but check failed"
else
  sudo rm -f "$SUDOERS"; bad "sudoers file was invalid — removed, nothing changed"; exit 1
fi

banner "3/4  Installing postgresql-client (for pre-deploy database dumps)"
if command -v pg_dump >/dev/null 2>&1; then ok "already present"
else sudo apt-get update -qq && sudo apt-get install -y -qq postgresql-client && ok "installed"; fi

banner "4/4  State check"
df -h "${APP_DIR:-/}" | tail -1 | awk '{print "  disk: " $4 " free of " $2 " (" $5 " used)"}'
FREE_MB=$(df -Pm "${APP_DIR:-/}" | awk 'NR==2 {print $4}')
[ "$FREE_MB" -ge 900 ] && ok "enough headroom for a deploy" || warn "under 900MB — the deploy will refuse to run until you free space"
git -C "$APP_DIR" rev-parse --short HEAD >/dev/null 2>&1 \
  && ok "deployed commit: $(git -C "$APP_DIR" rev-parse --short HEAD)" \
  || bad "$APP_DIR is not a git checkout — the pipeline needs one"

cat <<EOF

╔════════════════════════════════════════════════════════════════════╗
║  Server is ready. Now paste these into GitHub:                     ║
║  Settings → Secrets and variables → Actions                        ║
╚════════════════════════════════════════════════════════════════════╝

  ── Variables tab ──  (New repository variable)
    APP_DIR                   $APP_DIR
    DJANGO_DIR                $DJANGO_DIR
    VENV_DIR                  $VENV_DIR
    SERVICE_NAME              $SERVICE
    DJANGO_SETTINGS_MODULE    $SETTINGS
    HEALTH_URL                http://127.0.0.1/

  ── Secrets tab ──  (New repository secret)
    EC2_HOST                  $(curl -s --max-time 5 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo '3.21.28.122')
    EC2_USER                  $(id -un)
    EC2_SSH_KEY               paste the whole fireprenair.pem file,
                              including the BEGIN and END lines

Then push anything to main, or use Actions → Deploy backend to EC2 → Run workflow.
EOF
