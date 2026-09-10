"""Every money movement writes a `coin` line (#2698).

`audit.coin`'s docstring names four categories:

    Money moved. Wages, purchases, fees, till deltas — the record that
    answers whether the economy circulates or merely accrues.

Of the four, only wages had an emitter, plus one courier fee. Measured
across 111,863 retained audit lines:

    810  why=wage
    181  why=delivery_unpaid
     40  why=delivery

No purchase, no rent, no tithe, no till delta. The module's own stated
purpose names *"whether anybody ever buys clothes"* as one of three
questions it exists to answer, and that one could not be answered at
all.

`economy.py`'s header describes the loop as
`Treasury -> wages -> spending -> tills -> tithe -> treasury`. Only the
first leg was recorded.

These tests assert the CALL SITES exist rather than driving each shop,
bar, locker and clinic end to end: the failure being guarded against is
an unrecorded transfer, which is a property of the site and not of the
transaction. Two of them are driven for real as controls, so "the
emitter is spelled right" is not the only thing under test.
"""
import re

from evennia.utils.test_resources import EvenniaTest

#: Every file that moves tokens, and the reason it must record.
SITES = {
    "typeclasses/shopkeeper.py": "purchase",
    "world/bar.py": "drink",
    "typeclasses/bar.py": "till_take",
    "typeclasses/lockers.py": "locker_rent",
    "world/butchery.py": "carcass_sale",
    "world/souls/jobs.py": "treatment",
    "world/souls/economy.py": "tithe",
    "world/souls/posts.py": "resleeve_premium",
    "commands/CmdTheft.py": "theft",
    "world/director/courier.py": "delivery",
}


def _source(path):
    with open(path) as handle:
        return handle.read()


class TestEveryMoneySiteRecords(EvenniaTest):

    def test_each_site_emits_its_reason(self):
        missing = [f"{path} ({why})" for path, why in SITES.items()
                   if f'"{why}"' not in _source(path)]
        self.assertEqual(missing, [],
                         "money moves here with no audit line:\n"
                         + "\n".join(missing))

    def test_each_site_actually_calls_coin(self):
        """A reason string in a comment is not an emitter."""
        for path in SITES:
            self.assertRegex(
                _source(path), r"(audit|_audit)\.coin\(",
                f"{path} names a reason but never calls coin")

    def test_no_token_assignment_is_left_unrecorded(self):
        """The sweep that found these. A file that moves `tokens` and
        never records is the shape of the defect, so a NEW one shows up
        here rather than in a log census months later."""
        movers = re.compile(r"\.tokens\s*(?:[-+]?=|=\s*(?:int\()?\s*\w+\s*[-+])")
        unrecorded = []
        for path in ("typeclasses/shopkeeper.py", "world/bar.py",
                     "typeclasses/bar.py", "typeclasses/lockers.py",
                     "world/butchery.py", "world/souls/jobs.py",
                     "commands/CmdTheft.py", "world/souls/economy.py"):
            source = _source(path)
            if movers.search(source) and ".coin(" not in source:
                unrecorded.append(path)
        self.assertEqual(unrecorded, [])


class TestTheRecordIsActuallyWritten(EvenniaTest):
    """Controls: the emitters are driven, not merely grepped."""

    def test_coin_writes_a_line(self):
        from unittest.mock import patch
        from world.souls import audit
        with patch.object(audit, "_under_test", return_value=False), \
                patch.object(audit, "_logger") as log:
            audit.coin(self.char1, 12, "purchase", other=self.char2)
        said = log.return_value.info.call_args.args[0]
        self.assertIn("coin", said)
        self.assertIn("why=purchase", said)
        self.assertIn("amount=12", said)

    def test_it_records_a_party_with_no_soul(self):
        """The tithe and the resleeve premium move money with no person
        on either end, and `record` must not require one."""
        from unittest.mock import patch
        from world.souls import audit
        with patch.object(audit, "_under_test", return_value=False), \
                patch.object(audit, "_logger") as log:
            audit.coin(None, 40, "tithe")
        said = log.return_value.info.call_args.args[0]
        self.assertIn("why=tithe", said)
        self.assertIn("who=-", said)

    def test_a_broken_logger_does_not_break_the_sale(self):
        """`record` promises it never raises — the emitters are wrapped
        as well, but the promise is what makes the wrapping safe to
        trust at ten call sites."""
        from unittest.mock import patch
        from world.souls import audit
        with patch.object(audit, "_under_test", return_value=False), \
                patch.object(audit, "_logger", side_effect=RuntimeError):
            audit.coin(self.char1, 1, "purchase")     # must not raise
