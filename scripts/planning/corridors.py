from PIL import Image, ImageDraw, ImageFont
SP="/private/tmp/claude-502/-Users-rocket/9c546aa0-768b-4c91-992e-d7060f43d859/scratchpad"
INK=(11,14,20); MASS=(48,54,66); MASS2=(60,64,74); ROCK=(38,36,40); LINE=(35,44,58)
BONE=(216,211,196); DIM=(143,141,130); AMBER=(224,168,111); CYAN=(111,214,224); GREEN=(105,150,95)
def font(sz):
    for p in ("/System/Library/Fonts/Monaco.dfont","/System/Library/Fonts/Menlo.ttc"):
        try: return ImageFont.truetype(p,sz)
        except Exception: pass
    return ImageFont.load_default()
F10,F12,F14,F20=font(13),font(15),font(18),font(26)

def stairs(dr,x0,z0,x1,z1,X,Z,col=CYAN):
    n=6; pts=[]
    for i in range(n+1):
        t=i/n; pts.append((X(x0+(x1-x0)*t), Z(z0+(z1-z0)*t)))
    for i in range(n):
        a,b=pts[i],pts[i+1]
        dr.line((a[0],a[1],b[0],a[1]),fill=col,width=3)
        dr.line((b[0],a[1],b[0],b[1]),fill=col,width=3)
def jump(dr,x0,z0,x1,z1,X,Z,col=AMBER):
    mx,mz=(X(x0)+X(x1))//2,min(Z(z0),Z(z1))-26
    dr.line((X(x0),Z(z0),mx,mz),fill=col,width=4)
    dr.line((mx,mz,X(x1),Z(z1)),fill=col,width=4)
    dr.ellipse((X(x0)-5,Z(z0)-5,X(x0)+5,Z(z0)+5),fill=col)
    dr.ellipse((X(x1)-5,Z(z1)-5,X(x1)+5,Z(z1)+5),fill=col)
def ladder(dr,x,z0,z1,X,Z,col=CYAN):
    dr.line((X(x)-6,Z(z0),X(x)-6,Z(z1)),fill=col,width=3)
    dr.line((X(x)+6,Z(z0),X(x)+6,Z(z1)),fill=col,width=3)
    zz=z0
    while zz<z1:
        dr.line((X(x)-6,Z(zz),X(x)+6,Z(zz)),fill=col,width=2); zz+=0.5
def star(dr,x,y,col=AMBER):
    dr.text((x-8,y-10),"★",font=F14,fill=col)

# ================= SOUTH: THE WALL RUN (corridor B) =================
W,Hh=1600,1100; MX,TOP=90,140; CW,CH=115,40
im=Image.new("RGB",(W,Hh),INK); dr=ImageDraw.Draw(im,"RGBA")
def X(x): return int(MX+(-3.6-x)*CW)      # facing south: east(-x) at RIGHT
def Z(z): return int(TOP+(21.5-z)*CH)
dr.text((MX,32),"CORRIDOR B — THE WALL RUN (south elevation, facing the crater face)",font=F20,fill=BONE)
dr.text((MX,70),"Brackett is the trailhead · terraces finger the rock · buildable nearly NOW · analysis draft",font=F12,fill=AMBER)
dr.text((X(-4.2),110),"W ◄",font=F12,fill=DIM); dr.text((X(-12.8),110),"► E",font=F12,fill=DIM)
for z in range(0,21,2):
    dr.line((MX+60,Z(z),W-30,Z(z)),fill=(35,44,58,70),width=1); dr.text((16,Z(z)-8),f"{z}",font=F10,fill=DIM)
# crater wall backdrop
dr.polygon([(X(-4),Z(0)),(X(-13.4),Z(0)),(X(-13.4),Z(20)),(X(-4),Z(20))],fill=(28,27,31))
dr.line((X(-4),Z(20),X(-13.4),Z(20)),fill=BONE,width=3)
dr.text((X(-5.6),Z(20)-24),"RIM z20 — kept empty",font=F12,fill=BONE)
# ground + Braddock
dr.line((X(-4),Z(0),X(-13.4),Z(0)),fill=BONE,width=2)
dr.text((X(-5.4),Z(0)+10),"BRADDOCK AVENUE z0 — the geology stair starts here (free route)",font=F10,fill=DIM)
# Brackett mass
dr.rectangle((X(-8.8),Z(8),X(-11.2),Z(0)),fill=MASS,outline=LINE,width=2)
dr.text((X(-9.2),Z(8)-42),"THE BRACKETT ARMS 8 (exists)",font=F12,fill=BONE)
dr.text((X(-9.2),Z(8)-24),"T2 ascent core: ADD exterior fire escape",font=F10,fill=CYAN)
stairs(dr,-8.85,0,-8.85,8,X,Z)  # fire escape on east face
# terraces (fingers off the wall)
TER=[(-8.0,-9.6,7,"TERRACE I  z7","level gap from Brackett roof"),
     (-10.2,-11.8,10,"TERRACE II z10","cut stair from I"),
     (-12.2,-13.2,9,"IIb z9","jump-down finger"),
     (-9.0,-10.6,13,"TERRACE III z13  ★ the cliff bar","ladder from II"),
     (-7.2,-8.2,12,"IIIb z12","jump-down · VALVE landing"),
     (-10.8,-12.4,16,"TERRACE IV z16","cut stair from III"),
     (-8.6,-9.6,18,"TERRACE V z18","ladder"),
     ]
