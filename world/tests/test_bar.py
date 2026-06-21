"""
Tests for the unified speech backbone payload and the bartender's reaction.

The backbone (world.speech) attaches a structured ``speech``/``addressed``
payload to every *hearing* listener's msg, regardless of which verb (say / to /
pose) carried the words. The bartender reacts off that single shape. These
tests pin the payload routing and the bartender's branch selection.
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import BaseEvenniaTest

import world.speech as speech
import typeclasses.bar as barmod


class _Obs:
    """A minimal listener that records msg kwargs."""

    def __init__(self, name):
        self.name = name
        self.calls = []

    def msg(self, *args, **kwargs):
        self.calls.append(kwargs)

    def get_display_name(self, looker=None, **kw):
        return self.name

    last = property(lambda self: self.calls[-1] if self.calls else {})


def _room(contents):
    r = MagicMock()
    r.contents = contents
    return r


class TestDrinkNaming(BaseEvenniaTest):
    """Drink keys carry no leading article (display sites add it)."""

    def test_make_drink_strips_leading_article(self):
        from world.bar import make_drink

        d = make_drink(
            name="a mug of rotgut", desc="x", effects={}, location=self.room1
        )
        self.assertEqual(d.key, "mug of rotgut")

    def test_menu_names_are_article_free(self):
        from world.bar import HUB_AND_HOWL_MENU

        for recipe in HUB_AND_HOWL_MENU:
            self.assertFalse(
                recipe["name"].lower().startswith(("a ", "an ", "the ")),
                f"menu name {recipe['name']!r} still carries an article",
            )

    def test_aliases_still_targetable(self):
        from world.bar import make_drink

        d = make_drink(
            name="a mug of rotgut", desc="x", effects={}, location=self.room1
        )
        aliases = d.aliases.all()
        self.assertIn("rotgut", aliases)
        self.assertIn("mug", aliases)


class TestSpeechPayloadRouting(BaseEvenniaTest):
    """broadcast_speech attaches speech/addressed only to hearing listeners."""

    def setUp(self):
        super().setUp()
        self.speaker = _Obs("a lean man")
        self.target = _Obs("a tall woman")
        self.bystander = _Obs("a short man")
        self.room = _room([self.speaker, self.target, self.bystander])

    def _patch_perception(self, hear=True, see=True):
        # Backbone reads can_hear/can_see + attribution; stub them flat.
        return [
            patch.object(speech, "can_hear", lambda o: hear),
            patch.object(speech, "can_see", lambda o: see),
            patch.object(speech, "resolve_speaker_attribution",
                         lambda s, o: "a lean man"),
            patch.object(speech, "visible_voice_flavor", lambda s: None),
        ]

    def _run(self, **kw):
        from contextlib import ExitStack
        with ExitStack() as stack:
            for p in self._patch_perception(**kw.pop("perc", {})):
                stack.enter_context(p)
            speech.broadcast_speech(self.speaker, "hi", self.room, **kw)

    def test_say_not_addressed(self):
        self._run()
        self.assertEqual(self.target.last.get("speech"), "hi")
        self.assertFalse(self.target.last.get("addressed"))
        self.assertFalse(self.bystander.last.get("addressed"))

    def test_to_marks_only_target_addressed(self):
        self._run(target=self.target)
        self.assertTrue(self.target.last.get("addressed"))
        self.assertEqual(self.bystander.last.get("speech"), "hi")
        self.assertFalse(self.bystander.last.get("addressed"))

    def test_deaf_listener_gets_no_words(self):
        self._run(perc={"hear": False, "see": True})
        # Deaf-but-sighted still receives a line, but no speech payload.
        self.assertIsNone(self.target.last.get("speech"))
        self.assertNotIn("addressed", self.target.last)

    def test_no_channel_skipped(self):
        self._run(perc={"hear": False, "see": False})
        self.assertEqual(self.target.calls, [])


class TestPosePayload(BaseEvenniaTest):
    """A pose's embedded quote rides the same rails; refs count as addressed."""

    def test_pose_speech_payload_addressed(self):
        from world.emote import SpeechToken, CharRefToken, render_dot_pose

        actor = _Obs("a lean man")
        target = _Obs("a tall woman")
        room = _room([actor, target])
        tokens = [CharRefToken(target, "woman"),
                  SpeechToken("Let me get some rotgut.", actor)]

        with patch.object(speech, "can_hear", lambda o: True):
            with patch("world.emote.render_for_observer", lambda t, a, o: "rendered"):
                render_dot_pose(tokens, actor, room)

        self.assertEqual(target.last.get("speech"), "Let me get some rotgut.")
        self.assertTrue(target.last.get("addressed"))


