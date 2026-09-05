"""Compose an NPC persona dict from its live object fields, for the LLM sidecar.

Runs on the reactor (reads ``db`` + identity getters) and returns plain,
JSON-safe data handed to the off-reactor sidecar call (``world/llm/client.py``).
The builder-authored **immutable core** (manner / wants / boundaries) lives in
``db.llm_persona``; everything else is derived from the NPC's real identity so the
model voices *this* character — the same sdesc/longdesc/voice the world perceives.

See ``specs/proposals/LLM_GAMEMASTER_SPEC.md`` §5.2 (persona card).
"""

from evennia.utils.dbserialize import deserialize

from world.grammar import transform_pronoun
from world.identity import get_apparent_gender
from world.voice import get_voice_description, get_voice_ending, voice_phrase


def _self_pronouns(npc) -> str:
    """The NPC's own subject/object pronouns ("he/him") from the SAME canonical
    gender derivation the emote/identity engine uses (``get_apparent_gender`` ->
    ``transform_pronoun``), so the persona never disagrees with how the world
    renders this character's gender. Falls back to they/them on any hiccup."""
    try:
        gender = get_apparent_gender(npc)
        return (f"{transform_pronoun('I', 'third', gender)}/"
                f"{transform_pronoun('me', 'third', gender)}")
    except Exception:  # noqa: BLE001 — never break persona-building over pronouns
        return "they/them"


def _wardrobe(npc) -> tuple:
    """(wearing, carrying, wielding, hands_free): worn garments — with their
    live style state, so the model knows what's zipped/rolled and what the
    `style` tool can act on — the STASHED inventory, what's in the NPC's HANDS
    right now (Mr. Hands: held-is-wielded), and how many grasping slots are free.
    This is the NPC's real self-knowledge of its own kit; without it the model
    invents clothing it isn't wearing or talks about a weapon as if it's already
    drawn when it's stashed."""
    wearing, carrying, wielding, hands_free = [], [], [], None
    try:
        worn = list(npc.get_worn_items() or [])
        for item in worn:
            entry = item.key
            props = getattr(item, "style_properties", None) or {}
            states = sorted(str(v) for v in props.values() if v and v != "normal")
            if states:
                entry += f" ({', '.join(states)})"
            wearing.append(entry)
        worn_ids = {id(i) for i in worn}
        # Mr. Hands: `hands` is {container: item_or_None}. Held items are in
        # hand (wielded), distinct from stashed carry; count the empty slots
        # so the model knows if it has a free hand to draw INTO.
        hands = npc.hands or {}
        held_ids = set()
        hands_free = 0
        for container, item in hands.items():
            if item:
                wielding.append(f"{item.key} (in {str(container).replace('_', ' ')})")
                held_ids.add(id(item))
            else:
                hands_free += 1
        carrying = [obj.key for obj in npc.contents
                    if id(obj) not in worn_ids and id(obj) not in held_ids]
    except Exception:  # noqa: BLE001 — never break persona-building over kit
        pass
    return wearing, carrying, wielding, hands_free


def _room_desc(npc) -> str | None:
    """The room as THIS NPC perceives it — ``get_display_desc`` composes the
    sense layers for the looker (a blind NPC doesn't get the visual prose), so
    the model grounds itself in the street it's actually standing on instead
    of inventing a generic interior. ANSI-stripped, sentence-bounded trim."""
    loc = npc.location
    if not loc:
        return None
    try:
        getter = getattr(loc, "get_display_desc", None)
        raw = getter(npc) if callable(getter) else None
        raw = raw or getattr(loc.db, "desc", None)
        if not raw:
            return None
        from evennia.utils.ansi import strip_ansi
        text = " ".join(strip_ansi(str(raw)).split())
        if len(text) > 500:
            cut = text[:500]
            for end in (". ", "! ", "? "):
                i = cut.rfind(end)
                if i > 200:
                    cut = cut[: i + 1]
                    break
            text = cut.rstrip()
        return text
    except Exception:  # noqa: BLE001 — never break persona-building over a room
        return None


