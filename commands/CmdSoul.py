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
    Inspect the souls engine — one command, three depths.

    Usage:
        @soul           - the colony dashboard (population, employment,
                          economy, mood)
        @soul all       - one-line summary of every soul + treasury
        @soul <npc>     - full diagnostic for one soul

    The individual view shows need pressures, the arbitrated goal, the
    running job and its current step, wage state, mood and thoughts,
    LOD tier, and recent faults.
    """

    key = "@soul"
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def _colony_dashboard(self, caller):
        """Bare `@soul`: the colony at a glance — population, employment,
        economy, mood. One command, three depths (bare / all / <npc>)."""
        from collections import Counter

        from world.souls import economy, engine
        from world.souls import population as pop_mod
        from world.souls import thoughts as thoughts_mod
        from world.souls.posts import get_posts

        souls = [s for s in engine.get_souls() if s.pk]
        manned = opened = 0
        venue_lines = []
        till_total = 0
        for post in get_posts():
            slots = post.db.post_slots or {}
            m = [sh for sh, sl in slots.items()
                 if sl.get("keeper") and sl["keeper"].pk]
            o = [sh for sh in slots if sh not in m]
            manned += len(m)
            opened += len(o)
            if post.db.register is not None:
                till_total += int(post.db.register or 0)
            where = (post.location.key if post.location else post.key)
            venue_lines.append(f"  {where[:34]:<34} "
                               f"manned:{','.join(sorted(m)) or '-':<16} "
                               f"open:{','.join(sorted(o)) or '-'}")
        poverty = pop_mod.poverty_index(souls)
        moods = Counter(thoughts_mod.mood_band(thoughts_mod.mood(s))
                        for s in souls)
        lawless = sum(1 for s in souls if s.db.soul_lawless)
        lines = [
            f"|wThe Colony|n — {len(souls)} souls  "
            f"({lawless} lawless)  |wslots|n {manned} manned / "
            f"{opened} open",
            f"|wEconomy|n treasury:|y{economy.balance()}|n  "
            f"tills:|y{till_total}|n  "
            f"poverty:{poverty:.0%}"
            + ("  |r(the shuttle sends knives)|n" if poverty > 0.5
               else ""),
            f"|wMood|n " + "  ".join(
                f"{band}:{moods.get(band, 0)}"
                for band in ("bright", "level", "low", "grim")),
            "|wPosts|n",
        ] + venue_lines
        caller.msg("\n".join(lines))

    def func(self):
        caller = self.caller
        args = (self.args or "").strip().lstrip("/")
        if not args:
            self._colony_dashboard(caller)
            return
        if args.lower() == "all":
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
                derived = needs_mod.pressures(soul)
                hunger = derived["hunger"]
                rest = derived["rest"]
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

        needs = needs_mod.pressures(target)      # derived, zero-write read
        try:
            from world.gametime import colony_now
            from world.souls.engine import duty_pressure, soul_hour
            t = colony_now()
            needs["duty"] = duty_pressure(
                target, soul_hour(target, t.hour + t.minute / 60.0))
        except Exception:
            needs["duty"] = 0.0
        job = target.db.soul_job
        sched = target.db.soul_schedule or "day"
        home = target.db.soul_home
        post = target.db.soul_post
        venue = target.db.soul_venue
        from world.souls import thoughts as thoughts_mod
        from world.souls import traits as traits_mod
        mood_val = thoughts_mod.mood(target)
        trait_labels = traits_mod.labels(target)
        abhors, relishes = traits_mod.ethos(target)
        lines = [
            f"|wSoul: {target.key}|n (#{target.id})  "
            f"role:{target.db.soul_role or '?'}  "
            f"profile:{needs_mod.profile_name(target)}"
            f"{' |rlawless|n' if target.db.soul_lawless else ''}  "
            f"schedule:{sched}  "
            f"lod:{target.ndb.soul_lod or '?'}  "
            f"mood:|y{thoughts_mod.mood_band(mood_val)}|n ({mood_val:+.2f})",
            "  traits: " + (", ".join(f"|c{t}|n" for t in trait_labels)
                            or "none")
            + (f"   |rabhors|n {'/'.join(sorted(abhors))}" if abhors else "")
            + (f"   |grelishes|n {'/'.join(sorted(relishes))}"
               if relishes else ""),
            f"  home: {home.key if home else '-'}   "
            f"post: {post.key if post else '-'}   "
            f"till: {venue.key if venue else 'treasury'}",
            f"  tokens: |y{target.tokens or 0}|n   "
            f"wage owed: {float(target.db.soul_wage_owed or 0):.2f} "
            f"@ {float(target.db.soul_wage_rate or 0):.2f}/beat",
            "|wNeeds|n (soft {:.2f} / critical {:.2f})".format(
                needs_mod.SOFT, needs_mod.CRITICAL),
        ]
        for name, val in needs.items():
            flag = ("|rCRIT|n" if val >= needs_mod.CRITICAL
                    else "|ysoft|n" if val >= needs_mod.SOFT else "")
            lines.append(f"  {name:<12}{_bar(val)} {val:.2f} {flag}")
        felt = thoughts_mod.decayed(target)
        if felt:
            lines.append("|wThoughts|n (decayed)")
            for weighted, key, note, age in felt[-8:]:
                lines.append(f"  {weighted:+.2f} {key:<14} "
                             f"{int(age / 60):>4}m ago  {note}")
        cooldowns = {g: t for g, t in (target.db.soul_goal_cooldown or {}).items()
                     if t > time.time()}
        if cooldowns:
            lines.append("|wCooldowns|n " + "  ".join(
                f"{g}:{int(t - time.time())}s" for g, t in cooldowns.items()))
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
