#!/usr/bin/env bash
# Resilient live reload for gel.monster.
#
# `evennia reload` can strand the game when an LLM sidecar generation is
# in flight: the server disconnects from the portal, then blocks its own
# exit waiting on the threadpool thread stuck behind the (serialized,
# possibly crawling) sidecar — and the replacement server refuses to
# start ("Another twistd server is running"). Observed live 2026-07-01
# (twice, both during LLM playtests; idle reloads are clean).
#
# This script: reload -> verify -> if the server is down, kill the
# lingering server process, clear the pidfile, cold-start, and verify the
# player-facing telnet greeting. Run from the host:
#
#   ./scripts/deploy-reload.sh
set -u

CONTAINER=gelatinous
GAME=/usr/src/game

status_server() {
    docker exec -w "$GAME" "$CONTAINER" evennia status --settings settings.py 2>/dev/null \
        | grep -c "Server: RUNNING"
}

echo "--- reload ---"
docker exec -w "$GAME" "$CONTAINER" evennia reload --settings settings.py 2>&1 | tail -2

sleep 8
if [ "$(status_server)" -ge 1 ]; then
    echo "--- reload clean, server running ---"
else
    echo "--- server did not come back: recovering lingering process ---"
    docker exec "$CONTAINER" bash -lc '
        pids=$(ps -o pid=,args= -e | grep "server/server.py" | grep -v grep | awk "{print \$1}")
        for p in $pids; do kill "$p" 2>/dev/null; done
        sleep 4
        for p in $pids; do kill -9 "$p" 2>/dev/null; done
        rm -f '"$GAME"'/server/server.pid
    '
    docker exec -w "$GAME" "$CONTAINER" evennia start --settings settings.py 2>&1 | tail -2
    sleep 6
    if [ "$(status_server)" -ge 1 ]; then
        echo "--- recovered: server running ---"
    else
        echo "!!! RECOVERY FAILED — manual intervention needed" >&2
        exit 1
    fi
fi

echo "--- greeting check ---"
docker exec "$CONTAINER" python - <<'PY'
import socket
s = socket.create_connection(('127.0.0.1', 23), timeout=8); s.settimeout(5)
chunks = []
try:
    while True:
        d = s.recv(4096)
        if not d:
            break
        chunks.append(d)
except Exception:
    pass
s.close()
ok = b'Gelatinous' in b''.join(chunks)
print('GREETING OK' if ok else 'NO GREETING')
raise SystemExit(0 if ok else 1)
PY
