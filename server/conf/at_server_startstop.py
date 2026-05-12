"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    pass


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    # One-time recognition_memory schema migration (engine PR).
    #
    # Wipes any pre-engine-PR recognition_memory entries that were
    # keyed on real ``sleeve_uid`` (36-char UUID) instead of the new
    # 16-char Apparent UID, or that lack the post-engine-PR
    # ``lost_contact`` field. Idempotent — once all entries pass the
    # shape check, this is a no-op.
    #
    # TODO: Remove this call (and the helper in world/identity.py)
    # after the engine-PR deployment is verified clean across all
    # production characters.
    try:
        from world.identity import wipe_all_legacy_recognition_memory

        wiped = wipe_all_legacy_recognition_memory()
        if wiped:
            from evennia.utils import logger

            logger.log_info(
                f"identity: engine-PR migration wiped {wiped} legacy "
                f"recognition_memory entries"
            )
    except Exception:
        from evennia.utils import logger

        logger.log_trace("identity: legacy recognition_memory wipe failed")


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass
