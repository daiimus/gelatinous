"""A corpse wears what it was wearing, not what it was carrying (#2460).

On death, `_transition_character_to_death` moves ALL of
`character.contents` onto the corpse — worn kit and merely carried kit
alike, since worn items live in `contents` too — and then clears
`worn_items`. No record of the difference survived.

`_build_corpse_clothing_coverage_map` then admitted **any** object with
a truthy `db.coverage`, which is every garment in the pack. So `remove
jacket` and then die, and the corpse still read as wearing the jacket —
and the map is also what SUPPRESSES the preserved body longdescs, so
the chest, back, abdomen and arm descriptions vanished underneath a
garment that was in a bag.

The same applied to looted coats and newly-bought shirts: anything
clothing-shaped in the inventory dressed the body.

`Corpse.get_worn_items`' own docstring assumed contents == worn, which
stops being true the moment anything unworn is carried.

The record is stamped at the last moment the truth exists — before
`worn_items` is cleared — and stored as **ids**, so it survives the
items being looted away.

**It falls back to the old contents-wide behaviour when there is no
record.** Corpses that predate this, and any other creation path, still
render as they did rather than suddenly rendering naked.

**Finding 1 of the issue did not survive checking.** `give` handing
over a worn garment was the "wield" substring sniff, fixed in #2516 —
`CmdGive` now asks `is_wielding` rather than reading the refusal
sentence.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _CorpseCase(EvenniaTest):
    def corpse(self):
        return create_object("typeclasses.corpse.Corpse", key="a corpse",
                             location=self.room1)

    def garment(self, corpse, key="a jacket", coverage=("chest", "back")):
        item = create_object("typeclasses.items.Item", key=key,
                             location=corpse)
        item.db.coverage = list(coverage)
        item.db.worn_desc = key
        return item

    def covered(self, corpse):
        return set(corpse._build_corpse_clothing_coverage_map())


class TestOnlyTheWornGarmentDresses(_CorpseCase):
    def test_a_carried_garment_does_not_cover(self):
        corpse = self.corpse()
        carried = self.garment(corpse)
        corpse.db.worn_at_death = []          # they died carrying it
        self.assertEqual(self.covered(corpse), set())

    def test_a_worn_garment_does_cover(self):
        corpse = self.corpse()
        worn = self.garment(corpse)
        corpse.db.worn_at_death = [worn.id]
        self.assertEqual(self.covered(corpse), {"chest", "back"})

    def test_a_mixed_load_covers_only_the_worn_one(self):
        corpse = self.corpse()
        worn = self.garment(corpse, "a shirt", ("chest",))
        self.garment(corpse, "a spare coat", ("chest", "back", "abdomen"))
        corpse.db.worn_at_death = [worn.id]
        self.assertEqual(self.covered(corpse), {"chest"})

    def test_the_map_points_at_the_worn_item(self):
        corpse = self.corpse()
        worn = self.garment(corpse, "a shirt", ("chest",))
        self.garment(corpse, "a spare coat", ("chest",))
        corpse.db.worn_at_death = [worn.id]
        self.assertIs(corpse._build_corpse_clothing_coverage_map()["chest"],
                      worn)


class TestTheRecordSurvivesLooting(_CorpseCase):
    def test_looting_one_garment_does_not_dress_the_body_in_another(self):
        corpse = self.corpse()
        worn = self.garment(corpse, "a shirt", ("chest",))
        spare = self.garment(corpse, "a spare coat", ("back",))
        corpse.db.worn_at_death = [worn.id]
        worn.location = self.room1            # somebody took the shirt
        self.assertEqual(self.covered(corpse), set())
        self.assertIsNot(spare.location, self.room1)


class TestOldCorpsesRenderAsBefore(_CorpseCase):
    """No record means no opinion — an existing corpse must not suddenly
    render naked."""

    def test_without_a_record_contents_still_dress_it(self):
        corpse = self.corpse()
        self.garment(corpse)
        self.assertIsNone(corpse.db.worn_at_death)
        self.assertEqual(self.covered(corpse), {"chest", "back"})

    def test_non_clothing_is_still_excluded(self):
        corpse = self.corpse()
        create_object("typeclasses.items.Item", key="a credstick",
                      location=corpse)
        self.assertEqual(self.covered(corpse), set())


class TestDressingACorpseStillShows(_CorpseCase):
    """The filter must not break the path that dresses a corpse
    deliberately — `dress corpse in burial shroud` is the command's own
    documented example."""

    def test_a_shroud_dressed_onto_a_recorded_corpse_renders(self):
        corpse = self.corpse()
        worn = self.garment(corpse, "a shirt", ("chest",))
        corpse.db.worn_at_death = [worn.id]
        shroud = self.garment(corpse, "a burial shroud", ("back",))
        corpse.mark_worn(shroud)
        self.assertIn("back", self.covered(corpse))

    def test_marking_is_a_no_op_without_a_record(self):
        """No record means the map renders contents-wide anyway."""
        corpse = self.corpse()
        shroud = self.garment(corpse, "a burial shroud", ("back",))
        corpse.mark_worn(shroud)
        self.assertIsNone(corpse.db.worn_at_death)
        self.assertIn("back", self.covered(corpse))

    def test_the_dress_path_calls_it(self):
        import inspect
        from commands import CmdClothing
        source = inspect.getsource(CmdClothing.CmdDress._dress_corpse)
        self.assertIn("mark_worn", source)

    def test_it_does_not_double_record(self):
        corpse = self.corpse()
        shroud = self.garment(corpse, "a shroud", ("back",))
        corpse.db.worn_at_death = []
        corpse.mark_worn(shroud)
        corpse.mark_worn(shroud)
        self.assertEqual(list(corpse.db.worn_at_death).count(shroud.id), 1)


class TestTheOtherThreeStayFixed(EvenniaTest):
    """Findings 1, 3 and 5 were already closed — pins, not evidence."""

    def test_give_asks_the_hands_not_the_sentence(self):
        """#2516."""
        import inspect
        from commands import CmdInventory
        source = inspect.getsource(CmdInventory)
        self.assertIn("is_wielding", source)
        self.assertNotIn('"wield" not in wield_result', source)

    def test_a_garment_leaving_the_body_gives_up_its_slots(self):
        """#3: `dress` never cleared the dresser's hand — but
        `at_object_leave` calls `release_slots` for ANYTHING leaving a
        body, and `quiet=True` suppresses messages, not hooks."""
        import inspect
        from typeclasses.characters import Character
        self.assertIn("release_slots",
                      inspect.getsource(Character.at_object_leave))

    def test_dropping_single_use_kit_still_perishes_it(self):
        """#5, fixed by #2456: `drop` calls `at_drop`."""
        import inspect
        from commands import CmdInventory
        self.assertIn("at_drop", inspect.getsource(CmdInventory))


