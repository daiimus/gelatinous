"""Doors — the door IS the exit (verticality §2, decided 2026-07-10).

A door is a mirrored PAIR of ``DoorExit``s (Evennia exits are one-way;
the Evennia contrib door pattern shares state across the pair so both
sides always agree). States: **open** (free traversal), **closed**
and **locked** (both block passage outright). The door is a physical
state machine, not an auth check (user call 2026-07-10): passage
requires the door OPEN — ``open`` opens it (a locked door needs your
sleeve granted, and opening it unlocks it), ``close`` closes it,
``lock`` seals it, and walking never changes the state.

``door_broken`` is the §2.4 breach seam: a broken door hangs open and
cannot close or lock (reserved; nothing sets it yet).

The pathfinder consults ``door_blocks(traverser)`` so NPC dispatch
routes around doors the NPC can't pass instead of pathing through
walls it can't open.
"""

from typeclasses.exits import Exit
from world.access import is_granted

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
        Any not-open door blocks — passage requires the door open, and
        no NPC behaviour opens doors yet. (When granted NPCs learn the
        open verb, this refines to a lock-vs-grant check.)"""
        return not self.is_open()

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
                     "frame, idling |yamber|n.")
        else:
            state = "It is closed."
        return f"{desc} {state}"

    # ------------------------------------------------------------------
    # traversal
    # ------------------------------------------------------------------

    def _traverse_gate(self, traversing_object):
        """May *traversing_object* pass right now? Passage requires the
        door OPEN — walking never opens, unlocks, or closes anything."""
        if self.is_open():
            return True
        if self.db.door_locked is True:
            traversing_object.msg(
                "The door is sealed. The reader beside it idles |yamber|n.")
        else:
            traversing_object.msg(
                "The door is closed. You could open it.")
        return False

    def at_traverse(self, traversing_object, target_location):
        if not self._traverse_gate(traversing_object):
            return
        super().at_traverse(traversing_object, target_location)
