# Custom InkyPi Setup

This fork includes a custom `calendar_album` plugin with an album background feature.

## Auto-Update Configuration

The device is configured to automatically sync with the official InkyPi repo while preserving custom plugins.

### Git Remotes (on device)
```
origin   → https://github.com/davedavedavenm/InkyPi.git (this fork)
upstream → https://github.com/fatihak/InkyPi.git (official)
```

### Update Script (`/usr/local/sbin/inkypi-auto-update.sh`)
```bash
#!/usr/bin/env bash
set -e
cd /home/dave/InkyPi

# Sync with official repo
git fetch upstream
git merge upstream/main --no-edit || true

# Push to fork
git push origin main || true

# Pull and apply updates
git pull --ff-only
sudo bash install/update.sh
```

### Cron Schedule
Runs every 14 days at 04:30 via `/etc/cron.d/inkypi-auto-update`

## Custom Plugin: calendar_album

Located in `src/plugins/calendar_album/`

Features:
- 2-day time grid view (`timeGridTwoDay`)
- Random background image from album
- Customized CSS for e-ink display
- 70% opacity headers and time column
- Full viewport coverage

## Why Custom Plugin is Safe During Updates

The `calendar_album` directory only exists in this fork, not in the official repo. Git merge only affects files that exist in BOTH repos, so this plugin will never be touched by upstream merges.
