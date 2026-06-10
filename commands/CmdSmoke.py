"""Smoke / light / snuff commands.

Issues #454 (initial) and #456 (substance / delivery-method
generalisation).

Three commands share the same shape:

* Smokables are identified by the ``("smoke", "delivery_method")``
  tag; lighters by ``("lighter", "item_role")``.  Future joints,
  cigars, pipes carry the same smoke tag and route through these
  commands unchanged.  See
  ``specs/SUBSTANCES_AND_DELIVERY_SPEC.md`` for the layering.
* They use the held-hand surface (``caller.hands``) to enforce
  "the smokable / lighter must be in your hand."
* Per-observer broadcasts route through
  :func:`world.identity_utils.msg_room_identity`.

The interesting wrinkle is :class:`CmdLight`'s cross-character
syntax: ``light bob's cigarette`` lights a smokable held in Bob's
hand using the caller's lighter.  ``parse_possessive_target`` in
:mod:`world.smoke` does the split; ``resolve_character_target``
from :mod:`commands._identity_targeting` does the identity-aware
character lookup.
"""
from __future__ import annotations

from evennia import Command

from commands._identity_targeting import resolve_character_target
from world.identity_utils import msg_room_identity
from world.consumables import consume_use
from world.substances import apply_substance
from world.smoke import (
    find_held_lighter,
    find_held_smokable,
    get_substance,
    is_lit,
    is_smokable,
    parse_possessive_target,
    pick_burnt_out_message,
    pick_light_other_message,
    pick_light_self_message,
    pick_smoke_message,
    pick_snuff_message,
    set_lit,
)


# ---------------------------------------------------------------------
# Helpers shared across the three commands
# ---------------------------------------------------------------------


def _aliases_of(item) -> list[str]:
    """Return ``item.aliases`` as a plain list of strings.

    Evennia exposes ``aliases`` as an :class:`AliasHandler`, not a
    list — call ``.all()`` for the underlying tags.  Test fakes
    (plain lists) work via the duck-typed fallback.
    """
    aliases = getattr(item, "aliases", None)
    if aliases is None:
        return []
    if hasattr(aliases, "all"):
        return list(aliases.all() or [])
    try:
        return list(aliases)
    except TypeError:
        return []


def _find_held_smokable_matching(character, phrase: str):
    """Return the smokable in ``character``'s hand that matches
    ``phrase`` (case-insensitive substring against key / aliases),
    or None.  When ``phrase`` is empty, returns the first held
    smokable."""
    phrase = (phrase or "").strip().lower()
    hands = getattr(character, "hands", None) or {}
    candidates = [item for item in hands.values() if item and is_smokable(item)]
    if not phrase:
        return candidates[0] if candidates else None
    for item in candidates:
        haystack = " ".join(
            [getattr(item, "key", "") or ""] + _aliases_of(item)
        ).lower()
        if phrase in haystack:
            return item
    return None


# ---------------------------------------------------------------------
# CmdLight
# ---------------------------------------------------------------------


class CmdLight(Command):
    """
    Light a cigarette using a lighter wielded in your hand.

    Usage:
      light <cigarette>
      light <person>'s <cigarette>

    Both you and the person whose cigarette you're lighting must
    be holding it in a hand.  The lighter must be in one of your
    hands.

    Examples:
      light cigarette
      light noir cig
      light bob's cigarette
    """

    key = "light"
    locks = "cmd:all()"
    help_category = "Interaction"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Usage: light <cigarette> | light <person>'s <cigarette>")
            return

        # 1) Lighter must be wielded.
        lighter = find_held_lighter(caller)
        if lighter is None:
            caller.msg(
                "You need a lighter in your hand to light anything."
            )
            return

        # 2) Parse "bob's cig" vs "cig".
        owner_phrase, cigarette_phrase = parse_possessive_target(args)

        if owner_phrase is None:
            self._light_own(caller, cigarette_phrase, lighter)
            return
        self._light_other(caller, owner_phrase, cigarette_phrase, lighter)

    def _light_own(self, caller, phrase, lighter):
        cigarette = _find_held_smokable_matching(caller, phrase)
        if cigarette is None:
            caller.msg(
                "You aren't holding a cigarette matching that."
                if phrase else
                "You aren't holding a cigarette."
            )
            return
        if is_lit(cigarette):
            caller.msg("It's already lit.")
            return

        set_lit(cigarette, True)
        self_msg, room_template = pick_light_self_message()
        caller.msg(self_msg)
        if caller.location is not None:
            msg_room_identity(
                location=caller.location,
                template=room_template,
                char_refs={"actor": caller},
                exclude=[caller],
            )
        del lighter  # used for the contract check; no further action

    def _light_other(self, caller, owner_phrase, cigarette_phrase, lighter):
        target = resolve_character_target(caller, owner_phrase)
        if target is None:
            # resolve_character_target already messaged on ambiguity.
            # Hand-roll the no-match message.
            caller.msg(f"You don't see '{owner_phrase}' here.")
            return
        if target is caller:
            # User did "light self's cig" — fall through to own path.
            self._light_own(caller, cigarette_phrase, lighter)
            return

        cigarette = _find_held_smokable_matching(target, cigarette_phrase)
        if cigarette is None:
            tname = target.get_display_name(caller)
            caller.msg(f"{tname} isn't holding a cigarette matching that.")
            return
        if is_lit(cigarette):
            caller.msg("It's already lit.")
            return

        set_lit(cigarette, True)
        caller_msg, target_msg, room_template = pick_light_other_message()
        caller.msg(
            caller_msg.format(
                target=target.get_display_name(caller),
            )
        )
        if hasattr(target, "msg"):
            target.msg(
                target_msg.format(
                    actor=caller.get_display_name(target),
                )
            )
        if caller.location is not None:
            msg_room_identity(
                location=caller.location,
                template=room_template,
                char_refs={"actor": caller, "target": target},
                exclude=[caller, target],
            )
        del lighter


