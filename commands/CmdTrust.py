"""``trust`` / ``distrust`` — managing consent grants (TRUST_AND_CONSENT_SPEC §4).

Trust opens the conscious-and-willing path for invasive third-party actions
(dress, heal, …). It binds to the trusted person's CURRENT apparent identity:
if they change who they appear to be (doff an essential disguise, re-sleeve),
the grant silently stops matching.
"""

from evennia import Command

from world.consent import (
    ACTION_CLASSES, get_grants, grant_display_name, grant_trust,
    revoke_trust, wipe_trust,
)

_CLASSES_LINE = ", ".join(ACTION_CLASSES)


def _resolve_present_person(caller, phrase):
    """Resolve a phrase to a character PRESENT with the caller (grants are
    made face-to-face — spec §7.5). Emits its own failure message."""
    target = caller.search(phrase)
    if target is None:
        return None
    if target is caller:
        caller.msg("You don't need to trust yourself.")
        return None
    from world.identity import get_apparent_uid
    if not get_apparent_uid(target):
        caller.msg(
            f"{target.get_display_name(caller)} isn't someone you can "
            f"extend trust to."
        )
        return None
    return target


def _match_stored_grant(caller, phrase):
    """Match a phrase against stored grants by how the caller perceives
    them (recognition name or grant-time label) — the revoke path works
    from memory even when the person isn't here. Returns (uid, name) or
    (None, None); messages ambiguity/misses itself."""
    phrase_low = phrase.lower().strip()
    matches = []
    for uid, entry in get_grants(caller).items():
        name = grant_display_name(caller, uid, entry)
        low = name.lower()
        if phrase_low == low or phrase_low in low:
            matches.append((uid, name))
    if not matches:
        caller.msg(f"You don't have any trust extended to '{phrase}'.")
        return None, None
    if len(matches) > 1:
        names = ", ".join(name for _uid, name in matches)
        caller.msg(f"That matches more than one person you trust: {names}.")
        return None, None
    return matches[0]


class CmdTrust(Command):
    """
    Extend trust — let someone act on you while you're awake.

    Usage:
        trust                        - list who you trust, and with what
        trust <person>               - show what you trust that person with
        trust <person> to <action>   - grant one action class
        trust <person> to all        - grant everything
        trust no one                 - revoke every grant (same as distrust all)

    Action classes: dress, escort, grab, heal, search

    Most third-party actions land freely on someone who cannot contest —
    unconscious, dead, or restrained (grappled, strapped into a pod). Trust
    is the conscious-and-willing path: it lets the person you name do that
    class of thing to you while you're awake and free.

    Trust binds to the person AS YOU CURRENTLY PERCEIVE THEM. If they shed
    the identity you trusted (drop an essential disguise, re-sleeve into a
    new body), the grant no longer matches. Note that "heal" is deliberately
    all of medicine — treating, surgery, and harvesting alike. Choose your
    ripperdoc carefully.

    See also: distrust.
    """

    key = "trust"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()

        if not args:
            self._list_grants()
            return
        if args.lower() in ("no one", "noone", "nobody"):
            n = wipe_trust(caller)
            caller.msg("You trust no one now."
                       if n else "You already trust no one.")
            return

        person_phrase, sep, action = args.rpartition(" to ")
        if not sep:
            self._show_person(args)
            return
        person_phrase = person_phrase.strip()
        action = action.strip().lower()
        if action != "all" and action not in ACTION_CLASSES:
            caller.msg(f"'{action}' isn't a trustable action. "
                       f"Choose one of: {_CLASSES_LINE} — or 'all'.")
            return
        target = _resolve_present_person(caller, person_phrase)
        if target is None:
            return
        classes = grant_trust(caller, target, action)
        if not classes:
            caller.msg("That grant didn't take.")
            return
        name = target.get_display_name(caller)
        what = ("everything (" + ", ".join(classes) + ")"
                if action == "all" else action)
        caller.msg(
            f"You now trust {name} to {what}. It binds to them as they "
            f"appear now — if they become someone else, it lapses."
        )

    def _list_grants(self):
        caller = self.caller
        grants = get_grants(caller)
        if not grants:
            caller.msg("You trust no one.")
            return
        lines = ["You trust:"]
        for uid, entry in grants.items():
            name = grant_display_name(caller, uid, entry)
            classes = ", ".join(entry.get("classes") or ())
            lines.append(f"  {name} — {classes}")
        caller.msg("\n".join(lines))

    def _show_person(self, phrase):
        caller = self.caller
        target = _resolve_present_person(caller, phrase)
        if target is None:
            return
        from world.identity import get_apparent_uid
        entry = get_grants(caller).get(get_apparent_uid(target))
        name = target.get_display_name(caller)
        if not entry or not entry.get("classes"):
            caller.msg(f"You don't trust {name} with anything.")
            return
        caller.msg(f"You trust {name} to: "
                   + ", ".join(entry["classes"]) + ".")


class CmdDistrust(Command):
    """
    Revoke trust.

    Usage:
        distrust <person>              - revoke everything from that person
        distrust <person> to <action>  - revoke one action class
        distrust all                   - revoke every grant you've made

    Works from memory: the person doesn't need to be here — name them the
    way you know them (your recognition name for them, or how they looked
    when you granted it).

    See also: trust.
    """

    key = "distrust"
    aliases = ["untrust"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Usage: distrust <person> [to <action>] | distrust all")
            return
        if args.lower() == "all":
            n = wipe_trust(caller)
            caller.msg("You trust no one now."
                       if n else "You already trust no one.")
            return

        person_phrase, sep, action = args.rpartition(" to ")
        action_class = None
        if sep:
            person_phrase = person_phrase.strip()
            action_class = action.strip().lower()
            if action_class not in ACTION_CLASSES:
                caller.msg(f"'{action_class}' isn't a trustable action. "
                           f"Choose one of: {_CLASSES_LINE}.")
                return
        else:
            person_phrase = args

        uid, name = _match_stored_grant(caller, person_phrase)
        if uid is None:
            return
        if revoke_trust(caller, uid, action_class):
            what = action_class or "anything"
            caller.msg(f"You no longer trust {name} to {what}.")
        else:
            caller.msg(f"You didn't trust {name} to {action_class} "
                       f"in the first place.")
