"""Build 106 — people are not their jobs (#2148).

Half the cast was being described by trade: a squat VENDOR, a lithe
BARTENDER, a wiry SNAIL-KEEPER. The other half already read as people
— a rangy man in a company windbreaker, a squat woman in a white lab
coat — and the only difference was that nobody had set a keyword on
them, so the identity system fell back to a person-word and let build
and clothing do the distinguishing.

So this is mostly deletion. Clearing the trade-words lets everyone
read as somebody rather than something, and what they do for a living
becomes something you learn by watching them work.

Deliberately kept: the security robot, which IS its function.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/106_people_not_jobs.py
"""

from world.souls import engine
from world.souls import needs as needs_mod

TRADE_WORDS = {
    "vendor", "bartender", "tobacconist", "snail-keeper", "butcher",
    "broadcaster", "hand", "colonist", "drifter", "merchant", "doctor",
    "medic", "dispatcher", "server", "snailer", "keeper",
}

cleared, kept = [], []
for soul in engine.get_souls():
    if not soul.pk:
        continue
    if needs_mod.profile_name(soul) == "robot":
        kept.append(soul.key)          # a machine IS its function
        continue
    kw = getattr(soul, "sdesc_keyword", None)
    if kw and str(kw).lower() in TRADE_WORDS:
        soul.sdesc_keyword = ""
        cleared.append(soul.key)

print(f"BUILD 106: {len(cleared)} people stopped being their jobs; "
      f"{len(kept)} machines kept theirs")
for soul in sorted(engine.get_souls(), key=lambda s: s.key):
    if soul.pk:
        try:
            print(f"    {soul.key[:24]:<26}{soul.get_sdesc()[:56]}")
        except Exception:  # noqa: BLE001
            pass
