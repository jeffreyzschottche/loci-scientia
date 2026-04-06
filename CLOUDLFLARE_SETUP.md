# Cloudflare Tunnel Setup

This repository has two Cloudflare-related pieces:

1. A tunnel status check in the backend (`app/backend/cloudflare_tunnel.py`).
2. A support SSH toggle flow that depends on the helper scripts in `scripts/`.

Important: `./lociscientia.sh` currently installs `cloudflared` and starts the stock service, but it does not install or activate the repo-managed wrapper scripts. If you want the full "web always on, SSH only temporarily enabled from the UI" behavior, follow the manual setup below.

## What the repo expects

The intended tunnel layout is:

- `https://<device-id>.<domain>` -> `http://localhost:8000`
- `ssh://ssh-<device-id>.<domain>` -> `localhost:22`, but only when support is enabled

The repo scripts that implement this are:

- `scripts/cloudflared_common.sh`
- `scripts/cloudflared_service.sh`
- `scripts/cloudflared_healthcheck.sh`
- `scripts/support_cloudflare_hook.sh`
- `scripts/cloudflared.service`

The backend reports tunnel state through:

- `GET /health`

The support UI/API uses:

- `GET /api/v1/support/ssh`
- `POST /api/v1/support/ssh/enable`
- `POST /api/v1/support/ssh/disable`

Those support endpoints only work when `SUPPORT_SSH_HOOK` is configured.

## Prerequisites

- Linux host with `systemd`
- `cloudflared` installed
- `sshd` running locally
- The web app reachable on `http://localhost:8000`
- A Cloudflare Zero Trust tunnel token
- DNS / public hostname setup in Cloudflare for:
  - `<device-id>.<domain>`
  - `ssh-<device-id>.<domain>`

## 1. Create the tunnel in Cloudflare

In Cloudflare Zero Trust:

1. Create a tunnel for the device.
2. Copy the tunnel token.
3. Create or verify the two public hostnames:
   - `<device-id>.<domain>`
   - `ssh-<device-id>.<domain>`
4. Add Access policies for the web hostname and the SSH hostname.

The scripts in this repo decode the tunnel token and render:

- `/etc/cloudflared/credentials.json`
- `/etc/cloudflared/config.yml`

## 2. Install `cloudflared`

On Debian/Ubuntu:

```bash
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
printf 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared %s main\n' "$(lsb_release -cs)" | sudo tee /etc/apt/sources.list.d/cloudflared.list >/dev/null
sudo apt-get update
sudo apt-get install -y cloudflared
```

If you already ran `./lociscientia.sh`, `cloudflared` may already be installed.

## 3. Install the repo-managed scripts

Copy the helper scripts into `/usr/local/bin`:

```bash
sudo install -m 755 scripts/cloudflared_common.sh /usr/local/bin/cloudflared_common.sh
sudo install -m 755 scripts/cloudflared_service.sh /usr/local/bin/cloudflared_service.sh
sudo install -m 755 scripts/cloudflared_healthcheck.sh /usr/local/bin/cloudflared_healthcheck.sh
sudo install -m 755 scripts/support_cloudflare_hook.sh /usr/local/bin/support_cloudflare_hook.sh
```

Install the systemd unit:

```bash
sudo install -m 644 scripts/cloudflared.service /etc/systemd/system/cloudflared.service
sudo systemctl daemon-reload
```

## 4. Create `/etc/default/cloudflared`

The helper scripts read `AITJE_*` variables from `/etc/default/cloudflared`.

Example:

