"""Ambient broadcasters: the station-clock sweep (the Rook's P2)."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.director.broadcasts as bc


def _npc(flag=True, llm=True, nxt=None, interval=None):
    n = MagicMock()
    n.db = SimpleNamespace(ambient_broadcaster=flag, llm_driven=llm,
                           next_broadcast_at=nxt, broadcast_interval=interval)
    return n


class TestDue(TestCase):
    def test_first_sighting_schedules_ahead_not_fires(self):
        n = _npc()
        self.assertFalse(bc._due(n, now=1000.0))
        self.assertGreater(n.db.next_broadcast_at, 1000.0)

    def test_past_deadline_fires(self):
        self.assertTrue(bc._due(_npc(nxt=900.0), now=1000.0))
        self.assertFalse(bc._due(_npc(nxt=1100.0), now=1000.0))


class TestSweep(TestCase):
    def _sweep(self, npcs, now=1000.0):
        with patch.object(bc.ObjectDB.objects, "filter",
                          return_value=npcs):
            bc.maintain_broadcasts(now=now)

    def test_due_station_airs_and_reschedules(self):
        n = _npc(nxt=900.0, interval=100)
        self._sweep([n])
        n.llm_broadcast.assert_called_once()
        cue = n.llm_broadcast.call_args.args[0]
        self.assertIn("in the colony", cue)
        self.assertGreaterEqual(n.db.next_broadcast_at, 1075.0)  # 100*0.75
        self.assertLessEqual(n.db.next_broadcast_at, 1125.0)     # 100*1.25

    def test_not_due_stays_quiet(self):
        n = _npc(nxt=1100.0)
        self._sweep([n])
        n.llm_broadcast.assert_not_called()

    def test_unflagged_and_brainless_skipped(self):
        a = _npc(flag=False, nxt=900.0)
        b = _npc(llm=False, nxt=900.0)
        self._sweep([a, b])
        a.llm_broadcast.assert_not_called()
        b.llm_broadcast.assert_not_called()

    def test_one_broken_station_never_stalls_the_sweep(self):
        bad = _npc(nxt=900.0)
        bad.llm_broadcast.side_effect = RuntimeError("boom")
        good = _npc(nxt=900.0)
        self._sweep([bad, good])
        good.llm_broadcast.assert_called_once()


class TestBroadcastFraming(TestCase):
    def test_station_clock_turn(self):
        from world.llm.prompt import build_messages
        msgs = build_messages({"persona_seed": {"archetype": "dj",
                                                "name": "the Rook"}},
                              "the station clock", "It is night.",
                              "broadcast", None, None)
        turn = msgs[-1]["content"]
        self.assertIn("STATION CLOCK", turn)
        self.assertIn("Cut a short on-air segment", turn)
        self.assertIn("Never invent callers", turn)
