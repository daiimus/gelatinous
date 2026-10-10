"""The webclient reports the screen it actually has (#3396, #3397).

`measureScreen()` in web/static/webclient/js/gel.js froze its measuring
probe's font at first use, although the output pane's font shrinks at the
600px breakpoint, and subtracted desktop padding literals (20/16) although
the phone rule pads less. No JavaScript test harness exists in this
repository, so this pins the two shapes at source level, the way the staff
guard tests pin command source: the probe's font is refreshed on every call,
and the padding comes from the computed style, never from a literal.
"""
import re
from pathlib import Path
from unittest import TestCase

GEL = Path(__file__).resolve().parents[2] / "web" / "static" / "webclient" / "js" / "gel.js"


def _measure_screen_source():
    src = GEL.read_text(encoding="utf-8")
    start = src.index("function measureScreen()")
    end = src.index("function sendScreenSize()")
    return src[start:end]


def _create_branch_and_rest(body):
    """Split at the brace that CLOSES the `if (!probeEl) {...}` block, so an
    assignment smuggled into the branch after appendChild counts as frozen."""
    start = body.index("if (!probeEl)")
    close = body.index("}", body.index("document.body.appendChild(probeEl)"))
    return body[start:close], body[close:]


class TestTheProbeFollowsTheFont(TestCase):
    def test_the_font_is_set_on_every_call_after_the_branch(self):
        _, rest = _create_branch_and_rest(_measure_screen_source())
        for prop in ("fontFamily", "fontSize", "lineHeight"):
            self.assertIn(f"probeEl.style.{prop} = font.{prop}", rest)

    def test_nothing_about_the_font_lives_in_the_create_branch(self):
        create, _ = _create_branch_and_rest(_measure_screen_source())
        self.assertNotIn("font", create.lower())


class TestTheCellIsMeasuredFractionally(TestCase):
    def test_the_rect_is_used_not_the_whole_pixel_offsets(self):
        body = _measure_screen_source()
        self.assertIn("probeEl.getBoundingClientRect()", body)
        self.assertNotIn("probeEl.offsetWidth", body)
        self.assertNotIn("probeEl.offsetHeight", body)


class TestThePaddingIsTheStylesheets(TestCase):
    def test_no_padding_literal_is_subtracted(self):
        body = _measure_screen_source()
        self.assertIsNone(re.search(r"client(Width|Height)\s*-\s*\d+", body), body)

    def test_all_four_computed_paddings_are_used(self):
        body = _measure_screen_source()
        for side in ("paddingLeft", "paddingRight", "paddingTop", "paddingBottom"):
            self.assertIn(f"pad.{side}", body)
