"""Destroying armor takes a grenade stuck to it, and a deleted grenade's
fuse stops (#3561).

The delete hook severed the sticky bond only when the dying object was the
GRENADE. Deleting the ARMOR left the grenade inside it, so Evennia's
`clear_contents` sent the still-armed grenade to its home -- Limbo, since
grenades set none. Its countdown went silent (the stuck check failed) and
it detonated a few seconds later, gone from the fight. Owner ruling: the
grenade goes with the armor.

Deleting the grenade alone was not enough either. A pulled pin is a
scheduled timer, and a deleted object is still a truthy Python object with
an `ndb` inside the scheduled tick -- so the countdown ran on and the
failsafe exploded it. The timer is now stopped on delete (through the one
fuse-stop door that six call sites used to copy), and a grenade with no
database row refuses to explode or tick.

Asserts on STATE: rows in the database, timers cancelled, explosions not
reached.
"""
from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest
from twisted.internet.error import AlreadyCalled

import commands.explosion_utils as xu
from world.combat.constants import NDB_COUNTDOWN_REMAINING, NDB_GRENADE_TIMER
from world.combat.explosives import establish_stick


def _exists(obj_id):
    return ObjectDB.objects.filter(id=obj_id).exists()


class _Stuck(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.armor = create_object("typeclasses.items.Item", key="plate carrier",
                                   location=self.char1)
        self.grenade = create_object("typeclasses.items.Item", key="SPDR M9 grenade",
                                     location=self.room1)
        self.grenade.db.is_explosive = True
        establish_stick(self.grenade, self.armor, "chest")
        assert self.grenade.location == self.armor, "fixture: not stuck"
        assert self.armor.db.stuck_grenade == self.grenade


class TheArmorTakesItsGrenade(_Stuck):

    def test_destroying_the_armor_deletes_the_grenade(self):
        gid = self.grenade.id
        self.armor.delete()
        self.assertFalse(_exists(gid), "the grenade outlived its armor")

    def test_the_armor_is_still_deleted(self):
        aid = self.armor.id
        self.armor.delete()
        self.assertFalse(_exists(aid))

    def test_armor_with_nothing_stuck_deletes_as_before(self):
        plain = create_object("typeclasses.items.Item", key="vest", location=self.char1)
        pid = plain.id
        self.assertTrue(plain.delete())
        self.assertFalse(_exists(pid))

    def test_control_deleting_the_grenade_alone_leaves_the_armor(self):
        # The #3552 direction is unchanged: the armor survives, bond cleared.
        aid = self.armor.id
        self.grenade.delete()
        self.assertTrue(_exists(aid))
        self.assertIsNone(self.armor.db.stuck_grenade)


class ADeletedGrenadesFuseStops(_Stuck):

    def test_deleting_an_armed_grenade_cancels_its_timer(self):
        timer = MagicMock()
        setattr(self.grenade.ndb, NDB_GRENADE_TIMER, timer)
        self.grenade.delete()
        timer.cancel.assert_called_once()

    def test_destroying_the_armor_cancels_the_stuck_grenades_timer(self):
        timer = MagicMock()
        setattr(self.grenade.ndb, NDB_GRENADE_TIMER, timer)
        self.armor.delete()
        timer.cancel.assert_called_once()

    def test_a_timer_that_escaped_does_not_explode_a_deleted_grenade(self):
        # Belt and braces: even if a tick fires after the delete, nothing
        # goes off. Control first -- a live grenade DOES reach the blast.
        with patch.object(xu, "get_unified_explosion_proximity", return_value=[]) as blast:
            ghost = create_object("typeclasses.items.Item", key="frag", location=self.room1)
            ghost.db.is_explosive = True
            ghost.db.dud_chance = 0.0
            xu.explode_standalone_grenade(ghost)
            self.assertTrue(blast.called, "control: a live grenade never reached the blast")
        with patch.object(xu, "get_unified_explosion_proximity", return_value=[]) as blast:
            self.grenade.delete()
            xu.explode_standalone_grenade(self.grenade)
            blast.assert_not_called()

    def test_the_countdown_stops_ticking_once_the_grenade_is_gone(self):
        scheduled = []
        fake_timer = MagicMock()

        def fake_delay(seconds, fn, *a, **k):
            scheduled.append(fn)
            return fake_timer
        setattr(self.grenade.ndb, NDB_COUNTDOWN_REMAINING, 4)
        with patch.object(xu.utils, "delay", side_effect=fake_delay), \
                patch.object(xu, "explode_standalone_grenade") as boom:
            xu.start_grenade_ticker(self.grenade)
            self.assertEqual(len(scheduled), 1, "control: the ticker never scheduled")
            self.armor.delete()
            scheduled[0]()                      # the tick that was already queued
            self.assertEqual(len(scheduled), 1, "a deleted grenade scheduled another tick")
            boom.assert_not_called()


class TheOneFuseDoor(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.g = create_object("typeclasses.items.Item", key="frag", location=self.room1)

    def test_no_timer_is_a_no_op(self):
        self.assertFalse(xu.stop_grenade_fuse(self.g))

    def test_cancels_and_forgets(self):
        timer = MagicMock()
        setattr(self.g.ndb, NDB_GRENADE_TIMER, timer)
        self.assertTrue(xu.stop_grenade_fuse(self.g))
        timer.cancel.assert_called_once()
        self.assertIsNone(getattr(self.g.ndb, NDB_GRENADE_TIMER, None))

    def test_a_timer_that_already_fired_is_tolerated(self):
        # Four of the six old copies called a bare cancel(), which can raise here.
        timer = MagicMock()
        timer.cancel.side_effect = AlreadyCalled()
        setattr(self.g.ndb, NDB_GRENADE_TIMER, timer)
        self.assertTrue(xu.stop_grenade_fuse(self.g))
        self.assertIsNone(getattr(self.g.ndb, NDB_GRENADE_TIMER, None))

    def test_there_is_one_door(self):
        """Nothing outside the door touches a grenade's fuse timer by hand.

        Everywhere in the runtime tree (commands/, world/, typeclasses/),
        the fuse timer is named only by the constant's definition and by
        explosion_utils, which schedules it. Inside explosion_utils, only
        stop_grenade_fuse cancels or forgets it -- the old rig bug was a
        forget without a cancel, so both are checked."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        allowed = {root / "world/combat/constants.py", root / "commands/explosion_utils.py"}
        for top in ("commands", "world", "typeclasses"):
            for path in (root / top).rglob("*.py"):
                if "tests" in path.parts or path in allowed:
                    continue
                src = path.read_text(errors="ignore")
                for name in ("NDB_GRENADE_TIMER", "grenade_timer"):
                    self.assertNotIn(name, src, f"{path.relative_to(root)} touches the fuse timer")
        util = (root / "commands/explosion_utils.py").read_text()
        body_start = util.index("def stop_grenade_fuse")
        rest = util[:body_start] + util[util.index("\ndef ", body_start + 1):]
        self.assertNotIn(".cancel()", rest, "a hand-rolled cancel survives outside stop_grenade_fuse")
        self.assertNotIn("delattr(grenade.ndb, NDB_GRENADE_TIMER)", rest,
                         "a forget-without-cancel survives outside stop_grenade_fuse")

    def test_the_auto_defuse_resolver_refuses_a_deleted_grenade(self):
        # Its timers live outside ndb.grenade_timer, so only the guard
        # covers them. Control: a live grenade reaches the blast.
        self.g.db.dud_chance = 0.0   # a dud returns before the blast
        with patch.object(xu, "get_unified_explosion_proximity", return_value=[]) as blast:
            xu.trigger_auto_defuse_explosion(self.g)
            self.assertTrue(blast.called, "control: a live grenade never reached the blast")
        g2 = create_object("typeclasses.items.Item", key="frag2", location=self.room1)
        g2.delete()
        with patch.object(xu, "get_unified_explosion_proximity", return_value=[]) as blast:
            xu.trigger_auto_defuse_explosion(g2)
            blast.assert_not_called()
