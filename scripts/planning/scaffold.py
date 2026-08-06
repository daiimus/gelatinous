import json, collections
from PIL import Image, ImageDraw, ImageFont
SP="/private/tmp/claude-502/-Users-rocket/9c546aa0-768b-4c91-992e-d7060f43d859/scratchpad"
d=json.load(open(f"{SP}/city.json"))
STREET={"street","bridge","alley"}
z0={tuple(c["xyz"][:2]):c for c in d["cells"] if c["xyz"][2]==0}
cols=collections.defaultdict(int)
for c in d["cells"]:
    if "sky" not in (c.get("flags") or []):
        x,y,z=c["xyz"]; cols[(x,y)]=max(cols[(x,y)],z+1)
def is_street(p): return p in z0 and (z0[p].get("type") or "").lower() in STREET
def keyat(p): return z0[p]["key"] if p in z0 else ""
TERRA={(x,y) for x in range(5,12) for y in range(-11,-4)}
CHAN={(x,y) for x in range(-12,13) for y in range(-3,4)}

tiles=set()
for x in range(-12,13):
    for y in range(-21,13):
        p=(x,y)
        if p in TERRA or p in CHAN or is_street(p): continue
        tiles.add(p)
# blocks: orth components
def comps(nodes):
    seen=set(); out=[]
    for n in sorted(nodes):
        if n in seen: continue
        st=[n]; c=set()
        while st:
            p=st.pop()
            if p in c: continue
            c.add(p); seen.add(p)
            x,y=p
            for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if q in nodes and q not in c: st.append(q)
        out.append(sorted(c))
    return out
raw=comps(tiles)
# split big components into building-scale chunks (<=6 tiles, 2-wide strips)
blocks=[]
for c in raw:
    if len(c)<=6: blocks.append(c); continue
    bych={}
    for (x,y) in c:
        k=(x//2, y//3)
        bych.setdefault(k,[]).append((x,y))
    for k in sorted(bych): blocks.append(sorted(bych[k]))
def centroid(b):
    return (sum(p[0] for p in b)/len(b), sum(p[1] for p in b)/len(b))

# datum per block
CROWN={(x,y) for x in range(8,12) for y in range(9,12)}
SPIRE={(x,y) for x in range(4,8) for y in range(9,12)}
def block_datum(i,b):
    cx,cy=centroid(b)
    keys=" ".join(keyat(p).lower() for p in b)
    hmax=max(cols.get(p,0) for p in b)
    if "landing pad" in keys: return 1,"pad"
    if "agridome" in keys: return 1,"dome"
    if hmax>=7: return hmax,"mesa"          # Brackett
    if hmax==6: return 6,"mesa"             # QoC
    if any(p in CROWN for p in b): return 16,"crown"
    if any(p in SPIRE for p in b): return 14,"spire"
    if "constab" in keys or "armory" in keys: return 3,"civic"
    hb=(i*7)%3-1
    if cy>=4:
        if cx<=-8 and cy>=7: return max(2,3+hb),"padtown"
        if cy<=6: return max(2,3+hb),"bank"
        if cy<=8: return 7+hb,"podium"
        return 10+hb,"high"
    if cy<=-20: return max(2,3+hb),"fringe"
    if cy>=-8:  return max(2,3+hb),"bankS"
    if cy>=-12: return 4+hb,"works"
    return max(2,3+hb),"oldtown"
B=[]
for i,b in enumerate(blocks):
    dat,zone=block_datum(i,b)
    B.append({"i":i,"tiles":b,"datum":dat,"zone":zone})
# mesa steps: any block orth-adjacent to a mesa block gets datum>=mesa-2 (cap 6)
def adjacent(b1,b2):
    s2=set(b2)
    for x,y in b1:
        for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1),(x+2,y),(x-2,y),(x,y+2),(x,y-2)):
            if q in s2: return True
    return False
for bl in B:
    if bl["zone"]=="mesa": continue
    for m in B:
        if m["zone"]=="mesa" and adjacent(bl["tiles"],m["tiles"]):
            bl["datum"]=max(bl["datum"],m["datum"]-2); bl["zone"]+="+step"
# THE LONG CLIMB: force a staircase chain through the north grid (east side, then west along high row)
def block_at(p):
    for bl in B:
        if p in bl["tiles"]: return bl
    return None
CLIMB=[((-6,5),2),((-6,8),4),((-5,10),6),((-2,10),8),((2,10),8),((5,10),14),((10,10),16)]
chain=[]
for p,dat in CLIMB:
    bl=block_at(p)
    if bl and bl["zone"] not in ("crown","spire","mesa"):
        bl["datum"]=dat; bl["zone"]+="*climb"
    if bl: chain.append(bl)
