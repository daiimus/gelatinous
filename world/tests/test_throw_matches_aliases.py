""""pull pin on c4" finds the c4 in your hand (#2537, #3783).

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

All three commands now name their object with the core matcher,
`Character.search(name, candidates=pool)` (#3783), the same one the
not-held fallback uses, so the two lookups cannot disagree. Exact key or
alias wins over a partial name, each typed word must START a word of
the key or an alias ("nade" is not "grenade"), and ordinals pick a twin
("2nd grenade").

The tests drive the real commands on real objects. The caller is
`char2`: `char1` is a Developer in EvenniaTest, which changes the
#dbref and key-match branches.
"""
from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.CmdThrow import CmdCatch, CmdPull, CmdThrow
from world.combat.constants import (
    MSG_CATCH_OBJECT_NOT_FOUND,
    MSG_CATCH_WHAT,
    MSG_PULL_OBJECT_NOT_FOUND,
    MSG_THROW_OBJECT_NOT_FOUND,
    NDB_FLYING_OBJECTS,
)


class _ItemCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.caller = self.char2
        self.caller.msg = MagicMock()

    def item(self, key, aliases=(), location=None, **db_fields):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=location or self.caller,
                            aliases=list(aliases))
        for name, value in db_fields.items():
            obj.attributes.add(name, value)
        return obj

    def grenade(self, location=None, **db_fields):
        return self.item("HDG M67 fragmentation grenade",
                         ["grenade", "frag", "m67", "hdg grenade",
                          "frag grenade"], location=location, **db_fields)

    def hold(self, right=None, left=None):
        self.caller.hands = {"right_hand": right, "left_hand": left}

    def run_cmd(self, cmdclass, args):
        cmd = cmdclass()
        cmd.caller = self.caller
        cmd.args = args
        cmd.parse()
        cmd.func()

    def said(self, text):
        sent = [str(c.args[0]) for c in self.caller.msg.call_args_list if c.args]
        return any(text in line for line in sent)


class _ThrowCase(_ItemCase):
    def thrown(self, name):
        """What `throw <name> to here` launches, or None."""
        with patch.object(CmdThrow, "handle_utility_throw") as fly:
            self.run_cmd(CmdThrow, f"{name} to here")
        return fly.call_args.args[0] if fly.called else None


class TestTheAliasesThatUsedToFail(_ThrowCase):
    """Non-contiguous aliases — the ones luck did not cover."""

    def test_hdg_grenade(self):
        g = self.grenade()
        self.hold(right=g)
        self.assertIs(self.thrown("hdg grenade"), g)

    def test_frag_grenade(self):
        g = self.grenade()
        self.hold(right=g)
        self.assertIs(self.thrown("frag grenade"), g)

    def test_c4_style_short_alias(self):
        charge = self.item("Vantage BX-9 demolition charge", ["c4", "charge"])
        self.hold(right=charge)
        self.assertIs(self.thrown("c4"), charge)


class TestTheOnesThatWorkedByLuckStillWork(_ThrowCase):
    def test_a_contiguous_alias(self):
        g = self.grenade()
        self.hold(right=g)
        self.assertIs(self.thrown("grenade"), g)

    def test_a_leading_word_of_the_key(self):
        g = self.grenade()
        self.hold(right=g)
        self.assertIs(self.thrown("hdg"), g)

    def test_the_full_key(self):
        g = self.grenade()
        self.hold(right=g)
        self.assertIs(self.thrown("HDG M67 fragmentation grenade"), g)

    def test_case_does_not_matter(self):
        g = self.grenade()
        self.hold(right=g)
        self.assertIs(self.thrown("FRAG GRENADE"), g)


class TestPrecisionBeatsLength(_ThrowCase):
    """An exact name must not lose to a longer item containing it."""

    def test_an_exact_key_wins_over_a_partial_match(self):
        pipe_bomb = self.item("pipe bomb")
        pipe = self.item("pipe")
        self.hold(right=pipe_bomb, left=pipe)
        self.assertIs(self.thrown("pipe"), pipe)

    def test_an_exact_alias_wins_over_a_partial_match(self):
        long_one = self.item("improvised c4 satchel")
        real = self.item("Vantage BX-9 demolition charge", ["c4"])
        self.hold(right=long_one, left=real)
        self.assertIs(self.thrown("c4"), real)


class TestItFindsNothingWhenThereIsNothing(_ThrowCase):
    def test_an_unrelated_name(self):
        self.hold(right=self.grenade())
        self.assertIsNone(self.thrown("banana"))
        self.assertTrue(self.said(MSG_THROW_OBJECT_NOT_FOUND.format(object="banana")))

    def test_no_candidates(self):
        self.hold()
        self.assertIsNone(self.thrown("grenade"))
        self.assertTrue(self.said(MSG_THROW_OBJECT_NOT_FOUND.format(object="grenade")))

    def test_an_empty_hand_beside_a_full_one(self):
        """Hand dicts carry `None` for empty slots."""
        g = self.grenade()
        self.hold(right=None, left=g)
        self.assertIs(self.thrown("grenade"), g)


