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

    handler(post, speech, patron, by, addressed) -> bool   # True if claimed
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


#: An explicit, greppable "this job answers with silence". A bare
#: `fallback=None` cannot tell a considered choice from a forgotten
#: line, and the clinic's silence IS considered — a doctor asked
#: something odd stays quiet. Pass this instead so the next role
#: registered without a line is the only one that shows up in the log
#: (#2824).
SILENT = "__silent__"


def register(role, handler, aliases=(), fallback=None, archetype=None,
             tools=None, on_receive=None):
    """Bind a job to a post role.

    Args:
        handler: ``handler(post, speech, patron, by, addressed)`` -> bool
        aliases: what the job answers to ("bartender", "barkeep")
        fallback: what it says when addressed with no voice available.
            `SILENT` means the job answers with silence ON PURPOSE.
            Omitting it entirely gets the same runtime behaviour and a
            startup warning, because a mute NPC is otherwise found by a
            player standing at a counter with the sidecar down.
        archetype: the `world/llm/prompt.ARCHETYPES` key for its register
        on_receive: ``fn(post, obj, giver, by) -> bool`` — the job's
            answer to something being HANDED to whoever stands it.
            Receiving is the one venue act that happens to a PERSON
            rather than at a counter: you put the carcass in their hands.
        tools: ``{tool_name: fn(post, arg, patron, by)}`` — what the job can
            actually DO when the model calls one. The archetype GRANTS a
            tool; this is what runs it, and the two must come from the
            same place or a successor is handed `check_stock` and gets an
            empty string back (#2352).
    """
    if fallback is None:
        from evennia.utils import logger
        logger.log_warn(
            f"service.register({role!r}): no fallback line — a voiceless "
            f"{role} will not answer when addressed at a post. Pass "
            f"fallback=SILENT if that is intended.")
    _check_signature(role, "handler", handler,
                     ("post", "speech", "patron", "by", "addressed"))
    _check_signature(role, "on_receive", on_receive,
                     ("post", "obj", "giver", "by"))
    SERVICE[role] = {"handler": handler, "aliases": tuple(aliases),
                     "fallback": fallback, "archetype": archetype,
                     "tools": dict(tools or {}), "on_receive": on_receive}


def _check_signature(role, kind, fn, args) -> None:
    """Complain LOUDLY, at registration, about a handler that cannot be
    called the way `serve` calls it.

    The module docstring published a four-argument contract for years
    while the call site passed a fifth keyword. A handler written to it
    raised TypeError on every single line, the blanket except at the
    call site swallowed that into `False` — which means "the post did
    not claim it", an entirely ordinary outcome — and the venue was
    silently mute forever. No error reached the player or the room
    (#2797).

    Caught here rather than at the call site because a wrong signature
    is a programming error that should surface when the module loads,
    not on some patron's first order.
    """
    if fn is None:
        return
    from inspect import signature
    # `serve` passes `addressed` BY KEYWORD, so the handler's last
    # argument has to bind as one. on_receive is called positionally
    # throughout.
    positional, keyword = ((args[:-1], {args[-1]: object()})
                           if kind == "handler" else (args, {}))
    try:
        signature(fn).bind(*(object() for _ in positional), **keyword)
    except TypeError as err:
        from evennia.utils import logger
        logger.log_err(
            f"service: {role}'s {kind} {getattr(fn, '__name__', fn)!r} "
            f"cannot be called as ({', '.join(args)}): {err}. "
            f"This post will never serve.")
    except (ValueError, KeyError):
        pass    # builtin or C-level callable — no introspectable signature


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
    """The line this job gives when addressed with no voice to answer.

    `None` for a job that answers with silence — whether it CHOSE that
    (`fallback=SILENT`) or never had a line. The sentinel is a
    registration-time signal, not a thing anybody says out loud, so it
    is translated back here rather than at each caller: it is truthy,
    and every consumer guards on `if line` (#2824).
    """
    job = job_of(worker)
    line = job.get("fallback") if job else None
    return None if line == SILENT else line


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


def receive(worker, obj, giver):
    """Offer something handed to *worker* to the job they are standing.

    Returns True when the job took it. A body off shift is nobody in
    particular and takes nothing, which is correct: handing a corpse to
    an off-duty butcher in a bar should not start a butchery."""
    job = job_of(worker)
    hook = (job or {}).get("on_receive")
    if hook is None:
        return False
    try:
        return bool(hook(post_for(worker), obj, giver, worker))
    except TypeError as err:
        from evennia.utils import logger
        if err.__traceback__ is None or err.__traceback__.tb_next is None:
            logger.log_err(
                f"on_receive {getattr(hook, '__name__', hook)!r} has the "
                f"wrong signature for {worker}: {err}")
        else:
            logger.log_trace(f"on_receive failed for {worker}")
        return False
    except Exception:  # noqa: BLE001 — a bad hand-over must not eat the item
        from evennia.utils import logger
        logger.log_trace(f"on_receive failed for {worker}")
        return False


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
    except TypeError as err:
        # A TypeError raised with NO frame below this one came from the
        # call itself — a signature mismatch, not something inside the
        # handler. Only the second is what the blanket catch below is
        # defending against, and the first deserves to be loud: it means
        # this venue serves nobody, ever.
        from evennia.utils import logger
        if err.__traceback__ is None or err.__traceback__.tb_next is None:
            logger.log_err(
                f"service handler {getattr(handler, '__name__', handler)!r} "
                f"has the wrong signature for post {post}: {err}")
        else:
            logger.log_trace(f"service handler failed at {post}")
        return False
    except Exception:  # noqa: BLE001 — a broken counter must not eat the line
        from evennia.utils import logger
        logger.log_trace(f"service handler failed at {post}")
        return False