H={}
for bl in B:
    for p in bl["tiles"]: H[p]=bl["datum"]
# links/crossings/furniture
native=[];furn=[];cross=[]
for p,h in H.items():
    x,y=p
    for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
        q=(x+dx,y+dy)
        if q in H:
            dl=abs(h-H[q])
            if dl<=1: native.append((p,q))
            elif dl<=3: furn.append((p,q))
# CROSSINGS ARE 1:1 ONLY (owner law): equal heights, bi-directional, no damage.
# Where connectivity needs a crossing, EQUALIZE the facing buildings (pull the
# higher one down) — greedy, minimal edits, logged.
def bidx(pp):
    for bi,bl in enumerate(B):
        if pp in set(map(tuple,bl["tiles"])): return bi
    return None
tile_block={}
for bi,bl in enumerate(B):
    for t in bl["tiles"]: tile_block[tuple(t)]=bi
cand=[]
for p in z0:
    if not is_street(p): continue
    x,y=p
    for (a,b) in (((x-1,y),(x+1,y)),((x,y-1),(x,y+1))):
        if a in H and b in H and min(H[a],H[b])>=2:
            cand.append((p,a,b))
def rebuild_HL():
    global H,native,furn,cross
    H={}
    for bl in B:
        for t in bl["tiles"]: H[tuple(t)]=bl["datum"]
    native=[];furn=[];cross=[]
    for pp,h in H.items():
        x,y=pp
        for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
            q=(x+dx,y+dy)
            if q in H:
                dl=abs(h-H[q])
                if dl<=1: native.append((pp,q))
                elif dl<=3: furn.append((pp,q))
    for (pp,a,b) in cand:
        if H[a]==H[b] and H[a]>=2: cross.append((pp,a,b))
def islands_count():
    par={}
    def find(u):
        while par.setdefault(u,u)!=u: u=par[u]
        return u
    def uni(u,v): par[find(u)]=find(v)
    for pp in H: par[pp]=pp
    for a,b in native+furn: uni(a,b)
    for _,a,b in cross: uni(a,b)
    return len({find(pp) for pp in H}), par, find
rebuild_HL()
equalized=0
for _ in range(40):
    isl,par,find=islands_count()
    if isl<=4: break
    roots=collections.Counter(find(pp) for pp in H)
    best=None
    for (pp,a,b) in cand:
        if find(a)!=find(b):
            dl=abs(H[a]-H[b])
            if dl==0: continue
            score=(dl, -min(roots[find(a)],roots[find(b)]))
            if best is None or score<best[0]: best=(score,(pp,a,b))
    if best is None: break
    _,(pp,a,b)=best
    lo=min(H[a],H[b])
    hib=tile_block[a] if H[a]>H[b] else tile_block[b]
    B[hib]["datum"]=lo; B[hib]["zone"]+="+eq"
    equalized+=1
    rebuild_HL()
isl,_,_=islands_count()
fcross=[]
print(f"equalized {equalized} buildings for crossings")
parent={}
def find(u):
    while parent.setdefault(u,u)!=u: u=parent[u]
    return u
for p in H: parent[p]=p
def uni(a,b): parent[find(a)]=find(b)
for a,b in native+furn: uni(a,b)
for _,a,b in cross: uni(a,b)
isl=len({find(p) for p in H})
flat=sum(1 for a,b in native if H[a]==H[b])
print(f"buildings {len(B)} tiles {len(H)} | flat joins {flat} | +-1 joins {len(native)-flat} | furniture(touching) {len(furn)} | 1:1 crossings {len(cross)} | islands {isl}")
hi=[bl for bl in B if bl["datum"]>=14]
print("15-18 tier blocks:", len(hi), "tiles:", sum(len(b['tiles']) for b in hi))
json.dump({"blocks":[{"i":bl["i"],"tiles":bl["tiles"],"datum":bl["datum"],"zone":bl["zone"]} for bl in B]},
          open(f"{SP}/scaffold_blocks.json","w"))

# render
INK=(11,14,20); LINE=(35,44,58); BONE=(216,211,196); DIM=(143,141,130)
AMBER=(224,168,111); CYAN=(111,214,224); RED=(200,90,80)
def font(sz):
    for pth in ("/System/Library/Fonts/Monaco.dfont","/System/Library/Fonts/Menlo.ttc"):
        try: return ImageFont.truetype(pth,sz)
        except Exception: pass
    return ImageFont.load_default()
