"""An abdomen hit meets one side plate in full, and the armour screens say so (#3366).

Two side slots share the abdomen. Combat used to stack BOTH side plates at
half rating as sequential layers, handing the wearer a whole plate against
every abdomen hit while the halving comment claimed the opposite; the
display re-derived the slot map by hand and halved a third way, so the
same screen showed a 9 beside details adding to 8. Owner ruling
2026-09-20: the hit lands on one side or the other, even odds, meets that
plate in full plus the carrier, and an empty side means carrier only. The
displays read the carrier's declared coverage and list the layers a hit
can meet, with no total anywhere.
"""
from unittest.mock import patch

from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdArmor import CmdArmor, CmdSlot
from typeclasses import armor_mixin
from world.prototypes import CERAMIC_PLATES, PLATE_CARRIER, STANDARD_PLATE


def _ratings(layers):
    return [(l["item"].key, l["armor_rating"]) for l in layers]


class AbdomenHitMeetsOneSidePlateTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.carrier = spawn(PLATE_CARRIER)[0]
        self.left = spawn(STANDARD_PLATE)[0]
        self.right = spawn(CERAMIC_PLATES)[0]          # rating 10, so the sides are told apart
        for o in (self.carrier, self.left, self.right):
            o.move_to(self.char1, quiet=True)
        self.char1.wear_item(self.carrier)
        self.char1.wield_item(self.left, hand="right")
        self.call(CmdSlot(), "standard plate in plate carrier left side")
        self.char1.wield_item(self.right, hand="right")
        self.call(CmdSlot(), "trauma plate in plate carrier right side")
        assert self.carrier.installed_plates.get("left_side") is self.left
        assert self.carrier.installed_plates.get("right_side") is self.right

    # --- combat ------------------------------------------------------------

    def test_control_a_chest_hit_meets_the_front_plate_in_full_plus_the_carrier(self):
        front = spawn(STANDARD_PLATE)[0]; front.move_to(self.char1, quiet=True)
        self.char1.wield_item(front, hand="right")
        self.call(CmdSlot(), "standard plate in plate carrier front")
        layers = self.char1._expand_plate_carrier_layers(self.carrier, "chest")
        self.assertEqual(sorted(_ratings(layers)), sorted([("plate carrier", 2), ("standard plate", 7)]))

    def test_an_abdomen_hit_meets_exactly_one_side_plate_in_full(self):
        for _ in range(12):
            layers = self.char1._expand_plate_carrier_layers(self.carrier, "abdomen")
            plates = [r for r in _ratings(layers) if r[0] != "plate carrier"]
            self.assertEqual(len(plates), 1, "an abdomen hit met %r plates" % plates)
            self.assertIn(plates[0], [("standard plate", 7), ("trauma plate", 10)], "a plate was halved: %r" % plates)
            self.assertIn(("plate carrier", 2), _ratings(layers))

    def test_the_side_is_rolled(self):
        with patch.object(armor_mixin, "choice", lambda slots: "left_side"):
            left = _ratings(self.char1._expand_plate_carrier_layers(self.carrier, "abdomen"))
        with patch.object(armor_mixin, "choice", lambda slots: "right_side"):
            right = _ratings(self.char1._expand_plate_carrier_layers(self.carrier, "abdomen"))
        self.assertIn(("standard plate", 7), left); self.assertNotIn(("trauma plate", 10), left)
        self.assertIn(("trauma plate", 10), right); self.assertNotIn(("standard plate", 7), right)

    def test_an_empty_side_means_carrier_only(self):
        self.carrier.installed_plates = {"left_side": self.left, "right_side": None}
        with patch.object(armor_mixin, "choice", lambda slots: "right_side"):
            layers = self.char1._expand_plate_carrier_layers(self.carrier, "abdomen")
        self.assertEqual(_ratings(layers), [("plate carrier", 2)])

    # --- display ------------------------------------------------------------

    def test_the_display_reads_the_declared_coverage(self):
        # imported here so the combat tests above still run on a tree
        # without the display helpers and fail for the combat reason
        from commands.CmdArmor import plate_layers_at
        layers = plate_layers_at(self.carrier, "abdomen")
        self.assertEqual([s for s, _ in layers], ["left_side", "right_side"])
        self.assertEqual(plate_layers_at(self.carrier, "chest"), [("front", None)])
        self.carrier.plate_slot_coverage = {"front": ["abdomen"], "back": ["back"], "left_side": ["chest"], "right_side": ["chest"]}
        self.assertEqual([s for s, _ in plate_layers_at(self.carrier, "abdomen")], ["front"],
                         "the display followed a hand-typed map, not the carrier's")

    def test_the_coverage_screen_lists_the_layers_and_never_sums(self):
        from commands.CmdArmor import describe_plate_layers, plate_layers_at
        self.assertEqual(describe_plate_layers(plate_layers_at(self.carrier, "abdomen")),
                         "one of left side: standard plate (7) | right side: trauma plate (10)")
        out = self.call(CmdArmor(), "coverage") or ""
        self.assertIn("standard plate (7)", out)
        self.assertIn("trauma plate (10)", out)
        for wrong in ("(3)", "(5)", "9/10", "10/10", "12/10", "19/10"):
            self.assertNotIn(wrong, out, "a summed or halved number survived: %r" % wrong)

    def test_the_armor_table_shows_the_carrier_rating_and_a_plate_count(self):
        out = self.call(CmdArmor(), "") or ""
        self.assertIn("2/10 (2 plates)", out, out)
        self.assertNotIn("2-", out, "the old best-location range survived")

    def test_look_at_the_carrier_prints_no_protection_total(self):
        from evennia.commands.default.general import CmdLook
        out = self.call(CmdLook(), "plate carrier") or ""
        self.assertIn("Base Protection", out, out)
        self.assertNotIn("Total Protection", out, out)

    def test_slot_prints_no_protection_total(self):
        front = spawn(STANDARD_PLATE)[0]; front.move_to(self.char1, quiet=True)
        self.char1.wield_item(front, hand="right")
        out = self.call(CmdSlot(), "standard plate in plate carrier front") or ""
        self.assertIn("You install", out)
        self.assertNotIn("total protection", out.lower())
