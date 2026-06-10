"""Runtime-tier cache helpers.

Implements the "plain runtime dict + explicit flush" pattern from
``specs/STORAGE_PATTERNS_AUDIT_AND_REMEDIATION_SPEC.md``: load a
persisted ``db.X`` cache into an in-memory dict on first read, mutate
that dict freely without descriptor / pickle round-trips, push back to
``db.X`` only at meaningful boundaries.

Why this exists: the recognition caches (disguise pierce, forensic,
diagnose, autopsy) all live on a carrier object's ``db.X`` slot and
were rewritten on every miss inside ``get_display_name``'s hot path.
The pattern below cuts that to one descriptor read per object lifetime
(lazy load) plus one descriptor write per flush boundary.

Usage:

    from world.runtime_caches import (
        get_runtime_cache,
        flush_runtime_cache,
        register_runtime_cache,
    )

    cache = get_runtime_cache(carrier, "disguise_pierce_cache")
    cache[(target_dbref, apparent_uid)] = success

    # later, at a flush boundary:
    flush_runtime_cache(carrier, "disguise_pierce_cache")

The runtime dict is stored on the carrier as ``_runtime_<attr_name>``
— a plain Python instance attribute, no descriptor protocol.  Reads
of the cache after the lazy load are dict lookups; only the initial
load and the explicit flush hit ``db.X``.

``register_runtime_cache`` registers the (carrier, attr) pair on a
module-level set so the global flush hook (``flush_all_runtime_caches``
called from ``at_server_shutdown``) can sweep every active cache
without each callsite wiring its own teardown.

**Caveat — concurrent sessions.** A runtime cache is process-local.
Two sessions for the same character on the same server share the
runtime dict because they share the typeclass instance.  Two
processes (which we don't run) would diverge until the next flush.
Acceptable for our deployment model.
"""
from __future__ import annotations

import weakref
from typing import Any, Iterable


# Registered (id(carrier), attr_name) → weakref(carrier) entries.
# A regular dict avoids the "no extant strong reference" problem
# WeakSet runs into when nothing outside the registry holds the key,
# while the weakref values let us detect garbage-collected carriers
# lazily on next sweep.  Carriers that don't support weakrefs
# (rare — most Python objects do) fall back to a strong reference.
_REGISTRY: dict[tuple[int, str], Any] = {}


def _make_ref(carrier: Any) -> Any:
    """Return a weakref to ``carrier`` if supported, else the
    carrier itself.  Either way, ``_deref`` knows how to unwrap."""
    try:
        return weakref.ref(carrier)
    except TypeError:
        return carrier


def _deref(ref: Any) -> Any:
    """Unwrap whatever ``_make_ref`` produced."""
    if isinstance(ref, weakref.ref):
        return ref()
    return ref


def _runtime_attr_name(attr_name: str) -> str:
    """Mangle ``"disguise_pierce_cache"`` →
    ``"_runtime_disguise_pierce_cache"``."""
    return f"_runtime_{attr_name}"


def get_runtime_cache(carrier: Any, attr_name: str) -> dict:
    """Return a runtime dict for ``carrier.db.<attr_name>``.

    First call lazily loads the persisted dict into
    ``carrier._runtime_<attr_name>``; subsequent calls return the
    in-memory dict directly.  Callers mutate the returned dict
    freely; nothing is written back until
    :func:`flush_runtime_cache` runs.

    Args:
        carrier: Any object with a ``db`` accessor.
        attr_name: The persisted attribute name (e.g.
            ``"disguise_pierce_cache"``).

    Returns:
        A plain ``dict`` that aliases the runtime cache — mutations
        are visible to all readers on this process.
    """
    runtime_name = _runtime_attr_name(attr_name)
    cache = getattr(carrier, runtime_name, None)
    if cache is None:
        db = getattr(carrier, "db", None)
        persisted = getattr(db, attr_name, None) if db is not None else None
        # ``_SaverDict`` doesn't satisfy ``isinstance(persisted, dict)``
        # but supports ``.items()``.  Build a plain dict from the
        # iterable view so mutation cost stays off the descriptor
        # path.  Anything that doesn't expose items lands as empty.
        if persisted is None:
            cache = {}
        elif hasattr(persisted, "items"):
            cache = dict(persisted.items())
        else:
            cache = {}
        setattr(carrier, runtime_name, cache)
        register_runtime_cache(carrier, attr_name)
    return cache


def flush_runtime_cache(carrier: Any, attr_name: str) -> None:
    """Push ``carrier._runtime_<attr_name>`` back to
    ``carrier.db.<attr_name>``.

    No-op when the runtime cache was never loaded (no work done →
    nothing to persist).  Safe to call at any boundary; the cost is
    one descriptor write.
    """
    runtime_name = _runtime_attr_name(attr_name)
    cache = getattr(carrier, runtime_name, None)
    if cache is None:
        return
    db = getattr(carrier, "db", None)
    if db is None:
        return
    setattr(db, attr_name, dict(cache))


def register_runtime_cache(carrier: Any, attr_name: str) -> None:
    """Add ``(carrier, attr_name)`` to the global flush registry.

    Called automatically by :func:`get_runtime_cache` on lazy load;
    expose it here for callers that want to pre-register a cache
    before any read has happened (rare).
    """
    _REGISTRY[(id(carrier), attr_name)] = _make_ref(carrier)


def unregister_runtime_cache(carrier: Any, attr_name: str) -> None:
    """Drop a registered cache without flushing.

    Used by invalidation paths that intentionally discard the runtime
    state (e.g. when a sleeve UID changes and stale pierce results
    should not be persisted).  Pair with :func:`drop_runtime_cache`
    if you also want the runtime attribute cleared.
    """
    _REGISTRY.pop((id(carrier), attr_name), None)


def drop_runtime_cache(carrier: Any, attr_name: str) -> None:
    """Clear the runtime cache without flushing.

    Wipes ``carrier._runtime_<attr_name>`` so the next read lazy-
    loads from ``db.X`` afresh.  Useful for invalidation paths.
    """
    runtime_name = _runtime_attr_name(attr_name)
    if hasattr(carrier, runtime_name):
        try:
            delattr(carrier, runtime_name)
        except AttributeError:
            # __slots__ or descriptor-managed attrs may resist; tolerate.
            setattr(carrier, runtime_name, None)
    unregister_runtime_cache(carrier, attr_name)


def flush_all_runtime_caches() -> int:
    """Flush every registered runtime cache.

    Intended for ``at_server_shutdown`` and ``at_post_unpuppet``
    hooks.  Returns the count of flushed entries — useful for
    logging.  Carriers whose weakref has died are pruned during
    the sweep (lazy GC of stale entries).
    """
    count = 0
    dead_keys = []
    # Snapshot the items so the prune doesn't mutate during iteration.
    for key, ref in list(_REGISTRY.items()):
        carrier = _deref(ref)
        if carrier is None:
            dead_keys.append(key)
            continue
        _, attr_name = key
        flush_runtime_cache(carrier, attr_name)
        count += 1
    for key in dead_keys:
        _REGISTRY.pop(key, None)
    return count


def registered_caches() -> Iterable[tuple]:
    """Inspector — yields ``(carrier, attr_name)`` for every live
    registration.  Prunes dead weakrefs during iteration.  Primarily
    for tests and diagnostics."""
    dead_keys = []
    for key, ref in list(_REGISTRY.items()):
        carrier = _deref(ref)
        if carrier is None:
            dead_keys.append(key)
            continue
        _, attr_name = key
        yield (carrier, attr_name)
    for key in dead_keys:
        _REGISTRY.pop(key, None)
