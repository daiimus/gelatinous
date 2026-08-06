from PIL import Image, ImageDraw, ImageFont
SP="/private/tmp/claude-502/-Users-rocket/9c546aa0-768b-4c91-992e-d7060f43d859/scratchpad"
INK=(11,14,20); PLATE=(30,36,48); MASS=(48,54,66); LINE=(35,44,58); BONE=(216,211,196)
DIM=(143,141,130); AMBER=(224,168,111); CYAN=(111,214,224)
WATER=(26,58,74); WATER2=(20,44,58); GREEN=(105,150,95); RED=(200,90,80)
def font(sz):
    for p in ("/System/Library/Fonts/Monaco.dfont","/System/Library/Fonts/Menlo.ttc"):
        try: return ImageFont.truetype(p,sz)
        except Exception: pass
    return ImageFont.load_default()
F10,F12,F14,F20=font(13),font(15),font(18),font(26)

# ============ PLATE A: CROSS-SECTION (looking west, north at LEFT) ============
W,Hh=1560,1150; MX,TOP=95,150; CW,CH=92,54
im=Image.new("RGB",(W,Hh),INK); dr=ImageDraw.Draw(im,"RGBA")
def X(y): return MX+(7-y)*CW
def Z(z): return int(TOP+(13-z)*CH)
dr.text((MX,36),"THE CENTRAL CHANNEL — CROSS-SECTION",font=F20,fill=BONE)
dr.text((MX,74),"looking west · north at left · water at z-1 · analysis draft, nothing built",font=F12,fill=AMBER)
dr.text((X(7),Z(13)-28),"N ◄",font=F14,fill=DIM); dr.text((X(-7)-40,Z(13)-28),"► S",font=F14,fill=DIM)
# z scale
for z,lab in ((12,"12"),(10,"10"),(8,"8"),(6,"6  skyway datum"),(4,"4"),(2,"2"),(0,"0  quay"),(-1,"-1 surface"),(-2,"-2 shallows"),(-3,"-3 bed")):
    dr.line((MX+95,Z(z),W-40,Z(z)),fill=(35,44,58,90),width=1)
    dr.text((14,Z(z)-8),lab,font=F10,fill=DIM)
# megablock ghost (north, far left)
dr.rectangle((X(7),Z(12),X(6),Z(0)),fill=(48,54,66,120),outline=LINE)
dr.text((X(7)+6,Z(12)+6),"MEGABLOCK\nRISE 8→14",font=F10,fill=DIM)
for z in (6,10): dr.line((X(7),Z(z),X(6),Z(z)),fill=(224,168,111,120),width=2)
# farm tower on north bank block (y +5..+6)
dr.rectangle((X(6),Z(5),X(5),Z(0)),fill=MASS,outline=LINE,width=2)
for z in range(0,5): 
    dr.line((X(6)+6,Z(z+0.75),X(5)-6,Z(z+0.75)),fill=GREEN,width=3)
dr.text((X(6)+6,Z(5)-24),"VERTICAL FARM 5 — draws from the basin",font=F10,fill=GREEN)
# Tolliver quay
dr.rectangle((X(5),Z(0),X(3.5),Z(-0.35)),fill=PLATE,outline=LINE)
dr.text((X(5)+4,Z(0)-22),"TOLLIVER ROW — north quay (exists)",font=F12,fill=BONE)
# bank walls
dr.rectangle((X(3.6),Z(-0.35),X(3.4),Z(-3.2)),fill=MASS)
dr.rectangle((X(-3.4),Z(-0.35),X(-3.6),Z(-3.2)),fill=MASS)
# water body
dr.rectangle((X(3.4),Z(-1),X(-3.4),Z(-3.2)),fill=WATER)
dr.rectangle((X(3.4),Z(-2),X(-3.4),Z(-3.2)),fill=WATER2)
for i in range(int(X(3.4)),int(X(-3.4)),26):
    dr.arc((i,Z(-1)-6,i+18,Z(-1)+6),200,340,fill=CYAN,width=2)
