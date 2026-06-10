"""Smoke system — cigarette / pack / lighter helpers + flavor banks.

Issue #454.  Hosts the brand-specific message banks for the
``light`` / ``smoke`` / ``snuff`` commands and the small helpers
that those commands need: held-item lookups and the
``"bob's cigarette"`` possessive parser.

Conventions:

* Each message bank entry is a ``(self_text, room_template)`` tuple.
  The room template uses ``{actor}`` (and ``{target}`` where another
  character is involved) for per-observer rendering via
  :func:`world.identity_utils.msg_room_identity`.
* Brands are arbitrary strings; unknown brands fall back to
  :data:`BRAND_NEUTRAL`.
* Lit-state lives on cigarettes as a Tag (category
  ``cigarette_state``) — AGENTS.md prefers Tags for booleans.
"""
from __future__ import annotations

import random
from typing import Optional


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

#: Tag namespaces.
CIGARETTE_STATE_CATEGORY = "cigarette_state"
ITEM_ROLE_CATEGORY = "item_role"

#: Item-role tags.  ``light`` and ``smoke`` use these to identify
#: cigarettes / lighters by role rather than by typeclass, so
#: prototype-defined items don't need a bespoke typeclass.
CIGARETTE_ROLE = "cigarette"
LIGHTER_ROLE = "lighter"

#: Lit-state tag carried on individual cigarettes.
LIT_TAG = "lit"

#: Default puffs per cigarette.
DEFAULT_CIGARETTE_PUFFS = 6

#: Default cigarettes per pack.
DEFAULT_PACK_CAPACITY = 10

#: Brand identifiers.  Add more here when new brands arrive; banks
#: below are keyed by these constants.
BRAND_NEUTRAL = "neutral"
BRAND_NOIR = "noir"


# ---------------------------------------------------------------------
# Smoke message banks
# ---------------------------------------------------------------------

