"""
Characterization tests for the throw system (issue #471).

These tests pin the **user-confirmed-correct behavior** of the throw
system.  Written against the original monolithic ``CmdThrow`` (step
1), they now target the split layout (step 2): parsing / validation /
announcements in ``commands/CmdThrow.py``, physics in
``world/combat/throwing.py``.  The assertions are the contract — the
restructure moved the seams, not the behavior.

Notable behaviors documented here:

* **Dedicated throwing weapons never take the utility flight path.**
  Targeted throws redirect to the ``attack`` command; untargeted
  ones get a guidance message.  The old unreachable
  ``is_weapon=True`` flight plumbing was deleted in step 2;
  ``resolve_weapon_hit`` survives as the sticky grenade's
  stick/bounce/damage resolver.  (Ammo tracking for thrown weapons
  and guns is a future feature.)
* **The ndb semantics matter.**  Evennia's ndb handler returns
  ``None`` for unset attributes (never raises), so value checks —
  not ``hasattr`` — are what gate the flight lifecycle.  The ``Bag``
  stub below mimics this exactly.
* **Catch must cancel the flight timer.**  Step 1 fixed the
  ``room=`` → ``location=`` TypeError that aborted catch cleanup;
  the success-path test pins the full repaired flow.

Run via::

    evennia test --keepdb world.tests.test_throw_characterization
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.combat.constants import (
    MSG_THROW_GRAPPLED,
    MSG_THROW_INVALID_DIRECTION,
    MSG_THROW_NO_AIM_CROSS_ROOM,
    MSG_THROW_NO_HANDS,
    MSG_THROW_OBJECT_NOT_FOUND,
    MSG_THROW_OBJECT_NOT_WIELDED,
    MSG_PULL_ALREADY_PULLED,
    MSG_PULL_NO_PIN_REQUIRED,
    MSG_PULL_NOT_EXPLOSIVE,
    MSG_CATCH_NO_FREE_HANDS,
    MSG_CATCH_OBJECT_NOT_FOUND,
    NDB_COUNTDOWN_REMAINING,
    NDB_FLYING_OBJECTS,
    NDB_PROXIMITY_UNIVERSAL,
    THROW_FLIGHT_TIME,
)
from world.combat import throwing


# ===================================================================
# Evennia-faithful stubs
# ===================================================================


class Bag:
    """Attribute holder mimicking Evennia's db/ndb handlers.

    Unset attributes read as ``None`` (so ``hasattr`` is always
    True, exactly like production), and deleting an unset attribute
    is silent.
    """

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, name):
        return None

    def __delattr__(self, name):
        self.__dict__.pop(name, None)


def make_room(key="room"):
    room = MagicMock()
    room.key = key
    room.ndb = Bag()
    room.contents = []
    return room


def make_obj(key="rock", **db_fields):
    obj = MagicMock()
    obj.key = key
    obj.db = Bag(**db_fields)
    obj.ndb = Bag()
    return obj


def make_caller(room=None, hands=None):
    caller = MagicMock()
    caller.key = "Thrower"
    caller.db = Bag()
    caller.ndb = Bag()
    caller.location = room if room is not None else make_room()
    caller.hands = hands if hands is not None else {"left": None, "right": None}
    caller.search = MagicMock(return_value=[])
    return caller


def make_throw_cmd(caller, args=""):
    from commands.CmdThrow import CmdThrow

    cmd = CmdThrow()
    cmd.caller = caller
    cmd.args = args
    cmd.parse()
    return cmd


def caller_messages(caller):
    return [str(c.args[0]) for c in caller.msg.call_args_list if c.args]


# ===================================================================
# Parsing — the four syntaxes
# ===================================================================


class TestThrowParsing(TestCase):
    """``parse()`` routes the four documented syntaxes."""

    def parse(self, args):
        cmd = make_throw_cmd(make_caller(), args)
        return cmd

    def test_at_target(self):
        cmd = self.parse("knife at bob")
        self.assertEqual(cmd.throw_type, "at_target")
        self.assertEqual(cmd.object_name, "knife")
        self.assertEqual(cmd.target_name, "bob")

    def test_to_direction(self):
        cmd = self.parse("grenade to north")
        self.assertEqual(cmd.throw_type, "to_direction")
        self.assertEqual(cmd.object_name, "grenade")
        self.assertEqual(cmd.direction, "north")

    def test_to_here(self):
        cmd = self.parse("keys to here")
        self.assertEqual(cmd.throw_type, "to_here")
        self.assertEqual(cmd.object_name, "keys")

    def test_at_here_converts_to_to_here(self):
        """'throw knife at here' is treated as 'to here'."""
        cmd = self.parse("knife at here")
        self.assertEqual(cmd.throw_type, "to_here")
        self.assertIsNone(cmd.target_name)

    def test_bare_object_is_fallback(self):
        cmd = self.parse("rock")
        self.assertEqual(cmd.throw_type, "fallback")
        self.assertEqual(cmd.object_name, "rock")

    def test_object_containing_at_substring_not_split(self):
        """'combat knife' does not trigger the ' at ' split."""
        cmd = self.parse("combat knife")
        self.assertEqual(cmd.throw_type, "fallback")
        self.assertEqual(cmd.object_name, "combat knife")

    def test_empty_args_short_circuits_func(self):
        caller = make_caller()
        cmd = make_throw_cmd(caller, "")
        cmd.func()
        self.assertIn("Throw what?", caller_messages(caller)[0])


# ===================================================================
# Object validation — get_object_to_throw
# ===================================================================


class TestGetObjectToThrow(TestCase):
    def test_wielded_object_found_by_substring(self):
        rock = make_obj("heavy rock")
        caller = make_caller(hands={"right": rock, "left": None})
        cmd = make_throw_cmd(caller, "rock")
        self.assertIs(cmd.get_object_to_throw(), rock)

    def test_no_hands_at_all(self):
        caller = make_caller(hands={})
        cmd = make_throw_cmd(caller, "rock")
        self.assertIsNone(cmd.get_object_to_throw())
        self.assertIn(MSG_THROW_NO_HANDS, caller_messages(caller))

    def test_in_inventory_but_not_wielded(self):
        caller = make_caller(hands={"right": None})
        caller.search = MagicMock(return_value=[make_obj("rock")])
        cmd = make_throw_cmd(caller, "rock")
        self.assertIsNone(cmd.get_object_to_throw())
        self.assertIn(
            MSG_THROW_OBJECT_NOT_WIELDED.format(object="rock"),
            caller_messages(caller),
        )

    def test_object_nowhere(self):
        caller = make_caller(hands={"right": None})
        caller.search = MagicMock(return_value=[])
        cmd = make_throw_cmd(caller, "rock")
        self.assertIsNone(cmd.get_object_to_throw())
        self.assertIn(
            MSG_THROW_OBJECT_NOT_FOUND.format(object="rock"),
            caller_messages(caller),
        )

    def test_grappled_thrower_blocked(self):
        rock = make_obj("rock")
        caller = make_caller(hands={"right": rock})
        handler = MagicMock()
        handler.db.combatants = [
            {"char": caller, "grappled_by_dbref": 99},
        ]
        caller.ndb = Bag(combat_handler=handler)
        cmd = make_throw_cmd(caller, "rock")
        self.assertIsNone(cmd.get_object_to_throw())
        self.assertIn(MSG_THROW_GRAPPLED, caller_messages(caller))

    def test_expired_grenade_explodes_in_hand(self):
        """A held grenade whose countdown hit zero damages the
        thrower and is deleted instead of being thrown."""
        grenade = make_obj(
            "grenade", is_explosive=True, blast_damage=12, damage_type="blast"
        )
        grenade.ndb = Bag(countdown_remaining=0)
        caller = make_caller(hands={"right": grenade})
        cmd = make_throw_cmd(caller, "grenade")
        self.assertIsNone(cmd.get_object_to_throw())
        caller.take_damage.assert_called_once_with(
            12, location="chest", injury_type="blast"
        )
        grenade.delete.assert_called_once()


# ===================================================================
# Dedicated throwing weapons — redirect, never flight
# ===================================================================


class TestThrowingWeaponRedirect(TestCase):
    """``is_throwing_weapon`` objects redirect to ``attack`` and
    never enter the utility flight path."""

    def test_targeted_weapon_throw_invokes_attack(self):
        knife = make_obj("knife", is_throwing_weapon=True)
        caller = make_caller(hands={"right": knife})
        cmd = make_throw_cmd(caller, "knife at bob")
        cmd.func()
        caller.execute_cmd.assert_called_once_with("attack bob")

    def test_untargeted_weapon_throw_gets_guidance(self):
        knife = make_obj("knife", is_throwing_weapon=True)
        caller = make_caller(hands={"right": knife})
        cmd = make_throw_cmd(caller, "knife")
        cmd.func()
        caller.execute_cmd.assert_not_called()
        self.assertTrue(
            any("attack" in m for m in caller_messages(caller))
        )

    def test_weapon_never_takes_utility_flight(self):
        """Even a targeted weapon throw never launches a utility
        flight — the redirect fires first."""
        knife = make_obj("knife", is_throwing_weapon=True)
        caller = make_caller(hands={"right": knife})
        cmd = make_throw_cmd(caller, "knife at bob")
        with patch.object(cmd, "handle_utility_throw") as mock_fly:
            cmd.func()
        mock_fly.assert_not_called()


# ===================================================================
# Destination resolution
# ===================================================================


class TestDetermineDestination(TestCase):
    def test_to_here_lands_in_current_room_untargeted(self):
        caller = make_caller()
        cmd = make_throw_cmd(caller, "rock to here")
        cmd.obj_to_throw = make_obj("rock")
        destination, target = cmd.determine_destination()
        self.assertIs(destination, caller.location)
        self.assertIsNone(target)

    def test_at_target_uses_target_location(self):
        caller = make_caller()
        victim = MagicMock()
        cmd = make_throw_cmd(caller, "rock at bob")
        cmd.obj_to_throw = make_obj("rock")
        with patch.object(cmd, "find_target", return_value=victim):
            destination, target = cmd.determine_destination()
        self.assertIs(destination, victim.location)
        self.assertIs(target, victim)

    def test_to_direction_picks_random_room_occupant(self):
        caller = make_caller()
        adjacent = make_room("adjacent")
        bystander = MagicMock()
        cmd = make_throw_cmd(caller, "rock to north")
        cmd.obj_to_throw = make_obj("rock")
        with patch.object(cmd, "get_destination_room", return_value=adjacent), \
             patch("commands.CmdThrow.select_random_target_in_room",
                   return_value=bystander) as mock_pick:
            destination, target = cmd.determine_destination()
        self.assertIs(destination, adjacent)
        self.assertIs(target, bystander)
        mock_pick.assert_called_once_with(adjacent, exclude=caller)

    def test_sticky_grenade_prefers_magnetic_target(self):
        caller = make_caller()
        adjacent = make_room("adjacent")
        magnetic_victim = MagicMock()
        cmd = make_throw_cmd(caller, "spider to north")
        cmd.obj_to_throw = make_obj("spider grenade", is_sticky=True)
        with patch.object(cmd, "get_destination_room", return_value=adjacent), \
             patch("commands.CmdThrow.select_most_magnetic_target_in_room",
                   return_value=magnetic_victim):
            destination, target = cmd.determine_destination()
        self.assertIs(target, magnetic_victim)

    def test_sticky_falls_back_to_random_when_no_magnetic_target(self):
        caller = make_caller()
        adjacent = make_room("adjacent")
        random_victim = MagicMock()
        cmd = make_throw_cmd(caller, "spider to north")
        cmd.obj_to_throw = make_obj("spider grenade", is_sticky=True)
        with patch.object(cmd, "get_destination_room", return_value=adjacent), \
             patch("commands.CmdThrow.select_most_magnetic_target_in_room",
                   return_value=None), \
             patch("commands.CmdThrow.select_random_target_in_room",
                   return_value=random_victim):
            destination, target = cmd.determine_destination()
        self.assertIs(target, random_victim)

    def test_fallback_uses_aim_direction(self):
        caller = make_caller()
        caller.ndb = Bag(aiming_direction="north")
        aimed_room = make_room("aimed")
        cmd = make_throw_cmd(caller, "rock")
        cmd.obj_to_throw = make_obj("rock")
        with patch.object(cmd, "get_destination_room",
                          return_value=aimed_room) as mock_dest, \
             patch("commands.CmdThrow.select_random_target_in_room",
                   return_value=None):
            destination, target = cmd.determine_destination()
        mock_dest.assert_called_once_with("north")
        self.assertIs(destination, aimed_room)

    def test_fallback_without_aim_lands_in_current_room(self):
        caller = make_caller()
        cmd = make_throw_cmd(caller, "rock")
        cmd.obj_to_throw = make_obj("rock")
        with patch("commands.CmdThrow.select_random_target_in_room",
                   return_value=None):
            destination, target = cmd.determine_destination()
        self.assertIs(destination, caller.location)


class TestGetDestinationRoom(TestCase):
    def _cmd(self, exit_obj):
        caller = make_caller()
        caller.search = MagicMock(return_value=[exit_obj] if exit_obj else [])
        cmd = make_throw_cmd(caller, "rock to north")
        return cmd, caller

    def test_valid_exit_returns_destination(self):
        adjacent = make_room("adjacent")
        exit_obj = MagicMock()
        exit_obj.destination = adjacent
        cmd, caller = self._cmd(exit_obj)
        self.assertIs(cmd.get_destination_room("north"), adjacent)

    def test_loopback_exit_rejected(self):
        cmd, caller = self._cmd(None)
        exit_obj = MagicMock()
        exit_obj.destination = caller.location
        caller.search = MagicMock(return_value=[exit_obj])
        self.assertIsNone(cmd.get_destination_room("north"))
        self.assertTrue(
            any("loop back" in m for m in caller_messages(caller))
        )

    def test_invalid_direction_messaged(self):
        cmd, caller = self._cmd(None)
        self.assertIsNone(cmd.get_destination_room("zenith"))
        self.assertIn(
            MSG_THROW_INVALID_DIRECTION.format(direction="zenith"),
            caller_messages(caller),
        )

    def test_character_name_as_direction_suggests_at_syntax(self):
        """'throw rock to bob' explains the 'at' syntax instead."""

        class FakeCharacterClass:
            pass

        fake_char = FakeCharacterClass()
        fake_char.destination = None
        cmd, caller = self._cmd(fake_char)
        with patch("typeclasses.characters.Character", FakeCharacterClass):
            result = cmd.get_destination_room("bob")
        self.assertIsNone(result)
        self.assertTrue(
            any("at" in m and "bob" in m for m in caller_messages(caller))
        )


class TestFindTarget(TestCase):
    """Cross-room targeting requires aim (call-site wiring for the
    identity helper itself lives in test_inventory_command_identity)."""

    def test_no_same_room_target_and_no_aim_requires_aim_message(self):
        caller = make_caller()
        cmd = make_throw_cmd(caller, "rock at bob")
        with patch("commands.CmdThrow.resolve_character_target",
                   return_value=None):
            self.assertIsNone(cmd.find_target())
        self.assertIn(MSG_THROW_NO_AIM_CROSS_ROOM, caller_messages(caller))


# ===================================================================
# Flight — start, complete, cleanup (world.combat.throwing)
# ===================================================================


class TestFlight(TestCase):
    def _start(self, caller, obj, destination, target=None):
        with patch("world.combat.throwing.utils.delay") as mock_delay:
            mock_delay.return_value = MagicMock()
            throwing.start_flight(caller, obj, destination, target)
        return mock_delay

    def test_start_flight_stages_state_and_timer(self):
        caller = make_caller()
        obj = make_obj("rock")
        destination = make_room("dest")
        mock_delay = self._start(caller, obj, destination)

        self.assertIs(obj.ndb.flight_destination, destination)
        self.assertIsNone(obj.ndb.flight_target)
        self.assertIs(obj.ndb.flight_origin, caller.location)
        self.assertIs(obj.ndb.flight_thrower, caller)
        self.assertIn(obj, getattr(caller.location.ndb, NDB_FLYING_OBJECTS))
        mock_delay.assert_called_once_with(
            THROW_FLIGHT_TIME, throwing.complete_flight, obj
        )

    def test_complete_flight_moves_object_and_cleans_up(self):
        caller = make_caller()
        origin = caller.location
        obj = make_obj("rock")
        destination = make_room("dest")
        self._start(caller, obj, destination)

        with patch("world.combat.throwing.handle_landing") as mock_landing, \
             patch("world.combat.throwing.msg_room_identity"), \
             patch("commands.combat.movement.apply_gravity_to_items"):
            throwing.complete_flight(obj)

        obj.move_to.assert_called_once_with(destination, quiet=True)
        mock_landing.assert_called_once()
        # Flight state fully cleaned (values gone, reads return None)
        self.assertIsNone(obj.ndb.flight_destination)
        self.assertIsNone(obj.ndb.flight_thrower)
        self.assertNotIn(obj, getattr(origin.ndb, NDB_FLYING_OBJECTS))

    def test_complete_flight_skips_object_with_cleared_state(self):
        """After catch cleanup, flight_destination reads None and the
        late-firing timer must not move the object."""
        obj = make_obj("rock")
        throwing.complete_flight(obj)
        obj.move_to.assert_not_called()

    def test_complete_flight_explosive_checks_deflection_first(self):
        caller = make_caller()
        grenade = make_obj("grenade", is_explosive=True)
        destination = make_room("dest")
        self._start(caller, grenade, destination)

        with patch("world.combat.throwing.check_grenade_deflection",
                   return_value=True) as mock_deflect, \
             patch("world.combat.throwing.handle_landing") as mock_landing, \
             patch("world.combat.throwing.msg_room_identity"):
            throwing.complete_flight(grenade)

        mock_deflect.assert_called_once()
        mock_landing.assert_not_called()

    def test_deflected_flight_state_survives_completion(self):
        """A successful deflection re-stages flight state for the new
        trajectory; complete_flight's cleanup must not wipe it."""
        caller = make_caller()
        grenade = make_obj("grenade", is_explosive=True)
        destination = make_room("dest")
        new_destination = make_room("ricochet")

        def fake_deflect(obj, dest, thrower):
            obj.ndb.flight_destination = new_destination
            obj.ndb.flight_timer = MagicMock()
            return True

        self._start(caller, grenade, destination)
        with patch("world.combat.throwing.check_grenade_deflection",
                   side_effect=fake_deflect), \
             patch("world.combat.throwing.msg_room_identity"):
            throwing.complete_flight(grenade)

        self.assertIs(grenade.ndb.flight_destination, new_destination)

    def test_landing_failure_still_cleans_flight_state(self):
        """A bug in landing resolution surfaces (raises) but can
        never strand the object in the flying state."""
        caller = make_caller()
        obj = make_obj("rock")
        destination = make_room("dest")
        self._start(caller, obj, destination)

        with patch("world.combat.throwing.handle_landing",
                   side_effect=RuntimeError("boom")), \
             patch("world.combat.throwing.msg_room_identity"):
            with self.assertRaises(RuntimeError):
                throwing.complete_flight(obj)

        self.assertIsNone(obj.ndb.flight_destination)
        self.assertIsNone(obj.ndb.flight_timer)


