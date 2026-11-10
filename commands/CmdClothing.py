# Clothing System Commands
#
# Complete clothing management system including:
# - CmdWear/CmdRemove: Basic wear/remove functionality
# - CmdRollUp/CmdUnroll: Adjustable clothing features
# - CmdZip/CmdUnzip: Closure management
#
from evennia import Command
from evennia.utils.utils import iter_to_str

from world.combat.constants import (
    STYLE_ADJUSTABLE,
    STYLE_CLOSURE,
    STYLE_STATE_NORMAL,
    STYLE_STATE_ROLLED,
    STYLE_STATE_UNZIPPED,
    STYLE_STATE_ZIPPED,
)
from world.grammar import with_article
from world.identity_utils import msg_room_identity


def _snapshot_actor_names(caller, char_refs):
    """Capture per-observer display names for *char_refs* before mutation.

    Returns a ``pre_resolved_refs`` mapping suitable for
    :func:`world.identity_utils.msg_room_identity` of the shape
    ``{placeholder: {observer: display_name}}``.

    This is the snapshot idiom for actions that mutate the actor's own
    sdesc inputs (clothing, future ``wield``/``appear``).  Without it,
    observers receive the broadcast describing the actor's *post-action*
    sdesc, which produces nonsense like "a lithe masked droog in a
    black balaclava puts on a black balaclava" — the message describes
    the actor as if the action had already taken effect on their
    appearance.  See specs/IDENTITY_RECOGNITION_SPEC.md
    §"Action Broadcast Sdesc Stability".

    Defensive: snapshots every placeholder in *char_refs* so future
    multi-actor templates (e.g. forced equip with ``{actor}`` and
    ``{victim}``) get stable names too, not only the placeholder we
    know mutates today.
    """
    location = caller.location
    if location is None:
        return {}
    from world.perception import perceivers
    observers = perceivers(location, {caller})
    return {
        placeholder: {obs: char.get_display_name(obs) for obs in observers}
        for placeholder, char in char_refs.items()
    }


def _articled(item_key: str) -> str:
    """Return ``"a black balaclava"`` / ``"blue jeans"`` for *item_key*.

    Pluralia-tantum nouns (``"blue jeans"``) are returned bare; all
    other nouns receive the appropriate indefinite article.
    """
    return with_article(item_key)


class CmdWear(Command):
    """
    Wear a clothing item from your inventory.

    Usage:
        wear <item>

    Examples:
        wear jacket
        wear leather boots
        wear 2nd shirt
    """

    key = "wear"
    aliases = []
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        from world.channeled import refuse_if_channeling
        if refuse_if_channeling(self.caller):   # BLOCKED while channeling (#3376)
            return
        caller = self.caller
        name = self.args.strip()
        if not name:
            caller.msg("Wear what?")
            return

        # Held items stay in caller.contents, so this one search reaches
        # the hands too; a held item the caller cannot perceive stays
        # unfound (#3783).
        matches = caller.search(name, location=caller, quiet=True)
        if not matches:
            caller.msg(f"You don't have '{name}'.")
            return
        item = matches[0]

        # Check if item is wearable
        if not item.is_wearable():
            caller.msg(f"You can't wear {item.key}.")
            return
        
        # Check if already worn
        if caller.is_item_worn(item):
            caller.msg(f"You're already wearing {item.key}.")
            return
        
        # Attempt to wear the item.  Snapshot observer names BEFORE
        # mutating worn_items so the broadcast describes the actor as
        # they appeared at the moment they began the action.
        char_refs = {"actor": caller}
        pre_resolved = _snapshot_actor_names(caller, char_refs)
        action_template = f"{{actor}} puts on {_articled(item.key)}."

        if getattr(item, "disguise_essential", False):
            # Essential item: the wear triggers an unmasking moment.
            # Route the action emote through apply_signature_change
            # so observers see a single combined "action + reveal"
            # message instead of two separate prose lines.
            success, message = caller.wear_item(
                item,
                action_template=action_template,
                action_char_refs=char_refs,
                action_pre_resolved_refs=pre_resolved,
                action_exclude=[caller],
            )
        else:
            # Non-essential — plain action broadcast, no unmask.
            def _broadcast_action():
                msg_room_identity(
                    location=caller.location,
                    template=action_template,
                    char_refs=char_refs,
                    exclude=[caller],
                    pre_resolved_refs=pre_resolved,
                )

            success, message = caller.wear_item(
                item, on_committed=_broadcast_action,
            )
        caller.msg(message)