#: Per-brand smoke flavor.  ``smoke <cigarette>`` picks a random
#: entry; the actor receives the ``self`` form and the room gets the
#: ``room`` template rendered through :func:`msg_room_identity`.
SMOKE_MESSAGES: dict[str, list[tuple[str, str]]] = {
    BRAND_NEUTRAL: [
        (
            "You draw deeply from your cigarette, the ember flaring "
            "briefly as you inhale, before slowly releasing a thick "
            "plume of smoke into the air.",
            "{actor} draws deeply from their cigarette, the ember "
            "flaring briefly as they inhale, before slowly releasing "
            "a thick plume of smoke into the air.",
        ),
        (
            "You take a slow, deliberate puff from your cigarette, "
            "savoring the taste before exhaling a swirling mist of "
            "smoke.",
            "{actor} takes a slow, deliberate puff from their "
            "cigarette, savoring the taste before exhaling a "
            "swirling mist of smoke.",
        ),
        (
            "With a flick of your wrist, you take a long drag, the "
            "smoke curling around you like a wisp of memory before "
            "fading into the air.",
            "With a flick of their wrist, {actor} takes a long drag, "
            "the smoke curling around them like a wisp of memory "
            "before fading into the air.",
        ),
        (
            "You inhale deeply from the glowing tip of your "
            "cigarette, holding the smoke in your lungs for a moment "
            "before releasing a ghostly exhale.",
            "{actor} inhales deeply from the glowing tip of their "
            "cigarette, holding the smoke in their lungs for a "
            "moment before releasing a ghostly exhale.",
        ),
        (
            "You take another drag from your cigarette, the smoke "
            "twisting lazily from your lips as you watch it dance in "
            "the dim light.",
            "{actor} takes another drag from their cigarette, the "
            "smoke twisting lazily from their lips as they watch it "
            "dance in the dim light.",
        ),
        (
            "You pull in a slow breath, the warm smoke filling your "
            "chest, before exhaling in a long stream, the air thick "
            "with the scent of tobacco.",
            "{actor} pulls in a slow breath, the warm smoke filling "
            "their chest, before exhaling in a long stream, the air "
            "thick with the scent of tobacco.",
        ),
        (
            "The cigarette burns steadily between your fingers, and "
            "you take a casual drag, exhaling with a slight smile as "
            "the smoke drifts away.",
            "The cigarette burns steadily between {actor}'s fingers, "
            "and they take a casual drag, exhaling with a slight "
            "smile as the smoke drifts away.",
        ),
        (
            "You take a short, sharp drag, feeling the smoke hit the "
            "back of your throat before you push it out, watching "
            "the haze linger.",
            "{actor} takes a short, sharp drag, feeling the smoke "
            "hit the back of their throat before they push it out, "
            "watching the haze linger.",
        ),
        (
            "A soft ember glows as you take a deep pull from your "
            "cigarette, letting the smoke seep from your mouth like "
            "a slow, smoky sigh.",
            "A soft ember glows as {actor} takes a deep pull from "
            "their cigarette, letting the smoke seep from their "
            "mouth like a slow, smoky sigh.",
        ),
        (
            "You take a drag, the warmth of the cigarette creeping "
            "into your fingers as the smoke rises lazily, twisting "
            "in the air like a fading thought.",
            "{actor} takes a drag, the warmth of the cigarette "
            "creeping into their fingers as the smoke rises lazily, "
            "twisting in the air like a fading thought.",
        ),
        (
            "The smoke from your cigarette swirls around you as you "
            "inhale deeply, the taste sharp and bitter on your "
            "tongue before you exhale in a long, slow breath.",
            "The smoke from {actor}'s cigarette swirls around them "
            "as they inhale deeply, the taste sharp and bitter on "
            "their tongue before they exhale in a long, slow breath.",
        ),
        (
            "You flick the ash from your cigarette and take another "
            "long pull, feeling the familiar burn of smoke fill your "
            "lungs before exhaling it into the night.",
            "{actor} flicks the ash from their cigarette and takes "
            "another long pull, feeling the familiar burn of smoke "
            "fill their lungs before exhaling it into the night.",
        ),
        (
            "You inhale deeply, the cigarette's ember glowing "
            "brighter, and release a thick cloud of smoke that "
            "lingers in the air like a fading memory.",
            "{actor} inhales deeply, the cigarette's ember glowing "
            "brighter, and releases a thick cloud of smoke that "
            "lingers in the air like a fading memory.",
        ),
        (
            "You take a slow drag from your cigarette, the smoke "
            "filling your senses before you let it escape in a "
            "gentle, steady stream.",
            "{actor} takes a slow drag from their cigarette, the "
            "smoke filling their senses before they let it escape "
            "in a gentle, steady stream.",
        ),
    ],
    BRAND_NOIR: [
        (
            "You drag on your cigarette, the smoke curling around "
            "your fingers like a secret you're not ready to share. "
            "It leaves a bitter taste, but you're used to it by now.",
            "{actor} drags on their cigarette, the smoke curling "
            "around their fingers like a secret they're not ready "
            "to share. It leaves a bitter taste, but they look used "
            "to it by now.",
        ),
        (
            "The glow of the cigarette flares in the dim light, "
            "casting long shadows on the walls as you take a slow, "
            "deliberate puff. The smoke hangs in the air like the "
            "promise of something dangerous.",
            "The glow of {actor}'s cigarette flares in the dim "
            "light, casting long shadows on the walls as they take "
            "a slow, deliberate puff. The smoke hangs in the air "
            "like the promise of something dangerous.",
        ),
        (
            "The first drag fills your lungs, thick and heavy. You "
            "exhale slowly, letting the smoke mingle with the "
            "tension in the room.",
            "The drag fills {actor}'s lungs, thick and heavy. They "
            "exhale slowly, letting the smoke mingle with the "
            "tension in the room.",
        ),
        (
            "The cigarette burns between your lips, a small red "
            "beacon in the darkness. You take a long drag, and the "
            "smoke seems to hang around you, like a fog that won't "
            "lift.",
            "The cigarette burns between {actor}'s lips, a small "
            "red beacon in the darkness. They take a long drag, and "
            "the smoke seems to hang around them, like a fog that "
            "won't lift.",
        ),
        (
            "You flick the ash off your cigarette with a practiced "
            "hand, the embers glowing like a tiny flame in a world "
            "gone cold. A slow drag, and you exhale, watching the "
            "smoke swirl — just like the lies you've been fed.",
            "{actor} flicks the ash off their cigarette with a "
            "practiced hand, the embers glowing like a tiny flame "
            "in a world gone cold. A slow drag, and they exhale, "
            "watching the smoke swirl — just like the lies they've "
            "been fed.",
        ),
        (
            "You take a deep pull from the cigarette, the smoke "
            "searing the back of your throat as you exhale, watching "
            "it rise like a ghost disappearing into the night. It's "
            "the kind of night that feels like trouble.",
            "{actor} takes a deep pull from the cigarette, the smoke "
            "searing the back of their throat as they exhale, "
            "watching it rise like a ghost disappearing into the "
            "night. It's the kind of night that feels like trouble.",
        ),
        (
            "You inhale slowly, the smoke thick and heavy on your "
            "tongue. It feels like it might choke you, but you're "
            "no stranger to suffocating things. The haze leaves a "
            "bitter taste, just like your past.",
            "{actor} inhales slowly, the smoke thick and heavy on "
            "their tongue. It looks like it might choke them, but "
            "they're no stranger to suffocating things. The haze "
            "leaves a bitter taste, just like their past.",
        ),
        (
            "You take a long drag, the smoke swirling around you "
            "like a bad decision you can't undo. The night's dark, "
            "but the cigarette's glow is brighter than your future.",
            "{actor} takes a long drag, the smoke swirling around "
            "them like a bad decision they can't undo. The night's "
            "dark, but the cigarette's glow is brighter than their "
            "future.",
        ),
        (
            "The cigarette burns slow and steady, much like the "
            "minutes of your life ticking away. You pull in a drag, "
            "feeling the heat spread through your chest before "
            "letting it spill out, mixing with the stagnant air.",
            "The cigarette burns slow and steady, much like the "
            "minutes of {actor}'s life ticking away. They pull in a "
            "drag, the heat spreading through their chest before "
            "they let it spill out, mixing with the stagnant air.",
        ),
        (
            "You drag hard on the cigarette, the ember glowing like "
            "a warning in the quiet of the room. The smoke leaks "
            "from your lips, curling into the shadows, as if trying "
            "to escape.",
            "{actor} drags hard on the cigarette, the ember glowing "
            "like a warning in the quiet of the room. The smoke "
            "leaks from their lips, curling into the shadows, as if "
            "trying to escape.",
        ),
        (
            "A slow drag, and the smoke hits your lungs like the "
            "weight of a decision you'll regret.",
            "A slow drag, and the smoke hits {actor}'s lungs like "
            "the weight of a decision they'll regret.",
        ),
        (
            "The cigarette hangs loosely between your fingers, the "
            "end glowing red like a mark of sin. You inhale, the "
            "smoke bitter, and release it with a sigh that carries "
            "more than just tobacco.",
            "The cigarette hangs loosely between {actor}'s fingers, "
            "the end glowing red like a mark of sin. They inhale, "
            "the smoke bitter, and release it with a sigh that "
            "carries more than just tobacco.",
        ),
        (
            "You draw from the cigarette, the heat of the ember "
            "matching the heat in your chest. You let the smoke "
            "slip from your mouth, as though you're exhaling all "
            "the things you can't say.",
            "{actor} draws from the cigarette, the heat of the "
            "ember matching the heat in their chest. They let the "
            "smoke slip from their mouth, as though they're "
            "exhaling all the things they can't say.",
        ),
        (
            "You take a drag, slow and deliberate, like you're "
            "buying time. The smoke rolls from your lips in lazy "
            "spirals, but the tension in the air's tight enough to "
            "snap.",
            "{actor} takes a drag, slow and deliberate, like "
            "they're buying time. The smoke rolls from their lips "
            "in lazy spirals, but the tension in the air's tight "
            "enough to snap.",
        ),
        (
            "You take a long drag, the smoke filling your lungs "
            "like a promise made in the dark. Exhale, and the cloud "
            "lingers, thick with regret and unspoken words.",
            "{actor} takes a long drag, the smoke filling their "
            "lungs like a promise made in the dark. They exhale, "
            "and the cloud lingers, thick with regret and unspoken "
            "words.",
        ),
    ],
}


