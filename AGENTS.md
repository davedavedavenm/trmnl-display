# AGENTS.md — TRMNL Display

Management of TRMNL e-ink display integrations. Generates and deploys custom plugins/dashboards that show home assistant state, calendar, media, and other homelab data on the TRMNL device.

## Scope
- TRMNL plugin development (Liquid templates, Python render scripts)
- HA integration for display data
- Deploy scripts for pushing updates to the TRMNL device/API
- Out of scope: HA automations triggering the display — those live in `homelab-ha`

## Repo Structure

```
config/     — display and plugin configuration
deploy/     — deployment scripts
docs/       — changelog, notes
install/    — setup/install scripts
```

## Access

- **TRMNL API**: managed via deploy scripts; credentials in `.secrets/`
- **HA integration**: reads state via hass-mcp-plus MCP tools or REST API
- **khpi5**: display render scripts may run on khpi5

## Core Rules

1. **Test renders locally first** — run Python render scripts locally before deploying to device
2. **Liquid template syntax** — TRMNL uses Liquid; validate template syntax before pushing
3. **HA entity names change** — always verify entity IDs via `hass-mcp-plus` before hardcoding in templates
4. **API rate limits** — TRMNL API has limits; don't hammer it during development
5. **Secrets out of templates** — no credentials in Liquid or Python files

## MCP Tools

Access via MCPProxy (`http://127.0.0.1:8080/mcp`):
- `hass-mcp-plus` — live HA entity state for display data
- `nango-calendar` — calendar data for display
- `win-filesystem` — read/write template files on Windows
- `win-desktop-commander` — run render scripts

## Task Completion Workflow

1. **Execute** — develop or update the plugin/template
2. **Document** — add a dated entry to `docs/changelog.md` for non-trivial changes
3. **Commit** — stage only changed files (never `git add -A`); descriptive message (`trmnl: what and why`); push to origin
4. **Verify** — confirm the display renders correctly on device or in local preview

**Paths**:
- Windows: `C:\Users\Dave\repos\trmnl-display`
- khpi5: `/home/dave/repos/trmnl-display`

## Sub-Agent Use

Spawn sub-agents to fetch HA entity data while editing templates, or to read TRMNL API docs independently.

## Agent Memory Files

`.agent-memory/` (gitignored):
- `discoveries.md` — TRMNL API quirks, Liquid template gotchas, HA entity name changes
- `state.md` — current active plugins, known rendering issues
- `session-log.md` — brief dated log of display changes
