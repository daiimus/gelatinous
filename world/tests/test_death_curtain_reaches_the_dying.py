"""The curtain's own frames pass its own filter (#2469).

`Character.msg` blocked every system message to a dead character except
one recognised by its punctuation:

```python
if '▓' in str(text):
    return super().msg(...)      # allow death curtain animations
```

That is true of the opening frames and false of everything the animation
does afterwards. `curtain_of_death` re-pads mid-animation with `█`
(`:136`), erases the remaining `▓` across twelve trailing drip frames
(`:162-186`), and ends on three frames of pure spaces (`:189-191`).

Measured before the fix, on a character killed by a real bleed-out
rather than a mocked `is_dead`:

```
is_dead() at curtain time:  True
cause-of-death line:        0 of 1 delivered
curtain frames:            40 of 45 delivered   (the tail cut off)
```

The issue flagged its own premise as unverified — whether `is_dead()` is
already true when the curtain runs, since that decides whether the cause
line is lost. It is: `is_dead()` reads `medical_state.is_dead()`, which
the killing damage set before `at_death()` ever called the curtain.
`test_a_real_bleedout_is_dead_before_the_curtain` pins that, because if
it ever stops being true this whole issue changes shape.

The fix marks curtain traffic with `death_curtain=True` instead of
sniffing content, so delivery no longer depends on which characters a
frame happens to contain. That also closes the long-message edge case
(`:93-95`): when the text is wider than the terminal, frame 0 gets no
padding blocks at all and was dropped too.

The flag is *popped* before `super()`. Evennia forwards unknown kwargs
to the protocol as out-of-band outputfuncs, so leaving it in would send
a `death_curtain` OOB message to every client on every frame.

Also removed: a branch allowing `from_obj` whose key contains
"curtain". Nothing ever passed one — `DeathCurtain` is a plain object
and its `msg` calls have no `from_obj` — and a dead handler that looks
like it covers the case is what let the real filter drift out from under
the animation.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from typeclasses.curtain_of_death import curtain_of_death

CURTAIN_MSG = ("|rA |Rred |rhaze |Rblurs |ryour |Rvision |ras |Rthe "
               "|rworld |Rslips |raway|R...|n")


class _DyingCase(EvenniaTest):
    def kill(self, char):
        """Bleed them out for real rather than mocking `is_dead`."""
        state = char.medical_state
        state.blood_level = 0.0
        char.medical_state = state
        return char

    def delivered(self):
        """Record what actually reaches `super().msg`."""
        sink = []
        patch = mock.patch(
            "evennia.objects.objects.DefaultCharacter.msg",
            side_effect=lambda *a, **k: sink.append(
                (a[0] if a else k.get("text"), k)))
        return sink, patch


class TestTheDeadAreReallyDead(_DyingCase):
    def test_a_real_bleedout_is_dead_before_the_curtain(self):
        """The issue's own unverified premise, pinned."""
        self.assertTrue(self.kill(self.char1).is_dead())

    def test_a_live_character_is_not_filtered(self):
        sink, patch = self.delivered()
        with patch:
            self.char1.msg("an ordinary line")
        self.assertEqual(len(sink), 1)


class TestEveryFrameArrives(_DyingCase):
    def test_the_whole_animation_is_delivered(self):
        self.kill(self.char1)
        frames = curtain_of_death(CURTAIN_MSG, width=80)
        sink, patch = self.delivered()
        with patch:
            for frame in frames:
                self.char1.msg(frame, death_curtain=True)
        self.assertEqual(len(sink), len(frames))

    def test_the_blank_final_frames_arrive(self):
        """The last three frames are pure spaces — the end of the drip
        is the point of the effect."""
        self.kill(self.char1)
        sink, patch = self.delivered()
        with patch:
            self.char1.msg(" " * 79, death_curtain=True)
        self.assertEqual(len(sink), 1)

    def test_a_frame_padded_with_the_other_block_arrives(self):
        """Mid-animation frames re-pad with `█`, not `▓`."""
        self.kill(self.char1)
        sink, patch = self.delivered()
        with patch:
            self.char1.msg("█" * 40, death_curtain=True)
        self.assertEqual(len(sink), 1)

    def test_a_message_too_wide_to_pad_still_arrives(self):
        """`padding_needed <= 0` builds frame 0 with no blocks at all."""
        long_text = "x" * 200
        frames = curtain_of_death(long_text, width=40)
        self.assertNotIn("▓", frames[0])
        self.kill(self.char1)
        sink, patch = self.delivered()
        with patch:
            self.char1.msg(frames[0], death_curtain=True)
        self.assertEqual(len(sink), 1)


class TestTheDyingLearnWhatKilledThem(_DyingCase):
    def test_the_cause_line_is_delivered(self):
        self.kill(self.char1)
        sink, patch = self.delivered()
        with patch:
            self.char1.msg("|rYour body succumbs to blood loss. "
                           "The end draws near...|n", death_curtain=True)
        self.assertEqual(len(sink), 1)

    def test_start_animation_sends_it_flagged(self):
        """Through the real entry point, not a hand-built call."""
        from typeclasses.curtain_of_death import DeathCurtain
        self.kill(self.char1)
        seen = []
        with mock.patch.object(type(self.char1), "msg",
                               side_effect=lambda *a, **k: seen.append((a, k))):
            with mock.patch.object(DeathCurtain, "_show_next_frame"):
                DeathCurtain(self.char1).start_animation()
        self.assertTrue(seen, "no cause line was sent at all")
        self.assertTrue(all(k.get("death_curtain") for _a, k in seen),
                        "the cause line went out unflagged")


class TestTheFlagDoesNotReachTheClient(_DyingCase):
    """Evennia turns unknown kwargs into out-of-band outputfuncs."""

    def test_it_is_popped_when_dead(self):
        self.kill(self.char1)
        sink, patch = self.delivered()
        with patch:
            self.char1.msg("a frame", death_curtain=True)
        self.assertNotIn("death_curtain", sink[0][1])

    def test_it_is_popped_when_alive(self):
        sink, patch = self.delivered()
        with patch:
            self.char1.msg("a frame", death_curtain=True)
        self.assertNotIn("death_curtain", sink[0][1])


class TestTheFilterStillFilters(_DyingCase):
    def test_an_unflagged_system_message_is_still_blocked(self):
        self.kill(self.char1)
        sink, patch = self.delivered()
        with patch:
            self.char1.msg("You are hit by a stray round.")
        self.assertEqual(sink, [])

    def test_block_characters_no_longer_buy_passage(self):
        """An armour bar is `▓`-padded too — it used to sail through."""
        self.kill(self.char1)
        sink, patch = self.delivered()
        with patch:
            self.char1.msg("[" + "▓" * 10 + "░" * 10 + "]")
        self.assertEqual(sink, [])

    def test_the_death_progression_script_still_gets_through(self):
        """It identifies itself by `from_obj`, a different door that
        must keep working."""
        self.kill(self.char1)
        speaker = mock.MagicMock()
        speaker.key = "death_progression_script"
        speaker.locks.check.return_value = False
        sink, patch = self.delivered()
        with patch:
            self.char1.msg("Your vision dims further.", from_obj=speaker)
        self.assertEqual(len(sink), 1)

    def test_an_empty_message_is_still_dropped(self):
        self.kill(self.char1)
        sink, patch = self.delivered()
        with patch:
            self.char1.msg("", death_curtain=True)
        self.assertEqual(sink, [])
