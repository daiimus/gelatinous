# Combat Message Format Specification

## Overview

Combat prose lives in message banks under `world/combat/messages/`, one Python file per weapon type. Every bank holds a `MESSAGES` dict of phases, each phase a list of variants, and each variant written three times: once for the attacker, once for the victim, once for everyone else in the room. The loader `get_combat_message` (`world/combat/messages/__init__.py`) picks a variant, fills its placeholders per audience, capitalises and colours it, and returns it. These messages are a core part of the game's atmospheric identity; a bank should keep and deepen that identity, never thin it for technical convenience.

A second message family, `world/combat/messages/severance/`, holds 12 location banks (head, arms, hands, thighs, shins, feet, tail, forelegs, forepaws, hindlegs, hindpaws, cybernetic) with its own loader `get_severance_message` (`severance/__init__.py`). It is keyed by location / injury_type / severity rather than weapon / phase, and returns the same render shape (#332).

## Target Format Specification

### Standard Structure:

Every weapon bank is in this three-perspective dict format; no bank lacks `attacker_msg`.

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

**What the loader returns.** Besides `attacker_msg`, `victim_msg` and `observer_msg`, `get_combat_message` returns an identity-aware `observer_template` and `observer_char_refs`. The room line is delivered from those through `msg_room_identity`, so each bystander reads the attacker and target through their own recognition state. `observer_msg`, with `{attacker_name}` / `{target_name}` pre-resolved, is a legacy fallback only: `world/combat/attack.py` uses `observer_template` exclusively, as does `resolve_auto_escape` (`world/combat/actions.py`).

### Required Phases:
1. **`initiate`** - Combat preparation/weapon readying messages
2. **`hit`** - Successful attack messages
3. **`miss`** - Failed attack messages
4. **`kill`** - Fatal blow messages

Every weapon bank authors all four. `grapple.py` is the one exception, with its own phase set (§Special Extended Phases).

**A missing `kill` does not fall back to `hit`.** A bank with no `kill` phase falls through to the loader's generic `fallback_template_set` (in `get_combat_message`), which renders `"You kill {target_name} with {item_name}."` from the phase name, not that weapon's richer `hit` prose. `_handle_kill` (`world/combat/attack.py`) asks only for `"kill"` and has no second lookup. In practice this never fires, because every non-grapple bank authors a `kill` phase; but an author who omits one gets the flat generic sentence, not graceful degradation. The phase is optional in that sense, and the fallback is the generic line (#1513).

### Bank pairs (MULTI_WEAPON_COMBAT_SPEC §7)

A weapon type with a pair row in `AKIMBO_PROFILES_BY_TYPE` (`world/combat/constants.py`) has TWO banks: the base bank is one weapon in one hand, `<type>_akimbo` is the pair. The loader needs no change: the one door's `choice.weapon_type` names the bank, and the row's `weapon_type` swaps it. A pair bank may say `{item_name}` for the lead item's own name (owner ruling, MULTI_WEAPON_COMBAT_SPEC §14 #14: banks per weapon type, the item name inserted). No `{hand}` in combat banks for v1.

The pairs:

- `nailz.py` (one hand of Nailz; the hand-neutral lines, 24/30/30/28 per phase) and `nailz_akimbo.py` (both hands; the full original bank, with the implant's lines no longer dressed in gloves or a belt). The prototype's `weapon_type` names `nailz`; the `nailz` row of `AKIMBO_PROFILES_BY_TYPE` names `nailz_akimbo`. These two were `tiger_claws` / `tiger_claws_akimbo` until slice 2, when the owner ruled Nailz gets its own pair and the held Tiger Claws theirs.
- `tiger_claws.py` / `tiger_claws_akimbo.py`: the held Voxhaul Tiger claw, fresh glove prose (#3718).
- `light_pistol_akimbo.py`: any two light pistols (#3718).

`world/tests/test_both_claw_banks_resolve.py` pins that both Nailz banks (`nailz`, `nailz_akimbo`) resolve all four phases.

### Special Extended Phases (for specific weapons):

`grapple.py` has 14 phases and 89 authored variants. It has no `initiate` or `kill`.

- **`hit`** / **`miss`** - The grapple attempt won or lost
- **`escape_hit`** / **`escape_miss`** - Grappling escape attempts
- **`release`** - Voluntary release of grapples
- **`grapple_damage_hit`** / **`grapple_damage_miss`** / **`grapple_damage_kill`** - Damage while grappling
- **`release_charge`** / **`release_charge_away`** / **`release_jump`** / **`release_blast`** - A hold that ends for a reason other than the holder choosing it (#3615): letting go to charge a third party, letting go to charge out of the room, letting go for a gap jump, and a blast tearing the pair apart
- **`release_edge`** - A dragged victim cannot be taken over an edge, so the hold opens and the jumper goes on alone (#3668)
- **`release_intent`** - The actor-only *preview* printed when a charge is queued while holding someone (#3615). Nothing has happened to the hold yet, so the variant's `victim_msg` and `observer_msg` are authored as empty strings

The five #3615 phases (`release_charge`, `release_charge_away`, `release_jump`, `release_blast`, `release_intent`) exist because of the owner's call on #3615 (recorded 2026-09-18): *"adding the missing messages to our list that can be expanded/subtracted like all our combat messages and then wiring it in - makes the most sense."*

#### Who asks for each grapple phase

`get_combat_message` is asked for `grapple` phases at eleven production call sites: three resolver beats, two auto-escape beats, and six release beats across five doors (the charge door branches same-room / cross-room; the edge door is #3668).

| phase | variants | requested by |
|---|---|---|
| `hit` | 30 | `speak_grapple_beat(char, target, "hit")` on a won roll in `resolve_grapple_initiate` (`world/combat/grappling.py`) |
| `miss` | 3 | `speak_grapple_beat(char, target, "miss")` on a lost roll, same resolver |
| `release` | 2 | `speak_grapple_beat(char, grappling_target, "release")` in `resolve_release_grapple` |
| `escape_hit` | 2 | `resolve_auto_escape` (`world/combat/actions.py`), which the round loop runs for anyone grappled (`world/combat/handler.py`) |
| `escape_miss` | 2 | `resolve_auto_escape` (`world/combat/actions.py`) |
| `release_charge` | 3 | same-room branch of `_release_grapple_for_charge` — `speak_grapple_beat(char, grappled_victim, "release_charge", charge_target=target)` (`world/combat/movement_resolution.py`). Spends the third-party placeholder `{charge_target}` |
| `release_charge_away` | 2 | the cross-room branch of the same helper. Names no third party: the charge target is in another room, so the line says "charges away" instead |
| `release_jump` | 3 | gap jump in `CmdJump` (`let_go_for_the_leap`, `commands/combat/jump.py`): spoken with `break_grapple` only once the jumper's move has happened (or on a slip in place), its room line sent to the roof they left; a refused move keeps the hold and speaks nothing |
| `release_edge` | 2 | `hold_opens_at_the_edge` in `CmdJump` (`commands/combat/jump.py`), when a dragged victim's move off the edge is refused. After an edge jump the jumper has already gone over, so the room line is sent with `room=` to the roof the victim still stands on; on an edge descent both still stand on the roof |
| `release_blast` | 2 | the blast on a human-shield sacrifice jump (`CmdJump`, `commands/combat/jump.py`). The only one of the #3615 five where the *actor* did not choose it, and the prose says so ("The blast tears {target_name} out of your arms!") |
| `release_intent` | 1 | **actor only**: queue-time charge preview in `CmdCharge` (`commands/combat/movement.py`), called with `audiences=("actor",)` and `charge_target=target_search` |
| `grapple_damage_hit` | 30 | nothing |
| `grapple_damage_miss` | 5 | nothing |
| `grapple_damage_kill` | 2 | nothing |

52 variants reach players. The 37 that do not are all `grapple_damage_*`. No code path deals damage *for* a grapple, so there is no beat for those three phases to narrate; they are content behind a mechanic that does not exist, not a wiring gap (`specs/GRAPPLE_SYSTEM_SPEC.md` §Grapple Damage System). Nothing is to be hooked up to them until the owner question on #3285 is answered (see Not decided).

#### Delivery — `speak_grapple_beat`

`speak_grapple_beat(actor, target, phase, *, audiences=("actor", "victim", "room"), room=None, **extra_chars)` (`world/combat/grappling.py`) is the door onto the bank for every grapple beat except the two auto-escape beats, which `resolve_auto_escape` (`world/combat/actions.py`) fetches with `get_combat_message` and sends itself. It is public because three modules outside its own call it (`world/combat/movement_resolution.py`, `commands/combat/jump.py`, `commands/combat/movement.py`). It delivers exactly as the weapon banks do: `attacker_msg` to the actor, `victim_msg` to the target, and `observer_template` + `observer_char_refs` through `msg_room_identity` with the pair excluded, so every bystander sees the pair rendered through their own recognition state instead of a pre-baked name.

- **`audiences`** narrows delivery to a subset of `("actor", "victim", "room")`; the default is all three. Only `release_intent` uses it (`audiences=("actor",)`), because a *queued* charge has not ended the hold yet, and telling the victim or the room would describe a world state that does not exist. That phase's single variant also authors empty strings for the other two audiences, so the narrowing and the bank say the same thing and either alone would suffice.
- **`**extra_chars`** is forwarded verbatim as the accessor's `extra_chars` argument: a third party the line names, rendered per audience (§Third parties — `extra_chars`). `release_charge` and `release_intent` are the only phases that spend one, both as `charge_target`.
- **`hit_location`** is passed **for the `hit` phase only**: `select_hit_location(target, attacker=actor)` (`world/medical/utils.py`), the same anatomy-weighted, armour-aware draw an attack makes, the attacker reading the target's weak points. `hit` is the one reachable grapple phase that spends the placeholder. Every other phase is asked for without it and none of their variants uses it, as with the escape call sites in `world/combat/actions.py`. There is no `or "arm"` fallback and no placeholder default dict, so an unpassed `hit_location` surfaces as the loader's `(Error: Missing placeholder …)` rather than a silent limb, which is the contract the other banks live under (`specs/archive/WEAPON_MESSAGE_CONVERSION_SPEC.md`, #1583).
- **`room`** names the room that hears the beat when the actor has already left it (a gap jump, or a hold that opens at an edge the jumper has gone over, #3668). By default it is the actor's own room.

**Where the room broadcast lands.** `speak_grapple_beat` sends the room line to `room` when the caller passes one, and otherwise to `actor.location`, read at send time. Every door that passes no `room` speaks before its mover moves, or moves nobody. The cross-room charge releases the hold before `char.move_to(target_room)` (`_resolve_charge_cross_room`, `world/combat/movement_resolution.py`), so `release_charge_away` is heard in the room the pair was grappling in (#3615). The jump doors that speak after the jumper has moved pass `room=` the roof the jumper left: `let_go_for_the_leap` (`release_jump`) and `hold_opens_at_the_edge` (`release_edge`), both in `commands/combat/jump.py`. The victim's own line is sent directly, wherever the victim is.

**Grapple colour** is the grapple's own green and yellow, not the attack palette (§Automatic Color Application System).

#### `{hit_location}` is the target's location

`{hit_location}` is always the TARGET's location, in every audience's line, in every bank.

- In `grapple.py`, every `hit` variant spends it that way. A face on the attacker and observer lines is the literal word `face`, matching the victim line's "their face". Lines about the attacker's own limbs say `arms` outright ("locking your arms around {target_name}'s {hit_location}"; "Like a vise, your/{attacker_name}'s arms clamp around …"). No `hit` variant pluralises the placeholder; they all read `{target_name}'s {hit_location}` or `your {hit_location}`. The `grapple_damage_hit` lines about the attacker's own part say "your forearm" and "your shoulder" (#3710).
- Across all banks (#3710): an attacker line does not say "your {hit_location}" for the attacker's own part, and a victim or observer line does not say "{attacker_name}'s {hit_location}". The token is never glued inside a word or to a hyphen (`{hit_location}or` for armor, `cap` for kneecap, `line` for jawline, `s` for hands/knees/legs, `{hit_location}-first`). It is not used where the word is not the rolled part: the adverb "back" ("they stagger back"), the weapon's own part ("the head of the axe", "the neck of the bottle"), a sub-part ("the side of your head", "the back of the hand"), a posture ("drops to one knee", "folds at the waist"), a blow's name ("a side swing", "a gut punch"), list items ("the hand, wrist, and forearm"), and article-less struck parts the sentence itself fixes ("lands low, carving into shin", "marked from shoulder to hip", "slips between ribs"). Those say the author's word.
- Where the author names the struck part as a bare noun that the roll should still decide ("Steel collides with the {hit_location}", "bruising the {hit_location}"), the token stays, with an article where the grammar wants one.
- `world/tests/test_every_bank_spends_the_token_on_the_target.py` pins the attacker-self, attacker-part, glued and adverb-seat shapes at zero over every bank, and names the 8 entries whose attacker line carries a token while the victim line carries none.
- A token behind a possessive or article whose anatomy the sentence fixes by other words ("catches them under the chin; their {hit_location} snaps back") is the remaining limit of this rule; no rule reaches it.

#### Grapple prose that stays outside the bank

These keep bespoke prose because no bank phase carries their meaning:

- the consensual uncontested hold (the consent branch of `resolve_grapple_initiate`, `grappling.py`): the `hit` bank is all violent shoot-ins and vises, and a trusted `grab` involves no contest and no roll;
- `resolve_grapple_join` and `resolve_grapple_takeover`, whose beats are three-party and name a *current grappler* or a *third victim* that a two-party bank line has no slot for.

`establish_grapple` (`grappling.py`) also returns a hardcoded string. It is imported by `world/combat/handler.py` and called by nothing in production; only tests exercise it, to pin its one-grappler-one-victim guard.

### Standard Placeholders:

The loader supplies these placeholders:

- **`{attacker_name}`** - Attacker's display name (for victim/observer messages)
- **`{target_name}`** - Target's display name (for attacker/observer messages)
- **`{item_name}`** - Weapon/item name
- **`{damage}`** - Damage dealt (for hit/kill messages)
- **`{hit_location}`** - the target's struck location (§`{hit_location}` is the target's location)
- **`{blood}`** / **`{Blood}`** - the species-keyed *target* fluid: human crimson, synth cobalt, robot amber (#1206/#1207)
- **`{attacker}`** / **`{target}`** / **`{item}`** - bare aliases
- **`{phase}`** - the phase name
- any third-party placeholder passed in `extra_chars` (§Third parties — `extra_chars`)

A placeholder named in a template that the loader was not given renders as `(Error: Missing placeholder …)` in the line, not a silent blank.

What the banks actually use: `{attacker_name}`, `{target_name}` and `{hit_location}` in all 104; `{blood}` in 68; `{Blood}` in 16; `{item_name}` in 4 (`bowel_disruptor.py`, `tiger_claws.py`, `tiger_claws_akimbo.py`, `light_pistol_akimbo.py`); `{damage}` in 2 (`anti-material_rifle.py`, `heavy_pistol.py`); `{item}` in 1 (`melee.py`); `{charge_target}` in 1 (`grapple.py`); `{phase}` in none. `{damage}` is supported by the loader but is not the shipped authoring style. `{item_name}` is the style a pair bank may use (§Bank pairs); the other banks bake their weapon's name into the prose. Whether banks should use `{item_name}` and `{damage}` is open (#1513; see Not decided).

#### Third parties — `extra_chars`

A line sometimes has to name **someone who is neither the attacker nor the target**: the person a grappler lets go of their victim to charge at (#3615). `get_combat_message` takes a keyword `extra_chars={placeholder_name: object}` alongside `attacker` / `target` / `item`. Each entry adds one placeholder to the bank's vocabulary, and it is **rendered per audience, exactly as the two principals are**, rather than resolved once and baked in:

| audience | how the object renders | built at |
|---|---|---|
| `attacker_msg` | `get_display_name_safe(obj, attacker)` — the third party as the **actor** knows them | `attacker_format` in `get_combat_message` |
| `victim_msg` | `get_display_name_safe(obj, target)` — as the **victim** knows them | `victim_format` |
| legacy `observer_msg` | `obj.key`, pre-resolved — matching what that legacy field does for the pair | `observer_legacy_format` |
| identity-aware `observer_template` | **left as the literal `{placeholder}`**, and the object is carried in `observer_char_refs` | the observer-template block at the end of `get_combat_message` |

The last row carries the design. The observer template is formatted with `format_map(_PassThrough(shared_kwargs))`, and `extra_chars` is deliberately **not** folded into `shared_kwargs`, so an entry the map does not know survives formatting as the literal `{charge_target}` instead of being resolved early or raising `KeyError`. `observer_char_refs` carries the object under that same key, and `msg_room_identity` (`world/identity_utils.py`) substitutes it once per observer through *that observer's* recognition state. A bystander who knows the charge target by name reads the name; one who does not reads their sdesc, in the same sentence where the grappler and the victim are resolved the same way. Placeholders `msg_room_identity` has no ref for pass through untouched, so this costs the other banks nothing.

`extra_chars` defaults to `None` and is normalised to `{}` in the loader, so a caller that passes nothing gets the plain behaviour. Its only users are the grapple bank's `release_charge` and `release_intent` phases, whose `{charge_target}` is supplied by `speak_grapple_beat(..., charge_target=target)` (§Special Extended Phases). A placeholder named in a template but absent from `extra_chars` fails the way every other missing placeholder does: `(Error: Missing placeholder …)` in the rendered line, not a silent blank.

`get_combat_message` also takes `audiences` (default all three of `actor`, `victim`, `room`). It renders only the audiences listed and returns `""` for the others, with empty `observer_char_refs` when `room` is left out. This is because naming someone through the identity system rolls, and stores, a disguise check for that reader, and a line nobody receives must not spend that roll. `speak_grapple_beat` passes `audiences` on every call.

**What the third party reads.** The room broadcast excludes only the attacker and the target, so the third party is an ordinary observer, and `get_display_name(self)` returns their own key (`get_display_name` in `typeclasses/characters.py`). The person being charged reads *"Jorge lets go of Skullface and goes for [their own name]"*, not *"…goes for you"*. `msg_room_identity` has no second-person substitution; any door that wants one has to send that person their own line, the way the attacker and victim get theirs.

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

This rule is bank-wide, not a grapple detail (#3427). Templates are handed **bare** names and the *rendered sentence* is capitalised once, so the sentence decides the capital instead of the placeholder. `get_combat_message` (`world/combat/messages/__init__.py`) builds `target_sees_attacker` with no capitalisation of its own and passes each formatted `attacker_msg` / `victim_msg` / `observer_msg` through `capitalize_first` before colouring. The identity-aware observer path follows the same rule (#3209); all three audiences agree.

**What it means for authors.** A name may sit anywhere in a line. An sdesc keeps its lowercase article mid-sentence ("You stumble as a lanky man ties you up!") and takes the capital only when it opens the sentence ("A lanky man finds themselves trapped in your unyielding grapple!"). **Proper names are unaffected**: `capitalize_first` uppercases the first *visible* letter, and one that is already a capital stays as it is. It also steps over colour markup, so a pre-coloured line is not silently promoted from `|r` to `|R` (`capitalize_first`, `world/grammar.py`, #2207).

## Tone and Style Guidelines

### Existing Content Quality:
- **Rich, atmospheric messages** with visceral descriptions
- **Cinematic tone** influenced by:
  - Film noir and gritty crime fiction
  - Horror/thriller aesthetics
  - Hardboiled detective fiction
  - Industrial/urban decay atmosphere
  - Psychological tension and dread
- **Technical weapon details** integrated naturally
- **Multiple message variants** per phase (10-20+ per category; the banks' median per core phase is 30, min 4, max 45)
- **Consistent voice** across different weapon types

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

#### Example Analysis:

**Chainsaw (single-string)**:
```
"A guttural sound fills the room as the saw turns over. It doesn't want to start — it *needs* to."
```
- Mechanical personification
- Ominous inevitability
- Sensory detail (sound)
- Psychological undertones

**Anti-material Rifle (three-perspective)**:
```
"attacker_msg": "You meticulously line up the shot with your anti-material rifle, knowing a single round can vaporize {target_name}."
```
- Technical competence
- Calculated deliberation
- Understated lethality
- Professional focus

## Authoring a Bank

### Writing from existing prose
- **DO NOT TRUNCATE** existing message content
- **PRESERVE** the atmospheric quality and specific details
- **MAINTAIN** the established voice and tone
- **CONVERT** single strings to three-perspective format. For each message, write three versions:
  1. **Attacker**: first-person "You" perspective
  2. **Victim**: add victim-specific threat awareness
  3. **Observer**: third-person observational view
- Use `{attacker_name}` (victim/observer lines only), not `{attacker}`; use `{target_name}` (attacker/observer lines only), not `{target}`
- `{item_name}` and `{damage}` are supported by the loader; whether banks should use them is open (#1513)
- **Expand message variety** if needed (target: 10-20 per phase, 10+ preferred)
- **Add technical details** specific to weapon type
- **Enhance sensory descriptions** while maintaining tone
- **Ensure phase coverage** (initiate, hit, miss, kill minimum)
- **Test the bank** through the message system (`get_combat_message`)

### Checklist
- All existing atmospheric content preserved; nothing truncated or lost
- Three-perspective format and dictionary structure as specified
- Tone consistent across perspectives
- Technical weapon details included naturally; sensory descriptions rich and varied
- Standard placeholders used correctly
- Required phases present (initiate, hit, miss, kill)
- Professional competence conveyed; atmospheric tension maintained; industrial/noir aesthetic preserved
- Violence portrayed as matter-of-fact, not glorified; pacing deliberate and inevitable

### Common Pitfalls to Avoid:
- Truncating rich atmospheric content
- Making victim messages identical to observer messages
- Losing technical weapon-specific details
- Breaking the established noir/industrial tone
- Rushing a conversion without preserving quality

## Special Cases

### Grapple.py:
- Extended phases: `escape_hit`, `escape_miss`, `release`, `release_charge`, `release_charge_away`, `release_jump`, `release_blast`, `release_edge`, `release_intent`, `grapple_damage_*` — 14 phases / 89 variants in all (§Special Extended Phases)
- Use as template for other close-combat weapons

### Unarmed.py:
- Standard four-phase structure
- Good baseline template for new banks
- A non-human attacker's unarmed lines come from `unarmed_<species>.py` if that file exists (only `unarmed_rat.py` does), and from `unarmed.py` if it does not. `unarmed_rat.py` counts among the 104 banks. No other weapon type has species banks (#356)

### Weapon-Specific Considerations:
- **Firearms**: Emphasize technical preparation, recoil, ballistics
- **Bladed Weapons**: Focus on edge quality, precision, intimate violence
- **Improvised Weapons**: Highlight adaptation, desperation, creativity
- **Power Tools**: Mechanical personality, industrial brutality
- **Explosives**: Countdown tension, area effect awareness

## Delivery

### Automatic Color Application System

`_apply_color` (in `get_combat_message`, `world/combat/messages/__init__.py`) colours each rendered line by phase. In Evennia lowercase is normal and uppercase is bright. It checks, in order:

1. An **empty** message is returned as-is (this keeps `release_intent`'s empty victim and observer lines from arriving as stray colour codes).
2. A message already wrapped `|…`…`|n` is returned unchanged (pre-coloured templates bypass automatic colouring). This applies in both branches below.
3. **Grapple** (`weapon_type == "grapple"`): `hit` / `release` / `escape_hit` → `|g`; `miss` / `escape_miss` / `release_charge` / `release_charge_away` / `release_jump` / `release_blast` / `release_edge` / `release_intent` → `|y`; everything else in the bank uncoloured (#3427, #3615, #3668).
4. **Attack palette** (every other bank):
   - **Kill Messages**: `|r{message}|n` (normal red)
   - **Hit Messages**: `|R{message}|n` (bright red)
   - **Initiate Messages**: `|R{message}|n` (bright red) — `initiate` sits in `successful_hit_phases` with `hit`
   - **Miss Messages**: `|W{message}|n` (bright white)
   - **Other Messages**: No automatic coloring

**Why grapple has its own colours.** A grapple is a hold, not a wound, so it keeps the green and yellow its old hardcoded lines and its bespoke consensual-hold prose wear. The split is not success against failure but *hold kept or let go on purpose* (green) against *a grip lost, or about to be* (yellow), which is what the `release_*` phases narrate, including the preview, where the grip is not lost yet. `escape_hit` / `escape_miss` are coloured by this branch (they were bare from #3391 until #3427).

What the attack palette gives a player:
- **Threat escalation**: `initiate` and `hit` both render `|R`, so they look **identical**; `kill` renders `|r`, which is *less* bright than `|R`. There is no three-step visual progression from initiate → hit → kill (see Not decided).
- **Clarity**: Bright-white misses clearly indicate failed attempts
- **Consistency**: Automatic application ensures uniform presentation
- **Override Support**: Pre-colored templates bypass automatic coloring

### Initiate Messages

Combat initiation gives perspective-specific messages and a defensive reaction:

- **Attacker Initiate**: Aggressive stance establishment ("You draw your knife...")
- **Victim Defensive**: the target's own initiate line, as a defensive reaction ("Nick raises his baton defensively...")

The target's defensive message is sent when:
- Target wasn't already in combat, OR
- Target was in combat but not targeting anyone
- And in either case the target is neither dead nor unconscious (a body can still be attacked, but it does not pose), and is not the attacker

### Message Personalization
- **Attackers** see first-person messages (`attacker_msg`)
- **Victims** see second-person messages (`victim_msg`)
- **Observers** see third-person messages, delivered from `observer_template` through `msg_room_identity` (`observer_msg` is the legacy fallback; §Standard Structure)

### No Meta-Messages

There are no generic combat-state announcements: no "You enter combat!" and no "You are no longer in combat." Combat opens on the weapon-specific threat and flows into the action, which keeps transitions immersive and cuts message spam. A combatant who leaves combat on their feet gets a narrative line in place of the removed announcement (#306): "You lower your guard and step back from the fight.", and the room sees "{actor} lowers their guard and steps back from the fight."

### Death Messages

- **Observers**: no line when the death curtain starts. When it ends, a cause- and species-specific line from `get_death_cause_template` (`world/medical/medical_messages.py`), with the dying person named as each observer knows them; for blood loss: "{actor}'s lifeblood pools crimson around their still form."
- **Victim**: "Your body succumbs to blood loss. The end draws near..."
- **Fallback**: Beautiful mixed red death curtain message

The death curtain:
- colours its blocks randomly in `|r`/`|R`;
- centres its text accounting for colour code length;
- uses the medical system for cause-specific messaging;
- suppresses bleeding messages to prevent a race with the curtain.

#### Kill message before the curtain

In combat, the kill message is shown before the death curtain starts; if combat fails to handle the death, the 5-second fallback starts the curtain anyway. The medical system's `take_damage()` calls `at_death()` as soon as damage is fatal; `at_death()` checks for active combat via `ndb.combat_handler`:

- **In combat**: it sets `ndb.death_curtain_pending = True` and skips the immediate curtain. `_handle_kill` (`world/combat/attack.py`) triggers the deferred curtain after sending the kill message. A 5-second delayed trigger is the safety fallback, so the curtain appears even if combat fails to handle it and no death state is left stuck.
- **Not in combat** (bleeding out): the curtain is not deferred.

The sequence a dying combatant sees:
1. Fatal damage determined by medical system
2. Kill message sent by combat system ("Nick's bullet strikes you in the heart, killing you instantly")
3. Death curtain animation begins after kill message
4. Medical death analysis continues normally

The medical and combat systems coordinate this way without coupling.

## Not decided

- **Was a grapple-damage exchange ever meant to ship?** Open on #3285. Until it is answered, nothing is to be hooked up to the `grapple_damage_*` phases (§Special Extended Phases).
- **Should banks use `{item_name}` and `{damage}`?** The loader supports both; most banks bake their weapon's name into the prose and only two use `{damage}`. Whether that is intended house style or a gap is an open owner call (#1513).
- **Threat escalation colours.** `initiate` and `hit` render the same `|R`, and `kill` renders the dimmer `|r`. Whether the escalation should be `|r` → `|R` → `|R` + something (bold, a prefix, a bright-magenta kill) is an open owner call. The code is internally consistent; the escalation is not what a player sees.

## Related documents

- `specs/GRAPPLE_SYSTEM_SPEC.md` — the grapple system, §Grapple Damage System
- `specs/proposals/MULTI_WEAPON_COMBAT_SPEC.md` — §7 and §14 #14, bank pairs
- `specs/COMBAT_SYSTEM.md` — the combat system
- `specs/DEATH_CURTAIN_SPEC.md` — the death curtain
- `specs/archive/WEAPON_MESSAGE_CONVERSION_SPEC.md` — the missing-placeholder contract (#1583)
