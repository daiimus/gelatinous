""""repair plate carrier full" means full (#2521).

`repair` split its argument on whitespace and looked for the modifier at
**`args[1]` only**. Every piece of armour the game ships has a
multi-word name — "plate carrier", "ceramic trauma plates", "black
leather combat boots", "tactical jumpsuit" — so `args[1]` was the second
word of the armour *name*, never the modifier.

Two silent degradations:

* `repair plate carrier full` → `args[1] == "carrier"` → `repair_type`
  stayed `"standard"`. **25% restoration instead of 60%**, and the
  success line said nothing about `full` having been dropped.
* `repair plate carrier with sewing kit` → `tool_name` never set, so the
  tool bonus of up to **+12** was never applied — and on failure the
  player was told *"Perhaps you need better tools or more technical
  knowledge."* **while holding the correct tool.** That last one is the
  sharp end: the game blames the player's tool at the moment it is
  refusing to look at it.

`armor_name = args[0]` took a single token too, so the lookup was
partial-matching `"plate"` while the rest of the phrase was being mined
for a modifier that was not there.

Parsed from the end now. Both markers are **trailing**, which is what
keeps a "field jacket" named and a "vest with straps" findable — the
tool is whatever follows the *last* "with".

The docstring advertised `repair <armor> [with <tool>]` and `repair
<armor> field/full` with no single-word restriction, so this is the
behaviour the command already claimed.
"""
from evennia.utils.test_resources import EvenniaTest


def parse(raw):
    from commands.CmdArmor import CmdArmorRepair
    return CmdArmorRepair.parse_repair_args(raw.split())


class TestTheShippedArmourNames(EvenniaTest):
    """Every one of these is multi-word, which is the whole defect."""

    def test_a_bare_two_word_name(self):
        self.assertEqual(parse("plate carrier"),
                         ("plate carrier", "standard", None))

    def test_full_on_a_two_word_name(self):
        self.assertEqual(parse("plate carrier full"),
                         ("plate carrier", "full", None))

    def test_field_on_a_two_word_name(self):
        self.assertEqual(parse("plate carrier field"),
                         ("plate carrier", "field", None))

    def test_a_tool_on_a_two_word_name(self):
        self.assertEqual(parse("plate carrier with sewing kit"),
                         ("plate carrier", "standard", "sewing kit"))

    def test_a_three_word_name(self):
        self.assertEqual(parse("ceramic trauma plates full"),
                         ("ceramic trauma plates", "full", None))

    def test_a_four_word_name_with_a_tool(self):
        self.assertEqual(
            parse("black leather combat boots with repair kit"),
            ("black leather combat boots", "standard", "repair kit"))

    def test_a_one_word_name_still_works(self):
        self.assertEqual(parse("jumpsuit full"),
                         ("jumpsuit", "full", None))


class TestTheMarkersAreTrailing(EvenniaTest):
    """Why trailing: the words appear inside real armour names."""

    def test_a_field_jacket_keeps_its_name(self):
        self.assertEqual(parse("field jacket"),
                         ("field jacket", "standard", None))

    def test_a_field_jacket_can_still_be_fully_repaired(self):
        self.assertEqual(parse("field jacket full"),
                         ("field jacket", "full", None))

    def test_a_field_jacket_can_have_a_field_repair(self):
        self.assertEqual(parse("field jacket field"),
                         ("field jacket", "field", None))

    def test_a_name_containing_with_survives(self):
        self.assertEqual(parse("vest with straps with sewing kit"),
                         ("vest with straps", "standard", "sewing kit"))

    def test_a_trailing_with_and_nothing_after_it_is_not_a_tool(self):
        self.assertEqual(parse("plate carrier with"),
                         ("plate carrier with", "standard", None))


class TestNothingIsLeftEmpty(EvenniaTest):
    def test_a_bare_modifier_yields_no_name(self):
        """`repair full` should be refused, not repair something."""
        self.assertEqual(parse("full")[0], "")

    def test_a_bare_tool_yields_no_name(self):
        self.assertEqual(parse("with sewing kit")[0], "")

    def test_empty_input(self):
        self.assertEqual(parse(""), ("", "standard", None))


class TestTheOldParseReallyDegraded(EvenniaTest):
    """Reproduces the pre-fix arithmetic so the defect is demonstrated,
    not merely asserted."""

    @staticmethod
    def old_parse(raw):
        args = raw.split()
        armor_name = args[0] if args else ""
        repair_type, tool_name = "standard", None
        if len(args) > 1:
            if args[1].lower() == "field":
                repair_type = "field"
            elif args[1].lower() == "full":
                repair_type = "full"
            elif args[1].lower() == "with" and len(args) > 2:
                tool_name = " ".join(args[2:])
        return armor_name, repair_type, tool_name

    def test_full_was_dropped(self):
        self.assertEqual(self.old_parse("plate carrier full")[1], "standard")

    def test_the_tool_was_dropped(self):
        self.assertIsNone(
            self.old_parse("plate carrier with sewing kit")[2])

    def test_only_the_first_token_was_looked_up(self):
        self.assertEqual(self.old_parse("plate carrier full")[0], "plate")

    def test_a_single_word_name_did_work(self):
        """Which is why this survived: it works for names nobody uses."""
        self.assertEqual(self.old_parse("jumpsuit full"),
                         ("jumpsuit", "full", None))


class TestTheOldShapeIsGone(EvenniaTest):
    """A source pin, so the unfixed tree produces a clean FAILURE rather
    than only "the new helper is missing" import errors."""

    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "commands" / "CmdArmor.py").read_text(errors="ignore")

    def test_the_modifier_is_no_longer_read_at_args_1(self):
        body = self._source()
        self.assertNotIn('args[1].lower() == "field"', body)
        self.assertNotIn('args[1].lower() == "full"', body)

    def test_the_name_is_no_longer_just_the_first_token(self):
        self.assertNotIn("armor_name = args[0]", self._source())

    def test_the_parse_is_reachable_on_its_own(self):
        """Extracted so it can be tested without running a repair."""
        self.assertIn("def parse_repair_args(args):", self._source())
