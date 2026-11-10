"""armor, repair and unslot resolve names with the core matcher (#3783).

Each of these verbs used to compare the typed text to ``.key`` itself: a
substring anywhere in the key, plus (for armor and repair) an alias only
when typed in full. So an alias like "wristguard" worked only whole,
"2nd bracer" never worked, and "racer" found a "steel bracer". They now
hand the pool they already build (worn armour, armour you have, repair
tools, plates in worn or carried carriers, your carriers, the plates of
one carrier) to ``Character.search(candidates=...)``.

For every lookup these tests pin: an alias that is not a substring of the
key resolves; an ordinal picks the second of two twins; a fragment from
the middle of a word is refused with the command's own refusal.

Real objects, real commands.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdArmor import CmdArmor, CmdArmorRepair, CmdUnslot

ITEM = "typeclasses.items.Item"
SLOTS = ["front", "back", "left_side", "right_side"]


def _bracer(holder, desc, coverage, durability=20):
    """A worn-able steel bracer whose alias shares no text with its key."""
    return create_object(
        ITEM, key="steel bracer", location=holder, aliases=["wristguard"],
        attributes=[
            ("desc", desc),
            ("coverage", coverage),
            ("worn_desc", "A steel bracer"),
            ("layer", 2),
            ("armor_rating", 3),
            ("base_armor_rating", 3),
            ("armor_type", "steel"),
            ("armor_durability", durability),
            ("max_armor_durability", 20),
        ],
    )


def _carrier(holder):
    return create_object(
        ITEM, key="plate carrier", location=holder, aliases=["rig"],
        attributes=[
            ("coverage", ["chest", "back", "abdomen"]),
            ("worn_desc", "A plate carrier"),
            ("layer", 2),
            ("armor_rating", 2),
            ("armor_durability", 40),
            ("max_armor_durability", 40),
            ("is_plate_carrier", True),
            ("plate_slots", list(SLOTS)),
            ("installed_plates", {}),
        ],
    )


def _plate(carrier, slot):
    """A standard plate installed in *slot* of *carrier*."""
    plate = create_object(
        ITEM, key="standard plate", location=carrier,
        aliases=["ballistic insert"],
        attributes=[("is_armor_plate", True), ("armor_rating", 7)],
    )
    installed = dict(carrier.installed_plates or {})
    installed[slot] = plate
    carrier.installed_plates = installed
    return plate


class ArmorItemDetailsTest(EvenniaCommandTest):
    """``armor <item>``: the worn armour is the pool."""

    def setUp(self):
        super().setUp()
        self.left = _bracer(self.char1, "the first bracer", ["left_arm"])
        self.right = _bracer(self.char1, "the second bracer", ["right_arm"])
        for bracer in (self.left, self.right):
            worn, msg = self.char1.wear_item(bracer)
            assert worn, msg

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        out = self.call(CmdArmor(), "wrist")
        self.assertIn("Steel Bracer", out)
        self.assertNotIn("not wearing any armor", out)

    def test_an_ordinal_picks_the_second_twin(self):
        out = self.call(CmdArmor(), "2nd steel bracer")
        self.assertIn("the second bracer", out)
        self.assertNotIn("the first bracer", out)

    def test_a_mid_word_fragment_is_refused(self):
        out = self.call(CmdArmor(), "racer")
        self.assertIn("You are not wearing any armor matching 'racer'.", out)

    def test_me_is_not_armour(self):
        out = self.call(CmdArmor(), "me")
        self.assertIn("You are not wearing any armor matching 'me'.", out)


class RepairFindsArmorTest(EvenniaCommandTest):
    """``repair <armor>``: armour you have; a worn piece wins a tie."""

    def setUp(self):
        super().setUp()
        # Carried first, so it has the lower id; worn second.
        self.carried = _bracer(self.char1, "carried", ["left_arm"], 10)
        self.worn = _bracer(self.char1, "worn", ["right_arm"], 10)
        worn, msg = self.char1.wear_item(self.worn)
        assert worn, msg

    def _repaired(self, args):
        """Run repair; return (output, the armour the attempt got or None)."""
        with patch.object(CmdArmorRepair, "_attempt_repair") as attempt:
            out = self.call(CmdArmorRepair(), args)
        if not attempt.called:
            return out, None
        return out, attempt.call_args[0][1]

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        _, armor = self._repaired("wrist")
        self.assertIs(armor, self.worn)

    def test_a_worn_piece_wins_over_a_carried_twin(self):
        _, armor = self._repaired("steel bracer")
        self.assertIs(armor, self.worn)

    def test_an_ordinal_picks_the_second_twin(self):
        # Ordinals count all the armour you have, by id: the worn one is
        # the second, the carried one the first.
        _, armor = self._repaired("1st steel bracer")
        self.assertIs(armor, self.carried)
        _, armor = self._repaired("2nd steel bracer")
        self.assertIs(armor, self.worn)

    def test_a_mid_word_fragment_is_refused(self):
        out, armor = self._repaired("racer")
        self.assertIsNone(armor)
        self.assertIn("You don't have any armor matching 'racer'.", out)


class RepairFindsToolTest(EvenniaCommandTest):
    """``repair <armor> with <tool>``: repair tools you carry."""

    def setUp(self):
        super().setUp()
        self.bracer = _bracer(self.char1, "bracer", ["left_arm"], 10)
        self.kits = [
            create_object(
                ITEM, key="sewing kit", location=self.char1,
                aliases=["needlework"],
                attributes=[("repair_tool_type", "sewing_kit")],
            )
            for _ in range(2)
        ]

    def _tool(self, args):
        with patch.object(CmdArmorRepair, "_attempt_repair") as attempt:
            out = self.call(CmdArmorRepair(), args)
        if not attempt.called:
            return out, None
        return out, attempt.call_args[0][3]

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        _, tool = self._tool("steel bracer with needle")
        self.assertIn(tool, self.kits)

    def test_an_ordinal_picks_the_second_twin(self):
        _, tool = self._tool("steel bracer with 2nd sewing kit")
        self.assertIs(tool, self.kits[1])

    def test_a_mid_word_fragment_is_refused(self):
        out, tool = self._tool("steel bracer with ewing kit")
        self.assertIsNone(tool)
        self.assertIn("You don't have a repair tool matching 'ewing kit'.", out)


class UnslotFromWornCarrierTest(EvenniaCommandTest):
    """Bare ``unslot <plate>``: plates in the carriers you wear."""

    def setUp(self):
        super().setUp()
        self.carrier = _carrier(self.char1)
        worn, msg = self.char1.wear_item(self.carrier)
        assert worn, msg
        self.front = _plate(self.carrier, "front")
        self.back = _plate(self.carrier, "back")

    def _out(self, plate):
        return plate.location == self.char1 and plate in self.char1.hands.values()

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        self.call(CmdUnslot(), "ballistic insert")
        self.assertTrue(self._out(self.front) or self._out(self.back))

    def test_an_ordinal_picks_the_second_twin(self):
        self.call(CmdUnslot(), "2nd standard plate")
        self.assertTrue(self._out(self.back))
        self.assertIs(self.carrier.installed_plates.get("front"), self.front)

    def test_a_mid_word_fragment_is_refused(self):
        out = self.call(CmdUnslot(), "andard plate")
        self.assertIn(
            "You don't have any plate matching 'andard plate' installed in"
            " the carriers you're wearing.", out,
        )
        self.assertIs(self.carrier.installed_plates.get("front"), self.front)
        self.assertIs(self.carrier.installed_plates.get("back"), self.back)


class UnslotHintsAtCarriedCarrierTest(EvenniaCommandTest):
    """Bare ``unslot <plate>`` that finds the plate in a carried carrier
    names the ``from`` form and leaves the plate where it is."""

    def setUp(self):
        super().setUp()
        self.carrier = _carrier(self.char1)
        self.front = _plate(self.carrier, "front")
        self.back = _plate(self.carrier, "back")

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        out = self.call(CmdUnslot(), "ballistic insert")
        self.assertIn("Use: unslot standard plate from plate carrier", out)
        self.assertEqual(self.front.location, self.carrier)

    def test_an_ordinal_picks_the_second_twin(self):
        out = self.call(CmdUnslot(), "2nd standard plate")
        self.assertIn("Use: unslot standard plate from plate carrier", out)
        self.assertEqual(self.back.location, self.carrier)

    def test_a_mid_word_fragment_is_refused(self):
        out = self.call(CmdUnslot(), "andard plate")
        self.assertNotIn("Use: unslot", out)
        self.assertIn("You are not wearing any plate carriers.", out)


class UnslotFromNamedCarrierTest(EvenniaCommandTest):
    """``unslot <plate|slot> from <carrier>``: your carriers, then the
    plates of the one named."""

    def setUp(self):
        super().setUp()
        self.first = _carrier(self.char1)
        self.second = _carrier(self.char1)
        self.first_front = _plate(self.first, "front")
        self.second_front = _plate(self.second, "front")
        self.second_back = _plate(self.second, "back")

    # --- the carrier ------------------------------------------------------

    def test_a_carrier_alias_that_is_not_in_the_key_resolves(self):
        self.call(CmdUnslot(), "front from rig")
        self.assertIsNone(self.first.installed_plates.get("front"))
        self.assertIn(self.first_front, self.char1.hands.values())

    def test_an_ordinal_picks_the_second_carrier(self):
        self.call(CmdUnslot(), "front from 2nd plate carrier")
        self.assertIsNone(self.second.installed_plates.get("front"))
        self.assertIs(self.first.installed_plates.get("front"), self.first_front)

    def test_a_mid_word_carrier_fragment_is_refused(self):
        out = self.call(CmdUnslot(), "front from arrier")
        self.assertIn("You don't have a plate carrier matching 'arrier'.", out)
        self.assertIs(self.first.installed_plates.get("front"), self.first_front)

    def test_a_held_plate_does_not_shadow_the_carrier(self):
        # Carriers are the pool, so a plate in hand is not a candidate.
        loose = create_object(
            ITEM, key="plate", location=self.char1,
            attributes=[("is_armor_plate", True), ("armor_rating", 7)],
        )
        self.char1.wield_item(loose, hand="left")
        self.call(CmdUnslot(), "front from plate")
        self.assertIsNone(self.first.installed_plates.get("front"))

    # --- the plate in that carrier ----------------------------------------

    def test_a_plate_alias_that_is_not_in_the_key_resolves(self):
        self.call(CmdUnslot(), "ballistic insert from plate carrier")
        self.assertIsNone(self.first.installed_plates.get("front"))
        self.assertIn(self.first_front, self.char1.hands.values())

    def test_an_ordinal_picks_the_second_plate(self):
        self.call(CmdUnslot(), "2nd standard plate from 2nd plate carrier")
        self.assertIsNone(self.second.installed_plates.get("back"))
        self.assertIs(self.second.installed_plates.get("front"), self.second_front)
        self.assertIn(self.second_back, self.char1.hands.values())

    def test_a_mid_word_plate_fragment_is_refused(self):
        out = self.call(CmdUnslot(), "andard plate from plate carrier")
        self.assertIn(
            "No plate or slot matching 'andard plate' found in plate carrier.",
            out,
        )
        self.assertIs(self.first.installed_plates.get("front"), self.first_front)
