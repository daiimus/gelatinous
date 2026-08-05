# The Building Playbook — why we build, how we build, what remains

> **Status:** 🧭 LIVING DOCUMENT (2026-08-05). Not a system spec — the
> working doctrine for architecting the rest of the city. §1–§3 are
> settled law distilled from shipped practice and owner calls scattered
> across `VERTICALITY_AND_BUILDINGS_SPEC`, `SPATIAL_COORDINATE_SYSTEM_SPEC`,
> and two months of builds; they change only when a build teaches us
> something. §4 is the ledger of the remaining city and is *meant* to be
> argued with — entries marked **candidate** are unsettled until the
> owner says otherwise.

---

## 1 · What a build must accomplish

The city is the game's largest system, and a build is a systems commit,
not scenery. Before authoring a room, every proposed build answers six
questions. A build may answer "deliberately none" to any of them — but
it answers.

1. **Who works or lives here?** Places are staffed before they are
   described. A venue without a person is a facade; name the post, even
   if the NPC ships later (`NPC_POSTS_AND_REINCARNATION_SPEC` makes
   posts durable). Compare: every venue that *works* — Sable's lounge,
   Vance's clinic, Ottilie's cart, Ezra's shop — is a person first.
2. **What work does it host?** The growth thesis is the gig/freelancer/
   favor loop: progression is favor + gear + rep, not stat leveling.
   A build should create work — a gig board it grounds, a service it
   sells, a favor it can owe — or say why it hosts none.
3. **How does Z figure?** Verticality is the game's thesis and the
   volume is paid for. Every footprint decides its column: floors above,
   basement below, rooftop plate, air cells, or a deliberate refusal
   (single-story by design is a choice, not a default).
4. **What future system does it pre-wire?** The capstone doctrine is
   *build pieces connectable, snap on later* — decking wants towers and
   file-bearing institutions; climbing hooks want faces worth scaling;
   phase layer wants interiors that multiply; radio wants height; the
   Ripper wants a sewer. A build placed well makes a future system
   cheaper; say which one.
5. **What is true here?** Lore constraints bind: Domino's Gambit,
   stranded CY 61, brands on everything sold or made (exceptions:
   handmade, ubiquitous generics, deliberate anti-brands), venues carry
   distinguished proper names (the "Aster register"), interiors are
   surface language never voids, and the colony's maps stay vague-not-
   false. New lore beyond established canon is an owner call.
6. **What does the atlas owe it?** New rooms appear on the live atlas
   free via the export. A new *building class or landmark* owes rig art:
   the sprite scene, the grind, and the `export_models.py` rebake — art
   budget is part of the build estimate, not an afterthought.

## 1.5 · The City Section (owner-set, 2026-08-05)

The architecture of the whole, called out as core requirements. Builds
argue with §4; they do not argue with this section.

**The bowl.** The colony sits in a crater roughly **twenty stories**
deep. The skyline lives inside that envelope: the tallest building
tops out around **sixteen to eighteen** (the height that "feels tall"),
just under the rim. Today's tallest builds reach ~8 — the city has
used less than half its vertical budget. The crater wall is the city's
outermost facade and the honest end of every map.

**The organism.** The colony's purpose is **terraforming; everything
else is an offshoot of it.** The water cycle is the city's skeleton:
**ice mining below** feeds the terraformer; the **central channel** —
the gap the Central Span crosses — works as a large-scale **aquaponics
basin**; the basin feeds **vertical agricultural farms**; cultivation
climbs to **green spaces on the rooftops**. The Atmospheric Processor
makes the air. Every industry, gig, and trade in the colony should
trace to this cycle in at most two steps. Register note: this adds a
**solarpunk thread to the spacepunk/cyberpunk base** — grow-lights,
vine-run conduit, algae glass, planted roofs; growth forcing its way
through the grime is the proof the colony is alive.

**The plan: corridors, not zones.** The city organizes the way cities
organically form — along the routes work travels. **Industrial
corridors**: the freight run from the Landing Pad toward the
Processor's skirt; power down Volta; fab-labor along Riveter's Way.
**Cultural corridors**: each quarter's life concentrates on a main
street — venues cluster on the spine unless there is a reason to hide.
Even distribution is the enemy of role-play; convergence is engineered
at city scale first.

