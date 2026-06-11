"""Characterization tests for the explosion chain (#469 queue 3/4).

Pins the previously untested core of ``commands/explosion_utils.py``:
unified proximity merging, standalone explosion resolution (room and
in-hands), chain reactions, the auto-defuse pipeline, and the #469
exception policy — explosion resolvers log to the audit trail AND
raise (one-shot timer callbacks have no retry loop to protect).

Backstory worth keeping: writing this suite exposed that **every**
identity broadcast in this module passed ``room=`` to
``msg_room_identity`` (the parameter is ``location``), raising
TypeError — and the broad excepts swallowed it, silently aborting
explosion damage loops, grenade cleanup, and chain reactions at the
first announce.  The ``location=`` assertions below pin the fix.

Run via::

    evennia test --settings settings.py world.tests.test_explosion_chain
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.combat.constants import (
    NDB_COUNTDOWN_REMAINING,
    NDB_PROXIMITY,
    NDB_PROXIMITY_UNIVERSAL,
)


class Bag:
    """Evennia-style attribute holder: unset attributes read as None."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, name):
        return None

    def __delattr__(self, name):
        self.__dict__.pop(name, None)


def make_victim(key="victim"):
    v = MagicMock()
    v.key = key
    v.ndb = Bag()
    v.location = MagicMock()
    return v


def make_grenade(key="grenade", **db_fields):
    g = MagicMock()
    g.key = key
    g.db = Bag(is_explosive=True, **db_fields)
    g.ndb = Bag()
    return g


# ===================================================================
# Unified proximity merge
# ===================================================================


class TestUnifiedProximity(TestCase):
    def test_merges_character_proximity_of_object_proximity(self):
        """Grappling partners of anyone near the grenade get pulled
        into the blast list (human-shield mechanics)."""
        from commands.explosion_utils import get_unified_explosion_proximity

        bystander = make_victim("bystander")
        grappler = make_victim("grappler")
        bystander.ndb = Bag(**{NDB_PROXIMITY: {grappler}})
        grenade = make_grenade()
        grenade.ndb = Bag(**{NDB_PROXIMITY_UNIVERSAL: [bystander]})

        unified = get_unified_explosion_proximity(grenade)
        self.assertIn(bystander, unified)
        self.assertIn(grappler, unified)

    def test_does_not_mutate_original_proximity(self):
        from commands.explosion_utils import get_unified_explosion_proximity

        bystander = make_victim("bystander")
        grappler = make_victim("grappler")
        bystander.ndb = Bag(**{NDB_PROXIMITY: {grappler}})
        grenade = make_grenade()
        original = [bystander]
        grenade.ndb = Bag(**{NDB_PROXIMITY_UNIVERSAL: original})

        get_unified_explosion_proximity(grenade)
        self.assertEqual(original, [bystander])


# ===================================================================
# Standalone explosion — room blast
# ===================================================================


