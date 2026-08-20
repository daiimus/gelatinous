#!/usr/bin/env bash
# The reload step of the deploy cycle, made process-safe (#2088).
#
# Three outages share one anatomy: a hand-run `evennia reload` whose
# launcher got orphaned (chained commands, outer timeouts) and sat on
# the AMP port half-connected while the server stayed down. This
# script is the ONLY sanctioned way to reload:
#
#   1. The timeout lives INSIDE the container, wrapping the launcher —
#      a hung launcher kills itself; nothing can orphan it from outside.
#   2. The server is verified actually RUNNING afterward.
#   3. On failure, the documented recovery runs verbatim: kill any
#      orphan launcher, clear the stale server.pid, `evennia start`,
#      re-verify.
#
# Orchestrates only the documented Evennia CLI — no layer over
# internals. Exit 0 = server verified up; exit 1 = manual attention.
set -u
CONTAINER="${CONTAINER:-gelatinous}"
GAME=/usr/src/game

say() { echo "[safe_reload] $*"; }

server_running() {
    docker exec "$CONTAINER" bash -lc \
        "cd $GAME && timeout 20 evennia status 2>/dev/null" \
        | grep -q "Server: RUNNING"
}

verify() {  # poll up to ~60s for the server to report RUNNING
    for _ in $(seq 1 12); do
        if server_running; then return 0; fi
        sleep 5
    done
    return 1
}

say "issuing reload (launcher timeout lives in-container)..."
docker exec "$CONTAINER" bash -lc "cd $GAME && timeout 150 evennia reload"
say "verifying server..."
if verify; then
    say "server RUNNING — reload verified."
    exit 0
fi

say "server not up — running the documented recovery."
docker exec "$CONTAINER" bash -lc \
    "pkill -9 -f 'evennia reload' 2>/dev/null; rm -f $GAME/server/server.pid; true"
docker exec "$CONTAINER" bash -lc "cd $GAME && timeout 150 evennia start"
if verify; then
    say "server RUNNING after recovery."
    exit 0
fi
say "STILL DOWN — manual attention required (check evennia logs)."
exit 1
