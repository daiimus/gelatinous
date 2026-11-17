# Gelatinous

> **Read two more files before you change anything:** [`DEVELOPMENT_GUIDE.md`](DEVELOPMENT_GUIDE.md) (core principles, decision priority order, code standards) and [`WORKFLOW.md`](WORKFLOW.md) (how work is classified, labelled and tracked). The three files are one set of instructions.

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
  the game with *typeclasses*, not custom Django models. The one custom model
  is `KeywordEvent` in `world/models.py`, an audit-log table; do not add another.
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
# 4. When the run ends, put the live dir back: restore the files you copied,
#    delete the ones that are new, and check that status prints nothing
git -C <LIVE_DIR> checkout -- commands/CmdFoo.py
git -C <LIVE_DIR> status --short
```

Step 4 is not optional. The live dir is what the game loads at its next
reload, whoever asks for that reload; an unmerged file left there goes live
with it.

**Deploy cycle (every change, even docs):**
```bash
# issue -> branch -> PR -> merge, then sync the live checkout
gh issue create --label "type: <defect|enhancement|design|question|debt>" --label "area: <subsystem>" ...   # labels: see WORKFLOW.md
git checkout -b <issue>-<short-desc>
# ... commit with "Closes #N" in the body ...
git push -u origin <branch>
gh pr create ...            # agent both creates AND merges PRs
gh pr merge <n> --squash --delete-branch
# hard-reset the live checkout to the merged master (git runs on the host)
git -C <LIVE_DIR> fetch origin --quiet
git -C <LIVE_DIR> reset --hard origin/master --quiet
# reload only when code changed (skip for docs-only), and only with the
# owner's go: from a developer character logged in to the game, type
# @reload   (see below), then
docker exec <CONTAINER> evennia status --settings settings.py   # Portal + Server RUNNING
```

Rules: **never force-push to `master`.** `gh` must be authenticated for the
repo. Every change — including docs — goes issue → branch → PR → squash-merge.

**Reload from inside the game.** The preferred reload is `@reload`, typed by a
developer character that is logged in. It asks the Portal for the same restart
the command line does, and nothing outside the game waits on it. The
command-line `evennia reload` starts a launcher process that waits for the
restart; run from an agent's shell it has been chained, piped and cut off by a
timeout mid-restart, and each time the Server stayed down. Use it only when
there is no session to reload from, and then as the only command in its call.

Being logged in does not make a reload safe by itself. Before it, look at who
is connected. A reload does not wait for a model call that is in flight: it
abandons it, so an NPC's reply in progress is lost, and the next replies may
be slow while the model server finishes the abandoned one (#3815). A reload
does wait for work on Evennia's own worker pool, and fails if that work takes
more than a moment; today only the `bug` command puts any there (#3856).
After it, check `evennia status` within 30 seconds; if the Server is not
running, read `server/logs/server.log` and run `evennia start`.

A reload pauses the game for everyone in it and clears the `ndb` state on
every object, so each one needs the owner's go (see `WORKFLOW.md`, Rulings).

**A reload restarts the Server, not the Portal.** A setting the Portal reads
(for example Django's `SECRET_KEY`, ports and interfaces, `UPSTREAM_IPS`)
takes effect only when the Portal itself is restarted, and that disconnects
everyone. Count the restart as part of such a change, and get the owner's go
for it.

**The repository is public.** An issue, a pull request and a commit are all
published the moment they are written:

- No player names, account names or network addresses in any of them. Say who
  in general terms ("a player character", "an NPC at the bar").
- No session links and no "generated with" lines in commits or pull requests.
  Commits are authored with a GitHub no-reply address; a `Co-Authored-By`
  trailer that also uses a no-reply address is fine.
- Never ask for a third-party key or token in conversation, and do not use one
  that is offered there. Secrets live in `server/conf/secret_settings.py`,
  which is not in git.

**Before merging:**

- Every check on the pull request has passed. Wait for them; do not merge
  while one is pending.
- A change to how the game behaves has been read by an independent reviewer
  whose job is to refute it, not to approve it, and what they found is fixed
  or answered. For a docs-only or test-only change this may be skipped by
  stated judgment: say so in the pull request.
- New files are in the commit. Stage with `git add -A` or explicit paths;
  `git add -u` leaves a new file out without a word, and local tests still
  pass because the file is in the working tree.

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
non-persistent arbitrary data, use the parallel `obj.ndb`/`obj.nattributes`.

`ndb` answers the same way `db` does: a name that was never set reads as
`None`. So `hasattr(obj.ndb, name)` is true for every name, and the default in
`getattr(obj.ndb, name, default)` is never returned. Test `is None` there
too. (`world/tests/test_ndb_guards_are_not_guards.py` pins this. Older code
still has `hasattr` guards and `getattr` defaults on `ndb`; they are debt, not
a pattern.)

## Prototypes and Spawning

Do not confuse *defining typeclasses* (code logic) with *creating data*.
Typeclass hooks should only guarantee the Attribute data the code needs to
function. Define **actual data** with the **Prototype** system: reusable dicts
that spawn in-game objects. One `Item` typeclass (`typeclasses/items.py`) backs
over a hundred prototypes in `world/prototypes.py` — same code, different data.

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

## Before Changing Code

- **Read before judging.** Before calling code dead, or changing what a
  function does, read its spec, the whole function, every caller and the tests
  that pin it. A search that finds no caller is not proof: commands are reached
  by their `key` and aliases, hooks by Evennia, typeclasses by a path stored in
  the database. Read the spec before designing too; the thought has usually
  been had (`grep` the concept in `specs/`).
- **Search for the mechanism, not the name.** Before writing a helper, or
  saying something does not exist, search for the primitive it would use (the
  query, the attribute, the Evennia call, the alias list). The thing usually
  exists under a name you would not have guessed.
- **List every caller before adding a check.** When the fix is "send every
  caller through this check", list the callers across the whole repo first,
  and prefer to put the check in the shared function beneath them. A test
  that only scans the file being edited cannot find the caller in another
  file.
- **Most acts have more than one door.** An umbrella command and a standalone
  verb (`operate` and `harvest`), or a menu and a typed argument. They tend to
  share a resolver and not their checks, so they drift apart unnoticed: the
  working door gets used and the broken one does not. A fix covers every door,
  and is played through each.
- **Do not pick out people by typeclass.** Many of the colony's people are
  `typeclasses.llm_npc.LLMNpc`, so a filter on a path containing "character"
  finds only some of them and looks as if it found all. A body is whatever
  owns a `longdesc` attribute in the `appearance` category. And an attribute
  stored with a category is read with it: `obj.attributes.get("longdesc")`
  returns `None` for a character that has one.
- **Stay on plain Evennia.** Extend it the ways it offers: its APIs, hooks and
  typeclasses, and the classes its settings let a game name (the test runner
  in `server/conf/test_runner.py` and the websocket protocol are plugged in
  that way). Do not go beneath those: no patching of Evennia's modules at run
  time, no replacing its loggers, launcher or server lifecycle, even to fix a
  real fault. Its ordinary behaviour is not a defect to file here, and
  reporting anything upstream is the owner's call.
- **One issue, one fix.** Use the simplest mechanism the code already has. A
  remark about what might come later is not scope; record it on the issue and
  leave it there.

## Project Conventions

- **No magic strings.** Combat constants come from `world/combat/constants.py`;
  most other strings are centralized too — grep for the constant before hardcoding.
- **No broad `except Exception`.** Catch specific exceptions; let the unexpected surface.
  The one allowed use is a boundary where a failure in something optional must
  not break the thing that matters (a flavour line must not block a mechanic).
  A new one is marked `# noqa: BLE001` and says why on the same line. Older
  code has broad catches with no mark or no reason; that is debt, not a pattern.