class TestThrowNamesLikeEveryOtherCommand(_ThrowCase):
    def test_an_ordinal_picks_the_second_twin(self):
        first, second = self.grenade(), self.grenade()
        self.hold(right=first, left=second)
        self.assertIs(self.thrown("2nd grenade"), second)

    def test_a_fragment_from_the_middle_of_a_word_is_refused(self):
        """`nade` used to throw the grenade as a key substring."""
        self.hold(right=self.grenade())
        self.assertIsNone(self.thrown("nade"))
        self.assertTrue(self.said(MSG_THROW_OBJECT_NOT_FOUND.format(object="nade")))

    def test_me_is_not_a_fragment_of_fragmentation(self):
        """`throw me` used to throw the grenade ('me' in 'fragmentation');
        it must not throw the thrower either."""
        self.hold(right=self.grenade())
        self.assertIsNone(self.thrown("me"))
        self.assertTrue(self.said(MSG_THROW_OBJECT_NOT_FOUND.format(object="me")))


class TestPullNamesLikeEveryOtherCommand(_ItemCase):
    def pull(self, name):
        with patch("commands.explosion_utils.start_grenade_ticker"):
            self.run_cmd(CmdPull, f"pin on {name}")

    def test_an_alias_that_is_not_in_the_key(self):
        charge = self.item("Vantage BX-9 demolition charge", ["c4"],
                           is_explosive=True)
        self.hold(right=charge)
        self.pull("c4")
        self.assertTrue(charge.db.pin_pulled)

    def test_an_ordinal_picks_the_second_twin(self):
        first = self.grenade(is_explosive=True)
        second = self.grenade(is_explosive=True)
        self.hold(right=first, left=second)
        self.pull("2nd grenade")
        self.assertTrue(second.db.pin_pulled)
        self.assertFalse(first.db.pin_pulled)

    def test_a_fragment_from_the_middle_of_a_word_is_refused(self):
        g = self.grenade(is_explosive=True)
        self.hold(right=g)
        self.pull("nade")
        self.assertFalse(g.db.pin_pulled)
        self.assertTrue(self.said(MSG_PULL_OBJECT_NOT_FOUND.format(object="nade")))


class TestCatchNamesLikeEveryOtherCommand(_ItemCase):
    """In-flight objects stay in the thrower's (`char1`'s) contents."""

    def setUp(self):
        super().setUp()
        self.hold()

    def in_the_air(self, *objs):
        setattr(self.room1.ndb, NDB_FLYING_OBJECTS, list(objs))

    def catch(self, args):
        with patch("commands.CmdThrow.random") as rolled, \
                patch("commands.CmdThrow.msg_room_identity"):
            rolled.random.return_value = 0.1  # under 0.6: caught
            self.run_cmd(CmdCatch, args)

    def test_an_alias_that_is_not_in_the_key(self):
        g = self.grenade(location=self.char1)
        self.in_the_air(g)
        self.catch("frag grenade")
        self.assertEqual(g.location, self.caller)

    def test_an_ordinal_picks_the_second_twin(self):
        first = self.grenade(location=self.char1)
        second = self.grenade(location=self.char1)
        self.in_the_air(first, second)
        self.catch("2nd grenade")
        self.assertEqual(second.location, self.caller)
        self.assertEqual(first.location, self.char1)

    def test_a_fragment_from_the_middle_of_a_word_is_refused(self):
        g = self.grenade(location=self.char1)
        self.in_the_air(g)
        self.catch("nade")
        self.assertEqual(g.location, self.char1)
        self.assertTrue(self.said(MSG_CATCH_OBJECT_NOT_FOUND.format(object="nade")))

    def test_an_empty_name_catches_nothing(self):
        """An empty name matches every candidate in the core matcher, so
        the command refuses it before searching."""
        g = self.grenade(location=self.char1)
        self.in_the_air(g)
        self.catch("   ")
        self.assertEqual(g.location, self.char1)
        self.assertTrue(self.said(MSG_CATCH_WHAT))

    def test_me_is_not_in_the_air(self):
        g = self.grenade(location=self.char1)
        self.in_the_air(g)
        self.catch("me")
        self.assertEqual(g.location, self.char1)
        self.assertTrue(self.said(MSG_CATCH_OBJECT_NOT_FOUND.format(object="me")))


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

    def test_three_call_sites_use_the_core_matcher(self):
        body = self._source()
        self.assertNotIn("match_held", body)
        self.assertEqual(body.count("candidates=held, quiet=True"), 2)
        self.assertEqual(body.count("candidates=flying_objects, quiet=True"), 1)


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
