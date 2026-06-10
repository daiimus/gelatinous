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
    item = MagicMock(spec=["key", "get_display_name", "delete"])
    item.key = key
    # Stub get_display_name so caller-side first-person msgs don't blow up.
    item.get_display_name = lambda looker=None: key
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
