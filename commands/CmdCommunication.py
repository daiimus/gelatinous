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
    your name as they know you. You see your real name.

    Example:
        emote leans against the wall.
        → You see: "Jorge leans against the wall."
        → Others might see: "A lanky man leans against the wall."
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

        # Actor sees their real name (per spec: NOT "You")
        actor_name_for_self = caller.get_display_name(caller)
        caller.msg(f"{actor_name_for_self} {action}")

        # Each observer sees per-observer name
        for observer in location.contents:
            if observer is caller:
                continue
            if not hasattr(observer, "msg"):
                continue
            actor_name = caller.get_display_name(observer)
            observer.msg(
                text=f"{capitalize_first(actor_name)} {action}",
                type="pose",
                from_obj=caller,
            )
