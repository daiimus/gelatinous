"""Service at a shelf — the second shape (#2350).

A shop is SOLD FROM: the keeper takes the words, finds the thing on the
shelf, and presses it into your hand. A bar is SERVED FROM: the tender
makes it and sets it down. Two different gestures over the same counter,
and the difference is the whole reason `world/service.py` keys handlers
by role rather than by fixture class.

This is the same code the `Shopkeeper` typeclass used to carry, moved so
that anyone standing the post can run it — a vendor who happens to be a
plain `LLMNpc` sells exactly as well as one who is a `Shopkeeper`. See
`world/service.py` for why the competence belongs to the post.
"""

import re

from evennia.utils import delay

from world.bar import ORDER_CUES, ORDER_FILLER
from world.service import register

#: Roles that sell off a shelf. Content vocabulary, deliberately not
#: normalised — a pawnbroker, a tobacconist and a noodle vendor do the
#: same job and the colony calls it three things (#2350).
SHELF_ROLES = ("pawnbroker", "tobacconist", "vendor")

#: What the keeper SAYS and DOES while making the same checks. The
#: sequence — stock, price, purchase, hand it over — is the shape and is
#: shared; the phrasing and the final gesture are content. A shop presses
#: the thing into your hand; a cart sets it on the board.
STYLES = {
    "shelf": {
        "out": "Out of that until the next delivery.",
        "refused": "Counter says no. Take it up with the counter.",
        "gesture": ("plucks {item} from the shelf, presses it into "
                    "{target}'s hand, and sweeps {price} into the till."),
        # a shelf may be bottomless (`is_infinite`); a cart never is
        "always_finite": False,
    },
    "board": {
        "out": "Board's out of that. Bring me a rat and it won't be.",
        "refused": "Cart says no. Take it up with the cart.",
        "gesture": ("sets {item} on the board and sweeps {price} into "
                    "the till."),
        "always_finite": True,
    },
}


def shelf_of(counter):
    """The counter's real sellable list: [(proto_key, display, words)]."""
    from evennia.prototypes.prototypes import search_prototype
    if counter is None:
        return []
    entries = []
    for proto_key in (counter.db.prototype_inventory or {}):
        protos = search_prototype(proto_key)
        if not protos:
            continue
        display = protos[0].get("key") or proto_key
        words = set(re.findall(r"[a-z']+", display.lower()))
        for alias in protos[0].get("aliases") or ():
            words.update(re.findall(r"[a-z']+", str(alias).lower()))
        entries.append((proto_key, display, words))
    return entries


def match_shelf_order(counter, speech):
    """`match_from_shelf` against this counter's shelf."""
    return match_from_shelf(shelf_of(counter), speech)


def match_from_shelf(entries, speech):
    """Resolve speech against a shelf listing — conservative (an order
    cue or a bare order; a cue-less question is conversation) with
    best-overlap scoring. Returns the prototype key, ``"ambiguous"``
    when two items tie (the keeper asks which), or None.

    Takes the LISTING rather than the counter so a keeper can pass their
    own `_shelf()`, keeping that seam intact for anyone who overrides it.
    """
    low = " ".join((speech or "").lower().split())
    if not low:
        return None
    words = re.findall(r"[a-z']+", low)
    has_cue = any(cue in low for cue in ORDER_CUES)
    if "?" in low and not has_cue:
        return None
    scored = []
    for proto_key, _display, item_words in entries:
        overlap = sum(1 for w in words
                      if w in item_words or w.rstrip("s") in item_words)
        if overlap:
            scored.append((overlap, proto_key, item_words))
    if not scored:
        return None
    scored.sort(reverse=True)
    best = scored[0]
    if len(scored) > 1 and scored[1][0] == best[0]:
        return "ambiguous"
    if has_cue:
        return best[1]
    remainder = [w for w in words
                 if w not in best[2] and w.rstrip("s") not in best[2]
                 and w not in ORDER_FILLER]
    return best[1] if not remainder else None


def serve_from_shelf(post, speech, patron, by, addressed=False,
                     style="shelf"):
    """Sell what was asked for off this counter. True if claimed.

    An ADDRESSED line still has to name something on the shelf — unlike
    the old path, which claimed every addressed line and then fell back
    to the model from inside itself. Falling through instead means "you
    been working here long?" is conversation rather than a failed
    purchase, and the mixin lands it on the scripted line when there is
    no voice to take it.
    """
    if post is None:
        return False
    match = match_shelf_order(post, speech)
    if match is None:
        return False
    delay(1.5, _fulfil_from_shelf, post, match, patron, by, style)
    return True


def _fulfil_from_shelf(post, match, patron, by, style="shelf"):
    """Stock, price, purchase, hand it over — the checks in the order a
    keeper would make them."""
    lines = STYLES.get(style, STYLES["shelf"])
    if getattr(patron, "location", None) is not getattr(by, "location", None):
        return
    if match == "ambiguous":
        by.execute_cmd("say You'll have to be more particular — the "
                       "shelf carries more than one of those.")
        return
    stock = post.db.item_inventory or {}
    finite = lines["always_finite"] or not post.db.is_infinite
    if finite and int(stock.get(match, 0) or 0) <= 0:
        by.execute_cmd(f"say {lines['out']}")
        return
    price = int(post.get_price(match) or 0)
    have = int(getattr(patron, "tokens", 0) or 0)
    if price and have < price:
        by.execute_cmd(f"say That's {price}. Come back when you've got it.")
        return
    ok, item = post.purchase_item(patron, match)
    if not ok:
        by.execute_cmd(f"say {lines['refused']}")
        return
    hand_over(by, patron, item, price, lines["gesture"])


def hand_over(by, patron, item, price, gesture=None):
    """The final gesture. A manned counter is never self-service — the
    thing reaches the buyer through somebody's hands."""
    from world.grammar import with_article
    gesture = gesture or STYLES["shelf"]["gesture"]
    handle = None
    try:
        handle = by._address_handle(patron)
    except Exception:  # noqa: BLE001 — a missing handle is not a failed sale
        pass
    by.execute_cmd("emote " + gesture.format(
        item=with_article(item.key), target=handle or "the customer",
        price=price))


def serve_from_board_cart(post, speech, patron, by, addressed=False):
    """A cart sells the same way and sets it down instead."""
    return serve_from_shelf(post, speech, patron, by, addressed,
                            style="board")


def _check_stock(post, arg, patron, by):
    """What is actually on this counter's shelf."""
    if post is None:
        return "no counter to check"
    names = [display for _, display, _ in shelf_of(post)]
    return ("On the shelf: " + ", ".join(names) + ".") if names \
        else "The shelf is empty."


for _role in SHELF_ROLES:
    register(_role, serve_from_shelf,
             aliases=("shopkeeper", "shopkeep", "merchant", "vendor"),
             fallback="Shelf's all labeled. It says what I sell.",
             archetype="merchant",
             tools={"check_stock": _check_stock})
from world.butchery import on_receive as _butcher_receive  # noqa: E402

register("butcher", serve_from_board_cart,
         on_receive=_butcher_receive,
         aliases=("butcher", "cook"),
         fallback="Board's behind me. It says what I sell.",
         archetype="butcher",
         tools={"check_stock": _check_stock})
