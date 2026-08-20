"""The craving loop (#2076): a derived pressure over the addiction
machinery both populations already carry, acted on through the same
verbs and limitations players have.

Pins: the derived craving state (overdue habit / pre-habit misery
pull), the real-drink reset (apply_substance -> record_dose, never an
engine-side satisfy), and the planner's vice run.
"""
import time as _time
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest


class _CravingTestBase(BaseEvenniaTest):
    """Game typeclasses throughout — apply_substance needs a medical
    body and the drink verb lives on the game cmdset (the harness
    resets both to core defaults)."""

    def setUp(self):
        super().setUp()
        # the harness also resets PROTOTYPE_MODULES — reload the game's
        # module prototypes so the planner's ware inspection sees them
        from evennia.prototypes import prototypes as protomod
        if not protomod.search_prototype("doubleshift_lager"):
            protomod.load_module_prototypes("world.prototypes")
        self.game_room = create_object(
            "typeclasses.rooms.Room", key="back room")

    def _soul_char(self, key="TestSoul"):
        char = create_object(
            "typeclasses.characters.Character", key=key,
            location=self.game_room)
        char.cmdset.add(
            "commands.default_cmdsets.CharacterCmdSet", persistent=False)
        char.tags.add("soul", category="npc_role")
        char.db.soul_needs = {"hunger": 0.1, "_at": _time.time()}
        return char

    def _addict(self, char, substance="alcohol", craving_after=3600,
                overdue=3600):
        from world.medical.conditions import AddictionCondition
        cond = AddictionCondition(substance, craving_after=craving_after)
        cond.last_dose_time = _time.time() - craving_after - overdue
        char.medical_state.add_condition(cond)
        return cond


class TestCravingState(_CravingTestBase):
    def test_overdue_addiction_registers(self):
        from world.souls import needs

        soul = self._soul_char()
        self._addict(soul, overdue=3600)       # a full craving_after over
        p, sub = needs.craving_state(soul)
        self.assertGreaterEqual(p, needs.SOFT)
        self.assertEqual(sub, "alcohol")

    def test_fed_habit_is_quiet(self):
        from world.souls import needs

        soul = self._soul_char()
        cond = self._addict(soul)
        cond.record_dose()                     # just dosed
        p, sub = needs.craving_state(soul)
        self.assertEqual((p, sub), (0.0, None))

    def test_misery_reaches_for_the_bottle(self):
        """No habit yet: a grim mood applies the pre-habit pull with
        no target substance — the planner reads that as 'a drink'."""
        from world.souls import needs

        soul = self._soul_char()
        with patch("world.souls.thoughts.mood", return_value=-0.5):
            p, sub = needs.craving_state(soul)
        self.assertEqual((p, sub), (needs.MISERY_PULL, None))
        with patch("world.souls.thoughts.mood", return_value=0.1):
            p, sub = needs.craving_state(soul)
        self.assertEqual(p, 0.0)

    def test_real_drink_resets_the_clock(self):
        """The player-visible path: drinking a ware that carries the
        substance resets the craving through apply_substance's own
        record_dose — no engine-side satisfaction anywhere."""
        from world.souls import needs

        soul = self._soul_char()
        self._addict(soul, overdue=3600)
        self.assertGreaterEqual(needs.craving_pressure(soul), needs.SOFT)
        lager = create_object(
            "typeclasses.items.Item", key="can of lager", location=soul)
        lager.tags.add("drink", category="delivery_method")
        lager.db.drink_effects = {"alcohol": 1}
        lager.db.uses_left = 1
        soul.execute_cmd("drink lager")
        self.assertEqual(needs.craving_pressure(soul), 0.0)


