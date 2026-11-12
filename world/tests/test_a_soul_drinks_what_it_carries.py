"""A soul drinks what it carries, and what it buys (#3793).

Live, 2026-11-12: 12,091 of the 16,781 objects in the world were drinks
nobody had drunk. NPCs held 9,877 mugs of rotgut and 9,849 of them still
had all three sips; one soul carried 819.

The vice run's `consume` step typed `drink rotgut` and counted the
attempt. With a second mug in the pocket the command answers "Multiple
items match 'rotgut'." and no sip happens, so twelve refusals read as a
drink that "never finishes", the mug stayed, and the next craving bought
another. And the craving planner never looked in a pocket at all: it
planned a fresh purchase past whatever the soul already carried.

The meal had the same two faults and lost both in #2244. This pins the
vice run to the same behaviour, through the one loop both steps now
share (`jobs._serve_one`).

A run is ONE WARE'S WORTH. Both loops were written to keep going until
the soul carried nothing of the kind and to call the thirteenth serving a
ware that "never finishes". The meal really did that: seven bowls were
twelve bites and a false fault. The vice run never got as far as a sip,
and would have done the same the day it could drink.

Real objects and the real `drink` and `eat` commands throughout: the
defect lived in what the command does with a second mug, which a mocked
`execute_cmd` cannot show.
"""
import time as _time

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.bar import make_drink
from world.consumables import supports_delivery


class _CarriedWareBase(BaseEvenniaTest):
    """Game typeclasses and the game cmdset, as `test_craving` sets up:
    `apply_substance` needs a medical body and the `drink` verb lives on
    the game cmdset."""

    def setUp(self):
        super().setUp()
        from evennia.prototypes import prototypes as protomod
        if not protomod.search_prototype("doubleshift_lager"):
            protomod.load_module_prototypes("world.prototypes")
        self.game_room = create_object(
            "typeclasses.rooms.Room", key="back room")
        self.soul = create_object(
            "typeclasses.characters.Character", key="TestSoul",
            location=self.game_room)
        self.soul.cmdset.add(
            "commands.default_cmdsets.CharacterCmdSet", persistent=False)
        self.soul.tags.add("soul", category="npc_role")
        self.soul.db.soul_needs = {"hunger": 0.1, "_at": _time.time()}

    def mug(self, name="mug of rotgut", effects=None, sips=3):
        return make_drink(
            name=name, desc="A dented tin mug.", sips=sips,
            effects={"alcohol": 1} if effects is None else effects,
            location=self.soul, keywords=(name.split()[-1],))

    def bowl(self, bites=2):
        """Shaped like the shipped food prototypes: nutrition rides
        `drink_effects`, one dose a bite."""
        bowl = create_object(
            "typeclasses.items.Item", key="a bowl of kuro-nikomi stew",
            location=self.soul)
        bowl.tags.add("eat", category="delivery_method")
        bowl.db.drink_effects = {"nutrition": 1}
        bowl.db.uses_left = bites
        return bowl

    def addict(self, substance="alcohol"):
        from world.medical.conditions import AddictionCondition
        cond = AddictionCondition(substance, craving_after=3600)
        cond.last_dose_time = _time.time() - 7200
        self.soul.medical_state.add_condition(cond)
        return cond

    def drinks_carried(self):
        return [o for o in self.soul.contents if supports_delivery(o, "drink")]

    def sips_carried(self):
        return sum(int(o.db.uses_left) for o in self.drinks_carried())

    def give_job(self, goal, do, **step):
        self.soul.db.soul_job = {
            "goal": goal, "at": 0, "steps": [dict(step, do=do)]}

    def run_job(self, beats=40):
        """Step the job to its end. Returns how many beats it took."""
        from world.souls import jobs
        for beat in range(1, beats + 1):
            if not jobs.step_job(self.soul):
                return beat
        self.fail("the job never ended")

    def thought_kinds(self):
        return [t[1] for t in (self.soul.db.soul_thoughts or [])]

    def last_fault(self):
        faults = self.soul.db.soul_faults or []
        return faults[-1][1] if faults else None


