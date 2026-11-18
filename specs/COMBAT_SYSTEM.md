# G.R.I.M. Combat System Documentation

## Overview

The **G.R.I.M. Combat System** is a roleplay-focused, turn-based combat engine that emphasizes both violent and non-violent conflict resolution. It is built around four character attributes (Grit, Resonance, Intellect, Motorics) and supports complex tactical scenarios while keeping the focus on the narrative. The combat code lives in `world/combat/` and `commands/combat/`.

## Core Attributes - The G.R.I.M. System

### **Grit** - Physical Foundation

As a character concept, Grit is physical toughness and endurance, willpower and mental fortitude. That framing is flavour, not a mechanic.

What Grit does in play:
- **Disarm contest**: grit vs grit (`resolve_disarm` in `world/combat/actions.py`).
- **Drag contest**: the grappler's grit against the victim's when a grappler moves with a held victim (`_resolve_advance_cross_room` in `world/combat/movement_resolution.py`, `Exit.at_traverse` in `typeclasses/exits.py`).
- **Vital targeting**: grit + motorics sets how well an attacker aims at vital areas (`select_hit_location` in `world/medical/utils.py`).

`world/manifest.py` maps the melee, unarmed and athletics skills onto Grit, but those skills are a creation-time snapshot that nothing rolls (see that module's docstring).

Grit drives no health pool, no damage resistance and no recovery. There is no character-level hit-point stat: health is the organ-based medical model (`class Organ` in `world/medical/core.py`, per-organ HP), and damage mitigation is armor (`_calculate_armor_damage_reduction` in `typeclasses/armor_mixin.py`, called from `take_damage`). `world/combat/constants.py` declares `DEFAULT_HP = 10` and `HP_GRIT_MULTIPLIER = 2` under a `# Health system` heading; neither name is read anywhere in the repo.

### **Resonance** - Social Awareness

As a character concept: empathy and emotional intelligence, social awareness and reading people, communication and persuasion, conflict de-escalation.

Combat never reads Resonance. Under `world/combat/` it exists only as `STAT_RESONANCE` (`world/combat/constants.py`) and a descriptor-table entry, and it does not appear under `commands/combat/`. Its live uses are outside combat, in perception and recognition: stealth detection (`contest`, `active_search` and `search_hidden_exits` in `world/stealth.py`) and identity, voice and radio recognition (`attempt_disguise_pierce` in `world/identity.py`, `attempt_voice_discern` in `world/voice.py`, `_mutter_into` in `world/radio.py`). The "sensing intentions" side of Resonance is in play; there is no social-combat resolver.

### **Intellect** - Mental Acuity
- **Problem-solving** and tactical thinking
- **Pattern recognition** and analysis
- **Memory** and knowledge retention
- **Strategic planning** abilities

*Used for: Combat tactics, understanding complex situations, learning*

### **Motorics** - Physical Coordination
- **Dexterity** and hand-eye coordination
- **Reflexes** and reaction time
- **Balance** and physical grace
- **Fine motor control** for precise actions

*Used for: Attack accuracy, dodging, weapon handling, escape attempts*

## Combat Mechanics

### Turn-Based System
- **Initiative Order**: rolled once when a combatant is added (formula under Configuration).
- **Action Economy**: each character gets one primary action per turn.
- **Reaction System**: defensive actions and responses to attacks.
- **Round Structure**: clear turn order with automatic progression.

#### **Round Timing**
- **6-Second Rounds**: each combat round is 6 seconds of in-game time (`COMBAT_ROUND_INTERVAL = 6`).
- **Staggered Attacks**: attacks are staggered within each round so messages do not spam:
  - The first attacker executes as the round begins.
  - Each later attacker is delayed a further 1.5 seconds (`STAGGER_DELAY_INTERVAL = 1.5`).
  - The delay is capped at 4.5 seconds (`MAX_STAGGER_DELAY = 4.5`) so every attack completes before the next round.
- **Instant Actions**: some actions (flee, jump) bypass the round system, for emergencies.
- **Turn-Based Actions**: most tactical actions (advance, retreat, charge, disarm) are queued for the next round.

All timing values are set in `world/combat/constants.py`.

### Proximity-Based Engagement

#### **Melee Range**
- **Close Combat**: hand-to-hand, melee weapons, grappling.
- **Proximity Required**: a character must be in melee range to engage.
- **Movement Costs**: advancing and retreating affect the action economy.
- **Weapon Restrictions**: some weapons require specific ranges.

#### **Ranged Combat**
- **Shooting**: firearms, bows, thrown weapons.
- **Line of Sight**: a clear path is required for ranged attacks.
- **No cover**: nothing about the room, an object or terrain reaches the hit math. The to-hit roll (`process_attack` in `world/combat/attack.py`) takes no term derived from the room or its contents. (The only "cover" in `world/combat/` is clothing coverage and two flee messages about covered exits, `MSG_FLEE_ALL_EXITS_COVERED` and `MSG_FLEE_PARTIAL_SUCCESS` in `world/combat/constants.py`.)
- **Ammunition**: limited shots require tactical resource management 📋 UNBUILT (no issue)

### Grappling System

#### **Restraint Mode** (Default)
- **Who yields**: in a contested grapple only the grappler is set yielding. `resolve_grapple_initiate` in `world/combat/grappling.py` leaves the victim non-yielding so the victim auto-resists every turn (this matches `GRAPPLE_SYSTEM_SPEC.md`). Because `escape`'s "you switch to violent struggle" message fires only if the victim *was* yielding (`CmdEscapeGrapple` in `commands/combat/special_actions.py`), it never appears in a contested grapple.
- **Both yielding**: reachable in two ways: the victim chooses it, or the hold is consensual (#3363, owner ruling 2026-09-13). If the target trusts the grappler for `grab`, or cannot contest (unconscious, dead or already restrained), the hold is taken with no roll and both parties are set yielding, so nobody struggles.
- **Gentle Hold**: the grappler maintains control without harm.
- **Peaceful Resolution**: the preferred method for conflicts.
- **De-escalation**: allows for roleplay and negotiation.

#### **Violent Mode** (Escalation)
- **Active Resistance**: the victim chooses to fight back.
- **Escape Attempts**: violent struggles to break free.
- **Damage Potential**: the struggle can cause harm.
- **Last Resort**: when peaceful resolution fails.

### Yielding Mechanics

#### **Yielding State**
- **Non-Violent**: the character chooses not to fight.
- **Peaceful Stance**: attempts to de-escalate the conflict.
- **Defensive Only**: no aggressive actions taken.
- **Roleplay Focus**: emphasis on character interaction.

#### **Active Combat**
- **Aggressive Stance**: the character fights actively.
- **Full Actions**: all combat options are available.
- **Tactical Depth**: complex combat maneuvers are possible.
- **Consequence Awareness**: higher stakes and risks.

## Command Structure

### Core Actions (`commands/combat/core_actions.py`)
- **`attack <target>`** (alias `kill`): initiate or continue combat.
- **`stop attacking`**: cease aggressive actions, enter the yielding state.
- **`stop aiming`**: drop your aim at a target or a direction.
- **`stop`** (bare): abort a channeled act in progress.

### Movement Commands (`commands/combat/movement.py`)
- **`flee`**: attempt to escape combat entirely (once per round, instant execution).
- **`retreat`** (alias `disengage`): back away from melee range (same room).
- **`advance <target>`** (alias `engage`): close distance for melee combat.
- **`charge <target>`** (alias `rush`): reckless rush attack with bonuses and penalties.
- **`jump off <direction> edge`** / **`jump across <direction> edge`** (`commands/combat/jump.py`, also `jump on <explosive>`): go over an edge or across a gap on purpose; in a fight it pays both of flee's contests (below).

#### Refused at the edge (#3583, owner ruling 2026-09-16)

None of the three room-changing movement commands takes a body over a drop. `flee`, `advance` and `charge` all filter their exit pool through one predicate, `can_leave_by(mover, exit)` in `world/gravity.py`. It fails an exit that is an edge (`db.is_edge`), a gap (`db.is_gap`) or that leads into an air cell, unless the mover's `db.stays_aloft is True`. The predicate lives in the gravity module rather than in combat because it is the same question gravity asks everywhere else, and because combat movement relocates with `move_to` and so never reaches the refusal in `Exit.at_traverse` that already stops walking. `advance` (`world/combat/movement_resolution.py`) and `charge` keep the rejected exit so they can say why: *"The only way to X is over the N edge — that is a jump, not a charge."* Going over the edge is a deliberate act with its own verb and its own consequences (`specs/JUMP_COMMAND_SPEC.md`), never something a movement command does to you.

Owner: *"It would be refused at the edge… Ideally, very few rooftops will exist without exits though — so ending up on one where all you can do is jump is a tactical challenge."* A roof with nothing but edges is therefore a designed predicament, not a bug; see `specs/PARKOUR_TEMPLATE_LIBRARY.md` §1.5.

- **The edge question comes first.** `advance` asks `can_leave_by` BEFORE it rolls the grapple drag-resist contest (`world/combat/movement_resolution.py`), so a grappler who cannot go that way never drags their victim into a roll that would be thrown out.
- **The flags are read strictly.** `can_leave_by`, the jump verbs (`exit_obj.db.is_edge is not True` / `is_gap is not True`) and the edge/gap block in `Exit.at_traverse` (`is_edge = self.db.is_edge is True`) all require a literal `True`. A truthy-but-not-True attribute left on an exit by an old build script does not make it an edge in one place and a plain exit in another.
- **Souls ask the same predicate.** An NPC soul's `flee` job (`world/souls/jobs.py`) filters its exits through `can_leave_by` and reports "cornered — nowhere to flee" when none survive, so an NPC will not walk itself off a roof to escape.

#### The price of leaving a fight: flee and the jump verbs

Leaving a fight has two prices, and `flee` and the jump verbs charge both by exactly the same rules, through shared helpers in `commands/combat/movement.py`:

- `break_aim_lock(caller, *, bonus=0, label=None, immediate_attack=False)`: the Motorics-vs-Motorics roll that breaks an aimer's lock, with the aimer's opportunity attack on a loss, resolved at once when `immediate_attack` is True (the jump verbs).
- `roll_to_disengage(caller, handler, *, bonus=0, label=None)`: the Motorics-vs-Motorics roll against the best-Motorics opponent targeting you, ties to the blocker, with that blocker's opportunity attack on a loss.

**The opponent need not be in your room: suppressive fire, by design (owner 2026-09-16).** `opponents_targeting` takes every combatant in the merged fight whose target is you, wherever they stand. Someone being shot from a rooftop (#3589) still rolls against the shooter's Motorics to get off the street, and a loss reads "blocked by their opponents" with nobody beside them. Owner: *"That is the intended function. It would be suppressive fire pinning someone down."* The pin is the **constant attacking**, not the bullets: when ammunition exists, it is the attacker's willingness to keep firing every round that holds the target, and running dry ends the pin because the attacks stop, not because a counter did. This is a purely thematic and gameplay justification, and the intended one: do not "fix" the roll to filter by room.

**The gates come before the price (#3685, #3687; owner 2026-09-29: "That makes sense.").** A leave that cannot happen costs nothing. Each verb asks its own gates first, running the game's own refusals so they speak for themselves: the channel gate (`refuse_if_channeling`), a hold on the fleer, and an escortee the usher would walk at an exit that refuses every walker (`escort_barred_at`, then the real `usher_escortee`). Only then is the round's flee attempt counted (a refused flee is no attempt, so it cannot spend a token no round would clear), and only then are the contests paid. The move is made before combat is left, and the fight lets go of the fleer in the room it was in (`remove_combatant(..., room=)`), not the one they ran to. A refused move leaves the body where and as it was and says nothing of a flight that did not happen. One thing does end before the move, after the price: a march of the very victim the fleer holds, which the flight gives up (as the gap jump does, #3684).

**The opportunity attack.** Both losses go through one shared helper, `opportunity_attack(attacker, target, *, immediate=False)`, which runs a real `attack` against the RESOLVED target (#1002). For a jump it is resolved immediately; for a flee, on the next round (#3593). `CmdAttack.func` only ENROLS: it puts the attacker in the handler with the target and prints the weapon's initiate line, and the shot fires on the handler's next round. That is enough for a blocked fleer, who is still standing there when the round comes, but a jumper is out of the handler and off the roof inside the same command. So under `immediate=True`, `opportunity_attack` calls `world.combat.utils.resolve_bonus_attack(handler, attacker, target)`, the same helper that hands a ranged defender an immediate attack when an advance or a charge at them fails. It does the combat-entry lookup and the `process_attack` itself, with its own guards (a dead or unconscious target, melee reach, proximity). One immediate-attack implementation, three doors: a failed advance, a failed charge, and a jumper who lost a leaving contest. `break_aim_lock` forwards the flag as `immediate_attack`, and the jump verbs pass True on both halves.

**The jump verbs' bonus and label.** The jump verbs pass `bonus=JUMP_AWAY_BONUS` (20) to both rolls and `label="JUMP_AWAY"` to both. The label only re-prefixes the splattercast lines, so a jump logs `JUMP_AWAY_` rather than `FLEE_`.

**The consequence of a lost roll is where the two verbs part (#3591, ruled 2026-09-16).** A jump in a fight pays BOTH halves of flee's price, the aim contest (`break_aim_lock`) AND the melee disengage roll (`roll_to_disengage`), with the bold-move bonus on both, for both `jump off` and `jump across`. Flee keeps its own consequence: a lost disengage blocks the flee outright and sets `NDB_SKIP_ROUND`. A jump is never refused and never costs a round: a lost disengage hands the blocker an immediate attack ("catches you as you break for the edge"), the jumper reads *"You throw yourself at the edge regardless."*, and only being left dead or unconscious stops the departure. See the jump spec's "Fights at the edge" block.

#### A deleted target is not a relationship (#3568 / #3569, 2026-09-17)

Owner: "shouldn't happen in actual combat but addressing it makes sense … one of those things that should be logged".

- The orphan sweep (`detect_and_remove_orphaned_combatants`) resolves each recorded `target_dbref`. A target that no longer exists is cleared on the stored entry, a `TARGET_GONE` splattercast line and a `logger.log_warn` are emitted, and the combatant is told *after* the sweep has decided their fate: "Your target is no longer there." if they are leaving with it, "… Choose a new target if you wish to continue fighting." if someone still holds them in.
- A queued `advance` / `charge` / `disarm` reads its target through one resolver, `queued_action_target`, which tells a missing key (the player gave no target: the old message) from a key holding `None` (the target was deleted between rounds: "Your target is no longer there.", logged). The sweep drops such an action when it clears the target, so one deletion reports once.
- `at_repeat` re-reads the round snapshot after the sweep every time (#2422).
- The death path clears targets before a body is deleted, so the warning means a builder's or a system's deletion, never a kill.
- **The row never goes stale (#3555, 2026-09-19).** `Character.at_object_delete` removes the character from every active handler that lists it, through `remove_combatant`, before the object goes: whoever was targeting them is told and re-pointed at once, and no deserialised-to-None row is left for the rest of the round. As a second guard, the retarget candidate scan in `remove_combatant` skips a row whose character is gone, as its two sibling loops do. This is the #3552 delete-hook pattern, applied to fighters.

#### A body does not square up when its target leaves (#3347, 2026-09-18)

When a combatant leaves the fight through `remove_combatant` (every door: the end-of-round sweep, the attack path's kill, flee, the jump verbs, a dragged traversal, the deferred knockout ejection, the orphan sweep), everyone who was targeting them is re-pointed at someone who is targeting *them* and announced with the weapon's initiate pose. That is the auto-retarget, and this section is its only description. The announcer is checked the way #1584 checks the target on the attack command's side: a dead or unconscious combatant gets no new target and says nothing; the sweep ejects them. The announcement reaches the announcer, the new target and the room (#3620).

Three things put a dead or unconscious body in that loop:
- A knockout in combat does not eject on the hit: `_handle_unconsciousness` defers the message and the ejection behind a five-second timer (nothing in combat clears `unconsciousness_pending`), and the round is six seconds, so a fighter knocked out mid-round is enrolled and unconscious for the rest of it. Two knockouts in one round, one targeting the other, is the common case.
- Death does not eject a combatant at all (only the attack path's kill and the sweep do), so anyone killed by a fall, a grenade, a blast or a bleed-out on the medical tick is still enrolled until the end of the round.
- A body knocked out before it was attacked is enrolled with its attacker as its target.

**A hold is a hold (#3622, owner ruling 2026-09-18):** a yielding survivor is not re-pointed and not un-yielded. They are told who left, who is still targeting them, and that yielding means not fighting back ("use 'attack' or 'kill' to resume malicious intentions"). The orphan sweep lets them out if nobody is on them, and their own next `attack` names the target. Un-yielding them here would be the system un-yielding someone for a reason not their own: it would break a `stop` when a third party left, and turn a consensual hold into a struggle (the held person's flag drives the shield chance and the every-round auto-escape).

### Special Actions (`commands/combat/special_actions.py`)
- **`grapple <target>`**: attempt to grab and restrain the target.
- **`escape`**: break free from a grapple (switches to violent mode).
- **`release`**: let go of the grappled target.
- **`disarm <target>`**: attempt to remove the target's weapon.
- **`aim <target>`** / **`aim <direction>`** (`CmdAim`): a positioning tool: lock, tell, cross-room fire, flee-punish. It grants no accuracy. `help aim` says so ("Aiming does not improve your accuracy").
  - *Overturned intention:* this command was documented as "Improve accuracy for next attack". **Owner ruling 2026-09-13 (#3355): the promise is withdrawn.**
  - The to-hit roll in `process_attack` (`world/combat/attack.py`) is `effective_skill = attacker_skill * sight_factor * manip_factor * grip_factor`, `randint(1, 20) + effective_skill`, plus the weapon choice's `hit_bonus` and the one-shot charge bonus. It never reads `NDB_AIMING_AT`.
  - What aiming buys: the target is held in place; a visible tell is posted; `aim <direction>` unlocks cross-room fire through that exit (`CmdAttack.func` in `commands/combat/core_actions.py`); the aimer gets an opportunity attack if the aimed-at target flees (`break_aim_lock`, above); aiming at someone reveals the aimer (#3769).

#### Directional attacks resolve through `room_through` (#3589, owner ruling 2026-09-16)

`aim <direction>` + `attack` does not fire into whatever room the exit happens to point at. `commands/combat/core_actions.py` asks `world.gravity.room_through(exit_obj)` for the room the aim really reaches: over an **edge** (or any exit into air) that is the ground the edge drops to, not the empty air cell; across a **gap** it is the far perch; anywhere else it is just the destination. Owner: *"Aiming at an edge typically means aiming at the ground area it drops to because of sniping. Rooftop to street for example."*

- The ground is found by `ground_below`, which takes the **highest non-air room in the same column below**, read off `world/spatial`'s `coordinate_index()` (the one cell-addressed lookup in the game), with no cell limit and no floor at z=0 (the Drifts resolve downward past zero). It falls back to the `down` exit chain only off-grid or where the grid has nothing seeded below. So a shot over a parapet works whether or not anyone wired the column: **geometry wins over wiring**, and a bare column (#3581) still resolves the shot to the seeded street even though a fall down it parks in mid-air.
- Two `None` cases refuse the shot with *"You are aiming `<dir>`, but there's nothing down there to hit."*: nothing solid below at all; and the **occlusion rule**, where a room below that is not a surface (`is_surface`: a rooftop or `outside is True`) means an unbuilt roof is in the way.
- The aiming **look** and its aimed-room target search resolve the same way (`typeclasses/rooms.py`), falling back to the air cell so a bare column still renders. Throw's `at` form resolves the same way too, while its directional forms still fly into the air cell so gravity carries the object down.
- Upward (street → roof) aiming is unbuilt and parked with Phase 3 (#1511): no exit to aim through, no line-of-sight concept. The asymmetry only constrains who can OPEN: the attack command enrols the victim with the shooter as target, so from the next round a street target with a ranged weapon fires back at the roof, needing neither an aim nor an exit, **by design** (owner 2026-09-16: *"Automagic self-defense and the perk of carrying a gun."*). With a melee weapon the round's attack is refused across rooms (*"You can't reach … from here."*) and `advance`/`charge` find no way up.
- Aiming widens no other command's search (#3596). Only `look` (`commands/CmdLook.py`), `attack` and `throw ... at` reach into the aimed room.

Full contract: `specs/JUMP_COMMAND_SPEC.md`, "Aiming over an edge (#3589)".

### Information Commands (main character cmdset)

There is no dedicated combat info-command module. Combat-aware `look` comes from the main character cmdset, so it works both in and out of combat.
- **`look`**: enhanced awareness during combat (`commands/CmdLook.py`, the game's subclass of Evennia's `CmdLook`, added in `commands/default_cmdsets.py`). While you aim down an exit, `look` shows the aimed room and `look <target>` searches it before your own surroundings (#3596).

## Combat Flow

### 1. **Initiation**
- Player A attacks Player B.
- A combat handler is created.
- Attacker and target are added, each rolling initiative once.
- Both players enter combat state.

### 2. **Turn Processing**
- Every 6 seconds the handler runs one round.
- Orphan sweep: fighters who are gone or outside the fight's rooms are dropped.
- Everyone yielding and no grapple: peaceful end.
- Each fighter in initiative order: a queued action (grapple, release, advance, retreat, charge, disarm) runs; otherwise an attack is scheduled, staggered 1.5 s apart.
- Dead or unconscious fighters are removed.
- One fighter or none left: combat ends.

### 3. **Resolution**
- All players yielding: peaceful end.
- One player defeated: combat victory.
- All players flee: combat dispersed.
- Handler cleanup and state reset.

## Tactical Features

### Multi-Room Combat
- **Room Transitions**: combat can span multiple locations.
- **Ranged Coverage**: archers can control exits.
- **Tactical Positioning**: room layout affects combat options, but only through exits and multi-room handler management (`DB_MANAGED_ROOMS`), not through any terrain property.
- **No environmental factors**: no weather, terrain or lighting term reaches any combat roll (see Unbuilt).

### Weapon System
- **Weapon Types**: melee, ranged, thrown, improvised.
- **Which weapon swings**: one resolver, `choose_weapon` in `world/combat/weapon_choice.py`, answers for every reader (the swing, the reach gates, the initiate prose, aim, flee). Deployed natural weapons (claws) that can reach come first, then held weapons; tagged weapons push out untagged items; a target out of reach leaves only ranged options; two of one weapon type with an akimbo profile fight as one attack; each attack takes the next option that can reach. Detail: `specs/proposals/MULTI_WEAPON_COMBAT_SPEC.md`, `specs/proposals/GRIP_ENFORCEMENT_SPEC.md`.
- **Weapon Stats**: weapons carry `db.damage` (read via `get_weapon_damage` in `world/combat/utils.py`, and by `world/combat/weapon_choice.py` for the swing) and `db.is_ranged`. There is no per-weapon accuracy stat, only a small to-hit term:
  - A single held weapon adds nothing to the roll unless its `db.hit_bonus` is set (0 when unset, read by `world/combat/weapon_choice.py`); no prototype sets `hit_bonus` on a single weapon.
  - An akimbo pair's profile in `AKIMBO_PROFILES_BY_TYPE` adds +1 or -1.
  - A two-handed weapon without a free second hand rolls at reduced skill (`grip_hit_factor` in `world/combat/capacity.py`).
  - Otherwise the roll is the attacker's motorics, sight and manipulation (`process_attack` in `world/combat/attack.py`).
  - Thrown objects: `world/combat/throwing.py` flat-rates a 70% hit chance, under the comment "could be enhanced with accuracy system".
- **Ammunition**: limited resources for ranged weapons 📋 UNBUILT (no issue)
- **Durability**: weapons can break or become damaged 📋 UNBUILT (no issue)

### Status Effects
- **Grappled**: restricted movement and actions.
- **Aimed**: the aimed state (`NDB_AIMING_AT` / `NDB_AIMED_AT_BY`, set by `CmdAim`) immobilises the target, posts the visible tell, enables cross-room fire, and buys an opportunity attack on a flee attempt. It confers no accuracy bonus, by decision (owner ruling 2026-09-13, #3355). The state persists INTO combat: it is cleared on `aim stop`, on the aimer moving, or on leaving combat, and is not dropped when combat starts.
- **Yielding**: non-violent stance with limited options.
- **Wounded**: injury effects on performance.
- **Hidden** (`world/stealth.py`): opening an attack on a target who cannot perceive you is an ambush: "You strike from concealment!", a first-strike initiative bonus (`AMBUSH_INITIATIVE_BONUS`), and the attack reveals you. Aiming at someone reveals the aimer (#3769). Nobody can hide while in a fight or with a weapon aimed at them (#3763), and an untargeted throw never lands on someone the thrower cannot perceive. Detail: `specs/proposals/STEALTH_AND_DETECTION_SPEC.md`.

## Roleplay Integration

### Narrative Focus
- **Rich Messaging**: detailed, contextual combat descriptions.
- **Emotional Context**: messages reflect character motivations.
- **Consequence Awareness**: actions have meaningful narrative impact.
- **Story Enhancement**: combat serves the story, not vice versa.

### Non-Violent Resolution
- **Default Yielding**: peaceful resolution is preferred.
- **De-escalation**: multiple opportunities to avoid violence.
- **Restraint Options**: subdue without permanent harm.
- **Peaceful end**: when every combatant is yielding and no grapple is active, the handler ends the fight peacefully (`_check_peaceful_resolution` in `world/combat/handler.py`). That is a state check, not a Resonance contest; no social-combat resolver exists (see Unbuilt).

### Character Development
- **Skill Progression**: combat experience improves abilities (see Unbuilt).
- **Reputation System**: combat actions affect social standing (see Unbuilt).
- **Psychological Impact**: violence has emotional consequences.
- **Relationship Dynamics**: combat affects character relationships.

## Technical Implementation

### State Management
- **Handler DB state**: who targets, grapples or yields to whom, initiative and queued actions, held in the handler's `db.combatants` (survives a reload).
- **NDB Attributes**: temporary combat state (proximity, aim, the handler pointer), cleared by a reload. At start-up `server/conf/at_server_startstop.py` re-links the handler pointer and same-room melee proximity for live fights, and clears stranded aim tells rather than restoring aim.
- **DB Attributes**: persistent character data (stats, equipment, etc.).
- **Handler Persistence**: combat state survives server restarts.
- **Cleanup Systems**: automatic state cleanup when combat ends.

### Performance Considerations
- **Efficient Algorithms**: optimized for multiple simultaneous combats.
- **Memory Management**: proper cleanup of temporary data.
- **Scalability**: handles large numbers of participants.
- **Error Handling**: robust error recovery and logging.

### Debug Infrastructure
- **Comprehensive Logging**: detailed debug information.
- **State Inspection**: tools for examining combat state.
- **Error Reporting**: clear error messages for players and developers.
- `world/combat/debug.py` is a single diagnostics sink (`get_splattercast`, `debug_broadcast`, `log_debug`, `log_combat_action`) plus the durable audit log described by `COMBAT_AUDIT_LOGGING_SPEC.md`. It emits no timing, counter or throughput metric, and nothing under `world/combat/` measures performance (see Unbuilt).

## Configuration

### Combat Constants (`world/combat/constants.py`)
- Default attribute values: `DEFAULT_GRIT = 1`, `DEFAULT_RESONANCE = 1`, `DEFAULT_INTELLECT = 1`, `DEFAULT_MOTORICS = 1`.
- Timing: `COMBAT_ROUND_INTERVAL = 6`, `STAGGER_DELAY_INTERVAL = 1.5`, `MAX_STAGGER_DELAY = 4.5`.
- `DEFAULT_HP = 10` and `HP_GRIT_MULTIPLIER = 2` are defined and never read anywhere (see Grit).

There is no initiative base, damage multiplier or grapple difficulty constant. The rules:
- **Initiative**: `randint(1, 20) + motorics + surplus_limb_initiative_bonus(char) + ambush_bonus`, rolled once when a combatant is added (`add_combatant` in `world/combat/utils.py`, where `surplus_limb_initiative_bonus` is also defined). `ambush_bonus` is `AMBUSH_INITIATIVE_BONUS` when the attacker opens on a target who cannot perceive them, else 0.
- **Damage**: `randint(1, 6)` base plus the weapon choice's damage (the item's `db.damage`, or an akimbo profile's figure for a pair), with no global multiplier (`process_attack` in `world/combat/attack.py`), then armor reduction in `take_damage` (`_calculate_armor_damage_reduction` in `typeclasses/armor_mixin.py`).
- **Grapple**: an opposed motorics contest, not a fixed difficulty number (`world/combat/grappling.py`).

### Message Templates
- **Action Messages**: descriptions of combat actions.
- **Result Messages**: outcomes of attacks and defenses.
- **State Messages**: changes in combat state.
- **Weapon Messages**: weapon-specific descriptions.

## Messaging

### Perspective
Combat messages use a three-message format (attacker / victim / observer), consistently across all weapon types, adapting to combat state and participant status:
- **First person**: attackers see "You draw your knife..." rather than the observer message.
- **Second person**: victims see "Nick prepares to strike you!" for direct engagement.
- **Third person**: bystanders see a third-person description.

### Dual Initiate
Combat initiation shows both an aggressive and a defensive stance:
- **Attacker initiate**: weapon-specific aggressive preparation.
- **Victim defensive**: an automatic defensive stance when surprised or not currently engaged.
- **Contextual triggers**: the defensive message appears only when the target is not already in combat or targeting, and is conscious and alive (#1584: a corpse should not square up). (`CmdAttack.func` in `commands/combat/core_actions.py`.)

### Automatic Colour Coding
Phase colouring is applied in `get_combat_message` (`world/combat/messages/__init__.py`):
- **Threat escalation**: red initiate → red hit → bold red kill. In Evennia lowercase `|r` is the HILITE (bold) red and uppercase `|R` the regular one; this is correct as it stands and is not drift.
- **Misses**: white for failed attempts.
- **Grapple lines**: green for a hold taken, released or broken free of; yellow for a hold that failed or is being lost.
- **Automatic application**: no manual colour coding is needed in weapon templates.
- **Override support**: pre-coloured messages are respected.

### Clean Narrative Flow
- **No entry/exit spam**: there is no "You enter combat!" or "You are no longer in combat!" message.
- **Weapon-focused**: combat flows directly from the weapon initiate to the action.
- **Natural transitions**: combat begins and ends with narrative actions, not system announcements.

### Death System Integration
- **Medical cause**: death messages reflect the actual medical cause ("Nick is dying from blood loss..."), from the medical system's analysis, with atmospheric fallback messages when no analysis is available.
- **Death curtain**: colour codes are parsed so the curtain centres correctly; the "lifeless body" message is suppressed so it does not conflict; messages flow cause → curtain → confirmation.
- **Ordering**: attack messages appear before damage and death; the death curtain gets uninterrupted control during its animation; bleeding messages are suppressed during death processing.
- **Coordination**: combat damage hands off to medical processing, and the death curtain is kept separate from medical ticker messaging; combat initiation and defensive states are tracked.

## Advanced Features

### Customization Options
- **House Rules**: server-specific combat modifications.
- **Weapon Varieties**: easy addition of new weapon types.
- **Special Abilities**: character-specific combat techniques.
- **Environmental Hazards**: location-based combat modifiers.

## Best Practices

### For Players
- **Roleplay First**: use combat to enhance story.
- **Consider Consequences**: actions have meaningful impact.
- **Communicate Intent**: clear communication prevents misunderstandings.
- **Respect Boundaries**: honor other players' comfort levels.

### For Developers
- **Maintain Modularity**: keep combat systems cleanly separated.
- **Document Changes**: update documentation with modifications.
- **Test Thoroughly**: ensure changes don't break existing functionality.
- **Preserve Philosophy**: maintain the roleplay-first approach.

### For Administrators
- **Monitor Balance**: ensure fair and engaging combat.
- **Handle Disputes**: mediate conflicts between players.
- **Maintain Standards**: enforce roleplay and conduct standards.
- **Support Community**: foster a positive gaming environment.

## Unbuilt

Described as part of the system, not built:
- **Ammunition**: limited shots, limited resources for ranged weapons; tactical resource management 📋 UNBUILT (no issue). See also "Not decided".
- **Weapon durability**: weapons can break or become damaged 📋 UNBUILT (no issue)
- **Skill progression**: combat experience improves abilities.
- **Reputation system**: combat actions affect social standing.
- **Upward aiming** (street → roof): parked with Phase 3 (#1511).
- **Cover system**: objects and terrain affecting accuracy.
- **Social combat**: Resonance-based conflict resolution.
- **Performance monitoring**: tracking system performance.

### Planned Enhancements
- **Formation Fighting**: group tactics and coordination.
- **Environmental Effects**: weather, terrain, lighting impact.
- **Equipment Durability**: weapon and armor degradation.
- **Combat Styles**: different fighting approaches and techniques.

## Not decided

- **Should the pin be ammo burn? (owner, 2026-09-16), open: revisit when ammunition is designed.** Today the ruling is "the pin is the constant attacking": a shooter holds a target by being enrolled against them round after round, and ammunition, once it exists, only sets how long that can last. The alternative is that suppression is what the bullets buy: the shooter spends rounds to pin without needing to hit, a dry gun pins nothing, and a loaded one pins whether or not a shot is fired that round. The two disagree on exactly one thing: whether an attacker who is enrolled but not firing (empty, jammed, reloading, a melee weapon in hand) still counts in `opponents_targeting` for the disengage roll. Under the current ruling they do. Do not build the ammunition system on either answer without asking; the owner flagged this as something they may change their mind on.
- **Unbuilt features with no issue.** Skill Progression, Reputation System, Psychological Impact, Relationship Dynamics, Combat Styles, Special Abilities, Environmental Hazards and Formation Fighting are described and were never built. Are they still wanted, each to be marked UNBUILT with an issue filed, or should they be deleted from the spec?

## Related documents

- `specs/GRAPPLE_SYSTEM_SPEC.md`: grappling.
- `specs/JUMP_COMMAND_SPEC.md`: "Fights at the edge (#3583)", "Aiming over an edge (#3589)".
- `specs/PARKOUR_TEMPLATE_LIBRARY.md` §1.5: rooftops.
- `specs/proposals/MULTI_WEAPON_COMBAT_SPEC.md`, `specs/proposals/GRIP_ENFORCEMENT_SPEC.md`: weapon choice and grip.
- `specs/proposals/STEALTH_AND_DETECTION_SPEC.md`: hiding and ambush.
- `COMBAT_AUDIT_LOGGING_SPEC.md`: the durable combat audit log.
- `specs/roadmaps/COMBAT_REFACTOR_SPEC.md`: combat refactor roadmap.

---

*The G.R.I.M. combat system is designed to be a tool for storytelling, not a replacement for good roleplay. Its complexity serves the narrative, providing depth and consequence while maintaining focus on character development and compelling stories.*
