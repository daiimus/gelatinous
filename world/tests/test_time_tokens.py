"""Time is legible through objects, not a command."""

from datetime import datetime, timezone
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from world import gametime


class TestTimeTokens(EvenniaTest):

    def _at(self, iso_utc):
        moment = datetime.fromisoformat(iso_utc).replace(tzinfo=timezone.utc)
        return mock.patch.object(gametime, "_real_utc", return_value=moment)

    def test_time_token_renders_the_colony_clock(self):
        with self._at("2026-07-31T03:32:00"):          # 19:32 colony
            self.assertEqual(
                gametime.render_time_tokens("The face reads {time}."),
                "The face reads 19:32.")

    def test_twelve_hour_and_date_and_cy(self):
        with self._at("2026-07-31T03:32:00"):
            out = gametime.render_time_tokens("{time12} on {date}, {cy}")
            self.assertEqual(out, "7:32 PM on Jul 30, 3226, CY 61")

    def test_period_is_vague_for_devices_without_a_readout(self):
        with self._at("2026-07-31T11:00:00"):          # 03:00 colony
            self.assertEqual(
                gametime.render_time_tokens("It is {period}."),
                "It is the small hours.")

    def test_text_without_tokens_is_untouched(self):
        text = "A scratched chrome bracelet, its face cracked."
        self.assertIs(gametime.render_time_tokens(text), text)

    def test_unknown_braces_are_left_alone(self):
        """{their} and friends belong to other renderers."""
        text = "{Their} wrist bears a chrono."
        self.assertEqual(gametime.render_time_tokens(text), text)

    def test_empty_and_none_survive(self):
        self.assertEqual(gametime.render_time_tokens(""), "")
        self.assertIsNone(gametime.render_time_tokens(None))


class TestTimepiecesDisagree(EvenniaTest):
    """Two watches in a room should be able to tell you different things."""

    def _at(self, iso_utc):
        moment = datetime.fromisoformat(iso_utc).replace(tzinfo=timezone.utc)
        return mock.patch.object(gametime, "_real_utc", return_value=moment)

    def test_skew_runs_a_watch_fast(self):
        self.obj1.db.clock_skew = 11
        with self._at("2026-07-31T03:32:00"):
            self.assertEqual(
                gametime.render_time_tokens("{time}", self.obj1), "19:43")

    def test_skew_runs_a_watch_slow(self):
        self.obj1.db.clock_skew = -20
        with self._at("2026-07-31T03:32:00"):
            self.assertEqual(
                gametime.render_time_tokens("{time}", self.obj1), "19:12")

    def test_a_stopped_clock_shows_the_moment_it_died(self):
        self.obj1.db.clock_stopped = datetime(
            2025, 11, 13, 5, 43, tzinfo=timezone.utc).timestamp()
        with self._at("2026-07-31T03:32:00"):
            self.assertEqual(
                gametime.render_time_tokens("{time} on {date}", self.obj1),
                "21:43 on Nov 12, 3225")

    def test_a_garbage_skew_does_not_break_the_object(self):
        self.obj1.db.clock_skew = "eleven"
        with self._at("2026-07-31T03:32:00"):
            self.assertEqual(
                gametime.render_time_tokens("{time}", self.obj1), "19:32")


class TestObjectRendersItsOwnDesc(EvenniaTest):
    """The hook is on ObjectParent, so every object type gets it."""

    def test_looking_at_an_item_resolves_the_token(self):
        self.obj1.db.desc = "A field chrono reading {time}."
        with mock.patch.object(gametime, "_real_utc",
                               return_value=datetime(2026, 7, 31, 3, 32,
                                                     tzinfo=timezone.utc)):
            shown = self.obj1.get_display_desc(self.char1)
        self.assertEqual(shown, "A field chrono reading 19:32.")

    def test_an_ordinary_item_is_unaffected(self):
        self.obj1.db.desc = "A dented mug."
        self.assertEqual(self.obj1.get_display_desc(self.char1), "A dented mug.")
