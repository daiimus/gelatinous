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
    # #505: re-arm or cook off grenade fuses that crossed the reload
    try:
        from commands.explosion_utils import sweep_armed_grenades
        rearmed, detonated = sweep_armed_grenades()
        if rearmed or detonated:
            from evennia.utils import logger
            logger.log_info(f"Grenade fuse sweep: {rearmed} re-armed, "
                            f"{detonated} overdue (detonating).")
    except Exception:  # noqa: BLE001 — a broken sweep must not stop the boot
        from evennia.utils import logger
        logger.log_trace("Grenade fuse sweep failed.")


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
