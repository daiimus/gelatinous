"""Tests for the Phase 3.5 disguise prototype catalog.

Verifies that each disguise prototype in :mod:`world.prototypes` carries
the attribute surface required by the disguise engine
(:mod:`world.identity`), splits cleanly into Class A (visibly-obfuscating
with a non-empty ``disguise_adjective``) and Class B (silent obfuscators
with ``disguise_adjective=""``), and behaves correctly under same-type vs
cross-type swaps.

See ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Disguise Item Taxonomy"
and the PR-3.5 plan for the catalog rationale.
"""

from __future__ import annotations

from unittest import TestCase

from world import prototypes
from world.identity import (
    get_apparent_uid,
    get_disguise_adjective,
    get_essential_item_type_ids,
)
from world.tests._identity_helpers import prepare_mock_for_apparent_uid
from world.tests.test_identity import (
    _FakeDisguiseItem,
    _SignatureMockCharacter,
)


# Class A — visibly-obfuscating: must carry a non-empty
# ``disguise_adjective``.
CLASS_A_PROTOTYPES: tuple[str, ...] = (
    "BALACLAVA",
    "SKI_MASK",
    "SURGICAL_MASK",
    "RESPIRATOR",
    "DOMINO_MASK",
    "FACE_BANDANA",
    "HOODIE_HOOD_UP",
)

# Class B — silent obfuscators: must carry ``disguise_adjective=""``.
CLASS_B_PROTOTYPES: tuple[str, ...] = (
    "BLACK_WIG",
    "BLOND_WIG",
    "BROWN_WIG",
    "COLORED_CONTACTS",
    "MIRRORSHADES",
    "AVIATOR_SUNGLASSES",
)

ALL_DISGUISE_PROTOTYPES: tuple[str, ...] = (
    CLASS_A_PROTOTYPES + CLASS_B_PROTOTYPES
)

# Items whose ``coverage`` must include ``"hair"`` (replaces the legacy
# ``covers_hair`` boolean — see #176).  These are the head-coverings
# that conceal scalp/hair from observers.
COVERS_HAIR_PROTOTYPES: frozenset[str] = frozenset(
    {
        "BALACLAVA",
        "SKI_MASK",
        "HOODIE_HOOD_UP",
        "BLACK_WIG",
        "BLOND_WIG",
        "BROWN_WIG",
    }
)


def _attrs_dict(prototype_name: str) -> dict:
    """Return the prototype's ``attrs`` list flattened to a dict."""
    proto = getattr(prototypes, prototype_name)
    return dict(proto["attrs"])


def _fake_item_from_prototype(prototype_name: str) -> _FakeDisguiseItem:
    """Construct an :class:`_FakeDisguiseItem` from the prototype attrs.

    Uses the same duck-typed surface the engine reads at runtime, so the
    fake faithfully exercises ``get_essential_item_type_ids``,
    ``get_disguise_adjective``, and the distinguishing-feature chain.
    """
    attrs = _attrs_dict(prototype_name)
    proto = getattr(prototypes, prototype_name)
    return _FakeDisguiseItem(
        disguise_essential=attrs.get("disguise_essential", False),
        disguise_type_id=attrs.get("disguise_type_id", ""),
        is_disguise_item=attrs.get("is_disguise_item", False),
        disguise_adjective=attrs.get("disguise_adjective", ""),
        worn_sdesc_short=attrs.get("worn_sdesc_short", ""),
        coverage=attrs.get("coverage", []),
        key=proto["key"],
    )


class TestDisguisePrototypeStructure(TestCase):
    """Each prototype defines the disguise attribute surface correctly."""

    def test_all_prototypes_exist(self) -> None:
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                self.assertTrue(
                    hasattr(prototypes, name),
                    f"Missing disguise prototype: {name}",
                )

    def test_all_prototypes_are_disguise_items(self) -> None:
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                self.assertIs(
                    attrs.get("is_disguise_item"),
                    True,
                    f"{name} must set is_disguise_item=True",
                )

    def test_all_prototypes_are_essential(self) -> None:
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                self.assertIs(
                    attrs.get("disguise_essential"),
                    True,
                    f"{name} must set disguise_essential=True",
                )

    def test_all_prototypes_define_type_id(self) -> None:
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                type_id = attrs.get("disguise_type_id", "")
                self.assertTrue(
                    isinstance(type_id, str) and type_id,
                    f"{name} must define a non-empty disguise_type_id",
                )

    def test_all_prototypes_define_worn_sdesc_short(self) -> None:
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                short = attrs.get("worn_sdesc_short", "")
                self.assertTrue(
                    isinstance(short, str) and short,
                    f"{name} must define a non-empty worn_sdesc_short",
                )

    def test_prototype_keys_match_dict_names(self) -> None:
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                proto = getattr(prototypes, name)
                self.assertEqual(proto["prototype_key"], name)

    def test_typeclass_is_item(self) -> None:
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                proto = getattr(prototypes, name)
                self.assertEqual(
                    proto["typeclass"], "typeclasses.items.Item"
                )


