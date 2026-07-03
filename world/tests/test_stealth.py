"""Stealth engine (world/stealth.py) — contest, awareness store, tiers.

MagicMock stand-ins; randint/time patched for determinism. The identity key
is patched (uid derivation has its own suite).
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.stealth as stealth
from world.stealth import (
    ALERT, SUSPICIOUS, UNAWARE,
    active_search, attempt_hide, break_stealth, get_awareness,
    is_hidden_from, passive_check, set_awareness,
)


def _char(motorics=1, resonance=1, hidden=False, room=None):
    c = MagicMock()
    c.motorics = motorics
    c.resonance = resonance
    c.db.hidden = hidden
    c.db.awareness = None
    c.location = room
    return c


def _room(*contents):
    room = MagicMock()
    room.contents = list(contents)
    return room


def _uid_for(chars):
    """Patch uid derivation to a stable per-object key."""
    return patch("world.identity.get_apparent_uid",
                 side_effect=lambda t: f"uid-{id(t)}")


class TestAwarenessStore(TestCase):
    def test_default_unaware(self):
        with _uid_for(None):
            self.assertEqual(get_awareness(_char(), _char()), UNAWARE)

    def test_set_and_get(self):
        obs, target = _char(), _char()
        with _uid_for(None):
            set_awareness(obs, target, ALERT)
            self.assertEqual(get_awareness(obs, target), ALERT)

    def test_decay_over_time(self):
        obs, target = _char(), _char()
        with _uid_for(None):
            set_awareness(obs, target, ALERT)
            with patch("world.stealth.time") as t:
                t.time.return_value = __import__("time").time() \
                    + stealth.AWARENESS_DECAY * 2 + 1
                self.assertEqual(get_awareness(obs, target), ALERT - 2)

    def test_unaware_records_pruned(self):
        obs, target = _char(), _char()
        with _uid_for(None):
            set_awareness(obs, target, ALERT)
            set_awareness(obs, target, UNAWARE)
        self.assertEqual(obs.db.awareness, {})


class TestHideContest(TestCase):
    def test_sharp_watcher_keeps_track_dull_loses(self):
        room = _room()
        hider = _char(motorics=5, room=room)
        sharp = _char(resonance=20)
        dull = _char(resonance=0)
        room.contents = [hider, sharp, dull]
        with _uid_for(None), \
                patch("world.stealth.randint", return_value=10), \
                patch("world.perception.can_see", return_value=True):
            kept = attempt_hide(hider)
        self.assertTrue(hider.db.hidden)
        self.assertIn(sharp, kept)
        self.assertNotIn(dull, kept)
        with _uid_for(None):
            self.assertEqual(get_awareness(sharp, hider), ALERT)
            self.assertEqual(get_awareness(dull, hider), UNAWARE)

    def test_blind_watcher_never_contests(self):
        room = _room()
        hider = _char(motorics=0, room=room)
        blind = _char(resonance=20)
        room.contents = [hider, blind]
        with _uid_for(None), \
                patch("world.stealth.randint", return_value=10), \
                patch("world.perception.can_see", return_value=False):
            kept = attempt_hide(hider)
        self.assertEqual(kept, [])


class TestPassiveTier(TestCase):
    def test_clear_win_spots_outright(self):
        hider, obs = _char(motorics=0, hidden=True), _char(resonance=10)
        with _uid_for(None), \
                patch("world.stealth.randint", return_value=10):
            self.assertEqual(passive_check(obs, hider), ALERT)

    def test_near_miss_reads_suspicious(self):
        # equal totals: margin 0 -> hider holds, but it's within the
        # suspicion band
        hider, obs = _char(motorics=1, hidden=True), _char(resonance=1)
        with _uid_for(None), \
                patch("world.stealth.randint", return_value=10):
            self.assertEqual(passive_check(obs, hider), SUSPICIOUS)

    def test_clear_hold_stays_unaware(self):
        hider, obs = _char(motorics=10, hidden=True), _char(resonance=0)
        with _uid_for(None), \
                patch("world.stealth.randint", return_value=10):
            self.assertEqual(passive_check(obs, hider), UNAWARE)

    def test_rate_limited_no_reroll_spam(self):
        # first look: clear hold. Second look (better luck) inside the
        # cooldown must NOT re-roll — look-spam is not a search.
        hider, obs = _char(motorics=10, hidden=True), _char(resonance=0)
        with _uid_for(None):
            with patch("world.stealth.randint", return_value=10):
                self.assertEqual(passive_check(obs, hider), UNAWARE)
            with patch("world.stealth.randint",
                       side_effect=[1, 20]) as rand:
                self.assertEqual(passive_check(obs, hider), UNAWARE)
                rand.assert_not_called()

    def test_weaker_than_active_search(self):
        # a margin the passive glance loses, the active search wins:
        # totals equal (margin 0) passively, but the search bonus flips it
        hider = _char(motorics=1, hidden=True)
        room = _room(hider)
        searcher = _char(resonance=1, room=room)
        room.contents.append(searcher)
        hider.get_sdesc = lambda: "a shape"
        with _uid_for(None), \
                patch("world.stealth.randint", return_value=10):
            self.assertEqual(passive_check(searcher, hider), SUSPICIOUS)
            found, _objs = active_search(searcher)
        self.assertIn(hider, found)


class TestSearchAndBreak(TestCase):
    def test_search_reveals_stashed_object_for_everyone(self):
        obj = MagicMock(spec=["db", "get_display_name"])
        obj.db.hidden = True
        obj.db.stash_roll = 5
        room = _room(obj)
        searcher = _char(resonance=1, room=room)
        room.contents.append(searcher)
        with patch("world.stealth.randint", return_value=10):
            _chars, objs = active_search(searcher)
        self.assertIn(obj, objs)
        self.assertFalse(obj.db.hidden)

    def test_break_stealth_alerts_everyone_present(self):
        room = _room()
        hider = _char(hidden=True, room=room)
        a, b = _char(), _char()
        a.get_sdesc = b.get_sdesc = lambda: "x"
        room.contents = [hider, a, b]
        with _uid_for(None):
            self.assertTrue(break_stealth(hider, quiet=True))
            self.assertFalse(hider.db.hidden)
            self.assertEqual(get_awareness(a, hider), ALERT)
            self.assertEqual(get_awareness(b, hider), ALERT)

    def test_display_gate(self):
        hider, looker = _char(hidden=True), _char()
        with _uid_for(None):
            self.assertTrue(is_hidden_from(hider, looker))
            set_awareness(looker, hider, ALERT)
            self.assertFalse(is_hidden_from(hider, looker))
        hider.db.hidden = False
        self.assertFalse(is_hidden_from(hider, looker))


class TestHideCommand(TestCase):
    def test_hide_self_sets_state_and_notifies_keepers(self):
        from commands.CmdStealth import CmdHide
        room = _room()
        caller = _char(motorics=0, room=room)
        watcher = _char(resonance=20)
        watcher.get_display_name = lambda looker=None, **k: "you-know-who"
        caller.get_display_name = lambda looker=None, **k: "a lean man"
        room.contents = [caller, watcher]
        cmd = CmdHide()
        cmd.caller = caller
        cmd.args = ""
        with _uid_for(None), \
                patch("world.stealth.randint", return_value=10), \
                patch("world.perception.can_see", return_value=True):
            cmd.func()
        self.assertTrue(caller.db.hidden)
        self.assertIn("keep track", watcher.msg.call_args.args[0])

    def test_stash_object(self):
        from commands.CmdStealth import CmdHide
        room = _room()
        caller = _char(motorics=3, room=room)
        item = MagicMock()
        item.get_display_name = lambda looker=None, **k: "a shiv"
        caller.search.return_value = item
        cmd = CmdHide()
        cmd.caller = caller
        cmd.args = "shiv"
        cmd.func()
        item.move_to.assert_called_once_with(room, quiet=True)
        self.assertTrue(item.db.hidden)
        self.assertTrue(item.db.stash_roll)


class TestStateTransitionsBreakStealth(TestCase):
    """KO/death own override_place — a hidden character who drops must stop
    being hidden (no "lurking" corpse, no body fading to invisible as
    trackers' awareness decays). Pins the source-level calls."""

    def test_unconscious_and_death_paths_break_stealth(self):
        import inspect
        import typeclasses.characters as chars
        source = inspect.getsource(chars)
        anchors = [
            'self.override_place = "unconscious and motionless."',
            'self.override_place = "lying motionless and deceased."',
        ]
        for anchor in anchors:
            idx = 0
            while True:
                idx = source.find(anchor, idx)
                if idx == -1:
                    break
                window = source[idx:idx + 400]
                self.assertIn("break_stealth", window,
                              f"override_place write without break_stealth "
                              f"nearby: {anchor}")
                idx += len(anchor)


class TestEmergenceBeat(TestCase):
    """A voice must never materialize mid-sentence: a non-quiet break gives
    formerly-unaware observers the emergence line; trackers get nothing."""

    def test_unaware_observers_get_emergence_line(self):
        room = _room()
        hider = _char(hidden=True, room=room)
        hider.get_display_name = lambda looker=None, **k: "a lean man"
        unaware, tracker = _char(), _char()
        unaware.get_sdesc = tracker.get_sdesc = lambda: "x"
        room.contents = [hider, unaware, tracker]
        with _uid_for(None):
            set_awareness(tracker, hider, ALERT)
            break_stealth(hider)
        self.assertIn("emerges from concealment",
                      unaware.msg.call_args.args[0])
        tracker.msg.assert_not_called()

    def test_quiet_break_has_no_emergence(self):
        room = _room()
        hider = _char(hidden=True, room=room)
        unaware = _char()
        unaware.get_sdesc = lambda: "x"
        room.contents = [hider, unaware]
        with _uid_for(None):
            break_stealth(hider, quiet=True)
        unaware.msg.assert_not_called()


class TestWhisperStealth(TestCase):
    """Whisper is the creepy channel: it never breaks stealth, arrives
    unattributed from an unseen speaker, and leaves the target Suspicious."""

    def _cmd(self, caller, args):
        from commands.CmdCommunication import CmdWhisper
        cmd = CmdWhisper()
        cmd.caller = caller
        cmd.args = args
        cmd.parse()
        return cmd

    def _pair(self, hidden=False):
        room = _room()
        caller = _char(hidden=hidden, room=room)
        target = _char(room=room)
        target.get_display_name = lambda looker=None, **k: "a lean man"
        caller.get_display_name = lambda looker=None, **k: "a shadow"
        caller.search.return_value = target
        room.contents = [caller, target]
        return caller, target

    def test_new_syntax_parses(self):
        caller, target = self._pair()
        cmd = self._cmd(caller, '"Wakka." to lean man')
        self.assertEqual(cmd.speech, "Wakka.")
        self.assertEqual(cmd.target_str, "lean man")

    def test_legacy_syntax_still_parses(self):
        caller, target = self._pair()
        cmd = self._cmd(caller, "lean man = Wakka.")
        self.assertEqual(cmd.speech, "Wakka.")
        self.assertEqual(cmd.target_str, "lean man")

    def test_hidden_whisper_stays_hidden_and_unattributed(self):
        caller, target = self._pair(hidden=True)
        cmd = self._cmd(caller, '"Wakka." to lean man')
        with _uid_for(None), \
                patch("commands.CmdCommunication.can_hear",
                      return_value=True):
            cmd.func()
        self.assertTrue(caller.db.hidden)               # never breaks
        text = target.msg.call_args.kwargs.get("text")
        self.assertIn("Someone unseen whispers", text)
        self.assertNotIn("shadow", text)                # no attribution
        with _uid_for(None):
            self.assertEqual(get_awareness(target, caller), SUSPICIOUS)

    def test_visible_whisper_attributed(self):
        caller, target = self._pair(hidden=False)
        cmd = self._cmd(caller, '"Wakka." to lean man')
        with _uid_for(None), \
                patch("commands.CmdCommunication.can_hear",
                      return_value=True):
            cmd.func()
        text = target.msg.call_args.kwargs.get("text")
        self.assertIn("A shadow whispers to you", text)

    def test_bystander_who_cannot_see_whisperer_sees_nothing(self):
        caller, target = self._pair(hidden=True)
        bystander = _char()
        bystander.get_sdesc = lambda: "x"
        caller.location.contents.append(bystander)
        cmd = self._cmd(caller, '"Wakka." to lean man')
        with _uid_for(None), \
                patch("commands.CmdCommunication.can_hear",
                      return_value=True):
            cmd.func()
        bystander.msg.assert_not_called()
