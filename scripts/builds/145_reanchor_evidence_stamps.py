"""Build 145 — re-anchor evidence stamped on the old runtime clock (#2414).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/145_reanchor_evidence_stamps.py
    then a foreground reload.

Blood and graffiti were stamped with `evennia.utils.gametime`, which returns
ACCUMULATED SERVER RUNTIME. That counter is not monotonic — a database restore
rewinds it while stored stamps keep their old values. Live symptom, read off a
street:

    Evidence age span: -8649.8 hours

Server gametime was 40,725,994 while the stain's oldest incident was stamped
71,865,364 — dated roughly 360 days in the future. Others read as 54 years old.
Every forensic age in the game was meaningless, and blood age feeds both the
freshness description and an identification-confidence penalty.

WHAT THIS DOES. The old runtime→real-time mapping is gone with the counter, so
those stamps cannot be converted. Instead the SPACING is preserved and the
sequence re-anchored so the newest incident reads as `now`:

    newest -> now,  everything else -> now - (newest - ts)

The forensic story survives — three separate bleeding events, hours apart, two
sources — while the absolute reference becomes real again. The alternative,
inventing an absolute age, would be a fabrication dressed as evidence.

Only legacy stamps are touched: anything already on the real clock
(>= 1e9) is left exactly as it is, so this is re-run-safe.
"""
import time

from evennia.objects.models import ObjectDB

LEGACY_MAX = 1_000_000_000
now = time.time()


def _num(value):
    """Timestamps are not consistently typed: graffiti stores most of them as
    STRINGS holding a float ('29903326.30...'), blood stores floats. Coerce,
    and treat anything unparseable as missing rather than crashing a
    migration halfway through a live world."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

blood_objs = 0
blood_stamps = 0
graffiti_objs = 0
graffiti_stamps = 0

for obj in ObjectDB.objects.all():
    # ---- blood ----------------------------------------------------------
    incidents = obj.attributes.get("bleeding_incidents")
    if incidents:
        rows = [dict(i) for i in incidents]
        stamps = {id(r): _num(r.get("timestamp")) for r in rows}
        legacy = [r for r in rows
                  if stamps[id(r)] is not None and stamps[id(r)] < LEGACY_MAX]
        if legacy:
            newest = max(v for v in stamps.values() if v is not None)
            for r in rows:
                ts = stamps[id(r)]
                if ts is not None and ts < LEGACY_MAX:
                    r["timestamp"] = now - (newest - ts)
            obj.attributes.add("bleeding_incidents", rows)
            blood_objs += 1
            blood_stamps += len(legacy)
        created = _num(obj.attributes.get("created_time"))
        if created is not None and created < LEGACY_MAX:
            obj.attributes.add("created_time", now)

    # ---- graffiti -------------------------------------------------------
    entries = obj.attributes.get("graffiti_entries")
    if entries:
        rows = [dict(e) for e in entries]
        stamps = {id(r): _num(r.get("timestamp")) for r in rows}
        legacy = [r for r in rows
                  if stamps[id(r)] is not None and stamps[id(r)] < LEGACY_MAX]
        if legacy:
            newest = max(v for v in stamps.values() if v is not None)
            for r in rows:
                ts = stamps[id(r)]
                if ts is not None and ts < LEGACY_MAX:
                    # normalise to a float while we are here — these were
                    # stored as strings holding a float
                    r["timestamp"] = now - (newest - ts)
            obj.attributes.add("graffiti_entries", rows)
            graffiti_objs += 1
            graffiti_stamps += len(legacy)

print(f"blood objects re-anchored    : {blood_objs} ({blood_stamps} stamps)")
print(f"graffiti objects re-anchored : {graffiti_objs} ({graffiti_stamps} stamps)")
