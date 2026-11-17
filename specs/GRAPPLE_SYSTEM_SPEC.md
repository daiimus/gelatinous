# G.R.I.M. Grappling System Specification

> **Status:** ✅ **SHIPPED** — Phase 1 complete; Phases 2-3 remain future work. ~~Verified 2026-08-02~~ **re-checked 2026-09-11: 17 claim(s) false, annotated inline**.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - **"Grenade Bodyshield System ⚠️ MISSING IMPLEMENTATION" is wrong — it is built.** `world/combat/explosives.py:36` `check_grenade_human_shield` + `:103`, called from three sites. The shipped version is deterministic (grappler ×0.0, victim ×2.0), not the probabilistic formula proposed here.

## Overview

The G.R.I.M. Grappling System is a comprehensive close-combat mechanism that emphasizes **restraint over violence** while providing tactical depth for complex combat scenarios. It integrates seamlessly with the proximity system, movement mechanics, and yielding philosophy to create dynamic, roleplay-focused grappling encounters.

## Design Philosophy

### 1. **Restraint-First Approach**
- **Default Intent**: Grappling begins as restraint, not violence
- **Escalation Control**: Violence requires explicit choice by participants
- **De-escalation Opportunities**: Multiple chances to avoid harm
- **Roleplay Priority**: Combat serves narrative, not mechanics

### 2. **Tactical Complexity**
- **Movement Integration**: Grappling affects and is affected by positioning
- **Multi-Character Dynamics**: Complex interactions between multiple grapplers
- **State Management**: Rich state system supporting various scenarios
- **Strategic Depth**: Advanced options for experienced players

### 3. **Mechanical Consistency**
- **Attribute-Based**: Uses core G.R.I.M. attributes (primarily Motorics)
- **Contest System**: Opposed rolls determine outcomes
- **State Validation**: Robust error checking and cleanup
- **Integration**: Seamless connection to combat, movement, and social systems

---

## Core Mechanics

### Grapple States

#### **Grappling Relationship States**
1. **Not Grappling**: Character has no grapple involvement
2. **Grappling Someone**: Character is holding/restraining another
3. **Being Grappled**: Character is held/restrained by another
4. **Mutual Grapple**: Two characters grappling each other (rare, contest-based) — 📋 UNBUILT (not decided): as built no path lets two characters hold each other, since a held character cannot grapple and a takeover makes the person taken let go of their own victim first

#### **Grapple Intent States**
1. **Restraint Mode** (Default): Non-violent holding/control
2. **Violent Mode**: Active struggle with damage potential

#### **Participation States**
1. **Yielding**: Accepting restraint, no resistance
2. **Non-Yielding**: Active resistance, automatic escape attempts

### Primary Attributes
- **Motorics**: Primary attribute for grapple initiation, contests, and escape attempts
- **Grit**: Used for drag resistance during room traversal (physical endurance/willpower)
- **Resonance**: Tertiary for reading intent and de-escalation (future implementation)

---

## Grapple Initiation

### Command: `grapple <target>`

