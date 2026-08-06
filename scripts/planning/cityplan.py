import json, collections
from PIL import Image, ImageDraw, ImageFont

SP="/private/tmp/claude-502/-Users-rocket/9c546aa0-768b-4c91-992e-d7060f43d859/scratchpad"
d=json.load(open(f"{SP}/city.json"))

INK=(11,14,20); PLATE=(17,22,31); LINE=(35,44,58); BONE=(216,211,196)
DIM=(143,141,130); AMBER=(224,168,111); CYAN=(111,214,224); RED=(200,90,80)
def font(sz):
    for p in ("/System/Library/Fonts/Monaco.dfont","/System/Library/Fonts/Menlo.ttc",
              "/System/Library/Fonts/Courier.ttc"):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
F10,F12,F14,F20=font(13),font(15),font(18),font(26)

# grid → screen: east=-x → east right: px=(12-x); north=+y up: py=(12-y)
CELL=42; MX,MY=90,120
def P(x,y): return (MX+(12-x)*CELL, MY+(12-y)*CELL)

cols=collections.defaultdict(list)
z0={}
for c in d["cells"]:
    x,y,z=c["xyz"]
    sky="sky" in (c.get("flags") or [])
    if not sky: cols[(x,y)].append(z)
    if z==0 and not sky: z0[(x,y)]=c
H={k:max(v)+1 for k,v in cols.items()}

def typecolor(t,key):
    t=(t or "").lower(); k=key.lower()
    if t in ("street","bridge"): return (42,49,64)
    if t=="alley": return (30,35,46)
    if "rooftop" in t or t=="terrace": return (52,56,66)
    return (66,58,48)   # building mass

def base_plate(title, sub):
    W=MX*2+25*CELL; Hh=MY+130+34*CELL
    im=Image.new("RGB",(W,Hh),INK); dr=ImageDraw.Draw(im,"RGBA")
    dr.text((MX,34),title,font=F20,fill=BONE)
    dr.text((MX,70),sub,font=F12,fill=AMBER)
    # compass: east right
    cx,cy=W-150,60
    dr.text((cx,cy-14),"N",font=F14,fill=AMBER); dr.line((cx+8,cy+34,cx+8,cy+8),fill=DIM,width=2)
    dr.text((cx+34,cy+22),"E",font=F14,fill=DIM); dr.line((cx+16,cy+30,cx+30,cy+30),fill=DIM,width=2)
    for (x,y),c in z0.items():
        px,py=P(x,y)
        dr.rectangle((px,py,px+CELL-3,py+CELL-3),fill=typecolor(c.get("type"),c["key"]))
        h=H.get((x,y),1)
        if h>=6:
            dr.rectangle((px,py,px+CELL-3,py+CELL-3),fill=(224,168,111,90))
            dr.text((px+8,py+8),str(h),font=F12,fill=BONE)
        elif h>=2:
            dr.rectangle((px,py,px+CELL-3,py+CELL-3),fill=(224,168,111,40))
            dr.text((px+10,py+10),str(h),font=F10,fill=DIM)
    return im,dr

def label(dr,x,y,txt,color=BONE,dx=0,dy=-22,f=None):
    px,py=P(x,y); dr.text((px+dx,py+dy),txt,font=f or F12,fill=color)

# ---------- PLATE 1: AS BUILT ----------
im,dr=base_plate("DOMINO'S GAMBIT — AS BUILT","589 rooms · heights in stories · the missing middle: nothing stands at 4-5")
for x,y,t,c in ((-10,9,"LANDING PAD",CYAN),(2,10,"THAWN 2-3",BONE),(10,11,"HELIX 2-3",BONE),
                (0,0,"CENTRAL SPAN",CYAN),(-2,-15,"QoC 6",BONE),(1,-18,"AGRIDOME",BONE),
                (8,-15,"CONSTABULARY",BONE),(-10,-18,"BRACKETT 8",AMBER),(0,-8,"VOLTA",DIM),
                (4,-6,"RIVETER'S",DIM),(12,-12,"THE SPILLANE",DIM),(-10,-20,"BRADDOCK AV",DIM)):
    label(dr,x,y,t,c)
# channel band annotation
x0,y0=P(12,3); x1,y1=P(-12,-3)
dr.rectangle((x0,y0,x1+CELL-3,y1+CELL-3),outline=CYAN,width=2)
dr.text((x0+10,y0-26),"THE CHANNEL (y -3..+3) — crossed only at x=0",font=F12,fill=CYAN)
im.save(f"{SP}/plan_asbuilt.png")

# ---------- PLATE 2: THE PLAN ----------
im,dr=base_plate("DOMINO'S GAMBIT — THE PLAN","City Section applied: corridors, reservations, ascent routes · analysis draft, nothing built")
ov=Image.new("RGBA",im.size,(0,0,0,0)); od=ImageDraw.Draw(ov)

def zone(x0,y0,x1,y1,fill,outline,w=3):
    a=P(max(x0,x1),max(y0,y1)); b=P(min(x0,x1),min(y0,y1))
    od.rectangle((a[0],a[1],b[0]+CELL-3,b[1]+CELL-3),fill=fill,outline=outline,width=w)

