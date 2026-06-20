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
from random import random

from world.grammar import capitalize_first
from world.identity_utils import msg_room_identity
from world.voice import (
    can_hear,
    can_see,
    garbled_voice_phrase,
    resolve_speaker_attribution,
    voice_phrase,
    VOICE_FLAVOR_SPRINKLE_CHANCE,
)


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

        # Voice flavour for observers who can SEE the speaker (CAPACITY_CONSUMERS
        # spec §4.6 can-see branch): a garbled voice always renders — a ruined
        # voice is conspicuous — otherwise a sporadic, low-frequency sprinkle,
        # rolled once per utterance for a consistent reading.
        visible_flavor = garbled_voice_phrase(caller)
        if visible_flavor is None:
            phrase = voice_phrase(caller)
            if phrase and random() < VOICE_FLAVOR_SPRINKLE_CHANCE:
                visible_flavor = phrase
        visible_verb = f"says, |x*{visible_flavor}*|n" if visible_flavor else "says,"

        # Each observer's perception resolves per the sight/hearing chain
        # (§4.5). Hearing gates the *content* (the words); sight + the voice
        # channel gate the *attribution* (who):
        #   - can hear → the words, attributed by sight (name + flavour) or by
        #     voice discernment (name / "someone").
        #   - deaf but can see → they watch the speaker mouth something but
        #     can't make it out (no content).
        #   - deaf and blind → no channel at all; the utterance is suppressed.
        for observer in location.contents:
            if observer is caller:
                continue
            if not hasattr(observer, "msg"):
                continue

            heard = can_hear(observer)
            seen = can_see(observer)
            if not heard and not seen:
                continue  # no channel — suppress entirely

            speaker_name = resolve_speaker_attribution(caller, observer)
            if heard:
                verb = visible_verb if seen else "says,"
                text = f'{capitalize_first(speaker_name)} {verb} "{speech}"'
            else:
                # Deaf but watching: speech is visible, content is not.
                text = (
                    f"{capitalize_first(speaker_name)} says something "
                    f"you can't make out."
                )
            observer.msg(text=text, type="say", from_obj=caller)


class CmdTo(Command):
    """
    Speak aloud, directed at someone in the room.

    Usage:
        to <target> <message>

    Like ``say``, but pointed at one person — everyone present still hears it.
    The target is addressed directly ("... says to you, ..."); onlookers see
    who it was aimed at. Perception applies exactly as with ``say``: hearing
    gates the words, sight gates whether you can tell who is speaking.
    """

    key = "to"
    locks = "cmd:all()"
    help_category = "Social"

    def func(self):
        caller = self.caller

        args = (self.args or "").strip()
        parts = args.split(None, 1)
        if len(parts) < 2 or not parts[1].strip():
            caller.msg("Usage: to <target> <message>")
            return
        target_str, speech = parts[0], parts[1].strip()

        location = caller.location
        if not location:
            caller.msg("You have no location to speak in.")
            return

        target = caller.search(target_str)
        if not target:
            return  # search() already sent the error message

        # Actor sees their own message.
        caller.msg(f'You say to {target.get_display_name(caller)}, "{speech}"')

        # Voice flavour for observers who can SEE the speaker (as in `say`):
        # a garbled voice always renders; otherwise a sporadic sprinkle, rolled
        # once per utterance for a consistent reading across observers.
        visible_flavor = garbled_voice_phrase(caller)
        if visible_flavor is None:
            phrase = voice_phrase(caller)
            if phrase and random() < VOICE_FLAVOR_SPRINKLE_CHANCE:
                visible_flavor = phrase

        # Directed but audible: everyone present resolves it through the same
        # sight/hearing chain as `say`. The target is addressed as "you".
        for observer in location.contents:
            if observer is caller:
                continue
            if not hasattr(observer, "msg"):
                continue

            heard = can_hear(observer)
            seen = can_see(observer)
            if not heard and not seen:
                continue  # no channel — suppress entirely

            speaker_name = resolve_speaker_attribution(caller, observer)
            target_ref = (
                "you" if observer is target
                else target.get_display_name(observer)
            )
            if heard:
                if seen and visible_flavor:
                    verb = f"says to {target_ref}, |x*{visible_flavor}*|n"
                else:
                    verb = f"says to {target_ref},"
                text = f'{capitalize_first(speaker_name)} {verb} "{speech}"'
            else:
                # Deaf but watching: the address is visible, the words are not.
                text = (
                    f"{capitalize_first(speaker_name)} says something to "
                    f"{target_ref}, but you can't make it out."
                )
            observer.msg(text=text, type="say", from_obj=caller)


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

        # Target hears the full message — unless deaf, in which case they feel
        # the lean-in but can't make out the words (CAPACITY_CONSUMERS §4).
        speaker_name_for_target = capitalize_first(
            caller.get_display_name(target)
        )
        if can_hear(target):
            target_text = (
                f'{speaker_name_for_target} whispers to you, "{speech}"'
            )
        else:
            target_text = (
                f"{speaker_name_for_target} leans in to whisper, but you "
                f"can't make out a word of it."
            )
        target.msg(text=target_text, type="whisper", from_obj=caller)

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
