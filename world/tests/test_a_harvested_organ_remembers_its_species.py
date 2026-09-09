"""An organ cut out of a DETACHED part is not human by default (#3067).

#3067 replaced the raw `db.species` read with `world.anatomy.species_of`
across the surgical layer, because detached parts never carry
`db.species` -- they capture theirs at sever time into
`db.source_species`, and no severed-part constructor writes the former.

It missed `_configure_harvested_item`, which is the ONE site that stamps
species onto the harvested item itself, and the only path a harvested
organ is ever built through. So the COMMAND judged a severed rat head
correctly against the rat table while the OBJECT it produced was keyed,
described and made installable as human.

That is precisely the "the object and the command disagreed about what
it was" failure #3067 exists to close, and #3067 plus the rat harvest
axis made it newly REACHABLE: before, both halves were wrongly human, so
at least they agreed with each other.

The regression pin next door could not catch it. It greps for the
literal `db", None), "species"`, which matches only the one-step
`getattr(getattr(x, "db", None), "species", None)` form; this site binds
`source_db` first and then reads `getattr(source_db, "species", None)`,
which the pattern does not see. The pin's FILES tuple also did not list
`world/medical/procedures.py` at all -- both are fixed here.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical.procedures import _configure_harvested_item


class TestAnOrganTakesTheSpeciesOfWhatItCameOutOf(EvenniaTest):

    def _part(self, *, species=None, source_species=None):
        """A detached part, shaped the way the game really makes them."""
        part = create_object("typeclasses.items.Item", key="severed head",
                             location=self.room1)
        if species is not None:
            part.db.species = species
        if source_species is not None:
            part.db.source_species = source_species
        return part

    def _harvest_from(self, source):
        item = create_object("typeclasses.items.Organ", key="organ",
                             location=self.room1)
        _configure_harvested_item(item, organ_name="brain",
                                  condition="fresh", source=source,
                                  organ_data={})
        return item

    def test_an_organ_from_a_severed_rat_head_is_a_rat_organ(self):
        """The reported shape: `db.species` is None, `source_species`
        is where a detached part keeps it."""
        head = self._part(source_species="rat")
        self.assertIsNone(head.db.species)          # premise
        organ = self._harvest_from(head)
        self.assertEqual(organ.db.source_species, "rat")

    def test_the_key_does_not_say_human(self):
        head = self._part(source_species="rat")
        organ = self._harvest_from(head)
        self.assertNotIn("human", organ.key.lower())

    def test_it_is_not_made_installable_into_a_human(self):
        head = self._part(source_species="rat")
        organ = self._harvest_from(head)
        self.assertEqual(list(organ.db.compatible_species or []), ["rat"])

    def test_a_whole_corpse_still_works(self):
        """Corpses DO carry `db.species`; the accessor must not break
        the case that was already right."""
        corpse = self._part(species="human")
        organ = self._harvest_from(corpse)
        self.assertEqual(organ.db.source_species, "human")

    def test_something_with_neither_field_still_defaults_to_human(self):
        organ = self._harvest_from(self._part())
        self.assertEqual(organ.db.source_species, "human")