class TestTheDrinkStepDrinks(_CarriedWareBase):
    def setUp(self):
        super().setUp()
        self.habit = self.addict()  # the run judges whether the itch eased

    def test_the_drink_command_itself_works_here(self):
        """The control for everything below: with one mug the plain verb
        sips, so a failure further down is the step and not the rig."""
        mug = self.mug()
        self.soul.execute_cmd("drink rotgut")
        self.assertEqual(mug.db.uses_left, 2)

    def test_two_mugs_make_the_bare_name_ambiguous(self):
        """What the step used to type, and why it never drank: this is
        the command's own behaviour, pinned so the step's reason stays
        true."""
        self.mug()
        self.mug()
        self.soul.execute_cmd("drink rotgut")
        self.assertEqual(self.sips_carried(), 6)

    def test_one_mug_goes_down_sip_by_sip(self):
        from world.souls import jobs
        self.mug()
        self.give_job("craving", "consume", verb="drink")
        for left in (2, 1, 0):
            self.assertTrue(jobs.step_job(self.soul))
            self.assertEqual(self.sips_carried(), left)
        self.run_job()
        self.assertIsNone(self.last_fault())
        self.assertIn("took_the_edge_off", self.thought_kinds())

    def test_a_second_mug_does_not_stop_the_drinking(self):
        """THE defect. Before the fix the step counted a sip here and
        both mugs stayed full."""
        from world.souls import jobs
        self.mug()
        self.mug()
        self.give_job("craving", "consume", verb="drink")
        self.assertTrue(jobs.step_job(self.soul))
        self.assertEqual(self.sips_carried(), 5)
        self.assertIsNone(self.last_fault())

    def test_a_run_is_one_mug_s_worth_and_ends_clean(self):
        """Five mugs are fifteen sips. The run has a drink, not the
        pocket: three sips, the thought, no fault. A loop that runs to
        the end of the pocket takes twelve and then faults that the mug
        "never finishes", which is what the meal did with seven bowls."""
        for _ in range(5):
            self.mug()
        self.give_job("craving", "consume", verb="drink")
        self.run_job()
        self.assertEqual(len(self.drinks_carried()), 4)
        self.assertEqual(self.sips_carried(), 12)
        self.assertIsNone(self.last_fault())
        self.assertIn("took_the_edge_off", self.thought_kinds())
        self.assertIsNone(self.soul.db.soul_job)

    def test_a_deep_bottle_is_a_sitting_not_a_fault(self):
        """A ware holding more than a sitting's worth is put away part
        drunk. It is not a ware that never finishes."""
        from world.souls import jobs
        bottle = self.mug(name="jug of rotgut", sips=20)
        self.give_job("craving", "consume", verb="drink")
        self.run_job()
        self.assertEqual(bottle.db.uses_left, 20 - jobs.SERVINGS_PER_RUN)
        self.assertIsNone(self.last_fault())

    def test_a_refused_sip_is_a_fault_and_not_a_sip(self):
        """Counting the attempt is what hid this for seven weeks. A soul
        that cannot drink stops and says so, at once."""
        from world.souls import jobs
        self.mug()
        self.give_job("craving", "consume", verb="drink")
        real = self.soul.execute_cmd
        self.soul.execute_cmd = lambda *a, **kw: None      # the verb refuses
        try:
            self.assertFalse(jobs.step_job(self.soul))
        finally:
            self.soul.execute_cmd = real
        self.assertEqual(self.last_fault(), "could not drink mug of rotgut")
        self.assertIsNone(self.soul.db.soul_job)
        self.assertEqual(self.sips_carried(), 3)

    def test_the_baseline_is_taken_once(self):
        """A job outlives a reload, and the craving is already quiet
        after the first sip. A run picked up part-way keeps the pressure
        it started from: measured again it would read as a drink that
        did nothing."""
        from world.souls import needs
        self.habit.record_dose()               # the sip before the reload
        self.assertEqual(needs.craving_pressure(self.soul), 0.0)
        self.mug(sips=2)
        self.give_job("craving", "consume", verb="drink", start_p=0.7)
        self.run_job()
        self.assertEqual(self.drinks_carried(), [])
        self.assertIsNone(self.last_fault())
        self.assertIn("took_the_edge_off", self.thought_kinds())

    def test_empty_hands_are_a_fault(self):
        from world.souls import jobs
        self.give_job("craving", "consume", verb="drink")
        self.assertFalse(jobs.step_job(self.soul))
        self.assertEqual(self.last_fault(), "nothing to drink in hand")

    def test_the_step_says_which_one(self):
        """The syntax a player would use to narrow a twin."""
        from world.souls import jobs
        self.mug()
        typed = []
        real = self.soul.execute_cmd

        def spy(raw, *a, **kw):
            typed.append(raw)
            return real(raw, *a, **kw)

        self.soul.execute_cmd = spy
        self.give_job("craving", "consume", verb="drink")
        try:
            jobs.step_job(self.soul)
        finally:
            self.soul.execute_cmd = real
        self.assertEqual(typed, ["drink first rotgut"])

    def test_the_run_drinks_the_ware_it_was_given(self):
        """A soda water carried ahead of the rotgut is not what the
        craving is about. The plan names the ware and the run keeps to
        it."""
        soda = self.mug(name="glass of soda water", effects={})
        rotgut = self.mug()
        self.give_job("craving", "consume", verb="drink", item=rotgut.id)
        self.run_job()
        self.assertEqual([o.key for o in self.drinks_carried()],
                         ["glass of soda water"])
        self.assertEqual(soda.db.uses_left, 3)
        self.assertIsNone(self.last_fault())

    def test_without_a_named_ware_the_run_takes_the_first_carried(self):
        """The control for the test above: unnamed, the soda goes down
        and the run reports that it did nothing for the craving."""
        self.mug(name="glass of soda water", effects={})
        rotgut = self.mug()
        self.give_job("craving", "consume", verb="drink")
        self.run_job()
        self.assertEqual(rotgut.db.uses_left, 3)
        self.assertIn("didn't scratch the itch", self.last_fault())


