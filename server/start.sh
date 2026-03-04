#!/bin/sh
# Auto-migrate on startup, then start Evennia

# Fix log file permissions (can get reset by host OS)
chmod 666 /usr/src/game/server/logs/*.log 2>/dev/null || true

evennia migrate --run-syncdb
exec evennia start -l
