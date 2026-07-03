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
    render_think,
    tokenize_dot_pose,
    tokenize_emote,
)

from world.grammar import capitalize_first
from world.identity_utils import msg_room_identity
from world.perception import can_hear
from world.speech import broadcast_speech


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
        # Speaking gives you away (STEALTH_AND_DETECTION_SPEC §6.4).
        from world.stealth import break_stealth
        break_stealth(caller)

        if not self.args:
            caller.msg("Say what?")
            return

        speech = self.args.strip()
        location = caller.location
        if not location:
            caller.msg("You have no location to speak in.")
            return

        # Actor sees their own message; the room hears it through the shared
        # speech backbone (per-observer attribution, hearing-gated content,
        # voice flavour, and the structured speech payload NPCs react to).
        caller.msg(f'You say, "{speech}"')
        broadcast_speech(caller, speech, location)


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
        # Speaking gives you away (STEALTH_AND_DETECTION_SPEC §6.4).
        from world.stealth import break_stealth
        break_stealth(caller)

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

        # Actor sees their own message; the room hears it through the shared
        # speech backbone. `to` is just `say` with a target: the addressee is
        # rendered "you", and the structured payload marks them `addressed` so
        # an NPC can tell being spoken to directly from ambient room chatter.
        caller.msg(f'You say to {target.get_display_name(caller)}, "{speech}"')
        broadcast_speech(caller, speech, location, target=target)


class CmdWhisper(Command):
    """
    Whisper a message to a specific target.

    Usage:
        whisper "Wakka." to <person>
        whisper <person> = <message>     (legacy form)

    The target hears the full message. Other observers only see that a
    whisper occurred — never the content.

    Whispering does NOT give you away: a whisper from someone the target
    cannot see arrives as a voice with no owner — they'll know something
    is there, not who or where.
    """

    key = "whisper"
    locks = "cmd:all()"
    help_category = "Social"

    def parse(self):
        """Accept `whisper "text" to <person>` (canonical) or the legacy
        `whisper <person> = <text>`."""
        import re
        self.speech = self.target_str = ""
        raw = (self.args or "").strip()
        match = re.match(r'^"(?P<speech>[^"]+)"\s+to\s+(?P<target>.+)$', raw)
        if match:
            self.speech = match.group("speech").strip()
            self.target_str = match.group("target").strip()
            return
        if "=" in raw:
            target_str, _, speech = raw.partition("=")
            self.target_str = target_str.strip()
            self.speech = speech.strip()

    def func(self):
        caller = self.caller
        if not self.speech or not self.target_str:
            caller.msg('Usage: whisper "<message>" to <person>')
            return
        speech, target_str = self.speech, self.target_str

        location = caller.location
        if not location:
            caller.msg("You have no location to whisper in.")
            return

        # Resolve target via identity-aware search
        target = caller.search(target_str)
        if not target:
            return  # search() already sent error message

        # A whisper never breaks stealth (STEALTH_AND_DETECTION_SPEC §6.4
        # carve-out): it's the creepy channel. From a hidden speaker the
        # target can't see, the voice arrives with no owner — and leaves
        # them knowing SOMETHING is there.
        from world.stealth import (
            SUSPICIOUS, get_awareness, is_hidden_from, set_awareness,
        )
        unseen = is_hidden_from(caller, target)

        # Actor sees their own message
        target_name_for_actor = target.get_display_name(caller)
        caller.msg(f'You whisper to {target_name_for_actor}, "{speech}"')

        # Target hears the full message — unless deaf, in which case they feel
        # the lean-in but can't make out the words (CAPACITY_CONSUMERS §4).
        if unseen:
            speaker_name_for_target = "Someone unseen"
        else:
            speaker_name_for_target = capitalize_first(
                caller.get_display_name(target)
            )
        if can_hear(target):
            if unseen:
                target_text = (
                    f'Someone unseen whispers at your ear, "{speech}"'
                )
            else:
                target_text = (
                    f'{speaker_name_for_target} whispers to you, "{speech}"'
                )
        else:
            if unseen:
                target_text = (
                    "You feel a breath at your ear, but you can't make "
                    "out a word of it."
                )
            else:
                target_text = (
                    f"{speaker_name_for_target} leans in to whisper, but you "
                    f"can't make out a word of it."
                )
        target.msg(text=target_text, type="whisper", from_obj=caller)
        if unseen:
            if get_awareness(target, caller) < SUSPICIOUS:
                set_awareness(target, caller, SUSPICIOUS)

        # Room observers see that a whisper occurred, but NOT the content.
        # Observers who can't see the whisperer see nothing at all.
        for observer in location.contents:
            if observer is caller or observer is target:
                continue
            if not hasattr(observer, "msg"):
                continue
            if is_hidden_from(caller, observer):
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
        # Speaking gives you away (STEALTH_AND_DETECTION_SPEC §6.4).
        from world.stealth import break_stealth
        break_stealth(caller)

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
        # Speaking gives you away (STEALTH_AND_DETECTION_SPEC §6.4).
        from world.stealth import break_stealth
        break_stealth(caller)

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


class CmdThink(Command):
    """
    Think to yourself — private roleplay, shown as a thoughtbubble.

    Usage:
        think <thought>

    Your thought is normally private. For now, staff (Builder+) in the room
    can also perceive it — a window into what characters (and NPCs) are
    thinking. A telepathy/psychic sense will gate this for players later.

    Example:
        think these are my innermost thoughts.
          You see:        You think . o O ( these are my innermost thoughts. )
          A builder sees: A lanky man thinks . o O ( these are my innermost thoughts. )
    """

    key = "think"
    locks = "cmd:all()"
    help_category = "Social"

    def func(self) -> None:
        caller = self.caller

        if not self.args or not self.args.strip():
            caller.msg("Think what?")
            return

        location = caller.location
        if not location:
            caller.msg("You have nowhere to think.")
            return

        render_think(caller, self.args.strip(), location)