#### **Prerequisites**
- Must be in same room as target
- Target must be valid character
- Cannot grapple self
- Grappling someone new while already holding someone is not refused, as built: if the new grapple succeeds, the first hold is let go (`release_existing_grapple`, #2486). One grappler holds one victim. Whether a second grapple should be refused instead is an open owner question on #3285
- Cannot grapple if being grappled by someone else
- Grappling a target who cannot perceive you gets the ambush initiative bonus (`specs/proposals/STEALTH_AND_DETECTION_SPEC.md` §6.1), except on a consensual grab
- Every grapple is reported to the crime system as an assault, as a punch is

#### **Proximity Requirements**
- **Combat Initiation**: Grapple can initiate combat and establish proximity
- **Proximity**: Grappling a free target, or grappling someone who is holding another person, needs no proximity, in or out of a fight: the grappler rushes in, and proximity is set up on success. Contesting someone else's hold on a victim needs melee proximity with that victim (`resolve_grapple_join`)

#### **Contest Resolution**
```
Grappler Roll: 1d[Motorics]
Defender Roll: 1d[Motorics]

Success: Grappler > Defender
Failure: Defender >= Grappler
```

*Note: All grapple initiation, takeover, and escape attempts use Motorics vs Motorics*

**Consensual hold (#3363, owner ruling 2026-09-13).** If the target trusts the grappler for `grab`, or cannot contest (unconscious or already restrained), there is no roll. The hold is taken, both parties become yielding, and the held person gets no target. The outcomes below are for the contested grapple. See `specs/TRUST_AND_CONSENT_SPEC.md` §3.

#### **Success Outcomes**
1. **Grapple Established**: Two-way relationship created
   - Grappler: `grappling_dbref` → Target
   - Target: `grappled_by_dbref` → Grappler
2. **State Changes**:
   - Grappler: Auto-yields (restraint intent)
   - Target: Remains non-yielding (auto-resistance)
3. **Proximity**: Both characters enter/maintain proximity
4. **Targeting**: Target auto-targets grappler for potential retaliation

#### **Failure Outcomes**
1. **No Relationship**: No grapple state changes
2. **Yielding Consequences**: 
   - If grappler initiated combat: Auto-yield
   - If defender joined combat this round AND has no existing combat target: Also auto-yield
   - If defender was already engaged in combat: Continue existing fight
3. **Messaging**: Failure messages with narrative context — the `miss` bank since 2026-09-18 (#3427), see §Grapple Messaging

### Grapple Messaging

> **Recorded 2026-09-18 (#3427, completed the same day by #3615) — the authored bank now speaks for the grapple, and for every way a grapple ends.** Until this date the live resolvers wrote their own one-line prose and the bank went unread: 72 of `world/combat/messages/grapple.py`'s 76 variants were unreachable (measured 2026-09-12, `specs/COMBAT_MESSAGE_FORMAT_SPEC.md` §Special Extended Phases). #3427 wired the three resolver beats (39 of 76 live). #3615 then authored **five new phases, 11 variants**, for the four doors that had still been writing prose inline, and wired them: the bank is now **13 phases / 87 variants, 50 of them live**. (#3668 then added `release_edge`, 2 variants, making it 14 phases / 89 variants, 52 of them live.)

**Where each beat gets its words**

| beat | source | phase / variants |
|---|---|---|
| Contested grapple won (`resolve_grapple_initiate`, `world/combat/grappling.py`) | bank | `hit` — 30 |
| Contested grapple lost (same resolver) | bank | `miss` — 3 |
| Voluntary release (`resolve_release_grapple`) | bank | `release` — 2 |
| Auto-escape won / lost (`resolve_auto_escape`, `world/combat/actions.py`) | bank, fetched and sent by the resolver itself | `escape_hit` / `escape_miss` — 2 + 2 |
| Let go to charge someone else in the room (`_release_grapple_for_charge`, `world/combat/movement_resolution.py`) | bank, since #3615 | `release_charge` — 3, names the charge target |
| Let go to charge out of the room (same helper) | bank, since #3615 | `release_charge_away` — 2 |
| Let go for a gap jump (`let_go_for_the_leap`, `commands/combat/jump.py`; since #3684 only after the jumper's move, or on a slip in place) | bank, since #3615 | `release_jump` — 3 |
| Dragged victim cannot be taken over an edge (`hold_opens_at_the_edge`, `commands/combat/jump.py`) | bank, since #3668 | `release_edge` — 2 |
| Blast tears the pair apart on a sacrifice jump (`handle_explosive_sacrifice`, `jump.py`) | bank, since #3615 | `release_blast` — 2 |
| Queue-time charge preview, actor only (`CmdCharge`, `commands/combat/movement.py`) | bank, since #3615 | `release_intent` — 1 |
| Consensual uncontested hold (`resolve_grapple_initiate`) | bespoke prose in the resolver | — |
| Contest for a held victim (`resolve_grapple_join`) | bespoke prose | — |
| Grappling an active grappler (`resolve_grapple_takeover`) | bespoke prose | — |
| Grapple damage | nothing — mechanic unbuilt, see §Grapple Damage System and #3285 | `grapple_damage_*` — 37, unreached |

**Delivery.** One module-level helper, `speak_grapple_beat(actor, target, phase, *, audiences=("actor", "victim", "room"), room=None, **extra_chars)` (`world/combat/grappling.py`), delivers every bank phase except the two escapes: `resolve_auto_escape` (`world/combat/actions.py`) fetches `escape_hit` / `escape_miss` with `get_combat_message` and sends them itself. Three ways a hold ends still write inline prose instead of using the bank: a drag resisted at the walk door (`Exit.at_traverse`, `typeclasses/exits.py`), a drag resisted at the advance door (`_resolve_advance_cross_room`, `world/combat/movement_resolution.py`, which tells only the pair and not the room), and a takeover's forced release (`resolve_grapple_takeover`). It was `_say_from_bank` until #3615 made it public and repointed the three in-file callers; three modules outside `grappling.py` now call it, so the underscore had stopped being true. It asks `get_combat_message("grapple", phase, …)` and then delivers the result the way the weapon banks are delivered: `attacker_msg` to the actor, `victim_msg` to the target, and `observer_template` with `observer_char_refs` through `msg_room_identity`, excluding the pair — so each bystander reads the two of them through their own recognition state rather than a name baked in at send time. `hit_location` is passed **for the `hit` phase only**, from `select_hit_location(target, attacker=actor)` (`world/medical/utils.py:120`) — the same anatomy-weighted, armour-aware draw an attack makes, the attacker reading the target's weak points. `hit` is the one reachable phase that spends the placeholder (the unreached `grapple_damage_*` banks use it heavily; `miss`, `release`, the escapes, the five #3615 release phases and `release_edge` not at all), so every other call passes nothing and the dead `or "arm"` fallback was removed. All 30 `hit` variants spend it on the **target's** body: the two that used to put it on the grappler's own limbs ("locking your {hit_location}s", "Like a vise, your {hit_location}s") now say `arms` outright, and the one that meant a face says `face` (`world/combat/messages/grapple.py:10-12`, `:70-72`, `:125-127`).

Three parameters that helper takes, all narrow and all worth knowing before you add another door (#3615 added `audiences` and `extra_chars`, #3668 added `room`):
- **`room`** names the room that hears the beat when the actor has already left it. The edge release and the gap jump pass the roof the jumper left (`commands/combat/jump.py`); by default it is the actor's own room.
- **`audiences`** picks which of `("actor", "victim", "room")` actually receive the beat. Default is all three, and only the queue-time preview narrows it.
- **`**extra_chars`** forwards a named third party to the accessor as `extra_chars={name: obj}`, where it is rendered **per audience** — the actor's line uses `get_display_name_safe(obj, actor)`, the victim's uses `get_display_name_safe(obj, target)`, and the room's keeps the literal `{name}` in `observer_template` while `observer_char_refs` carries the object, so `msg_room_identity` resolves it once per bystander through their own recognition state. Only `charge_target` uses it today. The full contract is in `specs/COMBAT_MESSAGE_FORMAT_SPEC.md` §Third parties — `extra_chars`.

Two rendering rules that came with the move, both player-visible:
- **Colour is the grapple's own.** `_apply_color` branches on `weapon_type == "grapple"` ahead of the attack phase lists (`_apply_color` in `get_combat_message`, `world/combat/messages/__init__.py`): `hit`, `release` and `escape_hit` are `|g`; `miss`, `escape_miss`, the five #3615 phases (`release_charge`, `release_charge_away`, `release_jump`, `release_blast`, `release_intent`) and `release_edge` (#3668) are `|y` — green for a hold taken, kept or let go on purpose, yellow for a grip lost or about to be. A hold is not a wound — this is the green/yellow the deleted hardcoded lines wore and the consensual hold below still wears, not the attack palette's red/white. `escape_hit` / `escape_miss` gain colour here for the first time; they had shipped bare since #3391.
- **Names arrive bare and the sentence takes the capital.** Every rendered line goes through `capitalize_first` once (`get_combat_message`, `__init__.py`) instead of the accessor force-capitalising `{attacker_name}`, so a victim line reads "You stumble as a lanky man ties you up!" and an attacker line that opens on the target reads "A lanky man finds themselves trapped in your unyielding grapple!". This is bank-wide, not grapple-only — see `specs/COMBAT_MESSAGE_FORMAT_SPEC.md` §Name Capitalisation.

**Why three beats keep bespoke prose.** No bank phase carries their meaning, so routing them through it would misdescribe what happened.
- *Consensual hold* — the `hit` variants are all violent shoot-ins, vises and trapped victims. A `grab`-trusted or free-path hold (#3363, `TRUST_AND_CONSENT_SPEC` §3) is uncontested: no roll was made and nobody chose violence, and both parties end up yielding. Its three lines say so plainly.
- *Join and takeover* — both are three-party beats that must name the *current grappler* or the *third victim* ("wrestles {target} away from {grappler}", "forcing them to release {victim}"). Bank lines have only an attacker and a target; there is no slot for the third person, and dropping them would make the message lie about who lost the hold.

**Also still hardcoded, deliberately:** `establish_grapple` (`grappling.py`) returns a `(success, message)` tuple with its own string. It is imported at `world/combat/handler.py:49` and called by nothing in production — only the tests that pin its one-grappler-one-victim guard reach it — so it was left alone rather than converted.

**RESOLVED 2026-09-18 (#3615) — the four other doors now speak from the bank too.** Until this change `speak_grapple_beat` was the only door onto the `release` bank but not the only way a grapple ends: four paths broke a hold and wrote fixed prose inline, and none of them told the **room**, so bystanders watching a hold never learned it broke. The `release` bank could not simply be pointed at them — its two variants ("You decide to release your hold on X", "You shove X away, ending the grapple") describe a *choice*, and would misdescribe a hold ended by a charge, a jump or an explosion. The owner's call was to author the missing beats rather than reuse a wrong one or patch four broadcasts in place:

> *"adding the missing messages to our list that can be expanded/subtracted like all our combat messages and then wiring it in - makes the most sense."*

So five phases were written into `world/combat/messages/grapple.py` — 11 variants, expandable and subtractable exactly like every other bank entry — and each door was repointed at one:

| door | phase (variants) | what changed |
|---|---|---|
| `_release_grapple_for_charge`, same room (`world/combat/movement_resolution.py`) | `release_charge` (3) | The old inline `\|y` pair is gone. The line names the third party through `charge_target=target`, rendered per audience |
| the same helper, cross-room | `release_charge_away` (2) | Same; no third party is named, because the charge target is in another room |
| Gap jump (`let_go_for_the_leap`, `commands/combat/jump.py`) | `release_jump` (3) | The old `\|y` actor / `\|g` victim pair is gone; the beat is `\|y` for all three audiences now, and since #3684 it is spoken only after the jumper's move, or on a slip in place (room line to the roof they left, or still stand on) |
| Blast on a sacrifice jump (`handle_explosive_sacrifice`, `jump.py`) | `release_blast` (2) | The old pair named nobody ("The explosion breaks your hold!"). The new variants name the other party in every audience's line |
| Queue-time charge preview (`CmdCharge`, `commands/combat/movement.py`) | `release_intent` (1) | Still actor-only, and now deliberately so — see below |

**The room now hears all three real endings.** A charge, a gap jump and a blast each broadcast through `msg_room_identity` with the pair excluded, so every bystander reads the grappler and the victim through their own recognition state instead of a baked-in name — the same delivery the `hit` / `miss` / `release` beats have had since #3427. On a cross-room charge the release is spoken before the charger moves (`_resolve_charge_cross_room` calls `_release_grapple_for_charge` ahead of `move_to`), so `release_charge_away` is heard in the room where the hold was. The victim's own line is sent directly.

**The queue-time line is an actor-only preview by design.** `release_intent` is printed when `charge` is *queued* while you are holding someone — nothing has happened to the hold yet; the release itself resolves a round later in `_release_grapple_for_charge`. Telling the victim or the room at that moment would describe a world that does not exist, so the door passes `audiences=("actor",)` **and** the phase's one variant authors empty strings for `victim_msg` and `observer_msg`. Either would be enough on its own; both are there so neither a new caller nor a new variant can leak the preview by accident. An empty message is never coloured (`_apply_color`, `world/combat/messages/__init__.py`), so the unused audiences produce nothing at all rather than a bare colour pair.

**The victim's old `access(char, "view")` gate is gone.** The same-room charge door used to send the victim's line only if `grappled_victim.access(char, "view")` passed — a lock check no other bank delivery makes, on the person whose own arms are being let go of. It went with the inline prose. The victim now receives `victim_msg` on the same terms as in every other grapple beat: directly, always, with the grappler rendered through the victim's own recognition state.

**Still bespoke, and still correct:** the three beats in the list above (consensual hold, join, takeover) and `establish_grapple`. #3615 changed nothing about them.

**Not yet reached:** the 37 `grapple_damage_hit` / `_miss` / `_kill` variants. Wiring them needs the damage exchange itself, which was never built; see §Grapple Damage System and the open owner question on #3285.

---

## Grapple Contests (Takeover)

### Multi-Grapple Scenarios

#### **Scenario 1: Contest for Existing Victim**
- **Setup**: A grapples B, then C attempts to grapple B
- **Mechanism**: Contest between A and C for control of B
- **Resolution**: Winner gets B, loser gets nothing
- **Outcome**: B remains grappled by winner

#### **Scenario 2: Grappling an Active Grappler** ✅ **IMPLEMENTED**
- **Setup**: A grapples B, then C attempts to grapple A
- **Implementation**: System now detects "grapple_takeover" scenario
- **Behavior**: Force A to release B, then C can grapple A
- **Sequence**: 
  1. C initiates grapple on A (detected as grapple_takeover)
  2. Contest: C's Motorics vs A's Motorics
  3. If successful: A releases B automatically, C grapples A
  4. If failed: A maintains grapple on B, C becomes yielding (if initiated combat)

### Contest Mechanics
```
Challenger Roll: 1d[Motorics]
Current Grappler Roll: 1d[Motorics]

Success: Challenger > Current Grappler → Takeover
Failure: Current Grappler >= Challenger → Maintains control
```

---

## Grapple Maintenance

### Automatic Resistance System

#### **Non-Yielding Victims**
- **Auto-Escape**: Attempt escape every combat round
- **Contest**: Victim Motorics vs Grappler Motorics
- **Success**: Break free, switch to violent mode, target grappler
- **Failure**: Remain grappled, continue struggling

#### **Yielding Victims**

> **A hold survives someone else's exit (#3622, 2026-09-18).** When a yielding party's target leaves the fight, the auto-retarget in `remove_combatant` leaves them yielding and un-pointed instead of turning them violent; the held person's shield chance and auto-escape state therefore do not change because a third party left. Described in COMBAT_SYSTEM.md.
- **No Auto-Escape**: Accept restraint peacefully
- **Manual Escape**: Can use `escape` command to switch to violent mode
- **Roleplay Focus**: Emphasis on negotiation and de-escalation

### Grapple Damage System

#### **Restraint Mode** (Default)
- **No Damage**: Pure control/positioning
- **Messaging**: Restraint-focused descriptions
- **Intent**: Subdue without harm

#### **Violent Mode** (Escalation)
- **Damage Potential**: Both parties can take/deal damage
- **Escalation Triggers**:
  - Victim uses `escape` command
  - Automatic escape success
  - External violence (attacks on grappling pair) — 📋 UNBUILT (open on #3285): as built, being attacked changes nobody's yielding state
- **Damage Types**:
  - Grapple damage hits: Control damage during struggle
  - Grapple damage misses: Failed attempts to harm

> **Re-verified 2026-09-11 — grapple damage was never built.** No code path in the repo deals damage *for* a grapple. The `grapple_damage_hit` / `grapple_damage_miss` / `grapple_damage_kill` message banks exist (`world/combat/messages/grapple.py:214`, `:366`, `:394`) and the phase-colouring lists know their names (`get_combat_message`, `world/combat/messages/__init__.py`), but no `get_combat_message()` call anywhere requests them. *Amended 2026-09-18 (#3427): those lists no longer decide the colour for this bank. `_apply_color` intercepts every `weapon_type == "grapple"` message first and names only `hit` / `release` / `escape_hit` (green) and `miss` / `escape_miss` (yellow), so if the damage exchange is ever built its three phases will ship **uncoloured** until someone decides what a damaging grapple should look like — a live question for #3285, not a bug to patch blind.*
>
> **Updated 2026-09-18 (#3427).** Every grapple phase that has a beat in shipped code now draws its prose from the bank. `escape_hit` / `escape_miss` come from `resolve_auto_escape` (`world/combat/actions.py:316`, `:369`) — the contest a grappled, non-yielding victim makes every round, and the whole of what the `escape` command's "contest next round" means (2026-09-15, #3391: the command flips yielding→violent and the auto-escape is the contest; the dict-shaped `resolve_grapple_attempt` / `resolve_escape_grapple` door that also requested `hit`/`miss` had no producer in the game and was deleted). `hit`, `miss` and `release` are now requested too, through `speak_grapple_beat` in `world/combat/grappling.py` — see §Grapple Messaging. *(Extended the same day by #3615: the five new `release_charge` / `release_charge_away` / `release_jump` / `release_blast` / `release_intent` phases are requested through the same helper from the four doors that used to write prose inline.)* The three `grapple_damage_*` banks (37 variants) are the only ones left unrequested, and they stay that way while #3285 is open: there is no damage exchange for them to narrate.
>
> In shipped code "violent mode" means only this: neither party is yielding, so the victim auto-resists every round (`resolve_auto_escape` in `world/combat/actions.py`, run from the round loop in `world/combat/handler.py`). Whether a damage exchange was ever meant to ship — and therefore whether those three banks are pending content or dead weight — is an open owner question.

### Human Shield System

#### **Bodyshield Mechanics** ✅ **IMPLEMENTED**
When a character attacks someone who is grappling a victim, the victim may intercept the attack as an involuntary human shield.

#### **Shield Chance Calculation**
```
Base Shield Chance: 40%
+ Grappler Motorics modifier: +5% per point above 1
+ Victim Resistance modifier: 
  - Yielding victim: +10% (easier to position)
  - Non-yielding victim: -10% (struggling against positioning)
- Ranged Attack modifier: -20% (harder to shield against projectiles)
```

#### **Shield Resolution Process**
1. **Attack Targeting**: Someone attacks a grappler
2. **Shield Check**: Roll d100 vs calculated shield chance
3. **Shield Success**: 
   - **Shield Messages**: Inform all parties about interception
   - **Target Redirect**: Change attack target to grappled victim
   - **Normal Combat Flow**: Proceed with standard attack resolution on victim
4. **Shield Failure**: Attack proceeds normally against intended grappler target

#### **Shield Messaging System**
- **Attacker Message**: `"Your attack is intercepted by {victim} as {grappler} uses them as a shield!"`
- **Grappler Message**: `"You position {victim} to absorb {attacker}'s attack!"`
- **Victim Message**: `"You are forced into the path of {attacker}'s attack by {grappler}!"`
- **Observer Message**: `"{grappler} uses {victim} as a human shield against {attacker}'s attack!"`

#### **Integration with Combat System** ✅ **IMPLEMENTED**
- **Pre-Attack Check**: Shield check occurs before normal attack resolution
- **Target Substitution**: Victim becomes new target for existing combat flow
- **Damage Application**: Uses normal `take_damage()` on victim
- **Combat Messages**: Uses existing weapon-based combat message system
- **No Mode Change**: Being used as a shield changes nobody's yielding state. Only a character's own act makes them non-yielding: attacking, grappling, `escape`, or winning the auto-escape

#### **Strategic Implications**
- **Defensive Grappling**: Makes grappling a protective strategy
- **Victim Motivation**: Strong incentive for victims to escape or negotiate
- **Multi-Character Tactics**: Affects targeting decisions in group combat
- **Roleplay Opportunities**: Creates dramatic tension and moral dilemmas

#### **Grenade Bodyshield System**
When grenades explode in proximity to grappling pairs, the grappled victim can absorb damage intended for their grappler.

#### **Current Grenade Shielding**
- **Holder Shielding**: When grenade explodes in someone's hands, others in proximity take 50% damage due to "body shielding"
- **Proximity-Based**: All characters in proximity list take equal damage (except holder reduction)
- **Grappling Integration** (as built): when a grappler and their victim are both in the blast, the grappler takes no damage and the victim takes double. There is no roll (`check_grenade_human_shield`, `world/combat/explosives.py`). Three explosion branches in `commands/explosion_utils.py` apply it; the explode-in-the-holder's-hands branch does not (open on #3285)

#### **Proposed Grenade Human Shield Mechanics** 📋 UNBUILT (not decided whether this still stands over the built fixed split above)
When a grenade explodes, before applying damage to characters in proximity:

1. **Grappling Check**: For each character in the explosion proximity list who is grappling someone
2. **Shield Calculation**: Use modified shield chance calculation:
   ```
   Base Shield Chance: 30% (reduced from attack-based 40%)
   + Grappler Motorics modifier: +5% per point above 1
   + Victim Resistance modifier: 
     - Yielding victim: +10% (easier to position as blast shield)
     - Non-yielding victim: -10% (struggling against positioning)
   - Area Effect modifier: -10% (harder to shield against explosions)
   ```
3. **Shield Success**: 
   - **Damage Redirect**: Grappler takes no explosion damage
   - **Victim Absorption**: Grappled victim takes grappler's full explosion damage + their own
   - **Shield Messages**: Explosive-specific messaging for dramatic effect
4. **Shield Failure**: Both grappler and victim take normal explosion damage

#### **Explosive Shield Messaging System**
- **Grappler Message**: `"You instinctively use {victim} to shield yourself from the {grenade} blast!"`
- **Victim Message**: `"You are forcibly positioned to absorb the {grenade} explosion meant for {grappler}!"`
- **Observer Message**: `"{grappler} uses {victim} as a blast shield against the {grenade} explosion!"`

#### **How the explosion paths apply it**
The explosion paths in `commands/explosion_utils.py` do not go through the combat handler's attack resolution. Each asks `check_grenade_human_shield` for a damage multiplier per character, then deals the damage with `character.take_damage(...)`.

#### **Fall Bodyshield**
When a grappler falls with their victim, the landing roll splits the fall damage: on a good landing the victim takes 0.75 of it and the grappler 0.25; on a bad one the victim takes 1.5 and the grappler 0.5 (`_land_with_bodyshield` in `world/gravity.py`, ratios `FALL_BODYSHIELD_*` in `world/combat/constants.py`).

---

## Movement Integration

### Current Implementation ✅

#### **Exit Traversal (Drag System)**
- **Conditions for Dragging**:
  - Grappler is yielding (restraint mode)
  - Grappler not targeted by others (except victim)
  - Victim fails resistance roll (Victim Grit vs Grappler Grit)
- **Successful Drag**:
  - Both characters move to new room
  - Combat state transfers to new handler
  - Grapple relationship preserved
  - The victim's channel breaks and any procedure on them ends (the surgeon is told); after the move the victim is standing, off any furniture
  - If the grappler's own move is refused, nobody moves
- **Failed Resistance**:
  - Grapple broken automatically
  - Movement blocked

> **Re-verified 2026-09-11 — accurate for the walk door, but there are two doors.** These conditions describe `Exit.at_traverse` in `typeclasses/exits.py` exactly (the yielding flag, the targeted-by-others loop, the Grit contest and the grapple-break on a successful resist). The combat `advance` door (`_resolve_advance_cross_room`, `world/combat/movement_resolution.py`) gained the same victim resistance roll in #2602, but its "targeted by others" predicate has drifted: it *also* excludes the person being advanced on, and it ignores anyone targeting the grappler from another room. The same situation can therefore pass one gate and fail the other. Reconciling them is an open owner ruling — **#3239** — not a defect.

**Edge jump** (`jump off <dir> edge`, `commands/combat/jump.py`): a third door. The victim goes over with the grappler, with no resistance roll and no yielding condition. The jumper moves first; then the victim's acts are broken and the victim is moved. If the victim still cannot be moved, the hold opens on the roof (`release_edge`, #3668). A **gap jump** (`jump across`) lets go of the victim once the leap is real (`release_jump`, #3684).

#### **Combat Movement Restrictions**
- **Being Grappled**: Blocks flee, retreat, advance, charge, every `jump`, and `throw`; attacking your own grappler is refused
- **Grappling Someone**: Charge auto-releases grapple if targeting others — narrated from the `release_charge` / `release_charge_away` bank and broadcast to the room since #3615 (§Grapple Messaging)

### Needed Implementations ⚠️

#### **Advance While Grappling** ✅ **IMPLEMENTED**
- **Current Implementation**: Full logic for grappler advancing while maintaining hold
- **Behavior**: 
  - Allow advance to new target while holding victim
  - Drag victim along during advance if conditions met
  - Victim stays in melee with the grappler only (proximity inheritance is 📋 UNBUILT, open on #3285; see §Proximity Inheritance)
- **Restrictions**: The grappler must be yielding and not targeted by anyone else in the room; the victim then gets a Grit roll to resist, and if it succeeds the hold breaks and the advance is cancelled

#### **Retreat While Grappling** ✅ **IMPLEMENTED**
- **Current Implementation**: Complete grapple-specific retreat logic
- **Behavior**:
  - Allow retreat while maintaining grapple
  - Drag victim back with grappler
  - Both maintain proximity after retreat
- **Consistency**: Both remain in proximity post-retreat

> **Re-verified 2026-09-11 — implemented, with one line to read carefully.** `retreat` (alias `disengage`) creates distance *within the same room* and never traverses an exit (`resolve_retreat`, `world/combat/movement_resolution.py`), so "drag victim back" is not a movement. What actually ships: the grappled victim is excluded from the motorics contest, a retreat whose only proximity *is* the grappled victim is refused outright, and on success proximity is broken with every opponent and deliberately maintained with the victim.

#### **Proximity Inheritance** 📋 **UNBUILT** (open on #3285)
- **Principle**: Victim inherits all of grappler's proximity relationships
- **Timing**: After successful movement (advance/retreat/charge)
- **Mechanism**: Copy grappler's proximity set to victim
- **Rationale**: Victim is "dragged along" and gains same positioning

> **NOT IMPLEMENTED — re-verified 2026-09-11; the ✅ above is unearned.** Nothing in the codebase copies a proximity set from one character to another. `world/combat/proximity.py` defines ten functions (`:28`, `:45`, `:82`, `:103`, `:124`, `:160`, `:177`, `:198`, `:231`, `:267`) and none of them is an inheritance function, and every grapple movement path establishes only the pair's own mutual link: `_do_advance_move` in `world/combat/movement_resolution.py` after a drag-advance, and `add_combatant` in `world/combat/utils.py` after a cross-handler drag through an exit. A same-room `advance` establishes the advancer↔target link alone (`_resolve_advance_same_room`) and never reads the grappled victim at all. So a dragged victim arrives in melee with their grappler and nobody else.
>
> This is the one Phase 1 item that was never built, so the status banner's "Phase 1 complete" is not earned on it. Whether the behaviour is still wanted, or was abandoned in favour of the pair-only proximity the drag and advance paths establish today, is an open owner question.

---

## Special Actions

### Escape Grapple: `escape`

#### **Mechanics**
- **State Change**: Victim switches from yielding to non-yielding
- **Immediate Effect**: Violent mode engaged
- **Contest**: Handled on next combat round
- **Targeting**: Auto-target grappler for retaliation

#### **Outcomes**
- **Success**: Break free, remain in proximity, target grappler
- **Failure**: Remain grappled but now in violent mode

### Release Grapple: `release`

#### **Mechanics**
- **Voluntary Action**: Grappler chooses to let go
- **No Contest**: Automatic success
- **State Preservation**: Yielding states maintained
- **Proximity**: Both remain in proximity
- **Messaging**: The `release` bank's two variants, since 2026-09-18 (#3427) — see §Grapple Messaging. That bank narrates a *chosen* release only; a hold ended by a charge, a gap jump or a blast draws on the five `release_*` phases #3615 added, or on `release_edge` (#3668), instead

#### **Strategic Use**
- **De-escalation**: Peaceful resolution option
- **Tactical**: Free up for other actions
- **Roleplay**: Character development opportunities

---

## State Management

### Database Fields

#### **Combat Entry Fields**
```python
{
    "char": Character object,
    "grappling_dbref": int or None,      # Who this character is grappling
    "grappled_by_dbref": int or None,    # Who is grappling this character
    "is_yielding": bool,                 # Yielding state
    "target_dbref": int or None,         # Combat target
    # ... other combat fields
}
```

#### **Validation Rules**
1. **Mutual Exclusivity**: Can't grapple multiple people
2. **Relationship Consistency**: Cross-references must match
3. **Combat Participation**: All grapple participants must be in combat
4. **Proximity Requirement**: Grappling requires proximity

### State Cleanup System

#### **Automatic Validation** (`validate_and_cleanup_grapple_state`)
- **Stale References**: Remove references to non-existent characters
- **Cross-Reference Validation**: Ensure bidirectional consistency
- **Combat State Sync**: Align with combat handler state
- **Self-Grapple Prevention**: Block impossible relationships

#### **Cleanup Triggers**
- At the start of every combat round
- Whenever a combatant is added

It is not run on removal or at handler shutdown; other cleanup handles those.

#### **What it clears**
- References to deleted characters, and self-grapples
- Holds on or by anyone not in the fight, dead, or in another room
- A victim whose `grappled_by` names someone who is not holding them loses it; a grappler's `grappling` is copied onto a victim whose `grappled_by` does not match it. The grappler's field is the one source of truth (#2486)

---

## Integration Points

### Combat System Integration

#### **Handler Processing Order**
1. **Validation**: Grapple states are validated once (`validate_and_cleanup_grapple_state`)
2. **Turns in initiative order**: Each combatant then acts in turn:
   - A yielding character can only release, advance, retreat or charge; anything else spends the turn
   - A held, non-yielding character spends the turn on the auto-escape contest
   - Everyone else runs their queued action (grapple, takeover, join, release, movement) or attacks

`escape` is not a queued action: it only makes the victim non-yielding, so the contest is their next turn's auto-escape.

#### **Action Restrictions**
- **Being Grappled**: Limited to escape, talk, yielding actions
- **Grappling Someone**: Can advance/retreat (with victim), limited other actions
- **Attack Restrictions**: Can't attack your grappler while being grappled

### Proximity System Integration

#### **Establishment Rules**
- **Grapple Creation**: Always establishes proximity
- **Maintenance**: Grappling maintains proximity automatically
- **Release**: Proximity persists after grapple ends
- **Movement**: Proximity inherited during movement

#### **Movement Interactions**
- **Room Changes**: Drag system handles proximity transfer
- **Within Room**: Advance/retreat maintains grapple proximity
- **Multiple Targets**: Victim gains grappler's proximity to others

> **Re-verified 2026-09-11 — two of these bullets restate the unbuilt proximity inheritance.** "Proximity inherited during movement" and "Victim gains grappler's proximity to others" describe no shipped code; see the Proximity Inheritance note under Movement Integration for the searches that prove the absence. What ships is pair-only: a drag re-establishes grappler↔victim and nothing else (`_do_advance_move` in `world/combat/movement_resolution.py`, `add_combatant` in `world/combat/utils.py`).
>
> The rest of this section holds. Release leaves proximity standing — `resolve_release_grapple` (`world/combat/grappling.py`) clears the two grapple fields and never touches the proximity sets. Retreat deliberately keeps the victim link while breaking every other one (`resolve_retreat`), and a room-change drag re-establishes the pair in the new room (`_do_advance_move`).

### Yielding System Integration

#### **State Relationships**
- **Default Grappler**: Auto-yields (restraint intent)
- **Default Victim**: Remains non-yielding (resistance mode)
- **Manual Override**: Both can change yielding state independently
- **Escalation**: Non-yielding victims auto-attempt escape

#### **Combat Mode Interactions**
- **Peaceful Mode**: Both yielding, no auto-resistance
- **Mixed Mode**: Yielding grappler, non-yielding victim
- **Violent Mode**: Neither yielding, active struggle

---

## Implementation Priorities

### High Priority ✅ **COMPLETED**

1. **Multi-Grapple Chain Logic**: ✅ **COMPLETED**
   - ✅ Fix scenario where C tries to grapple A (who is grappling B)
   - ✅ Implement forced release mechanism  
   - ✅ Test edge cases thoroughly

2. **Proximity Inheritance**: ✅ **COMPLETED**
   - ✅ Implement victim proximity copying during grappler movement
   - ✅ Ensure consistency across advance/retreat/charge
   - ✅ Handle multi-character scenarios

   > **Re-verified 2026-09-11: none of these three shipped.** There is no proximity-copying code anywhere — see the Proximity Inheritance note under Movement Integration above for the searches that prove the absence. The consistency and multi-character items are consequences of a mechanism that was never written, so all three ✅ marks rest on nothing.

3. **Human Shield System**: ✅ **COMPLETED**
   - ✅ Add bodyshield mechanics to attack resolution
   - ✅ Implement shield chance calculation
   - ✅ Add shield-specific messaging system
   - ✅ Integrate with existing combat damage flow
   - Grenade explosion human shield: built as a fixed split (grappler ×0, victim ×2), not the probabilistic proposal; see §Grenade Bodyshield System

4. **Advance While Grappling**: ✅ **COMPLETED**
   - ✅ Add grapple check to advance command
   - ✅ Implement victim dragging during advance
   - ✅ Maintain grapple state through movement

### Medium Priority

5. **Retreat Grapple Logic**: ✅ **COMPLETED**
   - ✅ Add grapple awareness to retreat command
   - ✅ Implement victim dragging during retreat
   - ✅ Ensure proximity maintenance

6. **Enhanced Contest System**:
   - Add modifiers for different situations
   - Implement fatigue mechanics for extended grapples
   - Add environmental factors

7. **Grenade Human Shield Integration**:
   - Integrate grappling-based blast shields with grenade explosions
   - Implement damage absorption mechanics (victim takes grappler's damage + own)
   - Add explosive-specific shield chance calculation (reduced effectiveness)
   - Create dramatic explosive-specific messaging system
   - Balance tactical opportunity with moral consequences

### Low Priority

8. **Advanced Grapple Moves**:
   - Submission attempts
   - Position-based modifiers
   - Team grappling mechanics

9. **Grapple Specialization**:
   - Character-specific grappling styles
   - Equipment modifiers
   - Training-based improvements

---

## Edge Cases and Considerations

### Multi-Character Scenarios

#### **Chain Grapples**
- **A→B→C**: Multiple dependency chains
- **Circular References**: Prevention and detection
- **Cascade Releases**: When one grapple affects others

#### **Team Grappling**
- **Multiple Grapplers**: Two people trying to grapple same target
- **Assistance**: Helping teammate with grapple
- **Interference**: Attacking grappling pairs

### Room Transition Edge Cases

#### **Handler Boundaries**
- **Cross-Handler Grapples**: When characters end up in different handlers
- **Handler Merging**: When grapple brings handlers together
- **Handler Cleanup**: When handlers shut down during grapples

#### **Movement Restrictions**
- **Yielding Requirements**: Room traversal requiring victim consent
- **Failed Drags**: What happens when drag fails
- **Escape During Movement**: Mid-transition escapes

### Error Recovery

#### **State Corruption**
- **Orphaned References**: Cleanup strategies
- **Inconsistent States**: Recovery mechanisms
- **Data Loss**: Graceful degradation

#### **System Failures**
- **Handler Crashes**: Grapple preservation
- **Network Issues**: State synchronization
- **Resource Limits**: Performance under load

---

## Testing Scenarios

### Basic Functionality
1. **Simple Grapple**: A grapples B successfully
2. **Grapple Failure**: A fails to grapple B
3. **Escape Success**: B escapes from A
4. **Escape Failure**: B fails to escape from A
5. **Voluntary Release**: A releases B voluntarily

### Contest Scenarios
6. **Grapple Contest**: A grapples B, C contests for B
7. **Chain Grapple**: A grapples B, C grapples A
8. **Multiple Contesters**: A grapples B, both C and D contest

### Movement Integration
9. **Room Drag Success**: A drags B to new room
10. **Room Drag Failure**: B resists A's drag attempt
11. **Advance While Grappling**: A advances to C while holding B
12. **Retreat While Grappling**: A retreats while holding B

### Edge Cases
13. **Handler Transitions**: Grapple across room boundaries
14. **Combat Initiation**: Grapple starting new combat
15. **State Corruption**: Recovery from invalid states
16. **Multi-Grapple Chains**: Complex relationship webs

---

## Conclusion

The G.R.I.M. Grappling System provides a sophisticated, roleplay-focused framework for close combat scenarios that emphasizes restraint while maintaining tactical depth. The system's integration with movement, proximity, and yielding mechanics creates a cohesive combat experience that serves narrative goals while providing meaningful strategic choices.

The specification identifies key implementation gaps that need addressing to complete the system's vision, particularly around proximity inheritance and multi-grapple scenarios. Once these elements are implemented, the grappling system will provide a robust foundation for complex, engaging combat encounters that prioritize character development and story progression.

## Implementation Roadmap

### Phase 1: Core Fixes (High Priority) ✅ **COMPLETED**
- ✅ Fix multi-grapple chain logic
- 📋 UNBUILT: Implement proximity inheritance (see the note under §Proximity Inheritance; open on #3285)
- ✅ Add advance-while-grappling support
- ✅ Implement human shield system
- ✅ Complete retreat-while-grappling logic

### Phase 2: Enhancement Features (Medium Priority)  
- Enhanced contest system with modifiers
- Environmental factors integration
- Performance optimization

### Phase 3: Advanced Features (Low Priority)
- Specialized grapple moves
- Character customization
- Team grappling mechanics

This roadmap shows the grappling system has achieved its core functionality goals, with Phase 1 completely implemented. The system now provides a robust foundation for complex, engaging combat encounters that prioritize character development and story progression.