class TestBarStaffAccess(BaseEvenniaTest):
    """Staff (Builder+) can work/manage any bar; ownership still gates others."""

    def _bar(self, owner=None, staff=None):
        b = MagicMock()
        b.db.owner = owner
        b.db.staff = staff or []
        b._is_staff = barmod.BarCounter._is_staff  # real staticmethod
        return b

    def _char(self, is_staff=False):
        c = MagicMock()
        c.locks.check_lockstring = lambda obj, lockstr: is_staff
        return c

    def _is_bartender(self, bar, char):
        return barmod.BarCounter.is_bartender(bar, char)

    def test_staff_can_work_owned_bar(self):
        bar = self._bar(owner=object())  # owned by someone else
        self.assertTrue(self._is_bartender(bar, self._char(is_staff=True)))

    def test_non_staff_blocked_on_owned_bar(self):
        bar = self._bar(owner=object())
        self.assertFalse(self._is_bartender(bar, self._char(is_staff=False)))

    def test_owner_allowed(self):
        owner = self._char(is_staff=False)
        bar = self._bar(owner=owner)
        self.assertTrue(self._is_bartender(bar, owner))

    def test_unowned_allows_anyone(self):
        bar = self._bar()
        self.assertTrue(self._is_bartender(bar, self._char(is_staff=False)))

    def test_staff_check_failure_is_safe(self):
        bar = self._bar(owner=object())
        char = MagicMock()
        char.locks.check_lockstring.side_effect = RuntimeError("boom")
        # A lock-check hiccup must not crash; it just denies non-owners.
        self.assertFalse(self._is_bartender(bar, char))


class TestBartenderReaction(BaseEvenniaTest):
    """at_msg_receive routes the unified payload to ack / order / nothing."""

    def _bartender(self):
        b = MagicMock()
        b._is_gratitude = barmod.Bartender._is_gratitude  # real staticmethod
        b._acknowledge = MagicMock()
        return b

    def _call(self, b, speaker, **payload):
        return barmod.Bartender.at_msg_receive(
            b, text=None, from_obj=speaker, **payload
        )

    def test_addressed_order_fulfils(self):
        b = self._bartender()
        speaker = object()
        with patch.object(barmod, "delay") as mock_delay:
            self._call(b, speaker, speech="a rotgut please", addressed=True)
        mock_delay.assert_called_once()
        b._acknowledge.assert_not_called()

    def test_unaddressed_speech_does_nothing(self):
        b = self._bartender()
        with patch.object(barmod, "delay") as mock_delay:
            self._call(b, object(), speech="a rotgut please", addressed=False)
        mock_delay.assert_not_called()
        b._acknowledge.assert_not_called()

    def test_gratitude_acks_even_if_addressed(self):
        b = self._bartender()
        with patch.object(barmod, "delay") as mock_delay:
            self._call(b, object(), speech="much obliged", addressed=True)
        mock_delay.assert_not_called()
        b._acknowledge.assert_called_once()

    def test_no_speech_payload_ignored(self):
        b = self._bartender()
        with patch.object(barmod, "delay") as mock_delay:
            self._call(b, object(), speech=None, addressed=True)
        mock_delay.assert_not_called()
        b._acknowledge.assert_not_called()

    def test_own_speech_ignored(self):
        b = self._bartender()
        with patch.object(barmod, "delay") as mock_delay:
            # from_obj is the bartender itself
            self._call(b, b, speech="thanks", addressed=True)
        mock_delay.assert_not_called()
        b._acknowledge.assert_not_called()
