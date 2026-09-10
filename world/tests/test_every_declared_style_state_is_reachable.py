"""Every style state a garment declares can be reached by a command
(#2742).

The style system is data-driven — `can_style_property_to` just checks
membership in the garment's own `style_configs` — and the commands were
not. `CmdRollUp` and `CmdZip` named the four canonical states
(`normal`, `rolled`, `zipped`, `unzipped`) directly, so four live
garments declared states nothing could ever reach:

    corporate blazer      closure     buttoned / open
    white lab coat        closure     buttoned / open
    corporate necktie     adjustable  loosened
    tox-sealed slicker    adjustable  hood_down / hood_up

The slicker is the one that matters: `hood_up` carries the garment's
ONLY head coverage, so its hood could never be raised and the head was
permanently bare.

The commands now ask the GARMENT what it can be adjusted to, and take
their prose from the STATE — "you roll up the tox-sealed slicker" is
the wrong sentence for raising a hood.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdClothing import CmdRollUp, CmdZip
from world.prototypes import CORPO_BLAZER, LAB_COAT, NECKTIE, SEALED_SLICKER

CANONICAL = {"normal", "rolled", "zipped", "unzipped"}


def _wear(who, key, prop, states, start):
    item = create_object("typeclasses.items.Item", key=key, location=who)
    item.attributes.add("coverage", ["chest"])
    item.attributes.add("worn_desc", f"{key} worn")
    item.attributes.add("style_configs", {prop: states})
    item.attributes.add("style_properties", {prop: start})
    who.wear_item(item)
    return item


class TestTheProblemIsReal(EvenniaCommandTest):

    def test_four_live_prototypes_declare_non_canonical_states(self):
        """Control: if the prototypes had been renamed instead, this
        whole file would be guarding nothing."""
        found = {}
        for name, proto in (("CORPO_BLAZER", CORPO_BLAZER),
                            ("LAB_COAT", LAB_COAT),
                            ("NECKTIE", NECKTIE),
                            ("SEALED_SLICKER", SEALED_SLICKER)):
            attrs = {a[0]: a[1] for a in proto.get("attrs", ())}
            configs = attrs.get("style_configs") or {}
            for prop, states in configs.items():
                odd = set(states) - CANONICAL
                if odd:
                    found[name] = sorted(odd)
        self.assertTrue(found, "no prototype declares a non-canonical state")

    def test_the_slicker_hood_carries_the_head_coverage(self):
        """Why this one is not merely cosmetic."""
        attrs = {a[0]: a[1] for a in SEALED_SLICKER.get("attrs", ())}
        hood_up = attrs["style_configs"]["adjustable"]["hood_up"]
        # `coverage_mod` entries are signed — "+head" ADDS the head.
        self.assertIn("+head", hood_up.get("coverage_mod") or [])


class TestTheHoodGoesUp(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.slicker = _wear(
            self.char1, "tox-sealed slicker", "adjustable",
            {"hood_down": {"coverage_mod": [], "desc_mod": ""},
             "hood_up": {"coverage_mod": ["+head"],
                         "desc_mod": " hood up"}},
            "hood_down")

    def test_rollup_raises_it(self):
        self.call(CmdRollUp(), "slicker")
        self.assertEqual(
            self.slicker.get_style_property("adjustable"), "hood_up")

    def test_the_prose_is_about_a_hood_not_a_sleeve(self):
        out = self.call(CmdRollUp(), "slicker")
        self.assertIn("hood", out.lower())
        self.assertNotIn("roll up", out.lower())

    def test_unroll_lowers_it_again(self):
        self.call(CmdRollUp(), "slicker")
        self.call(CmdRollUp(), "slicker", cmdstring="unroll")
        self.assertEqual(
            self.slicker.get_style_property("adjustable"), "hood_down")

    def test_raising_it_twice_says_so(self):
        self.call(CmdRollUp(), "slicker")
        out = self.call(CmdRollUp(), "slicker")
        self.assertIn("already", out.lower())


class TestTheBlazerButtons(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.blazer = _wear(
            self.char1, "corporate blazer", "closure",
            {"buttoned": {"coverage_mod": [], "desc_mod": ""},
             "open": {"coverage_mod": [], "desc_mod": " open"}},
            "open")

    def test_button_closes_it(self):
        self.call(CmdZip(), "blazer", cmdstring="button")
        self.assertEqual(
            self.blazer.get_style_property("closure"), "buttoned")

    def test_unbutton_opens_it(self):
        """Set the start state directly rather than buttoning first.
        Driving `button` first passes against the unfixed tree too: the
        blazer stays `open` because neither command can move it, and
        then "it is open" is trivially true."""
        self.blazer.set_style_property("closure", "buttoned")
        self.call(CmdZip(), "blazer", cmdstring="unbutton")
        self.assertEqual(self.blazer.get_style_property("closure"), "open")


class TestTheNecktieLoosens(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.tie = _wear(
            self.char1, "corporate necktie", "adjustable",
            {"normal": {"coverage_mod": [], "desc_mod": ""},
             "loosened": {"coverage_mod": [], "desc_mod": " loosened"}},
            "normal")

    def test_rollup_loosens_it(self):
        self.call(CmdRollUp(), "necktie")
        self.assertEqual(
            self.tie.get_style_property("adjustable"), "loosened")

    def test_you_straighten_a_tie_rather_than_unrolling_it(self):
        self.call(CmdRollUp(), "necktie")
        out = self.call(CmdRollUp(), "necktie", cmdstring="unroll")
        self.assertIn("straighten", out.lower())
        self.assertEqual(self.tie.get_style_property("adjustable"), "normal")


class TestTheCanonicalStatesStillWork(EvenniaCommandTest):
    """Control: the four states that always worked must keep working,
    and keep their own prose."""

    def setUp(self):
        super().setUp()
        self.shirt = _wear(
            self.char1, "flannel shirt", "adjustable",
            {"normal": {"coverage_mod": [], "desc_mod": ""},
             "rolled": {"coverage_mod": [], "desc_mod": " rolled"}},
            "normal")
        self.jacket = _wear(
            self.char1, "windbreaker", "closure",
            {"zipped": {"coverage_mod": [], "desc_mod": ""},
             "unzipped": {"coverage_mod": [], "desc_mod": " open"}},
            "unzipped")

    def test_a_sleeve_still_rolls(self):
        out = self.call(CmdRollUp(), "flannel")
        self.assertIn("roll up", out.lower())
        self.assertEqual(
            self.shirt.get_style_property("adjustable"), "rolled")

    def test_and_still_unrolls(self):
        self.call(CmdRollUp(), "flannel")
        out = self.call(CmdRollUp(), "flannel", cmdstring="unroll")
        self.assertIn("unroll", out.lower())

    def test_a_zip_still_zips(self):
        out = self.call(CmdZip(), "windbreaker")
        self.assertIn("zip up", out.lower())
        self.assertEqual(self.jacket.get_style_property("closure"), "zipped")

    def test_a_garment_with_no_closure_still_says_so(self):
        out = self.call(CmdZip(), "flannel")
        self.assertIn("zipper", out.lower())
