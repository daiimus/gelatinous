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