- **Nothing slow on Evennia's worker pool.** `run_async` and `deferToThread`
  put work on the reactor's pool, and a reload waits for every thread in it,
  so one slow call there leaves the game down (#3815). A call that can block
  for more than a moment (a model, a remote service) goes through
  `world.llm.detached.run_detached`.
  `world/tests/test_model_calls_leave_the_worker_pool.py` lists the files
  still allowed on the reactor's pool.
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
  Evennia-standard way. **Do not override `return_appearance` to supply the
  description.** Overrides exist, and each has a reason other than that: it
  adds to what is shown (what is worn or held, a state) on top of `super()`,
  or the whole appearance is computed (a character's body, a corpse, a room,
  graffiti, a blood pool). A new override needs a reason of that kind.
  (`Organ.configure_from_harvest` / `Appendage.configure_from_sever` follow this;
  enforced by `world/tests/test_organ_display.py` and
  `world/tests/test_severed_part_descriptions.py`.)

## Design Laws

Rulings the owner has already made. Do not propose against them. Each names
where the detail is held.

- **No carried containers.** Inventory is flat: what is in the hands and what
  is carried loose. There is no bag, satchel, backpack or kit that holds
  whatever is put in it, and `put` refuses everything but a plate into a plate
  carrier and an item into an open locker. Some things hold their own contents
  and nothing else (a pack of cigarettes, a plate carrier, a corpse with what
  was on it, a severed limb with what was fitted to it); they are not an
  opening for a general container. A character's "kit" is loose items.
  (`specs/MODULAR_ARMOR_SYSTEM_SPEC.md`)
- **Everything sold or made carries a brand.** The exceptions are handmade
  goods, generics so common they are everywhere, and a deliberate anti-brand.
  (`specs/BUILDING_PLAYBOOK.md`)
- **Sky cells are part of the world.** They are deliberate negative space
  (fall lanes now, flight later), and every one is keyed "In the Air"
  (`SkyRoom` in `typeclasses/rooms.py`). A cell that no exit points at is not
  clutter; do not propose removing it. (`specs/BUILDING_PLAYBOOK.md`)
- **AI NPCs act only through real commands.** Whatever the language model
  makes an NPC do goes out through `execute_cmd`, as the command a player
  would type, and a refusal from that command stands: no fallback gives the
  NPC what the command refused. The scripted side of an NPC (the planner in
  `world/souls/`, the director) also moves some objects directly in Python,
  such as a courier's parcel; this law does not make that a defect, and
  whether it should change has not been ruled.
  (`specs/proposals/LLM_GAMEMASTER_SPEC.md`, Principle 2)
- **The game does not depend on one model or one backend.** It talks to
  configurable endpoints (`settings.LLM_GM_URL`, `settings.CIVIC_LLM_URL`) in
  the chat-completions shape, so the model and what serves it can be swapped.
  Do not propose pinning a model, moving a serving stack into the repo, or
  prompt tricks only one model understands. One caveat: a request carries a
  `json_schema` field that only some backends enforce, so on the others the
  shape of a reply is not guaranteed.
  (`specs/proposals/LLM_GAMEMASTER_SPEC.md`)

## File → Concept Map

| I need to... | Look in... |
|--------------|------------|
| Modify combat flow/turns | `world/combat/handler.py` |
| Change melee range rules | `world/combat/proximity.py` |
| Fix grappling mechanics | `world/combat/grappling.py` |
| Add/change combat constants | `world/combat/constants.py` |
| Modify attack/damage logic | `world/combat/attack.py` |
| Modify throw flight/landing/deflection | `world/combat/throwing.py` |
| Change combat messages | `world/combat/messages/*.py` |
| Modify attack command | `commands/combat/core_actions.py` |
| Add movement commands | `commands/combat/movement.py` |
| Add special actions | `commands/combat/special_actions.py` |
| Change character stats/behavior | `typeclasses/characters.py` |
| Modify items/weapons | `typeclasses/items.py` |
| Work on death/corpses | `typeclasses/corpse.py`, `typeclasses/death_progression.py`, `typeclasses/curtain_of_death.py` |
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
| Change what an AI NPC says or does | `typeclasses/llm_npc.py`, `world/llm/` |
| Make a slow call (a model, a remote service) | `world/llm/detached.py` |
| Change NPC needs, schedules, jobs, posts | `world/souls/` |
| Change how NPCs are dispatched to world events | `world/director/` |
| Change what a job does at its post | `world/service.py` |
| Modify radio | `world/radio.py`, `commands/CmdRadio.py` |
| Modify voice identity and speech | `world/voice.py`, `world/speech.py` |
| Change what a looker can see or hear | `world/perception.py` |
| Modify hide/sneak/search | `world/stealth.py`, `commands/CmdStealth.py` |
| Modify falling | `world/gravity.py` |
| Work on medical/anatomy | `world/medical/`, `world/anatomy/` |
| Modify world signals (WSIS) | `world/wsis.py` |
| Understand a system before implementing | `specs/*.md` |

## When Stuck

1. **`server/logs/server.log`** — tracebacks and errors.
2. **`server/logs/combat_audit.log`** — every combat/medical diagnostic, always on
   (written via `world/combat/debug.py`).  For live in-game output, set
   `SPLATTERCAST_LIVE = True` in settings to mirror it to the Splattercast channel.
3. **`server/logs/souls_audit.log`** — what each NPC soul set out to do,
   failed at, finished and earned (written by `world/souls/audit.py`). To see
   a model's raw reply beside the text players read, set
   `LLM_GM_DECISION_LOG = True` and read `server/logs/llm_decisions.log`
   (`world/llm/decision_log.py`).
4. **Grep for the constant** — most strings live in a `constants.py`.
5. **Trace from the command** — `commands/` calls into handler/system methods.
6. **Check NDB state** — many bugs are stale `char.ndb.*` references.
7. **Read the spec** — `specs/*.md` documents each system; Evennia docs at
   https://www.evennia.com/docs/latest/.

## Quick Reference

- Need new in-game mechanics? Subclass a base typeclass.
- Need data variation? Prototype, not a new typeclass.
- Need a persistent flag? Tag (attribute for complex data).
- Need a persistent object? `evennia.utils.create.*` or `evennia.prototypes.spawner.spawn`.
- Need persistent attributes? `obj.db.attr` (check `is None`, never `hasattr`;
  the same goes for `obj.ndb`).
- Need search? `caller.search` in a command, else `evennia.utils.search.*`.
- Need an interactive menu? `evmenu`. Need custom layout? `evform`.
- Naming a character in a room broadcast? `msg_room_identity`, not `msg_contents`.
- Giving an item a description? Set `db.desc`; do not override `return_appearance` to supply it.
- Running tests? `docker exec <CONTAINER> evennia test --settings settings.py world`.
- Deploying? issue → branch → PR → squash-merge → hard-reset live → with the
  owner's go, `@reload` from inside the game (code only) → check `evennia status`.
- Changing how the game behaves or what a player reads? Propose it and wait
  for the owner's go; a real choice needs a ruling first (`WORKFLOW.md`,
  Rulings).
- Proving a change works, or testing in the running game? `DEVELOPMENT_GUIDE.md`,
  Testing Guidelines.
