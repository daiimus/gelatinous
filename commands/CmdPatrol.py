"""``@patrol`` — post an NPC to a base and put it on a beat.

The builder interface to the director's routines layer
(``world/director/routines.py``). Build the precinct, stand in it, post
the bot, give it a beat — the heartbeat does the rest.
"""

from evennia import default_cmds

from world.director.routines import (
    HEARTBEAT_SECONDS,
    ensure_heartbeat,
    get_beat,
)


class CmdPatrol(default_cmds.MuxCommand):
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
        @patrol/dispatch                  - designate THIS room the dispatch
                                            room: the console and the operator
                                            live here (respawns stay at the
                                            base); without one, dispatch works
                                            from the base itself
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

    #: Without this, `MuxCommand.parse` does not validate switches at
    #: all, and an unrecognised one is simply dropped. Every branch in
    #: `func` is a membership test with no `else`, so the fall-through
    #: was the BARE form -- re-post this NPC to wherever the builder is
    #: standing, overwriting `db.post`. `@patrol/stat bob` silently
    #: moved bob's post instead of printing his status (#2565).
    #:
    #: Declaring the options also buys abbreviation: `/stat` now
    #: resolves to `/status`, and an ambiguous prefix says so.
    switch_options = ("base", "dispatch", "status", "clear", "beat", "auto")

    def parse(self):
        """Lower-case the switch, and remember that one was typed.

        `MuxCommand` compares switches case-SENSITIVELY, so `/Status`
        matches nothing even with `switch_options` declared: it is
        reported as an extra switch, dropped, and `self.switches` comes
        back empty -- indistinguishable in `func` from the bare form.
        Two separate steps are needed, and neither is enough alone:

        * fold the case here, so `/Status` and `/STATUS` work;
        * record that a switch was TYPED, so `func` can refuse rather
          than falling through when nothing survives validation.
        """
        raw = self.args or ""
        self.typed_a_switch = raw.startswith("/")
        if self.typed_a_switch:
            head, sep, tail = raw.partition(" ")
            self.args = head.lower() + sep + tail
        super().parse()

    def _walkable_waypoint(self, npc, room, post, radius=None):
        """Can this unit actually stand there, and get there on foot?

        Both beat-producing branches need the same guarantee, so it
        lives in one place. The other beat-producer in the codebase --
        `spawn_civilian`'s haunt sampler -- already applies exactly
        these filters, and `@patrol` applied none of them (#2566):

        * a Room, not any object `search` happened to match. The local
          in the `/beat` loop was even NAMED `room`; nothing enforced
          it, so `@patrol/beat <bot> = Petra` wrote a CHARACTER into
          `db.patrol_beat` and the pathfinder -- whose graph holds only
          rooms -- could never match it.
        * not a sky room. Those are all keyed "In the Air" by house
          convention, so a radius sample around any elevated post can
          pull one in, and no pedestrian belongs in the jump/fall
          transit volume.
        * reachable ON FOOT, WITH THIS UNIT AS THE TRAVERSER. Asking
          lock-blind answers a different question from the walk:
          `travel_to` calls `find_path_exits(..., traverser=npc)`, and
          a locked private apartment that counts as reachable without
          one gets sampled into the beat and then faults forever. That
          cost one tobacconist 273 failed attempts at the same door
          (#2711, #2714).

        Quiet: returns a reason rather than messaging, so `/auto` can
        filter a sample without narrating every rejection.
        """
        from world.spatial import is_reachable
        if not room.is_typeclass("typeclasses.rooms.Room", exact=False):
            return f"{room.get_display_name(self.caller)} isn't a room."
        if getattr(room.db, "is_sky_room", False):
            return (f"{room.get_display_name(self.caller)} is open air — "
                    f"a patrol can't stand there.")
        steps = (radius or 8) * 4
        if not is_reachable(post, room, traverser=npc, max_steps=steps):
            return (f"{room.get_display_name(self.caller)} isn't walkable "
                    f"from the post.")
        return None

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

        if "dispatch" in switches:
            from world.director.population import set_dispatch_room
            if caller.location is None:
                caller.msg("You have no location to designate.")
                return
            set_dispatch_room(caller.location)
            ensure_heartbeat()
            caller.msg(
                f"{caller.location.get_display_name(caller)} is now the "
                f"dispatch room: the console and the operator live here "
                f"(the heartbeat installs them if missing); respawns stay "
                f"at the security base. Move existing hardware and staff "
                f"yourself if you want THEM rather than fresh ones.")
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
            # Cleared, not zeroed: `next_waypoint` derives the starting
            # phase from identity, and writing 0 here pinned every unit
            # given a beat in one builder session to the same stop (#2431).
            if hasattr(npc.ndb, "patrol_idx"):
                del npc.ndb.patrol_idx
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
                # Coordinate distance alone offers rooms no pedestrian
                # belongs in. The civilian haunt sampler filters; this
                # sampled raw (#2566).
                nearby = [r for r in nearby
                          if not self._walkable_waypoint(npc, r, post,
                                                         radius)]
                if not nearby:
                    caller.msg("No WALKABLE rooms within that radius — "
                               "everything nearby is open air or has no "
                               "route on foot from the post.")
                    return
                beat = sample(nearby, min(4, len(nearby)))
            else:
                beat = []
                for token in rest.split(","):
                    room = caller.search(token.strip(), global_search=True)
                    if not room:
                        return  # search already messaged
                    # `global_search` with no typeclass filter matched
                    # anything at all — the NPC argument is type-checked
                    # a few lines up and the waypoints were not (#2566).
                    problem = self._walkable_waypoint(npc, room, post)
                    if problem:
                        caller.msg(problem + " Beat not set.")
                        return
                    beat.append(room)
                if not beat:
                    caller.msg("No rooms given.")
                    return
            npc.db.patrol_beat = beat
            if hasattr(npc.ndb, "patrol_idx"):
                del npc.ndb.patrol_idx      # let identity pick the phase

            ensure_heartbeat()
            caller.msg(
                f"{npc.get_display_name(caller)} now walks: "
                + ", ".join(r.get_display_name(caller) for r in beat)
                + f" (base first, every loop; ~{HEARTBEAT_SECONDS}s a leg).")
            return

        # A switch was typed and none of it survived validation. Do NOT
        # continue into the bare form below — that re-posts the NPC to
        # this room, which is not remotely what a mistyped `/status`
        # was asking for (#2565).
        if getattr(self, "typed_a_switch", False) and not switches:
            caller.msg(
                "Unrecognised switch. @patrol takes: "
                + ", ".join(f"/{opt}" for opt in self.switch_options)
                + ". Bare `@patrol <npc>` posts them where you stand.")
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
