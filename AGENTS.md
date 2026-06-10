# Gelatinous

## Overview

Gelatinous is a setting-agnostic RPG codebase built on Evennia; the current MUD
is a sci-fi offworld-colony setting. Combat runs on the **G.R.I.M.** system —
four stats: **Grit** (toughness/health), **Resonance** (empathy/social/will),
**Intellect** (knowledge/crafting), **Motorics** (agility/combat/reflexes). Core
player experiences: exploration, tactical combat, grappling/restraint, and
character death with corpse/decay systems.

This file is the **agent operational reference** — conventions, workflow, and a
map of where things live. It is **not** an architecture manual: deep system
documentation lives in `specs/*.md`, and the code is the final source of truth.

Two structural facts shape everything you do here:

- **Evennia is not a Django project.** The gamedir overlays the Evennia library.
  There is no `manage.py` (the `evennia` launcher replaces it), and you extend
  the game with *typeclasses*, not custom Django models.
- **The dev repo is not the live game.** You edit in one checkout and deploy to a
  separate one running inside Docker. See *Project Layout & Deployment* below —
  changes are invisible to the running game until you sync them across.

## Project Layout & Deployment

There are two checkouts. Set the concrete paths/names for your environment;
this guide uses placeholders:

| Role | Placeholder | Notes |
|------|-------------|-------|
| **Dev repo** (edit here) | `<DEV_REPO>` | Default branch `master`. Run all `git` here. |
| **Live game** (runs here) | `<LIVE_DIR>` | Runs inside Docker container `<CONTAINER>`. Its own git checkout; deployed via hard-reset. **No `git` in the container** — run git on the host. |

The container runs code from the **live** dir, not the dev repo. Nothing you
edit takes effect until it is copied (during iteration) or merged-and-reset
(for deploy).

**Iterating / testing a change:**
```bash
# 1. Edit in the dev repo, then copy changed files into the live dir
cp commands/CmdFoo.py <LIVE_DIR>/commands/CmdFoo.py
# 2. Run tests inside the container (evennia + inflect live in the Docker venv,
#    NOT host python3; the host can only py_compile)
docker exec <CONTAINER> evennia test --settings settings.py world
docker exec <CONTAINER> evennia test --settings settings.py world.tests.test_foo
# 3. Run Django-dependent Python via the container shell
docker exec <CONTAINER> evennia shell --settings settings.py -c "..."
```

**Deploy cycle (every change, even docs):**
```bash
# issue -> branch -> PR -> merge, then sync the live checkout
gh issue create --label <feature|refactoring|documentation|bug> ...
git checkout -b <issue>-<short-desc>
# ... commit with "Closes #N" in the body ...
git push -u origin <branch>
gh pr create ...            # agent both creates AND merges PRs
gh pr merge <n> --squash --delete-branch
# hard-reset the live checkout to the merged master (git runs on the host)
git -C <LIVE_DIR> fetch origin --quiet
git -C <LIVE_DIR> reset --hard origin/master --quiet
# reload only when code changed (skip for docs-only)
docker exec <CONTAINER> evennia reload --settings settings.py
docker exec <CONTAINER> evennia status --settings settings.py   # Portal + Server RUNNING
```

Rules: **never force-push to `master`.** `gh` must be authenticated for the
repo. Every change — including docs — goes issue → branch → PR → squash-merge.

## Typeclasses and Attributes

Evennia hinges on *typeclass inheritance* and *attribute access*. Typeclasses are
customized Django models you can subclass while persisting as the same base model.
Subclass a base typeclass (Object, Character, Room, Exit, Account, Script) to
extend game mechanics.

Because all objects share a small set of model fields, arbitrary data lives in the
**Attribute** system. Access is `obj.db.attrname` (a convenience accessor for
`obj.attributes`). You **never** validate an attribute's existence — it returns
`None` if unset. Do **not** use `hasattr`/`getattr`/`setattr` on the Attribute
system.

Bad:
```python
if hasattr(obj.db, "attrname"):
    ...
```
Good:
```python
if obj.db.attrname is None:
    print("There is no 'attrname' attribute.")
```

For simple booleans, prefer the **Tag** system (`obj.tags`) over attributes. For
non-persistent arbitrary data, use the parallel `obj.ndb`/`obj.nattributes`
(regular Python attributes — `hasattr` is fine on `ndb`).

## Prototypes and Spawning

Do not confuse *defining typeclasses* (code logic) with *creating data*.
Typeclass hooks should only guarantee the Attribute data the code needs to
function. Define **actual data** with the **Prototype** system: reusable dicts
that spawn in-game objects. One `WanderingNPC` typeclass (the wander logic) backs
many prototypes (deer, goblin, lost hiker) — same code, different data.

## Commands

Commands are how players interact. The cmdhandler matches input against the
caller's cmdset and runs the matching command's `func`. Treat these
cmdhandler-assigned attributes as always present: `self.caller`, `self.account`,
`self.session`, `self.cmdstring`, `self.args`. Subclasses of `MuxCommand` get
richer parsing — consult it when needed.

