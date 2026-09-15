"""@pin / @unpin hold souls only; players and staff are refused (#owner 2026-09-14)."""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdPin import CmdPin, CmdUnpin
from world.souls import engine


class PinRefusesPlayersAndStaffTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.soul = create_object("typeclasses.llm_npc.LLMNpc", key="Pinnable", location=self.room1)
        self.soul.db.is_npc = True
        engine.ensoul(self.soul, role="resident")

    def test_a_soul_can_be_pinned_and_unpinned(self):
        out = self.call(CmdPin(), "Pinnable", caller=self.char1)
        self.assertIn("pinned in place", out)
        self.assertTrue(engine.is_pinned(self.soul))
        out = self.call(CmdUnpin(), "Pinnable", caller=self.char1)
        self.assertIn("living again", out)
        self.assertFalse(engine.is_pinned(self.soul))

    def test_a_players_character_is_refused(self):
        out = self.call(CmdPin(), self.char2.key, caller=self.char1)
        self.assertIn("player's character", out)
        self.assertFalse(engine.is_pinned(self.char2))

    def test_staff_are_refused(self):
        staff = create_object("typeclasses.llm_npc.LLMNpc", key="Staffsoul", location=self.room1)
        engine.ensoul(staff, role="resident")
        staff.permissions.add("Builder")
        out = self.call(CmdPin(), "Staffsoul", caller=self.char1)
        self.assertIn("staff", out)
        self.assertFalse(engine.is_pinned(staff))

    def test_a_body_with_no_soul_is_refused(self):
        body = create_object("typeclasses.characters.Character", key="Hollow", location=self.room1)
        body.db.is_npc = True
        out = self.call(CmdPin(), "Hollow", caller=self.char1)
        self.assertIn("not a soul", out)

    def test_bare_pin_lists_the_pinned(self):
        engine.pin(self.soul)
        out = self.call(CmdPin(), "", caller=self.char1)
        self.assertIn("Pinnable", out)
