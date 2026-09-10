"""A room made of air has no crowd (#2736).

`sky` is a first-class room type with 154 instances and its own creation
path, and it was registered in none of the profile sets -- so it fell
through to `default`, the OPEN-AIR STREET pool. A character in freefall
was told a hauler crew was shouldering past them:

    "a hauler crew shoulders through with a slung crate, scattering the
     slower"
    "a pickpocket's hand slips out of a stranger's coat and is three
     bodies away"

ARMED AND FIRING, which corrects #2736's own scope note. It recorded
"not currently firing" on the grounds that no sky room holds a character
-- true, they are transit volumes -- but the thing that decides whether
the layer draws is the room's crowd level, and **84 of the 155 sky rooms
carry `crowd_base_level=1`**. Any jump or fall through one renders it.

Fixed with an EMPTY PROFILE rather than a branch upstream, so the intent
sits where the other profiles state theirs.

TWO TRAPS ON THE WAY IN, both worth keeping:

  * `CROWD_MESSAGES.get(profile) or CROWD_MESSAGES['default']` -- an
    empty dict is FALSY, so the first version of the sky profile fell
    straight back to the street and the whole fix was a no-op. Caught by
    verifying the output rather than trusting the edit. The lookup now
    distinguishes REGISTERED-and-empty ("no crowd here") from
    UNREGISTERED ("fall back"). Same or-swallows-a-real-value shape as
    #3093.
  * the intensity fallback then assumed every pool has a `packed` tier
    and raised `KeyError` on the empty one.

NOT CHANGED: the `default` fallback for an unregistered room type.
#2736 suggests the street is the wrong default -- an unknown type is
more likely an interior -- and that is probably right, but it changes
behaviour for every unregistered type at once and belongs to whoever
knows what those are.
"""
from evennia.utils.test_resources import EvenniaTest

from world.crowd.crowd_messages import (
    crowd_profile_for_room_type,
    get_crowd_messages,
)


class TestSkyRoomsAreEmpty(EvenniaTest):

    def test_a_street_still_has_a_crowd(self):
        """Control: a profile returning nothing for everything would
        pass every assertion below."""
        msgs = get_crowd_messages(
            3, profile=crowd_profile_for_room_type("street"))
        self.assertTrue(msgs)

    def test_an_interior_still_has_its_own(self):
        """Control: and the existing profiles are untouched."""
        self.assertEqual(crowd_profile_for_room_type("bar"), "interior")
        self.assertTrue(
            get_crowd_messages(3, profile="interior"))

    def test_sky_gets_its_own_profile(self):
        self.assertEqual(crowd_profile_for_room_type("sky"), "sky")

    def test_and_that_profile_is_silent(self):
        self.assertFalse(
            get_crowd_messages(3, profile="sky"),
            "mid-air drew crowd prose")

    def test_silent_at_every_level(self):
        for level in (1, 2, 3, 4, 9):
            self.assertFalse(get_crowd_messages(level, profile="sky"),
                             f"crowd prose at level {level}")

    def test_an_unregistered_type_still_falls_back(self):
        """The fallback is deliberately unchanged."""
        self.assertEqual(
            crowd_profile_for_room_type("something_nobody_registered"),
            "default")

    def test_a_registered_empty_profile_is_not_falsy_fallback(self):
        """The trap that made the first fix a no-op: an empty pool must
        stay empty rather than reverting to the street."""
        self.assertNotEqual(get_crowd_messages(3, profile="sky"),
                            get_crowd_messages(3, profile="default"))
