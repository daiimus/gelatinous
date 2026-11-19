# Trust & Consent Spec

## 0 · Purpose

Many in-game actions are **third-party**: one character acting *on* another.
Medical treatment, surgery, harvesting organs, frisking, restraining and
escorting are examples. Without a consent layer, every such command would
decide ad hoc whether the target can refuse. This spec defines **when consent
is required, how it is granted, and how it binds to perceived identity**, so
the behaviour is consistent and not painted into a corner.

The gate lives in `world/consent.py`: `can_contest`, `is_restrained`,
`is_conscious`, `has_trust` and `check_consent(actor, target, action_class)`.
The `trust` and `distrust` commands are `CmdTrust` / `CmdDistrust` in
`commands/CmdTrust.py`.

## 1 · Core stance — consent is the *conscious, unrestrained* path

**A target can refuse an invasive third-party action only when it can
contest: when it is conscious *and* unrestrained.** Otherwise the action lands
freely.

```
can_contest(target) = is_conscious(target) and not is_restrained(target)
```

* **Unconscious / dead** → cannot contest → **free action**.
* **Remains** (a corpse, a severed head, a severed limb) cannot contest →
  **free action**. `frisk`, `get … from`, `dress` and `undress` need no trust
  on any of them. A severed part is a corpse fragment and answers to the
  corpse's verbs (#3575, 2026-09-16).
* **Restrained** → cannot contest → **free action**. Restraint comes from a
  **grapple** *or* from lying in furniture marked `db.restraining`. Only the
  clinic AutoDoc pod sets that flag; `is_restrained` also counts any medical
  lie-in furniture. A grappled or pod-bound patient cannot contest healing or
  search/frisk; the action simply proceeds.
  * A pod holds only someone who lay down in it: nobody can put another
    person in, and anyone in it can `stand` and leave (📋 UNBUILT, #3409).
  * Restraint chairs and cuffs: 📋 UNBUILT (no issue).
* **Conscious *and* unrestrained** → **can contest** → the action requires
  **pre-granted trust** from the target (§2). Without it, the action is
  blocked. To proceed, the actor must first **restrain** the target (grapple
  them; putting an unwilling person into a pod is 📋 UNBUILT, #3409), after
  which the free-action path applies.

**Consciousness is a strict binary** on the runtime `consciousness` value.
There is no groggy middle band: groggy-but-awake contests.

**Restraint has one shared helper**, `is_restrained` in `world/consent.py`. It
unifies the grapple state (`world/combat/grappling.py`) with the `restraining`
property on furniture.

Rationale: this fits the deliberately dangerous, squishy world. You can do
anything to someone you have **subdued or strapped down**; you cannot grief
someone who is **awake, free and unwilling**, unless they have **trusted**
you. This is not "always require consent" (that kills the danger) and not
"never" (that is open griefing). It **generalizes the existing workaround**:
invasive commands already gated to unconscious/dead; trust is the
*conscious-and-willing* path, and restraint devices are the
*conscious-but-subdued* path.

### Build around restraint, not around NPC consent

The world is built around **restraint devices**, not around NPCs granting
trust. The **healing pod** is the canonical example: it establishes the
restrained state, and *that* is what authorizes the AutoDoc (or a doctor) to
operate, with no trust grant needed. NPCs are character objects and *can*
hold trust grants like anyone (§6), but it will be rare; the structural
systems (pods, chairs, restraints) do most of the consent work.

### A body left behind by a jacked-in decker

A **jacked-in decker's body** (left in meatspace while its owner is in the
net) reads as unable to resist, so the contest predicate makes it a
**free-action target**: frisk, move or harm the slumped body. This is
emergent from §1, with no special case (`specs/proposals/PHASE_LAYER_SPEC.md`
§5.3). Acting *across* phases is impossible, because perception windows are
perceive-only, so consent never spans phases.

## 2 · Trust binds to *perceived identity*, not to the person

The defining requirement: **trusting "batman" must not mean trusting "bruce
wayne."** This rides entirely on the existing identity machinery, with no new
identity logic.

* **Key = `get_apparent_uid(actor)`** (`world/identity.py`). It hashes the
  identity signature
  `(sleeve_uid, height_override, build_override, keyword_override,
  essential_disguise_item_type_ids)`:
  * Bruce doffs the cowl → an **essential disguise item** leaves the
    signature → his apparent UID flips from the batman UID to the bruce-wayne
    UID → a grant made to "batman" **no longer matches**.
  * `sleeve_uid` is a per-character salt → an **impostor** in an identical
    batman getup produces a *different* UID. Trust cannot be spoofed by
    copying an outfit.
  * The worn-item axis is **only essential disguise items**, not all
    clothing → swapping a non-essential jacket does **not** change the UID,
    so trust does not silently lapse over a wardrobe tweak, only over a real
    identity change.
* **Re-sleeve lapses trust.** If the trusted person re-sleeves into a new
  body (new `sleeve_uid`), their UID changes and the grant lapses. You
  trusted *that body/presentation*, not an abstract soul.
* A flash clone keeps the dead body's `sleeve_uid` (`create_flash_clone` in
  `commands/charcreate.py`), and so does a soul's new body (`restore` in
  `world/imprint.py`). Trust others gave that person still holds for the new
  body while its look is unchanged.
