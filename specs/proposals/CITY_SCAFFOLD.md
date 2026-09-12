# City Scaffold — every building, named and placed (DRAFT)

> **Status:** 📋 DRAFT FOR OWNER VETO (2026-08-05). Generated against
> the Roof Plan v2 (flat 1:1 datums per building, stagger between,
> the Long Climb street→18, the 14-18 high town with skywalks).
> Every name, program, and height below is a proposal — strike,
> rename, or reassign per line; the generator re-derives in seconds.
> Existing buildings are marked KEEP. Coordinates are grid (x,y),
> z = roof height in stories. Furniture per the template library §2.5.
>
> **Doc-review note (2026-09-11)** — three corrections to the banner
> above. None of them touches the design; the proposal itself is still
> unbuilt, which is what it claims to be.
>
> 1. **It was generated against the Roof Plan v3, not v2.**
>    `scripts/planning/scaffold.py` titles its own plate "THE ROOF PLAN
>    v3", `scripts/planning/README.md` calls it v3 (v1 is the superseded
>    `roofplan.py`; no v2 exists in the repo), `PARKOUR_TEMPLATE_LIBRARY.md`
>    §1.5 cites "owner law, Roof Plan v3", and the issue that delivered
>    this document (#1681) says v3. The wrong number is hardcoded in
>    `manifest.py`, so a re-run reprints it.
> 2. **KEEP is a 2026-08-05 map snapshot, already overtaken.** The Queen
>    of Cups was raised to a z12 roof (build 018, #1774) and is listed
>    here at 6; The Halcyon (builds 014/016/017 — #1766/#1770/#1772) now
>    stands as a z12 liner hull on and beside Kaspar Pawn & Salvage, over
>    tiles this table still offers as a fresh z2 workshop (x-8..-7
>    y-15..-13, which contains the sun-deck corner at -7,-15); and the
>    Greenhaus verticals and cisterns (builds 055–065) appear nowhere.
>    Read KEEP as "existed on 2026-08-05", and re-export before using it.
> 3. **`Roof z` on a KEEP row is generated, not as-built.** Outside the
>    mesa/pad/dome cases the generator synthesizes a datum from its zone
>    formula without consulting the building's real height, so these rows
>    silently propose raising built roofs: Suds & Bubbles Laundromat is
>    listed at 4 although `PARKOUR_TEMPLATE_LIBRARY.md` §1.5 makes its z1
>    rooftop the datum the whole roof city starts from — and the built
>    Laundromat→Market crossing over Braddock rides it — while Hammett's
>    Boot, one building, appears at 6, 4, 4 and 2 across its four chunks.
>
> Re-deriving is also not the one-command job the banner implies: both
> generators read `city.json` / `scaffold_blocks.json` from a hardcoded
> session scratchpad path that no longer exists (the committed blocks
> file sits in `scripts/planning/`, where nothing reads it), so a fresh
> `export_map()` dump and a path fix come first.

**Method**: buildings are 2×3-max chunks of the buildable tiles;
each holds ONE flat roof datum (bi-directional 1:1 fabric); ±1
between neighbors = jumps; 2-3 = furniture; >3 = deliberate breaks
(Pad Quarter flight cap, the dome, the Terraformer, the channel).

## The Crown

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| THE ANCHOR (16→18) — identity: owner call | anchor | x10..11 y9..11 (6) | 16 | THE ANCHOR (16→18) Rooftop (strip ×3) | fire escape (alley) |
| THE ANCHOR (16→18) — identity: owner call | anchor | x9..9 y9..11 (3) | 14 | THE ANCHOR (16→18) Rooftop (strip ×1) | fire escape (alley) |

## Spire Row

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| Voss Spire | tower | x5..5 y9..11 (3) | 14 | Voss Spire Rooftop (strip ×1) | fire escape (alley) |
| The Calder Stack | tower | x6..7 y9..11 (6) | 14 | The Calder Stack Rooftop (strip ×3) | fire escape (alley) |

## High Band (north)

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| Barlow Court | apartments | x-3..-3 y9..11 (3) | 11 | Barlow Court Rooftop (strip ×1) | fire escape (alley) |
| KEEP: Thawn-Harrison Cryogenics | existing | x1..1 y9..11 (3) | 8 | Thawn-Harrison Cryogenics Rooftop (strip ×1) | fire escape (alley) |
| 🧗 KEEP: Thawn-Harrison Cryogenics | existing | x2..3 y9..11 (6) | 8 | Thawn-Harrison Cryogenics Rooftop (strip ×3) | fire escape (alley), water tower / ladder +2 |
| Doyle House | apartments | x-7..-7 y9..11 (3) | 6 | Doyle House Rooftop (strip ×1) | fire escape (alley) |
| 🧗 Meridian Assurance Hall | corporate | x-6..-5 y9..11 (6) | 6 | Meridian Assurance Hall Rooftop (strip ×3) | fire escape (alley), water tower / ladder +2 |
| 🧗 The Okafor | apartments | x-2..-1 y9..11 (6) | 6 | The Okafor Rooftop (strip ×3) | fire escape (alley), water tower / ladder +2 |

## Podium Band (north)

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| Okafor Dry Goods | store | x2..3 y6..7 (4) | 8 | Okafor Dry Goods Rooftop (strip ×2) | fire escape (alley) |
| Halloran House | apartments | x6..7 y6..7 (4) | 8 | Halloran House Rooftop (strip ×2) | fire escape (alley) |
| The Brandt | apartments | x10..11 y6..7 (4) | 8 | The Brandt Rooftop (strip ×2) | fire escape (alley) |
| Okafor Dry Goods | store | x-10..-9 y6..7 (4) | 6 | Okafor Dry Goods Rooftop (strip ×2) | fire escape (alley) |
| Krebs Court | apartments | x-7..-7 y6..7 (2) | 6 | Krebs Court Rooftop | fire escape (alley) |
| The Marek | apartments | x-6..-5 y6..7 (4) | 6 | The Marek Rooftop (strip ×2) | fire escape (alley) |
| Danner Provisions | store | x-3..-3 y6..7 (2) | 6 | Danner Provisions Rooftop | fire escape (alley) |
| Ruiz Terrace | apartments | x-2..-1 y6..7 (4) | 6 | Ruiz Terrace Rooftop (strip ×2) | fire escape (alley) |
| Danner Stacks | apartments | x1..1 y6..7 (2) | 6 | Danner Stacks Rooftop | fire escape (alley) |
| The Voss | apartments | x5..5 y6..7 (2) | 6 | The Voss Rooftop | fire escape (alley) |
| Quill Stationery & Sundries | store | x9..9 y6..7 (2) | 6 | Quill Stationery & Sundries Rooftop | fire escape (alley) |
| Solano Rows | apartments | x-11..-11 y6..7 (2) | 3 | Solano Rows Rooftop | fire escape (alley) |

## Tolliver Bank

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| Yun Noodle Counter | store | x1..1 y5..5 (1) | 4 | Yun Noodle Counter Rooftop | fire escape (alley) |
| The Dry Dock | bar | x2..3 y5..5 (2) | 3 | The Dry Dock Rooftop | fire escape (alley) |
| The Furrow | bar | x5..5 y5..5 (1) | 3 | The Furrow Rooftop | fire escape (alley) |
| Marsh & Sons Hardware | store | x6..7 y5..5 (2) | 3 | Marsh & Sons Hardware Rooftop | fire escape (alley) |
| The Long Game — game hall | third | x9..9 y5..5 (1) | 3 | The Long Game Rooftop | fire escape (alley) |
| Petrova Terrace | apartments | x10..11 y5..5 (2) | 3 | Petrova Terrace Rooftop | fire escape (alley) |
| The Blue Hour | bar | x-11..-11 y5..5 (1) | 2 | The Blue Hour Rooftop | fire escape (alley) |
| KEEP: Gaia's Treasures | existing | x-10..-9 y5..5 (2) | 2 | Gaia's Treasures Rooftop | fire escape (alley) |
| Marsh & Sons Hardware | store | x-7..-7 y5..5 (1) | 2 | Marsh & Sons Hardware Rooftop | fire escape (alley) |
| 🧗 The Open Hand — preacher's hall | third | x-6..-5 y5..5 (2) | 2 | The Open Hand Rooftop | fire escape (alley), water tower / ladder +2 |
| The Ash Building | apartments | x-3..-3 y5..5 (1) | 2 | The Ash Building Rooftop | fire escape (alley) |

## Pad Quarter (flight cap)

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| Longhaul Yard Office | freight | x-11..-11 y9..11 (3) | 3 | Longhaul Yard Office Rooftop (strip ×1) | fire escape (alley) |

## Maxwell Bank

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| Barlow Secondhand | store | x-11..-11 y-6..-5 (2) | 4 | Barlow Secondhand Rooftop | fire escape (alley) |
| The Filament | bar | x-6..-5 y-6..-5 (4) | 4 | The Filament Rooftop (strip ×2) | fire escape (alley) |
| The Kettle Drum | bar | x1..1 y-6..-5 (2) | 4 | The Kettle Drum Rooftop | fire escape (alley) |
| KEEP: The Hub and Howl | existing | x-11..-11 y-7..-7 (1) | 3 | The Hub and Howl Rooftop | fire escape (alley) |
| The Brandt | apartments | x-10..-9 y-6..-5 (4) | 3 | The Brandt Rooftop (strip ×2) | fire escape (alley) |
| The Records Hall — archive | third | x-8..-7 y-7..-7 (2) | 3 | The Records Hall Rooftop | fire escape (alley) |
| Ninth Loaf — oven commons | third | x-3..-3 y-6..-5 (2) | 3 | Ninth Loaf Rooftop | fire escape (alley) |
| Quill Stationery & Sundries | store | x-2..-1 y-7..-7 (2) | 3 | Quill Stationery & Sundries Rooftop | fire escape (alley) |
| Nix Optics | store | x1..1 y-7..-7 (1) | 3 | Nix Optics Rooftop | fire escape (alley) |
| The Glasshouse Commons — greenhouse | third | x2..3 y-6..-5 (4) | 3 | The Glasshouse Commons Rooftop (strip ×2) | fire escape (alley) |
| The Ballast | bar | x-10..-9 y-7..-7 (2) | 2 | The Ballast Rooftop | fire escape (alley) |
| Nix Optics | store | x-8..-7 y-6..-5 (3) | 2 | Nix Optics Rooftop (strip ×1) | fire escape (alley) |
| Yun Noodle Counter | store | x-6..-5 y-7..-7 (2) | 2 | Yun Noodle Counter Rooftop | fire escape (alley) |
| Tanaka Rows | apartments | x-3..-3 y-7..-7 (1) | 2 | Tanaka Rows Rooftop | fire escape (alley) |
| KEEP: Maxwell Medical Clinic | existing | x-2..-1 y-6..-5 (4) | 2 | Maxwell Medical Clinic Rooftop (strip ×2) | fire escape (alley) |
| Quill Court | apartments | x2..3 y-7..-7 (2) | 2 | Quill Court Rooftop | fire escape (alley) |

## The Works (Volta/Pessoa)

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| Union Bench Co-op | workshop | x-11..-11 y-9..-9 (1) | 5 | Union Bench Co-op Rooftop | fire escape (alley) |
| Volta Cable Yard | workshop | x-8..-7 y-11..-10 (4) | 5 | Volta Cable Yard Rooftop (strip ×2) | fire escape (alley) |
| The Pot — communal kitchen | third | x-6..-5 y-9..-9 (2) | 5 | The Pot Rooftop | fire escape (alley) |
| Iyer Spice & Tin | store | x-2..-1 y-11..-10 (4) | 5 | Iyer Spice & Tin Rooftop (strip ×2) | fire escape (alley), water tower / ladder +2 |
| Union Bench Co-op | workshop | x1..1 y-9..-9 (1) | 5 | Union Bench Co-op Rooftop | fire escape (alley) |
| Volta Cable Yard | workshop | x4..4 y-11..-10 (2) | 5 | Volta Cable Yard Rooftop | fire escape (alley) |
| The Coil Shed | workshop | x-11..-11 y-11..-10 (2) | 4 | The Coil Shed Rooftop | fire escape (alley) |
| The Long Game — game hall | third | x-10..-9 y-9..-9 (2) | 4 | The Long Game Rooftop | fire escape (alley) |
| Calder Chandlery | store | x-6..-5 y-11..-10 (4) | 4 | Calder Chandlery Rooftop (strip ×2) | fire escape (alley) |
| The Gasket House | workshop | x-4..-3 y-11..-10 (4) | 4 | The Gasket House Rooftop (strip ×2) | fire escape (alley), water tower / ladder +2 |
| Spillane Pipeworks | workshop | x-4..-3 y-9..-9 (2) | 4 | Spillane Pipeworks Rooftop | fire escape (alley) |
| The Coil Shed | workshop | x1..1 y-11..-10 (2) | 4 | The Coil Shed Rooftop | fire escape (alley) |
| Marek's Gymnasium — boxing | third | x2..3 y-9..-9 (2) | 4 | Marek's Gymnasium Rooftop | fire escape (alley) |
| Ferro Parts & Salvage | store | x-10..-9 y-11..-10 (4) | 3 | Ferro Parts & Salvage Rooftop (strip ×2) | fire escape (alley) |
| Krebs Foundry Row | workshop | x-8..-7 y-9..-9 (2) | 3 | Krebs Foundry Row Rooftop | fire escape (alley) |
| The Pigeon Exchange — lofts | third | x-2..-1 y-9..-9 (2) | 3 | The Pigeon Exchange Rooftop | fire escape (alley) |
| Barlow Secondhand | store | x2..3 y-11..-10 (4) | 3 | Barlow Secondhand Rooftop (strip ×2) | fire escape (alley) |
| Krebs Foundry Row | workshop | x4..4 y-9..-9 (1) | 3 | Krebs Foundry Row Rooftop | fire escape (alley) |

## Old Town (south)

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| Halloran House | apartments | x-8..-7 y-19..-19 (2) | 6 | Halloran House Rooftop | fire escape (alley), water tower / ladder +2 |
| KEEP: Hammett's Boot | existing | x-8..-7 y-18..-17 (4) | 6 | Hammett's Boot Rooftop (strip ×2) | fire escape (alley), water tower / ladder +2 |
| Petrova Terrace | apartments | x-11..-11 y-15..-13 (3) | 6 | Petrova Terrace Rooftop (strip ×1) | fire escape (alley), water tower / ladder +2 |
| The Glasshouse Commons — greenhouse | third | x-10..-9 y-15..-13 (6) | 6 | The Glasshouse Commons Rooftop (strip ×3) | fire escape (alley), water tower / ladder +2 |
| KEEP: Hammett's Boot | existing | x-6..-5 y-18..-17 (4) | 4 | Hammett's Boot Rooftop (strip ×2) | fire escape (alley) |
| KEEP: Hammett's Boot; The Last Shift | existing | x-4..-3 y-18..-17 (4) | 4 | Hammett's Boot Rooftop (strip ×2) | fire escape (alley), water tower / ladder +2 |
| KEEP: Ramirez Provisions & Sundries | existing | x-2..-1 y-19..-19 (2) | 4 | Ramirez Provisions & Sundries Rooftop | fire escape (alley) |
| KEEP: Kaspar Urgent Care | existing | x-2..-1 y-18..-17 (4) | 4 | Kaspar Urgent Care Rooftop (strip ×2) | fire escape (alley), water tower / ladder +2 |
| KEEP: Kaspar Pawn & Salvage | existing | x-6..-5 y-15..-13 (6) | 4 | Kaspar Pawn & Salvage Rooftop (strip ×3) | fire escape (alley), water tower / ladder +2 |
| Iyer Rows | apartments | x4..5 y-19..-19 (2) | 4 | Iyer Rows Rooftop | fire escape (alley) |
| KEEP: Shipbreaker Alley | existing | x6..7 y-18..-17 (4) | 4 | Shipbreaker Alley Rooftop (strip ×2) | fire escape (alley) |
| The Calder Arms | apartments | x10..11 y-19..-19 (2) | 4 | The Calder Arms Rooftop | fire escape (alley) |
| Ostrov House | apartments | x1..1 y-15..-13 (3) | 4 | Ostrov House Rooftop (strip ×1) | fire escape (alley), water tower / ladder +2 |
| The Listening Room — radio cafe | third | x2..3 y-15..-13 (6) | 4 | The Listening Room Rooftop (strip ×3) | fire escape (alley) |
| Danner Provisions | store | x-6..-5 y-19..-19 (2) | 3 | Danner Provisions Rooftop | fire escape (alley) |
| Nix House | apartments | x1..1 y-19..-19 (1) | 3 | Nix House Rooftop | fire escape (alley) |
| KEEP: Shipbreaker Alley | existing | x6..7 y-19..-19 (2) | 3 | Shipbreaker Alley Rooftop | fire escape (alley) |
| Riveter's Toolhall | workshop | x8..9 y-18..-17 (4) | 3 | Riveter's Toolhall Rooftop (strip ×2) | fire escape (alley) |
| Marsh Rows | apartments | x6..7 y-15..-13 (6) | 3 | Marsh Rows Rooftop (strip ×3) | fire escape (alley) |
| KEEP: Hammett's Boot | existing | x-4..-3 y-19..-19 (2) | 2 | Hammett's Boot Rooftop | fire escape (alley) |
| Ferro Pattern Works | workshop | x-8..-7 y-15..-13 (6) | 2 | Ferro Pattern Works Rooftop (strip ×3) | fire escape (alley) |
| Ferro Parts & Salvage | store | x2..3 y-19..-19 (2) | 2 | Ferro Parts & Salvage Rooftop | fire escape (alley) |
| KEEP: Shipbreaker Alley | existing | x4..5 y-18..-17 (4) | 2 | Shipbreaker Alley Rooftop (strip ×2) | fire escape (alley) |
| Tolliver Baths — bathhouse | third | x8..9 y-19..-19 (2) | 2 | Tolliver Baths Rooftop | fire escape (alley) |
| Calder Chandlery | store | x10..11 y-18..-17 (4) | 2 | Calder Chandlery Rooftop (strip ×2) | fire escape (alley) |
| Ferro Pattern Works | workshop | x4..5 y-15..-13 (6) | 2 | Ferro Pattern Works Rooftop (strip ×3) | fire escape (alley) |
| Iyer Spice & Tin | store | x10..11 y-15..-13 (6) | 2 | Iyer Spice & Tin Rooftop (strip ×3) | fire escape (alley) |

## Braddock Fringe

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| The Calder Arms | apartments | x-12..-11 y-21..-21 (2) | 6 | The Calder Arms Rooftop | fire escape (alley), water tower / ladder +2 |
| Tolliver Baths — bathhouse | third | x-10..-9 y-21..-21 (2) | 6 | Tolliver Baths Rooftop | fire escape (alley), water tower / ladder +2 |
| Ostrov House | apartments | x-8..-7 y-21..-21 (2) | 4 | Ostrov House Rooftop | fire escape (alley) |
| KEEP: Suds & Bubbles Laundromat | existing | x-2..-1 y-21..-21 (2) | 4 | Suds & Bubbles Laundromat Rooftop | fire escape (alley) |
| Marsh & Sons Hardware | store | x4..5 y-21..-21 (2) | 4 | Marsh & Sons Hardware Rooftop | fire escape (alley) |
| The Voss | apartments | x10..11 y-21..-21 (2) | 4 | The Voss Rooftop | fire escape (alley) |
| Marsh Rows | apartments | x-4..-3 y-21..-21 (2) | 3 | Marsh Rows Rooftop | fire escape (alley) |
| Quill Court | apartments | x2..3 y-21..-21 (2) | 3 | Quill Court Rooftop | fire escape (alley) |
| Marek's Gymnasium — boxing | third | x8..9 y-21..-21 (2) | 3 | Marek's Gymnasium Rooftop | fire escape (alley) |
| Okafor Dry Goods | store | x-6..-5 y-21..-21 (2) | 2 | Okafor Dry Goods Rooftop | fire escape (alley) |
| The Listening Room — radio cafe | third | x0..1 y-21..-21 (2) | 2 | The Listening Room Rooftop | fire escape (alley) |
| Danner Stacks | apartments | x6..7 y-21..-21 (2) | 2 | Danner Stacks Rooftop | fire escape (alley) |
| Quill Stationery & Sundries | store | x12..12 y-21..-21 (1) | 2 | Quill Stationery & Sundries Rooftop | fire escape (alley) |

## Mesas (existing)

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| KEEP | existing | x-11..-11 y-19..-19 (1) | 8 | Rooftop | fire escape (alley) |
| KEEP: Cinder & Leaf | existing | x-10..-9 y-19..-19 (2) | 8 | Cinder & Leaf Rooftop | fire escape (alley) |
| KEEP: Shuttered Storefront; The Brackett Arms | existing | x-10..-9 y-18..-17 (4) | 8 | Shuttered Storefront Rooftop (strip ×2) | fire escape (alley) |
| KEEP: The Brackett Arms | existing | x-11..-11 y-18..-17 (2) | 6 | The Brackett Arms Rooftop | fire escape (alley) |
| KEEP: R0-01 | existing | x-4..-3 y-15..-13 (6) | 6 | R0-01 Rooftop (strip ×3) | fire escape (alley) |
| KEEP: Queen of Cups; R0-05 | existing | x-2..-1 y-15..-13 (6) | 6 | Queen of Cups Rooftop (strip ×3) | fire escape (alley) |

## Civic

| Building | Program | Footprint | Roof z | Roof room | Furniture |
|---|---|---|---|---|---|
| KEEP: Colonial Armory | existing | x-2..-1 y5..5 (2) | 3 | Colonial Armory Rooftop | fire escape (alley) |
| KEEP: Colonial Constabulary Elevator Car; Colonial Constabulary Entrance Hall; Colonial Constabulary Lobby | existing | x8..9 y-15..-13 (6) | 3 | Colonial Constabulary Elevator Car Rooftop (strip ×3) | fire escape (alley) |
| KEEP: Colonial Landing Pad | existing | x-10..-9 y9..11 (6) | 1 | Colonial Landing Pad Rooftop (strip ×3) | fire escape (alley) |
| KEEP: Pre-Fab Agridome | existing | x1..1 y-18..-17 (2) | 1 | Pre-Fab Agridome Rooftop | fire escape (alley) |
| KEEP: Pre-Fab Agridome | existing | x2..3 y-18..-17 (4) | 1 | Pre-Fab Agridome Rooftop (strip ×2) | fire escape (alley) |


**119 buildings** · 🧗 = a Long Climb station · roof rooms ship WITH the building (archipelago pattern: strips + air cells + fall links + edges at own height).

> **Doc-review note (2026-09-11)** — three things this footer leaves
> out, all of them generator artifacts rather than design decisions.
>
> - **The Long Climb is not continuous in the table above.** The
>   generator aims at street→2→4→6→8→8→14→16→18, but its z4 station falls
>   on a street cell and so has no building and no row; the z8 station at
>   x-2..-1 y9..11 was forced to 8 by the climb pass and then pulled back
>   to 6 by the crossing-equalization pass that runs after it (its zone
>   records this as `high*climb+eq+eq` in `scaffold_blocks.json`), which
>   is why The Okafor is listed at 6; and the remaining 8→14 hop from
>   Thawn-Harrison (x2..3) to Voss Spire (x5..5) crosses the street at x4
>   between unequal roofs, which the 1:1-crossings-only owner law this
>   plan is built on forbids. The climb needs re-deriving before it can
>   be built to.
> - **🧗 marks 4 of the 7 stations.** Every marker present is a station,
>   but the tag is suppressed on crown and spire blocks, so the top two
>   rungs (Voss Spire z14, THE ANCHOR z16) carry no marker, and the
>   vanished z4 rung has no row to mark. The climb cannot be read off
>   the markers.
> - **The names are not distinct, so "every building, named" overstates
>   the title.** The count itself is consistent with the Method above,
>   which defines a building as a chunk — but the 119 rows use only 80
>   distinct labels. Among the 92 newly-named rows, 30 roof-room names
>   collide across 63 of them: three unrelated stores are all "Okafor Dry
>   Goods", three more are all "Marsh & Sons Hardware", and "Quill
>   Stationery & Sundries Rooftop" appears three times — rooms that would
>   ship with identical keys. The name pools cycle modulo their length
>   with no uniqueness pass, so every repeat is an artifact. (Repeats on
>   KEEP rows are different: they are one real building spanning several
>   chunks — Hammett's Boot across four, at 6/4/4/2 — so "each holds ONE
>   flat roof datum" holds per chunk, not per named building.)
