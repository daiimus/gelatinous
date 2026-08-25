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
        self.rabbit.db.soul_run_clerk = self.char2.id

    def test_sign_it_out_cross_the_city_hand_over_come_home(self):
        job = actions.plan_for(self.rabbit, "run")
        self.assertEqual([s["do"] for s in job["steps"]],
                         ["collect", "travel", "handoff", "travel"])

    def test_no_clerk_no_plan(self):
        """Custody starts with a person. Without a consignor there is
        nothing to carry and no run to plan."""
        self.rabbit.db.soul_run_clerk = None
        self.assertIsNone(actions.plan_for(self.rabbit, "run"))

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


class TestChainOfCustody(EvenniaCommandTest):
    """The parcel is a real object that passes hand to hand (#2295).

    Spawned to the depot clerk → signed out by the courier → carried
    across the city → handed to the receiving employee → retired.

    It exists as an object precisely so it can be taken off her in the
    middle. A package that materialises in her hands and evaporates on
    arrival cannot be stolen, and a courier who cannot be robbed is a
    delivery animation rather than a job.
    """

    def setUp(self):
        super().setUp()
        self.rabbit, self.clerk = self.char1, self.char2
        self.rabbit.db.soul_post = self.room1
        self.clerk.location = self.room1

    def _parcel(self, holder):
        pkg = create_object("typeclasses.items.Item",
                            key="a Longhaul bonded parcel", location=holder)
        pkg.attributes.add("courier_package", True)
        return pkg

    def test_it_starts_in_the_clerks_hands_not_hers(self):
        from world.souls import salience
        pkg = salience._spawn_package(self.clerk, self.room2)
        self.assertIsNotNone(pkg)
        self.assertIs(pkg.location, self.clerk)

    def test_she_signs_it_out(self):
        from world.souls import jobs
        pkg = self._parcel(self.clerk)
        job = {"goal": "run", "at": 0,
               "steps": [{"do": "collect", "clerk": self.clerk.id}]}
        self.rabbit.db.soul_job = job
        jobs.step_job(self.rabbit)
        self.assertIs(pkg.location, self.rabbit)

    def test_no_clerk_no_run(self):
        """Her shift is gated on somebody else's, without either of
        them knowing about the other."""
        from world.souls import salience
        from world.director import courier
        with mock.patch.object(courier, "_keeper_in", return_value=None), \
             mock.patch.object(courier, "runnable_destinations") as dests:
            salience._work_courier(self.rabbit)
        dests.assert_not_called()
        self.assertIsNone(self.rabbit.db.soul_job)

    def test_an_empty_counter_faults_rather_than_inventing_one(self):
        from world.souls import jobs
        self.rabbit.db.soul_job = {
            "goal": "run", "at": 0,
            "steps": [{"do": "collect", "clerk": self.clerk.id}]}
        jobs.step_job(self.rabbit)      # clerk holds nothing
        self.assertIsNone(self.rabbit.db.soul_job)
        self.assertTrue(self.rabbit.db.soul_faults)

    def test_it_is_retired_on_handoff(self):
        """One McGuffin per run. Otherwise every counter in the colony
        slowly silts up with parcels nobody opens."""
        from world.souls import jobs
        counter = create_object("typeclasses.items.Item",
                                key="a counter", location=self.room1)
        counter.attributes.add("register", 10)
        pkg = self._parcel(self.rabbit)
        self.rabbit.db.soul_job = {
            "goal": "run", "at": 0,
            "steps": [{"do": "handoff", "counter": counter.id}]}
        jobs.step_job(self.rabbit)
        self.assertFalse(pkg.pk, "the parcel outlived its delivery")

    def test_it_can_be_taken_off_her(self):
        """The whole reason it's an object. Nothing special is needed —
        it's ordinary inventory, so anything that moves items moves
        this."""
        pkg = self._parcel(self.rabbit)
        pkg.move_to(self.clerk, quiet=True, move_hooks=False)
        self.assertIs(pkg.location, self.clerk)
        carried = [o for o in self.rabbit.contents
                   if o.attributes.has("courier_package")]
        self.assertEqual(carried, [])

    def test_the_mcguffin_says_nothing_about_itself(self):
        """Deliberate: nobody knows what's inside, including the people
        carrying it. It's custody, not cargo."""
        from world import prototypes
        desc = prototypes.COURIER_PACKAGE["desc"].lower()
        self.assertIn("longhaul", prototypes.COURIER_PACKAGE["key"].lower())
        self.assertIn("consignor's business", desc)


class TestWhereSheGoesWhenSheIsDone(EvenniaCommandTest):
    """Sometimes she hangs out on rooftops (#2299).

    `off_duty` exists because "nobody stays at work for want of a
    reason to leave" — the shopkeeper loitering behind her own counter
    for the seven hours between the end of her day and the start of her
    sleep. For a rabbit, the reason to leave is a roof.

    So the perch fills exactly the gap that goal was built for, and
    needs no new goal, no timer and no randomness: she's up there
    between clocking off and getting tired, and the band tree takes
    her home when rest finally outranks idling.
    """

    def setUp(self):
        super().setUp()
        self.rabbit = self.char1
        self.rabbit.db.soul_home = self.room1
        self.rabbit.location = self.room2

    def test_an_ordinary_soul_goes_home(self):
        job = actions.plan_for(self.rabbit, "off_duty")
        self.assertEqual(job["steps"][0]["room"], self.room1.id)

    def test_a_soul_with_a_perch_goes_up(self):
        self.rabbit.db.soul_perch = self.room2
        self.rabbit.location = self.room1
        job = actions.plan_for(self.rabbit, "off_duty")
        self.assertEqual(job["steps"][0]["room"], self.room2.id)

    def test_already_there_is_not_a_journey(self):
        self.rabbit.db.soul_perch = self.room2
        self.assertIsNone(actions.plan_for(self.rabbit, "off_duty"))

    def test_rest_still_outranks_the_view(self):
        """The perch is an IDLE preference, not a bed. When rest bites
        it is a band-2 schedule goal and off_duty is band 4, so she
        goes home like everybody else."""
        from world.souls.engine import _goal_band
        self.assertLess(_goal_band("rest"), _goal_band("off_duty"))

    def test_a_deleted_perch_falls_back_home(self):
        """A builder can demolish a roof. She should not stand at the
        depot forever because her perch stopped existing."""
        roof = create_object("typeclasses.rooms.Room", key="a roof")
        self.rabbit.db.soul_perch = roof
        roof.delete()
        job = actions.plan_for(self.rabbit, "off_duty")
        self.assertEqual(job["steps"][0]["room"], self.room1.id)


