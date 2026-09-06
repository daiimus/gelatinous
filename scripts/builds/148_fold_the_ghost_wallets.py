"""Build 148 — fold the ghost wallets into the real one (#2426).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/148_fold_the_ghost_wallets.py
    then a foreground reload.

`Character.tokens` is an `AttributeProperty(category="shop")`. A bare
`db.tokens` is a DIFFERENT ROW that nothing in the game reads. Two
director spawners wrote the bare one, so 40 street civilians and
witnesses walked around holding 12,728 credits that `pickpocket` answered
"is carrying no tokens" for -- while `@civilians` own help text promised
"carrying 100-500 tokens (muggable)". The souls `rob` step reads the real
property too, and terminated at 0.

`CmdTheft` already carried the diagnosis in a comment: "the REAL wallet
is the Character.tokens property (category 'shop') -- db.tokens is an
uncategorized ghost ledger this command alone used; money 'stolen' there
never existed." The READER was fixed. The writers were not.

WHAT THIS DOES. Adds each ghost balance to the real wallet and removes
the ghost row. Adding rather than overwriting, because a few of these
bodies have earned real credits since (Jody O' Fischer has 65), and
those are money the world actually gave them -- discarding either side
would be inventing a number.

Re-run-safe: a body with no ghost row is skipped, and the row is removed
as it is folded, so a second run finds nothing.
"""
from evennia.objects.models import ObjectDB


def main():
    folded = 0
    moved = 0
    skipped = []

    for obj in ObjectDB.objects.all():
        ghost = obj.attributes.get("tokens", category=None)
        if not ghost:
            continue
        # Only bodies that HAVE the real wallet — an item with a stray
        # `tokens` attribute is not a person and is left alone.
        #
        # On the INSTANCE, not the class: `tokens` is an
        # `AttributeProperty`, and `hasattr(type(obj), "tokens")`
        # evaluates the descriptor against the class, which fails and
        # made this skip all 40 bodies on the first run.
        if not hasattr(obj, "tokens"):
            skipped.append((obj.id, obj.key))
            continue
        try:
            amount = int(ghost)
        except (TypeError, ValueError):
            skipped.append((obj.id, obj.key))
            continue

        real = int(getattr(obj, "tokens", 0) or 0)
        obj.tokens = real + amount
        obj.attributes.remove("tokens", category=None)
        folded += 1
        moved += amount
        print(f"BUILD 148:   #{obj.id} {obj.key[:24]:24} "
              f"{real} + {amount} -> {obj.tokens}")

    print(f"BUILD 148: folded {folded} wallets, {moved} credits")
    if skipped:
        print(f"BUILD 148: skipped {len(skipped)} non-wallet rows: {skipped}")

    left = [o.id for o in ObjectDB.objects.all()
            if o.attributes.get("tokens", category=None)]
    print(f"BUILD 148: ghost rows remaining: {len(left)} {left[:10]}")


main()