for x0,x1,z,lab,note in TER:
    dr.rectangle((X(x0),Z(z),X(x1),Z(z-0.55)),fill=MASS2,outline=AMBER,width=2)
    dr.text((X(x0)+4,Z(z)-36),lab,font=F10,fill=BONE)
    dr.text((X(x0)+4,Z(z)-20),note,font=F10,fill=DIM)
star(dr,X(-9.25),Z(13)-46)
# rim gantry terminus
dr.rectangle((X(-9.9),Z(20.4),X(-10.7),Z(19.6)),outline=BONE,width=3)
dr.text((X(-9.8)-260,Z(20.4)-26),"THE ONE RIM TERMINUS — dead gantry",font=F10,fill=BONE)
# free route (geology stair, cyan) zigzagging wall behind terraces
stairs(dr,-12.9,0,-12.9,7,X,Z,(90,120,130)); stairs(dr,-12.9,7,-11.9,10,X,Z,(90,120,130))
dr.text((X(-13.35),Z(3)),"cut stair\n(free route)",font=F10,fill=(120,150,160))
# parkour route (amber)
jump(dr,-9.0,8,-8.6,7,X,Z)         # roof -> Terrace I (down 1, gap d12)
dr.text((X(-6.3),Z(6.2)),"gap d12\nAPRON: laundry deck z5",font=F10,fill=AMBER)
dr.rectangle((X(-8.2),Z(5),X(-9.2),Z(4.7)),outline=(224,168,111,150),width=2)
stairs(dr,-9.8,7,-10.4,10,X,Z)     # I -> II cut stair
jump(dr,-11.7,10,-12.3,9,X,Z)      # II -> IIb (down)
dr.text((X(-12.2),Z(10)+18),"d8",font=F10,fill=AMBER)
ladder(dr,-10.35,10,13,X,Z)        # II -> III ladder
jump(dr,-9.1,13,-8.1,12,X,Z)       # III -> IIIb
dr.text((X(-6.6),Z(12.2)),"d10 · VALVE −4:\ndrop escape to z8 roof",font=F10,fill=AMBER)
stairs(dr,-10.5,13,-11.1,16,X,Z)   # III -> IV
jump(dr,-10.9,16,-9.5,18,X,Z,col=(150,150,160))
dr.text((X(-11.2),Z(17.6)),"IV→V ladder",font=F10,fill=CYAN)
ladder(dr,-9.55,18,20,X,Z)         # V -> rim
dr.text((MX,Hh-56),"free route: Braddock cut stair zigzags the rock · parkour route: Brackett fire escape → roof → terrace chain (amber)",font=F12,fill=CYAN)
dr.text((MX,Hh-32),"NEW rooms: 7 terraces ×2-3 cells + stairs ≈ 20 · exposure discipline: aprons low, honest drops above z13",font=F12,fill=DIM)
im.save(f"{SP}/corridor_south.png")

# ================= NORTH: THE ARCHITECTURE CLIMB (corridor A) =================
W,Hh=1600,1100; MX,TOP=90,140; CW,CH=97,40
im=Image.new("RGB",(W,Hh),INK); dr=ImageDraw.Draw(im,"RGBA")
def X(x): return int(MX+(x+0.8)*CW)       # facing north: west(+x) at RIGHT
def Z(z): return int(TOP+(21.5-z)*CH)
dr.text((MX,32),"CORRIDOR A — THE ARCHITECTURE CLIMB (north elevation, from the channel)",font=F20,fill=BONE)
dr.text((MX,70),"Tolliver bank → midrise → podium → towers → the ANCHOR · zoning law for the megablock quarter · analysis draft",font=F12,fill=AMBER)
dr.text((X(-0.6),110),"E ◄",font=F12,fill=DIM); dr.text((X(12.6),110),"► W",font=F12,fill=DIM)
for z in range(0,21,2):
    dr.line((MX+60,Z(z),W-30,Z(z)),fill=(35,44,58,70),width=1); dr.text((16,Z(z)-8),f"{z}",font=F10,fill=DIM)
