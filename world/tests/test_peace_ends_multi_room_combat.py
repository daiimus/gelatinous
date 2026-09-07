""""@peace" ends the fight you are standing in (#2543).

A `CombatHandler` is **hosted** on one room but **manages** a list of
them. `@peace` enumerated `location.scripts.all()` — scripts attached to
*that room object* — while every other consumer scans
`db.managed_rooms`.

So an admin standing in the non-hosting half of a cross-room firefight
was told *"No combat to end in <room>"* while the handler kept ticking
rounds against the people in front of them.

`managed_rooms` starts as `[self.obj]` and grows when handlers merge for
cross-room ranged combat. Two doors onto "who is running combat here?",
and `@peace` used the one that does not know about multi-room combat.

The old form also had **no `is_active` filter**, so a stopped handler
still attached to the room counted as combat to end.

`find_combat_handlers` is now the one implementation;
`get_or_create_combat` uses it for its own first pass, which was the
same loop written out.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest


def find_handlers(location):
    from world.combat.handler import find_combat_handlers
    return find_combat_handlers(location)


class _CombatCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room2

    def handler_managing(self, *rooms, active=True):
        """A stand-in for a running handler, registered the way the real
        lookup finds one: by key, active flag, and managed_rooms."""
        script = mock.MagicMock()
        script.key = "combat_handler"
        script.db.managed_rooms = list(rooms)
        script.is_active = active
        return script


class TestTheLookupFollowsManagedRooms(_CombatCase):
    def _patched(self, scripts):
        return mock.patch(
            "evennia.scripts.models.ScriptDB.objects.filter",
            return_value=scripts)

    def test_it_finds_a_handler_hosted_elsewhere(self):
        """The whole defect: room2 is managed, not hosting."""
        handler = self.handler_managing(self.room1, self.room2)
        with self._patched([handler]):
            self.assertEqual(find_handlers(self.room2), [handler])

    def test_it_finds_a_handler_on_its_host_room(self):
        handler = self.handler_managing(self.room1)
        with self._patched([handler]):
            self.assertEqual(find_handlers(self.room1), [handler])

    def test_it_finds_nothing_in_an_unmanaged_room(self):
        handler = self.handler_managing(self.room1)
        with self._patched([handler]):
            self.assertEqual(find_handlers(self.room2), [])

    def test_a_handler_with_no_managed_rooms_is_skipped(self):
        handler = self.handler_managing()
        with self._patched([handler]):
            self.assertEqual(find_handlers(self.room1), [])

    def test_it_asks_for_active_handlers_only(self):
        """The filter is pushed into the query, so a stopped handler
        lying on the room can never come back."""
        with mock.patch(
                "evennia.scripts.models.ScriptDB.objects.filter",
                return_value=[]) as flt:
            find_handlers(self.room1)
        _args, kwargs = flt.call_args
        self.assertTrue(kwargs.get("db_is_active"))


class TestPeaceUsesIt(EvenniaTest):
    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "commands" / "CmdAdmin.py").read_text(errors="ignore")

    def test_peace_no_longer_enumerates_room_scripts(self):
        self.assertNotIn(
            "handlers = [script for script in location.scripts.all()",
            self._source())

    def test_peace_calls_the_canonical_lookup(self):
        self.assertIn("handlers = find_combat_handlers(location)",
                      self._source())


class TestTheTwoDoorsBecameOne(EvenniaTest):
    """`get_or_create_combat` had this loop written out; it now shares
    the implementation, so the two answers cannot drift again."""

    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "world" / "combat" / "handler.py").read_text(
            errors="ignore")

    def test_get_or_create_delegates(self):
        self.assertIn("for handler_script in find_combat_handlers(location):",
                      self._source())

    def test_the_duplicated_scan_is_gone(self):
        body = self._source()
        self.assertEqual(body.count("db_is_active=True"), 1)

    def test_the_lookup_never_creates(self):
        """`@peace` must not conjure a handler into an empty room."""
        body = self._source()
        start = body.index("def find_combat_handlers(location):")
        end = body.index("def get_or_create_combat(location):")
        self.assertNotIn("create_script", body[start:end])
