"""The floor is painted when it would show, not every tick (#3077).

Painting the blood pool was 72% of a bleeding tick: a linear scan of
`room.contents`, then four attribute writes on the pool's row and a
description rebuild -- every tick, per bleeder. N bleeders in one room
were N writers on one row, sixty times a minute. At 1,000 wounded
bodies that is the difference between 11% and 42% of the reactor.

The floor does not need repainting every tick. It needs to be right
when somebody looks. Volume now accumulates on the bleeder's script
(`ndb`) and flushes when a player is in the room, when the pending
volume would move the pool into a new rendering band, when
`_flush_ticks()` have elapsed, or when the script stops.

What must NOT change, and is pinned here:

* the maths -- blood loss is billed on every tick whether or not the
  pool is written; a body nobody can see still bleeds out on schedule;
* a player in the room sees full fidelity, exactly as before;
* forensics reads the same evidence: it de-duplicates sources on
  `apparent_uid` and keeps the latest `timestamp` per source, so one
  incident per bleeder per flush carrying the summed severity is the
  same evidence in fewer rows;
* nothing pending is lost when the script stops.

The presence check uses the real session layer: `EvenniaTest` gives
`char1` a puppeted session, so a bleeder in `char1`'s room is watched
and a bleeder in `room2` is not. No mocks.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.objects import BloodPool
from world.medical.conditions import BleedingCondition
from world.medical.script import start_medical_script


def _flush_ticks():
    """Introduced by this change -- imported lazily so the unfixed tree
    fails behaviourally instead of as a loader error."""
    from world.medical.constants import BLOOD_POOL_FLUSH_TICKS
    return BLOOD_POOL_FLUSH_TICKS


class _BleedCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        # `EvenniaTest` builds a session but never puppets it, so every
        # room reads as unwatched. Puppet char1 through the real account
        # path so the presence check exercises the session layer it
        # runs against in production, not a stub.
        self.account.puppet_object(self.session, self.char1)

    def bleeder(self, room, severity=6):
        body = create_object("typeclasses.characters.Character",
                             key="a bleeder", location=room)
        body.msg = lambda text=None, **kw: None
        state = body.medical_state
        state.conditions.append(BleedingCondition(severity=severity,
                                                  location="chest"))
        body.medical_state = state
        body.save_medical_state()
        script = start_medical_script(body)
        self.addCleanup(lambda: script._stop_task())
        return body, script

    @staticmethod
    def pools(room):
        return [o for o in room.contents if getattr(o.db, "is_blood_pool", False)]


class TestThePremise(_BleedCase):
    def test_char1_really_is_a_puppeted_session_in_room1(self):
        """Vacuity guard for every watched/unwatched split below."""
        from evennia.server.sessionhandler import SESSIONS
        puppets = [s.get_puppet() for s in SESSIONS.get_sessions()]
        self.assertIn(self.char1, puppets)
        self.assertEqual(self.char1.location, self.room1)

    def test_room2_is_unwatched(self):
        from world.medical.script import MedicalScript
        self.assertFalse(MedicalScript._room_is_watched(self.room2))
        self.assertTrue(MedicalScript._room_is_watched(self.room1))


class TestTheMathsIsNeverGated(_BleedCase):
    def test_an_unwatched_body_still_loses_blood(self):
        body, script = self.bleeder(self.room2, severity=1)
        before = body.medical_state.blood_level
        script.at_repeat()
        self.assertLess(body.medical_state.blood_level, before)

    def test_the_first_bleed_paints_once_then_a_trickle_waits(self):
        """The first blood on a clean floor is written at once -- one
        write, so blood appears when bleeding starts. After that,
        severity 1 stays inside band 0 (<=3) with nobody present, so
        the next ticks accumulate in memory instead of repainting."""
        body, script = self.bleeder(self.room2, severity=1)
        script.at_repeat()
        pools = self.pools(self.room2)
        self.assertEqual(len(pools), 1)
        self.assertEqual(len(pools[0].db.bleeding_incidents), 1)
        script.at_repeat(); script.at_repeat()
        self.assertEqual(len(pools[0].db.bleeding_incidents), 1)
        self.assertGreater(float(script.ndb._pool_pending or 0), 0)


class TestAWatchedRoomIsFullFidelity(_BleedCase):
    def test_a_player_present_gets_the_pool_on_the_first_tick(self):
        body, script = self.bleeder(self.room1, severity=1)
        script.at_repeat()
        self.assertEqual(len(self.pools(self.room1)), 1)

    def test_and_every_tick_after(self):
        body, script = self.bleeder(self.room1, severity=1)
        script.at_repeat(); script.at_repeat(); script.at_repeat()
        pool = self.pools(self.room1)[0]
        self.assertEqual(len(pool.db.bleeding_incidents), 3)
        self.assertEqual(float(script.ndb._pool_pending or 0), 0.0)


class TestUnwatchedFlushTriggers(_BleedCase):
    def test_a_band_crossing_flushes_at_once(self):
        """Severity 6 takes an empty floor from band 0 to band 1: the
        text would change, so it is written even with nobody there."""
        body, script = self.bleeder(self.room2, severity=6)
        script.at_repeat()
        pools = self.pools(self.room2)
        self.assertEqual(len(pools), 1)
        self.assertEqual(pools[0].db.total_volume, 6)

    def test_the_checkpoint_flushes_without_a_band_change(self):
        """Pending stays inside band 0, but the bounded-loss checkpoint
        still lands it on the floor."""
        body, script = self.bleeder(self.room2, severity=1)
        script._create_blood_pool(0.5)              # first blood: paints
        pool = self.pools(self.room2)[0]
        for _ in range(_flush_ticks() - 1):
            script._create_blood_pool(0.5)          # pending, no repaint
        self.assertEqual(len(pool.db.bleeding_incidents), 1)
        script._create_blood_pool(0.5)              # checkpoint tick
        self.assertEqual(len(pool.db.bleeding_incidents), 2)
        self.assertAlmostEqual(pool.db.total_volume,
                               0.5 * (_flush_ticks() + 1))

    def test_a_flush_is_one_incident_with_the_summed_severity(self):
        body, script = self.bleeder(self.room2, severity=1)
        script._create_blood_pool(0.5)              # first blood: paints
        for _ in range(_flush_ticks()):
            script._create_blood_pool(0.5)          # one checkpoint batch
        pool = self.pools(self.room2)[0]
        self.assertEqual(len(pool.db.bleeding_incidents), 2)
        self.assertAlmostEqual(pool.db.bleeding_incidents[1]["severity"],
                               0.5 * _flush_ticks())

    def test_stopping_the_script_flushes_what_is_pending(self):
        body, script = self.bleeder(self.room2, severity=1)
        script._create_blood_pool(0.5)              # first blood: paints
        pool = self.pools(self.room2)[0]
        script._create_blood_pool(0.5)
        script._create_blood_pool(0.5)              # 1.0 pending in memory
        self.assertEqual(len(pool.db.bleeding_incidents), 1)
        script.at_stop()
        self.assertEqual(len(pool.db.bleeding_incidents), 2)
        self.assertAlmostEqual(pool.db.total_volume, 1.5)


class TestForensicsReadsTheSameEvidence(_BleedCase):
    def test_the_batched_incident_carries_identity(self):
        body, script = self.bleeder(self.room2, severity=1)
        script._create_blood_pool(0.5)
        for _ in range(_flush_ticks()):
            script._create_blood_pool(0.5)
        pool = self.pools(self.room2)[0]
        inc = pool.db.bleeding_incidents[-1]        # the batched one
        from world.identity import get_apparent_uid
        self.assertEqual(inc["apparent_uid"], get_apparent_uid(body))
        self.assertIn("timestamp", inc)
        self.assertIn("blood_color", inc)

    def test_the_forensic_extractor_accepts_it(self):
        from world.forensics import extract_subject_from_blood_pool_incident
        body, script = self.bleeder(self.room2, severity=6)
        script.at_repeat()
        pool = self.pools(self.room2)[0]
        subject = extract_subject_from_blood_pool_incident(
            pool, pool.db.bleeding_incidents[0])
        self.assertEqual(subject.source_kind, "blood_pool")


class TestThePoolCacheValidatesItself(_BleedCase):
    def test_a_deleted_pool_is_not_served_stale(self):
        body, script = self.bleeder(self.room2, severity=6)
        script.at_repeat()
        pool = self.pools(self.room2)[0]
        self.assertIs(self.room2.ndb._blood_pool, pool)
        pool.delete()
        from world.medical.script import MedicalScript
        self.assertIsNone(MedicalScript._find_blood_pool(self.room2))

    def test_a_second_flush_after_cleaning_makes_a_fresh_pool(self):
        body, script = self.bleeder(self.room2, severity=6)
        script.at_repeat()
        self.pools(self.room2)[0].delete()
        script.at_repeat()
        self.assertEqual(len(self.pools(self.room2)), 1)

    def test_two_bleeders_share_one_pool(self):
        a, sa = self.bleeder(self.room2, severity=6)
        b, sb = self.bleeder(self.room2, severity=6)
        sa.at_repeat(); sb.at_repeat()
        self.assertEqual(len(self.pools(self.room2)), 1)


class TestOneDefinitionOfTheBands(EvenniaTest):
    def test_band_index_agrees_with_the_description_at_every_edge(self):
        pool = create_object(BloodPool, key="blood stains", location=self.room1)
        seen = {}
        for volume in (0, 3, 4, 10, 11, 20, 21, 35, 36, 99):
            pool.db.total_volume = volume
            seen.setdefault(BloodPool.volume_band(volume), set()).add(
                pool.get_volume_description())
        for band, labels in seen.items():
            self.assertEqual(len(labels), 1, f"band {band} renders {labels}")
        self.assertEqual(len(seen), 5)