# bed
dr.rectangle((X(3.4),Z(-3.2),X(-3.4),Z(-3.6)),fill=(40,38,34))
dr.text((X(0.4),Z(-3.15)),"silt — 61 years of things dropped",font=F10,fill=DIM)
# rafts + racks
for yc,lab in ((2.4,"raft lane — grow decks"),(-2.4,"raft lane")):
    dr.rectangle((X(yc+0.6),Z(-0.8),X(yc-0.6),Z(-1.05)),fill=PLATE,outline=AMBER)
    for k in range(3):
        dr.line((X(yc+0.45-k*0.3),Z(-0.8),X(yc+0.45-k*0.3),Z(-0.55)),fill=GREEN,width=4)
    dr.rectangle((X(yc+0.5),Z(-1.3),X(yc-0.5),Z(-2.4)),outline=(105,150,95,160),width=2)
    dr.text((X(yc+0.62),Z(-0.55)-18),lab,font=F10,fill=GREEN)
dr.text((X(2.2),Z(-2.75)),"aquaculture racks",font=F10,fill=(90,130,120))
# fairway + barge
dr.text((X(1.05),Z(-0.5)-30),"FAIRWAY — barges, kept clear",font=F10,fill=CYAN)
dr.rectangle((X(0.8),Z(-0.85),X(-0.8),Z(-1.35)),fill=(38,44,56),outline=LINE)
dr.ellipse((X(-0.62),Z(-0.88),X(-0.75),Z(-0.98)),fill=AMBER)
# gallery window (north wall)
dr.rectangle((X(3.6)+2,Z(-1.7),X(3.4)-2,Z(-2.3)),fill=(111,214,224,70),outline=CYAN,width=2)
dr.text((X(3.15),Z(-2.55)),"bank gallery — basement windows into green water (descs, not rooms)",font=F10,fill=CYAN)
# south quay + clinic + light
dr.rectangle((X(-3.5),Z(0),X(-5),Z(-0.35)),fill=PLATE,outline=LINE)
dr.text((X(-3.6)-190,Z(0)-22),"MAXWELL STREET — south quay (exists)",font=F12,fill=BONE)
dr.rectangle((X(-5),Z(2),X(-6.6),Z(0)),fill=MASS,outline=LINE,width=2)
dr.text((X(-5)-30,Z(2)-22),"CLINIC 2 — south bank stays LOW (2-3)",font=F10,fill=DIM)
ov=Image.new("RGBA",im.size,(0,0,0,0)); od=ImageDraw.Draw(ov)
od.polygon([(X(-6.6),Z(9)),(X(-3.2),Z(2.2)),(X(3.2),Z(-1)),(X(-6.6),Z(-1))],fill=(224,190,130,26))
im=Image.alpha_composite(im.convert("RGBA"),ov).convert("RGB"); dr=ImageDraw.Draw(im,"RGBA")
dr.text((X(-4.2),Z(3.4)),"light reaches the basin",font=F10,fill=(224,190,130))
# melt main
dr.ellipse((X(0.3),Z(-4)-12,X(-0.3),Z(-4)+12),outline=DIM,width=3)
dr.text((X(-0.5),Z(-4)-8),"melt main → runs west to the intake · ICE MINES below",font=F10,fill=DIM)
dr.text((MX,Hh-64),"water is the city's soft-fail: any fall ending in the basin lands safe — the channel is the parkour nursery",font=F12,fill=CYAN)
dr.text((MX,Hh-38),"room budget when wet: ~6 raft strip rooms + 4 underwater rooms + desc-only galleries — vast implied, brief actual",font=F12,fill=DIM)
im.save(f"{SP}/channel_section.png")

# ============ PLATE B: LONG PROFILE (looking north, west at LEFT) ============
W,Hh=1560,900; MX,TOP=95,150; CWx,CHz=52,80
im=Image.new("RGB",(W,Hh),INK); dr=ImageDraw.Draw(im,"RGBA")
def XP(x): return MX+(13-x)*CWx
def ZP(z): return int(TOP+(4-z)*CHz)
dr.text((MX,36),"THE CENTRAL CHANNEL — LONG PROFILE",font=F20,fill=BONE)
dr.text((MX,74),"looking north · west at left · Tolliver/Maxwell quays run the full length · analysis draft",font=F12,fill=AMBER)
dr.text((XP(13),ZP(4)-28),"W ◄",font=F14,fill=DIM); dr.text((XP(-13)-40,ZP(4)-28),"► E",font=F14,fill=DIM)
for z in (0,-1,-2,-3):
    dr.line((MX-8,ZP(z),W-40,ZP(z)),fill=(35,44,58,90),width=1)
    dr.text((14,ZP(z)-8),str(z),font=F10,fill=DIM)
