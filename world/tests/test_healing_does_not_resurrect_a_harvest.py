"""`full_heal` does not put back what a ripper took out (#2455).

`MedicalState.full_heal`'s own docstring promises it "never regrows a
severed limb or resurrects a harvested-out module (which would
duplicate its ability)", and `CmdAdmin` carries the same assertion at
both call sites. The code skipped only `wound_stage == "severed"`.

But `severed` is written into the death-time SNAPSHOT branch, which
corpses have and living characters do not. On a LIVING target
`_mark_organ_removed` stamps `injury_type="harvested"` and
`wound_stage="fresh"` — so a harvested organ fell straight through to
the restore.

A ripper cuts a shotgun module out of someone; the module is in the
ripper's hands. Staff then `@heal` or revive that character and the
module is back at full HP inside them, `/shotgun` works again, and the
extracted item still exists in the world. The ability is duplicated —
and `db.removed_organs` still lists the name, so the resurrected organ
cannot even be re-harvested through either door.

`injury_type` is the durable marker here, not the stage: `suture` moves
a harvested organ from "fresh" to "treated" and deliberately leaves the
injury type alone, so the stage cannot carry this and the type can.
`removed_organs` is consulted as a second source because it is the
authoritative record and survives anything that rewrites the organ row.

**Two of the issue's five findings were already fixed**, and checking
beat assuming. The blindsight / voice-modulator flags no longer exist:
`has_deployed_ability` asks the anatomy directly, and its docstring
names the case that made the old flag unfixable — a forearm module shot
to 0 HP while the arm stays attached calls no teardown hook at all.
And installing into a corpse now refuses instead of deleting the organ
and reporting success (#2507).
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _HarvestCase(EvenniaTest):
    def victim(self):
        return create_object("typeclasses.characters.Character",
                             key="Victim", location=self.room1)

    def harvested_organ(self, target):
        """The state `_mark_organ_removed` leaves on a LIVING body."""
        name = next(iter(target.medical_state.organs))
        organ = target.medical_state.organs[name]
        organ.current_hp = 0
        organ.injury_type = "harvested"
        organ.wound_stage = "fresh"
        target.db.removed_organs = [name]
        return name, organ


class TestAHealDoesNotPutItBack(_HarvestCase):
    def test_the_harvested_organ_stays_gone(self):
        target = self.victim()
        _name, organ = self.harvested_organ(target)
        target.medical_state.full_heal()
        self.assertEqual(organ.current_hp, 0)

    def test_it_keeps_its_harvested_marker(self):
        target = self.victim()
        _name, organ = self.harvested_organ(target)
        target.medical_state.full_heal()
        self.assertEqual(organ.injury_type, "harvested")

    def test_a_sutured_harvest_is_still_not_restored(self):
        """`suture` moves the stage to "treated" and leaves the injury
        type — so the stage cannot be the marker."""
        target = self.victim()
        _name, organ = self.harvested_organ(target)
        organ.wound_stage = "treated"
        target.medical_state.full_heal()
        self.assertEqual(organ.current_hp, 0)

    def test_removed_organs_alone_is_enough(self):
        """The authoritative record, in case anything rewrites the row."""
        target = self.victim()
        name, organ = self.harvested_organ(target)
        organ.injury_type = None
        target.db.removed_organs = [name]
        target.medical_state.full_heal()
        self.assertEqual(organ.current_hp, 0)


class TestOrdinaryHealingStillWorks(_HarvestCase):
    def test_a_wounded_organ_is_restored(self):
        target = self.victim()
        name = next(iter(target.medical_state.organs))
        organ = target.medical_state.organs[name]
        organ.current_hp = 1
        organ.injury_type = "blunt"
        organ.wound_stage = "fresh"
        target.medical_state.full_heal()
        self.assertEqual(organ.current_hp, organ.max_hp)

    def test_its_wound_bookkeeping_is_cleared(self):
        target = self.victim()
        name = next(iter(target.medical_state.organs))
        organ = target.medical_state.organs[name]
        organ.current_hp = 1
        organ.injury_type = "blunt"
        target.medical_state.full_heal()
        self.assertIsNone(organ.injury_type)

    def test_a_destroyed_in_place_organ_is_restored(self):
        """Destroyed is still ATTACHED — the docstring says those
        restore fully."""
        target = self.victim()
        name = next(iter(target.medical_state.organs))
        organ = target.medical_state.organs[name]
        organ.current_hp = 0
        organ.injury_type = "ballistic"
        target.medical_state.full_heal()
        self.assertEqual(organ.current_hp, organ.max_hp)

    def test_a_severed_organ_is_still_skipped(self):
        target = self.victim()
        name = next(iter(target.medical_state.organs))
        organ = target.medical_state.organs[name]
        organ.current_hp = 0
        organ.wound_stage = "severed"
        target.medical_state.full_heal()
        self.assertEqual(organ.current_hp, 0)


class TestTheTwoAlreadyFixedStayFixed(EvenniaTest):
    """Regression pins, not evidence."""

    def test_abilities_ask_anatomy_not_a_character_flag(self):
        from world.medical.augments import has_deployed_ability
        import inspect
        from world.combat import capacity
        from world import voice
        for module in (capacity, voice):
            self.assertIn("has_deployed_ability", inspect.getsource(module))
        self.assertTrue(callable(has_deployed_ability))

    def test_no_blindsight_flag_is_written_anywhere(self):
        import inspect
        from world.medical import augments
        self.assertNotIn("blindsight_active", inspect.getsource(augments))

    def test_installing_into_a_corpse_refuses_instead_of_deleting(self):
        import inspect
        from world.medical.procedures import _resolve_install
        source = inspect.getsource(_resolve_install)
        self.assertIn("needs a living body", source)
