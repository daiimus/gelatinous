"""A ripped-out augment takes its prose with it (#3491).

Install a cybernetic tail and harvest the tailbone back out: the body kept
reading "A segmented cybernetic tail sways at the base of the spine..."
beside the empty-socket wound, on the living body and on the corpse. The
augment's longdesc entry was added at install and never dropped.

Install now records the prose keys it surfaced on each organ it adds;
`_mark_organ_removed` (the one removal bookkeeping site behind both
harvest doors and `strip_organ`) takes a key down once the location it
names has no live organ left. Native prose and still-occupied locations
are left alone; a pre-#3491 install (no recorded keys) comes down only
when its container is an added location the species table never lists.
"""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.medical.core import Organ
from world.medical.procedures import _mark_organ_removed, open_incision
from world.tests import test_anatomy_augments as TA


def _remove(target, organ_name):
    with patch("world.medical.procedures.apply_vital_consequences"):
        _mark_organ_removed(target, organ_name)


def _add_organ(target, name, spec):
    organ = Organ(name, organ_data=dict(spec))
    organ.medical_state = target.medical_state
    target.medical_state.add_organ(name, organ)
    return organ


class ARippedOutAugmentTakesItsProseWithItTest(TestCase):

    def _install_tail(self):
        target = TA._patient()
        open_incision(target, "back")
        with patch("world.medical.procedures.roll_procedure", return_value={"outcome": "success"}):
            TA._resolve_install_augment(TA._surgeon(), target, organ_item=TA._tail_item(), location="back")
        self.assertIn("tail", target.longdesc, "fixture: install did not surface the tail")
        return target

    def test_the_tail_prose_comes_down_with_the_tailbone(self):
        target = self._install_tail()
        _remove(target, "cybernetic_tailbone")
        self.assertNotIn("tail", target.longdesc)
        self.assertIn("back", target.longdesc, "a neighbouring key was dropped")

    def test_install_records_the_keys_it_surfaced(self):
        target = self._install_tail()
        spec = target.medical_state.organs["cybernetic_tailbone"].to_dict()["data"]
        self.assertEqual(list(spec.get("augment_longdesc_keys") or []), ["tail"])

    def test_a_pre_provenance_tail_still_comes_down(self):
        """Installed before the keys were recorded: the container is an
        ADDED location, so its prose is safe to take down."""
        target = TA._patient()
        _add_organ(target, "cybernetic_tailbone", TA.TAIL_ORGAN_SPEC)
        target.longdesc = dict(target.longdesc, tail="A cybernetic tail.")
        _remove(target, "cybernetic_tailbone")
        self.assertNotIn("tail", target.longdesc)

    def test_prose_stays_while_the_location_is_still_occupied(self):
        target = self._install_tail()
        _add_organ(target, "tail_actuator", {"container": "tail", "max_hp": 10, "hit_weight": "rare", "inorganic": True})
        _remove(target, "cybernetic_tailbone")
        self.assertIn("tail", target.longdesc, "dropped while another live organ still sat in the tail")
        _remove(target, "tail_actuator")
        self.assertNotIn("tail", target.longdesc)

    def test_the_corpse_loses_the_prose_too(self):
        snapshot = {"organs": {
            "heart": {"container": "chest", "data": {"container": "chest"}, "current_hp": 20, "max_hp": 20},
            "cybernetic_tailbone": {"container": "tail", "current_hp": 25, "max_hp": 25,
                                    "data": dict(TA.TAIL_ORGAN_SPEC, inorganic=True, augment_longdesc_keys=["tail"])},
        }}
        db = SimpleNamespace(species="human", removed_organs=[], medical_state_at_death=snapshot, wounds_at_death=[],
                             longdesc_data={"chest": "A broad chest.", "tail": "A segmented cybernetic tail sways."})
        corpse = SimpleNamespace(db=db, key="corpse", get_medical_snapshot=lambda: db.medical_state_at_death)
        _remove(corpse, "cybernetic_tailbone")
        self.assertNotIn("tail", corpse.db.longdesc_data)
        self.assertIn("chest", corpse.db.longdesc_data)

    # --- controls ---------------------------------------------------------

    def test_a_native_organ_leaves_the_prose_alone(self):
        target = TA._patient()
        before = dict(target.longdesc)
        _remove(target, "heart")
        self.assertEqual(dict(target.longdesc), before)

    def test_a_pre_provenance_graft_on_native_anatomy_is_left_alone(self):
        """A cyber humerus in a human arm with no recorded keys: the arm is
        native anatomy, so no guess is made about its prose."""
        target = TA._patient()
        target.longdesc = dict(target.longdesc, left_arm="A cyber arm.")
        _add_organ(target, "left_humerus", {"container": "left_arm", "max_hp": 30, "hit_weight": "rare", "inorganic": True, "prosthetic_frame": True})
        for name, organ in list(target.medical_state.organs.items()):
            if name != "left_humerus" and organ.container == "left_arm":
                organ.current_hp = 0
        _remove(target, "left_humerus")
        self.assertIn("left_arm", target.longdesc)
