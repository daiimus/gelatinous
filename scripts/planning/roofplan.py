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
def hsh(x,y): return ((x*73+y*131)%3)-1

def target(p):
    x,y=p
    if p in TERRA or p in CHAN: return None
    if is_street(p): return None
    k=keyat(p).lower()
    if "landing pad" in k: return 1
    if "agridome" in k: return 1
    if "brackett" in k or (cols.get(p,0)>=7): return cols[p]-0 if cols[p]>=7 else None
    if "queen of cups" in k or cols.get(p,0)==6: return 6
    if 8<=x<=11 and 9<=y<=11:                            # the crown outranks names
        return 18 if (x,y) in ((10,10),(10,11)) else (16 if (x,y) in ((9,10),(11,10),(10,9)) else 13)
    if "thawn" in k: return 8
    if "helix" in k: return 12
    if "constab" in k or "armory" in k: return 3
    exists = p in z0
    # north grid
    if y>=4:
        if x<=-8 and y>=7: return max(2,3+hsh(x,y))          # pad quarter: flight cap
        if 8<=x<=11 and 9<=y<=11:                            # anchor crown
            return 18 if (x,y) in ((10,10),(10,11)) else (16 if (x,y) in ((9,10),(11,10),(10,9)) else 13)
        if y<=6: return max(2,4+hsh(x,y))                    # bank rows 3-5
        if y<=8: return 7+hsh(x,y)                           # podium band 6-8
        return 10+hsh(x,y)                                   # high band 9-11
    # south grid
    if y<=-4:
        if y<=-20: return max(2,3+hsh(x,y))                  # fringe rows 2-4
        if -19<=y<=-13:
            if abs(x-(-9))<=2 and abs(y-(-18))<=2 and not exists: return 5+((x+y)%2)  # steps to the mesa
            return max(2,3+hsh(x,y))                         # old town 2-4
        if -12<=y<=-9: return 4+hsh(x,y)                     # Volta/Pessoa works 3-5
        return max(2,3+hsh(x,y))                             # Maxwell bank 2-4
    return None

# candidate tiles: existing buildings + empty lots inside extent
H={}
for x in range(-12,13):
    for y in range(-21,13):
        p=(x,y)
        if is_street(p): continue
        t=target(p)
        if t: H[p]=t

# links: native (<=1), furniture (2-3); crossings over 1-wide streets
native=[]; furn=[]; cross=[]
for p,h in H.items():
    x,y=p
    for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
        q=(x+dx,y+dy)
        if q in H:
            dlt=abs(h-H[q])
            if dlt<=1: native.append((p,q))
            elif dlt<=3: furn.append((p,q))
for p in z0:
    if not is_street(p): continue
    x,y=p
    for (a,b) in (((x-1,y),(x+1,y)),((x,y-1),(x,y+1))):
        if a in H and b in H and abs(H[a]-H[b])<=1 and min(H[a],H[b])>=2:
            cross.append((p,a,b))
# connectivity
parent={}
def find(u):
    while parent.setdefault(u,u)!=u: u=parent[u]
    return u
def uni(u,v): parent[find(u)]=find(v)
for p in H: parent[p]=p
for a,b in native+furn: uni(a,b)
for _,a,b in cross: uni(a,b)
isl=len({find(p) for p in H})
print(f"tiles: {len(H)} | native links: {len(native)} | furniture bridges: {len(furn)} | street crossings: {len(cross)} | islands: {isl}")

# ---------- render ----------
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
W=MX*2+25*CELL; Hh=MY+170+34*CELL
im=Image.new("RGB",(W,Hh),INK); dr=ImageDraw.Draw(im,"RGBA")
dr.text((MX,34),"THE ROOF PLAN — every tile a rung (heights 1-20)",font=F20,fill=BONE)
dr.text((MX,72),"mesh law applied: ±1 native · 2-3 = furniture · >3 = boundary · generated from the City Section, argue per-tile",font=F12,fill=AMBER)
dr.text((W-160,54),"N",font=F14,fill=AMBER); dr.line((W-152,96,W-152,70),fill=DIM,width=2)
dr.text((W-126,84),"E",font=F14,fill=DIM); dr.line((W-144,92,W-130,92),fill=DIM,width=2)
def band(h):
    if h>=15: return (238,232,213)
    if h>=11: return (232,150,90)
    if h>=7:  return (224,168,111)
    if h>=4:  return (150,118,80)
    return (96,84,64)
for p,c in z0.items():
    if is_street(p):
        px,py=P(*p); dr.rectangle((px,py,px+CELL-3,py+CELL-3),fill=(38,44,57))
for p,h in H.items():
    px,py=P(*p)
    col=band(h)
    dr.rectangle((px,py,px+CELL-3,py+CELL-3),fill=(col[0],col[1],col[2],255 if h>=7 else 210))
    tcol=INK if h>=7 else BONE
    dr.text((px+(14 if h<10 else 8),py+12),str(h),font=F14,fill=tcol)
    if p not in z0:
        dr.rectangle((px,py,px+CELL-3,py+CELL-3),outline=(111,214,224,120),width=1)
# reserves
for zone,txt,colr in ((TERRA,"TERRAFORMER — reserved",RED),):
    xs=[p[0] for p in zone]; ys=[p[1] for p in zone]
    a=P(max(xs),max(ys)); b=P(min(xs),min(ys))
    dr.rectangle((a[0],a[1],b[0]+CELL-3,b[1]+CELL-3),outline=colr,width=3)
    dr.text((a[0]+8,a[1]+8),txt,font=F10,fill=colr)
a=P(12,3); b=P(-12,-3)
dr.rectangle((a[0],a[1],b[0]+CELL-3,b[1]+CELL-3),outline=(111,214,224,150),width=2)
dr.text((a[0]+8,a[1]+6),"CHANNEL — later",font=F10,fill=CYAN)
# furniture + crossings
for (p,q) in furn:
    ax,ay=P(*p); bx,by=P(*q)
    dr.ellipse(((ax+bx)//2+CELL//2-5,(ay+by)//2+CELL//2-5,(ax+bx)//2+CELL//2+5,(ay+by)//2+CELL//2+5),outline=CYAN,width=2)
for (s,a,b) in cross:
    ax,ay=P(*a); bx,by=P(*b)
    dr.line((ax+CELL//2,ay+CELL//2,bx+CELL//2,by+CELL//2),fill=CYAN,width=3)
# legend
lx,ly=MX,Hh-120
dr.text((lx,ly-24),"BANDS",font=F10,fill=DIM)
for i,(lo,hi) in enumerate(((2,3),(4,6),(7,10),(11,14),(15,18))):
    c=band(lo)
    dr.rectangle((lx+i*150,ly,lx+i*150+26,ly+26),fill=c)
    dr.text((lx+i*150+34,ly+4),f"{lo}-{hi}",font=F12,fill=BONE)
dr.text((lx,ly+40),"○ furniture bridge (water tower / shed step / fire escape)   — cyan tie = street crossing (air cell)   thin cyan outline = NEW lot",font=F10,fill=CYAN)
dr.text((lx,ly+64),f"{len(H)} roof tiles · {len(native)} native joins · {len(furn)} furniture bridges · {len(cross)} street crossings · ISLANDS: {isl}",font=F12,fill=AMBER)
im.save(f"{SP}/roofplan.png")
print("plate written")
