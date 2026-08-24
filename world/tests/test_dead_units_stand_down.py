"""A destroyed responder lets go of its call (#2255).

Nothing cleared an assignment on death, and the consequences compounded:

* the call stayed open in the ledger forever, with no outcome
* the wreck kept its errand, so it read as still working
* and because `think()` returns early for any assigned soul, the
  unit's soul stayed PERMANENTLY ASLEEP — even repaired, it would
  never think again

That last one is the quiet one. The precedence law that correctly stops
a live unit walking off a scene also bricks a dead one, so the recovery
loop this unblocks would have handed back a chassis that never moved.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.director import assignment as assign
from world.director import security


class _Event:
    def __init__(self, where):
        self.location = where
        self.payload = {}
        self.type = "crime"


class TestItLetsGo(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.unit = self.char1
        self.unit.db.role = "security"
        self.event = _Event(self.room1)
        assign._ACTIVE[self.unit] = assign.Assignment(
            npc=self.unit, event=self.event, post=self.room1)

    def tearDown(self):
        assign._ACTIVE.pop(self.unit, None)
        super().tearDown()

    def test_a_live_unit_keeps_its_call(self):
        self.assertTrue(assign.is_assigned(self.unit))

    def test_death_releases_it(self):
        with mock.patch.object(security, "_cmd"):
            assign.release_on_death(self.unit)
        self.assertFalse(assign.is_assigned(self.unit))

    def test_the_soul_can_think_again(self):
        """The whole point. is_assigned() gating think() is correct for
        the living and fatal for the dead."""
        with mock.patch.object(security, "_cmd"):
            assign.release_on_death(self.unit)
        self.assertIsNone(assign.get_assignment(self.unit))

    def test_the_call_is_settled_not_abandoned(self):
        called = {}
        with mock.patch.object(security, "close_call_for",
                               side_effect=lambda a, o, n: called.setdefault("o", o)):
            assign.release_on_death(self.unit)
        self.assertEqual(called.get("o"), "unit_lost")

    def test_the_corpse_does_not_transmit(self):
        """A destroyed unit does not key a mic. Its going silent
        mid-call IS the signal, and `unit_lost` has no line on
        purpose."""
        self.assertNotIn("unit_lost", security._CALL_OUTCOME_LINES)
        with mock.patch.object(security, "_cmd") as cmd:
            assign.release_on_death(self.unit)
        cmd.assert_not_called()

    def test_releasing_twice_is_harmless(self):
        with mock.patch.object(security, "_cmd"):
            assign.release_on_death(self.unit)
            assign.release_on_death(self.unit)   # must not raise

    def test_an_unassigned_death_is_a_no_op(self):
        assign._ACTIVE.pop(self.unit, None)
        assign.release_on_death(self.unit)       # must not raise

    def test_a_broken_settle_still_frees_the_soul(self):
        """Settling is flavour; releasing is structural. A handler that
        throws must not leave the wreck holding its errand."""
        with mock.patch.object(security, "close_call_for",
                               side_effect=RuntimeError("boom")):
            assign.release_on_death(self.unit)
        self.assertFalse(assign.is_assigned(self.unit))


class TestItIsWiredIntoDying(EvenniaCommandTest):
    def test_at_death_calls_it(self):
        import inspect
        from typeclasses.characters import Character
        self.assertIn("release_on_death",
                      inspect.getsource(Character.at_death))

    def test_security_registered_a_death_handler(self):
        self.assertIs(assign.DEATH_HANDLERS.get("security"),
                      security.security_death)