class TestClassAVisiblyObfuscating(TestCase):
    """Class A items carry a non-empty disguise_adjective."""

    def test_class_a_have_non_empty_adjective(self) -> None:
        for name in CLASS_A_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                adjective = attrs.get("disguise_adjective", "")
                self.assertTrue(
                    isinstance(adjective, str) and adjective,
                    f"{name} (Class A) must have non-empty "
                    f"disguise_adjective; got {adjective!r}",
                )

    def test_class_a_adjective_drives_get_disguise_adjective(self) -> None:
        for name in CLASS_A_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                expected = attrs["disguise_adjective"]
                char = _SignatureMockCharacter(
                    worn_items=[_fake_item_from_prototype(name)]
                )
                self.assertEqual(
                    get_disguise_adjective(char), expected
                )


class TestClassBSilentObfuscators(TestCase):
    """Class B items carry an empty disguise_adjective but still flip UID."""

    def test_class_b_have_empty_adjective(self) -> None:
        for name in CLASS_B_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                adjective = attrs.get("disguise_adjective", "")
                self.assertEqual(
                    adjective,
                    "",
                    f"{name} (Class B) must have empty "
                    f"disguise_adjective; got {adjective!r}",
                )

    def test_class_b_contributes_no_adjective(self) -> None:
        for name in CLASS_B_PROTOTYPES:
            with self.subTest(prototype=name):
                char = _SignatureMockCharacter(
                    worn_items=[_fake_item_from_prototype(name)]
                )
                self.assertIsNone(get_disguise_adjective(char))

    def test_class_b_still_shifts_apparent_uid(self) -> None:
        """Wearing a silent obfuscator must change the Apparent UID."""
        for name in CLASS_B_PROTOTYPES:
            with self.subTest(prototype=name):
                bare = _SignatureMockCharacter()
                disguised = _SignatureMockCharacter(
                    worn_items=[_fake_item_from_prototype(name)]
                )
                prepare_mock_for_apparent_uid(bare)
                prepare_mock_for_apparent_uid(disguised)
                bare_uid = get_apparent_uid(bare)
                disguised_uid = get_apparent_uid(disguised)
                self.assertIsNotNone(bare_uid)
                self.assertIsNotNone(disguised_uid)
                self.assertNotEqual(
                    bare_uid,
                    disguised_uid,
                    f"{name} (Class B) must shift the Apparent UID "
                    f"despite having no adjective",
                )


class TestHairCoverageFlag(TestCase):
    """Items in COVERS_HAIR_PROTOTYPES include ``"hair"`` in coverage; others omit it.

    Replaces the legacy ``covers_hair`` boolean with the unified
    clothing-coverage vocabulary; see #176.
    """

    def test_hair_coverage_set_correctly(self) -> None:
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                coverage = list(attrs.get("coverage", []))
                covers_hair = "hair" in coverage
                expected = name in COVERS_HAIR_PROTOTYPES
                self.assertEqual(
                    covers_hair,
                    expected,
                    f"{name} has 'hair' in coverage={covers_hair}, "
                    f"expected {expected} (coverage={coverage!r})",
                )

    def test_covers_hair_attribute_is_gone(self) -> None:
        """Legacy ``covers_hair`` attribute must not appear in any prototype."""
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                self.assertNotIn(
                    "covers_hair",
                    attrs,
                    f"{name} still defines legacy covers_hair "
                    f"attribute; migrate to coverage=[..., 'hair']",
                )


