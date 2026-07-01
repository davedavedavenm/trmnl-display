# TRMNL Orchestration Audit — 2026-06-26

## Executive Summary

Live read-only audit of the TRMNL/LaraPaper orchestration after the
TRMNL display switched from `calendar` to `jen_morning` at 06:45:03 BST on
2026-06-26. The orchestration worked exactly as designed — no bug in
the resolver, the cascade, the mode bridge, or the LaraPaper side. The
Pi service restart that produced the on-screen change was caused by an
explicit `ssh ... systemctl restart` line in the mode script on `khpi5`,
not by the systemd `morning-start.timer` on the Pi (which fires 2-3 s
earlier and is now redundant for the morning case). The
`morning-start.timer` is worth keeping as a safety net for the night-stop
recovery case.

This document is the live schedule reference and the canonical writeup
of the orchestration behaviour observed on 2026-06-26.

## What scheduled the 2026-06-26 jen_morning switch

### Source

`config/packages/trmnl_display_orchestration.yaml` — automation
`trmnl_resolve_display_mode_v1`.

- Re-evaluates every 1 minute via `time_pattern: minutes: "/1"`
- Also re-evaluates on changes to ~25 helper entities (mode booleans,
  commute state, person state, media player states, etc.)
- Only acts when `input_boolean.trmnl_display_automation_enabled` is `on`

### Cascade (first match wins)

| # | Check | Current value | Result |
|---|---|---|---|
| 1 | `trmnl_alert_active` | off | — |
| 2 | `trmnl_display_manual_override` ≠ `auto` | `auto` | — |
| 3 | sonos playing or hold timer | none | — |
| 4 | `jen_heading_home` or commute state in journey | no | — |
| 5 | **`trmnl_jen_morning_enabled` + weekday + now in [start, end]** | on, Fri, 06:45–07:45 BST | **MATCH** |
| 6 | `dave_commute_active` | off | — |
| 7 | bus window 07:50–09:30 weekday | too early | — |
| 8 | night window (≥ 22:50 or < 06:40) | just closed | — |
| 9 | default = `calendar` | `calendar` | lost to #5 |
| 10 | default = `ha_dashboard` | not set | — |
| 11 | else | `idle` | not reached |

### HA helpers that drive the morning window (live values on 2026-06-26)

| Helper | Value | Last written | Source |
|---|---|---|---|
| `input_datetime.trmnl_jen_morning_start` | `06:45:00` (Europe/London / BST) | 2026-06-25T19:59:03 UTC | `core.restore_state` |
| `input_datetime.trmnl_jen_morning_end` | `07:45:00` (Europe/London / BST) | 2026-06-25T19:59:03 UTC | `core.restore_state` |
| `input_boolean.trmnl_jen_morning_enabled` | `on` | 2026-06-25T19:59:03 UTC | `core.restore_state` |
| `input_select.trmnl_display_mode` | `jen_morning` (was `calendar` until 06:45:00) | 2026-06-26T05:45:00 UTC | `core.restore_state` |

All three jen_morning helpers were last written at the same moment
with `user_id: null`, which means they were not set by a human in the
HA UI. The original setter is unknown (HA recorder DB is stale at
2025-12-13, so 6+ months behind). Most likely cause: a package reload,
a backup-restore, or a previous `input_datetime.set_datetime` service
call without a user context.

The LaraPaper `Jen Morning` plugin (id 24) is itself a webhook-driven
plugin (`data_strategy: webhook`); HA pushes data into it via the
`trmnl_jen_morning_push` REST command in `config/packages/trmnl_jen_morning.yaml`.
The most recent push was at `2026-06-26T05:05:06 UTC` (06:05 BST) —
separate from the mode flip at 06:45 BST.

## Reconstructed timeline (all times BST)

| Time | What happened | Source |
|---|---|---|
| 06:05:06 | Jen Morning LaraPaper plugin data refreshed by HA `trmnl_jen_morning_push` | LaraPaper DB `data_payload_updated_at` |
| 06:40:00 | `trmnl-display-morning-start.timer` fires on `trmnl-pi` | Pi systemd journal |
| 06:40:02 | khpi5 SSHes to trmnl-pi as `dave` and runs `sudo systemctl restart trmnl-display.service` (calendar mode change) | Pi sshd journal: `COMMAND=/usr/bin/systemctl restart trmnl-display.service` from 192.168.1.143 |
| 06:40:26 | Pi polls LaraPaper, gets calendar image, displays. 7200 s sleep. | Pi `trmnl-display-shell.sh` |
| 06:45:00 | HA resolver flips `input_select.trmnl_display_mode` to `jen_morning` | HA `trmnl_resolve_display_mode_v1` |
| 06:45:00 | `trmnl_apply_display_mode_v1` calls `rest_command.trmnl_set_display_mode` with `mode: jen_morning` | HA package |
| 06:45:00 | Mode bridge on khpi5:8787 receives POST, runs `trmnl-set-display-mode jen_morning` | mode bridge log + LaraPaper DB playlist activation |
| 06:45:02 | khpi5 SSHes to trmnl-pi as `dave` and runs `sudo systemctl restart trmnl-display.service` (jen_morning mode change) | Pi sshd journal: `COMMAND=/usr/bin/systemctl restart trmnl-display.service` from 192.168.1.143 |
| 06:45:27 | Pi polls, gets jen_morning image, displays. 600 s sleep. | Pi `trmnl-display-shell.sh` |
| 06:55:27 | jen_morning refresh | Pi loop |
| 07:06:15 | jen_morning refresh | Pi loop |
| 07:16:15 | jen_morning refresh (next) | Pi loop |