class TestTheStepBeforeNamesTheWare(_CarriedWareBase):
    """`buy` and `pickup` tell the mouth which ware they just handed
    over (`jobs._hand_on`)."""

    def job(self, *does):
        return {"goal": "craving", "at": 0,
                "steps": [dict(step) for step in does]}

    def test_the_new_ware_is_named_to_a_drinking_step(self):
        from world.souls import jobs
        old = self.mug(name="glass of soda water", effects={})
        job = self.job({"do": "buy"}, {"do": "consume", "verb": "drink"})
        before = {old.id}
        new = self.mug()
        self.assertTrue(jobs._hand_on(self.soul, job, 0, before))
        self.assertEqual(job["steps"][1]["item"], new.id)

    def test_the_new_ware_is_named_to_an_eating_step(self):
        from world.souls import jobs
        job = self.job({"do": "pickup"}, {"do": "eat"})
        new = self.bowl()
        self.assertTrue(jobs._hand_on(self.soul, job, 0, set()))
        self.assertEqual(job["steps"][1]["item"], new.id)

    def test_only_a_ware_the_next_step_can_use_is_named(self):
        """A drink handed to a step that eats is not its ware."""
        from world.souls import jobs
        job = self.job({"do": "buy"}, {"do": "eat"})
        self.mug()
        self.assertTrue(jobs._hand_on(self.soul, job, 0, set()))
        self.assertNotIn("item", job["steps"][1])

    def test_a_step_that_does_not_consume_is_left_alone(self):
        from world.souls import jobs
        job = self.job({"do": "buy"}, {"do": "wear"})
        self.mug()
        self.assertTrue(jobs._hand_on(self.soul, job, 0, set()))
        self.assertNotIn("item", job["steps"][1])

    def test_nothing_new_is_reported_as_nothing(self):
        from world.souls import jobs
        old = self.mug()
        job = self.job({"do": "buy"}, {"do": "consume", "verb": "drink"})
        self.assertFalse(jobs._hand_on(self.soul, job, 0, {old.id}))
        self.assertNotIn("item", job["steps"][1])

    def test_the_last_step_of_a_job_has_nobody_to_tell(self):
        from world.souls import jobs
        job = self.job({"do": "buy"})
        self.mug()
        self.assertTrue(jobs._hand_on(self.soul, job, 0, set()))


