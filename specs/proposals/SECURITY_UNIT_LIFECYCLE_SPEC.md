# Security Unit Lifecycle — downed, recovered, repaired, junked

**Status:** ✅ **BUILT 2026-08-24.** Assignment leak (#2280), recovery
errand (#2282), strip-and-junk (#2284), and the harvest door that made
the §3 race reachable (#2286).
**Depends on:** `world/director/population.py` (the respawn loop),
`world/souls/*` (Phase 2 — units are souls), the mechanic post
**~~Blocks on:~~ UNBLOCKED 2026-08-24** — repair is real: the bench
advertises `repair`, three mechanics stand shifts with the machine kit,
and `operate` charts a chassis in its own words (#2262).

---

## 1. What happens today

A unit destroyed in the field is replaced. `maintain_security_complement`
counts living posted units against the base's complement and cycles one
replacement out of a charging alcove per tick — "at machine-logistics
pace, not instantly".

That is the whole lifecycle. Nothing recovers the casualty, nothing
repairs anything, and the remains stay where they fell.

**And the remains are armed.** A unit's weapon is not carried — it is an
augment ORGAN (`factory_fit_armament` seats an integrated shotgun module
through the same backend as installed human chrome). This game harvests
organs and chrome. So a downed secbot is a working shotgun lying in the
street, and nobody ever comes for it.

## 2. The intended lifecycle (owner, 2026-08-24)

    downed        → dragged back to the constabulary → repaired
    destroyed     → remains taken to the constabulary
                  → weapon arm removed
                  → disposed of in the junkyard

Two different outcomes off two different states, which the medical layer
already distinguishes: a unit that is *disabled* and one that is
*finished*.

## 3. Why this is content, not housekeeping

Recovery makes stripping a dead unit a **race** rather than a freebie.
Reach it before the recovery detail and you have armed yourself off the
colony's own security force; arrive late and the arm is already back at
the precinct with the rest bound for the scrap.

That single fact gives the loop stakes in both directions — a reason to
fight over a wreck, and a reason for security to hurry.

It also closes an armament leak that Phase 2 made more likely, because
souled units now patrol, charge, and wear out rather than standing
still: more units in the field is more units to lose.

## 4. Pieces, and what exists

| piece | state |
|---|---|
| replacement from the alcoves | ✅ built |
| dragging a body | ✅ emergent from grapple + movement (no command, by design) |
| the junkyard | ✅ **The Midden — Middle Yard**, tagged by build 128. NOT Kaspar Salvage, which is an indoor shop — "racked behind scuffed polycarb" is somewhere you sell a handset, not somewhere you dump a chassis |
| the weapon as a removable organ | ✅ built — `operate` already does surgery on parts |
| recovery detail (who fetches it) | ✅ another unit — `hold → travel → deliver` (#2282) |
| repair | ✅ the bench, three mechanics, the machine kit (#2262) |
| strip-and-junk disposal | ✅ module off, chassis to the yard (#2284) |

Most of the substrate is already here. What is missing is the *errand*:
somebody whose job is to go and get it.

## 5. Design notes

**Recovery is a JOB, not a director callback.** Phase 2 put units in the
souls system precisely so that going somewhere and doing something is a
job with steps, faults, and interruptions. A recovery detail is
`travel → grapple → drag → deliver`, which is the shape the souls layer
already runs, using the real verbs.

**Repair belongs to the mechanic**, whose post is the reason
`maintenance` is deliberately advertised NOWHERE (owner ruling,
2026-08-23). Servicing a unit on shift and rebuilding one that was
dropped are the same person's work, and should share a bench.

**A repaired unit keeps its defects; a replacement does not.** A chassis
that goes to the junkyard takes its quirks with it, and a fresh one out
of the alcove starts clean (#2254). So repairing a paranoid secbot has
to actually treat the paranoia — otherwise destroying it remains the
cheaper cure, which is a funny incentive to leave lying around.

## 6. Answered (owner, 2026-08-24)

* **Who fetches?** **Another unit — the force recovers its own.** A
  recovery job on a second unit: `travel → take hold → drag → deliver`.
  Quicker and colder than sending a mechanic, and it costs the force a
  patrol while it runs, so a downed unit visibly thins the streets.
* **Does a stripped chassis persist?** **Yes, in the junkyard.**
  Feedstock for the Ripper's cold room and for parts, and it lets
  Kaspar Salvage accumulate a visible history of the force's bad
  nights.
* **How long is the window?** **Minutes — genuinely losable.** Long
  enough that somebody who watched the fight can reach the wreck, take
  the arm and be gone. Recovery usually wins on quiet streets; a
  prepared thief usually wins. That is the stakes §3 asks for.

## 7. Closed: the assignment leak (#2280)

Found while comparing damaged-unit scenes. Nothing cleared an
assignment on death, so a destroyed responder kept its errand — the
call stayed open in the ledger with no outcome, and because
`think()` returns early for any assigned soul, **the unit's soul
stayed permanently asleep**. Even repaired, it would never think
again.

That would have quietly defeated this entire spec: the recovery loop
would have dragged a chassis home, the mechanic would have rebuilt it,
and it would have stood at the bench forever. `release_on_death` now
settles the call as `unit_lost` and frees the soul. The unit does not
transmit — a destroyed unit does not key a mic, and its going silent
mid-call is the signal.

## 8. Known trap for the recovery build

**The existing `grapple` job step cannot take hold of a wreck.** It
guards on `can_contest(mark)`, which is *conscious and not
restrained* — false for a downed unit. So the step reads an
unresisting body as ALREADY HELD, advances without issuing the
command, and the recovery detail would walk home dragging nothing,
successfully, with no fault raised.

Recovery therefore needs its own step that establishes a hold on a
body that cannot resist, rather than reusing the mugger's grapple.
Worth knowing before building: the failure is silent and would look
like a pathing bug.
