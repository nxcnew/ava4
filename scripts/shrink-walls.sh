#!/bin/bash
# Converts PNG images in walls/ and screens/ to high-quality JPEGs (same name, .jpg) to keep the repo and the page
# light. Originals move to walls-original/ or screens-original/ (gitignored). Images with transparency are left alone.
# Run from anywhere; the autopush watcher runs it before rebuilding manifest.json.
#     scripts/shrink-walls.sh            # every PNG in walls/ and screens/
#     scripts/shrink-walls.sh walls/a.png
cd "$(dirname "$0")/.." || exit 1
[ $# -eq 0 ] && set -- walls/*.png walls/*.PNG screens/*.png screens/*.PNG
for f in "$@"; do
  [ -f "$f" ] || continue
  sips -g hasAlpha "$f" 2>/dev/null | grep -q 'hasAlpha: yes' && continue
  orig="$(dirname "$f")-original"; mkdir -p "$orig"
  out="${f%.*}.jpg"
  sips -s format jpeg -s formatOptions 92 "$f" --out "$out" >/dev/null && mv "$f" "$orig/" && echo "$out"
done
