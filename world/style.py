"""Style motifs — the register a garment belongs to, and the register a
person dresses in (CLOTHING_TYPES_AND_STYLE_SPEC §4).

Two vocabularies ride every garment: TYPE places it on the layer
ladder (its name does that), and STYLE says what world it comes from.
A character carries style too, which turns dressing into a lookup
instead of an authored list — a generated resident can have coherent
taste without anyone writing their wardrobe by hand.

Style never gates *wearing*: anyone may put on anything. It only
drives CHOICE — what a soul buys, and what it reaches for first.
"""

#: The seven registers (owner-ruled 2026-08-20).
STYLES = ("salvage", "workwear", "clinical", "uniform", "shine",
          "street", "sealed")

#: Brands carry style: anything under these names takes this register
#: unless the garment says otherwise (the branding law earning its
#: keep — author a brand once, and every item under it is sorted).
BRAND_STYLES = {
    "longhaul": ("workwear",),
    "boiler run": ("workwear", "salvage"),
    "greenhaus": ("workwear",),
    "hive-mind": ("workwear", "sealed"),
    "thawn-harrison": ("clinical",),
    "octavia": ("clinical",),
    "noir": ("shine",),
    "awe": ("street",),
    "anchor": ("street",),
}

#: Failing a brand, the garment's own words place it. Checked in this
#: order, first hit wins, so a "surgical mask" reads clinical before it
#: reads street.
STYLE_KEYWORDS = (
    ("clinical", ("scrub", "surgical", "lab coat", "labcoat", "clinic",
                  "medical", "cryo", "nutrient", "autodoc")),
    ("sealed", ("respirator", "rebreather", "slicker", "tox", "sealed",
                "wader", "hazard", "filter", "gas ")),
    ("uniform", ("constabulary", "duty", "uniform", "service", "badge",
                 "corporate", "company", "dress shirt", "necktie",
                 "blazer", "oxford")),
    ("workwear", ("work", "coverall", "apron", "harness", "hi-vis",
                  "hi-viz", "pit ", "mining", "grip", "canvas",
                  "slaughter", "butcher", "rubber", "steel-toed",
                  "brass-toed", "utility")),
    ("shine", ("silk", "satin", "mesh", "halter", "heel", "slip",
               "evening", "sheath", "vinyl", "lace", "choker", "gilt",
               "sequin", "velvet", "crepe", "pencil skirt", "slit")),
    ("salvage", ("scuffed", "patched", "mended", "scrap", "salvage",
                 "battered", "stopped watch", "wig", "cut")),
)

#: What a resident wears when nothing else claims them.
DEFAULT_STYLE = ("street",)


def derive_style(name, desc=""):
    """Best-guess register for a garment.

    The NAME decides, the way it decides the layer. Descriptions were
    tried and are far too noisy — half the wardrobe mentions work,
    service or scuffing somewhere in its prose, which made flannel
    shirts read as workwear and shower sandals as uniform. Brands are
    the one exception: they are proper nouns, so they can be spotted
    anywhere without false positives.
    """
    brandhay = f"{name or ''} {desc or ''}".lower()
    for brand, styles in BRAND_STYLES.items():
        if brand in brandhay:
            return tuple(styles)
    low = (name or "").lower()
    for style, words in STYLE_KEYWORDS:
        if any(word in low for word in words):
            return (style,)
    return DEFAULT_STYLE


def style_of(obj):
    """A garment's declared style, deriving (without writing) if unset."""
    declared = obj.attributes.get("style") if obj.attributes else None
    if declared:
        return tuple(declared)
    return derive_style(getattr(obj, "key", ""),
                        obj.attributes.get("desc") if obj.attributes else "")


def style_of_character(char):
    """What this person dresses in. Unset reads as street — the colony's
    ordinary register, and the honest default for someone nobody has
    written a wardrobe for yet."""
    declared = char.db.style if char and char.db else None
    return tuple(declared) if declared else DEFAULT_STYLE


def affinity(garment_styles, wearer_styles):
    """How much this garment reads as this person: 2 for a direct hit,
    1 for the colony-default street register (which fits anyone), 0 for
    somebody else's world."""
    garment = set(garment_styles or ())
    wearer = set(wearer_styles or ())
    if garment & wearer:
        return 2
    if "street" in garment:
        return 1
    return 0


