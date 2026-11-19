# Gig #2 — The Ripper

The Ripper is the butcher's dark sibling, promised since the first gig spec:
**the corpse-in machinery pointed at sapient bodies.** Same deterministic
transaction + LLM voice split, same post/reincarnation integration — but where
the butcher's counterparty is dinner, the Ripper's is *someone*, and that
difference is the entire design. The design was spec'd in #1277/#1278. The
Ripper itself (archetype, blueprint, post, cold room) is 📋 UNBUILT; see
§8 for the order of work.

**Owner ruling, 2026-08-11 (PR #1946), recorded in `BUILDING_PLAYBOOK` §4:
"The Ripper stays parked until the Southside stands."**

**For owner review before any build**: §6 (legality & consequence) and §7
(open questions) are the decisions that shape this gig, and they touch
systems the butcher never had to (crime, forensics, sleeve identity).

The world already points at the gig. The butcher refuses sapient corpses with
"Ripper trade's not mine — take it elsewhere" (`world/butchery.py`
`_refusal_line`). `world/director/disposal.py` keeps stripped chassis in the
yard; those go to the future junkyard salvager, not the Ripper (§2). The
module docstring of `world/director/disposal.py` still calls the chassis "the
obvious feedstock for the Ripper's cold room"; the 2026-09-14 ruling replaces
that.

Ties into `GIG_PROTOTYPE_BUTCHER_SPEC` (the machinery),
`NPC_POSTS_AND_REINCARNATION_SPEC` (posts; and the sleeve economics this gig
weaponizes), `DEATH_AND_SLEEVE_LIFECYCLE_SPEC` (whose corpses these are),
`HEALTH_AND_SUBSTANCE_SYSTEM_SPEC` (organs as real items),
`ANATOMY_AUGMENTS_SPEC` (harvested chrome), and the forensics/crime/dispatch
layer (§6 — what selling a person *costs*).

---

## 0 · Purpose

The butcher proved the loop: bring a body, get paid by what it yields. The
Ripper generalizes it to the bodies that *matter* — human and synthetic
corpses — and in doing so gives the colony three things no other system
provides:

1. **An economy for murder.** Killing a person now produces a *sellable
   asset*. That is dark, on-theme, and mechanically honest — and it finally
   makes body disposal a decision instead of an afterthought.
2. **A secondhand chrome market.** Cyberware is the colony's most valuable
   portable property, and every corpse with an augment is a walking
   inventory. Harvested chrome re-enters the install economy: the surgical
   install path (`install` and `operate`, through `_resolve_install` and its
   siblings in `world/medical/procedures.py`) refits harvested organs and
   augments. The clinic NPC does not: it only fits new chrome from its own
   supply. An NPC doctor fitting a part the patient brings is
   📋 UNBUILT (no issue).
3. **Consequence pressure on the sleeve economy.** Re-sleeving is how death
   is survived; the Ripper is what happens to the *body left behind*. A
   victim who re-clones and later learns their old sleeve was parted out has
   a grudge with a name on it (§6).

## 1 · The character

The Ripper is a back-alley organ broker — the butcher's counterpart with a
surgeon's tools and a fence's ethics. Professionally incurious (the pawn-shop
virtue, sharpened): where a body came from is *aggressively* not their
business. They buy quiet, sell quiet, and their real product is discretion.

- **Location:** owner's call — the future sewer layer (unspecced and
  unbuilt, see `BUILDING_PLAYBOOK` §4) is the natural home (off the street
  grid, behind the phase of respectable commerce), or a back room off
  Hammett's Boot. TBD at build time (§7).
