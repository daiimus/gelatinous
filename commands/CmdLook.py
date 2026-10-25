"""`look`, with the aimed room in reach (#3596).

Evennia's `look <target>` searches the looker's own reach: their room
and their inventory. While a character aims down an exit, the room they
are looking INTO is the one down the barrel, so `look <target>` tries
that room first: a person there by their description (the identity
matcher, `world.search.identity_match_characters`; a Builder may also
use a real key), then a thing there by name, and only then the ordinary
reach, so a knife in your own hand is still `look knife`.

This replaces a widening that lived in `Character.get_search_candidates`
and reached EVERY command's default search while aiming. That widening
found things in the aimed room and not people (the identity pipeline
only read the looker's own room), so `look knife` worked down the
barrel and `look <the figure's description>` did not; and it let `put`,
`scan`, `diagnose`, `tune` and `remember` act on things on the street
below a parapet. Owner, 2026-10-24, on the audit: `look <description>`
down the barrel should work; emotes, `to` and `whisper` across the aim
should not. `attack` and `throw ... at` name the aimed room themselves
and are untouched.
"""
from evennia import default_cmds


class CmdLook(default_cmds.CmdLook):
    """
    look at location or object

    Usage:
      look
      look <obj>
      look *<account>

    Observes your location or objects in your vicinity. While aiming,
    `look` shows the room you aim into, and `look <target>` finds a
    person or thing there before it looks around you.
    """

    def func(self):
        caller = self.caller
        if not self.args:
            return super().func()
        location = caller.location
        aimed = (location.aimed_room_for(caller)
                 if location is not None and hasattr(location, "aimed_room_for")
                 else None)
        if aimed is not None:
            target = self.aimed_target(caller, aimed)
            if target is False:
                return                      # ambiguity already reported
            if target is not None:
                self.msg(text=(caller.at_look(target), {"type": "look"}),
                         options=None)
                return
        return super().func()

    def aimed_target(self, caller, aimed):
        """A person, then a thing, in *aimed*; None for neither, False
        when a multimatch was reported and the look should stop.

        People resolve the way `resolve_character_target` resolves them
        (identity first; a Builder may also name a real key), but the
        count is read here so one multimatch prints once and ends the
        look, whichever path found it. The presence gate applies to both
        pools (`filter_present`, and `get_search_candidates` on the
        explicit `candidates=`)."""
        from typeclasses.characters import Character
        from world.combat.constants import PERM_BUILDER
        from world.perception import filter_present
        from world.search import identity_match_characters

        query = self.args.strip()
        present = filter_present(caller, list(aimed.contents))
        people = identity_match_characters(caller, query, present)
        if not people and caller.check_permstring(PERM_BUILDER):
            staff_pool = [obj for obj in present if isinstance(obj, Character)]
            people = list(caller.search(query, candidates=staff_pool,
                                        quiet=True) or [])
        if len(people) > 1:
            caller.msg(f"Multiple targets match '{query}'. Please be more specific.")
            return False
        if people:
            return people[0]
        things = [obj for obj in aimed.contents
                  if not isinstance(obj, Character)
                  and getattr(obj, "destination", None) is None]
        found = caller.search(query, candidates=things, quiet=True) or []
        if len(found) > 1:
            caller.search(query, candidates=things)      # Evennia's multimatch text
            return False
        return found[0] if found else None