class TestWhatWasBoughtIsWhatIsDrunk(_CarriedWareBase):
    """The steps run together through `step_job`: the soul carries a
    soda water it has no use for, acquires the drink it came for, and
    drinks THAT."""

    def setUp(self):
        super().setUp()
        self.addict()
        self.soda = self.mug(name="glass of soda water", effects={})

    def assert_the_soda_is_untouched_and_nothing_else_is_left(self):
        self.assertEqual([o.key for o in self.drinks_carried()],
                         ["glass of soda water"])
        self.assertEqual(self.soda.db.uses_left, 3)
        self.assertIsNone(self.last_fault())
        self.assertIn("took_the_edge_off", self.thought_kinds())

    def test_a_drink_lifted_off_the_counter(self):
        """`pickup` with the real `get ... from ...`."""
        counter = create_object(
            "typeclasses.bar.BarCounter", key="the test bar",
            location=self.game_room)
        make_drink(name="mug of rotgut", desc="A dented tin mug.", sips=3,
                   effects={"alcohol": 1}, location=counter,
                   keywords=("rotgut",))
        self.soul.db.soul_job = {"goal": "craving", "at": 0, "steps": [
            {"do": "pickup", "counter": counter.id, "verb": "drink",
             "want": "mug of rotgut"},
            {"do": "consume", "verb": "drink"}]}
        self.run_job()
        self.assertEqual(counter.contents, [])
        self.assert_the_soda_is_untouched_and_nothing_else_is_left()

    def test_a_drink_bought_off_the_shelf(self):
        """`buy`, with the till stood in for: the sale is the shop's
        business, the ware arriving in the hand is this step's."""
        from evennia.prototypes.spawner import spawn
        shelf = create_object(
            "typeclasses.items.Item", key="vice counter",
            location=self.game_room)
        real = self.soul.execute_cmd

        def sold(raw, *a, **kw):
            if raw.startswith("buy "):
                spawn("doubleshift_lager")[0].move_to(self.soul, quiet=True)
                return None
            return real(raw, *a, **kw)

        self.soul.execute_cmd = sold
        self.soul.db.soul_job = {"goal": "craving", "at": 0, "steps": [
            {"do": "buy", "counter": shelf.id, "proto": "doubleshift_lager",
             "price": 3},
            {"do": "consume", "verb": "drink"}]}
        try:
            self.run_job()
        finally:
            self.soul.execute_cmd = real
        self.assert_the_soda_is_untouched_and_nothing_else_is_left()


class TestTheMealStepStillEats(_CarriedWareBase):
    """The meal moved onto the shared loop. Same command, same fault
    text, and a second bowl still does not stop it (#2244)."""

    def setUp(self):
        super().setUp()
        self.soul.db.soul_needs = {"hunger": 0.8, "_at": _time.time()}

    def bowls_carried(self):
        return [o for o in self.soul.contents if supports_delivery(o, "eat")]

    def bites_carried(self):
        return sum(int(o.db.uses_left) for o in self.bowls_carried())

    def test_the_eat_command_itself_works_here(self):
        """The control: one bowl, the plain verb, a bite gone."""
        bowl = self.bowl()
        self.soul.execute_cmd("eat stew")
        self.assertEqual(bowl.db.uses_left, 1)

    def test_a_second_bowl_does_not_stop_the_meal(self):
        from world.souls import jobs
        self.bowl()
        self.bowl()
        self.give_job("hunger", "eat")
        self.assertTrue(jobs.step_job(self.soul))
        self.assertEqual(self.bites_carried(), 3)
        self.assertIsNone(self.last_fault())

    def test_a_meal_is_one_bowl_and_ends_clean(self):
        """Seven bowls are fourteen bites. The meal is a bowl: it ate
        twelve bites and then faulted that the stew "never finishes"."""
        for _ in range(7):
            self.bowl()
        self.give_job("hunger", "eat")
        self.run_job()
        self.assertEqual(len(self.bowls_carried()), 6)
        self.assertIsNone(self.last_fault())
        self.assertIn("ate_well", self.thought_kinds())

    def test_a_refused_bite_is_a_fault_and_not_a_bite(self):
        from world.souls import jobs
        self.bowl()
        self.give_job("hunger", "eat")
        real = self.soul.execute_cmd
        self.soul.execute_cmd = lambda *a, **kw: None
        try:
            self.assertFalse(jobs.step_job(self.soul))
        finally:
            self.soul.execute_cmd = real
        self.assertEqual(self.last_fault(),
                         "could not eat a bowl of kuro-nikomi stew")
        self.assertEqual(self.bites_carried(), 2)

    def test_empty_hands_are_a_fault(self):
        from world.souls import jobs
        self.give_job("hunger", "eat")
        self.assertFalse(jobs.step_job(self.soul))
        self.assertEqual(self.last_fault(), "nothing edible in hand")


