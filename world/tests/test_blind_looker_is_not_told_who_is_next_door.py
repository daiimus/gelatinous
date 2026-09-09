"""A blind character is not told who is standing in the next room (#2793).

`get_display_desc` gates the room's own description on
`can_perceive_sense(looker, "visual")` and tells a blind looker "You
can't see a thing here." The adjacent-character glance appended right
after it was gated only on `can_perceive` -- the STEALTH presence gate,
whose own docstring says it answers "is this target concealed from that
looker", never "can that looker see". So a blinded character read, in
one output, that they could see nothing and that someone was to the
north. Looking at the exit itself had the same leak.

Both doors now use the same visual predicate the room description uses,
so the three cannot disagree. Blindness in these tests is real: both
eyes at 0 HP, which zeroes the `sight` capacity `can_see` reads -- no
stub, and a vacuity guard proves the same looker sees the neighbour the
moment the eyes are back.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.perception import can_perceive_sense


class _NeighbourCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.beyond = create_object("typeclasses.rooms.Room", key="beyond")
        self.door = create_object("typeclasses.exits.Exit", key="north",
                                  location=self.room1, destination=self.beyond)
        self.watcher = create_object("typeclasses.characters.Character",
                                     key="a watcher", location=self.room1)
        self.watcher.msg = lambda text=None, **kw: None
        self.neighbour = create_object("typeclasses.characters.Character",
                                       key="a neighbour", location=self.beyond)
        self.neighbour.msg = lambda text=None, **kw: None

    def blind(self, who):
        state = who.medical_state
        for name, organ in state.organs.items():
            if (organ.data or {}).get("capacity") == "sight":
                organ.current_hp = 0
        who.medical_state = state
        who.save_medical_state()
        who._medical_state = None

    def room_glance(self):
        return self.room1.get_adjacent_character_sightings(self.watcher) or ""

    def exit_glance(self):
        return self.door._get_exit_character_display(self.watcher) or ""


class TestThePremise(_NeighbourCase):
    def test_a_sighted_watcher_is_told_about_the_neighbour(self):
        """Vacuity guard: if nothing is reported even when sighted, the
        blind assertions below pass for free."""
        self.assertTrue(can_perceive_sense(self.watcher, "visual"))
        self.assertTrue(self.room_glance())
        self.assertTrue(self.exit_glance())

    def test_zeroing_the_eyes_really_blinds(self):
        self.blind(self.watcher)
        self.assertFalse(can_perceive_sense(self.watcher, "visual"))


class TestABlindWatcherIsToldNothing(_NeighbourCase):
    def test_the_room_glance_is_empty(self):
        self.blind(self.watcher)
        self.assertEqual(self.room_glance(), "")

    def test_the_exit_glance_is_empty(self):
        self.blind(self.watcher)
        self.assertEqual(self.exit_glance(), "")

    def test_the_whole_room_render_never_names_the_neighbour(self):
        self.blind(self.watcher)
        out = (self.room1.return_appearance(self.watcher) or "").lower()
        # The exits line may still say "north" -- a blind character can
        # be told an exit exists.  What must be gone is the SIGHTING.
        for phrase in ("figure to the north", "someone is to the north",
                       "to the north you see", "neighbour"):
            self.assertNotIn(phrase, out)
        self.assertIn("can't see", out)


class TestSightRestoresTheGlance(_NeighbourCase):
    def test_healing_the_eyes_brings_it_back(self):
        self.blind(self.watcher)
        self.assertEqual(self.room_glance(), "")
        state = self.watcher.medical_state
        for name, organ in state.organs.items():
            if (organ.data or {}).get("capacity") == "sight":
                organ.current_hp = organ.max_hp
        self.watcher.medical_state = state
        self.watcher.save_medical_state()
        self.watcher._medical_state = None
        self.assertTrue(self.room_glance())
