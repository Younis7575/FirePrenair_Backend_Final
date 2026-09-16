#!/usr/bin/env bash
#
# Run this ONCE on the EC2 box. It changes nothing — it only reads — and prints
# the exact values to paste into GitHub → Settings → Secrets and variables →
# Actions → Variables.
#
#   curl -fsSL https://raw.githubusercontent.com/Younis7575/FirePrenair_Backend_Final/main/deploy/inspect.sh | bash
#   ...or, if the checkout is already there:  bash deploy/inspect.sh
set -uo pipefail

echo "════════════════════════════════════════════════════════════"
echo " FirePrenair — server inspection (read-only)"
echo "════════════════════════════════════════════════════════════"

# ── Find the systemd unit that actually serves the app ───────────────────────
echo
echo "── Candidate services ──"
systemctl list-units --type=service --state=running --no-legend \
  | grep -iE 'daphne|gunicorn|uvicorn|fireprenair|django|asgi' \
  | awk '{print "   " $1}' || echo "   (none matched — listing all non-system units:)"

SERVICE=$(systemctl list-units --type=service --state=running --no-legend \
  | grep -iE 'daphne|gunicorn|uvicorn|fireprenair' | head -1 | awk '{print $1}' | sed 's/\.service$//')

if [ -z "${SERVICE:-}" ]; then
  echo "   !! Could not identify the app service automatically."
  echo "   Run: systemctl list-units --type=service --state=running"
  echo "   and look for whatever runs daphne/manage.py."
fi

# ── Derive paths from the unit file ──────────────────────────────────────────
WORKDIR=""
EXECSTART=""
if [ -n "${SERVICE:-}" ]; then
  WORKDIR=$(systemctl show -p WorkingDirectory --value "$SERVICE" 2>/dev/null)
  EXECSTART=$(systemctl show -p ExecStart --value "$SERVICE" 2>/dev/null)
  echo
  echo "── Unit: $SERVICE ──"
  echo "   WorkingDirectory : ${WORKDIR:-(unset)}"
  echo "   ExecStart        : ${EXECSTART:0:160}"
fi

# DJANGO_DIR is wherever manage.py lives.
DJANGO_DIR="$WORKDIR"
if [ ! -f "${DJANGO_DIR:-}/manage.py" ]; then
  DJANGO_DIR=$(find /home /var/www /opt /srv -maxdepth 5 -name manage.py -not -path '*/venv/*' 2>/dev/null | head -1 | xargs -r dirname)
fi
APP_DIR=""
if [ -n "${DJANGO_DIR:-}" ]; then
  APP_DIR=$(git -C "$DJANGO_DIR" rev-parse --show-toplevel 2>/dev/null || dirname "$DJANGO_DIR")
fi
VENV_DIR=""
for cand in "$DJANGO_DIR/venv" "$DJANGO_DIR/.venv" "$APP_DIR/venv" "$APP_DIR/.venv"; do
  [ -x "$cand/bin/python" ] && { VENV_DIR="$cand"; break; }
done
# Fall back to whatever python the unit actually executes.
if [ -z "$VENV_DIR" ] && [ -n "$EXECSTART" ]; then
  P=$(echo "$EXECSTART" | grep -oE '/[^ ]*/bin/(python|daphne)' | head -1)
  [ -n "$P" ] && VENV_DIR=$(dirname "$(dirname "$P")")
fi
SETTINGS=$(systemctl show -p Environment --value "${SERVICE:-}" 2>/dev/null | tr ' ' '\n' | grep '^DJANGO_SETTINGS_MODULE=' | cut -d= -f2)
[ -z "$SETTINGS" ] && SETTINGS="prenair.production_settings"

# ── State that decides whether a deploy is safe ──────────────────────────────
echo
echo "── Disk ──"
df -h "${APP_DIR:-/}" | tail -1 | awk '{print "   " $4 " free of " $2 "  (" $5 " used)"}'

echo
echo "── Deployed commit ──"
if [ -n "${APP_DIR:-}" ] && git -C "$APP_DIR" rev-parse HEAD >/dev/null 2>&1; then
  echo "   $(git -C "$APP_DIR" rev-parse --short HEAD)  $(git -C "$APP_DIR" log -1 --format=%s)"
  echo "   remote: $(git -C "$APP_DIR" remote get-url origin 2>/dev/null)"
else
  echo "   !! $APP_DIR is not a git checkout — the pipeline needs one."
fi

echo
echo "── Migration state (per app, latest applied) ──"
if [ -n "${VENV_DIR:-}" ] && [ -f "$DJANGO_DIR/manage.py" ]; then
  (cd "$DJANGO_DIR" && DJANGO_SETTINGS_MODULE="$SETTINGS" "$VENV_DIR/bin/python" manage.py showmigrations 2>/dev/null \
     | awk '/^[a-z]/{app=$0} /\[X\]/{last[app]=$0} END{for(a in last) print "   " a " -> " last[a]}' | sort | head -20) \
     || echo "   (could not read — check DJANGO_SETTINGS_MODULE)"
fi

echo
echo "════════════════════════════════════════════════════════════"
echo " Paste these into GitHub → Settings → Secrets and variables"
echo " → Actions → Variables"
echo "════════════════════════════════════════════════════════════"
printf '   %-24s %s\n' "APP_DIR"                 "${APP_DIR:-??}"
printf '   %-24s %s\n' "DJANGO_DIR"              "${DJANGO_DIR:-??}"
printf '   %-24s %s\n' "VENV_DIR"                "${VENV_DIR:-??}"
printf '   %-24s %s\n' "SERVICE_NAME"            "${SERVICE:-??}"
printf '   %-24s %s\n' "DJANGO_SETTINGS_MODULE"  "$SETTINGS"
printf '   %-24s %s\n' "HEALTH_URL"              "http://127.0.0.1/"
echo
echo " Anything showing ?? could not be detected — find it by hand before"
echo " enabling the pipeline. Nothing here was modified."
