"""A sleeve policy is bought alive and spent by a return (#3667, Slice A).

The record is one `ServerConfig` row per sleeve uid, keyed to the sample
the lobby terminal takes; only the body that bought it can redeem it; a
flash clone spends the dead body's own record and no other. Driven through
the real `press` command where a player would type it; the take/restore
pair is driven directly, as the returns will call it.

Harness notes: `Character.is_archived` is a property (patch it with
PropertyMock or set `db.archived`); a stored dict reads back as a
`_SaverDict`, not a `dict`; room broadcasts never reach a test observer
(the session gate), so the broadcast is asserted on the patched sender.
"""
from unittest import mock

from evennia import create_object, create_script
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdGraffiti import CmdPress
from typeclasses.terminals import InsuranceTerminal
from world import insurance
from world.insurance import (NO_POLICY, buy_policy, covers, policy_for,
                             restore_policy, spend_policy, status_line,
                             take_policy, void_policy)

BUY = f"{InsuranceTerminal.BUY_BUTTON} on terminal"


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

    def record_for(self, body):
        return {"uid": self.buyer.sleeve_uid, "buyer_dbref": body.id,
                "bought_at": 0, "buyer_key": body.key,
                "blueprint_key": None, "account_id": None}


class TheTerminal(_Lobby):

    def test_a_bare_press_reads_no_policy(self):
        self.assertIn(NO_POLICY, self.press("terminal"))

    def test_insure_files_a_policy_in_the_pressers_name(self):
        out = self.press(BUY)
        self.assertIn("on file in your name", out)
        self.assertTrue(covers(self.buyer))
        self.assertEqual(policy_for(self.buyer.sleeve_uid)["buyer_dbref"],
                         self.buyer.id)

    def test_the_room_hears_the_sample_taken(self):
        with mock.patch("world.identity_utils.msg_room_identity") as told:
            self.press(BUY)
        self.assertTrue(told.called)
        self.assertIn("takes a sample", told.call_args.kwargs["template"])

    def test_a_second_press_is_already_on_file(self):
        self.press(BUY)
        with mock.patch("world.identity_utils.msg_room_identity") as told:
            self.assertIn("already on file", self.press(BUY))
        self.assertFalse(told.called)

    def test_the_signs_own_words_are_buttons(self):
        # The plate says RENEW; a player who types it must not be told
        # "You don't have a 'terminal'".
        for word in ("renew", "sample"):
            self.assertIn(word, InsuranceTerminal.BUY_BUTTONS)
        self.assertIn("on file in your name", self.press("renew on terminal"))

    def test_status_after_buying(self):
        self.press(BUY)
        self.assertIn("on file in your name", self.press("terminal"))

    def test_a_label_that_is_not_a_button_is_not_answered(self):
        out = self.press("jackpot on terminal")
        self.assertNotIn("on file", out)
        self.assertFalse(covers(self.buyer))

    def test_the_buttons_have_one_home(self):
        self.assertEqual(set(InsuranceTerminal.BUTTONS),
                         set(InsuranceTerminal.BUY_BUTTONS)
                         | set(InsuranceTerminal.STATUS_BUTTONS))

    def test_it_is_found_by_its_index_tag(self):
        self.assertTrue(self.terminal.tags.has("insurance_terminal",
                                               category="machines"))


class ThePrice(_Lobby):

    def test_free_for_now_is_one_constant(self):
        self.assertEqual(insurance.POLICY_PRICE, 0)

    def test_when_priced_the_broke_are_quoted_and_refused(self):
        self.buyer.tokens = 3
        with mock.patch.object(insurance, "POLICY_PRICE", 5):
            ok, msg = buy_policy(self.buyer, self.terminal)
        self.assertFalse(ok)
        self.assertIn("5 tokens", msg)
        self.assertEqual(self.buyer.tokens, 3)

    def test_when_priced_the_buyer_pays_the_terminal_and_the_ledger(self):
        self.buyer.tokens = 12
        self.terminal.db.register = 100
        with mock.patch.object(insurance, "POLICY_PRICE", 5), \
             mock.patch("world.souls.audit.coin") as coin:
            ok, _ = buy_policy(self.buyer, self.terminal)
        self.assertTrue(ok)
        self.assertEqual(self.buyer.tokens, 7)
        self.assertEqual(self.terminal.db.register, 105)
        self.assertTrue(coin.called)
        self.assertEqual(coin.call_args.args[2], "sleeve_policy")


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

    def test_the_dying_are_refused(self):
        # A death progression attached to the body is "dying".
        create_script("typeclasses.scripts.Script", key="death_progression",
                      obj=self.buyer, autostart=False)
        ok, msg = buy_policy(self.buyer, self.terminal)
        self.assertFalse(ok)
        self.assertIn("no vital signs", msg)

    def test_the_archived_are_refused(self):
        self.buyer.db.archived = True          # the property reads it
        ok, msg = buy_policy(self.buyer, self.terminal)
        self.assertFalse(ok)
        self.assertIn("not in service", msg)

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
        husk = self.twin(archived=True)
        self.assertTrue(restore_policy(self.record_for(husk)))
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
        self.assertIn("held by another sleeve", status_line(self.buyer))


