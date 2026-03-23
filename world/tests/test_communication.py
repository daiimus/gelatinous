"""
Tests for Identity Phase 2b: msg_room_identity and communication commands.

Tests the ``msg_room_identity`` helper and custom ``CmdSay``,
``CmdWhisper``, and ``CmdEmote`` commands for per-observer identity
rendering.

Run via::

    evennia test world.tests.test_communication

All test cases match the specification in
``specs/EMOTE_POSE_SPEC.md`` and
``specs/IDENTITY_RECOGNITION_SPEC.md`` §msg_room_identity Helper.
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, call

from world.identity_utils import msg_room_identity


# ===================================================================
# Helpers — lightweight character / room stand-in
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


def _make_item(key="Knife"):
    """Build a non-character item that has no msg method."""
    item = MagicMock(spec=[])
    item.key = key
    return item


# ===================================================================
# Tests: msg_room_identity
# ===================================================================


class TestMsgRoomIdentity(TestCase):
    """Tests for the msg_room_identity helper."""

    def setUp(self):
        # Actor: Jorge — tall lean man → sdesc "gaunt man"
        self.jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        # Target: Maria — short athletic woman → sdesc "compact woman"
        self.maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="athletic",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        # Observer who knows both
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
        # Observer who knows neither
        self.observer_knows_neither = _make_character(
            key="Bob Doe",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={},
        )

    def test_per_observer_rendering(self):
        """Each observer sees appropriate names for actor and target."""
        room = _make_room([
            self.jorge, self.maria,
            self.observer_knows_both,
            self.observer_knows_neither,
        ])

        msg_room_identity(
            location=room,
            template="{actor} attacks {target} with a knife!",
            char_refs={"actor": self.jorge, "target": self.maria},
            exclude=[self.jorge, self.maria],
        )

        # Observer who knows both should see assigned names
        self.observer_knows_both.msg.assert_called_once()
        msg_text = self.observer_knows_both.msg.call_args[1].get(
            "text", self.observer_knows_both.msg.call_args[0][0]
            if self.observer_knows_both.msg.call_args[0] else None
        )
        self.assertIn("Jorge", msg_text)
        self.assertIn("Maria", msg_text)
        self.assertIn("with a knife!", msg_text)

        # Observer who knows neither should see sdescs
        self.observer_knows_neither.msg.assert_called_once()
        msg_text2 = self.observer_knows_neither.msg.call_args[1].get(
            "text", self.observer_knows_neither.msg.call_args[0][0]
            if self.observer_knows_neither.msg.call_args[0] else None
        )
        self.assertIn("gaunt man", msg_text2)
        self.assertIn("compact woman", msg_text2)

    def test_exclude_works(self):
        """Excluded characters should not receive the message."""
        room = _make_room([
            self.jorge, self.maria, self.observer_knows_both,
        ])

        msg_room_identity(
            location=room,
            template="{actor} waves.",
            char_refs={"actor": self.jorge},
            exclude=[self.jorge],
        )

        self.jorge.msg.assert_not_called()
        self.maria.msg.assert_called_once()
        self.observer_knows_both.msg.assert_called_once()

    def test_items_skipped(self):
        """Non-character objects without msg are skipped gracefully."""
        item = _make_item("Sword")
        room = _make_room([self.jorge, item, self.observer_knows_both])

        # Should not raise
        msg_room_identity(
            location=room,
            template="{actor} looks around.",
            char_refs={"actor": self.jorge},
            exclude=[self.jorge],
        )

        self.observer_knows_both.msg.assert_called_once()

    def test_kwargs_passed_through(self):
        """Extra kwargs (like type) are passed to observer.msg()."""
        room = _make_room([self.jorge, self.observer_knows_both])

        msg_room_identity(
            location=room,
            template="{actor} says something.",
            char_refs={"actor": self.jorge},
            exclude=[self.jorge],
            type="say",
        )

        call_kwargs = self.observer_knows_both.msg.call_args[1]
        self.assertEqual(call_kwargs.get("type"), "say")

    def test_no_exclude(self):
        """All room contents receive message when exclude is None."""
        room = _make_room([self.jorge, self.maria])

        msg_room_identity(
            location=room,
            template="{actor} stretches.",
            char_refs={"actor": self.jorge},
        )

        self.jorge.msg.assert_called_once()
        self.maria.msg.assert_called_once()

    def test_single_placeholder(self):
        """Template with only one character reference works."""
        room = _make_room([self.jorge, self.observer_knows_both])

        msg_room_identity(
            location=room,
            template="{actor} leaves north.",
            char_refs={"actor": self.jorge},
            exclude=[self.jorge],
        )

        msg_text = self.observer_knows_both.msg.call_args[1].get(
            "text", self.observer_knows_both.msg.call_args[0][0]
            if self.observer_knows_both.msg.call_args[0] else None
        )
        self.assertIn("Jorge", msg_text)
        self.assertIn("leaves north.", msg_text)


# ===================================================================
# Tests: CmdSay
# ===================================================================


class TestCmdSay(TestCase):
    """Tests for the identity-aware say command."""

    def _run_say(self, caller, speech, room_contents):
        """Helper to invoke CmdSay.func() with mocked state."""
        from commands.CmdCommunication import CmdSay

        cmd = CmdSay()
        cmd.caller = caller
        cmd.args = f" {speech}"
        cmd.cmdstring = "say"

        room = MagicMock()
        room.contents = room_contents
        caller.location = room

        cmd.func()

    def test_actor_sees_you_say(self):
        """Actor should see 'You say, \"...\"'."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice", sex="female", height="average",
            build="average", sleeve_uid="uid-alice",
        )
        self._run_say(jorge, "Hello!", [jorge, observer])

        jorge.msg.assert_called_once_with('You say, "Hello!"')

    def test_observer_sees_sdesc(self):
        """Observer who doesn't know the speaker sees sdesc."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice", sex="female", height="average",
            build="average", sleeve_uid="uid-alice",
            recognition_memory={},
        )
        self._run_say(jorge, "Hello!", [jorge, observer])

        # Observer should see sdesc-based name
        observer.msg.assert_called_once()
        call_kwargs = observer.msg.call_args[1]
        msg_text = call_kwargs.get("text", "")
        self.assertIn("says,", msg_text)
        self.assertIn("gaunt man", msg_text.lower())
        self.assertIn('"Hello!"', msg_text)

    def test_observer_sees_assigned_name(self):
        """Observer who has assigned a name sees that name."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice", sex="female", height="average",
            build="average", sleeve_uid="uid-alice",
            recognition_memory={
                "uid-jorge": {"assigned_name": "Jorge"},
            },
        )
        self._run_say(jorge, "Hello!", [jorge, observer])

        call_kwargs = observer.msg.call_args[1]
        msg_text = call_kwargs.get("text", "")
        self.assertIn("Jorge", msg_text)
        self.assertIn("says,", msg_text)

    def test_say_passes_type_metadata(self):
        """Say messages include type='say' for death filter compat."""
        jorge = _make_character(
            key="Jorge", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice", sex="female", height="average",
            build="average", sleeve_uid="uid-alice",
        )
        self._run_say(jorge, "Hello!", [jorge, observer])

        call_kwargs = observer.msg.call_args[1]
        self.assertEqual(call_kwargs.get("type"), "say")

    def test_say_no_args(self):
        """Say with no arguments shows help."""
        jorge = _make_character(
            key="Jorge", sex="male", height="tall",
            build="lean", sleeve_uid="uid-jorge",
        )
        from commands.CmdCommunication import CmdSay

        cmd = CmdSay()
        cmd.caller = jorge
        cmd.args = ""
        cmd.cmdstring = "say"
        jorge.location = MagicMock()

        cmd.func()

        jorge.msg.assert_called_once_with("Say what?")