## The 06:45:03 Pi restart — who, what, where

The Pi `trmnl-display.service` was stopped and immediately restarted
at 06:45:03.221 BST. The systemd journal shows this is a single
`JOB_TYPE=restart` (`JOB_ID=5203`) issued by systemd — not a crash,
not a `Restart=always` recovery, but an explicit external `systemctl
restart` call.

The smoking gun is in the Pi sshd journal:

```
Jun 26 06:45:02 trmnl-pi sshd[73317]: Accepted publickey for dave from
    192.168.1.143 port 60116 ssh2: ED25519
    SHA256:/2elo0DZ0bmXmXdoSV6houKcrdDRNM4cI/5gbj+xPk8
Jun 26 06:45:03 trmnl-pi sudo[73346]:     dave : PWD=/home/dave ;
    USER=root ; COMMAND=/usr/bin/systemctl restart
    trmnl-display.service
Jun 26 06:45:03 trmnl-pi sshd[73345]: Received disconnect from
    192.168.1.143 port 60116:11: disconnected by user
```

The same key fingerprint is `dave@Docker-VM`. The source IP
`192.168.1.143` is `khpi5` (the LaraPaper server). The same pattern
appeared at 06:40:02 (when the morning mode was `calendar`).

Tracing back to the cause: the final 2 lines of
`scripts/trmnl_set_display_mode.sh` (which mirrors
`/home/dave/bin/trmnl-set-display-mode` on khpi5) are:

```bash
# Wake up the physical display client to force an immediate pull of
# the new mode/content
echo "Waking up physical display client..."
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
    trmnl-pi "sudo systemctl restart trmnl-display.service" || true
```

So every call to `trmnl-set-display-mode` from the mode bridge
triggers an SSH to the Pi that restarts the display service. This is
an explicit, intended, and documented-by-comment design choice to
make mode changes visible immediately rather than waiting up to 600 s
for the Pi's next poll.

**This means the display change at 06:45:03 was caused by HA's
jen_morning mode activation**, not by the systemd morning-start.timer
(which ran 2-3 s earlier and was overridden by the same restart).

## Why the morning-start.timer is now redundant (but worth keeping)

The systemd timer at 06:40 (`/etc/systemd/system/trmnl-display-morning-start.timer`,
mirrored at `deploy/trmnl-display-morning-start.timer`) fires
`systemctl start trmnl-display.service` at 06:40 every day.

In the 2026-06-26 case:

1. 06:40:00 — timer fires, service started
2. 06:40:02 — khpi5 SSHes in and restarts the service (calendar mode change)
3. The timer's `start` is overridden by the restart 2 s later

The timer is still useful for the **night-stop recovery case**: if the
night-stop timer stopped the service at 23:00 and the HA mode is
already set to `ha_dashboard` or `jen_morning` for the next morning,
the local timer at 06:40 ensures the Pi wakes up and starts polling
even if HA is down or the mode bridge has lost the new mode.

The paired night-stop timer should not replay missed stops after the
Pi has been offline or asleep. It is intentionally configured with
`Persistent=false`, and the stop unit has a local-time `ExecCondition`
guard so a stale 23:00 stop cannot terminate the display during a
morning or daytime boot.

**Recommendation:** keep the timer as a safety net. Retiring it would
require the HA resolver to also push a "wake the Pi" SSH or to make
the Pi poll continuously. Both have higher cost than the current
redundancy.

## Current live schedule reference (as of 2026-06-26)

| Window | Condition | Source |
|---|---|---|
| **jen_morning** | weekday, `06:45 ≤ now < 07:45` (Europe/London) | `trmnl_resolve_display_mode_v1` + `input_datetime.trmnl_jen_morning_{start,end}` |
| **bus** | weekday, `07:50 ≤ now < 09:30` | `trmnl_resolve_display_mode_v1` `bus_window_active` |
| **night** | `now ≥ 22:50` or `now < 06:40` | `trmnl_resolve_display_mode_v1` `night_window_active` |
| **default weekday** | `calendar` | `input_select.trmnl_display_default_mode_weekday` |
| **default weekend** | `ha_dashboard` (only if no weekend calendar events) | `input_select.trmnl_display_default_mode_weekend` + `input_boolean.trmnl_weekend_has_calendar_events` |