# ===================================================================
# Landing — proximity and interactions
# ===================================================================


class TestLanding(TestCase):
    def test_utility_bounce_messages_target(self):
        caller = make_caller()
        target = MagicMock()
        target.ndb = Bag()
        obj = make_obj("rock")
        with patch("world.combat.throwing.msg_room_identity") as mock_room:
            throwing.handle_landing(obj, make_room("dest"), target, caller)
        target.msg.assert_called()
        self.assertTrue(mock_room.called)

    def test_sticky_landing_routes_to_hit_resolution(self):
        """The stick/bounce/damage resolver is reached via the sticky
        landing route — the only route since the dead weapon-flight
        path was removed."""
        caller = make_caller()
        target = MagicMock()
        target.ndb = Bag()
        spider = make_obj("spider grenade", is_sticky=True, is_explosive=True)
        with patch("world.combat.throwing.resolve_weapon_hit") as mock_hit, \
             patch("world.combat.throwing.msg_room_identity"):
            throwing.handle_landing(spider, make_room("dest"), target, caller)
        mock_hit.assert_called_once_with(spider, target, caller)

    def test_landing_proximity_adds_target_to_object(self):
        caller = make_caller()
        target = MagicMock()
        target.ndb = Bag()
        obj = make_obj("rock")
        throwing.assign_landing_proximity(obj, target, caller)
        self.assertIn(target, getattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL))

    def test_landing_proximity_inherits_targets_neighbors_not_thrower(self):
        """Object inherits the target's proximity web, but the
        thrower is filtered out of their own throw's blast circle."""
        caller = make_caller()
        bystander = MagicMock()
        target = MagicMock()
        target.ndb = Bag(in_proximity_with={bystander, caller})
        obj = make_obj("grenade", is_explosive=True)
        throwing.assign_landing_proximity(obj, target, caller)
        proximity = getattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL)
        self.assertIn(bystander, proximity)
        self.assertNotIn(caller, proximity)

    def test_grenade_landing_inherits_target_object_proximity(self):
        caller = make_caller()
        bystander = MagicMock()
        target = MagicMock()
        target.ndb = Bag(**{NDB_PROXIMITY_UNIVERSAL: [bystander, caller]})
        grenade = make_obj("grenade", is_explosive=True)
        throwing.handle_grenade_landing(grenade, target, caller)
        proximity = getattr(grenade.ndb, NDB_PROXIMITY_UNIVERSAL)
        self.assertIn(bystander, proximity)
        self.assertNotIn(caller, proximity)


