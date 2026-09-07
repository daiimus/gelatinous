"""A transmission reaches people, not the junk drawer (#2655).

Two independent causes compounded.

**The grille fanned to objects.** `_grille_audience` returned
`list(contents)` — every item, corpse, organ and blood pool in the room —
and `_collect` then filtered on `hasattr(listener, "msg")`, which
excludes *nothing*, because every typeclassed Evennia object has `.msg`.
It reads as a safety filter, which is why it survived.

**And the orphanage graded as perfect reception.** `_reception_fraction`
returns 0.0 — crisp — for anything off the coordinate grid, on the sound
principle that "range never silences rooms the grid doesn't cover". That
is right for an authored interior and wrong for `#2`, Evennia's
`DEFAULT_HOME`, which is not a place at all: it is where deleted things
land. **Eighteen orphaned handhelds sit there**, and Limbo holds 592
objects.

Measured live, one emergency transmission:

```
before:  627 unique listeners   (592 of them in Limbo)
after:     17 unique listeners
```

The fan-out fix reuses `world.emote._perceives` rather than re-deriving
it — the same duck-type that took a pose from 2,036 renders to 75
(#2788), imported so the audience of a pose and the audience of a radio
cannot drift apart.

The orphanage check walks the real `location` chain, **not**
`_grid_room`: that helper returns only grid-resident rooms, so for
anything in Limbo it answers `None` and an id check against it never
runs. My first attempt made exactly that mistake and changed nothing.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

# NOTE: production calls `_grille_audience(radio.location)` -- the
# PERSON or ROOM the radio sits in, not the radio. Passing the radio
# gives you its holder's inventory, which is how my first version of
# these tests measured the wrong thing entirely.
from world.radio import (
    _clarity_for_fraction,
    _grille_audience,
    _in_orphanage,
    _reception_fraction,
)


class _RadioCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.holder = self.char1
        self.holder.location = self.room1
        self.radio = create_object("typeclasses.objects.Object",
                                   key="a walkie", location=self.holder)

    def clutter(self, n):
        return [create_object("typeclasses.objects.Object",
                              key=f"crate {i}", location=self.room1)
                for i in range(n)]


class TestTheGrilleReachesPeople(_RadioCase):
    def test_furniture_is_not_an_audience(self):
        self.clutter(12)
        audience = _grille_audience(self.radio.location)
        self.assertNotIn("crate", " ".join(o.key for o in audience))

    def test_the_holder_still_hears_it(self):
        self.clutter(5)
        self.assertIn(self.holder, _grille_audience(self.radio.location))

    def test_another_person_in_the_room_hears_it(self):
        self.char2.location = self.room1
        self.assertIn(self.char2, _grille_audience(self.radio.location))

    def test_a_room_of_clutter_costs_nothing(self):
        self.clutter(50)
        self.assertLessEqual(len(_grille_audience(self.radio.location)), 2)

    def test_a_radio_on_the_floor_still_fans_to_the_room(self):
        self.radio.location = self.room1
        self.char2.location = self.room1
        audience = _grille_audience(self.radio.location)
        self.assertIn(self.char2, audience)


class TestTheOrphanageIsNotAPlace(_RadioCase):
    """`#2` is `DEFAULT_HOME` — where deleted things land, not a room
    anyone is standing in."""

    def _limbo(self):
        from evennia.objects.models import ObjectDB
        return ObjectDB.objects.filter(id=2).first()

    def test_a_radio_in_limbo_is_detected(self):
        limbo = self._limbo()
        if limbo is None:
            self.skipTest("no #2 in this database")
        self.radio.location = limbo
        self.assertTrue(_in_orphanage(self.radio))

    def test_a_radio_in_a_real_room_is_not(self):
        self.assertFalse(_in_orphanage(self.radio))

    def test_limbo_grades_as_gone(self):
        limbo = self._limbo()
        if limbo is None:
            self.skipTest("no #2 in this database")
        self.radio.location = limbo
        grade, _clarity = _clarity_for_fraction(
            _reception_fraction((0, 0, 0), 50, [], self.radio))
        self.assertEqual(grade, "gone")

    def test_an_authored_off_grid_room_still_fails_open(self):
        """Range must never silence a room the grid doesn't cover — only
        the orphanage is excluded, not off-grid generally."""
        interior = create_object("typeclasses.rooms.Room", key="a back room")
        self.radio.location = interior
        grade, _clarity = _clarity_for_fraction(
            _reception_fraction((0, 0, 0), 50, [], self.radio))
        self.assertEqual(grade, "clear")
