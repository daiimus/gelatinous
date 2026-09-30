"""A donor deleted mid-procedure does not crash the resolver (#3556).

The active procedure's kwargs hold the donor item itself. Deleted in
the 9-18 s window (a builder's `@destroy`, a sweep), it reads back from
the attribute store as None or as a husk with no row, and every install
resolver dereferences it: an AttributeError, and on the channeled path
one swallowed to silence. The callback now re-validates the item the
way it already re-validates the actor and the patient: the surgeon is
told, the chart step fails with a reason, nothing is dispatched.

Also: a completion hook that raises inside a channel is logged rather
than lost.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.medical import procedures as P


class _AnInstallOnTheTable(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.surgeon, self.patient = self.char1, self.char2
        self.patient.location = self.room1
        kit = create_object("typeclasses.items.Item", key="a surgical kit", location=self.surgeon)
        mock.patch("world.medical.utils.find_surgical_kit", return_value=kit).start()
        self.addCleanup(mock.patch.stopall)
        self.told = []
        self.surgeon.msg = lambda text=None, **kw: self.told.append(str(text))
        self.patient.db.surgical_state = {"incisions": {"chest": True}, "active_procedure": None}
        self.patient.db.medical_chart = {"status": "running",
                                         "steps": [{"id": 1, "verb": "install", "status": "running"}]}
        self.donor = create_object("typeclasses.items.Item", key="a donor heart", location=self.surgeon)
        self.record = P.start_procedure(self.patient, verb="install", actor=self.surgeon,
                                        organ_item=self.donor, location="chest")
        self.assertIsNotNone(self.record, "fixture: no procedure started")

    def resolve(self):
        spy = mock.Mock()
        with mock.patch.dict(P._VERB_RESOLVERS, {"install": spy}):
            P._resolve_procedure_callback(self.patient, token=self.record["token"])
        return spy


class TheGoneDonor(_AnInstallOnTheTable):

    def test_control_a_present_donor_is_dispatched(self):
        spy = self.resolve()
        spy.assert_called_once()
        self.assertIs(spy.call_args.kwargs["organ_item"], self.donor)

    def test_a_deleted_donor_is_not_dispatched_and_the_surgeon_is_told(self):
        self.donor.delete()
        spy = self.resolve()           # must not raise
        spy.assert_not_called()
        self.assertTrue(any("is gone" in t for t in self.told), self.told)
        self.assertIsNone((self.patient.db.surgical_state or {}).get("active_procedure"))
        step = self.patient.db.medical_chart["steps"][0]
        self.assertEqual(step["status"], "failed")
        self.assertIn("gone", step["outcome"])

    def test_a_deleted_donor_on_the_real_resolver_raises_nothing(self):
        # Belt and braces: the real install resolver behind the guard.
        self.donor.delete()
        P._resolve_procedure_callback(self.patient, token=self.record["token"])
        self.assertTrue(any("is gone" in t for t in self.told), self.told)


class TheChannelLogsWhatItSwallows(EvenniaCommandTest):

    def test_a_raising_completion_is_logged_not_lost(self):
        from world.channeled import begin_channel, channel_of, _finish
        actor = self.char1
        def boom():
            raise RuntimeError("resolver crashed")
        self.assertTrue(begin_channel(actor, 5, "working", on_complete=boom,
                                      on_interrupt=lambda f: None, key="working"))
        chan = channel_of(actor)
        token = next(v for k, v in chan.items() if "token" in k)
        with mock.patch("evennia.utils.logger.log_err") as logged:
            _finish(actor, token)        # must not raise
        logged.assert_called_once()
        self.assertIn("resolver crashed", logged.call_args.args[0])
