# Throw Command Implementation Specification

`throw` serves two purposes: moving a utility object to a person or another
room, and deploying a weapon in combat. It works with the existing proximity,
aim and combat systems. Around it sit the grenade commands: `pull` (pin),
`catch`, `rig`, `defuse`, `detonate`, and the enhanced `drop`.

## Where the code lives

- `commands/CmdThrow.py` — the command surface only: parsing, validation, and
  the origin announcements for `throw`, `pull` and `catch`.
- `world/combat/throwing.py` — the physics engine: flight timers, landing
  resolution, proximity assignment, grenade deflection, magnetic target
  selection. Anything that launches an object uses it directly (the rigged
  grenade triggers do).
- `commands/explosion_utils.py` — the explosion machinery, including
  `start_grenade_ticker` (the sticky-aware countdown) and `unrig_grenade`.
  `start_grenade_ticker` and `start_standalone_grenade_ticker` are candidates
  for unification.
- `CmdRig` lives in `commands/CmdExplosives.py` (as does `detonate`); `CmdDrop`
  in `commands/CmdInventory.py`; `drop_to_room` in `commands/combat/jump.py`.
- Behaviour is pinned by the characterization suite
  `world/tests/test_throw_characterization.py` (parsing, validation, flight
  lifecycle, landing/proximity, hit resolution, deflection, pull, catch). That
  suite is the contract for any change to the system (#471).

**Exception policy.** The engine has no broad excepts. A failure in the
flight-timer callback surfaces in the server log; flight-state cleanup runs in
`finally`, so a landing bug can never strand an object in the "flying" state.
The explosion code (`commands/explosion_utils.py`) has several broad excepts;
the chief deliberate one is the grenade ticker's failsafe: a live grenade must
never become a permanent dud, so on a ticker error it logs and explodes.

## Command syntax

```
throw <object>                    # Throw randomly in current room (if occupied) or in aimed direction
throw <object> at <target>        # Throw at specific target (requires aim for cross-room)
throw <object> to <direction>     # Throw to adjacent room in specified direction (random proximity)
throw <object> to here            # Lands on the ground in current room, near nobody
```

A bare `throw <object>` lands near a random person; `throw <object> to here`
lands near nobody.

Syntax priority:
1. **`throw <object> at <target>`**: specific targeting (requires aim for cross-room).
2. **`throw <object> to <direction>`**: directional throwing (no aim required).
3. **`throw <object> to here`**: current room, lands on the ground near nobody.
4. **`throw <object>`**: falls back to the aimed direction, or a random person in the current room.

## Validation

1. **The object must be wielded** (held in a hand under the Mr. Hand system), not just in inventory.
2. **The object must exist** and be accessible to the thrower.
3. **A target** (if given) must exist in the aimed room or the current room.
4. **A direction** (if given) must be a valid, traversable exit: any exit with a destination other than this room; an exit that loops back is refused. There is no lock or access check (📋 UNBUILT (no issue), see Unbuilt).
5. **`here`** is handled as an explicit current-room throw.
6. **Not while channeling** (#3376).
7. **Not integrated cyberware**: "<item> is part of your body — you can't throw it."
8. **Not while grappled**: "You cannot throw while grappled."
9. **Grenades**: a pin is not required to throw. An unpinned grenade flies as an inert object. Only an already-exploded grenade (timer <= 0) is refused; a missing timer counts as not expired. `validate_grenade_throw` in `commands/CmdThrow.py` does this, and it keeps the explosion-in-hands protection.

### Naming the object (`throw`, `pull`, `catch`)

All three commands name their object with the core matcher,
`caller.search(name, candidates=pool, quiet=True)` (#2537, #3783), scoped to
their own pool: the items in the hands for `throw` and `pull`, the room's
in-flight objects for `catch`. So they read names the way every other command
does:

- An exact key or alias wins over a partial name (`pipe` throws the pipe, not
  the pipe bomb; `c4` finds the charge aliased `c4`).
- A partial name must START a word of the key or an alias: `frag`, `m67` and
  `hdg frag` find the *HDG M67 fragmentation grenade*; `nade` does not.
- Ordinals pick a twin: `2nd grenade`, `second grenade`, `grenade-2`. With
  several matches and no ordinal, the first by creation order is used.
- `me` / `self` / `here` are not in any of these pools, so they find nothing.

The not-held check that chooses between *"You must be wielding X"* and *"You
don't have X"* uses the same matcher over the inventory, so the two lookups
cannot disagree. `catch` refuses an empty name before searching.

## Parsing

### Design philosophy
- **User-friendly over rigid**: accommodate user intent rather than forcing exact syntax.
- **Intelligent interpretation**: parse context to resolve ambiguous commands.
- **Graceful error recovery**: auto-correct common mistakes when possible.
- **Helpful feedback**: give specific suggestions when parsing fails.
- **Building standards**: avoid naming conflicts between exits and characters by design.

### Parsing priority
1. **"at" keyword**: `throw knife at bob` → targeted throwing.
2. **"to" keyword**: `throw knife to east` → directional throwing.
3. **"here"**: `throw knife to here` → current-room throwing.
4. **Fallback**: `throw knife` → use aim state or current room.

### Recovery and edge cases
- **at/to confusion**: only `at here` is converted (`throw knife at here` → `throw knife to here`, silently). `throw knife to bob`, where "bob" is not an exit, checks for a character and replies "Did you mean 'throw <object> at <person>' instead?"
- **`to` lookup**: `to` takes the first match of a plain search of the room, whatever it is. Exit priority over character names is 📋 UNBUILT (no issue).
- **`at` lookup**: `at` looks only for a person, here and then in the aimed room. With no aim set, `throw knife at east` replies "You must aim in a direction first to throw at targets in other rooms."; with aim set, "You cannot find 'east' to throw at." Treating "east" as a direction when no character "east" exists is 📋 UNBUILT (no issue).
- **Name conflicts**: building/design should prevent exit and character name conflicts.
- **Multi-word names**: handle unquoted multi-word names where possible; `throw battle axe to north` parses "battle axe" as the object and "north" as the direction.
- **Graceful degradation**: if complex parsing fails, fall back to a simpler interpretation; error messages differ by what the parser detected.

## Throwing weapons, utility objects, improvised weapons

- **Throwing weapons** (`db.is_throwing_weapon = True`): `throw` hands every
  such object off. Targeted (`throw <weapon> at <target>`), it runs
  `attack <target>` with it for full combat resolution, an ordinary attack.
  Untargeted, it gives a guidance message. The weapon never leaves the hand
  and nothing is consumed. User confirmed this is the correct design
  (#471). A throwing weapon therefore cannot be thrown to a direction, to
  `here` or with no target: `throw` refuses and it stays in hand. The refusal
  tells the player to use `throw <weapon> to <direction/here>` to discard it,
  which is refused the same way (`CmdThrow.func`; code defect, no issue).
- **Utility objects** (all other objects): bounce harmlessly off targets and
  transfer between rooms. Today any thrown object that is not a sticky grenade
  bounces off its target and does no damage, in or out of combat.
- **Improvised weapons**: non-throwing weapons used in combat deal base
  improvised damage, and objects thrown at someone already in combat always
  use improvised weapon damage — 📋 UNBUILT (no issue).

The detection flow first intended for this (check `is_throwing_weapon`; if
true, enter combat mode with weapon damage in flight; otherwise utility mode)
was replaced in #471: the weapon-flight path was deleted and a throwing weapon
redirects to `attack`. `resolve_weapon_hit` survives as the sticky grenade's
stick/bounce/damage resolver, reached through landing. Ammo/recovery tracking
for thrown weapons (alongside gun ammo) is the missing piece before a true
weapon-flight path would be worth wiring back (see Unbuilt).

## Aim integration

```
aim east           # Establish direction
throw knife at bob # System finds Bob in aimed room (east)
```

```
throw knife to east  # Throw to adjacent room eastward (no aim required)
throw keys to here   # Lands on the ground in current room, near nobody
```

- **Aim is kept**: throwing does not break an existing aim.
- **Cross-room targeting** needs an active aim to throw `at <target>` in an adjacent room. Aimed over an edge, the target is looked for on the ground the edge drops to (`world.gravity.room_through`, #3589); the object flies into the air cell beyond the edge and falls from there (#3579).
- **Directional throwing** (`to <direction>`) needs no aim.
- **Same-room** `at <target>` and `to here` need no aim.

## Flight

- **Duration**: 1/3 of a combat round (~2 seconds; a combat round is 6 seconds), by Evennia's `utils.delay()`.
- **Concurrent flights**: several objects can be in flight at once, per room and per player; each is handled independently.
- **State**: flying objects are tracked in the origin room's `ndb.flying_objects` list (non-persistent). Cleanup is automatic on landing, and manual on errors or disconnections. There is no hard limit on flying objects; one may be added if needed.
- **Thrower leaves the room** during flight: the object continues to its destination. **Thrower disconnects**: the flight continues.
- **Object deleted** during flight: its flight state is cleaned up.
- **Reload during flight**: the landing is cancelled. The flight timer and the room's flying list are lost, and the object stays in the thrower's inventory (it never left it, #2538), out of their hands. Nothing is lost.

### Room announcements
1. **Origin room**: "Alice throws a rock east" or "Alice tosses a rock nearby". The thrower reads "You throw a rock."
2. **During flight**: the object appears in the origin room's description as "A <object> is flying through the air." (added by the room's `return_appearance()` immediately, removed on landing; several flying objects are each listed).
3. **Destination room** (cross-room): "A rock flies in from somewhere". `get_arrival_direction` always returns "somewhere"; naming the real direction is 📋 UNBUILT (no issue).
4. **After landing**: the object leaves the flight description and appears in the room normally.

Only the current room sees a flying object; there is no cross-room
visibility. Announcements run origin → flight → destination.

| Syntax | Origin announcement |
|---|---|
| `throw rock to east` | "Alice throws a rock east" (the direction as typed) |
| `throw rock at bob` | "Alice throws a rock at Bob" (same room) or "Alice throws a rock east at someone" (cross-room, the aimed direction) |
| `throw keys to here` | "Alice tosses a keys nearby" (the article "a" is fixed in the template) |
| `throw rock` | "Alice throws a rock east" (if aimed) or "Alice tosses a rock nearby" (no aim) |

## Landing and proximity

- **Occupied room**: equal chance to land in proximity to any character the thrower can perceive, other than the thrower — `random.choice()` over the destination room's characters less the thrower and anyone the thrower cannot perceive (`select_random_target_in_room`). Each eligible character has equal probability regardless of their current proximity state. The thrower is never picked, nor anyone hidden from the thrower (#3763). Exception: `throw <object> to here` lands near nobody.
- **Untargeted sticky grenade**: goes to whoever wears the most magnetic chest armour that meets its thresholds, falling back to a random person.
- **Empty room**: the object lands on the ground with no proximity.
- **Same-room throw**: lands outside the thrower's proximity unless it lands near someone in the thrower's existing proximity.
- **Proximity inheritance**: if the chosen character has proximity relationships, the object inherits them. For a grenade, ALL characters in that person's proximity are added to the grenade's proximity.
- **Target leaves the room during flight**: the object lands where the target was. The "bounces harmlessly off" line is still sent to the target in their new room, a sticky grenade still rolls to hit them there, and the object's proximity list still names them (`handle_landing` in `world/combat/throwing.py`; code defect, no issue).

## Combat integration

- **Turn cost**: throwing an object or a grenade in combat costs no turn, and `throw` never touches the combat handler except to refuse a grappled thrower. A throwing weapon thrown at someone runs `attack <target>`, an ordinary attack. Combat throwing that always consumes the combat turn (the skip-turn mechanic from `flee`, with its standard skip-turn messaging) is 📋 UNBUILT (no issue; not decided whether still wanted).
- **Non-combat throwing**: no turn cost.
- **After throwing**: the thrower can take non-combat actions (inventory management, wield, etc.).
- **Damage**: throwing weapons use the weapon damage system (`1d6 + weapon.db.damage`) through `attack`, with standard ranged hit/miss. Utility objects do no damage. Improvised base damage (`1d6`) is 📋 UNBUILT (no issue). The only thrown object that does damage of its own is a sticky grenade.
- **Messages**: there is no shared "throwing" message category; each throwing weapon has its own message file (`world/combat/messages/throwing_knife.py`, `throwing_axe.py`). Separate messages for improvised vs. proper throwing weapons are wanted.
- **Weapon throws**: enter combat if not already in combat; may establish proximity with the target on a hit; handled by the turn-based combat handler like other ranged weapons.
- **Invalid combat state**: a missing combat handler is handled gracefully.

## Grenades

### Activation
- **Pin**: `pull pin on <grenade>` starts the fuse timer immediately. Its length is `db.fuse_time` (default 8 seconds). State is tracked with `db.pin_pulled` and the timer state.
- **No pin needed to throw**: pinned (live) and unpinned (inert) grenades can both be thrown; an unpinned grenade is an inert object, for tactical misdirection. The activation design first required `pull pin on grenade` before throwing; that requirement was removed for tactical flexibility.
- **Throw window**: after pulling the pin the player has the fuse time to throw, or the grenade explodes in hand.
- **Hand explosion**: if the timer expires while the grenade is in hand, it explodes and damages the holder: "The grenade explodes in your hands!"
- **Multiple timers**: many grenade countdowns run at once, each with proper cleanup.

### Landing, area and retreat
- **Proximity creation**: landing creates a danger zone using the proximity mechanics. Everyone in the chosen person's proximity inherits the grenade's proximity, so everyone fighting that person is in it.
- **Retreat escape**: the standard `retreat` command removes a character from grenade proximity, and leaving the room escapes the blast. This is the design. **⚠ The code does not honour it for a thrown or dropped grenade (#2540).** `retreat` is a combat-handler action: it needs a live handler and gates on `ndb.in_proximity_with`, the *melee* set, and `break_proximity` touches only that set. `resolve_retreat` does read the character's universal `ndb.proximity`, but the throw path writes only the **grenade's** side of that link, so it reads empty and retreat cannot see the grenade at all. `drop` has the same gap — it appends the dropper to the object's list and never writes the character's. The one place that writes both ends is `CmdDefuse`'s `establish_mutual_proximity`, reached when someone walks up to a grenade to defuse it; there is no `place` command, so #2540's "a placed grenade escapes correctly" describes that defuse-approach path rather than a placement one. The design stated here is right and the code is the defect — fix the link (and fix it for `drop` too), do not re-spec the escape.
- **Chain reactions**: several grenades create overlapping retreat scenarios and positioning puzzles. See Universal proximity.

### Catch (hot potato)
`catch <object>` intercepts a thrown object mid-flight, including a live
grenade, which can then be thrown straight back within its timer. Only people
in the room the object was thrown from can catch it, the thrower included,
during its 2-second flight; people in the room it is flying into cannot. The
catcher needs a free hand, and the object ends up in it. A successful catch
cancels the pending flight and clears its flight state (`catch_object`). The
chance is a flat 60%, with no stat roll; on a miss the object flies on and
lands as normal.

### Deflection
The person a thrown grenade is landing near can bat it away if they hold a
melee weapon (an item tagged `weapon` in category `type` that is not ranged).
They roll Motorics against 10 minus `deflection_bonus` × 20 (#2493). On
success the grenade flies back to the room it came from 60% of the time when
that is another room (at the thrower, if still there); otherwise it goes out a
random exit, and with no exit it lands where it is. Nobody can deflect while
grappling or grappled, and a grenade with `db.impact_detonation` cannot be
deflected (`check_grenade_deflection` in `world/combat/throwing.py`).

### Sticky grenades and remote charges
A grenade with `db.is_sticky` that lands near someone rolls to hit (70%), then
to clamp onto their outermost chest armour; if it hits but does not stick, the
hit does `1d6 + db.damage` (`resolve_weapon_hit`). Remote charges go off with
`detonate` (`commands/CmdExplosives.py`).

### Rigging
- `rig <grenade> to <exit>` traps an exit; the grenade goes off when someone traverses it. The rigger is immune: trap setters pass safely through their own rigged exits.
- Refusals: "There is already a grenade rigged to that exit."; "There is no exit '<exit>' to rig a trap to."; "You cannot rig a grenade that already has its pin pulled."
- **Visibility** (`rig_grenade`): `rig` leaves the grenade lying in the room, sets `db.integrate = True`, `db.integration_priority = 3` and an `integration_desc` of "A <grenade> is rigged to the <exit> exit with a barely visible trip wire.", and saves the previous three in `original_*` for `unrig_grenade` to restore.
- **Detection**: by the room's own prose (above) and by `scan` for the rigger only (#3351).
- **Disarming**: `defuse` takes the trap off its door through `commands/explosion_utils.unrig_grenade` — the one restore door.
- **A trap belongs to the DOOR OBJECT**: `exit.db.rigged_grenade` on the rigged exit and its return exit, `grenade.db.rigged_to_exit` back. A door that is destroyed (a builder's @destroy, a room deletion cascading through `clear_exits`) takes its trap down in `Exit.at_object_delete` through the same door: the grenade goes loose and unarmed where it lay, its prose restored, and the room hears "The trip wire on the X goes slack." The far side of the same doorway (the return exit) only drops its record. Doors that legitimately change what lies beyond them — the crane car's, the elevator's — are permanent objects that are re-pointed, never rebuilt, so a trap rides the car (`CraneContainer`, #3560; the elevator works the same way).

### Defuse
- `defuse <grenade>`: a manual attempt with a skill check (Intellect + Motorics) under time pressure: difficulty rises as the countdown approaches zero. Defusing a live charge you are not yet near searches the room for it and sets up proximity on the fly (`establish_mutual_proximity`).
- **Auto-defuse**: entering the proximity of a live grenade (on room entry) makes an automatic attempt, like D&D-style trap detection.
- **Early detonation**: a failed manual attempt has a 30% chance to set the grenade off at once; a failed auto-defuse, 10%.
- **One attempt** per character per grenade.
- **Rigged grenades** have a different difficulty for trap disarmament than for timed defusal.
- **Cleanup**: a defused grenade has all its proximity relationships cleared (combat and universal), which prevents chain reactions.

### Explosions
- Explosion paths: timer, hand, rigged, failed defuse.
- Null checks prevent iteration errors during explosions; NDB attribute comparisons check for None before integer operations.

### Tactics
- **Catch and re-throw**: thrown live grenades can be caught and thrown back.
- **Area denial**: dropping a live grenade creates a temporary danger zone.
- **Exit rigging**: grenades rigged against exits trigger when traversed.
- **Chain reactions**: exploding grenades can trigger other nearby grenades.

## Explosive object properties

All explosive behaviour is driven by object properties, checked during command
execution (not at object creation). A missing property defaults to a safe
value (no damage, no explosion).

- **`db.is_throwing_weapon`**, **`db.is_explosive`**: the identifying flags.
- **`db.fuse_time`**: seconds from pin pull to explosion (e.g. 8 for a standard grenade).
- **`db.blast_damage`**: damage dealt to characters in proximity when it explodes.
- **`db.chain_trigger`**: whether this explosive can trigger other nearby explosives.
- **`db.requires_pin`**: whether activation requires pin pulling (vs. impact detonation).
- **`db.dud_chance`**: probability of failing to detonate (0.0 = never, 1.0 = always).
- **`db.impact_detonation`**: today it only stops deflection.
- **`db.blast_radius`**: number of proximity "hops" an explosion affects (future expansion) — 📋 UNBUILT (no issue): nothing reads it.

### Explosive types the properties allow
- **Standard Grenade**: `fuse_time=8, blast_damage=20, chain_trigger=True, requires_pin=True`
- **Dud Grenade**: `dud_chance=1.0` (training/distraction use)
- **Hair Trigger**: `fuse_time=3, dud_chance=0.3` (fast but unreliable)
- **Impact Grenade**: `fuse_time=0, blast_damage=15, requires_pin=False` (explodes on landing) — 📋 UNBUILT (no issue): nothing explodes on landing
- **Smoke Grenade**: `fuse_time=3, blast_damage=0` (creates visibility/movement effects) — 📋 UNBUILT (no issue)
- **Flashbang**: `fuse_time=2, blast_damage=5` (stun/disorient effects) — 📋 UNBUILT (no issue)
- **Cluster Bomb**: `chain_trigger=True, blast_radius=2` (affects wider area) — 📋 UNBUILT (no issue): nothing reads `blast_radius`

## Universal proximity

Characters and objects share the same proximity mechanics. In Evennia,
characters inherit from objects, so proximity is handled uniformly. This lets
grenades work without special cases for different object types.

There are two proximity systems: combat proximity (`ndb.in_proximity_with`,
the melee set) and universal proximity (`ndb.proximity`), for different uses.
Movement between rooms cleans up both.

Principles:
- **Shared proximity space**: characters and objects can be in the same proximity relationships.
- **Bidirectional relationships**: characters can be in proximity to objects, and objects to characters. (The throw and drop paths write only the object's side; see #2540 under Grenades.)
- **Inheritance**: an object landing near a character inherits all of that character's proximity relationships.
- **Consistency**: the same proximity rules for all entities; reuse of the existing proximity infrastructure.
- **Universal retreat**: `retreat` escapes any proximity, character or object (not honoured by the code for thrown or dropped grenades, #2540).
- **Invalid state**: if proximity state becomes invalid, the system degrades gracefully.

### Drop
When any object is dropped, `drop_to_room` (`commands/combat/jump.py`) gives
it an `ndb.proximity` list if it has none, and `drop` (`CmdDrop` in
`commands/CmdInventory.py`) adds the dropper to it — only the object's side
(#2540). This applies to all objects, not just grenades, with no special case
per object type, and is what makes a dropped live grenade an area-denial tool.

### Example
```
Initial state: Alice fighting Bob and Charlie (all in mutual proximity)
Throw: Dave throws grenade, lands near Bob
Result: Grenade proximity = [Alice, Bob, Charlie] (inherited from Bob's proximity)
Escape: Any character can "retreat" to leave grenade proximity (⚠ not honoured by the code for a thrown grenade, #2540)
```

### Chain reactions
A chain reaction fires when an exploding grenade with `db.chain_trigger` has
another explosive in its blast list; that explosive goes off a second later.
The list gains an explosive only through a person whose own list holds one,
which only the `defuse` approach writes. A thrown object only ever lands near
a person, never near another grenade. Grenades landing near other grenades and
inheriting their proximity lists is 📋 UNBUILT (no issue); the web it would
make:

```
Grenade A: proximity = [Alice, Bob]
Grenade B: lands near Grenade A
Grenade B: proximity = [Alice, Bob, Grenade A]
Grenade A explodes: triggers Grenade B (in proximity)
Grenade B explodes: affects [Alice, Bob] (inherited proximity)
```

## Mr. Hand integration

- `hands` in `typeclasses/characters.py` is a derived property, not a stored attribute: its slots are the species' grasping containers (such as `left_hand`, `right_hand`) minus any that are severed or dead, and its values come from the `held_items` AttributeProperty. For a human it is `{"left_hand": None, "right_hand": None}`. Read it, change a copy and assign the copy back; changing it in place does nothing.
- The dictionary is keyed by grasping container, so it supports any hand names (third_hand, tail, etc.) and dynamic anatomy.
- `wield_item()`, `unwield_item()` and `list_held_items()` manage held items.
- **Throwable**: the object must be in `caller.hands.values()`. It is thrown from whichever hand holds it.
- **After the throw**: the object is removed from the hand by copying `caller.hands`, setting that hand to `None` in the copy and assigning the copy back (`CmdThrow.remove_from_hand`). The object is not removed from the inventory (#2538, below).

## Error messages

- **Nothing named**: "Throw what? Use 'throw <object>' or 'throw <object> at <target>'."
- **A body with no `hands` property**: "You must be holding something to throw it."
- **Every hand gone**: "You have no hands to throw with."
- **Object not found**: "You don't have '<object>' to throw."
- **Object not wielded**: "You must be wielding '<object>' to throw it."
- **Target not found**: "You cannot find '<target>' to throw at."
- **No aim for cross-room targeting**: "You must aim in a direction first to throw at targets in other rooms."
- **Invalid direction**: "There is no exit '<direction>' to throw through."
- **`to` used with a character name**: "Did you mean 'throw <object> at <target>' instead?"
- **Grappled**: "You cannot throw while grappled."
- **Cyberware**: "<item> is part of your body — you can't throw it."

## Known code defects

These are places where the code does not do what this spec describes. This
spec describes the correct intent; do not re-spec around them.

- **#2538** — a thrown object never leaves the thrower's inventory during
  flight, so a cooked grenade detonates in the thrower's hands at double
  damage in the wrong room, and the item stays re-wieldable mid-flight.
  Nothing here sanctions that; the Throw window and Hand explosion rules
  describe the behaviour that was wanted.
- **#2540** — the throw path writes only the grenade's side of the
  universal-proximity link, so movement and `retreat` cannot escape a
  **thrown** grenade's blast; `drop` has the same gap. See Grenades.
- Throwing-weapon discard refusal loop (no issue) — see Throwing weapons.
- Target leaves the room during flight (no issue) — see Landing and proximity.

## Decisions

- **Two-handed weapons**: should throwing a two-handed weapon require both hands to be free/wielding it? **DECIDED**: Not implemented yet, future consideration.
- **Improvised weapon damage**: should non-throwing weapons deal reduced damage when thrown? **DECIDED**: Yes, for now all improvised weapons use base damage. Future refinement will differentiate materials. 📋 UNBUILT (no issue): no improvised damage path exists; a thrown object that is not a sticky grenade bounces off and does no damage.
- **Accuracy system**: should throwing have hit/miss mechanics like other ranged weapons? **DECIDED**: Yes, throwing in combat uses normal ranged weapon logic with dedicated message category. (Each throwing weapon has its own message file, not a shared category; see Combat integration.)
- **Critical hits**: can thrown weapons score critical hits? **DECIDED**: Not initially, but perfect for future improvised weaponry mechanics.
- **Fuse timing**: should grenades have variable fuse lengths? **DECIDED**: Variable timing based on `object.db.fuse_time` property.
- **Dud chances**: should grenades have failure probability? **DECIDED**: Based on `object.db.dud_chance` property.
- **Blast radius**: how many characters can be in grenade proximity simultaneously? **DECIDED**: Driven by `object.db.blast_radius` for future expansion. 📋 UNBUILT (no issue): nothing reads `blast_radius`.
- **Chain explosions**: should grenades be able to trigger other grenades? **DECIDED**: Based on `object.db.chain_trigger` property.
- **Exit rigging mechanics**: how should rigged grenades be detected/disarmed? **DECIDED** (recorded 2026-09-21, #3560): see Rigging (detection, disarming, a trap belongs to the door object).
- **Rig visibility**: are rigged grenades visible in room descriptions? **DECIDED** (`rig_grenade`; recorded 2026-09-21): yes; see Rigging.
- **Throwing weapons redirect to `attack`**: User confirmed this is the correct design (#471); see Throwing weapons.

## Unbuilt

Each of these is wanted and not built. All are 📋 UNBUILT (no issue) unless
marked otherwise.

- **Direction lock/access check**: a direction must be traversable; today no lock or access check is made.
- **Exit priority**: `throw knife to northeast` always prioritizes exits over character names.
- **Smart fallback**: `throw knife at east` treats "east" as a direction if no character "east" exists.
- **Improvised damage**: non-throwing weapons used in combat deal base improvised damage (currently `1d6`); objects thrown at someone already in combat always use improvised weapon damage.
- **Turn consumption** (no issue; not decided whether still wanted): combat throwing always consumes the combat turn, using the skip-turn mechanic from `flee` and its standard skip-turn messaging.
- **Arrival direction**: the destination room's line names the incoming direction ("flies in from <direction>"), not "somewhere".
- **Permission checks**: respect room access permissions for object transfer.
- **Flight error recovery**: if the flight timer fails, the object defaults to landing in the origin room.
- **Room disconnection**: if the destination becomes inaccessible during flight, the object lands in the origin room.
- **Orphaned flight objects**: a cleanup routine to remove stale flying-object references.
- **Network issues**: a timeout mechanism for flight completion.
- **Grenade-to-grenade proximity**: grenades landing near other grenades inherit their proximity lists (see Chain reactions).
- **`db.blast_radius`**: proximity "hops" an explosion affects; nothing reads it (Cluster Bomb depends on it).
- **Impact Grenade** (explodes on landing), **Smoke Grenade** (visibility/movement effects), **Flashbang** (stun/disorient effects).

Future features, without issues:
- **Ammo/bundle system**: throwing weapons use the bundle system with ammo tracking, alongside gun ammo; limited throwing-weapon uses. Today nothing is consumed: a dedicated throwing weapon never leaves the hand.
- **Weapon retrieval**: mechanics for recovering thrown weapons. Not implemented.
- **Material properties**: different damage for different improvised weapons.
- **Door/barrier blocking**: physical obstacles (locked doors, barriers) prevent throwing between rooms.
- **Trajectory calculation**: more realistic flight paths.

Potential future enhancements (advanced grenades):
- Enhanced chain reaction logic with complex proximity webs.
- Multi-type explosive support with specialized effects.
- Advanced rigging mechanisms (pressure plates, tripwires).
- Defuse tool requirements for different explosive types.
- Character specialization bonuses for different grenade types.

Planned weapon retrieval features:
- Thrown weapon recovery mechanics.
- Bundle system with ammo tracking.
- Weapon durability and breaking on impact.
- Material-based improvised weapon damage scaling.

Possible integration points:
- **Identity system**: better target resolution when implemented.
- **Advanced room descriptions**: better object state display.
- **Enhanced aim system**: possibly cross-room aim for throwing only.

## Not decided

### Mr. Hand
1. **Hand preference**: if the object is in both hands, which hand throws it?
2. **Post-throw state**: should the hand remain "ready" for quick-draw of another weapon?

### Combat
3. **Range considerations**: should throwing weapons have range limits or always work cross-room?

### Flight and landing
4. **Interception**: can thrown objects be intercepted by other players/objects during flight? (Players: `catch` and grenade deflection, see Grenades. Objects such as cover or barriers: open.)
5. **Bounce mechanics**: when utility objects "bounce harmlessly," where exactly do they land?
6. **Fragile objects**: should some objects break when thrown (bottles, delicate items)?
7. **Weight considerations**: should heavy objects take longer to throw or fly slower?

### Rooms
8. **Room capacity**: should rooms have limits on simultaneous flying objects?
9. **Environmental effects**: should wind, gravity, or other room effects influence throws?
10. **Blocked exits**: how should locked doors or barriers affect cross-room throwing?
11. **Visibility**: should dark rooms affect throwing accuracy?

### Grenades
12. **Rig command syntax**: should it be `rig grenade to north` or `rig grenade against north exit`?
13. **Multiple rigs per exit**: can multiple grenades be rigged to the same exit?
14. **Timer inheritance**: do rigged grenades keep their original timer or reset when triggered?

### Performance
15. **Flight object cleanup**: how often should orphaned flight references be cleaned up?
16. **Room description caching**: should flying objects invalidate the room description cache?
17. **Concurrent throw limits**: should there be per-player or per-room throw rate limiting?
18. **Memory management**: how long should flight state persist in case of errors?

Also open: whether combat throwing should still consume a turn (see Unbuilt).

Also open: should `throw <object> to here` land near a random person, as the spec once said ("same as first syntax"), or on the ground near nobody, as it does today?

## Related

- Aim, combat handler, `retreat`, `flee`: the combat system.
- `world.gravity.room_through` (edges and air cells).
- `typeclasses/rooms.py` `return_appearance` (flying-object line).
- `typeclasses/characters.py` (Mr. Hand).
