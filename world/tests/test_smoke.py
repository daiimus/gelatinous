"""Tests for the smoke subsystem (issue #454).

Pure-function and command-level coverage against fakes — no
Evennia DB required.  Pins:

* ``parse_possessive_target`` splits ``"bob's cig"`` correctly.
* Held-item helpers find role-tagged items in ``character.hands``.
* ``pick_smoke_message`` returns brand-matched messages and falls
  back to NEUTRAL for unknown brands.
* ``CmdLight`` self path lights an unlit cigarette.
* ``CmdLight`` other-target path routes by identity resolution.
* ``CmdLight`` rejects unholding-a-lighter.
* ``CmdSmoke`` requires lit; decrements puffs; destroys at zero.
* ``CmdSnuff`` clears lit state.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world import smoke as sm


# ---------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------


class _FakeTags:
    """In-memory Tag handler matching ``obj.tags.has/add/remove``."""

    def __init__(self):
        self._tags: set[tuple[str, str | None]] = set()

    def has(self, key, category=None):
        return (key, category) in self._tags

    def add(self, key, category=None):
        self._tags.add((key, category))

    def remove(self, key, category=None):
        self._tags.discard((key, category))


class _FakeDB(SimpleNamespace):
    """``obj.db`` stand-in supporting ``getattr`` and ``setattr``."""

    def __getattribute__(self, name):
        # SimpleNamespace already returns None for missing-but-not-set
        # attributes only via ``getattr(obj, name, None)``.  For
        # direct attribute access we mirror the same lenient shape so
        # tests can simply read ``item.db.brand`` regardless of state.
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return None


class _FakeAttributes:
    """``item.attributes.get / add`` for the ``uses_left`` plumbing
    that :func:`world.medical.utils.use_item` reads."""

    def __init__(self, **initial):
        self._values = dict(initial)

    def get(self, key, default=None):
        return self._values.get(key, default)

    def add(self, key, value):
        self._values[key] = value


class _FakeItem:
    def __init__(
        self,
        *,
        key="cigarette",
        aliases=None,
        role_tags: list[tuple[str, str]] | None = None,
        substance="tobacco_neutral",
        uses_left=6,
        max_uses=6,
        legacy_brand=None,
    ):
        self.key = key
        self.aliases = list(aliases or [])
        self.tags = _FakeTags()
        for tag, category in (role_tags or []):
            self.tags.add(tag, category=category)
        # ``legacy_brand`` covers pre-#456 items: db.brand but no
        # db.substance.  ``substance`` covers the post-#456 shape.
        db_kwargs = {}
        if legacy_brand is not None:
            db_kwargs["brand"] = legacy_brand
        else:
            db_kwargs["substance"] = substance
        self.db = _FakeDB(**db_kwargs)
        self.attributes = _FakeAttributes(
            uses_left=uses_left, max_uses=max_uses,
        )
        self.deleted = False

    def delete(self):
        self.deleted = True


def _cigarette(substance="tobacco_neutral", **kw):
    return _FakeItem(
        role_tags=[(sm.SMOKE_DELIVERY, sm.DELIVERY_METHOD_CATEGORY)],
        substance=substance,
        **kw,
    )


def _lighter():
    return _FakeItem(
        key="lighter",
        role_tags=[(sm.LIGHTER_ROLE, sm.ITEM_ROLE_CATEGORY)],
        substance=None,
    )


class _FakeRoom:
    def __init__(self):
        self.contents = []


class _FakeCharacter:
    def __init__(self, *, key="Tester", location=None, hands=None):
        self.key = key
        self.dbref = f"#{abs(id(self)) % 10000}"
        self.location = location
        self.hands = hands or {}
        self.msgs: list[str] = []
        # Mock interface used by resolve_character_target's fallbacks.
        self.permissions = SimpleNamespace(check=lambda *_a, **_k: False)

    def msg(self, text):
        self.msgs.append(text)

    def get_display_name(self, looker=None):
        return self.key

    def check_permstring(self, _perm):
        return False


# ---------------------------------------------------------------------
# parse_possessive_target
# ---------------------------------------------------------------------


class TestParsePossessive(TestCase):
    def test_no_possessive(self):
        self.assertEqual(sm.parse_possessive_target("cigarette"), (None, "cigarette"))

    def test_simple_possessive(self):
        self.assertEqual(
            sm.parse_possessive_target("bob's cigarette"),
            ("bob", "cigarette"),
        )

    def test_multi_word_item(self):
        self.assertEqual(
            sm.parse_possessive_target("bob's noir cig"),
            ("bob", "noir cig"),
        )

    def test_empty_input(self):
        self.assertEqual(sm.parse_possessive_target(""), (None, ""))
        self.assertEqual(sm.parse_possessive_target("   "), (None, ""))

    def test_strips_whitespace(self):
        self.assertEqual(
            sm.parse_possessive_target("  alice's  cigarette  "),
            ("alice", "cigarette"),
        )


# ---------------------------------------------------------------------
# Held-item helpers
# ---------------------------------------------------------------------


class TestHeldItems(TestCase):
    def test_find_held_cigarette(self):
        cig = _cigarette()
        char = _FakeCharacter(hands={"left_hand": cig, "right_hand": None})
        self.assertIs(sm.find_held_cigarette(char), cig)

    def test_find_held_lighter(self):
        lig = _lighter()
        char = _FakeCharacter(hands={"left_hand": lig})
        self.assertIs(sm.find_held_lighter(char), lig)

    def test_find_held_returns_none_when_absent(self):
        char = _FakeCharacter(hands={"left_hand": None, "right_hand": None})
        self.assertIsNone(sm.find_held_cigarette(char))
        self.assertIsNone(sm.find_held_lighter(char))

    def test_distinguishes_roles(self):
        cig = _cigarette()
        lig = _lighter()
        char = _FakeCharacter(hands={"left_hand": cig, "right_hand": lig})
        self.assertIs(sm.find_held_cigarette(char), cig)
        self.assertIs(sm.find_held_lighter(char), lig)


# ---------------------------------------------------------------------
# Lit state
# ---------------------------------------------------------------------


class TestIsSmokableLegacyMigration(TestCase):
    """The new delivery-method tag is the source of truth, but
    pre-#456 cigarettes still carry the old ``("cigarette",
    "item_role")`` tag.  ``is_smokable`` migrates them on first
    access."""

    def test_new_tag_recognised(self):
        item = _cigarette()
        self.assertTrue(sm.is_smokable(item))

    def test_legacy_tag_migrated_in_place(self):
        item = _FakeItem(
            role_tags=[(sm.CIGARETTE_ROLE, sm.ITEM_ROLE_CATEGORY)],
        )
        # First access returns True AND mutates the tag set.
        self.assertTrue(sm.is_smokable(item))
        self.assertTrue(
            item.tags.has(
                sm.SMOKE_DELIVERY, category=sm.DELIVERY_METHOD_CATEGORY,
            )
        )
        self.assertFalse(
            item.tags.has(
                sm.CIGARETTE_ROLE, category=sm.ITEM_ROLE_CATEGORY,
            )
        )

    def test_no_tag_is_not_smokable(self):
        item = _FakeItem(role_tags=[])
        self.assertFalse(sm.is_smokable(item))


class TestGetSubstance(TestCase):
    def test_reads_substance_attribute(self):
        item = _cigarette(substance="tobacco_noir")
        self.assertEqual(sm.get_substance(item), "tobacco_noir")

    def test_legacy_brand_promoted_to_substance(self):
        """Pre-#456 cigarettes stored the identifier in ``db.brand``.
        ``get_substance`` returns it AND copies the value to
        ``db.substance`` so future reads see a single field."""
        item = _FakeItem(
            role_tags=[(sm.SMOKE_DELIVERY, sm.DELIVERY_METHOD_CATEGORY)],
            legacy_brand="noir",
        )
        self.assertEqual(sm.get_substance(item), "noir")
        # Now stamped onto db.substance.
        self.assertEqual(item.db.substance, "noir")

    def test_returns_none_when_neither_attribute_set(self):
        item = _FakeItem(
            role_tags=[(sm.SMOKE_DELIVERY, sm.DELIVERY_METHOD_CATEGORY)],
            substance=None,
        )
        # Clear the substance the helper might have stamped in init.
        item.db = _FakeDB()
        self.assertIsNone(sm.get_substance(item))


class TestLitState(TestCase):
    def test_unlit_by_default(self):
        cig = _cigarette()
        self.assertFalse(sm.is_lit(cig))

    def test_set_lit_true(self):
        cig = _cigarette()
        sm.set_lit(cig, True)
        self.assertTrue(sm.is_lit(cig))

    def test_set_lit_false(self):
        cig = _cigarette()
        sm.set_lit(cig, True)
        sm.set_lit(cig, False)
        self.assertFalse(sm.is_lit(cig))


# ---------------------------------------------------------------------
# Message pickers
# ---------------------------------------------------------------------


class TestMessagePicker(TestCase):
    def test_neutral_picks_from_neutral_bank(self):
        self_msg, room_template = sm.pick_smoke_message(
            sm.SUBSTANCE_TOBACCO_NEUTRAL,
        )
        self.assertIn(
            (self_msg, room_template),
            sm.SMOKE_MESSAGES[sm.SUBSTANCE_TOBACCO_NEUTRAL],
        )

    def test_noir_picks_from_noir_bank(self):
        self_msg, room_template = sm.pick_smoke_message(
            sm.SUBSTANCE_TOBACCO_NOIR,
        )
        self.assertIn(
            (self_msg, room_template),
            sm.SMOKE_MESSAGES[sm.SUBSTANCE_TOBACCO_NOIR],
        )

    def test_unknown_substance_falls_back_to_neutral(self):
        self_msg, room_template = sm.pick_smoke_message("unknown-substance")
        self.assertIn(
            (self_msg, room_template),
            sm.SMOKE_MESSAGES[sm.SUBSTANCE_TOBACCO_NEUTRAL],
        )

    def test_legacy_brand_keys_still_resolve(self):
        """Pre-#456 cigarettes had ``brand=\"neutral\"`` /
        ``brand=\"noir\"`` — the picker honours those values via
        the legacy mapping."""
        legacy_neutral, _ = sm.pick_smoke_message("neutral")
        legacy_noir, _ = sm.pick_smoke_message("noir")
        all_neutral_self = [
            s for s, _ in sm.SMOKE_MESSAGES[sm.SUBSTANCE_TOBACCO_NEUTRAL]
        ]
        all_noir_self = [
            s for s, _ in sm.SMOKE_MESSAGES[sm.SUBSTANCE_TOBACCO_NOIR]
        ]
        self.assertIn(legacy_neutral, all_neutral_self)
        self.assertIn(legacy_noir, all_noir_self)

    def test_room_templates_use_actor_placeholder(self):
        for brand, bank in sm.SMOKE_MESSAGES.items():
            for self_msg, room in bank:
                self.assertIn(
                    "{actor}", room,
                    f"{brand!r}: room template missing {{actor}}: "
                    f"{room!r}",
                )


# ---------------------------------------------------------------------
# CmdLight
# ---------------------------------------------------------------------


class TestCmdLight(TestCase):
    def _run(self, caller, args):
        from commands.CmdSmoke import CmdLight
        cmd = CmdLight()
        cmd.caller = caller
        cmd.args = " " + args  # Evennia passes the leading space
        # Patch msg_room_identity to a no-op for unit isolation.
        with patch("commands.CmdSmoke.msg_room_identity") as broadcast:
            cmd.func()
        return broadcast

    def test_rejects_without_lighter(self):
        room = _FakeRoom()
        caller = _FakeCharacter(location=room, hands={"left_hand": _cigarette()})
        room.contents.append(caller)
        self._run(caller, "cigarette")
        self.assertTrue(any("lighter" in m for m in caller.msgs))

    def test_self_light_marks_cigarette_lit(self):
        room = _FakeRoom()
        cig = _cigarette()
        caller = _FakeCharacter(
            location=room,
            hands={"left_hand": cig, "right_hand": _lighter()},
        )
        room.contents.append(caller)
        self._run(caller, "cigarette")
        self.assertTrue(sm.is_lit(cig))

    def test_self_light_already_lit_rejects(self):
        room = _FakeRoom()
        cig = _cigarette()
        sm.set_lit(cig, True)
        caller = _FakeCharacter(
            location=room,
            hands={"left_hand": cig, "right_hand": _lighter()},
        )
        room.contents.append(caller)
        self._run(caller, "cigarette")
        self.assertTrue(any("already lit" in m for m in caller.msgs))

    def test_other_light_routes_via_identity(self):
        room = _FakeRoom()
        target_cig = _cigarette(substance="tobacco_noir")
        target = _FakeCharacter(
            key="Bob", location=room,
            hands={"left_hand": target_cig},
        )
        caller = _FakeCharacter(
            location=room,
            hands={"left_hand": _lighter()},
        )
        room.contents.extend([caller, target])
        # Patch identity resolver to return our target deterministically.
        with patch(
            "commands.CmdSmoke.resolve_character_target",
            return_value=target,
        ):
            self._run(caller, "bob's cigarette")
        self.assertTrue(sm.is_lit(target_cig))
        # Target was msg'd.
        self.assertTrue(any("cigarette" in m for m in target.msgs))


# ---------------------------------------------------------------------
# CmdSmoke
# ---------------------------------------------------------------------


class TestCmdSmoke(TestCase):
    def _run(self, caller, args):
        from commands.CmdSmoke import CmdSmoke
        cmd = CmdSmoke()
        cmd.caller = caller
        cmd.args = " " + args
        with patch("commands.CmdSmoke.msg_room_identity"):
            cmd.func()

    def _setup(self, *, substance="tobacco_neutral", uses_left=6, lit=True):
        room = _FakeRoom()
        cig = _cigarette(substance=substance, uses_left=uses_left, max_uses=6)
        if lit:
            sm.set_lit(cig, True)
        caller = _FakeCharacter(
            location=room, hands={"left_hand": cig},
        )
        room.contents.append(caller)
        return caller, cig

    def test_requires_lit(self):
        caller, _cig = self._setup(lit=False)
        self._run(caller, "cigarette")
        self.assertTrue(any("isn't lit" in m for m in caller.msgs))

    def test_decrements_uses_left(self):
        caller, cig = self._setup(uses_left=6)
        self._run(caller, "cigarette")
        self.assertEqual(cig.attributes.get("uses_left"), 5)
        self.assertFalse(cig.deleted)

    def test_destroys_on_final_puff(self):
        caller, cig = self._setup(uses_left=1)
        self._run(caller, "cigarette")
        self.assertEqual(cig.attributes.get("uses_left"), 0)
        self.assertTrue(cig.deleted)
        # Burnout message went out.
        joined = "\n".join(caller.msgs)
        self.assertTrue(
            "spent" in joined or "burns down" in joined
            or "tumbles" in joined,
            joined,
        )


# ---------------------------------------------------------------------
# CmdSnuff
# ---------------------------------------------------------------------


class TestCmdSnuff(TestCase):
    def _run(self, caller, args):
        from commands.CmdSmoke import CmdSnuff
        cmd = CmdSnuff()
        cmd.caller = caller
        cmd.args = " " + args
        with patch("commands.CmdSmoke.msg_room_identity"):
            cmd.func()

    def test_clears_lit_state(self):
        room = _FakeRoom()
        cig = _cigarette()
        sm.set_lit(cig, True)
        caller = _FakeCharacter(
            location=room, hands={"left_hand": cig},
        )
        room.contents.append(caller)
        self._run(caller, "cigarette")
        self.assertFalse(sm.is_lit(cig))

    def test_rejects_unlit(self):
        room = _FakeRoom()
        cig = _cigarette()
        caller = _FakeCharacter(
            location=room, hands={"left_hand": cig},
        )
        room.contents.append(caller)
        self._run(caller, "cigarette")
        self.assertTrue(any("isn't lit" in m for m in caller.msgs))
