"""One patient, one procedure, and one chart chain (#2509, #2512).

## #2509 — the callback resolved whatever was in the slot

`active_procedure` is a single slot. Any new `start_procedure` overwrote
it unconditionally, and `_resolve_procedure_callback(target)` re-read it
with **no identity check** — no `started_at` comparison, no token:

```python
record = state.get("active_procedure")
if record is None:
    return  # interrupted / already resolved
```

`record is None` covers *interruption*. It does not cover *overwrite*.
So a 6-second incise timer could fire and resolve an 18-second harvest
twelve seconds early — and the timer handle is discarded at creation, so
nothing can cancel a stale one.

The gate that prevents the overlap already existed:
`is_procedure_active` was called by the seven standalone verbs in
`CmdSurgical` and **not** by the `operate` chart door. Enforced at the
funnel now, the way `SurgicalKitRequired` already is — a caller-side
check that one of eight callers forgot is exactly the shape that put it
here. The record also carries a token, because refusing the overlap
does not un-schedule a timer that is already in flight.

## #2512 — the leaked chart hook

The comment claimed the advancement hook was *"cleared from the map
regardless"*. Two of the function's three returns sat **above** the pop,
and a resolver that raised skipped it as well. `start_procedure` never
cleared a stale entry either — no `else: pop` — so a leak survived every
later procedure that carried no hook, which is every standalone verb.

Then it fired: some unrelated procedure on the same patient, weeks
later, handing a dead surgeon's chart chain to whoever happened to be
operating. The hook is taken off the map with the slot now, before
anything can return or raise.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical import procedures as P


class _SurgeryCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char2.location = self.room1
        self.kit = create_object("typeclasses.items.Item",
                                 key="a surgical kit",
                                 location=self.char1)
        self.kit.tags.add("surgical_kit", category="item_type")
        self.patch_kit = mock.patch(
            "world.medical.utils.find_surgical_kit",
            return_value=self.kit)
        self.patch_kit.start()
        self.addCleanup(self.patch_kit.stop)
        P._PROCEDURE_COMPLETE_HOOKS.clear()
        self.addCleanup(P._PROCEDURE_COMPLETE_HOOKS.clear)

    def slot(self, target=None):
        target = target or self.char2
        return (getattr(target.db, "surgical_state", None) or {}).get(
            "active_procedure")


class TestOnePatientOneProcedure(_SurgeryCase):
    def test_a_second_start_is_refused(self):
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")
        with self.assertRaises(P.ProcedureInProgress):
            P.start_procedure(self.char2, verb="harvest", actor=self.char1,
                              location="chest", organ_name="heart")

    def test_the_first_record_survives_the_attempt(self):
        first = P.start_procedure(self.char2, verb="incise",
                                  actor=self.char1, location="chest")
        try:
            P.start_procedure(self.char2, verb="harvest", actor=self.char1,
                              location="chest", organ_name="heart")
        except P.ProcedureInProgress:
            pass
        self.assertEqual(self.slot()["token"], first["token"])

    def test_a_second_SURGEON_is_refused_too(self):
        """The overlap that mattered: two people, one patient."""
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")
        with self.assertRaises(P.ProcedureInProgress):
            P.start_procedure(self.char2, verb="incise", actor=self.char2,
                              location="chest")

    def test_a_finished_patient_can_be_started_again(self):
        record = P.start_procedure(self.char2, verb="incise",
                                   actor=self.char1, location="chest")
        P._resolve_procedure_callback(self.char2, token=record["token"])
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")     # must not raise

    def test_an_interrupted_patient_can_be_started_again(self):
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")
        P.interrupt_procedure(self.char2)
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")     # must not raise

    def test_two_different_patients_are_independent(self):
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")
        P.start_procedure(self.char1, verb="incise", actor=self.char1,
                          location="chest")     # must not raise


class TestAStaleTimerResolvesNothing(_SurgeryCase):
    """Refusing the overlap does not un-schedule a timer already in
    flight, so the record carries an identity too."""

    def test_a_foreign_token_is_ignored(self):
        record = P.start_procedure(self.char2, verb="incise",
                                   actor=self.char1, location="chest")
        P._resolve_procedure_callback(self.char2, token="not-the-one")
        self.assertIsNotNone(self.slot())
        self.assertEqual(self.slot()["token"], record["token"])

    def test_the_right_token_resolves(self):
        record = P.start_procedure(self.char2, verb="incise",
                                   actor=self.char1, location="chest")
        P._resolve_procedure_callback(self.char2, token=record["token"])
        self.assertIsNone(self.slot())

    def test_a_record_carries_a_unique_token(self):
        first = P.start_procedure(self.char2, verb="incise",
                                  actor=self.char1, location="chest")
        P.interrupt_procedure(self.char2)
        second = P.start_procedure(self.char2, verb="incise",
                                   actor=self.char1, location="chest")
        self.assertNotEqual(first["token"], second["token"])

    def test_a_tokenless_call_still_resolves(self):
        """Back-compat for anything that calls it bare."""
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")
        P._resolve_procedure_callback(self.char2)
        self.assertIsNone(self.slot())


class TestTheChartHookDoesNotLeak(_SurgeryCase):
    """Driven with a BARE `_resolve_procedure_callback(target)` — the
    signature that exists on both sides of the fix — so these
    demonstrate the leak rather than the new keyword.
    """

    def hooks(self):
        return dict(P._PROCEDURE_COMPLETE_HOOKS)

    def test_a_vanished_actor_does_not_strand_the_hook(self):
        """The first early return, above the old pop."""
        record = P.start_procedure(self.char2, verb="incise",
                                   actor=self.char1, location="chest",
                                   on_complete=lambda t, a: None)
        state = self.char2.db.surgical_state
        state["active_procedure"] = dict(record, actor_dbref="#999999")
        self.char2.db.surgical_state = state
        P._resolve_procedure_callback(self.char2)
        self.assertEqual(self.hooks(), {})

    def test_an_unknown_verb_does_not_strand_the_hook(self):
        """The second early return, also above the old pop."""
        record = P.start_procedure(self.char2, verb="incise",
                                   actor=self.char1, location="chest",
                                   on_complete=lambda t, a: None)
        state = self.char2.db.surgical_state
        state["active_procedure"] = dict(record, verb="nonsense")
        self.char2.db.surgical_state = state
        P._resolve_procedure_callback(self.char2)
        self.assertEqual(self.hooks(), {})

    def test_a_raising_resolver_does_not_strand_the_hook(self):
        record = P.start_procedure(self.char2, verb="incise",
                                   actor=self.char1, location="chest",
                                   on_complete=lambda t, a: None)
        with mock.patch.dict(P._VERB_RESOLVERS,
                             {"incise": mock.Mock(side_effect=RuntimeError)}):
            with self.assertRaises(RuntimeError):
                P._resolve_procedure_callback(self.char2)
        self.assertEqual(self.hooks(), {})

    def test_a_hookless_start_clears_a_stale_entry(self):
        """`start_procedure` had no `else: pop`, so a leak survived
        every standalone verb that followed."""
        P._PROCEDURE_COMPLETE_HOOKS[self.char2.dbref] = lambda t, a: None
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")
        self.assertEqual(self.hooks(), {})

    def test_a_dead_surgeons_chart_cannot_hijack_the_next_operation(self):
        """The whole shape, end to end."""
        fired = []
        record = P.start_procedure(
            self.char2, verb="incise", actor=self.char1, location="chest",
            on_complete=lambda t, a: fired.append(a))
        # the surgeon goes away mid-procedure
        state = self.char2.db.surgical_state
        state["active_procedure"] = dict(record, actor_dbref="#999999")
        self.char2.db.surgical_state = state
        P._resolve_procedure_callback(self.char2)
        # somebody else operates on the same patient later
        later = P.start_procedure(self.char2, verb="incise",
                                  actor=self.char1, location="chest")
        P._resolve_procedure_callback(self.char2)
        self.assertEqual(fired, [], "a stranded chart hook fired")

    def test_a_normal_completion_still_fires_the_hook(self):
        fired = []
        record = P.start_procedure(
            self.char2, verb="incise", actor=self.char1, location="chest",
            on_complete=lambda t, a: fired.append(a))
        P._resolve_procedure_callback(self.char2)
        self.assertEqual(fired, [self.char1])

    def test_and_only_once(self):
        fired = []
        record = P.start_procedure(
            self.char2, verb="incise", actor=self.char1, location="chest",
            on_complete=lambda t, a: fired.append(a))
        P._resolve_procedure_callback(self.char2)
        P._resolve_procedure_callback(self.char2)
        self.assertEqual(len(fired), 1)


class TestAShortTimerCannotResolveALongProcedure(_SurgeryCase):
    """The overlap, demonstrated through the signature both versions
    share: start a 6s incise, start an 18s harvest, then fire the
    resolution the INCISE timer would fire.

    Unfixed, the second `start_procedure` silently replaced the slot and
    this resolved the HARVEST — twelve seconds early, with the incise's
    clock. Fixed, the second start is refused and the incise resolves as
    itself.

    Either way the assertion is the same: a harvest must not come out of
    an incise's timer.
    """

    def resolved(self):
        calls = []

        def _record(verb):
            def _fn(actor, target, **kwargs):
                calls.append(verb)
            return _fn

        return calls, {v: _record(v) for v in P._VERB_RESOLVERS}

    def test_the_harvest_does_not_resolve_early(self):
        calls, fakes = self.resolved()
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")
        try:
            P.start_procedure(self.char2, verb="harvest", actor=self.char1,
                              location="chest", organ_name="heart")
        except Exception:
            pass                      # refused is the fixed behaviour
        with mock.patch.dict(P._VERB_RESOLVERS, fakes):
            P._resolve_procedure_callback(self.char2)
        self.assertNotIn("harvest", calls,
                         "an incise timer resolved a harvest")

    def test_the_incise_resolves_as_itself(self):
        calls, fakes = self.resolved()
        P.start_procedure(self.char2, verb="incise", actor=self.char1,
                          location="chest")
        try:
            P.start_procedure(self.char2, verb="harvest", actor=self.char1,
                              location="chest", organ_name="heart")
        except Exception:
            pass
        with mock.patch.dict(P._VERB_RESOLVERS, fakes):
            P._resolve_procedure_callback(self.char2)
        self.assertEqual(calls, ["incise"])
