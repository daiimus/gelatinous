"""Harvested chrome comes back as the chrome it is; flesh still rots (#3488 slice).

`_configure_harvested_item` -- the one stamping site both harvest doors and
`strip_organ` route through -- named every harvested item off the SPECIES
table by ORGAN name with the corpse's decay tier: a cyber-arm bone came out
as "rotting human left humerus" with the stock Item description, a
single-species compatibility list, no value and no prototype link, and a
module fitted to a LEFT arm carried "left" frozen into its spec so it
deployed into the wrong hand when seated on the right.

Owner rulings 2026-09-13/14: chrome doesn't rot; anything installed can be
uninstalled and must come back reinstallable. `stamp_chrome_provenance`
records the item's identity into the organ spec at install; harvest reads
it back, takes the chrome's condition from its own housing, restores its
compatibility list, value and prototype tag, re-templates the side, and
carries the flesh-mount fields a Nailz-class module needs to reinstall.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical import procedures as P


class _RottingSource:
    """A corpse-shaped source at ADVANCED decay (putrid tier)."""
    def __init__(self, species="human"):
        self.dbref = "#999"
        class _DB: pass
        self.db = _DB(); self.db.species = species
        self.db.signature_at_death = None; self.db.apparent_uid_at_death = None
    def get_decay_stage(self): return "advanced"


class HarvestedChromeComesBackAsItselfTest(EvenniaTest):

    def _fresh_item(self):
        return create_object("typeclasses.items.Organ", key="harvested", location=self.room1)

    def _chrome_spec(self, side="left"):
        # A shotgun module as installed on the LEFT: side resolved into strings.
        spec = {"container": f"{side}_arm", "max_hp": 30, "hit_weight": "rare", "inorganic": True,
                "hardpoint": "forearm", "module_type": "forearm",
                "abilities": {"shotgun": {"type": "integrated_weapon", "slot": f"{side}_hand",
                                          "deploy_msg": f"Your {side} forearm splits along its seam."}}}
        return spec

    def test_chrome_keeps_its_name_and_description_and_does_not_rot(self):
        src_item = create_object("typeclasses.items.Item", key="Bellweather shotgun module", location=self.room1)
        src_item.db.desc = "A combat shotgun folded into a forearm-hardpoint form factor."
        src_item.db.compatible_species = ["human", "synthetic_humanoid"]; src_item.db.value = 340
        src_item.tags.add("SHOTGUN_MODULE", category="from_prototype")
        spec = P.stamp_chrome_provenance(self._chrome_spec(), src_item)
        item = self._fresh_item()
        P._configure_harvested_item(item, organ_name="left_forearm_hardpoint", condition="putrid", source=_RottingSource(),
                                    organ_data={"container": "left_arm", "data": spec, "current_hp": 30, "max_hp": 30, "conditions": []})
        self.assertEqual(item.key, "Bellweather shotgun module", "chrome was named off the species table: %r" % item.key)
        self.assertNotIn("rotting", item.key.lower())
        self.assertIn("forearm-hardpoint", item.db.desc or "")
        self.assertEqual(item.db.condition, "pristine", "chrome took the corpse's decay tier")
        self.assertEqual(list(item.db.compatible_species), ["human", "synthetic_humanoid"], "compatibility list narrowed")
        self.assertEqual(item.db.value, 340)
        # Evennia lowercases tag keys; the spawner's own link is lowercase too.
        self.assertEqual((item.db.prototype_key or "").lower(), "shotgun_module")
        self.assertIn("shotgun_module", [t.lower() for t in item.tags.get(category="from_prototype", return_list=True)])

    def test_chrome_condition_comes_from_its_own_housing(self):
        spec = P.stamp_chrome_provenance(self._chrome_spec(), create_object("typeclasses.items.Item", key="module", location=self.room1))
        item = self._fresh_item()
        P._configure_harvested_item(item, organ_name="left_forearm_hardpoint", condition="pristine", source=self.char1,
                                    organ_data={"container": "left_arm", "data": spec, "current_hp": 9, "max_hp": 30, "conditions": []})
        self.assertEqual(item.db.condition, "damaged")

    def test_side_is_re_templated_on_the_way_out(self):
        spec = P.stamp_chrome_provenance(self._chrome_spec("left"), create_object("typeclasses.items.Item", key="module", location=self.room1))
        item = self._fresh_item()
        P._configure_harvested_item(item, organ_name="left_forearm_hardpoint", condition="pristine", source=self.char1,
                                    organ_data={"container": "left_arm", "data": spec, "current_hp": 30, "max_hp": 30, "conditions": []})
        out = item.db.organ_spec
        self.assertEqual(out["abilities"]["shotgun"]["slot"], "{side}_hand", "slot still baked to the left: %r" % out["abilities"]["shotgun"]["slot"])
        self.assertIn("{side} forearm", out["abilities"]["shotgun"]["deploy_msg"])
        self.assertEqual(out["container"], "{side}_arm")
        self.assertEqual(out["chrome_provenance"]["key"], "module", "provenance strings must not be re-templated")

    def test_flesh_mount_fields_travel_for_reinstall(self):
        tray = create_object("typeclasses.items.Item", key="Nailz tray", location=self.room1)
        tray.db.module_mount = "flesh"; tray.db.flesh_containers = ["left_hand", "right_hand"]; tray.db.flesh_organ = "metacarpals"
        spec = P.stamp_chrome_provenance({"container": "left_hand", "abilities": {"nailz": {"type": "natural_weapon"}}, "module_type": "nailz"}, tray)
        item = self._fresh_item()
        P._configure_harvested_item(item, organ_name="left_metacarpals", condition="pristine", source=self.char1,
                                    organ_data={"container": "left_hand", "data": spec, "current_hp": 10, "max_hp": 10, "conditions": []})
        self.assertEqual(item.db.module_mount, "flesh")
        self.assertEqual(list(item.db.flesh_containers), ["left_hand", "right_hand"])
        self.assertEqual(item.db.module_type, "nailz")

    def test_grafted_chrome_without_provenance_is_still_named_as_chrome(self):
        # Installed before provenance existed: no stamp, but it IS grafted.
        item = self._fresh_item()
        P._configure_harvested_item(item, organ_name="left_forearm_hardpoint", condition="putrid", source=_RottingSource(),
                                    organ_data={"container": "left_arm", "data": {"inorganic": True, "hardpoint": "forearm"},
                                                "current_hp": 30, "max_hp": 30, "conditions": []})
        self.assertTrue(item.key.startswith("cybernetic"), item.key)
        self.assertNotIn("rotting", item.key.lower())
        self.assertNotEqual((item.db.desc or "").strip(), "It's a thing. Heavy enough to hurt if used wrong.")

    # --- control: flesh still rots and still narrows to its species -----------

    def test_flesh_organ_still_rots(self):
        item = self._fresh_item()
        P._configure_harvested_item(item, organ_name="heart", condition="putrid", source=_RottingSource(),
                                    organ_data={"container": "chest", "data": {"container": "chest"}, "current_hp": 20, "max_hp": 20, "conditions": []})
        self.assertIn("rotting", item.key.lower(), item.key)
        self.assertEqual(item.db.condition, "putrid")
        self.assertEqual(list(item.db.compatible_species), ["human"])