class TestSheAsksForTheCrane(EvenniaCommandTest):
    """An NPC changing the world so it can path through it (#2301).

    The Longhaul container is a moving room: it docks level with the
    Kaspar Urgent Care roof at level 2 and reaches the Queen of Cups
    rack roof at level 12. BOTH ENDS ARE ROOFTOPS, so the only souls it
    is any use to are the ones who walk roofs — currently one person.

    She does not operate it. She asks, on band 27.0, through the same
    radio a player would key, and the console answers in Ossie's voice
    or doesn't. No back door: the operator can refuse, be absent, or
    ask her to confirm.
    """

    def setUp(self):
        super().setUp()
        self.rabbit = self.char1

    def _handset(self, on=True, freq=None):
        from evennia.prototypes.spawner import spawn
        from world import prototypes
        radio = spawn(prototypes.WALKIE_TALKIE)[0]
        radio.db.radio_on = on
        radio.db.frequency = freq
        radio.move_to(self.rabbit, quiet=True, move_hooks=False)
        return radio

    def test_no_handset_no_call(self):
        """She can't shout at a crane."""
        self.assertFalse(courier.call_the_crane(self.rabbit, 2))

    def test_she_keys_the_real_verb(self):
        self._handset(on=True, freq="27.0")
        with mock.patch.object(type(self.rabbit), "execute_cmd") as cmd:
            self.assertTrue(courier.call_the_crane(self.rabbit, 12))
        said = " ".join(c.args[0] for c in cmd.call_args_list)
        self.assertIn("xmit", said)
        self.assertIn("12", said)

    def test_she_switches_it_on_first(self):
        self._handset(on=False, freq="27.0")
        with mock.patch.object(type(self.rabbit), "execute_cmd") as cmd:
            courier.call_the_crane(self.rabbit, 2)
        self.assertIn("toggle", " ".join(c.args[0] for c in cmd.call_args_list))

    def test_she_tunes_to_the_crane_band(self):
        self._handset(on=True, freq="911")
        with mock.patch.object(type(self.rabbit), "execute_cmd") as cmd:
            courier.call_the_crane(self.rabbit, 2)
        said = " ".join(c.args[0] for c in cmd.call_args_list)
        self.assertIn("tune", said)
        self.assertIn(courier.CRANE_BAND, said)

    def test_already_tuned_means_no_fiddling(self):
        self._handset(on=True, freq="27.0")
        with mock.patch.object(type(self.rabbit), "execute_cmd") as cmd:
            courier.call_the_crane(self.rabbit, 2)
        said = " ".join(c.args[0] for c in cmd.call_args_list)
        self.assertNotIn("tune", said)
        self.assertNotIn("toggle", said)


class TestWhichLevelSheAsksFor(EvenniaCommandTest):
    """Inferred from where she's standing, not from route introspection.
    Nobody stands on that roof for the view, and the only reason to
    board is to cross at the top."""

    def test_somewhere_ordinary_wants_nothing(self):
        self.assertIsNone(courier.crane_level_wanted(self.char1))

    def test_aboard_and_low_means_up(self):
        from typeclasses.rooms import CraneContainer
        car = mock.MagicMock(spec=CraneContainer)
        car.MIN_Z, car.QOC_Z = 2, 12
        car.db.level = 2
        with mock.patch.object(courier, "_crane_car",
                               return_value=(car, "aboard")):
            self.assertEqual(courier.crane_level_wanted(self.char1), 12)

    def test_aboard_and_level_wants_nothing(self):
        from typeclasses.rooms import CraneContainer
        car = mock.MagicMock(spec=CraneContainer)
        car.MIN_Z, car.QOC_Z = 2, 12
        car.db.level = 12
        with mock.patch.object(courier, "_crane_car",
                               return_value=(car, "aboard")):
            self.assertIsNone(courier.crane_level_wanted(self.char1))

    def test_at_the_dock_with_the_box_up_top_means_down(self):
        from typeclasses.rooms import CraneContainer
        car = mock.MagicMock(spec=CraneContainer)
        car.MIN_Z, car.QOC_Z = 2, 12
        car.db.level = 12
        with mock.patch.object(courier, "_crane_car",
                               return_value=(car, "dock")):
            self.assertEqual(courier.crane_level_wanted(self.char1), 2)

    def test_the_walk_is_never_blocked_by_the_crane(self):
        """A broken crane must not strand a courier mid-route."""
        import inspect
        from world.souls import jobs
        src = inspect.getsource(jobs.step_job)
        travel = src[src.index('if do == "travel":'):src.index('if do == "buy":')]
        self.assertIn("crane_level_wanted", travel)
        self.assertIn("except Exception", travel)
