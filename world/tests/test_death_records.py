"""Death records (world/death_records.py) — DEATH_AND_SLEEVE_LIFECYCLE_SPEC §9.

The OOC tombstone: who the sleeve was, born, died. Engraved on the owning
account at archive time; idempotent; NPCs (no account) get none; the corpse
link is internal and allowed to go stale.
"""

from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock

from world.death_records import add_record, get_records, stamp_corpse


def _account(records=None):
    acct = MagicMock()
    acct.db.death_records = records if records is not None else []
    return acct


def _sleeve(dbref="#42", key="Jorge Calderon II", birth=1000.0, account=None):
    ch = MagicMock()
    ch.dbref = dbref
    ch.key = key
    ch.db.current_sleeve_birth = birth
    ch.account = account
    ch.date_created = datetime(2025, 10, 14, 12, 0, 0)
    return ch


class TestAddRecord(TestCase):
    def test_engraves_name_and_two_dates(self):
        acct = _account()
        rec = add_record(_sleeve(account=acct), died=2000.0)
        self.assertEqual(rec["name"], "Jorge Calderon II")
        self.assertEqual(rec["born"], 1000.0)
        self.assertEqual(rec["died"], 2000.0)
        self.assertIsNone(rec["corpse_dbref"])       # stamped separately
        self.assertEqual(acct.db.death_records, [rec])

    def test_no_cause_no_location_ever(self):
        # The tombstone's whole design: a name and two dates, nothing else.
        rec = add_record(_sleeve(account=_account()), died=2000.0)
        self.assertEqual(
            set(rec), {"sleeve_dbref", "name", "born", "died", "corpse_dbref"})

    def test_npc_gets_no_tombstone(self):
        self.assertIsNone(add_record(_sleeve(account=None)))

    def test_idempotent_per_sleeve(self):
        acct = _account()
        sleeve = _sleeve(account=acct)
        first = add_record(sleeve, died=2000.0)
        again = add_record(sleeve, died=9999.0)     # re-archive: no double
        self.assertEqual(again, first)
        self.assertEqual(len(get_records(acct)), 1)

    def test_born_falls_back_to_creation_date(self):
        # Legacy sleeves predating current_sleeve_birth still get a born date.
        sleeve = _sleeve(birth=None, account=_account())
        rec = add_record(sleeve, died=2000.0)
        self.assertEqual(rec["born"],
                         datetime(2025, 10, 14, 12, 0, 0).timestamp())

    def test_explicit_account_overrides_lost_link(self):
        # Death path captures the account pre-unpuppet and passes it in.
        acct = _account()
        rec = add_record(_sleeve(account=None), account=acct, died=2000.0)
        self.assertIsNotNone(rec)
        self.assertEqual(len(get_records(acct)), 1)


class TestStampCorpse(TestCase):
    def test_links_record_to_body(self):
        acct = _account()
        sleeve = _sleeve(account=acct)
        add_record(sleeve, died=2000.0)
        corpse = MagicMock(); corpse.dbref = "#777"
        self.assertTrue(stamp_corpse(sleeve, corpse))
        self.assertEqual(get_records(acct)[0]["corpse_dbref"], "#777")

    def test_no_record_or_account_is_a_noop(self):
        corpse = MagicMock(); corpse.dbref = "#777"
        self.assertFalse(stamp_corpse(_sleeve(account=None), corpse))
        acct = _account()
        self.assertFalse(stamp_corpse(_sleeve(account=acct), corpse))
