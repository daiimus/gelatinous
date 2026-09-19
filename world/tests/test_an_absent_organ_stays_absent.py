"""An organ removed from a body stays removed across save and load (#3400).

`MedicalState.from_dict` built a fresh species-template body and overlaid
the snapshot's organs on it, so anything the template had and the snapshot
lacked came back at full HP on every load. The two doors that remove an
organ outright (an augment install clearing a limb, a reattach clearing a
stump) happened to refill the same names, which masked it. The snapshot is
the body now; the template is only the fallback for a snapshot with no
organ data.
"""
from evennia.utils.test_resources import EvenniaTest

from world.medical.core import MedicalState


class AbsentOrganStaysAbsentTest(EvenniaTest):

    def test_control_a_full_body_round_trips_unchanged(self):
        ms = MedicalState(None)
        names = set(ms.organs)
        back = MedicalState.from_dict(ms.to_dict())
        self.assertEqual(set(back.organs), names)

    def test_a_removed_organ_stays_removed(self):
        ms = MedicalState(None)
        ms.remove_organ("right_humerus")
        back = MedicalState.from_dict(ms.to_dict())
        self.assertNotIn("right_humerus", back.organs, "the template resurrected a removed organ")
        self.assertEqual(len(back.organs), len(ms.organs))

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
        from world.medical.core import MedicalState as MS
        back = MS.from_dict(self.char2.db.medical_state, self.char2)
        self.assertNotIn("left_tibia", back.organs)
