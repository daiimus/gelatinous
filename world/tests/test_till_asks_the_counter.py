"""`till` asks the counter who works there, like every other verb (#2471).

`CmdBarTill` had its own ownership test:

    if owner is not None and caller != owner and caller not in staff:

gated on `owner is not None`, so it short-circuits to "yes, you may"
whenever no owner is configured -- and **no bar in the colony has an
owner**. `BarCounter.at_object_creation` defaults `owner = None`, and the
one build script that assigns an owner covers a counter that is not among
the live fixtures.

Meanwhile `BarCounter.is_bartender` -- which `use`, `prepare` and `clean`
all ask -- returns False for a stranger as soon as the counter has any
staff at all. So on the hull-slab bar (owner `None`, one staff member) a
stranger was refused by `use` and allowed to empty the register in the
same breath. Two doors onto one decision, and the money was behind the
weaker one.

The remaining exposure is deliberate and is NOT changed here:
`is_bartender` documents that while no ownership is configured, anyone
present may work the bar. That is a v1 ruling, so `till` now inherits it
rather than inventing a second rule. It is raised with the owner
separately, because it currently guards real takings.
"""
from evennia.utils.test_resources import EvenniaTest


class _TillCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.counter = self.obj1
        self.counter.swap_typeclass("typeclasses.bar.BarCounter",
                                    clean_attributes=False,
                                    run_start_hooks="all")
        self.counter.location = self.room1
        self.keeper = self.char1
        self.stranger = self.char2
        for c in (self.keeper, self.stranger):
            c.location = self.room1
        self.counter.db.register = 500
        self.counter.db.owner = None
        self.counter.db.staff = []
        self.said = []

    def take(self, who):
        from typeclasses.bar import CmdBarTill
        self.said = []
        who.msg = lambda text=None, **kw: self.said.append(str(text))
        cmd = CmdBarTill()
        cmd.caller = who
        cmd.obj = self.counter
        cmd.args = ""
        cmd.func()
        return " ".join(self.said)


class TestAStaffedCounterRefusesAStranger(_TillCase):
    """The live case: owner None, staff non-empty."""

    def setUp(self):
        super().setUp()
        self.counter.db.staff = [self.keeper]

    def test_the_stranger_is_told_no(self):
        self.assertIn("not your register", self.take(self.stranger))

    def test_the_money_is_still_there(self):
        self.take(self.stranger)
        self.assertEqual(int(self.counter.db.register or 0), 500)

    def test_the_staff_member_can_still_take_it(self):
        self.take(self.keeper)
        self.assertEqual(int(self.counter.db.register or 0), 0)

    def test_till_and_use_now_give_the_same_answer(self):
        """The actual defect was that they did not."""
        refused_by_till = "not your register" in self.take(self.stranger)
        refused_by_the_counter = not self.counter.is_bartender(self.stranger)
        self.assertEqual(refused_by_till, refused_by_the_counter)


class TestAnOwnedCounterRefusesAStranger(_TillCase):
    def setUp(self):
        super().setUp()
        self.counter.db.owner = self.keeper

    def test_the_stranger_is_told_no(self):
        self.assertIn("not your register", self.take(self.stranger))

    def test_the_owner_can_take_it(self):
        self.take(self.keeper)
        self.assertEqual(int(self.counter.db.register or 0), 0)


class TestTheUnconfiguredCounterKeepsItsV1Rule(_TillCase):
    """`is_bartender` documents that with no owner and no staff, anyone
    present may work the bar. `till` inherits that rather than inventing
    a second rule -- 16 counters holding 444 credits are in this state
    live, which is raised with the owner rather than decided here."""

    def test_anyone_present_may_still_work_it(self):
        self.assertTrue(self.counter.is_bartender(self.stranger))

    def test_and_till_agrees(self):
        self.assertNotIn("not your register", self.take(self.stranger))