class CmdRemove(Command):
    """
    Remove a worn clothing item.

    Usage:
        remove <item>
        unwear <item>
        remove all

    Examples:
        remove jacket
        unwear boots
        remove all
    """

    key = "remove"
    aliases = ["unwear"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        from world.channeled import refuse_if_channeling
        if refuse_if_channeling(self.caller):   # BLOCKED while channeling (#3376)
            return
        caller = self.caller
        name = self.args.strip()
        if not name:
            caller.msg("Remove what?")
            return

        # Handle "remove all"
        if name.lower() == "all":
            worn_items = caller.get_worn_items()
            if not worn_items:
                caller.msg("You're not wearing anything.")
                return

            # Snapshot observer names BEFORE mutating worn state so the
            # broadcast describes the actor as they appeared at the
            # moment they began the action.
            char_refs = {"actor": caller}
            pre_resolved = _snapshot_actor_names(caller, char_refs)

            # Broadcast the aggregate action ahead of the loop so any
            # per-item identity-shift broadcasts fired by remove_item
            # land *after* the action description, not before it.  Uses
            # the planned worn-items list (optimistic); partial failures
            # land asymmetrically in the actor's msg vs. the room
            # broadcast, but that's vanishingly rare for "remove all".
            articled = iter_to_str([_articled(it.key) for it in worn_items])
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} removes {articled}.",
                char_refs=char_refs,
                exclude=[caller],
                pre_resolved_refs=pre_resolved,
            )

            removed_items = []
            for item in worn_items:
                success, message = caller.remove_item(item)
                # A garment that TORE APART is not one you removed
                # (#2596). `_perish` deletes it and narrates the tear
                # itself; naming it here would print "You remove: a
                # coverall" for an object that no longer exists.
                # `item.key` still reads after `delete()` — the cached
                # value survives — so the object's `pk` is the only
                # honest test.
                if success and getattr(item, "pk", 1) is not None:
                    removed_items.append(item.key)

            if removed_items:
                caller.msg(f"You remove: {', '.join(removed_items)}")
            else:
                caller.msg("You couldn't remove anything.")
            return
        
        # Only worn items are in the pool, so "2nd shirt" counts worn
        # shirts (#3783).
        matches = caller.search(
            name, candidates=caller.get_worn_items(), quiet=True)
        if not matches:
            caller.msg(f"You're not wearing '{name}'.")
            return
        item = matches[0]

        # STICKY GRENADE WARNING - Check for stuck grenades before removal
        # Snapshot actor names BEFORE remove_item mutates worn state.
        char_refs = {"actor": caller}
        pre_resolved = _snapshot_actor_names(caller, char_refs)

        if item.db.stuck_grenade is not None:
            grenade = item.db.stuck_grenade
            
            # Get remaining countdown time if any
            # None for an inert grenade (dud / never armed) -> 0, so the
            # clamped warning below renders instead of a TypeError (#3361).
            remaining = getattr(grenade.ndb, 'countdown_remaining', 0) or 0
            stuck_location = grenade.db.stuck_to_location if grenade.db.stuck_to_location is not None else 'unknown'
            
            # Send dramatic warning
            if remaining > 0:
                caller.msg(
                    f"\n|R╔══════════════════════════════════════╗|n\n"
                    f"|R║  ⚠️  CRITICAL WARNING  ⚠️           ║|n\n"
                    f"|R║                                      ║|n\n"
                    f"|R║  LIVE {grenade.key.upper()} ATTACHED       ║|n\n"
                    f"|R║  COUNTDOWN: {remaining} SECONDS REMAINING   ║|n\n"
                    f"|R║  MAGNETICALLY CLAMPED AT {stuck_location.upper():^7}  ║|n\n"
                    f"|R║                                      ║|n\n"
                    f"|R║  Removing this armor will NOT       ║|n\n"
                    f"|R║  break the magnetic bond!           ║|n\n"
                    f"|R║  Grenade stays stuck to armor!      ║|n\n"
                    f"|R║                                      ║|n\n"
                    f"|R║  DROP ARMOR AND FLEE TO SURVIVE!    ║|n\n"
                    f"|R╚══════════════════════════════════════╝|n\n"
                )
            else:
                caller.msg(
                    f"\n|y*** WARNING ***|n\n"
                    f"A {grenade.key} is magnetically clamped to this {item.key}.\n"
                    f"Removing the armor will NOT break the magnetic bond.\n"
                    f"The grenade will remain stuck to the armor.\n"
                )
            
            # Warn the room (possessive form: "their X" stays as-is)
            msg_room_identity(
                location=caller.location,
                template=(
                    f"|R{{actor}} carefully removes their {item.key} - "
                    f"the magnetically attached {_articled(grenade.key)} moves "
                    f"with it!|n"
                ),
                char_refs=char_refs,
                exclude=[caller],
                pre_resolved_refs=pre_resolved,
            )
        
        # Action emote is gated by the no-grenade case (stuck grenade
        # already broadcast above).  When the item is disguise-
        # essential, route through the combined-message path so
        # observers see "X removes a balaclava, revealing they are
        # Drek Drivel" in one line; otherwise use the plain
        # on_committed hook to emit a standalone action broadcast
        # before the (non-essential) mutation runs.
        action_template = f"{{actor}} removes {_articled(item.key)}."
        is_essential = getattr(item, "disguise_essential", False)
        grenade_already_broadcast = item.db.stuck_grenade is not None

        if is_essential and not grenade_already_broadcast:
            success, message = caller.remove_item(
                item,
                action_template=action_template,
                action_char_refs=char_refs,
                action_pre_resolved_refs=pre_resolved,
                action_exclude=[caller],
            )
        else:
            def _broadcast_action():
                if not grenade_already_broadcast:
                    msg_room_identity(
                        location=caller.location,
                        template=action_template,
                        char_refs=char_refs,
                        exclude=[caller],
                        pre_resolved_refs=pre_resolved,
                    )

            success, message = caller.remove_item(
                item, on_committed=_broadcast_action,
            )
        # `remove_item` returns an EMPTY message when the garment tore
        # apart rather than coming off (#2596) — `_perish` has already
        # told the wearer and the room. Printing it would be a blank
        # line under the tear.
        if message:
            caller.msg(message)


