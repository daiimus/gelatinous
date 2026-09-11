"""Player text bound for a public GitHub issue is neutralised.

Regression pin for #2527. `sanitize_description` truncated and stripped,
under a name and a docstring that both said "sanitize" and a spec that
ticked two sanitization boxes. Whatever a player typed reached the issue
body verbatim -- and the TITLE bypassed the function entirely.

Two things GitHub ACTS on rather than merely renders, and both reach
real people:

* `@name` pings that account, every time, from a report anyone in the
  game can file;
* `#123` cross-references an issue or PR and leaves a permanent
  backlink on it.

Escaped with a zero-width space rather than stripped: the report still
reads as the player wrote it. The text is evidence, and silently
deleting characters from a bug report is its own bug.

Markdown and HTML are deliberately left alone -- GitHub sanitizes HTML
in issue bodies, and formatting is not the hazard.
"""

from unittest import TestCase

from commands.CmdBug import CmdBug

ZW = "​"


class TestTheSanitizerSanitizes(TestCase):

    def setUp(self):
        self.cmd = CmdBug()

    def _title(self, text):
        """Call `sanitize_title`, reporting its ABSENCE as a named
        failure. On an unfixed tree the method does not exist and a bare
        call raises AttributeError — which reads like a broken harness
        rather than an unsanitized title."""
        fn = getattr(self.cmd, "sanitize_title", None)
        self.assertIsNotNone(
            fn, "CmdBug has no sanitize_title, so the title reaches the "
                "public issue unsanitized")
        return fn(text)

    def test_a_mention_does_not_ping(self):
        out = self.cmd.sanitize_description("ping @daiimus about this")
        self.assertIn(f"@{ZW}daiimus", out)

    def test_a_cross_reference_does_not_backlink(self):
        out = self.cmd.sanitize_description("same as #2527")
        self.assertIn(f"#{ZW}2527", out)

    def test_the_title_is_sanitized_too(self):
        """It bypassed the function entirely."""
        out = self._title("@daiimus broke #2527")
        self.assertIn(f"@{ZW}daiimus", out)
        self.assertIn(f"#{ZW}2527", out)

    def test_the_title_is_still_capped(self):
        self.assertEqual(len(self._title("x" * 500)), 100)

    # -- controls: what must NOT be touched --------------------------

    def test_an_email_address_is_untouched(self):
        out = self.cmd.sanitize_description("mail foo@bar.com please")
        self.assertIn("foo@bar.com", out)
        self.assertNotIn(ZW, out)

    def test_a_hash_that_is_not_a_reference_is_untouched(self):
        out = self.cmd.sanitize_description("I use C# and colour #ff00ff")
        self.assertNotIn(ZW, out)

    def test_markdown_and_html_survive(self):
        text = "the **bold** text and <b>html</b> and &#39; entity"
        self.assertEqual(self.cmd.sanitize_description(text), text)

    def test_truncation_still_happens(self):
        out = self.cmd.sanitize_description("y" * 6000)
        self.assertIn("truncated at 5000 characters", out)

    def test_empty_input_is_not_an_error(self):
        self.assertEqual(self.cmd.sanitize_description(""), "")
        self.assertEqual(self._title(None), "")