# crater rim ring
a=P(14,14); b=P(-14,-23)
od.rectangle((a[0],a[1],b[0],b[1]),outline=(143,141,130,255),width=4)
od.text((a[0]+16,b[1]-34),"CRATER WALL — rim z≈20 · kept empty · ONE terminus",font=F12,fill=DIM)
# channel
zone(12,3,-12,-3,(111,214,224,26),(111,214,224,180),2)
od.text((P(12,3)[0]+8,P(12,3)[1]+6),"CENTRAL CHANNEL — aquaponics basin · south bank LOW (2-3) for light · vertical farms on banks",font=F10,fill=CYAN)
# megablock quarter (north grid)
zone(12,12,1,6,(224,168,111,34),(224,168,111,200))
od.text((P(12,12)[0]+8,P(12,12)[1]+6,),"MEGABLOCK RISE 8-14 → ANCHOR 16-18 · street-tunnels + skyways · datum galleries",font=F10,fill=AMBER)
od.ellipse([P(3,11)[0]-6,P(3,11)[1]-6,P(1,9)[0]+CELL,P(1,9)[1]+CELL],outline=(224,168,111,255),width=3)
od.text((P(3,11)[0],P(3,11)[1]-24),"ANCHOR 16-18 (owner call: Thawn or new)",font=F10,fill=AMBER)
# processor reservation — the block the streets already frame (it is EMPTY today)
zone(11,-5,5,-11,(200,90,80,34),(200,90,80,220))
od.text((P(11,-5)[0]+8,P(11,-5)[1]+6),"ATMOSPHERIC PROCESSOR — the plot the grid was drawn around",font=F10,fill=RED)
od.text((P(11,-6)[0]+8,P(11,-6)[1]+8),"Maxwell N · Pessoa S · the Spillane W · Riveter's E",font=F10,fill=(200,120,110))
od.text((P(11,-7)[0]+8,P(11,-7)[1]+10),"7x7, empty since seeding · cone → z20 · ICE MINES below",font=F10,fill=(200,120,110))
gx,gy=P(4,-8)
od.ellipse((gx-4,gy-4,gx+CELL,gy+CELL),outline=(224,168,111,255),width=3)
od.text((gx+CELL+8,gy+10),"MAIN GATE — Volta & Riveter's",font=F10,fill=AMBER)
# wall fringe
zone(3,-21,-12,-21,(143,141,130,60),(143,141,130,200),2)
od.text((P(3,-21)[0]+8,P(3,-21)[1]+8),"WALL-DWELLING FRINGE — terraces climb the crater face",font=F10,fill=DIM)
# corridors (routes as arrows)
def route(pts,color,name,ny):
    xy=[(P(x,y)[0]+CELL//2,P(x,y)[1]+CELL//2) for x,y in pts]
    od.line(xy,fill=color,width=5)
    for p in xy: od.ellipse((p[0]-5,p[1]-5,p[0]+5,p[1]+5),fill=color)
    od.text((xy[0][0]-330 if xy[0][0]>900 else xy[0][0]+10,xy[0][1]+ny),name,font=F12,fill=color)
# A: north architecture climb (channel bank → megablocks → anchor → NW rim)
route([(0,4),(3,6),(5,8),(8,10),(10,11),(12,12)],(224,168,111,255),"A: 0→4→8→12→16→18→rim",-30)
# B: southeast geology climb (street → Brackett core → roofs → wall terraces → rim terminus)
route([(-12,-21),(-11,-19),(-10,-17),(-8,-16)],(216,211,196,255),"B: 0→8 (Brackett) →10→13→16→20",-34)
od.ellipse([P(-13,-22)[0]+8,P(-13,-22)[1]+8,P(-13,-22)[0]+30,P(-13,-22)[1]+30],outline=BONE,width=3)
od.text((P(-13,-22)[0]-120,P(-13,-22)[1]+34),"THE ONE RIM TERMINUS",font=F10,fill=BONE)
# C: processor spiral
route([(4,-8),(6,-8),(8,-8),(8,-9)],(111,214,224,255),"C: gate→works→catwalk helix→z20",26)
# industrial corridors
od.line([P(-12,-8)[0],P(-12,-8)[1]+CELL//2,P(4,-8)[0]+CELL,P(4,-8)[1]+CELL//2],fill=(143,141,130,255),width=3)
od.text((P(-4,-8)[0],P(-4,-8)[1]+18),"VOLTA: POWER RUN → skirt",font=F10,fill=DIM)
od.text((P(4,-4)[0]+56,P(4,-4)[1]-26),"RIVETER'S: FAB SPINE basin↔works",font=F10,fill=DIM)
# west bridge proposal
od.line([P(12,-4)[0]+CELL//2,P(12,-4)[1],P(12,4)[0]+CELL//2,P(12,4)[1]+CELL],fill=(111,214,224,255),width=4)
od.text((P(12,4)[0]+14,P(12,4)[1]-40),"PROPOSED WEST BRIDGE:\nSpillane crosses channel →\nfreight loop + 2nd crossing",font=F10,fill=CYAN)
# freight diagonal note
od.text((P(-4,9)[0],P(-4,9)[1]-40),"LANDING PAD → freight west along the north bank",font=F10,fill=DIM)
im=Image.alpha_composite(im.convert("RGBA"),ov).convert("RGB")
im.save(f"{SP}/plan_proposed.png")
print("plates written")
