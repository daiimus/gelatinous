"""@insure — a standing sleeve policy for staff and play testing (#3667).

Owner ruling 2026-09-25: "we should also have a way to make a character
perpetually insured. Usable for play testing, staff, etc." A standing
policy is the same record the lobby terminal files, flagged `perpetual`:
a return takes it like any other and then re-issues it in the new body's
name, so the holder never has to buy again. It bypasses the
players-in-the-loop rule on purpose, which is why the lock is Admin, the
same as the one other command that changes a player character's standing
(`@fixchar`).
"""
from evennia import default_cmds

from commands._identity_targeting import resolve_admin_target
from world import insurance
from world.combat.debug import get_splattercast


class CmdInsure(default_cmds.MuxCommand):
    """
    Give, take away or read a standing sleeve policy.

    Usage:
        @insure <character>          - a standing policy in that body's name
        @insure/revoke <character>   - take a standing policy away
        @insure/status <character>   - what is on file for that body

    A standing policy is never spent: a flash clone re-issues it in the
    new body's name. It replaces whatever the body's lineage had on file,
    and may be granted to a dead, archived body (that is how a playtester
    who died uninsured is brought back: grant, then respawn). Revoking
    leaves an ordinary purchase alone; that is the player's own.
    """

    key = "@insure"
    locks = "cmd:pperm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        switches = {sw.lower() for sw in self.switches}
        args = (self.args or "").strip()
        if not args or len(switches) > 1 or (switches - {"revoke", "status"}):
            caller.msg("Usage: @insure <character>, @insure/revoke <character>, "
                       "@insure/status <character>")
            return
        target = resolve_admin_target(caller, args)
        if target is None:
            caller.msg(f"|rCould not find '{args}'.|n")
            return

        if "status" in switches:
            caller.msg(f"{target.key}: {insurance.status_line(target)}")
            return
        if "revoke" in switches:
            ok, msg = insurance.revoke_perpetual(target)
        else:
            ok, msg = insurance.grant_perpetual(target, granted_by=caller)
        caller.msg(("|g" if ok else "|y") + msg + "|n")
        if ok:
            get_splattercast().msg(
                f"@insure: {msg} (by {caller.key}, body #{target.id})")
