"""A dragged patient takes the procedure with them (#3669).

A grapple-drag broke only the VICTIM's channel (#2774, #3663); the
surgeon's channel -- the timer for the procedure on that body -- kept
running and resolved against a patient a room away. Now the drag door
interrupts the procedure on the body and breaks the surgeon's channel,
telling them; and, as the belt, the resolver refuses when the patient is
no longer in the surgeon's room (or hands) at resolution time.

Controls: an undisturbed procedure still resolves; a death on the table
still does NOT break the surgeon's channel (owner ruling #3368).
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.channeled import channel_of
from world.combat.grappling import drag_victim_to
from world.medical import procedures as P


class _OnTheTable(EvenniaCommandTest):
    """char1 is the surgeon, char2 the patient, both in room1; a procedure
    is in flight on the patient."""

    def setUp(self):
        super().setUp()
        self.surgeon, self.patient = self.char1, self.char2
        self.patient.location = self.room1
        kit = create_object("typeclasses.items.Item", key="a surgical kit",
                            location=self.surgeon)
        mock.patch("world.medical.utils.find_surgical_kit", return_value=kit).start()
        self.addCleanup(mock.patch.stopall)
        self.told = []
        self.surgeon.msg = lambda text=None, **kw: self.told.append(str(text))
        self.patient.db.surgical_state = {"incisions": {}, "active_procedure": None}
        self.record = P.start_procedure(self.patient, verb="incise", actor=self.surgeon,
                                        location="chest")
        self.assertIsNotNone(self.record, "fixture: no procedure started")
        self.assertTrue(channel_of(self.surgeon), "fixture: the surgeon is not channeling")

    def resolver_spy(self):
        spy = mock.Mock()
        patcher = mock.patch.dict(P._VERB_RESOLVERS, {"incise": spy})
        patcher.start(); self.addCleanup(patcher.stop)
        return spy

    def active(self):
        return (self.patient.db.surgical_state or {}).get("active_procedure")


class TheDrag(_OnTheTable):

    def test_the_drag_takes_the_procedure_and_the_surgeons_channel(self):
        spy = self.resolver_spy()
        self.assertTrue(drag_victim_to(self.patient, self.room2))
        self.assertIsNone(self.active(), "the procedure record survived the drag")
        self.assertFalse(channel_of(self.surgeon), "the surgeon is still channeling on an empty table")
        self.assertTrue(any("hauled out" in t for t in self.told), self.told)
        # the surgeon's timer, had it survived, finds nothing to resolve
        P._resolve_procedure_callback(self.patient, token=self.record["token"])
        spy.assert_not_called()

    def test_control_an_undisturbed_procedure_resolves(self):
        spy = self.resolver_spy()
        P._resolve_procedure_callback(self.patient, token=self.record["token"])
        spy.assert_called_once()

    def test_the_chart_step_says_why(self):
        self.patient.db.medical_chart = {"status": "running",
                                         "steps": [{"id": 1, "verb": "incise", "status": "running"}]}
        drag_victim_to(self.patient, self.room2)
        step = self.patient.db.medical_chart["steps"][0]
        self.assertEqual(step["status"], "failed")
        self.assertIn("dragged", step["outcome"])

    def test_control_a_death_on_the_table_keeps_the_surgeons_channel(self):
        # Owner ruling #3368: the surgeon keeps working through a flatline.
        P.interrupt_procedure(self.patient, reason="the patient died")
        self.assertTrue(channel_of(self.surgeon))

    def test_the_drag_leaves_the_surgeons_other_channel_alone(self):
        # A surgeon already channeling on this patient starts a SECOND
        # body's procedure on the plain timer; dragging that second body
        # must not break the channel timing the first.
        other = create_object("typeclasses.characters.Character", key="Other",
                              location=self.room1)
        other.db.surgical_state = {"incisions": {}, "active_procedure": None}
        second = P.start_procedure(other, verb="incise", actor=self.surgeon, location="chest")
        self.assertIsNotNone(second)
        self.assertEqual(channel_of(self.surgeon).get("procedure_token"), self.record["token"])
        self.assertTrue(drag_victim_to(other, self.room2))
        self.assertIsNone((other.db.surgical_state or {}).get("active_procedure"))
        self.assertTrue(channel_of(self.surgeon), "the drag of another body broke this patient's channel")
        self.assertIsNotNone(self.active(), "this patient's procedure was lost")

    def test_a_drag_with_nothing_in_flight_is_quiet(self):
        P.interrupt_procedure(self.patient, reason="cleared")
        self.told.clear()
        self.assertIsNone(P.take_patient_away(self.patient, "the patient was dragged away"))
        self.assertEqual(self.told, [])


class TheBelt(_OnTheTable):
    """Separation by a path the drag door did not cover."""

    def test_a_patient_moved_away_is_not_operated_on_from_a_room_away(self):
        spy = self.resolver_spy()
        self.patient.move_to(self.room2, quiet=True, move_hooks=False)   # no interrupt at all
        P._resolve_procedure_callback(self.patient, token=self.record["token"])
        spy.assert_not_called()
        self.assertTrue(any("no longer here" in t for t in self.told), self.told)
        self.assertIsNone(self.active())

    def test_control_a_part_in_the_surgeons_hands_counts_as_here(self):
        head = create_object("typeclasses.items.Item", key="a severed head",
                             location=self.surgeon)
        self.assertTrue(P._patient_is_here(self.surgeon, head))
        self.assertTrue(P._patient_is_here(self.surgeon, self.patient))
        self.patient.location = self.room2
        self.assertFalse(P._patient_is_here(self.surgeon, self.patient))
