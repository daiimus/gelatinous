# G.R.I.M. Combat System Documentation

> **Status:** ✅ Shipped — high-level overview of the running combat system. NOTE: some features described below are aspirational and NOT implemented — skill progression, reputation, ammunition tracking, weapon durability, and formation fighting. Treat the combat code and COMBAT_REFACTOR (roadmap) as current truth where they disagree.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited 2026-09-11, and are NOT covered by the aspirational list above.** Each is annotated in place below.
> - **No cover system.** §Ranged Combat's "Cover System" has no implementation; nothing about the room, an object or terrain reaches the hit math (`world/combat/attack.py:422-470`).
> - **No environmental modifier.** §Multi-Room Combat's "Environmental Factors" contradicts this spec's own "Planned Enhancements", which still lists weather/terrain/lighting as unbuilt.
> - **`aim` grants no accuracy bonus.** The to-hit roll is `randint(1,20) + motorics × sight × manipulation` (`world/combat/attack.py:437`, `:469`) and never reads the aim state. Aim locks the target, posts a visible tell, enables cross-room fire along an aimed exit, and buys an opportunity attack if the target flees.
> - **Grappling auto-yields only the grappler**, not both parties (`world/combat/grappling.py:410-413`, matching `GRAPPLE_SYSTEM_SPEC.md:91-92` and `:413-414`).
> - **Resonance is unused by combat.** It appears under `world/combat/` only as `STAT_RESONANCE` (`constants.py:24`) and a descriptor-table entry (`:830`), and nowhere at all under `commands/combat/`; its live consumers are perception and recognition (`world/stealth.py:162`, `world/identity.py:1758`, `world/voice.py:485`, `world/radio.py:744`). There is no social-combat resolver.
> - **Grit drives no health pool and no damage resistance.** There is no character-level hit-point stat; health is the organ model (`world/medical/core.py:15`) and mitigation is armor (`typeclasses/armor_mixin.py:320`).
> - **No per-weapon accuracy stat.** Weapons carry `db.damage` and `db.is_ranged` only; every weapon lands on the attacker's motorics alone.
> - **`INITIATIVE_BASE`, `DAMAGE_MULTIPLIER` and `GRAPPLE_DIFFICULTY` do not exist** anywhere in the repo.
> - **No performance instrumentation.** `world/combat/debug.py` is a diagnostics/audit sink with no timing, counter or throughput metric.
> - **"(Sept 2024)"** on the improvements section is an off-by-one-year error — that section was added 2025-09-14 (`bba77e22`).
>
> **Two things that look like drift and are not** (checked 2026-09-11, recorded so the next auditor does not "fix" them): `look` really is combat-aware from the main character cmdset — Evennia's own `CmdLook` arrives by inheritance at `commands/default_cmdsets.py:150`, the game's custom subclass having been deleted with `commands/combat/info_commands.py` in `d8261f7e`; and the kill/hit colour escalation really is as documented, because in Evennia lowercase `|r` is the HILITE (bold) red and uppercase `|R` the regular one (`world/combat/messages/__init__.py:175-183`; cf. commit `ef3b18e6` "Bold white -> regular white", which changed `|w` → `|W`).

## Overview

The **G.R.I.M. Combat System** is a roleplay-focused, turn-based combat engine that emphasizes both violent and non-violent conflict resolution. It's built around four core character attributes and supports complex tactical scenarios while maintaining narrative focus.

## Core Attributes - The G.R.I.M. System

### **Grit** - Physical Foundation
- **Physical toughness** and endurance
- **Willpower** and mental fortitude  
- **Health points** and damage resistance
- **Recovery** from injuries and fatigue

*Used for: Absorbing damage, resisting effects, enduring hardship*

> **⚠ Corrected 2026-09-11 — aspirational, not shipped.** There is no character-level hit-point stat, and nothing consults Grit for absorption, resistance or recovery. Health is the organ-based medical model (`world/medical/core.py:15` `class Organ`, per-organ HP) and damage mitigation is armor (`typeclasses/armor_mixin.py:320` `_calculate_armor_damage_reduction`, called from `take_damage` at `:69`). The fossil of the system this paragraph describes is still in the tree: `world/combat/constants.py:29-30` declares `DEFAULT_HP = 10` and `HP_GRIT_MULTIPLIER = 2` under a `# Health system` heading, and **neither name is read anywhere in the repo**. Grit's three real uses are the disarm contest (`world/combat/actions.py:133-134`, grit vs grit), the drag contest (`world/combat/movement_resolution.py:462-463`, `typeclasses/exits.py:306-307`) and vital-targeting skill (`world/medical/utils.py:160-165`). `world/manifest.py:67-81` does map melee/unarmed/athletics onto Grit, but those skills are a creation-time snapshot that nothing rolls (see the module docstring). The toughness/willpower framing above is character-concept flavour, not a mechanic.