**Northside: the megablocks.** Corporate megablocks/arcologies cluster
north — the high end of the gradient and the corporate vocabulary's
home. They **eat the streets** (street-tunnels: covered street rooms,
no sky, sodium all day) and stitch to each other with **skyways**
(Minneapolis-style enclosed bridges: parkour rungs, weather-free
fabric, and funnels where paths must cross). Interiors obey
**vast-implied, brief-actual**: scale lives in sightlines, not room
count — one atrium gallery with the park ten stories down beats a
hundred corridor rooms. A room exists only if players can meet in it
or it is a rung on a route. The 16–18-story anchor's identity (Thawn
grown upward, or a new name) is an **owner call, pending**.

**Southside: the wall and the Processor.** The fringes build **into
the crater face** — unorthodox structures, slope-and-terrace geometry
(the sloped-exit tags exist for exactly this), the make-do register at
its extreme, terraces as commons. And the **Atmospheric Processor
dominates the colony**: footprint from Volta & Riveter's Way across to
the Spillane and deep toward the southern fringe — **reserved; nothing
else builds in that span**. Industrial-sacred register; plausibly the
one silhouette that reaches the rim.

**Below.** The down-Z layer is real: **ice mines** under the colony
feed the terraformer, and the underground (mines, service galleries,
the sewer the Ripper wants) is a build layer with its own routes, not
a basement afterthought.

**Traversal.** Street-to-precipice is a guaranteed, solvable journey:
**parkour as the common verb, rappelling/climbing as punctuation.**
Two or three **named ascent corridors** carry the guarantee — the
northern architecture climb (roofs and skyways through the
megablocks), the southern geology climb (wall-dwelling terraces), and
the Processor's industrial spiral. The stepping-stone height rule
binds **only along ascent corridors**; elsewhere a build takes
whatever height serves it. The **rim stays empty** — the reward for
twenty stories is wind and the whole colony below — except **one
terminus structure** (a beacon, a dead gantry) marking the top of the
route.

**Culture: vague by design.** No cemented cultures, no named factions
of players. The divides live in the **day-to-day texture** — street
preachers, tradesmen, an accent, an heirloom — drawn from three
ambient forces available to any build: descent from the mission's
org chart (crew, terraformers, corporate, labor, liner passengers who
were never supposed to stay), the Light (faiths of the stranding),
and the sleeve divide (eternalists vs. single-lifers, a line that runs
through families, not districts). Texture, never territory; flavor,
never canon. NPC-run factions remain the only factions.

## 2 · Settled doctrine (the law, with sources)

**The grid** (`SPATIAL_COORDINATE_SYSTEM_SPEC`, live):
- Coordinates are the data model; **hand-authoring is the authoring
  model**. No `@stack`, no ad-hoc builder commands — floors are rooms,
  stairwells are up/down exit pairs, authored like anything else.
- `@coordseed` seeds from the **pinned origin** (Central Span, the
  `coordseed_origin:spatial` tag) — never re-frame the world from where
  you happen to stand.
- Split levels use **sloped-exit tags** (`slope_down`/`slope_up:<exit>`),
  so the geometry stays derivable; `warp` is reserved for genuinely
  non-Euclidean links.
- Audit with `@room` (one-surface profile) and `@building <prefix>` /
  `/radius` (whole-structure drift table). A build is done at **zero
  geometry contradictions**, not before.

**The vertical doctrine** (owner-set 2026-07-25):
- Open plates — roofs, decks, hull-tops — are **strip rooms tiling
  their footprint**, never one big room.
- **Spine links are plain exits; every other applicable direction,
  including diagonals, is a wired edge.** Air cells are deliberate
  negative space: fall lanes now, flight later.
- **Every air build closes with the edge audit** — "edges accountable."
  No unexplained adjacency between a plate and the air beside it.

**Doors and tenancy** (`VERTICALITY_AND_BUILDINGS_SPEC` §2–§3, live):
- A door IS the exit, with state; passage requires it open.
- Access is **biometric grants** — no keys, codes, or cards; forgery is
  the attack surface. Unit doors get the spring-latch autolock.
- Rentable units carry `residence_building` + `residence_origin` at
  build time — `memory`'s dossier depends on them.
- B&E is a PvE mechanic: player-rented rooms are not burglary targets.

**The room itself** (practice, 246 rooms deep):
- **Five-senses descriptions** are the register — a room ships with its
  sense layers, not "desc now, senses later."
- Room `type` is load-bearing twice: it routes **crowd-pool** ambience
  and picks the room's **atlas class**. Set it deliberately; check both
  surfaces.
- The `outside` flag is weather and sky truth — the Toe breach doctrine:
  a hole in the hull means weather comes through it.
- Props are **seasoned, not stewed** — and branded.

## 3 · The session ritual

The shape of a build session, in order. Steps compress for small builds;
none are skipped silently.

