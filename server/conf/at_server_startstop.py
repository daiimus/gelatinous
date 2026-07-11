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


def _install_logfile_failure_unmask():
    """TEMPORARY INSTRUMENTATION — REMOVE once one failure is captured.

    Evennia's ``logger.log_file`` (the threaded writer behind channel
    history and the combat audit log) reports write failures via a bare
    ``log_trace()`` inside a Twisted errback. There is no live exception
    in an errback, so the server log gets literally ``NoneType: None``
    and the actual Failure is discarded — 7.9k such lines since the
    6.1.0 upgrade, in play-time bursts, reason unknown.

    This is a faithful copy of ``log_file`` changing ONLY the errback:
    it renders the failure's traceback plus the filename and a snippet
    of the lost line, marked LOGFILE-UNMASK for grepping.
    """
    from evennia.utils import logger as _elog
    from twisted.internet.threads import deferToThread

    def log_file_unmasked(msg, filename="game.log"):
        def callback(filehandle, msg):
            msg = "\n%s [-] %s" % (_elog.timeformat(), msg.strip())
            filehandle.write(msg)
            # flush manually: the handle stays open (upstream comment)
            filehandle.flush()

        def errback(failure):
            try:
                _elog.log_err(
                    f"LOGFILE-UNMASK: write to '{filename}' FAILED "
                    f"(lost line: {str(msg)[:120]!r}) ->\n"
                    f"{failure.getTraceback()}")
            except Exception:  # noqa: BLE001 — never let the unmask crash
                _elog.log_err("LOGFILE-UNMASK: write failed; failure "
                              "unrenderable.")

        filehandle = _elog._open_log_file(filename)
        if filehandle:
            deferToThread(callback, filehandle, msg).addErrback(errback)

    _elog.log_file = log_file_unmasked
    _elog.log_err("LOGFILE-UNMASK installed (temporary instrumentation).")


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    _install_logfile_failure_unmask()


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
