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
    """Whisper is the creepy channel ON THE SAY PARENT: never breaks
    stealth, rides the shared speech rails (attribution via the
    sight/voice/stealth chain, payload for NPC brains), leaves an
    unseen-whispered target Suspicious."""

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

    def _run(self, caller, rendered='Someone whispers to you, "Wakka."'):
        cmd = self._cmd(caller, '"Wakka." to lean man')
        with _uid_for(None), \
                patch("world.speech.render_speech_line",
                      return_value=rendered) as render, \
                patch("world.speech.speech_payload",
                      return_value={"speech": "Wakka.",
                                    "addressed": True}), \
                patch("world.speech.visible_voice_flavor",
                      return_value=None), \
                patch("world.perception.can_see", return_value=True):
            cmd.func()
        return render

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

    def test_hidden_whisper_never_breaks_stealth(self):
        caller, target = self._pair(hidden=True)
        self._run(caller)
        self.assertTrue(caller.db.hidden)
        with _uid_for(None):
            self.assertEqual(get_awareness(target, caller), SUSPICIOUS)

    def test_rides_the_say_parent(self):
        caller, target = self._pair()
        render = self._run(caller)
        render.assert_called_once()
        self.assertEqual(render.call_args.kwargs.get("verb"), "whispers")
        # the structured payload reaches the target's msg (NPC brains hear)
        self.assertEqual(target.msg.call_args.kwargs.get("speech"), "Wakka.")
        self.assertTrue(target.msg.call_args.kwargs.get("addressed"))

    def test_visible_whisper_leaves_no_awareness_mark(self):
        caller, target = self._pair(hidden=False)
        self._run(caller, rendered='A shadow whispers to you, "Wakka."')
        with _uid_for(None):
            self.assertEqual(get_awareness(target, caller), UNAWARE)

    def test_bystander_who_cannot_see_whisperer_sees_nothing(self):
        caller, target = self._pair(hidden=True)
        bystander = _char()
        bystander.get_sdesc = lambda: "x"
        caller.location.contents.append(bystander)
        self._run(caller)
        bystander.msg.assert_not_called()


class TestStealthAttribution(TestCase):
    """Concealment gates the VISUAL attribution channel: a hidden speaker
    attributes by voice — a known voice names them, a stranger's reads as
    'someone'."""

    def test_hidden_speaker_attributes_by_voice(self):
        from world.voice import resolve_speaker_attribution
        speaker, observer = _char(hidden=True), _char()
        with patch("world.voice.can_see", return_value=True), \
                patch("world.voice.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern",
                      return_value="Roony"), \
                patch("world.stealth.is_hidden_from", return_value=True):
            self.assertEqual(
                resolve_speaker_attribution(speaker, observer), "Roony")

    def test_hidden_speaker_unknown_voice_is_someone(self):
        from world.voice import resolve_speaker_attribution
        speaker, observer = _char(hidden=True), _char()
        with patch("world.voice.can_see", return_value=True), \
                patch("world.voice.can_hear", return_value=True), \
                patch("world.voice.attempt_voice_discern",
                      return_value=None), \
                patch("world.stealth.is_hidden_from", return_value=True):
            self.assertEqual(
                resolve_speaker_attribution(speaker, observer), "someone")

    def test_visible_speaker_attributes_by_sight(self):
        from world.voice import resolve_speaker_attribution
        speaker, observer = _char(), _char()
        speaker.get_display_name = lambda looker=None, **k: "a shadow"
        with patch("world.voice.can_see", return_value=True), \
                patch("world.stealth.is_hidden_from", return_value=False):
            self.assertEqual(
                resolve_speaker_attribution(speaker, observer), "a shadow")