### **Resonance** - Social Awareness
- **Empathy** and emotional intelligence
- **Social awareness** and reading people
- **Communication** and persuasion
- **Conflict de-escalation** abilities

*Used for: Sensing intentions, social combat, peaceful resolution*

> **⚠ Corrected 2026-09-11 — no combat use.** Resonance is read nowhere under `world/combat/` or `commands/combat/`; it exists there only as `STAT_RESONANCE` (`world/combat/constants.py:24`) and a descriptor-table entry (`:830`). Where it IS live is outside combat: stealth detection (`world/stealth.py:162`, `:240`, `:274`) and identity/voice/radio recognition (`world/identity.py:1758`, `world/voice.py:485`, `world/radio.py:744`) — i.e. the "sensing" half of this line ships, the "social combat" half does not.

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
- **Initiative Order**: Based on character stats and situational modifiers
- **Action Economy**: Each character gets one primary action per turn
- **Reaction System**: Defensive actions and responses to attacks
- **Round Structure**: Clear turn order with automatic progression

#### **Round Timing**
- **6-Second Rounds**: Each combat round represents 6 seconds of in-game time (configurable via `COMBAT_ROUND_INTERVAL`)
- **Staggered Attacks**: Individual attacks are staggered within each round to prevent message spam
  - First attacker: Executes immediately when round begins
  - Subsequent attackers: Delayed by 1.5 seconds each (configurable via `STAGGER_DELAY_INTERVAL`)
  - Maximum delay: 4.5 seconds (configurable via `MAX_STAGGER_DELAY`) to ensure all attacks complete before next round
- **Instant Actions**: Some actions (flee, jump) bypass the round system for emergency situations
- **Turn-Based Actions**: Most tactical actions (advance, retreat, charge, disarm) are queued for the next round

**Configuration**: All timing values can be adjusted in `world/combat/constants.py` without code changes.

### Proximity-Based Engagement

#### **Melee Range**
- **Close Combat**: Hand-to-hand, melee weapons, grappling
- **Proximity Required**: Must be in melee range to engage
- **Movement Costs**: Advancing/retreating affects action economy
- **Weapon Restrictions**: Some weapons require specific ranges

#### **Ranged Combat**
- **Shooting**: Firearms, bows, thrown weapons
- **Line of Sight**: Clear path required for ranged attacks
- **Cover System**: Objects and terrain affect accuracy
  > **⚠ Corrected 2026-09-11 — NOT implemented.** No cover mechanic exists anywhere in `world/combat/`; the only "cover" hits are clothing coverage (`constants.py:133-184`) and two flee messages about covered exits (`constants.py:587`, `:594`). The to-hit roll (`world/combat/attack.py:422-470`) takes no term derived from the room or its contents.
- **Ammunition**: Limited shots require tactical resource management

### Grappling System

#### **Restraint Mode** (Default)
- **Auto-Yielding**: Both parties start in non-violent mode
  > **⚠ Corrected 2026-09-11 — only the grappler auto-yields.** `world/combat/grappling.py:410-413` sets `char_entry[DB_IS_YIELDING] = True` for the grappler and deliberately leaves the victim non-yielding (the line that would yield them is commented out) so the victim auto-resists every turn. `GRAPPLE_SYSTEM_SPEC.md:91-92` and `:413-414` document the shipped behaviour correctly; this line is the outlier. A knock-on: `escape`'s "you switch to violent struggle" message only fires if the victim *was* yielding (`commands/combat/special_actions.py:248-252`), so in a default grapple it never appears. Both parties yielding is reachable, but only if the victim chooses it.
- **Gentle Hold**: Grappler maintains control without harm
- **Peaceful Resolution**: Preferred method for conflicts
- **De-escalation**: Allows for roleplay and negotiation

#### **Violent Mode** (Escalation)
- **Active Resistance**: Victim chooses to fight back
- **Escape Attempts**: Violent struggles to break free
- **Damage Potential**: Can cause harm during struggle
- **Last Resort**: When peaceful resolution fails

### Yielding Mechanics

#### **Yielding State**
- **Non-Violent**: Character chooses not to fight
- **Peaceful Stance**: Attempts to de-escalate conflict
- **Defensive Only**: No aggressive actions taken
- **Roleplay Focus**: Emphasis on character interaction

#### **Active Combat**
- **Aggressive Stance**: Character fights actively
- **Full Actions**: All combat options available
- **Tactical Depth**: Complex combat maneuvers possible
- **Consequence Awareness**: Higher stakes and risks