# ===================================================================
# Tests: CmdWhisper
# ===================================================================


class TestCmdWhisper(TestCase):
    """Tests for the identity-aware whisper command."""

    def _run_whisper(self, caller, args, room_contents, search_result=None):
        """Helper to invoke CmdWhisper.func()."""
        from commands.CmdCommunication import CmdWhisper

        cmd = CmdWhisper()
        cmd.caller = caller
        cmd.args = f" {args}"
        cmd.cmdstring = "whisper"

        room = MagicMock()
        room.contents = room_contents
        caller.location = room

        # Mock caller.search to return the target
        if search_result is not None:
            caller.search = MagicMock(return_value=search_result)

        cmd.func()

    def test_actor_sees_own_whisper(self):
        """Actor sees 'You whisper to <target>, \"...\"'."""
        jorge = _make_character(
            key="Jorge", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
            recognition_memory={
                "uid-maria": {"assigned_name": "Maria"},
            },
        )
        maria = _make_character(
            key="Maria Santos", sex="female", height="short",
            build="athletic", sdesc_keyword="woman", sleeve_uid="uid-maria",
        )
        self._run_whisper(
            jorge, "Maria = Meet me later.",
            [jorge, maria], search_result=maria,
        )

        # Actor should see whisper to target
        jorge.msg.assert_called_once()
        actor_msg = jorge.msg.call_args[0][0]
        self.assertIn("You whisper to", actor_msg)
        self.assertIn("Maria", actor_msg)
        self.assertIn("Meet me later.", actor_msg)

    def test_target_hears_message(self):
        """Target receives the full whisper with speaker's name."""
        jorge = _make_character(
            key="Jorge", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        maria = _make_character(
            key="Maria Santos", sex="female", height="short",
            build="athletic", sdesc_keyword="woman", sleeve_uid="uid-maria",
        )
        self._run_whisper(
            jorge, "Maria = Secret stuff",
            [jorge, maria], search_result=maria,
        )

        maria.msg.assert_called_once()
        call_kwargs = maria.msg.call_args[1]
        msg_text = call_kwargs.get("text", "")
        self.assertIn("whispers to you", msg_text)
        self.assertIn("Secret stuff", msg_text)

    def test_observer_sees_no_content(self):
        """Room observers see that a whisper happened but NOT the content."""
        jorge = _make_character(
            key="Jorge", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        maria = _make_character(
            key="Maria Santos", sex="female", height="short",
            build="athletic", sdesc_keyword="woman", sleeve_uid="uid-maria",
        )
        observer = _make_character(
            key="Bob", sex="male", height="average",
            build="average", sleeve_uid="uid-bob",
        )
        self._run_whisper(
            jorge, "Maria = Top secret",
            [jorge, maria, observer], search_result=maria,
        )

        observer.msg.assert_called_once()
        call_kwargs = observer.msg.call_args[1]
        msg_text = call_kwargs.get("text", "")
        self.assertIn("whispers something to", msg_text)
        self.assertNotIn("Top secret", msg_text)

    def test_whisper_passes_type_metadata(self):
        """Whisper messages include type='whisper' for death filter."""
        jorge = _make_character(
            key="Jorge", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        maria = _make_character(
            key="Maria", sex="female", height="short",
            build="athletic", sleeve_uid="uid-maria",
        )
        observer = _make_character(
            key="Bob", sex="male", height="average",
            build="average", sleeve_uid="uid-bob",
        )
        self._run_whisper(
            jorge, "Maria = Hello",
            [jorge, maria, observer], search_result=maria,
        )

        # Check target message type
        target_kwargs = maria.msg.call_args[1]
        self.assertEqual(target_kwargs.get("type"), "whisper")

        # Check observer message type
        obs_kwargs = observer.msg.call_args[1]
        self.assertEqual(obs_kwargs.get("type"), "whisper")

    def test_whisper_no_equals(self):
        """Whisper without = shows usage."""
        jorge = _make_character(
            key="Jorge", sex="male", height="tall",
            build="lean", sleeve_uid="uid-jorge",
        )
        from commands.CmdCommunication import CmdWhisper

        cmd = CmdWhisper()
        cmd.caller = jorge
        cmd.args = " just talking"
        cmd.cmdstring = "whisper"
        jorge.location = MagicMock()

        cmd.func()
        jorge.msg.assert_called_once_with(
            "Usage: whisper <target> = <message>"
        )


# ===================================================================
# Tests: CmdEmote
# ===================================================================


class TestCmdEmote(TestCase):
    """Tests for the identity-aware emote command."""

    def _run_emote(self, caller, action, room_contents):
        """Helper to invoke CmdEmote.func()."""
        from commands.CmdCommunication import CmdEmote

        cmd = CmdEmote()
        cmd.caller = caller
        cmd.args = f" {action}"
        cmd.cmdstring = "emote"

        room = MagicMock()
        room.contents = room_contents
        caller.location = room

        cmd.func()

    def test_actor_sees_real_name(self):
        """Actor sees their own real name, NOT 'You'."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice", sex="female", height="average",
            build="average", sleeve_uid="uid-alice",
        )
        self._run_emote(jorge, "leans against the wall.", [jorge, observer])

        # render_emote sends via keyword args (text=..., type=..., from_obj=...)
        jorge.msg.assert_called_once()
        call_kwargs = jorge.msg.call_args[1]
        actor_msg = call_kwargs.get("text", "")
        self.assertIn("Jorge Jackson", actor_msg)
        self.assertIn("leans against the wall.", actor_msg)

    def test_observer_sees_sdesc(self):
        """Observer who doesn't know actor sees sdesc."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice", sex="female", height="average",
            build="average", sleeve_uid="uid-alice",
            recognition_memory={},
        )
        self._run_emote(jorge, "leans against the wall.", [jorge, observer])

        call_kwargs = observer.msg.call_args[1]
        msg_text = call_kwargs.get("text", "")
        # Should see sdesc, capitalized at start of sentence
        self.assertIn("gaunt man", msg_text.lower())
        self.assertIn("leans against the wall.", msg_text)
        # First character should be uppercase (article "A")
        self.assertTrue(msg_text[0].isupper())

    def test_observer_sees_assigned_name(self):
        """Observer who has assigned a name sees that name in emote."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice", sex="female", height="average",
            build="average", sleeve_uid="uid-alice",
            recognition_memory={
                "uid-jorge": {"assigned_name": "Jorge"},
            },
        )
        self._run_emote(jorge, "waves.", [jorge, observer])

        call_kwargs = observer.msg.call_args[1]
        msg_text = call_kwargs.get("text", "")
        self.assertIn("Jorge", msg_text)
        self.assertIn("waves.", msg_text)

    def test_emote_passes_type_metadata(self):
        """Emote messages include type='pose' for death filter."""
        jorge = _make_character(
            key="Jorge", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice", sex="female", height="average",
            build="average", sleeve_uid="uid-alice",
        )
        self._run_emote(jorge, "nods.", [jorge, observer])

        call_kwargs = observer.msg.call_args[1]
        self.assertEqual(call_kwargs.get("type"), "pose")

    def test_emote_no_args(self):
        """Emote with no arguments shows help."""
        jorge = _make_character(
            key="Jorge", sex="male", height="tall",
            build="lean", sleeve_uid="uid-jorge",
        )
        from commands.CmdCommunication import CmdEmote

        cmd = CmdEmote()
        cmd.caller = jorge
        cmd.args = ""
        cmd.cmdstring = "emote"
        jorge.location = MagicMock()

        cmd.func()
        jorge.msg.assert_called_once_with("What do you want to emote?")

    def test_emote_char_ref_resolved_per_observer(self):
        """Character reference in emote body is resolved per-observer."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        maria = _make_character(
            key="Maria Santos", sex="female", height="short",
            build="stocky", sdesc_keyword="woman", sleeve_uid="uid-maria",
        )
        # Observer knows Maria as "Maria" but doesn't know Jorge
        observer = _make_character(
            key="Bob", sex="male", height="average",
            build="average", sleeve_uid="uid-bob",
            recognition_memory={
                "uid-maria": {"assigned_name": "Maria"},
            },
        )
        # Jorge emotes referencing Maria by her sdesc (short+stocky = "squat")
        self._run_emote(
            jorge, "nods at squat woman.", [jorge, maria, observer]
        )

        obs_kwargs = observer.msg.call_args[1]
        obs_text = obs_kwargs.get("text", "")
        # Observer should see assigned name "Maria" for the target
        self.assertIn("Maria", obs_text)
        # Observer should see sdesc for Jorge (actor)
        self.assertIn("gaunt man", obs_text.lower())
        self.assertIn("nods at", obs_text)

    def test_emote_char_ref_unknown_observer(self):
        """Observer who knows neither actor nor target sees sdescs for both."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        maria = _make_character(
            key="Maria Santos", sex="female", height="short",
            build="stocky", sdesc_keyword="woman", sleeve_uid="uid-maria",
        )
        observer = _make_character(
            key="Bob", sex="male", height="average",
            build="average", sleeve_uid="uid-bob",
        )
        # Jorge emotes referencing Maria by descriptor+keyword
        self._run_emote(
            jorge, "nods at squat woman.", [jorge, maria, observer]
        )

        obs_kwargs = observer.msg.call_args[1]
        obs_text = obs_kwargs.get("text", "")
        # Both should appear as sdescs
        self.assertIn("gaunt man", obs_text.lower())
        self.assertIn("squat woman", obs_text.lower())
        # Real names should NOT appear
        self.assertNotIn("Jorge", obs_text)
        self.assertNotIn("Maria", obs_text)

    def test_emote_char_ref_in_speech_not_resolved(self):
        """Character names inside quoted speech are NOT resolved."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
        )
        maria = _make_character(
            key="Maria Santos", sex="female", height="short",
            build="stocky", sdesc_keyword="woman", sleeve_uid="uid-maria",
        )
        observer = _make_character(
            key="Bob", sex="male", height="average",
            build="average", sleeve_uid="uid-bob",
        )
        # Jorge says Maria's descriptor inside quotes — should NOT resolve
        self._run_emote(
            jorge,
            'says "I saw squat woman earlier."',
            [jorge, maria, observer],
        )

        obs_kwargs = observer.msg.call_args[1]
        obs_text = obs_kwargs.get("text", "")
        # Inside speech, "squat woman" should be preserved verbatim
        self.assertIn('"I saw squat woman earlier."', obs_text)

    def test_emote_actor_sees_char_ref_via_own_memory(self):
        """Actor's char ref rendering uses their own recognition memory."""
        jorge = _make_character(
            key="Jorge Jackson", sex="male", height="tall",
            build="lean", sdesc_keyword="man", sleeve_uid="uid-jorge",
            recognition_memory={
                "uid-maria": {"assigned_name": "Maria"},
            },
        )
        maria = _make_character(
            key="Maria Santos", sex="female", height="short",
            build="stocky", sdesc_keyword="woman", sleeve_uid="uid-maria",
        )
        # Jorge emotes referencing Maria by descriptor+keyword
        self._run_emote(
            jorge, "nods at squat woman.", [jorge, maria]
        )

        # Actor should see "Maria" (their assigned name) for the target
        jorge_kwargs = jorge.msg.call_args[1]
        jorge_text = jorge_kwargs.get("text", "")
        self.assertIn("Maria", jorge_text)
        self.assertIn("nods at", jorge_text)


