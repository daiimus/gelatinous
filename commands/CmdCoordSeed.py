"""``@coordseed`` — assign (x, y, z) coordinates to the world by walking
cardinal exits outward from the PINNED origin room.

Phase 1 of the spatial coordinate substrate
(``specs/proposals/SPATIAL_COORDINATE_SYSTEM_SPEC.md``). Authoritative:
geometry contradictions (a direction that doesn't reverse) are reported,
not silently resolved — fix the exit, tag it ``warp`` to exclude it, or
tag it ``slope_down``/``slope_up`` if it's honest split-level geometry.

The origin is PINNED (2026-07-12): seeding always anchors at the one
tagged origin room, never at wherever the builder happens to stand —
re-framing every coordinate in the colony by running the command from
the wrong bar was the grid's worst footgun.
"""

from evennia import default_cmds
from evennia.utils.search import search_tag

from world.spatial import (
    clear_xyz,
    seed_coordinates,
    set_xyz,
)
from world.spatial.coordinates import all_coordinate_rooms, get_xyz

#: The tag pinning the world's canonical (0, 0, 0) room.
ORIGIN_TAG = "coordseed_origin"
ORIGIN_TAG_CATEGORY = "spatial"


def pinned_origin():
    """The one pinned origin room, or None."""
    rooms = search_tag(ORIGIN_TAG, category=ORIGIN_TAG_CATEGORY)
    return rooms[0] if rooms else None


def plan_diff(assignments):
    """What the walk would CHANGE, and what it would land on top of.

    `seed_coordinates` reports CONTRADICTIONS -- the same walk reaching
    one room two ways with different results. It never compares its
    answer against what is on disk, so `/check` could print a clean
    report while the run underneath it moved rooms and stacked them
    (#2755).

    That gap is not academic. Against the world as it stands the walk
    relocates 27 rooms and 18 of them land on a cell another room
    already holds -- and two rooms sharing a cell means `distance()` 0
    and `bearing()` "here" between places that are not the same place,
    so signal range, dispatch facing and anything else keyed on
    proximity silently read them as co-located.

    The walk is not wrong; it is one of three writers of `db.xyz`
    (itself, `@coordset`, and ~40 build scripts placing vertical
    geometry by hand), and it is the only one that thinks it is alone.
    Deciding who OWNS the attribute is an owner call and is not made
    here -- this only makes the effect visible before it happens.

    Returns ``(moved, collisions)``:
      moved      [(room, current, target)] -- would change coordinate
      collisions [(room, current, target, holders)] -- target cell is
                 already held by somebody else
    """
    moved = []
    for room, coord in assignments.items():
        current = get_xyz(room)
        if current is not None and tuple(current) != tuple(coord):
            moved.append((room, tuple(current), tuple(coord)))

    occupied = {}
    for room in all_coordinate_rooms():
        cell = get_xyz(room)
        if cell is not None:
            occupied.setdefault(tuple(cell), []).append(room)

    collisions = []
    for room, current, target in moved:
        holders = [r for r in occupied.get(target, []) if r is not room]
        if holders:
            collisions.append((room, current, target, holders))
    return moved, collisions


def moving_rooms(rooms):
    """Those of *rooms* whose coordinate is legitimately transient.

    An elevator car and the crane container REWRITE their own `xyz` as
    they travel, so their coordinate is only true at the instant it is
    read. Seeding one is not drift being corrected -- it is a fixed
    answer being stamped onto something that moves, and the next trip
    overwrites it. Worth naming in a report rather than silently
    counted among ordinary rooms.
    """
    out = []
    for room in rooms:
        path = (getattr(room, "typeclass_path", "") or "").lower()
        if "elevator" in path or "crane" in path:
            out.append(room)
    return out


