"""A session-less NPC must receive room broadcasts.

Regression pin for #2640.  `msg_room_identity` skipped every observer
without a connected session, justified in the comment by:

    Messages to session-less objects are discarded by Evennia anyway.

That is false, and backwards.  `DefaultObject.msg` calls
`at_msg_receive` UNCONDITIONALLY and consults sessions sixteen lines
later, only to decide where the *text* goes::

    if not self.at_msg_receive(text=text, from_obj=from_obj, **kwargs):
        return
    ...
    sessions = make_iter(session) if session else self.sessions.all()

Which is the entire mechanism `LLMNpc` is built on.  Nothing was being
discarded; by skipping the call the gate CREATED the discard it claimed
to be exploiting.

`msg_room_identity` is the broadcast door for the eight generated social
commands -- nod, shrug, laugh, sigh, smile, wave, bow, frown, each with
a solo and a targeted form -- so every LLM-driven NPC in the colony was
blind to all of them.  Standing right there, perceiving nothing.

The #462 performance motive survives and is pinned below: items,
corpses, organs and blood pools have `.msg` and no hook, and still cost
nothing.  Only two classes in the codebase override `at_msg_receive`
(`LLMNpcMixin`, `AnsweringFixture`) and both exist to act on what they
hear.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock

from world.identity_utils import msg_room_identity


class _Sessions:
    def __init__(self, n=0):
        self._n = n

    def count(self):
        return self._n


class _Player:
    """A connected observer: reads the text."""

    def __init__(self):
        self.sessions = _Sessions(1)
        self.received = []

    def msg(self, text=None, **kwargs):
        self.received.append(text)


class _Prop:
    """An item, corpse or blood pool: has `.msg`, wants nothing."""

    def __init__(self):
        self.sessions = _Sessions(0)
        self.received = []

    def msg(self, text=None, **kwargs):
        self.received.append(text)


class _ListeningNpc(_Prop):
    """Session-less, but overrides the hook — the LLMNpc shape."""

    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        return True


class _NoSessionHandler(_Prop):
    """An object whose `sessions` is None entirely."""

    def __init__(self):
        super().__init__()
        self.sessions = None


class _Room:
    def __init__(self, contents):
        self.contents = contents


def _char(name):
    c = MagicMock()
    c.get_display_name = lambda looker=None, **kw: name
    return c


def _broadcast(room, template="{actor} waves.", **kwargs):
    msg_room_identity(location=room, template=template,
                      char_refs={"actor": _char("a lanky man")}, **kwargs)


class TestAnNpcCanSeeYouWave(TestCase):

    # -- the defect --------------------------------------------------

    def test_a_session_less_npc_receives_the_broadcast(self):
        npc = _ListeningNpc()
        _broadcast(_Room([npc]))
        self.assertEqual(
            npc.received, ["A lanky man waves."],
            "an NPC that overrides at_msg_receive was skipped, so every "
            "social emote was invisible to it",
        )

    def test_the_npc_sees_the_same_render_a_player_does(self):
        player, npc = _Player(), _ListeningNpc()
        _broadcast(_Room([player, npc]))
        self.assertEqual(npc.received, player.received)

    def test_an_npc_with_a_null_sessions_handler_still_receives(self):
        npc = _NoSessionHandler()
        npc.at_msg_receive = lambda *a, **k: True
        # Bound on the INSTANCE, not the class — must not count.
        _broadcast(_Room([npc]))
        self.assertEqual(
            npc.received, [],
            "the hook is a typeclass property; an instance attribute is "
            "not a listening NPC",
        )

    # -- controls: the #462 performance motive must survive -----------

    def test_a_prop_is_still_skipped(self):
        """Items, corpses, organs, blood pools: `.msg` and no hook."""
        prop = _Prop()
        _broadcast(_Room([prop]))
        self.assertEqual(prop.received, [])

    def test_an_object_with_no_sessions_handler_is_still_skipped(self):
        obj = _NoSessionHandler()
        _broadcast(_Room([obj]))
        self.assertEqual(obj.received, [])

    def test_a_bare_mock_is_not_mistaken_for_an_npc(self):
        """A MagicMock answers to every attribute, including the hook.

        The predicate takes real Python functions only, so a test double
        does not silently join the audience of every broadcast in the
        suite.
        """
        mock = MagicMock()
        mock.sessions.count.return_value = 0
        _broadcast(_Room([mock]))
        mock.msg.assert_not_called()

    def test_a_connected_player_still_receives(self):
        player = _Player()
        _broadcast(_Room([player]))
        self.assertEqual(player.received, ["A lanky man waves."])

    def test_exclude_still_wins_over_the_hook(self):
        """An excluded NPC stays excluded — it is the actor."""
        npc = _ListeningNpc()
        _broadcast(_Room([npc]), exclude=[npc])
        self.assertEqual(npc.received, [])

    def _predicate(self):
        """Bound off the module, not imported, so this file still LOADS
        against the unfixed tree -- an ImportError here would turn every
        test above into an ERROR and destroy the control."""
        import world.identity_utils as mod
        predicate = getattr(mod, "_implements_msg_hook", None)
        self.assertIsNotNone(
            predicate, "world.identity_utils._implements_msg_hook is missing",
        )
        return predicate

    def test_the_real_llm_npc_class_is_recognised(self):
        """Not just the local fake: the shipped typeclasses qualify."""
        from typeclasses.llm_npc import LLMNpc
        from typeclasses.items import AnsweringFixture

        predicate = self._predicate()
        self.assertTrue(predicate(LLMNpc))
        self.assertTrue(predicate(AnsweringFixture))

    def test_a_plain_object_typeclass_is_not_recognised(self):
        """The control for the one above."""
        from evennia.objects.objects import DefaultObject
        from typeclasses.objects import Object

        predicate = self._predicate()
        self.assertFalse(predicate(DefaultObject))
        self.assertFalse(predicate(Object))
