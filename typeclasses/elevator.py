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

Security seam (not yet consumed): ``db.floor_locks`` is reserved for the
§2.2 biometric grant-file check on secured floors.
"""

from evennia.utils.utils import delay

from typeclasses.exits import Exit
from typeclasses.items import Item
from typeclasses.rooms import IndoorRoom

DOOR_SECONDS = 3
RIDE_SECONDS_PER_FLOOR = 6

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

    def at_object_creation(self):
        super().at_object_creation()
        self.db.floors = []
        self.db.current_floor = 0
        self.db.moving = False
        self.db.target_floor = None
        self.db.floor_locks = {}

    def at_init(self):
        super().at_init()
        # delays don't survive a reload — a car caught mid-ride snaps
        # to where it was headed, doors open, no messages
        if self.db.moving:
            target = self.db.target_floor
            if target is None:
                target = self.db.current_floor
            self._arrive(target, quiet=True)

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
        for obj in self.contents:
            if getattr(obj, "destination", None) or obj.db_destination_id:
                return obj
        return None

    # ------------------------------------------------------------------
    # the two requests
    # ------------------------------------------------------------------

    def request_floor(self, label, presser=None):
        """A panel press inside the car."""
        idx = self.floor_index(label)
        if idx is None:
            if presser:
                presser.msg("The panel has no such floor.")
            return False
        if self.db.moving:
            if presser:
                presser.msg("The car is already in motion.")
            return False
        if idx == self.db.current_floor:
            if presser:
                presser.msg("The doors are already open on that floor.")
            return False
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
        if self.db.moving:
            if presser:
                presser.msg("Behind the doors, the mechanism is already "
                            "in motion.")
            return False
        if idx == self.db.current_floor:
            if presser:
                presser.msg("The doors are already open.")
            return False
        self._begin_move(idx)
        return True

    # ------------------------------------------------------------------
    # motion
    # ------------------------------------------------------------------

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
                set_xyz(self, *xyz)
        except Exception:
            pass
        if not quiet:
            self.msg_contents("The car settles; the doors slide open.")
            landing.msg_contents("The elevator doors slide open with a "
                                 "pneumatic sigh.")


class ElevatorDoorExit(Exit):
    """A landing's `elevator` exit. Destination is always the car;
    traversal only works while the car is docked here, doors open."""

    def at_traverse(self, traversing_object, target_location):
        if not car_docked(self.destination, self.location):
            traversing_object.msg(DOORS_SHUT_MSG)
            return
        super().at_traverse(traversing_object, target_location)


class ElevatorCarExit(Exit):
    """The car's `out` exit. Its destination is re-pointed on arrival;
    it refuses while the car is between floors."""

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
