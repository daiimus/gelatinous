"""Typeclasses for the smoke subsystem (issue #454).

Only the pack needs custom code — it auto-spawns N cigarettes at
creation with the pack's brand baked onto each.  Cigarettes and
lighters are plain :class:`Item` instances whose role / brand /
uses-left are set via prototype attributes + Tags.
"""
from __future__ import annotations

from evennia.prototypes.spawner import spawn

from typeclasses.items import Item
from world.smoke import (
    DEFAULT_PACK_CAPACITY,
    SUBSTANCE_TOBACCO_NEUTRAL,
)


class CigarettePack(Item):
    """A container that ships pre-filled with cigarettes of its substance.

    Pack attributes (settable via prototype):

    * ``substance`` (str) — propagated to each spawned cigarette so
      ``smoke`` picks the right flavor bank.
    * ``cigarette_prototype`` (str) — prototype key spawned to fill
      the pack (e.g. ``"CIGARETTE_NEUTRAL"``).
    * ``capacity`` (int) — how many cigarettes to spawn at creation.
      Defaults to :data:`world.smoke.DEFAULT_PACK_CAPACITY`.

    Legacy ``brand`` attribute on existing packs (pre-#456) is
    transparently honoured — it migrates to ``substance`` on first
    access via :func:`world.smoke.get_substance`.
    """

    def at_object_creation(self):
        super().at_object_creation()
        # Defensive defaults so prototypes that forget to set the
        # fields don't crash creation.  Honour legacy ``brand`` from
        # any pre-#456 packs.
        if self.db.substance is None:
            legacy_brand = self.db.brand
            self.db.substance = legacy_brand or SUBSTANCE_TOBACCO_NEUTRAL
        if self.db.capacity is None:
            self.db.capacity = DEFAULT_PACK_CAPACITY
        if self.db.cigarette_prototype is None:
            # Substance-matched default — neutral pack spawns neutral
            # cigarettes.  Override in the prototype to ship NOIR
            # cigarettes, etc.
            self.db.cigarette_prototype = "CIGARETTE_NEUTRAL"

        self._fill_with_cigarettes()

    def _fill_with_cigarettes(self):
        """Spawn ``self.db.capacity`` cigarettes into the pack with
        the pack's substance stamped on each.  No-op when the pack
        already contains cigarettes (idempotent across reloads)."""
        if self.contents:
            return
        proto_key = self.db.cigarette_prototype
        substance = self.db.substance
        capacity = int(self.db.capacity or 0)
        for _ in range(capacity):
            spawned = spawn(proto_key)
            if not spawned:
                continue
            cig = spawned[0]
            cig.location = self
            # Imprint the pack's substance on the cigarette so the
            # smoke command picks the right flavor bank even after
            # the cigarette has been removed from the pack.
            cig.db.substance = substance
