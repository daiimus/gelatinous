"""@spawnmob makes a whole person, pinned; a rat or robot is a body; /blank is gone.

Owner rulings 2026-09-14: no hollow bodies; humans and synths are built
like any archetype (persona, clothes, pockets), rolled like an arrival
(style, traits, designation), ensouled with no cube and no job, and
pinned so they cannot run off.
"""
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdSpawnMob import CmdSpawnMob, archetypes_for
from world.director.civilians import CIV_TAG, CIV_TAG_CATEGORY
from world.souls import engine


class SpawnmobMakesAPersonTest(EvenniaCommandTest):

    def _spawn(self, args):
        before = set(o.id for o in ObjectDB.objects.all())
        out = self.call(CmdSpawnMob(), args, caller=self.char1)
        new = [o for o in ObjectDB.objects.all() if o.id not in before
               and o.location == self.room1]
        return out, new

    def test_a_human_is_a_pinned_soul_with_a_persona_and_clothes(self):
        out, new = self._spawn("/human Ada Test")
        self.assertEqual(len(new), 1, out)
        npc = new[0]
        self.assertEqual(npc.key, "Ada Test")
        self.assertTrue(npc.typeclass_path.endswith("LLMNpc"), npc.typeclass_path)
        self.assertEqual(npc.db.species, "human")
        self.assertTrue(npc.tags.get(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1]), "no soul")
        self.assertTrue(engine.is_pinned(npc), "not pinned")
        self.assertIn(npc.db.soul_role, archetypes_for("human"))
        self.assertIsNone(npc.db.soul_post); self.assertIsNone(npc.db.soul_home)
        self.assertTrue((npc.db.llm_persona or {}).get("description"), "no persona description")
        self.assertTrue(npc.db.llm_driven)
        self.assertTrue(npc.db.soul_traits, "no traits"); self.assertTrue(npc.db.designation, "no designation")
        self.assertTrue(any(getattr(o.db, "worn_desc", None) or getattr(o.db, "clothing_type", None)
                            or "coveralls" in o.key or "shirt" in o.key or "boots" in o.key
                            for o in npc.contents) or npc.contents, "no clothes in inventory")
        self.assertFalse(npc.tags.get(CIV_TAG, category=CIV_TAG_CATEGORY), "tagged as a director civilian")
        from world.rental import residence_of
        self.assertIsNone(residence_of(npc), "was given a cube")
        self.assertIn("pinned", out)

    def test_bare_spawnmob_is_a_human_person(self):
        out, new = self._spawn("")
        self.assertEqual(len(new), 1, out)
        self.assertEqual(new[0].db.species, "human")
        self.assertTrue(engine.is_pinned(new[0]))

    def test_a_synth_gets_a_synthetic_archetype(self):
        out, new = self._spawn("/synth")
        self.assertEqual(len(new), 1, out)
        self.assertEqual(new[0].db.species, "synthetic_humanoid")
        self.assertIn(new[0].db.soul_role, archetypes_for("synthetic_humanoid"))
        self.assertTrue(engine.is_pinned(new[0]))

    def test_a_rat_is_a_body_with_rat_anatomy_and_no_soul(self):
        out, new = self._spawn("/rat Fido")
        self.assertEqual(len(new), 1, out)
        rat = new[0]
        self.assertEqual(rat.db.species, "rat")
        self.assertFalse(rat.tags.get(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1]))
        self.assertIn("forepaw", " ".join(rat.medical_state.organs[n].container for n in rat.medical_state.organs)
                      + " ".join(rat.longdesc or {}))

    def test_a_robot_is_a_body_with_species_written(self):
        out, new = self._spawn("/robot")
        self.assertEqual(len(new), 1, out)
        self.assertEqual(new[0].db.species, "robot")
        self.assertFalse(engine.is_pinned(new[0]))

    def test_blank_is_gone(self):
        out, new = self._spawn("/blank")
        self.assertEqual(new, [], "/blank still spawned something")
        self.assertIn("/blank is gone", out)

    def test_an_unknown_switch_spawns_nothing(self):
        out, new = self._spawn("/rt Fido")
        self.assertEqual(new, [])
        self.assertIn("Unrecognised", out)
