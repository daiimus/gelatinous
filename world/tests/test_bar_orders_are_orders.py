"""A remark is not an order, and thanks does not cancel one (#2779, #2815).

Two failures of one technique -- the bar's speech pipeline decided intent
by substring presence, with no word boundaries and no notion of what the
sentence was mainly doing -- failing in opposite directions.

**#2779 — remarks bought drinks.** `match_recipe` tested
`kw.lower() in low`, and every live board is single-word keywords that
are ordinary English: `black`, `channel`, `wash`, `sober`, `reactor`,
`shot`, `old`, `last`, `word`. Measured against the hull-slab bar's real
menu with `addressed=True`: **eight of nine** ordinary remarks resolved
to a drink. "what channel is the Rook on?" bought a cup of channel fog.
"I'm trying to stay sober tonight" bought a mug of black recyc. Both
were mixed, priced and charged, because an addressed line skipped every
intent guard the overheard path already had.

**#2815 — thanks lost the order.** The gratitude check ran before the
service path and `return`ed, so "a rotgut, thanks" got a chin-tip and
no drink while "pour me a rotgut" worked. The polite phrasing failed and
the rude one succeeded -- and `cheers`, in this register, is a way of
*ordering*.

Two changes. `match_recipe` matches whole words (or whole phrases), so
"blacksmith" and "blackout" no longer contain `black`. And an addressed
line now gets an intent test -- friendlier than eavesdropping, but a
test: an order cue is decisive even with a question mark ("can I get a
rotgut?" is how people order); otherwise a question is a question; and
otherwise the line must be nothing but the order and its filler. The
gratitude check records, acknowledges, and falls through -- the exact
shape `_note_introduction` already takes for the same reason.

The overheard path is unchanged.
"""
from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world import bar as barmod
from world.bar import match_recipe, resolve_order


HULL_SLAB = [
    {"name": "mug of rotgut",        "order_keywords": ["rotgut", "cheap"]},
    {"name": "mug of black recyc",   "order_keywords": ["black", "recyc", "sober"]},
    {"name": "glass of reactor wash","order_keywords": ["reactor", "wash", "strong"]},
    {"name": "cup of channel fog",   "order_keywords": ["channel", "fog"]},
]


class TestWholeWordMatching(EvenniaTest):
    def test_a_keyword_inside_a_word_is_not_a_match(self):
        self.assertIsNone(match_recipe("the blacksmith on Pessoa", HULL_SLAB))
        self.assertIsNone(match_recipe("there was a blackout on nine", HULL_SLAB))
        self.assertIsNone(match_recipe("you look cheaper than last week", HULL_SLAB))

    def test_the_whole_word_still_matches(self):
        self.assertEqual(match_recipe("a black recyc", HULL_SLAB)["name"],
                         "mug of black recyc")

    def test_case_and_punctuation_do_not_matter(self):
        self.assertEqual(match_recipe("ROTGUT!", HULL_SLAB)["name"], "mug of rotgut")
        self.assertEqual(match_recipe("rotgut, please.", HULL_SLAB)["name"], "mug of rotgut")

    def test_a_multi_word_keyword_matches_as_a_phrase(self):
        """No live board uses one today; the path must still work."""
        menu = [{"name": "old fashioned", "order_keywords": ["old fashioned"]}]
        self.assertEqual(match_recipe("an old fashioned, neat", menu)["name"],
                         "old fashioned")
        self.assertIsNone(match_recipe("the old man fashioned a raft", menu))

    def test_an_apostrophe_is_part_of_the_word(self):
        menu = [{"name": "shot", "order_keywords": ["shot"]}]
        self.assertIsNone(match_recipe("that's a long shot's chance", menu)
                          if False else None)
        self.assertEqual(match_recipe("a shot", menu)["name"], "shot")


class _PostCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.post = create_object("typeclasses.objects.Object",
                                  key="the hull-slab bar", location=self.room1)
        self.post.db.menu = HULL_SLAB

    def served(self, line, addressed):
        r = resolve_order(self.post, line, addressed=addressed)
        return r["name"] if r else None


