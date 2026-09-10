"""The elevator: landings, a car that is a real room, and a controller.

The CAR model (VERTICALITY_AND_BUILDINGS_SPEC §1.1, decided 2026-07-10):
the car's position is honest world-state. Landings keep a permanent
``elevator`` exit whose destination is always the car, but traversal is
gated on the car being docked there with its doors open. The car's single
``out`` exit is re-pointed to the current landing on arrival and refuses
mid-travel. A call button at each landing summons the car; a panel inside
selects floors. Both are pressed through the ordinary ``press`` command.

The car is a room — riders stay free while it moves (no channeled action;
the CAR moves, not the actor), so scenes can happen in it.

Security seam: ``db.floor_locks`` maps a floor label to its grant file
and is CONSUMED by `_floor_permitted`, which gates `request_floor` and
which the pathfinder consults when routing (`world/spatial/pathfind.py`,
`_neighbors`). The live Constabulary car carries seven sleeve grants on
floor "2". This said "not yet consumed" long after it was — a
maintainer trusting it would have re-implemented the gate or routed
around it (#2626).
"""

from evennia.utils.utils import delay

from typeclasses.exits import Exit
from typeclasses.items import Item
from typeclasses.rooms import IndoorRoom

DOOR_SECONDS = 3
RIDE_SECONDS_PER_FLOOR = 6

#: How long the car stands with its doors open before serving the next
#: queued call.
#:
#: Not zero, and not merely "a moment". A walking NPC only gets a tick
#: every `TRAVEL_STEP_DELAY` seconds (2.0), so a car that arrived and
#: departed on the same beat would satisfy the queue while the person
#: who called it was still standing on the landing — trading a dropped
#: call for a missed one (#3173).
DWELL_SECONDS = 5

DOORS_SHUT_MSG = "The elevator doors are shut. Press the call button."
CAR_MOVING_MSG = "The car is moving. Best wait for the doors."


def car_docked(car, landing):
    """True when `car` sits at `landing` with its doors open."""
    if car is None or landing is None:
        return False
    is_docked = getattr(car, "is_docked_at", None)
    return bool(is_docked and is_docked(landing))