class TestTheCravingChecksItsPockets(_CarriedWareBase):
    def setUp(self):
        super().setUp()
        from world.souls import actions
        counter = create_object(
            "typeclasses.items.Item", key="vice counter",
            location=self.game_room)
        counter.db.prototype_inventory = {"doubleshift_lager": 3}
        counter.db.advertises = {"vice": 0.9}
        counter.tags.add("advertiser", category="souls")
        actions._ad_cache["at"] = 0.0          # bust the registry cache
        self.soul.tokens = 20
        self.addict()

    def plan(self):
        from world.souls import actions
        plan = actions.plan_for(self.soul, "craving")
        return [s["do"] for s in plan["steps"]] if plan else None

    def test_with_empty_pockets_the_soul_goes_and_buys(self):
        """The control: the counter is reachable and affordable."""
        self.assertEqual(self.plan(), ["travel", "buy", "consume"])

    def test_a_carried_drink_is_drunk_before_another_is_bought(self):
        self.mug()
        self.assertEqual(self.plan(), ["consume"])

    def test_the_plan_names_the_carried_ware_and_its_verb(self):
        from world.souls import actions
        mug = self.mug()
        plan = actions.plan_for(self.soul, "craving")
        self.assertEqual(plan["steps"], [
            {"do": "consume", "verb": "drink", "item": mug.id}])
        self.assertEqual(plan["goal"], "craving")

    def test_the_plan_names_the_ware_that_answers_the_craving(self):
        """Not the first drinkable in the pocket: the one with the
        craved substance in it."""
        from world.souls import actions
        self.mug(name="glass of soda water", effects={})
        self.mug(name="mug of black recyc", effects={"caffeine": 1})
        rotgut = self.mug()
        plan = actions.plan_for(self.soul, "craving")
        self.assertEqual(plan["steps"][0]["item"], rotgut.id)

    def test_a_drink_without_the_craved_substance_does_not_count(self):
        self.mug(name="mug of black recyc", effects={"caffeine": 1})
        self.assertEqual(self.plan(), ["travel", "buy", "consume"])

    def test_a_flavour_only_drink_does_not_count(self):
        self.mug(name="glass of soda water", effects={})
        self.assertEqual(self.plan(), ["travel", "buy", "consume"])

    def test_a_ware_that_names_one_substance_counts(self):
        """A shelf ware carries `db.substance`, not a recipe's map."""
        can = create_object(
            "typeclasses.items.Item", key="can of lager", location=self.soul)
        can.tags.add("drink", category="delivery_method")
        can.db.substance = "alcohol"
        can.db.uses_left = 1
        self.assertEqual(self.plan(), ["consume"])

    def test_a_carried_garment_is_not_a_drink(self):
        create_object("typeclasses.items.Item", key="flannel shirt",
                      location=self.soul)
        self.assertEqual(self.plan(), ["travel", "buy", "consume"])

    def test_a_carried_smoke_is_not_planned(self):
        """No smoking, as for a ware on a shelf: lighting is a real
        dependency a soul does not manage. The cigarette carries the
        craved leaf and still does not count, because neither `drink`
        nor `eat` takes it. Without the verb test the plan would be to
        drink a cigarette, refused at every craving."""
        from world.souls import actions
        tobacco = self.addict("tobacco_neutral")
        self.assertIsNotNone(tobacco)
        smoke = create_object(
            "typeclasses.items.Item", key="cigarette", location=self.soul)
        smoke.tags.add("smoke", category="delivery_method")
        smoke.db.substance = "tobacco_neutral"
        self.assertIsNone(actions._carried_vice(self.soul, "tobacco_neutral"))
        plug = create_object(
            "typeclasses.items.Item", key="plug of chewing tobacco",
            location=self.soul)
        plug.tags.add("eat", category="delivery_method")
        plug.db.drink_effects = {"tobacco_neutral": 1}
        self.assertEqual(
            actions._carried_vice(self.soul, "tobacco_neutral"),
            (plug, "eat"))

    def test_pockets_then_the_run_ends_the_craving_with_nothing_bought(self):
        """Plan and steps together: a soda and two mugs carried. One mug
        is drunk, nothing is bought, the soda is untouched and the habit
        is fed."""
        from world.souls import actions, needs
        soda = self.mug(name="glass of soda water", effects={})
        self.mug()
        self.mug()
        before = set(o.id for o in self.soul.contents)
        self.soul.db.soul_job = actions.plan_for(self.soul, "craving")
        self.run_job()
        self.assertEqual(sorted(o.key for o in self.drinks_carried()),
                         ["glass of soda water", "mug of rotgut"])
        self.assertEqual(soda.db.uses_left, 3)
        self.assertFalse(set(o.id for o in self.soul.contents) - before)
        self.assertEqual(needs.craving_pressure(self.soul), 0.0)
        self.assertEqual(self.soul.tokens, 20)
        self.assertIsNone(self.last_fault())



