"""A keyword cannot be approved into two gender lists (#2650).

`add_approved_keyword` loaded ONE list and asked "is it already in this
one?", so the same keyword could be approved as both feminine and
masculine. `get_apparent_gender` then resolves feminine-first, so the
duplicate silently read female — and the admin who approved it as
masculine was told it worked.

The old error message was accurate about what it had checked, which is
what made the gap easy to miss.
"""
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from world import identity as identity_mod
from world.identity import add_approved_keyword


class _Lists(EvenniaTest):
    """Holds the three lists in memory so nothing touches ServerConfig."""

    def setUp(self):
        super().setUp()
        self.lists = {"feminine": set(), "masculine": set(),
                      "neutral": set()}
        self.written = []
        patchers = [
            patch.object(identity_mod, "_load_gender_keyword_set",
                         side_effect=lambda name: self.lists[name]),
            patch.object(identity_mod.ServerConfig.objects, "conf",
                         side_effect=lambda *a, **kw: self.written.append(a)),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

    def add(self, keyword, gender_list):
        return add_approved_keyword(keyword, gender_list, admin_name="test")


class TestAKeywordLivesInOneList(_Lists):

    def test_a_fresh_keyword_is_accepted(self):
        """Control: if nothing could be added, every rejection below
        would pass for the wrong reason."""
        ok, why = self.add("droog", "masculine")
        self.assertTrue(ok, why)

    def test_the_same_list_twice_is_still_refused(self):
        self.lists["masculine"].add("droog")
        ok, why = self.add("droog", "masculine")
        self.assertFalse(ok)
        self.assertIn("masculine", why)

    def test_a_different_list_is_refused_too(self):
        self.lists["feminine"].add("droog")
        ok, why = self.add("droog", "masculine")
        self.assertFalse(ok, "approved into a second gender list")
        self.assertIn("feminine", why)

    def test_the_refusal_says_which_list_has_it(self):
        """An admin who is told 'already in the masculine list' while
        adding to masculine has no idea the real holder is feminine."""
        self.lists["neutral"].add("figure")
        _ok, why = self.add("figure", "feminine")
        self.assertIn("neutral", why)

    def test_every_pair_is_covered(self):
        """Not just the pair that happened to be reported: three lists
        make six orderings and any of them silently resolves."""
        for holder in ("feminine", "masculine", "neutral"):
            for adding in ("feminine", "masculine", "neutral"):
                if holder == adding:
                    continue
                for name in self.lists:
                    self.lists[name].clear()
                self.lists[holder].add("spanner")
                ok, _why = self.add("spanner", adding)
                self.assertFalse(
                    ok, f"{holder!r} keyword accepted into {adding!r}")

    def test_a_refusal_writes_nothing(self):
        self.lists["feminine"].add("droog")
        self.add("droog", "masculine")
        self.assertEqual(self.written, [])

    def test_an_invalid_list_is_still_refused(self):
        ok, why = self.add("droog", "unhelpful")
        self.assertFalse(ok)
        self.assertIn("Invalid", why)
