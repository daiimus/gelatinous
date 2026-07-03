"""``@civilians`` — spawn, inspect, and purge the ambient population.

The refine-on-the-fly surface for the civilian layer
(``world/director/civilians.py``): the population is meant to be
iterated on, so everything here is cheap to redo.
"""

from evennia import default_cmds

from world.director.civilians import (
    CIVILIAN_ROLES,
    all_civilians,
    purge_civilians,
    spawn_civilian,
)


class CmdCivilians(default_cmds.MuxCommand):
    """
    Manage the civilian population.

    Usage:
        @civilians                        - list roles + the live census
        @civilians/spawn <role> [n]       - spawn n (default 1) of <role> HERE
        @civilians/populate <n>           - spawn n civilians (random roles)
                                            spread across random street rooms
        @civilians/purge [role]           - delete all civilians (or one role)

    Civilians are full people: named, dressed from their role's wardrobe,
    carrying 100-500 tokens (muggable), drifting between a few nearby
    haunts at a stroll (every 3-6 heartbeats), with a role persona the
    LLM puppets when someone engages them. All of them carry the
    civilian:director tag, so /purge can only ever touch them — never
    PCs, never the working NPCs.
    """

    key = "@civilians"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        switches = self.switches or []
        args = self.args.strip()

        if "spawn" in switches:
            parts = args.split()
            if not parts or parts[0] not in CIVILIAN_ROLES:
                caller.msg(f"Roles: {', '.join(sorted(CIVILIAN_ROLES))}. "
                           f"Usage: @civilians/spawn <role> [n]")
                return
            role = parts[0]
            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            spawned = [spawn_civilian(role, caller.location)
                       for _ in range(max(1, min(count, 20)))]
            spawned = [s for s in spawned if s]
            caller.msg(f"Spawned {len(spawned)} {role}(s) here: "
                       + ", ".join(s.key for s in spawned))
            return

        if "populate" in switches:
            from random import choice as rchoice
            from world.spatial.coordinates import all_coordinate_rooms
            try:
                count = max(1, min(int(args), 40))
            except (TypeError, ValueError):
                caller.msg("Usage: @civilians/populate <n>")
                return
            streets = [r for r in all_coordinate_rooms()
                       if "Room" in r.typeclass_path
                       and not getattr(r.db, "is_sky_room", False)]
            if not streets:
                caller.msg("No coordinate rooms to populate.")
                return
            spawned = []
            for _ in range(count):
                npc = spawn_civilian(rchoice(sorted(CIVILIAN_ROLES)),
                                     rchoice(streets))
                if npc:
                    spawned.append(npc)
            caller.msg(f"Populated {len(spawned)} civilians across the grid.")
            return

        if "purge" in switches:
            n = purge_civilians(args or None)
            caller.msg(f"Purged {n} civilian(s)"
                       + (f" (role: {args})" if args else "") + ".")
            return

        # bare: census
        civs = all_civilians()
        caller.msg(f"|cRoles:|n {', '.join(sorted(CIVILIAN_ROLES))}")
        caller.msg(f"|cLive civilians: {len(civs)}|n")
        for npc in civs[:30]:
            # NB: Evennia's .db returns None for unset attrs (getattr
            # defaults never fire) — coerce before format specs.
            role = npc.db.role or "?"
            caller.msg(
                f"  {npc.key[:24]:24} [{role:8}] @ "
                f"{npc.location.key[:28] if npc.location else '(none)'}")
        if len(civs) > 30:
            caller.msg(f"  … and {len(civs) - 30} more.")
