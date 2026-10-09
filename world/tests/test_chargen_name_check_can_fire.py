"""The name check compares what the game stores (#2550), and an implant
is not a consumable (#2568).

## #2550 — a check against a string nothing is stored under

`validate_name` asked for `db_key__iexact="First Last"`. Nothing is ever
stored under that: `build_name_from_death_count` appends a Roman
numeral, so the first sleeve is keyed `"First Last I"`. The two differ
**by construction**, so the friendly in-menu check could never fire
against a telnet-created character — and the collision surfaced 1300
lines later as a raw exception string at the confirmation node, which
routed back to confirmation rather than to the name prompt. Nothing the
player could do from there changed the name.

The check now compares on the **base** name, using the same regex
`build_name_from_death_count` strips with, so "First Last" reads as
taken whether the existing sleeve is I, II or XIV.

The late failure keeps its dead end for genuine errors, but a name
collision — the one failure a player can act on — now says so and
returns to the name prompt.

## #2568 — an implant is not a consumable

13 of the 101 live medical items carry no `uses_left` (verified against
the DB while fixing: the same 13 carry no `medical_type` either — they
are cyberware, `is_medical_item` without being something you spend).

The second half of this file, the #2568 implant readout regression, left
with `medlist` and `refillmed` under #3728 (2026-10-09).
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.charcreate import build_name_from_death_count, validate_name


class TestTheNameCheckCanFire(EvenniaCommandTest):
    def existing(self, key):
        return create_object("typeclasses.characters.Character", key=key,
                             location=self.room1)

    def test_a_first_sleeve_blocks_the_base_name(self):
        self.existing("Jon Smith I")
        ok, msg = validate_name("Jon Smith")
        self.assertFalse(ok, "the check never fired")
        self.assertIn("taken", msg)

    def test_a_later_sleeve_blocks_it_too(self):
        self.existing("Jon Smith XIV")
        self.assertFalse(validate_name("Jon Smith")[0])

    def test_it_is_case_insensitive(self):
        self.existing("Jon Smith I")
        self.assertFalse(validate_name("jon smith")[0])

    def test_an_unused_name_is_still_free(self):
        self.existing("Jon Smith I")
        self.assertTrue(validate_name("Vera Halloway")[0])

    def test_a_longer_name_is_not_a_collision(self):
        """"Jon Smith" must not be blocked by "Jon Smithers II"."""
        self.existing("Jon Smithers II")
        self.assertTrue(validate_name("Jon Smith")[0])

    def test_the_stored_form_really_does_carry_a_numeral(self):
        """The premise: what chargen validates and what it stores."""
        self.assertEqual(build_name_from_death_count("Jon Smith", 1),
                         "Jon Smith I")

    def test_a_bare_stored_name_still_blocks(self):
        """Legacy keys with no numeral are still matched exactly."""
        self.existing("Jon Smith")
        self.assertFalse(validate_name("Jon Smith")[0])