* Grants live on the character who made them and are not copied: a flash
  clone starts trusting no one.

### Storage

Grants live on the **grantor** (the potential target):
`db.consent_grants = {apparent_uid: {"classes": [action classes], "label": "<how
the grantor saw them at grant time>"}}`. The label is refreshed on each new
grant. Grants survive logout until revoked.

### Duress

**A grant made under duress stands** (while grappled or threatened). It is
valid but revocable: bargaining your way out of a grapple is
world-appropriate, a grant is a grant, and it can be revoked the moment you
are free.

### The gate is checked per command

There is no special machinery for revoking mid-procedure. Multi-step surgery
is multiple commands, and the gate is checked on each command invocation, so
a revocation takes effect at the next step. The step in flight completes;
nothing aborts mid-swing.

## 3 · Action classes

Trust is granted per **action class**. A class maps to a set of gated
commands.

| Class | Covers | Notes |
|---|---|---|
| `escort` | `escort <person>`: lead them through exits ahead of you | `follow` is your own movement and needs no trust. Dragging is grapple plus movement, with no class and no command. |
| `grab` | consensual restraint through `grapple` (let them grab/restrain you uncontested) | the "strap me in willingly" path (§3.4) |
| `heal` | **all** medical commands: treat, bandage, inject, install, **operate, harvest** | **deliberately blanket** (§3.1). `heal` also gates giving any substance to someone else through a consumption verb (`inject`, `chug`, `devour` and the rest), medical or not (#2458). |
| `search` | `frisk` (alias `patdown`): **identifies the items on their person** (worn, carried, **and concealed**) | the active counter to organic concealment (§3.2) |
| `dress` | dress / undress (strip) the target's clothing | `dress`/`undress` call `check_consent(caller, target, "dress")` through `_can_third_party_clothing` (`commands/CmdClothing.py`). Severed parts and corpses can always be dressed and undressed (§3.3) |

Where each class is checked:

* Medical items (treat and the rest) check `heal` through
  `check_medical_requirements`.
* `operate`, `incise`, `harvest`, `install` and `suture` share one consent
  seam, `_resolve_target` in `commands/CmdSurgical.py` (`heal` class).
* `grapple` checks `grab` in `resolve_grapple_initiate`
  (`world/combat/grappling.py`), before the contest.

### Movement

`escort <person>` leads someone: at each exit they go through first and you
come after (`usher_escortee` in `world/movement_coupling.py`, called from
`Character.at_pre_move` in `typeclasses/characters.py`). Consent and
consciousness are checked again before every move, so a revoked grant
releases them at the next doorway, and an exit that refuses them stops you at
the threshold too. Someone unconscious cannot be escorted; drag them by
grapple instead. Two people cannot escort each other. `stop escorting`
releases your escortee.

`follow <person>` needs no trust: when the leader leaves, you take the same
exit after them (`bring_followers`, called from `Character.at_post_move`;
command in `commands/CmdFollow.py`). Following someone, or stopping, reveals
a hidden follower. A follower who cannot keep up (a refused door, a leader
who leaves with no exit) loses the trail, and one who cannot perceive a
hidden leader is left behind without a word. `stop following` also breaks
away from anyone escorting you.

Dragging stays **emergent** from grapple plus movement, with no command, by
design.

### 3.1 · `heal` is intentionally all-medical — betrayal included

`heal` is **one blanket class covering every medical command**, by design. It
is a deep level of trust: granting it lets the holder do anything medical to
you while you are awake, including malpractice and **harvesting your
organs**. The betrayal affordance (you trusted your ripperdoc; they cut out
your kidney) is a **feature**, not a footgun. We do *not* split benevolent
treatment from invasive surgery in the trust layer: the danger is the point.

### 3.2 · `frisk` — what it reveals

`frisk <target>` **identifies the items on a person: worn, carried, and the
concealed holdout the sdesc normally hides.** The manifest reads the worn
registry, in-hand items, carried pockets and tokens. It is a *reveal*, not a
contest, so it rides the standard consent gate (consent, or an unconscious /
restrained / dead target). Corpse objects are always searchable.

It is the lawful/forceful inspection: a security bot frisks a subdued
suspect, a medic frisks a willing patient, you frisk a corpse. It is the
information step that precedes confiscation or theft.

Contrast **theft** (`steal`/`pickpocket`), which is the *nonconsensual
contest* version and lives in `specs/proposals/STEALTH_AND_DETECTION_SPEC.md`
§6.2: frisk asks, theft takes. Theft reads the same `can_contest` predicate
(`commands/CmdTheft.py`): against a mark who cannot contest (unconscious,
dead, restrained) it lands with no contest. Trust plays no part in theft.

### 3.3 · `dress` — narrow by design (2026-07-02)

`dress` covers **third-party clothing manipulation only**: dressing someone,
undressing/stripping them. It is deliberately **narrow**, not a broader
"intimacy" class. Intimacy in this game is expressed through free-form poses,
which stay ungated social fiction, and no further mechanical contact verbs are
foreseen (the ones that exist, frisk, grapple, heal and escort, are already
classed). If a new contact verb ever appears, it gets its own class by the
same pattern.

The companion case does NOT ride this class in practice: an LLM companion
wears/removes her own clothing via the `style` tool (self-action, §6), so the
player's request is answered by *her* act, with no grant needed.

### 3.4 · `grab` — a consensual grapple (#3363, owner ruling, 2026-09-13)

`resolve_grapple_initiate` (`world/combat/grappling.py`) calls
`check_consent(grappler, target, "grab")` before the contest.

* **Trusted**, or a target who cannot contest (unconscious / restrained, the
  free path): the target is held **uncontested**. There is no roll, both
  parties are set yielding so nobody auto-struggles, the held person gets no
  retaliation target, and the prose reads "takes hold of X, who lets you".
  `CmdGrapple` grants no ambush bonus on a consensual grab.
* **Untrusted**: the contested grapple.

Grapple doubles as holding; what makes it an attack is whether anyone chose
violence. `CmdGrapple` still reports every grab to the crime system as an
assault (`report_crime`) and has the target react as to an attack
(`react_to_attack`), consensual or not.

## 4 · Command surface

| Command | Effect |
|---|---|
| `trust <person> to <action>` | grant one action class to that person's *current apparent identity* |
| `trust <person> to all` | grant every action class (blanket) |
| `trust` | list who you trust and with what (rendered via recognition names, §5) |
| `trust <person>` | show that person's grants (**not** a blanket; blanket is `to all`) |
| `distrust` / `untrust <person> [to <action>]` | revoke one class, or all of that person's grants when `to <action>` is omitted |
| `distrust all` / `trust no one` | wipe every grant |

**Granting requires the person present.** You trust who you can see, and the
UID is captured at grant time.

**Revoking works from memory.** Name the person as you know them (your
recognition name, or the label taken at grant time); they need not be
present. An exact name wins over partial matches; several partial matches
are refused. `distrust <person> to all` is refused: to revoke everything from
one person, leave out `to <action>`. This presence asymmetry matches how
perception gates everything else.

## 5 · Listing & perception

`trust` renders each stored UID back through recognition:
`world.identity.resolve_assigned_name` on your recognition memory (your own
name for that look, or the name of the look you watched it come from). The
list reads in *your* terms: `You trust:`, then one line per grant, e.g.
`batman — heal` and `the lean droog — escort`. A UID you have since forgotten
falls back to the display-label snapshot taken at grant time. You always see
trust the way you *perceive* the trusted party, consistent with how the rest
of the identity system renders.

`trust <person>` is different: it works only on someone in the room with you,
names them as you see them now, and shows what you trust that look with.

## 6 · NPC participation — **self-action only** (resolved 2026-07-02)

NPCs are character objects and the `db.consent_grants` store works on them
like anyone, but **NPCs do not grant trust in practice**. The decided stance:

* **NPC as grantor: no.** No LLM `trust` tool is planned; an NPC never hands a
  player standing consent. Where an NPC *cooperates*, it acts on ITSELF
  through its own real commands. The canonical case is the LLM companion
  wearing/removing her own clothing via the `style` tool. The player asks;
  the NPC does. This keeps consent as an in-fiction act every time rather than
  a stored permission, and players can never mechanically act on a conscious
  NPC's body (the restrain/unconscious paths aside). A RipperDoc-style
  standing `heal` grant remains *technically possible* via the shared store
  if a future design wants it (nothing structural forbids it), but it is out
  of scope and off the roadmap.
* **NPC as actor on a player.** A security bot cannot heal/search a
  *conscious, unrestrained, untrusting* player; it must lawfully **restrain**
  them first (grapple; cuffs, and putting someone into a pod, are
  📋 UNBUILT, see §1). This is the dispatch spec's reserved seam
  (`specs/proposals/NPC_DISPATCH_AND_SIMULATION_SPEC.md` §6): sequence
  coercive authority content *after* this gate.

### NPCs that restrain today

* **Criminal side.** Coercive restrain-then-act by NPCs runs through real
  commands and this spec's own predicate. A lawless soul that cannot afford to
  eat builds a `grapple → rob → disengage` job (the hunger plan in
  `world/souls/actions.py`). The `grapple` step in `world/souls/jobs.py`
  consults `can_contest(mark)` before issuing the command, and the `rob` step
  re-checks it.
* **Lawful side, one case.** A unit takes hold of a downed unit's wreck by
  `grapple` and drags it to the recovery bay (the `recover` plan in
  `world/souls/actions.py`, steps `hold` and `deliver` in
  `world/souls/jobs.py`).
* **Security units do not restrain.** `world/director/security.py` gives a
  unit challenge, aim-lock and watch (`security_arrival`, `watch_once`) and
  escalates straight to `attack` (`_engage`). It never grapples, cuffs or pods
  anyone, so "restrain-then-act" has no lawful actor.

## 8 · Cross-references

- `IDENTITY_RECOGNITION_SPEC`: `get_apparent_uid` / `get_identity_signature` /
  `get_assigned_name` / `recognition_memory`; the entire identity key (§2).
- Grapple / restrain (`world/combat/grappling.py`): one source of the
  restrained state (§1).
- Clinic furniture / AutoDoc (`typeclasses/furniture.py` `AutoDoc`): the
  restraint-device source (healing pod) and the primary `heal` consumer.
- `commands/CmdSurgical.py` `_resolve_target`: the one consent seam for
  operate, incise, harvest, install and suture (`heal` class).
- `specs/proposals/NPC_DISPATCH_AND_SIMULATION_SPEC.md` §6: NPC-on-player
  actions defer to this gate.
- `specs/proposals/PHASE_LAYER_SPEC.md` §5.3: a jacked-in decker's body is a
  free-action target (§1).
- `specs/proposals/STEALTH_AND_DETECTION_SPEC.md` §6.2: theft, the contest
  counterpart to `frisk` (§3.2).

## 10 · Unbuilt

* Putting another (unwilling) person into a pod. Today a pod holds only
  someone who lay down in it, and anyone in it can `stand` and leave:
  📋 UNBUILT, #3409.
* Restraint chairs and cuffs: 📋 UNBUILT (no issue).
* A lawful NPC that restrains a conscious suspect (lawful restrain-then-act
  for security NPCs, the dispatch coercive-authority seam,
  `specs/proposals/NPC_DISPATCH_AND_SIMULATION_SPEC.md` §6): 📋 UNBUILT
  (no issue). What remains is security-NPC content (when bots choose to
  restrain-then-move), which belongs to the dispatch arc.
* Future (user-stated): motorics-based movement DELAY will sequence these
  beats into organic chase scenes.
* Future (user-stated): a stealth `shadow` command = follow while unseen
  (`specs/proposals/STEALTH_AND_DETECTION_SPEC.md`).

## 11 · Not decided

The resolutions in §1 (consciousness, restraint helper),
§2 (duress, per-command gate) and §4 (presence-asymmetric grant and revoke)
were presented in the 2026-07-02 deep-dig as recommendations, were not
contested, and were built as written; the owner has not ruled on them
separately.

* Should a flash clone keep the trust grants its dead body had made,
  instead of starting with none?
* Should `distrust <person> to all` be accepted as the same as
  `distrust <person>`, matching `trust <person> to all`, or stay refused
  (perhaps with an error that points to `distrust <person>`)?
