# Deployment

This repo stores desired deployment state. The live hosts are updated by copying the relevant files from the repo to the target host, then reloading services.

## Prerequisites

- SSH aliases: `khpi5`, `trmnl-pi`, `home-assistant`
- Docker Compose on `khpi5`
- Home Assistant packages enabled
- LaraPaper app key set outside git

Python dependencies for companion scripts are listed in `requirements.txt`.

## LaraPaper on khpi5

Repo files:

- `deploy/larapaper/docker-compose.yml`
- `deploy/larapaper/nginx/proxy_map.conf`
- `deploy/larapaper/nginx/fastcgi_params`
- `deploy/larapaper/.env.example`

Deploy:

```bash
scp deploy/larapaper/docker-compose.yml khpi5:/home/dave/larapaper/docker-compose.yml
scp deploy/larapaper/nginx/proxy_map.conf khpi5:/home/dave/larapaper/nginx/proxy_map.conf
scp deploy/larapaper/nginx/fastcgi_params khpi5:/home/dave/larapaper/nginx/fastcgi_params
ssh khpi5 "cd /home/dave/larapaper && docker compose up -d"
```

Live secrets belong in the deployment environment. Do not commit a real Laravel `APP_KEY`.

## khpi5 Companion Scripts

Repo files:

- `scripts/trmnl_calendar_multi.py`
- `scripts/trmnl_ha_dashboard.py`
- `scripts/trmnl_sonos_local.py`
- `scripts/run_trmnl_sonos.sh`
- `scripts/trmnl_mode_bridge.py`
- `scripts/trmnl_set_display_mode.sh`

Deploy:

```bash
scp scripts/trmnl_calendar_multi.py khpi5:/home/dave/trmnl-calendar/main.py
scp scripts/trmnl_ha_dashboard.py khpi5:/home/dave/trmnl_ha_dashboard.py
scp scripts/trmnl_sonos_local.py khpi5:/home/dave/trmnl-sonos-local.py
scp scripts/run_trmnl_sonos.sh khpi5:/home/dave/run_trmnl_sonos.sh
scp scripts/trmnl_mode_bridge.py khpi5:/home/dave/bin/trmnl-mode-bridge.py
scp scripts/trmnl_set_display_mode.sh khpi5:/home/dave/bin/trmnl-set-display-mode
ssh khpi5 "chmod +x /home/dave/run_trmnl_sonos.sh /home/dave/bin/trmnl-mode-bridge.py /home/dave/bin/trmnl-set-display-mode"
ssh khpi5 "sudo systemctl restart trmnl-mode-bridge.service"
```

## Pi Display Client

Repo files:

- `scripts/trmnl-display-shell.sh`
- `config/trmnl/show_img.json`
- `config/trmnl/config.example.json`
- `deploy/trmnl-pi/environment`
- `deploy/systemd/trmnl-display.service`

Deploy:

```bash
scp scripts/trmnl-display-shell.sh trmnl-pi:/home/dave/bin/trmnl-display-shell.sh
scp config/trmnl/show_img.json trmnl-pi:/home/dave/.config/trmnl/show_img.json
scp deploy/trmnl-pi/environment trmnl-pi:/tmp/trmnl-pi-environment
scp deploy/systemd/trmnl-display.service trmnl-pi:/tmp/trmnl-display.service
ssh trmnl-pi "sudo mv /tmp/trmnl-pi-environment /etc/environment"
ssh trmnl-pi "sudo mv /tmp/trmnl-display.service /etc/systemd/system/trmnl-display.service && sudo systemctl daemon-reload && sudo systemctl restart trmnl-display.service"
```

`config/trmnl/config.example.json` documents the expected shape, but the live file contains the device API key and must not be committed.

## Home Assistant

Repo files:

- `config/packages/trmnl_display_orchestration.yaml`
- `config/packages/trmnl_ha_dashboard.yaml`
- `config/packages/trmnl_jen_morning.yaml`

Deploy:

```bash
scp config/packages/trmnl_display_orchestration.yaml home-assistant:/config/packages/trmnl_display_orchestration.yaml
scp config/packages/trmnl_ha_dashboard.yaml home-assistant:/config/packages/trmnl_ha_dashboard.yaml
scp config/packages/trmnl_jen_morning.yaml home-assistant:/config/packages/trmnl_jen_morning.yaml
ssh home-assistant "ha core check"
ssh home-assistant "ha core restart"
```

The mode bridge bearer token must be stored in Home Assistant `secrets.yaml` as `trmnl_mode_bridge_bearer`.

## Post-Deploy Checks

```bash
ssh khpi5 "/home/dave/bin/trmnl-set-display-mode status"
ssh khpi5 "docker logs --tail 80 larapaper-app-1"
ssh trmnl-pi "journalctl -u trmnl-display.service --no-pager -n 80"
```

Confirm the physical display after the next Pi poll.
