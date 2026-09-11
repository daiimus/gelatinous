# Workflow — specs, roadmaps and issues

How work is classified and tracked. Code conventions live in
[`DEVELOPMENT_GUIDE.md`](DEVELOPMENT_GUIDE.md); this document is about the
layer above the code.

## The three documents, and what each is allowed to say

| artifact | answers | authority |
|---|---|---|
| **spec** (`specs/*.md`) | *What should this system do?* | design intent |
| **roadmap** (`specs/roadmaps/*.md`) | *In what order, and what is built?* | sequencing + phase status |
| **issue** (GitHub) | *What is the next concrete unit of work?* | execution state |

The rule that keeps them honest: **a spec never claims a phase is built.**
Only a roadmap says built-or-not, and only an issue says in-progress. When a
spec describes unbuilt behaviour it must say so inline — `📋 UNBUILT`, with a
pointer to the issue.

`specs/roadmaps/MEDICAL_SUBSTRATE_ROADMAP.md` is the reference implementation
of the roadmap pattern: a phase list, a status key, a separate readiness
ledger mapping unconsumed flags to the substrate that will consume them, and
an explicit sequencing rule ("build the substrate before wiring schema to
it"). New roadmaps should copy its shape.

## Issue labels — three axes, always all three

Every open issue carries exactly one label from each axis. If you cannot
pick a type, the issue is not yet understood well enough to file.

### `type:` — what kind of work is this

| label | means |
|---|---|
| `type: defect` | Behaviour contradicts spec, docs, or itself. There is a right answer. |
| `type: enhancement` | New capability, or an improvement to behaviour that is not wrong today. |
| `type: design` | A real choice with no single right answer. Needs a ruling, not a fix. |
| `type: question` | Cannot be scoped until someone answers something. |
| `type: debt` | Dead flags, stale docs, duplication. No behaviour change. |

The distinction that matters most is **defect vs design**. A defect can be
fixed by anyone who reads the spec. A design item cannot be fixed at all
until it is decided — filing one as a defect invites someone to "fix" it by
guessing, and guessing against an undecided question is how specs drift.

### `area:` — which subsystem

`combat` · `medical` · `souls` · `identity` · `world` · `economy` · `items` ·
`platform` · `docs`

One per issue. If something genuinely spans two, pick the one whose code
would change.

### `status:` — why isn't this moving

| label | means |
|---|---|
| `status: needs-decision` | Waiting on an owner call. The code cannot answer it. |
| `status: parked` | **Decided**, deliberately deferred. Not awaiting input. |
| `status: blocked` | Waiting on another issue or an unbuilt substrate. |

`parked` and `needs-decision` are the pair worth keeping honest. An issue the
owner has already decided to defer is *not* homework, and filing it as
"needs-decision" is what turns a backlog into a wall. When a decision is
made, the issue moves to `parked` or loses its status label entirely — it
does not stay in `needs-decision` because it is still open.

## Anti-drift: the one rule that would have caught the last three

**Every roadmap phase gets exactly one issue, and the phase status and the
issue state must agree.**

A phase cannot read "Not started" while its issue is closed. A phase cannot
read "Complete" with its issue open. This is the check that failed in
September 2026, when `MEDICAL_SUBSTRATE_ROADMAP` simultaneously:

- recorded kidney fatality as `DRIFT` / "substrate gap" **after**
  `RenalFailureCondition` had shipped and been wired, and
- recorded brain-destruction-is-unconsciousness as settled design **after**
  the owner had ruled otherwise.

Stale in both directions at once, in a document that was actively being
worked in. Nothing linked the phases to anything that would have noticed.

Corollary: **when a ruling supersedes something a doc records as intentional,
annotate rather than delete.** The superseded note usually still contains the
reasoning that made it right at the time, and deleting it invites the next
audit to re-file the decision as a bug. See the Phase 1 note in that
roadmap's Category A for the worked example.

## Provenance in issues

State how a finding was reached, because it determines how much to trust it:

- **Observed in play** — driven through the real command path in the running game.
- **Read from source** — traced by reading; no runtime confirmation.
- **Inferred** — reasoning from either of the above, not itself verified.

An issue that does not distinguish these will eventually be acted on as
though its weakest claim were its strongest. Where a measurement came from a
probe that manipulated state directly, say so — those have been wrong often
enough to warrant the caveat.
