# Live Deployment Workflow

This document is the working contract for the current TRMNL/LaraPaper-based stack.

## Current Architecture
- Local repo: source of truth for templates, scripts, docs, and Home Assistant packages
- `khpi5`: live LaraPaper server and companion-script host
- Pi Zero / Inky device: thin display client only
- Home Assistant: orchestration and mode selection layer

Do not treat a local render or local code change as "done" for TRMNL work. The change is only complete once it has been deployed to `khpi5` and verified on the physical panel.

## First Visual Check
For this stack, the LaraPaper web UI preview and the generated PNG file are the first visual proxy for the live screen.

Use them before concluding anything about the physical panel:
- if LaraPaper preview is grayscale, the problem is still in the server render path
- if LaraPaper preview is colour but the panel is grayscale, the problem is in the final device path on `trmnl-pi`

## Deployment Rule
For any change that affects a TRMNL plugin, LaraPaper webhook flow, companion script, or Home Assistant orchestration path, follow this sequence:

1. Make and test the code change locally.
2. Push or copy the relevant change to `khpi5`.
3. Run the server-side script or refresh path on `khpi5`.
4. Confirm LaraPaper generated a fresh image and inspect the preview/PNG visually.
5. Confirm the Pi client pulled that image.
6. Confirm the physical display matches the intended result.

## Validation Gates
- Gate A: data fetch or payload generation succeeds
- Gate B: LaraPaper render succeeds and a new image is generated
- Gate C: `trmnl-display` pulls the new image successfully
- Gate D: the physical panel updates correctly
- Gate E: unrelated recipes still render cleanly

## Colour Rule
For the current 7.3" panel, the target is full ACeP palette usage, not grayscale fallback.

In practice that means:
- preserve distinct colours where the panel can render them well
- avoid accidentally biasing recipes toward monochrome for convenience
- treat a regression from colour to grayscale as a bug unless it is an intentional user-selectable mode

### ACeP 7-Color Palette Realities

The Pimoroni Inky Impression 7.3" uses Spectra/ACeP electrophoretic ink with 7 particles. How each CSS color actually renders on the panel:

| CSS Color | ACeP Reality | Design Guidance |
|---|---|---|
| `#000000` (Black) | Solid black | Use for backgrounds; reads well |
| `#FFFFFF` (White) | Solid white/paper | Use for primary text on dark |
| `#FF0000` (Red) | Vibrant red | Excellent for alerts, badges, emphasis |
| `#0000FF` (Blue) | Visible blue | Good for weather data, cold accents |
| `#00FF00` (Green) | Muted, dark olive | Renders very dark; avoid for text, use small indicators only |
| `#FFFF00` (Yellow) | Amber/gold | Good for labels, highlights on dark |
| `#FFA500` (Orange) | Visible orange | Good for Sonos, warmth, emphasis |

Design for the panel's actual output, not what your monitor shows. Green in particular is dramatically darker on ACeP than on an LCD.

## Sonos-Specific Rule
The Sonos recipe must preserve a colour-capable path.

If image preprocessing is used, it must be tunable and must not silently collapse the live output into grayscale-like rendering. If there is a tradeoff between legibility and colour richness, expose it as an explicit mode rather than baking it into a single default.

When Sonos appears grayscale:
- check the live Sonos payload first to see whether album art is present
- inspect the live LaraPaper preview/PNG
- verify the `inky_impression_7_3` device model on `khpi5` is still using the 7-colour palette and not a 1-bit black/white model
- only then adjust recipe styling or artwork preprocessing

## Known Root Cause
One confirmed failure mode already occurred in this project:
- LaraPaper on `khpi5` drifted so `inky_impression_7_3` was configured as `colors=2`, `bit_depth=1`, `palette=bw`
- result: all recipes rendered as black/white PNGs even when recipe code expected colour

Treat that configuration drift as a primary diagnostic check whenever colour disappears.

## Pangolin Reverse Proxy Setup