class TestSameTypeSwapApparentUidStable(TestCase):
    """Swapping items of the same disguise_type_id must not shift UID."""

    def test_balaclava_to_ski_mask_uid_unchanged(self) -> None:
        with_balaclava = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("BALACLAVA")]
        )
        with_ski_mask = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("SKI_MASK")]
        )
        prepare_mock_for_apparent_uid(with_balaclava)
        prepare_mock_for_apparent_uid(with_ski_mask)
        self.assertEqual(
            get_apparent_uid(with_balaclava),
            get_apparent_uid(with_ski_mask),
            "BALACLAVA and SKI_MASK share disguise_type_id='balaclava'; "
            "swapping must not shift Apparent UID.",
        )

    def test_wig_swap_uid_unchanged(self) -> None:
        with_black = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("BLACK_WIG")]
        )
        with_blond = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("BLOND_WIG")]
        )
        prepare_mock_for_apparent_uid(with_black)
        prepare_mock_for_apparent_uid(with_blond)
        self.assertEqual(
            get_apparent_uid(with_black),
            get_apparent_uid(with_blond),
            "All wigs share disguise_type_id='wig'; swapping must not "
            "shift Apparent UID.",
        )

    def test_brown_wig_collapses_with_other_wigs(self) -> None:
        """BROWN_WIG must collapse with BLACK_WIG and BLOND_WIG.

        Per the rationale on BLACK_WIG in ``world/prototypes.py``: wig
        colour is appearance flavour, not an identity-class distinction.
        All three wig prototypes share ``disguise_type_id='wig'`` and
        must produce identical Apparent UIDs when worn alone.
        """
        with_black = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("BLACK_WIG")]
        )
        with_brown = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("BROWN_WIG")]
        )
        with_blond = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("BLOND_WIG")]
        )
        for char in (with_black, with_brown, with_blond):
            prepare_mock_for_apparent_uid(char)
        self.assertEqual(
            get_apparent_uid(with_black),
            get_apparent_uid(with_brown),
        )
        self.assertEqual(
            get_apparent_uid(with_brown),
            get_apparent_uid(with_blond),
        )

    def test_sunglasses_swap_uid_unchanged_within_type(self) -> None:
        """MIRRORSHADES and AVIATOR_SUNGLASSES are distinct types.

        They obfuscate the same body slot (eyes) but model different
        ``disguise_type_id`` values, so their swap *should* shift the
        UID.  This test guards the inverse: same type → same UID, by
        comparing two AVIATOR_SUNGLASSES instances.
        """
        a = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("AVIATOR_SUNGLASSES")]
        )
        b = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("AVIATOR_SUNGLASSES")]
        )
        prepare_mock_for_apparent_uid(a)
        prepare_mock_for_apparent_uid(b)
        self.assertEqual(get_apparent_uid(a), get_apparent_uid(b))


class TestCrossTypeSwapApparentUidShifts(TestCase):
    """Swapping to a different disguise_type_id must shift the UID."""

    def test_balaclava_to_hood_uid_shifts(self) -> None:
        with_balaclava = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("BALACLAVA")]
        )
        with_hood = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("HOODIE_HOOD_UP")]
        )
        prepare_mock_for_apparent_uid(with_balaclava)
        prepare_mock_for_apparent_uid(with_hood)
        self.assertNotEqual(
            get_apparent_uid(with_balaclava),
            get_apparent_uid(with_hood),
        )

    def test_mirrorshades_to_aviators_uid_shifts(self) -> None:
        """Different sunglass types model as different disguise_type_id."""
        with_mirror = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("MIRRORSHADES")]
        )
        with_aviators = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("AVIATOR_SUNGLASSES")]
        )
        prepare_mock_for_apparent_uid(with_mirror)
        prepare_mock_for_apparent_uid(with_aviators)
        self.assertNotEqual(
            get_apparent_uid(with_mirror),
            get_apparent_uid(with_aviators),
        )

    def test_contacts_to_sunglasses_uid_shifts(self) -> None:
        with_contacts = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("COLORED_CONTACTS")]
        )
        with_aviators = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("AVIATOR_SUNGLASSES")]
        )
        prepare_mock_for_apparent_uid(with_contacts)
        prepare_mock_for_apparent_uid(with_aviators)
        self.assertNotEqual(
            get_apparent_uid(with_contacts),
            get_apparent_uid(with_aviators),
        )

    def test_surgical_mask_to_respirator_uid_shifts(self) -> None:
        """SURGICAL_MASK and RESPIRATOR are deliberately distinct types.

        Both cover the lower face, but a flat paper rectangle reads
        very differently from a moulded respirator with twin filter
        cans.  Per the rationale comments in ``world/prototypes.py``:
        silhouette overlap is not enough to collapse the type id when
        the visible signature differs sharply.  Swapping between them
        must shift the Apparent UID so observers register the change.
        """
        with_surgical = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("SURGICAL_MASK")]
        )
        with_respirator = _SignatureMockCharacter(
            worn_items=[_fake_item_from_prototype("RESPIRATOR")]
        )
        prepare_mock_for_apparent_uid(with_surgical)
        prepare_mock_for_apparent_uid(with_respirator)
        self.assertNotEqual(
            get_apparent_uid(with_surgical),
            get_apparent_uid(with_respirator),
        )


class TestEssentialTypeIdsFromCatalog(TestCase):
    """get_essential_item_type_ids reads each prototype's type_id."""

    def test_each_prototype_contributes_its_type_id(self) -> None:
        for name in ALL_DISGUISE_PROTOTYPES:
            with self.subTest(prototype=name):
                attrs = _attrs_dict(name)
                expected = (attrs["disguise_type_id"],)
                char = _SignatureMockCharacter(
                    worn_items=[_fake_item_from_prototype(name)]
                )
                self.assertEqual(
                    get_essential_item_type_ids(char), expected
                )
