"""
Communication Commands — Identity-Aware Overrides

Custom ``say``, ``whisper``, and ``emote`` commands that render speaker
and target names per-observer using the identity and recognition system.

These replace Evennia's built-in defaults so that unrecognized characters
appear by short description rather than real name.

See specs/EMOTE_POSE_SPEC.md for the full specification.
"""

from __future__ import annotations

from evennia.commands.command import Command

from world.emote import (
    render_dot_pose,
    render_emote,
    tokenize_dot_pose,
    tokenize_emote,
)
from world.grammar import capitalize_first
from world.identity_utils import msg_room_identity


class CmdSay(Command):
    """
    Speak aloud in the current room.

    Usage:
        say <message>
        "<message>

    Each observer sees the speaker's name as they know them.
    Speech content passes through unchanged.
    """

    key = "say"
    aliases = ['"']
    locks = "cmd:all()"
    help_category = "Social"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Say what?")
            return

        speech = self.args.strip()
        location = caller.location
        if not location:
            caller.msg("You have no location to speak in.")
            return

        # Actor sees their own message
        caller.msg(f'You say, "{speech}"')

        # Each observer sees per-observer speaker attribution
        for observer in location.contents:
            if observer is caller:
                continue
            if not hasattr(observer, "msg"):
                continue
            speaker_name = caller.get_display_name(observer)
            observer.msg(
                text=f'{capitalize_first(speaker_name)} says, "{speech}"',
                type="say",
                from_obj=caller,
            )


class CmdWhisper(Command):
    """
    Whisper a message to a specific target.

    Usage:
        whisper <target> = <message>

    The target hears the full message. Other observers only see that
    a whisper occurred — they do not see the content.
    """

    key = "whisper"
    locks = "cmd:all()"
    help_category = "Social"

    def func(self):
        caller = self.caller

        if not self.args or "=" not in self.args:
            caller.msg("Usage: whisper <target> = <message>")
            return

        target_str, _, speech = self.args.partition("=")
        target_str = target_str.strip()
        speech = speech.strip()

        if not target_str or not speech:
            caller.msg("Usage: whisper <target> = <message>")
            return

        location = caller.location
        if not location:
            caller.msg("You have no location to whisper in.")
            return

        # Resolve target via identity-aware search
        target = caller.search(target_str)
        if not target:
            return  # search() already sent error message

        # Actor sees their own message
        target_name_for_actor = target.get_display_name(caller)
        caller.msg(f'You whisper to {target_name_for_actor}, "{speech}"')

        # Target hears the full message
        speaker_name_for_target = caller.get_display_name(target)
        target.msg(
            text=(
                f'{capitalize_first(speaker_name_for_target)}'
                f' whispers to you, "{speech}"'
            ),
            type="whisper",
            from_obj=caller,
        )

        # Room observers see that a whisper occurred, but NOT the content
        for observer in location.contents:
            if observer is caller or observer is target:
                continue
            if not hasattr(observer, "msg"):
                continue
            speaker_name = caller.get_display_name(observer)
            target_name = target.get_display_name(observer)
            observer.msg(
                text=(
                    f"{capitalize_first(speaker_name)} whispers"
                    f" something to {target_name}."
                ),
                type="whisper",
                from_obj=caller,
            )


class CmdEmote(Command):
    """
    Perform an emote visible to the room.

    Usage:
        emote <action text>
        :<action text>

    Your name is prepended to the action text. Each observer sees
    your name as they know you. You see your real name. Other
    characters mentioned by name or short description are resolved
    per-observer. Names inside quoted speech are not resolved.

    Example:
        emote leans against the wall.
        → You see: "Jorge leans against the wall."
        → Others might see: "A lanky man leans against the wall."

        emote nods at Jorge.
        → Observer who knows Jorge sees: "A lanky man nods at Jorge."
        → Observer who doesn't: "A lanky man nods at a compact woman."
    """

    key = "emote"
    aliases = [":", "pose"]
    locks = "cmd:all()"
    help_category = "Social"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("What do you want to emote?")
            return

        action = self.args.strip()
        location = caller.location
        if not location:
            caller.msg("You have no location to emote in.")
            return

        # Gather room occupants for character reference matching.
        # Filter on get_sdesc (Character-only) — Exits and items also
        # have get_display_name but lack get_sdesc, which
        # build_char_candidates requires.
        room_occupants = [
            obj
            for obj in location.contents
            if obj is not caller and hasattr(obj, "get_sdesc")
        ]

        tokens = tokenize_emote(action, caller, room_occupants)

        if not tokens:
            caller.msg("What do you want to emote?")
            return

        # Broadcast to room (each observer gets unique char ref rendering)
        render_emote(tokens, caller, location)


class CmdDotPose(Command):
    """
    First-person natural emote using the dot-pose system.

    Usage:
        .<verb> <text>

    Write emotes in a natural first-person style. Verbs are marked with
    a leading dot; the first word is automatically treated as a verb.
    First-person pronouns (I, my, me, mine, myself) are transformed
    per-observer.  Other characters in the room can be referenced by
    name or short description.

    Examples::

        .lean back.
          You see:    You lean back.
          Others see: A lanky man leans back.

        .scratch my jaw, "What day is it?" I .ask.
          You see:    You scratch your jaw, "What day is it?" you ask.
          Others see: A lanky man scratches his jaw, "What day is it?" he asks.

        "Get down!" I .shout, .diving behind cover.
          You see:    "Get down!" you shout, diving behind cover.
          Others see: "Get down!" A lanky man shouts, diving behind cover.

        .nod at Jorge
          You see:    You nod at Jorge.
          Others see: A lanky man nods at a compact woman.
    """

    key = "."
    locks = "cmd:all()"
    help_category = "Social"
    # Prevent Evennia from stripping the args — we need the full text.
    arg_regex = r"(?s).*"

    def func(self) -> None:
        caller = self.caller

        # Extract the emote text from raw_string.
        # raw_string looks like ".lean back." — strip the leading "."
        raw = self.raw_string
        if raw.startswith("."):
            raw = raw[1:]

        # Strip trailing whitespace only (leading space is meaningful
        # for speech-first patterns like ' "Hey," I .say')
        emote_text = raw.rstrip()

        if not emote_text or not emote_text.strip():
            caller.msg(
                "Usage: .<verb> <text>\n"
                "  .lean back.\n"
                '  .scratch my jaw, "What day is it?" I .ask.\n'
                '  "Get down!" I .shout, .diving behind cover.'
            )
            return

        location = caller.location
        if not location:
            caller.msg("You have no location to emote in.")
            return

        # Gather room occupants for character reference matching.
        # Filter on get_sdesc (Character-only) — Exits and items also
        # have get_display_name but lack get_sdesc, which
        # build_char_candidates requires.
        room_occupants = [
            obj
            for obj in location.contents
            if obj is not caller and hasattr(obj, "get_sdesc")
        ]

        tokens = tokenize_dot_pose(emote_text, caller, room_occupants)

        if not tokens:
            caller.msg(
                "Usage: .<verb> <text>\n"
                "  .lean back.\n"
                '  .scratch my jaw, "What day is it?" I .ask.\n'
                '  "Get down!" I .shout, .diving behind cover.'
            )
            return

        # Broadcast to room (each observer gets a unique rendering)
        render_dot_pose(tokens, caller, location)
