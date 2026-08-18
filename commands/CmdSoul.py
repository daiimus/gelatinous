"""@soul — the souls-engine diagnostic (NPC_NEEDS_AND_GOALS_SPEC §8).

Ships WITH phase 1 by spec mandate: a soul you cannot inspect is a soul
you cannot debug. Shows the machine's actual state — need meters, the
goal the tree picked, the job step in flight, and the fault log.
"""

import time

from evennia import Command

from world.souls import engine, economy
from world.souls import needs as needs_mod


def _bar(value, width=10):
    filled = int(round(max(0.0, min(1.0, value)) * width))
    return "|g" + "=" * filled + "|n" + "." * (width - filled)


class CmdSoul(Command):
    """
    Inspect the souls engine.

    Usage:
        @soul <npc>     - full diagnostic for one soul
        @soul/all       - one-line summary of every soul + treasury

    Shows need pressures, the arbitrated goal, the running job and its
    current step, wage state, LOD tier, and recent faults.
    """

    key = "@soul"
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip().lstrip("/")
        if not args or args.lower() == "all":
            souls = engine.get_souls()
            if not souls:
                caller.msg("No ensouled NPCs.")
                return
            lines = ["|wSouls|n (treasury: "
                     f"|y{economy.balance()}|n tokens)"]
            for soul in souls:
                job = soul.db.soul_job or {}
                goal = job.get("goal", "idle")
                lod = soul.ndb.soul_lod or "?"
                where = soul.location.key if soul.location else "nowhere"
                hunger = needs_mod.pressure(soul, "hunger")
                rest = needs_mod.pressure(soul, "rest")
                faults = len(soul.db.soul_faults or [])
                lines.append(
                    f"  {soul.key:<18} {goal:<8} lod:{lod:<5} "
                    f"hun:{hunger:.2f} rest:{rest:.2f} "
                    f"tok:{soul.tokens or 0:<5} "
                    f"faults:{faults}  @ {where}")
            caller.msg("\n".join(lines))
            return

        target = caller.search(args, global_search=True)
        if not target:
            return
        if not target.tags.get(engine.SOUL_TAG[0],
                               category=engine.SOUL_TAG[1]):
            caller.msg(f"{target.key} has no soul.")
            return

        needs = target.db.soul_needs or {}
        job = target.db.soul_job
        sched = target.db.soul_schedule or "day"
        home = target.db.soul_home
        post = target.db.soul_post
        venue = target.db.soul_venue
        lines = [
            f"|wSoul: {target.key}|n (#{target.id})  "
            f"role:{target.db.soul_role or '?'}  schedule:{sched}  "
            f"lod:{target.ndb.soul_lod or '?'}",
            f"  home: {home.key if home else '-'}   "
            f"post: {post.key if post else '-'}   "
            f"till: {venue.key if venue else 'treasury'}",
            f"  tokens: |y{target.tokens or 0}|n   "
            f"wage owed: {float(target.db.soul_wage_owed or 0):.2f} "
            f"@ {float(target.db.soul_wage_rate or 0):.2f}/beat",
            "|wNeeds|n (soft {:.2f} / critical {:.2f})".format(
                needs_mod.SOFT, needs_mod.CRITICAL),
        ]
        for name in needs_mod.DECAY_PER_MIN:
            val = needs.get(name, 0.0)
            flag = ("|rCRIT|n" if val >= needs_mod.CRITICAL
                    else "|ysoft|n" if val >= needs_mod.SOFT else "")
            lines.append(f"  {name:<8}{_bar(val)} {val:.2f} {flag}")
        if job:
            steps = job.get("steps") or []
            at = job.get("at", 0)
            step = steps[at] if at < len(steps) else None
            lines.append(
                f"|wJob|n goal:{job.get('goal')}  step {at + 1}/"
                f"{len(steps)}: {step.get('do') if step else 'done'}")
        else:
            lines.append("|wJob|n none (idle)")
        faults = target.db.soul_faults or []
        if faults:
            lines.append("|wFaults|n")
            now = time.time()
            for stamp, msg in faults:
                ago = int((now - stamp) / 60)
                lines.append(f"  {ago:>4}m ago  {msg}")
        caller.msg("\n".join(lines))
