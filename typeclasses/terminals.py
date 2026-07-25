"""Terminals — pressable machines (the decking substrate's physical layer).

A terminal is a fixed machine you operate through the ordinary
``press``/``push`` command: ``press rent on kiosk``, ``press <button>``.
Buttons route through ``at_press(presser, arg)`` — the same contract
elevator panels and call buttons use — so every machine in the colony
shares one interaction grammar. When decking lands, these are the
boxes whose records become files: the interface stays the buttons,
the truth moves to the net.

First citizen: the RENTAL TERMINAL (housing guarantee, spec §2.5).
"""

from typeclasses.items import Item
from world.rental import (
    RELOCATION_WINDOW, assign_cube, is_free, residence_of, unit_matches)


class RentalTerminal(Item):
    """The housing-guarantee kiosk. ``press rent`` claims a cube;
    ``press confirm`` completes a relocation; a bare ``press kiosk``
    reads your registration status."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.pressable = True
        self.db.rental_terminal = True
        self.locks.add("get:false()")
        self.db.get_err_msg = "It is bolted down and knows it."
        if "kiosk" not in self.aliases.all():
            self.aliases.add("kiosk")

    # -- press grammar ---------------------------------------------------
    def at_press(self, presser, arg=None):
        arg = (arg or "").strip().lower()
        parts = arg.split(None, 1)
        verb = parts[0] if parts else ""
        unit = parts[1].strip() if len(parts) > 1 else None
        if verb in ("rent", "claim", "here", "confirm"):
            self._press_rent(presser, unit=unit,
                             confirm=(verb == "confirm"))
            return True
        if not arg or arg in ("status", "info"):
            self._press_status(presser)
            return True
        return False    # not one of this machine's buttons

    def _cubes(self):
        return [c for c in (self.db.cubes or [])
                if c is not None and getattr(c, "pk", None)]

    @staticmethod
    def _unit_short(cube):
        """The board name: "The Brackett Arms - Unit 3B" -> "3B"."""
        tail = cube.key.split(" - ")[-1]
        return tail[5:] if tail.lower().startswith("unit ") else tail

    def _press_status(self, presser):
        cubes = self._cubes()
        free = [self._unit_short(c) for c in cubes if is_free(c)]
        current = residence_of(presser)
        home = (f"Registered residence: |w{current.key}|n."
                if current else
                "No registered residence — your housing credit is unspent.")
        board = (" Vacant: " + ", ".join(free) + ".") if free else ""
        presser.msg(
            f"The screen wakes under your touch.\n{home}\n"
            f"Vacancies here: {len(free)} of {len(cubes)}.{board}\n"
            f"|wpress rent on kiosk|n to register, or "
            f"|wpress rent <unit> on kiosk|n to choose.")

    def _press_rent(self, presser, unit=None, confirm=False):
        current = residence_of(presser)
        cubes = self._cubes()
        # any claim that would change an existing registration wants an
        # explicit confirm — cross-building, or naming a different unit
        # on this very board (in-building moves are real relocations)
        relocating = current is not None and not (
            (unit and unit_matches(current, unit))
            or (not unit and current in cubes))
        if relocating and not confirm:
            hours = int(RELOCATION_WINDOW // 3600)
            which = f" {unit}" if unit else ""
            presser.msg(
                f"You're registered at {current.key}. Claiming here "
                f"relocates you — the old door answers your sleeve for "
                f"{hours} more hours, then seals. "
                f"|wpress confirm{which} on kiosk|n to proceed.")
            return
        ok, msg = assign_cube(presser, self, unit=unit)
        presser.msg(msg)
        if ok and presser.location:
            presser.location.msg_contents(
                "The rental terminal chirps its registration jingle.",
                exclude=[presser])


class RepeaterBreaker(Item):
    """A repeater's power isolator — the head-end cabinet, floors away
    from the mast it feeds. ``press breaker`` toggles the linked
    repeater's power: district infrastructure you can reach with a
    boot instead of a ladder (tampering stays in players' sphere; the
    mast up top is the violent seam)."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.pressable = True
        self.locks.add("get:false()")
        self.db.get_err_msg = "It is conduit-fed and bolted to the wall."
        if "breaker" not in self.aliases.all():
            self.aliases.add("breaker")

    def at_press(self, presser, arg=None):
        mast = self.db.linked_repeater
        if mast is None or not getattr(mast, "pk", None):
            presser.msg("The breaker throws with a dead clack — nothing "
                        "answers on the other end of the conduit.")
            return True
        going_on = getattr(mast.db, "radio_on", False) is not True
        mast.db.radio_on = going_on
        if going_on:
            presser.msg("You haul the breaker closed. The conduit "
                        "overhead picks up a live hum.")
            room_line = "The head-end breaker slams closed; the conduit hums."
            mast_line = ("The repeater mast's cabinet clicks, and its "
                         "patient hum resumes.")
        else:
            presser.msg("You haul the breaker open. Somewhere far "
                        "overhead, a hum you'd stopped hearing spins down.")
            room_line = "The head-end breaker bangs open; the conduit goes dead."
            mast_line = ("The repeater mast's hum spins down; its status "
                         "lamp fades to nothing.")
        if presser.location:
            presser.location.msg_contents(room_line, exclude=[presser])
        mast_room = getattr(mast, "location", None)
        if mast_room is not None and mast_room != presser.location:
            mast_room.msg_contents(mast_line)
        return True
