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
    RELOCATION_WINDOW, assign_cube, is_free, residence_of)


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
        if arg in ("rent", "claim", "here", "confirm"):
            self._press_rent(presser, confirm=(arg == "confirm"))
            return True
        if not arg or arg in ("status", "info"):
            self._press_status(presser)
            return True
        return False    # not one of this machine's buttons

    def _cubes(self):
        return [c for c in (self.db.cubes or [])
                if c is not None and getattr(c, "pk", None)]

    def _press_status(self, presser):
        cubes = self._cubes()
        vacancies = sum(1 for c in cubes if is_free(c))
        current = residence_of(presser)
        home = (f"Registered residence: |w{current.key}|n."
                if current else
                "No registered residence — your housing credit is unspent.")
        presser.msg(
            f"The screen wakes under your touch.\n{home}\n"
            f"Vacant cubes here: {vacancies} of {len(cubes)}. "
            f"|wpress rent on kiosk|n to register.")

    def _press_rent(self, presser, confirm=False):
        current = residence_of(presser)
        cubes = self._cubes()
        if current is not None and current not in cubes and not confirm:
            hours = int(RELOCATION_WINDOW // 3600)
            presser.msg(
                f"You're registered at {current.key}. Claiming here "
                f"relocates you — the old door answers your sleeve for "
                f"{hours} more hours, then seals. "
                f"|wpress confirm on kiosk|n to proceed.")
            return
        ok, msg = assign_cube(presser, self)
        presser.msg(msg)
        if ok and presser.location:
            presser.location.msg_contents(
                "The rental terminal chirps its registration jingle.",
                exclude=[presser])
