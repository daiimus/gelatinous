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

    def sells(self, machine, in_range=True, routable=True):
        """Make the machine a restock point, with a ration prototype
        behind its one ware. `_advertisers` is stood in for as the real
        one behaves: asked for straight-line range it answers
        `in_range`; asked for sources with a route (the default) it
        also needs `routable`. `self.routes_asked` counts the second
        kind, which is the one that costs a pathfind."""
        found = [(0.5, machine, machine.location)]
        self.routes_asked = 0
        self.routable = routable        # a test may lock the door later

        def advertisers(soul, need, radius=30, reachable=True):
            if need != constants.RATION_ADVERT or not in_range:
                return []
            if reachable:
                self.routes_asked += 1
                return list(found) if self.routable else []
            return list(found)

        patches = [
            mock.patch.object(actions, "_advertisers",
                              side_effect=advertisers),
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

    def test_a_board_plan_reads_the_prototype_it_would_plate(self):
        """The number comes from the food, never from the board entry:
        nothing would carry an entry's figure onto the dish, and the
        walk would be weighed on one number and the meal felt on
        another."""
        self.kitchen.db.menu = [
            {"name": "mixed bowl"},
            {"name": "mixed bowl with a figure on the board", "quality": 8},
            {"name": "plated bowl", "proto": "meal"}]
        asks = lambda name: [{"do": "order", "counter": 1, "want": name}]
        with mock.patch.object(actions, "_proto_food",
                               return_value=(6, False)):
            got = [actions._meal_quality(self.kitchen, asks(entry["name"]))
                   for entry in self.kitchen.db.menu]
        ordinary = constants.FOOD_QUALITY_DEFAULT
        self.assertEqual(got, [ordinary, ordinary, 6.0])

    def test_the_real_prototype_reader(self):
        """Unpatched: quality and the ration tag off a registry entry."""
        entry = {"prototype_key": "x",
                 "tags": [("eat", "delivery_method"), RATION],
                 "attrs": [("uses_left", 1),
                           (constants.FOOD_QUALITY_ATTR, 2)]}
        plain = {"prototype_key": "y", "tags": [("eat", "delivery_method")],
                 "attrs": [("uses_left", 3)]}
        actions._proto_food_memo.clear()
        self.addCleanup(actions._proto_food_memo.clear)
        with mock.patch("evennia.prototypes.prototypes.search_prototype",
                        side_effect=lambda key: {"x": [entry],
                                                 "y": [plain]}.get(key, [])):
            self.assertEqual(actions._proto_food("x"), (2, True))
            self.assertEqual(actions._proto_food("y"), (None, False))
            self.assertEqual(actions._proto_food("nothing"), (None, False))


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

    def test_no_route_is_not_wanted(self):
        """In straight-line range, behind a door this soul cannot open
        (#2316's padlocked shutter). Offered anyway, the plan would
        fail, fault, cool for fifteen minutes and be offered again, for
        every soul in range, for as long as the machine stood."""
        self.sells(self.machine(), routable=False)
        self.assertFalse(actions.wants_ration(self.soul))
        self.assertIsNone(actions.plan_for(self.soul, "provision"))

    def test_the_route_is_asked_once_and_remembered(self):
        """Every idle think asks; only the first pays for a pathfind."""
        self.sells(self.machine(), routable=False)
        for _ in range(5):
            self.assertFalse(actions.wants_ration(self.soul))
        self.assertEqual(self.routes_asked, 1)

    def test_and_asked_again_when_the_memory_is_stale(self):
        self.sells(self.machine(), routable=False)
        self.assertFalse(actions.wants_ration(self.soul))
        self.soul.ndb.ration_no_route = {self.yard.id: _time.time() - 1}
        self.assertFalse(actions.wants_ration(self.soul))
        self.assertEqual(self.routes_asked, 2)

    def test_a_no_holds_only_for_the_room_it_was_given_in(self):
        """The route depends on where the soul stands. An answer got in
        one room and spent in another is how an errand comes to be
        offered where it cannot be planned."""
        self.sells(self.machine(), routable=False)
        self.assertFalse(actions.wants_ration(self.soul))
        self.soul.location = self.far
        self.assertFalse(actions.wants_ration(self.soul))
        self.assertEqual(self.routes_asked, 2, "the old room's no was used")

    def test_a_soul_on_a_beat_asks_once_a_stop_not_once_a_visit(self):
        """Idle at every stop of a beat. With one remembered room each
        stop overwrote the last, and the pathfind was paid again on
        every return for as long as the door stayed shut."""
        self.sells(self.machine(), routable=False)
        for _lap in range(3):
            for stop in (self.yard, self.far):
                self.soul.location = stop
                self.assertFalse(actions.wants_ration(self.soul))
        self.assertEqual(self.routes_asked, 2, "one for each stop")

    def test_stale_rooms_are_forgotten(self):
        self.sells(self.machine(), routable=False)
        self.soul.ndb.ration_no_route = {999: _time.time() - 1}
        self.assertFalse(actions.wants_ration(self.soul))
        self.assertEqual(list(self.soul.ndb.ration_no_route),
                         [self.yard.id])

    def test_a_yes_is_never_remembered(self):
        """A yes is acted on in the same think, from the same room, so
        there is nothing to carry anywhere."""
        self.sells(self.machine())
        self.assertTrue(actions.wants_ration(self.soul))
        self.assertTrue(actions.wants_ration(self.soul))
        self.assertEqual(self.routes_asked, 2)
        self.routable = False                       # the door is locked
        self.assertFalse(actions.wants_ration(self.soul))

    def test_a_busy_soul_is_not_asked(self):
        """The band tree runs on every think, job or no job, and an
        idle errand never replaces a job. Asking mid-patrol only got an
        answer for wherever the beat had reached."""
        self.sells(self.machine())
        skip = self.idle()
        self.soul.db.soul_job = {"goal": "patrol", "band": 4, "at": 0,
                                 "steps": [{"do": "patrol_mark"}]}
        self.assertFalse(actions.wants_ration(self.soul))
        self.assertEqual(self.routes_asked, 0)
        _band, goal = engine._desired_goal(self.soul, NOON, exclude=skip)
        self.assertNotEqual(goal, "provision")

    def test_a_plan_that_finds_no_route_stops_the_offer(self):
        """The door was locked between the offer and the plan: one
        failed plan, then nothing from this room until the route is
        asked afresh."""
        self.sells(self.machine())
        self.assertTrue(actions.wants_ration(self.soul))
        self.routable = False
        self.assertIsNone(actions.plan_for(self.soul, "provision"))
        asked = self.routes_asked
        self.assertFalse(actions.wants_ration(self.soul))
        self.assertEqual(self.routes_asked, asked,
                         "it paid for another pathfind to hear no again")

    def test_a_shut_counter_is_not_wanted(self):
        """A staffed shelf with nobody on shift sells nothing."""
        self.sells(self.machine())
        with mock.patch.object(actions, "_counter_open", return_value=False):
            self.assertFalse(actions.wants_ration(self.soul))
            self.assertIsNone(actions.plan_for(self.soul, "provision"))

    def real_source(self, cells_away):
        """A machine the REAL `_advertisers` has to find: tagged,
        advertising, and that many map cells from the soul."""
        self.yard.db.xyz = (0, 0, 0)
        self.far.db.xyz = (cells_away, 0, 0)
        machine = self.machine()
        machine.db.advertises = {constants.RATION_ADVERT: 0.5}
        machine.tags.add("advertiser", category="souls")
        actions._ad_cache["at"] = 0.0             # re-read the tag index
        self.addCleanup(actions._ad_cache.update, {"at": 0.0})
        patches = [
            mock.patch.object(actions, "_proto_food", return_value=(2, True)),
            mock.patch.object(actions, "_is_edible_proto", return_value=True),
            mock.patch.object(actions, "_reachable_only",
                              side_effect=lambda soul, found: found),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return machine

    def test_the_real_range_lets_a_near_source_in(self):
        self.real_source(cells_away=10)
        self.assertTrue(actions.wants_ration(self.soul))

    def test_and_keeps_a_far_one_out_without_asking_the_route(self):
        """Beyond the planner's thirty cells nothing is offered, and
        nothing is pathed: this is where the whole colony stands until
        a machine sells a ration."""
        self.real_source(cells_away=40)
        with mock.patch.object(actions, "_ration_source") as routed:
            self.assertFalse(actions.wants_ration(self.soul))
        routed.assert_not_called()

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
        self.assertEqual([s["do"] for s in job["steps"]],
                         ["travel", "buy", "stow"])
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

    def bought_into_the_hand(self):
        """Stand in for the shop, which this test has none of: `buy`
        puts a ration in the buyer's free hand, as
        `ShopContainer.purchase_item` does. Every other command is
        real."""
        soul = self.soul
        real = soul.execute_cmd

        def execute_cmd(raw_string, **kwargs):
            if not raw_string.startswith("buy "):
                return real(raw_string, **kwargs)
            bar = self.bar()
            free = next(hand for hand, held in soul.hands.items()
                        if held is None)
            soul.wield_item(bar, free)

        soul.execute_cmd = execute_cmd

    def held(self):
        return [item.key for item in self.soul.hands.values() if item]

    def test_the_errand_ends_with_the_ration_put_away(self):
        """A shop hands a purchase over (#3808). Bought to be kept, it
        would have stayed in that hand for days: seventy souls each
        holding a bar, and each a hand short for its radio."""
        machine = self.machine()
        machine.location = self.yard
        self.sells(machine)
        self.bought_into_the_hand()
        self.soul.db.soul_job = actions.plan_for(self.soul, "provision")
        for _ in range(6):
            if self.soul.db.soul_job is None:
                break
            jobs.step_job(self.soul)
        self.assertIsNone(self.soul.db.soul_job)
        self.assertEqual([o.key for o in actions._carried_rations(self.soul)],
                         ["a ration bar"])
        self.assertEqual(self.held(), [], "still holding it")
        self.assertEqual(self.soul.db.soul_faults or [], [])

    def test_putting_away_nothing_is_not_a_fault(self):
        """Both hands were full, so the shop put it straight in a
        pocket: the step has nothing to do and says nothing."""
        bar = self.bar()
        self.soul.db.soul_job = {"goal": "provision", "band": 4, "at": 0,
                                 "steps": [{"do": "stow", "item": bar.id}]}
        jobs.step_job(self.soul)
        jobs.step_job(self.soul)
        self.assertIsNone(self.soul.db.soul_job)
        self.assertEqual(self.soul.db.soul_faults or [], [])
        self.assertEqual([o.key for o in self.soul.contents],
                         ["a ration bar"])

    def test_a_meal_bought_is_still_handed_on_to_be_eaten(self):
        """The control: `buy` then `eat` names the ware for the mouth,
        as it did, and nothing is put away."""
        steps = [{"do": "buy", "counter": 1, "proto": "x"}, {"do": "eat"}]
        job = {"goal": "hunger", "at": 0, "steps": steps}
        stew = self.stew()
        self.assertTrue(jobs._hand_on(self.soul, job, 0, set()))
        self.assertEqual(steps[1].get("item"), stew.id)

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

    def test_a_meal_and_a_ration_that_are_both_a_bar(self):
        """`eat first bar` took whichever came first. The ration went
        down, the meal the plan named stayed in the pocket, and the
        soul went for another ration."""
        self.food("a ration bar", quality=2, ration=True)   # carried first
        chocolate = self.food("a chocolate bar")
        self.finish(chocolate)
        self.assertEqual([o.key for o in self.soul.contents],
                         ["a ration bar"])

    def test_the_word_a_ware_is_asked_for_by(self):
        word = lambda key: jobs._word_for(self.soul, key)
        self.assertEqual(word("a bowl of stew"), "stew")     # nothing carried
        self.food("a ration bar", ration=True)
        self.assertEqual(word("a bowl of stew"), "stew")     # still its own
        self.assertEqual(word("a chocolate bar"), "chocolate")
        self.food("a chocolate bar")
        self.assertEqual(word("a chocolate bar"), "chocolate",
                         "a twin does not count against the word")
        self.assertEqual(word("a ration bar"), "ration")
        self.assertEqual(word("bar"), "bar", "no other word to use")

    def test_only_a_plain_word_is_put_forward(self):
        """Two stews: `stew` and `bowl` are both taken, `of` is too
        short to mean anything, and the hyphenated word is not sent
        through the ordinal's rewriting. The last word stands, which is
        what was typed before this function existed."""
        self.food("a bowl of rat stew")
        self.assertEqual(
            jobs._word_for(self.soul, "a bowl of kuro-nikomi stew"), "stew")

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
