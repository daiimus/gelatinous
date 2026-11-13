"""The keeper of a food counter eats from their own board, on the house
(#3802).

Owner ruling 2026-11-13, choosing among four ways to feed them: *"A and
their meal should as a result be complimentary."* A was: the keeper
makes it themselves, with the `prepare` command a player behind the
counter already has.

Live, 2026-11-13: the night keeper of the Snailery stood behind the
stew at hunger 1.00 for three and a half hours. Nobody can serve a
keeper at their own counter (#2364), the only other open seller wanted
three tokens and they had none, so the planner had no plan and said so
every fifteen minutes. The three keepers of that counter made 31 of the
colony's 79 hungry-with-no-plan faults in eighteen hours.

Real objects and real commands throughout: the real board entry shape,
the real prototype, `prepare`, `get ... from ...` and `eat`. What is
under test is that a bowl gets made, lifted and eaten, and that nobody
is charged for it.
"""
import datetime
import time
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.souls import actions, jobs, needs

#: the Snailery's board as it stands live: the staple is free, the rest
#: are not
STEW = {
    "name": "bowl of kuro-nikomi",
    "order_keywords": ("kuro", "nikomi", "stew"),
    "proto": "snail_kuro",
    "price": 0,
    "craft": "ladles the black stew up out of the pot",
}
SKEWER = {
    "name": "grilled snail skewer",
    "order_keywords": ("skewer", "grilled"),
    "proto": "snail_skewer",
    "price": 3,
    "craft": "lays six on the grill-pan",
}
#: what a bar pours: on a board, and not food
POUR = {
    "name": "mug of rotgut",
    "order_keywords": ("rotgut",),
    "price": 0,
    "effects": {"alcohol": 3},
}
NOON = datetime.datetime(2026, 11, 13, 12, 0)     # the day shift


class _KitchenCase(EvenniaTest):
    """A counter with the day keeper behind it and a customer in front.

    `EvenniaTest`, not the `Base` one: the board names real prototypes,
    and the base class resets the settings that register them."""

    def setUp(self):
        super().setUp()
        clock = mock.patch("world.gametime.colony_now", return_value=NOON)
        clock.start()
        self.addCleanup(clock.stop)
        self.yard = create_object("typeclasses.rooms.Room", key="yard")
        self.counter = create_object(
            "typeclasses.bar.BarCounter", key="the shell counter",
            location=self.yard)
        self.counter.db.menu = [SKEWER, STEW]
        self.counter.db.register = 0
        self.keeper = self.soul("Keeper")
        self.relief = self.soul("Relief")
        self.patron = self.soul("Patron")
        self.counter.db.post_slots = {
            "day": {"keeper": self.keeper},
            "swing": {"keeper": self.relief}}

    def soul(self, key):
        npc = create_object(
            "typeclasses.characters.Character", key=key, location=self.yard)
        npc.tags.add("soul", category="npc_role")
        npc.db.soul_needs = {"hunger": 0.9, "_at": time.time()}
        npc.tokens = 0
        return npc

    def plan(self, who):
        return actions._feed_at(who, self.counter, "buy_consume")

    def doing(self, steps):
        return [step["do"] for step in steps or []]


class TestThePlan(_KitchenCase):
    def test_the_keeper_prepares_it_themselves(self):
        steps = self.plan(self.keeper)
        self.assertEqual(self.doing(steps), ["prepare", "pickup", "eat"],
                         "the keeper had no way to eat at their own counter")
        self.assertEqual(steps[0]["counter"], self.counter.id)
        self.assertEqual(steps[1]["counter"], self.counter.id)

    def test_they_take_the_house_staple(self):
        """The cheapest thing on the board, wherever it is listed."""
        steps = self.plan(self.keeper)
        self.assertEqual(steps[0]["word"], "kuro")
        self.assertEqual(steps[0]["want"], STEW["name"])

    def test_it_is_on_the_house(self):
        """Complimentary: a board with nothing free on it still feeds
        a keeper who has nothing."""
        self.counter.db.menu = [SKEWER]
        self.assertEqual(self.keeper.tokens, 0)
        steps = self.plan(self.keeper)
        self.assertEqual(self.doing(steps), ["prepare", "pickup", "eat"])
        self.assertEqual(steps[0]["word"], "skewer")

    def test_a_customer_still_orders_from_the_keeper(self):
        """The control: everyone else is served as before."""
        steps = self.plan(self.patron)
        self.assertEqual(self.doing(steps), ["order", "pickup", "eat"])
        self.assertEqual(steps[0]["tender"], self.keeper.id)

    def test_only_the_keeper_eats_free(self):
        """The control on the price: the same priced board, the same
        empty purse, and a customer has no plan."""
        self.counter.db.menu = [SKEWER]
        self.assertIsNone(self.plan(self.patron))

    def test_off_their_own_shift_they_order_like_anyone(self):
        """The swing keeper, standing there at noon, is a customer."""
        steps = self.plan(self.relief)
        self.assertEqual(self.doing(steps), ["order", "pickup", "eat"])
        self.assertEqual(steps[0]["tender"], self.keeper.id)

    def test_a_counter_that_only_pours_feeds_nobody(self):
        """The control: a bar's keeper still walks somewhere with food."""
        self.counter.db.menu = [POUR]
        self.assertIsNone(self.plan(self.keeper))

    def test_ordering_from_yourself_is_still_refused(self):
        """Unchanged (#2364), and why a keeper's DRINK is not covered
        here: the craving door still asks this and gets no."""
        self.assertIsNone(actions._tender_for(self.keeper, self.counter))