class TestTheHungerChecksItsPocketsForFood(_CarriedWareBase):
    def setUp(self):
        super().setUp()
        from world.souls import actions
        counter = create_object(
            "typeclasses.items.Item", key="food counter",
            location=self.game_room)
        counter.db.prototype_inventory = {"mystery_skewer": 3}
        counter.db.advertises = {"hunger": 0.9}
        counter.tags.add("advertiser", category="souls")
        actions._ad_cache["at"] = 0.0          # bust the registry cache
        self.soul.tokens = 20
        self.soul.db.soul_needs = {"hunger": 0.8, "_at": _time.time()}

    def plug(self):
        """The shipped chewing tobacco: the eat verb works on it and it
        feeds nobody."""
        from evennia.prototypes.spawner import spawn
        plug = spawn("chewing_tobacco_plug")[0]
        plug.move_to(self.soul, quiet=True)
        return plug

    def plan(self):
        from world.souls import actions
        return actions.plan_for(self.soul, "hunger")

    def test_with_empty_pockets_the_soul_goes_and_buys(self):
        """The control: the counter is reachable and affordable."""
        self.assertEqual([s["do"] for s in self.plan()["steps"]],
                         ["travel", "buy", "eat"])

    def test_carried_food_is_eaten_and_named(self):
        bowl = self.bowl()
        self.assertEqual(self.plan()["steps"],
                         [{"do": "eat", "item": bowl.id}])

    def test_a_plug_of_tobacco_is_not_a_meal(self):
        """Eatable, and not food: the soul still goes and buys."""
        self.plug()
        self.assertEqual([s["do"] for s in self.plan()["steps"]],
                         ["travel", "buy", "eat"])

    def test_the_meal_is_the_food_and_not_the_plug_beside_it(self):
        """A meal is one ware, so which ware matters: carried ahead of
        the stew, the plug was the meal, it fed nobody, and the stew
        stayed in the pocket."""
        plug = self.plug()
        bowl = self.bowl()
        self.assertEqual(self.plan()["steps"],
                         [{"do": "eat", "item": bowl.id}])
        self.soul.db.soul_job = self.plan()
        self.run_job()
        self.assertEqual(plug.db.uses_left, 4)
        self.assertIsNone(bowl.pk)
        self.assertIsNone(self.last_fault())
        self.assertIn("ate_well", self.thought_kinds())
