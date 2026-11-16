"""Blocking calls that a shutdown does not wait for (#3815).

Evennia's ``run_async`` puts a function on the reactor's worker pool.
That pool is meant for quick work. When the Server stops or reloads,
Twisted joins every thread in it before the process may exit, and the
Portal starts the replacement Server as soon as the old one's connection
drops, without waiting for that exit.

A model call can take two minutes. One in flight at a reload held the
old process, and its pid file, until the model answered. The replacement
found the pid file and quit, and the game stayed down.

So calls that may block for long run here: on a pool of our own whose
workers are daemon threads and which nothing stops. The old Server does
not wait for them, whatever they are doing. The call it abandons is
harmless as long as the work keeps to the rule below; its callbacks are
never run, which is also what happened to them before.

Like the reactor's own pool, this one starts when the reactor is
running. In a process that never runs one (a test run, `evennia shell`)
the work is held and nothing is sent, as it was on the reactor's pool.

The rule for ``work``: network and parsing only. No Evennia objects and
no database. The callbacks run on the reactor, where both are safe.

This module imports nothing from Evennia or Django, so that a test can
run it under a real reactor in a process of its own.
"""
from threading import Thread

from twisted.internet import threads
from twisted.python.threadpool import ThreadPool

#: The most calls in flight at once; one past that waits its turn. The
#: reactor's pool, which these calls used to share, allows ten, so this
#: is the ceiling they already had.
MAX_IN_FLIGHT = 10


class DetachedPool(ThreadPool):
    """A Twisted thread pool whose workers are daemon threads.

    Nothing calls ``stop`` on it, so nothing joins its threads, and
    Python does not wait for a daemon thread when the process exits.
    """

    @staticmethod
    def threadFactory(*args, **kwargs):
        return Thread(*args, daemon=True, **kwargs)


#: No thread exists until the first call: workers are made on demand.
_pool = DetachedPool(minthreads=0, maxthreads=MAX_IN_FLIGHT, name="detached")


def run_detached(work, at_return, at_err):
    """Run ``work()`` off the reactor and hand the outcome back on it.

    Wired the way ``evennia.utils.run_async`` wires its pair, callback
    first and errback after it, so an exception from ``at_return`` still
    reaches ``at_err``. Only the pool differs.

    Args:
        work (callable): takes nothing; network and parsing only.
        at_return (callable): called on the reactor with what ``work``
            returned.
        at_err (callable): called on the reactor with a ``Failure`` if
            ``work`` raised.

    Returns:
        Deferred: fires when the outcome has been handed back.
    """
    from twisted.internet import reactor

    if not _pool.started:
        # As the reactor starts its own pool: once it is running, which
        # is now if it already is. Until then a pool hands out no work,
        # so a process that never runs a reactor never sends anything.
        reactor.callWhenRunning(_pool.start)
    deferred = threads.deferToThreadPool(reactor, _pool, work)
    deferred.addCallback(at_return)
    deferred.addErrback(at_err)
    return deferred
