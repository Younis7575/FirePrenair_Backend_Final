#!/usr/bin/env bash
#
# Run this ONCE on the EC2 box, as the `ubuntu` user:
#
#   bash deploy/bootstrap.sh <SERVICE_NAME>
#
# It does the three things the pipeline needs and nothing else:
#   1. lets the deploy user restart *only* the app service via sudo
#   2. installs postgresql-client, so the deploy can pg_dump before it changes
#      anything (production_settings.py uses Postgres, not SQLite)
#   3. reports disk headroom, because the deploy refuses to run when it is low
#
# Re-running is safe.
set -Eeuo pipefail

SERVICE_NAME="${1:-}"
if [ -z "$SERVICE_NAME" ]; then
  echo "Usage: bash deploy/bootstrap.sh <SERVICE_NAME>" >&2
  echo "Run deploy/inspect.sh first if you do not know it." >&2
  exit 1
fi
SERVICE_NAME="${SERVICE_NAME%.service}"

if ! systemctl cat "$SERVICE_NAME" >/dev/null 2>&1; then
  echo "!! No systemd unit called '$SERVICE_NAME'. Check the name and retry." >&2
  exit 1
fi

DEPLOY_USER="${SUDO_USER:-$(id -un)}"

echo "==> Granting $DEPLOY_USER permission to restart $SERVICE_NAME (and nothing else)"
SUDOERS=/etc/sudoers.d/fireprenair-deploy
sudo tee "$SUDOERS" >/dev/null <<EOF
# Added by deploy/bootstrap.sh — lets CI restart the app without a password.
# Deliberately narrow: no general sudo, only this one service.
$DEPLOY_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart $SERVICE_NAME, /bin/systemctl restart $SERVICE_NAME.service
$DEPLOY_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-active $SERVICE_NAME, /bin/systemctl is-active $SERVICE_NAME.service
$DEPLOY_USER ALL=(ALL) NOPASSWD: /usr/bin/journalctl -u $SERVICE_NAME *
EOF
sudo chmod 440 "$SUDOERS"
# A malformed sudoers file can lock you out of sudo entirely, so validate and
# remove it again if it does not parse.
if ! sudo visudo -cf "$SUDOERS"; then
  sudo rm -f "$SUDOERS"
  echo "!! sudoers file was invalid and has been removed. Nothing changed." >&2
  exit 1
fi
echo "    ok"

echo "==> Installing postgresql-client (for pre-deploy database dumps)"
if command -v pg_dump >/dev/null 2>&1; then
  echo "    already present ($(pg_dump --version))"
else
  sudo apt-get update -qq && sudo apt-get install -y -qq postgresql-client
  echo "    installed"
fi

echo "==> Disk headroom"
df -h / | tail -1 | awk '{print "    " $4 " free of " $2 " (" $5 " used)"}'
FREE_MB=$(df -Pm / | awk 'NR==2 {print $4}')
if [ "$FREE_MB" -lt 900 ]; then
  echo "    !! Under 900MB free — the deploy will refuse to run."
  echo "       Reclaim space, e.g.:"
  echo "         sudo journalctl --vacuum-time=7d"
  echo "         sudo apt-get clean && sudo apt-get autoremove -y"
  echo "         rm -rf ~/.cache/pip"
  echo "       If that is not enough, grow the EBS volume."
fi

echo
echo "==> Bootstrap complete. Verifying the sudo grant works:"
sudo -n systemctl is-active "$SERVICE_NAME" && echo "    passwordless restart is authorised"