class CmdCoordSeed(default_cmds.MuxCommand):
    """
    Seed the world with (x, y, z) coordinates.

    Usage:
        @coordseed             - seed from the PINNED origin room (0,0,0)
        @coordseed/check       - dry run: report what would happen, write nothing
        @coordseed/origin      - pin YOUR CURRENT ROOM as the canonical origin
        @coordseed/clear       - preview what clearing would destroy
        @coordseed/clear/confirm  - actually clear (irreversible for rooms
                                    the seed walk cannot reach)

    Switches are matched case-insensitively, and an UNRECOGNISED switch
    aborts rather than being ignored (#2573). That matters here because
    `/check` is a safety and the default is the write: a typo used to
    mean "no dry run", so `@coordseed/Check` seeded 1,069 live rooms and
    reported "Seeded".

    Walks cardinal exits (north/south/east/west, the diagonals, up/down)
    breadth-first from the pinned origin, assigning one coordinate unit
    per step (+X east, +Y north, +Z up). It does not matter where you
    stand — the origin is pinned so the frame can never shift. Non-
    cardinal exits (enter, climb, out) and ``warp``-tagged exits are
    skipped; ``slope_down``/``slope_up``-tagged exits apply their extra
    z-step (split-level geometry, e.g. sunken berths).

    Contradictions — a room reached two ways with different coordinates —
    are a geometry bug in the build (a "north" that doesn't come back
    "south"). They are listed for you to fix; coordinates are never
    averaged. Tags: ``@tag <exit> = warp:exit_type`` (non-Euclidean,
    excluded) or ``@tag <exit> = slope_down:exit_type`` (honest slope,
    derived).
    """

    key = "@coordseed"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"
    switch_options = ("check", "origin", "clear", "confirm", "force")

    def func(self):
        caller = self.caller

        # Lower-cased, because Evennia PRESERVES switch case and
        # `switch_options` compares the raw token — `/Check` matched
        # nothing (#2573).
        switches = [str(sw).lower() for sw in (self.switches or [])]

        # And an unknown switch ABORTS rather than being ignored.
        # Evennia's own handling only prints "Extra switch ignored" and
        # carries on, which is the wrong polarity for a command whose
        # safety flag is opt-in and whose default is a 1,069-room write:
        # a typo would remove the guard rather than lose a feature.
        unknown = [sw for sw in switches if sw not in self.switch_options]
        if unknown:
            caller.msg(
                f"|rUnrecognised switch(es):|n /{', /'.join(unknown)}. "
                f"Nothing was changed. Valid: "
                f"/{', /'.join(self.switch_options)}."
            )
            return

        if "clear" in switches:
            rooms = all_coordinate_rooms()
            # What the seed walk could put back, so the preview can say
            # what is genuinely one-way (#2577). Coordinates come from
            # three writers — the walk, direct stamping (`@airfill`,
            # build scripts) and runtime movers (the elevator and crane
            # cars) — and only the first is reproducible.
            origin = pinned_origin()
            recoverable = set()
            if origin is not None:
                try:
                    assignments, _contra = seed_coordinates(origin)
                    recoverable = set(assignments)
                except Exception:  # noqa: BLE001 — a preview never breaks
                    recoverable = set()
            orphans = [r for r in rooms if r not in recoverable]

            if "confirm" not in switches:
                caller.msg(
                    f"|y@coordseed/clear would strip coordinates from "
                    f"{len(rooms)} room(s).|n\n"
                    f"  the seed walk could restore: {len(recoverable)}\n"
                    f"  |rone-way, nothing can restore: {len(orphans)}|n\n"
                    f"Rooms reached only by non-cardinal exits (in, out, "
                    f"elevator) or by no exit at all are never visited by "
                    f"the walk, and rooms stamped directly by @airfill or "
                    f"a build script are not either.\n"
                    f"Run |w@coordseed/clear/confirm|n to do it anyway."
                )
                return

            for room in rooms:
                clear_xyz(room)
            caller.msg(
                f"Cleared coordinates from {len(rooms)} room(s) — "
                f"{len(orphans)} of them unrecoverable by the seed walk."
            )
            return

        if "origin" in switches:
            here = caller.location
            if here is None:
                caller.msg("You have no location to pin.")
                return
            old = pinned_origin()
            if old is not None and old != here:
                old.tags.remove(ORIGIN_TAG, category=ORIGIN_TAG_CATEGORY)
            here.tags.add(ORIGIN_TAG, category=ORIGIN_TAG_CATEGORY)
            moved = (f" (moved from {old.get_display_name(caller)})"
                     if old is not None and old != here else "")
            caller.msg(f"|gOrigin pinned:|n {here.get_display_name(caller)} "
                       f"is now (0, 0, 0){moved}.")
            return

        origin = pinned_origin()
        if origin is None:
            caller.msg("|rNo origin is pinned.|n Stand in the world's "
                       "(0, 0, 0) room and run |w@coordseed/origin|n first "
                       "— seeding from an arbitrary room would re-frame "
                       "every coordinate in the colony.")
            return

        assignments, contradictions = seed_coordinates(origin)
        dry = "check" in switches

        # WHAT IT WOULD CHANGE, not just what it computed. The walk's
        # own contradiction list only describes its internal
        # consistency; it never looks at what is on disk, so a run that
        # moves rooms onto each other previews as clean (#2755).
        moved, collisions = plan_diff(assignments)
        movers = moving_rooms(list(assignments))

        if collisions and not dry and "force" not in switches:
            caller.msg(
                f"|rRefusing to seed: {len(collisions)} room(s) would land "
                f"on a cell another room already holds.|n\n"
                f"Two rooms in one cell read as distance 0 and bearing "
                f"'here' to every proximity check in the game.\n"
                f"Run |w@coordseed/check|n to see them, or "
                f"|w@coordseed/force|n to do it anyway."
            )
            return

        if not dry:
            for room, coord in assignments.items():
                set_xyz(room, *coord)

        verb = "Would seed" if dry else "Seeded"
        caller.msg(
            f"|g{verb} {len(assignments)} room(s)|n from the pinned origin "
            f"{origin.get_display_name(caller)} (0, 0, 0)."
        )

        if moved:
            caller.msg(
                f"|y{len(moved)} room(s) would change coordinate|n"
                if dry else
                f"|y{len(moved)} room(s) changed coordinate|n"
            )
            for room, current, target in moved[:12]:
                caller.msg(f"   {room.get_display_name(caller)} "
                           f"{current} -> {target}")
            if len(moved) > 12:
                caller.msg(f"   ...and {len(moved) - 12} more")

        if collisions:
            caller.msg(
                f"|r{len(collisions)} of those land on an OCCUPIED cell|n "
                f"— two rooms in one cell read as distance 0 and bearing "
                f"'here' to every proximity check."
            )
            for room, _current, target, holders in collisions[:12]:
                held = ", ".join(h.get_display_name(caller) for h in holders)
                caller.msg(f"   {room.get_display_name(caller)} -> {target} "
                           f"(held by {held})")
            if len(collisions) > 12:
                caller.msg(f"   ...and {len(collisions) - 12} more")

        if movers:
            caller.msg(
                f"|y{len(movers)} moving room(s) are in the walk|n — an "
                f"elevator car or crane container rewrites its own "
                f"coordinate as it travels, so seeding one stamps a fixed "
                f"answer onto something that moves: "
                + ", ".join(m.get_display_name(caller) for m in movers[:6])
            )

        if contradictions:
            caller.msg(
                f"|r{len(contradictions)} geometry contradiction(s) "
                f"— each is a build bug to fix (or tag warp/slope):|n"
            )
            for c in contradictions[:40]:
                caller.msg(
                    f"  {c['from_room'].get_display_name(caller)} "
                    f"--{c['direction']}--> "
                    f"{c['dest'].get_display_name(caller)}: already at "
                    f"{c['existing']}, this path expects {c['expected']}."
                )
            if len(contradictions) > 40:
                caller.msg(f"  ... and {len(contradictions) - 40} more.")
        else:
            caller.msg("|gNo geometry contradictions — clean.|n")

        if dry:
            caller.msg("|y(dry run — nothing was written)|n")