## Command Structure

### Core Actions (`commands/combat/core_actions.py`)
- **`attack <target>`**: Initiate or continue combat
- **`stop attacking`**: Cease aggressive actions, enter yielding state

### Movement Commands (`commands/combat/movement.py`)
- **`flee`**: Attempt to escape combat entirely (once per round, instant execution)
- **`retreat`**: Back away from melee range (same room)
- **`advance <target>`**: Close distance for melee combat
- **`charge <target>`**: Reckless rush attack with bonuses/penalties

> **Refused at the edge (#3583, owner ruling 2026-09-16).** None of the
> three room-changing movement commands will take a body over a drop.
> `flee`, `advance` and `charge` all filter their exit pool through one
> predicate — `can_leave_by(mover, exit)` in `world/gravity.py` — which
> fails an exit that is an edge (`db.is_edge`), a gap (`db.is_gap`) or
> that leads into an air cell, unless the mover's `db.stays_aloft is
> True`. The predicate lives in the gravity module rather than in combat
> because it is the same question gravity asks everywhere else, and
> because combat movement relocates with `move_to` and so never reaches
> the refusal in `Exit.at_traverse` that already stops walking. `advance`
> (`world/combat/movement_resolution.py`) and `charge` keep the rejected
> exit so they can say why: *"The only way to X is over the N edge — that
> is a jump, not a charge."* Going over the edge is a deliberate act with
> its own verb and its own consequences (`specs/JUMP_COMMAND_SPEC.md`),
> never something a movement command does to you.
>
> Owner: *"It would be refused at the edge… Ideally, very few rooftops
> will exist without exits though — so ending up on one where all you can
> do is jump is a tactical challenge."* A roof with nothing but edges is
> therefore a designed predicament, not a bug — see
> `specs/PARKOUR_TEMPLATE_LIBRARY.md` §1.5.
>
> Three details worth not re-deriving:
>
> * **The edge question comes first.** `advance` asks `can_leave_by`
>   BEFORE it rolls the grapple drag-resist contest
>   (`world/combat/movement_resolution.py`), so a grappler who cannot go
>   that way never drags their victim into a roll that was going to be
>   thrown out anyway.
> * **The flags are read strictly.** `can_leave_by`, the jump verbs
>   (`exit_obj.db.is_edge is not True` / `is_gap is not True`) and the
>   edge/gap block in `Exit.at_traverse` (`is_edge = self.db.is_edge is
>   True`) all require a literal `True`. A truthy-but-not-True attribute
>   left on an exit by an old build script does not make it an edge in
>   one place and a plain exit in another.
> * **Souls ask the same predicate.** An NPC soul's `flee` job
>   (`world/souls/jobs.py`) filters its exits through `can_leave_by`
>   too, and reports "cornered — nowhere to flee" when none survive — so
>   an NPC will not walk itself off a roof to escape.
>
> **Both of flee's contests are now shared.** Leaving a fight has always
> had two prices, and `CmdFlee` held both inline. #3583 extracted the
> first and #3591 the second, so `flee` and the jump verbs charge them by
> exactly the same rules:
>
> * `break_aim_lock(caller, *, bonus=0, label=None)` — the
>   Motorics-vs-Motorics roll that breaks an aimer's lock, with the
>   aimer's opportunity attack on a loss.
> * `roll_to_disengage(caller, handler, *, bonus=0, label=None)` — the
>   Motorics-vs-Motorics roll against the best-Motorics opponent
>   targeting you, ties to the blocker, with that blocker's opportunity
>   attack on a loss.
>
>   **The opponent need not be in your room — suppressive fire, by
>   design (owner 2026-09-16).** `opponents_targeting` takes every
>   combatant in the merged fight whose target is you, wherever they
>   stand, so someone being shot from a rooftop (#3589) still rolls
>   against the shooter's Motorics to get off the street, and a loss
>   reads "blocked by their opponents" with nobody beside them. Owner:
>   *"That is the intended function. It would be suppressive fire pinning
>   someone down."* The pin is the **constant attacking**, not the
>   bullets: when ammunition exists it is the attacker's willingness to
>   keep firing every round that holds the target, and running dry ends
>   the pin because the attacks stop, not because a counter did. Purely
>   thematic/gameplay justification, and the intended one — do not
>   "fix" the roll to filter by room.
>
>   **Future consideration (owner, 2026-09-16), open — revisit when
>   ammunition is designed:** whether the pin should instead be *ammo
>   burn*. Today the ruling is "the pin is the constant attacking":
>   a shooter holds a target by being enrolled against them round after
>   round, and ammunition, once it exists, only sets how long that can
>   last. The alternative is that suppression is what the bullets buy —
>   the shooter spends rounds to pin without needing to hit, a dry gun
>   pins nothing, and a loaded one pins whether or not a shot is fired
>   that round. The two disagree on exactly one thing: whether an
>   attacker who is enrolled but not firing (empty, jammed, reloading,
>   a melee weapon in hand) still counts in `opponents_targeting` for
>   the disengage roll. Under the current ruling they do. Do not build
>   the ammunition system on either answer without asking; the owner
>   flagged this as something they may change their mind on.
>
>   **A deleted target is not a relationship (#3568 / #3569, 2026-09-17;
>   owner: "shouldn't happen in actual combat but addressing it makes
>   sense … one of those things that should be logged").**  The orphan
>   sweep (`detect_and_remove_orphaned_combatants`) used to count a
>   recorded `target_dbref` as a relationship whether or not the
>   character still existed, so a combatant whose target was deleted
>   mid-fight stayed "locked in combat" for as long as a third party kept
>   the handler alive.  It now resolves the dbref; a target that no longer
>   exists is cleared on the stored entry, a `TARGET_GONE` splattercast
>   line and a `logger.log_warn` are emitted, and the combatant is told
>   *after* the sweep has decided their fate -- "Your target is no longer
>   there." if they are leaving with it, "… Choose a new target if you
>   wish to continue fighting." if someone still holds them in.  A queued
>   `advance` / `charge` / `disarm` reads its target through one resolver,
>   `queued_action_target`, which tells a missing key (the player gave no
>   target, old message) from a key holding `None` (the target was deleted
>   between rounds: "Your target is no longer there.", logged); the sweep
>   drops such an action when it clears the target so one deletion reports
>   once.  `at_repeat` re-reads the round snapshot after the sweep every
>   time (#2422).  The death path clears targets before a body is deleted,
>   so the warning is a builder's or a system's deletion, never a kill.
>
> **A body does not square up when its target leaves (#3347, 2026-09-18).**
> When a combatant leaves the fight -- `remove_combatant`, every door: the
> end-of-round sweep, the attack path's kill, flee, the jump verbs, a
> dragged traversal, the deferred knockout ejection, the orphan sweep -- everyone
> who was targeting them is re-pointed at someone who is targeting *them*
> and announced with the weapon's initiate pose. That is the auto-retarget,
> and this paragraph is its only description. The announcer is now checked
> the way #1584 checks the target on the attack command's side: a dead or
> unconscious combatant gets no new target and says nothing; the sweep
> ejects them. Three things put a body in that loop. A knockout in combat
> does not eject on the hit: `_handle_unconsciousness` defers the message
> and the ejection behind a five-second timer (nothing in combat clears
> `unconsciousness_pending`), and the round is six seconds, so a fighter
> knocked out mid-round is enrolled and unconscious for the rest of it;
> two knockouts in one round, one targeting the other, is the common case.
> Death does not eject a combatant at all (only the attack path's kill and
> the sweep do), so anyone killed by a fall, a grenade, a blast or a
> bleed-out on the medical tick is still enrolled until the end of the
> round. And a body knocked out before it was attacked is enrolled with its
> attacker as its target. **A hold is a hold (#3622, owner ruling
> 2026-09-18):** a yielding survivor is not re-pointed and not un-yielded.
> They are told who left, who is still targeting them, and that yielding
> means not fighting back ("use 'attack' or 'kill' to resume malicious
> intentions"); the orphan sweep lets them
> out if nobody is on them, and their own next `attack` names the target.
> That was the one place the system un-yielded someone for a reason not
> their own: it broke a `stop` when a third party left, and turned a
> consensual hold into a struggle (the held person's flag drives the shield
> chance and the every-round auto-escape). Recorded, not changed: the
> announcement reaches the announcer and the new target, but the
> room line has never been sent and the announcer gets a second fallback
> line, because a local import shadows `msg_room_identity` (#3620).
>
> Both losses go through one more shared helper,
> `opportunity_attack(attacker, target, *, immediate=False)`, which runs a
> real `attack` against the RESOLVED target (#1002) — immediately for a
> jump, through the shared `resolve_bonus_attack` that failed advance and
> charge already use; on the next round for a flee (#3593, below). The
> jump verbs pass
> `bonus=JUMP_AWAY_BONUS` (20) to both rolls and `label="JUMP_AWAY"` to
> both — the label only re-prefixes the splattercast lines, so a jump
> logs `JUMP_AWAY_` rather than `FLEE_`.
>
> **The consequence of a lost roll is where the two verbs part.** Flee
> keeps its own: a lost disengage blocks the flee outright and sets
> `NDB_SKIP_ROUND`. A jump is never refused and never costs a round — the
> blocker gets their attack, the jumper says *"You throw yourself at the
> edge regardless."*, and only being left dead or unconscious stops the
> departure. See the jump spec's "Fights at the edge" block.
>
> _(2026-09-16, #3591: RULED and built. A jump in a fight pays BOTH halves
> of flee's price: the aim contest (`break_aim_lock`) AND the melee
> disengage roll — flee's Part 2 extracted into `roll_to_disengage(caller,
> handler, *, bonus=0, label=None)` in commands/combat/movement.py, the
> best-Motorics opponent targeting the jumper, ties to the blocker — with
> the bold-move bonus on both. A lost disengage hands the blocker an
> immediate attack via the shared `opportunity_attack(attacker, target, *,
> immediate=True)`
> ("catches you as you break for the edge"), and the jump still goes; only
> death or unconsciousness stops it. Never a refusal, never a lost round.
> Both `jump off` and `jump across`. Flee keeps its own consequence on a
> lost disengage: blocked and a round skipped.)_
>
> _(2026-09-16, #3593: the shot is resolved IMMEDIATELY for a jump, on the
> next round for a flee — and NOT by a new path. `CmdAttack.func` only
> ENROLS: it puts the attacker in the handler with the target and prints the
> weapon's initiate line, and the shot itself fires on the handler's next
> round. That is enough for a blocked fleer, who is still standing there
> when the round comes round, but it was nothing at all for a jumper, who is
> out of the handler and off the roof inside the same command — the
> opportunity attack read as a price and cost nothing. So
> `opportunity_attack(attacker, target, *, immediate=False)` now finishes
> the job under `immediate=True` by calling
> `world.combat.utils.resolve_bonus_attack(handler, attacker, target)` — the
> same helper that already hands a ranged defender an immediate attack when
> an advance or a charge at them fails. It does the combat-entry lookup and
> the `process_attack` itself, with its own guards (a dead or unconscious
> target, melee reach, proximity). One immediate-attack implementation,
> three doors: a failed advance, a failed charge, and a jumper who lost a
> leaving contest. `break_aim_lock` forwards the flag as `immediate_attack`,
> and the jump verbs pass True on both halves. Flee is unchanged.)_

### Special Actions (`commands/combat/special_actions.py`)
- **`grapple <target>`**: Attempt to grab and restrain target
- **`escape`**: Break free from grapple (switches to violent mode)
- **`release`**: Let go of grappled target
- **`disarm <target>`**: Attempt to remove target's weapon
- ~~**`aim <target>`**: Improve accuracy for next attack~~ **Owner ruling 2026-09-13 (#3355): the promise is withdrawn.** Aim is a positioning tool -- lock, tell, cross-room fire, flee-punish -- and grants no accuracy. `help aim` now says so.
  > **Directional attacks resolve through `room_through` (#3589, owner ruling 2026-09-16).** `aim <direction>` + `attack` no longer fires into whatever room the exit happens to point at. `commands/combat/core_actions.py` asks `world.gravity.room_through(exit_obj)` for the room the aim really reaches: over an **edge** (or any exit into air) that is the ground the edge drops to, not the empty air cell; across a **gap** it is the far perch; anywhere else it is just the destination. Owner: *"Aiming at an edge typically means aiming at the ground area it drops to because of sniping. Rooftop to street for example."* The ground is found by `ground_below`, which takes the **highest non-air room in the same column below** — read off `world/spatial`'s `coordinate_index()`, the one cell-addressed lookup in the game, with no cell limit and no floor at z=0 (the Drifts resolve downward past zero), falling back to the `down` exit chain only off-grid or where the grid has nothing seeded below. So a shot over a parapet works whether or not anyone wired the column: **geometry wins over wiring**, and a bare column (#3581) still resolves the shot to the seeded street even though a fall down it parks in mid-air. Two `None` cases refuse the shot — *"You are aiming `<dir>`, but there's nothing down there to hit."* — nothing solid below at all, and the **occlusion rule**: a room below that is not a surface (`is_surface` — a rooftop or `outside is True`) means an unbuilt roof is in the way. The aiming **look** and its aimed-room target search resolve the same way (`typeclasses/rooms.py`), falling back to the air cell so a bare column still renders; throw's `at` form resolves the same way too, while its directional forms still fly into the air cell so gravity carries the object down. Upward (street → roof) is unbuilt and parked with Phase 3 (#1511) — no exit to aim through, no line-of-sight concept — but the asymmetry only constrains who can OPEN: the attack command enrols the victim with the shooter as target, so from the next round a street target with a ranged weapon fires back at the roof, needing neither an aim nor an exit — **by design** (owner 2026-09-16: *"Automagic self-defense and the perk of carrying a gun."*); with a melee weapon the round's attack is refused across rooms (*"You can't reach … from here."*) and `advance`/`charge` find no way up. The other exposure the review named — aiming widens every bare name search into the aimed room, now a populated street — is filed as #3596. Full contract: `specs/JUMP_COMMAND_SPEC.md`, "Aiming over an edge (#3589)".
  > **⚠ Corrected 2026-09-11 — no accuracy bonus is applied.** `world/combat/attack.py:437` computes `effective_skill = attacker_skill * sight_factor * manip_factor` and `:469` rolls `randint(1, 20) + effective_skill`; `NDB_AIMING_AT` is never read in that file. What aiming actually buys: the target is held in place, a visible tell is posted, `aim <direction>` unlocks cross-room fire through that exit (`commands/combat/core_actions.py:97-115`), and the aimer gets an opportunity attack if the aimed-at target flees (`commands/combat/movement.py:229`). Whether the bonus should be built or the promise withdrawn is an open owner question — `CmdAim`'s own help text (`commands/combat/special_actions.py:361`) makes the same claim.

### Information Commands (main character cmdset)
There is no dedicated combat info-command module. Combat-aware `look` is provided
by the main character cmdset (so it works both in and out of combat) rather than a
separate `commands/combat/` file.
- **`look`**: Enhanced awareness during combat (registered on the main character cmdset)

## Combat Flow

### 1. **Initiation**
```
Player A: attack Player B
→ Combat handler created
→ Initiative order established
→ Both players enter combat state
```

### 2. **Turn Processing**
```
→ Check initiative order
→ Process active player's action
→ Apply results and consequences
→ Check for combat end conditions
→ Move to next player's turn
```

### 3. **Resolution**
```
→ All players yielding: Peaceful end
→ One player defeated: Combat victory
→ All players flee: Combat dispersed
→ Handler cleanup and state reset
```

## Tactical Features

### Multi-Room Combat
- **Room Transitions**: Combat can span multiple locations
- **Ranged Coverage**: Archers can control exits
- **Tactical Positioning**: Room layout affects combat options
- **Environmental Factors**: Terrain and obstacles matter
  > **⚠ Corrected 2026-09-11 — NOT implemented, and contradicted by this spec's own roadmap.** No weather, terrain or lighting term reaches any combat roll (a repo grep for those words under `world/combat/` hits only weapon prose). "Planned Enhancements" below still lists "Environmental Effects: Weather, terrain, lighting impact" as future work — that entry is the accurate one. Room layout does matter, but only through exits and multi-room handler management (`DB_MANAGED_ROOMS`), not through any terrain property.

### Weapon System
- **Weapon Types**: Melee, ranged, thrown, improvised
- **Weapon Stats**: Damage, accuracy, range, special properties
  > **⚠ Corrected 2026-09-11 — damage and range ship; accuracy does not.** Weapons carry `db.damage` (read via `get_weapon_damage`, `world/combat/utils.py:209-229`) and `db.is_ranged` (`:232-233`). There is no per-weapon accuracy attribute anywhere in the repo; every weapon lands on the attacker's motorics alone (`world/combat/attack.py:422-470`), so a pistol and a brick are equally easy to hit with. Thrown objects are blunter still — `world/combat/throwing.py:433` flat-rates a 70% hit chance under the comment "could be enhanced with accuracy system".
- **Ammunition**: Limited resources for ranged weapons
- **Durability**: Weapons can break or become damaged

### Status Effects
- **Grappled**: Restricted movement and actions
- ~~**Aimed**: Bonus accuracy on next attack~~ **Owner ruling 2026-09-13 (#3355): no accuracy bonus, by decision.** The state persists INTO combat (cleared on `aim stop`, on the aimer moving, or on leaving combat) -- it is not dropped when combat starts.
  > **⚠ Corrected 2026-09-11.** The aimed state is real (`NDB_AIMING_AT` / `NDB_AIMED_AT_BY`, set at `commands/combat/special_actions.py:632-633`) but confers no accuracy bonus — see the `aim <target>` note under Command Structure. Its mechanical effects are immobilising the target, the visible tell, cross-room fire, and an opportunity attack on a flee attempt.
- **Yielding**: Non-violent stance with limited options
- **Wounded**: Injury effects on performance

## Roleplay Integration

### Narrative Focus
- **Rich Messaging**: Detailed, contextual combat descriptions
- **Emotional Context**: Messages reflect character motivations
- **Consequence Awareness**: Actions have meaningful narrative impact
- **Story Enhancement**: Combat serves the story, not vice versa

### Non-Violent Resolution
- **Default Yielding**: Peaceful resolution preferred
- **De-escalation**: Multiple opportunities to avoid violence
- **Restraint Options**: Subdue without permanent harm
- **Social Combat**: Resonance-based conflict resolution
  > **⚠ Corrected 2026-09-11 — NOT implemented.** No social-combat resolver exists, and Resonance is never read by any combat code path. The non-violent resolution that DOES ship is the yielding system: when every combatant is yielding and no grapple is active, the handler ends the fight peacefully (`world/combat/handler.py:755-793` `_check_peaceful_resolution`). That is a state check, not a Resonance contest.

### Character Development
- **Skill Progression**: Combat experience improves abilities
- **Reputation System**: Combat actions affect social standing
- **Psychological Impact**: Violence has emotional consequences
- **Relationship Dynamics**: Combat affects character relationships

## Technical Implementation

### State Management
- **NDB Attributes**: Temporary combat state (proximity, targeting, etc.)
- **DB Attributes**: Persistent character data (stats, equipment, etc.)
- **Handler Persistence**: Combat state survives server restarts
- **Cleanup Systems**: Automatic state cleanup when combat ends

### Performance Considerations
- **Efficient Algorithms**: Optimized for multiple simultaneous combats
- **Memory Management**: Proper cleanup of temporary data
- **Scalability**: Handles large numbers of participants
- **Error Handling**: Robust error recovery and logging

### Debug Infrastructure
- **Comprehensive Logging**: Detailed debug information
- **State Inspection**: Tools for examining combat state
- **Error Reporting**: Clear error messages for players and developers
- **Performance Monitoring**: Tracking system performance
  > **⚠ Corrected 2026-09-11 — NOT implemented.** `world/combat/debug.py` (236 lines) is a single diagnostics sink — `get_splattercast` (`:160`), `debug_broadcast` (`:175`), `log_debug` (`:191`), `log_combat_action` (`:212`) — plus the durable audit log described by `COMBAT_AUDIT_LOGGING_SPEC.md`. It emits no timing, counter or throughput metric, and nothing anywhere under `world/combat/` measures performance. The other three bullets in this section are earned.

## Configuration

### Combat Constants (`world/combat/constants.py`)
```python
# Default attribute values
DEFAULT_GRIT = 1
DEFAULT_RESONANCE = 1
DEFAULT_INTELLECT = 1
DEFAULT_MOTORICS = 1

# Combat mechanics
INITIATIVE_BASE = 10
DAMAGE_MULTIPLIER = 1.5
GRAPPLE_DIFFICULTY = 8
```

> **⚠ Corrected 2026-09-11 — the four `DEFAULT_*` lines are real (`world/combat/constants.py:17-20`); the three "Combat mechanics" lines are not.** `INITIATIVE_BASE`, `DAMAGE_MULTIPLIER` and `GRAPPLE_DIFFICULTY` appear nowhere in the repo. What actually ships:
> - **Initiative** — `randint(1, 20) + motorics + surplus_limb_initiative_bonus(char) + ambush_bonus`, rolled once when a combatant is added (`world/combat/utils.py:668-673`; the limb bonus is defined at `:295`).
> - **Damage** — `randint(1, 6)` base plus the weapon's own `db.damage`, with no global multiplier (`world/combat/attack.py:531-534`), then armor reduction in `take_damage` (`typeclasses/armor_mixin.py:69`, `:320`).
> - **Grapple** — an opposed motorics contest, not a fixed difficulty number (`world/combat/grappling.py`).
>
> Also in this file and **defined but never read anywhere**: `DEFAULT_HP = 10` and `HP_GRIT_MULTIPLIER = 2` (`:29-30`) — see the Grit note above. The timing constants this spec cites elsewhere are all genuine: `COMBAT_ROUND_INTERVAL = 6`, `STAGGER_DELAY_INTERVAL = 1.5`, `MAX_STAGGER_DELAY = 4.5` (`:806-808`).

### Message Templates
- **Action Messages**: Descriptions of combat actions
- **Result Messages**: Outcomes of attacks and defenses
- **State Messages**: Changes in combat state
- **Weapon Messages**: Weapon-specific descriptions

## Advanced Features

### Planned Enhancements
- **Formation Fighting**: Group tactics and coordination
- **Environmental Effects**: Weather, terrain, lighting impact
- **Equipment Durability**: Weapon and armor degradation
- **Combat Styles**: Different fighting approaches and techniques

### Customization Options
- **House Rules**: Server-specific combat modifications
- **Weapon Varieties**: Easy addition of new weapon types
- **Special Abilities**: Character-specific combat techniques
- **Environmental Hazards**: Location-based combat modifiers

## Best Practices

### For Players
- **Roleplay First**: Use combat to enhance story
- **Consider Consequences**: Actions have meaningful impact
- **Communicate Intent**: Clear communication prevents misunderstandings
- **Respect Boundaries**: Honor other players' comfort levels

### For Developers
- **Maintain Modularity**: Keep combat systems cleanly separated
- **Document Changes**: Update documentation with modifications
- **Test Thoroughly**: Ensure changes don't break existing functionality
- **Preserve Philosophy**: Maintain roleplay-first approach

### For Administrators
- **Monitor Balance**: Ensure fair and engaging combat
- **Handle Disputes**: Mediate conflicts between players
- **Maintain Standards**: Enforce roleplay and conduct standards
- **Support Community**: Foster positive gaming environment

## Recent System Improvements (Sept 2024)

> **⚠ Corrected 2026-09-11 — the date is wrong and "Recent" is stale.** This section was added **2025-09-14** in commit `bba77e22` ("Updated specs to reflect recent changes"), which appended sibling blocks to `COMBAT_MESSAGE_FORMAT_SPEC.md` and `DEATH_CURTAIN_SPEC.md` the same day. Read it as a **historical changelog entry for Sept 2025**, not as a description of recent work. The substance below verified accurate on re-check: perspective-specific messaging; the dual initiate, including its documented contextual triggers (`commands/combat/core_actions.py:493-503` — since #1584 it additionally requires the target to be conscious and alive, because a corpse should not square up); automatic phase colouring (`world/combat/messages/__init__.py:163-183`, in place since 2025-05-24, `1c8c6a3c`), the threat-escalation order included — `|r` is Evennia's bold red and `|R` the regular one; the removal of combat entry/exit spam; and medical-cause death messages.

### Quality of Life Enhancements

#### Enhanced Message Personalization
Combat messaging now provides proper perspective-specific experiences:
- **First-Person Actions**: Attackers see "You draw your knife..." instead of observer messages
- **Second-Person Reactions**: Victims see "Nick prepares to strike you!" for direct engagement
- **Third-Person Observation**: Bystanders see appropriate third-person descriptions

#### Dual Initiate System
Combat initiation now shows both aggressive and defensive stances:
- **Attacker Initiate**: Shows weapon-specific aggressive preparation
- **Victim Defensive**: Automatic defensive stance when surprised or not currently engaged
- **Contextual Triggers**: Defensive messages only when target isn't already in combat or targeting

#### Automatic Color Coding
Visual clarity improved through contextual color application:
- **Threat Escalation**: Red initiate → Red hit → Bold red kill
- **Clear Misses**: White coloring for failed attempts
- **Automatic Application**: No manual color coding required in weapon templates
- **Override Support**: Pre-colored messages respected

#### Clean Narrative Flow
Removed meta-gaming elements for better immersion:
- **No Entry/Exit Spam**: Eliminated "You enter combat!" and "You are no longer in combat!" messages
- **Weapon-Focused**: Combat flows directly from weapon initiate to action
- **Natural Transitions**: Combat begins and ends with narrative actions, not system announcements

### Death System Integration

#### Medical Cause Integration
Death messages now reflect actual medical causes:
- **Informed Death**: "Nick is dying from blood loss..." based on medical analysis
- **Cause Detection**: Leverages existing medical system for accurate reporting
- **Fallback Graceful**: Beautiful atmospheric messages when analysis unavailable

#### Enhanced Death Curtain
Visual death experience improved significantly:
- **Proper Color Rendering**: Fixed color code parsing for perfect centering
- **Medical Suppression**: Prevented "lifeless body" message conflicts
- **Timing Coordination**: Clean message flow from cause → curtain → confirmation

#### Race Condition Prevention
Eliminated message ordering conflicts:
- **Attack Before Consequences**: Attack messages now appear before damage/death
- **Curtain Exclusivity**: Death curtain gets uninterrupted control during animation
- **Medical Coordination**: Bleeding messages suppressed during death processing

### Technical Improvements

#### Message Architecture
- **Perspective-Aware**: Three-message format (attacker/victim/observer) fully implemented
- **Context-Sensitive**: Messages adapt based on combat state and participant status
- **Weapon-Agnostic**: System works consistently across all weapon types

#### System Coordination
- **Combat-Medical Sync**: Proper handoff between combat damage and medical processing
- **Death-Medical Sync**: Clean separation of death curtain and medical ticker messaging
- **State Management**: Improved tracking of combat initiation and defensive states

---

*The G.R.I.M. combat system is designed to be a tool for storytelling, not a replacement for good roleplay. Its complexity serves the narrative, providing depth and consequence while maintaining focus on character development and compelling stories.*
