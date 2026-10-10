"""The website stylesheet defines its component theme once (#3356).

`web/static/website/css/custom.css` carried the whole component theme twice:
the Atlas copy, then a stale pre-Atlas copy of the same sections. Because the
stale copy came last it won every cascade tie the first copy had not settled
with `!important`, so table hover rendered pure green, button glows were pure
red and yellow, and the scanline was twice as heavy as the spec says. No CSS
harness exists in this repository, so this pins the file at source level, the
way the webclient pin does: each section banner appears once, and the values
the stale copy carried are gone.
"""
import re
from pathlib import Path
from unittest import TestCase

CSS = Path(__file__).resolve().parents[2] / "web" / "static" / "website" / "css" / "custom.css"
BANNER = re.compile(r"^/\* ===== ([A-Z][A-Z /-]+?) ===== \*/\s*$", re.M)

STALE = (
    "rgba(0, 255, 0, 0.05)",   # table hover, pure green
    "rgba(255, 0, 0, 0.5)",    # btn-danger glow, pure red
    "rgba(255, 255, 0, 0.5)",  # btn-warning glow, pure yellow
)
INTENDED = (
    "rgba(95, 211, 141, 0.08)",  # table hover, jade tint
    "rgba(232, 85, 85, 0.4)",    # btn-danger glow, softened
    "rgba(230, 197, 71, 0.4)",   # btn-warning glow, softened
)


def _source():
    return CSS.read_text(encoding="utf-8")


class TestEachSectionIsDefinedOnce(TestCase):
    def test_no_section_banner_repeats(self):
        names = BANNER.findall(_source())
        repeated = sorted({n for n in names if names.count(n) > 1})
        self.assertEqual(repeated, [], f"section banners defined more than once: {repeated}")

    def test_the_flicker_keyframes_are_defined_once(self):
        self.assertEqual(_source().count("@keyframes terminal-flicker"), 1)


class TestTheStaleValuesAreGone(TestCase):
    def test_no_pure_green_red_or_yellow_survives(self):
        src = _source()
        for value in STALE:
            self.assertNotIn(value, src, f"stale pre-Atlas value still present: {value}")

    def test_the_softened_values_are_present(self):
        src = _source()
        for value in INTENDED:
            self.assertIn(value, src, f"softened value missing: {value}")
        # The glow colours appear twice each by design (text-shadow and
        # box-shadow); the table hover tint is a single declaration.
        self.assertEqual(src.count(INTENDED[0]), 1, "the jade hover tint should be declared once")
