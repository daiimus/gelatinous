"""``@dispatch`` — raise a world event here and route responders to it.

A builder/debug window onto the director's dispatch core
(``world/director/dispatch.py``). Eligible NPCs (by ``db.role``) walk to
your location via the spatial pathfinder.
"""

from evennia import Command

from world.director import WorldEvent, find_responders, raise_event
from world.director.dispatch import ROLE_RESPONDS_TO


class CmdDispatch(Command):
    """
    Raise a world event at your location and dispatch responders.

    Usage:
        @dispatch <type> [severity]   - raise an event; send responders
        @dispatch                     - list event types and who'd respond
        @dispatch/status              - show active assignments (the pool)

    Eligible NPCs are those whose ``db.role`` responds to the event type
    (set one with ``@set <npc>/role = security``). The nearest are routed
    to you over the exit graph; ``severity`` (default 1) scales how many.
    A dispatched responder arrives, investigates, lingers, then returns
    to its post; while assigned it will not answer other incidents.

    Example:
        @set guard/role = security
        @dispatch assault
    """

    key = "@dispatch"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if "status" in (self.switches or []):
            from world.director import active_assignments
            assignments = active_assignments()
            if not assignments:
                caller.msg("No active assignments — the pool is idle.")
                return
            caller.msg(f"|cActive assignments ({len(assignments)}):|n")
            for a in assignments:
                loc = a.event.location
                caller.msg(
                    f"  {a.npc.get_display_name(caller)} — {a.event.type} at "
                    f"{loc.get_display_name(caller) if loc else '?'} "
                    f"[{a.state}] (post: "
                    f"{a.post.get_display_name(caller) if a.post else '?'})"
                )
            return

        if not args:
            caller.msg("|cEvent types → responding roles:|n")
            for etype, roles in sorted(ROLE_RESPONDS_TO.items()):
                caller.msg(f"  {etype}: {', '.join(roles)}")
            caller.msg("Usage: @dispatch <type> [severity]")
            return

        parts = args.split()
        etype = parts[0].lower()
        severity = 1
        if len(parts) > 1 and parts[1].isdigit():
            severity = int(parts[1])

        if etype not in ROLE_RESPONDS_TO:
            caller.msg(
                f"Unknown event type '{etype}'. Known: "
                f"{', '.join(sorted(ROLE_RESPONDS_TO))}."
            )
            return

        if caller.location is None:
            caller.msg("You have no location to raise an event in.")
            return

        # Attach a BOLO snapshot of the instigator (§5.1: the responder
        # gets a description, never the perp object). Raising the event
        # on yourself means YOU match the report when the unit arrives.
        from world.director import build_bolo
        event = WorldEvent(
            type=etype, location=caller.location,
            severity=severity, source=caller,
            payload={"bolo": build_bolo(caller)},
        )
        ranked = find_responders(event)
        if not ranked:
            caller.msg(
                f"|y{etype}|n raised — but no reachable responder "
                f"({', '.join(ROLE_RESPONDS_TO[etype])}) found."
            )
            return

        dispatched = raise_event(event)
        caller.msg(
            f"|r{etype}|n (severity {severity}) raised at "
            f"{caller.location.get_display_name(caller)}. "
            f"Dispatched {len(dispatched)} of {len(ranked)} eligible:"
        )
        sent = set(dispatched)
        for steps, npc in ranked:
            mark = "|g→ en route|n" if npc in sent else "|x(standby)|n"
            caller.msg(
                f"  {npc.get_display_name(caller)} "
                f"({steps} steps away) {mark}"
            )