### Per-mode display refresh interval (set by `trmnl_set_display_mode.sh`)

| Mode | Refresh (s) | Notes |
|---|---|---|
| `bus` | 600 | live departure times |
| `sonos` | 60 | now-playing |
| `jen_commute` | 420 | ETA, slower than now-playing |
| `jen_morning` | 600 | morning headline + quote |
| `ha_dashboard` | 600 | sidecar-rendered |
| `dave_commute` | 600 | placeholder for future |
| `alert` | 600 | placeholder for future |
| `calendar` | 7200 | slow-changing |
| `idle` | 7200 | slow-changing |

### Toggle helpers (`trmnl_mode_*_enabled`)

| Helper | Default | Purpose |
|---|---|---|
| `trmnl_mode_calendar_enabled` | on | gate calendar mode |
| `trmnl_mode_sonos_enabled` | on | gate sonos mode |
| `trmnl_mode_jen_commute_enabled` | on | gate jen commute |
| `trmnl_mode_dave_commute_enabled` | on | gate dave commute |
| `trmnl_mode_alert_enabled` | on | gate alert |
| `trmnl_jen_morning_enabled` | on | gate jen morning window |
| `trmnl_display_automation_enabled` | on | master switch for resolver |
| `trmnl_display_manual_override` | `auto` | per-mode pin (`auto` lets resolver run) |

## HA Dashboard package observations / recommendations

`config/packages/trmnl_ha_dashboard.yaml` defines the HA dashboard
plugin integration, the sidecar refresh, and the Lovelace helper
view. Audit observations:

1. **The 120 s cooldown in `trmnl-refresh-ha-sidecar` is appropriate.**
   It prevents refresh storms from media_player or Sonos triggers.
2. **The helper-change-triggered refresh fires regardless of active
   mode.** `trmnl_ha_dashboard_helper_change_refresh_v1` runs on any
   change to the slot or generic-entity helpers, even when the
   current mode is `calendar`, `sonos`, `jen_morning`, etc. This is
   wasted work — the sidecar image is only displayed when
   `trmnl_display_mode == 'ha_dashboard'`. **Recommendation:** gate
   the sidecar refresh to only run when the active mode is
   `ha_dashboard`:
   ```yaml
   condition:
     - condition: state
       entity_id: input_select.trmnl_display_mode
       state: "ha_dashboard"
   ```
   No change in this commit; filed as a follow-up.
3. **The `trmnl_ha_dashboard_refresh_button_v1` correctly uses
   `force: true`** to bypass the 120 s cooldown. This is the right
   shape for the "user explicitly wants the dashboard now" path.
4. **The sidecar handoff in `trmnl-set-display-mode` (the `ha_dashboard`
   branch) is the right place to push the rendered PNG into LaraPaper
   and update `devices.current_screen_image`.** This keeps the
   dashboard up to date immediately on mode change, without waiting
   for the next scheduled refresh.

## Open follow-ups (not in this commit)

1. **HA recorder DB is stale at 2025-12-13** (6+ months behind). The
   actual `core.service` calls and helper mutations from the past
   6 months are not in the recorder. Either the recorder is paused,
   misconfigured, or running on a different host. Investigate.
2. **The original setter of `trmnl_jen_morning_start = 06:45:00`** is
   unknown. The value was first written before the recorder
   started tracking, so the history is lost. Worth re-asking: is
   06:45 the right morning start, or should it be e.g. 06:30 (matches
   the night window close at 06:40) or 07:00 (matches work start
   time)?
3. **Consider retiring `trmnl-display-morning-start.timer` and
   `trmnl-display-night-stop.timer`** in a future commit if a
   quiet-week observation confirms the HA resolver is reliable. The
   current redundancy is safe but not strictly necessary.
4. **Apply the `trmnl_ha_dashboard_helper_change_refresh_v1` gating
   recommendation** above. One-line condition addition.
5. **Re-derive `trmnl_jen_morning_start` from `trmnl_display_default_mode_weekday`
   or a related helper** so the morning window is a single point of
   truth instead of a separate time range.

## Read-only operations used in this audit (for reproducibility)

- `journalctl` on `trmnl-pi` (display + sshd, verbose and -o short-full)
- `systemctl cat` and `systemctl list-timers` on `trmnl-pi` and `khpi5`
- `docker logs larapaper-app-1 --since/--until` on `khpi5`
- `python3` with `sqlite3` stdlib against `/home/dave/tmp/larapaper.sqlite`
  and `/config/.storage/core.restore_state` (read-only via SSH)
- `jq` against `/config/.storage/core.restore_state` on HA host
- `last`, `ip neigh`, `ss -tunlp`, `find` (read-only env audit)
- `scp` of read-only audit scripts to `/tmp/` on each host
- `cat` of system files: mode script, service units, bash/zsh history

No live-host changes were made during this audit. The only repo
changes are the doc updates and the cross-references in
`docs/SOURCE_OF_TRUTH.md`, captured in this commit.
