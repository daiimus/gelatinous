"""Grenade fuses survive reloads (#505).

The per-second delay chains die with the process; the ticker starters
persist ``db.detonation_deadline`` and the at_server_start sweep
re-arms live fuses / cooks off overdue ones. Duds and defuses drop
the deadline so a reload never re-detonates a spent grenade.
"""

import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import commands.explosion_utils as xu


def _grenade(pin_pulled=True, deadline=None):
    g = MagicMock()
    g.db = SimpleNamespace(pin_pulled=pin_pulled,
                           detonation_deadline=deadline)
    g.ndb = SimpleNamespace()
    return g


class TestFuseSweep(TestCase):
    def _sweep_with(self, grenades):
        mock_qs = MagicMock()
        mock_qs.distinct.return_value = grenades
        with patch("evennia.objects.models.ObjectDB") as db, \
                patch.object(xu, "start_standalone_grenade_ticker") as tick, \
                patch.object(xu.utils, "delay") as delay:
            db.objects.filter.return_value = mock_qs
            result = xu.sweep_armed_grenades()
        return result, tick, delay

    def test_live_fuse_rearms_at_true_remaining(self):
        g = _grenade(deadline=time.time() + 8)
        (rearmed, detonated), tick, delay = self._sweep_with([g])
        self.assertEqual((rearmed, detonated), (1, 0))
        tick.assert_called_once_with(g)
        self.assertIn(g.ndb.countdown_remaining, (7, 8))
        delay.assert_not_called()

    def test_overdue_fuse_cooks_off_after_start(self):
        g = _grenade(deadline=time.time() - 30)
        (rearmed, detonated), tick, delay = self._sweep_with([g])
        self.assertEqual((rearmed, detonated), (0, 1))
        tick.assert_not_called()
        delay.assert_called_once_with(2, xu.explode_standalone_grenade, g)

    def test_defused_before_reload_is_left_alone(self):
        g = _grenade(pin_pulled=False, deadline=time.time() + 5)
        (rearmed, detonated), tick, delay = self._sweep_with([g])
        self.assertEqual((rearmed, detonated), (0, 0))
        g.attributes.remove.assert_called_once_with("detonation_deadline")
        tick.assert_not_called()

    def test_one_bad_grenade_never_stops_the_sweep(self):
        cursed = MagicMock()
        cursed.db = property(lambda s: (_ for _ in ()).throw(RuntimeError))
        good = _grenade(deadline=time.time() + 5)
        (rearmed, _), tick, _ = self._sweep_with([cursed, good])
        self.assertEqual(rearmed, 1)


class TestDeadlineStamp(TestCase):
    def test_standalone_ticker_stamps_the_deadline(self):
        g = _grenade()
        g.ndb.countdown_remaining = 6
        before = time.time()
        with patch.object(xu.utils, "delay"), \
                patch.object(xu, "get_splattercast",
                             return_value=MagicMock()):
            xu.start_standalone_grenade_ticker(g)
        self.assertAlmostEqual(g.db.detonation_deadline, before + 6,
                               delta=2)

    def test_sticky_ticker_stamps_the_deadline(self):
        g = _grenade()
        g.ndb.countdown_remaining = 4
        before = time.time()
        with patch.object(xu.utils, "delay"), \
                patch.object(xu, "get_splattercast",
                             return_value=MagicMock()):
            xu.start_grenade_ticker(g)
        self.assertAlmostEqual(g.db.detonation_deadline, before + 4,
                               delta=2)
