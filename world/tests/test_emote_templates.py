"""
Tests for Emote Phase 5: Pre-Built Emote Templates.

Tests the emote template dictionary, command factory, and generated
social commands (nod, shrug, wave, etc.).

Run via::

    evennia test world.tests.test_emote_templates

All test cases match the specification in
``specs/EMOTE_POSE_SPEC.md`` §Pre-Built Emote Templates.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from world.emote_templates import (
    EMOTE_TEMPLATES,
    SOCIAL_COMMANDS,
    _actor_preposition,
    _actor_verb,
    _make_social_cmd,
)


# ===================================================================
# Helpers — lightweight character / room stand-ins
# ===================================================================


def _make_character(
    *,
    key="Jorge Jackson",
    sex="male",
    height="tall",
    build="lean",
    sdesc_keyword=None,
    hair_color=None,
    hair_style=None,
    sleeve_uid="uid-abc-123",
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
    char.hair_color = hair_color
    char.hair_style = hair_style
    char.sleeve_uid = sleeve_uid
    char.recognition_memory = (
        recognition_memory if recognition_memory is not None else {}
    )

    # Hands / clothing
    char.hands = {"left": None, "right": None}
    char.worn_items = {}

    def _coverage_map():
        coverage = {}
        if char.worn_items:
            for loc, items in char.worn_items.items():
                if items:
                    coverage[loc] = items[0]
        return coverage

    char._build_clothing_coverage_map = _coverage_map

    # Bind real methods
    char.get_distinguishing_feature = (
        lambda: Character.get_distinguishing_feature(char)
    )
    char.get_sdesc = lambda: Character.get_sdesc(char)
    char.get_display_name = (
        lambda looker=None, **kw: Character.get_display_name(
            char, looker, **kw
        )
    )

    # gender property
    sex_val = (sex or "ambiguous").lower().strip()
    if sex_val in ("male", "man", "masculine", "m"):
        type(char).gender = PropertyMock(return_value="male")
    elif sex_val in ("female", "woman", "feminine", "f"):
        type(char).gender = PropertyMock(return_value="female")
    else:
        type(char).gender = PropertyMock(return_value="neutral")

    return char


def _make_room(contents):
    """Build a mock room with the given contents list."""
    room = MagicMock()
    room.contents = contents
    return room


# ===================================================================
# Tests: Template Dictionary
# ===================================================================


class TestEmoteTemplates(TestCase):
    """Validate the EMOTE_TEMPLATES dictionary structure."""

    def test_all_templates_have_solo(self):
        """Every template must define a solo form."""
        for kw, templates in EMOTE_TEMPLATES.items():
            self.assertIn(
                "solo", templates, f"Template '{kw}' missing 'solo' key"
            )

    def test_solo_templates_contain_actor(self):
        """Solo templates must contain {actor} placeholder."""
        for kw, templates in EMOTE_TEMPLATES.items():
            self.assertIn(
                "{actor}",
                templates["solo"],
                f"Solo template for '{kw}' missing {{actor}}",
            )

    def test_targeted_templates_contain_both_placeholders(self):
        """Targeted templates must contain {actor} and {target}."""
        for kw, templates in EMOTE_TEMPLATES.items():
            if "targeted" not in templates:
                continue
            targeted = templates["targeted"]
            self.assertIn(
                "{actor}",
                targeted,
                f"Targeted template for '{kw}' missing {{actor}}",
            )
            self.assertIn(
                "{target}",
                targeted,
                f"Targeted template for '{kw}' missing {{target}}",
            )

    def test_expected_keywords_present(self):
        """The spec-defined keywords are all present."""
        expected = {"nod", "shrug", "laugh", "sigh", "smile", "wave",
                    "bow", "frown"}
        self.assertEqual(expected, set(EMOTE_TEMPLATES.keys()))

    def test_sigh_has_no_targeted(self):
        """Sigh is solo-only per spec."""
        self.assertNotIn("targeted", EMOTE_TEMPLATES["sigh"])


# ===================================================================
# Tests: Command Factory
# ===================================================================


class TestCommandFactory(TestCase):
    """Tests for the _make_social_cmd factory function."""

    def test_creates_command_class(self):
        """Factory returns a Command subclass."""
        from evennia.commands.command import Command

        cls = _make_social_cmd("nod", "{actor} nods.")
        self.assertTrue(issubclass(cls, Command))

    def test_command_key_matches_keyword(self):
        """Generated command key matches the keyword."""
        cls = _make_social_cmd("nod", "{actor} nods.")
        self.assertEqual(cls.key, "nod")

    def test_command_help_category(self):
        """Generated command has Social help category."""
        cls = _make_social_cmd("nod", "{actor} nods.")
        # Evennia normalizes help_category to lowercase
        self.assertEqual(cls.help_category.lower(), "social")

    def test_class_name_set(self):
        """Factory sets a descriptive class name."""
        cls = _make_social_cmd("wave", "{actor} waves.")
        self.assertEqual(cls.__name__, "CmdSocial_Wave")

    def test_actor_verb_defaults_to_keyword(self):
        """_actor_verb returns keyword when no override exists."""
        self.assertEqual(_actor_verb("nod"), "nod")
        self.assertEqual(_actor_verb("laugh"), "laugh")

    def test_actor_preposition_defaults_to_at(self):
        """_actor_preposition defaults to 'at'."""
        self.assertEqual(_actor_preposition("nod"), "at")
        self.assertEqual(_actor_preposition("smile"), "at")

    def test_actor_preposition_bow_override(self):
        """Bow has a custom preposition."""
        self.assertEqual(_actor_preposition("bow"), "respectfully to")


# ===================================================================
# Tests: Generated SOCIAL_COMMANDS list
# ===================================================================


class TestSocialCommandsList(TestCase):
    """Tests for the pre-generated SOCIAL_COMMANDS list."""

    def test_correct_count(self):
        """One command per template keyword."""
        self.assertEqual(len(SOCIAL_COMMANDS), len(EMOTE_TEMPLATES))

    def test_all_keywords_covered(self):
        """Every template keyword has a corresponding command."""
        keys = {cls.key for cls in SOCIAL_COMMANDS}
        self.assertEqual(keys, set(EMOTE_TEMPLATES.keys()))

    def test_commands_are_unique_classes(self):
        """Each command is a distinct class."""
        classes = set(SOCIAL_COMMANDS)
        self.assertEqual(len(classes), len(SOCIAL_COMMANDS))


# ===================================================================
# Tests: Social Command Execution — Solo Mode
# ===================================================================


class TestSocialCmdSolo(TestCase):
    """Test the solo (no-target) execution of social commands."""

    def setUp(self):
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.observer = _make_character(
            key="Alice Smith",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
            recognition_memory={},
        )
        self.room = _make_room([self.jorge, self.observer])
        self.jorge.location = self.room

        # Make search available on jorge
        self.jorge.search = MagicMock()

    def _run_cmd(self, keyword, args=""):
        """Instantiate and execute a social command."""
        cmd_cls = None
        for cls in SOCIAL_COMMANDS:
            if cls.key == keyword:
                cmd_cls = cls
                break
        self.assertIsNotNone(cmd_cls, f"No command for '{keyword}'")

        cmd = cmd_cls()
        cmd.caller = self.jorge
        cmd.args = args
        cmd.raw_string = f"{keyword} {args}".strip()
        cmd.func()

    def test_nod_solo_actor_sees_you_nod(self):
        """Actor sees 'You nod.' for solo nod."""
        self._run_cmd("nod")
        self.jorge.msg.assert_any_call("You nod.")

    def test_shrug_solo_actor_sees_you_shrug(self):
        """Actor sees 'You shrug.' for solo shrug."""
        self._run_cmd("shrug")
        self.jorge.msg.assert_any_call("You shrug.")

    def test_laugh_solo_actor_sees_you_laugh(self):
        """Actor sees 'You laugh.' for solo laugh."""
        self._run_cmd("laugh")
        self.jorge.msg.assert_any_call("You laugh.")

    def test_sigh_solo_actor_sees_you_sigh(self):
        """Actor sees 'You sigh.' for solo sigh."""
        self._run_cmd("sigh")
        self.jorge.msg.assert_any_call("You sigh.")

    def test_solo_observer_sees_sdesc(self):
        """Observer who doesn't know actor sees sdesc-based message."""
        self._run_cmd("nod")
        self.observer.msg.assert_called_once()
        msg_text = self.observer.msg.call_args[1].get(
            "text",
            self.observer.msg.call_args[0][0]
            if self.observer.msg.call_args[0]
            else None,
        )
        # tall + lean → "gaunt", sdesc_keyword "man"
        self.assertIn("gaunt man", msg_text.lower())
        self.assertIn("nods", msg_text)

    def test_solo_observer_gets_pose_type(self):
        """Observer msg kwargs include type='pose'."""
        self._run_cmd("wave")
        self.observer.msg.assert_called_once()
        kwargs = self.observer.msg.call_args[1]
        self.assertEqual(kwargs.get("type"), "pose")

    def test_solo_observer_gets_from_obj(self):
        """Observer msg kwargs include from_obj=caller."""
        self._run_cmd("wave")
        kwargs = self.observer.msg.call_args[1]
        self.assertIs(kwargs.get("from_obj"), self.jorge)

    def test_solo_actor_excluded_from_room_broadcast(self):
        """Actor does not receive the room broadcast (only the self-view)."""
        self._run_cmd("smile")
        # Actor gets exactly one msg call: "You smile."
        actor_calls = self.jorge.msg.call_args_list
        self.assertEqual(len(actor_calls), 1)
        self.assertEqual(actor_calls[0][0][0], "You smile.")

    def test_observer_sees_capitalized_sdesc(self):
        """Observer message starts with capitalized sdesc (A gaunt man)."""
        self._run_cmd("frown")
        msg_text = self.observer.msg.call_args[1].get(
            "text",
            self.observer.msg.call_args[0][0]
            if self.observer.msg.call_args[0]
            else None,
        )
        # msg_room_identity auto-capitalizes the first placeholder
        self.assertTrue(
            msg_text.startswith("A gaunt man"),
            f"Expected message to start with 'A gaunt man', got: {msg_text}",
        )


