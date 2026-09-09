"""The suture picker stops guessing, and the suture verb stops refusing
what the picker offers (#2553, #2554).

Two defects on the same act, both of the shape this audit keeps
finding: one decision reachable through two code paths, with the rule
attached to only one of them.

**#2553 — the picker guessed, against a standing ruling.** `_parse_pick`
exists specifically to stop silent wrong picks: a complete name wins,
several candidates is a question, nothing is a refusal. Owner ruling
2026-08-24, "never guess". It was applied to four pickers and missed
the fifth. `_process_suture_location` re-implemented the pre-ruling
algorithm inline -- **first substring match against the rendered
display label wins** -- and that label carries status tags and colour
codes. So typing `stump` selected **"suture all"**, and so did typing
`n`. The surgeon got a whole-body suture they never asked for, with no
error to notice.

The root cause was the tuple convention. `_pick_aliases` reads
`item[0]` as the thing the player is naming, but the suture and install
pickers stored `(label, value)`, handing it the rendered string. Both
are now value-first like the other four, so there is one convention
rather than two.

**#2554 — and the verb refused what the picker offered.** `CmdSuture`
gated on `open_incision_locations` alone. `_resolve_suture`, the code
that verb dispatches into, treats un-sutured amputation stumps as
first-class sutureable *by design* -- combat-driven amputation bypasses
the `open_incision` call in `_resolve_amputate`, so a severance often
has no incision to close. The `operate` picker offers exactly those
stumps. Same stitches: allowed through the menu, refused by the verb.

The guard now asks `sutureable_locations`, which is the resolver's own
`open incisions | untreated stumps` rule lifted into one named helper
that both the guard and the resolver call -- so the two cannot drift
apart again.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.CmdOperate import (
    _node_suture_location,
    _process_suture_location,
)
from world.medical import charts as chart_lib
from world.medical.procedures import open_incision_locations

# The symbols this change INTRODUCES are imported lazily. Imported at
# module scope they turn the unfixed tree into a loader error, and a
# loader error is not evidence -- it stops every test in the file from
# running at all, including the behavioural ones that would otherwise
# fail honestly.


def _sutureable(target):
    from world.medical.procedures import sutureable_locations
    return sutureable_locations(target)


def _untreated_stumps(target):
    from world.medical.procedures import untreated_stump_locations
    return untreated_stump_locations(target)


def _suture_all():
    from commands.CmdOperate import SUTURE_ALL
    return SUTURE_ALL


class _SurgeryCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.patient = create_object("typeclasses.characters.Character",
                                     key="a patient", location=self.room1)
        self.char1.location = self.room1
        self.char1.ndb._operate_target = self.patient
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))
        chart_lib.save_chart(self.patient, chart_lib.new_chart(self.char1))

    def sever_a_limb(self):
        """Produce a real severance: an organ at wound_stage 'severed'
        with 0 HP is what `sever_character_body` writes, and the only
        shape `compute_severed_containers` accepts."""
        state = self.patient.medical_state
        for organ in state.organs.values():
            container = getattr(organ, "container", None)
            if container and container not in (
                    "head", "neck", "chest", "abdomen"):
                organ.wound_stage = "severed"
                organ.current_hp = 0
                self.patient.medical_state = state
                self.patient.save_medical_state()
                return container
        self.skipTest("no limb container in this anatomy")

    def steps(self):
        chart = chart_lib.get_chart(self.patient)
        return chart["steps"] if chart else []

    def arm_picker(self):
        _node_suture_location(self.char1, "")
        return self.char1.ndb._operate_pickable or []


class TestAStumpIsSutureable(_SurgeryCase):
    """#2554's premise, established against the real severance
    machinery rather than asserted."""

    def test_the_fixture_really_severs_something(self):
        loc = self.sever_a_limb()
        self.assertIn(loc, _untreated_stumps(self.patient))

    def test_a_stump_has_no_open_incision(self):
        """The whole point -- if severance opened an incision there
        would be no disagreement to fix."""
        self.sever_a_limb()
        self.assertEqual(open_incision_locations(self.patient), [])

    def test_but_it_is_sutureable(self):
        loc = self.sever_a_limb()
        self.assertIn(loc, _sutureable(self.patient))

    def test_an_untouched_body_is_not_sutureable(self):
        self.assertEqual(_sutureable(self.patient), [])


class TestTheVerbNoLongerRefusesTheStump(_SurgeryCase):
    def test_the_guard_admits_a_stump_only_body(self):
        self.sever_a_limb()
        self.assertTrue(_sutureable(self.patient),
                        "the verb's guard would refuse this body")

    def test_the_guard_and_the_resolver_read_the_same_set(self):
        """`_resolve_suture` closes `open incisions | untreated
        stumps`. The guard must not be narrower than that."""
        loc = self.sever_a_limb()
        from world.medical import procedures
        resolver_set = (set(procedures.open_incision_locations(self.patient))
                        | _untreated_stumps(self.patient))
        self.assertEqual(set(_sutureable(self.patient)),
                         resolver_set)
        self.assertIn(loc, resolver_set)


class TestTheVerbItselfNoLongerRefuses(_SurgeryCase):
    """The player-visible half of #2554, driven through the command
    rather than the helper -- it uses no symbol this change
    introduces, so it fails honestly against the unfixed tree instead
    of turning the file into a loader error."""

    def setUp(self):
        super().setUp()
        # The trust/consent gate (TRUST_AND_CONSENT_SPEC §3, `heal`
        # class) fires BEFORE the incision guard, so a conscious
        # patient who has not consented never reaches the code under
        # test. My first version of this class asserted the absence of
        # a refusal that was never going to be reached -- three
        # vacuous passes. The control below is what caught it.
        from world.consent import grant_trust
        grant_trust(self.patient, self.char1, "heal")

    def _suture(self, arg):
        from commands.CmdSurgical import CmdSuture
        cmd = CmdSuture()
        cmd.caller = self.char1
        cmd.args = f" {arg}"
        cmd.obj = self.char1
        self.said.clear()
        try:
            cmd.func()
        except Exception:
            # A later step (kit, roll, timers) is not what is under
            # test; only whether the guard let us past it.
            pass
        return "\n".join(self.said)

    def test_the_consent_gate_is_open_for_this_fixture(self):
        """Vacuity guard. Without this, every assertion in this class
        passes on a refusal that never reaches the suture guard."""
        from world.consent import check_consent
        self.assertTrue(check_consent(self.char1, self.patient, "heal"))

    def test_a_stump_only_patient_is_not_turned_away(self):
        self.sever_a_limb()
        out = self._suture("patient")
        self.assertNotIn("no open incisions", out)
        self.assertNotIn("nothing that needs closing", out)

    def test_naming_the_stump_location_is_not_turned_away(self):
        stump = self.sever_a_limb()
        out = self._suture(f"patient's {stump.replace('_', ' ')}")
        # Assert the GENERIC refusal too: on the unfixed tree the
        # empty-open_locs branch fires first, so checking only the
        # location-specific wording passed vacuously.
        self.assertNotIn("no open incisions", out)
        self.assertNotIn("nothing that needs closing", out)
        self.assertNotIn("isn't incised", out)
        self.assertNotIn("has nothing to close", out)

    def test_an_uninjured_patient_is_still_turned_away(self):
        """The guard must still guard -- a fix that admits everything
        would pass both tests above."""
        out = self._suture("patient")
        self.assertTrue(
            "nothing that needs closing" in out
            or "no open incisions" in out,
            f"an uninjured patient was admitted: {out!r}")


class TestThePickerNoLongerGuesses(_SurgeryCase):
    def setUp(self):
        super().setUp()
        self.stump = self.sever_a_limb()

    def test_the_picker_offers_the_stump(self):
        values = [v for v, _label in self.arm_picker()]
        self.assertIn(self.stump, values)

    def test_entries_are_value_first(self):
        """The convention `_pick_aliases` depends on. Stored the other
        way round, the label's colour codes and tags become matchable
        text -- which is the defect."""
        for value, label in self.arm_picker():
            self.assertNotIn("|", value)

    def test_typing_stump_does_not_silently_select_all(self):
        self.arm_picker()
        _process_suture_location(self.char1, "stump")
        self.assertEqual(self.steps(), [],
                         "a step was added for an unmatched word")

    def test_typing_n_does_not_silently_select_all(self):
        self.arm_picker()
        _process_suture_location(self.char1, "n")
        added = [s for s in self.steps() if s["args"] == {}]
        self.assertEqual(added, [],
                         "'n' selected the whole-body suture")

    def test_the_all_sentinel_is_a_token_not_a_sentence(self):
        """The root cause of the "n" case: the value is what the
        matcher sees, so a sentence makes almost every letter a
        substring hit."""
        self.assertNotIn(" ", _suture_all())

    def test_an_unmatched_word_refuses_rather_than_guessing(self):
        self.arm_picker()
        self.said.clear()
        _process_suture_location(self.char1, "zzzz")
        self.assertEqual(self.steps(), [])
        self.assertTrue(self.said, "refused silently")


class TestThePickerStillWorks(_SurgeryCase):
    """A guard that refuses everything would pass every test above."""

    def setUp(self):
        super().setUp()
        self.stump = self.sever_a_limb()

    def test_naming_the_stump_location_selects_it(self):
        self.arm_picker()
        _process_suture_location(self.char1, self.stump.replace("_", " "))
        self.assertEqual([s["args"] for s in self.steps()],
                         [{"location": self.stump}])

    def test_the_underscore_form_works_too(self):
        self.arm_picker()
        _process_suture_location(self.char1, self.stump)
        self.assertEqual([s["args"] for s in self.steps()],
                         [{"location": self.stump}])

    def test_typing_all_still_selects_the_whole_body_suture(self):
        self.arm_picker()
        _process_suture_location(self.char1, "all")
        self.assertEqual([s["args"] for s in self.steps()], [{}])

    def test_a_numeric_pick_still_works(self):
        items = self.arm_picker()
        _process_suture_location(self.char1, "1")
        expected = {} if items[0][0] == _suture_all() else {
            "location": items[0][0]}
        self.assertEqual([s["args"] for s in self.steps()], [expected])

    def test_cancel_still_returns_to_the_top(self):
        self.arm_picker()
        self.assertEqual(_process_suture_location(self.char1, "x"),
                         "node_top")