- **Post:** registered like every named NPC (blueprint + fixture + policy).
  Policy lean: **successor** — rippers are street, and a dead ripper's
  successor *inheriting the cold room* is exactly this world. (Counter-lean:
  a ripper of all people might carry sleeve insurance; owner's call.)
- **Archetype:** `ripper` — flat, unhurried, transactional; speaks about
  bodies exclusively as inventory; never asks names, never offers them. The
  few-shot demonstrates `remember` and the restraint `none` (the
  "demonstrate, don't describe" rule in `LLM_GAMEMASTER_SPEC`). The Ripper's
  read on a supplier comes from the engine-owned opinion layer (#2388), not a
  tool call; there is no `feel` tool. The deterministic transaction is never a
  tool.

## 2 · The buy side — corpses in

A mirror of the butcher's `world/butchery.py` `process_corpse` (entered via
`on_receive`), with the guards inverted. The player types:

```
give corpse to ripper
```

The Ripper then works deterministically, in this order:

1. **Species guard.** Accepts `human` and `synthetic_humanoid`. Refuses
   animals ("take the rat to the meat cart") and robots ("scrap's a
   different trade"). Owner, 2026-09-14: robots are robots, not chrome; a
   **junkyard salvager** (future gig) handles them. Other specs had named the
   Ripper as the chassis buyer; that was overturned by this ruling.
2. **Freshness gate.** Decay scales organ viability; past a threshold only
   the chrome is worth anything (chrome doesn't rot).
3. **Appraisal.** Walk `world.medical.removable.harvestable_organs(corpse)`,
   the predicate both harvest doors use (it drops removed organs, severed
   containers and 0-HP organs; on a skeletal body it keeps only bones and
   grafted inorganic parts):
   - **Biological organs:** entries where `is_grafted` is false, priced by
     type; synth organs are priced differently (§3).
   - **Chrome:** entries where `is_grafted` is true, priced by its prototype
     value (harvested chrome carries `value`, `brand` and `prototype_key`,
     #3490). Undamaged chrome is the payday; a corpse can be worth more than
     its killer's bounty.
4. **Payout** from a finite till (the post's, per the standing rule).
5. **Stock:** organs and chrome enter the cold room's inventory (§4).
6. **The corpse** is consumed (§5 decides what "consumed" means
   forensically).

Then the Ripper's LLM voice speaks the transaction and remembers the
supplier.

Pre-harvested corpses are worth less automatically (the snapshot already
tracks `removed_organs`) — a clinic-stripped body is mostly chrome and
disappointment. **Head trauma discounts the brain; the brain is the organ
that pays worst anyway** (nobody trustworthy is buying those).

## 3 · Valuation

- **Biological organs (human):** heart > liver > kidneys/lungs > eyes/ears >
  the rest. Condition-scaled by organ HP × freshness, the butcher's exact
  math on a darker menu.
- **Synthetic organs:** durable, non-rotting (species spec) — lower per-unit
  price (grown, not scarce) but decay-immune, so a week-old synth corpse
  still pays. A deliberate asymmetry: synths are worth *killing carefully*
  and worth *finding late*. The code does not exempt synth tissue: the
  corpse's decay factor (`Corpse.get_decay_factor`) is time-based for every
  species, `harvestable_organs` drops non-bone synth organs once the body is
  skeletal, and `_configure_harvested_item` stamps `harvested_at` on synth
  organs like any organic one. The freshness gate must special-case
  `synthetic_humanoid` for this asymmetry to hold. 📋 UNBUILT (no issue)
- **Chrome:** priced from the prototype's value with a used-goods haircut.
  The Ripper pays a fraction; sells at margin (§4). High-end chrome (cyber
  hearts, targeting processors) is the whale trade.

## 4 · The sell side — the cold room

A `ShopContainer` post fixture (the FoodCart pattern, colder):

- **Used chrome**, buyable and installable by a surgeon — the surgical
  install path (`_resolve_install_augment`) takes harvested augments; the
  clinic NPC fitting one is 📋 UNBUILT (no issue). Cheaper than new; the
  "risk" texture (failed-install odds, provenance questions) is an open
  question (§7), not assumed.
- **Transplant organs**, sellable to players carrying them to a doctor — the
  donor-organ surgery path exists (`_resolve_install` fits a harvested organ
  when its `compatible_species` matches the patient). This quietly creates
  the *organ courier* job: buy a heart in the dark, walk it to a clinic,
  someone lives.
- Stock is real (limited inventory, fed by what suppliers bring), sales
  credit the till — the closed loop, verbatim from the cart.

## 5 · The third service — disposal

The inverse transaction, and the Ripper's most narratively loaded offer:
**pay the Ripper to make a body disappear.** No payout — a *fee* — and the
corpse is gone: no graveside discovery, no autopsy, no forensic record left
lying in a room. Murder cleanup as a paid service.

- Deterministic: hand over corpse + fee (say the word, e.g. `give corpse…`
  then the fee is quoted flat and paid like a dish order).
- What it destroys is *evidence*: the corpse object and everything the
  forensics layer could have read from it.
- Harvested parts are evidence too: each one carries its source corpse's
  identity signature, apparent UID and dbref (`_configure_harvested_item` in
  `world/medical/procedures.py`), so a part that leaves the cold room still
  traces back to the body.
- What it does NOT destroy (§6): whatever the world already knows —
  witnesses, dispatch records, the victim's own re-sleeved memory.

## 6 · Legality & consequence — the owner-review section

**Rulings recorded 2026-09-14** (from the chrome-removal review): anything
installed can be uninstalled; robots go to the junkyard salvager, not the
Ripper; chrome doesn't rot (organic organs get a harvest timestamp,
`db.harvested_at` on every organic harvest, #3498; the freshness gate that
reads it and the refrigeration component wait on the balance pass); chrome
stays on the corpse and you re-sleeve as a flesh bag. The consequence stack
below is not decided (§7).

This is where the Ripper differs from the butcher in kind, not degree.
Selling a rat is commerce; selling a person should have *weight*. Proposed
consequence stack, cheapest first — each independently shippable:

1. **Witness pressure.** The witness → dispatch → BOLO funnel
   (`world/director/crime.py` `report_crime`) exists, but carrying a corpse
   is not a crime type and raises nothing. This needs a new crime type and a
   hook on the carry or give act. 📋 UNBUILT (no issue)
2. **The re-sleeved victim knows *something* (cheap, delicious).** Their old
   sleeve never surfaced. For a PC that's pure roleplay fuel; for a named NPC
   (post keeper), the §P3 memory snapshot means their re-sleeve can carry a
   seeded grudge — "someone sold my body" — against whoever the post's
   snapshot last saw them with. The grudge rides the engine-owned
   opinion/valence layer (#2388), not a tool call.
   `NPC_POSTS_AND_REINCARNATION_SPEC` §6 (Witnessed murder) and §5 Unbuilt
   (Succession as WSIS fodder) still describe it as a seeded `feel`. Lean: v2, not v1.
3. **Sleeve-UID traceability (the real teeth, later).** Corpses carry
   identity (`sleeve_uid`, recognition surfaces). A sold PC corpse could
   leave a *trace* in the Ripper's ledger — a hackable/discoverable record
   (decking hook!) tying killer → corpse → sale. This is the WSIS-tier
   version; spec it when the net exists.
4. **Constabulary heat on the fixture (ambient).** The cold room is a known
   shadow — periodic dispatch interest, a reason the Ripper's prices carry a
   discretion premium.

## 7 · Open questions (owner)

- **The owner's core call: how *illegal* is this, today?** Options: (a)
  fully shadow — no mechanical enforcement yet, consequence is
  witness-driven only (lean: this, for v1 — the systems that make it truly
  dangerous arrive with factions/decking); (b) actively policed — selling
  triggers BOLO machinery now. The spec is written so (a) upgrades to (b)
  without rework. §6's consequence stack as a whole is owner-pending.
- **Where does the Ripper live?** Sewers (fits, pending your build) vs. a
  Boot back room (live today). This gates the build start more than any
  code.
- **Post policy:** successor (lean) vs. sleeve insurance (§1).
- **Does the Ripper buy PC corpses at a premium or a discount?** Premium
  says "murder pays"; discount says "hot goods are cheap." (Lean: discount —
  professionally incurious ≠ stupid.)
- **Used-chrome install risk:** flat discount only, or a failure/rejection
  texture on secondhand augments? (Lean: flat discount v1; risk texture is
  a medical-system feature, spec it there.)
- **Disposal fee scale:** flat, or scaled to how *hot* the corpse is (a PC
  sleeve costs more to vanish than a colonist NPC)? (Lean: scaled, crudely —
  PC sleeves ×3.)
- **Does she deal with the clinics?** A quiet supply line (clinic buys
  organs, asks nothing) knits the gigs into an economy — or is that a
  bridge too respectable? (Lean: yes, as flavor first — Marta's AutoDoc
  doesn't ask where the kidney came from.)
- **Name & face:** owner's call, or I draft on build approval.
- **Provenance of sold parts:** should a part sold by the Ripper still
  trace back to its source corpse, or does the cold room scrub that
  provenance?

## 8 · Phasing

Every phase is 📋 UNBUILT, and the whole gig is parked until the Southside
stands (ruling above).

1. **§R1 — Buy side.** The ripper NPC + cold-room post + corpse appraisal
   (organs + chrome) + payout. The Ripper works as a gig from day one:
   corpses become money. Witness pressure needs the corpse-carrying crime
   hook (§6.1); it is not free.
2. **§R2 — Sell side.** Chrome + organs as limited stock; the courier trade;
   till loop closed. (Mirrors the cart's sell-side build exactly.)
3. **§R3 — Disposal.** The fee service + evidence destruction.
4. **Later:** re-sleeve grudge seeding (§6.2), ledger traceability (§6.3,
   post-decking), gig-asks ("bring me a fresh synth liver — don't ask"),
   clinic supply lines.

## Related documents

`GIG_PROTOTYPE_BUTCHER_SPEC`, `NPC_POSTS_AND_REINCARNATION_SPEC`,
`DEATH_AND_SLEEVE_LIFECYCLE_SPEC`, `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC`,
`ANATOMY_AUGMENTS_SPEC`, `LLM_GAMEMASTER_SPEC`, `BUILDING_PLAYBOOK` §4.
