"""`@heal`'s partial branches removed conditions behind the cache's back,
and their "least severe first" ordering ordered nothing (#2544).

**The stale death verdict.** Both partial branches removed conditions
with a raw `list.remove()` instead of `MedicalState.remove_condition()`,
skipping `_invalidate_derived_state()` -- the only thing that clears
`_cached_is_dead`. Conditions are a genuine input to that verdict:
`_compute_is_dead` reads `calculate_body_capacity`, and conditions
modify organ functionality. Nothing else on the path clears the cache
either -- `save_medical_state()` only serializes, and
`update_vital_signs()` assigns `pain_level` / `consciousness`, which are
plain attributes with no setter. Worse, both branches then STOP the
medical script when the list empties, so no future tick would recompute.

A staff member reviving someone by removing the condition that killed
them saw the success message and the character stayed dead to the game,
because `Character.msg` consults `is_dead()` on every message.

The same raw-removal shape was in two more places the issue did not
list: `MedicalScript.at_repeat` (which reads `is_dead()` a few lines
later) and `@heal`'s consciousness-suppression branch. The latter
happens to escape, because it assigns `blood_level` afterwards and that
setter invalidates -- but relying on a later unrelated assignment is not
a property the next edit should have to preserve. All four now route
through `remove_condition`.

**And the ordering.** `severity_order` was keyed by strings
("minor"/"moderate"/...) while every severity the engine writes is an
integer, so `.get()` missed on every lookup and scored everything `0`.
`least_severity` started at `inf`: the first condition scored `0 < inf`
and won; every later one scored `0 < 0` and lost. The loop always took
the FIRST condition in list order -- the oldest, not the mildest.

The string form survives only as the default argument of
`Character.add_medical_condition`, which has no callers repo-wide. The
sort key maps the legacy words onto the numeric ladder rather than
crashing, using the same boundaries `medinfo` uses (#2534).

NOT fixed, because it does not exist: the issue's second defect, the
un-stopped ticker. `remove_condition` guards it with
`hasattr(condition, 'stop_condition')` and **no `stop_condition` is
defined anywhere in the tree** -- conditions lost their own tickers when
the medical script became the sampler, which is the same reason
`tick_interval` is inert (#2514). That branch has never fired.
"""
from evennia.utils.test_resources import EvenniaTest

from world.medical.conditions import BleedingCondition, PainCondition


def _severity_rank(condition):
    from commands.CmdAdmin import _severity_rank as fn
    return fn(condition)


class _HealCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char2.location = self.room1
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))
        self.char2.msg = lambda text=None, **kw: None

    def give(self, *conditions):
        state = self.char2.medical_state
        for c in conditions:
            state.conditions.append(c)
        self.char2.medical_state = state
        self.char2.save_medical_state()
        return state

    def heal(self, args):
        from commands.CmdAdmin import CmdHeal
        cmd = CmdHeal()
        cmd.caller = self.char1
        cmd.obj = self.char1
        cmd.args = f" {args}"
        self.said.clear()
        cmd.func()
        return "\n".join(self.said)

    def severities(self):
        return sorted(c.severity for c in self.char2.medical_state.conditions)


class TestTheFixtureDrivesTheRealCommand(_HealCase):
    """Vacuity guards. Every assertion below reads state after a
    command run; if the command never ran, they all pass for free."""

    def test_conditions_are_actually_present(self):
        self.give(PainCondition(severity=4, location="chest"))
        self.assertEqual(len(self.char2.medical_state.conditions), 1)

    def test_healing_reports_success(self):
        self.give(PainCondition(severity=4, location="chest"))
        out = self.heal(f"{self.char2.key} = pain")
        self.assertIn("healed", out.lower())

    def test_healing_actually_removes(self):
        self.give(PainCondition(severity=4, location="chest"))
        self.heal(f"{self.char2.key} = pain")
        self.assertEqual(self.char2.medical_state.conditions, [])


