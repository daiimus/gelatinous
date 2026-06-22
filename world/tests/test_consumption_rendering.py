"""
Tests for Phase 2 per-observer rendering in CmdConsumption.

Verifies the inject / apply / bandage / eat / drink / inhale / smoke
verbs route their room broadcasts through :func:`msg_room_identity`
so that each observer sees the actor (and optional target) rendered
according to their own recognition memory.

Run via::

    evennia test world.tests.test_consumption_rendering

Aligns with ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Phase 2 —
Consistency" Conversion Status.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

from world.tests._identity_helpers import (
    apparent_uid_for,
    prepare_mock_for_apparent_uid,
)


# ===================================================================
# Mock builders (mirrors world/tests/test_communication.py)
# ===================================================================


def _make_character(
    *,
    key,
    sex="male",
    height="tall",
    build="lean",
    sdesc_keyword="man",
    sleeve_uid,
    recognition_memory=None,
):
    """Build a mock character with identity methods bound."""
    from typeclasses.characters import Character

    char = MagicMock(spec=Character)
    char.key = key
    char.sex = sex
    char.height = height
    char.build = build
    char.sdesc_keyword = sdesc_keyword
    char.hair_color = None
    char.hair_style = None
    char.sleeve_uid = sleeve_uid
    char.recognition_memory = (
        recognition_memory if recognition_memory is not None else {}
    )
    char.hands = {"left": None, "right": None}
    char.worn_items = {}
    char._build_clothing_coverage_map = lambda: {}

    char.get_distinguishing_feature = (
        lambda: Character.get_distinguishing_feature(char)
    )
    char.get_sdesc = lambda: Character.get_sdesc(char)
    char.get_display_name = (
        lambda looker=None, **kw: Character.get_display_name(
            char, looker, **kw
        )
    )

    sex_val = (sex or "ambiguous").lower().strip()
    if sex_val in ("male", "man", "masculine", "m"):
        type(char).gender = PropertyMock(return_value="male")
    elif sex_val in ("female", "woman", "feminine", "f"):
        type(char).gender = PropertyMock(return_value="female")
    else:
        type(char).gender = PropertyMock(return_value="neutral")

    prepare_mock_for_apparent_uid(char)
    return char


def _make_room(contents):
    room = MagicMock()
    room.contents = contents
    return room


def _make_item(key="medkit"):
    """Non-character item (no msg attribute, deliberately empty spec)."""
    item = MagicMock(spec=["key", "get_display_name", "delete", "db"])
    item.key = key
    # Stub get_display_name so caller-side first-person msgs don't blow up.
    item.get_display_name = lambda looker=None: key
    # No substance — the #487 dose hook no-ops on None.
    item.db = MagicMock()
    item.db.substance = None
    # Not a recipe-composed drink — the drink branch (#643) must no-op.
    item.db.drink_effects = None
    return item


# ===================================================================
# Helpers
# ===================================================================


def _observer_text(observer):
    """Pull the text= kwarg or first positional arg from observer.msg()."""
    if not observer.msg.call_args:
        return ""
    args = observer.msg.call_args
    return args.kwargs.get("text") or (args.args[0] if args.args else "")


def _run_consumption_cmd(
    cmd_cls,
    *,
    caller,
    target,
    item,
    args="medkit",
    body_location=None,
    is_medical=True,
    medical_type="pain_relief",
    cmdstring=None,
):
    """Invoke a consumption command's func() with stubbed parsing/effects.

    Patches :meth:`ConsumptionCommand.get_item_and_target`,
    :meth:`check_medical_requirements`, :meth:`execute_treatment`,
    and module-level ``is_medical_item`` / ``get_medical_type`` so the
    test runs the room-broadcast branch end-to-end without touching
    the medical state machine or the live DB.

    ``CmdBandage`` uses its own ``parse()`` pipeline and ``caller.search``
    instead of ``get_item_and_target``; this helper handles both flows.
    """
    cmd = cmd_cls()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmdstring or cmd_cls.key
    cmd.body_location = body_location

    # CmdBandage uses its own parsed attrs + caller.search
    is_bandage = cmd_cls.__name__ == "CmdBandage"
    if is_bandage:
        cmd.item_name = "medkit"
        cmd.target_name = None if caller is target else "target"
        caller.search = MagicMock(return_value=[item])

    parse_result = {
        "item": item,
        "target": target,
        "body_location": body_location,
        "errors": [],
    }

    patches = [
        patch.object(cmd, "check_medical_requirements", return_value=[]),
        patch.object(cmd, "execute_treatment", return_value="ok"),
        patch(
            "commands.CmdConsumption.is_medical_item",
            return_value=is_medical,
        ),
        patch(
            "commands.CmdConsumption.get_medical_type",
            return_value=medical_type,
        ),
        # Delivery gating (#474) is tag-driven and tested in
        # test_consumables; these tests exercise the rendering branch.
        patch(
            "commands.CmdConsumption.supports_delivery",
            return_value=True,
        ),
    ]
    if not is_bandage:
        patches.insert(
            0, patch.object(cmd, "get_item_and_target", return_value=parse_result)
        )
    else:
        # Bandage resolves target via resolve_character_target when not self
        patches.append(
            patch(
                "commands.CmdConsumption.resolve_character_target",
                return_value=target,
            )
        )

    # Apply all patches via nested context
    from contextlib import ExitStack

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        cmd.func()


# ===================================================================
# Tests
# ===================================================================


class TestChugDevourFullDose(TestCase):
    """chug/devour stack every remaining use's dose at once."""

    def test_drink_effects_scaled_by_uses(self):
        from commands.CmdConsumption import CmdChug
        cmd = CmdChug()
        item = MagicMock()
        item.db.uses_left = 3
        item.db.drink_effects = {"alcohol": 1}
        item.db.drink_taste = "It scours the throat."
        target = MagicMock()
        msgs = []
        target.msg = lambda *a, **k: msgs.append(a[0] if a else k.get("text"))
        with patch("world.substances.apply_substance",
                   return_value={"feedback": ["A slow heaviness."]}) as ap:
            cmd._apply_full_dose(item, target)
        ap.assert_called_once_with(target, "alcohol", doses=3)   # 1 × 3 sips
        self.assertTrue(any("scours the throat" in m for m in msgs))

    def test_medical_item_is_guarded(self):
        from commands.CmdConsumption import CmdChug
        cmd = CmdChug()
        caller = MagicMock()
        caller.msg = MagicMock()
        cmd.caller = caller
        item = MagicMock()
        item.get_display_name = lambda looker=None: "a stimpak"
        parse = {"item": item, "target": caller, "errors": []}
        with patch.object(cmd, "get_item_and_target", return_value=parse), \
             patch("commands.CmdConsumption.supports_delivery", return_value=True), \
             patch("commands.CmdConsumption.is_medical_item", return_value=True), \
             patch.object(cmd, "_apply_full_dose") as full:
            cmd.args = "stimpak"
            cmd.func()
        full.assert_not_called()
        self.assertIn("proper dosing", caller.msg.call_args[0][0])

    def test_legacy_substance_scaled_by_uses(self):
        from commands.CmdConsumption import CmdDevour
        cmd = CmdDevour()
        item = MagicMock()
        item.db.uses_left = 2
        item.db.drink_effects = None
        item.db.substance = "opium"
        target = MagicMock()
        target.msg = MagicMock()
        with patch("world.substances.apply_substance",
                   return_value={"feedback": []}) as ap:
            cmd._apply_full_dose(item, target)
        ap.assert_called_once_with(target, "opium", doses=2)


