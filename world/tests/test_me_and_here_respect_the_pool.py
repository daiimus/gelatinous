"""`me`, `self` and `here` answer only where the caller or the room can be found.

`Character.search` short-circuited the magic keywords before it looked at
anything else, so they answered EVERY search, including one a command had
scoped to a pool. `caller.search("me", candidates=held_items)` returned the
caller. A command that asked "which of the things in my hand did they
mean?" got a person back: `rig me to north`, `catch me`, `throw me`.

Evennia's own rule (`DefaultObject.get_search_direct_match`) is that the
tokens resolve when the search is global or the pool holds the caller or the
room. The ordinary local search always does, so nothing a player types at
`look me` or `medical me` changes. A scoped search now gets Evennia's rule.

This is the root of the per-command guards the #3783 census kept proposing:
one fix in the core matcher instead of a membership filter at forty sites.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestMagicKeywordsRespectThePool(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.knife = create_object("typeclasses.items.Item", key="knife",
                                   location=self.char1)
        self.rock = create_object("typeclasses.items.Item", key="rock",
                                  location=self.room1)

    # -- the ordinary local search: unchanged ---------------------------
    def test_me_and_self_are_the_caller_in_an_ordinary_search(self):
        self.assertIs(self.char1.search("me"), self.char1)
        self.assertIs(self.char1.search("self"), self.char1)
        self.assertEqual(self.char1.search("ME", quiet=True), [self.char1])

    def test_here_is_the_room_in_an_ordinary_search(self):
        self.assertIs(self.char1.search("here"), self.room1)
        self.assertEqual(self.char1.search("here", quiet=True), [self.room1])

    # -- a pool that holds neither: the tokens are just words ------------
    def test_me_is_not_in_my_hands(self):
        """The control: this returned [char1] before the fix."""
        found = self.char1.search("me", candidates=[self.knife], quiet=True)
        self.assertEqual(list(found), [])

    def test_self_and_here_are_not_in_my_hands(self):
        self.assertEqual(
            list(self.char1.search("self", candidates=[self.knife], quiet=True)), [])
        self.assertEqual(
            list(self.char1.search("here", candidates=[self.knife], quiet=True)), [])

    def test_me_is_not_in_my_inventory(self):
        found = self.char1.search("me", location=self.char1, quiet=True)
        self.assertNotIn(self.char1, list(found))

    def test_an_empty_pool_finds_nobody(self):
        self.assertEqual(list(self.char1.search("me", candidates=[], quiet=True)), [])
        self.assertEqual(list(self.char1.search("here", candidates=[], quiet=True)), [])

    def test_me_does_not_turn_into_a_partial_name(self):
        """`drop me` must not drop the medkit. When the pool does not hold
        the caller, Evennia goes on to look for the CALLER in that pool,
        not for a name beginning with "me", so the answer is nothing."""
        medkit = create_object("typeclasses.items.Item", key="medkit",
                               location=self.char1)
        found = self.char1.search("me", candidates=[self.knife, medkit], quiet=True)
        self.assertEqual(list(found), [])

    # -- a pool that DOES hold the caller or the room: Evennia's rule ----
    def test_me_resolves_when_the_pool_holds_the_caller(self):
        found = self.char1.search("me", candidates=[self.char1, self.rock], quiet=True)
        self.assertEqual(list(found), [self.char1])

    def test_me_resolves_in_the_room_s_contents(self):
        found = self.char1.search("me", location=self.room1, quiet=True)
        self.assertEqual(list(found), [self.char1])

    def test_here_resolves_when_the_pool_holds_the_room(self):
        found = self.char1.search("here", candidates=[self.room1, self.rock], quiet=True)
        self.assertEqual(list(found), [self.room1])

    def test_a_global_search_still_answers_the_tokens(self):
        self.assertEqual(
            list(self.char1.search("me", global_search=True, quiet=True)), [self.char1])
