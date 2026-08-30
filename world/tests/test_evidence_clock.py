"""Evidence ages on a clock that survives a restore (#2414).

Blood and graffiti were stamped with `evennia.utils.gametime`, which returns
ACCUMULATED SERVER RUNTIME. That counter is not monotonic: a database restore
rewinds it while stored stamps keep their values. A live stain read

    Evidence age span: -8649.8 hours

with server gametime at 40,725,994 and the stain stamped 71,865,364 — dated
about 360 days in the future. Others read as 54 years old.

This is not cosmetic. Blood age feeds the freshness description AND an
identification-confidence penalty, so corrupt ages quietly corrupt forensics.

`world.gametime.stamp()` is real POSIX seconds and already existed for exactly
this — "stored time should be a plain monotonic number so durations are
subtraction". No new clock was introduced.
"""
import time

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from typeclasses.objects import LEGACY_RUNTIME_STAMP_MAX, _incident_age_hours


class TestEvidenceAge(BaseEvenniaTest):

    def test_a_recent_stamp_reads_its_real_age(self):
        two_hours_ago = time.time() - 7200
        self.assertAlmostEqual(
            _incident_age_hours({"timestamp": two_hours_ago}), 2.0, places=1)

    def test_a_future_stamp_never_reads_negative(self):
        """The reported symptom. `since` clamps, so the worst case is 'fresh'
        rather than a number that cannot exist."""
        ahead = time.time() + 31_000_000
        self.assertEqual(_incident_age_hours({"timestamp": ahead}), 0.0)

    def test_a_legacy_runtime_stamp_is_not_treated_as_real_time(self):
        """A runtime-scale value is unconvertible — the mapping went with the
        counter. Reading it as an epoch stamp would produce a 54-year-old
        puddle, which is worse than admitting we do not know."""
        self.assertEqual(_incident_age_hours({"timestamp": 71_865_364}), 0.0)

    def test_the_legacy_boundary_is_below_any_real_stamp(self):
        self.assertLess(LEGACY_RUNTIME_STAMP_MAX, time.time())

    def test_missing_or_empty_is_safe(self):
        self.assertEqual(_incident_age_hours({}), 0.0)
        self.assertEqual(_incident_age_hours(None), 0.0)


class TestStainsUseIt(BaseEvenniaTest):

    def test_a_fresh_stain_is_fresh(self):
        stain = create_object("typeclasses.objects.BloodPool",
                              key="blood stains", location=self.room1)
        stain.db.bleeding_incidents = [
            {"timestamp": time.time() - 1800, "severity": 5}]
        self.assertAlmostEqual(stain.get_age_hours(), 0.5, places=1)

    def test_a_stain_with_no_incidents_is_zero(self):
        stain = create_object("typeclasses.objects.BloodPool",
                              key="blood stains", location=self.room1)
        stain.db.bleeding_incidents = []
        self.assertEqual(stain.get_age_hours(), 0)

    def test_a_legacy_stain_no_longer_reports_a_negative_span(self):
        """The exact live case, pinned."""
        stain = create_object("typeclasses.objects.BloodPool",
                              key="blood stains", location=self.room1)
        stain.db.bleeding_incidents = [
            {"timestamp": 71_865_364, "severity": 8},
            {"timestamp": 71_866_047, "severity": 36},
        ]
        self.assertGreaterEqual(stain.get_age_hours(), 0)