1. **Recon** — the live atlas plus `@building`/`@room` over the site.
   Agree the footprint and column on the grid before any digging.
2. **The name pass** — venue proper names, street names, unit numbering.
   Names are design; do them sober, first.
3. **Rooms** — dig, type, `outside`, crowd base, five senses.
4. **Coordinates** — seed from the origin, tag slopes, run the audit to
   zero contradictions.
5. **The column** — strips, spines, edges, air cells; close with the
   edge audit.
6. **Doors and tenancy** where they apply — grants, latch, residence
   attrs, kiosk wiring.
7. **People and work** — posts named (built now or queued), gig/favor
   hooks grounded, shopkeeper/till wiring where trade happens.
8. **Props** — branded, one seasoning element per cell.
9. **The atlas gate** — verify on the live render; if the build
   introduced a new class or landmark, do the art: rig scene → sprite
   grind → `export_models.py` rebake, in the same arc, not "later."
10. **Ship** — the deploy cycle, and if a build taught doctrine, the
    playbook and the source spec get the lesson in the same PR.

## 4 · The remaining city — the ledger

What the city still owes us, ranked by how much is already decided.
**Spec'd** items have documents; **named** items exist as owner calls in
banners and memory; **candidates** are unsettled proposals awaiting an
owner verdict — argue with them.

**Spec'd, waiting:**
- **The Ripper's den** (`GIG_RIPPER_SPEC`, pending owner review of §6
  legality + §7): sapient corpses → appraisal → cold-room resale, paid
  disposal. Wants the Brackett basement and a sewer connection —
  which makes it the natural *first customer of the sewer layer*.
- **The Rook, Phase 2** (`project` decision): the ambient broadcast loop
  around the sealed Brackett basement studio. Small build, mostly
  systems; the space exists.
- **Clinic completions**: cyberware-install rooms and the clinic's
  remaining sense layers (`MAXWELL` TODO list) — install space is also
  decking/chrome-economy pre-wiring.

**Named in doctrine, undesigned:**
- **The underground**: the ice mines feeding the terraformer (§1.5),
  plus the service galleries and the sewer the Ripper wants (Brackett
  basement link, paid disposal, B&E underworld, decking texture). One
  down-Z layer, several customers — design it as a layer, not as
  disconnected basements.
- **The water cycle made visible**: the central channel as aquaponics
  basin, vertical farm structures, rooftop green spaces — the
  solarpunk thread (§1.5). Each is a build; together they are the
  colony's metabolism on display.
- **Climbing-hooks content**: the mechanic is now **doctrine-ruled**
  (see `PARKOUR_TEMPLATE_LIBRARY.md` §0: both directions, any edge,
  gear-length tiers, deployed lines thread room descs and can be cut,
  failure burns stamina not falls) but not yet built. The rooftop
  archipelago, the Boot hull, and Thawn's tower faces are the obvious
  first ascents; every build from today pre-wires the seams per the
  template library.
- **The tower you run up**: decking is explicitly gated on verticality's
  texture — "the corp tower you run up." Thawn-Harrison is the standing
  corp presence and its courtyard/cathedral register is already art;
  whether the run-up tower IS Thawn or a new build is an **owner
  call**.

**Candidates (unsettled — owner verdict wanted):**
- **A true market hall**: stalls exist as street props; a roofed market
  venue would host hawker posts, gig-board density, and fence/pawn
  texture (P3 pawn was rejected once — a market revives the question
  only if the owner does).
- **The port**: the Colonial Landing Pad exists as a pad; a working port
  district (freight, customs, the Longhaul/Slowboat brands made flesh)
  would ground the logistics economy and give the pad a reason.
- **The gate-anchor site**: the atlas lore names processor stacks and a
  gate anchor from the terraform mission. As a district it would be the
  colony's one monument to being stranded — high lore risk, high
  payoff, entirely an owner call on what is true there.

## 5 · Fitting it together

The connective tissue, so individual builds sum to a city:

- **Every build feeds the loop**: place → post → work → favor → rep.
  A build that adds rooms without adding work must justify itself as
  connective tissue (streets, air, sewers) or refusal (ruins).
- **Systems snap on later, so seams go in now**: posts before NPCs,
  height before flight, files before decking, faces before climbing.
  The cheap version of a future system is an attribute set today.
- **The atlas is the shared truth**: builds are architected on the live
  render, verified on it, and owe it art when they change its
  vocabulary. If it isn't on the atlas, it didn't happen.
- **Doctrine lives here**: when a build fights the playbook and wins,
  the playbook changes in the same PR. When it fights and loses, the
  build changes. Silence is the only wrong outcome.