# ===================================================================
# Hit resolution (reachable via the sticky landing route)
# ===================================================================


class TestResolveWeaponHit(TestCase):
    def _target(self):
        target = MagicMock()
        target.key = "Victim"
        target.ndb = Bag()
        return target

    @patch("world.combat.throwing.capitalize_first", side_effect=lambda s: s)
    @patch("world.combat.throwing.get_display_name_safe",
           side_effect=lambda t, o: getattr(t, "key", "x"))
    @patch("world.combat.throwing.msg_room_identity")
    def test_hit_applies_damage_and_proximity(self, mock_room, *_):
        caller = make_caller()
        target = self._target()
        weapon = make_obj("brick", damage=3, damage_type="blunt")
        with patch("world.combat.throwing.random") as mock_random:
            mock_random.random.return_value = 0.1   # under 0.7 → hit
            mock_random.randint.return_value = 4
            throwing.resolve_weapon_hit(weapon, target, caller)
        target.take_damage.assert_called_once_with(
            7, location="chest", injury_type="blunt"
        )
        self.assertIn(caller, getattr(target.ndb, NDB_PROXIMITY_UNIVERSAL))

    @patch("world.combat.throwing.capitalize_first", side_effect=lambda s: s)
    @patch("world.combat.throwing.get_display_name_safe",
           side_effect=lambda t, o: getattr(t, "key", "x"))
    @patch("world.combat.throwing.msg_room_identity")
    def test_miss_deals_no_damage(self, mock_room, *_):
        caller = make_caller()
        target = self._target()
        weapon = make_obj("brick", damage=3)
        with patch("world.combat.throwing.random") as mock_random:
            mock_random.random.return_value = 0.9   # over 0.7 → miss
            throwing.resolve_weapon_hit(weapon, target, caller)
        target.take_damage.assert_not_called()
        target.msg.assert_called()