#: What a garment's style STATES are called, in the second and third
#: person, and as a state to be "already" in.
#:
#: The style system is data-driven — `can_style_property_to` just checks
#: membership in the garment's own `style_configs` — and the commands
#: were not. They hard-coded the four canonical state names, so four
#: live garments declared states no command could ever reach: the
#: corporate blazer and the white lab coat close to `buttoned`/`open`,
#: the necktie to `loosened`, and the tox-sealed slicker to
#: `hood_up`/`hood_down` — where `hood_up` carries the garment's only
#: head coverage, so its hood could never be raised (#2742).
#:
#: The prose comes from the STATE rather than from the command, because
#: "you roll up the tox-sealed slicker" is the wrong sentence for
#: raising a hood.
_STYLE_PROSE = {
    "rolled":    ("roll up", "rolls up", "rolled up"),
    "loosened":  ("loosen", "loosens", "loosened"),
    "hood_up":   ("raise the hood on", "raises the hood on", "hood up"),
    "hood_down": ("lower the hood on", "lowers the hood on", "hood down"),
    "zipped":    ("zip up", "zips up", "zipped up"),
    "buttoned":  ("button up", "buttons up", "buttoned up"),
    "unzipped":  ("unzip", "unzips", "unzipped"),
    "open":      ("unbutton", "unbuttons", "unbuttoned"),
    "normal":    ("straighten", "straightens", "straight"),
}

#: Returning to `normal` is named for what you are undoing, not for the
#: state you land in: you unroll a rolled sleeve and straighten a
#: loosened tie, and both end up `normal`.
_RESTORE_PROSE = {
    "rolled":   ("unroll", "unrolls", "unrolled"),
    "loosened": ("straighten", "straightens", "straight"),
}

#: Each command's intent, as the state names that satisfy it in
#: preference order. The first one the GARMENT declares wins. The
#: canonical four are named through their constants so the two tables
#: cannot drift apart from `world/combat/constants.py`.
_ADJUST_TO = (STYLE_STATE_ROLLED, "loosened", "hood_up")
_RESTORE_TO = (STYLE_STATE_NORMAL, "hood_down")
_CLOSE_TO = (STYLE_STATE_ZIPPED, "buttoned")
_OPEN_TO = (STYLE_STATE_UNZIPPED, "open")


def _target_style_state(item, prop, wanted):
    """The first of *wanted* this garment actually declares.

    The garment's own `style_configs` is the authority. The commands
    used to name the state themselves, which is why a garment calling
    its states anything else was unreachable (#2742).
    """
    declared = (item.style_configs or {}).get(prop) or {}
    for state in wanted:
        if state in declared:
            return state
    return None


def _style_prose(target_state, current_state):
    """(second person, third person, already-adjective) for a change."""
    if target_state == "normal" and current_state in _RESTORE_PROSE:
        return _RESTORE_PROSE[current_state]
    return _STYLE_PROSE.get(target_state, ("adjust", "adjusts", "adjusted"))