```bash
sudo tee /etc/default/cloudflared >/dev/null <<'EOF'
AITJE_TUNNEL_TOKEN=eyJ...
AITJE_DEVICE_ID=klant-001
AITJE_DOMAIN=aitje.nl
AITJE_SUPPORT_SSH_DEFAULT=0

# Optional overrides
# AITJE_CLOUDFLARED_ENV_FILE=/etc/default/cloudflared
# AITJE_CLOUDFLARED_CONFIG_PATH=/etc/cloudflared/config.yml
# AITJE_CLOUDFLARED_CREDENTIALS_PATH=/etc/cloudflared/credentials.json
# AITJE_CLOUDFLARED_STATE_DIR=/var/lib/aitje/cloudflared
# AITJE_CLOUDFLARED_METRICS_HOST=127.0.0.1
# AITJE_CLOUDFLARED_METRICS_PORT=45231
EOF
```

## 5. Start the custom service

```bash
sudo systemctl enable cloudflared.service
sudo systemctl restart cloudflared.service
sudo systemctl status cloudflared.service
```

The wrapper script will:

- decode `AITJE_TUNNEL_TOKEN`
- generate `/etc/cloudflared/credentials.json`
- generate `/etc/cloudflared/config.yml`
- start `cloudflared tunnel run`
- expose a readiness endpoint on `http://127.0.0.1:45231/ready`

## 6. Configure the app `.env`

Add or verify these values in `.env`:

```env
CF_TUNNEL_ENABLED=true
CF_DEVICE_ID=klant-001
CF_DOMAIN=aitje.nl
SUPPORT_SSH_HOOK=/usr/local/bin/support_cloudflare_hook.sh
```

Optional status overrides if you changed the defaults:

```env
# CF_CLOUDFLARED_CONFIG_PATH=/etc/cloudflared/config.yml
# CF_CLOUDFLARED_CREDENTIALS_PATH=/etc/cloudflared/credentials.json
# CF_CLOUDFLARED_SUPPORT_STATE_FILE=/var/lib/aitje/cloudflared/support_ssh_enabled
# CF_CLOUDFLARED_METRICS_HOST=127.0.0.1
# CF_CLOUDFLARED_METRICS_PORT=45231
```

## 7. Allow the support hook to restart the service

`support_cloudflare_hook.sh` uses `sudo -n` by default. That means the user running the backend must be allowed to run these actions without an interactive password prompt:

- create `/var/lib/aitje/cloudflared`
- write `/var/lib/aitje/cloudflared/support_ssh_enabled`
- restart `cloudflared.service`

In practice, add a narrow `sudoers` rule for the backend user. The exact command paths vary by distro, so verify them with:

```bash
command -v install
command -v tee
command -v systemctl
```

If you do not want to use `sudo`, set:

```env
AITJE_CLOUDFLARED_USE_SUDO=0
```

but then the backend process itself must have permission to write the state file and restart the service.

## 8. Verify the setup

Check the cloudflared health script:

```bash
/usr/local/bin/cloudflared_healthcheck.sh
```

Check the backend health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

You should see a `cloudflared` object with values like:

- `configured: true`
- `status: connected`
- `service_active: true`
- `ready: true`

## 9. Test SSH support toggling

Before enabling support, the generated config should route the SSH hostname to `http_status:404`.

Enable support from the app UI or through the admin API:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/support/ssh/enable \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"duration_minutes":60}'
```

Disable it again:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/support/ssh/disable \
  -H "Authorization: Bearer <admin-token>"
```

The hook writes the state file:

- `/var/lib/aitje/cloudflared/support_ssh_enabled`

and restarts `cloudflared`, which regenerates the config with either:

- `ssh://localhost:22` when enabled
- `http_status:404` when disabled

## Current limitations

- The repo-managed tunnel scripts currently route to `localhost:22` and `localhost:8000` directly. They do not currently honor `CF_SSH_PORT` or `CF_WEB_PORT`.
- `./lociscientia.sh` installs `cloudflared`, but it does not install the custom `cloudflared_service.sh` / `support_cloudflare_hook.sh` flow.
- Backend tunnel status checks `cloudflared.service` specifically.

If you want the full functionality that the UI suggests, use the manual setup in this document rather than relying only on `./lociscientia.sh`.
