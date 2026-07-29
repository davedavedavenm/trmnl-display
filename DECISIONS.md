# Decisions — TRMNL Display

Settled, closed questions for this repo. Check here before proposing to
change, redo, or re-open something; update this file in the same session a
decision is settled or reversed.

Status values: **Active** · **Superseded** · **Historical**.

---

## Colour architecture — Active

The live hardware is a 6/7-colour ACeP Spectra panel (Pimoroni Inky
Impression 7.3), not a standard monochrome TRMNL panel. Colour-critical
dashboards use the repo-owned indexed-colour sidecar renderer; LaraPaper
remains the BYOS management layer unless explicitly replaced. Never "fix"
this stack toward common monochrome TRMNL assumptions — that's a
regression, not a simplification.

## Plugin portability — Active

Every plugin/recipe must be fully configurable via the TRMNL/LaraPaper web
UI from `settings.yml`. Sidecar renderers must read settings (themes,
layouts, entity mappings, credentials) from the plugin payload/database —
never hardcode local entity IDs, labels, URLs, or room names into reusable
plugin logic. Hardcoding turns a shareable plugin into a private screen.

## Plugin interchange format — Active

This repo stores the **flat** interchange shape (templates + `settings.yml`
at each plugin root) as source of truth, matching the official TRMNL
private-plugin ZIP format — not the `src/` dev-time layout `trmnlp` uses
internally. Don't migrate plugins into `src/` without updating the
sidecar renderers and `scripts/validate_trmnl_ha_plugin_contract.py`, which
read the flat paths directly.

## CI scope — Active

The official `trmnlp push`-to-cloud CI job is intentionally omitted. This
stack distributes through LaraPaper BYOS and this repo, not the TRMNL cloud
marketplace — don't add a push-to-cloud step expecting it to be needed.

## Repo hygiene & scratch artifacts — Active

`scripts/tmp/` is for disposable dev artifacts: only the two dated sidecar
proof PNGs (`sidecar_colour_dashboard_proof_2026-05-01.png` and its source
proof) are tracked; everything else there is cleaned periodically and must
not be relied on or referenced. Root-level scratch/review/test images,
`scratch_*.py`, and `/tmp/` are never tracked. A cleanup pass on 2026-07-29
removed ~200 ignored clutter files plus five unreferenced tracked dev
artifacts; `.env`, `.gemini/`, and the proof PNGs are intentionally kept.
Keep the tree clean rather than letting scratch files accumulate.
