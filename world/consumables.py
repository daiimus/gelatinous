"""Generic consumable-item lifecycle helpers.

A consumable is any item that carries ``uses_left`` and ``max_uses``
attributes and gets destroyed when its remaining uses reach zero.
Cigarettes, medical bandages, pills, vials, drinks, food — same
shape, same decrement-and-delete logic.

This module hosts the single decrement helper that every consumable
verb in the codebase should delegate to.  Callers that need
specialised flavor on destruction wrap with a callback rather than
forking the helper.

See ``specs/SUBSTANCES_AND_DELIVERY_SPEC.md`` for the architectural
context — this is the lowest layer in the item → substance →
delivery stack.
"""
from __future__ import annotations

from typing import Callable, Optional

#: Tag category for delivery-method tags — ``("eat", "delivery_method")``,
#: ``("inject", ...)``, etc.  See SUBSTANCES_AND_DELIVERY_SPEC §2/§4.
DELIVERY_METHOD_CATEGORY = "delivery_method"

#: Pre-#474 medical items declared *how they enter the body* via their
#: ``medical_type`` string (which also keys their pharmacology).  This
#: table maps each legacy type to the delivery method(s) the old
#: command gates accepted, so already-spawned items self-heal to tags
#: on first use.  ``medical_type`` itself stays — it remains the
#: pharmacology key for the treatment system.
LEGACY_MEDICAL_TYPE_DELIVERIES: dict[str, tuple[str, ...]] = {
    # CmdInject's old injectable_types
    "pain_relief": ("inject",),
    "blood_restoration": ("inject",),
    "stimulant": ("inject",),
    "toxin": ("inject",),
    # CmdApply's old applicable_types (wound_care doubled as a
    # bandage type)
    "burn_treatment": ("apply",),
    "antiseptic": ("apply",),
    "healing_salve": ("apply",),
    "wound_care": ("apply", "bandage"),
    "fracture_treatment": ("apply",),
    "organ_repair": ("apply",),
    # CmdBandage's old bandage_types
    "bandage": ("bandage",),
    "gauze": ("bandage",),
    # CmdEat's old edible_types
    "pill": ("eat",),
    "tablet": ("eat",),
    "food": ("eat",),
    "ration": ("eat",),
    "medicine": ("eat",),
    # CmdDrink's old liquid_types
    "liquid_medicine": ("drink",),
    "water": ("drink",),
    "alcohol": ("drink",),
    "potion": ("drink",),
    "drink": ("drink",),
    # CmdInhale's old inhalable_types
    "oxygen": ("inhale",),
    "anesthetic": ("inhale",),
    "inhaler": ("inhale",),
    "gas": ("inhale",),
    "vapor": ("inhale",),
    # The retired CmdConsumption.CmdSmoke's smokable_types — mapped
    # to the canonical smoke delivery so old medicinal herbs work
    # with commands/CmdSmoke.py (flavor-only until they get a
    # ``substance`` id).
    "herb": ("smoke",),
    "cigarette": ("smoke",),
    "medicinal_plant": ("smoke",),
    "dried_medicine": ("smoke",),
}


def supports_delivery(item, method: str) -> bool:
    """True when ``item`` supports the ``method`` delivery verb.

    The delivery check for every consumption command (eat / drink /
    inhale / inject / apply / bandage / smoke).  Reads the
    ``(method, "delivery_method")`` tag; items that predate the tag
    scheme are self-healed from their legacy ``medical_type`` —
    the implied tags are written back so the migration happens once
    per item (the ``is_smokable`` pattern from #456).
    """
    if item is None:
        return False
    tags = getattr(item, "tags", None)
    if tags is None:
        return False
    if tags.has(method, category=DELIVERY_METHOD_CATEGORY):
        return True
    # Legacy migration: derive delivery tags from medical_type once.
    attributes = getattr(item, "attributes", None)
    if attributes is None:
        return False
    medical_type = attributes.get("medical_type", "")
    implied = LEGACY_MEDICAL_TYPE_DELIVERIES.get(medical_type, ())
    if implied:
        for verb in implied:
            tags.add(verb, category=DELIVERY_METHOD_CATEGORY)
        return method in implied
    return False


def consume_use(
    item,
    *,
    on_destroy: Optional[Callable] = None,
) -> dict:
    """Decrement ``item``'s ``uses_left`` by one, delete on zero.

    Args:
        item: The consumable to decrement.  Must expose
            ``item.attributes`` with ``.get(key, default)`` and
            ``.add(key, value)`` semantics matching Evennia's
            ``AttributeHandler``.
        on_destroy: Optional zero-arg callable invoked just before
            the item is deleted.  Use for "tossed away" / "crumbles"
            broadcasts — the helper does not emit any messages of
            its own.

    Returns:
        ``{"success": bool, "destroyed": bool}``.  ``success=False``
        when the item had zero uses left to begin with (or no
        ``attributes`` surface); ``destroyed=True`` when the call
        consumed the final use and the item is now gone.
    """
    attrs = getattr(item, "attributes", None)
    if attrs is None:
        return {"success": False, "destroyed": False}
    uses_left = int(attrs.get("uses_left", 0) or 0)
    if uses_left <= 0:
        return {"success": False, "destroyed": False}
    uses_left -= 1
    attrs.add("uses_left", uses_left)
    if uses_left <= 0:
        if on_destroy is not None:
            try:
                on_destroy()
            except Exception:
                # A bad on_destroy callback should not prevent the
                # item from being deleted — the lifecycle invariant
                # (zero uses ⇒ gone) is more important.
                pass
        try:
            item.delete()
        except AttributeError:
            pass
        return {"success": True, "destroyed": True}
    return {"success": True, "destroyed": False}
