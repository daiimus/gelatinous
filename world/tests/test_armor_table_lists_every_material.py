"""The armour table lists every material, and every material has a row (#3440).

`armor effectiveness` built its rows from a literal list of four names,
so `synthetic` -- the row of the tactical set and the plate carrier, the
second most common armour material in the live world -- never printed.
The table now iterates the matrix, so a new material cannot go missing.

The lightweight plate declared `armor_type` "composite", which was not a
matrix key at all, so mitigation fell it silently back to the `generic`
row. The matrix now carries a `composite` row: first-cut values approved
by the owner 2026-09-15 as a placeholder for the balance pass.
"""
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdArmor import CmdArmor
from world.combat.constants import ARMOR_EFFECTIVENESS_MATRIX


class TestTheTableListsEveryMaterial(EvenniaCommandTest):
    def _table(self):
        return self.call(CmdArmor(), "effectiveness")

    def test_synthetic_has_a_row(self):
        self.assertIn("Synthetic", self._table())

    def test_composite_has_a_row(self):
        self.assertIn("Composite", self._table())

    def test_generic_stays_hidden(self):
        self.assertNotIn("Generic", self._table())

    def test_every_matrix_row_but_generic_prints(self):
        out = self._table()
        for key in ARMOR_EFFECTIVENESS_MATRIX:
            if key != "generic":
                self.assertIn(key.title(), out)


class TestEveryArmourPrototypeMitigatesOnARealRow(EvenniaCommandTest):
    def test_every_declared_armor_type_is_a_matrix_key(self):
        from world import prototypes
        declared = {}
        for name in dir(prototypes):
            proto = getattr(prototypes, name)
            if isinstance(proto, dict):
                for attr in proto.get("attrs", ()):
                    if attr and attr[0] == "armor_type":
                        declared[name] = attr[1]
        self.assertTrue(declared, "no armour prototypes found")
        missing = {n: t for n, t in declared.items()
                   if t not in ARMOR_EFFECTIVENESS_MATRIX}
        self.assertEqual(missing, {})

    def test_the_lightweight_plate_no_longer_falls_back_to_generic(self):
        """The mitigation helper lives on the WEARER (ArmorMixin on
        Character); the plate only carries the type and rating."""
        plate = spawn("LIGHTWEIGHT_PLATE")[0]
        try:
            rating = plate.db.armor_rating
            wearer = self.char1
            got = wearer._get_armor_effectiveness(plate.db.armor_type, "bullet", rating)
            self.assertEqual(
                got, wearer._get_armor_effectiveness("composite", "bullet", rating))
            self.assertNotEqual(
                got, wearer._get_armor_effectiveness("generic", "bullet", rating))
        finally:
            plate.delete()
