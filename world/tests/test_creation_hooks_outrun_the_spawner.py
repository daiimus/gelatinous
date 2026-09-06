"""Creation hooks run before the spawner sets attributes (#2430).

`at_object_creation` runs DURING `create_object`; the spawner applies the
prototype's attributes afterwards. Any hook that takes an irreversible
side effect based on its own attributes therefore reads the defensive
defaults and never self-corrects.

Only two hooks in `typeclasses/` take side effects rather than setting
pure defaults, and both were wrong:

**The pack.** `CigarettePack._fill_with_cigarettes` read
`db.cigarette_prototype` and `db.substance` before either was set, so
every pack shipped neutral cigarettes — and the fill is idempotent, so it
never corrected. Live: **all ten Noir packs in the colony held
`tobacco_neutral`**, meaning the brand on the packet and the tobacco
inside it disagreed, against the everything-is-branded rule.

**The corpse.** `_seed_decay_aliases_and_key` read `db.species` before it
was set, seeded human aliases, and overwrote the correct key with "human
corpse". The KEY is repaired later by `_refresh_decay_key_if_changed`;
the ALIASES were not, and that method's docstring says so explicitly —
so a synth chassis answered to "human corpse", "rotting corpse" and
"skeletal remains" for the rest of its existence. Latent right now (all
six live corpses are human), but `IDENTITY_RECOGNITION_SPEC` marks the
species overlay shipped, so it is not a deferred item.

Both repair on the next interaction rather than needing a migration: the
pack when anyone looks at it, the corpse on the room decay check that
already repairs its key.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestThePackMatchesItsLabel(EvenniaTest):
    def _pack(self, substance, proto):
        pack = create_object("typeclasses.smoke.CigarettePack",
                             key="pack of Noir cigarettes",
                             location=self.room1)
        pack.db.substance = substance
        pack.db.cigarette_prototype = proto
        return pack

    def test_a_misbranded_pack_repairs_itself_on_look(self):
        """The live shape: created neutral, attributes applied after."""
        pack = self._pack("tobacco_noir", "CIGARETTE_NOIR")
        for cig in pack.contents:
            cig.db.substance = "tobacco_neutral"
        pack.return_appearance(self.char1)
        substances = {c.db.substance for c in pack.contents}
        self.assertNotIn("tobacco_neutral", substances)

    def test_it_still_has_cigarettes_afterwards(self):
        pack = self._pack("tobacco_noir", "CIGARETTE_NOIR")
        for cig in pack.contents:
            cig.db.substance = "tobacco_neutral"
        pack.return_appearance(self.char1)
        self.assertTrue(pack.contents)

    def test_a_correct_pack_is_left_alone(self):
        pack = self._pack("tobacco_noir", "CIGARETTE_NOIR")
        for cig in pack.contents:
            cig.db.substance = "tobacco_noir"
        before = [c.id for c in pack.contents]
        pack.return_appearance(self.char1)
        self.assertEqual([c.id for c in pack.contents], before)

    def test_a_cigarette_already_taken_out_is_not_touched(self):
        """Somebody's property. Only what is still in the pack is
        replaced."""
        pack = self._pack("tobacco_noir", "CIGARETTE_NOIR")
        taken = pack.contents[0]
        taken.location = self.char1
        taken.db.substance = "tobacco_neutral"
        pack.return_appearance(self.char1)
        self.assertTrue(taken.pk)
        self.assertEqual(taken.db.substance, "tobacco_neutral")


class TestTheCorpseAnswersToItsOwnSpecies(EvenniaTest):
    def _corpse(self, species):
        corpse = create_object("typeclasses.corpse.Corpse",
                               key="human corpse", location=self.room1)
        corpse.db.species = species          # as the spawner does: AFTER
        return corpse

    def test_a_synth_stops_answering_to_human_names(self):
        corpse = self._corpse("synthetic_humanoid")
        corpse._refresh_decay_key_if_changed()
        self.assertNotIn("human corpse", set(corpse.aliases.all()))

    def test_it_answers_to_its_own(self):
        from world.anatomy import get_species_corpse_name
        corpse = self._corpse("synthetic_humanoid")
        corpse._refresh_decay_key_if_changed()
        own = get_species_corpse_name("synthetic_humanoid", "fresh")
        self.assertIn(own, set(corpse.aliases.all()))

    def test_the_generic_aliases_survive(self):
        """"corpse", "body", "remains" are stage- and species-
        independent and must not be pruned with the rest."""
        corpse = self._corpse("synthetic_humanoid")
        corpse._refresh_decay_key_if_changed()
        aliases = set(corpse.aliases.all())
        for generic in ("corpse", "body", "remains"):
            self.assertIn(generic, aliases)

    def test_a_human_corpse_is_unaffected(self):
        corpse = self._corpse("human")
        corpse._refresh_decay_key_if_changed()
        self.assertIn("corpse", set(corpse.aliases.all()))
        self.assertTrue(corpse.key)
