"""Substance layer — registry + effect pipeline (issue #458).

Middle layer of the Item → Substance → Delivery model documented
in ``specs/SUBSTANCES_AND_DELIVERY_SPEC.md``.  Items carry a
``db.substance`` id; delivery commands (smoke today, the
``CmdConsumption`` cluster after migration) resolve that id here
and call :func:`apply_substance` per dose.

Public surface:

* :class:`Substance` / :class:`SubstanceEffect` — declaration
  dataclasses.
* :data:`SUBSTANCES` — the registry dict.
* :func:`get_substance_entry` — id → entry lookup.
* :func:`apply_substance` — the effect pipeline.
"""
from world.substances.registry import (
    SUBSTANCES,
    Substance,
    SubstanceEffect,
    apply_substance,
    get_substance_entry,
)

__all__ = [
    "SUBSTANCES",
    "Substance",
    "SubstanceEffect",
    "apply_substance",
    "get_substance_entry",
]
