"""Two of the five findings in #2446 that survived checking.

### `to <radio>, ...` obeys the lock `xmit` obeys (§2)

Both verbs reach `world.radio.transmit`, which enforces only *powered*
and *tuned* — the real guards live in the commands, and they had
drifted. `CmdTransmit`, `CmdTune` and `CmdToggle` all call
`refuse_if_channeling`; `CmdTo` did not. So mid-`sabotage` (90s) or
mid-`repair` (180s) you could not key your handset with `xmit`, but
`to walkie, all clear` transmitted fine — the second door onto the same
act, without the guard.

The check goes in **before** `break_stealth`, not after. #2530
established that a refused command must not blow your cover for an
action that never happened, and a channeling refusal is exactly that.
It is scoped to the radio branch: keying a handset is a hands and
attention act, ordinary directed speech is not.

### The crowd weather table was keyed against a vocabulary that
doesn't exist (§5)

`CrowdSystem.weather_modifiers` defined `heavy_rain`, which is not a
weather type and could never be selected, and omitted `light_rain` and
`foggy_rain`, which both are. Those two real weathers contributed
nothing — and not just to prose: `world/director/witness.py` and
`world/stealth.py` read the same level, so rain that thins a street
thinned neither the witnesses nor the cover.

The set-equality test is the actual fix. Two hand-maintained
vocabularies in different packages will drift again; pinning them to
each other is what stops it.

**Three of the five findings in that issue did not survive checking.**
§1 (sense-layer spacing) was fixed by #2989 on 2026-09-07 — the current
`format_appearance` compares against `get_display_desc`, which is
exactly the repair proposed. §3 ("the 3th floor") already imports
`world.grammar.ordinal`. §4 (weather does not persist a reload) is
real but is a design question, not a defect, and is raised for a
ruling rather than fixed here.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.crowd.crowd_system import CrowdSystem
from world.weather.weather_messages import WEATHER_INTENSITY


class TestTheTwoVocabulariesAgree(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.mods = CrowdSystem().weather_modifiers

    def test_every_real_weather_has_a_crowd_effect(self):
        missing = sorted(set(WEATHER_INTENSITY) - set(self.mods))
        self.assertEqual(missing, [], f"weathers with no crowd effect: {missing}")

    def test_no_crowd_key_is_a_weather_that_does_not_exist(self):
        dead = sorted(set(self.mods) - set(WEATHER_INTENSITY))
        self.assertEqual(dead, [], f"dead crowd keys: {dead}")

    def test_the_two_named_in_the_issue_are_present(self):
        for weather in ("light_rain", "foggy_rain"):
            self.assertIn(weather, self.mods)

    def test_the_dead_key_is_gone(self):
        self.assertNotIn("heavy_rain", self.mods)

    def test_rain_still_thins_a_street_monotonically(self):
        """Shape, not tuning — no system here has had its balance pass."""
        self.assertGreater(self.mods["light_rain"], self.mods["rain"])
        self.assertGreater(self.mods["rain"], self.mods["torrential_rain"])

    def test_the_new_weathers_actually_move_the_level(self):
        room = create_object("typeclasses.rooms.Room", key="a street")
        room.db.type = "street"
        room.db.crowd_base_level = 3
        room.db.outside = True
        crowd = CrowdSystem()

        # `world/weather/__init__.py` binds the NAME `weather_system` to
        # an INSTANCE, shadowing the submodule of the same name — so
        # `patch("world.weather.weather_system.get_current_weather")`
        # resolves the module, which has no such attribute. Patch the
        # instance the crowd system actually imports.
        from world.weather import weather_system as live_weather

        def level_under(weather):
            with patch.object(live_weather, "get_current_weather",
                              return_value=weather):
                return crowd.calculate_crowd_level(room)

        self.assertLess(level_under("torrential_rain"), level_under("clear"))
        self.assertLessEqual(level_under("foggy_rain"), level_under("light_rain"))


class TestChannelingBlocksBothDoors(EvenniaCommandTest):
    """`xmit` and `to <radio>, ...` are two doors onto one act."""

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.radio = create_object("typeclasses.objects.Object",
                                   key="a walkie", location=self.char1)

    def _to(self, args):
        from commands.CmdCommunication import CmdTo
        return self.call(CmdTo(), args)

    def _channeling(self):
        """Patch the predicate itself — the guard is imported inside the
        function, so `world.channeled` is the binding that matters."""
        return patch("world.channeled.refuse_if_channeling",
                     return_value=True)

    def test_a_channeling_character_cannot_key_the_handset(self):
        with self._channeling(), \
                patch("world.radio.is_radio", return_value=True), \
                patch("world.radio.transmit") as sent:
            self._to("walkie all clear")
        sent.assert_not_called()

    def test_and_it_does_not_blow_their_cover_first(self):
        """#2530: a refused command must not reveal you for an action
        that never happened."""
        with self._channeling(), \
                patch("world.radio.is_radio", return_value=True), \
                patch("world.stealth.break_stealth") as revealed:
            self._to("walkie all clear")
        revealed.assert_not_called()

    def test_an_unencumbered_character_still_transmits(self):
        with patch("world.channeled.refuse_if_channeling",
                   return_value=False), \
                patch("world.radio.is_radio", return_value=True), \
                patch("world.radio.transmit") as sent:
            self._to("walkie all clear")
        sent.assert_called_once()

    def test_plain_directed_speech_is_not_a_hands_verb(self):
        """Channeling must not silence ordinary talking — the guard is
        scoped to the radio branch."""
        self.char2.location = self.room1
        with self._channeling(), \
                patch("world.radio.is_radio", return_value=False), \
                patch("world.stealth.break_stealth") as revealed:
            self._to("Char2 you still there")
        revealed.assert_called_once()
