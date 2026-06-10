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