#: Roles the colony already knows about, mapped to how they dress.
#: Departments (SKILLS_AND_DESIGNATION_SPEC) will supersede this once
#: the manifest lands; until then, a soul's job is the best signal we
#: actually have.
ROLE_STYLES = {
    "doctor": ("clinical",),
    "medic": ("clinical",),
    "secunit": ("uniform",),
    "dispatch": ("uniform",),
    "bartender": ("shine",),
    "companion": ("shine",),
    "dj": ("shine",),
    "butcher": ("workwear",),
    "vendor": ("workwear",),
    "grower": ("workwear",),
    "shopkeeper": ("street",),
    "worker": ("workwear",),
}


def roll_style(role=None, rng=None):
    """A style for somebody nobody authored. Role first — a doctor
    dresses clinical whatever else is true of them — then the street
    and salvage the colony is mostly made of."""
    import random as _random

    rng = rng or _random
    if role and role in ROLE_STYLES:
        return tuple(ROLE_STYLES[role])
    return (rng.choices(("street", "salvage", "workwear", "shine"),
                        weights=(5, 3, 3, 1))[0],)

# ---------------------------------------------------------------------
# PRESENTATION — the second axis (owner-ruled 2026-08-20)
# ---------------------------------------------------------------------
#
# Style says which world a garment comes from; presentation says which
# line it cuts. They are orthogonal: `shine` + femme is the slit skirt,
# `shine` unmarked is the Rook's black silk.
#
# THREE RULES, and they are the whole point:
#
#   1. It describes the GARMENT, never the wearer. There is no table
#      anywhere of what a body may put on.
#   2. It never gates. Anyone wears anything; presentation only shapes
#      what a soul reaches for first.
#   3. A character's leaning is its OWN attribute, rolled independently
#      of `sex`. Deriving it from sex would have built exactly the
#      stereotype machine this design exists to avoid — so a
#      male-sexed arrival may lean femme, and the game dresses him that
#      way without comment.
#
# All three readings are FIRST-CLASS and derive on their own terms.
# The data will skew femme/neutral — most masc-coded silhouettes are
# already carried by the style registers, since an evening suit reads
# `shine` and heavy boots read `workwear` — but that is an observation
# about this colony's wardrobe, not a property of the system. A
# necktie and a pair of boxers read masc exactly as a shawl and a pair
# of panties read femme, and a character may lean any of the three.
#
# And it is a READING, not an essence: this is how the colony sees the
# garment, which is culture, and culture is allowed to be different
# somewhere else.

PRESENTATIONS = ("femme", "masc", "neutral")   # unmarked reads neutral

#: Names that carry a femme reading in this colony.
FEMME_KEYWORDS = (
    "skirt", "dress", "gown", "blouse", "halter", "heels", "heeled",
    "slip", "sheath", "stockings", "tights", "bra", "panties", "camisole",
    "corset", "bodice", "shawl", "sheer",
)

#: And a masc one. Shorter by nature rather than by neglect: this
#: colony's masc-coded clothing mostly reads through its REGISTER
#: instead — a suit is `shine`, a slaughter apron is `workwear` — so
#: only garments whose cut is the marked thing land here.
MASC_KEYWORDS = (
    "necktie", "bow tie", "cravat", "cummerbund", "tuxedo",
    "three-piece", "waistcoat", "boxers", "y-fronts", "boxer briefs",
    "binder", "flat cap",
)


def presentation_of(obj):
    """A garment's declared presentation, deriving from its name when
    unset. Absence of a mark means neutral, which is most clothing."""
    declared = obj.attributes.get("presentation") if obj.attributes else None
    if declared:
        return tuple(declared)
    return derive_presentation(getattr(obj, "key", ""))


#: Compounds that borrow a marked word without inheriting its reading.
#: A dress shirt is not a dress; the third time this codebase has been
#: bitten by substrings (a "brass-toed boot" once read as a bra).
NOT_MARKED = ("dress shirt", "dress trousers", "dress boots",
              "dress uniform", "slip-on", "slipper")


def derive_presentation(name):
    """Which line this garment's cut reads as. Unmarked is neutral,
    which is most clothing and not a lesser answer."""
    import re

    low = (name or "").lower()
    for phrase in NOT_MARKED:
        low = low.replace(phrase, " ")
    for reading, words in (("femme", FEMME_KEYWORDS),
                           ("masc", MASC_KEYWORDS)):
        for word in words:
            if re.search(r"\b" + re.escape(word), low):
                return (reading,)
    return ()


