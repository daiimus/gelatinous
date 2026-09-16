"""Severed parts are corpse fragments: frisk, get, undress and look ask
one question, "what is this body wearing", and every body answers it
from its own store (#3575).

Before: `frisk` treated only corpses as loot, so a limb or head fell
into the living-person path; the frisk manifest asked `get_worn_items`,
which on a corpse is deliberately only the disguise-essential subset, so
a frisked corpse under-reported its clothes; `undress` had three private
readers (character registry, corpse contents-with-coverage, the limb
ledger) that
each had to be fixed separately (#2456 for look, #3554 for undress).

Now `worn_garments()` lives on ClothingMixin, Corpse and Appendage
(SeveredHead inherits), and the verbs ask the body.
"""
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest


def _garment(key, coverage, location):
    g = create_object("typeclasses.items.Item", key=key, location=location)
    g.db.coverage = list(coverage)
    return g


class _Remains(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.corpse = create_object("typeclasses.corpse.Corpse", key="a corpse", location=self.room1)
        self.coat = _garment("wool coat", ["chest", "back"], self.corpse)
        # the death transfer stamps this record; `mark_worn` only appends
        # to an existing one, and a corpse with NO record is contents-wide
        # by design (#3107)
        self.corpse.db.worn_at_death = [self.coat.id]
        self.loose = _garment("spare coat", ["chest"], self.corpse)      # carried, never worn
        self.head = create_object("typeclasses.items.SeveredHead", key="severed head", location=self.room1)
        self.cap = _garment("knit cap", ["head"], self.head)
        self.head.db.worn_items = {"head": [self.cap]}
        self.limb = create_object("typeclasses.items.Appendage", key="severed left arm", location=self.room1)
        self.glove = _garment("leather glove", ["left_hand"], self.limb)
        self.limb.db.worn_items = {"left_hand": [self.glove]}
        self.said = []
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))

    def run_cmd(self, cls, args, cmdstring):
        cmd = cls(); cmd.caller = self.char1; cmd.args = args; cmd.cmdstring = cmdstring; cmd.switches = []
        cmd.parse()
        with patch("evennia.utils.delay", lambda t, fn, *a, **kw: fn(*a, **kw)):
            cmd.func()
        return " ".join(self.said)


class TestOneQuestionThreeBodies(_Remains):
    def test_the_corpse_answers_from_its_death_record(self):
        self.assertEqual(self.corpse.worn_garments(), [self.coat])

    def test_the_head_and_limb_answer_from_their_ledgers(self):
        self.assertEqual(self.head.worn_garments(), [self.cap])
        self.assertEqual(self.limb.worn_garments(), [self.glove])

    def test_a_character_answers_from_its_registry(self):
        self.assertEqual(self.char1.worn_garments(), list(self.char1.get_worn_items() or []))


class TestFriskTreatsEveryFragmentAsLoot(_Remains):
    def _frisk(self, key):
        from commands.CmdInventory import CmdFrisk
        self.said.clear()
        return self.run_cmd(CmdFrisk, key, "frisk")

    def test_a_limb_is_searched_and_its_glove_reads_as_worn(self):
        said = self._frisk("severed left arm")
        self.assertNotIn("would resist", said, said)
        self.assertIn("patting it down", said, said)
        self.assertIn("leather glove", said, said)
        self.assertRegex(said, r"leather glove\s+\(worn\)")

    def test_a_head_is_searched_and_its_cap_reads_as_worn(self):
        said = self._frisk("severed head")
        self.assertRegex(said, r"knit cap\s+\(worn\)", said)

    def test_a_corpse_frisk_lists_every_worn_garment_not_just_the_disguise_ones(self):
        said = self._frisk("a corpse")
        self.assertRegex(said, r"wool coat\s+\(worn\)", said)
        # carried items are listed bare, with no "(worn)" tag
        self.assertIn("spare coat", said, said)
        self.assertNotRegex(said, r"spare coat\s+\(worn\)", said)


class TestUndressAndGetWorkOnFragments(_Remains):
    def test_undress_the_limb(self):
        from commands.CmdClothing import CmdUndress
        said = self.run_cmd(CmdUndress, "severed left arm", "undress")
        self.assertIn("leather glove", said, said)
        self.assertEqual(self.glove.location, self.char1)
        self.assertEqual(self.limb.worn_garments(), [])

    def test_undress_the_head(self):
        from commands.CmdClothing import CmdUndress
        self.run_cmd(CmdUndress, "severed head", "undress")
        self.assertEqual(self.cap.location, self.char1)
        self.assertEqual(self.head.worn_garments(), [])

    def test_undress_the_corpse_offers_only_what_it_wore(self):
        from commands.CmdClothing import CmdUndress
        said = self.run_cmd(CmdUndress, "a corpse", "undress")
        self.assertEqual(self.coat.location, self.char1)
        self.assertEqual(self.loose.location, self.corpse, "the carried coat was never worn and must stay")

    def test_get_the_glove_from_the_limb(self):
        from commands.CmdInventory import CmdGet
        said = self.run_cmd(CmdGet, "leather glove from severed left arm", "get")
        self.assertEqual(self.glove.location, self.char1, said)
        self.assertEqual(self.limb.worn_garments(), [], "the ledger did not release the slot on the move")
