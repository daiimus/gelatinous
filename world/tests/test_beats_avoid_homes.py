"""A private dwelling is not a route node (#2711, #2714).

Beats were BUILT with a lock-blind reachability test and WALKED with a
lock-aware one. `is_reachable(start, goal, traverser=None, ...)` accepts
a traverser and the builder did not pass one, so a locked private
apartment counted as reachable and was sampled into the beat. The walk
then passed `traverser=npc`, correctly found no route, and faulted --
one tobacconist failed the same locked door 273 times and counting.

Passing the traverser fixes the fault loop but not the propriety
problem, which is the second half: an UNLOCKED unit is still somebody's
home, and a civilian whose beat includes it walks into a tenant's flat
on a timer. One keeper's beat held two occupied, unlocked Brackett
units.

Live before the fix: 2 of 46 beats contained private residences.
"""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock

from world.director.civilians import _is_private_residence
from world.director.routines import get_beat


def _room(key="a street", **attrs):
    db = SimpleNamespace(cube_door=None, residence_building=None)
    for k, v in attrs.items():
        setattr(db, k, v)
    room = MagicMock()
    room.db = db
    room.key = key
    return room


class TestWhatCountsAsAHome(TestCase):
    def test_a_street_is_not_a_residence(self):
        self.assertFalse(_is_private_residence(_room()))

    def test_a_cube_door_marks_a_residence(self):
        self.assertTrue(_is_private_residence(_room(cube_door=17)))

    def test_a_residence_building_marks_one_too(self):
        """Both attributes are written together by the rental build and
        agree on all 231 residence rooms in the world; both are tested so
        a partial build cannot slip through."""
        self.assertTrue(_is_private_residence(_room(residence_building=5)))

    def test_something_without_a_db_is_not_a_residence(self):
        self.assertFalse(_is_private_residence(object()))


class TestTheBeatSelfHeals(TestCase):
    """The builder now excludes homes, but beats already written persist
    on the NPC. Filtering at the single read funnel heals those on next
    read rather than needing a data migration, and covers any beat
    authored by hand or by an older build."""

    def _npc(self, beat, post=None):
        npc = MagicMock()
        npc.db = SimpleNamespace(patrol_beat=list(beat), post=post)
        return npc

    def test_a_home_is_dropped_from_an_existing_beat(self):
        street, home = _room("a street"), _room("Unit 6C", cube_door=1)
        npc = self._npc([street, home])
        self.assertEqual(get_beat(npc), [street])

    def test_the_repair_is_written_back(self):
        street, home = _room("a street"), _room("Unit 6C", cube_door=1)
        npc = self._npc([street, home])
        get_beat(npc)
        self.assertEqual(npc.db.patrol_beat, [street])

    def test_a_beat_of_only_homes_becomes_empty(self):
        """Jim del Fischer's case exactly — both his stops were units, so
        his beat is now empty rather than faulting forever."""
        npc = self._npc([_room("Unit 4D", cube_door=1),
                         _room("Unit 6C", cube_door=2)])
        self.assertEqual(get_beat(npc), [])

    def test_a_clean_beat_is_untouched(self):
        """The pin: this must not rewrite beats that are fine."""
        rooms = [_room("a street"), _room("an alley")]
        npc = self._npc(list(rooms))
        self.assertEqual(get_beat(npc), rooms)
        self.assertEqual(npc.db.patrol_beat, rooms)

    def test_the_post_is_still_prepended(self):
        post, street = _room("the shop"), _room("a street")
        npc = self._npc([street], post=post)
        self.assertEqual(get_beat(npc), [post, street])

    def test_no_beat_stays_no_beat(self):
        self.assertEqual(get_beat(self._npc([])), [])


class TestTheBuilderAsksTheWalkersQuestion(TestCase):
    def test_the_builder_passes_a_traverser(self):
        """Structural: the default-None traverser makes the lock-blind
        form the easy one to write, which is how this happened."""
        import inspect

        import world.director.civilians as civ
        src = inspect.getsource(civ)
        self.assertIn("is_reachable(anchor, room, traverser=npc", src)

    def test_the_builder_excludes_homes(self):
        import inspect

        import world.director.civilians as civ
        self.assertIn("not _is_private_residence(room)",
                      inspect.getsource(civ))
