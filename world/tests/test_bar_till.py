"""The register can be emptied — money in, money out.

Uses Evennia's command-test helper (`self.call`) rather than
`execute_cmd`: the bar's commands live on an OBJECT cmdset, and driving
them through the cmdset router in a test harness silently no-ops.
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.bar import CmdBarTill


class TestBarTill(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.bar = create_object("typeclasses.bar.BarCounter", key="bar",
                                 location=self.room1)
        self.char1.location = self.room1
        self.char1.tokens = 0

    def _till(self, args=""):
        self.call(CmdBarTill(), args, obj=self.bar, caller=self.char1)

    def test_owner_takes_the_whole_register(self):
        self.bar.db.owner = self.char1
        self.bar.db.register = 120
        self._till()
        self.assertEqual(self.bar.db.register, 0)
        self.assertEqual(self.char1.tokens, 120)

    def test_partial_take_leaves_the_rest(self):
        self.bar.db.owner = self.char1
        self.bar.db.register = 120
        self._till("bar = 50")
        self.assertEqual(self.bar.db.register, 70)
        self.assertEqual(self.char1.tokens, 50)

    def test_cannot_take_more_than_is_there(self):
        self.bar.db.owner = self.char1
        self.bar.db.register = 30
        self._till("bar = 500")
        self.assertEqual(self.bar.db.register, 0)
        self.assertEqual(self.char1.tokens, 30)

    def test_staff_may_take(self):
        self.bar.db.owner = self.char2
        self.bar.db.staff = [self.char1]
        self.bar.db.register = 40
        self._till()
        self.assertEqual(self.char1.tokens, 40)

    def test_a_stranger_may_not(self):
        """The stranger has to be an ACTUAL stranger.

        `EvenniaTest` gives `char1` the `developer` permission, and
        `BarCounter.is_bartender` deliberately grants game staff every
        bar -- so char1 is not a stranger to this counter, and this test
        only ever passed because `till` used to ask a different question
        from `use`, `prepare` and `clean` (#2471). char2 carries no
        permissions, which is what the case was always about.
        """
        self.bar.db.owner = self.char1
        self.bar.db.register = 40
        self.char2.location = self.room1
        self.char2.tokens = 0
        self.call(CmdBarTill(), "", obj=self.bar, caller=self.char2)
        self.assertEqual(self.bar.db.register, 40)
        self.assertEqual(self.char2.tokens, 0)

    def test_game_staff_may_take_any_register(self):
        """The other half of the same ruling, now pinned rather than
        implied: `is_bartender` says staff can work and manage any bar,
        and `till` is management."""
        self.bar.db.owner = self.char2
        self.bar.db.register = 40
        self._till()
        self.assertEqual(self.char1.tokens, 40)

    def test_unowned_bar_is_open_to_anyone(self):
        self.bar.db.register = 15
        self._till()
        self.assertEqual(self.char1.tokens, 15)

    def test_empty_register_pays_nothing(self):
        self.bar.db.owner = self.char1
        self.bar.db.register = 0
        self._till()
        self.assertEqual(self.char1.tokens, 0)

    def test_a_nonsense_amount_takes_nothing(self):
        self.bar.db.owner = self.char1
        self.bar.db.register = 60
        self._till("bar = lots")
        self.assertEqual(self.bar.db.register, 60)
        self.assertEqual(self.char1.tokens, 0)