class TestTheDeathVerdictIsNotLeftStale(_HealCase):
    """Behavioural: poison the cache with a verdict the state does not
    support, then check the command's removal forces a recompute. On the
    unfixed tree the raw `list.remove` leaves the lie in place."""

    def _poison(self):
        state = self.char2.medical_state
        state._cached_is_dead = True
        self.assertIs(state.is_dead(), True, "cache did not take")
        return state

    def test_condition_type_branch_clears_the_cache(self):
        self.give(PainCondition(severity=4, location="chest"))
        state = self._poison()
        self.heal(f"{self.char2.key} = pain")
        self.assertIs(state.is_dead(), False,
                      "the character is still dead to the game")

    def test_partial_branch_clears_the_cache(self):
        self.give(PainCondition(severity=4, location="chest"),
                  BleedingCondition(severity=2, location="arm"))
        state = self._poison()
        self.heal(f"{self.char2.key} = 1")
        self.assertIs(state.is_dead(), False)

    def test_an_untouched_body_really_is_not_dead(self):
        """Control: the recompute must return False on its own merits,
        not because the assertion is weak."""
        self.assertIs(self.char2.medical_state.is_dead(), False)


class TestLeastSevereFirstActuallyOrders(_HealCase):
    def test_the_mildest_goes_first(self):
        self.give(PainCondition(severity=8, location="chest"),
                  BleedingCondition(severity=2, location="arm"),
                  PainCondition(severity=5, location="leg"))
        self.heal(f"{self.char2.key} = 1")
        self.assertEqual(self.severities(), [5, 8])

    def test_two_mildest_go_first(self):
        self.give(PainCondition(severity=8, location="chest"),
                  BleedingCondition(severity=2, location="arm"),
                  PainCondition(severity=5, location="leg"))
        self.heal(f"{self.char2.key} = 2")
        self.assertEqual(self.severities(), [8])

    def test_it_is_not_merely_list_order(self):
        """The defect's signature: the old loop took the FIRST entry.
        Put the WORST condition first so 'first' and 'mildest' disagree
        -- otherwise the broken code passes too."""
        self.give(PainCondition(severity=9, location="chest"),
                  BleedingCondition(severity=1, location="arm"))
        self.heal(f"{self.char2.key} = 1")
        self.assertEqual(self.severities(), [9])


class TestTheSortKey(_HealCase):
    def test_numeric_severities_rank_by_value(self):
        self.assertLess(_severity_rank(PainCondition(severity=2)),
                        _severity_rank(PainCondition(severity=7)))

    def test_a_legacy_string_severity_does_not_crash(self):
        """`Character.add_medical_condition` still defaults to "minor"
        and has no callers; if one ever appears it must sort, not
        explode."""
        legacy = PainCondition(severity=3)
        legacy.severity = "moderate"
        self.assertEqual(_severity_rank(legacy), 5.0)

    def test_an_unknown_string_sorts_lowest(self):
        odd = PainCondition(severity=3)
        odd.severity = "whatever"
        self.assertEqual(_severity_rank(odd), 0.0)


class TestNothingStillRemovesRaw(EvenniaTest):
    """The point of the fix is that there is ONE way to remove a
    condition. Pin it: only the helpers themselves, plus the documented
    fallback inside `utils.remove_condition_safely`, may call
    `list.remove` on a conditions list."""

    def test_only_the_helpers_remove_raw(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        offenders = []
        for path in root.rglob("*.py"):
            if "tests" in path.parts or path.name.startswith("test_"):
                continue
            rel = path.relative_to(root).as_posix()
            if rel in ("world/medical/core.py", "world/medical/utils.py"):
                continue
            for num, line in enumerate(
                    path.read_text(errors="ignore").splitlines(), 1):
                if "conditions.remove(" in line:
                    offenders.append(f"{rel}:{num}")
        self.assertEqual(offenders, [])
