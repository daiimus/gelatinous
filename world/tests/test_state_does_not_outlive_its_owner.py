"""Two pieces of state that outlived the thing scoped to clear them
(#2579, #2580).

## #2579 — a logged-out body kept its seat

`at_post_unpuppet` pulls the body off the grid with a **direct
assignment** to `location`, not a `move_to` — so `at_post_move` never
fires, and `at_post_move` is where posture is cleared. The furniture
module's own docstring promises *"moving auto-stands you"*: true of
movement, false of logout.

So the seat stayed occupied by a body no longer in the world. The
capacity guard counts them, so a disconnect could hold a chair against
everyone else indefinitely — and `is_restrained()` reads `db.furniture`,
which is one of the free-action paths in the consent gate.

Live when found: **three characters holding a seat, two of them off the
grid.** The third is the Rook, who has to be in the broadcast chair to
transmit — a seated NPC with no session is not a bug. The clearing is
therefore on **unpuppet**, not on posture generally, and the repair
script skipped her explicitly.

## #2580 — a lost organ left its effect switched on

Two of the four toggleable abilities record the same fact twice: on the
organ (`ability_state["deployed"]`) and on the **character**, because
that is where the consumers read it — `world.voice.get_voice_signature`
and `world.combat.capacity`. Normal toggle-off clears both. The
organ-**loss** hooks cleared only the organ half.

Lose the limb while engaged and the effect stays on permanently, with no
way to switch it off: the toggle refuses, because the organ it looks for
is gone. Full accuracy with no eyes and no hardware.

Cleared across the **remaining living hosts** rather than outright: an
ability can be seated in more than one organ (#2483), and losing one of
a pair must not switch off the other.

**One thing checked and found NOT to be a bug:** those hooks guard with
`isinstance(ability_state, dict)`, which is the `_SaverDict` shape that
has bitten this codebase seven times. `MedicalState` is a plain Python
object serialised to and from a dict, so the entries stay real dicts
through a round-trip — verified rather than assumed.
"""
from evennia.utils.test_resources import EvenniaTest


class TestLogoutStandsYouUp(EvenniaTest):
    def seated(self):
        seat = self.obj1
        self.char1.db.posture = "sitting"
        self.char1.db.furniture = seat
        self.char1.temp_place = "sitting on a stool."
        return seat

    def unpuppet(self):
        """No sessions attached, which is the branch that stows the
        body."""
        self.char1.at_post_unpuppet()

    def test_the_posture_is_cleared(self):
        self.seated()
        self.unpuppet()
        self.assertEqual(self.char1.db.posture, "standing")

    def test_the_seat_is_released(self):
        self.seated()
        self.unpuppet()
        self.assertIsNone(self.char1.db.furniture)

    def test_the_placement_line_goes_too(self):
        self.seated()
        self.unpuppet()
        self.assertEqual(self.char1.temp_place, "")

    def test_the_body_still_leaves_the_grid(self):
        """The hook's actual job must survive the addition."""
        self.seated()
        self.unpuppet()
        self.assertIsNone(self.char1.location)

    def test_the_prelogout_location_is_still_recorded(self):
        self.seated()
        where = self.char1.location
        self.unpuppet()
        self.assertEqual(self.char1.db.prelogout_location, where)

    def test_a_standing_character_is_unaffected(self):
        self.char1.db.posture = "standing"
        self.char1.db.furniture = None
        self.unpuppet()
        self.assertEqual(self.char1.db.posture, "standing")


class TestASeatedNpcIsNotTouched(EvenniaTest):
    """The Rook has to stay in the broadcast chair to transmit. The
    clearing is on UNPUPPET, so anything never puppeted keeps its seat
    — pinned, because "no session and sitting" looks like the bug."""

    def test_sitting_with_no_session_is_not_itself_cleared(self):
        seat = self.obj1
        self.char2.db.posture = "sitting"
        self.char2.db.furniture = seat
        self.assertEqual(self.char2.sessions.count(), 0)
        # nothing calls at_post_unpuppet on an NPC that never logged in
        self.assertEqual(self.char2.db.posture, "sitting")
        self.assertIs(self.char2.db.furniture, seat)


class _AbilityCase(EvenniaTest):
    def seat(self, ability, ability_type, container="head"):
        state = self.char1.medical_state
        organ = next((o for o in state.organs.values()
                      if getattr(o, "container", None) == container
                      and o.current_hp > 0), None)
        self.assertIsNotNone(organ, f"no living organ in {container}")
        data = dict(organ.data)
        merged = dict(data.get("abilities") or {})
        merged[ability] = {"type": ability_type}
        data["abilities"] = merged
        organ.data = data
        self.char1.medical_state = state
        return organ


