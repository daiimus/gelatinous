# Planning generators (2026-08-05 architecture phase)

Analysis/visualization scripts from the city-architecture sessions —
these DERIVE the plates and drafts the owner reviewed, from the live
map export. Not build scripts; nothing here mutates the game.

- `cityplan.py` — as-built + City Section plan plates (PNG)
- `roofplan.py` — Roof Plan v1 (superseded; kept for the derivation)
- `scaffold.py` — Roof Plan v3: per-building flat datums, 1:1-only
  street crossings with auto-equalization, the Long Climb, the high
  town + skywalks; emits `scaffold_blocks.json`
- `manifest.py` — renders `specs/proposals/CITY_SCAFFOLD.md` from the
  blocks json (names/programs per district)
- `corridors.py` — Wall Run + Architecture Climb elevation plates
- `channel.py` — Central Channel cross-section + long profile plates

All read `city.json` (dump `world.mapping.export_map()` to get a fresh
one) and render via Pillow (`scripts/atlas/.venv`). Re-run after map
changes; argue with the constants at the top of each.
