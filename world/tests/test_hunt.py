"""The NPC hunt (world/director/hunt.py) — STEALTH_AND_DETECTION_SPEC §5.

MagicMock harness: travel, dispatch, and the awareness reads are patched at
their source modules; what's under test is the state machine — commit,
sweep-with-the-real-search-command, reacquire/engage/propagate, give up.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import world.director.hunt as hunt
from world.director.hunt import (
    SEARCH_BUDGET, is_hunting, propagate_alert, tick_hunt,
)
from world.stealth import ALERT, SEARCHING, SUSPICIOUS


def _npc(room=None):
    npc = MagicMock()
    npc.ndb.hunt = None
    npc.db.role = "security"
    npc.location = room if room is not None else MagicMock()
    return npc


def _rec(key="uid-prey", level=SEARCHING, last_room=77):
    return [(key, level, last_room, 100.0)]


def _all_wanted():
    """Most machine tests assume the target has cause on file."""
    return patch("world.director.intel.is_wanted",
                 return_value={"count": 1})


class TestHuntMachine(TestCase):
    def test_no_records_no_hunt(self):
        npc = _npc()
        with _all_wanted(), patch("world.stealth.hunt_records", return_value=[]), \
                patch("world.director.travel.is_travelling",
                      return_value=False):
            self.assertFalse(tick_hunt(npc))
        self.assertFalse(is_hunting(npc))

    def test_suspicious_commits_with_orient_beat(self):
        npc = _npc()
        with _all_wanted(), patch("world.stealth.hunt_records",
                   return_value=_rec(level=SUSPICIOUS)), \
                patch("world.director.travel.is_travelling",
                      return_value=False), \
                patch.object(hunt, "_present_target", return_value=None):
            self.assertTrue(tick_hunt(npc))
        npc.execute_cmd.assert_called_once()
        self.assertIn("snaps alert", npc.execute_cmd.call_args.args[0])
        self.assertTrue(is_hunting(npc))
        self.assertEqual(npc.ndb.hunt["key"], "uid-prey")
        self.assertEqual(npc.ndb.hunt["budget"], SEARCH_BUDGET)

    def test_committed_hunter_travels_to_last_known(self):
        npc = _npc()
        last_room = MagicMock()
        last_room.id = 77
        npc.ndb.hunt = {"key": "uid-prey", "budget": SEARCH_BUDGET,
                        "swept": [], "last_room": 77}
        with _all_wanted(), patch("world.stealth.hunt_records", return_value=_rec()), \
                patch("world.director.travel.is_travelling",
                      return_value=False), \
                patch("world.director.travel.travel_to") as travel, \
                patch.object(hunt, "_room_by_id", return_value=last_room), \
                patch.object(hunt, "_present_target", return_value=None):
            self.assertTrue(tick_hunt(npc))
        travel.assert_called_once_with(npc, last_room)

    def test_arrival_sweeps_with_the_real_search_command(self):
        last_room = MagicMock()
        last_room.id = 77
        npc = _npc(room=last_room)
        npc.ndb.hunt = {"key": "uid-prey", "budget": 2,
                        "swept": [], "last_room": 77}
        with _all_wanted(), \
                patch("world.stealth.hunt_records", return_value=_rec()), \
                patch("world.director.travel.is_travelling",
                      return_value=False), \
                patch.object(hunt, "_room_by_id", return_value=last_room), \
                patch.object(hunt, "_present_target", return_value=None):
            self.assertTrue(tick_hunt(npc))
        npc.execute_cmd.assert_called_once_with("search")
        self.assertEqual(npc.ndb.hunt["budget"], 1)
        self.assertIn(77, npc.ndb.hunt["swept"])

    def test_reacquire_engages_and_propagates(self):
        npc = _npc()
        npc.location.id = 55
        prey = MagicMock()
        with patch("world.stealth.hunt_records",
                   return_value=_rec(level=ALERT)), \
                patch("world.director.travel.is_travelling",
                      return_value=False), \
                patch.object(hunt, "_present_target", return_value=prey), \
                patch("world.stealth.set_awareness"), \
                patch("world.stealth._target_key",
                      return_value="uid-prey"), \
                patch("world.director.intel.is_wanted",
                      return_value={"count": 2}), \
                patch("world.director.dispatch.raise_event") as raised, \
                patch.object(hunt, "propagate_alert") as propagate:
            self.assertTrue(tick_hunt(npc))
        say = [c.args[0] for c in npc.execute_cmd.call_args_list
               if c.args[0].startswith("say ")]
        self.assertTrue(say and "Halt, Colonist" in say[0])
        raised.assert_called_once()
        propagate.assert_called_once_with(npc, "uid-prey", 55)
        self.assertFalse(is_hunting(npc))     # dispatch owns it now

    def test_budget_exhaustion_gives_up(self):
        npc = _npc()
        npc.ndb.hunt = {"key": "uid-prey", "budget": 0,
                        "swept": [77], "last_room": 77}
        with _all_wanted(), \
                patch("world.stealth.hunt_records", return_value=_rec()), \
                patch("world.director.travel.is_travelling",
                      return_value=False), \
                patch.object(hunt, "_room_by_id", return_value=None), \
                patch.object(hunt, "_present_target", return_value=None), \
                patch("world.stealth.seed_awareness") as seed:
            self.assertTrue(tick_hunt(npc))
        self.assertFalse(is_hunting(npc))
        self.assertIn("abandons its sweep",
                      npc.execute_cmd.call_args.args[0])
        seed.assert_called_once()             # record dropped to Unaware

    def test_decayed_record_ends_hunt(self):
        npc = _npc()
        npc.ndb.hunt = {"key": "uid-prey", "budget": 2,
                        "swept": [], "last_room": 77}
        with patch("world.stealth.hunt_records", return_value=[]), \
                patch("world.director.travel.is_travelling",
                      return_value=False), \
                patch("world.stealth.seed_awareness"):
            self.assertFalse(tick_hunt(npc))
        self.assertFalse(is_hunting(npc))


class TestPropagation(TestCase):
    def test_other_security_seeded_to_searching(self):
        npc = _npc()
        ally = MagicMock()
        ally.db.role = "security"
        bystander = MagicMock()
        bystander.db.role = "hawker"
        qs = MagicMock()
        qs.distinct.return_value = [npc, ally, bystander]
        with patch("evennia.objects.models.ObjectDB") as odb, \
                patch("world.stealth.seed_awareness") as seed:
            odb.objects.filter.return_value = qs
            n = propagate_alert(npc, "uid-prey", 55)
        self.assertEqual(n, 1)
        seed.assert_called_once_with(ally, "uid-prey", SEARCHING, 55)


class TestInnocentLurker(TestCase):
    """A hunt requires CAUSE (user-decided): an unwanted hidden presence
    is silently ignored — no orient, no sweep, no roust. Hiding is not
    a crime; the detected innocent just reads as a nervous face."""

    def test_clean_colonist_is_silently_ignored(self):
        npc = _npc()
        prey = MagicMock()
        with patch("world.stealth.hunt_records",
                   return_value=_rec(level=ALERT)), \
                patch("world.director.travel.is_travelling",
                      return_value=False), \
                patch.object(hunt, "_present_target", return_value=prey), \
                patch("world.director.intel.is_wanted",
                      return_value=None), \
                patch("world.director.dispatch.raise_event") as raised:
            self.assertFalse(tick_hunt(npc))     # patrol proceeds normally
        npc.execute_cmd.assert_not_called()      # no emote, no say, nothing
        raised.assert_not_called()
        self.assertFalse(is_hunting(npc))

    def test_pardon_mid_hunt_stands_down_silently(self):
        npc = _npc()
        prey = MagicMock()
        with patch.object(hunt, "propagate_alert"), \
                patch("world.stealth.set_awareness") as aware, \
                patch("world.stealth._target_key",
                      return_value="uid-prey"), \
                patch("world.director.intel.is_wanted",
                      return_value=None):
            hunt._engage(npc, prey)
        npc.execute_cmd.assert_not_called()
        self.assertTrue(aware.call_args.kwargs.get("roll_stamp"))


class TestSituationalCause(TestCase):
    """Reasonable suspicion (user-decided): near a fresh UNRESOLVED
    incident, a hidden presence is cause even without a wanted record."""

    def test_unwanted_hider_hunted_near_hot_incident(self):
        npc = _npc()
        with patch("world.stealth.hunt_records",
                   return_value=_rec(level=SUSPICIOUS)), \
                patch("world.director.travel.is_travelling",
                      return_value=False), \
                patch.object(hunt, "_present_target", return_value=None), \
                patch("world.director.intel.is_wanted",
                      return_value=None), \
                patch("world.director.dispatch.incident_context",
                      return_value=True):
            self.assertTrue(tick_hunt(npc))
        self.assertTrue(is_hunting(npc))

    def test_unwanted_hider_ignored_when_scene_is_cold(self):
        npc = _npc()
        with patch("world.stealth.hunt_records",
                   return_value=_rec(level=SUSPICIOUS)), \
                patch("world.director.travel.is_travelling",
                      return_value=False), \
                patch("world.director.intel.is_wanted",
                      return_value=None), \
                patch("world.director.dispatch.incident_context",
                      return_value=False), \
                patch.object(hunt, "_room_by_id", return_value=None):
            self.assertFalse(tick_hunt(npc))
        npc.execute_cmd.assert_not_called()

    def test_engage_allows_incident_cause(self):
        npc = _npc()
        npc.location.id = 55
        prey = MagicMock()
        with patch.object(hunt, "propagate_alert") as propagate, \
                patch("world.stealth.set_awareness"), \
                patch("world.stealth._target_key",
                      return_value="uid-prey"), \
                patch("world.director.intel.is_wanted",
                      return_value=None), \
                patch("world.director.dispatch.incident_context",
                      return_value=True), \
                patch("world.director.dispatch.raise_event"):
            hunt._engage(npc, prey)
        say = [c.args[0] for c in npc.execute_cmd.call_args_list
               if c.args[0].startswith("say ")]
        self.assertTrue(say and "Halt, Colonist" in say[0])
        propagate.assert_called_once()


class TestIncidentLog(TestCase):
    """The dispatch-side incident store: sourceless events run a scene hot
    in the room and its adjacents; known-source events don't; heat fades."""

    def _clear(self):
        from evennia.server.models import ServerConfig
        ServerConfig.objects.conf("director_incidents", delete=True)

    def test_sourceless_event_heats_room_and_adjacents(self):
        from world.director.dispatch import (
            WorldEvent, incident_context, raise_event,
        )
        self._clear()
        scene = MagicMock()
        scene.id = 900
        scene.exits = []
        with patch("world.director.dispatch.dispatch", return_value=[]):
            raise_event(WorldEvent("disturbance", scene, source=None))
        self.assertTrue(incident_context(scene))
        adjacent = MagicMock()
        adjacent.id = 901
        exit_obj = MagicMock()
        exit_obj.destination = scene
        adjacent.exits = [exit_obj]
        self.assertTrue(incident_context(adjacent))
        far = MagicMock()
        far.id = 999
        far.exits = []
        self.assertFalse(incident_context(far))
        self._clear()

    def test_known_source_event_is_not_situational_cause(self):
        from world.director.dispatch import (
            WorldEvent, incident_context, raise_event,
        )
        self._clear()
        scene = MagicMock()
        scene.id = 902
        scene.exits = []
        with patch("world.director.dispatch.dispatch", return_value=[]):
            raise_event(WorldEvent("disturbance", scene,
                                   source=MagicMock()))
        self.assertFalse(incident_context(scene))
        self._clear()

    def test_heat_fades_with_the_window(self):
        from world.director.dispatch import (
            WorldEvent, incident_context, raise_event,
        )
        self._clear()
        scene = MagicMock()
        scene.id = 903
        scene.exits = []
        with patch("world.director.dispatch.dispatch", return_value=[]):
            raise_event(WorldEvent("disturbance", scene, source=None))
        self.assertFalse(incident_context(scene, window=0.0))
        self._clear()

    def test_explosions_raise_sourceless_incidents(self):
        from commands.explosion_utils import (
            notify_adjacent_rooms_of_explosion,
        )
        room = MagicMock()
        room.exits = []
        with patch("world.director.dispatch.raise_event") as raised:
            notify_adjacent_rooms_of_explosion(room)
        event = raised.call_args.args[0]
        self.assertEqual(event.type, "disturbance")
        self.assertIsNone(event.source)
        self.assertIs(event.location, room)
