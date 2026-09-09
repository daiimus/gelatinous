"""Skeletal remains refuse soft-tissue harvest (#2816).

`ORGAN_CONDITION_BY_DECAY` maps the `skeletal` decay stage to the
condition `refuse`, and **no organ has prose registered for it**.
`world/anatomy/organs.py` says so in its own docstring, and explains
why that is safe:

    The `refuse` condition (current skeletal-stage soft-tissue gate) is
    intentionally absent: skeletal corpses refuse soft-tissue harvest at
    the command gate, so no Organ instance ever reaches that condition
    with registered prose.

**There was no such gate.** Driven in game against a corpse aged past
the one-week skeletal threshold, `harvest` listed all twelve soft
organs on "skeletal remains", the roll succeeded, and it produced:

    item: 'desiccated liver'
    desc: "It's a thing. Heavy enough to hurt if used wrong."

Not the empty string the docstring implies -- the generic fallback
object description, which is worse, because it reads as a real item
somebody forgot to write.

The gate lives at the RESOLVER, not in `CmdHarvest`, for the same
reason the incision check immediately above it does: chart-commenced
harvests call `start_procedure` directly and bypass command-level
gates. The listing is filtered too, so a player is not offered a
command that cannot succeed.

Bones are deliberately exempt. `BONE_ORGANS` carry their own
`desiccated` tier (#213) for the skeletal-stage bone harvest #227
anticipates, so this refuses soft tissue only and that feature can land
without unpicking the gate. A skeletal human still yields a jaw.
"""
import time

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.anatomy.organs import BONE_ORGANS
from world.combat.constants import ORGAN_CONDITION_BY_DECAY


def _skeletal(corpse):
    """Age a corpse past the skeletal threshold the way time would.
    `get_decay_stage` reads `creation_time`, not `death_time` -- my
    first probe set the wrong field and the corpse stayed 'fresh'."""
    corpse.db.creation_time = time.time() - (60 * 60 * 24 * 400)
    return corpse


class _CorpseCase(EvenniaTest):
    def corpse(self, skeletal=True):
        c = create_object("typeclasses.corpse.Corpse",
                          key="a corpse", location=self.room1)
        if skeletal:
            _skeletal(c)
        return c


class TestThePremise(_CorpseCase):
    def test_skeletal_maps_to_refuse(self):
        self.assertEqual(ORGAN_CONDITION_BY_DECAY.get("skeletal"), "refuse")

    def test_refuse_has_no_prose_for_any_organ(self):
        """If prose were registered, gating would be the wrong fix."""
        from world.anatomy import SPECIES_DEFINITIONS, get_species_organs
        from world.anatomy.organs import get_organ_default_description
        for species in SPECIES_DEFINITIONS:
            for organ in get_species_organs(species) or {}:
                self.assertFalse(
                    get_organ_default_description(organ, "refuse",
                                                  species=species),
                    f"{species}/{organ} now has refuse prose")

    def test_the_fixture_really_reaches_skeletal(self):
        self.assertEqual(self.corpse().get_decay_stage(), "skeletal")

    def test_a_fresh_corpse_is_not_skeletal(self):
        self.assertNotEqual(self.corpse(skeletal=False).get_decay_stage(),
                            "skeletal")


class TestSoftTissueIsRefused(_CorpseCase):
    def _harvest(self, corpse, organ):
        from world.medical.procedures import _resolve_harvest, open_incision
        said = []
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        open_incision(corpse, "abdomen", surgeon=self.char1)
        before = set(self.room1.contents) | set(self.char1.contents)
        _resolve_harvest(self.char1, corpse, organ_name=organ,
                         location="abdomen")
        made = [o for o in list(self.room1.contents) + list(self.char1.contents)
                if o not in before]
        return "\n".join(said), made

    def test_a_liver_is_refused(self):
        out, made = self._harvest(self.corpse(), "liver")
        self.assertIn("nothing but bone", out)
        self.assertEqual(made, [])

    def test_the_refusal_names_the_organ(self):
        out, _ = self._harvest(self.corpse(), "liver")
        self.assertIn("liver", out)

    def test_a_fresh_corpse_is_not_refused(self):
        """The gate must not swallow ordinary harvesting."""
        out, _made = self._harvest(self.corpse(skeletal=False), "liver")
        self.assertNotIn("nothing but bone", out)


class TestBonesStayHarvestable(_CorpseCase):
    """#227 will want skeletal-stage bone harvest; the gate is written
    so that lands without unpicking it."""

    def test_jaw_is_a_bone(self):
        self.assertIn("jaw", BONE_ORGANS)

    def test_a_bone_is_not_refused_at_skeletal(self):
        from world.medical.procedures import _resolve_harvest, open_incision
        corpse = self.corpse()
        said = []
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        open_incision(corpse, "head", surgeon=self.char1)
        _resolve_harvest(self.char1, corpse, organ_name="jaw",
                         location="head")
        self.assertNotIn("nothing but bone", "\n".join(said))
