import json, collections
SP="/private/tmp/claude-502/-Users-rocket/9c546aa0-768b-4c91-992e-d7060f43d859/scratchpad"
city=json.load(open(f"{SP}/city.json"))
blocks=json.load(open(f"{SP}/scaffold_blocks.json"))["blocks"]
z0={tuple(c["xyz"][:2]):c for c in city["cells"] if c["xyz"][2]==0}
def keyat(p): return z0.get(tuple(p),{}).get("key","")

BAR=["The Ballast","The Filament","The Blue Hour","The Kettle Drum","The Dry Dock","The Furrow","The Slow Orbit","The Tin Lantern"]
STORE=["Okafor Dry Goods","Marsh & Sons Hardware","Quill Stationery & Sundries","Danner Provisions","Ferro Parts & Salvage","Calder Chandlery","Iyer Spice & Tin","Barlow Secondhand","Nix Optics","Yun Noodle Counter"]
APT=["The Calder Arms","Ostrov House","Marsh Rows","Quill Court","Danner Stacks","The Voss","Halloran House","Petrova Terrace","The Brandt","Solano Rows","Krebs Court","The Marek","Doyle House","Tanaka Rows","The Ash Building","Ruiz Terrace","Barlow Court","The Okafor","Nix House","Iyer Rows"]
THIRD=["Tolliver Baths — bathhouse","The Listening Room — radio cafe","Marek's Gymnasium — boxing","The Glasshouse Commons — greenhouse","The Long Game — game hall","The Pot — communal kitchen","The Pigeon Exchange — lofts","The Records Hall — archive","The Open Hand — preacher's hall","Ninth Loaf — oven commons"]
WORK=["Ferro Pattern Works","The Coil Shed","Union Bench Co-op","Volta Cable Yard","Krebs Foundry Row","The Gasket House","Spillane Pipeworks","Riveter's Toolhall"]
TOWER=["Voss Spire","The Calder Stack","Ferro House","Ostrov Vertical","The Brandt Needle"]
CORP=["Meridian Assurance Hall","The Ledger House","Gateway & Colonial Trust","The Registry Annex"]
FREIGHT=["Longhaul Yard Office","Slowboat Bond Store","The Manifest House","Pad Row Bunkhouse"]
existing_names={ (z0[p]["key"].split(" - ")[0]) for p in z0 }

ZP={"bank":["bar","store","third","apartments","store","bar"],
    "bankS":["store","bar","apartments","third","store"],
    "oldtown":["apartments","store","apartments","third","workshop"],
    "fringe":["apartments","third","apartments","store"],
    "works":["workshop","workshop","store","third"],
    "podium":["apartments","store","apartments"],
    "high":["apartments","corporate","apartments"],
    "spire":["tower"],"crown":["anchor"],
    "padtown":["freight","freight","store"]}
POOL={"bar":BAR,"store":STORE,"apartments":APT,"third":THIRD,"workshop":WORK,
      "tower":TOWER,"corporate":CORP,"freight":FREIGHT}
used=collections.Counter(); zct=collections.Counter()
DIST={"bank":"Tolliver Bank","bankS":"Maxwell Bank","oldtown":"Old Town (south)","fringe":"Braddock Fringe",
      "works":"The Works (Volta/Pessoa)","podium":"Podium Band (north)","high":"High Band (north)",
      "spire":"Spire Row","crown":"The Crown","padtown":"Pad Quarter (flight cap)","mesa":"Mesas (existing)",
      "civic":"Civic","pad":"Civic","dome":"Civic"}
out=collections.defaultdict(list)
for bl in blocks:
    tiles=[tuple(t) for t in bl["tiles"]]
    zone=bl["zone"].split("+")[0].split("*")[0]
    climb="*climb" in bl["zone"]; step="+step" in bl["zone"]
    xs=[t[0] for t in tiles]; ys=[t[1] for t in tiles]
    foot=f"x{min(xs)}..{max(xs)} y{min(ys)}..{max(ys)} ({len(tiles)})"
    exist=sorted({keyat(t).split(" - ")[0] for t in tiles if keyat(t)})
    if zone in ("mesa","civic","pad","dome") or (exist and zone not in ("crown","spire")):
        name="KEEP: "+"; ".join(exist[:3]) if exist else "KEEP"
        prog="existing"
    elif zone=="crown":
        name="THE ANCHOR (16→18) — identity: owner call"; prog="anchor"
    else:
        prog=ZP.get(zone,["apartments"])[zct[zone]%len(ZP.get(zone,["apartments"]))]; zct[zone]+=1
        pool=POOL[prog]; name=pool[used[prog]%len(pool)]; used[prog]+=1
        if name.split(" — ")[0] in existing_names: name="New "+name
    furn=[]
    furn.append("fire escape (alley)")
    if step or climb: furn.append("water tower / ladder +2")
    roof=f"{name.split(' — ')[0]} Rooftop" if prog!="existing" else (exist[0]+" Rooftop" if exist else "Rooftop")
    out[DIST.get(zone,zone)].append({
        "name":name,"prog":prog,"foot":foot,"z":bl["datum"],
        "roof":roof + (f" (strip ×{max(1,len(tiles)//2)})" if len(tiles)>2 else ""),
        "furn":", ".join(furn), "climb":climb})
md=[]
md.append("# City Scaffold — every building, named and placed (DRAFT)\n")
md.append("> **Status:** 📋 DRAFT FOR OWNER VETO (2026-08-05). Generated against")
md.append("> the Roof Plan v2 (flat 1:1 datums per building, stagger between,")
md.append("> the Long Climb street→18, the 14-18 high town with skywalks).")
md.append("> Every name, program, and height below is a proposal — strike,")
md.append("> rename, or reassign per line; the generator re-derives in seconds.")
md.append("> Existing buildings are marked KEEP. Coordinates are grid (x,y),")
md.append("> z = roof height in stories. Furniture per the template library §2.5.\n")
md.append("**Method**: buildings are 2×3-max chunks of the buildable tiles;")
md.append("each holds ONE flat roof datum (bi-directional 1:1 fabric); ±1")
md.append("between neighbors = jumps; 2-3 = furniture; >3 = deliberate breaks")
md.append("(Pad Quarter flight cap, the dome, the Terraformer, the channel).\n")
tot=0
for dist in ["The Crown","Spire Row","High Band (north)","Podium Band (north)","Tolliver Bank",
             "Pad Quarter (flight cap)","Maxwell Bank","The Works (Volta/Pessoa)","Old Town (south)",
             "Braddock Fringe","Mesas (existing)","Civic"]:
    rows=out.get(dist)
    if not rows: continue
    md.append(f"## {dist}\n")
    md.append("| Building | Program | Footprint | Roof z | Roof room | Furniture |")
    md.append("|---|---|---|---|---|---|")
    for r in sorted(rows,key=lambda r:-r["z"]):
        nm=("🧗 " if r["climb"] else "")+r["name"]
        md.append(f"| {nm} | {r['prog']} | {r['foot']} | {r['z']} | {r['roof']} | {r['furn']} |")
        tot+=1
    md.append("")
md.append(f"\n**{tot} buildings** · 🧗 = a Long Climb station · roof rooms ship WITH the building (archipelago pattern: strips + air cells + fall links + edges at own height).\n")
open(f"{SP}/CITY_SCAFFOLD.md","w").write("\n".join(md))
print(f"manifest: {tot} buildings written")