class TestVicePlan(_CravingTestBase):
    def _vice_counter(self, inventory):
        counter = create_object(
            "typeclasses.items.Item", key="vice counter",
            location=self.game_room)
        counter.db.prototype_inventory = dict(inventory)
        counter.db.advertises = {"vice": 0.9}
        counter.tags.add("advertiser", category="souls")
        from world.souls import actions
        actions._ad_cache["at"] = 0.0          # bust the registry cache
        return counter

    def test_planner_buys_cheapest_matching_ware(self):
        from world.souls import actions

        soul = self._soul_char()
        soul.tokens = 20
        self._addict(soul, overdue=3600)
        counter = self._vice_counter(
            {"doubleshift_lager": 3, "old_meridian_whiskey": 25,
             "cigarette_pack_neutral": 4})     # smoke-only: no lighter
        plan = actions.plan_for(soul, "craving")
        self.assertIsNotNone(plan)
        does = [s["do"] for s in plan["steps"]]
        self.assertEqual(does, ["travel", "buy", "consume"])
        self.assertEqual(plan["steps"][1]["proto"], "doubleshift_lager")
        self.assertEqual(plan["steps"][2]["verb"], "drink")

    def test_broke_lawful_soul_just_aches(self):
        from world.souls import actions

        soul = self._soul_char()
        soul.tokens = 0
        self._addict(soul, overdue=3600)
        self._vice_counter({"doubleshift_lager": 3})
        self.assertIsNone(actions.plan_for(soul, "craving"))

    def test_tobacco_family_matches_across_brands(self):
        """A noir-tobacco addict accepts the neutral-leaf chewing plug
        — the addiction is to the leaf, not the brand."""
        from world.souls import actions

        soul = self._soul_char()
        soul.tokens = 20
        self._addict(soul, substance="tobacco_noir", overdue=3600)
        self._vice_counter({"chewing_tobacco_plug": 3})
        plan = actions.plan_for(soul, "craving")
        self.assertIsNotNone(plan)
        self.assertEqual(plan["steps"][1]["proto"], "chewing_tobacco_plug")
        self.assertEqual(plan["steps"][2]["verb"], "eat")


class TestStockAwareness(_CravingTestBase):
    """#2090: limited-inventory shops (the butcher's cart) only offer
    what was actually stocked — the planner never walks a soul to an
    empty shelf."""

    def _hunger_counter(self, infinite, stock):
        counter = create_object(
            "typeclasses.items.Item", key="stock counter",
            location=self.game_room)
        counter.db.prototype_inventory = {"mystery_skewer": 3}
        counter.db.advertises = {"hunger": 0.9}
        counter.db.is_infinite = infinite
        counter.db.item_inventory = stock
        counter.tags.add("advertiser", category="souls")
        from world.souls import actions
        actions._ad_cache["at"] = 0.0
        return counter

    def test_empty_limited_shelf_yields_no_plan(self):
        from world.souls import actions

        soul = self._soul_char()
        soul.tokens = 20
        self._hunger_counter(infinite=False, stock={})
        self.assertIsNone(actions.plan_for(soul, "hunger"))

    def test_stocked_limited_shelf_sells(self):
        from world.souls import actions

        soul = self._soul_char()
        soul.tokens = 20
        self._hunger_counter(infinite=False, stock={"mystery_skewer": 2})
        plan = actions.plan_for(soul, "hunger")
        self.assertIsNotNone(plan)
        self.assertEqual(plan["steps"][1]["proto"], "mystery_skewer")


class TestAdvertiseScope(_CravingTestBase):
    """#2096: a sealed biome's fixtures serve only their resident —
    room-scoped advertisers are invisible to souls elsewhere."""

    def test_room_scoped_advertiser_invisible_from_outside(self):
        from world.souls import actions

        soul = self._soul_char()
        far_room = create_object("typeclasses.rooms.Room", key="far room")
        chair = create_object(
            "typeclasses.items.Item", key="sealed chair", location=far_room)
        chair.db.advertises = {"social": 0.8}
        chair.db.advertise_scope = "room"
        chair.tags.add("advertiser", category="souls")
        actions._ad_cache["at"] = 0.0
        found = [o.key for _sc, o, _r in actions._advertisers(soul, "social")]
        self.assertNotIn("sealed chair", found)

    def test_room_scoped_advertiser_serves_its_resident(self):
        from world.souls import actions

        soul = self._soul_char()
        chair = create_object(
            "typeclasses.items.Item", key="sealed chair",
            location=self.game_room)
        chair.db.advertises = {"social": 0.8}
        chair.db.advertise_scope = "room"
        chair.tags.add("advertiser", category="souls")
        actions._ad_cache["at"] = 0.0
        found = [o.key for _sc, o, _r in actions._advertisers(soul, "social")]
        self.assertIn("sealed chair", found)