# ===================================================================
# Tests: Social Command Execution — Targeted Mode
# ===================================================================


class TestSocialCmdTargeted(TestCase):
    """Test the targeted execution of social commands."""

    def setUp(self):
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        self.observer_knows_both = _make_character(
            key="Alice Smith",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
            recognition_memory={
                "uid-jorge": {"assigned_name": "Jorge"},
                "uid-maria": {"assigned_name": "Maria"},
            },
        )
        self.observer_knows_neither = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )
        self.room = _make_room([
            self.jorge,
            self.maria,
            self.observer_knows_both,
            self.observer_knows_neither,
        ])
        self.jorge.location = self.room

        # search returns maria
        self.jorge.search = MagicMock(return_value=self.maria)

    def _run_cmd(self, keyword, args=""):
        """Instantiate and execute a social command."""
        cmd_cls = None
        for cls in SOCIAL_COMMANDS:
            if cls.key == keyword:
                cmd_cls = cls
                break
        self.assertIsNotNone(cmd_cls, f"No command for '{keyword}'")

        cmd = cmd_cls()
        cmd.caller = self.jorge
        cmd.args = args
        cmd.raw_string = f"{keyword} {args}".strip()
        cmd.func()

    def test_nod_targeted_actor_self_view(self):
        """Actor sees 'You nod at <target_name>.' for targeted nod."""
        self._run_cmd("nod", "maria")
        # Maria's display name as seen by jorge
        target_name = self.maria.get_display_name(self.jorge)
        expected = f"You nod at {target_name}."
        self.jorge.msg.assert_any_call(expected)

    def test_bow_targeted_actor_sees_custom_preposition(self):
        """Actor sees 'You bow respectfully to <target>.' for bow."""
        self._run_cmd("bow", "maria")
        target_name = self.maria.get_display_name(self.jorge)
        expected = f"You bow respectfully to {target_name}."
        self.jorge.msg.assert_any_call(expected)

    def test_targeted_observer_who_knows_both(self):
        """Observer who knows both sees assigned names."""
        self._run_cmd("nod", "maria")
        msg_text = self.observer_knows_both.msg.call_args[1].get(
            "text",
            self.observer_knows_both.msg.call_args[0][0]
            if self.observer_knows_both.msg.call_args[0]
            else None,
        )
        self.assertIn("Jorge", msg_text)
        self.assertIn("Maria", msg_text)
        self.assertIn("nods at", msg_text)

    def test_targeted_observer_who_knows_neither(self):
        """Observer who knows neither sees sdescs."""
        self._run_cmd("smile", "maria")
        msg_text = self.observer_knows_neither.msg.call_args[1].get(
            "text",
            self.observer_knows_neither.msg.call_args[0][0]
            if self.observer_knows_neither.msg.call_args[0]
            else None,
        )
        # jorge: tall+lean → gaunt man
        self.assertIn("gaunt man", msg_text.lower())
        # maria: short+athletic → compact woman
        self.assertIn("compact woman", msg_text.lower())
        self.assertIn("smiles at", msg_text)

    def test_targeted_uses_caller_search(self):
        """Target resolution goes through caller.search()."""
        self._run_cmd("wave", "maria")
        self.jorge.search.assert_called_once_with("maria")

    def test_targeted_search_failure_aborts(self):
        """When search returns None, command aborts gracefully."""
        self.jorge.search.return_value = None
        self._run_cmd("wave", "nobody")
        # Actor should NOT get a self-view message
        self.jorge.msg.assert_not_called()
        # Observers should NOT get broadcast
        self.observer_knows_both.msg.assert_not_called()

    def test_targeted_observer_gets_pose_type(self):
        """Observer msg kwargs include type='pose' for targeted form."""
        self._run_cmd("laugh", "maria")
        kwargs = self.observer_knows_both.msg.call_args[1]
        self.assertEqual(kwargs.get("type"), "pose")

    def test_targeted_actor_excluded_from_broadcast(self):
        """Actor doesn't receive the room broadcast."""
        self._run_cmd("nod", "maria")
        # Actor gets exactly one msg call (the self-view)
        actor_calls = self.jorge.msg.call_args_list
        self.assertEqual(len(actor_calls), 1)


