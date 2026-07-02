"""Tests for the security BOLO + scan-and-match arrival handler
(crime slice 1): the responder is a perceiver, never an oracle."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.director import WorldEvent
from world.director import assignment as amod
from world.director import security as smod
from world.director.assignment import ARRIVAL_HANDLERS, Assignment
from world.director.security import build_bolo, match_bolo, security_arrival


class _Room:
    def __init__(self, name, contents=()):
        self.name = name
        self.contents = list(contents)


class _Char:
    """Hashable character stand-in; ``uid`` fakes its apparent presentation."""

    def __init__(self, name, uid=None, height=None, build=None):
        self.name = name
        self.uid = uid
        self.height = height
        self.build = build
        self.location = None
        self.ndb = SimpleNamespace()
        self.db = SimpleNamespace(role="security")
        self.execute_cmd = MagicMock()

    def is_typeclass(self, path, exact=False):
        return True


def _fake_uid(char):
    return getattr(char, "uid", None)


def _assignment(npc, bolo):
    event = WorldEvent("assault", npc.location,
                       payload={"bolo": bolo} if bolo is not None else {})
    a = Assignment(npc=npc, event=event, post=_Room("post"))
    amod._ACTIVE[npc] = a
    return a


@patch("world.director.security.get_apparent_uid", side_effect=_fake_uid)
class TestBolo(TestCase):
    def test_build_snapshots_uid_and_silhouette(self, _g):
        perp = _Char("perp", uid="abc123", height="tall", build="lean")
        self.assertEqual(build_bolo(perp),
                         {"uid": "abc123", "height": "tall", "build": "lean"})
        self.assertIsNone(build_bolo(None))

    def test_precise_match_is_high(self, _g):
        bolo = {"uid": "abc123", "height": "tall", "build": "lean"}
        self.assertEqual(match_bolo(bolo, _Char("x", uid="abc123")), "high")

    def test_changed_presentation_defeats_precise_match(self, _g):
        # Disguise / re-sleeve => different current uid => at best coarse.
        bolo = {"uid": "abc123", "height": "tall", "build": "lean"}
        disguised = _Char("x", uid="OTHER", height="short", build="heavy")
        self.assertIsNone(match_bolo(bolo, disguised))

    def test_silhouette_match_is_low_mistaken_identity(self, _g):
        # An innocent lookalike with the same height+build fits the report.
        bolo = {"uid": "abc123", "height": "tall", "build": "lean"}
        lookalike = _Char("bystander", uid="INNOCENT",
                          height="tall", build="lean")
        self.assertEqual(match_bolo(bolo, lookalike), "low")

    def test_no_bolo_no_match(self, _g):
        self.assertIsNone(match_bolo(None, _Char("x", uid="abc123")))
        self.assertIsNone(match_bolo({}, _Char("x", uid="abc123")))


@patch("world.director.security.get_short_sdesc", return_value="a tall lean drifter")
@patch("world.director.security.get_apparent_uid", side_effect=_fake_uid)
@patch("world.director.security.can_see", return_value=True)
@patch("world.director.security.delay")
class TestSecurityArrival(TestCase):
    def setUp(self):
        amod._ACTIVE.clear()

    def tearDown(self):
        amod._ACTIVE.clear()

    def _scene(self, *others):
        bot = _Char("bot", uid="BOT")
        room = _Room("scene", contents=[bot, *others])
        bot.location = room
        for o in others:
            o.location = room
        return bot

    def test_registered_for_security_role(self, *_m):
        self.assertIs(ARRIVAL_HANDLERS.get("security"), security_arrival)

    def test_high_confidence_challenges_and_watches(self, mock_delay, *_m):
        perp = _Char("perp", uid="PERP", height="tall", build="lean")
        bot = self._scene(perp)
        a = _assignment(bot, {"uid": "PERP", "height": "tall", "build": "lean"})
        security_arrival(bot, a)
        said = " ".join(str(c) for c in bot.execute_cmd.call_args_list)
        self.assertIn("Hold your position", said)
        self.assertEqual(a.payload["watch_rounds"], smod.WATCH_ROUNDS)
        self.assertIs(mock_delay.call_args.args[1], smod._watch_tick)

    def test_low_confidence_questions_the_lookalike(self, mock_delay, *_m):
        lookalike = _Char("bystander", uid="INNOCENT",
                          height="tall", build="lean")
        bot = self._scene(lookalike)
        a = _assignment(bot, {"uid": "PERP", "height": "tall", "build": "lean"})
        security_arrival(bot, a)
        said = " ".join(str(c) for c in bot.execute_cmd.call_args_list)
        self.assertIn("fit a description", said)
        self.assertIs(mock_delay.call_args.args[1], amod.resolve)

    def test_no_match_logs_and_resolves(self, mock_delay, *_m):
        bot = self._scene(_Char("passerby", uid="X", height="short",
                                build="heavy"))
        a = _assignment(bot, {"uid": "PERP", "height": "tall", "build": "lean"})
        security_arrival(bot, a)
        said = " ".join(str(c) for c in bot.execute_cmd.call_args_list)
        self.assertIn("nothing that matches", said)
        self.assertIs(mock_delay.call_args.args[1], amod.resolve)

    def test_blind_bot_scans_nothing(self, mock_delay, _cs, *_m):
        with patch("world.director.security.can_see", return_value=False):
            perp = _Char("perp", uid="PERP")
            bot = self._scene(perp)
            a = _assignment(bot, {"uid": "PERP", "height": None, "build": None})
            security_arrival(bot, a)
        said = " ".join(str(c) for c in bot.execute_cmd.call_args_list)
        self.assertIn("nothing that matches", said)  # perceived no one

    def test_watch_gives_up_when_suspect_leaves(self, mock_delay, *_m):
        perp = _Char("perp", uid="PERP")
        bot = self._scene(perp)
        a = _assignment(bot, {"uid": "PERP", "height": None, "build": None})
        a.payload["watch_rounds"] = 2
        bot.location.contents.remove(perp)  # suspect slipped away
        with patch.object(amod, "resolve") as mock_resolve:
            with patch("world.director.security.resolve", mock_resolve):
                smod._watch_tick(bot)
        mock_resolve.assert_called_once_with(bot)

    def test_watch_holds_then_stands_down_after_rounds(self, mock_delay, *_m):
        perp = _Char("perp", uid="PERP")
        bot = self._scene(perp)
        a = _assignment(bot, {"uid": "PERP", "height": None, "build": None})
        a.payload["watch_rounds"] = 2
        smod._watch_tick(bot)                      # round 1: still watching
        self.assertIs(mock_delay.call_args.args[1], smod._watch_tick)
        with patch("world.director.security.resolve") as mock_resolve:
            smod._watch_tick(bot)                  # round 2: gives up
            mock_resolve.assert_called_once_with(bot)
