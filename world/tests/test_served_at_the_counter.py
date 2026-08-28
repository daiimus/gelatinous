"""Nobody could be served at a counter (#2342).

The Snailery is a sit-down restaurant that worked like a vending
machine, and that was not a mistake in the build: the shop model was the
only model souls could use. Ordering is directed speech, `to` takes a
single-token target, identity gates the name — so a soul (and a stranger)
could read a menu and had no way to act on it.

Three doors exist now, and the VENUE picks which one opens: a tended
board is ordered from, a serving fixture is grazed, a shelf is bought
from. These pin each door open and pin the other two shut.
"""

from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.consumables import supports_delivery
from world.souls import actions, jobs

#: a plated board entry — a real prototype comes off the grill
DISH = {
    "name": "snail skewer",
    "order_keywords": ("skewer", "snails"),
    "proto": "snail_skewer",
    "price": 3,
    "craft": "lifts a skewer off the grill",
}

#: a mixed board entry — the drink path the bar was built on
POUR = {
    "name": "mug of rotgut",
    "order_keywords": ("rotgut",),
    "price": 2,
    "effects": {"alcohol": 3},
}


class _CounterTest(EvenniaCommandTest):
    """A counter with a board and somebody working it."""

    def setUp(self):
        super().setUp()
        self.counter = create_object(
            "typeclasses.bar.BarCounter", key="the shell counter",
            location=self.room1)
        self.counter.db.menu = [DISH]
        self.tender = create_object(
            "typeclasses.bar.Bartender", key="Nonna", location=self.room1)
        self.patron = self.char1
        self.patron.location = self.room1
        self.patron.tokens = 10


class TestTheOrderCommand(_CounterTest):
    """`order <thing>` is directed speech with the targeting done for you."""

    def _order(self, text):
        import typeclasses.bar as barmod
        return self.call(barmod.CmdOrder(), text,
                         caller=self.patron, obj=self.counter)

    def test_the_order_reaches_the_tender(self):
        """The whole point: no name needed. Live, this patron resolves
        nothing — identity gates 'Nonna', and the sdesc that would
        resolve ('a wiry woman') is shared by half the room."""
        with mock.patch("world.speech.broadcast_speech") as heard:
            self._order("skewer")
        self.assertTrue(heard.called)
        self.assertIs(heard.call_args.kwargs.get("target"), self.tender)

    def test_the_order_is_spoken_aloud(self):
        """Not a private channel: the room hears you order."""
        with mock.patch("world.speech.broadcast_speech") as heard:
            self._order("skewer")
        self.assertEqual(heard.call_args.args[1], "skewer")

    def test_an_unworked_counter_takes_no_orders(self):
        self.tender.delete()
        self.assertIn("nobody working", self._order("skewer"))

    def test_ordering_nothing_asks_what(self):
        self.assertIn("Order what?", self._order(""))


class TestAMenuThatPlatesADish(_CounterTest):
    """A board entry naming a `proto` serves that real item."""

    def test_a_plated_entry_becomes_the_real_food(self):
        dish = self.tender._make_order(DISH, self.counter)
        self.assertEqual(dish.location, self.counter)
        self.assertTrue(supports_delivery(dish, "eat"))

    def test_a_mixed_entry_is_still_a_drink(self):
        drink = self.tender._make_order(POUR, self.counter)
        self.assertEqual(drink.location, self.counter)
        self.assertTrue(supports_delivery(drink, "drink"))

    def test_a_prototype_that_does_not_exist_serves_nothing(self):
        self.assertIsNone(self.tender._make_order(
            {"name": "ghost", "proto": "no_such_prototype_at_all"},
            self.counter))

    def test_the_dish_lands_on_the_counter_and_the_till_takes_the_cash(self):
        """The whole gesture, through the real serve path: made on the
        surface, payment swept, nothing pressed into a hand."""
        self.tender._fulfil_order("skewer", self.patron)
        served = [o for o in self.counter.contents
                  if supports_delivery(o, "eat")]
        self.assertEqual(len(served), 1)
        self.assertEqual(self.patron.tokens, 7)
        self.assertEqual(self.counter.db.register, 3)

    def test_a_patron_who_cannot_pay_is_not_served(self):
        self.patron.tokens = 1
        self.tender._fulfil_order("skewer", self.patron)
        self.assertEqual(self.counter.contents, [])
        self.assertEqual(self.patron.tokens, 1)


