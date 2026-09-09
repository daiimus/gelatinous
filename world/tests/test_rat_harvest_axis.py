"""Rat anatomy has the harvest axis filled in (#3068).

`world/anatomy/species.py` defines four species. Rat was the only one
with **no harvestable organs at all** -- 25 organs, 0 harvestable, while
human, robot and synthetic_humanoid each have 12.

That was an omission rather than a decision, on three signals: the human
table writes `"can_be_harvested": False` explicitly when it means it and
the rat block contained the key zero times; the rat table is not sparse
(it carries `bone_type`, `can_be_destroyed`, `backup_available` and
`cannot_be_destroyed`, none of which human uses); and nothing refused
rats structurally -- the listing was empty purely because no organ
carried the flag.

The rule the human table follows, and this now mirrors: **soft viscera
and sense organs yes; bone, spine, lungs and stomach no.** Human
harvests 12 of 28 on exactly that basis and refuses the skeleton, both
spines, both lungs and the stomach.

Rat gets 10, not 12, because rats have no `nose` and no `tongue` organ.

**Harvest only, no `can_be_replaced`.** Human marks heart and liver
replaceable; rats deliberately do not get that, because
`_resolve_install` -- the plain biological-organ path -- has no species
check at all (only the augment and module resolvers consult
`compatible_species`). Demonstrated in play: a harvested rat liver
installs into a human whenever the surgical roll succeeds. "The graft
won't take" is `roll_procedure`'s failure branch, not a refusal.

Tails are not on this axis. `tail` is a SEVERABLE CONTAINER, so a rat
tail is obtained with `sever` and arrives as a proper `rat tail`
Appendage with authored prose -- that already worked. `tail_vertebrae`
is the bone inside it, and bones are not harvested here or in human.
"""
from evennia.utils.test_resources import EvenniaTest

from world.anatomy import SPECIES_DEFINITIONS, get_species_organs

SOFT = {"brain", "heart", "jaw", "left_ear", "right_ear", "left_eye",
        "right_eye", "left_kidney", "right_kidney", "liver"}
NEVER = {"stomach", "left_lung", "right_lung", "cervical_spine",
         "thoracolumbar_spine", "pelvis", "tail_vertebrae"}


def _harvestable(species):
    organs = get_species_organs(species) or {}
    return {n for n, s in organs.items() if (s or {}).get("can_be_harvested")}


def _replaceable(species):
    organs = get_species_organs(species) or {}
    return {n for n, s in organs.items() if (s or {}).get("can_be_replaced")}


class TestNoSpeciesIsLeftWithoutTheAxis(EvenniaTest):
    def test_every_species_harvests_something(self):
        """The defect in one line: rat had 25 organs and 0 harvestable,
        so nothing could be taken from a rat anywhere in the game."""
        empty = [sp for sp in SPECIES_DEFINITIONS
                 if get_species_organs(sp) and not _harvestable(sp)]
        self.assertEqual(empty, [])

    def test_the_other_species_are_unchanged(self):
        for sp in ("human", "robot", "synthetic_humanoid"):
            self.assertEqual(len(_harvestable(sp)), 12, sp)


class TestTheRatSet(EvenniaTest):
    def test_the_soft_viscera_and_senses_are_harvestable(self):
        self.assertEqual(_harvestable("rat"), SOFT)

    def test_bone_spine_lungs_and_stomach_are_not(self):
        taken = _harvestable("rat")
        for name in NEVER:
            self.assertNotIn(name, taken, name)

    def test_no_leg_or_paw_bone_is_harvestable(self):
        taken = _harvestable("rat")
        bones = [n for n in (get_species_organs("rat") or {})
                 if "bone" in n or "bones" in n]
        self.assertTrue(bones, "fixture found no bones to check")
        self.assertEqual([b for b in bones if b in taken], [])

    def test_it_follows_the_human_rule(self):
        """Rat harvests exactly the human set minus the two organs rats
        do not have."""
        rat_organs = set(get_species_organs("rat") or {})
        expected = _harvestable("human") & rat_organs
        self.assertEqual(_harvestable("rat"), expected)

    def test_rats_lack_nose_and_tongue(self):
        """Which is why the count is 10 and not 12."""
        rat_organs = set(get_species_organs("rat") or {})
        self.assertNotIn("nose", rat_organs)
        self.assertNotIn("tongue", rat_organs)


class TestHarvestOnly(EvenniaTest):
    """No `can_be_replaced` on rat organs: `_resolve_install` has no
    species check, so making them replaceable widens that hole rather
    than using it."""

    def test_no_rat_organ_is_replaceable(self):
        self.assertEqual(_replaceable("rat"), set())

    def test_human_still_is(self):
        self.assertEqual(_replaceable("human"), {"heart", "liver"})


class TestTailsAreSeveredNotHarvested(EvenniaTest):
    def test_tail_is_a_severable_container(self):
        from world.anatomy import get_species_severable_containers
        self.assertIn("tail", get_species_severable_containers("rat"))

    def test_the_tail_bone_is_not_harvestable(self):
        self.assertNotIn("tail_vertebrae", _harvestable("rat"))

    def test_severing_a_tail_yields_an_appendage(self):
        from evennia import create_object
        from typeclasses.items import apply_sever_to_character
        rat = create_object("typeclasses.characters.Character",
                            key="a rat", location=self.room1)
        rat.db.species = "rat"
        before = {o.id for o in self.room1.contents}
        apply_sever_to_character(rat, "tail")
        new = [o for o in self.room1.contents if o.id not in before]
        self.assertTrue(any("tail" in (o.key or "") for o in new),
                        f"severing produced {[o.key for o in new]}")
