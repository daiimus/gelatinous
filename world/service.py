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

#: post_role -> handler. See the module docstring for the contract.
SERVICE = {}

#: Modules that register handlers. An import manifest, not behaviour —
#: registration has to have HAPPENED before the first patron speaks, and
#: nothing else guarantees these are imported by then. Handlers still live
#: with the state they read; only the import lives here.
PROVIDERS = ("world.bar",)

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


def register(role, handler):
    """Bind a service handler to a post role."""
    SERVICE[role] = handler


def handler_for(post):
    """The handler this post serves through, or None."""
    if post is None:
        return None
    _ensure_loaded()
    return SERVICE.get(getattr(post.db, "post_role", None))


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
