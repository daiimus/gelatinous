"""Ambush + theft (STEALTH_AND_DETECTION_SPEC §6.1/§6.2).

MagicMock harness; the stealth contest and consent predicate are patched at
their sources so what's under test is the command logic — random selection,
same-room-only gating, the caught consequences, the free path.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.stealth import AMBUSH_INITIATIVE_BONUS


class TestAmbushPredicate(TestCase):
    def test_ambush_when_target_cannot_perceive(self):
        from world.stealth import is_ambush
        atk, tgt = MagicMock(), MagicMock()
        with patch("world.perception.can_perceive", return_value=False):
            self.assertTrue(is_ambush(atk, tgt))
        with patch("world.perception.can_perceive", return_value=True):
            self.assertFalse(is_ambush(atk, tgt))

    def test_never_ambush_self(self):
        from world.stealth import is_ambush
        c = MagicMock()
        self.assertFalse(is_ambush(c, c))

    def test_initiative_bonus_threaded(self):
        # add_combatant must fold ambush_bonus into the initiative roll
        from world.combat import utils
        handler = MagicMock()
        handler.db.combatants = []
        char = MagicMock()
        with patch("random.randint", return_value=10), \
                patch("world.combat.utils.get_numeric_stat", return_value=0), \
                patch("world.combat.utils.surplus_limb_initiative_bonus",
                      return_value=0), \
                patch("world.combat.utils.get_character_dbref",
                      return_value=None):
            utils.add_combatant(handler, char,
                                ambush_bonus=AMBUSH_INITIATIVE_BONUS)
        entry = handler.db.combatants[0]
        from world.combat.constants import DB_INITIATIVE
        self.assertEqual(entry[DB_INITIATIVE], 10 + AMBUSH_INITIATIVE_BONUS)


def _target(tokens=0, contents=None, worn=None, hands=None):
    t = MagicMock()
    t.get_sdesc = lambda: "a mark"
    t.get_display_name = lambda looker=None, **k: "a mark"
    t.contents = contents or []
    t.get_worn_items = lambda: (worn or [])
    t.hands = hands or {}
    t.db.tokens = tokens
    return t


def _item(name):
    it = MagicMock()
    it.get_display_name = lambda looker=None, **k: name
    return it


class TestStealableInventory(TestCase):
    def test_excludes_worn_and_held(self):
        from commands.CmdTheft import _stealable_inventory
        loose, worn, held = _item("a chip"), _item("a coat"), _item("a knife")
        t = _target(contents=[loose, worn, held], worn=[worn],
                    hands={"r": held})
        self.assertEqual(_stealable_inventory(t), [loose])


class TestSteal(TestCase):
    def _cmd(self, args, target):
        from commands.CmdTheft import CmdSteal
        cmd = CmdSteal()
        cmd.caller = MagicMock()
        cmd.caller.get_display_name = lambda looker=None, **k: "a thief"
        cmd.caller.search.return_value = target
        cmd.args = args
        cmd.parse()
        return cmd

    def test_no_item_picks_random_carried(self):
        chip = _item("a chip")
        target = _target(contents=[chip])
        cmd = self._cmd("mark", target)
        with patch("commands.CmdTheft.can_contest", return_value=True), \
                patch("commands.CmdTheft.is_ambush", return_value=False), \
                patch("commands.CmdTheft.contest", return_value=-5):
            cmd.func()
        chip.move_to.assert_called_once()          # clean lift
        self.assertIn("clean", cmd.caller.msg.call_args.args[0])

    def test_empty_inventory_message(self):
        cmd = self._cmd("mark", _target(contents=[]))
        with patch("commands.CmdTheft.can_contest", return_value=True):
            cmd.func()
        self.assertIn("nothing loose", cmd.caller.msg.call_args.args[0])

    def test_caught_alerts_and_raises_incident(self):
        chip = _item("a chip")
        target = _target(contents=[chip])
        cmd = self._cmd("mark", target)
        with patch("commands.CmdTheft.can_contest", return_value=True), \
                patch("commands.CmdTheft.is_ambush", return_value=False), \
                patch("commands.CmdTheft.contest", return_value=5), \
                patch("commands.CmdTheft._caught") as caught:
            cmd.func()
        chip.move_to.assert_not_called()           # the lift failed
        caught.assert_called_once_with(cmd.caller, target)

    def test_subdued_mark_is_free_loot(self):
        chip = _item("a chip")
        target = _target(contents=[chip])
        cmd = self._cmd("mark", target)
        with patch("commands.CmdTheft.can_contest", return_value=False), \
                patch("commands.CmdTheft.contest") as roll:
            cmd.func()
        chip.move_to.assert_called_once()
        roll.assert_not_called()                   # no contest when helpless

    def test_specific_item_must_be_reachable(self):
        chip = _item("a chip")
        target = _target(contents=[chip])
        cmd = self._cmd("datajack from mark", target)   # not present
        cmd.caller.search = MagicMock(side_effect=lambda *a, **k:
                                      target if a and a[0] == "mark" else None)
        with patch("commands.CmdTheft.can_contest", return_value=True):
            cmd.func()
        self.assertIn("can't get at", cmd.caller.msg.call_args.args[0])

    def test_ambush_bonus_applied_to_contest(self):
        chip = _item("a chip")
        target = _target(contents=[chip])
        cmd = self._cmd("mark", target)
        with patch("commands.CmdTheft.can_contest", return_value=True), \
                patch("commands.CmdTheft.is_ambush", return_value=True), \
                patch("commands.CmdTheft.contest", return_value=-1) as roll:
            cmd.func()
        from world.stealth import AMBUSH_CONTEST_BONUS
        self.assertEqual(roll.call_args.kwargs.get("hider_bonus"),
                         AMBUSH_CONTEST_BONUS)


class TestPickpocket(TestCase):
    def _cmd(self, target):
        from commands.CmdTheft import CmdPickpocket
        cmd = CmdPickpocket()
        cmd.caller = MagicMock()
        cmd.caller.db.tokens = 0
        cmd.caller.get_display_name = lambda looker=None, **k: "a thief"
        cmd.caller.search.return_value = target
        cmd.args = "mark"
        return cmd

    def test_clean_lift_transfers_tokens(self):
        target = _target(tokens=90)
        cmd = self._cmd(target)
        with patch("commands.CmdTheft.can_contest", return_value=True), \
                patch("commands.CmdTheft.is_ambush", return_value=False), \
                patch("commands.CmdTheft.contest", return_value=-5), \
                patch("commands.CmdTheft.randint", return_value=20):
            cmd.func()
        self.assertEqual(cmd.caller.db.tokens, 20)
        self.assertEqual(target.db.tokens, 70)

    def test_no_tokens_message(self):
        cmd = self._cmd(_target(tokens=0))
        with patch("commands.CmdTheft.can_contest", return_value=True):
            cmd.func()
        self.assertIn("no tokens", cmd.caller.msg.call_args.args[0])

    def test_caught_leaves_tokens_and_raises(self):
        target = _target(tokens=90)
        cmd = self._cmd(target)
        with patch("commands.CmdTheft.can_contest", return_value=True), \
                patch("commands.CmdTheft.is_ambush", return_value=False), \
                patch("commands.CmdTheft.contest", return_value=5), \
                patch("commands.CmdTheft.randint", return_value=20), \
                patch("commands.CmdTheft._caught") as caught:
            cmd.func()
        self.assertEqual(target.db.tokens, 90)     # nothing taken
        caught.assert_called_once()


class TestCaughtConsequences(TestCase):
    def test_caught_alerts_witnesses_and_raises_sourceless_crime(self):
        from commands.CmdTheft import _caught
        thief = MagicMock()
        thief.get_sdesc = lambda: "a thief"
        victim = MagicMock()
        witness, blindfolded = MagicMock(), MagicMock()
        witness.get_sdesc = blindfolded.get_sdesc = lambda: "x"
        room = MagicMock()
        room.contents = [thief, victim, witness, blindfolded]
        thief.location = room
        with patch("commands.CmdTheft.set_awareness") as aware, \
                patch("world.perception.can_see",
                      side_effect=lambda o: o is witness), \
                patch("world.director.dispatch.raise_event") as raised:
            _caught(thief, victim)
        awared = {c.args[0] for c in aware.call_args_list}
        self.assertIn(victim, awared)
        self.assertIn(witness, awared)
        self.assertNotIn(blindfolded, awared)      # can't see = not alerted
        event = raised.call_args.args[0]
        self.assertEqual(event.type, "crime")
        self.assertIsNone(event.source)            # unidentified -> hot scene
