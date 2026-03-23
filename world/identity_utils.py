"""
Identity-Aware Messaging Utilities

Helper functions for sending per-observer identity-resolved messages.
The primary entry point is :func:`msg_room_identity`, which replaces
direct ``msg_contents()`` calls for any message that references
characters by name.

See specs/IDENTITY_RECOGNITION_SPEC.md §msg_room_identity Helper for
the full specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from world.grammar import capitalize_first

if TYPE_CHECKING:
    from typeclasses.characters import Character
    from typeclasses.rooms import Room


def msg_room_identity(
    location: "Room",
    template: str,
    char_refs: dict[str, "Character"],
    exclude: list | None = None,
    **kwargs,
) -> None:
    """Send an identity-aware message to all observers in a room.

    Each observer receives a personalised copy of *template* where
    ``{placeholder}`` tokens are replaced with the referenced
    character's display name as seen **by that specific observer**.

    Args:
        location: The room to broadcast in.
        template: Message string with ``{placeholder}`` tokens that
            correspond to keys in *char_refs*.
            Example: ``"{actor} attacks {target} with a knife!"``
        char_refs: Mapping of placeholder names to Character objects.
            Example: ``{"actor": attacker, "target": target}``
        exclude: Characters/objects to exclude from receiving the
            message.  Typically the actor and/or target who receive
            separate first-person messages.
        **kwargs: Extra keyword arguments passed through to each
            ``observer.msg()`` call (e.g. ``type="say"``).

    Example::

        msg_room_identity(
            location=room,
            template="{actor} attacks {target} with a knife!",
            char_refs={"actor": attacker, "target": target},
            exclude=[attacker, target],
        )

    Observer A (knows both): ``"Jorge attacks Skullface with a knife!"``
    Observer B (knows neither): ``"A lanky man attacks a wiry droog with a knife!"``
    """
    exclude_set = set(exclude) if exclude else set()

    # Determine which placeholder appears first in the template
    # so we can capitalize its display name for proper sentence casing.
    # e.g. "|g{actor} grapples {target}!" → capitalize actor's sdesc
    # so "a lanky man" becomes "A lanky man" at the sentence start.
    first_placeholder: str | None = None
    first_pos = len(template)
    for placeholder in char_refs:
        pos = template.find(f"{{{placeholder}}}")
        if pos != -1 and pos < first_pos:
            first_pos = pos
            first_placeholder = placeholder

    for observer in location.contents:
        if observer in exclude_set:
            continue
        if not hasattr(observer, "msg"):
            continue

        resolved = template
        for placeholder, char in char_refs.items():
            display_name = char.get_display_name(observer)
            if placeholder == first_placeholder:
                display_name = capitalize_first(display_name)
            resolved = resolved.replace(f"{{{placeholder}}}", display_name)

        observer.msg(text=resolved, **kwargs)
