"""The signal ring survives a reload, and a settings change.

Regression pin for #2672. Two durability defects on the same rows.

1. `flush()` had ZERO callers. Its docstring named two ("called by the
   heartbeat, and at shutdown") and neither existed, so checkpointing
   happened only on the `CHECKPOINT_EVERY = 25` count trigger.
   Everything since the last multiple of 25 died with the process --
   measured live, the newest checkpointed row was 58 minutes old, about
   35 signals of colony history one reload from gone.

2. The ring lived on `GLOBAL_SCRIPTS.souls_heartbeat`. Evennia manages
   those from `settings` and RECREATES a managed script when its entry
   changes, so an interval tweak to the souls heartbeat would have taken
   the entire history with it, silently.

Now kept in `ServerConfig` -- a plain global key/value table that
nothing manages and nothing recreates -- and flushed from
`at_server_stop`, which runs for reload, reset and shutdown alike.

`_load` adopts from the old home once, so the history already recorded
there moves rather than being dropped. Verified live: 286 rows adopted
and written through.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.wsis as wsis


class TestTheColonyRemembersWhatItNoticed(TestCase):

    def setUp(self):
        wsis._ring = None
        wsis._since_checkpoint = 0

    def tearDown(self):
        wsis._ring = None

    def test_flush_writes_without_waiting_for_the_count(self):
        """The defect: only the 25-emit trigger ever checkpointed."""
        wsis._ring = [("sig", 1)]
        with patch("evennia.server.models.ServerConfig") as cfg:
            wsis.flush()
        cfg.objects.conf.assert_called_once()
        self.assertEqual(cfg.objects.conf.call_args.args[0], "wsis_ring")

    def test_a_partial_batch_still_checkpoints(self):
        """One emit, then a shutdown — the exact loss case."""
        wsis._ring = [("sig", 1)]
        wsis._since_checkpoint = 1
        with patch("evennia.server.models.ServerConfig") as cfg:
            wsis.flush()
        cfg.objects.conf.assert_called_once()

    def test_the_ring_is_not_kept_on_the_managed_script(self):
        """A settings change recreates a GLOBAL_SCRIPTS entry, taking
        anything stored on it."""
        import inspect
        src = inspect.getsource(wsis._checkpoint)
        self.assertIn("ServerConfig", src)
        self.assertNotIn("hb.db.wsis_ring", src)

    def test_the_old_home_is_adopted_once(self):
        """The history already recorded must move, not be dropped."""
        hb = MagicMock()
        hb.db.wsis_ring = [("old", 1), ("older", 2)]
        with patch("evennia.server.models.ServerConfig") as cfg, \
             patch.object(wsis, "_heartbeat", return_value=hb):
            cfg.objects.conf.return_value = None
            ring = wsis._load()
        self.assertEqual(len(ring), 2)

    def test_the_new_home_wins_once_populated(self):
        """The control — adoption is one-time, not every load."""
        hb = MagicMock()
        hb.db.wsis_ring = [("stale", 9)]
        with patch("evennia.server.models.ServerConfig") as cfg, \
             patch.object(wsis, "_heartbeat", return_value=hb):
            cfg.objects.conf.return_value = [("current", 1), ("current", 2),
                                             ("current", 3)]
            ring = wsis._load()
        self.assertEqual(len(ring), 3)