class TestRoomExplosion(TestCase):
    def _explode(self, grenade, shield_modifiers=None):
        from commands.explosion_utils import explode_standalone_grenade

        with patch("commands.explosion_utils.msg_room_identity") as mock_room, \
             patch("commands.explosion_utils.notify_adjacent_rooms_of_explosion"), \
             patch("world.combat.utils.check_grenade_human_shield",
                   return_value=shield_modifiers or {}):
            explode_standalone_grenade(grenade)
        return mock_room

    def test_all_proximity_victims_take_damage_and_grenade_deletes(self):
        """The full damage loop runs for every victim — pinning the
        behavior restored by the room= → location= fix (previously the
        first announce raised and silently spared the rest)."""
        v1, v2 = make_victim("v1"), make_victim("v2")
        grenade = make_grenade(blast_damage=10, damage_type="blast")
        grenade.location = MagicMock()  # a room (not Character/Item)
        grenade.ndb = Bag(**{NDB_PROXIMITY_UNIVERSAL: [v1, v2]})

        mock_room = self._explode(grenade)

        v1.take_damage.assert_called_once_with(
            10, location="chest", injury_type="blast"
        )
        v2.take_damage.assert_called_once_with(
            10, location="chest", injury_type="blast"
        )
        grenade.delete.assert_called_once()
        # Every identity broadcast used the correct keyword.
        for call in mock_room.call_args_list:
            self.assertIn("location", call.kwargs)
            self.assertNotIn("room", call.kwargs)

    def test_human_shield_modifiers_scale_damage(self):
        """Grapplers take zero, their victims double."""
        grappler, shieldee = make_victim("grappler"), make_victim("shieldee")
        grenade = make_grenade(blast_damage=10)
        grenade.location = MagicMock()
        grenade.ndb = Bag(**{NDB_PROXIMITY_UNIVERSAL: [grappler, shieldee]})

        self._explode(
            grenade, shield_modifiers={grappler: 0.0, shieldee: 2.0}
        )
        grappler.take_damage.assert_not_called()
        shieldee.take_damage.assert_called_once()
        self.assertEqual(shieldee.take_damage.call_args.args[0], 20)

    def test_chain_reaction_arms_nearby_explosives(self):
        from commands.explosion_utils import explode_standalone_grenade

        other_bomb = make_grenade("satchel")
        grenade = make_grenade(blast_damage=5, chain_trigger=True)
        grenade.location = MagicMock()
        grenade.ndb = Bag(**{NDB_PROXIMITY_UNIVERSAL: [other_bomb]})

        with patch("commands.explosion_utils.msg_room_identity"), \
             patch("commands.explosion_utils.notify_adjacent_rooms_of_explosion"), \
             patch("world.combat.utils.check_grenade_human_shield",
                   return_value={}), \
             patch("commands.explosion_utils.start_standalone_grenade_ticker") as mock_tick:
            explode_standalone_grenade(grenade)

        self.assertTrue(other_bomb.db.pin_pulled)
        self.assertEqual(
            getattr(other_bomb.ndb, NDB_COUNTDOWN_REMAINING), 1
        )
        mock_tick.assert_called_once_with(other_bomb)

    def test_resolver_failure_is_audited_and_raised(self):
        """The #469 policy: explosion resolvers log to the audit trail
        and re-raise — never a silent half-explosion again."""
        from commands.explosion_utils import explode_standalone_grenade

        victim = make_victim()
        grenade = make_grenade(blast_damage=5)
        grenade.location = MagicMock()
        grenade.ndb = Bag(**{NDB_PROXIMITY_UNIVERSAL: [victim]})

        router = MagicMock()
        with patch("commands.explosion_utils.msg_room_identity",
                   side_effect=RuntimeError("broadcast broke")), \
             patch("commands.explosion_utils.notify_adjacent_rooms_of_explosion"), \
             patch("world.combat.utils.check_grenade_human_shield",
                   return_value={}), \
             patch("commands.explosion_utils.get_splattercast",
                   return_value=router):
            with self.assertRaises(RuntimeError):
                explode_standalone_grenade(grenade)

        logged = " ".join(
            str(c.args[0]) for c in router.msg.call_args_list if c.args
        )
        self.assertIn("Error in explode_standalone_grenade", logged)


# ===================================================================
# Standalone explosion — in someone's hands (real Character)
# ===================================================================


class TestInHandsExplosion(EvenniaTest):
    character_typeclass = Character

    def test_holder_takes_double_damage_and_room_is_told(self):
        from commands.explosion_utils import explode_standalone_grenade

        grenade = make_grenade(blast_damage=10, damage_type="blast")
        grenade.location = self.char1  # isinstance Character → holder
        grenade.ndb = Bag(**{NDB_PROXIMITY_UNIVERSAL: []})

        with patch.object(self.char1, "take_damage") as mock_damage, \
             patch("commands.explosion_utils.msg_room_identity") as mock_room, \
             patch("commands.explosion_utils.notify_adjacent_rooms_of_explosion"):
            explode_standalone_grenade(grenade)

        mock_damage.assert_called_once_with(
            20, location="chest", injury_type="blast"
        )
        grenade.delete.assert_called_once()
        self.assertTrue(mock_room.called)
        self.assertIn("location", mock_room.call_args.kwargs)

    def test_bystanders_shielded_by_holder_take_half(self):
        from commands.explosion_utils import explode_standalone_grenade

        bystander = make_victim("bystander")
        grenade = make_grenade(blast_damage=10, damage_type="blast")
        grenade.location = self.char1
        grenade.ndb = Bag(**{NDB_PROXIMITY_UNIVERSAL: [bystander]})

        with patch.object(self.char1, "take_damage"), \
             patch("commands.explosion_utils.msg_room_identity"), \
             patch("commands.explosion_utils.notify_adjacent_rooms_of_explosion"):
            explode_standalone_grenade(grenade)

        bystander.take_damage.assert_called_once_with(
            5, location="chest", injury_type="blast"
        )


