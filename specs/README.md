# Specifications Directory

This directory contains detailed specifications for various features of the Gelatinous MUD project.

---

## Core Specifications (Required)

These specs document core game systems that are always active:

### Combat System
- `GRAPPLE_SYSTEM_SPEC.md` - Grappling mechanics
- `PROXIMITY_SYSTEM_SPEC.md` - Tactical positioning
- `COMBAT_MESSAGE_FORMAT_SPEC.md` - Combat messaging system

### Commands
- `JUMP_COMMAND_SPEC.md` - Jumping between rooms
- `THROW_COMMAND_SPEC.md` - Throwing items/characters
- `WREST_COMMAND_SPEC.md` - Taking items by force

### World Simulation
- `WORLD_STATE_INTELLIGENCE_SYSTEM_SPEC.md` - Zone-level world state simulation, threat scoring, anomaly detection, and player-facing intelligence terminals (design phase)

---

## Optional Specifications (Forum Integration)

**These are completely optional** - only needed if you're running a Discourse forum:

### Main Guides
- **`FORUM_INTEGRATION_GUIDE.md`** - Overview: Do you need forum integration? How to remove it if not needed.
- **`DISCOURSE_INTEGRATION.md`** - Complete step-by-step setup guide with all code snippets ready to copy/paste.

**Note**: If you're not using Discourse, these files won't affect your game. The code is designed to gracefully degrade when Discourse settings are not configured.

---

## How To Tell If You Need Forum Integration

### ✅ You MIGHT want it if:
- You want persistent, searchable community discussions
- You want to provide game guides, announcements, or support forums
- You have resources to run/manage a separate Discourse instance
- You want unified login between game and forum

### ❌ You DON'T need it if:
- You only want in-game chat (Evennia has channels built-in)
- You prefer Discord or another existing platform
- You're just getting started and want simplicity
- You don't want to manage a separate service

---

## Quick Check: Is Forum Integration Active?

Look at your `server/conf/secret_settings.py`:

```python
# If you see this and it's set to a real value:
DISCOURSE_SSO_SECRET = "some-secret-here"
DISCOURSE_URL = "https://forum.yourgame.com"

# Then forum integration is active.

# If these don't exist or are commented out:
# Then forum integration is disabled.
```

---

## Removing Forum Specs (Optional Cleanup)

If you're certain you won't use forum integration:

```bash
# Remove optional forum specs
rm specs/DISCOURSE_*.md
rm specs/FORUM_INTEGRATION_*.md
rm specs/CACHING_AND_PRECONNECT_SETUP.md
```

The game will work exactly the same - these are just documentation files.

---

## Questions?

- **Game doesn't work**: Forum specs are documentation only - they don't affect game functionality
- **Want to add forum later**: Just follow `FORUM_INTEGRATION_GUIDE.md` when ready
- **Want to use different forum**: The iframe approach works with other platforms too
- **Confused about optional vs required**: When in doubt, ignore Discourse specs - you don't need them unless you're specifically setting up a forum

---

## Summary

```
Core Specs (always relevant):
├── GRAPPLE_SYSTEM_SPEC.md
├── PROXIMITY_SYSTEM_SPEC.md
├── COMBAT_MESSAGE_FORMAT_SPEC.md
├── JUMP_COMMAND_SPEC.md
├── THROW_COMMAND_SPEC.md
├── WREST_COMMAND_SPEC.md
└── WORLD_STATE_INTELLIGENCE_SYSTEM_SPEC.md  ← World simulation & intel (design phase)

Forum Specs (optional - only if using Discourse):
├── FORUM_INTEGRATION_GUIDE.md    ← Overview & decision guide
└── DISCOURSE_INTEGRATION.md      ← Complete setup instructions
```

When in doubt: **Ignore the forum specs** - they're optional enhancements, not requirements.