# ---------------------------------------------------------------------
# CmdSmoke
# ---------------------------------------------------------------------


class CmdSmoke(Command):
    """
    Take a puff from a lit cigarette in your hand.

    Usage:
      smoke <cigarette>

    The cigarette must be wielded in one of your hands and
    currently lit.  Each puff consumes one of the cigarette's
    remaining uses.  When the last puff is taken, the spent
    cigarette is tossed away.

    Examples:
      smoke cigarette
      smoke noir cig
    """

    key = "smoke"
    locks = "cmd:all()"
    help_category = "Interaction"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg(
                "Smoke what?  Name a smokable you're holding "
                "(``smoke cigarette`` / ``smoke smoke`` / "
                "``smoke joint``)."
            )
            return
        cigarette = _find_held_smokable_matching(caller, args)
        if cigarette is None:
            caller.msg(
                f"You aren't holding a smokable matching '{args}'."
            )
            return
        if not is_lit(cigarette):
            caller.msg("It isn't lit.  Light it first.")
            return

        substance = get_substance(cigarette)
        self_msg, room_template = pick_smoke_message(substance)
        caller.msg(self_msg)
        if caller.location is not None:
            msg_room_identity(
                location=caller.location,
                template=room_template,
                char_refs={"actor": caller},
                exclude=[caller],
            )

        # Pharmacology — one dose per puff through the substance
        # pipeline (issue #458).  Unregistered substances no-op
        # (flavor-only items are legitimate).  The subtle feedback
        # line only renders when an effect actually landed, so a
        # pain-free smoker just gets the flavor message.
        dose_result = apply_substance(caller, substance)
        for line in dose_result.get("feedback", ()):
            caller.msg(f"|c{line}|n")

        # Decrement puff count via the unified consumable helper.
        # When the last puff goes the item deletes itself; we emit
        # the burnout broadcast on that transition.
        outcome = consume_use(cigarette)
        if outcome.get("destroyed"):
            burnt_self, burnt_room = pick_burnt_out_message()
            caller.msg(burnt_self)
            if caller.location is not None:
                msg_room_identity(
                    location=caller.location,
                    template=burnt_room,
                    char_refs={"actor": caller},
                    exclude=[caller],
                )


# ---------------------------------------------------------------------
# CmdSnuff
# ---------------------------------------------------------------------


class CmdSnuff(Command):
    """
    Snuff out a lit cigarette you're holding.

    Usage:
      snuff <cigarette>

    The cigarette stays in your hand with its remaining puffs
    intact; you can light it again later.

    Examples:
      snuff cigarette
      snuff noir cig
    """

    key = "snuff"
    locks = "cmd:all()"
    help_category = "Interaction"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Snuff what?  Name a smokable you're holding.")
            return
        cigarette = _find_held_smokable_matching(caller, args)
        if cigarette is None:
            caller.msg(
                f"You aren't holding a smokable matching '{args}'."
            )
            return
        if not is_lit(cigarette):
            caller.msg("It isn't lit.")
            return

        set_lit(cigarette, False)
        self_msg, room_template = pick_snuff_message()
        caller.msg(self_msg)
        if caller.location is not None:
            msg_room_identity(
                location=caller.location,
                template=room_template,
                char_refs={"actor": caller},
                exclude=[caller],
            )
