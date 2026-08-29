"""Service at a post — what the job DOES, keyed by the job's name.

The competence belongs to the post, not to whoever is standing it. That
law is already written twice in this codebase: `AnsweringFixture` says
it outright ("the competence lives here; the voice belongs to whoever
holds the chair"), and the dispatch console proves it — a player who
takes the desk is the dispatcher. Venues were the one place still doing
the opposite, with `_fulfil_order` welded to `Bartender`, so the Hub and
Howl could not pour a drink on two of its three shifts: the swing and
night keepers hold the post, have the role, stand behind the bar, and
are a typeclass that never learned to serve.

A registry rather than a fixture base class, because the number of
handlers should be the number of SERVICE SHAPES, not the number of venue
typeclasses. Bartender/Shopkeeper/Butcher/Doctor were four
implementations of one shape — match a request, produce a thing, take
payment — and moving each one down onto its own fixture class would
relocate that duplication rather than collapse it. Keying on
`post_role` also handles the five posts that are ROOMS rather than
fixtures, and the counters whose class and role already disagree (the
Snailery's `BarCounter` runs `post_role="snailer"`).

Handlers register in the module that owns the state they read — bar
service lives in `world/bar.py` — exactly as `ROLE_WORK` handlers live
in the director modules they belong to. Nothing accumulates here.

    register("bartender", serve_from_board)

    handler(post, speech, patron, by) -> bool     # True if claimed
"""

#: post_role -> the whole job. The handler is only the largest part of
#: it: a job also answers to a NAME ("hey, bartender"), has a LINE it
#: gives when there is no voice to improvise one, and carries the
#: ARCHETYPE that shapes how it talks and which tools it is granted.
#:
#: All four used to live on the role typeclass, which meant a successor
#: inherited the post and none of them — the Hub and Howl's swing keeper
#: could not serve, did not answer to "bartender", said nothing at all
#: with the model off, and was prompted as a generic colonist while
#: standing behind a bar (#2352).
SERVICE = {}

#: Modules that register handlers. An import manifest, not behaviour —
#: registration has to have HAPPENED before the first patron speaks, and
#: nothing else guarantees these are imported by then. Handlers still live
#: with the state they read; only the import lives here.
PROVIDERS = ("world.bar", "world.shop.service", "world.clinic")

_loaded = False


def _ensure_loaded():
    global _loaded
    if _loaded:
        return
    _loaded = True
    from importlib import import_module
    for path in PROVIDERS:
        try:
            import_module(path)
        except Exception:  # noqa: BLE001 — one bad provider can't mute the rest
            from evennia.utils import logger
            logger.log_trace(f"service provider {path} failed to load")


def register(role, handler, aliases=(), fallback=None, archetype=None,
             tools=None):
    """Bind a job to a post role.

    Args:
        handler: ``handler(post, speech, patron, by, addressed)`` -> bool
        aliases: what the job answers to ("bartender", "barkeep")
        fallback: what it says when addressed with no voice available
        archetype: the `world/llm/prompt.ARCHETYPES` key for its register
        tools: ``{tool_name: fn(post, arg, patron, by)}`` — what the job can
            actually DO when the model calls one. The archetype GRANTS a
            tool; this is what runs it, and the two must come from the
            same place or a successor is handed `check_stock` and gets an
            empty string back (#2352).
    """
    SERVICE[role] = {"handler": handler, "aliases": tuple(aliases),
                     "fallback": fallback, "archetype": archetype,
                     "tools": dict(tools or {})}


def job_for(post):
    """The whole job record for this post, or None."""
    if post is None:
        return None
    _ensure_loaded()
    return SERVICE.get(getattr(post.db, "post_role", None))


def handler_for(post):
    """The handler this post serves through, or None."""
    job = job_for(post)
    return job.get("handler") if job else None


def post_for(worker):
    """The post *worker* is currently standing, or None.

    Their shift decides it, not their presence: `keeper_on_duty` is the
    one reading of "is this the person working here right now", shared
    with the till and the souls planner so none of them can disagree.
    Both shapes of post are searched — a fixture in the room, and the
    room itself.
    """
    room = getattr(worker, "location", None)
    if room is None:
        return None
    from world.souls.posts import keeper_on_duty
    try:
        candidates = list(room.contents) + [room]
    except Exception:  # noqa: BLE001 — an odd location must not break speech
        return None
    for obj in candidates:
        if not getattr(obj.db, "post_role", None):
            continue
        try:
            # UNBOUND counter — no shifts, no keeper — is the vending tier:
            # whoever is standing here serves. The same answer `_counter_open`
            # gives, so the planner and the counter cannot disagree about
            # whether a place with no shift structure is open.
            if not (obj.db.post_slots or obj.db.post_keeper is not None):
                return obj
            if keeper_on_duty(obj) is worker:
                return obj
        except Exception:  # noqa: BLE001 — a bad post can't break speech
            continue
    return None


def job_of(worker):
    """The job *worker* is standing right now, or None. Off shift this is
    None and they are simply themselves again — which is the point: the
    voice follows the body, and an off-duty vendor is not a vendor."""
    return job_for(post_for(worker))


def aliases_for(worker):
    """What the job this worker is standing answers to."""
    job = job_of(worker)
    return list(job["aliases"]) if job else []


def fallback_for(worker):
    """The line this job gives when addressed with no voice to answer."""
    job = job_of(worker)
    return job.get("fallback") if job else None


def archetype_for(worker):
    """The prompt archetype this worker's CURRENT job implies, or None.

    Beats whatever the persona was authored with. A blueprint says who
    somebody is; the post says what they are doing right now, and the
    second is what a patron is talking to.
    """
    job = job_of(worker)
    return job.get("archetype") if job else None


def run_tool(worker, tool, arg, patron):
    """Run a job tool for whoever is standing the post.

    Returns ``(handled, result)``. The caller must distinguish "this job
    has no such tool" from "the tool ran and returned nothing", or a
    keeper answers an empty string as though it were stock.
    """
    job = job_of(worker)
    fn = (job or {}).get("tools", {}).get(tool)
    if fn is None:
        return False, None
    try:
        return True, fn(post_for(worker), arg, patron, worker)
    except Exception:  # noqa: BLE001 — a broken tool must not eat the turn
        from evennia.utils import logger
        logger.log_trace(f"job tool {tool} failed for {worker}")
        return True, None


def serve(worker, speech, patron, addressed=False):
    """Try to fulfil *speech* as a service request at *worker*'s post.

    Returns True when the post claimed it — the caller must then stay
    quiet, because the order has been taken and answering again would
    have the tender ask what you wanted while already pouring it.

    `addressed` distinguishes a line aimed at this person from one merely
    overheard; handlers hold overheard speech to a stricter standard.
    """
    _ensure_loaded()
    post = post_for(worker)
    handler = handler_for(post)
    if handler is None:
        return False
    try:
        return bool(handler(post, speech, patron, worker, addressed=addressed))
    except Exception:  # noqa: BLE001 — a broken counter must not eat the line
        from evennia.utils import logger
        logger.log_trace(f"service handler failed at {post}")
        return False