# ---------------------------------------------------------------------
# Light / snuff / burnout banks (brand-agnostic for v1)
# ---------------------------------------------------------------------

#: Self-light flavor (caller lights their own cigarette).
LIGHT_SELF_MESSAGES: list[tuple[str, str]] = [
    (
        "You flick open your lighter, the flame catching the tip of "
        "the cigarette. A soft glow blooms in the dark.",
        "{actor} flicks open their lighter, the flame catching the "
        "tip of the cigarette. A soft glow blooms in the dark.",
    ),
    (
        "You strike a flame and bring it to the cigarette, the "
        "paper catching with a quiet hiss.",
        "{actor} strikes a flame and brings it to their cigarette, "
        "the paper catching with a quiet hiss.",
    ),
    (
        "Your thumb works the lighter; the cigarette tip catches and "
        "glows alive.",
        "{actor}'s thumb works the lighter; the cigarette tip "
        "catches and glows alive.",
    ),
]

#: Cross-character light (caller lights target's cigarette).  Uses
#: ``{target}`` placeholder in addition to ``{actor}``.
LIGHT_OTHER_MESSAGES: list[tuple[str, str, str]] = [
    # (caller_self, target_self, room_template)
    (
        "You lean in and light {target}'s cigarette, the flame "
        "briefly painting their face.",
        "{actor} leans in and lights your cigarette, the flame "
        "briefly painting your face.",
        "{actor} leans in and lights {target}'s cigarette, the "
        "flame briefly painting their face.",
    ),
    (
        "You cup the lighter and bring it to {target}'s cigarette; "
        "the tip catches.",
        "{actor} cups their lighter and brings it to your "
        "cigarette; the tip catches.",
        "{actor} cups their lighter and brings it to {target}'s "
        "cigarette; the tip catches.",
    ),
    (
        "Your lighter sparks; you offer the flame to {target}'s "
        "cigarette and it takes.",
        "{actor}'s lighter sparks; they offer the flame to your "
        "cigarette and it takes.",
        "{actor}'s lighter sparks; they offer the flame to "
        "{target}'s cigarette and it takes.",
    ),
]

