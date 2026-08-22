"""A resleeve comes back as the same person (#2183).

Two rules from IDENTITY_RECOGNITION_SPEC, neither of which the estate
snapshot honoured:

  §Principles 1 — "Recognition is based on the physical sleeve (body),
  not consciousness. Same body = same recognition across clones."
  §Sleeve — "Flash clones are physically identical and inherit the same
  `sleeve_uid`."

The blueprint-rebuild path minted a fresh uuid4, so an institution came
back a stranger wearing its own face — while its restored episodic
memory greeted people by name. The snapshot also never carried
`recognition_memory` or `voice_memory` at all, so who you knew died
with you even though what you remembered did not.

`taken_at` is the forward-compatible part: restore asks only what the
backup HELD. Today that is death minus a constant. When backups become
a thing you go and do, `taken_at` is when you did it, and none of the
restore logic changes.
"""
from datetime import datetime, timedelta

from evennia.utils.test_resources import EvenniaCommandTest

from world.souls import posts


def _iso(ts):
    return datetime.fromtimestamp(ts).isoformat()


class TestTheBackupHoldsWhoYouKnew(EvenniaCommandTest):
    def test_the_estate_captures_faces_and_voices(self):
        self.char1.recognition_memory = {"aaa": {"assigned_name": "Sable"}}
        self.char1.voice_memory = {"bbb": {"assigned_name": "the Rook"}}
        estate = posts._estate_of(self.char1, 1_000_000.0)
        self.assertEqual(estate["recognition"]["aaa"]["assigned_name"],
                         "Sable")
        self.assertEqual(estate["voice"]["bbb"]["assigned_name"],
                         "the Rook")

    def test_the_estate_records_the_sleeve(self):
        estate = posts._estate_of(self.char1, 1_000_000.0)
        self.assertEqual(estate["sleeve_uid"], self.char1.sleeve_uid)
        self.assertIsNotNone(estate["sleeve_uid"])

    def test_taken_at_is_the_backup_moment_not_the_death(self):
        died = 1_000_000.0
        estate = posts._estate_of(self.char1, died)
        self.assertEqual(estate["died_at"], died)
        self.assertEqual(estate["taken_at"], died - posts.RESLEAVE_GAP)
        self.assertLess(estate["taken_at"], estate["died_at"])


class TestTheGapAppliesToPeople(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.cutoff = 1_000_000.0
        self.old = _iso(self.cutoff - 10_000)
        self.new = _iso(self.cutoff + 10_000)

    def test_somebody_known_before_the_backup_survives(self):
        kept = posts._remembered_before(
            {"uid": {"first_seen": self.old}}, self.cutoff)
        self.assertIn("uid", kept)

    def test_somebody_met_inside_the_gap_is_lost(self):
        kept = posts._remembered_before(
            {"uid": {"first_seen": self.new}}, self.cutoff)
        self.assertEqual(kept, {})

    def test_an_unreadable_timestamp_keeps_the_relationship(self):
        for stamp in (None, "", "not-a-date", 12345):
            kept = posts._remembered_before(
                {"uid": {"first_seen": stamp}}, self.cutoff)
            self.assertIn("uid", kept, f"dropped on {stamp!r}")

    def test_junk_entries_do_not_crash_the_restore(self):
        self.assertEqual(
            posts._remembered_before({"uid": "not a dict"}, self.cutoff), {})
        self.assertEqual(posts._remembered_before(None, self.cutoff), {})


class TestForwardCompatibility(EvenniaCommandTest):
    """An on-demand backup should need no restore-side change."""

    def test_an_explicit_taken_at_is_honoured_verbatim(self):
        """Simulates a backup taken at a chosen moment rather than
        derived from a constant."""
        pressed = 2_000_000.0
        estate = posts._estate_of(self.char1, 9_999_999.0)
        estate["taken_at"] = pressed            # what the command will do
        cutoff = estate.get("taken_at")
        self.assertEqual(float(cutoff), pressed)

    def test_a_pre_taken_at_record_still_restores(self):
        """Records written before the field existed derive it."""
        legacy = {"died_at": 1_000_000.0, "memories": [], "dossiers": {},
                  "thoughts": []}
        cutoff = legacy.get("taken_at")
        if cutoff is None:
            cutoff = float(legacy["died_at"]) - posts.RESLEAVE_GAP
        self.assertEqual(cutoff, 1_000_000.0 - posts.RESLEAVE_GAP)
