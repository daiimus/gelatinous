"""The operate menu's donor picker names its donors with the core matcher
(#3783).

The donors on offer are real objects in the surgeon's inventory, so a
typed name goes through ``Character.search`` scoped to that list, as it
does in every other command. Before, the picker took the first donor
whose key held the typed text anywhere: aliases never matched, "2nd
kidney" never worked, and "idney" found a kidney.

Driven through the real node and processor with real objects.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands import CmdOperate as op
from typeclasses.characters import Character
from typeclasses.items import Organ


class _DonorPickerCase(EvenniaTest):
    character_typeclass = Character

    def donor(self, key: str, organ_name: str = "kidney") -> Organ:
        organ = create_object(Organ, key=key, location=self.char1)
        organ.db.organ_name = organ_name
        return organ

    def pick(self, raw: str):
        """Render the donor node, then answer its prompt with ``raw``."""
        op._node_install_organ(self.char1, "")
        return op._process_install_donor(self.char1, raw)

    def chosen(self):
        return self.char1.ndb._operate_install_donor_item


class TestTheDonorPickerUsesTheCoreMatcher(_DonorPickerCase):

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        self.donor("donor heart", "heart")
        kidney = self.donor("donor kidney")
        kidney.aliases.add("renal graft")
        self.assertEqual(self.pick("renal graft"), "node_install_location")
        self.assertEqual(self.chosen(), kidney)
        self.assertEqual(self.char1.ndb._operate_install_donor,
                         "donor kidney")

    def test_an_ordinal_picks_the_second_of_two_twins(self):
        self.donor("donor kidney")
        second = self.donor("donor kidney")
        self.assertEqual(self.pick("2nd donor kidney"),
                         "node_install_location")
        self.assertEqual(self.chosen(), second)

    def test_a_bare_twin_name_takes_the_first(self):
        first = self.donor("donor kidney")
        self.donor("donor kidney")
        self.assertEqual(self.pick("donor kidney"), "node_install_location")
        self.assertEqual(self.chosen(), first)

    def test_a_fragment_from_the_middle_of_a_word_is_refused(self):
        self.donor("donor kidney")
        self.char1.msg = _Recorder()
        self.assertIsNone(self.pick("idney"))
        self.assertIsNone(self.chosen())
        self.assertIn("No donor matches.", self.char1.msg.text)

    def test_the_start_of_a_word_still_matches(self):
        kidney = self.donor("donor kidney")
        self.assertEqual(self.pick("kid"), "node_install_location")
        self.assertEqual(self.chosen(), kidney)

    def test_me_is_not_a_donor(self):
        """The pool holds no person, so ``me`` finds nothing."""
        self.donor("donor kidney")
        self.char1.msg = _Recorder()
        self.assertIsNone(self.pick("me"))
        self.assertIsNone(self.chosen())
        self.assertIn("No donor matches.", self.char1.msg.text)

    def test_only_the_listed_donors_are_candidates(self):
        """Something else in the pack is not a donor, even by name."""
        create_object("typeclasses.items.Item", key="kidney dish",
                      location=self.char1)
        self.char1.msg = _Recorder()
        self.donor("donor heart", "heart")
        self.assertIsNone(self.pick("kidney"))
        self.assertIsNone(self.chosen())
        self.assertIn("No donor matches.", self.char1.msg.text)

    def test_a_menu_number_still_indexes_the_list(self):
        donors = [self.donor("donor kidney"), self.donor("donor heart",
                                                          "heart")]
        listed = [obj for obj, _label in op._list_donor_organs(self.char1)]
        self.assertEqual(sorted(listed, key=lambda o: o.id),
                         sorted(donors, key=lambda o: o.id))
        self.assertEqual(self.pick("2"), "node_install_location")
        self.assertEqual(self.chosen(), listed[1])

    def test_a_number_past_the_list_is_out_of_range(self):
        self.donor("donor kidney")
        self.char1.msg = _Recorder()
        self.assertIsNone(self.pick("5"))
        self.assertIn("Out of range.", self.char1.msg.text)


class _Recorder:
    """Stands in for ``msg`` so a test can read what the surgeon saw."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, text=None, **kwargs) -> None:
        self.lines.append(str(text))

    @property
    def text(self) -> str:
        return "\n".join(self.lines)
