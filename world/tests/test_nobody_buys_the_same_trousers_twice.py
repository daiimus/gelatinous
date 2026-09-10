"""A soul stops shopping for a gap it already owns a garment for
(#3169).

`#6106 Sam Fukuda` was carrying 628 unworn pairs of trousers — 438
`blue jeans`, 190 `cargo trousers` — spanning object ids 9811 to 16850
against a world maximum of 16864. One more arrived every planning cycle.

His blueprint gives him layer-5 rubber waders that stop at the thigh, so
`groin` stayed bare and `wardrobe_pressure` sat at 1.0 permanently. Then:

1. `_wearable` asks `can_wear_now`, which correctly refuses a layer-1
   garment going UNDER the worn layer-5 waders (#2337).
2. So `carried` is empty and the plan falls through to the shop branch,
   which scores wares by how much of `_uncovered` they close. Trousers
   close `groin`. It buys.
3. The `wear` step then finds nothing wearable — the new pair is
   refused for the same reason as the other 627 — and faults.
4. The trousers stay in inventory. Next cycle, back to 1.

The planner learned not to PICK an unwearable garment and never learned
not to BUY one. Two fixes, because either alone leaves the body stuck:
the shop branch stops buying a gap it already owns, and the wear step
takes the blocking outer layer off, puts the under layer on, and puts
the outer back — which is what `_shed_the_issue` already did for the
paper decant issue alone.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.souls import jobs as jobs_mod

#: Bound with a do-nothing fallback rather than imported by name: a
#: missing import makes this file fail to LOAD against the unfixed tree,
#: and a test that never runs is not a control. The fallback answers
#: "nothing was moved aside", which is exactly what the unfixed tree
#: does, so the assertions below fail there for the right reason.
_make_room_for = getattr(jobs_mod, "_make_room_for",
                         lambda soul, garment: False)


def _garment(where, key, coverage, layer):
    item = create_object("typeclasses.items.Item", key=key, location=where)
    item.attributes.add("coverage", list(coverage))
    item.attributes.add("layer", layer)
    item.attributes.add("worn_desc", f"{key} worn")
    return item


class _Waders(EvenniaTest):
    """Sam's exact shape: an outer layer that stops short of the gap."""

    def setUp(self):
        super().setUp()
        self.who = create_object("typeclasses.characters.Character",
                                 key="Sammy", location=self.room1)
        self.waders = _garment(self.who, "rubber waders",
                               ("left_thigh", "right_thigh", "left_shin",
                                "right_shin", "left_foot", "right_foot"), 5)
        self.shirt = _garment(self.who, "thermal shirt",
                              ("chest", "back", "abdomen"), 1)
        for g in (self.shirt, self.waders):
            self.who.wear_item(g)
        self.jeans = _garment(self.who, "blue jeans",
                              ("groin", "left_thigh", "right_thigh"), 1)


class TestTheFixtureReproducesTheTrap(_Waders):

    def test_the_outer_layer_is_on(self):
        """Control: without the waders worn there is nothing blocking
        and every assertion below would pass trivially."""
        self.assertTrue(self.who.is_item_worn(self.waders))

    def test_the_gap_is_real(self):
        self.assertFalse(self.who.is_location_covered("groin"))

    def test_and_the_jeans_will_not_go_on(self):
        """The refusal the planner reads as 'owns nothing'."""
        self.assertFalse(self.who.can_wear_now(self.jeans))


