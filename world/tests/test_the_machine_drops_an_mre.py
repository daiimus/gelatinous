"""The cigarette machine drops an MRE (#3806).

Owner, 2026-11-13: *"Let's make a MRE."*

The mechanics tests (#3804, #3808) had to stand in for the ration and
for the shop, because the world had neither: a hand-made bar, a patched
prototype reader, and a `buy` that was a function in the test. This
file is the other half. Nothing here is stood in for:

* the REAL prototype, `longhaul_mre`, read the way the planner reads it;
* a REAL shop shelf, stocked and advertised the way build 171 does it
  to the live machine;
* the real `buy`, `unwield` and `eat`, as a soul types them.

So it pins the item's numbers, and it is the first run of the whole
errand, purchase to pocket to mouth, on the real thing.
"""
import time

from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from world import prototypes
from world.souls import actions, constants, jobs, needs

MRE = "longhaul_mre"
MRE_KEY = "a Longhaul MRE"
#: the live machine's other wares on 2026-11-13: neither is food
OTHER_WARES = {"CIGARETTE_PACK_NOIR": 0, "DISPOSABLE_LIGHTER": 0}


class _MachineCase(EvenniaTest):
    """A corridor, the machine, and one soul standing at it.

    `EvenniaTest`, not the `Base` one: the machine sells real
    prototypes, and the base class resets the settings that register
    them."""

    def setUp(self):
        super().setUp()
        for memo in (actions._proto_food_memo, actions._edible_memo):
            memo.pop(MRE, None)
        self.corridor = create_object(
            "typeclasses.rooms.Room", key="corridor")
        self.machine = create_object(
            "typeclasses.shopkeeper.ShopContainer",
            key="battered cigarette machine", location=self.corridor)
        self.machine.db.prototype_inventory = dict(OTHER_WARES)
        # what build 171 does to the live one
        self.assertTrue(self.machine.add_prototype(MRE, price=0))
        self.machine.db.advertises = {constants.RATION_ADVERT: 0.8}
        self.machine.tags.add("advertiser", category="souls")
        actions._ad_cache["at"] = 0.0             # re-read the tag index
        self.addCleanup(actions._ad_cache.update, {"at": 0.0})
        self.soul = create_object(
            "typeclasses.characters.Character", key="TestSoul",
            location=self.corridor)
        self.soul.tags.add("soul", category="npc_role")
        self.soul.db.soul_needs = {"hunger": 0.0, "_at": time.time()}
        self.soul.tokens = 0

    def one_in_the_pocket(self):
        item = spawn(MRE)[0]
        item.move_to(self.soul, quiet=True)
        return item

    def rations(self):
        return [o.key for o in actions._carried_rations(self.soul)]

    def held(self):
        return [item.key for item in self.soul.hands.values() if item]

    def hungry(self, how=0.9):
        self.soul.db.soul_needs = {"hunger": how, "_at": time.time()}

    def run_job(self, goal, band, beats=6):
        self.soul.db.soul_job = actions.plan_for(self.soul, goal)
        self.assertIsNotNone(self.soul.db.soul_job, f"no plan for {goal}")
        self.soul.db.soul_job["band"] = band
        for _ in range(beats):
            if self.soul.db.soul_job is None:
                break
            jobs.step_job(self.soul)


