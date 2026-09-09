"""A harvestable organ always has prose to show (#2777).

`get_organ_default_description` returns `""` when no prose is
registered, and its docstring is explicit that callers should "treat
empty as render nothing rather than asserting". That is the right
contract for an organ nobody can hold. It is the wrong outcome for one
a player just cut out of a body.

Twelve organs across the four species currently have no prose:

    human 1 · rat 10 · synthetic_humanoid 1 · robot 0

**None of them is harvestable, so none is reachable today.** This test
pins that coincidence into an invariant, because the two facts are
maintained in different files by different edits and nothing connected
them.

That gap is not hypothetical. #3069 turned ten rat organs from
unharvestable to harvestable in `species.py` without touching
`organ_descriptions.py`, and it happened to be safe only because every
one of those ten already had prose via the default organic fallback.
The next such change gets a failing test instead of a silent empty
description.

**#2777's premise does not hold, and this test records why.** It
reports that harvesting a human, rat or synthetic `cervical_spine`
yields an empty description, and that robot is the only species where
it renders. Measured: `cervical_spine` has `can_be_harvested` unset on
**all four species, robot included**, and the harvest command offers it
on none of them. There is no way to obtain the organ the issue is
about. Its robot/human contrast was reading the description table, not
the harvestability flag.
"""
from evennia.utils.test_resources import EvenniaTest

from world.anatomy import SPECIES_DEFINITIONS, get_species_organs
from world.anatomy.organs import get_organ_default_description

CONDITIONS = ("pristine", "damaged", "putrid")


def _harvestable(species):
    return {name for name, spec in (get_species_organs(species) or {}).items()
            if (spec or {}).get("can_be_harvested")}


class TestEveryHarvestableOrganHasProse(EvenniaTest):
    def test_no_harvestable_organ_renders_empty(self):
        offenders = []
        for species in SPECIES_DEFINITIONS:
            for organ in sorted(_harvestable(species)):
                if not get_organ_default_description(
                        organ, "pristine", species=species):
                    offenders.append(f"{species}/{organ}")
        self.assertEqual(offenders, [], "; ".join(offenders))

    def test_damaged_and_putrid_render_too(self):
        """A harvested organ is rarely pristine -- the decay states are
        the ones a player actually sees."""
        offenders = []
        for species in SPECIES_DEFINITIONS:
            for organ in sorted(_harvestable(species)):
                for condition in CONDITIONS:
                    if not get_organ_default_description(
                            organ, condition, species=species):
                        offenders.append(f"{species}/{organ}/{condition}")
        self.assertEqual(offenders[:10], [], "; ".join(offenders[:10]))

    def test_every_species_is_checked(self):
        """Guards the guard: a species with no harvestable organs would
        make the sweep above vacuously true for it."""
        for species in SPECIES_DEFINITIONS:
            self.assertTrue(_harvestable(species), f"{species} harvests nothing")


class TestTheUnreachableGapsStayUnreachable(EvenniaTest):
    """The organs with no prose are fine precisely because nobody can
    hold one. If that changes, the test above starts failing -- this one
    documents the current shape so the failure reads clearly."""

    def test_cervical_spine_is_not_harvestable_on_any_species(self):
        from world.anatomy import get_organ_spec
        for species in SPECIES_DEFINITIONS:
            spec = get_organ_spec("cervical_spine", species) or {}
            self.assertFalse(
                spec.get("can_be_harvested"),
                f"{species} now harvests cervical_spine; it needs prose")

    def test_organs_without_prose_are_all_unharvestable(self):
        for species in SPECIES_DEFINITIONS:
            harvestable = _harvestable(species)
            for organ in get_species_organs(species) or {}:
                if get_organ_default_description(organ, "pristine",
                                                 species=species):
                    continue
                self.assertNotIn(organ, harvestable,
                                 f"{species}/{organ} is harvestable and mute")