def presentation_of_character(char):
    """What this person dresses toward. Unset means no leaning, which
    is not the same as neutral clothing — it means they simply don't
    weight the axis."""
    declared = char.db.presents if char and char.db else None
    return tuple(declared) if declared else ()


def presentation_affinity(garment_pres, wearer_pres):
    """1 when the garment's line matches what this person dresses
    toward, 0 otherwise. Deliberately smaller than style affinity: what
    world you dress from matters more than which line you cut."""
    if not wearer_pres:
        return 0                      # no leaning: the axis is silent
    if set(garment_pres or ()) & set(wearer_pres):
        return 1
    if not garment_pres and "neutral" in wearer_pres:
        return 1
    return 0


def roll_presentation(rng=None):
    """A leaning for somebody nobody authored — rolled INDEPENDENTLY of
    sex, on purpose (rule 3 above). Most people don't weight the axis
    much; some dress decidedly one way."""
    import random as _random

    rng = rng or _random
    pick = rng.choices(("", "femme", "masc", "neutral"),
                       weights=(5, 3, 2, 2))[0]
    return (pick,) if pick else ()

# ---------------------------------------------------------------------
# TYPE — the layer ladder, derived from a garment's own name
# ---------------------------------------------------------------------
#
# The convention that makes "name it a coat and it layers like a coat"
# true at runtime, rather than once in a migration script. Collisions
# resolve two ways, and the order matters:
#
#   1. An EXPLICIT layer always wins. Authors keep control; this only
#      answers when nobody said.
#   2. Among keywords, the LONGEST match wins — the most specific
#      reading of the name. "hooded labcoat" is a labcoat (outer), not
#      a hood (shell); "boot socks" are socks (skin), not boots.
#   3. Equal-length matches at different rungs fall to the INNER one,
#      which is the safer error: a garment worn too far in blocks
#      nothing, while one worn too far out blocks everything beneath.
#   4. No match at all reads as base, the rung most clothing occupies.

RUNGS = {
    0: ("bra", "briefs", "boxers", "panties", "thong", "g-string",
        "underwear", "undershirt", "sock", "socks", "stocking",
        "stockings", "tights"),
    1: ("shirt", "tee", "t-shirt", "tshirt", "blouse", "henley", "tank",
        "top", "trousers", "pants", "jeans", "skirt", "dress",
        "jumpsuit", "leggings", "suit", "wig", "bodysuit", "slip"),
    2: ("vest", "waistcoat", "hoodie", "sweater", "jumper", "cardigan",
        "glasses", "sunglasses", "shades", "mirrorshades", "mask",
        "respirator", "rebreather", "balaclava", "carrier", "lenses"),
    3: ("jacket", "windbreaker", "blazer", "harness", "hood", "slicker",
        "cut"),
    4: ("coat", "labcoat", "trench", "overcoat", "topcoat", "greatcoat",
        "duster", "robe", "apron", "scrubs", "coverall", "parka",
        "bathrobe", "cloak", "poncho"),
    5: ("boot", "boots", "shoe", "shoes", "sneaker", "sneakers", "oxford",
        "oxfords", "wader", "waders", "sandal", "sandals", "loafer",
        "heel", "heels", "slipper", "slippers", "clog", "clogs", "belt",
        "tie", "necktie", "scarf", "shawl", "bandana", "bandanna",
        "armband", "badge", "glove", "gloves", "hat", "cap", "helmet",
        "choker", "garter", "garters", "watch", "chrono", "wrap",
        "collar", "earpiece", "goggles"),
}

#: The rung a garment lands on when its name says nothing.
DEFAULT_RUNG = 1


def derive_rung(name):
    """Which rung this garment's NAME puts it on, or None when nothing
    in the name claims it."""
    import re

    low = (name or "").lower()
    best = None                       # (length, -rung) -> most specific
    for rung, words in RUNGS.items():
        for word in words:
            if re.search(r"\b" + re.escape(word) + r"\b", low):
                score = (len(word), -rung)
                if best is None or score > best[0]:
                    best = (score, rung)
    return best[1] if best else None