#: Snuff flavor (caller extinguishes their own cigarette).
SNUFF_MESSAGES: list[tuple[str, str]] = [
    (
        "You crush the cigarette out, the ember dying with a faint "
        "hiss.",
        "{actor} crushes their cigarette out, the ember dying with "
        "a faint hiss.",
    ),
    (
        "You stub the cigarette against a hard surface; the smoke "
        "thins to nothing.",
        "{actor} stubs their cigarette against a hard surface; the "
        "smoke thins to nothing.",
    ),
    (
        "You pinch the lit tip until the glow fails.",
        "{actor} pinches the lit tip until the glow fails.",
    ),
]

#: Burnout flavor — cigarette consumed and discarded.
BURNT_OUT_MESSAGES: list[tuple[str, str]] = [
    (
        "You take the last drag, then flick the spent cigarette "
        "away.",
        "{actor} takes the last drag, then flicks the spent "
        "cigarette away.",
    ),
    (
        "The cigarette burns down to the filter; you toss it.",
        "{actor}'s cigarette burns down to the filter; they toss it.",
    ),
    (
        "A final pull, then the dead end of the cigarette tumbles "
        "from your fingers.",
        "A final pull, then the dead end of {actor}'s cigarette "
        "tumbles from their fingers.",
    ),
]


# ---------------------------------------------------------------------
# Pickers
# ---------------------------------------------------------------------

def pick_smoke_message(brand: str | None) -> tuple[str, str]:
    """Return a random ``(self, room_template)`` for ``brand``.

    Unknown brands fall back to :data:`BRAND_NEUTRAL`.
    """
    bank = SMOKE_MESSAGES.get(brand or BRAND_NEUTRAL) or SMOKE_MESSAGES[BRAND_NEUTRAL]
    return random.choice(bank)


