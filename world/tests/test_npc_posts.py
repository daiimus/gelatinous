"""What survives of the blueprint post layer.

The sweep this module once tested is retired — there is one post
registry now (world/souls/posts.py), and its coverage lives in
test_souls_posts.py. What remains here is the estate snapshot the
death path still calls, and successor construction.
"""


from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import override_settings
from evennia.utils.test_resources import BaseEvenniaTest

import world.npcs.posts as postsmod


def _fixture(keeper=None, vacant_since=None, room=None):
    f = MagicMock()
    f.location = room or MagicMock()
    f.db.post_keeper = keeper
    f.db.post_vacant_since = vacant_since
    f.db.post_active_desc = None
    f.db.integration_desc = "active line"
    return f


POST = {"fixture": "#999", "policy": "successor", "delay_hours": 24,
        "vacant_desc": "shuttered line"}


class TestSuccessorBuild(BaseEvenniaTest):
    """A real successor: new person, same trade."""

    def test_successor_is_a_new_person_with_the_trade(self):
        from world.npcs.blueprints import BLUEPRINTS, build_successor
        npc = build_successor("butcher_ottilie", self.room1)
        try:
            self.assertNotEqual(npc.key, "Ottilie Krug")
            self.assertTrue(npc.db.llm_driven)
            persona = dict(npc.db.llm_persona)
            self.assertEqual(persona["name"], npc.key)
            self.assertEqual(persona["archetype"], "butcher")
            # the trade kit transferred
            want = sorted(g["key"] for g in
                          BLUEPRINTS["butcher_ottilie"]["wardrobe"])
            have = sorted(i.key for i in npc.get_worn_items())
            self.assertEqual(want, have)
            # the empty book: no dossiers, no memories
            self.assertFalse(npc.db.llm_dossiers)
            self.assertFalse(npc.db.llm_memories)
            self.assertEqual(npc.temp_place,
                             "working the cook-pot behind the food cart.")
        finally:
            npc.delete()


class TestMemoryAcrossDeath(TestCase):
    """§P3: the death-side snapshot and the policy split — re-sleeve restores
    the book, a successor never opens it."""

    def _dying_keeper(self, is_keeper=True):
        npc = MagicMock()
        npc.key = "Ottilie Krug"
        npc.db.llm_dossiers = {"uid1": {"names": ["the ratcatcher"]}}
        npc.db.llm_memories = [{"text": "clean kills, always"}]
        fixture = MagicMock()
        fixture.db.post_keeper = npc if is_keeper else MagicMock()
        fixture.db.post_memory_snapshot = None
        return npc, fixture

    def test_snapshot_taken_for_keeper(self):
        npc, fixture = self._dying_keeper()
        with patch.object(postsmod, "_resolve", return_value=fixture):
            postsmod.snapshot_keeper_memory(npc)
        snap = fixture.db.post_memory_snapshot
        self.assertEqual(snap["keeper"], "Ottilie Krug")
        self.assertEqual(snap["dossiers"], {"uid1": {"names": ["the ratcatcher"]}})
        self.assertEqual(snap["memories"], [{"text": "clean kills, always"}])

    def test_non_keeper_death_no_snapshot(self):
        npc, fixture = self._dying_keeper(is_keeper=False)
        with patch.object(postsmod, "_resolve", return_value=fixture):
            postsmod.snapshot_keeper_memory(npc)
        self.assertIsNone(fixture.db.post_memory_snapshot)

