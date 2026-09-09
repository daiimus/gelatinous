"""A keeper who handed it over is not told it went off the shelf.

`buy` has two paths. A manned counter routes through the keeper, who
emotes the hand-over via `shop.service.hand_over` -- "presses it into
the lean man's hand ... sweeps 15 into the till". An unmanned shelf is
self-service, and `_notify_merchant` exists to tell a merchant standing
nearby that a sale happened without them.

Both paths called `_notify_merchant`, so a keeper who had just put the
item into the buyer's hands was immediately also told:

    "<buyer> bought <item> off the shelf for <price>."

For an LLM keeper that does not merely print -- it goes through
`_observe_action` into the buffer their next turn reads. All four live
merchant keepers are `llm_driven=True` with an observation buffer
(Bellows, Ezra Vantomme, Auntie Lin, Nonna Escallier), so every manned
sale wrote a contradiction into the NPC's own memory: they served it by
hand, and remember it going off the shelf while they stood there.

A manned sale is not a self-service sale, so it does not get the
self-service line at all.

ALSO NOTED, NOT FIXED: `_notify_merchant` still scans the room for
`is_merchant`, while `_find_keeper` was converted to the post-based
`keeper_on_duty` in the same commit (#2352) precisely because a
generated successor is a plain `LLMNpc` and carries no `is_merchant`.
The two doors disagree. Measured today the gap is EMPTY -- all four
shelf posts have keepers that do carry the flag -- so it is latent
rather than live, and it opens the first time succession installs a
generated keeper. Recorded on the issue rather than changed blind.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.shop import CmdBuy


class TestTheServerIsNotToldItWasSelfService(EvenniaCommandTest):
    """Drives the real `buy` command.

    An earlier version called `_notify_merchant` directly with a
    `served_by` argument the fix had not added yet, so every case raised
    TypeError -- an ERROR, which proves nothing about the assertion. The
    defect is in WHICH PATH calls the notifier, so the test has to go
    through the command.
    """

    def setUp(self):
        super().setUp()
        self.counter = create_object("typeclasses.shopkeeper.ShopContainer",
                                     key="counter", location=self.room1)
        self.counter.db.prototype_inventory = {"SHIV": 5}
        self.counter.db.item_inventory = {"SHIV": 3}
        self.counter.db.is_infinite = False

        self.keeper = create_object("typeclasses.llm_npc.LLMNpc",
                                    key="Testkeeper", location=self.room1)
        self.keeper.db.llm_driven = True

        self.char1.location = self.room1
        self.char1.tokens = 500

        self.observed = []
        self.keeper._observe_action = lambda who, line: self.observed.append(line)

    def _buy(self, manned=True):
        keeper = self.keeper if manned else None
        with patch("world.souls.posts.keeper_on_duty", return_value=keeper):
            self.call(CmdBuy(), "shiv from counter")

    def test_an_unmanned_sale_still_tells_a_merchant_present(self):
        """The control. Without it the fix could be "never notify
        anybody", which would delete the feature instead of fixing it."""
        self.keeper.is_merchant = True
        self._buy(manned=False)
        self.assertTrue(any("off the shelf" in l for l in self.observed),
                        f"a self-service sale told nobody: {self.observed}")

    def test_the_keeper_who_served_is_not_told_it_went_off_the_shelf(self):
        self.keeper.is_merchant = True
        self._buy(manned=True)
        self.assertFalse(
            any("off the shelf" in l for l in self.observed),
            f"the keeper who handed it over was told it went off the "
            f"shelf: {self.observed}")
