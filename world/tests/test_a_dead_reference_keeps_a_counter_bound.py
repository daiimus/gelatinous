"""A counter whose person was deleted stays bound, and so closed (#3573).

A counter is either BOUND -- the job system (shift slots, a posted
keeper) or a hand-set owner/staff allowlist decides who works it -- or
UNBOUND, the vending tier where whoever is standing there serves. Five
places asked that question inline, and every one read a DELETED keeper,
owner or staff member back as None, i.e. "never assigned". So a counter
whose person was gone fell to the vending tier: anyone present could
work it and empty the till, the #2921 regression. A dead staff entry
failed the other way, `[None]` counting as "has staff".

Now there is one question, `world.souls.posts.is_bound`, and a reference
that was ever set keeps the counter bound whether or not that person
still exists. Real objects throughout: the dead-reference case only
exists for a real Attribute row.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.bar import tender_at
from world.service import post_for
from world.souls.actions import _counter_open
from world.souls.posts import is_bound


class _Counter(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.bar = create_object("typeclasses.bar.BarCounter", key="test bar",
                                 location=self.room1)
        self.bar.db.post_role = "bartender"
        self.stranger = self.char2             # a plain player, not staff
        self.stranger.location = self.room1

    def _npc(self, key):
        return create_object("typeclasses.characters.Character", key=key,
                             location=self.room1)


class TheControlIsTheVendingTier(_Counter):

    def test_a_fresh_counter_is_unbound_and_anyone_serves(self):
        self.assertFalse(is_bound(self.bar))
        self.assertTrue(self.bar.is_bartender(self.stranger))
        self.assertTrue(_counter_open(self.bar))
        self.assertIs(post_for(self.stranger), self.bar)


class ADeadOwnerKeepsItClosed(_Counter):

    def test_live_owner_works_it_and_a_stranger_does_not(self):
        owner = self._npc("Nonna")
        self.bar.db.owner = owner
        self.assertTrue(is_bound(self.bar))
        self.assertTrue(self.bar.is_bartender(owner))
        self.assertFalse(self.bar.is_bartender(self.stranger))

    def test_once_the_owner_is_deleted_the_till_stays_shut(self):
        owner = self._npc("Nonna")
        self.bar.db.owner = owner
        owner.delete()
        self.assertIsNone(self.bar.db.owner, "fixture: the reference should read back None")
        self.assertTrue(is_bound(self.bar), "a deleted owner unbound the counter")
        self.assertFalse(self.bar.is_bartender(self.stranger),
                         "anyone present can now work the bar and empty its till")


class ADeadStaffEntry(_Counter):

    def test_does_not_open_the_counter(self):
        hand = self._npc("barback")
        self.bar.db.staff = [hand]
        hand.delete()
        self.assertTrue(is_bound(self.bar))
        self.assertFalse(self.bar.is_bartender(self.stranger))

    def test_does_not_lock_out_the_living_staff(self):
        gone, still = self._npc("gone"), self._npc("still here")
        self.bar.db.staff = [gone, still]
        gone.delete()
        self.assertTrue(self.bar.is_bartender(still))


class ADeadLegacyKeeper(_Counter):
    """A counter bound only by the single-keeper field, no shift slots,
    whose keeper was deleted -- the case the five copies disagreed on."""

    def setUp(self):
        super().setUp()
        keeper = self._npc("Del")
        self.bar.db.post_keeper = keeper
        keeper.delete()

    def test_it_is_still_bound(self):
        self.assertTrue(is_bound(self.bar))

    def test_every_gate_reads_closed(self):
        self.assertFalse(self.bar.is_bartender(self.stranger))
        self.assertFalse(_counter_open(self.bar))
        self.assertIsNone(post_for(self.stranger))

    def test_no_bystander_npc_is_pressed_into_serving(self):
        # tender_at used to test post_slots alone and fell through to
        # "any NPC in the room" for this counter.
        bystander = self._npc("bystander")
        bystander.db.is_npc = True
        self.assertIsNone(tender_at(self.bar))

    def test_a_shop_counter_asks_the_same_question(self):
        shop = create_object("typeclasses.shopkeeper.ShopContainer", key="test shop",
                             location=self.room1)
        keeper = self._npc("Otto")
        shop.db.post_keeper = keeper
        keeper.delete()
        self.assertTrue(is_bound(shop))
