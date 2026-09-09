"""The worn/carried record survives corpse creation (#2460, reopened).

#2460 gave the corpse a record of WHAT WAS ACTUALLY WORN, because
everything in `contents` -- worn kit and merely carried kit alike --
moves onto the corpse, and without the record the appearance path
admitted any object with a truthy `db.coverage`. A jacket you took off
before dying read as worn and suppressed the chest/back/abdomen/arm
longdescs with it.

The capture sat immediately after the transfer loop, with a comment
saying it was taken "BEFORE the clear below because this is the last
moment the truth exists".

#2912 then gave `Character` an `at_object_leave` hook that releases
hand and clothing slots for anything leaving the body -- a good
invariant. But the transfer loop moves every item with default
`move_hooks`, so `worn_items` is now emptied AS THE LOOP RUNS. By the
time the capture is reached the dict is empty, its
`and character.worn_items` guard is falsy, and the write is skipped
entirely.

Verified in the running game: a body wearing scrubs and carrying a lab
coat produced `corpse.db.worn_at_death: None`. And per
`Corpse.note_dressed`, "no record means the map still renders
contents-wide" -- so the fallback is precisely the #2460 behaviour,
restored in full.

Two commits, each correct alone: one moved the clear earlier, the other
was written when the clear came later. Nothing failed loudly.
"""
from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from typeclasses.death_progression import DeathProgressionScript


class TestTheCorpseKnowsWhatWasWorn(EvenniaTest):

    def _body(self):
        who = create_object("typeclasses.characters.Character",
                            key="Testdead", location=self.room1)
        worn = spawn("MEDICAL_SCRUBS")[0]
        worn.location = who
        carried = spawn("LAB_COAT")[0]
        carried.location = who
        who.wear_item(worn)
        return who, worn, carried

    def test_the_record_is_written_at_all(self):
        who, worn, _carried = self._body()
        corpse = DeathProgressionScript._create_corpse_from_character(None, who)
        self.assertIsNotNone(
            corpse.db.worn_at_death,
            "no record was written, so the coverage map renders "
            "contents-wide and #2460 is back")

    def test_it_holds_the_worn_garment(self):
        who, worn, _carried = self._body()
        corpse = DeathProgressionScript._create_corpse_from_character(None, who)
        self.assertIn(worn.id, list(corpse.db.worn_at_death or []))

    def test_it_records_each_garment_once(self):
        """`worn_items` is keyed by body LOCATION, so a garment appears
        once per slot it covers. A set of scrubs came back as the same
        id eight times. Caught by an in-play probe asserting equality
        while the test above only asserted membership -- `in` is a
        weaker question than `==` and hid it."""
        who, worn, _carried = self._body()
        corpse = DeathProgressionScript._create_corpse_from_character(None, who)
        record = list(corpse.db.worn_at_death or [])
        self.assertEqual(record, [worn.id])

    def test_it_does_not_hold_the_merely_carried_one(self):
        """The whole point of the record."""
        who, _worn, carried = self._body()
        corpse = DeathProgressionScript._create_corpse_from_character(None, who)
        self.assertNotIn(carried.id, list(corpse.db.worn_at_death or []))

    def test_a_naked_death_still_writes_no_record(self):
        """Documenting EXISTING behaviour, not asserting a fix.

        A body wearing nothing writes no record, so the coverage map
        renders contents-wide and a carried coat on a naked corpse still
        reads as worn. That predates #2912 -- the guard has always been
        `if worn_items:` -- so it is not part of this regression and is
        not changed here.

        Written as an explicit `is None` rather than
        `list(x or []) == []`, which was the first version and passes
        for `None` just as happily as for `[]` -- an assertion that
        cannot tell the two apart is not testing the thing it names.
        """
        who = create_object("typeclasses.characters.Character",
                            key="Testnude", location=self.room1)
        carried = spawn("LAB_COAT")[0]
        carried.location = who
        corpse = DeathProgressionScript._create_corpse_from_character(None, who)
        self.assertIsNone(corpse.db.worn_at_death)