class TestTheVenueChoosesTheDoor(_CounterTest):
    """The planner reads the venue, not the soul's species."""

    def setUp(self):
        super().setUp()
        self.soul = self.patron
        self.counter.db.advertises = {"hunger": 0.9}
        # advertisers are found by an INDEXED TAG (hardening law #3)
        self.counter.tags.add("advertiser", category="souls")

    def _doors(self, need="hunger"):
        actions._ad_cache["at"] = 0          # the cache has a TTL
        plan = actions.plan_for(self.soul, need)
        return [step["do"] for step in plan["steps"]] if plan else None

    def test_a_tended_board_is_ordered_from(self):
        self.assertEqual(self._doors(),
                         ["travel", "order", "pickup", "eat"])

    def test_an_unworked_board_is_not(self):
        """Nobody behind it, nobody to ask — and no shelf to fall back
        on, so the soul walks somewhere else."""
        self.tender.delete()
        self.assertIsNone(self._doors())

    def test_a_board_nobody_can_afford_is_not_worth_the_walk(self):
        self.soul.tokens = 1
        self.assertIsNone(self._doors())

    def test_a_shelf_is_still_bought_from(self):
        """Regression: the shop door must not have moved."""
        self.counter.db.menu = None
        self.counter.db.prototype_inventory = {"snail_skewer": 3}
        self.assertEqual(self._doors(), ["travel", "buy", "eat"])

    def test_a_serving_fixture_is_still_grazed(self):
        """The Rook's nutrient line (#2074), untouched."""
        self.counter.db.menu = None
        self.counter.db.snacks = [{"name": "paste",
                                   "order_keywords": ("paste",),
                                   "effects": {"nutrition": 2}}]
        self.assertEqual(self._doors(), ["travel", "graze"])

    def test_a_recluse_is_never_served(self):
        """The seal is the story: a recluse grazes and does nothing
        else, even standing at a board with a tender behind it."""
        self.soul.db.soul_profile = "recluse"
        self.assertIsNone(self._doors())

    def test_free_snacks_do_not_feed_anyone(self):
        """Bar snacks carry no nutrition on purpose. If they ever did,
        bottomless free food would end hunger for the whole colony."""
        from world.bar import DEFAULT_BAR_SNACKS
        for snack in DEFAULT_BAR_SNACKS:
            self.assertFalse((snack.get("effects") or {}).get("nutrition"),
                             f"{snack['name']} would feed the colony free")


class TestTheCravingDoor(_CounterTest):
    """An addict can be poured a drink, not just sold a bottle."""

    def setUp(self):
        super().setUp()
        self.soul = self.patron
        self.counter.db.menu = [POUR]
        self.counter.db.advertises = {"vice": 0.9}
        self.counter.tags.add("advertiser", category="souls")

    def _doors(self):
        actions._ad_cache["at"] = 0
        with mock.patch("world.souls.needs.craving_state",
                        return_value=(0.9, "alcohol")):
            plan = actions.plan_for(self.soul, "craving")
        return [step["do"] for step in plan["steps"]] if plan else None

    def test_a_bar_can_answer_a_craving(self):
        self.assertEqual(self._doors(),
                         ["travel", "order", "pickup", "consume"])

    def test_a_board_without_the_substance_does_not(self):
        self.counter.db.menu = [DISH]
        self.assertIsNone(self._doors())