LaraPaper runs on `khpi5` (port 4567) and is served externally through a **Pangolin** reverse proxy at `https://trmnl.magnusfamily.co.uk`.

### Docker Compose Configuration

File: `/home/dave/larapaper/docker-compose.yml`

```yaml
services:
    app:
        image: ghcr.io/usetrmnl/larapaper:latest
        ports:
            - "4567:8080"
        environment:
            - APP_URL=https://trmnl.magnusfamily.co.uk
            - APP_TRUSTED_PROXIES=*
            - APP_TIMEZONE=Europe/London
            - ...
        volumes:
            - database:/var/www/html/database/storage
            - storage:/var/www/html/storage/app/public/images/generated
            - ./nginx/proxy_map.conf:/etc/nginx/conf.d/proxy_map.conf:ro
            - ./nginx/fastcgi_params:/etc/nginx/fastcgi_params:ro
```

Key environment variables:

| Variable | Value | Purpose |
|---|---|---|
| `APP_URL` | `https://trmnl.magnusfamily.co.uk` | Tells Laravel the canonical external URL. Used for route generation, email links, etc. |
| `APP_TRUSTED_PROXIES` | `*` | Trusts all reverse proxy IPs so Laravel reads `X-Forwarded-*` headers correctly |
| `ASSET_URL` | *(not set)* | Deliberately omitted — assets resolve relative to the request origin. Set this only if you need a dedicated CDN. |

### Custom Nginx Configs

**`./nginx/proxy_map.conf`** — Maps `X-Forwarded-Proto` header to an nginx `$https_flag` variable, ensuring Laravel detects HTTPS when accessed through the proxy:

```nginx
map $http_x_forwarded_proto $https_flag {
    https on;
    default off;
}
```

**`./nginx/fastcgi_params`** — Standard FastCGI params with the HTTPS flag injected:

```nginx
fastcgi_param  HTTPS $https_flag;
```

### Access Paths

| URL | Use Case |
|---|---|
| `http://192.168.1.143:4567` | Direct LAN access (Pi Zero device fetches from here) |
| `https://trmnl.magnusfamily.co.uk` | External access via Pangolin proxy (web UI, mobile) |

**Note:** The dashboard at `http://192.168.1.143:4567/dashboard` will render without CSS/JS if accessed via the local IP because `APP_URL` is set to the external domain. This is expected behaviour — always use `https://trmnl.magnusfamily.co.uk/dashboard` for the web UI, or remove `APP_URL` if you need both to work equally.

### Physical Device Fetch Path

The Pi Zero (`trmnl-pi`, `192.168.1.74`) polls the LaraPaper API at the local address:
```
GET http://192.168.1.143:4567/api/display
Headers: ID=88:A2:9E:2B:2B:B9, access-token=<api_key>
```

It does not use the proxy URL because it runs on the same LAN. The `image_url` returned by LaraPaper uses the proxy domain (via `APP_URL`), but the Pi client only uses the `filename` hash to verify changes and downloads the actual image from the same host it polled.

## Documentation Rule
When making decisions about TRMNL recipes, private plugins, palettes, BYOS behavior, or community-supported integrations:
- prefer official TRMNL documentation first
- then use official or well-supported community recipe guidance
- document any deliberate divergence in this repo

## Empirical Override Rule
When vendor documentation, product naming, or nominal hardware taxonomy conflicts with a render path that has already been validated on the live stack:
- prefer the empirically validated live render behavior
- do not change live palette/model assumptions without side-by-side proof that the new path is better on the actual screen
- treat the currently working LaraPaper + `trmnl-display` + `show_img` output as canonical until a replacement is tested and accepted

## Current Server Roles
- LaraPaper host: `khpi5`
- Display client: Pi Zero / Inky hardware
- Home Assistant role: orchestration, helpers, automations, webhook/script triggers

## Definition Of Done
A TRMNL-facing change is done only when:
- the repo is updated
- the live server on `khpi5` is updated
- the generated output is validated
- the physical display is checked
