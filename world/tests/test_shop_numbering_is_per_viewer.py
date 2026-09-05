"""`buy 002` must mean what YOUR screen said (#2470).

`get_browse_display(viewer)` built a number->prototype map and stored it
on the CONTAINER (`self.ndb.item_number_map`), not on the viewer -- the
`viewer` argument was accepted and never used. `_find_prototype_key`
then read that one shared map for whoever typed `buy <number>`.

In limited-inventory mode the listing SKIPS out-of-stock entries and
numbers what remains sequentially, so the mapping shifts whenever stock
changes:

    A looks:  [001] stew  [002] chops  [003] skewers
    the last stew is bought, and drops out of the listing
    B looks:  [001] chops [002] skewers      <- container map rewritten
    A types `buy 002` expecting chops, and is handed skewers

`return_appearance` calls `get_browse_display` too, so ANY look at the
shop rewrites the shared map -- not only an explicit browse.

The issue that reported this flagged the scenario as inferred and asked
for it to be reproduced before fixing, since if numbering were stable
across stock changes the impact would be nil. It is not stable:
`TestTheSharedMapHandsOverTheWrongItem` below fails against the unfixed
module, which is the reproduction.

Two live shops are in limited-inventory mode and so are exposed: the
steel counter (16 lines) and the hull-plate food cart (5).
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.shop import CmdBuy


def _proto(key, name):
    return {
        "prototype_key": key,
        "key": name,
        "typeclass": "typeclasses.items.Item",
    }


class _ShopCase(EvenniaTest):
    """A cart with three lines, one of which will sell out."""

    def setUp(self):
        super().setUp()
        from evennia.prototypes.prototypes import save_prototype

        self.protos = {
            "test_stew": "rat tail stew",
            "test_chops": "grilled chops",
            "test_skewers": "skewers",
        }
        for key, name in self.protos.items():
            save_prototype(_proto(key, name))

        self.shop = create_object("typeclasses.shopkeeper.ShopContainer",
                                  key="a hull-plate food cart",
                                  location=self.room1)
        self.shop.db.is_infinite = False
        self.shop.db.prototype_inventory = {
            "test_stew": 10, "test_chops": 20, "test_skewers": 30,
        }
        self.shop.db.item_inventory = {
            "test_stew": 1, "test_chops": 5, "test_skewers": 5,
        }
        self.alice = self.char1
        self.bob = self.char2
        for c in (self.alice, self.bob):
            c.location = self.room1

    def look(self, who):
        return self.shop.get_browse_display(who)

    def resolve(self, who, typed):
        """What `buy <typed>` would hand *who*."""
        cmd = CmdBuy()
        cmd.caller = who
        return cmd._find_prototype_key(self.shop, typed)

    def sell_out(self, key):
        stock = dict(self.shop.db.item_inventory)
        stock[key] = 0
        self.shop.db.item_inventory = stock


class TestNumberingIsStableForOneViewer(_ShopCase):
    def test_the_listing_numbers_from_one(self):
        out = self.look(self.alice)
        self.assertIn("[001]", out)
        self.assertIn("[003]", out)

    def test_a_number_buys_what_it_says(self):
        self.look(self.alice)
        self.assertEqual(self.resolve(self.alice, "002"), "test_chops")

    def test_the_hash_and_bare_forms_agree(self):
        self.look(self.alice)
        self.assertEqual(self.resolve(self.alice, "#2"),
                         self.resolve(self.alice, "2"))


class TestTheSharedMapHandsOverTheWrongItem(_ShopCase):
    """The reproduction the issue asked for."""

    def test_another_viewer_does_not_move_your_numbers(self):
        self.look(self.alice)              # 001 stew, 002 chops, 003 skewers
        self.sell_out("test_stew")
        self.look(self.bob)                # 001 chops, 002 skewers
        self.assertEqual(self.resolve(self.alice, "002"), "test_chops")

    def test_a_plain_look_moves_them_too(self):
        """`return_appearance` browses, so any look rewrites the map --
        Bob does not have to be shopping."""
        self.look(self.alice)
        self.sell_out("test_stew")
        self.shop.return_appearance(self.bob)
        self.assertEqual(self.resolve(self.alice, "002"), "test_chops")

    def test_bobs_own_numbers_are_right_for_bob(self):
        self.look(self.alice)
        self.sell_out("test_stew")
        self.look(self.bob)
        self.assertEqual(self.resolve(self.bob, "002"), "test_skewers")

    def test_the_two_of_them_disagree_on_purpose(self):
        """After the stock change the same typed number legitimately
        means different things to each of them."""
        self.look(self.alice)
        self.sell_out("test_stew")
        self.look(self.bob)
        self.assertNotEqual(self.resolve(self.alice, "002"),
                            self.resolve(self.bob, "002"))


class TestBuyingWithoutLookingFirst(_ShopCase):
    def test_a_number_nobody_has_seen_falls_through(self):
        """No map for this viewer: the number must not silently resolve
        against somebody else's listing."""
        self.look(self.bob)
        self.assertIsNone(self.resolve(self.alice, "002"))

    def test_a_name_still_works_without_a_listing(self):
        self.assertEqual(self.resolve(self.alice, "test_chops"),
                         "test_chops")

    def test_a_map_from_another_shop_is_not_used(self):
        """The map has to belong to the container being bought from."""
        other = create_object("typeclasses.shopkeeper.ShopContainer",
                              key="another cart", location=self.room1)
        other.db.is_infinite = False
        other.db.prototype_inventory = {"test_skewers": 30}
        other.db.item_inventory = {"test_skewers": 5}
        other.get_browse_display(self.alice)
        self.assertIsNone(self.resolve(self.alice, "001"))
