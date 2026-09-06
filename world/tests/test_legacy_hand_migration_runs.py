"""The PR-H2 legacy hand migration actually runs (#2582).

`_migrate_legacy_hands_if_needed` guarded on `isinstance(legacy, dict)`.
Evennia returns a persisted dict as `_SaverDict`, whose MRO is
`_SaverDict -> _SaverMutable -> MutableMapping -> Mapping` — it never
inherits `dict`. So the guard was always False, the migration had **never
run for anyone**, and 55 legacy rows were still present.

Seven characters were holding weapons the game could not see, because
`hands` reads `held_items` and the items were sitting in the old row:

    Jimmy Nightshade    katana
    Aetos McLuvin       chainsaw
    Nick Kramer         light pistol
    Martha Howard       HDG M88 tactical pistol
    LackOfSkillz Hurtz  PAM Model 6 pistol
    Drivel X            katana
    Anna Ends           HIVE-MIND Mark VII coverall

**This shape has now appeared five times in this codebase** — #2701
(bleeding conditions), #2465 (placement rows), #2468 (worn layers),
#2438 (severance), and here. A stored container is mapping- or
sequence-LIKE, never the builtin, so `isinstance` against `dict` or
`list` reads as a safety guard and is really an unconditional skip.

The migration is self-healing: it runs on the next `hands` read, which
every consumer performs, so no build script is needed.
"""
from evennia.utils.test_resources import EvenniaTest


class _LegacyCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char = self.char1
        self.weapon = self.obj1
        self.weapon.key = "a katana"
        self.weapon.location = self.char

    def seed_legacy(self, mapping):
        """Exactly how a pre-PR-H2 body stores it: an attribute in the
        `equipment` category, which comes back as a `_SaverDict`."""
        self.char.attributes.add("hands", mapping, category="equipment")

    def legacy_row(self):
        return self.char.attributes.get("hands", category="equipment")


class TestTheStoredShapeIsNotADict(_LegacyCase):
    """The trap itself, pinned so the next reader does not re-add the
    isinstance check."""

    def test_a_persisted_mapping_is_not_a_dict_subclass(self):
        self.seed_legacy({"right": self.weapon})
        self.assertFalse(isinstance(self.legacy_row(), dict))

    def test_but_it_is_mapping_shaped(self):
        self.seed_legacy({"right": self.weapon})
        self.assertTrue(hasattr(self.legacy_row(), "items"))


class TestTheMigrationRuns(_LegacyCase):
    def test_the_weapon_becomes_visible(self):
        self.seed_legacy({"right": self.weapon})
        self.assertIn(self.weapon, self.char.hands.values())

    def test_the_legacy_row_is_removed(self):
        self.seed_legacy({"right": self.weapon})
        self.char.hands            # the read that migrates
        self.assertIsNone(self.legacy_row())

    def test_the_shorthand_key_becomes_canonical(self):
        self.seed_legacy({"right": self.weapon})
        self.char.hands
        self.assertIn("right_hand", dict(self.char.held_items or {}))

    def test_it_is_idempotent(self):
        self.seed_legacy({"right": self.weapon})
        self.char.hands
        self.char.hands
        self.assertIn(self.weapon, self.char.hands.values())


class TestItDoesNotClobberNewerData(_LegacyCase):
    """"Only carries forward slots that aren't already populated" — the
    transition-window rule the docstring promises."""

    def test_a_populated_slot_wins(self):
        newer = self.obj2
        newer.key = "a bone-handled knife"
        self.char.held_items = {"right_hand": newer}
        self.seed_legacy({"right": self.weapon})
        self.char.hands
        self.assertIs(dict(self.char.held_items or {})["right_hand"], newer)

    def test_an_empty_slot_is_filled(self):
        self.char.held_items = {}
        self.seed_legacy({"right": self.weapon})
        self.char.hands
        self.assertIs(dict(self.char.held_items or {})["right_hand"],
                      self.weapon)


class TestNothingToMigrateIsSafe(_LegacyCase):
    def test_a_body_with_no_legacy_row_is_untouched(self):
        self.char.held_items = {"right_hand": self.weapon}
        self.char.hands
        self.assertIn(self.weapon, self.char.hands.values())

    def test_a_junk_legacy_value_is_ignored(self):
        self.char.attributes.add("hands", "not a mapping",
                                 category="equipment")
        self.char.hands   # must not raise
