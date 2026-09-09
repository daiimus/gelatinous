"""`undress <corpse>` offers what the corpse is shown wearing (#2977).

`_corpse_garments` returns everything in a corpse's contents that
declares `coverage`, and its docstring gives the reason:

    That is the corpse's real model -- `_build_corpse_clothing_coverage_map`
    already renders every item in `contents` that declares `coverage` as
    covering the body.

That premise was true only while `corpse.db.worn_at_death` was always
`None`, which is exactly the state #3107 found and fixed: the record was
never being written, so the coverage map fell back to rendering
contents-wide and the two lists agreed by accident.

With the record written, they diverge:

    worn_at_death: [16505]
    coverage map credits: ['surgical scrubs']
    undress offers    : ['surgical scrubs', 'white lab coat']

So `undress` offers to take off a coat the corpse was carrying in a
pocket, was never shown wearing, and whose removal changes nothing in
the description. This is a door I opened myself while closing another
one -- the fix for the record and the consumer of the record were in
different files, and only one of them was looked at.

The fallback is kept deliberately and matches `Corpse.note_dressed`'s
stated rule: "No record means the map still renders contents-wide", so a
corpse from before the record existed still undresses exactly as it
renders.
"""
from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from commands.CmdClothing import _corpse_garments
from typeclasses.death_progression import DeathProgressionScript


class TestUndressMatchesTheDescription(EvenniaTest):

    def _corpse(self):
        who = create_object("typeclasses.characters.Character",
                            key="Testdead", location=self.room1)
        self.worn = spawn("MEDICAL_SCRUBS")[0]
        self.worn.location = who
        self.carried = spawn("LAB_COAT")[0]
        self.carried.location = who
        who.wear_item(self.worn)
        return DeathProgressionScript._create_corpse_from_character(None, who)

    def _shown(self, corpse):
        cov = corpse._build_corpse_clothing_coverage_map()
        out = set()
        for items in cov.values():
            for g in (items if isinstance(items, (list, tuple)) else [items]):
                out.add(g.key)
        return out

    def test_the_worn_garment_is_offered(self):
        """Control: this must not become 'undress offers nothing'."""
        corpse = self._corpse()
        self.assertIn(self.worn.key,
                      [g.key for g in _corpse_garments(corpse)])

    def test_a_merely_carried_garment_is_not_offered(self):
        corpse = self._corpse()
        self.assertNotIn(
            self.carried.key, [g.key for g in _corpse_garments(corpse)],
            "undress offered a garment the corpse was only carrying")

    def test_the_two_lists_agree(self):
        """The property that matters: you can take off what you can see."""
        corpse = self._corpse()
        self.assertEqual(self._shown(corpse),
                         {g.key for g in _corpse_garments(corpse)})

    def test_a_corpse_with_no_record_still_undresses_contents_wide(self):
        """`note_dressed`: "No record means the map still renders
        contents-wide" -- an old corpse must not become undressable
        down to nothing."""
        corpse = self._corpse()
        corpse.attributes.remove("worn_at_death")
        offered = {g.key for g in _corpse_garments(corpse)}
        self.assertIn(self.carried.key, offered)
        self.assertIn(self.worn.key, offered)
