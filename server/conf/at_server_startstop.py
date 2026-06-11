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
    _arm_hang_diagnostics()


def _arm_hang_diagnostics():
    """Arm faulthandler so a hung server can diagnose itself (#489).

    Two reload-shutdown deadlocks (2026-06-11) left the Server alive
    with every thread parked on a futex and no way to see the Python
    stacks (Alpine/musl: no py-spy).  This arms two zero-cost probes:

    * ``kill -USR1 <server pid>`` (from inside the container) dumps
      every thread's stack to ``server/logs/hang_diagnostics.log``
      on demand — run it WHILE the server is hung, before killing it.
    * ``at_server_stop`` schedules an automatic dump 20s into any
      shutdown — if shutdown completes normally the dump is
      cancelled; if it deadlocks, the stacks land in the file with
      no human in the loop.
    """
    import faulthandler
    import os
    import signal

    from django.conf import settings

    global _HANG_LOG
    path = os.path.join(settings.LOG_DIR, "hang_diagnostics.log")
    # Keep the handle open for the process lifetime — faulthandler
    # needs a live fd at signal time.
    _HANG_LOG = open(path, "a")
    _HANG_LOG.write(f"\n=== armed (pid {os.getpid()}) ===\n")
    _HANG_LOG.flush()
    faulthandler.register(signal.SIGUSR1, file=_HANG_LOG, all_threads=True)


_HANG_LOG = None


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    pass


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    # #489: if this shutdown deadlocks (see _arm_hang_diagnostics),
    # dump all thread stacks to the hang log 20s in.  A clean
    # shutdown exits the process before the timer fires; a hung one
    # self-reports.  cancel_dump… is unnecessary on clean exit.
    import faulthandler
    if _HANG_LOG is not None:
        _HANG_LOG.write("\n=== shutdown began; auto-dump armed (20s) ===\n")
        _HANG_LOG.flush()
        faulthandler.dump_traceback_later(20, file=_HANG_LOG)
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