def pick_light_self_message() -> tuple[str, str]:
    return random.choice(LIGHT_SELF_MESSAGES)


def pick_light_other_message() -> tuple[str, str, str]:
    return random.choice(LIGHT_OTHER_MESSAGES)


def pick_snuff_message() -> tuple[str, str]:
    return random.choice(SNUFF_MESSAGES)


def pick_burnt_out_message() -> tuple[str, str]:
    return random.choice(BURNT_OUT_MESSAGES)


# ---------------------------------------------------------------------
# Item helpers
# ---------------------------------------------------------------------

def is_cigarette(item) -> bool:
    """True when ``item`` carries the cigarette role tag."""
    if item is None:
        return False
    tags = getattr(item, "tags", None)
    if tags is None:
        return False
    return tags.has(CIGARETTE_ROLE, category=ITEM_ROLE_CATEGORY)


def is_lighter(item) -> bool:
    """True when ``item`` carries the lighter role tag."""
    if item is None:
        return False
    tags = getattr(item, "tags", None)
    if tags is None:
        return False
    return tags.has(LIGHTER_ROLE, category=ITEM_ROLE_CATEGORY)


def is_lit(cigarette) -> bool:
    """True when a cigarette currently carries the lit Tag."""
    if cigarette is None:
        return False
    tags = getattr(cigarette, "tags", None)
    if tags is None:
        return False
    return tags.has(LIT_TAG, category=CIGARETTE_STATE_CATEGORY)


def set_lit(cigarette, value: bool) -> None:
    """Add / remove the lit Tag."""
    tags = getattr(cigarette, "tags", None)
    if tags is None:
        return
    if value:
        tags.add(LIT_TAG, category=CIGARETTE_STATE_CATEGORY)
    else:
        tags.remove(LIT_TAG, category=CIGARETTE_STATE_CATEGORY)


def find_held(character, predicate) -> Optional[object]:
    """Return the first held item satisfying ``predicate``, or
    ``None``.  ``character.hands`` is a dict of slot → item / None."""
    hands = getattr(character, "hands", None)
    if not hands:
        return None
    for item in hands.values():
        if item is not None and predicate(item):
            return item
    return None


def find_held_cigarette(character) -> Optional[object]:
    """Convenience wrapper — first cigarette in ``character``'s hands."""
    return find_held(character, is_cigarette)


def find_held_lighter(character) -> Optional[object]:
    """Convenience wrapper — first lighter in ``character``'s hands."""
    return find_held(character, is_lighter)


def consume_puff(cigarette) -> dict:
    """Decrement ``cigarette.attributes['uses_left']`` by one.

    When the result reaches zero the cigarette is deleted and the
    return dict's ``destroyed`` flag is set so callers can emit the
    burnout broadcast.

    Returns:
        ``{"success": bool, "destroyed": bool}`` — ``success=False``
        when the cigarette had no puffs left to begin with.
    """
    attrs = getattr(cigarette, "attributes", None)
    if attrs is None:
        return {"success": False, "destroyed": False}
    uses_left = int(attrs.get("uses_left", 0) or 0)
    if uses_left <= 0:
        return {"success": False, "destroyed": False}
    uses_left -= 1
    attrs.add("uses_left", uses_left)
    if uses_left <= 0:
        try:
            cigarette.delete()
        except AttributeError:
            pass
        return {"success": True, "destroyed": True}
    return {"success": True, "destroyed": False}


# ---------------------------------------------------------------------
# Argument parser — "bob's cigarette" / "cigarette"
# ---------------------------------------------------------------------

def parse_possessive_target(args: str) -> tuple[str | None, str]:
    """Split ``"bob's cigarette"`` into ``("bob", "cigarette")``.

    When no possessive form is present, returns ``(None, args)`` —
    the caller is implicitly the owner.

    Whitespace is normalised; empty input returns ``(None, "")``.
    """
    raw = (args or "").strip()
    if not raw:
        return None, ""
    # Split only on the first ``"'s "`` so multi-word item names work
    # (``"bob's hand-rolled cig"``).
    if "'s " in raw:
        owner, _, item = raw.partition("'s ")
        return owner.strip(), item.strip()
    return None, raw
