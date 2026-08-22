# Backups, Stale Restores & Memory Forgery

> **Status:** 📋 **DESIGN DRAFT — spec-first, build-later (2026-08-22).**
> **§4 and §8.1/§8.2 carry owner rulings (2026-08-22).**
> §1 documents **shipped** behaviour (traced from
> `world/souls/posts.py`, `typeclasses/death_progression.py`); §2
> onward is proposal. The interactive half depends on the net layer
> ([`DECKING_MATRIX`](DECKING_MATRIX.md)), which is itself spec-first
> and gated on the phase/verticality work — so this is
> **spec-now, build-when-the-world-is-ready**.
>
> **Design lineage:** the "consciousness is a file you can copy, lose,
> or edit" premise is common to the genre; the specific handling here
> is ours, and source material is paraphrased rather than cited.
>
> **Related:** [`IDENTITY_RECOGNITION_SPEC`](../IDENTITY_RECOGNITION_SPEC.md)
> (apparent UID, the forensic chain),
> [`NPC_MEMORY_AND_IDENTITY_SPEC`](../NPC_MEMORY_AND_IDENTITY_SPEC.md),
> [`DEATH_AND_SLEEVE_LIFECYCLE_SPEC`](DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md),
> [`NPC_POSTS_AND_REINCARNATION_SPEC`](../NPC_POSTS_AND_REINCARNATION_SPEC.md).

---

## 1 · What exists today (shipped)

A **backup** already exists in the game. It is called the *estate*, it
is taken at death, and it is a plain record — which is the whole
reason this spec is short.

`world/souls/posts.py::_estate_of()` writes:

```python
{
  "version": 1,
  "name":        str,     # who this is
  "sleeve_uid":  str,     # the BODY to come back in
  "died_at":     float,
  "taken_at":    float,   # what the backup HELD — restore keys on this
  "memories":    [...],   # episodic (llm_memories)
  "dossiers":    {...},   # what they concluded about people
  "thoughts":    [...],   # interiority
  "recognition": {...},   # who they knew by FACE, keyed by apparent UID
  "voice":       {...},   # who they knew by VOICE
}
```

* **Trigger:** every death calls `snapshot_estate()`, but it only
  *stores* for a post-holder. Backups are therefore **institutional** —
  a policy covering staff, not a consumer product. PCs get none.
* **Storage:** on the post fixture, `db.post_memory_snapshots[shift]`.
  One record per shift, **overwritten**.
* **Restore:** `_try_resleave()` rebuilds the named keeper, debits
  `RESLEAVE_PREMIUM` from the insurer's till to a Thawn-Harrison
  terminal, and restores everything with a timestamp earlier than
  `taken_at`. The body inherits the recorded `sleeve_uid`, so the face
  is the same face.
* **The gap:** `taken_at = died_at - RESLEAVE_GAP` (5400s). The last
  ~90 minutes never made the backup.

### 1.1 · The one design decision already made

`taken_at` is the only field restore consults. Today it is derived
from a constant. **Everything in §2 works by changing where that
number comes from, and changes no restore logic.**

---

## 2 · Backups become something you DO

Replace the constant with an event.

* A character visits a terminal (Thawn-Harrison, clinics, a black
  clinic at a markup) and takes a backup. `taken_at` is *now*.
* The gap stops being a number in the source and becomes **how long
  you left it** — a fact about the character, visible in play, and
  their own fault.
* Skipping it is a real economy: the premium competes with rent, food,
  and chrome. Poverty means going un-backed, which means the colony's
  poorest die hardest. That is the setting working correctly.

**Prerequisite — history.** "Restore from the latest" is only
meaningful if more than one exists. Keep a list ordered by `taken_at`,
capped. Everything interesting below needs this: a shelf of past
selves to browse, choose between, steal, or quietly edit.

**Storage fork.** Once a backup belongs to a *person* rather than a
post, its home is the **insurer**, keyed by identity — not the post
fixture. The record already carries `name`, `sleeve_uid` and
`taken_at`, so this is a relocation, not a redesign. It also gives the
thing a physical address, which §5 needs.

---

## 3 · Three tiers of harm

Ranked by how interesting they are, which is the inverse of how
obvious they are.

| | effect | why it's weak or strong |
|---|---|---|
| **Destroy** | they stay dead | weak — the world already kills people for free |
| **Steal** | you hold a person in a file | strong — leverage, ransom, a copy walking around |
| **Edit** | they come back subtly wrong | **strongest** — nobody knows, including them |

**Editing is the good one**, and it needs no new data model.
Recognition is a dict keyed by apparent UID, each entry carrying an
`assigned_name`, encounter history and free-text `notes`. So:

* **Delete an entry** → the restored person walks past their closest
  ally without a flicker.
* **Add one** → they greet a stranger like family, warmly, by name.
* **Rename one** → they call the wrong person by the right name.
* **Edit the notes** → the LLM layer reasons from a forged premise and
  argues *for* it, in their own voice.

You do not kill somebody. You edit who they loved. That is the thesis
of the whole feature, and it is a dict write.

---

## 4 · The sleeve is a container, not a field

**RULED (owner, 2026-08-22): `sleeve_uid` is read-only. The sleeve
itself is never editable.**

The record carries the body identity because continuity requires it
(`IDENTITY_RECOGNITION_SPEC` §Principles 1: *same body = same
recognition across clones*; and `create_flash_clone` already inherits
it — *"same body means same sleeve_uid"*).
`apparent_uid = blake2b(sleeve_uid + overrides + essential worn items)`,
so all recognition resolves through it. Forging that field would be
identity theft nothing could argue with, and it is therefore closed.

