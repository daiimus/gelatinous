"""Chargen's frames close, and the name budget is stated where it is
enforced (#3438, #3436).

**Frames.** Four consecutive chargen screens -- height, build, hair
colour, hair style -- carried one extra space in their title row, so
the closing bar sat one column right of the corners above and below
it, on the house 66-column frame NEW_PLAYER_EXPERIENCE_SPEC §3 fixes.
Rendered through the real nodes, colour stripped, every framing row of
every chargen banner is 66 wide.

**Budget.** Both doors labelled the name fields "2-30 characters" each
while the combined name is capped at 30 by ``validate_name``, so a legal
pair such as "Christopherson Featherstonehaugh" (14 + 17) cleared both
fields and died on a rule the player was never shown -- as a bare
"Name must be 30 characters or less." on telnet, and as a non-field
error attached to neither input on the web. The prompts and help text
now state the combined budget, the rejection names the numbers, and the
web error lands on the last-name field.
"""
from types import SimpleNamespace

from evennia.utils.ansi import strip_ansi
from evennia.utils.test_resources import EvenniaTest

from commands import charcreate

FRAME_WIDTH = 66
FRAME_CHARS = ("╔", "║", "╚")


def _caller(**data):
    seen = []
    base = {"first_name": "Ada", "last_name": "Lovelace", "sex": "female"}
    base.update(data)
    c = SimpleNamespace(ndb=SimpleNamespace(charcreate_data=base), msg=lambda text=None, **kw: seen.append(str(text)))
    c.seen = seen
    return c


class TestTheFourFramesClose(EvenniaTest):
    NODES = ("first_char_height", "first_char_build",
             "first_char_hair_color", "first_char_hair_style")

    def _frame_rows(self, node_name):
        text, _options = getattr(charcreate, node_name)(_caller(), "")
        return [line for line in strip_ansi(text).splitlines()
                if line.lstrip().startswith(FRAME_CHARS)]

    def test_every_framing_row_is_the_house_width(self):
        for node_name in self.NODES:
            with self.subTest(node=node_name):
                rows = self._frame_rows(node_name)
                self.assertTrue(rows, f"{node_name} rendered no frame")
                self.assertEqual({len(r.strip()) for r in rows}, {FRAME_WIDTH},
                                 f"{node_name}: {[len(r.strip()) for r in rows]}")


class TestTheNameBudgetIsStatedWhereItIsEnforced(EvenniaTest):
    FIRST, LAST = "Christopherson", "Featherstonehaugh"   # 14 + 1 + 17 = 32

    def test_the_telnet_prompt_states_the_combined_budget(self):
        text, _ = charcreate.first_char_name_first(_caller(), "")
        self.assertIn("together", strip_ansi(text))

    def test_telnet_rejects_with_the_numbers(self):
        c = _caller(first_name=self.FIRST)
        charcreate.first_char_name_last(c, self.LAST)
        said = " ".join(c.seen)
        self.assertIn("together", said, said)
        self.assertIn("32", said, said)
        self.assertIn("30", said, said)

    def test_a_pair_that_fits_still_passes_the_budget_check(self):
        c = _caller(first_name="Ada")
        charcreate.first_char_name_last(c, "Lovelace")
        self.assertNotIn("together", " ".join(c.seen))

    def _web_form(self, first, last):
        from web.website.forms import CharacterForm
        blank = CharacterForm()
        return CharacterForm(data={
            "first_name": first, "last_name": last, "sex": "male", "desc": "",
            "grit": 75, "resonance": 75, "intellect": 75, "motorics": 75,
            "height": blank.fields["height"].choices[0][0],
            "build": blank.fields["build"].choices[0][0],
        })

    def test_the_web_help_text_states_the_combined_budget(self):
        from web.website.forms import CharacterForm
        f = CharacterForm()
        self.assertIn("together", f.fields["first_name"].help_text)
        self.assertIn("together", f.fields["last_name"].help_text)

    def test_the_web_error_lands_on_the_last_name_field(self):
        form = self._web_form(self.FIRST, self.LAST)
        form.is_valid()
        self.assertIn("last_name", form.errors, dict(form.errors))
        self.assertIn("together", " ".join(form.errors["last_name"]))
