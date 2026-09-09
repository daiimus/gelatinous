"""An abandoned insertion point cannot capture the next step (#2552).

The chart editor's insertion point is armed by `i <N>` and used to be
cleared in exactly one place: the *success* branch of
`_add_step_to_chart`. Every abort route out of the verb-pick flow --
eleven of them, plus the `ValueError` return inside the consume path
itself -- returned to the top menu with the flag still armed. The
surgeon's next "Add procedure step" then silently inserted at a stale
position instead of appending.

The confirmation line is the only signal, and it is easy to miss:
*"Step inserted:"* rather than *"Step added:"*.

Worst case is an ordering inversion the runner cannot recover from. Arm
against step I, cancel, then add `suture chest`: the new step lands at
position 1 and executes **before** `incise chest`, so the runner tries
to close an incision that does not exist yet.

The fix is one clear at one choke point -- `_node_top` -- rather than a
clear at each of the eleven abort sites. Every route out of the flow
passes through the top menu, and putting it there means a twelfth abort
route cannot reintroduce the bug. That is the whole point: this defect
exists *because* the clear was attached to one path instead of to the
thing all paths have in common.

The docstring at the consume site already stated the contract the code
did not keep -- "cleared after consumption so the next Add procedure
step invocation appends normally". It is cleared after *successful*
consumption.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.CmdOperate import (
    _add_step_to_chart,
    _node_top,
    _process_edit_choice,
    _process_verb_choice,
)

# `_clear_insert_point` is introduced BY this change. Imported at module
# scope it turns the unfixed tree into a loader error, which stops every
# behavioural test in this file from running -- and a file that cannot
# load is not evidence that a fix was needed.


def _clear_insert_point(caller):
    from commands.CmdOperate import _clear_insert_point as fn
    return fn(caller)
from world.medical import charts as chart_lib


class _ChartCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.patient = create_object("typeclasses.characters.Character",
                                     key="a patient", location=self.room1)
        self.char1.location = self.room1
        self.char1.ndb._operate_target = self.patient
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))

        chart = chart_lib.new_chart(self.char1)
        chart_lib.add_step(chart, "incise", {"location": "chest"})
        chart_lib.add_step(chart, "harvest", {"organ_name": "heart"})
        chart_lib.add_step(chart, "suture", {"location": "chest"})
        chart_lib.save_chart(self.patient, chart)

    def verbs(self):
        chart = chart_lib.get_chart(self.patient)
        return [s["verb"] for s in chart["steps"]]

    def armed(self):
        return getattr(self.char1.ndb, "_operate_insert_before", None)


class TestTheFixtureIsRealBeforeAnythingIsAsserted(_ChartCase):
    """Vacuity guards -- every assertion below is about ordering, and
    ordering claims are meaningless on an empty or unsaved chart."""

    def test_the_chart_persisted_three_steps(self):
        self.assertEqual(self.verbs(), ["incise", "harvest", "suture"])

    def test_arming_really_arms(self):
        _process_edit_choice(self.char1, "i 3")
        self.assertIsNotNone(self.armed())


class TestCancellingTheVerbPickDisarms(_ChartCase):
    def test_the_flag_is_gone_after_returning_to_the_top(self):
        _process_edit_choice(self.char1, "i 3")
        self.assertEqual(_process_verb_choice(self.char1, "x"), "node_top")
        _node_top(self.char1, "")
        self.assertIsNone(self.armed())

    def test_the_next_step_appends_instead_of_inserting(self):
        _process_edit_choice(self.char1, "i 3")
        _process_verb_choice(self.char1, "x")
        _node_top(self.char1, "")
        _add_step_to_chart(self.char1, "suture", {"location": "arm"})
        self.assertEqual(
            self.verbs(), ["incise", "harvest", "suture", "suture"])

    def test_the_confirmation_says_added_not_inserted(self):
        _process_edit_choice(self.char1, "i 3")
        _process_verb_choice(self.char1, "x")
        _node_top(self.char1, "")
        self.said.clear()
        _add_step_to_chart(self.char1, "suture", {"location": "arm"})
        out = "\n".join(self.said)
        self.assertIn("Step added", out)
        self.assertNotIn("Step inserted", out)


class TestTheOrderingInversion(_ChartCase):
    """The failure that actually breaks a procedure: a suture ordered
    before the incision it closes."""

    def test_a_cancelled_insert_against_step_one_does_not_precede_incise(self):
        _process_edit_choice(self.char1, "i 1")
        _process_verb_choice(self.char1, "x")
        _node_top(self.char1, "")
        _add_step_to_chart(self.char1, "suture", {"location": "chest"})
        self.assertEqual(self.verbs()[0], "incise",
                         "a suture was ordered before its incision")


class TestArmingStillWorksWhenNotCancelled(_ChartCase):
    """The feature must survive the fix -- an insert that is actually
    carried through still inserts."""

    def test_a_carried_through_insert_lands_in_position(self):
        _process_edit_choice(self.char1, "i 3")
        _add_step_to_chart(self.char1, "apply",
                           {"item_key": "gauze", "location": "chest"})
        self.assertEqual(
            self.verbs(), ["incise", "harvest", "apply", "suture"])

    def test_and_says_inserted(self):
        _process_edit_choice(self.char1, "i 3")
        self.said.clear()
        _add_step_to_chart(self.char1, "apply",
                           {"item_key": "gauze", "location": "chest"})
        self.assertIn("Step inserted", "\n".join(self.said))

    def test_and_disarms_afterwards(self):
        _process_edit_choice(self.char1, "i 3")
        _add_step_to_chart(self.char1, "apply",
                           {"item_key": "gauze", "location": "chest"})
        self.assertIsNone(self.armed())


class TestTheFailedConsumeAlsoDisarms(_ChartCase):
    """`_add_step_to_chart` returns early on ValueError, above the old
    clear. The step never lands, but the flag used to survive."""

    def test_a_rejected_step_does_not_leave_the_point_armed(self):
        _process_edit_choice(self.char1, "i 3")
        _add_step_to_chart(self.char1, "incise", {})   # missing required arg
        self.assertEqual(self.verbs(), ["incise", "harvest", "suture"])
        _node_top(self.char1, "")
        self.assertIsNone(self.armed())


class TestTheClearIsOneDefinition(_ChartCase):
    def test_the_helper_is_idempotent(self):
        _clear_insert_point(self.char1)
        _clear_insert_point(self.char1)
        self.assertIsNone(self.armed())

    def test_it_clears_an_armed_point(self):
        self.char1.ndb._operate_insert_before = 2
        _clear_insert_point(self.char1)
        self.assertIsNone(self.armed())