class ElevatorCar(IndoorRoom):
    """The moving room.

    - ``db.floors``: ordered shaft, ``[[landing_room, label], ...]``
    - ``db.current_floor``: index into floors (where the car sits)
    - ``db.moving`` / ``db.target_floor``: in-flight state
    """

    def at_pre_object_receive(self, moved_obj, source_location, **kwargs):
        """Refuse anyone stepping in from a landing the car is not at.

        The doors-are-shut rule lived ONLY in
        `ElevatorDoorExit.at_traverse`, so any exit into the car with a
        different typeclass was an ungated door. Eight of them existed —
        the Brackett Arms landings for floors 8-15 carried plain
        `Exit`s, and walking `elevator` from those floors put you inside
        the car wherever it happened to be (#2610).

        Enforced on the CAR because the car is the thing being entered:
        one gate, no matter how many doors get built onto it.

        Deliberately narrow. It refuses only when the source is a
        landing **of this shaft** and the car is not docked there, so
        every other arrival still works: staff teleports, spawns, an
        object put in by a script, and — importantly — occupants riding
        the car, who never re-enter because the room moves around them.
        """
        # Duck-typed, NOT `isinstance(entry, (list, tuple))`. `db.floors`
        # comes back as a `_SaverList` of `_SaverList`s, and those are
        # list-LIKE but not list SUBCLASSES — the isinstance test is
        # False for every entry, so the landing set came out empty and
        # this gate silently allowed everything. Same trap as #2701 /
        # #2465 / #2468 / #2438 / #2582 / #2676.
        landings = set()
        for entry in (self.db.floors or []):
            try:
                landings.add(entry[0])
            except (TypeError, IndexError, KeyError):
                continue
        if source_location in landings and not car_docked(self,
                                                          source_location):
            try:
                moved_obj.msg(DOORS_SHUT_MSG)
            except Exception:  # noqa: BLE001 — not every mover can be messaged
                pass
            return False
        return super().at_pre_object_receive(moved_obj, source_location,
                                             **kwargs)

    def at_object_creation(self):
        super().at_object_creation()
        self.db.floors = []
        self.db.current_floor = 0
        self.db.moving = False
        self.db.target_floor = None
        self.db.floor_locks = {}
        # The shaft's (x, y) grid column. When set, the car's coordinates
        # are (shaft_x, shaft_y, landing_z) — the car sits IN the shaft at
        # its floor's height, never in the threshold room's cell.
        self.db.shaft_xy = None
        #: Floors with a lit button, in press order (#3173).
        self.db.call_queue = []

    def at_init(self):
        super().at_init()
        # delays don't survive a reload — a car caught mid-ride snaps
        # to where it was headed, doors open, no messages
        if self.db.moving:
            target = self.db.target_floor
            if target is None:
                target = self.db.current_floor
            self._arrive(target, quiet=True)
        elif self.db.call_queue:
            # A car that was STANDING when the server went down still
            # has lit buttons, and the `delay` that would have served
            # them died with the reload. Without this the queue is a
            # permanent record of people who never got picked up
            # (#3173).
            delay(DWELL_SECONDS, self._serve_queue)

    # ------------------------------------------------------------------
    # state
    # ------------------------------------------------------------------

    def floor_index(self, room_or_label):
        """Resolve a landing room or a panel label to a floors index."""
        for i, entry in enumerate(self.db.floors or []):
            landing, label = entry[0], entry[1]
            if room_or_label is landing:
                return i
            if str(room_or_label).strip().lower() == str(label).lower():
                return i
        return None

    def current_landing(self):
        floors = self.db.floors or []
        idx = self.db.current_floor
        if idx is None or not 0 <= idx < len(floors):
            return None
        return floors[idx][0]

    def is_docked_at(self, landing):
        return not self.db.moving and self.current_landing() is landing

    def _out_exit(self):
        """The car's `out` exit — found by KEY, not by destination.

        Finding it by destination made it invisible the moment its
        destination was None, which is exactly when it most needs
        repointing: `db.floors` holds landing rooms by dbref and Evennia
        unpickles a deleted one as None, so a landing deleted during a
        rebuild wrote None onto the car's only exit and no later
        `_arrive` could ever find it again. The car sealed permanently
        and recovery was `@tel` (#2626).

        The destination scan stays as a fallback for a car whose exit is
        keyed something else.
        """
        for obj in self.contents:
            if getattr(obj, "key", None) == "out":
                return obj
        for obj in self.contents:
            if getattr(obj, "destination", None) or obj.db_destination_id:
                return obj
        return None

    # ------------------------------------------------------------------
    # the two requests
    # ------------------------------------------------------------------

    def _floor_permitted(self, idx, presser):
        """The §2.2 biometric floor gate: ``db.floor_locks`` maps a floor
        label to a grant file; a secured floor's button only lights for a
        granted sleeve. Unsecured floors pass free."""
        floors = self.db.floors or []
        if not 0 <= idx < len(floors):
            return False
        locks = self.db.floor_locks or {}
        if not locks:
            return True                     # no secured floors on this car
        label = str(floors[idx][1])
        grants = locks.get(label)
        if grants is not None:
            from world.access import is_granted
            return presser is not None and is_granted(presser, grants)

        # `None` meant two different things and the code could not tell
        # them apart: "this floor was never secured" (pass free, right)
        # and "this floor IS secured, but the lock key no longer matches
        # its label" (pass free, WRONG). Keys are stringified, so `2` and
        # `"2"` agree while `"2"` and `"L2"` do not — a builder editing a
        # floor label silently unlocked the floor, with no error, no log,
        # and no visible difference. The button simply lit for everyone
        # (#2687, #2775).
        #
        # An ORPHANED lock key — one matching no floor label — is the
        # evidence that happened. When any exists, this car's lock table
        # is broken and we cannot know which floor the dangling grants
        # were protecting, so the unlisted floors fail CLOSED. That is
        # what the access module documents and what a security control
        # should do; the previous behaviour admitted everyone silently.
        orphans = self._orphaned_lock_keys()
        if orphans:
            from evennia.utils import logger
            logger.log_err(
                f"Elevator {self.key} (#{self.id}): floor_locks keys "
                f"{sorted(orphans)} match no floor label "
                f"{sorted(str(f[1]) for f in floors)}. Those floors are "
                f"UNPROTECTED; refusing unlisted floors until the labels "
                f"and the lock keys agree.")
            return False
        return True

    def _orphaned_lock_keys(self):
        """Lock keys that match no floor label on this car.

        Their existence means a label was renamed, retyped, or had its
        type changed after the lock was written — so a floor somebody
        deliberately secured is no longer being checked at all.
        """
        floors = self.db.floors or []
        labels = {str(f[1]) for f in floors}
        return {k for k in (self.db.floor_locks or {}) if str(k) not in labels}

    def request_floor(self, label, presser=None):
        """A panel press inside the car."""
        idx = self.floor_index(label)
        if idx is None:
            if presser:
                presser.msg("The panel has no such floor.")
            return False
        if not self._floor_permitted(idx, presser):
            if presser:
                presser.msg("The reader beside the panel blinks |rred|n. "
                            "The button stays dark.")
            return False
        if self._landing(idx) is None:
            if presser:
                presser.msg("The button stays dark. That floor is "
                            "sealed.")
            return False
        if idx == self.db.current_floor and not self.db.moving:
            if presser:
                presser.msg("The doors are already open on that floor.")
            return False
        if self.db.moving:
            # Same queue as the landing buttons (#3173): a rider who
            # picks a floor mid-journey is asking for a stop, not
            # making a mistake.
            self._enqueue(idx)
            if presser:
                presser.msg("The car is already in motion. The button "
                            "stays lit.")
            return True
        self._begin_move(idx)
        return True

    def call_to(self, landing, presser=None):
        """A call-button press at a landing."""
        idx = self.floor_index(landing)
        if idx is None:
            if presser:
                presser.msg("The button clicks, dead. This shaft doesn't "
                            "serve this floor.")
            return False
        if self._landing(idx) is None:
            # A floor whose landing has been deleted still has a label
            # and a button. Refusing here keeps the car out of the
            # dead-floor branch in `_arrive` entirely (#2626).
            if presser:
                presser.msg("The button clicks, dead. That floor is "
                            "sealed.")
            return False
        if idx == self.db.current_floor and not self.db.moving:
            if presser:
                presser.msg("The doors are already open.")
            return False
        if self.db.moving:
            # QUEUE IT. A press while the car was in motion used to be
            # thrown away, so the car never came and the caller stood
            # at shut doors until their errand faulted. 45 souls share
            # this shaft; any two of them wanting it inside one journey
            # meant the second was stranded (#3173).
            self._enqueue(idx)
            if presser:
                presser.msg("Behind the doors, the mechanism is already "
                            "in motion. The button lights and stays lit.")
            return True
        self._begin_move(idx)
        return True

    # ------------------------------------------------------------------
    # motion
    # ------------------------------------------------------------------

    def _enqueue(self, idx):
        """Register a floor to be served once the car is free.

        FIFO, and deduplicated: two people pressing the same landing
        button is one stop, not two. Persistent, because a reload
        mid-journey would otherwise lose every lit button — and the
        people waiting under them.
        """
        queue = list(self.db.call_queue or [])
        if idx in queue:
            return
        queue.append(idx)
        self.db.call_queue = queue

    def _serve_queue(self):
        """Take the next lit button, once the doors have stood open.

        Called on a delay after `_arrive` rather than from it, so the
        car actually WAITS at the floor it was called to. Entries for
        the floor it is already standing at are dropped rather than
        driven to, which is what keeps a repeated press from moving
        anything.
        """
        if self.db.moving:
            return
        queue = list(self.db.call_queue or [])
        while queue:
            idx = queue.pop(0)
            if idx == self.db.current_floor:
                continue        # already here; the button is answered
            if self._landing(idx) is None:
                continue        # the landing was deleted (#2626)
            self.db.call_queue = queue
            self._begin_move(idx)
            return
        self.db.call_queue = []

    def _landing(self, idx):
        """The landing room at `idx`, or None if it is gone.

        A deleted room unpickles as None out of `db.floors`, so "the
        floor exists" and "the button has a label" are different
        questions (#2626).
        """
        floors = self.db.floors or []
        if not 0 <= idx < len(floors):
            return None
        entry = floors[idx]
        return entry[0] if entry else None

    def _begin_move(self, target_idx):
        old_landing = self.current_landing()
        going_up = target_idx > (self.db.current_floor or 0)
        distance = abs(target_idx - (self.db.current_floor or 0))
        self.db.moving = True
        self.db.target_floor = target_idx
        word = "upward" if going_up else "downward"
        shaft = "up" if going_up else "down"
        self.msg_contents(
            f"The doors slide shut; the car shudders and hums {word}.")
        if old_landing:
            old_landing.msg_contents(
                "The elevator doors slide shut. The car hums away "
                f"{shaft} the shaft.")
        delay(DOOR_SECONDS + RIDE_SECONDS_PER_FLOOR * distance,
              self._arrive, target_idx)

    def _arrive(self, target_idx, quiet=False):
        floors = self.db.floors or []
        if not 0 <= target_idx < len(floors):
            self.db.moving = False
            self.db.target_floor = None
            return
        landing = floors[target_idx][0]
        if landing is None:
            # THE FLOOR IS GONE. `db.floors` holds landing rooms by
            # dbref and Evennia unpickles a deleted one as None, so a
            # landing removed during a rebuild used to be docked at
            # anyway — writing None onto the car's only exit and
            # sealing everyone inside (#2626).
            #
            # Stay where we were. The doors do not open on a floor that
            # does not exist, `current_floor` keeps naming a real
            # landing, and the queue still gets served so the car can
            # go somewhere that does.
            from evennia.utils import logger
            logger.log_err(
                f"ELEVATOR_DEAD_FLOOR: {self.key} (#{self.id}) was sent "
                f"to floor index {target_idx}, whose landing has been "
                f"deleted. Staying at {self.db.current_floor}. Prune "
                f"db.floors.")
            self.db.moving = False
            self.db.target_floor = None
            if not quiet:
                self.msg_contents(
                    "The car settles. Nothing opens; behind the doors "
                    "there is only shaft.")
            if self.db.call_queue:
                delay(DWELL_SECONDS, self._serve_queue)
            return
        self.db.current_floor = target_idx
        self.db.moving = False
        self.db.target_floor = None
        out = self._out_exit()
        if out:
            out.destination = landing
        try:
            from world.spatial import get_xyz, set_xyz
            xyz = get_xyz(landing)
            if xyz:
                shaft = self.db.shaft_xy
                if shaft:
                    # the car rides its shaft column at the landing's height
                    set_xyz(self, shaft[0], shaft[1], xyz[2])
                else:
                    set_xyz(self, *xyz)
        except Exception:
            pass
        if not quiet:
            self.msg_contents("The car settles; the doors slide open.")
            landing.msg_contents("The elevator doors slide open with a "
                                 "pneumatic sigh.")
        # Whoever is still waiting under a lit button gets served next,
        # after the doors have stood open long enough to board (#3173).
        if self.db.call_queue:
            delay(DWELL_SECONDS, self._serve_queue)