F10,F12,F14,F20=font(13),font(15),font(17),font(26)
CELL=46; MX,MY=95,150
def P(x,y): return (MX+(12-x)*CELL, MY+(12-y)*CELL)
W=MX*2+25*CELL; Hh=MY+175+34*CELL
im=Image.new("RGB",(W,Hh),INK); dr=ImageDraw.Draw(im,"RGBA")
dr.text((MX,34),"THE ROOF PLAN v3 — 1:1 crossings only, the Long Climb, the high town",font=F20,fill=BONE)
dr.text((MX,72),"crossings ONLY between equal roofs (bi-directional, no damage) · furniture only at touching joins · street→18 continuous",font=F12,fill=AMBER)
def band(h):
    if h>=15: return (238,232,213)
    if h>=11: return (232,150,90)
    if h>=7:  return (224,168,111)
    if h>=4:  return (150,118,80)
    return (96,84,64)
for p in z0:
    if is_street(p):
        px,py=P(*p); dr.rectangle((px,py,px+CELL-3,py+CELL-3),fill=(38,44,57))
for p,h in H.items():
    px,py=P(*p); col=band(h)
    dr.rectangle((px,py,px+CELL-3,py+CELL-3),fill=col)
    dr.text((px+(14 if h<10 else 8),py+12),str(h),font=F14,fill=INK if h>=7 else BONE)
    if p not in z0: dr.rectangle((px,py,px+CELL-3,py+CELL-3),outline=(111,214,224,110),width=1)
for zone,txt in ((TERRA,"TERRAFORMER"),):
    xs=[p[0] for p in zone]; ys=[p[1] for p in zone]
    a=P(max(xs),max(ys)); b=P(min(xs),min(ys))
    dr.rectangle((a[0],a[1],b[0]+CELL-3,b[1]+CELL-3),outline=RED,width=3)
    dr.text((a[0]+8,a[1]+8),txt,font=F10,fill=RED)
a=P(12,3); b=P(-12,-3)
dr.rectangle((a[0],a[1],b[0]+CELL-3,b[1]+CELL-3),outline=(111,214,224,140),width=2)
dr.text((a[0]+8,a[1]+6),"CHANNEL — later",font=F10,fill=CYAN)
for (s,a,b) in cross:
    ax,ay=P(*a); bx,by=P(*b)
    dr.line((ax+CELL//2,ay+CELL//2,bx+CELL//2,by+CELL//2),fill=(111,214,224,170),width=3)
for (p,q) in furn:
    ax,ay=P(*p); bx,by=P(*q)
    dr.ellipse(((ax+bx)//2+CELL//2-5,(ay+by)//2+CELL//2-5,(ax+bx)//2+CELL//2+5,(ay+by)//2+CELL//2+5),outline=CYAN,width=2)
# skywalks among 14+ blocks
hib=[bl for bl in B if bl["datum"]>=14]
for i1 in range(len(hib)):
    for i2 in range(i1+1,len(hib)):
        if adjacent(hib[i1]["tiles"],hib[i2]["tiles"]):
            c1=centroid(hib[i1]["tiles"]); c2=centroid(hib[i2]["tiles"])
            a=P(c1[0],c1[1]); b=P(c2[0],c2[1])
            dr.line((a[0]+CELL//2,a[1]+CELL//2,b[0]+CELL//2,b[1]+CELL//2),fill=BONE,width=5)
dr.text((P(7,12)[0],P(7,12)[1]-26),"SKYWALKS — the 14-18 high town",font=F10,fill=BONE)
# the long climb path
pts=[P(*p) for p,_ in CLIMB]
pts=[(x+CELL//2,y+CELL//2) for x,y in pts]
dr.line(pts,fill=(224,168,111,230),width=6)
for x,y in pts: dr.ellipse((x-6,y-6,x+6,y+6),fill=AMBER)
dr.text((pts[0][0]-40,pts[0][1]+30),"THE LONG CLIMB: street→2→4→6→8→8→14→16→18 (jump ±1 · furniture +2 marked)",font=F12,fill=AMBER)
lx,ly=MX,Hh-118
for i,(lo,hi2) in enumerate(((2,3),(4,6),(7,10),(11,14),(15,18))):
    c=band(lo); dr.rectangle((lx+i*150,ly,lx+i*150+26,ly+26),fill=c)
    dr.text((lx+i*150+34,ly+4),f"{lo}-{hi2}",font=F12,fill=BONE)
dr.text((lx,ly+38),f"1:1 flat joins {flat} (the fabric) · ±1 joins {len(native)-flat} (the texture) · furniture {len(furn)} · crossings {len(cross)} · islands {isl}",font=F12,fill=AMBER)
dr.text((lx,ly+62),"thick bone = skywalks (high town) · amber path = the Long Climb · ○ furniture · cyan tie = air crossing",font=F10,fill=CYAN)
im.save(f"{SP}/roofplan3.png")
print("plate written")
