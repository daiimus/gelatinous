"""Ambush + theft (STEALTH_AND_DETECTION_SPEC §6.1/§6.2).

MagicMock harness; the stealth contest and consent predicate are patched at
their sources so what's under test is the command logic — random selection,
same-room-only gating, the caught consequences, the free path.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdTheft import CmdSteal

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


def _target(tokens=0, contents=None, worn=None, hands=None, held_items=None):
    t = MagicMock()
    t.get_sdesc = lambda: "a mark"
    t.get_display_name = lambda looker=None, **k: "a mark"
    t.contents = contents or []
    t.get_worn_items = lambda: (worn or [])
    t.hands = hands or {}
    # the slot store the filter reads; by default it agrees with the view
    t.held_items = dict(t.hands) if held_items is None else held_items
    t.tokens = tokens          # the real wallet surface (Character property)
    return t


def _item(name, integrated=False):
    it = MagicMock()
    it.get_display_name = lambda looker=None, **k: name
    it.db.integrated = integrated   # a MagicMock would answer "yes"
    return it


class TestStealableInventory(TestCase):
    def test_excludes_worn_and_held(self):
        from commands.CmdTheft import _stealable_inventory
        loose, worn, held = _item("a chip"), _item("a coat"), _item("a knife")
        t = _target(contents=[loose, worn, held], worn=[worn],
                    hands={"r": held})
        self.assertEqual(_stealable_inventory(t), [loose])

    def test_integrated_hardware_is_never_loose(self):
        # #3698: integrated hardware is never loose, even with no slot
        # naming it (the flag clause alone; the store clause is next).
        from commands.CmdTheft import _stealable_inventory
        loose, gun = _item("a chip"), _item("a forearm shotgun", integrated=True)
        t = _target(contents=[loose, gun], hands={"l": None, "r": None}, held_items={"l": None, "r": None})
        self.assertEqual(_stealable_inventory(t), [loose])

    def test_what_a_slot_still_holds_is_not_loose(self):
        # The view drops a pulped hand's slot; the store still names the knife.
        from commands.CmdTheft import _stealable_inventory
        loose, knife = _item("a chip"), _item("a knife")
        t = _target(contents=[loose, knife], hands={"r": None}, held_items={"l": knife, "r": None})
        self.assertEqual(_stealable_inventory(t), [loose])

    def test_a_stub_without_a_store_falls_back_to_the_view(self):
        from commands.CmdTheft import _stealable_inventory
        loose, held = _item("a chip"), _item("a knife")
        t = _target(contents=[loose, held], hands={"r": held})
        del t.held_items
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

    def test_caught_report_rides_the_witness_pipeline(self):
        # No magic radio: the botched lift routes through report_crime
        # (crowd-gated witness + real walkie), never a raw raise_event.
        from commands.CmdTheft import _caught
        thief = MagicMock()
        room = MagicMock(); room.contents = []
        thief.location = room
        victim = MagicMock()
        with patch("commands.CmdTheft.set_awareness"), \
                patch("world.director.crime.report_crime") as report, \
                patch("world.director.dispatch.raise_event") as raw:
            _caught(thief, victim)
        report.assert_called_once()
        args, kwargs = report.call_args
        self.assertEqual(args[0], "pickpocketing")
        self.assertIs(args[1], room)
        self.assertIsNone(kwargs.get("perp"))   # witnessed-but-unidentified
        raw.assert_not_called()

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
        cmd.caller.tokens = 0
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
        self.assertEqual(cmd.caller.tokens, 20)
        self.assertEqual(target.tokens, 70)

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
        self.assertEqual(target.tokens, 90)        # nothing taken
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
                patch("world.director.crime.report_crime") as report:
            _caught(thief, victim)
        awared = {c.args[0] for c in aware.call_args_list}
        self.assertIn(victim, awared)
        self.assertIn(witness, awared)
        self.assertNotIn(blindfolded, awared)      # can't see = not alerted
        report.assert_called_once()                # the real pipeline, no raw raise


class TheGunStaysInTheBody(EvenniaCommandTest):
    """#3698 against real objects: a deployed integrated weapon in a hand
    whose organs are at 0 HP in place is in the contents but not in the
    hands view. Steal must not lift it, named or blind."""

    def setUp(self):
        super().setUp()
        for char in (self.char1, self.char2):
            char.db.species = "human"
        self.gun = create_object("typeclasses.items.Item", key="forearm shotgun", location=self.char2)
        self.gun.db.integrated = True
        self.chip = create_object("typeclasses.items.Item", key="credit chip", location=self.char2)
        self.char2.held_items = {"left_hand": self.gun}
        state = self.char2.medical_state
        for organ in state.organs.values():
            if getattr(organ, "container", None) == "left_hand":
                organ.current_hp = 0
        self.char2.medical_state = state
        self.char2.save_medical_state()

    def test_the_view_drops_the_hand_but_the_gun_is_not_loose(self):
        from commands.CmdTheft import _stealable_inventory
        self.assertNotIn("left_hand", self.char2.hands)
        self.assertIn(self.gun, self.char2.contents)
        self.assertEqual(_stealable_inventory(self.char2), [self.chip])

    def test_a_named_steal_is_refused(self):
        with patch("commands.CmdTheft.can_contest", return_value=False):
            out = self.call(CmdSteal(), "forearm shotgun from Char2", caller=self.char1)
        self.assertIn("can't get at", out)
        self.assertEqual(self.gun.location, self.char2)

    def test_a_blind_steal_takes_the_chip_never_the_gun(self):
        # choice() pinned to the first loose item: on master's filter that
        # is the gun, every run.
        with patch("commands.CmdTheft.can_contest", return_value=False), \
                patch("commands.CmdTheft.choice", lambda seq: seq[0]):
            self.call(CmdSteal(), "Char2", caller=self.char1)
        self.assertEqual(self.gun.location, self.char2)
        self.assertEqual(self.chip.location, self.char1)

    def test_a_plain_knife_in_the_pulped_hand_is_not_loose_either(self):
        # The store clause on a real body: held_items is a saver mapping,
        # not a dict, and the view has dropped the hand; the knife the slot
        # still names is not loose.
        from collections.abc import Mapping
        from commands.CmdTheft import _stealable_inventory
        knife = create_object("typeclasses.items.Item", key="knife", location=self.char2)
        self.char2.held_items = {"left_hand": knife}
        self.assertTrue(isinstance(self.char2.held_items, Mapping))
        self.assertFalse(isinstance(self.char2.held_items, dict))
        self.assertNotIn("left_hand", self.char2.hands)
        self.assertEqual(_stealable_inventory(self.char2), [self.chip])
        with patch("commands.CmdTheft.can_contest", return_value=False):
            out = self.call(CmdSteal(), "knife from Char2", caller=self.char1)
        self.assertIn("can't get at", out)
        self.assertEqual(knife.location, self.char2)
