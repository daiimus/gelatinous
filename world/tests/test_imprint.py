"""One imprint, both kinds of person (#2188).

Players and NPCs resleeve through the SAME capture/restore functions,
so they cannot drift into different rules about what survives a death.
That matters more than the feature: when backups become something a
character does at a terminal, the change lands for everybody at once
because there is only one path to change.

Owner ruling (2026-08-22): PCs retain who they knew, minus the gap.
"""
from datetime import datetime, timedelta

from evennia.utils.test_resources import EvenniaCommandTest

from world import imprint


def _iso(dt):
    return dt.isoformat()


class TestCapture(EvenniaCommandTest):
    def test_it_records_the_body_and_the_people(self):
        self.char1.recognition_memory = {"aaa": {"assigned_name": "Sable"}}
        self.char1.voice_memory = {"bbb": {"assigned_name": "the Rook"}}
        snap = imprint.capture(self.char1, 1_000_000.0)
        self.assertEqual(snap["sleeve_uid"], self.char1.sleeve_uid)
        self.assertEqual(snap["recognition"]["aaa"]["assigned_name"], "Sable")
        self.assertEqual(snap["voice"]["bbb"]["assigned_name"], "the Rook")

    def test_taken_at_is_the_backup_not_the_death(self):
        snap = imprint.capture(self.char1, 1_000_000.0)
        self.assertEqual(snap["died_at"], 1_000_000.0)
        self.assertEqual(snap["taken_at"], 1_000_000.0 - imprint.GAP)

    def test_a_person_with_no_episodic_brain_still_captures(self):
        """A player has no llm_memories; that must not break capture."""
        snap = imprint.capture(self.char1, 1_000_000.0)
        self.assertEqual(snap["memories"], [])
        self.assertEqual(snap["dossiers"], {})


class TestCutoff(EvenniaCommandTest):
    def test_taken_at_wins_when_present(self):
        self.assertEqual(
            imprint.cutoff_of({"taken_at": 42.0, "died_at": 9_999.0}), 42.0)

    def test_older_records_derive_it(self):
        self.assertEqual(
            imprint.cutoff_of({"died_at": 1_000_000.0}),
            1_000_000.0 - imprint.GAP)

    def test_an_on_demand_backup_needs_no_restore_change(self):
        """The whole point of storing taken_at rather than deriving."""
        pressed = 2_000_000.0
        self.assertEqual(imprint.cutoff_of({"taken_at": pressed,
                                           "died_at": 9_000_000.0}), pressed)


class TestTheGapAppliesToPeople(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.cut = 1_000_000.0
        self.before = _iso(datetime.fromtimestamp(self.cut - 10_000))
        self.after = _iso(datetime.fromtimestamp(self.cut + 10_000))

    def test_known_before_the_backup_survives(self):
        self.assertIn("u", imprint.remembered_before(
            {"u": {"first_seen": self.before}}, self.cut))

    def test_met_inside_the_gap_is_lost(self):
        self.assertEqual(imprint.remembered_before(
            {"u": {"first_seen": self.after}}, self.cut), {})

    def test_a_bad_timestamp_keeps_the_relationship(self):
        for stamp in (None, "", "nonsense", 12345):
            self.assertIn("u", imprint.remembered_before(
                {"u": {"first_seen": stamp}}, self.cut), f"lost on {stamp!r}")

    def test_junk_does_not_crash(self):
        self.assertEqual(imprint.remembered_before({"u": "nope"}, self.cut), {})
        self.assertEqual(imprint.remembered_before(None, self.cut), {})


class TestRestoreIsOnePathForEverybody(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.cut = 1_000_000.0
        old = _iso(datetime.fromtimestamp(self.cut - imprint.GAP - 10_000))
        recent = _iso(datetime.fromtimestamp(self.cut - 10))
        self.snap = {
            "version": 1, "name": "Laszlo",
            "sleeve_uid": "body-abc",
            "died_at": self.cut, "taken_at": self.cut - imprint.GAP,
            "memories": [], "dossiers": {}, "thoughts": [],
            "recognition": {"old": {"first_seen": old,
                                    "assigned_name": "Sable"},
                            "new": {"first_seen": recent,
                                    "assigned_name": "the stranger"}},
            "voice": {"old": {"first_seen": old}},
        }

    def test_the_clone_wakes_knowing_the_old_friend(self):
        imprint.restore(self.char2, self.snap)
        self.assertIn("old", self.char2.recognition_memory)
        self.assertEqual(
            self.char2.recognition_memory["old"]["assigned_name"], "Sable")

    def test_the_clone_does_not_know_who_it_met_in_the_alley(self):
        imprint.restore(self.char2, self.snap)
        self.assertNotIn("new", self.char2.recognition_memory)

    def test_voice_comes_back_too(self):
        imprint.restore(self.char2, self.snap)
        self.assertIn("old", self.char2.voice_memory)

    def test_the_sleeve_is_inherited(self):
        imprint.restore(self.char2, self.snap)
        self.assertEqual(self.char2.sleeve_uid, "body-abc")

    def test_an_empty_record_is_a_no_op(self):
        self.assertFalse(imprint.restore(self.char2, None))
        self.assertFalse(imprint.restore(self.char2, {}))


class TestBothPathsUseIt(EvenniaCommandTest):
    def test_the_npc_path_delegates(self):
        """posts._imprint_of must BE imprint.capture, not a copy of it."""
        from world.souls import posts
        snap = posts._imprint_of(self.char1, 1_000_000.0)
        self.assertEqual(snap, imprint.capture(self.char1, 1_000_000.0))

    def test_the_player_path_restores_through_it(self):
        import inspect

        from commands import charcreate
        src = inspect.getsource(charcreate.create_flash_clone)
        self.assertIn("imprint_mod.restore", src)
        self.assertNotIn("recognition_memory is NOT inherited", src)


class TestRestoreAppliesOnlyWhatTheRecordHolds(EvenniaCommandTest):
    """A record without face/voice must not erase the body's own (#2799).

    `restore` guards four fields with `if snap.get(...)` and wrote the
    last two unconditionally, `or {}`-ing a missing key into an empty
    dict. Restoring a record written before recognition existed therefore
    wiped the recognition and voice memory of the body it was restored
    onto — silently, and totally.

    The docstring already states the contract: "Applies only what the
    record holds."
    """

    def test_a_record_without_recognition_leaves_it_alone(self):
        self.char1.recognition_memory = {"uid-a": {"assigned_name": "Sully"}}
        self.char1.voice_memory = {"v-a": {"assigned_name": "Sully"}}
        # a legacy snapshot: no recognition/voice keys at all
        imprint.restore(self.char1, {"sleeve_uid": "sleeve-1"})
        self.assertEqual(self.char1.recognition_memory,
                         {"uid-a": {"assigned_name": "Sully"}})
        self.assertEqual(self.char1.voice_memory,
                         {"v-a": {"assigned_name": "Sully"}})

    def test_a_record_that_holds_them_still_applies(self):
        self.char1.recognition_memory = {"old": {"assigned_name": "Old"}}
        imprint.restore(self.char1, {
            "sleeve_uid": "sleeve-1",
            "recognition": {"uid-b": {"assigned_name": "Vesper",
                                      "first_seen": 0}},
        })
        self.assertIn("uid-b", self.char1.recognition_memory)