class TestLeakSweep(TestCase):
    """Leak-completeness (spec §7): no enumeration path shows a hidden
    target to an unaware observer. Each test drives one real path."""

    def _hidden_char(self):
        c = _char(hidden=True)
        c.get_sdesc = lambda: "a shape"
        return c

    def test_choke_basics(self):
        from world.perception import can_perceive, filter_present
        looker = _char()
        hidden, plain = self._hidden_char(), _char()
        with _uid_for(None):
            self.assertFalse(can_perceive(looker, hidden))
            self.assertTrue(can_perceive(looker, plain))
            self.assertEqual(filter_present(looker, [hidden, plain]),
                             [plain])
            set_awareness(looker, hidden, ALERT)
            self.assertTrue(can_perceive(looker, hidden))

    def test_adjacent_sightings_do_not_count_hidden(self):
        from typeclasses.rooms import Room
        looker = _char()
        hidden = self._hidden_char()
        adjacent = _room(hidden)
        exit_obj = MagicMock()
        exit_obj.destination = adjacent
        exit_obj.key = "north"
        room = MagicMock()
        room.exits = [exit_obj]
        sightings = Room.get_adjacent_character_sightings.__get__(room)
        with _uid_for(None):
            self.assertEqual(sightings(looker), "")
            set_awareness(looker, hidden, ALERT)
            self.assertIn("lone figure", sightings(looker))

    def test_identity_targeting_refuses_hidden(self):
        from commands._identity_targeting import resolve_character_target
        caller = _char()
        caller.check_permstring.return_value = False
        hidden = self._hidden_char()
        with _uid_for(None), \
                patch("commands._identity_targeting."
                      "identity_match_characters",
                      side_effect=lambda c, q, cands: list(cands)):
            self.assertIsNone(
                resolve_character_target(caller, "shape",
                                         candidates=[hidden]))
            set_awareness(caller, hidden, ALERT)
            self.assertIs(
                resolve_character_target(caller, "shape",
                                         candidates=[hidden]),
                hidden)

    def test_emote_charref_candidates_exclude_hidden(self):
        from world.emote import build_char_candidates
        actor = _char()
        hidden = self._hidden_char()
        with _uid_for(None):
            names = [c for _n, c, _rc in
                     build_char_candidates(actor, [actor, hidden])]
        self.assertNotIn(hidden, names)

    def test_llm_present_roster_excludes_hidden(self):
        from typeclasses.llm_npc import LLMNpcMixin
        npc = _char()
        hidden = self._hidden_char()
        room = _room(npc, hidden)
        npc.location = room
        npc._address_handle = lambda t: "a shape"
        present = LLMNpcMixin._present_others.__get__(npc)
        with _uid_for(None):
            self.assertEqual(present(), [])
            set_awareness(npc, hidden, ALERT)
            self.assertEqual(present(), ["a shape"])


class TestCrowdBonus(TestCase):
    """Blending in is real: crowd density is a hider bonus at every tier."""

    def test_dense_crowd_tips_the_contest(self):
        from world.stealth import contest
        hider, seeker = _char(motorics=1), _char(resonance=2)
        room = MagicMock()
        hider.location = room
        with patch("world.stealth.randint", return_value=10), \
                patch("world.crowd.CrowdSystem.calculate_crowd_level",
                      return_value=3):
            # 10+1+3 vs 10+2: hider holds in the throng
            self.assertLessEqual(contest(hider, seeker), 0)
        with patch("world.stealth.randint", return_value=10), \
                patch("world.crowd.CrowdSystem.calculate_crowd_level",
                      return_value=0):
            # empty street: the same match-up loses
            self.assertGreater(contest(hider, seeker), 0)

    def test_bonus_clamped(self):
        from world.stealth import crowd_hider_bonus
        with patch("world.crowd.CrowdSystem.calculate_crowd_level",
                   return_value=9):
            self.assertEqual(crowd_hider_bonus(MagicMock()), 3)
        with patch("world.crowd.CrowdSystem.calculate_crowd_level",
                   side_effect=Exception("no crowd")):
            self.assertEqual(crowd_hider_bonus(MagicMock()), 0)
