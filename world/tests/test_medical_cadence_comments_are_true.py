"""The medical constants describe the clock they actually run on (#2514).

`constants.py` is the single source of truth for medical cadence and
says so in its own words -- yet three comments in that same file still
anchored their arithmetic to an abandoned per-condition interval design,
citing a 12-second tick, a 180-second tick, and a two-tier bleeding
cadence. **None of the three exists at runtime.**

This is not a cosmetic complaint. `CONDITION_CADENCE_SPEC` §2 records
the identical trap firing once already: when #465 corrected the medical
tick from a testing-leftover 12s to the intended 60s, infection silently
became **5x slower than designed**, because its probability comments
still read "25 ticks at 12s intervals". *Nobody changed infection; they
changed the clock.* All three stale comments sat directly above balance
knobs, and no medical system has been balance-passed yet -- so they were
load-bearing for work that hasn't happened.

These tests pin the facts the comments now assert, so the next clock
change makes them fail instead of quietly lying:

* healing really is per MINUTE (behavioural -- double the elapsed time,
  double the HP), so `MEDICAL_TICK_INTERVAL` only sets sampling rate;
* the script really does ignore `condition.tick_interval`, which
  `CONDITION_CADENCE_SPEC` §7 sanctions as "retained in serialization
  for backward compatibility but ignored";
* `BLEEDING_DAMAGE_THRESHOLDS["severe"]` really is unread -- it is
  PARKED for the Phase 3 tactical tier (§1.6, "build when fire /
  severe-bleeding exist as content"), not dead, which is why it was
  left in place rather than deleted or wired.
"""
import pathlib
import re

from evennia.utils.test_resources import EvenniaTest

from world.medical.constants import (
    BLEEDING_DAMAGE_THRESHOLDS,
    CONSCIOUSNESS_RECOVERY_HAZARD_PER_MINUTE,
    MEDICAL_TICK_INTERVAL,
)
from world.medical.core import MedicalState
from world.medical.script import _hp_per_tick, _process_healing

ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestHealingIsPerMinuteNotPerTick(EvenniaTest):
    """The behavioural half. If this ever fails, the comment on
    `WOUND_HEALING_DIVISOR` has become a lie again."""

    def _dressed_organ(self, rate=25):
        state = MedicalState(self.char1)
        organ = next(iter(state.organs.values()))
        # A deep deficit on purpose: `Organ.heal` caps at `max_hp`, and
        # a shallow wound makes the 4-minute pass hit the ceiling and
        # look sub-linear when it is not. My first fixture did exactly
        # that -- 9 HP against an expected 20.
        organ.max_hp = 500
        organ.current_hp = 1
        organ.stabilized = True
        organ.dressing_rate = rate
        organ.dressing_progress = 0.0
        return state, organ

    def test_the_rate_is_nonzero_for_this_fixture(self):
        """Vacuity guard -- a rate below the divisor heals 0 and would
        make every assertion below pass for the wrong reason."""
        self.assertGreater(_hp_per_tick(25), 0)

    def test_four_minutes_heals_four_times_one_minute(self):
        state_a, organ_a = self._dressed_organ()
        _process_healing(self.char1, state_a, elapsed_minutes=1.0)
        one = organ_a.current_hp

        state_b, organ_b = self._dressed_organ()
        _process_healing(self.char1, state_b, elapsed_minutes=4.0)
        four = organ_b.current_hp

        self.assertEqual(four - 1, (one - 1) * 4)

    def test_elapsed_time_is_what_moves_hp_not_the_tick_constant(self):
        state, organ = self._dressed_organ()
        _process_healing(self.char1, state, elapsed_minutes=0.0)
        self.assertEqual(organ.current_hp, 1)


class TestTheScriptIgnoresPerConditionIntervals(EvenniaTest):
    """CONDITION_CADENCE_SPEC §7: `tick_interval` is retained in
    serialization and ignored. The per-condition values (60/120/300)
    are inert."""

    def test_the_script_never_consults_tick_interval(self):
        body = (ROOT / "world" / "medical" / "script.py").read_text()
        self.assertNotIn("tick_interval", body)

    def test_the_field_is_still_serialized_for_compatibility(self):
        from world.medical.conditions import PainCondition
        self.assertIn("tick_interval", PainCondition(severity=3).to_dict())

    def test_the_declared_interval_is_sixty(self):
        self.assertEqual(MEDICAL_TICK_INTERVAL, 60)


class TestTheParkedSevereTierIsStillParked(EvenniaTest):
    """Not deleted, not wired. Either move would be wrong: deleting
    discards the Phase 3 threshold, wiring it makes a balance decision
    on an untuned system."""

    def test_the_key_still_exists(self):
        self.assertIn("severe", BLEEDING_DAMAGE_THRESHOLDS)

    def test_nothing_reads_it(self):
        hits = []
        for path in ROOT.rglob("*.py"):
            if "test" in path.parts or path.name.startswith("test_"):
                continue
            for line in path.read_text(errors="ignore").splitlines():
                if "BLEEDING_DAMAGE_THRESHOLDS" in line and "severe" in line:
                    hits.append(f"{path.name}: {line.strip()}")
        self.assertEqual(hits, [], "the parked tier got wired up")

    def test_the_minor_tier_is_the_live_one(self):
        from world.medical.conditions import create_condition_from_damage
        below = create_condition_from_damage(
            BLEEDING_DAMAGE_THRESHOLDS["minor"] - 1, "cut", "chest")
        at = create_condition_from_damage(
            BLEEDING_DAMAGE_THRESHOLDS["minor"], "cut", "chest")
        self.assertNotIn("bleeding", {c.type for c in below})
        self.assertIn("bleeding", {c.type for c in at})


class TestNoCommentCitesACadenceThatDoesNotExist(EvenniaTest):
    """The narrow source guard, aimed at exactly one thing: a comment
    asserting a tick length the engine does not run at."""

    def test_constants_cites_no_phantom_tick(self):
        body = (ROOT / "world" / "medical" / "constants.py").read_text()
        # Allow a word or two between the number and "tick" -- the
        # original site 1 read "the existing 12s medical tick", which a
        # strict `\d+s\s+tick` pattern walks straight past.
        phantom = re.findall(
            r"\b(\d+)\s*s(?:ec(?:ond)?s?)?\b[^.\n]{0,20}?\btick", body)
        bad = [s for s in phantom if int(s) != MEDICAL_TICK_INTERVAL]
        self.assertEqual(bad, [], f"comment cites a {bad} second tick")

    def test_the_sedation_note_matches_its_own_hazard(self):
        """The comment claims a severity drop is roughly 1/hazard
        minutes. Pin the hazard it is describing."""
        self.assertEqual(
            CONSCIOUSNESS_RECOVERY_HAZARD_PER_MINUTE["sedative"], 0.50)