class TestDeathStampsTheRecord(EvenniaTest):
    def test_the_transfer_writes_worn_at_death(self):
        import inspect
        from typeclasses import death_progression
        source = inspect.getsource(death_progression)
        self.assertIn("worn_at_death", source)

    def test_it_is_captured_before_worn_items_is_cleared(self):
        """Stamped at the last moment the truth exists."""
        import inspect
        from typeclasses import death_progression
        source = inspect.getsource(death_progression)
        self.assertLess(source.index("worn_at_death"),
                        source.index("character.worn_items = {}"))


class TestGiveStaysFixed(EvenniaTest):
    """Finding 1, already closed by #2516 — a pin, not evidence."""

    def test_give_asks_the_hands_not_the_sentence(self):
        import inspect
        from commands import CmdInventory
        source = inspect.getsource(CmdInventory)
        self.assertIn("is_wielding", source)
        self.assertNotIn('"wield" not in wield_result', source)


class TestThePreviewReadsLikeTheRoom(EvenniaTest):
    """`describe short`'s preview rendered braced verbs at the wrong
    grammatical number for neutral / nonbinary characters (#2460).

    Braced verbs follow the PRONOUN's number: singular for he / she,
    plural for singular-they. The room render computes that; the preview
    omitted `number` entirely and defaulted to singular, so an author
    saw "They holds themselves very still" while every actual `look`
    renders "They hold themselves very still".

    The preview is the authoring surface the spec advertises, so an
    author could "correct" correct prose into broken prose. Male and
    female are unaffected — both paths are singular — which is why it
    stayed hidden.
    """

    def test_a_neutral_character_reads_plural(self):
        from typeclasses.appearance_mixin import body_number_for
        for gender in ("neutral", "nonbinary", "other", "", None):
            self.assertEqual(body_number_for(gender), "plural", repr(gender))

    def test_he_and_she_read_singular(self):
        from typeclasses.appearance_mixin import body_number_for
        for gender in ("male", "female", "MALE", "Female"):
            self.assertEqual(body_number_for(gender), "singular", gender)

    def test_the_preview_asks_for_a_number(self):
        import inspect
        from commands import CmdCharacter
        source = inspect.getsource(CmdCharacter)
        idx = source.index("Set your short description.")
        self.assertIn("body_number_for", source[idx - 400:idx + 600])

    def test_the_room_and_the_preview_use_the_same_helper(self):
        """One expression, asked in three places — the preview was the
        one that never asked."""
        import inspect
        from typeclasses import appearance_mixin
        from commands import CmdCharacter
        for module in (appearance_mixin, CmdCharacter):
            self.assertIn("body_number_for", inspect.getsource(module))

    def test_a_neutral_body_renders_the_plural_verb(self):
        """Driven through the real renderer, not the helper."""
        self.char1.db.gender = "neutral"
        rendered = self.char1._process_description_variables(
            "{they} {hold} still.", self.char1,
            force_third_person=True, number="plural",
        )
        self.assertNotIn("holds", rendered)