class TestTheMeal(_KitchenCase):
    def start(self, who=None):
        who = who or self.keeper
        who.db.soul_job = {"goal": "hunger", "band": 1, "at": 0,
                           "steps": self.plan(who)}
        self.bind_prepare(who)
        return who

    def bind_prepare(self, who):
        """Hand `prepare` to the real command, bound to THIS counter.

        A harness matter, not a game one. Test objects reuse database
        ids from one test to the next, and under the test runner a
        command that belongs to an object in the room (as `prepare`
        belongs to the counter) resolves against the counter of an
        EARLIER test: the first test in a process passes and every
        later one is told "You aren't working this bar." The command
        itself runs for real, `plate_or_mix` and the craft emote
        included; every other command goes through `execute_cmd`
        untouched."""
        import typeclasses.bar as barmod
        real = who.execute_cmd

        def execute_cmd(raw_string, **kwargs):
            if not raw_string.startswith("prepare "):
                return real(raw_string, **kwargs)
            cmd = barmod.CmdBarPrepare()
            cmd.caller, cmd.obj = who, self.counter
            cmd.cmdstring, cmd.args = "prepare", raw_string[len("prepare"):]
            return cmd.func()

        who.execute_cmd = execute_cmd

    def step(self, who, times=1):
        for _ in range(times):
            if who.db.soul_job is None:
                break
            jobs.step_job(who)

    def on_the_counter(self):
        return [o.key for o in self.counter.contents]

    def carried(self, who):
        return [o.key for o in who.contents]

    def test_the_dish_lands_on_the_counter(self):
        keeper = self.start()
        self.step(keeper)
        self.assertEqual(len(self.on_the_counter()), 1)
        self.assertIn("kuro-nikomi", self.on_the_counter()[0])
        self.assertEqual(keeper.db.soul_job.get("at"), 1)

    def test_the_keeper_lifts_it(self):
        keeper = self.start()
        self.step(keeper, 2)
        self.assertEqual(self.on_the_counter(), [])
        self.assertEqual(len(self.carried(keeper)), 1)

    def test_and_eats_it_down(self):
        keeper = self.start()
        before = needs.pressure(keeper, "hunger")
        self.step(keeper, 10)
        self.assertIsNone(keeper.db.soul_job, "the meal never finished")
        self.assertEqual(self.carried(keeper), [])
        self.assertEqual(self.on_the_counter(), [])
        self.assertLess(needs.pressure(keeper, "hunger"), before - 0.3)
        self.assertEqual(keeper.db.soul_faults or [], [])

    def test_nobody_is_charged(self):
        self.counter.db.menu = [SKEWER]            # a dish with a price
        keeper = self.start()
        keeper.tokens = 5
        before = needs.pressure(keeper, "hunger")
        self.step(keeper, 10)
        self.assertIsNone(keeper.db.soul_job)
        self.assertLess(needs.pressure(keeper, "hunger"), before - 0.1,
                        "nothing was eaten, so nothing was proved")
        self.assertEqual(keeper.tokens, 5)
        self.assertEqual(self.counter.db.register, 0)

    def test_a_dish_that_will_not_come_together_is_said_at_once(self):
        """`prepare` sets the dish down immediately, so an empty counter
        after it is a refusal. The step says so on the spot and does
        not leave `pickup` standing three rounds for nothing."""
        keeper = self.start()
        keeper.db.soul_job["steps"][0]["word"] = "nothing-on-this-board"
        self.step(keeper)
        self.assertIsNone(keeper.db.soul_job)
        self.assertEqual(self.on_the_counter(), [])
        self.assertIn("could not prepare",
                      (keeper.db.soul_faults or [])[-1][1])

    def test_a_keeper_relieved_before_the_step_makes_nothing(self):
        """Planned on shift, stepped after the slot changed hands: the
        command would refuse, so the step says why and stops."""
        keeper = self.start()
        self.counter.db.post_slots = {"day": {"keeper": self.relief}}
        self.step(keeper)
        self.assertIsNone(keeper.db.soul_job)
        self.assertEqual(self.on_the_counter(), [])
        self.assertIn("not working", (keeper.db.soul_faults or [])[-1][1])
