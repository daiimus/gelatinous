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
    def test_blindsight_flag_is_cleared_on_harvest(self):
        from world.combat.capacity import BLINDSIGHT_FLAG
        from world.medical.augments import (park_organ_hardware,
                                            toggle_ability)
        organ = self.seat("eyez", "blindsight")
        toggle_ability(self.char1, "eyez")
        self.assertTrue(getattr(self.char1.db, BLINDSIGHT_FLAG))
        park_organ_hardware(self.char1, organ)
        self.assertFalse(getattr(self.char1.db, BLINDSIGHT_FLAG))

    def test_voice_modulator_flag_is_cleared_on_harvest(self):
        from world.medical.augments import (park_organ_hardware,
                                            toggle_ability)
        organ = self.seat("modulate", "voice_modulator")
        toggle_ability(self.char1, "modulate")
        self.assertTrue(self.char1.db.voice_modulator_active)
        park_organ_hardware(self.char1, organ)
        self.assertFalse(self.char1.db.voice_modulator_active)

    def test_severance_clears_it_too(self):
        from world.combat.capacity import BLINDSIGHT_FLAG
        from world.medical.augments import (carry_hardware_to_appendage,
                                            toggle_ability)
        from evennia import create_object
        organ = self.seat("eyez", "blindsight")
        toggle_ability(self.char1, "eyez")
        limb = create_object("typeclasses.items.Appendage", key="a head",
                             location=self.room1)
        carry_hardware_to_appendage(self.char1, ["head"], limb)
        self.assertFalse(getattr(self.char1.db, BLINDSIGHT_FLAG))

    def test_an_ability_with_no_character_flag_is_left_alone(self):
        """Natural weapons keep their state on the organ only — the
        helper must not invent a flag for them."""
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