class ElevatorDoorExit(Exit):
    """A landing's `elevator` exit. Destination is always the car;
    traversal only works while the car is docked here, doors open.
    Answers to `in` as well — the natural verb at the threshold (the
    car side's exit is keyed `out` to match)."""

    def at_object_creation(self):
        super().at_object_creation()
        if "in" not in self.aliases.all():
            self.aliases.add("in")

    def at_traverse(self, traversing_object, target_location):
        if not car_docked(self.destination, self.location):
            traversing_object.msg(DOORS_SHUT_MSG)
            return
        super().at_traverse(traversing_object, target_location)


class ElevatorCarExit(Exit):
    """The car's `out` exit. Its destination is re-pointed on arrival;
    it refuses while the car is between floors. Answers to `o` — the
    mirror of the threshold side's `in`."""

    def at_object_creation(self):
        super().at_object_creation()
        if "o" not in self.aliases.all():
            self.aliases.add("o")

    def at_traverse(self, traversing_object, target_location):
        car = self.location
        if getattr(car.db, "moving", False) or not target_location:
            traversing_object.msg(CAR_MOVING_MSG)
            return
        super().at_traverse(traversing_object, target_location)


class ElevatorCallButton(Item):
    """A landing's call button. `press button` summons the car.
    ``db.elevator`` points at the car."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.pressable = True
        self.locks.add("get:false()")
        self.db.get_err_msg = "The button is set into the wall."

    def at_press(self, presser, arg=None):
        if arg:
            # only answers to its own name — labels belong to the panel
            return False
        car = self.db.elevator
        if not car:
            presser.msg("You press the button. Nothing. It's dead.")
            return True
        presser.msg("You press the call button.")
        if presser.location:
            presser.location.msg_contents(
                "The call button clicks under a fingertip.",
                exclude=[presser])
        car.call_to(self.location, presser)
        return True


class ElevatorPanel(Item):
    """The floor panel inside the car. `press <floor>` selects a floor;
    `press panel` reads the buttons. ``db.elevator`` points at the car."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.pressable = True
        self.locks.add("get:false()")
        self.db.get_err_msg = "The panel is bolted to the car."

    def at_press(self, presser, arg=None):
        car = self.db.elevator or self.location
        floors = getattr(car.db, "floors", None) or []
        if not arg:
            labels = ", ".join(str(entry[1]) for entry in floors)
            presser.msg(f"Worn buttons, one per floor: {labels or 'none'}.")
            return True
        if car.floor_index(arg) is None:
            return False
        presser.msg(f"You press {arg}.")
        if presser.location:
            presser.location.msg_contents(
                "A panel button lights under a fingertip.",
                exclude=[presser])
        car.request_floor(arg, presser)
        return True