Commands can `yield` for player input from inside `func`:
```python
class ExampleCommand(Command):
    key = "catch"

    def func(self):
        response = yield "Is your refrigerator running?"
        if response.lower() in ("yes", "y"):
            self.msg("Then you had better go catch it!")
```

## Utilities: When NOT to Roll Your Own

Evennia ships a large utility suite in `evennia.utils` — `create` (persistent
entities), `search` (finding entities), `evform`/`evmenu` (formatting and
interactive menus), and `evennia.utils.utils` (general helpers). **Always check
`evennia.utils` before writing your own helper.**

## Project Conventions

- **No magic strings.** Combat constants come from `world/combat/constants.py`;
  most other strings are centralized too — grep for the constant before hardcoding.
- **No broad `except Exception`.** Catch specific exceptions; let the unexpected surface.
- **Style.** PEP 8, 88-char lines, type hints on new functions.
- **Specs track code.** Update the relevant `specs/*.md` in the same PR as the change.
- **Per-observer rendering.** Any room broadcast that *names a character* must
  route through `world.identity_utils.msg_room_identity`, not
  `location.msg_contents()`, so each observer sees the actor/target by their own
  recognition memory. Pre-interpolate non-character tokens (items, body parts)
  into the template; the helper's `char_refs` dict is character-only. **Skip the
  helper for item-only broadcasts** (no character named) — per-observer rendering
  adds nothing there. See `specs/IDENTITY_RECOGNITION_SPEC.md`.
  ```python
  from world.identity_utils import msg_room_identity
  msg_room_identity(
      location=caller.location,
      template=f"{{actor}} injects {item.key} into {{target}}.",
      char_refs={"actor": caller, "target": target},
      exclude=[caller, target],
  )
  ```
- **`db.desc` rendering contract.** To give an item description, populate
  `self.db.desc` and let Evennia's default `return_appearance` slot it in — the
  Evennia-standard way. **Do not override `return_appearance`** to inject text.
  (`Organ.configure_from_harvest` / `Appendage.configure_from_sever` follow this;
  enforced by `world/tests/test_organ_display.py`.)

## File → Concept Map

| I need to... | Look in... |
|--------------|------------|
| Modify combat flow/turns | `world/combat/handler.py` |
| Change melee range rules | `world/combat/proximity.py` |
| Fix grappling mechanics | `world/combat/grappling.py` |
| Add/change combat constants | `world/combat/constants.py` |
| Modify attack/damage logic | `world/combat/utils.py` |
| Change combat messages | `world/combat/messages/*.py` |
| Modify attack command | `commands/combat/core_actions.py` |
| Add movement commands | `commands/combat/movement.py` |
| Add special actions | `commands/combat/special_actions.py` |
| Change character stats/behavior | `typeclasses/characters.py` |
| Modify items/weapons | `typeclasses/items.py` |
| Work on death/corpses | `typeclasses/corpse.py`, `typeclasses/deathscroll.py` |
| Change room behavior | `typeclasses/rooms.py` |
| Find object prototypes | `world/prototypes.py` |
| Modify identity/recognition/sdescs/keywords | `world/identity.py` |
| Change identity message routing | `world/identity_utils.py` |
| Fix target resolution/search | `world/search.py` |
| Modify emote/dot-pose tokenizer/renderer | `world/emote.py` |
| Add/change social templates | `world/emote_templates.py` |
| Fix grammar engine (conjugation, articles) | `world/grammar.py` |
| Modify say/whisper/emote commands | `commands/CmdCommunication.py` |
| Manage character descriptions (`describe`) | `commands/CmdCharacter.py` |
| Understand a system before implementing | `specs/*.md` |

## When Stuck

1. **`server/logs/server.log`** — tracebacks and errors.
2. **`server/logs/combat_audit.log`** — every combat/medical diagnostic, always on
   (async writes via `world/combat/debug.py`).  For live in-game output, set
   `SPLATTERCAST_LIVE = True` in settings to mirror it to the Splattercast channel.
3. **Grep for the constant** — most strings live in a `constants.py`.
4. **Trace from the command** — `commands/` calls into handler/system methods.
5. **Check NDB state** — many bugs are stale `char.ndb.*` references.
6. **Read the spec** — `specs/*.md` documents each system; Evennia docs at
   https://www.evennia.com/docs/latest/.

## Quick Reference

- Need new in-game mechanics? Subclass a base typeclass.
- Need data variation? Prototype, not a new typeclass.
- Need a persistent flag? Tag (attribute for complex data).
- Need a persistent object? `evennia.utils.create.*` or `evennia.prototypes.spawner.spawn`.
- Need persistent attributes? `obj.db.attr` (check `is None`, never `hasattr`).
- Need search? `caller.search` in a command, else `evennia.utils.search.*`.
- Need an interactive menu? `evmenu`. Need custom layout? `evform`.
- Naming a character in a room broadcast? `msg_room_identity`, not `msg_contents`.
- Giving an item a description? Set `db.desc`; never override `return_appearance`.
- Running tests? `docker exec <CONTAINER> evennia test --settings settings.py world`.
- Deploying? issue → branch → PR → squash-merge → hard-reset live → reload (code only).
