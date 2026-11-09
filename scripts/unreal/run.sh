#!/bin/bash
# Usage: run.sh script.py  (or code on stdin). Sends it to the running Unreal editor via the file bridge.
B="$(cd "$(dirname "$0")" && pwd)"; n="job$(date +%s)_$$_$RANDOM"
if [ -n "$1" ]; then cp "$1" "$B/inbox/$n.py.part"; else cat > "$B/inbox/$n.py.part"; fi
mv "$B/inbox/$n.py.part" "$B/inbox/$n.py"
for i in $(seq 1 ${WAIT:-600}); do [ -f "$B/outbox/$n.out" ] && { cat "$B/outbox/$n.out"; exit 0; }; sleep 1; done
echo "TIMEOUT waiting for Unreal"; exit 1
