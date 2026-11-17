# Workflow — specs, roadmaps and issues

How work is classified and tracked. Code conventions live in
[`DEVELOPMENT_GUIDE.md`](DEVELOPMENT_GUIDE.md); this document is about the
layer above the code.

## The three documents, and what each is allowed to say

| artifact | answers | holds |
|---|---|---|
| **spec** (`specs/*.md`) | *What does this system do, and what should it do?* | the rule as it stands now, the owner's rulings, what is unbuilt, what is undecided |
| **roadmap** (`specs/roadmaps/*.md`) | *What comes next, and in what order?* | the order of work not yet done |
| **issue** (GitHub) | *What is the next concrete unit of work?* | execution state |

**Who the documents are for.** The code here is written by a language model
working with the owner, and these documents are what that model reads before
it writes. Owner, 2026-11-17, asked how they should be shaped: "What is best
for you as the LLM? This is 100% vibe coded project." And to the answer set
out below: "I concur."

- **No document says what is built.** Whether something is built is checked
  in the code, which takes seconds and is never out of date. A "shipped"
  marker, a status banner or a phase table is useful only while it is right,
  and it is the first thing to go wrong: a stale one is acted on. Only an
  issue says what is in progress.
- **A spec says what cannot be read from the code**: what the system does
  and should do now, each ruling in the owner's words with its date, what is
  deliberately not built, and what is not decided. Unbuilt behaviour is
  marked where it stands, `📋 UNBUILT`, with its issue number when there is
  one.
- **A spec gives the current rule first, and briefly.** No change-log
  narrative ("it used to", "the first version") and no line numbers: name
  the function. The history is in git and on the issues. The one piece of
  history that stays is a short note where a ruling overturned an intention
  the document had recorded (see Anti-drift below).
- **A roadmap is short**: what comes next, and in what order. It is not a
  ledger of what was built.
- **`AGENTS.md`, `DEVELOPMENT_GUIDE.md` and this file stay tight.** They are
  read at the start of every piece of work.

Specs written before this still carry status markers, phase tables and
history. They are being brought to this shape (#3865). Until a spec has been,
trust the code over its status lines.

`specs/roadmaps/MEDICAL_SUBSTRATE_ROADMAP.md` is the model for a roadmap in
what it sequences: a phase list in order, a readiness ledger mapping
unconsumed flags to the substrate that will consume them, and an explicit
sequencing rule ("build the substrate before wiring schema to it"). Its
status key predates the rule above.

## Issue labels — three axes

Every open issue carries exactly one `type:` label and one `area:` label. A
`status:` label is added only while one of the three below applies, and
comes off when it no longer does. If you cannot pick a type, the issue is not
yet understood well enough to file.

A player's `bug` report arrives without them: the game files it itself
(`commands/CmdBug.py`) with the labels `bug` and `player-reported`, plus the
category the player picked (`combat`, `medical`, `movement`, `items`,
`commands`, `web`, `world`, `social`, `system` or `other`). Triage gives it
its `type:` and `area:` labels.

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

## Rulings — what the owner decides, and how

Two different things are asked of the owner:

- A **ruling** decides what the game should do. It is needed where there is a
  real choice about how the game behaves or what a player reads; that is what
  `type: design` marks. Where a spec or an earlier ruling already gives the
  answer there is nothing to rule on. That is the sense of "a defect can be
  fixed by anyone who reads the spec" above: nobody has to decide what the
  right answer is.
- A **go** is leave to start. Any change to how the game behaves waits for
  one, a defect fix included. A go given for a named list of work covers that
  list and nothing added to it later. It does not cover the reloads that work
  leads to: each reload is asked for when it is due (below).

Whether code is correct is neither of these. It is settled by following the
code against the running game, with a control, and reporting what was
checked. Do not hold a pull request waiting for the owner to review its code.

**Asking.**

- Propose before starting: say what will change and what a player will see.
  Wait for the go on anything that changes how the game behaves.
- One decision at a time, in plain words.
- Ask before anything that cannot be undone or that takes the game away from
  the people in it: deleting live data, a reload, a restart, stopping the
  server. An earlier or general go-ahead does not cover the next one.
  Removing what a test itself created or caused, in that test's own teardown,
  is not this: it needs a dry run and a line in the report (see
  `DEVELOPMENT_GUIDE.md`, Testing Inside the Live Game).
- "I do not know yet" is an answer. Say it rather than force a verdict the
  evidence does not support.

**Recording.**

- A ruling goes on its issue in the owner's own words, quoted, with the date.
  Then the labels change (see `status:` above).
- A remark is not a decision. What has not been decided is open, and is
  listed as open.
- "Observed, and fine as it is" is a valid outcome. Not every finding is a
  defect, and an issue may be closed on those words.
- A report on a batch of work says what it did not touch, so that silence is
  never read as "checked".

## The board

**https://github.com/users/daiimus/projects/1** — *Gelatinous Roadmap*.

Fields, and what each is for:

| field | values | why it exists |
|---|---|---|
| **Status** | Needs decision · Parked · Blocked · Ready · In progress · Done | the execution pipeline. `Ready` is the one that matters — decided *and* scoped, so it can be picked up without asking anything. |
| **Area** | the nine subsystems | grouping. |
| **Work type** | defect · enhancement · design · question · debt | filtering. "show me defects in souls" is the query that turns a backlog into a sitting. |
| **Effort** | S · M · L · XL | unset by default; fill in when scoping, not when filing. |
| **Roadmap phase** | free text | the link back to a spec phase. This is the anti-drift hook below. |

The labels and the board fields are kept deliberately parallel, because
labels are what you see from the CLI and the issue list, and fields are what
you see on the board. Labels are the source of truth; if they disagree, the
labels win.

## Anti-drift: the one rule that would have caught the last three

**Every roadmap phase gets exactly one issue, and the phase status and the
issue state must agree.**

*Since 2026-11-17 a roadmap keeps no status for finished work (see "The three
documents" above). What is left of this rule: every phase on a roadmap is
work not yet done and has exactly one open issue, and a phase whose issue
closes comes off the roadmap. The worked example below is from before that.
Its lesson is the reason for the change: a status line in a document went
stale in both directions at once.*

A phase cannot read "Not started" while its issue is closed. A phase cannot
read "Complete" with its issue open. This is the check that failed in
September 2026, when `MEDICAL_SUBSTRATE_ROADMAP` simultaneously:

- recorded kidney fatality as `DRIFT` / "substrate gap" **after**
  `RenalFailureCondition` had shipped and been wired, and
- recorded brain-destruction-is-unconsciousness as settled design **after**
  the owner had ruled otherwise.

Stale in both directions at once, in a document that was actively being
worked in. Nothing linked the phases to anything that would have noticed.

*Correction (#3402, 2026-09-24): the first bullet was itself backwards. The
`DRIFT` record was **right** — the renal drain had stopped billing on
2026-09-05 (#2936), so kidney loss had genuinely stopped killing, and it was
the 2026-09-11 true-up marking it "✅ RESOLVED" that was stale. Checking the
roadmap against the issue tracker would not have caught it either; only
checking it against the running code would. The owner has since ruled kidney
loss non-lethal.*

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
