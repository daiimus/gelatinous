"""What survives of the blueprint post layer.

The sweep this module once tested is retired — there is one post
registry now (world/souls/posts.py), and its coverage lives in
test_souls_posts.py. Its death-side snapshot (`snapshot_keeper_memory`)
went too (#3424): write-only since #3672. What remains here is
successor construction.
"""

from evennia.utils.test_resources import BaseEvenniaTest



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
