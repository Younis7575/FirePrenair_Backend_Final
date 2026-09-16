# FirePrenair backend — deployment

## What runs where

| | |
|---|---|
| Server | EC2 `i-0ee96e28b9e17f899` (`fireprenair`), us-east-2, t2.medium, Ubuntu |
| Public IP | `3.21.28.122` — **auto-assigned, not Elastic** |
| In front | Cloudflare (`fireprenair.com` → Cloudflare → origin :80) |
| Web server | nginx 1.24.0 |
| App | Django **ASGI** — daphne + channels + channels-redis |
| Database | **PostgreSQL** — credentials in the server's `.env`, not in git |
| Settings | `prenair.production_settings` (`DEBUG=False`) |
| SSH | user `ubuntu`, key pair named `fireprenair` |

## One-time setup

### 1. Repository secrets
`Settings → Secrets and variables → Actions → Secrets`

| Secret | Value |
|---|---|
| `EC2_HOST` | `3.21.28.122` |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | the **entire** contents of `fireprenair.pem`, `-----BEGIN` line through `-----END` line |

### 2. Repository variables
Same page, **Variables** tab. Fill these in with the real paths on the box
(`systemctl list-units --type=service | grep -i daphne` finds the service name;
`readlink -f $(dirname $(sudo systemctl cat <service> | grep -m1 WorkingDirectory | cut -d= -f2))` finds the path).

| Variable | Example |
|---|---|
| `APP_DIR` | `/home/ubuntu/Fireprenair` (the git checkout) |
| `DJANGO_DIR` | `/home/ubuntu/Fireprenair/prenair` |
| `VENV_DIR` | `/home/ubuntu/Fireprenair/prenair/venv` |
| `SERVICE_NAME` | `fireprenair` (the systemd unit running daphne) |
| `DJANGO_SETTINGS_MODULE` | `prenair.production_settings` |
| `HEALTH_URL` | `http://127.0.0.1/` |

### 3. On the server, once

Connect from the EC2 console (**Instances → fireprenair → Connect → EC2 Instance
Connect → Connect**), then run one command:

```bash
cd /home/ubuntu/Fireprenair && git pull && bash deploy/setup-server.sh
```

It finds the service, path and virtualenv itself, grants CI the narrow sudo
right to restart that one service, installs `postgresql-client`, and prints
every value to paste into GitHub. Safe to re-run. If it cannot identify the
service, re-run as `SERVICE_OVERRIDE=<name> bash deploy/setup-server.sh`.

<details><summary>Or do it by hand</summary>

```bash
# The deploy restarts a service, so the deploy user needs exactly that right —
# and nothing more.
echo 'ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart fireprenair, /bin/systemctl is-active fireprenair, /bin/journalctl -u fireprenair *' \
  | sudo tee /etc/sudoers.d/fireprenair-deploy
sudo chmod 440 /etc/sudoers.d/fireprenair-deploy

# pg_dump, so the deploy can back the database up before changing anything.
sudo apt-get install -y postgresql-client

# Point the checkout at the repo if it is not already.
cd /home/ubuntu/Fireprenair && git remote -v
```
</details>

### 4. Protect the first run
Create a `production` environment (`Settings → Environments`) with yourself as a
required reviewer. The deploy job then waits for your approval before touching
the live box. Remove it once you trust the pipeline.

## How a deploy goes

`git push origin main` →

1. **check** job — installs deps, runs `manage.py check` against production
   settings, and fails the build if `DEBUG=True` ever reaches production settings.
2. **deploy** job — SSHes in and runs `deploy/deploy.sh`, which:
   - aborts if less than 900MB is free (the disk was at 88.9% of 6.7GB);
   - `pg_dump`s the database (credentials read from the server's own `.env`),
     gzips it, keeps the last 7 — and **refuses to deploy if the dump fails**;
   - `git reset --hard origin/main`;
   - `pip install -r requirements.txt`;
   - `makemigrations` + `migrate`;
   - `collectstatic --clear`;
   - restarts the service, then curls it up to 10 times;
   - **rolls back to the previous commit and restarts** if any step fails.

Roll back by hand at any time:
```bash
cd /home/ubuntu/Fireprenair && git reset --hard <previous-sha> && sudo systemctl restart fireprenair
```

## Known risks

**Migrations are not in version control.** `.gitignore` contains `*migrations/`,
so the 13 migration files on the dev machine never reach the server and each
environment generates its own history. The deploy script runs `makemigrations`
on the box to compensate — which is how this project already works, but it means
dev and production can drift apart and a model change can produce different SQL
in each place. Fixing it means removing that ignore rule, committing the
migrations, and reconciling them with whatever the production database already
has — do that deliberately, not during a deploy.

**No Elastic IP.** The public IP is auto-assigned, so stopping and starting the
instance changes it. `production_settings.ALLOWED_HOSTS` still lists two old
addresses (`3.135.224.67`, `18.188.41.235`) — evidence this has already
happened. Allocate an Elastic IP and the `EC2_HOST` secret stops being a
moving target.

**Disk pressure.** 88.9% of 6.71GB used. The deploy refuses to run below 900MB
free rather than filling the disk and taking the site down; if it starts
refusing, grow the EBS volume.

**A credential is committed.** `prenair/fcm_service_account.json` is a Firebase
service-account key tracked in git. The repo is private, so it is not public —
but it is in the history, and anyone with repo access has it.

**requirements.txt did not describe the app.** Three packages the code imports
at module level were missing from it — `psycopg2` (the Postgres driver),
`docraptor` and `elevenlabs`. The server has all three installed by hand, so
nothing was visibly wrong until CI built an environment from the file alone and
the app would not import. All three are now pinned. Rebuilding the virtualenv
from `requirements.txt` was, until this commit, something that would have
broken the site.

**The app cannot start without an OpenAI key.** `home/views.py` runs
`client = OpenAI()` at module level, and four other modules do the same with
`settings.OPENAI_API_KEY`. A missing key therefore does not disable one AI
feature — it raises during URLconf import and stops the site from starting.
Building those clients lazily, inside the views that use them, would turn a
total outage into one broken feature. CI passes placeholders to get past it.

**The Postgres driver was never pinned.** `production_settings.py` uses
`django.db.backends.postgresql`, but `psycopg2` was missing from
`requirements.txt` — the server has one installed by hand. Rebuilding the
virtualenv from the requirements file alone would have left Django unable to
reach the database. `psycopg2-binary==2.9.9` is now pinned.
