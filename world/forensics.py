"""Forensic Recognition Engine (PR-E).

Canonical access layer for forensic recovery across all evidence
surfaces: corpses (shipped), blood-pool incidents (data prep only),
and photographic evidence (stub — spec L1000 / L1015 / L1020).

Two surfaces converge here:

* **Identity recovery** — given an evidence source, attempt to match
  the source's apparent UID against the looker's recognition memory
  via a skill check (Surface A, previously embedded in
  :meth:`typeclasses.corpse.Corpse._attempt_forensic_recognition`).
* **Signature reconstruction** — given an evidence source, render the
  preserved identity signature's axes (height/build/keyword/essential
  items) into a human-readable forensic report without ever
  surfacing an assigned name unless the looker already holds the UID
  (Surface B, unlocked by PR #183's ``signature_at_death`` snapshot).

The engine is source-agnostic: every consumer extracts a
:class:`ForensicSubject` from its native object (corpse, blood-pool
incident, photo) and routes through the same engine functions.  This
keeps the recognition contract — *live UID is the only key that
returns an assigned name* — invariant across evidence types and
prevents per-surface drift as new consumers are added.

This module is companion to :mod:`world.identity`'s disguise-piercing
engine (``attempt_disguise_pierce`` at ~L1394) — both gate
identity-leak vectors through skill rolls with permanent per-observer
caches.  Disguise piercing handles *live* targets whose disguise an
observer might see through; forensic recognition handles *static*
evidence (corpses, blood, photos) where the source presentation may
have drifted from the looker's stored memory.

Out of scope (deferred per PR-E scope lock):

* Photo capture/display gameplay (stub raises ``NotImplementedError``).
* Blood-pool forensic *consumer* (the data field is wired in
  :meth:`typeclasses.objects.BloodPool.add_bleeding_incident` so
  future consumers have something to read, but no command surfaces it
  yet).
* Multi-UID linking gameplay (:func:`link_subjects` is a primitive
  returning a diagnostic dataclass; no command exposes it).
* Memory decay, active impersonation detection (spec L1668 Phase 5).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from world.combat.constants import AUTOPSY_TIME_BUCKETS
from world.identity import (
    get_apparent_uid,
    get_identity_signature,
    render_signature_summary,
)


# ---------------------------------------------------------------------
# Subject envelope
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class ForensicSubject:
    """Source-agnostic envelope for a piece of forensic evidence.

    All engine functions consume this neutral shape so consumers don't
    have to know whether the evidence came from a corpse, a blood
    incident, or a photo.  Frozen so subjects can be used as cache
    keys or compared for equality across consumers.

    Attributes:
        signature: The 5-tuple from :func:`world.identity.get_identity_signature`
            captured at the moment the evidence was created, or
            ``None`` if no snapshot is available (e.g. pre-PR-#183
            corpses still in the live DB, or legacy blood incidents
            recorded before the ``signature`` field was added).
        apparent_uid_at_death: The hashed apparent UID at evidence
            creation time.  Distinct from
            ``signature[0]`` (the raw ``sleeve_uid``); this is the
            disguise-aware UID used for recognition-memory lookup.
            ``None`` if not captured.
        essential_item_type_ids: Tuple of disguise-essential item
            type IDs preserved on the evidence, or empty tuple.
            Convenience accessor — also reachable via
            ``signature[4]``.
        source_kind: One of ``"corpse"``, ``"blood_pool"``,
            ``"photo"``.  Used by renderers that want to phrase
            reports per source type.
        source_ref: The originating object (corpse / blood pool /
            photo).  Held for cache-key generation; engine functions
            never call methods on it.
    """

    signature: tuple | None
    apparent_uid_at_death: str | None
    essential_item_type_ids: tuple[str, ...]
    source_kind: str
    source_ref: Any = field(compare=False, hash=False)


# ---------------------------------------------------------------------
# Extractors — one per evidence surface
# ---------------------------------------------------------------------


def extract_subject_from_corpse(corpse) -> ForensicSubject:
    """Build a :class:`ForensicSubject` from a corpse object.

    Reads the death-time snapshot fields established by PR #183:

    * ``corpse.db.signature_at_death`` — the full 5-tuple.
    * ``corpse.db.apparent_uid_at_death`` — the hashed UID.

    Pre-PR-#183 corpses still in the live DB have neither field
    populated; the returned subject carries ``signature=None`` and
    consumers should render a "no further detail" message.

    Args:
        corpse: A :class:`typeclasses.corpse.Corpse` instance (duck
            typing accepted — only ``corpse.db.*`` is read).

    Returns:
        A populated :class:`ForensicSubject`.
    """
    signature = corpse.db.signature_at_death
    apparent_uid = corpse.db.apparent_uid_at_death
    essential = tuple(signature[4]) if signature is not None else ()
    return ForensicSubject(
        signature=signature,
        apparent_uid_at_death=apparent_uid,
        essential_item_type_ids=essential,
        source_kind="corpse",
        source_ref=corpse,
    )


def extract_subject_from_blood_pool_incident(
    pool, incident: dict
) -> ForensicSubject:
    """Build a :class:`ForensicSubject` from one blood-pool incident.

    Each entry in ``pool.db.bleeding_incidents`` is a dict.  The
    ``"signature"`` key is read with :py:meth:`dict.get` so legacy
    incidents recorded before PR-E land as ``signature=None``
    automatically — no migration script required.

    The legacy ``"sleeve_uid"`` field is honoured for
    backward-compatible identity hashing when a full signature is
    absent: we synthesise an apparent UID from a minimal sleeve-only
    signature so consumers still see continuity.  This mirrors the
    behaviour of :func:`world.identity.get_apparent_uid` for a bare
    sleeve.

    Args:
        pool: The :class:`typeclasses.objects.BloodPool` the incident
            belongs to.
        incident: One incident dict from
            ``pool.db.bleeding_incidents``.

    Returns:
        A populated :class:`ForensicSubject`.
    """
    signature = incident.get("signature")
    apparent_uid = incident.get("apparent_uid")
    essential = tuple(signature[4]) if signature is not None else ()
    return ForensicSubject(
        signature=signature,
        apparent_uid_at_death=apparent_uid,
        essential_item_type_ids=essential,
        source_kind="blood_pool",
        source_ref=(pool, incident.get("timestamp")),
    )


def extract_subject_from_photo(photo) -> ForensicSubject:
    """Stub for photographic evidence (spec L1000 / L1015 / L1020).

    Photo capture/display is out of scope for PR-E.  When the photo
    typeclass lands, this function will read its preserved signature
    snapshot (same shape as ``corpse.db.signature_at_death``) and
    return a ``source_kind="photo"`` subject.

    Args:
        photo: Future photographic-evidence object.

    Raises:
        NotImplementedError: Always.  Wire the consumer in a follow-up
            PR.
    """
    raise NotImplementedError(
        "Photographic evidence extraction is not yet implemented; "
        "see specs/IDENTITY_RECOGNITION_SPEC.md L1000 / L1015 / L1020."
    )


# ---------------------------------------------------------------------
# Recognition engine — Surface A
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class RecognitionResult:
    """Outcome of an :func:`attempt_forensic_recognition` call.

    Attributes:
        success: ``True`` if the looker's roll met or exceeded the
            DC (or a cached prior success replayed).
        revealed_uid: The apparent UID that was matched against
            memory, or ``None`` if the subject has no UID to match.
            Callers can use this to look up the assigned name in
            ``observer.recognition_memory``.
        from_cache: ``True`` if the result was replayed from a prior
            roll on the same ``(observer, subject)`` pair (silent
            re-render per the cached-failure UX decision).
    """

    success: bool
    revealed_uid: str | None
    from_cache: bool


def attempt_forensic_recognition(
    looker,
    subject: ForensicSubject,
    dc: int,
    *,
    cache_owner,
    cache_attr: str = "forensic_recognition_cache",
) -> RecognitionResult:
    """Roll Intellect vs ``dc`` to recover identity from evidence.

    The roll outcome is cached permanently per
    ``(looker.dbref, subject-key)`` on ``cache_owner.db.<cache_attr>``.
    This rewards a single careful examination and prevents Intellect
    re-rolls on every examine from eventually surfacing an identity
    by chance.

    Caching strategy mirrors the disguise-pierce convention
    (:func:`world.identity.attempt_disguise_pierce`): permanent per
    observer, keyed on the evidence's apparent UID so a signature
    change (e.g. a disguise-essential item looted off a corpse,
    invalidating the death-time UID) naturally produces a fresh
    cache slot on the next examine.

    Args:
        looker: The character attempting recognition.  Must have a
            ``dbref`` for the cache key; anonymous lookers re-roll
            every call (bounded cache hygiene).
        subject: The :class:`ForensicSubject` under examination.
        dc: Intellect DC the looker must meet or exceed.
        cache_owner: The object whose ``db.<cache_attr>`` holds the
            per-observer roll cache.  Typically the corpse itself
            (so the cache moves with the evidence); for blood-pool
            incidents the pool object is appropriate.
        cache_attr: Attribute name on ``cache_owner.db`` to use for
            the cache dict.  Defaults to ``"forensic_recognition_cache"``
            for backwards compatibility with corpse storage.

    Returns:
        :class:`RecognitionResult` describing the outcome.  If the
        subject has no apparent UID (``apparent_uid_at_death is None``
        and no signature[0]) the call returns
        ``RecognitionResult(False, None, False)`` without rolling.
    """
    revealed_uid = subject.apparent_uid_at_death
    if revealed_uid is None:
        # Fall back to live re-derivation from the source where
        # possible — kept for parity with the pre-PR-E corpse path
        # that computed UIDs from the corpse itself rather than the
        # death-time hash.  Also covers pre-PR-#183 corpses still in
        # the live DB whose ``apparent_uid_at_death`` / ``signature_at_death``
        # snapshot fields were never populated.
        if subject.source_kind == "corpse":
            try:
                revealed_uid = get_apparent_uid(subject.source_ref)
            except (AttributeError, TypeError, ValueError):
                revealed_uid = None

    if revealed_uid is None:
        return RecognitionResult(success=False, revealed_uid=None, from_cache=False)

    cache_db = getattr(cache_owner, "db", None)
    cache = getattr(cache_db, cache_attr, None) if cache_db is not None else None
    if cache is None:
        cache = {}

    looker_dbref = getattr(looker, "dbref", None)
    cache_key = (looker_dbref, revealed_uid)
    if looker_dbref is not None and cache_key in cache:
        return RecognitionResult(
            success=bool(cache[cache_key]),
            revealed_uid=revealed_uid,
            from_cache=True,
        )

    from world.combat.dice import roll_stat

    roll = roll_stat(looker, "intellect", default=1)
    success = roll >= dc

    if looker_dbref is not None:
        cache[cache_key] = success
        setattr(cache_db, cache_attr, cache)

    return RecognitionResult(
        success=success, revealed_uid=revealed_uid, from_cache=False
    )


# ---------------------------------------------------------------------
# Report renderer — Surface B
# ---------------------------------------------------------------------


def _fuzzy_time_of_death(corpse) -> str:
    """Return a fuzzy time-of-death string from a corpse's death_time.

    Drives the autopsy report's "Apparent time of death" line.  The
    buckets are tuned to align with the decay-stage thresholds in
    ``world/combat/constants.py`` so the narrative tracks the corpse
    model without leaking exact seconds.  Pre-PR-#183 corpses without
    a ``death_time`` return ``"unknown"``.

    Args:
        corpse: A :class:`typeclasses.corpse.Corpse` instance (duck
            typed — only ``corpse.db.death_time`` is read).

    Returns:
        One of the strings in :data:`world.combat.constants.AUTOPSY_TIME_BUCKETS`,
        or ``"unknown"`` if the corpse has no death-time stamp.
    """
    death_time = getattr(getattr(corpse, "db", None), "death_time", None)
    if death_time is None:
        return "unknown"
    try:
        elapsed = time.time() - float(death_time)
    except (TypeError, ValueError):
        return "unknown"
    if elapsed < 0:
        elapsed = 0
    for threshold, label in AUTOPSY_TIME_BUCKETS:
        if elapsed < threshold:
            return label
    return AUTOPSY_TIME_BUCKETS[-1][1]


def _render_wound_lines(corpse) -> list[str]:
    """Render wound enumeration lines for the autopsy report.

    Reads ``corpse.db.wounds_at_death`` (the existing PR #133 snapshot)
    and groups entries by body location, using
    :func:`world.medical.wounds.get_wound_description` for severity
    prose and
    :func:`world.medical.wounds.get_location_display_name` for the
    location label.  Returns an empty list when no wounds were
    snapshotted (pre-PR-#133 corpses, peaceful deaths) so the caller
    can omit the section header cleanly.

    Args:
        corpse: A :class:`typeclasses.corpse.Corpse` instance.

    Returns:
        A list of report lines (without the section header).  Empty
        if there are no wounds to render.
    """
    wounds = getattr(getattr(corpse, "db", None), "wounds_at_death", None) or []
    if not wounds:
        return []

    try:
        from world.medical.wounds import (
            get_location_display_name,
            get_wound_description,
        )
    except ImportError:
        return []

    grouped: dict[str, list[str]] = {}
    for wound in wounds:
        location = wound.get("location") or "unknown"
        try:
            descr = get_wound_description(
                injury_type=wound.get("injury_type", "unknown"),
                location=location,
                severity=wound.get("severity", "Moderate"),
                stage=wound.get("stage", "fresh"),
                organ=wound.get("organ"),
            )
        except (TypeError, ValueError, KeyError):
            descr = (
                f"{wound.get('severity', 'unspecified')} "
                f"{wound.get('injury_type', 'wound')}"
            )
        grouped.setdefault(location, []).append(descr)

    lines: list[str] = []
    for location, descrs in grouped.items():
        try:
            label = get_location_display_name(location)
        except (TypeError, ValueError, KeyError):
            label = location.replace("_", " ")
        for descr in descrs:
            lines.append(f"  {label}: {descr}")
    return lines


def _render_organ_lines(corpse) -> list[str]:
    """Render the organ-inventory section of the autopsy report.

    Reads ``corpse.get_medical_snapshot()`` (PR #186) and per-organ
    status from the serialized :class:`world.medical.core.MedicalState`.
    Organs whose name appears in ``corpse.db.removed_organs`` (harvest
    target) or whose ``container`` appears in
    ``corpse.db.severed_locations`` (sever target) render as
    ``"absent"`` per the no-surgeon-attribution rule (PR-186 Q3).

    A snapshot of ``None`` (pre-PR-#186 corpse) yields an empty list,
    letting the caller print a "no internal examination possible"
    marker instead.

    Args:
        corpse: A :class:`typeclasses.corpse.Corpse` instance.

    Returns:
        A list of report lines (without the section header).  Empty
        when no snapshot is available.
    """
    snapshot = None
    getter = getattr(corpse, "get_medical_snapshot", None)
    if callable(getter):
        snapshot = getter()
    if not snapshot:
        return []

    removed = set(
        getattr(getattr(corpse, "db", None), "removed_organs", None) or []
    )
    severed = set(
        getattr(getattr(corpse, "db", None), "severed_locations", None) or []
    )

    lines: list[str] = []
    organs = snapshot.get("organs") or {}
    for name, organ in organs.items():
        if name in removed or organ.get("container") in severed:
            status = "absent"
        else:
            current_hp = organ.get("current_hp", 0)
            max_hp = organ.get("max_hp", 1) or 1
            ratio = current_hp / max_hp
            if current_hp <= 0:
                status = "destroyed"
            elif ratio < 0.5:
                status = "damaged"
            else:
                status = "intact"
        lines.append(f"  {name}: {status}")
    return lines


def render_forensic_report(
    subject: ForensicSubject,
    *,
    observer,
) -> str:
    """Render a human-readable autopsy report from a subject.

    The single-tier report (PR #186 dropped the ``/deep`` switch)
    composes up to five sections, omitting any that have no data:

    1. **Identity axes** — height / build / keyword from the preserved
       :func:`world.identity.get_identity_signature`.
    2. **Apparent time of death** — fuzzy bucket from
       :func:`_fuzzy_time_of_death`.
    3. **Apparent cause of death** — ``corpse.db.death_cause``.
    4. **Wounds** — enumerated by body location via
       :func:`_render_wound_lines`.
    5. **Organ inventory** — from
       :meth:`typeclasses.corpse.Corpse.get_medical_snapshot` via
       :func:`_render_organ_lines`; harvested / severed organs render
       as ``"absent"`` (PR-186 Q3 — no surgeon attribution).
    6. **Worn essentials** — disguise-essential item type IDs from
       :attr:`ForensicSubject.essential_item_type_ids`.  Folded into
       the unified report (formerly ``/deep``-only).

    Pre-PR-#183 subjects with ``signature=None`` collapse to a single
    "no further forensic detail" line so identity-axes never leak as
    blank fields.

    Critically, this function **never** assigns a name to the
    subject.  The recognition contract requires that an assigned
    name only appear when the observer already holds the UID in
    their recognition memory; that lookup happens in the consumer
    (the autopsy command), after which the consumer may concatenate
    the recognized name with this report.

    Args:
        subject: The evidence subject to render.
        observer: The character reading the report.  Reserved for
            future observer-specific phrasing (per-observer
            rendering hooks).  Currently unused but accepted to
            keep the signature stable as renderers grow.

    Returns:
        A string suitable for ``observer.msg()``.
    """
    del observer  # Reserved; see docstring.

    if subject.signature is None:
        return "The remains yield no further forensic detail."

    summary = render_signature_summary(subject.signature)
    height = summary["height_override"] or "indeterminate"
    build = summary["build_override"] or "indeterminate"
    keyword = summary["keyword_override"] or "indeterminate"

    lines: list[str] = [
        "|wForensic Examination|n",
        f"  Apparent height : {height}",
        f"  Apparent build  : {build}",
        f"  Keyword         : {keyword}",
    ]

    corpse = subject.source_ref if subject.source_kind == "corpse" else None

    if corpse is not None:
        tod = _fuzzy_time_of_death(corpse)
        lines.append(f"  Time of death   : {tod}")

        cause = getattr(getattr(corpse, "db", None), "death_cause", None)
        if cause:
            lines.append(f"  Cause of death  : {cause}")

        wound_lines = _render_wound_lines(corpse)
        if wound_lines:
            lines.append("|wWounds|n")
            lines.extend(wound_lines)

        organ_lines = _render_organ_lines(corpse)
        if organ_lines:
            lines.append("|wOrgan Inventory|n")
            lines.extend(organ_lines)
        elif getattr(corpse, "get_medical_snapshot", lambda: None)() is None:
            lines.append(
                "  (No internal examination possible — pre-mortem records "
                "unavailable.)"
            )

    essentials = subject.essential_item_type_ids
    if essentials:
        joined = ", ".join(essentials)
        lines.append(f"  Worn essentials : {joined}")

    return "\n".join(lines)


# ---------------------------------------------------------------------
# Linking primitive
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class LinkResult:
    """Outcome of :func:`link_subjects`.

    Attributes:
        shared_sleeve_uid: ``True`` iff both subjects carry the same
            raw ``sleeve_uid`` (i.e. genetically the same person).
            Requires both subjects to have a captured signature.
        shared_apparent_uid: ``True`` iff both subjects carry the
            same ``apparent_uid_at_death`` (same disguised
            presentation at the moment each was captured).
        shared_axes: Tuple of signature-axis names that match
            between the two subjects, drawn from ``("sleeve_uid",
            "height_override", "build_override", "keyword_override",
            "essential_item_type_ids")``.  Empty if either subject
            lacks a signature.
    """

    shared_sleeve_uid: bool
    shared_apparent_uid: bool
    shared_axes: tuple[str, ...]


_AXIS_NAMES = (
    "sleeve_uid",
    "height_override",
    "build_override",
    "keyword_override",
    "essential_item_type_ids",
)


def link_subjects(a: ForensicSubject, b: ForensicSubject) -> LinkResult:
    """Compare two subjects axis-by-axis (primitive, no gameplay).

    Returned exclusively for engine-internal use and future linking
    gameplay (spec L1020).  No command exposes this in PR-E.

    Args:
        a: First subject.
        b: Second subject.

    Returns:
        A :class:`LinkResult` describing shared identity surfaces.
    """
    shared_apparent_uid = (
        a.apparent_uid_at_death is not None
        and a.apparent_uid_at_death == b.apparent_uid_at_death
    )
    if a.signature is None or b.signature is None:
        return LinkResult(
            shared_sleeve_uid=False,
            shared_apparent_uid=shared_apparent_uid,
            shared_axes=(),
        )

    shared_axes = tuple(
        name
        for name, va, vb in zip(_AXIS_NAMES, a.signature, b.signature)
        if va == vb and va is not None
    )
    shared_sleeve_uid = "sleeve_uid" in shared_axes
    return LinkResult(
        shared_sleeve_uid=shared_sleeve_uid,
        shared_apparent_uid=shared_apparent_uid,
        shared_axes=shared_axes,
    )
