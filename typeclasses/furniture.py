"""Furniture — objects a character occupies in a posture (sit / lie).

A lean substrate (FURNITURE_AND_POSTURE): a ``Furniture`` declares which postures
it allows and how many can occupy it; characters take a posture via the
``sit`` / ``lie`` / ``stand`` commands (``commands/CmdFurniture``), which record
``db.posture`` + ``db.furniture`` and surface it in the room through the existing
``temp_place`` placement line. Posture is cosmetic + a precondition (e.g. a
patient must lie in an :class:`AutoDoc` to be treated) — no combat coupling.

Occupancy is **derived** from the room (characters whose ``db.furniture`` is this
object), never stored, so it can't desync when someone is moved, KO'd, or deleted.
"""

from typeclasses.objects import Object


class Seating:
    """Mixin: the occupancy/posture API for anything you can sit on or lie in —
    a loose :class:`Furniture` object, OR a fixed fixture like a bar (the stools
    are part of it). The owning class sets ``db.postures`` / ``db.capacity`` /
    ``db.preposition`` in its own ``at_object_creation``; these methods only read
    them, so an object with no postures set isn't sittable. Occupancy is derived
    from the room — a moved/KO'd/deleted occupant never lingers."""

    def occupants(self):
        loc = self.location
        if not loc:
            return []
        # Only characters ever point db.furniture at us, so a simple match is
        # enough (and doesn't couple to the exact Character class).
        return [o for o in loc.contents if o.db.furniture == self]

    def is_full(self):
        return len(self.occupants()) >= int(self.db.capacity or 1)

    def allows(self, posture):
        return posture in (self.db.postures or ())

    def primary_posture(self):
        return (self.db.postures or ("sitting",))[0]


class Furniture(Seating, Object):
    """A loose object you can sit on or lie on — a stool, a couch, a stretcher."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.postures = ("sitting",)   # postures this furniture allows
        self.db.capacity = 1              # how many can occupy it at once
        self.db.preposition = "on"        # "sits ON a stool" / "lies IN a pod"
        self.locks.add("get:false()")     # furniture stays put


class AutoDoc(Furniture):
    """A medical pod / stretcher you lie in — and the apparatus a clinic is built
    around (the bar-counter analogue for a doctor). This phase makes it lie-on
    furniture and marks it medical; the treatment capability (the doctor's
    resolver) hangs off ``is_medical`` in the medical phase."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.postures = ("lying",)
        self.db.preposition = "in"
        self.db.is_medical = True
        # Clinic apparatus: operating on a patient lying here steadies the work —
        # a bonus to the treatment check (world.medical.utils.calculate_treatment_
        # success). The clinic's medical-supply STOCK (real items the doctor draws)
        # is layered on in the doctor phase.
        self.db.treatment_bonus = 3
