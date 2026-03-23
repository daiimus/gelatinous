"""
Pre-Built Emote Templates — Social Commands

Convenience shortcuts for common social emotes (nod, shrug, wave, etc.).
Each template command supports a solo form (``nod``) and optionally a
targeted form (``nod jorge``), rendered per-observer via the identity
system.

A command-factory approach generates one :class:`~evennia.commands.command.Command`
subclass per template keyword.  The generated commands are collected in
:data:`SOCIAL_COMMANDS` for registration in the character command set.

See specs/EMOTE_POSE_SPEC.md §Pre-Built Emote Templates for the full
specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from evennia.commands.command import Command

from world.grammar import capitalize_first
from world.identity_utils import msg_room_identity

if TYPE_CHECKING:
    pass


# -------------------------------------------------------------------
# Template definitions
# -------------------------------------------------------------------

#: Each entry maps a keyword to its solo and (optionally) targeted
#: observer template.  Templates use ``{actor}`` and ``{target}``
#: placeholders resolved per-observer by :func:`msg_room_identity`.
EMOTE_TEMPLATES: dict[str, dict[str, str]] = {
    "nod": {
        "solo": "{actor} nods.",
        "targeted": "{actor} nods at {target}.",
    },
    "shrug": {
        "solo": "{actor} shrugs.",
        "targeted": "{actor} shrugs at {target}.",
    },
    "laugh": {
        "solo": "{actor} laughs.",
        "targeted": "{actor} laughs at {target}.",
    },
    "sigh": {
        "solo": "{actor} sighs.",
    },
    "smile": {
        "solo": "{actor} smiles.",
        "targeted": "{actor} smiles at {target}.",
    },
    "wave": {
        "solo": "{actor} waves.",
        "targeted": "{actor} waves at {target}.",
    },
    "bow": {
        "solo": "{actor} bows.",
        "targeted": "{actor} bows respectfully to {target}.",
    },
    "frown": {
        "solo": "{actor} frowns.",
        "targeted": "{actor} frowns at {target}.",
    },
}

#: Mapping from template keyword to the third-person verb form shown to
#: the actor in their self-view (e.g. "You nod.", "You bow.").  Entries
#: are only needed when the verb differs from the keyword.
_ACTOR_VERBS: dict[str, str] = {
    # All current keywords happen to be the base verb form already.
    # Add overrides here if a future keyword diverges
    # (e.g. "curtsy": "curtsy").
}

#: Targeted actor self-view prepositions.  Keyed by template keyword.
#: Defaults to "at" when absent.
_ACTOR_PREPOSITIONS: dict[str, str] = {
    "bow": "respectfully to",
}


# -------------------------------------------------------------------
# Command factory
# -------------------------------------------------------------------


def _actor_verb(keyword: str) -> str:
    """Return the base verb form for the actor self-view."""
    return _ACTOR_VERBS.get(keyword, keyword)


def _actor_preposition(keyword: str) -> str:
    """Return the preposition used in the actor's targeted self-view."""
    return _ACTOR_PREPOSITIONS.get(keyword, "at")


def _make_social_cmd(
    keyword: str,
    solo_template: str,
    targeted_template: str | None = None,
) -> type[Command]:
    """Create a :class:`Command` subclass for a social emote template.

    Args:
        keyword: The command keyword (e.g. ``"nod"``).
        solo_template: Observer template for the no-target form.
            Must contain ``{actor}`` placeholder.
        targeted_template: Observer template for the targeted form.
            Must contain ``{actor}`` and ``{target}`` placeholders.
            ``None`` if this emote has no targeted variant.

    Returns:
        A new ``Command`` subclass ready for registration in a cmdset.
    """
    verb = _actor_verb(keyword)
    preposition = _actor_preposition(keyword)

    class _SocialCmd(Command):
        __doc__ = (
            f"Perform a social emote: {keyword}.\n\n"
            f"Usage:\n"
            f"    {keyword}"
            + (f"\n    {keyword} <target>" if targeted_template else "")
            + "\n"
        )

        key = keyword
        locks = "cmd:all()"
        help_category = "Social"

        def func(self) -> None:
            caller = self.caller
            location = caller.location
            if not location:
                caller.msg("You have no location to emote in.")
                return

            args = self.args.strip() if self.args else ""

            if not args:
                # --- Solo form ---
                caller.msg(f"You {verb}.")
                msg_room_identity(
                    location,
                    solo_template,
                    {"actor": caller},
                    exclude=[caller],
                    type="pose",
                    from_obj=caller,
                )
                return

            # --- Targeted form ---
            if targeted_template is None:
                caller.msg(f"Usage: {keyword}")
                return

            target = caller.search(args)
            if not target:
                return  # search() already sent error

            target_name = target.get_display_name(caller)
            caller.msg(
                f"You {verb} {preposition} {target_name}."
            )
            msg_room_identity(
                location,
                targeted_template,
                {"actor": caller, "target": target},
                exclude=[caller],
                type="pose",
                from_obj=caller,
            )

    # Give the class a unique name for introspection / debugging.
    _SocialCmd.__name__ = f"CmdSocial_{keyword.title()}"
    _SocialCmd.__qualname__ = f"CmdSocial_{keyword.title()}"

    return _SocialCmd


# -------------------------------------------------------------------
# Generated command classes
# -------------------------------------------------------------------

#: All generated social emote command classes, ready for cmdset
#: registration.
SOCIAL_COMMANDS: list[type[Command]] = [
    _make_social_cmd(
        keyword=kw,
        solo_template=templates["solo"],
        targeted_template=templates.get("targeted"),
    )
    for kw, templates in EMOTE_TEMPLATES.items()
]
