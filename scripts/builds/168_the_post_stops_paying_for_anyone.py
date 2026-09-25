"""Build 168 — the post stops paying for anyone (#3667, Slice B data).

Sleeve insurance is personal now (`world/insurance`): a return is paid
by the dead keeper's own policy, never by the post. The live rows that
carried the old model:

1. `post_policy = "resleave"` on every post build 098 stamped. The post
   no longer decides who comes back, only whether strangers may be hired,
   so `resleave` becomes `successor`. Left alone, the narrowed sweep gate
   would send those posts to `continue` forever (#3565).
2. `post_insurer` attribute rows (build 098 wrote `... or None`, so two
   posts carry a row holding None). Stripped.
3. The legacy single `post_blueprint` on four posts (builds 076/077).
   The sweep reads `post_blueprints[shift]` only; the legacy value is a
   duplicate of the shift entry on each of the four. Removed.
4. Maxwell's clinic register was branded "a Thawn-Harrison billing
   terminal" (build 074), an odd leftover of the premium flowing there.
   Re-keyed as Maxwell's own, keeping "billing terminal" in the key,
   which build 074's finder matches on; its register, `treatment`
   advertiser and `medic` post are untouched (owner ruling Q4).

Idempotent: every step reads before it writes and reports counts.

Run IN-GAME (idmapper):
    @py exec(open('/usr/src/game/scripts/builds/168_the_post_stops_paying_for_anyone.py').read(), {'print': self.msg})
"""

from evennia.typeclasses.attributes import Attribute
from evennia.utils.search import search_object

from world.souls.posts import get_posts

relabelled = stripped = delegacied = 0
for post in get_posts():
    if post.db.post_policy == "resleave":
        post.db.post_policy = "successor"
        relabelled += 1
    if post.attributes.has("post_insurer"):
        post.attributes.remove("post_insurer")
        stripped += 1
    legacy = post.db.post_blueprint
    if legacy is not None:
        shifts = dict(post.db.post_blueprints or {})
        if legacy not in shifts.values():
            print(f"BUILD 168: {post.key} #{post.id} legacy blueprint "
                  f"{legacy!r} names nobody's shift; left in place, look at it")
        else:
            post.attributes.remove("post_blueprint")
            delegacied += 1
print(f"BUILD 168: {relabelled} posts relabelled successor, {stripped} "
      f"post_insurer rows stripped, {delegacied} legacy post_blueprint "
      f"rows removed")

# stray rows on objects that are not posts (belt and braces)
strays = [a for a in Attribute.objects.filter(db_key="post_insurer")]
for a in strays:
    a.delete()
if strays:
    print(f"BUILD 168: {len(strays)} stray post_insurer attribute rows deleted")

front = next((r for r in search_object("Maxwell Medical Clinic")
              if r.pk and not r.destination
              and r.key == "Maxwell Medical Clinic"), None)
if front is None:
    print("BUILD 168: Maxwell front room not found; terminal left as is")
else:
    terminal = next((o for o in front.contents
                     if "billing terminal" in o.key.lower()), None)
    if terminal is None:
        print("BUILD 168: no billing terminal in the clinic; nothing to re-key")
    elif "Thawn-Harrison" not in terminal.key:
        print(f"BUILD 168: terminal #{terminal.id} already {terminal.key!r}; skipped")
    else:
        terminal.key = "a Maxwell Medical billing terminal"
        desc = terminal.db.desc or ""
        terminal.db.desc = desc.replace(
            "The Thawn-Harrison crest sits above a smaller line of type: "
            "YOUR RECOVERY IS OUR BUSINESS.",
            "The Maxwell Medical mark sits above a smaller line of type: "
            "YOUR RECOVERY IS OUR BUSINESS.")
        print(f"BUILD 168: terminal #{terminal.id} re-keyed {terminal.key!r}; "
              f"register {terminal.db.register}, post and advertiser untouched")
