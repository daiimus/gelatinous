# G.R.I.M. Grappling System Specification

The G.R.I.M. Grappling System is close combat that puts **restraint before violence**. A grapple starts as a hold, not an attack; violence is something a participant chooses. It works with the proximity system, movement, and yielding. The resolvers are in `world/combat/grappling.py`, the commands in `commands/combat/special_actions.py`, the drag doors in `typeclasses/exits.py` and `world/combat/movement_resolution.py`, and the words in `world/combat/messages/grapple.py`.

## Design Philosophy

1. **Restraint first.** Grappling begins as restraint. Violence needs an explicit choice by a participant. There are several chances to avoid harm. Combat serves the story, not the mechanics.
2. **Tactical depth.** Grappling affects, and is affected by, positioning. Several characters can be involved at once.
3. **Mechanical consistency.** Grappling uses the core G.R.I.M. attributes, mainly Motorics. Outcomes are opposed rolls. State is checked and cleaned up every round.

---

## Core Mechanics

### Grapple States

**Relationship**
1. **Not grappling**: no grapple involvement.
2. **Grappling someone**: holding another character.
3. **Being grappled**: held by another character.
4. **Mutual grapple**: two characters grappling each other — 📋 UNBUILT (not decided): no path lets two characters hold each other, since a held character cannot grapple and a takeover makes the person taken let go of their own victim first.

**Intent**
1. **Restraint mode** (default): non-violent holding and control.
2. **Violent mode**: active struggle. In the game this means only that neither party is yielding, so the victim auto-resists every round (see Grapple Damage System below).

**Participation**
1. **Yielding**: accepts restraint, no resistance.
2. **Non-yielding**: resists, with an automatic escape attempt every round.

### Attributes
- **Motorics**: grapple initiation, contests, takeovers and escapes.
- **Grit**: resisting a drag through an exit (physical endurance and will).
- **Resonance**: reading intent and de-escalation — 📋 UNBUILT (no issue).

---

## Grapple Initiation: `grapple <target>`