class TestTheMRE(_MachineCase):
    def test_the_planner_reads_it_as_a_ration(self):
        self.assertEqual(actions._proto_food(MRE), (2, True))
        self.assertTrue(actions._is_edible_proto(MRE))

    def test_its_tag_and_its_quality_are_the_ones_the_code_asks_for(self):
        """The prototype writes them as plain data; the code reads them
        through `constants`. This is what keeps the two the same."""
        proto = prototypes.LONGHAUL_MRE
        self.assertEqual(proto["prototype_key"], MRE)
        self.assertIn(constants.RATION_TAG, proto["tags"])
        self.assertIn((constants.FOOD_QUALITY_ATTR, 2), proto["attrs"])

    def test_one_in_a_pocket_waits_there(self):
        """It is a ration, so it is not food to finish first: the rule
        that ended the hoard (#3793) does not see it."""
        item = self.one_in_the_pocket()
        self.assertEqual(item.key, MRE_KEY)
        self.assertTrue(actions._is_ration(item))
        self.assertEqual(self.rations(), [MRE_KEY])
        self.assertIsNone(actions._carried_food(self.soul))

    def test_it_is_worse_than_an_ordinary_meal(self):
        item = self.one_in_the_pocket()
        self.assertEqual(actions.food_quality(item), 2.0)
        self.assertLess(actions.food_quality(item),
                        constants.FOOD_QUALITY_DEFAULT)
        self.assertLess(jobs.ate_well_valence(actions.food_quality(item)),
                        constants.ATE_WELL_VALENCE)

    def test_it_feeds_as_a_bowl_of_stew_does_in_one_sitting(self):
        """Three doses at once: 0.45 off hunger, and no half-eaten
        pouch goes back in the pocket."""
        self.one_in_the_pocket()
        self.hungry()
        before = needs.pressure(self.soul, "hunger")
        self.soul.execute_cmd("eat mre")
        self.assertAlmostEqual(before - needs.pressure(self.soul, "hunger"),
                               0.45, delta=0.02)
        self.assertEqual([o.key for o in self.soul.contents], [])


class TestTheMachine(_MachineCase):
    def test_the_mre_is_its_only_ration(self):
        self.assertEqual(actions._ration_wares(self.machine), [(MRE, 0)])

    def test_it_is_not_a_place_to_eat(self):
        """The control: it advertises `ration`, never `hunger`. A hungry
        soul with an empty pocket and no kitchen has no plan, and is
        not sent to stand at a machine."""
        self.hungry()
        self.assertEqual(actions._advertisers(self.soul, "hunger"), [])
        self.assertIsNone(actions.plan_for(self.soul, "hunger"))

    def test_a_soul_with_an_empty_pocket_wants_one(self):
        self.assertTrue(actions.wants_ration(self.soul))

    def test_without_the_mre_nobody_wants_anything_from_it(self):
        """The control: the same machine as it stood before build 171's
        first step, cigarettes and a lighter."""
        self.machine.remove_prototype(MRE)
        self.assertEqual(actions._ration_wares(self.machine), [])
        self.assertFalse(actions.wants_ration(self.soul))

    def test_the_errand_ends_with_one_in_the_pocket_and_empty_hands(self):
        """The real `buy` puts the purchase in a free hand; the real
        `unwield` puts it away in the same beat (#3808)."""
        self.assertEqual(self.held(), [])
        self.run_job("provision", band=4)
        self.assertIsNone(self.soul.db.soul_job, "the errand never finished")
        self.assertEqual(self.rations(), [MRE_KEY])
        self.assertEqual(self.held(), [], "still holding it")
        self.assertEqual(self.soul.db.soul_faults or [], [])
        self.assertEqual(self.soul.tokens, 0)

    def test_one_is_enough(self):
        self.run_job("provision", band=4)
        self.assertFalse(actions.wants_ration(self.soul))
        self.assertIsNone(actions.plan_for(self.soul, "provision"))

    def test_hungry_with_no_kitchen_it_eats_the_mre(self):
        """What the ration is for: nothing open, nothing in reach."""
        self.run_job("provision", band=4)
        self.hungry()
        before = needs.pressure(self.soul, "hunger")
        self.run_job("hunger", band=1)
        self.assertIsNone(self.soul.db.soul_job, "the meal never finished")
        self.assertEqual(self.rations(), [])
        self.assertLess(needs.pressure(self.soul, "hunger"), before - 0.3)
        self.assertEqual(self.soul.db.soul_faults or [], [])

    def test_and_then_goes_for_another(self):
        self.run_job("provision", band=4)
        self.hungry()
        self.run_job("hunger", band=1)
        self.assertTrue(actions.wants_ration(self.soul))

    def test_anyone_can_buy_one_by_its_name(self):
        """A player types the name, not the prototype key."""
        self.soul.execute_cmd("buy mre from machine")
        self.assertEqual(self.rations(), [MRE_KEY])