**But the interesting crime was never forging the field.** A backup
holds a *body* — a sleeve you can grow. So:

> Steal somebody's backup. Write **your own** persona into it. Grow
> it. There are now two of you, and the second one wears their face.

The sleeve is immutable; **the contents are not**. You do not edit
whose body it is — you take a body that is unambiguously theirs and
put yourself inside it. Recognition works perfectly, because it is
genuinely their sleeve. The colony sees them. It is you.

### 4.1 · Double-sleeving is a goal, not just a crime

Running two bodies at once is a **desirable player objective**, not
only an attack. The backup system is one route to it: bodies are
expensive and rare, and somebody else's backup is a body nobody is
currently using.

Consequences that make it worth the trouble — and worth catching:

* their face is seen doing things they did not do, and every witness
  is honestly certain it was them
* they have an alibi that nothing in the recognition layer supports
* §5's forensic chain is the **only** system that disagrees — the
  corpse's stamped signature against a living presentation

**Open (owner):** how one mind runs two bodies. Simultaneous control,
switching with the idle body dormant, or a copy that diverges into its
own person the moment it wakes. That last one is a different and much
larger story engine — see §8.4 — and this spec does not assume an
answer.

---

## 5 · Detection already exists

This is what makes forgery *fair* rather than unfalsifiable, and it
needs no new system.

Per `IDENTITY_RECOGNITION_SPEC` §Forensic chain, every body-derived
surface is stamped at the moment of transformation with
`apparent_uid_at_death` and `source_signature` — corpses, severed
limbs, organs, blood pools. The old body keeps a true record of who it
was.

So a tampered restore is **discoverable by autopsy**: the corpse's
stamped signature versus what the restored person now presents. That
is a real investigative loop, built from parts that already ship, and
it is the bridge this spec sits on — *forensics on one side, cybercrime
on the other, the backup in between.*

Corollary: **the corpse becomes evidence worth destroying.** Anyone
forging a restore wants the old body gone — which is a gig, and one
the Ripper spec is already shaped to take
([`GIG_RIPPER_SPEC`](GIG_RIPPER_SPEC.md)).

---

## 6 · Distortion on a living sleeve

The owner-parked **memory distortion** thread lands here rather than
in a separate system. Same operations, different target: instead of
editing a backup and waiting for a death, edit the person in front of
you.

* **Vector:** not the net — the *body*. A clinic chair, an Autodoc, a
  black-market rig. Distortion is surgery, not a run.
* **Same fields:** `recognition`, `voice`, `dossiers`, `memories`.
* **Different risk:** a living target may *notice* — inconsistencies
  they can be confronted with, which is drama rather than a die roll.
* **The pairing:** distort a sleeve *and* its backup, and there is no
  version of that person who disagrees with you. That is the endgame
  crime, and it should be very hard.

---

## 7 · Net-layer integration

Under the everything-is-a-file doctrine
([`DECKING_MATRIX`](DECKING_MATRIX.md) §2), backups are simply files
on the insurer's system. No special-casing:

* they are **found** by the same enumeration as any other record
* they are **read** with the same verbs (the read *is* the theft — a
  copy is a person)
* they are **written** with the same verbs, under the same trace
  pressure
* the insurer is a **fixed, findable, defensible address** — which
  gives the net layer one of its first genuinely high-stakes targets

Backups also make traces *personal*: getting caught mid-write on
somebody's estate is not a fine, it is being found holding a person.

---

## 8 · Questions

**8.1 — `sleeve_uid` writability. ✅ RULED (2026-08-22):** read-only /
signed. The sleeve is a container, never an editable field. The crime
is inhabiting a stolen body, not forging one — §4.

**8.2 — Do PCs get backups? ✅ RULED (2026-08-22):** no; the estate
stays **institutional**. Players already resleeve free via
`create_flash_clone`, which inherits the sleeve (`same body means same
sleeve_uid`) and deliberately leaves the brain empty — *"flash clones
have empty brains and recognise nobody"*. There is no perm-death to
soften and no premium to charge, so coverage would buy nothing today.

> Worth noting for later: this is **coherent, not inconsistent**. A PC
> without a backup wakes recognising nobody; an NPC with one wakes
> knowing what the backup held. **The backup IS the memory.** If PC
> coverage is ever revisited, that is the value it sells — not
> survival.

**8.3 — History depth.** How many past selves does an insurer keep,
and does a stale restore cost less than a fresh one? *(Open.)*

**8.4 — Is a copy a person?** §4.1 makes two bodies reachable. If the
second wakes and *diverges*, the colony contains two people with one
past and a growing disagreement. That is a story engine of its own and
probably its own spec. *(Open.)*

**8.5 — Does the world know backups exist?** Common knowledge or a
Thawn-Harrison secret. Changes every conversation about it. *(Open.)*

---

## 9 · What must not be built yet

* Anything needing the net layer (§7) — gated on phase + verticality.
* Double-sleeving (§4.1) — needs the net layer AND an answer to how
  one mind runs two bodies (§8.4). The largest thing in this spec.
* Personal backups — **ruled out** for now (§8.2), not merely gated.

**Buildable independently, whenever wanted:** backup *history* (§2
prerequisite) and the on-demand capture command. Both are small, both
are useful on their own, and both are the foundation everything else
assumes. Neither commits to a single answer in §8.