# ===================================================================
# Tests: CmdDotPose
# ===================================================================


class TestCmdDotPose(TestCase):
    """Tests for the CmdDotPose command integration."""

    def _run_dot_pose(
        self,
        caller,
        raw_string: str,
        room_contents: list,
    ) -> None:
        """Execute CmdDotPose with the given raw string."""
        from commands.CmdCommunication import CmdDotPose

        cmd = CmdDotPose()
        cmd.caller = caller
        cmd.raw_string = raw_string
        # args would be whatever Evennia parses after the key "."
        cmd.args = raw_string[1:] if raw_string.startswith(".") else raw_string
        cmd.cmdstring = "."

        room = MagicMock()
        room.contents = room_contents
        caller.location = room

        cmd.func()

    # -- Basic verb conjugation --

    def test_actor_sees_you_form(self):
        """Actor sees 'You lean back.' for '.lean back.'"""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        self._run_dot_pose(jorge, ".lean back.", [jorge])

        # Actor is also an observer in render_dot_pose — find the call
        # render_dot_pose calls observer.msg(text=..., type="pose", from_obj=actor)
        call_kwargs = jorge.msg.call_args[1]
        msg_text = call_kwargs.get("text", "")
        self.assertIn("You lean back.", msg_text)

    def test_observer_sees_third_person(self):
        """Observer sees conjugated verb with actor's display name."""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
        )
        self._run_dot_pose(jorge, ".lean back.", [jorge, observer])

        call_kwargs = observer.msg.call_args[1]
        msg_text = call_kwargs.get("text", "")
        # Observer doesn't know Jorge, sees sdesc
        self.assertIn("gaunt man", msg_text.lower())
        self.assertIn("leans back.", msg_text)

    def test_observer_known_sees_assigned_name(self):
        """Observer who assigned a name sees that name."""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
            recognition_memory={
                "uid-jorge": {"assigned_name": "Jorge"},
            },
        )
        self._run_dot_pose(jorge, ".lean back.", [jorge, observer])

        call_kwargs = observer.msg.call_args[1]
        msg_text = call_kwargs.get("text", "")
        self.assertIn("Jorge leans back.", msg_text)

    # -- Pronoun transformation --

    def test_pronoun_my_transforms(self):
        """'my' becomes 'your' for actor, 'his' for male observer view."""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
        )
        self._run_dot_pose(
            jorge, ".scratch my jaw.", [jorge, observer]
        )

        actor_kwargs = jorge.msg.call_args[1]
        actor_text = actor_kwargs.get("text", "")
        self.assertIn("your jaw", actor_text)

        obs_kwargs = observer.msg.call_args[1]
        obs_text = obs_kwargs.get("text", "")
        self.assertIn("his jaw", obs_text)

    # -- Speech passthrough --

    def test_speech_preserved(self):
        """Quoted speech passes through unchanged."""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
        )
        self._run_dot_pose(
            jorge,
            '.nod. "Understood."',
            [jorge, observer],
        )

        obs_kwargs = observer.msg.call_args[1]
        obs_text = obs_kwargs.get("text", "")
        self.assertIn('"Understood."', obs_text)

    # -- Speech-first pattern --

    def test_speech_first_pattern(self):
        """Speech before actor mention: '"Get down!" I .shout'"""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
        )
        self._run_dot_pose(
            jorge,
            '"Get down!" I .shout.',
            [jorge, observer],
        )

        actor_kwargs = jorge.msg.call_args[1]
        actor_text = actor_kwargs.get("text", "")
        self.assertIn('"Get down!"', actor_text)
        self.assertIn("you shout", actor_text)

        obs_kwargs = observer.msg.call_args[1]
        obs_text = obs_kwargs.get("text", "")
        self.assertIn('"Get down!"', obs_text)
        # Observer sees capitalized display name or pronoun after speech
        self.assertIn("shout", obs_text.lower())

    # -- Death filter metadata --

    def test_passes_type_pose(self):
        """Messages include type='pose' for death filter compat."""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
        )
        self._run_dot_pose(jorge, ".lean back.", [jorge, observer])

        obs_kwargs = observer.msg.call_args[1]
        self.assertEqual(obs_kwargs.get("type"), "pose")

    def test_passes_from_obj(self):
        """Messages include from_obj=caller for death filter compat."""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        observer = _make_character(
            key="Alice",
            sex="female",
            height="average",
            build="average",
            sleeve_uid="uid-alice",
        )
        self._run_dot_pose(jorge, ".lean back.", [jorge, observer])

        obs_kwargs = observer.msg.call_args[1]
        self.assertEqual(obs_kwargs.get("from_obj"), jorge)

    # -- Empty input --

    def test_empty_shows_usage(self):
        """Just '.' with no text shows usage hint."""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sleeve_uid="uid-jorge",
        )
        jorge.location = MagicMock()

        from commands.CmdCommunication import CmdDotPose

        cmd = CmdDotPose()
        cmd.caller = jorge
        cmd.raw_string = "."
        cmd.args = ""
        cmd.cmdstring = "."

        cmd.func()

        jorge.msg.assert_called_once()
        msg_text = jorge.msg.call_args[0][0]
        self.assertIn("Usage:", msg_text)

    # -- No location --

    def test_no_location(self):
        """Command with no location shows error."""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sleeve_uid="uid-jorge",
        )
        jorge.location = None

        from commands.CmdCommunication import CmdDotPose

        cmd = CmdDotPose()
        cmd.caller = jorge
        cmd.raw_string = ".lean back."
        cmd.args = "lean back."
        cmd.cmdstring = "."

        cmd.func()

        jorge.msg.assert_called_once_with(
            "You have no location to emote in."
        )

    # -- Character references --

    def test_char_ref_resolved_per_observer(self):
        """Character references resolve per-observer."""
        jorge = _make_character(
            key="Jorge Jackson",
            sex="male",
            height="tall",
            build="lean",
            sdesc_keyword="man",
            sleeve_uid="uid-jorge",
        )
        maria = _make_character(
            key="Maria Santos",
            sex="female",
            height="short",
            build="stocky",
            sdesc_keyword="woman",
            sleeve_uid="uid-maria",
        )
        # Observer knows Maria as "Maria"
        observer = _make_character(
            key="Bob",
            sex="male",
            height="average",
            build="average",
            sleeve_uid="uid-bob",
            recognition_memory={
                "uid-maria": {"assigned_name": "Maria"},
            },
        )
        self._run_dot_pose(
            jorge,
            ".nod at stocky woman",
            [jorge, maria, observer],
        )

        # Observer should see Maria's assigned name
        obs_kwargs = observer.msg.call_args[1]
        obs_text = obs_kwargs.get("text", "")
        self.assertIn("Maria", obs_text)
        self.assertIn("nod", obs_text.lower())