class TestFlavourOnlyDrinkTaste(TestCase):
    """A no-effect drink (soda, black recyc) still surfaces its taste."""

    def test_empty_effects_still_shows_taste(self):
        from commands.CmdConsumption import CmdDrink
        cmd = CmdDrink()
        item = MagicMock()
        item.db.drink_effects = {}      # flavour-only pour
        item.db.drink_taste = "It tastes of clean soda fizz."
        target = MagicMock()
        msgs = []
        target.msg = lambda *a, **k: msgs.append(a[0] if a else k.get("text"))
        with patch("world.substances.apply_substance") as ap:
            cmd._apply_substance_dose(item, target)
        self.assertIn("It tastes of clean soda fizz.", msgs)
        ap.assert_not_called()

    def test_non_drink_uses_substance_path(self):
        from commands.CmdConsumption import CmdDrink
        cmd = CmdDrink()
        item = MagicMock()
        item.db.drink_effects = None    # not a recipe-composed drink
        item.db.substance = None
        target = MagicMock()
        target.msg = MagicMock()
        with patch("world.substances.apply_substance",
                   return_value={"feedback": []}) as ap:
            cmd._apply_substance_dose(item, target)
        ap.assert_called_once()


class TestOrdinalItemParse(TestCase):
    """`drink 2nd mug` keeps the ordinal attached to its noun for search."""

    def _cmd(self):
        from commands.CmdConsumption import CmdDrink
        cmd = CmdDrink()
        caller = MagicMock()
        caller.ORDINAL_WORDS = {"first": 1, "second": 2, "1st": 1, "2nd": 2}
        caller._searched = []
        def fake_search(q, location=None, quiet=False):
            caller._searched.append(q)
            return [MagicMock()]
        caller.search = fake_search
        cmd.caller = caller
        return cmd, caller

    def test_numeric_ordinal_kept_with_noun(self):
        cmd, caller = self._cmd()
        res = cmd.get_item_and_target("2nd mug", require_medical=False)
        self.assertEqual(caller._searched, ["2nd mug"])
        self.assertEqual(res["target"], caller)  # no bogus target

    def test_word_ordinal_kept_with_noun(self):
        cmd, caller = self._cmd()
        cmd.get_item_and_target("second rotgut", require_medical=False)
        self.assertEqual(caller._searched, ["second rotgut"])

    def test_plain_item_then_target_still_splits(self):
        cmd, caller = self._cmd()
        with patch("commands.CmdConsumption.resolve_character_target",
                   return_value=MagicMock()) as rct:
            cmd.get_item_and_target("pill alice", require_medical=False)
        self.assertEqual(caller._searched, ["pill"])
        rct.assert_called_once()
        self.assertEqual(rct.call_args[0][1], "alice")