# ground line + water + bed
dr.line((XP(12.5),ZP(0),XP(-12.5),ZP(0)),fill=BONE,width=2)
dr.rectangle((XP(11.5),ZP(-1),XP(-11.5),ZP(-3)),fill=WATER)
for i in range(int(XP(11.5)),int(XP(-11.5)),30):
    dr.arc((i,ZP(-1)-6,i+20,ZP(-1)+6),200,340,fill=CYAN,width=2)
dr.rectangle((XP(11.5),ZP(-3),XP(-11.5),ZP(-3.3)),fill=(40,38,34))
# central span
dr.rectangle((XP(0.25),ZP(0.5),XP(-0.25),ZP(-3)),fill=MASS,outline=LINE,width=2)
dr.rectangle((XP(1.6),ZP(0.6),XP(-1.6),ZP(0.35)),fill=PLATE,outline=LINE,width=2)
dr.rectangle((XP(0.15),ZP(2.6),XP(-0.15),ZP(0.6)),fill=MASS)
dr.text((XP(1.5),ZP(2.6)-24),"CENTRAL SPAN (section) — pier base = SPAN ROOTS",font=F12,fill=BONE)
# span roots chamber
dr.rectangle((XP(0.8),ZP(-2),XP(-0.8),ZP(-2.9)),outline=AMBER,width=3)
dr.text((XP(0.7),ZP(-2)-22),"SPAN ROOTS — dive rooms ×2",font=F10,fill=AMBER)
# west end: weir, intake, west bridge
dr.rectangle((XP(12),ZP(0),XP(11.5),ZP(-3.3)),fill=MASS)
dr.rectangle((XP(11.4),ZP(-2),XP(10.4),ZP(-2.9)),outline=AMBER,width=3)
dr.text((XP(11.3),ZP(-1.6)),"INTAKE VAULT — works access · locked · B&E / decking seam",font=F10,fill=AMBER)
dr.line((XP(11.5),ZP(-2.5),XP(13),ZP(-2.5)),fill=DIM,width=5)
dr.text((XP(13),ZP(-3.4)+12),"mains → Terraformer works (under the Spillane)",font=F10,fill=DIM)
dr.rectangle((XP(12.6),ZP(1.6),XP(12.2),ZP(0)),fill=MASS,outline=LINE)
dr.text((XP(13),ZP(1.6)-22),"PUMPHOUSE",font=F10,fill=DIM)
dr.line((XP(12.9),ZP(0.6),XP(11.6),ZP(0.6)),fill=(111,214,224,200),width=4)
dr.text((XP(12.9),ZP(0.6)-24),"WEST BRIDGE (proposed)",font=F10,fill=CYAN)
# east end: head + grate + riser
dr.rectangle((XP(-11.5),ZP(0),XP(-12),ZP(-3.3)),fill=MASS)
dr.rectangle((XP(-10.4),ZP(-1.5),XP(-11.4),ZP(-2.5)),outline=AMBER,width=3)
dr.text((XP(-5.2),ZP(-1.35)),"THE EAST GRATE — barrier to the mines (future link)",font=F10,fill=AMBER)
dr.line((XP(-11.7),ZP(-4.3),XP(-11.7),ZP(-2.5)),fill=DIM,width=5)
dr.text((XP(-10.2),ZP(-4)),"ice-melt riser — from the mines",font=F10,fill=DIM)
# rafts + silt
for x0 in (9,7,5,3,-3,-5,-7):
    dr.rectangle((XP(x0+0.4),ZP(-0.85),XP(x0-0.4),ZP(-1.1)),fill=PLATE,outline=(224,168,111,140))
    dr.line((XP(x0),ZP(-0.85),XP(x0),ZP(-0.6)),fill=GREEN,width=3)
dr.text((XP(9),ZP(-0.6)-20),"grow rafts along both lanes",font=F10,fill=GREEN)
for x0 in (-4.5,-5.5,-6.5,-8):
    dr.line((XP(x0),ZP(-2.95),XP(x0-0.3),ZP(-2.8)),fill=DIM,width=2)
dr.text((XP(-4.5),ZP(-3.3)+8),"silt field — salvage & secrets",font=F10,fill=DIM)
dr.text((MX,Hh-60),"the channel is a street made of water: barge freight west-east, the fairway kept clear, quays as the convergence spines",font=F12,fill=CYAN)
dr.text((MX,Hh-34),"underwater inventory: SPAN ROOTS ×2 · INTAKE VAULT · EAST GRATE = four rooms carrying the whole layer",font=F12,fill=DIM)
im.save(f"{SP}/channel_profile.png")
print("channel plates written")