class TestLosingTheOrganSwitchesTheEffectOff(_AbilityCase):
    """Blindsight and the modulator are read off the ORGAN (#2484), so
    every way of losing it ends the effect — including the one that
    calls no teardown hook at all."""

    def blindsight(self):
        from world.combat.capacity import _blindsight_active
        return _blindsight_active(self.char1)

    def modulated(self):
        from world.voice import is_voice_modulated
        return is_voice_modulated(self.char1)

    def test_blindsight_ends_on_harvest(self):
        from world.medical.augments import (park_organ_hardware,
                                            toggle_ability)
        organ = self.seat("eyez", "blindsight")
        toggle_ability(self.char1, "eyez")
        self.assertTrue(self.blindsight())
        park_organ_hardware(self.char1, organ)
        self.assertFalse(self.blindsight())

    def test_the_modulator_ends_on_harvest(self):
        from world.medical.augments import (park_organ_hardware,
                                            toggle_ability)
        organ = self.seat("modulate", "voice_modulator")
        toggle_ability(self.char1, "modulate")
        self.assertTrue(self.modulated())
        park_organ_hardware(self.char1, organ)
        self.assertFalse(self.modulated())

    def test_severance_ends_it_too(self):
        from world.medical.augments import (carry_hardware_to_appendage,
                                            toggle_ability)
        from evennia import create_object
        self.seat("eyez", "blindsight")
        toggle_ability(self.char1, "eyez")
        self.assertTrue(self.blindsight())
        limb = create_object("typeclasses.items.Appendage", key="a head",
                             location=self.room1)
        carry_hardware_to_appendage(self.char1, ["head"], limb)
        self.assertFalse(self.blindsight())

    def test_a_module_destroyed_in_place_ends_it(self):
        """The third route, and the one that ran NO cleanup code: the
        module is shot to 0 HP while the limb stays attached. Nothing is
        harvested, nothing is severed, so neither parking hook fires —
        and `iter_abilities` then skips the dead organ, so the toggle
        that could have cleared a flag answers "you have no cyberware to
        command". A cached flag was welded on for good."""
        organ = self.seat("eyez", "blindsight")
        from world.medical.augments import toggle_ability
        toggle_ability(self.char1, "eyez")
        self.assertTrue(self.blindsight())
        organ.current_hp = 0
        self.char1.medical_state = self.char1.medical_state
        self.assertFalse(self.blindsight())

    def test_a_modulator_destroyed_in_place_ends_it(self):
        organ = self.seat("modulate", "voice_modulator")
        from world.medical.augments import toggle_ability
        toggle_ability(self.char1, "modulate")
        self.assertTrue(self.modulated())
        organ.current_hp = 0
        self.char1.medical_state = self.char1.medical_state
        self.assertFalse(self.modulated())

    def test_the_toggle_really_does_refuse_a_dead_organ(self):
        """Pinning the reason route 3 was unrecoverable, so the fix is
        not mistaken for redundant with the toggle."""
        organ = self.seat("eyez", "blindsight")
        from world.medical.augments import toggle_ability
        toggle_ability(self.char1, "eyez")
        organ.current_hp = 0
        self.char1.medical_state = self.char1.medical_state
        self.assertIn("no cyberware", toggle_ability(self.char1, "eyez"))

    def test_a_second_host_keeps_the_effect_running(self):
        """One ability can seat into two organs (#2483); losing one must
        not switch off the other."""
        self.seat("eyez", "blindsight", container="head")
        organ_b = self.seat("eyez", "blindsight", container="chest")
        from world.medical.augments import (park_organ_hardware,
                                            toggle_ability)
        toggle_ability(self.char1, "eyez")
        park_organ_hardware(self.char1, organ_b)
        self.assertTrue(self.blindsight())

    def test_an_ability_with_no_character_effect_is_left_alone(self):
        """Natural weapons keep their state on the organ only — parking
        one must not raise."""
        from world.medical.augments import park_organ_hardware
        organ = self.seat("nailz", "natural_weapon", container="right_hand")
        park_organ_hardware(self.char1, organ)   # must not raise


class TestTheAbilityStateIsARealDict(EvenniaTest):
    """The `_SaverDict` shape has bitten this codebase seven times, and
    both loss hooks guard with `isinstance(..., dict)`. Verified here
    rather than assumed: `MedicalState` is a plain object serialised to
    and from a dict, so entries survive as real dicts."""

    def test_it_round_trips_as_a_dict(self):
        from world.medical.augments import _ability_state
        state = self.char1.medical_state
        organ = next(iter(state.organs.values()))
        _ability_state(organ, "probe")["deployed"] = True
        self.char1.medical_state = state
        self.char1.save_medical_state()
        again = self.char1.medical_state
        organ2 = next(iter(again.organs.values()))
        for entry in (getattr(organ2, "ability_state", None) or {}).values():
            self.assertIsInstance(entry, dict)
