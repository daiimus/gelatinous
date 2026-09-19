"""An organ removed from a body stays removed across save and load; a table
addition still reaches an old body (#3400).

`MedicalState.from_dict` built a fresh species-template body and overlaid
the snapshot's organs on it, so anything the template had and the snapshot
lacked came back at full HP on every load. The two doors that remove an
organ outright (augment install, reattach) refill the same names, which
masked it. But the overlay was also the only way a species-table addition
reached a saved body. So the body now records meaningful absence
(`removed_organs`): the loader builds from the snapshot and adds a template
organ back only when it is neither present nor recorded removed.
"""
from evennia.utils.test_resources import EvenniaTest

from world.medical.core import MedicalState, Organ


class AbsentOrganStaysAbsentTest(EvenniaTest):

    def test_control_a_full_body_round_trips_unchanged(self):
        ms = MedicalState(None)
        back = MedicalState.from_dict(ms.to_dict())
        self.assertEqual(set(back.organs), set(ms.organs))
        self.assertEqual(back.removed_organs, set())

    def test_a_removed_organ_stays_removed(self):
        ms = MedicalState(None)
        ms.remove_organ("right_humerus")
        data = ms.to_dict()
        self.assertEqual(data["removed_organs"], ["right_humerus"])
        back = MedicalState.from_dict(data)
        self.assertNotIn("right_humerus", back.organs, "the template resurrected a removed organ")
        self.assertEqual(back.removed_organs, {"right_humerus"})
        again = MedicalState.from_dict(back.to_dict())
        self.assertNotIn("right_humerus", again.organs, "absence did not survive a second round trip")

    def test_a_table_addition_reaches_an_old_body(self):
        # A snapshot saved before the table gained an organ: the name is
        # simply missing, with no removal recorded. The 53 live bodies that
        # predate cervical_spine and nose have this shape.
        data = MedicalState(None).to_dict()
        del data["organs"]["nose"]
        del data["organs"]["cervical_spine"]
        data.pop("removed_organs", None)          # pre-#3400 snapshots have no such key
        back = MedicalState.from_dict(data)
        self.assertIn("nose", back.organs)
        self.assertIn("cervical_spine", back.organs)
        self.assertEqual(back.organs["cervical_spine"].current_hp, back.organs["cervical_spine"].max_hp)
        # and in table position, as the old overlay left them, not appended
        self.assertEqual(list(back.organs), list(MedicalState(None).organs))

    def test_a_reseated_organ_leaves_the_removed_list(self):
        ms = MedicalState(None)
        ms.remove_organ("right_humerus")
        chrome = Organ("right_humerus", organ_data={"container": "right_arm", "max_hp": 40, "vital": False})
        ms.add_organ("right_humerus", chrome)
        data = ms.to_dict()
        self.assertEqual(data["removed_organs"], [])
        back = MedicalState.from_dict(data)
        self.assertIn("right_humerus", back.organs)
        self.assertEqual(back.removed_organs, set())

    def test_a_tombstoned_organ_keeps_its_zero(self):
        # Harvest and severance do not remove; they zero. That must survive too.
        ms = MedicalState(None)
        ms.organs["heart"].current_hp = 0
        back = MedicalState.from_dict(ms.to_dict())
        self.assertEqual(back.organs["heart"].current_hp, 0)

    def test_a_legacy_snapshot_without_organs_gets_the_template(self):
        data = MedicalState(None).to_dict()
        del data["organs"]
        back = MedicalState.from_dict(data)
        self.assertEqual(set(back.organs), set(MedicalState(None).organs))

    def test_the_character_round_trip_holds(self):
        ms = self.char2.medical_state
        ms.remove_organ("left_tibia")
        self.char2.save_medical_state()
        back = MedicalState.from_dict(self.char2.db.medical_state, self.char2)
        self.assertNotIn("left_tibia", back.organs)
        self.assertIn("nose", back.organs)