# ===================================================================
# Grenade deflection
# ===================================================================


class TestGrenadeDeflection(TestCase):
    def _setup(self, *, impact=False, target_present=True,
               wielding=None, grappled=False):
        caller = make_caller()
        destination = make_room("dest")
        grenade = make_obj("grenade", is_explosive=True,
                           impact_detonation=impact)
        target = MagicMock()
        target.key = "Defender"
        target.location = destination if target_present else make_room("else")
        target.hands = wielding if wielding is not None else {}
        if grappled:
            handler = MagicMock()
            handler.db.combatants = [
                {"char": target, "grappled_by_dbref": 7},
            ]
            target.ndb = Bag(combat_handler=handler)
        else:
            target.ndb = Bag()
        grenade.ndb = Bag(flight_target=target)
        return grenade, destination, caller, target

    def test_impact_grenades_cannot_be_deflected(self):
        grenade, dest, caller, _ = self._setup(impact=True)
        self.assertFalse(
            throwing.check_grenade_deflection(grenade, dest, caller)
        )

    def test_untargeted_grenade_not_deflectable(self):
        grenade, dest, caller, _ = self._setup()
        grenade.ndb = Bag()  # no flight_target
        self.assertFalse(
            throwing.check_grenade_deflection(grenade, dest, caller)
        )

    def test_target_elsewhere_cannot_deflect(self):
        grenade, dest, caller, _ = self._setup(target_present=False)
        self.assertFalse(
            throwing.check_grenade_deflection(grenade, dest, caller)
        )

    def test_grappled_target_cannot_deflect(self):
        melee = make_obj("pipe")
        grenade, dest, caller, _ = self._setup(
            wielding={"right": melee}, grappled=True
        )
        self.assertFalse(
            throwing.check_grenade_deflection(grenade, dest, caller)
        )

    def test_ranged_weapon_cannot_deflect(self):
        gun = make_obj("pistol", is_ranged=True)
        grenade, dest, caller, _ = self._setup(wielding={"right": gun})
        self.assertFalse(
            throwing.check_grenade_deflection(grenade, dest, caller)
        )

    @patch("world.combat.utils.roll_stat", return_value=12)
    def test_motorics_roll_beats_base_threshold(self, mock_roll):
        """Roll 12 vs base threshold 10 → deflection attempt fires."""
        melee = make_obj("pipe")
        grenade, dest, caller, target = self._setup(
            wielding={"right": melee}
        )
        with patch("world.combat.throwing.perform_grenade_deflection",
                   return_value=True) as mock_perform:
            result = throwing.check_grenade_deflection(grenade, dest, caller)
        self.assertTrue(result)
        mock_perform.assert_called_once()

    @patch("world.combat.utils.roll_stat", return_value=12)
    @patch("world.combat.throwing.msg_room_identity")
    def test_deflection_bonus_raises_threshold(self, mock_room, mock_roll):
        """deflection_bonus 0.30 → threshold 16; roll 12 now fails."""
        melee = make_obj("pipe", deflection_bonus=0.30)
        grenade, dest, caller, target = self._setup(
            wielding={"right": melee}
        )
        with patch("world.combat.throwing.perform_grenade_deflection") as mock_perform:
            result = throwing.check_grenade_deflection(grenade, dest, caller)
        self.assertFalse(result)
        mock_perform.assert_not_called()

    def test_deflected_grenade_rethrown_back_at_thrower(self):
        """60%-branch deflection re-targets origin; deflector becomes
        the new thrower and the timer restarts shortened."""
        grenade, dest, caller, target = self._setup()
        origin = make_room("origin")
        caller.location = origin
        grenade.ndb = Bag(flight_target=target, flight_origin=origin)
        deflector = MagicMock()
        deflector.ndb = Bag()
        with patch("world.combat.throwing.random") as mock_random, \
             patch("world.combat.throwing.utils.delay") as mock_delay:
            mock_random.random.return_value = 0.1  # under 0.6 → back
            result = throwing.determine_deflection_target(
                grenade, deflector, caller, dest
            )
        self.assertTrue(result)
        self.assertIs(grenade.ndb.flight_destination, origin)
        self.assertIs(grenade.ndb.flight_thrower, deflector)
        mock_delay.assert_called_once()
        self.assertEqual(
            mock_delay.call_args.args[0], max(1, THROW_FLIGHT_TIME - 1)
        )

    def test_deflection_with_no_exits_fails(self):
        grenade, dest, caller, target = self._setup()
        dest.contents = []
        deflector = MagicMock()
        with patch("world.combat.throwing.random") as mock_random:
            mock_random.random.return_value = 0.9  # over 0.6 → random exit
            result = throwing.determine_deflection_target(
                grenade, deflector, caller, dest
            )
        self.assertFalse(result)