class TheInsertIsTheGuard(_Lobby):
    """`ServerConfig.value`'s setter saves on assignment, which once put
    the INSERT outside the try: a duplicate key was a traceback, not
    "already on file"."""

    def test_a_duplicate_insert_is_already_on_file_not_a_traceback(self):
        buy_policy(self.buyer, self.terminal)
        # the row exists; make the pre-check blind so the INSERT is reached
        with mock.patch("world.insurance.policy_for", return_value=None):
            ok, msg = buy_policy(self.buyer, self.terminal)
        self.assertFalse(ok)
        self.assertIn("already on file", msg)

    def test_restoring_into_an_occupied_key_reports_false(self):
        buy_policy(self.buyer, self.terminal)
        self.assertFalse(restore_policy(self.record_for(self.buyer)))
        self.assertTrue(covers(self.buyer))


class TakeAndRestore(_Lobby):

    def test_only_the_buyer_can_take_it(self):
        buy_policy(self.buyer, self.terminal)
        self.assertIsNone(take_policy(self.buyer.sleeve_uid, self.char1.id))
        self.assertTrue(covers(self.buyer))

    def test_a_take_spends_it_exactly_once(self):
        buy_policy(self.buyer, self.terminal)
        self.assertIsNotNone(take_policy(self.buyer.sleeve_uid, self.buyer.id))
        self.assertIsNone(take_policy(self.buyer.sleeve_uid, self.buyer.id))
        self.assertFalse(covers(self.buyer))

    def test_a_row_that_vanished_between_the_read_and_the_delete_is_not_taken(self):
        # The race guard: the read saw a record, the DELETE found nothing.
        rec = self.record_for(self.buyer)
        with mock.patch("world.insurance.policy_for", return_value=rec):
            self.assertIsNone(take_policy(self.buyer.sleeve_uid, self.buyer.id))

    def test_a_failed_return_puts_it_back(self):
        buy_policy(self.buyer, self.terminal)
        rec = take_policy(self.buyer.sleeve_uid, self.buyer.id)
        self.assertTrue(restore_policy(rec))
        self.assertTrue(covers(self.buyer))


class AFlashCloneSpendsIt(_Lobby):

    def clone_of(self, body):
        from commands.charcreate import create_flash_clone
        with mock.patch("commands.charcreate.get_start_location",
                        return_value=self.room2):
            clone = create_flash_clone(self.account2, body)
        self.addCleanup(void_policy, clone.sleeve_uid)
        return clone

    def test_the_dead_bodys_record_is_gone_after_the_clone(self):
        buy_policy(self.buyer, self.terminal)
        self.buyer.archive_character(reason="death")
        clone = self.clone_of(self.buyer)
        self.assertEqual(clone.sleeve_uid, self.buyer.sleeve_uid)
        self.assertIsNone(policy_for(self.buyer.sleeve_uid))

    def test_cloning_an_older_husk_leaves_a_living_bodys_cover_alone(self):
        # The living body of the lineage is insured; an OLDER husk of the
        # same lineage is cloned. Only the dead body's own record may go.
        buy_policy(self.buyer, self.terminal)               # the living one
        husk = create_object("typeclasses.characters.Character", key="husk",
                             location=None)
        husk.sleeve_uid = self.buyer.sleeve_uid
        husk.db.archived = True
        self.assertFalse(spend_policy(husk.sleeve_uid, husk.id))
        self.assertTrue(covers(self.buyer), "the living body lost its cover")
