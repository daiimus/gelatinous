"""The website stylesheet defines its component theme once (#3356).

`web/static/website/css/custom.css` carried the whole component theme twice:
the Atlas copy, then a stale pre-Atlas copy of the same sections, body rule
included. Because the stale copy came last it won every cascade tie the
first copy had not settled with `!important`: pure red and yellow button
glows, a scanline twice as heavy as the spec states, a faster flicker. No
CSS harness exists in this repository, so this pins the file at source
level, the way the webclient pin does: every section banner once (and the
banner check must account for every banner line, so a new banner style
cannot slip past it), every `@keyframes` once, no rule repeated verbatim in
the same context, and the stale copy's own values gone.
"""
import re
from collections import Counter
from pathlib import Path
from unittest import TestCase

CSS = Path(__file__).resolve().parents[2] / "web" / "static" / "website" / "css" / "custom.css"

# The three banner styles the file uses: `/* ===== NAME ===== */` on one
# line; `/* ===== NAME =====` opening a prose comment; and `/* ====...`
# followed by an upper-case title on the next line. Every line that opens
# with `/* =` is a banner, and the test checks the two counts agree.
BANNER_LINE = re.compile(r"^/\* =", re.M)
BANNER = re.compile(
    r"^/\* =+ (?P<inline>[A-Z][^\n=]*?) =+(?: \*/)?\s*$"
    r"|^/\* =+\s*\n[ \t]+(?P<titled>[A-Z][^\n]*?)\s*$",
    re.M,
)
KEYFRAMES = re.compile(r"@keyframes\s+([\w-]+)")
CONTEXTS = ("@media", "@supports")

STALE = (
    "rgba(255, 0, 0, 0.5)",    # btn-danger glow, pure red
    "rgba(255, 255, 0, 0.5)",  # btn-warning glow, pure yellow
    "rgba(0, 255, 0, 0.05)",   # table hover, pure green
)
SOFTENED = (
    "rgba(232, 85, 85, 0.4)",  # btn-danger glow
    "rgba(230, 197, 71, 0.4)", # btn-warning glow
)


def _source():
    return CSS.read_text(encoding="utf-8")


def _banners(src):
    return [m.group("inline") or m.group("titled") for m in BANNER.finditer(src)]


def _rules(src):
    """(context, selector, body) for every rule; @media/@supports blocks are
    the context of the rules inside them; @keyframes blocks are skipped whole.
    Rule bodies never nest in this file, so a body ends at the next brace."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    found, ctx, buf, i = [], [], "", 0
    while i < len(src):
        ch = src[i]
        if ch == "{":
            head = re.sub(r"\s+", " ", buf.rsplit(";", 1)[-1]).strip()
            buf = ""
            if head.startswith(CONTEXTS):
                ctx.append(head)
            elif head.startswith("@keyframes"):
                depth, i = 1, i + 1
                while depth:
                    depth += {"{": 1, "}": -1}.get(src[i], 0)
                    i += 1
                continue
            else:
                j = src.index("}", i)
                body = re.sub(r"\s+", " ", src[i + 1:j]).strip().rstrip(";")
                found.append((" > ".join(ctx), head, body))
                i = j + 1
                continue
        elif ch == "}":
            buf = ""
            if ctx:
                ctx.pop()
        else:
            buf += ch
        i += 1
    return found


def _repeated(items):
    return sorted(k for k, n in Counter(items).items() if n > 1)


class TestEachSectionIsDefinedOnce(TestCase):
    def test_no_section_banner_repeats(self):
        src = _source()
        names = _banners(src)
        self.assertGreater(len(names), 20, "banner regex no longer matches the file")
        self.assertEqual(len(names), len(BANNER_LINE.findall(src)), "a banner line the banner regex does not read")
        self.assertEqual(_repeated(names), [], "section banners defined more than once")

    def test_no_keyframes_block_repeats(self):
        self.assertEqual(_repeated(KEYFRAMES.findall(_source())), [], "@keyframes defined more than once")

    def test_no_rule_is_repeated_verbatim_in_the_same_context(self):
        rules = _rules(_source())
        self.assertGreater(len(rules), 100, "rule parser no longer sees the file")
        dups = [f"{ctx or 'top level'}: {sel} {{ {body[:60]} }}" for ctx, sel, body in _repeated(rules)]
        self.assertEqual(dups, [], "rules repeated verbatim in the same context")


class TestTheStaleValuesAreGone(TestCase):
    def test_no_pure_red_yellow_or_green_survives(self):
        src = _source()
        for value in STALE:
            self.assertEqual(src.count(value), 0, f"stale pre-Atlas value still present: {value}")

    def test_the_softened_glows_are_present(self):
        src = _source()
        for value in SOFTENED:
            self.assertGreater(src.count(value), 0, f"softened value missing: {value}")
