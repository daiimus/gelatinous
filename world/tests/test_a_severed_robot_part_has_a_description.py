"""A severed robot or synth part comes off the corpse WITH a description (#3362).

`SEVERED_PART_DESCRIPTIONS` covered two of the four registered species.
For a registered species with no bank the lookup deliberately returned
silence (#2725 -- a robot head must not weep blood), and
`Appendage.configure_from_sever` writes `db.desc` only when there is
prose, so a severed robot or synth limb rendered with Evennia's blank
default. Owner ruling 2026-09-13: every species gets its own authored
bank, no routing to shared chrome prose.

Drives the REAL route -- `spawn_severed_part_from_corpse` on a corpse of
each species -- and asserts the part has a description in the species'
own register.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.items import spawn_severed_part_from_corpse

# What a severed part shows when NOTHING wrote db.desc: the Item typeclass's
# stock default. Before #3362 every severed robot/synth part said this.
ITEM_DEFAULT = "It's a thing. Heavy enough to hurt if used wrong."


class SeveredInorganicPartDescribedTest(EvenniaTest):

    def _corpse(self, species):
        corpse = create_object("typeclasses.corpse.Corpse", key=f"{species} corpse", location=self.room1)
        corpse.db.species = species
        return corpse

    def _sever(self, species, location="left_arm"):
        part = spawn_severed_part_from_corpse(self._corpse(species), location)
        self.assertIsNotNone(part, f"no part spawned for {species}.{location}")
        return part

    def test_robot_arm_has_a_description(self):
        part = self._sever("robot")
        desc = (part.db.desc or "").strip()
        self.assertTrue(desc and desc != ITEM_DEFAULT, "severed robot arm shows the stock Item default")
        self.assertNotIn("blood", desc.lower()); self.assertNotIn("human", desc.lower())

    def test_synth_arm_has_a_description(self):
        part = self._sever("synthetic_humanoid")
        desc = (part.db.desc or "").strip()
        self.assertTrue(desc and desc != ITEM_DEFAULT, "severed synth arm shows the stock Item default")
        self.assertNotIn("blood", desc.lower()); self.assertNotIn("human", desc.lower())

    def test_robot_head_via_real_route(self):
        part = self._sever("robot", "head")
        desc = (part.db.desc or "").strip()
        self.assertTrue(desc and desc != ITEM_DEFAULT, "severed robot head shows the stock Item default")

    def test_human_still_described(self):
        # Control: the flesh bank is untouched.
        part = self._sever("human")
        self.assertIn("severed", (part.db.desc or "").lower())

    # --- a REAL robot corpse carries inorganic-flagged organs; that must not
    #     re-route it to the generic chrome template or rename it "cybernetic"
    def _chrome_snapshot(self, container="left_arm"):
        return {"organs": {"o1": {"container": container, "data": {"inorganic": True}}}}

    def test_robot_with_inorganic_organs_keeps_its_name_and_bank(self):
        corpse = self._corpse("robot"); corpse.db.medical_state_at_death = self._chrome_snapshot()
        part = spawn_severed_part_from_corpse(corpse, "left_arm")
        self.assertIn("robot", part.key.lower(), "robot limb was renamed %r" % part.key)
        self.assertNotIn("cybernetic", part.key.lower())
        self.assertNotIn("cybernetic", (part.db.desc or "").lower(), "robot limb got the generic chrome prose")
        self.assertIn("left arm", (part.db.desc or "").lower())

    def test_synth_with_inorganic_organs_keeps_its_name_and_bank(self):
        corpse = self._corpse("synthetic_humanoid"); corpse.db.medical_state_at_death = self._chrome_snapshot()
        part = spawn_severed_part_from_corpse(corpse, "left_arm")
        self.assertNotIn("cybernetic", part.key.lower())
        self.assertNotIn("cybernetic", (part.db.desc or "").lower())

    def test_human_with_a_chrome_arm_still_reads_cybernetic(self):
        # Control for #516: chrome on a flesh body is still chrome.
        corpse = self._corpse("human"); corpse.db.medical_state_at_death = self._chrome_snapshot()
        part = spawn_severed_part_from_corpse(corpse, "left_arm")
        self.assertIn("cybernetic", part.key.lower(), "human chrome arm lost its cybernetic name: %r" % part.key)
        self.assertIn("cybernetic", (part.db.desc or "").lower())