# ===================================================================
# Auto-defuse pipeline
# ===================================================================


class TestAutoDefuse(TestCase):
    def _character_in_room_with(self, *objects):
        char = make_victim("sapper")
        char.location = MagicMock()
        char.location.contents = list(objects)
        return char

    def test_live_grenade_in_proximity_triggers_attempt(self):
        from commands.explosion_utils import check_auto_defuse

        char = self._character_in_room_with()
        grenade = make_grenade(pin_pulled=True)
        grenade.ndb = Bag(**{
            NDB_COUNTDOWN_REMAINING: 5,
            NDB_PROXIMITY_UNIVERSAL: [char],
        })
        char.location.contents = [grenade]

        with patch("commands.explosion_utils.attempt_auto_defuse") as mock_attempt:
            check_auto_defuse(char)
        mock_attempt.assert_called_once_with(char, grenade)

    def test_unpulled_or_expired_grenades_ignored(self):
        from commands.explosion_utils import check_auto_defuse

        char = self._character_in_room_with()
        unpulled = make_grenade("unpulled", pin_pulled=False)
        expired = make_grenade("expired", pin_pulled=True)
        expired.ndb = Bag(**{
            NDB_COUNTDOWN_REMAINING: 0,
            NDB_PROXIMITY_UNIVERSAL: [char],
        })
        char.location.contents = [unpulled, expired]

        with patch("commands.explosion_utils.attempt_auto_defuse") as mock_attempt:
            check_auto_defuse(char)
        mock_attempt.assert_not_called()

    def test_one_attempt_per_character_per_grenade(self):
        from commands.explosion_utils import check_auto_defuse

        char = self._character_in_room_with()
        grenade = make_grenade(pin_pulled=True)
        grenade.ndb = Bag(**{
            NDB_COUNTDOWN_REMAINING: 5,
            NDB_PROXIMITY_UNIVERSAL: [char],
            "defuse_attempted_by": [char],
        })
        char.location.contents = [grenade]

        with patch("commands.explosion_utils.attempt_auto_defuse") as mock_attempt:
            check_auto_defuse(char)
        mock_attempt.assert_not_called()

    def test_attempt_routes_on_skill_roll(self):
        from commands.explosion_utils import attempt_auto_defuse

        char = make_victim("sapper")
        grenade = make_grenade(pin_pulled=True)
        grenade.ndb = Bag(**{NDB_COUNTDOWN_REMAINING: 8})

        # High roll → success handler (15 base + max(0, 10-8)=2 → 17).
        with patch("world.combat.utils.roll_stat", return_value=20), \
             patch("commands.explosion_utils.handle_auto_defuse_success") as ok, \
             patch("commands.explosion_utils.handle_auto_defuse_failure") as bad:
            attempt_auto_defuse(char, grenade)
        ok.assert_called_once()
        bad.assert_not_called()

        # Low roll → failure handler; attempt recorded both times.
        grenade2 = make_grenade(pin_pulled=True)
        grenade2.ndb = Bag(**{NDB_COUNTDOWN_REMAINING: 8})
        with patch("world.combat.utils.roll_stat", return_value=1), \
             patch("commands.explosion_utils.handle_auto_defuse_success") as ok, \
             patch("commands.explosion_utils.handle_auto_defuse_failure") as bad:
            attempt_auto_defuse(char, grenade2)
        bad.assert_called_once()
        ok.assert_not_called()
        self.assertIn(char, grenade2.ndb.defuse_attempted_by)