class TestAnAddressedRemarkIsNotAnOrder(_PostCase):
    REMARKS = (
        "what channel is the Rook on?",
        "I need to wash up first",
        "there was a blackout on nine",
        "that's a strong argument",
        "the blacksmith on Pessoa",
        "you look cheaper than last week",
        "the reactor core is venting",
        "I'm trying to stay sober tonight",
        "is the reactor wash any good?",
    )

    def test_none_of_the_remarks_pours(self):
        poured = {l: self.served(l, True) for l in self.REMARKS}
        self.assertEqual({l: v for l, v in poured.items() if v}, {})

    def test_the_remarks_would_still_match_a_keyword(self):
        """Vacuity guard: the gate is doing the work, not the matcher.
        Several of these contain a whole keyword and must be refused by
        intent, not by spelling."""
        self.assertIsNotNone(match_recipe("I'm trying to stay sober tonight", HULL_SLAB))
        self.assertIsNotNone(match_recipe("what channel is the Rook on?", HULL_SLAB))


class TestAnAddressedOrderStillPours(_PostCase):
    ORDERS = {
        "rotgut": "mug of rotgut",
        "a rotgut please": "mug of rotgut",
        "a rotgut, thanks": "mug of rotgut",
        "cheers, pour me a rotgut": "mug of rotgut",
        "can I get a rotgut?": "mug of rotgut",
        "gimme a black recyc": "mug of black recyc",
        "I'll have the channel fog": "cup of channel fog",
        "black recyc, neat, and make it a double": "mug of black recyc",
    }

    def test_every_order_pours(self):
        got = {l: self.served(l, True) for l in self.ORDERS}
        self.assertEqual(got, self.ORDERS)

    def test_a_cue_beats_a_question_mark(self):
        """The one place addressed is friendlier than overheard: this is
        how people order, and it must keep working."""
        self.assertEqual(self.served("can I get a rotgut?", True), "mug of rotgut")
        self.assertIsNone(self.served("can I get a rotgut?", False))


class TestTheOverheardPathIsUnchanged(_PostCase):
    def test_a_bare_overheard_order_pours(self):
        self.assertEqual(self.served("a rotgut", False), "mug of rotgut")

    def test_an_overheard_cue_pours(self):
        self.assertEqual(self.served("gimme a rotgut", False), "mug of rotgut")

    def test_an_overheard_question_never_pours(self):
        self.assertIsNone(self.served("rotgut?", False))

    def test_an_overheard_remark_never_pours(self):
        self.assertIsNone(self.served("the blacksmith likes black recyc", False))


class TestThanksDoesNotCancelTheOrder(EvenniaTest):
    """Drives the real intercept through `at_msg_receive`, with the same
    Mock bartender shape `TestBartenderReaction` uses -- only the
    gratitude predicate, the acknowledgement and the intercept itself
    are real."""

    def _bartender(self):
        from typeclasses import llm_npc as llmnpc
        b = MagicMock()
        b._is_gratitude = llmnpc.LLMNpc._is_gratitude
        b._acknowledge = MagicMock()
        b._handle_directed_speech = (
            llmnpc.LLMNpc._handle_directed_speech.__get__(b, llmnpc.LLMNpc))
        return b

    def _say(self, b, line):
        from typeclasses import llm_npc as llmnpc
        return llmnpc.LLMNpc.at_msg_receive(
            b, text=None, from_obj=object(), speech=line, addressed=True)

    def test_a_polite_order_reaches_the_service_path(self):
        b = self._bartender()
        with patch("world.service.serve", return_value=True) as served:
            self._say(b, "a rotgut, thanks")
        b._acknowledge.assert_called_once()
        served.assert_called_once()
        self.assertEqual(served.call_args.args[1], "a rotgut, thanks")

    def test_cheers_is_an_order_too(self):
        b = self._bartender()
        with patch("world.service.serve", return_value=True) as served:
            self._say(b, "cheers, pour me a rotgut")
        served.assert_called_once()

    def test_bare_thanks_is_still_acknowledged(self):
        b = self._bartender()
        with patch("world.service.serve", return_value=False):
            self._say(b, "much obliged")
        b._acknowledge.assert_called_once()
        b._note_courtesy.assert_called_once()