class TestConsumptionPerObserverRendering(TestCase):
    """Each consumption verb broadcasts per-observer-rendered text."""

    def setUp(self):
        self.actor = _make_character(
            key="Jorge Jackson",
            sleeve_uid="uid-jorge",
            height="tall",
            build="lean",
            sdesc_keyword="man",
        )
        self.patient = _make_character(
            key="Maria Santos",
            sex="female",
            sleeve_uid="uid-maria",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
        )
        self.knower = _make_character(
            key="Alice",
            sex="female",
            sleeve_uid="uid-alice",
            recognition_memory={
                apparent_uid_for(self.actor): {"assigned_name": "Jorge"},
                apparent_uid_for(self.patient): {"assigned_name": "Maria"},
            },
        )
        self.stranger = _make_character(
            key="Bob",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

        self.item = _make_item("medkit")
        self.room = _make_room(
            [self.actor, self.patient, self.knower, self.stranger]
        )
        self.actor.location = self.room
        self.patient.location = self.room

        # Patient needs a medical_state for the requirement passthrough,
        # though we patch check_medical_requirements anyway.
        self.actor.medical_state = MagicMock()
        self.patient.medical_state = MagicMock()
        self.actor.is_unconscious = lambda: False
        self.patient.is_unconscious = lambda: False

    # ---- inject --------------------------------------------------

    def test_inject_self_broadcast(self):
        from commands.CmdConsumption import CmdInject

        _run_consumption_cmd(
            CmdInject,
            caller=self.actor,
            target=self.actor,
            item=self.item,
        )

        self.assertIn("Jorge", _observer_text(self.knower))
        self.assertIn("medkit", _observer_text(self.knower))
        self.assertIn("gaunt man", _observer_text(self.stranger))

    def test_inject_other_broadcast(self):
        from commands.CmdConsumption import CmdInject

        _run_consumption_cmd(
            CmdInject,
            caller=self.actor,
            target=self.patient,
            item=self.item,
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("Maria", ktext)
        self.assertIn("medkit", ktext)
        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)
        self.assertIn("compact woman", stext)

    # ---- apply ---------------------------------------------------

    def test_apply_other_broadcast(self):
        from commands.CmdConsumption import CmdApply

        _run_consumption_cmd(
            CmdApply,
            caller=self.actor,
            target=self.patient,
            item=self.item,
            medical_type="wound_care",
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("Maria", ktext)
        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)
        self.assertIn("compact woman", stext)

    # ---- bandage -------------------------------------------------

    def test_bandage_self_broadcast(self):
        from commands.CmdConsumption import CmdBandage

        _run_consumption_cmd(
            CmdBandage,
            caller=self.actor,
            target=self.actor,
            item=self.item,
            body_location="left arm",
            medical_type="wound_care",
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("left arm", ktext)
        self.assertIn("gaunt man", _observer_text(self.stranger))

    # ---- eat -----------------------------------------------------

    def test_eat_self_broadcast(self):
        from commands.CmdConsumption import CmdEat

        _run_consumption_cmd(
            CmdEat,
            caller=self.actor,
            target=self.actor,
            item=self.item,
            is_medical=False,
            medical_type="food",
        )

        self.assertIn("Jorge", _observer_text(self.knower))
        self.assertIn("medkit", _observer_text(self.knower))
        self.assertIn("gaunt man", _observer_text(self.stranger))

    # ---- drink ---------------------------------------------------

    def test_drink_other_broadcast(self):
        from commands.CmdConsumption import CmdDrink

        _run_consumption_cmd(
            CmdDrink,
            caller=self.actor,
            target=self.patient,
            item=self.item,
            is_medical=False,
            medical_type="water",
        )

        ktext = _observer_text(self.knower)
        self.assertIn("Jorge", ktext)
        self.assertIn("Maria", ktext)
        stext = _observer_text(self.stranger)
        self.assertIn("gaunt man", stext)
        self.assertIn("compact woman", stext)

    # ---- inhale --------------------------------------------------

    def test_inhale_self_broadcast(self):
        from commands.CmdConsumption import CmdInhale

        _run_consumption_cmd(
            CmdInhale,
            caller=self.actor,
            target=self.actor,
            item=self.item,
            medical_type="oxygen",
        )

        self.assertIn("Jorge", _observer_text(self.knower))
        self.assertIn("gaunt man", _observer_text(self.stranger))

    # ---- smoke ---------------------------------------------------

    # ---- exclusion / first-person guard --------------------------

    def test_actor_and_patient_excluded_from_room_broadcast(self):
        """Actor and patient receive their own first/second-person msgs."""
        from commands.CmdConsumption import CmdInject

        _run_consumption_cmd(
            CmdInject,
            caller=self.actor,
            target=self.patient,
            item=self.item,
        )

        actor_texts = [
            (c.args[0] if c.args else c.kwargs.get("text", ""))
            for c in self.actor.msg.call_args_list
        ]
        self.assertTrue(
            any("You inject" in t for t in actor_texts),
            f"Actor missing first-person inject msg: {actor_texts}",
        )

        patient_texts = [
            (c.args[0] if c.args else c.kwargs.get("text", ""))
            for c in self.patient.msg.call_args_list
        ]
        self.assertTrue(
            any("into you" in t for t in patient_texts),
            f"Patient missing second-person msg: {patient_texts}",
        )