# ===================================================================
# CmdPull — pin pulling
# ===================================================================


class TestCmdPull(TestCase):
    def _cmd(self, caller, args):
        from commands.CmdThrow import CmdPull

        cmd = CmdPull()
        cmd.caller = caller
        cmd.args = args
        cmd.parse()
        return cmd

    def test_bad_syntax_messaged(self):
        caller = make_caller()
        cmd = self._cmd(caller, "the lever")
        cmd.func()
        self.assertTrue(caller_messages(caller))

    def test_not_explosive_rejected(self):
        rock = make_obj("rock")
        caller = make_caller(hands={"right": rock})
        cmd = self._cmd(caller, "pin on rock")
        cmd.func()
        self.assertIn(
            MSG_PULL_NOT_EXPLOSIVE.format(object="rock"),
            caller_messages(caller),
        )

    def test_pinless_grenade_rejected(self):
        grenade = make_obj("grenade", is_explosive=True, requires_pin=False)
        caller = make_caller(hands={"right": grenade})
        cmd = self._cmd(caller, "pin on grenade")
        cmd.func()
        self.assertIn(
            MSG_PULL_NO_PIN_REQUIRED.format(object="grenade"),
            caller_messages(caller),
        )

    def test_already_pulled_rejected(self):
        grenade = make_obj("grenade", is_explosive=True, pin_pulled=True)
        caller = make_caller(hands={"right": grenade})
        cmd = self._cmd(caller, "pin on grenade")
        cmd.func()
        self.assertIn(
            MSG_PULL_ALREADY_PULLED.format(object="grenade"),
            caller_messages(caller),
        )

    @patch("commands.explosion_utils.start_grenade_ticker")
    @patch("commands.CmdThrow.msg_room_identity")
    def test_pull_sets_flag_countdown_and_ticker(self, mock_room, mock_ticker):
        grenade = make_obj("grenade", is_explosive=True, fuse_time=8)
        caller = make_caller(hands={"right": grenade})
        cmd = self._cmd(caller, "pin on grenade")
        cmd.func()
        self.assertTrue(grenade.db.pin_pulled)
        self.assertEqual(
            getattr(grenade.ndb, NDB_COUNTDOWN_REMAINING), 8
        )
        mock_ticker.assert_called_once_with(grenade)


