"""A corpse renders its installed augments -- and the mark of a ripped-out one (#3379).

`Corpse._get_preserved_longdesc_descriptions` walked the species' FACTORY
display order only. A cybernetic tail lives in a container the species
table never lists, so the corpse silently omitted it, and a harvested tail
left no visible mark even though `_mark_organ_removed` records a
`harvested` wound at that very location.

Owner ruling 2026-09-13: any added anatomy, non-specific; the removal mark
"works off the wound system". The loop now visits every container the
death snapshot knows and every location a preserved wound names.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class CorpseShowsChromeAndScarsTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.corpse = create_object("typeclasses.corpse.Corpse", key="corpse", location=self.room1)
        self.corpse.db.species = "human"
        self.corpse.db.longdesc_data = {
            "chest": "A broad chest, still under the coat.",
            "tail": "A segmented cybernetic tail, its plating dull and scuffed.",
        }
        self.corpse.db.medical_state_at_death = {"organs": {
            "heart": {"container": "chest", "data": {}},
            "cyber_tail": {"container": "tail",
                           "data": {"inorganic": True, "hardpoint": "spine", "module_type": "tail"}},
        }}

    def rendered(self):
        return dict(self.corpse._get_preserved_longdesc_descriptions())

    # --- installed chrome renders --------------------------------------------

    def test_installed_augment_location_renders(self):
        out = self.rendered()
        self.assertIn("tail", out, "augment location never visited: %r" % list(out))
        self.assertIn("cybernetic tail", out["tail"])

    def test_factory_anatomy_still_renders_first(self):
        keys = [loc for loc, _ in self.corpse._get_preserved_longdesc_descriptions()]
        self.assertIn("chest", keys)
        self.assertLess(keys.index("chest"), keys.index("tail"), "augment rendered before factory anatomy")

    # --- a ripped-out augment leaves its mark, via the wound system ----------

    def test_harvested_augment_shows_the_surgery_mark(self):
        import time
        del self.corpse.db.longdesc_data["tail"]          # the tail itself is gone
        self.corpse.db.longdesc_data = dict(self.corpse.db.longdesc_data)
        self.corpse.db.wounds_at_death = [{
            "location": "tail", "injury_type": "harvested", "organ": "cyber_tail",
            "severity": "moderate", "stage": "fresh", "timestamp": time.time(),
        }]
        out = self.rendered()
        self.assertIn("tail", out, "the harvested augment's location was never visited: %r" % list(out))
        low = out["tail"].lower()
        self.assertTrue(any(w in low for w in ("incision", "extracted", "excised", "surgical", "hollow", "cut")),
                        "no surgery mark rendered at the tail: %r" % out["tail"])

    # --- control: an unknown-species corpse and a plain corpse are unchanged --

    def test_no_augments_means_no_extra_locations(self):
        self.corpse.db.medical_state_at_death = {"organs": {"heart": {"container": "chest", "data": {}}}}
        self.corpse.db.longdesc_data = {"chest": "A broad chest."}
        self.assertEqual(list(self.rendered()), ["chest"])
