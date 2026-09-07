"""Two reads that could not reach the value they wanted (#2581, #2593).

## #2581 — the one member of the family with no AttributeProperty

`typeclasses/items.py` declares the plate-carrier family as
AttributeProperties — `is_plate_carrier`, `installed_plates`,
`plate_slots`, `is_armor_plate`, `plate_size` — but **not**
`plate_slot_coverage`. Its only writer is the prototype, so it landed as
a plain DB row, and **Evennia typeclasses do not fall through to DB
attributes on a plain `getattr`**.

Three consumers read it that way and always saw `{}`, so their per-slot
filter never fired:

```
armor_mixin.py:567  _get_total_armor_rating   getattr(...)   broken
medical/utils.py:323                          getattr(...)   broken
items.py:384        validate_plate_slot_coverage            broken, zero callers
```

Declared uncategorised, exactly like its five siblings, so it reads the
**same row** the prototype already wrote — no migration. Verified
against all four live carriers: `getattr` returned a sentinel before and
returns the real mapping now.

**Damage mitigation was never wrong**, and the issue says so.
`_expand_plate_carrier_layers` uses the working `.db.` door, which is why
plates already refused to absorb damage at locations they do not cover.

## #2593 — the death signal read the cause before it was written

`character.db.death_cause` is not written until the corpse is built, ten
lines below the emit. So a first death always announced `(unknown)` —
and because nothing clears the attribute, a **second** death announced
the *previous* death's cause, which is worse than unknown because it is
confidently wrong.

`get_death_cause()` derives it from the medical state, which is what the
corpse constructor calls, so the signal and the corpse now agree. The
stale attribute is deliberately **not** used as a fallback.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

SENTINEL = object()


class TestThePlateCoverageIsReachable(EvenniaTest):
    def carrier(self):
        obj = create_object("typeclasses.items.Item", key="a plate carrier",
                            location=self.room1)
        obj.db.plate_slot_coverage = {"front": ["chest"],
                                      "left_side": ["abdomen"]}
        return obj

    def test_getattr_reaches_the_prototype_written_row(self):
        obj = self.carrier()
        got = getattr(obj, "plate_slot_coverage", SENTINEL)
        self.assertIsNot(got, SENTINEL)
        self.assertEqual(dict(got).get("front"), ["chest"])

    def test_the_db_door_still_works(self):
        """`_expand_plate_carrier_layers` uses it, and that path was
        never broken."""
        obj = self.carrier()
        self.assertEqual(dict(obj.db.plate_slot_coverage).get("left_side"),
                         ["abdomen"])

    def test_both_doors_see_the_same_row(self):
        obj = self.carrier()
        self.assertEqual(dict(getattr(obj, "plate_slot_coverage")),
                         dict(obj.db.plate_slot_coverage))

    def test_a_write_through_the_property_is_visible_to_db(self):
        obj = self.carrier()
        obj.plate_slot_coverage = {"back": ["back"]}
        self.assertEqual(dict(obj.db.plate_slot_coverage), {"back": ["back"]})

    def test_an_item_with_none_reads_empty_not_missing(self):
        plain = create_object("typeclasses.items.Item", key="a crate",
                              location=self.room1)
        self.assertEqual(dict(getattr(plain, "plate_slot_coverage", SENTINEL)
                              or {}), {})

    def test_it_is_declared_beside_its_siblings(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "items.py").read_text(errors="ignore")
        for name in ("is_plate_carrier", "installed_plates", "plate_slots",
                     "is_armor_plate", "plate_size",
                     "plate_slot_coverage"):
            self.assertIn(f"{name} = AttributeProperty(", body,
                          f"{name} is not declared")


class TestTheDeathSignalNamesTheCause(EvenniaTest):
    def emit_note(self, live_cause, stale_attr=None):
        """Runs the emit block's decision as the code now makes it."""
        self.char1.db.death_cause = stale_attr
        with mock.patch.object(type(self.char1), "get_death_cause",
                               return_value=live_cause):
            try:
                cause = self.char1.get_death_cause()
            except Exception:  # noqa: BLE001
                cause = None
            return f"{self.char1.key} ({cause or 'unknown'})"

    def old_emit_note(self, live_cause, stale_attr=None):
        """The pre-fix decision, so the defect is demonstrated rather
        than described: it read the ATTRIBUTE, which the corpse writes
        ten lines later."""
        self.char1.db.death_cause = stale_attr
        return (f"{self.char1.key} "
                f"({self.char1.db.death_cause or 'unknown'})")

    def test_the_old_form_said_unknown_on_a_first_death(self):
        self.assertIn("(unknown)",
                      self.old_emit_note("blood loss", stale_attr=None))

    def test_the_old_form_reused_the_previous_cause(self):
        """Worse than unknown — confidently wrong."""
        self.assertIn("(blood loss)",
                      self.old_emit_note("gunshot", stale_attr="blood loss"))

    def test_a_first_death_names_the_cause(self):
        """The attribute is still None at this point — the live read is
        what makes the note true."""
        self.assertIn("(blood loss)",
                      self.emit_note("blood loss", stale_attr=None))

    def test_it_no_longer_says_unknown_when_the_cause_is_known(self):
        self.assertNotIn("unknown",
                         self.emit_note("blood loss", stale_attr=None))

    def test_a_second_death_does_not_reuse_the_first(self):
        """The stale attribute holds the PREVIOUS cause; the live read
        must win."""
        note = self.emit_note("gunshot", stale_attr="blood loss")
        self.assertIn("(gunshot)", note)
        self.assertNotIn("blood loss", note)

    def test_an_unreadable_cause_says_unknown_not_the_old_one(self):
        """"Unknown" is honest; last death's cause is not."""
        note = self.emit_note(None, stale_attr="blood loss")
        self.assertIn("(unknown)", note)
        self.assertNotIn("blood loss", note)

    def test_the_source_no_longer_reads_the_attribute_there(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "death_progression.py").read_text(
            errors="ignore")
        start = body.index('wsis.emit("death"')
        window = body[start - 900:start + 200]
        self.assertIn("get_death_cause()", window)
        self.assertNotIn("character.db.death_cause or 'unknown'", window)

    def test_the_corpse_still_records_it(self):
        """The signal and the corpse must agree — the corpse writer is
        untouched."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "death_progression.py").read_text(
            errors="ignore")
        self.assertIn("corpse.db.death_cause = character.get_death_cause()",
                      body)
