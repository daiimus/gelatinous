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


class TestTheProbeFollowsTheFont(TestCase):
    def test_the_font_is_read_outside_the_create_once_branch(self):
        body = _measure_screen_source()
        # the three style assignments sit after the `if (!probeEl) {...}` block
        after_create = body[body.index("document.body.appendChild(probeEl)"):]
        for prop in ("fontFamily", "fontSize", "lineHeight"):
            self.assertIn(f"probeEl.style.{prop} = font.{prop}", after_create)

    def test_the_font_is_not_frozen_into_the_create_branch(self):
        body = _measure_screen_source()
        create = body[body.index("if (!probeEl)"):body.index("document.body.appendChild(probeEl)")]
        self.assertNotIn("font-family:", create)
        self.assertNotIn("font-size:", create)


class TestThePaddingIsTheStylesheets(TestCase):
    def test_no_padding_literal_is_subtracted(self):
        body = _measure_screen_source()
        self.assertIsNone(re.search(r"client(Width|Height)\s*-\s*\d+", body), body)

    def test_all_four_computed_paddings_are_used(self):
        body = _measure_screen_source()
        for side in ("paddingLeft", "paddingRight", "paddingTop", "paddingBottom"):
            self.assertIn(f"pad.{side}", body)
