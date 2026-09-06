"""Two combat state defects that outlived their moment (#2424, #2425).

**#2424 — three departure broadcasts that never fired.**
`previous_location` was read three times and assigned NOWHERE. It is not
a `DefaultObject` attribute either, so `hasattr` was always False and
each guarded block was dead code:

    commands/combat/movement.py  aim-break flee
    commands/combat/jump.py      leaping off an edge
    commands/combat/jump.py      a failed gap jump

Each was the ONLY departure message for a move deliberately made
`quiet=True`, so bystanders watched a character vanish while the
destination announced an arrival — it reads as a teleport. The in-combat
flee branch in the same function captures `old_location` before the move
and broadcasts correctly, so this was two doors onto one decision inside
a single command.

**#2425 — a charge penalty that followed you out of the fight.**
`charge_penalty` is consumed only when somebody attacks you, and it was
missing from `cleanup_combatant_state`'s purge list. Flee, or die to a
third party, or have the fight end on the orphan sweep, and you kept it
for the rest of the uptime: the first attack in an unrelated fight later
halved your dodge and announced "Still off-balance from your failed
charge" out of nowhere.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import (
    NDB_CHARGE_BONUS,
    NDB_CHARGE_PENALTY,
    NDB_PROXIMITY,
)


class TestTheChargePenaltyIsPurgedWithTheRest(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char = self.char1
        self.char.location = self.room1

    def cleanup(self):
        """`cleanup_combatant_state(char, entry, handler)` -- the real
        signature, which is what leaving a fight calls."""
        from world.combat.utils import cleanup_combatant_state
        handler = mock.MagicMock()
        handler.db.combatants = []
        cleanup_combatant_state(self.char, {"char": self.char}, handler)

    def test_it_does_not_survive_leaving_combat(self):
        setattr(self.char.ndb, NDB_CHARGE_PENALTY, True)
        self.cleanup()
        self.assertFalse(getattr(self.char.ndb, NDB_CHARGE_PENALTY, False))

    def test_the_neighbours_are_still_purged(self):
        """It was added to an existing list; the list still works."""
        setattr(self.char.ndb, NDB_CHARGE_BONUS, True)
        setattr(self.char.ndb, NDB_PROXIMITY, {self.char2})
        self.cleanup()
        self.assertFalse(getattr(self.char.ndb, NDB_CHARGE_BONUS, False))
        self.assertFalse(getattr(self.char.ndb, NDB_PROXIMITY, None))

    def test_a_character_who_never_charged_is_unaffected(self):
        self.cleanup()
        self.assertFalse(getattr(self.char.ndb, NDB_CHARGE_PENALTY, False))

    def test_the_consumer_still_consumes_it_mid_fight(self):
        """Purging on cleanup must not stop it working while the fight
        is still going. The consumer returns a DODGE MULTIPLIER -- 0.5
        while off-balance, 1.0 otherwise -- not a boolean."""
        from world.combat.attack import _consume_charge_penalty
        setattr(self.char.ndb, NDB_CHARGE_PENALTY, True)
        self.assertEqual(_consume_charge_penalty(self.char), 0.5)
        self.assertFalse(getattr(self.char.ndb, NDB_CHARGE_PENALTY, False))

    def test_consuming_twice_only_lands_once(self):
        from world.combat.attack import _consume_charge_penalty
        setattr(self.char.ndb, NDB_CHARGE_PENALTY, True)
        _consume_charge_penalty(self.char)
        self.assertEqual(_consume_charge_penalty(self.char), 1.0)


class TestTheWritersNameTheConstant(EvenniaTest):
    """A literal `char.ndb.charge_penalty = True` beside a consumer that
    reads `NDB_CHARGE_PENALTY` is how the two drift apart."""

    def test_movement_resolution_uses_the_constant(self):
        import inspect
        from world.combat import movement_resolution
        src = inspect.getsource(movement_resolution)
        self.assertNotIn("ndb.charge_penalty = True", src)
        self.assertIn("NDB_CHARGE_PENALTY", src)


class TestThePhantomAttributeIsGone(EvenniaTest):
    """`previous_location` was read three times and assigned zero times.
    Nothing should reach for it again."""

    MODULES = ("commands.combat.movement", "commands.combat.jump")

    def test_no_module_reads_it(self):
        import inspect
        import importlib
        for name in self.MODULES:
            src = inspect.getsource(importlib.import_module(name))
            code = "\n".join(
                line for line in src.splitlines()
                if not line.strip().startswith("#")
            )
            self.assertNotIn("previous_location", code,
                             f"{name} still reaches for previous_location")

    def test_the_departure_sites_capture_the_room_first(self):
        """Each of the three sites has to read `location` BEFORE its
        `move_to`, or the broadcast goes to the room they arrived in."""
        import inspect
        import importlib
        for name in self.MODULES:
            src = inspect.getsource(importlib.import_module(name))
            self.assertIn("old_location = ", src)
