"""#3767 -- acting reveals, slice two.

Owner, 2026-10-24: "You shouldn't be able to hide a rigged grenade or
charge. It's a trap. A visible trap (if you're in the same room with
it)." and "If they're hidden, an NPC shouldn't see them. The NPC should
only recognize visible people Or when a hidden person is revealed/unhides."

So `hide <device>` refuses an explosive whose pin is out or which is wired
to an exit; a detonator arming a stashed charge brings it into plain
sight before its beep; and an LLM NPC deciding whether a speaker is
alone with it counts only the company it perceives (the PRESENT roster
and the arrival notice already did, #2589).

Two things settled earlier and pinned here, not changed: lying in a
clinic pod reveals a hidden patient like any seat (#3763, through the
pose), and an aimer cannot target someone they cannot perceive, so an aim
never outlives a hide.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdExplosives import CmdDetonate
from commands.CmdFurniture import CmdLie
from commands.CmdStealth import CmdHide
from commands._identity_targeting import resolve_character_target
from world.perception import can_perceive
from world.stealth import UNAWARE, set_awareness


class _Hider(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char2.location = self.room1

    def grenade(self, key="frag grenade", location=None, pin=False, rigged=None):
        g = create_object("typeclasses.items.Item", key=key,
                          location=location or self.char2)
        g.db.is_explosive = True
        if pin:
            g.db.pin_pulled = True
        if rigged is not None:
            g.db.rigged_to_exit = rigged
        return g

    def as_player(self, cmd, args):
        return self.call(cmd, args, caller=self.char2) or ""


class TestALiveDeviceCannotBeHidden(_Hider):

    def test_a_pulled_pin_refuses(self):
        g = self.grenade(pin=True)
        out = self.as_player(CmdHide(), "frag grenade")
        self.assertIn("in plain sight", out)
        self.assertIs(g.location, self.char2)
        self.assertFalse(g.db.hidden)

    def test_a_rigged_charge_refuses(self):
        g = self.grenade(rigged=self.exit)
        out = self.as_player(CmdHide(), "frag grenade")
        self.assertIn("in plain sight", out)
        self.assertFalse(g.db.hidden)

    def test_control_a_safe_grenade_can_be_stashed(self):
        g = self.grenade()
        out = self.as_player(CmdHide(), "frag grenade")
        self.assertIn("stash", out)
        self.assertTrue(g.db.hidden)
        self.assertIs(g.location, self.room1)

    def test_control_a_live_thing_that_is_not_an_explosive_is_untouched(self):
        tin = create_object("typeclasses.items.Item", key="tin", location=self.char2)
        tin.db.pin_pulled = True          # nonsense on a tin; the guard reads is_explosive first
        out = self.as_player(CmdHide(), "tin")
        self.assertIn("stash", out)


class TestArmingBringsAStashedChargeIntoSight(_Hider):

    def setUp(self):
        super().setUp()
        self.detonator = create_object("typeclasses.items.RemoteDetonator",
                                       key="detonator", location=self.char1)
        self.char1.hands = {"left_hand": self.detonator}

    def charge(self):
        g = self.grenade(key="demo charge", location=self.room1)
        g.db.hidden = True                       # stashed before it was scanned
        self.detonator.db.scanned_explosives = list(
            self.detonator.db.scanned_explosives or []) + [g.id]
        return g

    def test_one_charge(self):
        g = self.charge()
        self.call(CmdDetonate(), f"e-{g.id} with detonator")
        self.assertTrue(g.db.pin_pulled, "the charge did not arm")
        self.assertFalse(g.db.hidden)

    def test_all_charges(self):
        a, b = self.charge(), self.charge()
        self.call(CmdDetonate(), "all with detonator")
        self.assertTrue(a.db.pin_pulled and b.db.pin_pulled)
        self.assertFalse(a.db.hidden or b.db.hidden)


class TestTheNpcCountsOnlyWhatItSees(_Hider):

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc", key="a keeper",
                                 location=self.room1)
        self.npc.db.llm_driven = True
        # char1 is the bystander, char2 the speaker
        self.bystander, self.speaker = self.char1, self.char2

    def test_a_hidden_bystander_leaves_the_speaker_alone_with_the_npc(self):
        self.bystander.db.hidden = True
        set_awareness(self.npc, self.bystander, UNAWARE)
        self.assertFalse(can_perceive(self.npc, self.bystander), "premise")
        self.assertTrue(self.npc._is_alone_with(self.speaker))

    def test_control_a_visible_bystander_is_company(self):
        self.assertFalse(self.npc._is_alone_with(self.speaker))

    def test_revealed_the_bystander_is_company_again(self):
        self.bystander.db.hidden = True
        set_awareness(self.npc, self.bystander, UNAWARE)
        from world.stealth import break_stealth
        break_stealth(self.bystander, quiet=True)
        self.assertFalse(self.npc._is_alone_with(self.speaker))


class TestPinsFromEarlierRulings(_Hider):

    def test_lying_in_a_clinic_pod_reveals(self):
        pod = create_object("typeclasses.furniture.AutoDoc", key="autodoc",
                            location=self.room1)
        pod.db.postures = ("lying",)
        self.char2.db.hidden = True
        set_awareness(self.char1, self.char2, UNAWARE)
        self.as_player(CmdLie(), "autodoc")
        self.assertEqual(self.char2.db.posture, "lying")
        self.assertFalse(self.char2.db.hidden)

    def test_an_aim_never_outlives_a_hide(self):
        """An aimer cannot target someone they cannot perceive, and a target
        under a live aim cannot hide (#3763), so there is no state in which
        an aim points at a hidden person."""
        self.char2.db.hidden = True
        set_awareness(self.char1, self.char2, UNAWARE)
        self.assertIsNone(resolve_character_target(self.char1, "char2"))
