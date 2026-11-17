# Combat Message Format Specification

> **Status:** ✅ **SHIPPED** — verified against code 2026-08-02.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - "Required Phases: initiate, hit, miss, kill" — *corrected 2026-11: this claim holds. Every weapon bank authors `initiate`, `hit`, `miss` and `kill`; `grapple.py` is the one exception, with its own phase set (§Special Extended Phases). An earlier version of this bullet said 33 banks had no `initiate`; that count was wrong.*
> - The colour scheme documented here is not what ships: `_apply_color` (`__init__.py:182-207`) colours hit/initiate/kill and miss only, and miss uses `|W` not `|w`. *Re-measured 2026-09-18 (#3427, line refs refreshed after #3615): `initiate` sits in `successful_hit_phases` (`:170-176`) and renders `|R` exactly like `hit`, so "initiate gets none" was wrong even in 2026-08; and the phase lists are no longer the whole story — `weapon_type == "grapple"` takes an override branch ahead of them (`:186-198`, see §Special Extended Phases), and an empty message string is now returned uncoloured (`:184-185`) instead of being wrapped into a bare `|R|n`.*
> - The third-person contract has moved on. `observer_msg` with `{attacker_name}`/`{target_name}` is now a **legacy fallback**; the shipped path is the identity-aware `observer_template` + `observer_char_refs` (`__init__.py:222-243`; re-measured 2026-09-18 after #3615 the block sits at `__init__.py:238-272`). *This bullet is accurate: `observer_template` is built at `:238-266`, `observer_char_refs` at `:268-272`, and the live consumers pass `observer_msg` only as a fallback — `world/combat/attack.py` uses `observer_template` exclusively (`:618`, `:653`, `:698-717`), as does `resolve_auto_escape` (`world/combat/actions.py:623`, `:676`).*
> - `{damage}` is listed as a standard placeholder; 2 of 104 banks use it.

**Version 1.0 - Message Refactoring Guidelines**

## Overview

This specification defines the standardized format for combat messages across all weapon types in the gelatinous combat system. The goal is to refactor existing messages from the old single-string format to the new multi-perspective dictionary format while preserving the rich, atmospheric content and distinctive tone.

## Current State Analysis

### Format Status by File Type:
- ✅ **Already Converted**: `anti-material_rifle.py`, `unarmed.py`, `grapple.py`
- ✅ **Refactoring Complete**: ~80 weapon message files converted to new format
  - *Re-measured 2026-09-12, counts updated 2026-11:* `world/combat/messages/` now holds **104 weapon banks** (plus `__init__.py`), every one in the three-perspective dict format — no bank lacks `attacker_msg`. Median variants per core phase: 30 (min 4, max 45). One of the 104 is `unarmed_rat.py`, a species bank (§Unarmed.py). There is also a second message family this spec never mentions: **`world/combat/messages/severance/`** — 12 location banks (head, arms, hands, thighs, shins, feet, tail, forelegs, forepaws, hindlegs, hindpaws, cybernetic) plus its own loader `get_severance_message` (`severance/__init__.py`), keyed by location / injury_type / severity rather than weapon / phase, returning the same render shape (#332).
- ✅ **Special Cases Handled**: `grapple.py` (extended phases), `unarmed.py` (base template)

### Existing Content Quality:
- **Rich, atmospheric messages** with visceral descriptions
- **Cinematic tone** influenced by:
  - Film noir and gritty crime fiction
  - Horror/thriller aesthetics  
  - Hardboiled detective fiction
  - Industrial/urban decay atmosphere
  - Psychological tension and dread
- **Technical weapon details** integrated naturally
- **Multiple message variants** per phase (10-20+ per category)
- **Consistent voice** across different weapon types

## Target Format Specification

### Standard Structure:
```python
MESSAGES = {
    "phase_name": [
        {
            "attacker_msg": "You [action] with {item_name}...",
            "victim_msg": "{attacker_name} [action] at you with {item_name}...", 
            "observer_msg": "{attacker_name} [action] with {item_name}..."
        },
        # ... additional message variants (10-20+ recommended)
    ],
    # ... additional phases
}
```

### Required Phases:
1. **`initiate`** - Combat preparation/weapon readying messages
2. **`hit`** - Successful attack messages  
3. **`miss`** - Failed attack messages
4. **`kill`** - Fatal blow messages. Every bank authors it; a bank without it would get the loader's generic one-line fallback, not its own `hit` prose
   - *Corrected 2026-09-12 — it does not fall back to `hit`.* A bank with no `kill` phase falls through to the loader's **generic** `fallback_template_set` (in `get_combat_message`, `world/combat/messages/__init__.py`), which renders `"You kill {target_name} with {item_name}."` from the phase name — not to that weapon's richer `hit` prose. `_handle_kill` (`world/combat/attack.py`) asks only for `"kill"` and has no second lookup. In practice this never fires, because all 103 non-grapple banks author a `kill` phase; but an author who omits one on the strength of this line gets the flat generic sentence, not graceful degradation. (This is the "is the phase genuinely optional?" half of **#1513**: optional, yes — but the fallback is not what the parenthesis promises.)

### Bank pairs (MULTI_WEAPON_COMBAT_SPEC §7, shipped 2026-10-05)

A weapon type with a pair row in `AKIMBO_PROFILES_BY_TYPE` (`world/combat/constants.py`) has TWO banks: the base bank is one weapon in one hand, `<type>_akimbo` is the pair. The loader needs no change: the one door's `choice.weapon_type` names the bank, and the row's `weapon_type` swaps it. A pair bank may say `{item_name}` for the lead item's own name (owner ruling, MULTI_WEAPON_COMBAT_SPEC §14 #14: banks per weapon type, the item name inserted). Slice 4 (2026-10-06, #3718) added `tiger_claws.py` / `tiger_claws_akimbo.py` (the held Voxhaul Tiger claw, fresh glove prose) and `light_pistol_akimbo.py` (any two light pistols). The first pair: `nailz.py` (one hand of Nailz; the hand-neutral lines, 24/30/30/28 per phase) and `nailz_akimbo.py` (both hands; the full original bank, with the implant's lines no longer dressed in gloves or a belt); they were `tiger_claws` / `tiger_claws_akimbo` until slice 2, when the owner ruled Nailz gets its own pair and the held Tiger Claws theirs. The prototype's `weapon_type` names `nailz`; the `nailz` row of `AKIMBO_PROFILES_BY_TYPE` names `nailz_akimbo` (slice 4). No `{hand}` in combat banks for v1. `world/tests/test_both_claw_banks_resolve.py` pins that both banks resolve all four phases.

### Special Extended Phases (for specific weapons):
- **`escape_hit`** / **`escape_miss`** - Grappling escape attempts
- **`release`** - Voluntary release of grapples
- **`grapple_damage_hit`** / **`grapple_damage_miss`** / **`grapple_damage_kill`** - Damage while grappling
- **`release_charge`** / **`release_charge_away`** / **`release_jump`** / **`release_blast`** - A hold that ends for a reason other than the holder choosing it (#3615): letting go to charge a third party, letting go to charge out of the room, letting go for a gap jump, and a blast tearing the pair apart
- **`release_edge`** - A dragged victim cannot be taken over an edge, so the hold opens and the jumper goes on alone (#3668)
- **`release_intent`** - The actor-only *preview* printed when a charge is queued while holding someone (#3615). Nothing has happened to the hold yet, so the variant's `victim_msg` and `observer_msg` are authored as empty strings

> **Reachability re-measured 2026-09-18 (#3615), counts updated 2026-11 for #3668 — `grapple.py` is now 14 phases / 89 authored variants, and 52 of them reach players.** This supersedes the same-day #3427 measurement ("39 of 76"), which itself superseded 2026-09-12's "72 of 76 unreachable". #3427 wired the three resolver beats to the bank as it stood; #3615 **authored five new phases (11 variants)** for the ways a hold ends without its holder choosing to end it, and wired the four remaining doors onto them — the owner's call: *"adding the missing messages to our list that can be expanded/subtracted like all our combat messages and then wiring it in - makes the most sense."* What is still unreached is one unbuilt mechanic, not a plumbing gap. `get_combat_message` is asked for `grapple` phases at **eleven** production call sites — three resolver beats, two auto-escape beats, and six release beats across five doors (the charge door branches same-room / cross-room; #3668 added the edge door) — and all eleven run.
>
> | phase | variants | reaches players | requested by |
> |---|---|---|---|
> | `hit` | 30 | ✅ 2026-09-18 (#3427) | `speak_grapple_beat(char, target, "hit")` on a won roll in `resolve_grapple_initiate` (`world/combat/grappling.py`) |
> | `miss` | 3 | ✅ 2026-09-18 (#3427) | `speak_grapple_beat(char, target, "miss")` on a lost roll, same resolver |
> | `release` | 2 | ✅ 2026-09-18 (#3427) | `speak_grapple_beat(char, grappling_target, "release")` in `resolve_release_grapple` |
> | `escape_hit` | 2 | ✅ unchanged | `resolve_auto_escape` (`world/combat/actions.py:316`), which the round loop runs for anyone grappled (`world/combat/handler.py`) |
> | `escape_miss` | 2 | ✅ unchanged | `resolve_auto_escape` (`world/combat/actions.py:369`) |
> | `release_charge` | 3 | ✅ new 2026-09-18 (#3615) | same-room branch of `_release_grapple_for_charge` — `speak_grapple_beat(char, grappled_victim, "release_charge", charge_target=target)` (`world/combat/movement_resolution.py`). Spends the third-party placeholder `{charge_target}` |
> | `release_charge_away` | 2 | ✅ new 2026-09-18 (#3615) | the cross-room branch of the same helper. Names no third party: the charge target is in another room, so the line says "charges away" instead |
> | `release_jump` | 3 | ✅ new 2026-09-18 (#3615); moved after the move 2026-09-29 (#3684) | gap jump in `CmdJump` (`let_go_for_the_leap`, `commands/combat/jump.py`): spoken with `break_grapple` only once the jumper's move has happened (or on a slip in place), its room line sent to the roof they left; a refused move keeps the hold and speaks nothing |
> | `release_edge` | 2 | ✅ (#3668) | `hold_opens_at_the_edge` in `CmdJump` (`commands/combat/jump.py`), when a dragged victim's move off the edge is refused. After an edge jump the jumper has already gone over, so the room line is sent with `room=` to the roof the victim still stands on; on an edge descent both still stand on the roof |
> | `release_blast` | 2 | ✅ new 2026-09-18 (#3615) | the blast on a human-shield sacrifice jump (`CmdJump`, `commands/combat/jump.py`). The only one of the #3615 five where the *actor* did not choose it, and the prose says so ("The blast tears {target_name} out of your arms!") |
> | `release_intent` | 1 | ✅ new 2026-09-18 (#3615) — **actor only** | queue-time charge preview in `CmdCharge` (`commands/combat/movement.py`), called with `audiences=("actor",)` and `charge_target=target_search` |
> | `grapple_damage_hit` | 30 | ❌ | nothing |
> | `grapple_damage_miss` | 5 | ❌ | nothing |
> | `grapple_damage_kill` | 2 | ❌ | nothing |
>
> **Live: 52. Unreached: 37 — all of them `grapple_damage_*`.** No code path deals damage *for* a grapple, so there is no beat for those three banks to narrate. They are pending content behind an unbuilt mechanic, not a wiring gap: the owner question "was a grapple-damage exchange ever meant to ship?" is open on **#3285** (`specs/GRAPPLE_SYSTEM_SPEC.md` §Grapple Damage System carries the verified not-built note). Nothing should be hooked up to them until that is answered.
>
> **Delivery — one public helper.** `speak_grapple_beat(actor, target, phase, *, audiences=("actor", "victim", "room"), room=None, **extra_chars)` (`world/combat/grappling.py`) is the door onto the bank for every grapple beat except the two auto-escape beats, which `resolve_auto_escape` (`world/combat/actions.py`) still fetches with `get_combat_message` and sends itself. It was `_say_from_bank` until #3615 made it public: three modules outside its own now call it (`world/combat/movement_resolution.py`, `commands/combat/jump.py`, `commands/combat/movement.py`), so the leading underscore had stopped describing its reach. It delivers exactly as the weapon banks do: `attacker_msg` to the actor, `victim_msg` to the target, and `observer_template` + `observer_char_refs` through `msg_room_identity` with the pair excluded — so every bystander sees the pair rendered through their own recognition state instead of a pre-baked name. Four details of its signature:
>
> - **`audiences`** narrows delivery to a subset of `("actor", "victim", "room")`; the default is all three. Only `release_intent` uses it (`audiences=("actor",)`), because a *queued* charge has not ended the hold yet and telling the victim or the room would describe a world state that does not exist. Belt and braces: that phase's single variant also authors empty strings for the other two audiences, so the narrowing and the bank say the same thing and either alone would suffice.
> - **`**extra_chars`** is forwarded verbatim as the accessor's `extra_chars` argument — a third party the line names, rendered per audience; see §Standard Placeholders for the contract. `release_charge` and `release_intent` are the only phases that spend one, both as `charge_target`.
> - **`hit_location`** is passed **for the `hit` phase only** — `select_hit_location(target, attacker=actor)` (`world/medical/utils.py:120`), the same anatomy-weighted, armour-aware draw an attack makes, the attacker reading the target's weak points — because `hit` is the one reachable grapple phase that spends the placeholder. Every other phase, the newer release phases included, is asked for without it and none of their variants uses it, as with the escape call sites in `world/combat/actions.py`. There is no `or "arm"` fallback and no placeholder default dict: both were dead and were deleted on 2026-09-18 (#3427), so an unpassed `hit_location` would surface as the loader's `(Error: Missing placeholder …)` rather than a silent limb — which is the contract the other banks live under (`specs/archive/WEAPON_MESSAGE_CONVERSION_SPEC.md`, #1583).
> - **`room`** names the room that hears the beat when the actor has already left it (a gap jump, or a hold that opens at an edge the jumper has gone over, #3668). By default it is the actor's own room.
>
> **Where the room broadcast lands.** `speak_grapple_beat` sends the room line to `room` when the caller passes one, and otherwise to `actor.location`, read at send time. Every door that passes no `room` speaks before its mover moves, or moves nobody. The cross-room charge releases the hold before `char.move_to(target_room)` (`_resolve_charge_cross_room`, `world/combat/movement_resolution.py`), so `release_charge_away` is heard in the room the pair was grappling in (#3615). The jump doors that speak after the jumper has moved pass `room=` the roof the jumper left: `let_go_for_the_leap` (`release_jump`) and `hold_opens_at_the_edge` (`release_edge`), both in `commands/combat/jump.py`. The victim's own line is sent directly, wherever the victim is.
>
> Two second-order, player-visible consequences of routing through the loader:
> - **Colour stayed the grapple's own** (re-measured 2026-09-18, after review; extended by #3615). The deleted hardcoded lines were green on success (`|g`) and yellow on failure (`|y`), and the loader preserves that rather than repainting the hold in the attack palette: `_apply_color` takes a `weapon_type == "grapple"` branch *ahead* of the phase lists (in `get_combat_message`, `world/combat/messages/__init__.py`) — `hit`, `release` and `escape_hit` → `|g`; `miss`, `escape_miss`, **all five #3615 phases** (`release_charge`, `release_charge_away`, `release_jump`, `release_blast`, `release_intent`) and `release_edge` (#3668) → `|y`; anything else in the bank uncoloured. The split is not success-vs-failure but *hold kept or let go on purpose* (green) against *a grip lost, or about to be* (yellow), which is what the five new phases narrate — including the preview, where the grip is not lost yet. A hold is not a wound, and the consensual uncontested hold that still writes its own lines beside this one wears the same green. *(An intermediate version of #3427 let these phases fall through to the attack palette — `hit` → `|R`, `miss` → `|W`, `release` bare. That is not what ships; ignore any note describing it.)* Two side effects worth knowing: `escape_hit` / `escape_miss` are **coloured for the first time** — they had shipped bare since #3391, because their phase names were in neither colour list — and an **empty** message string is returned untouched instead of becoming a bare `"|R|n"`, which is what keeps `release_intent`'s empty victim and observer lines from arriving as two stray colour codes.
> - **`{hit_location}` is always the TARGET's location, in every audience's line** — and as of 2026-09-18 every `hit` variant spends it that way. Three variants misused it and all three were corrected in #3427: one used it for a face on the attacker and observer lines (now the literal word `face`, `world/combat/messages/grapple.py:125`, `:127`, matching the victim line that already said "their face"); and two spent a target-side draw on the *attacker's own* limbs, `"locking your {hit_location}s around {target_name}'s {hit_location}"` (`grapple.py:10`) and `"Like a vise, your/{attacker_name}'s {hit_location}s clamp around …"` (`:70-72`), which rendered as "your left arms" — both now say `arms` outright (`grapple.py:10-12`, `:70-72`), keeping the target-side `{hit_location}` only where it describes the target. **No `hit` variant pluralises the placeholder any more**; the survivors all read `{target_name}'s {hit_location}` or `your {hit_location}`. The 30 unreached `grapple_damage_hit` variants narrate an unbuilt mechanic (#3285); their two attacker-part lines (`:226` "your forearm", `:311` "your shoulder") were fixed with the bank-wide sweep (#3710). **Swept bank-wide 2026-10-08 (#3710):** the 2025-09-27 conversion (nine commits, `ea6c0afa` to `36722fc5`) had tokenized a body-word list wherever it appeared. On master, by the pin's own regexes: 271 attacker lines said "your {hit_location}" for the attacker's own part (275 tokens); 29 victim or observer lines said "{attacker_name}'s {hit_location}"; 130 tokens were glued inside words or to a hyphen (`{hit_location}or` = armor, `cap` = kneecap, `line` = jawline, `s` = hands, knees, legs; the three hyphens, `{hit_location}-first`, were an authored style that reads wrong for most locations); those three shapes cover 434 distinct tokens. A further 577 tokens sat in seats judged, line by line against the pre-conversion ancestor, not to be the rolled part: the adverb "back" ("they stagger back"), the weapon's own part ("the head of the axe", "the neck of the bottle"), a sub-part ("the side of your head", "the back of the hand"), a posture ("drops to one knee", "folds at the waist"), a blow's name ("a side swing", "a gut punch"), list items ("the hand, wrist, and forearm"), and a small number of article-less struck parts the sentence itself fixes ("lands low, carving into shin", "marked from shoulder to hip", "slips between ribs"). All 1011 say the author's word now (10151 tokens on master, 9140 on the branch; no line gained one). Where the author named the struck part as a bare noun that the roll should still decide ("Steel collides with the {hit_location}", "bruising the {hit_location}"), the token stays, with an article where the grammar wants one. `world/tests/test_every_bank_spends_the_token_on_the_target.py` pins the attacker-self, attacker-part, glued and adverb-seat shapes at zero over every bank and names the 8 entries (down from 252) whose attacker line carries a token while the victim line carries none. A token behind a possessive or article whose anatomy the sentence fixes by other words ("catches them under the chin; their {hit_location} snaps back") is the conversion's remaining limit, not reachable by rule.
>
> **What deliberately keeps bespoke prose**, because no bank phase carries its meaning: the consensual uncontested hold (the consent branch of `resolve_grapple_initiate`, `grappling.py` — the `hit` bank is all violent shoot-ins and vises, and a trusted `grab` involves no contest and no roll); `resolve_grapple_join` and `resolve_grapple_takeover`, whose beats are three-party and name a *current grappler* or a *third victim* that a two-party bank line has no slot for. `establish_grapple` (`grappling.py`) also still returns a hardcoded string — it is imported at `world/combat/handler.py:49` and called by nothing in production; only tests exercise it, to pin its one-grappler-one-victim guard.

### Standard Placeholders:
- **`{attacker_name}`** - Attacker's display name (for victim/observer messages)
- **`{target_name}`** - Target's display name (for attacker/observer messages)  
- **`{item_name}`** - Weapon/item name
- **`{damage}`** - Damage dealt (for hit/kill messages). Supported by the loader; whether banks should use it is open (#1513)

> **Measured 2026-09-12 — this list is both incomplete and optimistic.** The loader (`get_combat_message`, `world/combat/messages/__init__.py`) also supplies `{hit_location}`, `{blood}` / `{Blood}` (species-keyed *target* fluid — human crimson, synth cobalt, robot amber; #1206/#1207), the bare aliases `{attacker}` / `{target}` / `{item}`, and `{phase}`. Actual usage across the 104 banks (re-counted 2026-11): `{attacker_name}` 104, `{target_name}` 104, `{hit_location}` 104, `{blood}` 68, `{Blood}` 16, `{item_name}` **4** (`bowel_disruptor.py`, `tiger_claws.py`, `tiger_claws_akimbo.py`, `light_pistol_akimbo.py`), `{damage}` **2** (`anti-material_rifle.py`, `heavy_pistol.py`), `{item}` 1 (`melee.py`), `{charge_target}` 1 (`grapple.py`), `{phase}` 0. `{damage}` is supported by the loader but is not the shipped authoring style. `{item_name}` is the style a pair bank may use (§Bank pairs); the other banks bake their weapon's name into the prose. Whether that is intended house style or a gap is an open owner call (#1513). *(Re-measured 2026-09-18 after #3615 the shared-kwargs block sits at `:124-167`.)*

#### Third parties — `extra_chars` (added 2026-09-18, #3615)

> A line sometimes has to name **someone who is neither the attacker nor the target** — the person a grappler lets go of their victim to charge at. `get_combat_message` takes a keyword `extra_chars={placeholder_name: object}` alongside `attacker` / `target` / `item` (`world/combat/messages/__init__.py:8`). Each entry adds one placeholder to the bank's vocabulary, and the point of the mechanism is that it is **rendered per audience, exactly as the two principals already are**, rather than resolved once and baked in:
>
> | audience | how the object renders | built at |
> |---|---|---|
> | `attacker_msg` | `get_display_name_safe(obj, attacker)` — the third party as the **actor** knows them | `attacker_format` in `get_combat_message` |
> | `victim_msg` | `get_display_name_safe(obj, target)` — as the **victim** knows them | `victim_format` |
> | legacy `observer_msg` | `obj.key`, pre-resolved — matching what that legacy field already does for the pair | `observer_legacy_format` |
> | identity-aware `observer_template` | **left as the literal `{placeholder}`**, and the object is carried in `observer_char_refs` | the observer-template block at the end of `get_combat_message` |
>
> The last row is the one that carries the design. The observer template is formatted with `format_map(_PassThrough(shared_kwargs))`, and `extra_chars` is deliberately **not** folded into `shared_kwargs` — so an entry the map does not know survives formatting as the literal `{charge_target}` instead of being resolved early or raising `KeyError`. `observer_char_refs` then carries the object under that same key, and `msg_room_identity` (`world/identity_utils.py`) substitutes it once per observer through *that observer's* recognition state. A bystander who knows the charge target by name reads the name; one who does not reads their sdesc — in the same sentence where the grappler and the victim are already resolved that way. Placeholders `msg_room_identity` has no ref for pass through untouched, as they always have, so this costs nothing to the other banks.
>
> `extra_chars` defaults to `None` and is normalised to `{}` in the loader, so a caller that passes nothing gets exactly the behaviour it got before. The only shipped users are the grapple bank's `release_charge` and `release_intent` phases, whose `{charge_target}` is supplied by `speak_grapple_beat(..., charge_target=target)` (§Special Extended Phases). A placeholder named in a template but absent from `extra_chars` fails the way every other missing placeholder does — `(Error: Missing placeholder …)` in the rendered line, not a silent blank.
>
> `get_combat_message` also takes `audiences` (default all three of `actor`, `victim`, `room`). It renders only the audiences listed and returns `""` for the others, with empty `observer_char_refs` when `room` is left out. This is because naming someone through the identity system rolls, and stores, a disguise check for that reader, and a line nobody receives must not spend that roll. `speak_grapple_beat` passes `audiences` on every call.
>
> **One reading to know about.** The room broadcast excludes only the attacker and the target, so the third party themself is an ordinary observer and `get_display_name(self)` returns their own key (`get_display_name` in `typeclasses/characters.py`) — the person being charged reads *"Jorge lets go of Skullface and goes for [their own name]"*, not *"…goes for you"*. `msg_room_identity` has no second-person substitution and never has; any door that wants one has to send that person their own line, the way the attacker and victim get theirs.

### Message Perspective Guidelines:

#### Attacker Messages (First Person):
- Use "You" perspective
- Focus on the character's actions, sensations, intent
- Include tactical/technical weapon details
- Emphasize control and deliberation

**Example**: 
```
"You meticulously line up the shot with your anti-material rifle, knowing a single round can vaporize {target_name}."
```

#### Victim Messages (Second Person):
- Use "you" for the victim, "{attacker_name}" for the aggressor
- Emphasize the threat/danger directed at the victim
- Include victim-specific sensory details
- Build tension and immediacy

**Example**:
```
"{attacker_name} meticulously lines up the shot with their anti-material rifle, knowing a single round can vaporize you."
```

#### Observer Messages (Third Person):
- Use "{attacker_name}" and "{target_name}"
- Focus on external, visible actions
- Maintain atmospheric tension
- Avoid victim-specific internal details

**Example**:
```
"{attacker_name} meticulously lines up the shot with the anti-material rifle, knowing a single round can vaporize {target_name}."
```

#### Name Capitalisation (all banks)

> **Recorded 2026-09-18 (#3427) — this is bank-wide, not a grapple detail.** Templates are handed **bare** names and the *rendered sentence* is capitalised once, so the sentence decides the capital instead of the placeholder. `get_combat_message` builds `target_sees_attacker` with no capitalisation of its own (`get_combat_message`, `world/combat/messages/__init__.py`) and passes each formatted `attacker_msg` / `victim_msg` / `observer_msg` through `capitalize_first` before colouring. This is the rule the identity-aware observer path has followed since #3209; the three audiences now agree.
>
> **What this replaced.** The accessor used to force-capitalise `{attacker_name}` in *every* victim line and never capitalised a `{target_name}` that opened an attacker line. A multi-word sdesc therefore took a capital mid-sentence — "You stumble as **A** lanky man ties you up!" — while an attacker line that opened on the target began lowercase — "a lanky man finds themselves trapped in your unyielding grapple!". Both are fixed for every bank at once.
>
> **What it means for authors.** A name may sit anywhere in a line. An sdesc keeps its lowercase article mid-sentence ("as a lanky man ties you up") and takes the capital only when it opens the sentence ("A lanky man ties you up"). **Proper names are unaffected** — `capitalize_first` uppercases the first *visible* letter and one that is already a capital stays as it is; it also steps over colour markup, so a pre-coloured line is not silently promoted from `|r` to `|R` (`capitalize_first`, `world/grammar.py`, #2207).

## Tone and Style Guidelines

### Core Aesthetic Influences:
- **Film Noir**: Shadows, moral ambiguity, stark contrasts
- **Industrial Horror**: Mechanical brutality, urban decay
- **Hardboiled Fiction**: Terse, economical prose with punch
- **Psychological Thriller**: Building dread, intimate violence
- **Crime Drama**: Professional competence meets personal stakes

### Writing Style Requirements:

#### Language Characteristics:
- **Terse, punchy sentences** with strong rhythm
- **Visceral, tactile descriptions** that engage multiple senses
- **Technical authenticity** woven naturally into narrative
- **Atmospheric details** that build mood and tension
- **Varied sentence structure** to create rhythm and flow

#### Tone Elements:
- **Deliberate pacing** - Actions feel inevitable, not rushed
- **Professional competence** - Characters know their weapons/craft
- **Underlying menace** - Even preparation feels threatening
- **Sensory richness** - Sound, texture, weight, temperature
- **Emotional restraint** - Violence is matter-of-fact, not theatrical

#### Example Analysis from Existing Content:

**Chainsaw (old format)**:
```
"A guttural sound fills the room as the saw turns over. It doesn't want to start — it *needs* to."
```
- ✅ Mechanical personification
- ✅ Ominous inevitability  
- ✅ Sensory detail (sound)
- ✅ Psychological undertones

**Anti-material Rifle (new format)**:
```
"attacker_msg": "You meticulously line up the shot with your anti-material rifle, knowing a single round can vaporize {target_name}."
```
- ✅ Technical competence
- ✅ Calculated deliberation
- ✅ Understated lethality
- ✅ Professional focus

## Refactoring Process

### Step 1: Content Preservation
- **DO NOT TRUNCATE** existing message content
- **PRESERVE** the atmospheric quality and specific details
- **MAINTAIN** the established voice and tone
- **CONVERT** single strings to three-perspective format

### Step 2: Perspective Adaptation
For each existing message, create three versions:
1. **Attacker**: Convert to first-person "You" perspective
2. **Victim**: Add victim-specific threat awareness
3. **Observer**: Maintain third-person observational view

### Step 3: Placeholder Updates
- Replace `{attacker}` with `{attacker_name}` (victim/observer only)
- Replace `{target}` with `{target_name}` (attacker/observer only)
- `{item_name}` and `{damage}` are supported by the loader; whether banks should use them is open (#1513)

### Step 4: Content Enhancement
- **Expand message variety** if needed (target: 10-20 per phase)
- **Add technical details** specific to weapon type
- **Enhance sensory descriptions** while maintaining tone
- **Ensure phase coverage** (initiate, hit, miss, kill minimum)

## Quality Assurance Checklist

### Content Quality:
- [ ] All existing atmospheric content preserved
- [ ] Three-perspective format implemented correctly
- [ ] Tone consistency maintained across perspectives
- [ ] Technical weapon details included naturally
- [ ] Sensory descriptions rich and varied

### Technical Requirements:
- [ ] Standard placeholders used correctly
- [ ] Required phases present (initiate, hit, miss, kill)
- [ ] Dictionary structure matches specification
- [ ] No truncated or lost content from original
- [ ] Message variety adequate (10+ per phase preferred)

### Tone Verification:
- [ ] Professional competence conveyed
- [ ] Atmospheric tension maintained
- [ ] Industrial/noir aesthetic preserved
- [ ] Violence portrayed as matter-of-fact, not glorified
- [ ] Pacing feels deliberate and inevitable

## Special Cases

### Grapple.py:
- Already converted ✅
- Extended phases: `escape_hit`, `escape_miss`, `release`, `release_charge`, `release_charge_away`, `release_jump`, `release_blast`, `release_edge`, `release_intent`, `grapple_damage_*` — 14 phases / 89 variants in all as of #3668
- Use as template for other close-combat weapons

### Unarmed.py:
- Already converted ✅
- Standard four-phase structure
- Good baseline template for conversion
- A non-human attacker's unarmed lines come from `unarmed_<species>.py` if that file exists (today only `unarmed_rat.py`), and from `unarmed.py` if it does not. No other weapon type has species banks (#356)

### Weapon-Specific Considerations:
- **Firearms**: Emphasize technical preparation, recoil, ballistics
- **Bladed Weapons**: Focus on edge quality, precision, intimate violence
- **Improvised Weapons**: Highlight adaptation, desperation, creativity
- **Power Tools**: Mechanical personality, industrial brutality
- **Explosives**: Countdown tension, area effect awareness

## Implementation Priority

### Phase 1: High-Priority Weapons (in use by prototypes)
- [ ] `knife.py` - DAGGER prototype
- [ ] `long_sword.py` - SWORD prototype  
- [ ] `baseball_bat.py` - BASEBALL_BAT prototype
- [ ] `staff.py` - STAFF prototype
- [ ] `throwing_knife.py` - THROWING_KNIFE prototype
- [ ] `throwing_axe.py` - THROWING_AXE prototype
- [ ] `shuriken.py` - SHURIKEN prototype

### Phase 2: Common Weapons
- [ ] `crowbar.py`, `hammer.py`, `machete.py`, `katana.py`
- [ ] `battle_axe.py`, `chainsaw.py`, `pipe_wrench.py`
- [ ] `brick.py`, `broken_bottle.py`, `tire_iron.py`

### Phase 3: Specialized/Exotic Weapons
- [ ] Firearms, exotic melee, improvised weapons
- [ ] Less common but atmospheric weapons

## Notes for Implementation

### Conversion Workflow:
1. **Backup original** file content
2. **Analyze existing messages** for tone and content
3. **Create three-perspective versions** of each message
4. **Test format** with message system
5. **Verify tone consistency** across perspectives
6. **Expand content** if message count is low

### Common Pitfalls to Avoid:
- ❌ Truncating rich atmospheric content
- ❌ Making victim messages identical to observer messages
- ❌ Losing technical weapon-specific details
- ❌ Breaking the established noir/industrial tone
- ❌ Rushing the conversion without preserving quality

### Success Criteria:
- ✅ All original atmospheric content preserved and enhanced
- ✅ Three distinct but consistent perspectives per message
- ✅ Technical integration with combat system
- ✅ Tone consistency maintained across all weapon types
- ✅ Enhanced player immersion through perspective-specific details

---

**Remember**: These messages are a core part of the game's atmospheric identity. The refactoring should enhance and preserve this identity, not diminish it through technical convenience.

## Recent Quality of Life Improvements (Sept 2024)

### Automatic Color Application System
The combat message system now automatically applies contextual colors based on message phase:

#### Color Scheme:
- **Kill Messages**: `|r{message}|n` (normal red)
- **Hit Messages**: `|R{message}|n` (bright red)
- **Initiate Messages**: `|R{message}|n` (bright red)
- **Miss Messages**: `|W{message}|n` (bright white)
- **Other Messages**: No automatic coloring. An empty string, and a line that is already coloured, are returned unchanged

*Corrected 2026-09-12 and 2026-11: this table once called `|r` bold and `|R` regular, and gave misses as `|w`. In Evennia lowercase is normal and uppercase is bright; the codes above are the ones `_apply_color` (`world/combat/messages/__init__.py`) uses.*

> **Amended 2026-09-18 (#3427, extended by #3615) — the table above describes the *attack* palette, which is no longer the only one.** `_apply_color` (`world/combat/messages/__init__.py`) checks two things before the phase lists: an **empty** message is returned as-is, where it previously became the bare colour pair `"|R|n"`; and `weapon_type == "grapple"` takes its own branch — `hit` / `release` / `escape_hit` → `|g`, `miss` / `escape_miss` / `release_charge` / `release_charge_away` / `release_jump` / `release_blast` / `release_edge` / `release_intent` → `|y`, everything else uncoloured. A grapple is a hold, not a wound, so it keeps the green/yellow its hardcoded lines wore and its bespoke consensual-hold prose still wears. `escape_hit` / `escape_miss` are coloured by this for the first time (bare since #3391). The pre-coloured-template bypass (a message already wrapped `|…`…`|n`) applies in both branches.

#### Benefits:
- **Threat Escalation**: Visual progression from initiate → hit → kill
  - *Measured 2026-09-12 — there is no three-step progression.* `initiate` and `hit` are both in `successful_hit_phases` and both render `|R` (`successful_hit_phases` and `_apply_color` in `world/combat/messages/__init__.py`), so the first two steps are visually **identical**; `kill` renders `|r`, which is *less* bright than `|R`, not more. Whether the intended escalation is `|r` → `|R` → `|R` + something (bold, a prefix, a bright-magenta kill) is an open owner call; the code is internally consistent, the claimed escalation is not what a player sees.
- **Clarity**: Bright-white misses clearly indicate failed attempts
- **Consistency**: Automatic application ensures uniform presentation
- **Override Support**: Pre-colored templates bypass automatic coloring

### Enhanced Initiate Message System
Combat initiation now provides proper perspective-specific messages and defensive reactions:

#### Dual Initiate Messages:
- **Attacker Initiate**: Aggressive stance establishment ("You draw your knife...")
- **Victim Defensive**: Defensive reaction when not already engaged ("Nick raises his baton defensively...")

#### Conditions for Victim Defensive Messages:
- Target wasn't already in combat, OR
- Target was in combat but not targeting anyone
- And in either case the target is neither dead nor unconscious (a body can still be attacked, but it does not pose), and is not the attacker

#### Message Personalization:
- **Attackers** see first-person messages (`attacker_msg`)
- **Victims** see second-person messages (`victim_msg`)  
- **Observers** see third-person messages (`observer_msg`)

### Meta-Message Removal
Eliminated generic combat state announcements for cleaner narrative flow:
- **Removed**: "You enter combat!" message
- **Removed**: "You are no longer in combat." message  
- **Added**: TODO placeholder for narrative combat exit messages

#### Benefits:
- More immersive combat transitions
- Focus on weapon-specific narrative content
- Reduced message spam
- Natural flow from threat establishment to action

### Death Message Improvements
Enhanced death system messaging with medical cause integration:

#### Informed Death Messages:
- **Observers**: no line when the curtain starts. When it ends, a cause- and species-specific line from `get_death_cause_template` (`world/medical/medical_messages.py`), with the dying person named as each observer knows them; for blood loss: "{actor}'s lifeblood pools crimson around their still form."
- **Victim**: "Your body succumbs to blood loss. The end draws near..."
- **Fallback**: Beautiful mixed red death curtain message

#### Death Curtain Enhancements:
- **Color-corrected** random |r/|R block coloring
- **Proper text centering** accounting for color code length
- **Medical system integration** for cause-specific messaging
- **Race condition prevention** with bleeding message suppression

#### Kill Message Timing Fix (September 2024)
**Problem**: Death curtain animation was starting before kill messages could be displayed, causing narrative sequence issues where the death animation interrupted the climactic kill message.

**Root Cause**: Medical system's `take_damage()` method called `at_death()` immediately upon fatal damage determination, starting the death curtain before combat system could send contextual kill messages.

**Solution**: Implemented deferred death curtain system in `at_death()` method:
- **Combat Detection**: `at_death()` checks for active combat via `ndb.combat_handler`
- **Deferred Execution**: If in combat, sets `ndb.death_curtain_pending = True` and skips immediate curtain
- **Combat Integration**: `_handle_kill` (`world/combat/attack.py`) triggers the deferred curtain after sending the kill message
- **Safety Fallback**: 5-second delayed trigger ensures curtain appears even if combat fails to handle it

**Result**: Proper narrative sequence restored:
1. Fatal damage determined by medical system
2. Kill message sent by combat system ("Nick's bullet strikes you in the heart, killing you instantly")
3. Death curtain animation begins after kill message
4. Medical death analysis continues normally

**Benefits**:
- ✅ **Preserved Narrative Flow**: Kill messages appear before death animation
- ✅ **System Integration**: Medical and combat systems coordinate without coupling
- ✅ **Backward Compatibility**: Non-combat deaths (bleeding out) work unchanged
- ✅ **Robust Fallback**: Safety mechanism prevents stuck death states

---