# ===================================================================
# CmdCatch — hot potato
# ===================================================================


class TestCmdCatch(TestCase):
    def _cmd(self, caller, args="grenade"):
        from commands.CmdThrow import CmdCatch

        cmd = CmdCatch()
        cmd.caller = caller
        cmd.args = args
        return cmd

    def test_no_free_hands(self):
        full = make_obj("brick")
        caller = make_caller(hands={"left": full, "right": full})
        cmd = self._cmd(caller)
        cmd.func()
        self.assertIn(MSG_CATCH_NO_FREE_HANDS, caller_messages(caller))

    def test_object_not_flying(self):
        caller = make_caller()
        cmd = self._cmd(caller)
        cmd.func()
        self.assertIn(
            MSG_CATCH_OBJECT_NOT_FOUND.format(object="grenade"),
            caller_messages(caller),
        )

    @patch("commands.CmdThrow.msg_room_identity")
    def test_failed_catch_object_flies_on(self, mock_room):
        grenade = make_obj("grenade")
        caller = make_caller()
        setattr(caller.location.ndb, NDB_FLYING_OBJECTS, [grenade])
        cmd = self._cmd(caller)
        with patch("commands.CmdThrow.random") as mock_random:
            mock_random.random.return_value = 0.9  # over 0.6 → fail
            cmd.func()
        grenade.move_to.assert_not_called()
        self.assertIn(
            grenade, getattr(caller.location.ndb, NDB_FLYING_OBJECTS)
        )

    @patch("commands.CmdThrow.msg_room_identity")
    def test_successful_catch_wields_cleans_and_cancels(self, mock_room):
        """Successful catch: object lands in the free hand, leaves the
        flying list, flight state is cleared, and the pending flight
        timer is cancelled (no ghost arrival).  This is the path the
        ``room=`` → ``location=`` fix repaired."""
        grenade = make_obj("grenade")
        timer = MagicMock()
        destination = make_room("dest")
        grenade.ndb = Bag(
            flight_destination=destination,
            flight_timer=timer,
        )
        caller = make_caller(hands={"right": None})
        setattr(caller.location.ndb, NDB_FLYING_OBJECTS, [grenade])
        cmd = self._cmd(caller)
        with patch("commands.CmdThrow.random") as mock_random:
            mock_random.random.return_value = 0.1  # under 0.6 → catch
            cmd.func()

        grenade.move_to.assert_called_once_with(caller)
        self.assertIs(caller.hands["right"], grenade)
        self.assertNotIn(
            grenade, getattr(caller.location.ndb, NDB_FLYING_OBJECTS)
        )
        timer.cancel.assert_called_once()
        self.assertIsNone(grenade.ndb.flight_destination)
        # Room announce went through the identity broadcast.
        mock_room.assert_called_once()
        self.assertIn(
            "location", mock_room.call_args.kwargs,
            "catch announce must pass location= (the room= regression)",
        )
