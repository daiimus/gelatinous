"""Making conversation does not buy you a drink (#2735).

Measured against a three-item shelf before the fix:

    "can I get your name?"                 ->  CAN_OF_LAGER
    "can you tell me where the water is"   ->  ambiguous
    "get out of my way"                    ->  ambiguous
    "can I get a lager"                    ->  CAN_OF_LAGER   (correct)

Three causes, and the first is the one that makes the headline case so
hard to see:

1. ONE WORD DID TWO JOBS. `can i get` is a registered order cue, and
   `can` is the first word of "a can of lager". The same word satisfied
   the cue AND the item match. Stripping the cue before scoring fixes
   it: a word spent being the cue cannot also be the item.

2. STOPWORDS WERE ORDER TERMS. "a can of lager" contributed `of` to its
   own word-set, so "get out of my way" -- no cue at all -- scored
   against every item on the shelf.

3. AMBIGUITY WAS DECIDED BEFORE ORDER-SHAPE. "can you tell me where the
   water is" tied `water` against `can` and returned "ambiguous", so the
   keeper asked which one you wanted -- to a question that was not an
   order. The order-shape gate now runs first.

Same class as #2689 (ordinary remarks served as drink orders): matching
intent on bare word overlap, with no stopword filtering and no floor.
"""
from evennia.utils.test_resources import EvenniaTest

from world.shop.service import match_from_shelf

SHELF = [
    ("CAN_OF_LAGER", "a can of lager", {"can", "of", "lager"}),
    ("PACK_OF_SMOKES", "a pack of smokes", {"pack", "of", "smokes"}),
    ("BOTTLE_OF_WATER", "a bottle of water", {"bottle", "of", "water"}),
]


class TestRealOrdersStillWork(EvenniaTest):
    """Controls first. A matcher that refuses everything would pass every
    assertion in the class below."""

    def test_a_cued_order_sells(self):
        self.assertEqual(match_from_shelf(SHELF, "can I get a lager"),
                         "CAN_OF_LAGER")

    def test_a_bare_order_sells(self):
        self.assertEqual(match_from_shelf(SHELF, "lager"), "CAN_OF_LAGER")

    def test_another_item_sells_too(self):
        self.assertEqual(match_from_shelf(SHELF, "gimme a pack of smokes"),
                         "PACK_OF_SMOKES")

    def test_a_genuine_tie_still_asks(self):
        """Ambiguity is a feature when the line really is an order."""
        shelf = SHELF + [("LAGER_BOTTLE", "a bottle of lager",
                          {"bottle", "of", "lager"})]
        self.assertEqual(match_from_shelf(shelf, "can I get a lager"),
                         "ambiguous")


class TestConversationIsNotAnOrder(EvenniaTest):

    def test_asking_their_name_buys_nothing(self):
        self.assertIsNone(match_from_shelf(SHELF, "can I get your name?"))

    def test_asking_where_something_is_buys_nothing(self):
        self.assertIsNone(
            match_from_shelf(SHELF, "can you tell me where the water is"))

    def test_telling_someone_to_move_buys_nothing(self):
        self.assertIsNone(match_from_shelf(SHELF, "get out of my way"))

    def test_asking_for_a_word_buys_nothing(self):
        self.assertIsNone(match_from_shelf(SHELF, "can I have a word?"))

    def test_a_cueless_question_is_still_conversation(self):
        """The guard that already worked, pinned."""
        self.assertIsNone(match_from_shelf(SHELF, "is the water clean?"))
