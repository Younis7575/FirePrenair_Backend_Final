#!/usr/bin/env bash
#
# Point the server's checkout at Younis7575/FirePrenair_Backend_Final.
#
#   bash deploy/repoint-remote.sh
#
# It does NOT touch a single line of deployed code — no pull, no reset, no
# restart. It only changes where git fetches from, and sets up the read-only
# SSH key GitHub requires for a private repository (HTTPS passwords stopped
# working in 2021).
#
# Safe to re-run.
set -uo pipefail

REPO_SSH="git@github.com:Younis7575/FirePrenair_Backend_Final.git"
CHECKOUT="${1:-/home/ubuntu/Fireprenair}"
KEY=~/.ssh/fireprenair_deploy

banner() { printf '\n\033[1;36m%s\033[0m\n' "$*"; }
ok()     { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
warn()   { printf '  \033[1;33m!\033[0m %s\n' "$*"; }

cd "$CHECKOUT" || { echo "No checkout at $CHECKOUT"; exit 1; }

banner "Before"
echo "  remote : $(git remote get-url origin 2>/dev/null || echo none)"
echo "  HEAD   : $(git log -1 --format='%h %ad %s' --date=short 2>/dev/null)"
DIRTY=$(git status --short | wc -l | tr -d ' ')
echo "  uncommitted files: $DIRTY"
[ "$DIRTY" != "0" ] && warn "there are local edits here — they are NOT touched by this script,
    but the first deploy does 'git reset --hard' and WILL discard them.
    Save them first:  git -C $CHECKOUT diff > ~/server-local-changes.patch"

banner "1/3  Deploy key"
if [ -f "$KEY" ]; then
  ok "already exists at $KEY"
else
  ssh-keygen -t ed25519 -N '' -C "fireprenair-deploy@$(hostname)" -f "$KEY" >/dev/null
  ok "generated $KEY"
fi
# Make git use this key for github.com without touching any global ssh config.
git config core.sshCommand "ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
ok "this checkout will use that key for github.com"

banner "2/3  Remote"
git remote set-url origin "$REPO_SSH"
ok "origin -> $(git remote get-url origin)"

banner "3/3  Add the public key to GitHub, then verify"
cat <<EOF

  Copy the line between the markers and add it at:
    https://github.com/Younis7575/FirePrenair_Backend_Final/settings/keys/new
    Title: fireprenair-ec2        Allow write access: LEAVE UNCHECKED

────────────────────────────────────────────────────────────────────────
$(cat "$KEY.pub")
────────────────────────────────────────────────────────────────────────

  Then run:   git -C $CHECKOUT fetch origin && echo FETCH-OK

  A successful fetch downloads history only. Your running code does not
  change until a deploy runs.
EOF