dr.line((X(-0.5),Z(20),X(13),Z(20)),fill=(143,141,130,140),width=2)
dr.text((X(0.0),Z(20)-24),"rim z20 beyond — the north route tops out on ARCHITECTURE; only the south touches the crater",font=F10,fill=DIM)
dr.line((X(-0.5),Z(0),X(13),Z(0)),fill=BONE,width=2)
dr.text((X(-0.5),Z(0)+10),"TOLLIVER ROW z0 — trailhead on the bank (channel behind the viewer)",font=F10,fill=DIM)
# masses: [x0,x1,h,fill,label]
BL=[(1.2,2.6,4,MASS,"MIDRISE 4 (new)"),(3.0,4.4,4,MASS,"MIDRISE 4"),(4.8,5.8,3,MASS,"3"),
    (6.2,8.0,8,MASS2,"PODIUM 8 (Thawn base? owner call)"),
    (8.4,9.6,8,MASS,""),(9.9,10.9,7,MASS,""),
    (11.2,12.6,12,MASS2,"HIGH BLOCK 12"),
    ]
for x0,x1,h,f,lab in BL:
    dr.rectangle((X(x0),Z(h),X(x1),Z(0)),fill=f,outline=LINE,width=2)
    dr.text((X(x0)+4,Z(h)-22),lab,font=F10,fill=BONE) if lab else dr.text((X(x0)+8,Z(h)+8),str(h),font=F10,fill=DIM)
# anchor tower
dr.rectangle((X(12.9),Z(17.5),X(14.0),Z(0)),fill=(66,60,52),outline=AMBER,width=2)
dr.polygon([(X(12.9),Z(17.5)),(X(13.2),Z(18.4)),(X(13.6),Z(17.9)),(X(14.0),Z(18.6)),(X(14.0),Z(17.5))],fill=(66,60,52),outline=AMBER)
dr.text((X(9.6),Z(19.4)-24),"THE ANCHOR 16-18 — identity: owner call (Thawn grown, or a new name)",font=F12,fill=AMBER)
# prize tower
dr.rectangle((X(10.0),Z(14),X(10.7),Z(7)),fill=(52,50,58),outline=LINE,width=2)
star(dr,X(10.3),Z(14)-16); dr.text((X(9.2),Z(14)-40),"PRIZE 14 — dead-end vantage over the pad",font=F10,fill=AMBER)
# skyway datum
dr.line((X(1.2),Z(6),X(12.6),Z(6)),fill=(224,168,111,150),width=3)
dr.text((X(1.3),Z(6)+8),"SKYWAY DATUM z6 — enclosed below, runnable on top (T6)",font=F10,fill=AMBER)
# aprons
for ax in (2.7,4.5):
    dr.rectangle((X(ax),Z(2),X(ax+0.4),Z(1.7)),outline=(224,168,111,150),width=2)
dr.text((X(2.7),Z(2)+8),"aprons z2",font=F10,fill=(224,168,111,200))
# route
stairs(dr,1.25,0,1.25,4,X,Z)                     # external stair up midrise A
jump(dr,2.5,4,3.1,4,X,Z); dr.text((X(2.55),Z(4.7)-24),"d8",font=F10,fill=AMBER)
jump(dr,4.3,4,4.9,3,X,Z); dr.text((X(4.35),Z(4.4)-20),"d8",font=F10,fill=AMBER)
stairs(dr,5.7,3,6.3,8,X,Z)                       # core up podium
dr.text((X(5.35),Z(7.0)),"T2 core",font=F10,fill=CYAN)
jump(dr,7.9,8,8.5,8,X,Z); dr.text((X(7.95),Z(8.7)-24),"d10",font=F10,fill=AMBER)
jump(dr,9.5,8,10.0,7,X,Z); dr.text((X(9.55),Z(8.4)-20),"d10",font=F10,fill=AMBER)
stairs(dr,10.8,7,11.3,12,X,Z)                    # core up high block
jump(dr,12.5,12,12.95,12,X,Z); dr.text((X(11.6),Z(13.2)-24),"d12 — the hard beat",font=F10,fill=AMBER)
stairs(dr,13.3,12,13.3,17.5,X,Z)                 # anchor core
dr.line((X(11.05),Z(12),X(11.05),Z(8)),fill=(150,150,160),width=4)
dr.text((X(10.2),Z(9.6)),"VALVE −4",font=F10,fill=DIM)
dr.text((MX,Hh-56),"sawtooth: 0→4→4→3→8→8→7→12→12→16-18 · one up-move per 2-3 across moves at worst, 1:4 average",font=F12,fill=CYAN)
dr.text((MX,Hh-32),"this profile IS the zoning law for the megablock quarter: heights chosen so the ladder exists before the blocks do",font=F12,fill=DIM)
im.save(f"{SP}/corridor_north.png")
print("corridor plates written")
