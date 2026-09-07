""""pull pin on c4" finds the c4 in your hand (#2537).

`throw`, `pull` and `catch` each hand-rolled `name in obj.key` and
ignored aliases entirely. The not-found fallback then searched with
`caller.search()`, which **does** honour aliases — so an aliased item
you were holding failed the hand loop, succeeded the fallback, and
produced:

> *"You must be wielding 'c4' to throw it."*

for something already in your hand. Wielded items are always in
`caller.contents` (`wield_item` refuses otherwise), so the fallback
always found them and the self-contradicting branch was the one that
always fired.

**The branding convention makes this systemic, not incidental.** Every
manufactured item carries a brand, so keys are long branded strings and
the aliases are the words a player would actually type:

```
key:     "HDG M67 fragmentation grenade"
aliases: grenade, frag, m67, hdg grenade, frag grenade
```

`grenade`, `frag` and `m67` worked **by luck** — they happen to be
contiguous substrings of the key. `hdg grenade` and `frag grenade` are
not contiguous, and failed.

One matcher now, `match_held`, used by all three commands. Exact key or
alias wins over a substring, so a precise name is never beaten by a
longer item that merely contains it.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

def match_held(name, candidates):
    """Imported lazily so this module still LOADS against the unfixed
    tree. A module-scope import of a not-yet-existing helper turns every
    test into a loader error, which proves nothing — this is the third
    time I have made that mistake in this audit."""
    from commands.CmdThrow import match_held as real
    return real(name, candidates)


class _ItemCase(EvenniaTest):
    def item(self, key, aliases=()):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=self.char1)
        for alias in aliases:
            obj.aliases.add(alias)
        return obj

    def grenade(self):
        return self.item("HDG M67 fragmentation grenade",
                         ["grenade", "frag", "m67", "hdg grenade",
                          "frag grenade"])


class TestTheAliasesThatUsedToFail(_ItemCase):
    """Non-contiguous aliases — the ones luck did not cover."""

    def test_hdg_grenade(self):
        g = self.grenade()
        self.assertIs(match_held("hdg grenade", [g]), g)

    def test_frag_grenade(self):
        g = self.grenade()
        self.assertIs(match_held("frag grenade", [g]), g)

    def test_c4_style_short_alias(self):
        charge = self.item("Vantage BX-9 demolition charge", ["c4", "charge"])
        self.assertIs(match_held("c4", [charge]), charge)


class TestTheOnesThatWorkedByLuckStillWork(_ItemCase):
    def test_a_contiguous_alias(self):
        g = self.grenade()
        self.assertIs(match_held("grenade", [g]), g)

    def test_a_leading_substring_of_the_key(self):
        g = self.grenade()
        self.assertIs(match_held("hdg", [g]), g)

    def test_the_full_key(self):
        g = self.grenade()
        self.assertIs(match_held("HDG M67 fragmentation grenade", [g]), g)

    def test_case_does_not_matter(self):
        g = self.grenade()
        self.assertIs(match_held("FRAG GRENADE", [g]), g)


class TestPrecisionBeatsLength(_ItemCase):
    """An exact name must not lose to a longer item containing it."""

    def test_an_exact_key_wins_over_a_substring_match(self):
        pipe = self.item("pipe")
        pipe_bomb = self.item("pipe bomb")
        self.assertIs(match_held("pipe", [pipe_bomb, pipe]), pipe)

    def test_an_exact_alias_wins_over_a_substring_match(self):
        long_one = self.item("improvised c4 satchel")
        real = self.item("Vantage BX-9 demolition charge", ["c4"])
        self.assertIs(match_held("c4", [long_one, real]), real)


class TestItFindsNothingWhenThereIsNothing(_ItemCase):
    def test_an_unrelated_name(self):
        self.assertIsNone(match_held("banana", [self.grenade()]))

    def test_an_empty_name(self):
        self.assertIsNone(match_held("", [self.grenade()]))

    def test_no_candidates(self):
        self.assertIsNone(match_held("grenade", []))

    def test_none_entries_are_skipped(self):
        """Hand dicts carry `None` for empty slots."""
        g = self.grenade()
        self.assertIs(match_held("grenade", [None, g, None]), g)

    def test_an_object_without_an_alias_handler(self):
        """Flying-object lists can hold stubs in tests."""
        from types import SimpleNamespace
        stub = SimpleNamespace(key="a rock")
        self.assertIs(match_held("rock", [stub]), stub)


class TestAllThreeCommandsUseIt(EvenniaTest):
    """The defect was the same loop copied three times."""

    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "commands" / "CmdThrow.py").read_text(errors="ignore")

    def test_no_hand_rolled_key_loop_survives(self):
        body = self._source()
        self.assertNotIn("in wielded_obj.key.lower()", body)
        self.assertNotIn("in obj.key.lower()", body)

    def test_three_call_sites(self):
        self.assertEqual(self._source().count("match_held("), 4)  # def + 3



class TestTheOldMatcherReallyMissed(EvenniaTest):
    """Reproduces the pre-fix loop, so the defect is demonstrated rather
    than asserted — and so this module fails meaningfully against the
    unfixed tree instead of only erroring on a missing import."""

    @staticmethod
    def old_match(name, candidates):
        for obj in candidates:
            if obj and name.lower() in str(obj.key).lower():
                return obj
        return None

    def _grenade(self):
        obj = create_object("typeclasses.items.Item",
                            key="HDG M67 fragmentation grenade",
                            location=self.char1)
        for alias in ("grenade", "frag", "m67", "hdg grenade",
                      "frag grenade"):
            obj.aliases.add(alias)
        return obj

    def test_a_non_contiguous_alias_was_missed(self):
        g = self._grenade()
        self.assertIsNone(self.old_match("frag grenade", [g]))

    def test_and_so_was_hdg_grenade(self):
        g = self._grenade()
        self.assertIsNone(self.old_match("hdg grenade", [g]))

    def test_a_contiguous_one_worked_by_luck(self):
        """Which is why this survived — the common aliases happen to be
        substrings of the key."""
        g = self._grenade()
        self.assertIs(self.old_match("grenade", [g]), g)

    def test_a_short_alias_with_no_key_overlap_was_missed(self):
        charge = create_object("typeclasses.items.Item",
                               key="Vantage BX-9 demolition charge",
                               location=self.char1)
        charge.aliases.add("c4")
        self.assertIsNone(self.old_match("c4", [charge]))
