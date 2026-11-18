# Security Unit Lifecycle — downed, recovered, repaired, junked

Security units are souls (`world/souls/*`). A unit lost in the field is
replaced from the alcoves. A unit that is downed is fetched home by
another unit and repaired at the mechanic's bench. A unit that dies on
the way home has its weapon arm removed and its chassis dumped in the
junkyard. The pieces: the assignment release (#2280), the recovery
errand (#2282), strip-and-junk (#2284), the harvest door that makes the
§3 race reachable (#2286), and repair at the bench (#2262).

**Depends on:** `world/director/population.py` (the respawn loop),
`world/souls/*` (Phase 2 — units are souls), the mechanic post.

---

## 1. Replacement, and the armed remains

A unit destroyed in the field is replaced. `maintain_security_complement`
(`world/director/population.py`) counts living posted units against the
base's complement and cycles one replacement out of a charging alcove per
tick — "at machine-logistics pace, not instantly".

**The remains are armed.** A unit's weapon is not carried — it is an
augment ORGAN (`factory_fit_armament`, same file, seats an integrated
shotgun module through the same backend as installed human chrome). This
game harvests organs and chrome. So a downed secbot is a working shotgun
lying in the street.

## 2. The intended lifecycle (owner, 2026-08-24)

    downed        → dragged back to the constabulary → repaired
    destroyed     → remains taken to the constabulary
                  → weapon arm removed
                  → disposed of in the junkyard

Two different outcomes off two different states, which the medical layer
already distinguishes: a unit that is *disabled* and one that is
*finished*.

**How it runs:** only the downed branch starts. A destroyed unit is
never picked up: `notice_casualty` → `recover_casualty`
(`world/director/medical.py`) is the only way a recovery starts, and
`find_casualty` skips the dead (#2757). The wreck stays where it fell,
with its arm still fitted. The destroyed branch of the `deliver` step
(`strip_and_junk`) runs only when a unit dies while it is being carried
home. So the §3 race over a dead unit's arm does not happen in play.

## 3. Why this is content, not housekeeping

Recovery makes stripping a dead unit a **race** rather than a freebie.
Reach it before the recovery detail and you have armed yourself off the
colony's own security force; arrive late and the arm is already back at
the precinct with the rest bound for the scrap.

That single fact gives the loop stakes in both directions — a reason to
fight over a wreck, and a reason for security to hurry.

It also closes an armament leak that Phase 2 made more likely, because
souled units patrol, charge, and wear out rather than standing still:
more units in the field is more units to lose.

## 4. The pieces

| piece | where |
|---|---|
| replacement from the alcoves | `maintain_security_complement` (`world/director/population.py`) |
| dragging a body | emergent from grapple + movement (no command, by design) |
| the junkyard | **The Midden — Middle Yard** (#7487), tagged by build 128 with `SCRAPYARD_TAG = ("scrapyard", "disposal")` (`world/director/disposal.py`). NOT Kaspar Pawn & Salvage, which is an indoor shop — "racked behind scuffed polycarb" is somewhere you sell a handset, not somewhere you dump a chassis |
| the weapon as a removable organ | `operate` does surgery on parts |
| recovery detail (who fetches it) | another unit — `hold → travel → deliver` (#2282) |
| repair | the bench, three mechanics, the machine kit (#2262); `operate` charts a chassis in its own words |
| strip-and-junk disposal | module off, chassis to the yard (`strip_and_junk`, #2284) |

The delivery bay and the yard are tag-driven (builds 127 and 128).

## 5. Recovery

**Recovery is a JOB, not a director callback.** Phase 2 put units in the
souls system precisely so that going somewhere and doing something is a
job with steps, faults, and interruptions, using the real verbs.

**Who starts it.** No unit is sent to a downed unit. Recovery starts
only when another unit thinks while standing in the same room
(`notice_casualty`, called from `think()` in `world/souls/engine.py`).
`recover_casualty` (`world/director/medical.py`) elects the errand:
unit-only, both ways, and band-arbitrated so a unit does not drop a call
for it.

**The steps.** `plan_for(soul, "recover")` (`world/souls/actions.py`)
builds `hold → travel → deliver`, run by `world/souls/jobs.py`:

- **hold** comes FIRST, because the wreck is where the noticing unit
  already is. It is its own step, not the mugger's `grapple` (see the
  trap below). It checks `is_grappled(handler, wreck)` with both
  arguments and re-issues the grab rather than assuming an unresisting
  body is already held.
- **travel** to the delivery bay. Dragging stays emergent — hold it, then
  walk — so there is no `drag` step and no drag command.
- **deliver**: a downed unit is left for the bench. A unit that died on
  the way goes through `strip_and_junk` (`world/director/disposal.py`):
  armament module off, chassis moved to the yard, not deleted.

**The trap the `hold` step avoids.** The `grapple` job step guards on
`can_contest(mark)`, which is *conscious and not restrained* — false for
a downed unit. So that step reads an unresisting body as ALREADY HELD
and advances without issuing the command. Reused for recovery, the
detail would walk home dragging nothing, successfully, with no fault
raised — a silent failure that would look like a pathing bug. That is
why recovery does not reuse it.

**Radio.** The recovering unit sends "Unit N down. Recovering." when it
takes the errand (`recover_casualty`). On delivery (the `deliver` step)
it sends either "Unit N recovered." or, for a unit that died on the way,
"recovered, not repairable" with whether the armament came off. That
part follows the `strip_and_junk` report, so a wreck that is still
armed is never radioed "Armament secured." (#2765).

**The window.** Because recovery starts only when a unit passes through
the room, the window is set by patrol traffic, not by a timer.

## 6. Repair

**Repair belongs to the mechanic.** Servicing a unit on shift and
rebuilding one that was dropped are the same person's work, and share a
bench. The bench advertises `maintenance` and `repair` only while
somebody is standing there: build 124 sets `advertises =
{"maintenance": 0.9}` with `advertise_staffed = True` (#2261), and build
125 adds `repair` alongside it for damage as opposed to scheduled wear.
The rule is in `world/souls/salience.py::_work_mechanic`: "a machine
cannot fix itself: `maintenance` advertises only at a STAFFED bench".

> Owner ruling 2026-08-23 had `maintenance` deliberately advertised
> NOWHERE, because the mechanic's post is where that work is done. The
> next day the staffed bench advertiser (#2261) replaced that; it keeps
> the ruling's point — this is the mechanic's work, not a wall fitting's.

**A repaired unit keeps its defects; a replacement does not.** A chassis
that goes to the junkyard takes its quirks with it, and a fresh one out
of the alcove starts clean (#2254). So repairing a paranoid secbot has
to actually treat the paranoia — otherwise destroying it remains the
cheaper cure, which is a funny incentive to leave lying around.

Each completed maintenance service at the staffed bench clears the
unit's newest defect, one per service (the dwell step in
`world/souls/jobs.py`, through `clear_defect` in `world/souls/traits.py`).
Nothing else clears a defect, so a damage repair clears none.

## 7. Death releases the assignment (#2280)

`release_on_death` settles a destroyed responder's call through
`close_call_for(assignment, "unit_lost", npc)`
and frees the soul. Without it the call would stay open in the ledger
with no outcome and the soul would hold its errand — and the recovery
loop would drag a chassis home, the mechanic would rebuild it, and it
would stand at the bench forever.

The destroyed unit does not transmit — a destroyed unit does not key a
mic, and its going silent mid-call is the signal. `unit_lost` has no
line in `_CALL_OUTCOME_LINES`.

An assigned soul is arbitrated, not silenced: an assignment is a band-0
`respond` job (#2384). The early exits left in `think()` are a pinned
soul and `_in_combat`.

## 8. Answered (owner, 2026-08-24)

* **Who fetches?** **Another unit — the force recovers its own.** A
  recovery job on a second unit: `travel → take hold → drag → deliver`.
  Quicker and colder than sending a mechanic, and it costs the force a
  patrol while it runs, so a downed unit visibly thins the streets.

  The steps as they run are `hold → travel → deliver` (§5).
* **Does a stripped chassis persist?** **Yes, in the junkyard.**
  Feedstock for the Ripper's cold room and for parts, and it lets
  Kaspar Salvage accumulate a visible history of the force's bad
  nights.

  > **Superseded in part, owner 2026-09-14:** robots go to a future
  > junkyard salvager, not the Ripper, and the Ripper refuses robots
  > (`GIG_RIPPER_SPEC` §2). The chassis still stays in the yard.

  The yard is The Midden — Middle Yard, not Kaspar's (§4).
  `strip_and_junk` moves the wreck rather than deleting it.
* **How long is the window?** **Minutes — genuinely losable.** Long
  enough that somebody who watched the fight can reach the wreck, take
  the arm and be gone. Recovery usually wins on quiet streets; a
  prepared thief usually wins. That is the stakes §3 asks for.

  The window is set by patrol traffic, not by a timer (§5).

## Not decided

- Whether recovery should pick up destroyed units: 📋 UNBUILT (not
  decided).
- Is a unit dragged home unconscious meant to be repaired at the bench?
  The mechanic racks only units with a high maintenance need.
- When a recovered unit dies while carried and its armament is not
  recovered, the unit radios "Requesting a second unit", but nothing sends
  one. Should that stay radio narration for whoever holds dispatch
  (perhaps reworded so it promises no unit), or should it start an errand
  that sends a unit to the wreck?

## Related

- `GIG_RIPPER_SPEC` §2 — the Ripper refuses robots.
