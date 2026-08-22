"""One estate, both kinds of person (#2188).

Players and NPCs resleeve through the SAME capture/restore functions,
so they cannot drift into different rules about what survives a death.
That matters more than the feature: when backups become something a
character does at a terminal, the change lands for everybody at once
because there is only one path to change.

Owner ruling (2026-08-22): PCs retain who they knew, minus the gap.
"""
from datetime import datetime, timedelta

from evennia.utils.test_resources import EvenniaCommandTest

from world import estate


def _iso(dt):
    return dt.isoformat()


class TestCapture(EvenniaCommandTest):
    def test_it_records_the_body_and_the_people(self):
        self.char1.recognition_memory = {"aaa": {"assigned_name": "Sable"}}
        self.char1.voice_memory = {"bbb": {"assigned_name": "the Rook"}}
        snap = estate.capture(self.char1, 1_000_000.0)
        self.assertEqual(snap["sleeve_uid"], self.char1.sleeve_uid)
        self.assertEqual(snap["recognition"]["aaa"]["assigned_name"], "Sable")
        self.assertEqual(snap["voice"]["bbb"]["assigned_name"], "the Rook")

    def test_taken_at_is_the_backup_not_the_death(self):
        snap = estate.capture(self.char1, 1_000_000.0)
        self.assertEqual(snap["died_at"], 1_000_000.0)
        self.assertEqual(snap["taken_at"], 1_000_000.0 - estate.GAP)

    def test_a_person_with_no_episodic_brain_still_captures(self):
        """A player has no llm_memories; that must not break capture."""
        snap = estate.capture(self.char1, 1_000_000.0)
        self.assertEqual(snap["memories"], [])
        self.assertEqual(snap["dossiers"], {})


class TestCutoff(EvenniaCommandTest):
    def test_taken_at_wins_when_present(self):
        self.assertEqual(
            estate.cutoff_of({"taken_at": 42.0, "died_at": 9_999.0}), 42.0)

    def test_older_records_derive_it(self):
        self.assertEqual(
            estate.cutoff_of({"died_at": 1_000_000.0}),
            1_000_000.0 - estate.GAP)

    def test_an_on_demand_backup_needs_no_restore_change(self):
        """The whole point of storing taken_at rather than deriving."""
        pressed = 2_000_000.0
        self.assertEqual(estate.cutoff_of({"taken_at": pressed,
                                           "died_at": 9_000_000.0}), pressed)


class TestTheGapAppliesToPeople(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.cut = 1_000_000.0
        self.before = _iso(datetime.fromtimestamp(self.cut - 10_000))
        self.after = _iso(datetime.fromtimestamp(self.cut + 10_000))

    def test_known_before_the_backup_survives(self):
        self.assertIn("u", estate.remembered_before(
            {"u": {"first_seen": self.before}}, self.cut))

    def test_met_inside_the_gap_is_lost(self):
        self.assertEqual(estate.remembered_before(
            {"u": {"first_seen": self.after}}, self.cut), {})

    def test_a_bad_timestamp_keeps_the_relationship(self):
        for stamp in (None, "", "nonsense", 12345):
            self.assertIn("u", estate.remembered_before(
                {"u": {"first_seen": stamp}}, self.cut), f"lost on {stamp!r}")

    def test_junk_does_not_crash(self):
        self.assertEqual(estate.remembered_before({"u": "nope"}, self.cut), {})
        self.assertEqual(estate.remembered_before(None, self.cut), {})


class TestRestoreIsOnePathForEverybody(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.cut = 1_000_000.0
        old = _iso(datetime.fromtimestamp(self.cut - estate.GAP - 10_000))
        recent = _iso(datetime.fromtimestamp(self.cut - 10))
        self.snap = {
            "version": 1, "name": "Laszlo",
            "sleeve_uid": "body-abc",
            "died_at": self.cut, "taken_at": self.cut - estate.GAP,
            "memories": [], "dossiers": {}, "thoughts": [],
            "recognition": {"old": {"first_seen": old,
                                    "assigned_name": "Sable"},
                            "new": {"first_seen": recent,
                                    "assigned_name": "the stranger"}},
            "voice": {"old": {"first_seen": old}},
        }

    def test_the_clone_wakes_knowing_the_old_friend(self):
        estate.restore(self.char2, self.snap)
        self.assertIn("old", self.char2.recognition_memory)
        self.assertEqual(
            self.char2.recognition_memory["old"]["assigned_name"], "Sable")

    def test_the_clone_does_not_know_who_it_met_in_the_alley(self):
        estate.restore(self.char2, self.snap)
        self.assertNotIn("new", self.char2.recognition_memory)

    def test_voice_comes_back_too(self):
        estate.restore(self.char2, self.snap)
        self.assertIn("old", self.char2.voice_memory)

    def test_the_sleeve_is_inherited(self):
        estate.restore(self.char2, self.snap)
        self.assertEqual(self.char2.sleeve_uid, "body-abc")

    def test_an_empty_record_is_a_no_op(self):
        self.assertFalse(estate.restore(self.char2, None))
        self.assertFalse(estate.restore(self.char2, {}))


class TestBothPathsUseIt(EvenniaCommandTest):
    def test_the_npc_path_delegates(self):
        """posts._estate_of must BE estate.capture, not a copy of it."""
        from world.souls import posts
        snap = posts._estate_of(self.char1, 1_000_000.0)
        self.assertEqual(snap, estate.capture(self.char1, 1_000_000.0))

    def test_the_player_path_restores_through_it(self):
        import inspect

        from commands import charcreate
        src = inspect.getsource(charcreate.create_flash_clone)
        self.assertIn("estate_mod.restore", src)
        self.assertNotIn("recognition_memory is NOT inherited", src)
