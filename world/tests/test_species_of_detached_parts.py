"""A detached part is judged by the species it remembers (#2546).

The game stores species in two fields and the callers were reading only
one. Living characters and corpses carry `db.species` --
`death_progression` sets it on the corpse. **Detached parts never do**:
limbs, heads and harvested organs capture theirs at sever time into
`db.source_species`, and no severed-part constructor writes
`db.species` at all.

So every species lookup on a detached part returned `None` and fell
back to human, while the part's own name and description were rendered
from `source_species`. The object and the command disagreed about what
it was.

Measured live before the fix: **43 severed parts, every one with
`db.species = None`**, including real rat heads carrying five organs
apiece -- so they are genuine surgical targets, not inert props.

The concrete failure: the human `brain` spec has
`can_be_harvested=True` and the rat's does not. A severed rat head fell
back to the human table and offered brain, eyes, ears and jaw as
harvestable, while the rat *corpse* -- which does carry
`db.species="rat"` -- refused them. Same animal, same organ, opposite
answer depending on which piece you were holding.

The fix is one accessor, `world.anatomy.species_of`, because the call
sites will not stay in sync by hand -- there were fourteen of them
across five modules. `species` is checked first and `source_species` is
the fallback, so bodies and corpses keep answering off the field they
already use.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.anatomy import get_organ_spec


def _species_of(target):
    from world.anatomy import species_of
    return species_of(target)


class _PartCase(EvenniaTest):
    def part(self, source_species):
        """A detached part as the sever pipeline leaves it: it knows
        its origin, and `db.species` is never written."""
        obj = create_object("typeclasses.objects.Object",
                            key="a severed thing", location=self.room1)
        obj.db.source_species = source_species
        return obj


class TestThePremise(_PartCase):
    def test_a_detached_part_has_no_db_species(self):
        part = self.part("rat")
        self.assertIsNone(part.attributes.get("species", default=None))

    def test_but_it_remembers_where_it_came_from(self):
        self.assertEqual(self.part("rat").db.source_species, "rat")

    def test_the_old_read_returned_none(self):
        part = self.part("rat")
        old = getattr(getattr(part, "db", None), "species", None)
        self.assertIsNone(old, "premise gone: something now sets db.species")

    def test_the_two_anatomy_tables_really_differ(self):
        """If human and rat agreed about the brain there would be no
        observable failure to fix."""
        self.assertTrue(get_organ_spec("brain", "human").get("can_be_harvested"))
        self.assertFalse(
            (get_organ_spec("brain", "rat") or {}).get("can_be_harvested"))


class TestTheAccessor(_PartCase):
    def test_a_detached_part_answers_with_its_source(self):
        self.assertEqual(_species_of(self.part("rat")), "rat")

    def test_a_living_body_still_answers_with_db_species(self):
        self.char1.db.species = "robot"
        self.assertEqual(_species_of(self.char1), "robot")

    def test_db_species_wins_when_both_are_set(self):
        """Corpses carry both after a post-mortem severance; the body's
        own field is the authority."""
        part = self.part("rat")
        part.db.species = "human"
        self.assertEqual(_species_of(part), "human")

    def test_neither_set_returns_none(self):
        """Callers apply their own `or "human"`; the accessor must not
        pre-empt that."""
        bare = create_object("typeclasses.objects.Object", key="a rock",
                             location=self.room1)
        self.assertIsNone(_species_of(bare))

    def test_it_survives_an_object_with_no_db(self):
        self.assertIsNone(_species_of(object()))


class TestTheInstrumentRefusal(_PartCase):
    """`instruments_wanted` told a surgeon holding a severed robot limb
    that they needed a surgical kit."""

    def test_a_severed_robot_part_wants_a_tool_roll(self):
        from world.medical.utils import instruments_wanted
        self.assertEqual(instruments_wanted(self.part("robot")),
                         "a tool roll")

    def test_a_severed_flesh_part_still_wants_a_kit(self):
        from world.medical.utils import instruments_wanted
        self.assertEqual(instruments_wanted(self.part("rat")),
                         "a surgical kit")

    def test_a_robot_body_is_unchanged(self):
        from world.medical.utils import instruments_wanted
        self.char1.db.species = "robot"
        self.assertEqual(instruments_wanted(self.char1), "a tool roll")


class TestSupplyMatching(_PartCase):
    """`serves_species` judges whether a supply can do anything for a
    body; it was judging detached parts as human."""

    def test_the_supply_helper_sees_the_source_species(self):
        from world.medical.utils import _species_of as supply_species
        self.assertEqual(supply_species(self.part("robot")), "robot")

    def test_it_still_defaults_to_human(self):
        from world.medical.utils import _species_of as supply_species
        bare = create_object("typeclasses.objects.Object", key="a rock",
                             location=self.room1)
        self.assertEqual(supply_species(bare), "human")


class TestNoSurgicalSiteReadsTheRawFieldAnyMore(EvenniaTest):
    """Fourteen call sites will not stay in sync by hand. Pin the ones
    that judge a body's anatomy so a new one cannot quietly reintroduce
    the split."""

    FILES = (
        "commands/CmdOperate.py",
        "commands/CmdSurgical.py",
        "world/medical/utils.py",
        "world/medical/severance.py",
        "world/medical/wounds/messages/__init__.py",
    )

    def test_they_go_through_the_accessor(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        offenders = []
        for rel in self.FILES:
            body = (root / rel).read_text()
            for num, line in enumerate(body.splitlines(), 1):
                if 'db", None), "species"' in line:
                    offenders.append(f"{rel}:{num}")
        self.assertEqual(offenders, [])
