"""Wren runs packages (#2258).

`route_taste` shipped and was set on nobody. Its docstring names who it
was for — "the courier, the runner, the burglar" — and the colony had
none of them, so every soul walked the pavement like an accountant and
the vertical city was decoration as far as NPCs were concerned.

A courier is also the one job that exercises everything at once:
pathfinding, verticality, taste, tills, and the shift clock. She is a
working instrument.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.director import courier
from world.souls import actions, salience
from world.spatial.pathfind import _route_cost


class _Roof:
    db = type("d", (), {"type": "rooftop"})()


class TestSheTakesTheAwkwardWay(EvenniaCommandTest):
    def test_an_ordinary_colonist_avoids_roofs(self):
        self.assertEqual(_route_cost(_Roof(), None), 6.0)

    def test_the_rabbit_barely_minds(self):
        self.char1.db.route_taste = 0.2
        self.assertAlmostEqual(_route_cost(_Roof(), self.char1), 1.2)

    def test_but_a_roof_never_beats_the_pavement(self):
        """The pathfinder clamps at max(DEFAULT_COST, ...). Taste makes
        the awkward way comparable, never preferable — otherwise she'd
        climb a building to cross a street."""
        self.char1.db.route_taste = 0.0
        self.assertGreaterEqual(_route_cost(_Roof(), self.char1), 1.0)


class TestWhereARunCanGo(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.rabbit = self.char1
        self.rabbit.db.soul_post = self.room1
        self.counter = create_object("typeclasses.items.Item", key="a counter", location=self.room2)
        self.counter.attributes.add("register", 10)

    def test_an_unstaffed_counter_is_not_a_destination(self):
        """'Deliver to an employee' — a package needs somebody to take
        it, and an empty shop has nobody."""
        self.assertEqual(courier.runnable_destinations(self.rabbit), [])

    def test_her_own_depot_is_never_a_run(self):
        """Carrying a parcel across the room is not a run."""
        mine = create_object("typeclasses.items.Item", key="depot counter", location=self.room1)
        mine.attributes.add("register", 10)
        rooms = [r for r, _c, _k in courier.runnable_destinations(self.rabbit)]
        self.assertNotIn(self.room1, rooms)


class TestTheHandover(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.rabbit = self.char1
        self.counter = create_object("typeclasses.items.Item", key="a counter", location=self.room2)
        self.rabbit.tokens = 0

    def _package(self):
        pkg = create_object("typeclasses.items.Item", key="a wrapped package", location=self.rabbit)
        pkg.attributes.add("courier_package", True)
        return pkg

    def test_a_funded_till_pays_her(self):
        self.counter.attributes.add("register", 10)
        pkg = self._package()
        out = courier.hand_over(self.rabbit, self.counter, pkg)
        self.assertEqual(out["paid"], 1)
        self.assertEqual(self.rabbit.tokens, 1)
        self.assertEqual(self.counter.attributes.get("register"), 9)

    def test_a_dry_till_still_gets_its_package(self):
        """The delivery lands unpaid. A courier who withholds a parcel
        because the till is short is a different, worse character — and
        the debt being visible is the whole point."""
        self.counter.attributes.add("register", 0)
        pkg = self._package()
        out = courier.hand_over(self.rabbit, self.counter, pkg)
        self.assertTrue(out["delivered"])
        self.assertTrue(out["short"])
        self.assertEqual(self.rabbit.tokens, 0)

    def test_a_dry_till_tells_the_colony(self):
        """Eight of ten tills held zero the day this was written.
        Subsidising her would have hidden that; instead she measures
        it, through a signal the bus already understood."""
        self.counter.attributes.add("register", 0)
        with mock.patch("world.wsis.emit") as emit:
            courier.hand_over(self.rabbit, self.counter, self._package())
        self.assertEqual(emit.call_args.args[0], "till_empty")

    def test_she_never_overdraws_a_till(self):
        self.counter.attributes.add("register", 0)
        courier.hand_over(self.rabbit, self.counter, self._package())
        self.assertGreaterEqual(
            int(self.counter.attributes.get("register")), 0)

    def test_the_fee_is_testing_scale(self):
        """One token, deliberately. She runs all shift; at a realistic
        fee she would strip every till in the colony inside a day."""
        self.assertEqual(courier.FEE, 1)


class TestTheRunIsAJob(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.rabbit = self.char1
        self.rabbit.db.soul_post = self.room1
        self.counter = create_object("typeclasses.items.Item", key="a counter", location=self.room2)
        self.rabbit.db.soul_run_to = self.room2.id
        self.rabbit.db.soul_run_counter = self.counter.id

    def test_cross_the_city_hand_over_come_home(self):
        job = actions.plan_for(self.rabbit, "run")
        self.assertEqual([s["do"] for s in job["steps"]],
                         ["travel", "handoff", "travel"])

    def test_it_ends_where_it_started(self):
        job = actions.plan_for(self.rabbit, "run")
        self.assertEqual(job["steps"][-1]["room"], self.room1.id)

    def test_no_destination_no_plan(self):
        self.rabbit.db.soul_run_to = None
        self.assertIsNone(actions.plan_for(self.rabbit, "run"))

    def test_handoff_is_not_deliver(self):
        """`deliver` is the recovery step's name and means something
        else entirely. Two jobs sharing a step name would silently
        cross the wires."""
        import inspect
        from world.souls import jobs
        src = inspect.getsource(jobs.step_job)
        self.assertIn('if do == "handoff":', src)
        self.assertIn('if do == "deliver":', src)


class TestRunsAreShiftWork(EvenniaCommandTest):
    def test_the_courier_is_in_the_work_registry(self):
        """Runs are post work — the same registry the medic's restock
        and the mechanic's racking live in, so this is one entry rather
        than a new scheduler."""
        self.assertIn("courier", salience.ROLE_WORK)

    def test_she_does_not_take_a_second_run_while_out(self):
        rabbit = self.char1
        rabbit.db.soul_job = {"goal": "run", "at": 0, "steps": []}
        with mock.patch.object(courier, "runnable_destinations") as dests:
            salience._work_courier(rabbit)
        dests.assert_not_called()

    def test_nowhere_to_go_means_she_waits(self):
        rabbit = self.char1
        rabbit.db.soul_post = self.room1
        with mock.patch.object(courier, "runnable_destinations",
                               return_value=[]):
            salience._work_courier(rabbit)
        self.assertIsNone(rabbit.db.soul_job)