class TestTheBlockingLayerIsMovedAside(_Waders):

    def test_the_jeans_end_up_on(self):
        self.assertTrue(_make_room_for(self.who, self.jeans))
        self.assertTrue(self.who.is_item_worn(self.jeans))

    def test_and_the_waders_go_back(self):
        """A failed OR successful attempt must not leave the body barer
        than it found it."""
        _make_room_for(self.who, self.jeans)
        self.assertTrue(self.who.is_item_worn(self.waders))

    def test_the_gap_closes(self):
        _make_room_for(self.who, self.jeans)
        self.assertTrue(self.who.is_location_covered("groin"))

    def test_it_declines_when_nothing_is_blocking(self):
        """Control: it must not strip a body for a garment that is
        being refused for some OTHER reason."""
        hat = _garment(self.who, "wool cap", ("head",), 1)
        self.assertFalse(_make_room_for(self.who, hat))
        self.assertTrue(self.who.is_item_worn(self.waders))

    def test_it_puts_everything_back_when_the_wear_still_fails(self):
        """One patched call only. A second would find the waders
        already off — the mock swallows the re-wear as well — so
        `blocking` would be empty and the count would read zero for a
        reason that has nothing to do with the behaviour."""
        from unittest.mock import patch
        with patch.object(type(self.who), "wear_item",
                          return_value=(False, "no")) as worn:
            self.assertFalse(_make_room_for(self.who, self.jeans))
            offered = [c.args[0] for c in worn.call_args_list]
        self.assertIn(self.jeans, offered)
        self.assertIn(self.waders, offered,
                      "the blocking garment was never offered back")


class TestTheShopDoesNotSellYouAnotherOne(EvenniaTest):
    """The leak half, driven through `plan_for` itself.

    An earlier version of this class re-implemented the shop branch's
    filter and asserted against the copy, which would have passed with
    the fix reverted. The seams are patched instead — the advertiser,
    the counter, the stock and the prototype coverage — so the code
    under test is the real one.
    """

    def setUp(self):
        super().setUp()
        self.who = create_object("typeclasses.characters.Character",
                                 key="Sammy", location=self.room1)
        # Sam's exact shape, or the test measures nothing: an OUTER
        # layer over the legs that stops short of the groin. Without
        # the waders the carried jeans go straight on, the planner
        # takes its `carried` branch, and no shop is ever consulted —
        # which passes against the unfixed tree too.
        top = _garment(self.who, "thermal shirt", ("chest", "back"), 1)
        waders = _garment(self.who, "rubber waders",
                          ("left_thigh", "right_thigh", "left_shin",
                           "right_shin", "left_foot", "right_foot"), 5)
        for g in (top, waders):
            self.who.wear_item(g)
        self.who.tokens = 500
        self.rail = create_object("typeclasses.items.Item",
                                  key="the free rail", location=self.room1)
        self.rail.db.prototype_inventory = {"CARGO_TROUSERS": 0}

    def plan(self):
        from unittest.mock import patch
        from world.souls import actions
        with patch.object(actions, "_advertisers",
                          return_value=[(1.0, self.rail, self.room1)]), \
             patch.object(actions, "_counter_open", return_value=True), \
             patch.object(actions, "_in_stock", return_value=True), \
             patch.object(actions, "_proto_coverage",
                          return_value={"groin", "left_thigh",
                                        "right_thigh"}), \
             patch.object(actions, "_is_provisional_proto",
                          return_value=False), \
             patch.object(actions, "_proto_affinity", return_value=0.0):
            return actions.plan_for(self.who, "wardrobe")

    def test_an_empty_handed_soul_still_shops(self):
        """Control: the filter must not stop everyone shopping, and it
        proves the whole fixture reaches the shop branch at all."""
        plan = self.plan()
        self.assertIsNotNone(plan, "the fixture never reached the shop")
        self.assertIn("buy", [s["do"] for s in plan["steps"]])

    def test_a_soul_already_carrying_trousers_does_not(self):
        _garment(self.who, "blue jeans",
                 ("groin", "left_thigh", "right_thigh"), 1)
        plan = self.plan()
        if plan is not None:
            self.assertNotIn(
                "buy", [s["do"] for s in plan["steps"]],
                "bought a 629th pair of trousers it cannot wear")

    def test_a_soul_carrying_something_irrelevant_still_shops(self):
        """Owning a HAT does not close a groin-shaped gap."""
        _garment(self.who, "wool cap", ("head",), 1)
        plan = self.plan()
        self.assertIsNotNone(plan)
        self.assertIn("buy", [s["do"] for s in plan["steps"]])
