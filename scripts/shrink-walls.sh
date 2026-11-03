#!/bin/bash
# Converts wallpaper PNGs in walls/ to high-quality JPEGs (same name, .jpg) to keep the repo and the page light.
# Originals move to walls-original/ (gitignored). Images with transparency are left alone. Run from the repo root;
# the autopush watcher runs it before rebuilding manifest.json.
#     scripts/shrink-walls.sh            # every PNG in walls/
#     scripts/shrink-walls.sh walls/a.png
cd "$(dirname "$0")/.." || exit 1
mkdir -p walls-original
[ $# -eq 0 ] && set -- walls/*.png walls/*.PNG
for f in "$@"; do
  [ -f "$f" ] || continue
  sips -g hasAlpha "$f" 2>/dev/null | grep -q 'hasAlpha: yes' && continue
  out="${f%.*}.jpg"
  sips -s format jpeg -s formatOptions 92 "$f" --out "$out" >/dev/null && mv "$f" walls-original/ && echo "$out"
done
