# Security Unit Lifecycle — downed, recovered, repaired, junked

**Status:** proposed 2026-08-24, NOT built (#2255)
**Depends on:** `world/director/population.py` (the respawn loop),
`world/souls/*` (Phase 2 — units are souls), the mechanic post
**Blocks on:** repair mechanics, which do not exist

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
| the junkyard | ✅ exists (Kaspar Salvage / the scrap yards) |
| the weapon as a removable organ | ✅ built — `operate` already does surgery on parts |
| recovery detail (who fetches it) | ✗ |
| repair | ✗ — and it is the mechanic's job |
| strip-and-junk disposal | ✗ |

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

## 6. Open questions

* **Who fetches?** Another unit (the force recovers its own), or the
  mechanic (a person with a trolley)? A unit is quicker and colder; the
  mechanic is better content and slower to arrive.
* **Does a stripped chassis stay in the junkyard as an object?** It is
  the obvious feedstock for the Ripper's cold room and for parts.
* **How long is the window?** The race only exists if recovery takes
  long enough to lose.
