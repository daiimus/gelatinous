"""The posts watcher (NPC_POSTS_AND_REINCARNATION_SPEC §P2): vacancy
stamping, delay gating, policy dispatch, and the successor generator."""

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


class TestSweep(TestCase):
    def _run(self, fixture, now, post=None, combat=False):
        with patch.object(postsmod, "_resolve", return_value=fixture), \
             patch.object(postsmod, "_combat_at", return_value=combat), \
             patch("world.npcs.blueprints.build_npc") as bn, \
             patch("world.npcs.blueprints.build_successor") as bs, \
             patch("world.identity_utils.msg_room_identity"):
            bs.return_value = MagicMock()
            bn.return_value = MagicMock()
            postsmod._sweep_post("butcher_ottilie", {}, post or POST, now)
        return bn, bs

    def test_staffed_post_untouched(self):
        keeper = MagicMock(); keeper.pk = 1
        f = _fixture(keeper=keeper)
        keeper.location = f.location
        bn, bs = self._run(f, now=1000.0)
        bn.assert_not_called(); bs.assert_not_called()
        self.assertIsNone(f.db.post_vacant_since)

    def test_vacancy_stamped_and_shuttered(self):
        f = _fixture(keeper=None)
        self._run(f, now=1000.0)
        self.assertEqual(f.db.post_vacant_since, 1000.0)
        self.assertEqual(f.db.integration_desc, "shuttered line")
        self.assertEqual(f.db.post_active_desc, "active line")

    def test_before_delay_nothing_happens(self):
        f = _fixture(vacant_since=1000.0)
        bn, bs = self._run(f, now=1000.0 + 23 * 3600)
        bn.assert_not_called(); bs.assert_not_called()

    def test_after_delay_successor_seated(self):
        f = _fixture(vacant_since=1000.0)
        f.db.post_active_desc = "active line"
        bn, bs = self._run(f, now=1000.0 + 25 * 3600)
        bs.assert_called_once()
        bn.assert_not_called()
        self.assertIsNone(f.db.post_vacant_since)
        self.assertEqual(f.db.integration_desc, "active line")
        self.assertIsNotNone(f.db.post_keeper)

    def test_resleave_policy_rebuilds_same_person(self):
        f = _fixture(vacant_since=1000.0)
        post = dict(POST, policy="resleave", delay_hours=8)
        bn, bs = self._run(f, now=1000.0 + 9 * 3600, post=post)
        bn.assert_called_once()
        bs.assert_not_called()

    def test_combat_blocks_seating(self):
        f = _fixture(vacant_since=1000.0)
        bn, bs = self._run(f, now=1000.0 + 25 * 3600, combat=True)
        bn.assert_not_called(); bs.assert_not_called()
        self.assertEqual(f.db.post_vacant_since, 1000.0)


class TestPolicyData(TestCase):
    def test_decided_delays(self):
        from world.npcs.blueprints import BLUEPRINTS
        for key, bp in BLUEPRINTS.items():
            post = bp["post"]
            if post["policy"] == "successor":
                self.assertEqual(post["delay_hours"], 24, key)
            elif post["policy"] == "resleave":
                self.assertEqual(post["delay_hours"], 8, key)

    def test_roster_split(self):
        from world.npcs.blueprints import BLUEPRINTS
        successors = {k for k, bp in BLUEPRINTS.items()
                      if bp["post"]["policy"] == "successor"}
        self.assertEqual(successors, {"butcher_ottilie", "merchant_ezra"})
        # Del and Sully are institutions (owner-decided 2026-07-24)
        for inst in ("bartender_del", "bartender_sully"):
            self.assertEqual(BLUEPRINTS[inst]["post"]["policy"], "resleave")


@override_settings(PROTOTYPE_MODULES=["world.prototypes"])
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
