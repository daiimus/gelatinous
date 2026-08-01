# Linked Fixtures Specification

> **Status:** 📋 **Proposal — not implemented.** Designs *linked fixtures*: one
> real thing represented by several objects in several rooms, sharing state so
> they cannot contradict each other. The clock tower is the first instance and
> the reason the design exists, but the machinery is deliberately not about
> clocks. Builds on the time tokens shipped 2026-07-31 (#1502), which this
> needs **no changes to** — that constraint drives the whole design.

## 1 · Intent

Some things are too big to live in one room. A clock tower is visible from
several streets; so is the Boot, the agridome, the Sentinel mast, a fire, a
column of smoke.

The obvious approach — a cross-room visibility layer that renders an object
into rooms it is not in — is a large piece of machinery with hard questions
attached (line of sight, intervening buildings, z-levels, how far is too far).

**This spec takes the cheaper road, on the owner's call:** place a real object
in every room that should see the thing, and link them so they share state. No
visibility system, no sight lines. Each object is a real object, findable and
lookable by the normal rules.

The link exists for one reason: **the faces must never disagree.** If someone
sabotages the tower, every face shows it. A world where one face is stopped and
another runs is worse than having no faces at all.

## 2 · The model

A **link group** is a named set of objects that share state.

Members have a **role**:

| role | where | can be interacted with |
|------|-------|------------------------|
| `body` | the thing's own room — the tower itself | **yes** — sabotage, repair, anything physical |
| `face` | every other room that can see it | **no** — reads state, refuses interaction |

A group has exactly one `body` and any number of `face`s. A group with no
`body` is legal (a thing you can see but never reach — a distant flare, an
orbital) and simply has no interaction surface.

**Faces refuse rather than pretend.** Attempting to sabotage a face answers
with distance, not with a failure message:

> *That's four blocks away. You can see it; you can't reach it.*

This is the whole reason roles exist. If every face were equally sabotageable,
players would tamper with whichever one was nearest, and the tower would
quietly become a thing that is everywhere. Giving the crime a **location** is
what makes sabotage a plan instead of a click.

## 3 · Why write-through replication, not read-through

Two ways to share state. This matters more than it looks.

**Read-through** — one canonical object holds the state; faces store a dbref
and resolve it on every render. No drift is possible. But every render costs a
lookup, deleting the body breaks every face, and — decisively — the time-token
renderer would have to learn that an object's `clock_skew` might live somewhere
else.

**Write-through replication** — every member carries the state; a state change
writes to all members of the group.

**Replication wins on one argument:** `{time}`, `clock_skew` and
`clock_stopped` (`world/gametime.py`, shipped) need **zero changes**. Each face
already renders its own description correctly with its own attributes. The link
is only a *write path* — one function that finds the group and applies a change
— and everything downstream stays exactly as it is today.

The cost is drift: a builder editing one member directly desyncs it until
someone re-syncs. That is worth a `sync` verb, not a different architecture.

## 4 · Data shape

Per member, all plain attributes:

```
db.link_group   str    group name, e.g. "clocktower_hammett"
db.link_role    str    "body" | "face"
```

Membership is found by searching `link_group`; a tag (`link_group:<name>`,
category `linked`) should back it so lookup is a tag query rather than a scan,
matching how civilians and director objects are already tagged.

**State itself is not specified here.** That is the point: the link layer moves
*whatever attributes a fixture type declares*. A clock declares
`clock_skew` and `clock_stopped`; a fire would declare something else.

```
db.link_state   list[str]   attribute names this group keeps in sync
```

Declaring the synced set per group — rather than hardcoding clock fields —
is what stops this being a clock feature.

## 5 · Behaviour

**Write.** `set_linked_state(obj, **attrs)` resolves the group, validates the
names against `link_state`, and writes to every member including the caller.
Members that have been deleted are skipped, not fatal.

**Read.** Nothing. Members are read normally, by the existing renderers. This
is the property that keeps the change small.

**Sync.** `sync_group(name, source=None)` copies the declared state from the
source (default: the `body`, else the oldest member) onto every other member.
Run after adding a member, or after a builder edits one directly.

**Creation.** A new member added to an existing group is synced immediately on
creation, so it never appears showing a different time from its neighbours.

**Deletion.** Deleting a `face` is harmless. Deleting the `body` leaves a group
that can be seen but not touched — legal, and worth a builder warning rather
than a prohibition.

## 6 · The clock tower — the first instance

Nothing new is required for it. The clock tower is:

- a `body` in the tower's own room, with a description carrying `{time}`
- N `face`s in the streets that see it, each with its own description —
  *"the tower stands over the rooftops to the north, reading {time}"*
- `link_state = ["clock_skew", "clock_stopped"]`

**Sabotage is already modelled**, by attributes that shipped with the time
tokens:

| attack | attribute | what it looks like |
|--------|-----------|--------------------|
| stop it | `clock_stopped` | the face freezes at the moment it died. Loud. Everyone in the district knows. |
| skew it | `clock_skew` | the face lies, confidently. **Nobody knows.** |

Repair clears the attribute. Both propagate to every face through the link.

## 7 · Design consequences worth keeping

**Skew sabotage is invisible, and that is the good crime.** A stopped clock is
vandalism; a clock running eleven minutes fast is an *operation*. The whole
district reads the same wrong time, and the only contradiction anywhere in the
world is somebody's wristwatch.

That makes personal timepieces worth carrying — which reaches back into the
decision that time is legible only through objects. A public clock makes the
hour free inside its sightline and scarce outside it; sabotage makes the hour
*wrong* inside its sightline and correct only for people who didn't need it.
The detection loop falls out of the fiction rather than being designed in.

**The tower is authoritative and may be lying.** Decide deliberately whether a
tower's skew is ever set by anything other than sabotage — a tower that has
simply been four minutes fast for a decade because nobody can climb it is a
different and equally good story.

## 8 · Builder surface

```
@link <obj> = <group>[:body|face]   join a group in a role (default face)
@link/state <group> = attr[,attr]   declare the synced attribute set
@link/sync <group>                  re-sync from the body
@link/list [<group>]                members, roles, and any drift
```

`@link/list` reporting **drift** is the important one — it is how a builder
discovers that a face was edited directly, which is the failure mode this
architecture accepts in exchange for its simplicity.

## 9 · Failure modes

- **Drift** — accepted, detectable via `@link/list`, fixable via `@link/sync`.
- **A group with two bodies** — reject on join; the crime needs one location.
- **A member in no room** (carried, in a container) — legal but strange; warn.
- **A huge group** — writes are O(members). Fine at tens, not at thousands;
  no fixture should need thousands, and if one does, this is the wrong tool.
- **State written directly, bypassing the helper** — cannot be prevented, only
  detected. Documented, not defended against.

## 10 · What else this serves

Deliberately not clock machinery:

- **The Boot and the agridome** — landmarks with a presence in several streets.
- **The Sentinel mast** — already a two-object standard (mast + cabinet); a
  link group is the natural generalisation, and its powered/wrecked state is
  exactly the kind of thing that must not disagree between the two.
- **Fires, smoke columns, floodlights** — states that several rooms observe.
- **A barricade seen from both sides**, a sign readable from either face.

## 11 · Testing

- state written to one member appears on every member
- a face refuses interaction; the body accepts it
- a group with no body can be read and not touched
- deleting a member does not break a write to the rest
- a new member is synced on creation
- `sync_group` repairs a deliberately drifted member
- a group whose `link_state` omits an attribute does **not** propagate it
- time tokens still render per-member with no changes (regression guard)

## 12 · Open questions for the owner

1. **Does a face show the time at all, or only at close range?** The radio
   masts already carry a two-ring model (crisp / reach) that the Atlas draws.
   Faces could borrow it: inner ring reads the face, outer ring sees only the
   silhouette. Richer, and more work.
2. **Does the echo live in the room description or only on `look`?** In the
   description it is always present and risks clutter across dozens of rooms;
   on `look` it is clean but undiscovered. Probably a short line in the
   description with the detail on `look`.
3. **Who can repair it?** A skill gate, a tool, a gig contract — or anyone
   with the patience to climb.