def build_persona(npc) -> dict:
    """Build the persona dict from the NPC's real fields. Defensive throughout.

    Must run on the reactor (reads db + identity getters). The returned dict is
    inert JSON passed to the sidecar thread — no live objects leak across.
    """
    longdescs = {}
    raw = getattr(npc, "longdesc", None) or {}
    for loc in raw:
        desc = npc.get_longdesc(loc)
        if desc:
            longdescs[loc] = desc

    location = None
    if npc.location:
        location = {
            "name": npc.location.key,
            "desc": _room_desc(npc),
        }

    # The board they are actually working, so they know exactly what they
    # serve (and what they don't) — and never fake pouring something
    # off-list. Read off the POST rather than a typeclass method, so a
    # successor standing the bar is grounded in it too (#2352).
    from world import service
    post = service.post_for(npc)
    menu = None
    board = (post.db.menu if post is not None else None)
    if not board:
        find_bar = getattr(npc, "_find_bar", None)
        bar = find_bar() if callable(find_bar) else None
        board = (bar.db.menu if bar else None) or npc.db.menu or []
    menu = [r.get("name") for r in (board or []) if r.get("name")] or None

    # The butcher's real trade, same grounding principle: the cart's ACTUAL
    # board (live shop stock + prices) and what she buys — without these the
    # model invents stock ("sushi pork") and meats she's never carried.
    cart_menu = None
    buys = None
    find_block = getattr(npc, "_find_block", None)
    if callable(find_block):
        try:
            from world.butchery import ACCEPTED_BUTCHER_SPECIES
            buys = sorted(ACCEPTED_BUTCHER_SPECIES)
            block = find_block()
            if block is not None:
                stock = block.db.item_inventory or {}
                prices = block.db.prototype_inventory or {}
                from evennia.prototypes.prototypes import search_prototype
                entries = []
                for proto_key, count in stock.items():
                    if int(count or 0) <= 0:
                        continue
                    protos = search_prototype(proto_key)
                    name = (protos[0].get("key") if protos else None) or proto_key
                    price = prices.get(proto_key)
                    entries.append(f"{name} ({price} tokens, {count} left)")
                cart_menu = entries   # [] = sold out; rendered explicitly
        except Exception:  # noqa: BLE001 — persona building never breaks on trade
            cart_menu, buys = None, None

    # The shopkeeper's real shelf, same grounding principle as the cart:
    # without it the keeper invents stock and prices.
    shop_menu = None
    find_counter = getattr(npc, "_find_counter", None)
    if callable(find_counter):
        try:
            counter = find_counter()
            if counter is not None:
                from evennia.prototypes.prototypes import search_prototype
                inv = counter.db.prototype_inventory or {}
                stock = counter.db.item_inventory or {}
                infinite = bool(counter.db.is_infinite)
                entries = []
                for proto_key, price in inv.items():
                    protos = search_prototype(proto_key)
                    name = (protos[0].get("key") if protos else None) or proto_key
                    if infinite:
                        entries.append(f"{name} ({price} tokens)")
                    else:
                        count = int(stock.get(proto_key, 0) or 0)
                        if count > 0:
                            entries.append(f"{name} ({price} tokens, "
                                           f"{count} left)")
                shop_menu = entries
        except Exception:  # noqa: BLE001 — persona building never breaks on trade
            shop_menu = None

    wearing, carrying, wielding, hands_free = _wardrobe(npc)

    # Radio state (RADIO_COMMS_SPEC §7.3): what the brain can key up with —
    # a worn/held powered walkie, or a built-in comms organ. None = no way
    # onto the air (the radio tool would refuse, so don't advertise it).
    radio = None
    try:
        from world.radio import (
            active_transmit_radio, comms_organ_frequency, frequency_of,
            is_powered,
        )
        device = active_transmit_radio(npc)
        if device is not None and is_powered(device):
            band = frequency_of(device)
            radio = (f"a radio tuned to {band}" if band
                     else "a radio tuned to nothing")
        else:
            band = comms_organ_frequency(npc)
            if band:
                radio = f"a built-in comms module tuned to {band}"
    except Exception:  # noqa: BLE001 — persona building never breaks on comms
        radio = None

    return {
        "radio": radio,
        "sdesc": npc.get_sdesc(),
        "wearing": wearing,
        "carrying": carrying,
        "wielding": wielding,
        "hands_free": hands_free,
        "longdescs": longdescs,
        "skintone": getattr(npc.db, "skintone", None),
        "height": npc.height,
        "build": npc.build,
        "sex": npc.sex,
        "pronouns": _self_pronouns(npc),   # canonical self-gender (he/him, …)
        "species": npc.species,
        "voice": voice_phrase(npc),
        "voice_description": get_voice_description(npc),
        "voice_ending": get_voice_ending(npc),
        "location": location,
        "menu": menu,
        "cart_menu": cart_menu,
        "buys": buys,
        "shop_menu": shop_menu,
        # deserialize → plain dict/list (the seed's nested mes_example is a
        # _SaverDict/_SaverList off the DB, which json.dumps can't serialize).
        "persona_seed": deserialize(npc.db.llm_persona) or {},
        # THE JOB BEATS THE SEED. A blueprint says who somebody is; the
        # post says what they are doing right now, and the second is what
        # a patron is talking to. Without this a successor stands behind
        # the bar prompted as a generic colonist, with a colonist's tool
        # grant — no `check_stock`, no `prepare_drink` (#2352). Off shift
        # it resolves to None and they are simply themselves again.
        "archetype": service.archetype_for(npc),
    }
