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

from typing import TYPE_CHECKING, Any

import re

from world.grammar import capitalize_first

if TYPE_CHECKING:
    from typeclasses.characters import Character
    from typeclasses.rooms import Room


#: Per-class memo for :func:`_hears_broadcasts` -- the answer depends only
#: on the typeclass, and a busy room asks it once per object per message.
_MSG_HOOKED: dict[type, bool] = {}


def _implements_msg_hook(cls: type) -> bool:
    """Does ``cls`` define its own ``at_msg_receive``?

    Real Python functions only. A test double's auto-attribute is a Mock,
    not a function, so a bare ``MagicMock`` observer is not mistaken for a
    listening NPC.
    """
    cached = _MSG_HOOKED.get(cls)
    if cached is None:
        import inspect
        from evennia.objects.objects import DefaultObject

        hook = getattr(cls, "at_msg_receive", None)
        cached = (inspect.isfunction(hook)
                  and hook is not DefaultObject.at_msg_receive)
        _MSG_HOOKED[cls] = cached
    return cached


def _hears_broadcasts(observer: Any) -> bool:
    """Should this observer be rendered for at all?

    Two ways to want a room broadcast:

    * a **connected session** -- a player, who will read the text;
    * an **``at_msg_receive`` override** -- an NPC or fixture, which acts
      on the message rather than reading it.

    The gate used to test only the first, justified by the claim that
    "messages to session-less objects are discarded by Evennia anyway"
    (#462). That is false, and backwards. ``DefaultObject.msg`` calls
    ``at_msg_receive`` UNCONDITIONALLY and only consults sessions sixteen
    lines later, to decide where the *text* goes -- which is the entire
    mechanism ``LLMNpc`` is built on. Nothing was being discarded; by
    skipping the call the gate created the discard it claimed to be
    exploiting, and every LLM-driven NPC in the colony went blind to all
    eight social emotes (#2640).

    The performance motive behind #462 was sound and survives: items,
    corpses, organs and blood pools have ``.msg`` and no hook, so they
    still cost nothing. Only two classes in the codebase override
    ``at_msg_receive`` -- ``LLMNpcMixin`` and ``AnsweringFixture`` -- and
    both exist precisely to act on what they hear.
    """
    sessions = getattr(observer, "sessions", None)
    if sessions is not None:
        try:
            if sessions.count():
                return True
        except Exception:  # noqa: BLE001 - a handler that won't answer
            pass           #                is not a session
    return _implements_msg_hook(type(observer))


#: Every ``{placeholder}`` in a broadcast template, in source order.
_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

#: Colour codes are markup, not prose -- they must not count as the
#: text standing between a placeholder and the sentence before it.
_COLOUR_CODE_RE = re.compile(r"\|\[?\w{1,3}")


def _opens_a_sentence(template: str, pos: int) -> bool:
    """Does the placeholder at ``pos`` sit at the start of a sentence?

    True at the very start of the template, and after a ``.``, ``!`` or
    ``?``. False mid-sentence, so "... techs peel {actor} out of the
    gel" renders "an average man" rather than "An average man".

    Judged on the TEMPLATE, not on the rendered text: where a sentence
    begins is something the author decided, and it must not vary with
    whose name lands in the gap.
    """
    prefix = _COLOUR_CODE_RE.sub("", template[:pos]).strip()
    return not prefix or prefix[-1] in ".!?"


def msg_room_identity(
    location: "Room",
    template: str,
    char_refs: dict[str, "Character"],
    exclude: list | None = None,
    pre_resolved_refs: dict[str, dict] | None = None,
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
        pre_resolved_refs: Optional pre-computed display-name snapshots,
            shaped ``{placeholder: {observer: display_name_str}}``.
            When an observer has an entry under a placeholder, that
            string is used verbatim instead of calling
            ``char.get_display_name(observer)``.  This is the snapshot
            idiom used by actions whose effect mutates the actor's own
            sdesc inputs (e.g. putting on a disguise item) — the
            command captures pre-mutation names *before* mutating
            state, then passes them here so the broadcast describes
            the actor as they appeared at the moment they began the
            action.  See specs/IDENTITY_RECOGNITION_SPEC.md
            §"Action Broadcast Sdesc Stability".  Missing placeholder
            keys or missing observer keys silently fall through to
            the live ``get_display_name`` lookup.
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
    pre_resolved_refs = pre_resolved_refs or {}

    # Plan the substitution ONCE, per OCCURRENCE rather than per name.
    #
    # This used to pick a single "first placeholder" by minimum position,
    # then substitute it with an unbounded `str.replace`. Two things
    # were wrong with that, and both were about what an author may
    # safely write (#2641):
    #
    #   * `str.replace` has no count, so the capitalisation decided
    #     about one occurrence was applied to EVERY occurrence:
    #     "{actor} draws, and {actor} fires." rendered "A lanky man
    #     draws, and A lanky man fires." A repeated reference could not
    #     be written correctly at all.
    #   * sentence-start-ness was tested for that one placeholder only,
    #     so a later one opening a sentence was never considered:
    #     "{actor} steps back. {target} does not." rendered its second
    #     name lowercase, even though the guard right there reasons
    #     about ".!?" as terminators.
    #
    # Walking occurrences in order removes the "first placeholder"
    # concept entirely: each one gets its own verdict from the same
    # prefix test. Planned outside the observer loop because the
    # template is the same for everyone -- only the names differ.
    segments: list[str] = []
    plan: list[tuple[str, bool]] = []
    cursor = 0
    for match in _PLACEHOLDER_RE.finditer(template):
        name = match.group(1)
        if name not in char_refs:
            # Not ours. Another consumer's placeholder ({item}, {side})
            # passes through untouched, as it always has.
            continue
        segments.append(template[cursor:match.start()])
        plan.append((name, _opens_a_sentence(template, match.start())))
        cursor = match.end()
    segments.append(template[cursor:])

    for observer in location.contents:
        if observer in exclude_set:
            continue
        if not hasattr(observer, "msg"):
            continue
        # Audience gate (#462, corrected by #2640): render for observers
        # that will READ this (a connected session) or ACT on it (an
        # `at_msg_receive` override). Everything in a room has `.msg` —
        # items, corpses, organs, blood pools — and per-observer
        # display-name resolution is the most expensive render path in
        # the game, so the cheap majority is still skipped.
        if not _hears_broadcasts(observer):
            continue

        # One resolution per character per observer, however many times
        # the template names them -- `get_display_name` is the most
        # expensive call on this path and a repeated placeholder must
        # not pay for it twice.
        resolved_names: dict[str, str] = {}
        parts = [segments[0]]
        for index, (placeholder, capitalize) in enumerate(plan):
            display_name = resolved_names.get(placeholder)
            if display_name is None:
                snapshot_for_placeholder = pre_resolved_refs.get(placeholder)
                if (
                    snapshot_for_placeholder is not None
                    and observer in snapshot_for_placeholder
                ):
                    display_name = snapshot_for_placeholder[observer]
                else:
                    display_name = char_refs[placeholder].get_display_name(
                        observer
                    )
                resolved_names[placeholder] = display_name
            parts.append(
                capitalize_first(display_name) if capitalize else display_name
            )
            parts.append(segments[index + 1])

        observer.msg(text="".join(parts), **kwargs)
