"""The rental terminal (cube-hotel housing guarantee).

    rent            - your registration status + vacancies here
    rent claim      - claim a cube (or confirm a relocation)

Everyone carries ONE rental credit — one permanent residence. Claiming
somewhere new releases your old cube with a relocation window: the old
door answers your sleeve for a while yet, then seals for good.
"""

from evennia import Command

from world.rental import (
    RELOCATION_WINDOW, assign_cube, is_free, residence_of)


def find_terminal(caller):
    location = caller.location
    if location is None:
        return None
    for obj in location.contents:
        if getattr(getattr(obj, "db", None), "rental_terminal",
                   None) is True:
            return obj
    caller.msg("There's no rental terminal here.")
    return None


class CmdRent(Command):
    """
    Register a cube at a rental terminal.

    Usage:
        rent            - your status and this hotel's vacancies
        rent claim      - claim a cube here (relocating releases your
                          old one after a handover window)

    One rental credit per person: one permanent residence, guaranteed.
    """

    key = "rent"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        terminal = find_terminal(caller)
        if terminal is None:
            return
        arg = (self.args or "").strip().lower()
        cubes = [c for c in (terminal.db.cubes or [])
                 if c is not None and getattr(c, "pk", None)]
        vacancies = sum(1 for c in cubes if is_free(c))

        if arg in ("claim", "confirm", "here"):
            current = residence_of(caller)
            if current is not None and current not in cubes \
                    and arg != "confirm":
                # relocation is a real decision — make it explicit once
                hours = int(RELOCATION_WINDOW // 3600)
                caller.msg(
                    f"You're registered at {current.key}. Claiming "
                    f"here relocates you — the old door answers your "
                    f"sleeve for {hours} more hours, then seals. "
                    f"Type |wrent confirm|n to proceed.")
                return
            ok, msg = assign_cube(caller, terminal)
            caller.msg(msg)
            if ok and caller.location:
                caller.location.msg_contents(
                    "The rental terminal chirps its registration jingle.",
                    exclude=[caller])
            return

        # bare: status
        current = residence_of(caller)
        home = (f"Registered residence: |w{current.key}|n."
                if current else
                "No registered residence — your housing credit is unspent.")
        caller.msg(f"{home}\nVacant cubes here: {vacancies} of "
                   f"{len(cubes)}. |wrent claim|n to register.")
