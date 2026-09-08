"""A stashed item needs finding before it can be taken (#2476).

`stash` drops the item into the room, flags `db.hidden`, and freezes the
hider's craft into `db.stash_roll` — the difficulty a searcher has to
beat:

```python
item.db.hidden = True
item.db.stash_roll = randint(1, 20) + int(getattr(caller, "motorics", 1))
```

`active_search` is the counter, and it is the ONLY consumer of that
number. `get` consulted neither flag: `_find_item_in_room` searched raw
`location.contents`, and `_can_be_taken` checks only the `get` lock and
`at_pre_get`. So anyone who could name the item lifted the contraband
with no roll at all — the whole mechanic bypassed by typing the item's
name.

The room already refuses to *render* a hidden object (`rooms.py:528`,
`:696`), so the two halves of the game disagreed: the room said nothing
was there and `get` handed it over.

Filtered in the candidate pool rather than refused at the gate, so the
answer is the same *"You don't see a 'X' here."* the room already gives.
A refusal that named the item would confirm it was there, which is the
thing being hidden.

**And the flag outlived the hiding place.** `active_search` clears
`hidden` for everyone when the roll lands, but nothing ever cleared
`stash_roll` — so a found item carried the original hider's difficulty
around, and dropping it somewhere else re-armed a hiding place nobody
worked for. Both are cleared on the way into a hand.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdInventory import CmdGet
from commands.CmdStealth import CmdHide


class _StashCase(EvenniaCommandTest):
    def contraband(self, key="a wrapped brick"):
        item = create_object("typeclasses.items.Item", key=key,
                             location=self.char1)
        return item

    def stash(self, item):
        self.call(CmdHide(), item.key.split()[-1], caller=self.char1)
        return item

    def held(self):
        return [i for i in self.char1.hands.values() if i]


class TestStashActuallyHides(_StashCase):
    def test_the_stash_sets_the_flag_and_the_roll(self):
        item = self.stash(self.contraband())
        self.assertIs(item.db.hidden, True)
        self.assertTrue(item.db.stash_roll)

    def test_it_is_in_the_room(self):
        item = self.stash(self.contraband())
        self.assertEqual(item.location, self.room1)


class TestYouCannotJustPickItUp(_StashCase):
    def test_get_does_not_find_it(self):
        item = self.stash(self.contraband())
        self.call(CmdGet(), "brick", caller=self.char1)
        self.assertEqual(item.location, self.room1)

    def test_it_answers_the_way_the_room_does(self):
        self.stash(self.contraband())
        out = self.call(CmdGet(), "brick", caller=self.char1)
        self.assertIn("don't see", out)

    def test_the_refusal_does_not_confirm_the_item_is_there(self):
        """A message naming the item would give away the stash."""
        self.stash(self.contraband())
        out = self.call(CmdGet(), "brick", caller=self.char1)
        self.assertNotIn("hidden", out.lower())
        self.assertNotIn("stash", out.lower())

    def test_an_ordinary_item_is_still_takeable(self):
        item = create_object("typeclasses.items.Item", key="a crowbar",
                             location=self.room1)
        self.call(CmdGet(), "crowbar", caller=self.char1)
        self.assertEqual(item.location, self.char1)


class TestFindingItFirstWorks(_StashCase):
    def test_a_successful_search_makes_it_takeable(self):
        from unittest import mock
        item = self.stash(self.contraband())
        with mock.patch("world.stealth.randint", return_value=20):
            from world.stealth import active_search
            _chars, objs = active_search(self.char1, self.room1)
        self.assertIn(item, objs)
        self.call(CmdGet(), "brick", caller=self.char1)
        self.assertEqual(item.location, self.char1)

    def test_a_failed_search_leaves_it_hidden(self):
        from unittest import mock
        item = self.stash(self.contraband())
        item.db.stash_roll = 999
        with mock.patch("world.stealth.randint", return_value=1):
            from world.stealth import active_search
            active_search(self.char1, self.room1)
        self.assertIs(item.db.hidden, True)
        self.call(CmdGet(), "brick", caller=self.char1)
        self.assertEqual(item.location, self.room1)


class TestAFoundItemStopsBeingAStash(_StashCase):
    def found_and_taken(self):
        item = self.stash(self.contraband())
        item.db.hidden = False          # what a successful search leaves
        self.call(CmdGet(), "brick", caller=self.char1)
        return item

    def test_the_hidden_flag_is_gone(self):
        item = self.found_and_taken()
        self.assertFalse(item.db.hidden)

    def test_the_hiders_difficulty_does_not_travel_with_it(self):
        """Otherwise dropping it elsewhere re-arms a hiding place
        nobody worked for."""
        item = self.found_and_taken()
        self.assertIsNone(item.db.stash_roll)

    def test_it_really_is_in_hand(self):
        item = self.found_and_taken()
        self.assertEqual(item.location, self.char1)

    def test_stashing_it_again_rolls_fresh(self):
        item = self.found_and_taken()
        self.call(CmdHide(), "brick", caller=self.char1)
        self.assertIs(item.db.hidden, True)
        self.assertTrue(item.db.stash_roll)
