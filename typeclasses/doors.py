"""Doors — the door IS the exit (verticality §2, decided 2026-07-10).

A door is a mirrored PAIR of ``DoorExit``s (Evennia exits are one-way;
the Evennia contrib door pattern shares state across the pair so both
sides always agree). States: **open** (free traversal), **closed**
(walking through auto-opens it), **locked** (blocked unless the
traverser's sleeve is on the grant file — §2.2 biometric model, via
``world.access``).

Traversal through a locked door for a GRANTED sleeve is momentary:
the reader flashes green, the door admits them, and it seals locked
again behind — passage alone never de-secures a floor. Explicitly
``open``-ing a locked door (granted) unlocks it for real.

``door_broken`` is the §2.4 breach seam: a broken door hangs open and
cannot close or lock (reserved; nothing sets it yet).

The pathfinder consults ``door_blocks(traverser)`` so NPC dispatch
routes around doors the NPC can't pass instead of pathing through
walls it can't open.
"""

from typeclasses.exits import Exit
from world.access import is_granted

READER_DENIED_MSG = "The reader beside the door blinks red. The lock holds."
DOOR_CLOSED_HINT = "You could knock."


class DoorExit(Exit):
    """One side of a door. State lives mirrored on both sides."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_door = True
        self.db.door_closed = True     # a freshly hung door starts shut
        self.db.door_locked = False
        self.db.door_broken = False
        self.db.access_grants = []     # §2.2 grant file: [{sleeve, until, issued_by}]
        if "door" not in self.aliases.all():
            self.aliases.add("door")

    # ------------------------------------------------------------------
    # the pair
    # ------------------------------------------------------------------

    def twin(self):
        """The matching exit on the far side, cached after first lookup."""
        cached = self.db.door_twin
        if cached is not None and getattr(cached, "pk", None):
            return cached
        dest = self.destination
        for ex in (getattr(dest, "exits", None) or []):
            if (getattr(ex.db, "is_door", None) is True
                    and ex.destination is self.location):
                self.db.door_twin = ex
                ex.db.door_twin = self
                return ex
        return None

    def _mirror(self, **states):
        """Set door state attributes on BOTH sides of the pair."""
        sides = [self]
        other = self.twin()
        if other is not None:
            sides.append(other)
        for side in sides:
            for key, value in states.items():
                setattr(side.db, key, value)

    # ------------------------------------------------------------------
    # state queries
    # ------------------------------------------------------------------

    def is_open(self):
        return self.db.door_broken is True or self.db.door_closed is not True

    def is_locked_for(self, char):
        """Locked against *char* specifically (grant file consulted)."""
        if self.db.door_broken is True or self.db.door_locked is not True:
            return False
        return not is_granted(char, self.db.access_grants)

    def door_blocks(self, traverser):
        """Pathfinder hook: is this edge impassable for *traverser*?
        Closed-but-unlocked doors don't block (traversal auto-opens);
        only a lock the traverser's sleeve can't answer does."""
        return self.is_locked_for(traverser)

    # ------------------------------------------------------------------
    # messaging
    # ------------------------------------------------------------------

    def _both_rooms_msg(self, text, exclude=None):
        exclude = exclude or []
        for room in (self.location, self.destination):
            if room is not None:
                room.msg_contents(text, exclude=exclude)

    # ------------------------------------------------------------------
    # appearance — a closed door blocks sight (§2.1: sight through a
    # closed door is NONE; the exit pipeline otherwise composes the
    # far room's view, people included, straight through sealed steel)
    # ------------------------------------------------------------------

    def return_appearance(self, looker, **kwargs):
        if self.is_open():
            return super().return_appearance(looker, **kwargs)
        desc = self.db.desc or "A solid door, built to be on the wrong side of."
        if self.db.door_locked is True:
            state = ("It is sealed; a biometric reader sits flush in the "
                     "frame, idling amber.")
        else:
            state = "It is closed."
        return f"{desc} {state}"

    # ------------------------------------------------------------------
    # traversal
    # ------------------------------------------------------------------

    def _traverse_gate(self, traversing_object):
        """May *traversing_object* pass right now? Handles the door's
        own state changes and messaging; returns True to proceed."""
        if self.db.door_broken is True:
            return True
        if self.db.door_locked is True:
            if is_granted(traversing_object, self.db.access_grants):
                # momentary admission — seals locked again behind them
                traversing_object.msg(
                    "The reader flashes green; the lock releases just "
                    "long enough to let you through, then seals again.")
                self._both_rooms_msg(
                    "The door unseals briefly to let someone through, "
                    "then locks again.", exclude=[traversing_object])
                return True
            traversing_object.msg(
                f"{READER_DENIED_MSG} {DOOR_CLOSED_HINT}")
            return False
        if self.db.door_closed is True:
            # walking through an unlocked door opens it
            self._mirror(door_closed=False)
            traversing_object.msg("You push the door open.")
            self._both_rooms_msg("The door swings open.",
                                 exclude=[traversing_object])
        return True

    def at_traverse(self, traversing_object, target_location):
        if not self._traverse_gate(traversing_object):
            return
        super().at_traverse(traversing_object, target_location)