class CmdRollUp(Command):
    """
    Roll up sleeves or similar adjustable clothing features.

    Usage:
        rollup <item>
        unroll <item>

    Examples:
        rollup shirt
        unroll sleeves
        rollup jacket
    """

    key = "rollup"
    aliases = ["unroll"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        from world.channeled import refuse_if_channeling
        if refuse_if_channeling(self.caller):   # BLOCKED while channeling (#3376)
            return
        caller = self.caller
        name = self.args.strip()
        if not name:
            caller.msg("Roll up what?")
            return

        # The pool is every worn item, not only adjustable ones, so a
        # worn garment with nothing to roll gets its own refusal below
        # (#3783).
        matches = caller.search(
            name, candidates=caller.get_worn_items(), quiet=True)
        if not matches:
            caller.msg(f"You're not wearing '{name}'.")
            return
        item = matches[0]

        # Ask the GARMENT what it can be adjusted TO, rather than
        # naming a state and hoping it has one (#2742).
        adjusting = self.cmdstring.lower() == "rollup"
        wanted = _ADJUST_TO if adjusting else _RESTORE_TO

        if STYLE_ADJUSTABLE not in item.style_configs:
            verb = "roll up" if adjusting else "unroll"
            caller.msg(f"The {item.key} doesn't have anything to {verb}.")
            return

        current_state = item.get_style_property(STYLE_ADJUSTABLE)
        target_state = _target_style_state(item, STYLE_ADJUSTABLE, wanted)
        if target_state is None:
            verb = "roll up" if adjusting else "unroll"
            caller.msg(f"There's no way to {verb} the {item.key}.")
            return

        action, action_third, already = _style_prose(
            target_state, current_state)

        if current_state == target_state:
            caller.msg(f"The {item.key} is already {already}.")
            return

        if not item.can_style_property_to(STYLE_ADJUSTABLE, target_state):
            caller.msg(f"That wouldn't change anything about the {item.key}.")
            return
        
        # Snapshot observer names BEFORE the style change so the
        # broadcast describes the actor as they appeared at the
        # moment they began the action (rolling/unrolling can
        # change worn_sdesc_short and thus the sdesc).
        char_refs = {"actor": caller}
        pre_resolved = _snapshot_actor_names(caller, char_refs)

        # Apply the style change
        success = item.set_style_property(STYLE_ADJUSTABLE, target_state)
        
        if success:
            caller.msg(f"You {action} the {item.key}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} {action_third} {_articled(item.key)}.",
                char_refs=char_refs,
                exclude=[caller],
                pre_resolved_refs=pre_resolved,
            )
        else:
            caller.msg(f"You can't {action} the {item.key}.")


class CmdZip(Command):
    """
    Zip, unzip, button, or unbutton clothing items with closures.

    Usage:
        zip <item>
        unzip <item>
        button <item>
        unbutton <item>

    Examples:
        zip jacket
        unzip boots
        button shirt
        unbutton coat
        zip up coat
    """

    key = "zip"
    aliases = ["unzip", "button", "unbutton"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        from world.channeled import refuse_if_channeling
        if refuse_if_channeling(self.caller):   # BLOCKED while channeling (#3376)
            return
        caller = self.caller
        typed = self.args.strip()
        if not typed:
            caller.msg("Zip what?")
            return

        # Handle "zip up" as just "zip". Strip first, then test for
        # "up ", so the name left behind is never empty.
        name = typed
        if name.lower().startswith("up "):
            name = name[3:].strip()

        # The pool is every worn item, not only ones with a closure, so
        # a worn garment without one gets its own refusal below (#3783).
        matches = caller.search(
            name, candidates=caller.get_worn_items(), quiet=True)
        if not matches:
            caller.msg(f"You're not wearing '{typed}'.")
            return
        item = matches[0]

        # The closure the GARMENT declares, preferring the one this
        # command is named for. The corporate blazer and the white lab
        # coat close to `buttoned`/`open`, which neither `zip` nor
        # `button` could reach while the state was hard-coded (#2742).
        cmd = self.cmdstring.lower()
        closing = cmd in ("zip", "button")
        wanted = _CLOSE_TO if closing else _OPEN_TO
        if cmd in ("button", "unbutton"):
            wanted = tuple(reversed(wanted))     # prefer buttoned / open

        if STYLE_CLOSURE not in item.style_configs:
            if cmd in ("zip", "unzip"):
                caller.msg(f"The {item.key} doesn't have a zipper.")
            else:  # button, unbutton
                caller.msg(f"The {item.key} doesn't have buttons.")
            return

        current_state = item.get_style_property(STYLE_CLOSURE)
        target_state = _target_style_state(item, STYLE_CLOSURE, wanted)
        if target_state is None:
            caller.msg(f"There's no way to {'close' if closing else 'open'} "
                       f"the {item.key}.")
            return

        action, action_past, already = _style_prose(
            target_state, current_state)

        if current_state == target_state:
            caller.msg(f"The {item.key} is already {already}.")
            return

        if not item.can_style_property_to(STYLE_CLOSURE, target_state):
            caller.msg(f"That wouldn't change anything about the {item.key}.")
            return
        
        # Snapshot observer names BEFORE the style change so the
        # broadcast describes the actor as they appeared at the
        # moment they began the action (zipping/buttoning can
        # change worn_sdesc_short and thus the sdesc).
        char_refs = {"actor": caller}
        pre_resolved = _snapshot_actor_names(caller, char_refs)

        # Apply the style change
        success = item.set_style_property(STYLE_CLOSURE, target_state)
        
        if success:
            caller.msg(f"You {action} the {item.key}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} {action_past} {_articled(item.key)}.",
                char_refs=char_refs,
                exclude=[caller],
                pre_resolved_refs=pre_resolved,
            )
        else:
            caller.msg(f"You can't {action} the {item.key}.")


# =====================================================================
# Third-party clothing manipulation (#307, PR-H3)
# =====================================================================
#
# Two new verbs surface the third-party clothing interface settled
# in the design discussion:
#
#   dress <target> in <item>     — put clothing on someone / something
#   undress <target> [<item>]    — remove clothing from someone / something
#
# Both verbs gate on whether the target can refuse:
#
#   * Severed appendages (worn-on-severed structure introduced in
#     this PR) are always dressable
#   * Unconscious, dead and restrained characters cannot contest,
#     so the action lands freely
#   * A conscious, unrestrained character must have trusted the
#     caller for the ``dress`` class
#
# Characters do not answer that question here: they ride the shared
# consent gate (world/consent.check_consent, TRUST_AND_CONSENT_SPEC
# ``dress`` class), so any new permission rule belongs there rather
# than hard-coded into these verbs.


def _can_third_party_clothing(caller, target):
    """Permission gate for dress / undress (#307 PR-H3; trust layer #967).

    Severed appendages are always dressable. Characters ride the shared
    consent gate (TRUST_AND_CONSENT_SPEC ``dress`` class): free when the
    target cannot contest (unconscious / dead / restrained), otherwise the
    target must have trusted the caller to dress them.
    """
    from typeclasses.items import Appendage
    if isinstance(target, Appendage):
        return True
    from world.consent import check_consent
    return check_consent(caller, target, "dress")


def _is_corpse(target) -> bool:
    """A corpse, by type.

    `isinstance`, not a duck-type: every `hasattr` on a MagicMock is
    True, and this predicate is reachable from tests that pass mocks.
    """
    try:
        from typeclasses.corpse import Corpse
    except Exception:  # noqa: BLE001
        return False
    return isinstance(target, Corpse)


def _resolve_clothing_target(caller, target_phrase, quiet=False):
    """Resolve a third-party clothing target with identity-layer
    obfuscation.

    Three resolution stages, mirroring ``CmdSurgical._resolve_target``
    so the surface for ``dress`` / ``undress`` matches the rest of
    the medical / interaction verbs:

    1. **Identity pipeline** (``resolve_character_target``) — the
       *only* path to a character target.  Handles default sdescs
       ("towering", "woman"), recognised-name keywords, and disguise
       overrides.  Has its own staff fallback for builders that
       cannot find an identity match (key-based search), so the
       privileged-key path is preserved for admins without leaking
       through to ordinary players.
    2. **Inventory fallback** — severed appendages the caller is
       carrying.  Characters can't be in inventory, so naturally
       character-free.
    3. **Room fallback** — corpses and other non-character targets
       in the same room.  Characters explicitly filtered so a
       player can't bypass identity obfuscation by typing a real
       character key.

    Returns ``None`` on no match.  The identity helper / search
    emit their own messages on ambiguity or not-found.
    """
    raw = target_phrase.strip()
    if not raw:
        return None

    # Stage 1 — identity pipeline (only path to character targets).
    from commands._identity_targeting import resolve_character_target
    identity_match = resolve_character_target(
        caller, raw, allow_self=False,
    )
    if identity_match is not None:
        return identity_match

    # Stage 2 — inventory fallback (severed limbs etc).
    candidates = list(caller.contents)
    if candidates:
        inventory_match = caller.search(
            raw, candidates=candidates, quiet=True,
        )
        if inventory_match:
            return (
                inventory_match[0]
                if isinstance(inventory_match, list)
                else inventory_match
            )

    # Stage 3 — room fallback, characters filtered out so identity
    # is the only path to a character target.
    from typeclasses.characters import Character
    location = caller.location
    if location is None:
        return None
    non_character_candidates = [
        obj for obj in location.contents
        if not isinstance(obj, Character)
    ]
    # `quiet` matters for the two-argument form (#2517): `undress bob
    # jacket` asks greedily for a target named "bob jacket" first, which
    # is GUARANTEED to fail because the phrase contains the item word.
    # Stage 3 was the only stage that spoke, so every use of the
    # documented form printed `Could not find "bob jacket".` one line
    # before succeeding.
    if not non_character_candidates:
        match = caller.search(raw, candidates=[], quiet=quiet)
    else:
        match = caller.search(raw, candidates=non_character_candidates,
                              quiet=quiet)
    # UNWRAP, as stage 2 already does. `search(quiet=True)` returns a
    # LIST; only the loud form returns an object. Stage 3 returned it
    # raw, so the greedy first pass in `undress`/`dress` -- which is
    # always quiet -- handed every room target back as a one-element
    # list (#2475).
    #
    # That is what actually made `undress corpse` refuse. The consent
    # gate was fixed to recognise a Corpse (#2519), but a list is not a
    # Corpse: `is_conscious` fell through to "no readable medical
    # state, assume awake", the caller was told the corpse "is
    # conscious and would resist", and building that very message then
    # raised AttributeError on `list.get_display_name`.
    if isinstance(match, (list, tuple)):
        return match[0] if match else None
    return match


class CmdDress(Command):
    """Dress another character or severed body part in a clothing item.

    Usage:
        dress <target> in <item>

    Examples:
        dress unconscious bob in jacket
        dress severed left arm in leather glove
        dress corpse in burial shroud

    Works freely on a target who cannot contest — unconscious,
    dead, restrained, or a severed appendage. A conscious, free
    target must have trusted you to dress them (see ``help
    trust``). The clothing item must be in your inventory; it
    transfers to the target along with the worn registration.

    Related: undress, wear, remove.
    """

    key = "dress"
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        from world.channeled import refuse_if_channeling
        if refuse_if_channeling(self.caller):   # BLOCKED while channeling (#3376)
            return
        caller = self.caller
        args = (self.args or "").strip()

        if " in " not in args:
            caller.msg("Usage: dress <target> in <item>")
            return

        target_phrase, _, item_phrase = args.partition(" in ")
        target_phrase = target_phrase.strip()
        item_phrase = item_phrase.strip()
        if not target_phrase or not item_phrase:
            caller.msg("Usage: dress <target> in <item>")
            return

        target = _resolve_clothing_target(caller, target_phrase)
        if target is None:
            return

        item = caller.search(item_phrase, location=caller, quiet=True)
        if not item:
            caller.msg(f"You don't have '{item_phrase}'.")
            return
        if isinstance(item, list):
            item = item[0]

        if not _can_third_party_clothing(caller, target):
            caller.msg(
                f"{target.get_display_name(caller)} is conscious "
                f"and would resist — they'd need to trust you to "
                f"dress them (or be restrained)."
            )
            return

        if not hasattr(item, "is_wearable") or not item.is_wearable():
            caller.msg(f"{item.get_display_name(caller)} can't be worn.")
            return

        from typeclasses.items import Appendage
        # SNAPSHOT BEFORE MUTATING (#2520). Every first-person verb in
        # this file captures per-observer display names before touching
        # `worn_items` and broadcasts with `pre_resolved_refs`; the two
        # THIRD-PARTY doors did neither. Dressing someone in a
        # disguise-essential garment shifts THEIR sdesc, so a broadcast
        # composed afterwards names the target by the identity the mask
        # just gave them — "X dresses a masked stranger in a balaclava"
        # — instead of by who the room was looking at a moment ago.
        #
        # `_dress_character` was given an `on_committed` hook for
        # exactly this, documented as being "so the caller can interpose
        # an action broadcast before the mutation fires any
        # identity-shift recognition messages". It was plumbed and never
        # passed.
        item_name_d = item.get_display_name(caller)
        char_refs = {"actor": caller, "target": target}
        pre_resolved = _snapshot_actor_names(caller, char_refs)
        action_template = f"{{actor}} dresses {{target}} in {item_name_d}."

        def _broadcast_action():
            msg_room_identity(
                location=caller.location,
                template=action_template,
                char_refs=char_refs,
                exclude=[caller, target],
                pre_resolved_refs=pre_resolved,
            )

        broadcast_done = False
        if isinstance(target, Appendage):
            success, message = self._dress_appendage(target, item)
        elif _is_corpse(target):
            success, message = self._dress_corpse(target, item)
        elif hasattr(target, "wear_item"):
            if getattr(item, "disguise_essential", False):
                # Essential: route the action through the unmask so
                # observers get one combined line, the way `CmdWear`
                # does for the first-person case.
                success, message = self._dress_character(
                    target, item,
                    action_template=action_template,
                    action_char_refs=char_refs,
                    action_pre_resolved_refs=pre_resolved,
                    action_exclude=[caller, target],
                )
            else:
                success, message = self._dress_character(
                    target, item, on_committed=_broadcast_action)
            broadcast_done = True
        else:
            caller.msg(
                f"You can't dress {target.get_display_name(caller)}."
            )
            return

        if not success:
            caller.msg(message)
            return

        target_name_d = target.get_display_name(caller)
        caller.msg(f"You dress {target_name_d} in {item_name_d}.")
        if (
            hasattr(target, "has_account")
            and getattr(target, "has_account", False)
            and hasattr(target, "msg")
        ):
            target.msg(
                f"{caller.get_display_name(target)} dresses you in "
                f"{item.get_display_name(target)}."
            )
        if not broadcast_done:
            # Appendages and corpses have no `wear_item` and no identity
            # to shift, so they broadcast here as before.
            _broadcast_action()
        # LLM NPC perception (#954): being dressed is tactile and personal.
        try:
            from world.llm.observation import (
                clothing_line, observe_directed_action, observe_event)
            observe_event(caller.location,
                          clothing_line(caller, target, item, dressing=True),
                          exclude=(caller, target))
            observe_directed_action(
                caller, target,
                f"{caller.get_display_name(target)} dresses you in "
                f"{item.get_display_name(target)}.")
        except Exception:  # noqa: BLE001 — perception never breaks the verb
            pass

    def _dress_character(self, target, item, *, on_committed=None,
                         action_template=None, action_char_refs=None,
                         action_pre_resolved_refs=None, action_exclude=None):
        """Move the item into ``target``'s inventory and call its
        existing ``wear_item`` method.  On failure, roll the item
        back to the caller so it isn't orphaned on a target that
        wouldn't accept it.

        ``on_committed`` is forwarded to ``wear_item`` so the caller
        can interpose an action broadcast before the mutation fires
        any identity-shift recognition messages."""
        item.move_to(target, quiet=True)
        success, message = target.wear_item(
            item, on_committed=on_committed,
            action_template=action_template,
            action_char_refs=action_char_refs,
            action_pre_resolved_refs=action_pre_resolved_refs,
            action_exclude=action_exclude,
        )
        if not success:
            item.move_to(self.caller, quiet=True)
        return success, message

    def _dress_corpse(self, target, item):
        """Put a garment on a corpse (#2519).

        A corpse has no `worn_items` map and no `wear_item` — moving the
        garment into its contents IS dressing it, because
        `_build_corpse_clothing_coverage_map` renders every item there
        that declares coverage. The gate used to refuse this outright
        and tell the player the corpse "is conscious and would resist",
        while the command's own help offered `dress corpse in burial
        shroud` as an example.
        """
        item.move_to(target, quiet=True)
        # Tell the corpse this one is WORN (#2460). The coverage map is
        # filtered by `worn_at_death` now, so a corpse carrying that
        # record would render a freshly-dressed shroud as loose loot
        # and show the body underneath it.
        marker = getattr(target, "mark_worn", None)
        if callable(marker):
            marker(item)
        return True, ""

    def _dress_appendage(self, target, item):
        """Worn-on-severed-appendage path.  Match the item's
        coverage against the locations the part carries; wear at the
        intersection.

        Those locations are the severed cluster -- the same set the
        travel rule chose the part's garments by and the renderer
        walks: a limb's downstream chain, a head's whole head cluster
        (hair, eyes, face, ears, neck too), so goggles fit a severed
        head and a balaclava registers at hair AND head.  Not
        ``db.chain``: that is the limb table, which has no head entry,
        and the part's display name reads it.

        Rejects items that don't cover any carried location (a right
        glove can't wear on a severed left arm; a chest piece can't
        wear on a severed leg; a glove can't wear on a head).
        """
        from typeclasses.items import severed_cluster
        chain = set(severed_cluster(
            target.db.source_species or "human",
            target.db.location_name or "",
        ))
        if hasattr(item, "get_current_coverage"):
            coverage = set(item.get_current_coverage() or ())
        else:
            coverage = set()

        applicable = coverage & chain
        if not applicable:
            return False, (
                f"{item.get_display_name(self.caller)} doesn't fit on "
                f"{target.get_display_name(self.caller)}."
            )

        item.move_to(target, quiet=True)
        appendage_worn = dict(target.db.worn_items or {})
        for loc in applicable:
            existing = list(appendage_worn.get(loc) or ())
            if item not in existing:
                # Outermost first, the living stack's order (#3578): the
                # renderer takes the first entry at each location, so a
                # higher layer goes in front of every lower one, the way
                # ClothingMixin.wear_item inserts.
                index = 0
                for i, worn in enumerate(existing):
                    if (getattr(item, "layer", 0) or 0) <= (getattr(worn, "layer", 0) or 0):
                        index = i + 1
                    else:
                        break
                existing.insert(index, item)
                appendage_worn[loc] = existing
        target.db.worn_items = appendage_worn
        return True, ""


class CmdUndress(Command):
    """Remove clothing from another character or severed body part.

    Usage:
        undress <target>
        undress <target> <item>

    First form removes all worn items.  Second removes a single
    worn item, named by key or alias (``jacket-2`` picks the second
    of two).  Removed items transfer to your inventory.

    Works freely on a target who cannot contest (unconscious,
    dead, restrained, or a severed appendage); a conscious, free
    target must have trusted you — same gate as ``dress``.

    Related: dress, remove.
    """

    key = "undress"
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        from world.channeled import refuse_if_channeling
        if refuse_if_channeling(self.caller):   # BLOCKED while channeling (#3376)
            return
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Usage: undress <target> [<item>]")
            return

        # Greedy on target first — multi-word targets like
        # ``severed left arm`` work.  Only narrow if the whole
        # phrase doesn't resolve.
        # The greedy pass is SILENT: it is expected to fail whenever an
        # item was named, and its error contradicted the success that
        # followed (#2517).
        target = _resolve_clothing_target(caller, args, quiet=True)
        item_phrase = None
        if target is None:
            tokens = args.rsplit(" ", 1)
            if len(tokens) == 2:
                maybe_target = tokens[0].strip()
                maybe_item = tokens[1].strip()
                target = _resolve_clothing_target(caller, maybe_target)
                if target is not None:
                    item_phrase = maybe_item
        if target is None:
            # Nothing resolved either way — say so once, about the whole
            # phrase, rather than staying silent because the greedy pass
            # was quiet.
            _resolve_clothing_target(caller, args)
            return

        if not _can_third_party_clothing(caller, target):
            caller.msg(
                f"{target.get_display_name(caller)} is conscious "
                f"and would resist — they'd need to trust you to "
                f"dress them (or be restrained)."
            )
            return

        # SNAPSHOT BEFORE THE REMOVAL LOOP (#2520). Taking a
        # disguise-essential garment OFF shifts the target's sdesc just
        # as putting one on does, so a broadcast composed afterwards
        # names them by the identity the unmasking revealed rather than
        # the one the room had been looking at.
        #
        # Undress removes a LIST through `remove_item`, so unlike
        # `dress` there is no single mutation to interpose on; the
        # snapshot plus `pre_resolved_refs` on the existing broadcast is
        # the faithful equivalent.
        undress_refs = {"actor": caller, "target": target}
        undress_pre_resolved = _snapshot_actor_names(caller, undress_refs)

        from typeclasses.items import Appendage
        if isinstance(target, Appendage) or _is_corpse(target):
            removed = self._undress_remains(target, item_phrase)
        elif hasattr(target, "worn_garments"):
            removed = self._undress_character(target, item_phrase)
        else:
            caller.msg(
                f"You can't undress {target.get_display_name(caller)}."
            )
            return

        if not removed:
            if item_phrase:
                caller.msg(
                    f"{target.get_display_name(caller)} isn't wearing "
                    f"'{item_phrase}'."
                )
            else:
                caller.msg(
                    f"{target.get_display_name(caller)} isn't wearing "
                    f"anything."
                )
            return

        for item in removed:
            item.move_to(caller, quiet=True)

        names = ", ".join(item.get_display_name(caller) for item in removed)
        target_name = target.get_display_name(caller)
        caller.msg(f"You undress {target_name}, taking: {names}.")
        if (
            hasattr(target, "has_account")
            and getattr(target, "has_account", False)
            and hasattr(target, "msg")
        ):
            target.msg(
                f"{caller.get_display_name(target)} undresses you, "
                f"taking your clothing."
            )
        msg_room_identity(
            location=caller.location,
            template=f"{{actor}} undresses {{target}}.",
            char_refs=undress_refs,
            exclude=[caller, target],
            pre_resolved_refs=undress_pre_resolved,
        )
        # LLM NPC perception (#954): being stripped is VERY personal.
        try:
            from world.llm.observation import (
                clothing_line, observe_directed_action, observe_event)
            observe_event(caller.location,
                          clothing_line(caller, target, dressing=False),
                          exclude=(caller, target))
            observe_directed_action(
                caller, target,
                f"{caller.get_display_name(target)} undresses you, "
                f"taking your clothing.")
        except Exception:  # noqa: BLE001 — perception never breaks the verb
            pass

    def _undress_character(self, target, item_phrase):
        """Strip worn items off ``target`` and return the removed
        list.  Uses ``remove_item`` so layer-conflict / state
        cleanup runs the same way it does for self-removal."""
        worn = target.worn_garments()
        if not worn:
            return []

        if item_phrase:
            # The ONE item the player named, never every garment whose
            # name contains the word (#2517). The pool sits on the
            # target, not the caller; candidates= does not care (#3783).
            worn = self.caller.search(
                item_phrase, candidates=worn, quiet=True)[:1]
            if not worn:
                return []

        removed = []
        for item in worn:
            success, _msg = target.remove_item(item)
            # a torn garment is not taken (#2596)
            if success and getattr(item, "pk", 1) is not None:
                removed.append(item)
        return removed

    def _undress_remains(self, target, item_phrase):
        """Take garments off a corpse or a severed part and return the
        removed list. Both answer `worn_garments()` from their own store
        (the corpse from contents + `worn_at_death`, the part from its
        ledger), and both clean up on the move -- the corpse clears its
        death-time signature, the part releases the wardrobe slot -- so
        this is the same three lines for either (#3575)."""
        garments = target.worn_garments()
        if not garments:
            return []
        if item_phrase:
            # One named garment, as `_undress_character` (#2517, #3783).
            garments = self.caller.search(
                item_phrase, candidates=garments, quiet=True)[:1]
        removed = []
        for item in garments:
            item.move_to(self.caller, quiet=True)
            removed.append(item)
        return removed
