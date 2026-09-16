#!/usr/bin/env bash
#
# Point the server's checkout at Younis7575/FirePrenair_Backend_Final.
#
#   bash deploy/repoint-remote.sh
#
# It does NOT touch a single line of deployed code — no pull, no reset, no
# restart. It only changes where git fetches from. The repository is public, so
# no credentials or deploy key are needed.
#
# Safe to re-run.
set -uo pipefail

REPO_URL="https://github.com/Younis7575/FirePrenair_Backend_Final.git"
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

banner "1/2  Remote"
git remote set-url origin "$REPO_URL"
ok "origin -> $(git remote get-url origin)"

banner "2/2  Verify"
if git fetch origin --quiet 2>/dev/null; then
  ok "fetch works — no credentials needed (public repo)"
  echo "  origin/main is at: $(git log -1 --format='%h %s' origin/main)"
  echo "  this checkout is : $(git log -1 --format='%h %s' HEAD)"
  echo
  echo "  Your running code has NOT changed. It changes on the first deploy,"
  echo "  which does 'git reset --hard origin/main'."
else
  warn "fetch failed — check the repo is public and the box has internet"
fi

cat <<'EOF'

  Next: bash deploy/setup-server.sh
EOF
