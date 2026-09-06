"""A dropped surgery resolver must not wedge the patient (#2419).

`start_procedure` persists the record on
`target.db.surgical_state["active_procedure"]` and schedules the thing
that clears it with `evennia_delay(..., persistent=False)`. A reload
inside the 6-30s window drops the resolver, and the flag stays set.

`is_procedure_active` was a bare `is not None`, so it never noticed. Then
`_reject_if_busy` refused every surgical verb on that patient with "is
already partway through a procedure" -- permanently. On a corpse or an
unconscious patient there is no recovery path at all: nobody can operate,
and the patient cannot ask anyone to.

`CONDITION_CADENCE_SPEC` §6.3 is explicit and marked shipped:

    "`utils.delay` is for ephemera only... Anything that must survive a
    reload uses a Script, a TickerHandler subscription, or a persisted
    deadline timestamp swept at server start."

This was a persisted deadline with no sweep. Reading it against the clock
is the cheapest form of that sweep: no startup hook, no migration, and
anyone already wedged by a past reload frees themselves the next time
somebody asks.

These tests do not stub the clock into the module -- they write real
`started_at` values into the record, which is what a reload leaves
behind.
"""
import time

from evennia.utils.test_resources import EvenniaTest

from world.medical import procedures


class _ProcedureCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.patient = self.char1
        self.surgeon = self.char2
        for c in (self.patient, self.surgeon):
            c.location = self.room1

    def set_record(self, started_at, duration_s, verb="incise"):
        """Exactly what `start_procedure` persists, aged to order."""
        state = dict(self.patient.db.surgical_state or {})
        state["active_procedure"] = {
            "verb": verb,
            "actor_dbref": self.surgeon.dbref,
            "started_at": started_at,
            "duration_s": duration_s,
            "kwargs": {},
        }
        self.patient.db.surgical_state = state


class TestAProcedureInFlightStillBlocks(_ProcedureCase):
    """The guard has to keep doing its job."""

    def test_a_fresh_procedure_is_active(self):
        self.set_record(time.time(), 30)
        self.assertTrue(procedures.is_procedure_active(self.patient))

    def test_one_with_time_left_is_active(self):
        self.set_record(time.time() - 5, 30)
        self.assertTrue(procedures.is_procedure_active(self.patient))

    def test_no_record_is_not_active(self):
        self.assertFalse(procedures.is_procedure_active(self.patient))


class TestADroppedResolverExpires(_ProcedureCase):
    """The wedge: the record outlives the delay that clears it."""

    def test_a_procedure_past_its_deadline_is_not_active(self):
        self.set_record(time.time() - 60, 30)
        self.assertFalse(procedures.is_procedure_active(self.patient))

    def test_a_procedure_from_last_week_is_not_active(self):
        self.set_record(time.time() - 7 * 24 * 3600, 30)
        self.assertFalse(procedures.is_procedure_active(self.patient))

    def test_the_longest_procedure_still_expires(self):
        longest = max(procedures.PROCEDURE_DURATIONS.values())
        self.set_record(time.time() - (longest + 1), longest)
        self.assertFalse(procedures.is_procedure_active(self.patient))


class TestAnUnreadableDeadlineIsNotEternal(_ProcedureCase):
    """An unreadable deadline is precisely the case that produced a
    permanent lock, so it must fail open rather than closed."""

    def test_a_missing_started_at_is_stale(self):
        self.set_record(None, 30)
        self.assertFalse(procedures.is_procedure_active(self.patient))

    def test_a_missing_duration_is_stale(self):
        self.set_record(time.time(), None)
        self.assertFalse(procedures.is_procedure_active(self.patient))

    def test_a_garbage_deadline_is_stale(self):
        self.set_record("whenever", "a while")
        self.assertFalse(procedures.is_procedure_active(self.patient))


class TestTheSurgicalVerbsAgree(_ProcedureCase):
    """What a player actually meets: `_reject_if_busy` is the door that
    was stuck shut."""

    def _busy(self):
        from commands.CmdSurgical import _reject_if_busy
        said = []
        self.surgeon.msg = lambda text=None, **kw: said.append(str(text))
        blocked = _reject_if_busy(self.surgeon, self.patient)
        return blocked, " ".join(said)

    def test_a_patient_mid_procedure_is_still_refused(self):
        self.set_record(time.time(), 30)
        blocked, said = self._busy()
        self.assertTrue(blocked)
        self.assertIn("partway through", said)

    def test_a_patient_wedged_by_a_reload_is_operable_again(self):
        self.set_record(time.time() - 3600, 30)
        blocked, _ = self._busy()
        self.assertFalse(blocked)
