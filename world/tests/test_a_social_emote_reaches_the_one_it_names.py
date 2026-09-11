"""A social emote marks the one person it points at (#3211).

The second half of "`wave at <npc>` does nothing". #2640 was why the
message never arrived; this is why it still would not draw a reaction
once it did.

`msg_room_identity` varies the TEXT per observer but sent one shared
kwargs dict to the whole room, so the targeted form of the eight
generated social commands could not say who it was aimed at. Adding a
bare `addressed=True` would have told the entire room the pose was aimed
at them. So the flag simply was not sent, and `LLMNpcMixin.at_msg_receive`
-- which reacts only when `kwargs.get("addressed")` -- filed every
targeted wave, nod and bow in the observation buffer and stopped there.

Meanwhile `world/emote.py` computes exactly this per observer, twice
(`id(observer) in referenced`), for dot-poses and `emote`. So
`.waves at bartender` was answered and `wave at bartender` -- the shipped
command for the same gesture -- was not. Two doors onto one act,
disagreeing.

HARNESS NOTE: `msg_room_identity` renders only for observers that will
READ the message (a connected session) or ACT on it (an `at_msg_receive`
override). A bare test observer has neither and is skipped entirely, so a
plain `Character` bystander would "prove" the flag was absent by never
being rendered for at all. Every observer below is an `LLMNpc`, which
overrides the hook and therefore passes the gate for the real reason.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import (EvenniaCommandTest,
                                          EvenniaTest)

from world.identity_utils import msg_room_identity
from typeclasses.llm_npc import LLMNpc
from world.emote_templates import SOCIAL_COMMANDS


class _Recorder:
    """Captures the kwargs each observer's at_msg_receive actually gets.

    ``as_hook`` returns a real FUNCTION, and that matters: the audience
    gate asks ``inspect.isfunction`` whether the class overrides the hook,
    so a callable object -- or a Mock -- does not qualify and the observer
    is skipped before any kwargs are sent. Patching with one would make
    this whole file "prove" the flag was missing by never rendering at all.
    """

    def __init__(self):
        self.calls = []

    def as_hook(self):
        calls = self.calls

        def at_msg_receive(npc_self, text=None, from_obj=None, **kwargs):
            calls.append((npc_self, text, kwargs))
            return True

        return at_msg_receive

    def kwargs_for(self, npc):
        for who, _text, kw in self.calls:
            if who is npc:
                return kw
        return None

    def heard(self, npc):
        return any(who is npc for who, _t, _k in self.calls)


class AddressedRefsTest(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.target = create_object(LLMNpc, key="bartender",
                                    location=self.room1)
        self.bystander = create_object(LLMNpc, key="drinker",
                                       location=self.room1)

    def _broadcast(self, **extra):
        rec = _Recorder()
        with patch.object(LLMNpc, "at_msg_receive", rec.as_hook()):
            msg_room_identity(
                self.room1,
                "{actor} waves at {target}.",
                {"actor": self.char1, "target": self.target},
                exclude=[self.char1],
                type="pose",
                from_obj=self.char1,
                **extra,
            )
        return rec

    # --- harness control -------------------------------------------------

    def test_both_observers_are_rendered_for(self):
        # Passes on the fixed and unfixed tree alike. If this fails, the
        # audience gate skipped them and every other assertion here is
        # measuring nothing.
        rec = self._broadcast(addressed_refs=("target",))
        self.assertTrue(rec.heard(self.target), "target never rendered for")
        self.assertTrue(rec.heard(self.bystander),
                        "bystander never rendered for")

    # --- the defect ------------------------------------------------------

    def test_the_named_observer_is_addressed(self):
        rec = self._broadcast(addressed_refs=("target",))
        self.assertTrue(
            rec.kwargs_for(self.target).get("addressed"),
            "the one the pose points at was not flagged, so an NPC waved "
            "at can only observe the wave, never answer it")

    def test_the_room_is_not_addressed(self):
        # The reason a bare addressed=True was never an option.
        rec = self._broadcast(addressed_refs=("target",))
        self.assertFalse(rec.kwargs_for(self.bystander).get("addressed"),
                         "the whole room was told the pose was aimed at it")

    def test_text_still_varies_per_observer(self):
        rec = self._broadcast(addressed_refs=("target",))
        for _who, text, _kw in rec.calls:
            self.assertIn("waves at", text)

    # --- back-compat controls -------------------------------------------

    def test_callers_without_addressed_refs_are_untouched(self):
        rec = self._broadcast()
        for _who, _text, kw in rec.calls:
            self.assertNotIn("addressed", kw)

    def test_an_explicit_addressed_kwarg_still_wins(self):
        rec = self._broadcast(addressed_refs=("target",), addressed=False)
        self.assertFalse(rec.kwargs_for(self.target).get("addressed"))


class SocialCommandTest(EvenniaCommandTest):
    """Where players touch it: the real generated `wave` command.

    NOT via `execute_cmd`. Under `evennia test` there is no reactor, so
    `execute_cmd` returns a Deferred that never resolves -- it produces
    zero messages even for `look`, which means a test driving it would
    pass or fail for reasons that have nothing to do with the code. The
    command is driven through Evennia's own `call()` helper instead.
    """

    def setUp(self):
        super().setUp()
        self.npc = create_object(LLMNpc, key="bartender", location=self.room1)
        self.wave = next(c for c in SOCIAL_COMMANDS
                         if getattr(c, "key", None) == "wave")

    def test_wave_at_npc_marks_the_npc_addressed(self):
        rec = _Recorder()
        with patch.object(LLMNpc, "at_msg_receive", rec.as_hook()):
            # `wave <target>`, not `wave at <target>`: the command passes
            # its raw args to `caller.search`, and the "at" is supplied
            # by the rendered prose ("You wave at the bartender."), not
            # parsed out of the input.
            self.call(self.wave(), "bartender", caller=self.char1)
        self.assertTrue(rec.heard(self.npc),
                        "the NPC never heard the wave at all")
        self.assertTrue(
            rec.kwargs_for(self.npc).get("addressed"),
            "`wave at bartender` did not flag the bartender, while "
            "`.waves at bartender` does -- the two pose doors disagree")
