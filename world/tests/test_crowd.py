"""Crowd message profile routing + pool distinctness.

Three crowd pools — open-air `default`, enclosed-venue `interior`, and the
dance-floor `nightclub` — must stay distinct so a venue never renders messages
that read like the wrong setting (the bug that made a nightclub look like a
street crush). Room types route to the right pool.
"""

from unittest import TestCase

from world.crowd.crowd_messages import (
    CROWD_MESSAGES,
    crowd_profile_for_room_type,
    get_crowd_messages,
)


def _flatten(profile):
    out = set()
    for tier in CROWD_MESSAGES[profile].values():
        for category in tier.values():
            out |= set(category)
    return out


class CrowdProfileRoutingTests(TestCase):
    def test_room_type_routing(self):
        self.assertEqual(crowd_profile_for_room_type("nightclub"), "nightclub")
        self.assertEqual(crowd_profile_for_room_type("club"), "nightclub")
        self.assertEqual(crowd_profile_for_room_type("bar"), "interior")
        self.assertEqual(crowd_profile_for_room_type("lounge"), "interior")
        self.assertEqual(crowd_profile_for_room_type("street"), "default")
        self.assertEqual(crowd_profile_for_room_type(None), "default")

    def test_pools_are_mutually_distinct(self):
        default = _flatten("default")
        interior = _flatten("interior")
        nightclub = _flatten("nightclub")
        self.assertEqual(default & interior, set(), "interior reuses street lines")
        self.assertEqual(default & nightclub, set(), "nightclub reuses street lines")
        self.assertEqual(interior & nightclub, set(), "nightclub reuses bar lines")

    def test_get_crowd_messages_selects_profile(self):
        # A packed nightclub pulls dance-floor prose, not bar prose.
        pool = get_crowd_messages(4, profile="nightclub")
        joined = " ".join(m for cat in pool.values() for m in cat).lower()
        self.assertIn("bass", joined)
        # Unknown profile falls back to default without error.
        self.assertTrue(get_crowd_messages(4, profile="bogus"))
