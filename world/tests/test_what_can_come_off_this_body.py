"""One answer to "what can come off this body" -- living or dead (#3380, #3381).

Before: the typed `harvest` offered species-axis organs plus modules with a
module_type and refused every other grafted augment (a cyber tailbone, an
empty hardpoint, a cyber humerus); the `operate` chart applied NO harvest
filter and would pull a human lung; the two doors disagreed on 16 of 28
human organs, and the resolver had no gate at all. Corpse severance read
the species set alone at three sites, so a cyber tail came off a living
body but never off the corpse, while `operate`'s overlay branch was dead
on the dead (keyed on a Character-only property).

Owner rulings 2026-09-13/14: anything installed can be uninstalled; robots
are robots (native inorganic anatomy is not chrome); chrome doesn't rot.
`world.medical.removable` is the one predicate every door now reads.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical import removable as rm
from world.medical.core import Organ


def _tail_spec():
    return {"container": "tail", "max_hp": 20, "hit_weight": "rare", "inorganic": True,
            "prosthetic_frame": True, "severable_container": True}


class PredicateTest(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.body = self.char1                      # human, living
        state = self.body.medical_state
        organ = Organ("cybernetic_tailbone", organ_data=_tail_spec())
        organ.medical_state = state
        state.organs["cybernetic_tailbone"] = organ
        self.body.medical_state = state
        self.body.save_medical_state()
        self.body._medical_state = None

    # --- harvest: the axis OR a graft ------------------------------------------

    def test_species_axis_organ_is_harvestable(self):
        names = {n for n, _c in rm.harvestable_organs(self.body)}
        self.assertIn("liver", names)

    def test_human_lung_is_not_harvestable_at_either_door(self):
        names = {n for n, _c in rm.harvestable_organs(self.body)}
        self.assertNotIn("left_lung", names)
        from commands import CmdOperate
        self.assertNotIn("left_lung", {n for n, _c in CmdOperate._list_organs(self.body)},
                         "the chart door still offers a human lung")

    def test_grafted_tailbone_is_harvestable(self):
        names = {n for n, _c in rm.harvestable_organs(self.body)}
        self.assertIn("cybernetic_tailbone", names, "a grafted augment without module_type was refused")

    def test_native_inorganic_anatomy_is_not_a_graft(self):
        # Robots are robots: an inorganic organ the species table OWNS is native.
        table = {"left_humerus": {"container": "left_arm", "inorganic": True}}
        entry = {"container": "left_arm", "data": {"inorganic": True, "max_hp": 30}}
        from unittest import mock
        with mock.patch("world.anatomy.species.get_species_organs", return_value=table):
            self.assertFalse(rm.is_grafted("left_humerus", entry, "robot"))

    def test_canonical_name_chrome_on_flesh_is_a_graft(self):
        entry = {"container": "left_arm", "data": {"inorganic": True, "prosthetic_frame": True}}
        self.assertTrue(rm.is_grafted("left_humerus", entry, "human"), "a cyber humerus on a human read as native")

    # --- severance: species set OR overlay, living and dead ---------------------

    def test_living_tail_is_severable(self):
        self.assertIn("tail", rm.severable_containers(self.body))
        self.assertTrue(rm.container_is_severable(self.body, "tail"))

    def test_corpse_tail_is_severable(self):
        corpse = create_object("typeclasses.corpse.Corpse", key="corpse", location=self.room1)
        corpse.db.species = "human"
        corpse.db.medical_state_at_death = {"organs": {
            "heart": {"container": "chest", "data": {}, "current_hp": 20},
            "left_humerus": {"container": "left_arm", "data": {}, "current_hp": 20},
            "cybernetic_tailbone": {"container": "tail", "data": _tail_spec(), "current_hp": 20},
        }}
        self.assertIn("tail", rm.severable_containers(corpse), "the corpse door still reads the species set alone")
        from commands.forensics import _severable_locations
        from commands.CmdOperate import _list_severable_containers
        self.assertIn("tail", _severable_locations(corpse))
        self.assertIn("tail", _list_severable_containers(corpse))
        self.assertIn("left_arm", _severable_locations(corpse))
        self.assertNotIn("chest", _severable_locations(corpse))

    def test_already_severed_container_is_not_offered_again(self):
        corpse = create_object("typeclasses.corpse.Corpse", key="corpse", location=self.room1)
        corpse.db.species = "human"
        corpse.db.medical_state_at_death = {"organs": {"left_humerus": {"container": "left_arm", "data": {}, "current_hp": 20}}}
        corpse.db.severed_locations = ["left_arm"]
        self.assertNotIn("left_arm", rm.severable_containers(corpse))

    # --- chrome doesn't rot ------------------------------------------------------

    def test_skeletal_body_still_yields_grafted_chrome(self):
        corpse = create_object("typeclasses.corpse.Corpse", key="corpse", location=self.room1)
        corpse.db.species = "human"
        corpse.db.medical_state_at_death = {"organs": {
            "liver": {"container": "abdomen", "data": {}, "current_hp": 20},
            "left_forearm_hardpoint": {"container": "left_arm", "current_hp": 20,
                                       "data": {"inorganic": True, "hardpoint": "forearm", "prosthetic_frame": True}},
        }}
        corpse.get_decay_stage = lambda: "skeletal"
        names = {n for n, _c in rm.harvestable_organs(corpse)}
        self.assertNotIn("liver", names, "flesh survived a skeletal body")
        self.assertIn("left_forearm_hardpoint", names, "chrome rotted away with the flesh")


class InstallIsLivingOnlyAtTheDoorTest(EvenniaTest):
    """The plain-organ `install` branch let a corpse through to be refused
    silently in the resolver; the other three branches refused at the door.
    Owner 2026-09-14: install into a non-living body is for robots and maybe
    bioroids, later -- organics are living-only, and the door says so."""

    def test_install_into_a_corpse_is_refused_at_the_command(self):
        from unittest import mock
        from commands.CmdSurgical import CmdInstall
        corpse = create_object("typeclasses.corpse.Corpse", key="corpse", location=self.room1)
        corpse.db.species = "human"
        corpse.db.medical_state_at_death = {"organs": {"heart": {"container": "chest", "data": {}, "current_hp": 20}}}
        organ = create_object("typeclasses.items.Organ", key="human heart", location=self.char1)
        organ.db.organ_name = "heart"; organ.db.compatible_species = ["human"]
        cmd = CmdInstall(); cmd.caller = self.char1; cmd.args = "heart in corpse"; cmd.switches = []; cmd.cmdstring = "install"
        seen = []
        with mock.patch.object(self.char1, "msg", side_effect=lambda text=None, **kw: seen.append(str(text))), \
             mock.patch("commands.CmdSurgical._resolve_target", return_value=corpse), \
             mock.patch("world.medical.procedures.start_procedure") as started:
            cmd.func()
        started.assert_not_called()
        self.assertTrue(any("alive" in m.lower() for m in seen), "no living-only refusal at the door: %r" % seen)
