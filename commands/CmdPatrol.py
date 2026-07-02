"""``@patrol`` — post an NPC to a base and put it on a beat.

The builder interface to the director's routines layer
(``world/director/routines.py``). Build the precinct, stand in it, post
the bot, give it a beat — the heartbeat does the rest.
"""

from evennia import Command

from world.director.routines import (
    HEARTBEAT_SECONDS,
    ensure_heartbeat,
    get_beat,
)


class CmdPatrol(Command):
    """
    Post an NPC to a base of operations and set its patrol beat.

    Usage:
        @patrol <npc>                     - post <npc> HERE (this room
                                            becomes its base: assignments
                                            return it here; intel syncs here)
        @patrol/beat <npc> = <r1>, <r2>…  - set the beat (room names/#dbrefs);
                                            the base is walked at the top of
                                            every loop automatically
        @patrol/auto <npc> = <radius>     - auto-beat: sample nearby rooms
                                            within <radius> of the base
        @patrol/base [complement]         - designate THIS room the security
                                            base: secbots spawn/post/sync/
                                            respawn here; the heartbeat keeps
                                            <complement> units alive (default 1)
        @patrol/status [npc]              - show posts and beats
        @patrol/clear <npc>               - take <npc> off patrol (keeps post)

    The heartbeat ticks every ~45s: an idle patroller walks one leg of
    its beat, sweeps the waypoint (security NPCs scan for wanted faces —
    a hit raises a disturbance on the spot), and moves on. Dispatch,
    travel, and combat always preempt; the beat resumes after.
    """

    key = "@patrol"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"

    def _find_npc(self, name):
        npc = self.caller.search(name, global_search=True)
        if npc and not npc.is_typeclass(
                "typeclasses.characters.Character", exact=False):
            self.caller.msg(f"{npc.get_display_name(self.caller)} is not a character.")
            return None
        return npc

    def func(self):
        caller = self.caller
        switches = self.switches or []
        args = self.args.strip()

        if "base" in switches:
            from world.director.population import set_security_base
            if caller.location is None:
                caller.msg("You have no location to designate.")
                return
            try:
                complement = int(args) if args else 1
            except ValueError:
                caller.msg("Complement must be a number.")
                return
            set_security_base(caller.location, complement)
            ensure_heartbeat()
            caller.msg(
                f"{caller.location.get_display_name(caller)} is now the "
                f"security base: secbots spawn, post, sync, and respawn "
                f"here; the heartbeat maintains a complement of "
                f"{complement}.")
            return

        if "status" in switches:
            import time
            from evennia.objects.models import ObjectDB
            from evennia.scripts.models import ScriptDB
            script = ScriptDB.objects.filter(
                db_key="director_routines").first()
            if script:
                last = getattr(script.db, "last_tick", None)
                ago = f"{int(time.time() - last)}s ago" if last else "NEVER"
                caller.msg(f"Heartbeat: last tick {ago} "
                           f"(counts: {getattr(script.db, 'last_counts', None)})")
            else:
                caller.msg("Heartbeat: no script exists.")
            npcs = ([self._find_npc(args)] if args else [
                o for o in ObjectDB.objects.filter(
                    db_attributes__db_key="patrol_beat").distinct()])
            npcs = [n for n in npcs if n]
            if not npcs:
                caller.msg("No one is on patrol.")
                return
            for npc in npcs:
                post = getattr(npc.db, "post", None)
                beat = get_beat(npc)
                caller.msg(
                    f"{npc.get_display_name(caller)} — post: "
                    f"{post.get_display_name(caller) if post else '(none)'}; "
                    f"beat: "
                    + (", ".join(r.get_display_name(caller) for r in beat)
                       if beat else "(none)"))
            return

        if "clear" in switches:
            npc = self._find_npc(args)
            if not npc:
                return
            npc.db.patrol_beat = None
            npc.ndb.patrol_idx = 0
            caller.msg(f"{npc.get_display_name(caller)} is off patrol "
                       f"(post kept).")
            return

        if "beat" in switches or "auto" in switches:
            if "=" not in args:
                caller.msg("Usage: @patrol/beat <npc> = <room>, <room>… "
                           "or @patrol/auto <npc> = <radius>")
                return
            name, _, rest = args.partition("=")
            npc = self._find_npc(name.strip())
            if not npc:
                return
            post = getattr(npc.db, "post", None)
            if post is None:
                caller.msg("Post them first: stand in the base room and "
                           "run @patrol <npc>.")
                return
            if "auto" in switches:
                from random import sample
                from world.spatial import rooms_within
                try:
                    radius = int(rest.strip())
                except ValueError:
                    caller.msg("Radius must be a number.")
                    return
                nearby = rooms_within(post, radius)
                if not nearby:
                    caller.msg("No coordinate rooms within that radius.")
                    return
                beat = sample(nearby, min(4, len(nearby)))
            else:
                beat = []
                for token in rest.split(","):
                    room = caller.search(token.strip(), global_search=True)
                    if not room:
                        return  # search already messaged
                    beat.append(room)
                if not beat:
                    caller.msg("No rooms given.")
                    return
            npc.db.patrol_beat = beat
            npc.ndb.patrol_idx = 0
            ensure_heartbeat()
            caller.msg(
                f"{npc.get_display_name(caller)} now walks: "
                + ", ".join(r.get_display_name(caller) for r in beat)
                + f" (base first, every loop; ~{HEARTBEAT_SECONDS}s a leg).")
            return

        # bare: post <npc> here
        if not args:
            caller.msg("Usage: @patrol <npc>  (see help @patrol)")
            return
        npc = self._find_npc(args)
        if not npc:
            return
        if caller.location is None:
            caller.msg("You have no location to post them to.")
            return
        npc.db.post = caller.location
        caller.msg(
            f"{npc.get_display_name(caller)} is posted to "
            f"{caller.location.get_display_name(caller)} — assignments "
            f"return it here; intel syncs here. Set a beat with "
            f"@patrol/beat or @patrol/auto.")
