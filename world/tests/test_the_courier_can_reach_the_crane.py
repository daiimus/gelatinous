"""The courier's hail reaches the console, in the units it parses
(#2619, #2617).

Two defects at the two ends of one radio call, filed separately and
inseparable in practice: the second is masked by the first.

**The hail was dropped before the parser saw it.** `CraneConsole._handle`
is only reachable through `AnsweringFixture._maybe_answer`, which
returned early for any *machine* speaker — and `_is_machine` tested
`db.is_npc` / `db.llm_driven`, which is true of every souled body in the
colony, including Wren, the courier built to hail the crane. The Rabbit's
delivery run stalled at the crane every time: the box on the car, the
hail sent, nothing answering.

**And the two ends used different units.** The car rides a Z column
(`MIN_Z` 1 .. `MAX_Z` 16); the console and the people on the radio talk
about house floors (2..17). The Queen's rack roof is `QOC_Z` 12 to the
car and the 13th floor to a person. The console converted with a bare
`floor - 1`; the courier hailed with a raw z and no conversion at all.
"Bring the box to 12" put the container one level BELOW the roof she was
standing on.

The offset is now written once, on the car class, and both ends go
through it.
"""
from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.items import AnsweringFixture
from typeclasses.rooms import CraneContainer

#: Bound with the OLD behaviour as the fallback rather than imported by
#: name: a missing classmethod makes this file ERROR against the unfixed
#: tree, and an error stops a test before it can assert anything. The
#: fallbacks are exactly what each end used to do — the courier sent a
#: raw z, the console subtracted one — so the assertions below fail
#: there by showing the two ends disagreeing, which is the defect.
floor_of = getattr(CraneContainer, "floor_of", staticmethod(int))
z_of = getattr(CraneContainer, "z_of", staticmethod(lambda f: int(f) - 1))


class TestTheOffsetIsWrittenOnce(EvenniaTest):

    def test_the_two_ends_agree(self):
        for z in range(CraneContainer.MIN_Z, CraneContainer.MAX_Z + 1):
            self.assertEqual(z_of(floor_of(z)),
                             z)

    def test_the_queens_roof_is_the_thirteenth(self):
        """The number the whole defect turns on: z 12 is floor 13, and
        the courier used to say 12."""
        from typeclasses.crane import CraneConsole
        self.assertEqual(floor_of(CraneContainer.QOC_Z),
                         CraneConsole.QOC_FLOOR)

    def test_and_the_dock_is_the_second(self):
        from typeclasses.crane import CraneConsole
        self.assertEqual(floor_of(CraneContainer.MIN_Z),
                         CraneConsole.MIN_FLOOR)

    def test_the_top_of_travel_agrees_too(self):
        from typeclasses.crane import CraneConsole
        self.assertEqual(floor_of(CraneContainer.MAX_Z),
                         CraneConsole.MAX_FLOOR)


class TestTheCourierAsksInFloors(EvenniaTest):

    def _wren(self):
        who = create_object("typeclasses.characters.Character",
                            key="Wren", location=self.room1)
        who.db.is_npc = True
        who.db.llm_driven = True
        return who

    def test_she_hails_the_floor_not_the_z(self):
        from world.director import courier
        who = self._wren()
        said = []
        # `call_the_crane` imports these INSIDE the function, so they are
        # attributes of `world.radio` and never of `courier`.
        from world import radio as radio_mod
        with patch.object(radio_mod, "is_radio", return_value=True), \
             patch.object(radio_mod, "is_powered", return_value=True), \
             patch.object(radio_mod, "same_band", return_value=True), \
             patch.object(radio_mod, "frequency_of", return_value="27MHz"), \
             patch.object(type(who), "execute_cmd",
                          side_effect=lambda line, **kw: said.append(line)):
            handset = create_object("typeclasses.items.Item",
                                    key="a Magpie", location=who)
            courier.call_the_crane(who, CraneContainer.QOC_Z)
        self.assertTrue(said, "she never keyed the handset")
        self.assertIn(str(floor_of(CraneContainer.QOC_Z)),
                      said[-1])
        self.assertNotIn(f"to {CraneContainer.QOC_Z}.", said[-1])


class TestAFixtureIgnoresFixturesNotPeople(EvenniaTest):

    def test_a_souled_npc_is_not_a_machine(self):
        """The predicate that dropped the hail."""
        who = create_object("typeclasses.characters.Character",
                            key="Wren", location=self.room1)
        who.db.is_npc = True
        who.db.llm_driven = True
        self.assertFalse(AnsweringFixture._is_machine(who))

    def test_a_player_is_not_either(self):
        """Control: the guard has not simply been inverted."""
        self.assertFalse(AnsweringFixture._is_machine(self.char1))

    def test_but_another_fixture_is(self):
        """What the guard is actually for: stations answering stations
        is how the band fills with machines talking to machines."""
        other = create_object("typeclasses.crane.CraneConsole",
                              key="another console", location=self.room1)
        self.assertTrue(AnsweringFixture._is_machine(other))

    def test_and_so_is_a_base_station(self):
        station = MagicMock()
        station.db = MagicMock()
        station.db.is_base_station = True
        self.assertTrue(AnsweringFixture._is_machine(station))
