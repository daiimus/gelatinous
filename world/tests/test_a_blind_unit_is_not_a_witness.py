"""A security unit that cannot see does not witness a crime (#2668).

`world/director/crime.py` called `can_see` with TWO arguments; it takes
one. Every call raised `TypeError` straight into a bare `except` whose
comment reads *"no perception layer, still a witness"* — so the gate has
never executed, and a unit with destroyed optics positively identified a
perpetrator every time.

The function's own docstring states the rule it was failing to apply:
*"a unit that cannot see the room cannot record it."*

The two-argument call says what the author meant, and it is TWO
questions rather than one:

* can this unit see at all — `can_see(witness)`;
* can it perceive THIS perp — `can_perceive(witness, perp)`, because a
  hidden perpetrator is not witnessed by somebody they are hidden from.

A bare `can_see(witness)` would have satisfied the docstring and left
the second half missing, which is the half the two-argument call was
reaching for.

The IMPORT falls open now, not the call. A missing perception layer is a
deployment fact and "still a witness" is a reasonable answer to it; a
`TypeError` is a bug, and swallowing one as an answer is exactly how
this survived.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world import perception as perception_mod
from world.director import crime as crime_mod


class _Scene(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.perp = self.char1
        self.perp.location = self.room1
        self.unit = create_object("typeclasses.characters.Character",
                                  key="a dented security robot",
                                  location=self.room1)
        self.unit.db.role = "security"

    def witness(self):
        return crime_mod._unit_on_scene(self.room1, self.perp)


class TestASeeingUnitWitnesses(_Scene):

    def test_the_fixture_produces_a_witness(self):
        """Control: if nothing ever witnessed, every exclusion below
        would pass for the wrong reason."""
        self.assertIs(self.witness(), self.unit)

    def test_a_non_security_body_is_not_a_witness(self):
        self.unit.db.role = "resident"
        self.assertIsNone(self.witness())

    def test_the_perp_does_not_witness_themselves(self):
        self.perp.db.role = "security"
        self.unit.delete()
        self.assertIsNone(self.witness())


class TestABlindUnitDoesNot(_Scene):

    def test_destroyed_optics_disqualify_it(self):
        with patch.object(perception_mod, "can_see",
                          side_effect=lambda who: who is not self.unit):
            self.assertIsNone(self.witness(),
                              "a unit that cannot see identified a perp")

    def test_a_seeing_unit_beside_it_still_witnesses(self):
        """Control: the gate is per-unit, not per-room."""
        other = create_object("typeclasses.characters.Character",
                              key="a chrome-trimmed security robot",
                              location=self.room1)
        other.db.role = "security"
        with patch.object(perception_mod, "can_see",
                          side_effect=lambda who: who is not self.unit):
            self.assertIs(self.witness(), other)


class TestAHiddenPerpIsNotWitnessed(_Scene):

    def test_hidden_from_the_unit(self):
        with patch.object(perception_mod, "can_perceive",
                          side_effect=lambda looker, target: False):
            self.assertIsNone(self.witness())

    def test_the_gate_asks_about_the_right_pair(self):
        """`can_perceive(witness, perp)` — reversed, it would ask
        whether the PERP can see the robot."""
        seen = []
        with patch.object(perception_mod, "can_perceive",
                          side_effect=lambda looker, target: (
                              seen.append((looker, target)) or True)):
            self.witness()
        self.assertIn((self.unit, self.perp), seen)


class TestAMissingLayerStillWitnesses(_Scene):
    """The fail-open that is legitimate — and the one that is not."""

    def test_no_perception_module_is_still_a_witness(self):
        import builtins
        real = builtins.__import__

        def no_perception(name, *args, **kwargs):
            if name == "world.perception":
                raise ImportError("no perception layer")
            return real(name, *args, **kwargs)

        with patch.object(builtins, "__import__", no_perception):
            self.assertIs(self.witness(), self.unit)

    def test_a_typeerror_is_not_swallowed_as_an_answer(self):
        """The defect itself: a signature mismatch read as 'still a
        witness'. It must surface now, not answer."""
        with patch.object(perception_mod, "can_see",
                          side_effect=TypeError("takes 1 positional "
                                                "argument but 2 were given")):
            with self.assertRaises(TypeError):
                self.witness()