# ===================================================================
# Tests: Solo-Only Command — Targeted Rejected
# ===================================================================


class TestSoloOnlyCommand(TestCase):
    """Test that solo-only commands reject target arguments."""

    def setUp(self):
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.room = _make_room([self.jorge])
        self.jorge.location = self.room
        self.jorge.search = MagicMock()

    def test_sigh_with_target_shows_usage(self):
        """Sigh with args shows usage error (no targeted template)."""
        cmd_cls = None
        for cls in SOCIAL_COMMANDS:
            if cls.key == "sigh":
                cmd_cls = cls
                break
        self.assertIsNotNone(cmd_cls)

        cmd = cmd_cls()
        cmd.caller = self.jorge
        cmd.args = "someone"
        cmd.raw_string = "sigh someone"
        cmd.func()

        self.jorge.msg.assert_called_once_with("Usage: sigh")


# ===================================================================
# Tests: No Location Edge Case
# ===================================================================


class TestNoLocation(TestCase):
    """Test that commands handle missing location gracefully."""

    def setUp(self):
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self.jorge.location = None

    def test_solo_no_location(self):
        """Solo command with no location sends error."""
        cmd_cls = None
        for cls in SOCIAL_COMMANDS:
            if cls.key == "nod":
                cmd_cls = cls
                break

        cmd = cmd_cls()
        cmd.caller = self.jorge
        cmd.args = ""
        cmd.raw_string = "nod"
        cmd.func()

        self.jorge.msg.assert_called_once_with(
            "You have no location to emote in."
        )
