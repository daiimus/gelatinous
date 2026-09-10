"""The death curtain's dripping sea actually renders (#2628).

The effect DEATH_CURTAIN_SPEC describes twice — a dense `█` sea
collapsing out of a `▓` field — had never appeared. The frame builder
did:

    frame = "".join(chars).center(curtain_width, "█")

and `chars` is built at full curtain width and only ever mutated in
place (characters replaced by spaces, never removed), so `.center()`
had nothing to pad and returned the string unchanged. Measured on the
unfixed code: 43 frames, zero `█`. The comment on that line described
what did not happen.
"""
from evennia.utils.test_resources import EvenniaTest

from typeclasses.curtain_of_death import (
    _strip_color_codes, curtain_of_death,
)

#: Written out rather than imported from the module under test. Importing
#: the constants would make this file fail to LOAD against the unfixed
#: code, and a test that never runs is not a test that failed — the
#: control has to come back as a failing assertion about the animation.
SEA_INTACT = "\u2593"      # ▓
SEA_DRIPPING = "\u2588"    # █

MESSAGE = "You die."


class TestTheDeathCurtainHasTwoTones(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.frames = [_strip_color_codes(f)
                       for f in curtain_of_death(MESSAGE)]

    def test_the_animation_runs_at_all(self):
        """Control: zero frames would make every assertion below pass
        for the wrong reason."""
        self.assertGreater(len(self.frames), 10)

    def test_the_first_frame_is_the_intact_field(self):
        self.assertIn(SEA_INTACT, self.frames[0])
        self.assertNotIn(SEA_DRIPPING, self.frames[0])

    def test_the_dripping_sea_renders(self):
        """The assertion the unfixed code fails: not one frame in 43
        contained the dripping character."""
        self.assertTrue(
            any(SEA_DRIPPING in f for f in self.frames[1:]),
            "the two-tone effect the spec asserts twice never renders")

    def test_the_message_is_legible_before_it_drips(self):
        """And the effect did not eat the thing it frames."""
        self.assertIn(MESSAGE, self.frames[0])

    def test_it_ends_empty(self):
        self.assertEqual(self.frames[-1].strip(), "")

    def test_a_message_too_long_to_pad_still_drips(self):
        """The other width branch. With no room to pad, `.center` was a
        no-op for a second reason, so this case needs its own frame."""
        long_frames = [_strip_color_codes(f)
                       for f in curtain_of_death("no. " * 60)]
        self.assertGreater(len(long_frames), 10)
        self.assertTrue(any(SEA_DRIPPING in f for f in long_frames[1:])
                        or all(SEA_INTACT not in f for f in long_frames),
                        "a message with no sea to drip should have no "
                        "sea characters at all, in either tone")
