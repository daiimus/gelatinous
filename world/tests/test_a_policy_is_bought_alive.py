"""A sleeve policy is bought alive and spent by a return (#3667, Slice A).

The record is one `ServerConfig` row per sleeve uid, keyed to the sample
the lobby terminal takes; only the body that bought it can redeem it; a
flash clone spends the lineage's record. Driven through the real `press`
command where a player would type it; the take/restore pair is driven
directly, as the returns will call it.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdGraffiti import CmdPress
from world import insurance
from world.insurance import (NO_POLICY, buy_policy, covers, policy_for,
                             restore_policy, take_policy, void_policy)


class _Lobby(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.terminal = create_object("typeclasses.terminals.InsuranceTerminal",
                                      key="a Thawn-Harrison policy terminal",
                                      location=self.room1)
        self.buyer = self.char2                 # no staff permission
        self.addCleanup(void_policy, self.buyer.sleeve_uid)

    def press(self, args):
        return self.call(CmdPress(), args, caller=self.buyer) or ""


class TheTerminal(_Lobby):

    def test_a_bare_press_reads_no_policy(self):
        self.assertIn(NO_POLICY, self.press("terminal"))

    def test_insure_files_a_policy_in_the_pressers_name(self):
        out = self.press("insure on terminal")
        self.assertIn("on file in your name", out)
        self.assertTrue(covers(self.buyer))
        rec = policy_for(self.buyer.sleeve_uid)
        self.assertEqual(rec["buyer_dbref"], self.buyer.id)

    def test_a_second_press_is_already_on_file(self):
        self.press("insure on terminal")
        self.assertIn("already on file", self.press("insure on terminal"))

    def test_status_after_buying(self):
        self.press("insure on terminal")
        self.assertIn("on file in your name", self.press("terminal"))

    def test_a_label_that_is_not_a_button_is_not_answered(self):
        out = self.press("jackpot on terminal")
        self.assertNotIn("on file", out)
        self.assertFalse(covers(self.buyer))

    def test_the_price_is_one_constant_and_free_for_now(self):
        self.assertEqual(insurance.POLICY_PRICE, 0)
        before = int(self.buyer.tokens or 0)
        self.press("insure on terminal")
        self.assertEqual(int(self.buyer.tokens or 0), before)


class WhoCanGiveASample(_Lobby):

    def test_no_sleeve_signature_is_refused(self):
        self.buyer.sleeve_uid = None
        ok, msg = buy_policy(self.buyer, self.terminal)
        self.assertFalse(ok)
        self.assertIn("no sleeve signature", msg)

    def test_the_dead_are_refused(self):
        with mock.patch.object(type(self.buyer), "is_dead", return_value=True):
            ok, msg = buy_policy(self.buyer, self.terminal)
        self.assertFalse(ok)
        self.assertIn("no vital signs", msg)
        self.assertIsNone(policy_for(self.buyer.sleeve_uid))

    def test_the_unconscious_are_refused(self):
        with mock.patch.object(type(self.buyer), "is_unconscious", return_value=True):
            ok, _ = buy_policy(self.buyer, self.terminal)
        self.assertFalse(ok)

    def test_control_a_living_conscious_body_is_accepted(self):
        ok, _ = buy_policy(self.buyer, self.terminal)
        self.assertTrue(ok)


class OneRecordPerLineage(_Lobby):
    """A flash clone carries the buyer's uid. An older husk's leftover is
    void when the living body buys; a record held by a living twin is not."""

    def twin(self, *, archived):
        other = create_object("typeclasses.characters.Character", key="twin",
                              location=self.room1)
        other.sleeve_uid = self.buyer.sleeve_uid
        if archived:
            other.db.archived = True
            other.location = None
        return other

    def test_an_archived_husks_record_is_replaced_by_the_living_body(self):
        husk = self.twin(archived=True)         # db.archived = True: the property reads it
        ok, _ = buy_policy(husk, self.terminal)
        self.assertFalse(ok, "an archived husk must not be able to buy")
        # plant the husk's leftover record by hand, as an unspent return would
        restore_policy({"uid": self.buyer.sleeve_uid, "buyer_dbref": husk.id,
                        "bought_at": 0, "buyer_key": "twin",
                        "blueprint_key": None, "account_id": None})
        self.assertFalse(covers(self.buyer))
        ok, msg = buy_policy(self.buyer, self.terminal)
        self.assertTrue(ok, msg)
        self.assertTrue(covers(self.buyer))

    def test_a_living_twins_record_is_not_taken_over(self):
        twin = self.twin(archived=False)
        ok, _ = buy_policy(twin, self.terminal)
        self.assertTrue(ok)
        ok, msg = buy_policy(self.buyer, self.terminal)
        self.assertFalse(ok)
        self.assertIn("another sleeve", msg)


class TakeAndRestore(_Lobby):

    def test_only_the_buyer_can_take_it(self):
        buy_policy(self.buyer, self.terminal)
        self.assertIsNone(take_policy(self.buyer.sleeve_uid, self.char1.id))
        self.assertTrue(covers(self.buyer))

    def test_a_take_spends_it_exactly_once(self):
        buy_policy(self.buyer, self.terminal)
        rec = take_policy(self.buyer.sleeve_uid, self.buyer.id)
        self.assertIsNotNone(rec)
        self.assertIsNone(take_policy(self.buyer.sleeve_uid, self.buyer.id))
        self.assertFalse(covers(self.buyer))

    def test_a_failed_return_puts_it_back(self):
        buy_policy(self.buyer, self.terminal)
        rec = take_policy(self.buyer.sleeve_uid, self.buyer.id)
        restore_policy(rec)
        self.assertTrue(covers(self.buyer))


class AFlashCloneSpendsIt(_Lobby):

    def test_the_lineages_record_is_gone_after_the_clone(self):
        from commands.charcreate import create_flash_clone
        buy_policy(self.buyer, self.terminal)
        self.buyer.archive_character(reason="death")
        with mock.patch("commands.charcreate.get_start_location",
                        return_value=self.room2):
            clone = create_flash_clone(self.account2, self.buyer)
        self.addCleanup(void_policy, clone.sleeve_uid)
        self.assertEqual(clone.sleeve_uid, self.buyer.sleeve_uid)
        self.assertIsNone(policy_for(self.buyer.sleeve_uid))
        # and the clone can buy afresh: nothing is stranded
        ok, _ = buy_policy(clone, self.terminal)
        self.assertTrue(ok)
