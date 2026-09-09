"""`remember` asks which one, instead of picking for you (#2409).

The target lookup is:

    target = caller.search(target_str, quiet=True)
    target = target[0] if target else self._find_document(caller, target_str)

`quiet=True` suppresses Evennia's own messaging and returns a LIST, and
`target[0]` then takes the first match. The NO-match case is handled --
the next line re-runs `caller.search` for its error message -- but the
MULTI-match case is not: two people who both answer to the typed word
means the first one in the room's contents is silently remembered.

That is worse here than in most commands. `remember <target> as <name>`
writes into recognition memory, which is what the whole identity layer
reads to decide whether an observer gets a name. Guessing wrong does
not fail loudly; it teaches the player a face under the wrong name and
keeps answering that way.

The fix re-runs the search unquieted on ambiguity, which is the same
thing the no-match branch already does one line below -- so the player
gets Evennia's standard "More than one match" list and picks with an
ordinal, exactly as they would anywhere else.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdCharacter import CmdRemember


class TestAnAmbiguousRememberAsksFirst(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        # Two bodies that answer to the same typed word.
        self.a = create_object("typeclasses.characters.Character",
                               key="courier", location=self.room1)
        self.b = create_object("typeclasses.characters.Character",
                               key="courier", location=self.room1)
        for who in (self.a, self.b):
            who.height = "tall"
            who.build = "lean"
            who.sdesc_keyword = "androog"

    def _remembered(self):
        mem = self.char1.recognition_memory or {}
        try:
            return dict(mem)
        except Exception:  # noqa: BLE001
            return {}

    def test_an_unambiguous_remember_still_works(self):
        """Control: without this, 'never remembers' would pass for a
        command that does nothing at all."""
        self.b.delete()
        self.call(CmdRemember(), "courier as Wren")
        self.assertTrue(self._remembered(),
                        "an unambiguous remember stored nothing")

    def test_two_matches_do_not_silently_pick_one(self):
        before = self._remembered()
        self.call(CmdRemember(), "courier as Wren")
        self.assertEqual(
            self._remembered(), before,
            "an ambiguous remember committed a face without asking")

    def test_it_says_so(self):
        """Evennia's own wording is "Multiple matches for ...", followed
        by the numbered list the player picks from with an ordinal.
        Asserted on the real string, not the one I assumed."""
        out = str(self.call(CmdRemember(), "courier as Wren")).lower()
        self.assertIn("multiple matches", out)
        self.assertIn("1.", out)
