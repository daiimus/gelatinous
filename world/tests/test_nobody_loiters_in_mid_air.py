"""Nothing reads as a crowd in "In the Air" (#2443).

`SkyRoom.at_object_creation` set `crowd_base_level = 1`, so every sky
cell sailed past the `== 0` disable gate in `CrowdSystem.
get_crowd_contributions`. `room.type == "sky"` has no entry in
`room_type_modifiers` and `crowd_profile_for_room_type("sky")` returns
`'default'` — the open-air STREET-CRUSH pool. A character hanging in
mid-air read lines about haulers, gutters and chit-hustlers, printed by
the auto-look the moment they landed.

Measured live: **153 SkyRooms, 84 of them at base level 1.** The other
69 are the `@airfill` cells, and `CmdBuildTools` writes their 0 by hand
with the comment *"nobody loiters in mid-air"*. So the intent was never
in doubt — it just lived in one build command instead of on the class,
and every SkyRoom made by a build script (greenhaus towers, the crane
shaft, the marquee, the cisterns) kept the class default.

**The prose was the visible half, not the whole defect.** Crowd level
also feeds `world/director/witness.py` (whether anyone saw a crime) and
`world/stealth.py` (a concealment bonus for blending in). At base 1 a
sky room supplied bystanders who could witness something done in
mid-air, and a crowd for a falling character to hide in. So the gate
goes in `calculate_crowd_level`, ahead of all five consumers, rather
than in `get_crowd_contributions`, where only the prose would be fixed.

`UNPEOPLED_ROOM_TYPES` is a floor, not a profile: `get_crowd_messages`
falls back to `'default'` for any profile it does not recognise, so
"no crowd here" cannot be expressed as a pool — it has to be answered
before a pool is chosen.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.crowd import crowd_system


class _SkyCase(EvenniaTest):
    def sky(self):
        return create_object("typeclasses.rooms.SkyRoom", key="In the Air")

    def street(self, base=1):
        room = create_object("typeclasses.rooms.Room", key="a street")
        room.db.type = "street"
        room.db.crowd_base_level = base
        room.db.outside = True
        return room


class TestTheClassDefaultIsRight(_SkyCase):
    def test_a_fresh_sky_room_is_unpeopled(self):
        self.assertEqual(self.sky().crowd_base_level, 0)

    def test_it_is_still_typed_sky(self):
        self.assertEqual(self.sky().db.type, "sky")

    def test_it_is_still_outside(self):
        """The type carries weather and the jump lattice — only the
        crowd changes."""
        self.assertTrue(self.sky().db.outside)

    def test_it_is_still_a_sky_room(self):
        self.assertTrue(self.sky().db.is_sky_room)


class TestNoCrowdProseInTheAir(_SkyCase):
    def test_the_description_is_empty(self):
        self.assertEqual(
            crowd_system.get_crowd_contributions(self.sky(), self.char1), "")

    def test_a_crowded_sky_room_is_still_empty(self):
        """The floor holds even against a builder who writes a base
        level onto an air cell by hand."""
        room = self.sky()
        room.db.crowd_base_level = 3
        self.assertEqual(
            crowd_system.get_crowd_contributions(room, self.char1), "")

    def test_bodies_in_the_air_do_not_make_a_crowd(self):
        room = self.sky()
        room.db.crowd_base_level = 3
        self.char1.location = room
        self.char2.location = room
        self.assertEqual(crowd_system.calculate_crowd_level(room), 0)


class TestTheLevelItselfIsZero(_SkyCase):
    """The consumers that are not prose: witness chance and the stealth
    concealment bonus both read the LEVEL."""

    def test_the_level_is_zero(self):
        self.assertEqual(crowd_system.calculate_crowd_level(self.sky()), 0)

    def test_a_hand_set_base_level_does_not_lift_it(self):
        room = self.sky()
        room.db.crowd_base_level = 3
        self.assertEqual(crowd_system.calculate_crowd_level(room), 0)

    def test_there_is_no_crowd_to_hide_in(self):
        from world.stealth import crowd_hider_bonus
        room = self.sky()
        room.db.crowd_base_level = 3
        self.assertEqual(crowd_hider_bonus(room), 0)

    def test_nobody_is_up_there_to_witness_anything(self):
        from world.director.witness import witness_chance
        room = self.sky()
        room.db.crowd_base_level = 3
        self.assertEqual(witness_chance(room), 0)


class TestStreetsAreUntouched(_SkyCase):
    """The gate must be a floor for one room type, not a change to the
    crowd model."""

    def test_a_street_still_has_a_level(self):
        self.assertGreater(
            crowd_system.calculate_crowd_level(self.street()), 0)

    def test_a_street_still_has_prose(self):
        room = self.street(base=3)
        self.char1.location = room
        self.assertNotEqual(
            crowd_system.get_crowd_contributions(room, self.char1), "")

    def test_an_explicit_zero_still_disables_a_street(self):
        self.assertEqual(
            crowd_system.get_crowd_contributions(self.street(base=0),
                                               self.char1), "")

    def test_the_predicate_only_claims_sky(self):
        from world.crowd.crowd_messages import room_type_is_unpeopled
        self.assertTrue(room_type_is_unpeopled("sky"))
        for other in ("street", "alley", "bar", "market", "rooftop", ""):
            self.assertFalse(room_type_is_unpeopled(other), other)

    def test_it_survives_a_room_with_no_type_at_all(self):
        from world.crowd.crowd_messages import room_type_is_unpeopled
        self.assertFalse(room_type_is_unpeopled(None))
