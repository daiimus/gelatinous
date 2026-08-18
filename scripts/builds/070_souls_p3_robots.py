"""Build 070 — spec-P3 world wiring: the charge cradle + first robot soul.

The dispatch base station console advertises `charge` (spec §12) —
robots dwell there to refill the battery. One security unit gets a
soul on the robot profile: no hunger, no wallet, no schedule; patrols
stay director-owned (precedence law), and the soul only walks it to
the cradle between assignments when the battery runs down.

Idempotent: ad re-mirrors; skips if a robot soul already exists.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/070_souls_p3_robots.py
"""

from evennia.objects.models import ObjectDB

from world.director.population import get_dispatch_room
from world.souls import engine, ensoul

OUT = []

# ---- 1. The base station advertises charge -------------------------
base = get_dispatch_room()
station = None
if base:
    station = next((o for o in base.contents
                    if getattr(o.db, "is_base_station", None) is True), None)
if station:
    ads = dict(station.db.advertises or {})
    ads["charge"] = 0.9
    ads["maintenance"] = 0.6
    station.db.advertises = ads
    station.tags.add("advertiser", category="souls")
    OUT.append(f"charge ad: {station.key} (#{station.id}) @ {base.key}")
else:
    OUT.append("NO base station found — charge ad not placed")

# ---- 2. First robot soul -------------------------------------------
existing = [s for s in engine.get_souls()
            if s.db.soul_profile == "robot"
            or s.db.soul_role == "secunit"]
if existing:
    OUT.append(f"robot soul already exists: {existing[0].key}; skipped")
elif station:
    bot = next((o for o in ObjectDB.objects.filter(
        db_key__icontains="security robot") if o.pk and o.location), None)
    if bot:
        ensoul(bot, role="secunit", home=None, post=None,
               schedule="day", wage_rate=0.0, venue=None, profile="robot")
        OUT.append(f"ensouled: {bot.key} (#{bot.id}) @ {bot.location.key} "
                   f"profile:robot")
    else:
        OUT.append("no security robot found to ensoul")

print("BUILD 070: souls spec-P3 robots")
for line in OUT:
    print(f"  {line}")
print(f"  souls: {[(s.key, s.db.soul_role) for s in engine.get_souls()]}")
