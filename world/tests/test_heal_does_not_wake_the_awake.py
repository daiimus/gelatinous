"""`@heal` does not tell awake people they just came round (#2542).

`@heal` calls `remove_unconscious_state()` on every target, under a
comment calling it *"an expected no-op"*. It is not a no-op — it
broadcasts *"X regains consciousness."* to the whole room and tells the
target *"You slowly regain consciousness..."*.

So `@heal here` in a room of eight awake, standing people emitted eight
spurious recovery broadcasts.

The narration is now gated on whether the character was **actually**
under, read from the same cmdset `apply_unconscious_state` installs
(`unconscious_cmdset`, as the default). The cmdset removal and the
`override_place` clear stay unconditional — those genuinely are
idempotent, which is presumably what the "no-op" comment meant.

Gated in `remove_unconscious_state` rather than at the `@heal` call
site, because there are four callers and the same reasoning applies to
all of them: two in `CmdAdmin`, the genuine recovery in
`world/medical/script.py`, and `apply_death_state` clearing the state on
its way to killing you — that last one was already silent, but only
because `is_dead()` happened to be true by the time it ran.
"""
from evennia.utils.test_resources import EvenniaTest


class _WakeCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1

    @staticmethod
    def _capture(target, said):
        """Records positional AND `text=` calls. `msg_room_identity`
        sends the room its line as a keyword, so a positional-only
        capture reads empty and every assertion about the room passes
        for the wrong reason."""
        def cap(*a, **k):
            if a:
                said.append(str(a[0]))
            elif "text" in k:
                said.append(str(k["text"]))
        target.msg = cap

    def heard_by_room(self, fn):
        """The room broadcast, read at the call rather than at char2.

        `msg_room_identity` has a session gate (#462) and test
        characters have no session, so a bystander's `msg` never fires
        and asserting on it reads empty — every "the room was told
        nothing" test would pass for the wrong reason.
        """
        from unittest import mock
        with mock.patch("typeclasses.characters.msg_room_identity") as spy:
            fn()
        return " ".join(str(c.kwargs.get("template", ""))
                        for c in spy.call_args_list)

    def heard_by_self(self, fn):
        said = []
        self._capture(self.char1, said)
        fn()
        return " ".join(said)


class TestAnAwakeCharacterIsNotWoken(_WakeCase):
    def test_the_room_is_told_nothing(self):
        out = self.heard_by_room(self.char1.remove_unconscious_state)
        self.assertNotIn("regains consciousness", out)

    def test_the_character_is_told_nothing(self):
        out = self.heard_by_self(self.char1.remove_unconscious_state)
        self.assertNotIn("regain consciousness", out)

    def test_calling_it_repeatedly_stays_quiet(self):
        """`@heal here` hits every target; eight calls, eight
        broadcasts, was the reported symptom."""
        def five_times():
            for _ in range(5):
                self.char1.remove_unconscious_state()
        self.assertNotIn("regains consciousness",
                         self.heard_by_room(five_times))


class TestARealRecoveryStillNarrates(_WakeCase):
    """The fix must not silence the case the message exists for."""

    def knock_out(self):
        self.char1.apply_unconscious_state(force_test=True)
        self.assertTrue(
            self.char1.cmdset.has("unconscious_cmdset", must_be_default=True),
            "fixture did not actually apply the unconscious cmdset")

    def test_the_room_is_told(self):
        self.knock_out()
        out = self.heard_by_room(self.char1.remove_unconscious_state)
        self.assertIn("regains consciousness", out)

    def test_the_character_is_told(self):
        self.knock_out()
        out = self.heard_by_self(self.char1.remove_unconscious_state)
        self.assertIn("regain consciousness", out)

    def test_waking_twice_only_narrates_once(self):
        self.knock_out()
        self.char1.remove_unconscious_state()
        out = self.heard_by_room(self.char1.remove_unconscious_state)
        self.assertNotIn("regains consciousness", out)


class TestTheStateIsStillCleared(_WakeCase):
    """The parts that really were idempotent stay unconditional."""

    def test_the_normal_cmdset_is_restored(self):
        self.char1.apply_unconscious_state(force_test=True)
        self.char1.remove_unconscious_state()
        self.assertFalse(
            self.char1.cmdset.has("unconscious_cmdset", must_be_default=True))

    def test_the_unconscious_placement_is_cleared(self):
        self.char1.override_place = "unconscious and motionless."
        self.char1.remove_unconscious_state()
        self.assertIsNone(self.char1.override_place)

    def test_another_placement_is_left_alone(self):
        self.char1.override_place = "leaning on the bar."
        self.char1.remove_unconscious_state()
        self.assertEqual(self.char1.override_place, "leaning on the bar.")

    def test_it_is_safe_on_a_character_who_was_never_under(self):
        self.char1.remove_unconscious_state()
        self.assertFalse(
            self.char1.cmdset.has("unconscious_cmdset", must_be_default=True))


class TestDyingDoesNotNarrateRecovery(_WakeCase):
    """`apply_death_state` clears the unconscious state on its way to
    killing you. That was already silent — but only because
    `is_dead()` happened to be true by then. Both guards now apply."""

    def test_a_dead_character_says_nothing(self):
        from unittest import mock
        self.char1.apply_unconscious_state(force_test=True)
        with mock.patch.object(type(self.char1), "is_dead",
                               return_value=True):
            out = self.heard_by_room(self.char1.remove_unconscious_state)
        self.assertNotIn("regains consciousness", out)