class TestTakingWhatWasSetDown(_CounterTest):
    """The `pickup` step: a pair of hands, not a purchase."""

    def setUp(self):
        super().setUp()
        self.soul = self.patron
        self.soul.db.soul_job = {"goal": "hunger", "at": 0, "steps": [
            {"do": "pickup", "counter": self.counter.id, "verb": "eat",
             "want": "snail skewer"},
        ]}

    def _step(self):
        """Run the step, capturing the real command it issues.

        A soul acts through commands and nothing else; in the live
        server they run inline, but under test they land on the reactor,
        so the command is captured here and its effect applied directly.
        """
        self.said = []

        def _ran(cmdstring, **kwargs):
            self.said.append(cmdstring)
            if cmdstring.startswith("get "):
                for obj in list(self.counter.contents):
                    if obj.key in cmdstring:
                        obj.move_to(self.soul, quiet=True)

        with mock.patch.object(type(self.soul), "execute_cmd",
                               side_effect=_ran):
            return jobs.step_job(self.soul)

    def test_it_lifts_the_dish_off_the_counter(self):
        self.tender._make_order(DISH, self.counter)
        self.assertTrue(self._step())
        self.assertTrue(any(supports_delivery(o, "eat")
                            for o in self.soul.contents))
        self.assertIn("from the shell counter", self.said[0])

    def test_it_waits_while_the_tender_is_still_working(self):
        """The order rides a delay and can route through the model on
        its way. Standing at the counter for a beat is correct."""
        with mock.patch.object(jobs, "fault") as faulted:
            self.assertTrue(self._step())
        faulted.assert_not_called()
        self.assertEqual(self.soul.db.soul_job["at"], 0)

    def test_a_counter_that_never_serves_eventually_faults(self):
        with mock.patch.object(jobs, "fault") as faulted:
            for _ in range(5):
                self._step()
        self.assertTrue(faulted.called)
        self.assertIn("nothing came", str(faulted.call_args))

    def test_it_takes_the_dish_it_asked_for(self):
        """Two souls at one counter: take yours, not theirs."""
        self.tender._make_order(POUR, self.counter)
        mine = self.tender._make_order(DISH, self.counter)
        self._step()
        self.assertIn(mine, self.soul.contents)
        self.assertNotIn("rotgut", self.said[0])


class TestHoldingThePostIsTheQualification(_CounterTest):
    """The Hub and Howl bug (#2350).

    Its swing and night keepers hold the bartender post, carry
    `soul_role='bartender'`, stand behind the bar — and could not pour a
    drink, because `_fulfil_order` was welded to a class they are not.
    Two thirds of every day, the busiest bar in the colony could not
    serve. Competence belongs to the post.
    """

    def setUp(self):
        super().setUp()
        from world.souls.posts import register_post
        self.tender.delete()
        # a bare LLMNpc — no Bartender class in sight
        self.plain = create_object("typeclasses.llm_npc.LLMNpc",
                                   key="Bianca", location=self.room1)
        register_post(self.counter, "bartender", shifts=("day",))
        self.counter.db.post_slots = {
            "day": {"keeper": self.plain, "vacant_since": None}}

    def _speak(self, line, addressed=True):
        with mock.patch("world.souls.posts.current_shift",
                        return_value="day"):
            return self.plain._handle_directed_speech(
                line, self.patron, {"addressed": addressed})

    def test_a_plain_npc_on_the_post_serves(self):
        self.assertTrue(self._speak("a skewer"))

    def test_and_the_dish_actually_lands(self):
        from world.bar import fulfil_now
        with mock.patch("world.souls.posts.current_shift",
                        return_value="day"):
            self.assertTrue(
                fulfil_now(self.counter, "skewer", self.patron, self.plain))
        self.assertTrue(any(supports_delivery(o, "eat")
                            for o in self.counter.contents))

    def test_conversation_is_still_conversation(self):
        """A refusal falls through to the voice — the post only claims
        what it can actually serve."""
        self.assertFalse(self._speak("long night?"))

    def test_off_shift_the_post_does_not_answer(self):
        with mock.patch("world.souls.posts.current_shift",
                        return_value="night"):
            handled = self.plain._handle_directed_speech(
                "a skewer", self.patron, {"addressed": True})
        self.assertFalse(handled)


class TestWhoIsWorkingTheCounter(_CounterTest):
    """One reading of the question, so the command and the planner
    cannot disagree with the till."""

    def test_an_unposted_counter_falls_back_to_whoever_is_here(self):
        from world.bar import tender_at
        self.assertIs(tender_at(self.counter), self.tender)

    def test_a_posted_counter_answers_to_the_clock(self):
        """A bartender standing in the room after hours cannot be
        pressed into serving — the rule that stops a proprietor selling
        at midnight."""
        from world.bar import tender_at
        self.counter.db.post_slots = {"day": {"keeper": None}}
        with mock.patch("world.souls.posts.current_shift",
                        return_value="night"):
            self.assertIsNone(tender_at(self.counter))

    def test_the_fact_and_the_person_agree(self):
        from world.souls.posts import any_keeper_present, keeper_on_duty
        self.counter.db.post_slots = {
            "day": {"keeper": self.tender}}
        with mock.patch("world.souls.posts.current_shift",
                        return_value="day"):
            self.assertIs(keeper_on_duty(self.counter), self.tender)
            self.assertTrue(any_keeper_present(self.counter))
