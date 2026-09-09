"""Typeclasses for the smoke subsystem (issue #454).

Only the pack needs custom code — it auto-spawns N cigarettes at
creation with the pack's brand baked onto each.  Cigarettes and
lighters are plain :class:`Item` instances whose role / brand /
uses-left are set via prototype attributes + Tags.
"""
from __future__ import annotations

from evennia.prototypes.spawner import spawn
from evennia.utils import delay

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

    def return_appearance(self, looker, **kwargs):
        """Look at the pack — and repair it first if it is misbranded.

        `at_object_creation` runs DURING `create_object`, before the
        spawner applies the prototype's attributes, so the fill below
        read the defensive defaults and every pack shipped neutral
        cigarettes. Live, all ten Noir packs in the colony held
        `tobacco_neutral` (#2430). The fill is idempotent, so it never
        corrected itself.

        Repairing on look means the pack fixes itself the first time
        anybody examines it, with no migration and no reliance on a hook
        the spawner has already outrun.
        """
        self._ensure_correct_fill()
        return super().return_appearance(looker, **kwargs)

    def _ensure_correct_fill(self):
        """Refill the pack if it is empty or holding the wrong substance.

        Only ever replaces cigarettes that are still IN the pack — one
        already taken out is somebody's property and is left alone.
        """
        want = self.db.substance
        if not want:
            return
        wrong = [c for c in self.contents
                 if c.db.substance is not None and c.db.substance != want]
        if wrong:
            # ONE FOR ONE. Replacing the mis-branded ones and then
            # topping the pack back up to `capacity` would hand a
            # part-smoked pack more cigarettes than it had.
            replace = len(wrong)
            for cig in wrong:
                cig.delete()
            self._fill_with_cigarettes(count=replace)
            return
        if self.contents:
            return
        # EMPTY. This is where the fill used to happen unconditionally,
        # and it is why a pack could mint cigarettes: before #2935 the
        # fill ran ONCE, from `at_object_creation`; moving the check
        # into `return_appearance` made it run on every look, and
        # "empty" cannot tell "never filled" -- the migration case this
        # exists for -- from "a player smoked them all".
        #
        # `at_object_leave` normally crushes a pack as its last
        # cigarette is drawn, but anything that empties one without
        # firing that hook (a `move_hooks=False` move, a deferred
        # delete that did not land) left a live empty pack that refilled
        # itself on the next look. Measured: a 10-pack emptied by hand
        # then looked at came back holding 10 again, and pack #4667 was
        # sitting live at 0/10 waiting to do it.
        #
        # So remember the fill instead of inferring it from being
        # non-empty.
        if not self.db.filled_once:
            self._fill_with_cigarettes()

    def _fill_with_cigarettes(self, count=None):
        """Spawn cigarettes into the pack with the pack's substance
        stamped on each.

        ``count`` defaults to ``self.db.capacity`` -- a fresh pack. The
        repair path passes the number it just deleted, so replacing
        mis-branded cigarettes cannot top a part-smoked pack back up.

        Marks the pack as filled, so a later look can tell "never
        filled" from "emptied by a player"; inferring that from being
        non-empty is what let a pack mint a fresh set on every look.
        """
        if count is None and self.contents:
            return
        proto_key = self.db.cigarette_prototype
        substance = self.db.substance
        capacity = int(self.db.capacity or 0) if count is None else int(count)
        self.db.filled_once = True
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

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        """Crush the empty pack once its last cigarette is drawn.

        ``at_object_leave`` fires while the cigarette is *still* in
        ``self.contents`` (its move hasn't committed yet), so we check
        whether anything OTHER than the leaver remains. If not, this was the
        last one — defer the delete to the next tick (``delay(0, …)``) so the
        cigarette's move finishes first and ``self.delete()`` doesn't try to
        relocate the in-flight cigarette.
        """
        super().at_object_leave(moved_obj, target_location, **kwargs)
        if any(obj is not moved_obj for obj in self.contents):
            return                              # cigarettes still inside
        taker = target_location
        if taker and hasattr(taker, "msg"):
            taker.msg(f"That's the last one — you crumple the empty "
                      f"{self.key} and toss it aside.")
        delay(0, self.delete)
