"""Every bar of the login frame is the same width (#2752).

The bottom border carried 64 shade blocks where the three top rows
carried 65, so the frame did not close — the bottom edge sat one column
left of the top edge, on the first screen every player sees. It also put
the top rows off the 66-column rule `NEW_PLAYER_EXPERIENCE_SPEC` §3
fixes for the post-menu blocks, which the bottom bar already matched, so
the two halves disagreed with each other AND with the spec.

The header row was correct by accident. Its trailing shade run was a
literal, and it measured right only because
`len("Gelatinous Monster") + len("6.1.0")` happened to land there —
renaming the server or bumping Evennia would have skewed it.
"""
from django.conf import settings
from django.test import override_settings
from evennia.utils.ansi import strip_ansi
from evennia.utils.test_resources import EvenniaTest

from server.conf import connection_screens as screens_mod
from server.conf.connection_screens import connection_screen

#: Read off the module with the spec's own number as the default:
#: importing a constant that does not exist yet makes this file fail to
#: LOAD against the unfixed tree, and a test that never runs is not a
#: control. 66 is `NEW_PLAYER_EXPERIENCE_SPEC` §3.
FRAME_WIDTH = getattr(screens_mod, "FRAME_WIDTH", 66)

EDGE = "█"


def bars(screen):
    """Every framing row, colour stripped."""
    return [line for line in strip_ansi(screen).splitlines()
            if line.startswith(EDGE)]


class TestTheLoginFrameCloses(EvenniaTest):

    def test_the_screen_has_a_frame_at_all(self):
        """Control: no bars means no mismatch, and every width
        assertion below would pass on an empty list."""
        self.assertGreaterEqual(len(bars(connection_screen())), 4)

    def test_every_bar_is_the_same_width(self):
        widths = {len(bar) for bar in bars(connection_screen())}
        self.assertEqual(
            len(widths), 1,
            f"the frame does not close — bar widths {sorted(widths)}")

    def test_and_that_width_is_the_spec_width(self):
        for bar in bars(connection_screen()):
            self.assertEqual(len(bar), FRAME_WIDTH)

    def test_every_bar_is_closed_at_both_ends(self):
        for bar in bars(connection_screen()):
            self.assertTrue(bar.endswith(EDGE), bar)


class TestTheHeaderIsNotCorrectByAccident(EvenniaTest):
    """The row that lined up only because two runtime values happened
    to be the right length."""

    @override_settings(SERVERNAME="A")
    def test_a_short_server_name(self):
        widths = {len(bar) for bar in bars(connection_screen())}
        self.assertEqual(widths, {FRAME_WIDTH})

    @override_settings(
        SERVERNAME="A Very Much Longer Server Name Indeed")
    def test_a_long_server_name(self):
        widths = {len(bar) for bar in bars(connection_screen())}
        self.assertEqual(
            widths, {FRAME_WIDTH},
            "renaming the server skewed the header row")

    def test_the_title_still_says_the_server_name(self):
        """Control: padding must not have eaten the text it pads."""
        self.assertIn(settings.SERVERNAME,
                      strip_ansi(connection_screen()))
