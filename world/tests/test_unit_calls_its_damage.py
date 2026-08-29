"""A wrecked unit says so and holds the scene (#2272).

`think()` returns early for any assigned soul, so on a call the souls
layer -- and its band tree -- is asleep for the whole assignment. That
is the RIGHT behaviour: you do not walk off a scene because you are
hurt, and it means the critical-`health` need shipped in #2266 can
never pull a unit off a live call.

But it left the damage mute. This force communicates entirely by
voice, and the one thing a unit never transmitted was its own
condition -- so dispatch knew where every unit went and nothing about
what state it was in.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaCommandTest

from world.director import security


class _Event:
    def __init__(self, where):
        self.location = where
        self.payload = {}
        self.type = "crime"


class _Assignment:
    def __init__(self, where):
        self.event = _Event(where)
        self.payload = {}


class TestItCallsItsOwnDamage(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.unit = self.char1
        self.unit.db.species = "robot"
        self.unit.db.role = "security"
        self.assignment = _Assignment(self.room1)

    def _wreck(self):
        self.unit.db.medical_state = {"conditions": [
            {"type": "bleeding"}] + [{"type": "fracture"}] * 6}

    def test_a_wrecked_unit_transmits(self):
        self._wreck()
        with mock.patch.object(security, "_cmd") as cmd:
            security._mayday(self.unit, self.assignment)
        said = " ".join(c.args[1] for c in cmd.call_args_list)
        self.assertIn("xmit", said)
        self.assertIn("Chassis compromised", said)

    def test_it_names_the_scene_it_is_standing_on(self):
        """Not the unit's own room — the CALL's location, so the board
        hears where the trouble is even if the unit has drifted."""
        self._wreck()
        with mock.patch.object(security, "_cmd") as cmd:
            security._mayday(self.unit, self.assignment)
        self.assertIn(self.room1.key, cmd.call_args_list[0].args[1])

    def test_an_intact_unit_stays_off_the_air(self):
        self.unit.db.medical_state = {"conditions": []}
        with mock.patch.object(security, "_cmd") as cmd:
            security._mayday(self.unit, self.assignment)
        cmd.assert_not_called()

    def test_lightly_damaged_is_not_a_mayday(self):
        """The band is for shouting for help on. A dented unit that
        clogs it is worse than one that says nothing."""
        self.unit.db.medical_state = {"conditions": [{"type": "fracture"}]}
        with mock.patch.object(security, "_cmd") as cmd:
            security._mayday(self.unit, self.assignment)
        cmd.assert_not_called()

    def test_it_says_it_once_and_not_every_round(self):
        self._wreck()
        with mock.patch.object(security, "_cmd") as cmd:
            for _ in range(5):
                security._mayday(self.unit, self.assignment)
        self.assertEqual(len(cmd.call_args_list), 1)
        self.assertTrue(self.assignment.payload["mayday"])

    def test_it_holds_the_scene(self):
        """The whole point of the ruling: it calls the damage in and
        STAYS. Nothing here stands the unit down."""
        self._wreck()
        with mock.patch.object(security, "_cmd"):
            security._mayday(self.unit, self.assignment)
        self.assertIsNotNone(self.assignment.event)
        self.assertNotIn("stand_down", self.assignment.payload)

    def test_an_unreadable_body_never_strands_the_responder(self):
        self.unit.db.medical_state = "not a dict at all"
        with mock.patch.object(security, "_cmd") as cmd:
            security._mayday(self.unit, self.assignment)   # must not raise
        cmd.assert_not_called()


class TestItIsWiredWhereUnitsActuallyTick(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.unit = self.char1
        self.unit.db.species = "robot"
        self.unit.db.role = "security"
        self.assignment = _Assignment(self.room1)

    def test_the_watch_round_checks_it(self):
        """The watch round is the loop that keeps running THROUGH a
        fight, which is where a unit actually gets wrecked. If the check
        only lived on arrival it would never fire mid-combat.

        BEHAVIOURAL on purpose. This used to assert that the SOURCE TEXT
        of `_watch_tick` contained `_mayday(npc, assignment)`. Criterion
        8 split the round out into `watch_once` (#2384): the call moved
        down one function, the conduct did not change at all, and the
        test went red anyway. A test that tracks letters reports a
        refactor as a regression — and would just as happily stay green
        if the call were left sitting in a function nothing ever ran.

        Combat is forced ON because that is the case the docstring is
        about: the mayday has to fire while the fight owns the unit.
        """
        with mock.patch("world.director.assignment.get_assignment",
                        return_value=self.assignment), \
                mock.patch.object(security, "_in_combat", return_value=True), \
                mock.patch.object(security, "_mayday") as mayday:
            self.assertTrue(security.watch_once(self.unit))   # keeps watching
        mayday.assert_called_once()

    def test_arrival_checks_it_too(self):
        """A unit can reach a scene already wrecked from the last one."""
        import inspect
        self.assertIn("_mayday(npc, assignment)",
                      inspect.getsource(security.security_arrival))