### Prerequisites
- Grappler and target are in the same room.
- The target is a valid character.
- You cannot grapple yourself.
- You cannot grapple while someone else is grappling you.
- Grappling someone new while already holding someone is not refused: if the new grapple succeeds, the first hold is let go (`release_existing_grapple`, #2486). One grappler holds one victim. Whether a second grapple should be refused instead is open (see Not decided, #3285).
- Grappling a target who cannot perceive you gets the ambush initiative bonus (`specs/proposals/STEALTH_AND_DETECTION_SPEC.md` §6.1), except on a consensual grab.
- Every grapple is reported to the crime system as an assault, as a punch is.

### Proximity
- A grapple can start combat and set up proximity.
- Grappling a free target, or grappling someone who is holding another person, needs no proximity, in or out of a fight: the grappler rushes in, and proximity is set up on success.
- Contesting someone else's hold on a victim needs melee proximity with that victim (`resolve_grapple_join`).

### The contest
Grappler rolls 1d[Motorics], defender rolls 1d[Motorics]. The grappler wins only on a strictly higher roll; a tie goes to the defender. Initiation, takeover and escape all use Motorics against Motorics.

### Consensual hold (#3363, owner ruling 2026-09-13)
If the target trusts the grappler for `grab`, or cannot contest (unconscious or already restrained), there is no roll. The hold is taken, both parties become yielding, and the held person gets no target. The outcomes below are for the contested grapple. See `specs/TRUST_AND_CONSENT_SPEC.md` §3.

### Success (`resolve_grapple_initiate`)
1. A two-way relationship is set: the grappler's `grappling_dbref` names the target, and the target's `grappled_by_dbref` names the grappler.
2. The grappler auto-yields (restraint intent). The target stays non-yielding (auto-resistance).
3. Both enter or keep proximity.
4. The target auto-targets the grappler, for possible retaliation.

### Failure
1. No grapple state changes.
2. Yielding consequences:
   - If the grappler started the combat, the grappler auto-yields.
   - If the defender joined combat this round and has no combat target, the defender also auto-yields.
   - If the defender was already fighting, that fight continues.
3. The failure is narrated from the `miss` bank (see Grapple Messaging).

---

## Grapple Contests

### Contest for a held victim (`resolve_grapple_join`)
A holds B; C tries to grapple B. A and C contest for B. The winner holds B; the loser gets nothing.

### Grappling an active grappler (`resolve_grapple_takeover`)
A holds B; C tries to grapple A. This is detected as a `grapple_takeover`.
1. C's Motorics against A's Motorics. C wins only on a strictly higher roll.
2. If C wins: A releases B automatically, and C holds A.
3. If C loses: A keeps hold of B, and C becomes yielding if C started the combat.

---

## Grapple Maintenance

### Non-yielding victims
- They attempt to escape every combat round (`resolve_auto_escape` in `world/combat/actions.py`, run from the round loop in `world/combat/handler.py`).
- Victim Motorics against grappler Motorics.
- On success: the victim breaks free, switches to violent mode (non-yielding), and targets the grappler.
- On failure: the victim stays held and keeps struggling.

### Yielding victims
- No auto-escape: they accept restraint.
- They can use `escape` to switch to violent mode.
- The emphasis is on negotiation and de-escalation.
- **A hold survives someone else's exit (#3622, 2026-09-18).** When a yielding party's target leaves the fight, the auto-retarget in `remove_combatant` leaves them yielding and without a target instead of turning them violent. So the held person's shield chance and auto-escape state do not change because a third party left. Described in `specs/COMBAT_SYSTEM.md`.

### Grapple Damage System

**Restraint mode** (default): no damage, only control and positioning; restraint-focused descriptions; the intent is to subdue without harm.

**Violent mode** (escalation): in the game, violent mode deals no damage. No code path deals damage for a grapple. Violent mode means only that neither party is yielding, so the victim auto-resists every round.

Escalation triggers:
- the victim uses `escape`;
- the victim wins the auto-escape;
- an attack on the grappling pair — 📋 UNBUILT (open on #3285): being attacked changes nobody's yielding state.

The damage exchange the spec describes — grapple damage hits (control damage during the struggle) and grapple damage misses (failed attempts to harm), with both parties able to take and deal damage — is 📋 UNBUILT (open on #3285); see Unbuilt.

---

## Human Shield

### Attacks
When someone attacks a character who is holding a victim, the victim may intercept the attack as an involuntary human shield.

**Shield chance**
```
Base shield chance: 40%
+ Grappler Motorics: +5% per point above 1
+ Victim resistance:
  - yielding victim: +10% (easier to position)
  - non-yielding victim: -10% (struggling against positioning)
- Ranged attack: -20% (harder to shield against projectiles)
```

**Order**
1. Someone attacks a grappler.
2. Before normal attack resolution, roll d100 against the shield chance.
3. On success: all parties are told of the interception; the attack's target becomes the victim; the attack then resolves normally on the victim, with the weapon's own combat messages and the victim's normal `take_damage()`.
4. On failure: the attack proceeds against the grappler.

**Shield messages**
- Attacker: `"Your attack is intercepted by {victim} as {grappler} uses them as a shield!"`
- Grappler: `"You position {victim} to absorb {attacker}'s attack!"`
- Victim: `"You are forced into the path of {attacker}'s attack by {grappler}!"`
- Observers: `"{grappler} uses {victim} as a human shield against {attacker}'s attack!"`

**No mode change.** Being used as a shield changes nobody's yielding state. Only a character's own act makes them non-yielding: attacking, grappling, `escape`, or winning the auto-escape.

Purpose: grappling becomes a protective tactic; victims have a strong reason to escape or negotiate; it changes targeting in group fights; it gives dramatic tension and moral dilemmas.

### Grenades
- **Holder shielding**: when a grenade explodes in someone's hands, others in proximity take 50% damage, because the holder's body shields them.
- **Proximity**: everyone in the proximity list takes equal damage, apart from the holder reduction.
- **Grappling**: when a grappler and their victim are both in the blast, the grappler takes no damage and the victim takes double. There is no roll (`check_grenade_human_shield`, `world/combat/explosives.py`). Three explosion branches in `commands/explosion_utils.py` apply it; the explode-in-the-holder's-hands branch does not (open on #3285).
- The explosion paths in `commands/explosion_utils.py` do not go through the combat handler's attack resolution. Each asks `check_grenade_human_shield` for a damage multiplier per character, then deals the damage with `character.take_damage(...)`.

A probabilistic grenade shield was proposed before this fixed split was built; it is kept under Unbuilt.

### Falls
When a grappler falls with their victim, the landing roll splits the fall damage: on a good landing the victim takes 0.75 of it and the grappler 0.25; on a bad one the victim takes 1.5 and the grappler 0.5 (`_land_with_bodyshield` in `world/gravity.py`, ratios `FALL_BODYSHIELD_*` in `world/combat/constants.py`).

---

## Movement

### Dragging through an exit (walk door, `Exit.at_traverse` in `typeclasses/exits.py`)
A drag happens when:
- the grappler is yielding (restraint mode);
- nobody but the victim is targeting the grappler;
- the victim fails a resistance roll: victim Grit against grappler Grit.

On a successful drag:
- both characters move to the new room;
- combat state moves to the new room's handler;
- the hold is kept;
- the victim's channel breaks and any procedure on them ends (the surgeon is told); after the move the victim is standing, off any furniture;
- if the grappler's own move is refused, nobody moves.

If the victim resists: the hold breaks and the grappler's movement is blocked.

### Dragging with `advance` (advance door, `_resolve_advance_cross_room` in `world/combat/movement_resolution.py`)
- The grappler can advance on a new target while holding the victim, and drags the victim along.
- The grappler must be yielding and not targeted by anyone else in the room. The victim then gets a Grit roll to resist (#2602); if it succeeds, the hold breaks and the advance is cancelled.
- After the move the victim is in melee with the grappler only (`_do_advance_move`). Proximity inheritance is 📋 UNBUILT (open on #3285); see Unbuilt.
- The two doors' "targeted by others" checks differ. The advance door also leaves out the person being advanced on, and ignores anyone targeting the grappler from another room. So the same situation can pass one door and fail the other. Reconciling them is an open owner ruling, **#3239**, not a defect.

### Edge jump (`jump off <dir> edge`, `commands/combat/jump.py`)
A third door. The victim goes over with the grappler, with no resistance roll and no yielding condition. The jumper moves first; then the victim's acts are broken and the victim is moved. If the victim still cannot be moved, the hold opens on the roof (`hold_opens_at_the_edge`, `release_edge`, #3668).

### Gap jump (`jump across`)
The grappler lets go of the victim once the leap is real: only after the jumper's move, or on a slip in place (`let_go_for_the_leap`, `release_jump`, #3684).

### Retreat while grappling (`resolve_retreat`, `world/combat/movement_resolution.py`)
`retreat` (alias `disengage`) makes distance within the same room and never goes through an exit, so the victim is not moved anywhere. With a victim held:
- the victim is left out of the Motorics contest;
- a retreat whose only proximity is the victim is refused;
- on success, proximity is broken with every opponent and kept with the victim.

### Charge while grappling
Charging someone else releases the hold (`_release_grapple_for_charge`, `world/combat/movement_resolution.py`). The release is narrated from the `release_charge` / `release_charge_away` bank and told to the room (see Grapple Messaging).

### What a held character cannot do
Being grappled blocks flee, retreat, advance, charge, every `jump`, and `throw`. Attacking your own grappler is refused.

---

## Special Actions

### `escape`
- The victim switches from yielding to non-yielding: violent mode at once.
- `escape` is not a contest and is not queued. The contest is the victim's auto-escape on their next turn (#3391).
- On success: the victim breaks free, stays in proximity, and targets the grappler.
- On failure: the victim stays held, now in violent mode.

### `release`
- The grappler chooses to let go. No contest; it always succeeds.
- Yielding states are kept.
- Both stay in proximity: `resolve_release_grapple` clears the two grapple fields and does not touch proximity.
- Narrated from the `release` bank's two variants (see Grapple Messaging). That bank narrates a chosen release only.
- Uses: de-escalation; freeing yourself for other actions; roleplay.

---

## Grapple Messaging

The authored bank in `world/combat/messages/grapple.py` speaks for the grapple and for every way a grapple ends (#3427, #3615). The bank has 14 phases and 89 variants; 52 are reached in play. The 37 `grapple_damage_*` variants are not.

### Where each beat gets its words

| beat | source | phase / variants |
|---|---|---|
| Contested grapple won (`resolve_grapple_initiate`, `world/combat/grappling.py`) | bank | `hit` — 30 |
| Contested grapple lost (same resolver) | bank | `miss` — 3 |
| Voluntary release (`resolve_release_grapple`) | bank | `release` — 2 |
| Auto-escape won / lost (`resolve_auto_escape`, `world/combat/actions.py`) | bank, fetched and sent by the resolver itself | `escape_hit` / `escape_miss` — 2 + 2 |
| Let go to charge someone else in the room (`_release_grapple_for_charge`, `world/combat/movement_resolution.py`) | bank (#3615) | `release_charge` — 3, names the charge target |
| Let go to charge out of the room (same helper) | bank (#3615) | `release_charge_away` — 2, names no third party, because the charge target is in another room |
| Let go for a gap jump (`let_go_for_the_leap`, `commands/combat/jump.py`; only after the jumper's move, or on a slip in place, #3684) | bank (#3615) | `release_jump` — 3 |
| Dragged victim cannot be taken over an edge (`hold_opens_at_the_edge`, `commands/combat/jump.py`) | bank (#3668) | `release_edge` — 2 |
| Blast tears the pair apart on a sacrifice jump (`handle_explosive_sacrifice`, `commands/combat/jump.py`) | bank (#3615) | `release_blast` — 2, names the other party in every audience's line |
| Queue-time charge preview, actor only (`CmdCharge`, `commands/combat/movement.py`) | bank (#3615) | `release_intent` — 1 |
| Consensual uncontested hold (`resolve_grapple_initiate`) | bespoke prose in the resolver | — |
| Contest for a held victim (`resolve_grapple_join`) | bespoke prose | — |
| Grappling an active grappler (`resolve_grapple_takeover`) | bespoke prose | — |
| Grapple damage | nothing — mechanic unbuilt, see Grapple Damage System and #3285 | `grapple_damage_*` — 37, unreached |

Three ways a hold ends still write inline prose instead of using the bank: a drag resisted at the walk door (`Exit.at_traverse`, `typeclasses/exits.py`), a drag resisted at the advance door (`_resolve_advance_cross_room`, `world/combat/movement_resolution.py`, which tells only the pair and not the room), and a takeover's forced release (`resolve_grapple_takeover`).

`establish_grapple` (`world/combat/grappling.py`) also returns a `(success, message)` tuple with its own string. It is imported by `world/combat/handler.py` and called by nothing in production — only the tests that pin its one-grappler-one-victim guard reach it — so it was left alone rather than converted.

### Why the release beats were authored (#3615)
The `release` bank's two variants ("You decide to release your hold on X", "You shove X away, ending the grapple") describe a *choice*, and would misdescribe a hold ended by a charge, a jump or an explosion. The owner's call was to author the missing beats rather than reuse a wrong one or patch four broadcasts in place (2026-09-18, #3615):

> *"adding the missing messages to our list that can be expanded/subtracted like all our combat messages and then wiring it in - makes the most sense."*

So the `release_*` phases are bank entries, expandable and subtractable exactly like every other bank entry.

### Delivery: `speak_grapple_beat`
`speak_grapple_beat(actor, target, phase, *, audiences=("actor", "victim", "room"), room=None, **extra_chars)` in `world/combat/grappling.py` delivers every bank phase except the two escapes; `resolve_auto_escape` fetches `escape_hit` / `escape_miss` with `get_combat_message` and sends them itself.

It asks `get_combat_message("grapple", phase, …)` and delivers the result the way the weapon banks are delivered: `attacker_msg` to the actor, `victim_msg` to the target, and `observer_template` with `observer_char_refs` through `msg_room_identity`, excluding the pair. Each bystander reads the two of them through their own recognition state rather than a name baked in at send time. The victim receives `victim_msg` directly, always, with no lock check, the grappler rendered through the victim's own recognition state.

Its three narrow parameters, worth knowing before you add another door:
- **`room`** names the room that hears the beat when the actor has already left it. The edge release and the gap jump pass the roof the jumper left (or, after a slip, the roof they still stand on) (`commands/combat/jump.py`). By default it is the actor's own room.
- **`audiences`** picks which of `("actor", "victim", "room")` receive the beat. The default is all three; only the queue-time preview narrows it.
- **`**extra_chars`** forwards a named third party to the accessor as `extra_chars={name: obj}`, rendered **per audience**: the actor's line uses `get_display_name_safe(obj, actor)`, the victim's uses `get_display_name_safe(obj, target)`, and the room's keeps the literal `{name}` in `observer_template` while `observer_char_refs` carries the object, so `msg_room_identity` resolves it once per bystander. Only `charge_target` uses it today. The full contract is in `specs/COMBAT_MESSAGE_FORMAT_SPEC.md` §Third parties — `extra_chars`.

**`hit_location`** is passed **for the `hit` phase only**, from `select_hit_location(target, attacker=actor)` (`world/medical/utils.py`): the same anatomy-weighted, armour-aware draw an attack makes, the attacker reading the target's weak points. `hit` is the one reached phase that uses the placeholder (the unreached `grapple_damage_*` banks use it heavily; `miss`, `release`, the escapes, the `release_*` phases and `release_edge` not at all), so every other call passes nothing. All 30 `hit` variants spend it on the **target's** body: where a line means the grappler's own limbs it says `arms` outright, and where it means a face it says `face`.

### The room hears all three real endings
A charge, a gap jump and a blast each broadcast through `msg_room_identity` with the pair excluded, so every bystander reads the grappler and the victim through their own recognition state. On a cross-room charge the release is spoken before the charger moves (`_resolve_charge_cross_room` calls `_release_grapple_for_charge` ahead of `move_to`), so `release_charge_away` is heard in the room where the hold was. The victim's own line is sent directly.

### The queue-time line is an actor-only preview
`release_intent` is printed when `charge` is *queued* while you are holding someone. Nothing has happened to the hold yet; the release itself resolves a round later in `_release_grapple_for_charge`. Telling the victim or the room then would describe a world that does not exist. So the door passes `audiences=("actor",)` **and** the phase's one variant authors empty strings for `victim_msg` and `observer_msg`. Either would be enough alone; both are there so neither a new caller nor a new variant can leak the preview by accident. An empty message is never coloured (`_apply_color`, `world/combat/messages/__init__.py`), so the unused audiences produce nothing at all.

### Why three beats keep bespoke prose
No bank phase carries their meaning, so routing them through it would misdescribe what happened.
- *Consensual hold*: the `hit` variants are all violent shoot-ins, vises and trapped victims. A `grab`-trusted or free-path hold (#3363, `TRUST_AND_CONSENT_SPEC` §3) is uncontested: no roll was made, nobody chose violence, and both parties end up yielding. Its three lines say so plainly.
- *Join and takeover*: both are three-party beats that must name the *current grappler* or the *third victim* ("wrestles {target} away from {grappler}", "forcing them to release {victim}"). Bank lines have only an attacker and a target; there is no slot for the third person, and dropping them would make the message lie about who lost the hold.

### Rendering rules (player-visible)
- **Colour is the grapple's own.** `_apply_color` (in `get_combat_message`, `world/combat/messages/__init__.py`) handles `weapon_type == "grapple"` before the attack phase lists. `hit`, `release` and `escape_hit` are `|g`; `miss`, `escape_miss`, `release_charge`, `release_charge_away`, `release_jump`, `release_blast`, `release_intent` and `release_edge` are `|y`. Green is a hold taken, kept or let go on purpose; yellow is a grip lost or about to be. A hold is not a wound, so this is green and yellow (as the consensual hold's lines also are), not the attack palette's red and white. The `grapple_damage_*` phases are not named there, so if the damage exchange is ever built they will be uncoloured until someone decides what a damaging grapple should look like — a question for #3285, not a bug to patch blind.
- **Names arrive bare and the sentence takes the capital.** Every rendered line goes through `capitalize_first` once (`get_combat_message`), so a victim line reads "You stumble as a lanky man ties you up!" and an attacker line that opens on the target reads "A lanky man finds themselves trapped in your unyielding grapple!". This is bank-wide — see `specs/COMBAT_MESSAGE_FORMAT_SPEC.md` §Name Capitalisation.

---

## State Management

### Combat entry fields
Each combatant's entry in the handler carries `grappling_dbref` (who this character holds), `grappled_by_dbref` (who holds this character), `is_yielding`, and `target_dbref`, alongside the other combat fields.

### Rules the state keeps
1. One grappler holds one victim.
2. The two cross-references match.
3. Everyone in a grapple is in the combat.
4. Grappling means proximity.

### State Cleanup System: `validate_and_cleanup_grapple_state`
Runs at the start of every combat round and whenever a combatant is added. It is not run on removal or at handler shutdown; other cleanup handles those.

It clears:
- references to deleted characters, and self-grapples;
- holds on or by anyone not in the fight, dead, or in another room;
- mismatched cross-references. A victim whose `grappled_by` names someone who is not holding them loses it; a grappler's `grappling` is copied onto a victim whose `grappled_by` does not match it. The grappler's field is the one source of truth (#2486).

---

## Integration

### Combat round order
1. Grapple state is validated once (`validate_and_cleanup_grapple_state`).
2. Each combatant then acts in initiative order:
   - a yielding character can only release, advance, retreat or charge; anything else spends the turn;
   - a held, non-yielding character spends the turn on the auto-escape contest;
   - everyone else runs their queued action (grapple, takeover, join, release, movement) or attacks.

### Action restrictions
- **Being grappled**: limited to escape, talk and yielding actions; cannot attack your grappler.
- **Grappling someone**: can advance and retreat with the victim; other actions are limited.

### Proximity
- Creating a grapple always sets up proximity, and grappling keeps it.
- Proximity stays after a grapple ends.
- A drag through an exit, or a drag-advance, sets up the pair's own proximity in the new room and nothing else (`_do_advance_move` in `world/combat/movement_resolution.py`, `add_combatant` in `world/combat/utils.py`). A same-room `advance` sets up the advancer↔target link alone (`_resolve_advance_same_room`) and does not involve the victim.
- Retreat keeps the victim link and breaks every other.
- The victim gaining the grappler's proximity to others is 📋 UNBUILT (open on #3285); see Proximity Inheritance under Unbuilt.

### Yielding
- The grappler auto-yields on a contested grapple (restraint intent); the victim stays non-yielding (resistance).
- Each can change their own yielding state.
- Non-yielding victims auto-attempt escape.
- Both yielding: no auto-resistance. Yielding grappler, non-yielding victim: the victim resists. Neither yielding: violent mode.

---

## Unbuilt

### Proximity Inheritance — 📋 UNBUILT (open on #3285)
- **Principle**: the victim inherits all of the grappler's proximity relationships.
- **Timing**: after a successful advance, retreat or charge.
- **Mechanism**: copy the grappler's proximity set to the victim.
- **Rationale**: the victim is dragged along and gains the same positioning.
- It was to be consistent across advance, retreat and charge, and handle multi-character scenarios.

Nothing copies a proximity set from one character to another; a dragged victim arrives in melee with their grappler and nobody else. Whether this is still wanted is open (see Not decided).

### Grapple damage exchange — 📋 UNBUILT (open on #3285)
In violent mode both parties could take and deal damage: grapple damage hits (control damage during the struggle) and grapple damage misses (failed attempts to harm). The `grapple_damage_hit` / `grapple_damage_miss` / `grapple_damage_kill` banks (37 variants) exist in `world/combat/messages/grapple.py`, and the phase-colouring lists in `get_combat_message` know their names, but nothing requests them; there is no damage exchange for them to narrate. Whether it was ever meant to ship is not decided (see Not decided).

### Escalation when the pair is attacked — 📋 UNBUILT (open on #3285)
An attack on the grappling pair was to escalate the grapple to violent mode. Being attacked changes nobody's yielding state.

### Proposed grenade human shield — 📋 UNBUILT (not decided whether this still stands over the built fixed split)
Before damage is applied to characters in a grenade's proximity:
1. **Grappling check**: for each character in the explosion's proximity list who is grappling someone,
2. **Shield chance**:
   ```
   Base shield chance: 30% (reduced from attack-based 40%)
   + Grappler Motorics: +5% per point above 1
   + Victim resistance:
     - yielding victim: +10% (easier to position as blast shield)
     - non-yielding victim: -10% (struggling against positioning)
   - Area effect: -10% (harder to shield against explosions)
   ```
3. **Shield success**: the grappler takes no explosion damage; the victim takes the grappler's full explosion damage plus their own; explosive-specific messages.
4. **Shield failure**: both take normal explosion damage.

Messages:
- Grappler: `"You instinctively use {victim} to shield yourself from the {grenade} blast!"`
- Victim: `"You are forcibly positioned to absorb the {grenade} explosion meant for {grappler}!"`
- Observers: `"{grappler} uses {victim} as a blast shield against the {grenade} explosion!"`

The goal includes balancing the tactical opportunity against moral consequences.

### Medium priority — 📋 UNBUILT (no issue)
- **Enhanced contest system**: modifiers for different situations; fatigue for extended grapples; environmental factors.
- **Performance optimization.**

### Low priority — 📋 UNBUILT (no issue)
- **Advanced grapple moves**: submission attempts; position-based modifiers; team grappling.
- **Grapple specialization**: character-specific grappling styles (character customization); equipment modifiers; training-based improvements.

---

## Not decided

1. Should grappling someone new while already holding someone be refused, instead of releasing the first hold? (#3285)
2. The walk door and the advance door check "targeted by others" differently. Which rule should both follow? (#3239)
3. Was a grapple damage exchange ever meant to ship — so are the three `grapple_damage_*` banks pending content or dead weight? If it ships, what colour should a damaging grapple be? (#3285)
4. Should the explode-in-the-holder's-hands branch apply the grappler/victim shield? (#3285)
5. Is proximity inheritance still wanted, or was it abandoned in favour of the pair-only proximity the drag and advance paths set up? (#3285)
6. Should a mutual grapple exist? (not decided)
7. Does the probabilistic grenade shield proposal still stand over the built fixed split? (not decided)

### Edge cases to consider
- **Chain grapples**: A→B→C dependency chains; preventing and detecting circular references; cascade releases, when one grapple affects others.
- **Team grappling**: two people grappling the same target; helping a teammate with a grapple; attacking grappling pairs.
- **Handler boundaries**: characters ending up in different handlers; a grapple bringing handlers together; handlers shutting down during a grapple.
- **Movement**: room traversal requiring victim consent; what happens when a drag fails; escapes mid-transition.
- **State corruption**: orphaned references; inconsistent states; graceful degradation on data loss.
- **System failures**: grapple preservation on handler crashes; state synchronization on network issues; performance under load.

---

## Related documents
- `specs/TRUST_AND_CONSENT_SPEC.md` §3 — consensual holds.
- `specs/COMBAT_MESSAGE_FORMAT_SPEC.md` — bank format, §Third parties — `extra_chars`, §Name Capitalisation, §Special Extended Phases.
- `specs/proposals/STEALTH_AND_DETECTION_SPEC.md` §6.1 — ambush initiative.
- `specs/COMBAT_SYSTEM.md` — target removal and auto-retarget.
