"""
Tests for clothing broadcast snapshot + article grammar (PR-E).

Covers the helper utilities ``_snapshot_actor_names`` and ``_articled``
in :mod:`commands.CmdClothing` that ensure room broadcasts for
``wear`` / ``remove`` / ``rollup`` / ``zip`` describe the actor's
*pre-mutation* sdesc and use indefinite-article grammar for item names.

See ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Action Broadcast Sdesc
Stability".

Run via::

    evennia test world.tests.test_clothing_broadcast
"""

from unittest import TestCase
from unittest.mock import MagicMock

from evennia.utils.utils import iter_to_str

from commands.CmdClothing import _articled, _snapshot_actor_names


class TestArticled(TestCase):
    """Indefinite-article grammar for item keys."""

    def test_consonant_initial(self):
        self.assertEqual(_articled("black balaclava"), "a black balaclava")

    def test_vowel_initial(self):
        self.assertEqual(_articled("axe handle"), "an axe handle")

    def test_silent_h_uses_an(self):
        # get_article handles "hour" as vowel-sound
        self.assertEqual(_articled("hour glass"), "an hour glass")


class TestArticledIterToStr(TestCase):
    """`iter_to_str` over articled keys produces natural lists."""

    def test_single(self):
        self.assertEqual(
            iter_to_str([_articled("jacket")]),
            "a jacket",
        )

    def test_two(self):
        self.assertEqual(
            iter_to_str([_articled("jacket"), _articled("axe")]),
            "a jacket and an axe",
        )

    def test_three(self):
        self.assertEqual(
            iter_to_str([
                _articled("jacket"),
                _articled("axe"),
                _articled("balaclava"),
            ]),
            "a jacket, an axe, and a balaclava",
        )


class TestSnapshotActorNames(TestCase):
    """Pre-mutation observer-name capture for char_refs."""

    def _observer(self, name):
        obs = MagicMock()
        obs.msg = MagicMock()  # has msg attr
        obs._test_name = name
        return obs

    def _itemobj(self):
        # An object without a msg attribute — must be skipped.
        item = MagicMock(spec=[])
        return item

    def test_snapshot_excludes_caller(self):
        caller = MagicMock()
        caller.msg = MagicMock()
        alice = self._observer("alice")
        bob = self._observer("bob")
        room = MagicMock()
        room.contents = [caller, alice, bob]
        caller.location = room

        # actor.get_display_name returns observer-specific names
        caller.get_display_name = MagicMock(
            side_effect=lambda obs: f"PRE-{obs._test_name}"
        )

        snapshot = _snapshot_actor_names(caller, {"actor": caller})

        self.assertIn("actor", snapshot)
        self.assertEqual(
            snapshot["actor"],
            {alice: "PRE-alice", bob: "PRE-bob"},
        )
        # Caller never asked for own display name
        for call in caller.get_display_name.call_args_list:
            self.assertNotIn(caller, call.args)

    def test_snapshot_skips_non_msg_contents(self):
        caller = MagicMock()
        caller.msg = MagicMock()
        alice = self._observer("alice")
        item = self._itemobj()  # no msg attr
        room = MagicMock()
        room.contents = [caller, alice, item]
        caller.location = room
        caller.get_display_name = MagicMock(
            side_effect=lambda obs: f"PRE-{obs._test_name}"
        )

        snapshot = _snapshot_actor_names(caller, {"actor": caller})

        self.assertEqual(snapshot["actor"], {alice: "PRE-alice"})

    def test_snapshot_defensive_for_all_char_refs(self):
        """Snapshot every placeholder, not only 'actor'."""
        caller = MagicMock()
        caller.msg = MagicMock()
        victim = MagicMock()
        victim.msg = MagicMock()
        observer = self._observer("alice")
        room = MagicMock()
        room.contents = [caller, victim, observer]
        caller.location = room

        caller.get_display_name = MagicMock(return_value="PRE-actor")
        victim.get_display_name = MagicMock(return_value="PRE-victim")

        snapshot = _snapshot_actor_names(
            caller, {"actor": caller, "victim": victim}
        )

        self.assertEqual(set(snapshot.keys()), {"actor", "victim"})
        self.assertEqual(snapshot["actor"][observer], "PRE-actor")
        self.assertEqual(snapshot["victim"][observer], "PRE-victim")

    def test_snapshot_empty_when_no_location(self):
        caller = MagicMock()
        caller.location = None
        snapshot = _snapshot_actor_names(caller, {"actor": caller})
        self.assertEqual(snapshot, {})
