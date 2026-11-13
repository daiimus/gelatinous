"""Food has a quality, a walk has a cost, and one ration may wait in
the pocket (#3804).

Owner, 2026-11-13, on what the mechanic is for: *"What I want to avoid
is someone deep in the currently non-existent mines going like 40+
rooms to a restaurant rather then eating a ration."* And on the rule it
must not break: *"Hoard fix is a good callout. We don't want to harm
that logic."*

So three things are pinned here, and the second half of each class is
its controls:

* the hoard rule stands exactly as #3793 left it, for everything a
  soul carries except a ration;
* the ration is weighed against the one meal the soul would otherwise
  walk to, by quality less a cost per room, with no distance written
  down anywhere;
* a soul carries one, and goes for another only when it has none and
  one is to be had.

Hand-made food, as in the #3796 tests: what is under test is the
planner's choice and the job's steps, and nothing in the world sells a
ration yet (#3806).
"""
import time as _time
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.souls import actions, constants, engine, jobs

RATION = constants.RATION_TAG
NOON = 12.0


class _PocketCase(BaseEvenniaTest):
    """A soul in a yard, a kitchen somewhere else, and pockets to fill."""

    def setUp(self):
        super().setUp()
        self.yard = create_object("typeclasses.rooms.Room", key="yard")
        self.far = create_object("typeclasses.rooms.Room", key="far kitchen")
        self.kitchen = create_object(
            "typeclasses.objects.Object", key="a kitchen", location=self.far)
        self.soul = create_object(
            "typeclasses.characters.Character", key="TestSoul",
            location=self.yard)
        self.soul.cmdset.add(
            "commands.default_cmdsets.CharacterCmdSet", persistent=False)
        self.soul.tags.add("soul", category="npc_role")
        self.soul.db.soul_needs = {"hunger": 0.7, "_at": _time.time()}
        self.soul.tokens = 0

    def food(self, key, where=None, quality=None, ration=False,
             bites=1, dose=1):
        item = create_object(
            "typeclasses.items.Item", key=key,
            location=self.soul if where is None else where)
        item.tags.add("eat", category="delivery_method")
        item.db.drink_effects = {"nutrition": dose}
        item.db.uses_left = bites
        if quality is not None:
            item.attributes.add(constants.FOOD_QUALITY_ATTR, quality)
        if ration:
            item.tags.add(RATION[0], category=RATION[1])
        return item

    def bar(self, **kwargs):
        return self.food("a ration bar", quality=2, ration=True, **kwargs)

    def stew(self, **kwargs):
        return self.food("a bowl of stew", bites=3, **kwargs)

    def a_kitchen(self, rooms, quality=None, here=False):
        """Everything `plan_for` asks about one workable seller: where
        it is, the plan it gives, how good its food is, how far."""
        room = self.yard if here else self.far
        steps = [{"do": "buy", "counter": self.kitchen.id, "proto": "meal"}]
        quality = constants.FOOD_QUALITY_DEFAULT if quality is None else quality
        patches = [
            mock.patch.object(actions, "_advertisers",
                              return_value=[(1.0, self.kitchen, room)]),
            mock.patch.object(actions, "_feed_at", return_value=steps),
            mock.patch.object(actions, "_meal_quality", return_value=quality),
            mock.patch("world.spatial.pathfind.path_length",
                       return_value=rooms),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def no_kitchen(self):
        patch = mock.patch.object(actions, "_advertisers", return_value=[])
        patch.start()
        self.addCleanup(patch.stop)

    def machine(self, price=0):
        """An unstaffed shelf with a ration on it, like the cigarette
        machine with a bar in it."""
        machine = create_object(
            "typeclasses.objects.Object", key="a machine", location=self.far)
        machine.db.prototype_inventory = {"ration_bar": price}
        return machine

    def sells(self, machine, in_range=True):
        """Make the machine a restock point the planner can see (or one
        out of range), with a ration prototype behind its one ware."""
        found = [(0.5, machine, self.far)] if in_range else []
        patches = [
            mock.patch.object(
                actions, "_advertisers",
                side_effect=lambda soul, need, **kw: (
                    found if need == constants.RATION_ADVERT else [])),
            mock.patch.object(actions, "_proto_food",
                              return_value=(2, True)),
            mock.patch.object(actions, "_is_edible_proto", return_value=True),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def meal_plan(self):
        job = actions.plan_for(self.soul, "hunger")
        return [step["do"] for step in job["steps"]] if job else None

    def eats(self):
        """The id of the pocket item the hunger plan would eat, if any."""
        job = actions.plan_for(self.soul, "hunger")
        steps = job["steps"] if job else []
        return steps[0].get("item") if len(steps) == 1 else None


class TestTheHoardRuleStands(_PocketCase):
    """#3793: what a soul carries is eaten before anything is bought.
    A ration is the one thing let off, and nothing else is."""

    def test_a_ration_is_not_food_to_finish_first(self):
        self.bar()
        self.assertIsNone(actions._carried_food(self.soul))

    def test_any_other_food_still_is(self):
        """The control, and the rule itself."""
        stew = self.stew()
        self.assertEqual(actions._carried_food(self.soul), stew)

    def test_a_leftover_is_found_behind_a_ration(self):
        self.bar()
        stew = self.stew()
        self.assertEqual(actions._carried_food(self.soul), stew)

    def test_a_leftover_is_eaten_first_with_a_ration_and_a_kitchen_next_door(self):
        self.bar()
        stew = self.stew()
        self.a_kitchen(rooms=0, here=True)
        self.assertEqual(self.eats(), stew.id)

    def test_a_leftover_is_eaten_before_a_far_better_kitchen(self):
        """The trap a quality score would have set: a stew carried off
        after an interrupted order (#3796) passed over for better food,
        and the next interruption adding another."""
        stew = self.stew()
        self.a_kitchen(rooms=1, quality=9)
        self.assertEqual(self.eats(), stew.id)

    def test_a_soul_at_its_limit_does_not_want_another(self):
        self.bar()
        machine = self.machine()
        self.sells(machine)
        self.assertFalse(actions.wants_ration(self.soul))


class TestTheWalk(_PocketCase):
    """The ration against the meal the soul would otherwise walk to.
    Placeholder numbers: ration 2, an ordinary meal 5, a room 0.1."""

    def test_with_no_ration_a_soul_walks_however_far(self):
        """The control: nothing changes for a soul with empty pockets."""
        self.a_kitchen(rooms=40)
        self.assertEqual(self.meal_plan(), ["travel", "buy"])

    def test_forty_rooms_from_a_meal_it_eats_the_ration(self):
        """The owner's miner: 5 - 4.0 = 1.0, under the ration's 2."""
        bar = self.bar()
        self.a_kitchen(rooms=40)
        self.assertEqual(self.eats(), bar.id)

    def test_six_rooms_from_a_meal_it_walks(self):
        """The canteen that opens near the mine: 5 - 0.6 = 4.4."""
        self.bar()
        self.a_kitchen(rooms=6)
        self.assertEqual(self.meal_plan(), ["travel", "buy"])

    def test_a_tie_goes_to_the_pocket(self):
        """5 - 3.0 = 2: no reason to walk thirty rooms for the same."""
        bar = self.bar()
        self.a_kitchen(rooms=30)
        self.assertEqual(self.eats(), bar.id)

    def test_better_food_is_worth_a_longer_walk(self):
        """A quality-7 meal at the same forty rooms: 7 - 4.0 = 3.0."""
        self.bar()
        self.a_kitchen(rooms=40, quality=7)
        self.assertEqual(self.meal_plan(), ["travel", "buy"])

    def test_and_even_that_has_an_end(self):
        bar = self.bar()
        self.a_kitchen(rooms=60, quality=7)
        self.assertEqual(self.eats(), bar.id)

    def test_a_kitchen_in_the_room_beats_the_ration(self):
        """A keeper standing at their own food counter makes the stew;
        the ration stays where it is."""
        self.bar()
        self.a_kitchen(rooms=0, here=True)
        self.assertEqual(self.meal_plan(), ["travel", "buy"])

    def test_with_nowhere_to_go_it_eats_the_ration(self):
        """With no ration this soul has no plan at all (the control
        below), which is the miner's case today."""
        bar = self.bar()
        self.no_kitchen()
        self.assertEqual(self.eats(), bar.id)

    def test_with_nowhere_to_go_and_no_ration_it_goes_hungry(self):
        """The control: unchanged."""
        self.no_kitchen()
        self.assertIsNone(actions.plan_for(self.soul, "hunger"))

    def test_a_kitchen_with_no_way_to_it_is_no_kitchen(self):
        bar = self.bar()
        self.a_kitchen(rooms=None)
        self.assertEqual(self.eats(), bar.id)

    def test_the_cost_of_a_room_is_the_constant(self):
        """Tuning is one number in one file."""
        self.bar()
        self.a_kitchen(rooms=40)
        with mock.patch.object(constants, "FOOD_WALK_COST_PER_ROOM", 0.0):
            self.assertEqual(self.meal_plan(), ["travel", "buy"])

    def test_a_better_ration_is_reached_for_sooner(self):
        self.food("a fine ration", quality=4.5, ration=True)
        self.a_kitchen(rooms=6)
        self.assertEqual(self.meal_plan(), ["eat"])


class TestTheQualityOfAMeal(_PocketCase):
    def test_a_food_that_declares_none_is_ordinary(self):
        self.assertEqual(actions.food_quality(self.stew()),
                         constants.FOOD_QUALITY_DEFAULT)

    def test_a_food_says_its_own(self):
        self.assertEqual(actions.food_quality(self.bar()), 2.0)

    def test_nonsense_is_ordinary_too(self):
        for junk in ("good", True, None, [3]):
            self.assertEqual(actions._as_quality(junk),
                             constants.FOOD_QUALITY_DEFAULT, repr(junk))

    def test_a_shelf_plan_reads_the_prototype(self):
        steps = [{"do": "buy", "counter": 1, "proto": "meal"}]
        with mock.patch.object(actions, "_proto_food",
                               return_value=(7, False)):
            self.assertEqual(actions._meal_quality(self.kitchen, steps), 7.0)

    def test_a_board_plan_reads_the_entry_it_asks_for(self):
        self.kitchen.db.menu = [
            {"name": "plain bowl"},
            {"name": "good bowl", "quality": 8},
            {"name": "plated bowl", "proto": "meal"}]
        asks = lambda name: [{"do": "order", "counter": 1, "want": name}]
        with mock.patch.object(actions, "_proto_food",
                               return_value=(6, False)):
            got = [actions._meal_quality(self.kitchen, asks(name))
                   for name in ("plain bowl", "good bowl", "plated bowl")]
        self.assertEqual(got, [constants.FOOD_QUALITY_DEFAULT, 8.0, 6.0])


class TestRestocking(_PocketCase):
    """One ration, fetched on a quiet beat, and only when there is one
    to be had."""

    def test_nothing_sells_one_so_nobody_wants_one(self):
        """The world as it stands today (#3806): dormant."""
        self.no_kitchen()
        self.assertFalse(actions.wants_ration(self.soul))

    def test_an_empty_pocket_and_a_machine_in_range(self):
        self.sells(self.machine())
        self.assertTrue(actions.wants_ration(self.soul))

    def test_out_of_range_is_not_wanted(self):
        """Or the goal would be offered and fail every fifteen minutes."""
        self.sells(self.machine(), in_range=False)
        self.assertFalse(actions.wants_ration(self.soul))

    def test_beyond_the_purse_is_not_wanted(self):
        self.sells(self.machine(price=3))
        self.assertFalse(actions.wants_ration(self.soul))
        self.soul.tokens = 3
        self.assertTrue(actions.wants_ration(self.soul))

    def test_a_body_with_no_purse_is_asked_without_error(self):
        """Every soul is asked this on every idle think, whatever it is
        built from: a bare Evennia character has no `tokens` at all
        (`test_one_driver` runs the band tree on one)."""
        bare = create_object("evennia.objects.objects.DefaultCharacter",
                             key="Bare", location=self.yard)
        self.sells(self.machine(price=3))
        self.assertFalse(actions.wants_ration(bare))
        self.assertEqual(engine._desired_goal(bare, NOON)[1] == "provision",
                         False)

    def test_a_body_that_does_not_eat_bought_food_wants_none(self):
        self.sells(self.machine())
        self.soul.db.soul_profile = "robot"
        self.assertFalse(actions.wants_ration(self.soul))
        self.soul.db.soul_profile = "recluse"
        self.assertFalse(actions.wants_ration(self.soul))

    def test_the_errand_is_a_walk_and_a_purchase_and_no_meal(self):
        machine = self.machine()
        self.sells(machine)
        job = actions.plan_for(self.soul, "provision")
        self.assertEqual([s["do"] for s in job["steps"]], ["travel", "buy"])
        self.assertEqual(job["steps"][0]["room"], self.far.id)
        self.assertEqual(job["steps"][1]["counter"], machine.id)
        self.assertEqual(job["steps"][1]["proto"], "ration_bar")

    def test_there_is_no_errand_for_a_full_pocket(self):
        self.sells(self.machine())
        self.bar()
        self.assertIsNone(actions.plan_for(self.soul, "provision"))

    def idle(self):
        """A soul with nothing pressing: fed, rested, dressed, insured."""
        self.soul.db.soul_needs = {"hunger": 0.0, "rest": 0.0, "social": 0.0,
                                   "_at": _time.time()}
        return {"wardrobe", "insurance", "comms"}

    def test_an_idle_soul_is_offered_the_errand(self):
        self.sells(self.machine())
        skip = self.idle()
        self.assertEqual(engine._desired_goal(self.soul, NOON, exclude=skip),
                         (4, "provision"))

    def test_and_not_while_it_cools_down(self):
        self.sells(self.machine())
        skip = self.idle() | {"provision"}
        _band, goal = engine._desired_goal(self.soul, NOON, exclude=skip)
        self.assertNotEqual(goal, "provision")

    def test_a_hungry_soul_eats_before_it_shops(self):
        """Band 4: anything pressing comes first."""
        self.sells(self.machine())
        skip = self.idle()
        self.soul.db.soul_needs = {"hunger": 0.7, "_at": _time.time()}
        _band, goal = engine._desired_goal(self.soul, NOON, exclude=skip)
        self.assertEqual(goal, "hunger")

    def test_the_bought_ration_stays_in_the_pocket(self):
        """`buy` with no `eat` after it: bought, kept, job done."""
        machine = self.machine()
        machine.location = self.yard
        self.soul.db.soul_job = {"goal": "provision", "band": 4, "at": 0,
                                 "steps": [{"do": "buy",
                                            "counter": machine.id,
                                            "proto": "ration_bar",
                                            "price": 0}]}
        with mock.patch.object(type(self.soul), "execute_cmd",
                               side_effect=lambda raw, **kw: self.bar()):
            jobs.step_job(self.soul)
        jobs.step_job(self.soul)
        self.assertIsNone(self.soul.db.soul_job)
        self.assertEqual([o.key for o in actions._carried_rations(self.soul)],
                         ["a ration bar"])
        self.assertEqual(self.soul.db.soul_faults or [], [])


class TestTheMeal(_PocketCase):
    """Real `eat`: what goes down, and how it feels afterwards."""

    def finish(self, item):
        self.soul.db.soul_job = {"goal": "hunger", "band": 3, "at": 0,
                                 "steps": [{"do": "eat", "item": item.id}]}
        for _ in range(8):
            if self.soul.db.soul_job is None:
                break
            jobs.step_job(self.soul)
        self.assertIsNone(self.soul.db.soul_job, "the meal never finished")

    def lift(self):
        """The valence of the newest `ate_well` thought, or None."""
        felt = [valence for _stamp, key, valence, _note
                in (self.soul.db.soul_thoughts or []) if key == "ate_well"]
        return felt[-1] if felt else None

    def test_the_meal_named_is_the_meal_eaten(self):
        """A ration in the pocket is not eaten in place of the stew the
        plan named, and is still there afterwards."""
        self.bar()
        stew = self.stew()
        self.finish(stew)
        self.assertEqual([o.key for o in self.soul.contents],
                         ["a ration bar"])

    def test_an_ordinary_meal_lifts_what_a_meal_always_lifted(self):
        """The control: no dish has a number yet, so nothing moves."""
        self.finish(self.stew())
        self.assertAlmostEqual(self.lift(), 0.15)

    def test_a_ration_is_felt_less(self):
        self.finish(self.bar(dose=3))
        self.assertAlmostEqual(self.lift(), 0.06)

    def test_a_fine_meal_is_felt_more_and_no_meal_is_a_drug(self):
        self.finish(self.food("a feast", quality=8, bites=3))
        self.assertAlmostEqual(self.lift(), 0.24)
        self.assertEqual(jobs.ate_well_valence(50),
                         constants.ATE_WELL_VALENCE_MAX)

    def test_the_lift_follows_the_numbers(self):
        self.assertAlmostEqual(jobs.ate_well_valence(None), 0.15)
        self.assertAlmostEqual(jobs.ate_well_valence(5), 0.15)
        self.assertEqual(jobs.ate_well_valence(0), 0.0)
        self.assertEqual(jobs.ate_well_valence(-3), 0.0)
