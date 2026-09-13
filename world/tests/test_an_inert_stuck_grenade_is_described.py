"""look / remove on armor with an INERT stuck grenade describe it (#3361).

Both sites read the grenade's countdown from ndb with a default of 0 --
but Evennia's ndb hands back None for a key that was never set, and
`None > 0` is a TypeError. So a dud, or a grenade stuck with its pin
never pulled, or any stuck grenade whose ndb was wiped without a live
deadline, turned `look <armor>` and `remove <armor>` into tracebacks.
The intended line -- "A <grenade> is magnetically clamped to this item."
-- was unreachable for exactly the grenades it was written for.

(An ARMED grenade across a reload is a different story and works: the
#505 sweep restores countdown_remaining before anyone can look.)
"""
from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdClothing import CmdRemove
from world.prototypes import PLATE_CARRIER


class InertStuckGrenadeTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.armor = spawn(PLATE_CARRIER)[0]          # real wearable, so remove reaches the gate
        self.armor.move_to(self.char1, quiet=True)
        self.grenade = create_object("typeclasses.items.Item", key="dud grenade", location=self.armor)
        self.armor.db.stuck_grenade = self.grenade
        self.grenade.db.stuck_to_location = "chest"
        # No countdown_remaining on ndb: an inert grenade.

    def test_look_describes_the_clamped_grenade(self):
        text = self.armor.return_appearance(self.char1)   # raised TypeError before
        self.assertIn("magnetically clamped", text)
        self.assertNotIn("EXPLOSION IN", text)

    def test_look_with_live_countdown_warns(self):
        # Control: a running fuse still produces the loud warning.
        self.grenade.ndb.countdown_remaining = 5
        text = self.armor.return_appearance(self.char1)
        self.assertIn("EXPLOSION IN 5 SECONDS", text)

    def test_remove_does_not_traceback(self):
        self.char1.wear_item(self.armor)
        assert self.armor in {i for l in (self.char1.worn_items or {}).values() for i in l}, "precondition: not worn"
        out = self.call(CmdRemove(), "plate carrier")   # raised TypeError before
        self.assertNotIn("Traceback", out or "")
        self.assertNotIn("TypeError", out or "")
