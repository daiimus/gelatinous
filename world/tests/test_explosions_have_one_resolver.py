"""Explosives: two live findings from #2453, two already closed.

**A failed defuse of a grenade in your OWN HANDS was a free escape.**
`trigger_early_explosion` was a near-line-for-line copy of
`explosion_utils.explode_standalone_grenade` with one thing missing:
the holder branch. So the 30% early-detonation path sent
`msg_contents` to the CHARACTER (which fans out to their inventory, not
the room), handed `Character.exits` to the adjacent-room notifier
(empty, a silent no-op), got an empty proximity list, damaged nobody,
and deleted the grenade. You took nothing, the room was told nothing.

Fumbling a defuse on a live grenade in your hand was therefore strictly
SAFER than letting the fuse run out, which doubles damage against the
holder. `THROW_COMMAND_SPEC` marks both paths shipped and parallel.

Two resolvers sharing damage/chain/dud logic almost exactly, and only
one ever grew the guard — they read as complete side by side unless you
diff them. So the fix DELEGATES rather than growing a second copy: the
standalone resolver is a strict superset (dud, holder, stuck-to-armor,
human shield, room-filtered blast list, chain, delete), and one
resolver cannot drift from itself.

**`jump on <explosive>` inherited nothing.** Two defects in one line:
it read `NDB_PROXIMITY` ("in_proximity_with", the COMBAT relationship)
while a grenade's blast list lives on `NDB_PROXIMITY_UNIVERSAL`
("proximity"), and `getattr(obj.ndb, key, default)` never returns the
default — Evennia's DbHolder answers None for a missing key, so the
`set()` was decoration and the truthiness test always failed. The
hero's documented proximity inheritance, the whole point of throwing
yourself on a grenade, was a silent no-op every time.

**Two findings did not survive checking.** Finding 1 (blast damage
from an adjacent room) — the symptom is closed: the room filter lives
inside `get_unified_explosion_proximity`, which every damage loop
calls, so a character who ran is dropped at detonation. The underlying
one-directional proximity write remains as state hygiene, not a live
defect. Finding 4 (`at_delete` is not an Evennia hook) — #2590 renamed
both to `at_object_delete`; only the capacity gate still counted
without pruning, which is hardened here.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.combat.constants import NDB_PROXIMITY, NDB_PROXIMITY_UNIVERSAL


class _BoomCase(EvenniaTest):
    def grenade(self, location=None):
        nade = create_object("typeclasses.items.Item", key="a grenade",
                             location=location or self.room1)
        nade.db.is_explosive = True
        nade.db.blast_damage = 10
        nade.db.dud_chance = 0.0
        nade.db.pin_pulled = True
        return nade


class TestOneResolverForEveryDetonation(_BoomCase):
    def test_early_detonation_delegates(self):
        from commands.CmdExplosives import CmdDefuse
        nade = self.grenade(location=self.char1)
        cmd = CmdDefuse()
        cmd.caller = self.char1
        with patch("commands.explosion_utils.explode_standalone_grenade") \
                as resolver:
            cmd.trigger_early_explosion(nade)
        resolver.assert_called_once_with(nade)

    def test_it_no_longer_carries_its_own_damage_loop(self):
        """The copy is what drifted. If a second one reappears, this
        fails."""
        import inspect
        from commands.CmdExplosives import CmdDefuse
        source = inspect.getsource(CmdDefuse.trigger_early_explosion)
        self.assertNotIn("take_damage", source)
        self.assertNotIn("chain_trigger", source)

    def test_the_shared_resolver_still_knows_about_holders(self):
        import inspect
        from commands.explosion_utils import explode_standalone_grenade
        source = inspect.getsource(explode_standalone_grenade)
        self.assertIn("holder", source)


class TestTheHeroInheritsTheBlastList(_BoomCase):
    def test_the_universal_key_is_what_jump_reads(self):
        import inspect
        from commands.combat import jump
        source = inspect.getsource(jump)
        idx = source.index("Get everyone currently in proximity")
        window = source[idx:idx + 900]
        self.assertIn("NDB_PROXIMITY_UNIVERSAL", window)

    def test_the_two_keys_really_are_different(self):
        """If these were ever unified the fix would be moot — pin that
        they are not."""
        self.assertNotEqual(NDB_PROXIMITY, NDB_PROXIMITY_UNIVERSAL)

    def test_a_missing_ndb_key_answers_none_not_the_default(self):
        """The second half of the defect: `getattr(obj.ndb, k, default)`
        never returns the default, so the `set()` was decoration."""
        nade = self.grenade()
        self.assertIsNone(getattr(nade.ndb, NDB_PROXIMITY_UNIVERSAL,
                                  "sentinel"))

    def test_a_populated_blast_list_is_readable_through_that_key(self):
        nade = self.grenade()
        setattr(nade.ndb, NDB_PROXIMITY_UNIVERSAL, [self.char2])
        found = getattr(nade.ndb, NDB_PROXIMITY_UNIVERSAL, None) or []
        self.assertIn(self.char2, found)


class TestTheDetonatorStopsLyingAboutCapacity(EvenniaTest):
    def detonator(self):
        det = create_object("typeclasses.items.RemoteDetonator",
                            key="a detonator", location=self.char1)
        return det

    def test_a_stale_signature_does_not_wedge_the_gate(self):
        det = self.detonator()
        det.db.max_capacity = 2
        det.db.scanned_explosives = [999999, 999998]   # long gone
        nade = create_object("typeclasses.items.Item", key="a grenade",
                             location=self.room1)
        nade.db.is_explosive = True
        ok, _msg = det.add_explosive(nade)
        self.assertTrue(ok, "an effectively-empty detonator refused a scan")

    def test_a_genuinely_full_detonator_still_refuses(self):
        det = self.detonator()
        det.db.max_capacity = 1
        live = create_object("typeclasses.items.Item", key="a live one",
                             location=self.room1)
        live.db.is_explosive = True
        det.db.scanned_explosives = [live.id]
        other = create_object("typeclasses.items.Item", key="another",
                              location=self.room1)
        other.db.is_explosive = True
        ok, msg = det.add_explosive(other)
        self.assertFalse(ok)
        self.assertIn("capacity", msg.lower())

    def test_the_delete_hook_has_the_real_evennia_name(self):
        """#2590. `at_delete` is not a hook; `at_object_delete` is."""
        from typeclasses.items import Item, RemoteDetonator
        for cls in (Item, RemoteDetonator):
            self.assertTrue(hasattr(cls, "at_object_delete"))
            self.assertFalse(hasattr(cls, "at_delete"))


class TestTheAdjacentRoomLeakStaysClosed(_BoomCase):
    """Finding 1's symptom, already fixed — pinned as a regression."""

    def test_the_blast_list_is_room_filtered(self):
        import inspect
        from commands.explosion_utils import get_unified_explosion_proximity
        source = inspect.getsource(get_unified_explosion_proximity)
        self.assertIn("get_explosion_room", source)
