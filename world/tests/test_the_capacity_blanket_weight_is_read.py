"""`organ_contribution` is a live dial, not decoration (#2768).

It is declared 19 times across all four species, inside capacity blocks,
next to `fatal_threshold` which IS live:

    "breathing": {
        "organs": ["left_lung", "right_lung"],
        "fatal_threshold": 0.0,
        "organ_contribution": 0.5,
        ...
    }

and `_resolve_capacity_contribution` never read it. Its two lookups
build `f"{organ_name}_contribution"` and `f"{bone_type}_contribution"`,
so the literal string "organ_contribution" would only ever be
constructed for an organ actually named "organ".

It was invisible because every declared value happens to equal what the
string fallback yields anyway -- measured across all 19 declarations and
the 35 organ/capacity pairs under them, ZERO disagree. So this wires the
key WITHOUT changing any current number.

That coincidence is the reason to fix it rather than shrug: the dial
would have been silently dead at the moment someone first turned it, and
the balance pass is exactly when someone will. The fallback it shadows
is a coarse four-value string (total/major/moderate/minor =
1.0/0.5/0.25/0.05) with no way to express 0.4 -- which is plausibly why
the float key was written in the first place.

PRECEDENCE MATTERS and is pinned below: the blanket weight is the
capacity's default for its organs, not an override of the ones named
individually. `digestion` in the human table declares
`liver_contribution: 1.0` and `stomach_contribution: 0.5` -- a blanket
that outranked those would silently flatten a deliberate asymmetry.
"""
from evennia.utils.test_resources import EvenniaTest


class _Organ:
    def __init__(self, contribution="minor", data=None):
        self.contribution = contribution
        self.data = data or {}


class TestBlanketWeight(EvenniaTest):

    def _resolve(self, capacity_data, organ=None, organ_name="left_lung",
                 capacity_name="breathing"):
        state = self.char1.medical_state
        return state._resolve_capacity_contribution(
            organ_name, organ or _Organ(), capacity_data, capacity_name)

    def test_the_string_fallback_still_works(self):
        """Control: with no keys at all, the organ's own coarse string
        is still what answers."""
        got = self._resolve({}, organ=_Organ("major"))
        self.assertEqual(got, 0.5)

    def test_the_blanket_weight_is_used(self):
        got = self._resolve({"organ_contribution": 0.4}, organ=_Organ("minor"))
        self.assertEqual(got, 0.4)

    def test_a_value_the_string_scale_cannot_express(self):
        """The reason the float key exists: 0.4 is not in the coarse
        four-value scale at all."""
        got = self._resolve({"organ_contribution": 0.37}, organ=_Organ("total"))
        self.assertAlmostEqual(got, 0.37)

    def test_an_organ_specific_key_still_wins(self):
        """`digestion` declares liver 1.0 and stomach 0.5; a blanket that
        outranked them would flatten a deliberate asymmetry."""
        got = self._resolve(
            {"organ_contribution": 0.4, "left_lung_contribution": 0.9},
            organ=_Organ("minor"))
        self.assertEqual(got, 0.9)

    def test_a_bone_type_key_still_wins(self):
        got = self._resolve(
            {"organ_contribution": 0.4, "femur_contribution": 0.8},
            organ=_Organ("minor"), organ_name="left_femur",
            capacity_name="moving")
        self.assertEqual(got, 0.8)


class TestTodaysTablesAreUnchanged(EvenniaTest):
    """The safety argument, asserted rather than asserted-about.

    Wiring a dial is only safe because no declared value differs from
    what the fallback already produced. If a future edit turns one of
    them, this test SHOULD be updated -- it exists to make that a
    deliberate act rather than a silent one.
    """

    def test_every_declaration_currently_matches_the_fallback(self):
        from world.anatomy.species import SPECIES_DEFINITIONS
        from world.medical.constants import CONTRIBUTION_VALUES

        def find(node, path=()):
            if isinstance(node, dict):
                if "organ_contribution" in node:
                    yield path, node
                for k, v in node.items():
                    yield from find(v, path + (k,))

        decls = list(find(SPECIES_DEFINITIONS))
        self.assertTrue(decls, "walked the species table and found none")

        pairs = 0
        for path, cap in decls:
            species, cap_name = path[0], path[-1]
            spec = SPECIES_DEFINITIONS.get(species, {})
            organs = next((spec[k] for k in ("organs", "organ_definitions",
                                             "anatomy")
                           if isinstance(spec.get(k), dict)), {})
            declared = float(cap["organ_contribution"])
            for organ_name in cap.get("organs", []):
                if f"{organ_name}_contribution" in cap:
                    continue          # a specific key, which still wins
                pairs += 1
                data = organs.get(organ_name, {}) or {}
                key = data.get(f"{cap_name}_contribution",
                               data.get("contribution", "minor"))
                eff = (CONTRIBUTION_VALUES.get(key, 0.05)
                       if isinstance(key, str) else float(key))
                self.assertAlmostEqual(
                    eff, declared,
                    msg=f"{species}/{cap_name}/{organ_name}: declared "
                        f"{declared}, fallback {eff} — wiring the dial "
                        f"CHANGES this number")
        self.assertTrue(pairs, "no organ/capacity pairs were checked")
