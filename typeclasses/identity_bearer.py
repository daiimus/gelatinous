"""Identity-bearer mixin.

Shared recognition / forensic-recovery surface for objects that carry
a death-time identity snapshot — :class:`typeclasses.corpse.Corpse`
and (post PR-#193) :class:`typeclasses.items.SeveredHead`.

The mixin is deliberately decoupled from any concrete typeclass; it
relies on a small duck-typed contract that subclasses must satisfy:

============================  ===========================================
Required member                Contract
============================  ===========================================
``self.db.signature_at_death`` 5-tuple identity signature captured at
                               the moment of bodily separation (death
                               for a corpse, sever for a head).  May be
                               ``None`` on pre-snapshot legacy objects;
                               recognition then never succeeds.
``self.db.apparent_uid_at_death`` Hashed apparent UID matching
                               ``signature_at_death``.  May be ``None``.
``get_decay_stage(self) -> str`` Returns one of ``"fresh"``, ``"early"``,
                               ``"moderate"``, ``"advanced"``,
                               ``"skeletal"``.  ``"skeletal"`` is the
                               hard cutoff — no recognition path beyond
                               it.
``_decay_display_name(self) -> str`` Fallback display name when no
                               recognition match is found
                               (e.g. ``"fresh corpse"``, ``"early head"``).
============================  ===========================================

Subclasses may override ``_FORENSIC_RECOGNITION_DC`` to tune per-stage
Intellect DCs for the forensic-recovery roll.  The default mirrors
:class:`typeclasses.corpse.Corpse`'s pre-mixin behaviour.

The recognition flow is two-pass:

1. **Natural recognition** against the *decay-degraded* apparent UID.
   At ``fresh`` and ``early`` stages the degraded UID equals the fresh
   UID, so this path covers ordinary recognition through light decay.
   At ``moderate`` and ``advanced`` the body-identity axis is blanked,
   so only loose-feature memory matches survive.
2. **Forensic recovery** against the *fresh-equivalent* UID, gated by
   a per-observer cached Intellect roll keyed off
   :data:`_FORENSIC_RECOGNITION_DC`.  Per-observer-per-bearer-permanent
   — a failed roll on first contact sticks.

See ``specs/IDENTITY_RECOGNITION_SPEC.md`` §"Identity-Bearer Mixin"
for the broader design rationale.
"""

from __future__ import annotations


class IdentityBearerMixin:
    """Two-pass recognition + forensic-recovery for snapshot-bearing objects.

    Mix into a typeclass whose instances expose the contract above.
    Provides :meth:`get_display_name` and the
    :meth:`_attempt_forensic_recognition` helper.  Subclasses still own
    ``get_decay_stage`` and ``_decay_display_name``.
    """

    #: Intellect DC by decay stage for forensic-recognition recovery.
    #: Stages absent from this map never roll: ``fresh`` / ``early``
    #: don't need recovery (the degraded UID still matches memory), and
    #: ``skeletal`` is hard-cutoff in :meth:`get_display_name` before
    #: this table is consulted.  Override in subclasses to tune.
    _FORENSIC_RECOGNITION_DC = {
        "moderate": 3,
        "advanced": 5,
    }

    def get_display_name(self, looker, **kwargs):
        """Return a display name, preferring recognition memory.

        Mirrors the corpse-recognition contract: observers who already
        remember the deceased / severed party see the decay-stage name
        followed by the assigned name in parentheses (PR-G); strangers
        and the system see only the decay-stage fallback.

        * ``looker is None`` → decay-stage fallback.
        * ``get_decay_stage() == "skeletal"`` → hard cutoff; return
          decay-stage fallback regardless of recognition memory.
        * Otherwise two-pass: natural (degraded UID) then forensic
          (fresh UID + Intellect roll).  A successful match returns
          ``"<decay name> (<assigned name>)"`` — e.g.
          ``"rotting corpse (Jorge)"`` — so the recognising observer
          still sees decay state at a glance while having the
          remembered identity surfaced.
        """
        del kwargs  # Evennia passes look context we don't need.
        decay_name = self._decay_display_name()
        assigned = self.recognised_as(looker)
        if assigned:
            return f"{decay_name} ({assigned})"
        return decay_name

    def recognised_as(self, looker):
        """The name *looker* knows these remains by, or ``None``.

        The recognition half of :meth:`get_display_name`, on its own
        (#3821), for text that names the dead inside a sentence: the
        ``{name}`` token of a preserved description, where "rotting
        corpse (Jorge)" does not fit and the real key must not go. Same
        two passes, same forensic roll and the same stored verdict, so
        the name in the prose and the name in the header cannot
        disagree.
        """
        if looker is None:
            return None
        stage = self.get_decay_stage()
        if stage == "skeletal":
            return None

        memory = getattr(looker, "recognition_memory", None)
        if not memory:
            return None

        # Pass 1: natural recognition against the decay-degraded UID.
        try:
            from world.identity import (
                get_apparent_uid,
                get_apparent_uid_for_decay,
                resolve_assigned_name,
            )
            degraded_uid = get_apparent_uid_for_decay(self, stage)
        except (AttributeError, TypeError, ValueError):
            degraded_uid = None

        # The name the looker HOLDS for that look: its own, or the one
        # of the look they watched it come from (#3811). Read by hand,
        # this found a blank for anybody who had watched the mask go on:
        # named while they stood, anonymous the moment they fell.
        if degraded_uid is not None and degraded_uid in memory:
            assigned = resolve_assigned_name(memory, degraded_uid)[0]
            if assigned:
                return assigned

        # Pass 2: forensic recovery against the fresh-equivalent UID.
        try:
            fresh_uid = get_apparent_uid(self)
        except (AttributeError, TypeError, ValueError):
            fresh_uid = None

        if (
            fresh_uid is not None
            and fresh_uid != degraded_uid
            and fresh_uid in memory
        ):
            if self._attempt_forensic_recognition(looker, stage):
                assigned = resolve_assigned_name(memory, fresh_uid)[0]
                if assigned:
                    return assigned

        return None

    def _attempt_forensic_recognition(self, looker, stage):
        """Resolve (and cache) a forensic-recognition Intellect roll.

        Per-observer, per-bearer, permanent: a looker who fails the roll
        the first time they examine this bearer will keep failing, and
        a looker who passes will keep recognising it across subsequent
        looks.  Rewards a single careful examination and prevents
        Intellect re-rolls on every ``look`` from eventually surfacing
        an identity by chance.

        Thin wrapper over
        :func:`world.forensics.attempt_forensic_recognition`.  The
        engine owns the roll and the cache; this method preserves the
        stage-DC table and the cache-attribute slot so subclasses
        sharing the slot (e.g. corpse → severed head migration) reuse
        the same cache entries.

        Args:
            looker: The character attempting recognition.
            stage: The bearer's current decay stage (used for DC).

        Returns:
            ``True`` if the looker recovers the identity, else ``False``.
        """
        dc = self._FORENSIC_RECOGNITION_DC.get(stage)
        if dc is None:
            # Stage has no defined DC — never recover.
            return False

        from world.forensics import (
            attempt_forensic_recognition,
            extract_subject_from_corpse,
        )

        subject = extract_subject_from_corpse(self)
        result = attempt_forensic_recognition(
            looker,
            subject,
            dc,
            cache_owner=self,
            cache_attr="forensic_recognition_cache",
        )
        return result.success
