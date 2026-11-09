#!/bin/bash
# Desktop control for driving GUI apps (Epic launcher, Unreal, MetaHuman Creator).
#   scripts/screen.sh shot [out.jpg]     screenshot of the main display, 1400 px wide
#   scripts/screen.sh click X Y          left-click at X,Y in that screenshot's pixels
#   scripts/screen.sh dclick X Y         double-click
#   scripts/screen.sh move X Y           move the mouse only
#   scripts/screen.sh type "text"        type text into the focused field
# Screenshot pixels are scaled to screen points, so coordinates read off the image can be used directly.
# Owner rule: only the main display is ever captured (-m). Never add an option to capture other screens.
# Owner rule: before every click/move/type, check the mouse is where we left it. If not, the owner is
#   using the computer: wait until the mouse has been still for 30 s, then exit 3 WITHOUT acting, so the
#   caller takes a fresh screenshot before trying again (the screen may have changed).
# Needs screen recording and Accessibility allowed for the calling app, and cliclick (brew install cliclick).
set -e
W=1400
IDLE=30
STATE="${TMPDIR:-/tmp}/screen-sh-mouse"
points_w() { osascript -l JavaScript -e 'ObjC.import("AppKit"); $.NSScreen.screens.objectAtIndex(0).frame.size.width'; }
pt() { python3 -c "s=$(points_w)/$W; print(f'{round($1*s)},{round($2*s)}')"; }
record() { cliclick p > "$STATE"; }
guard() {
  local cur last still=0
  cur=$(cliclick p)
  [ -f "$STATE" ] || { echo "$cur" > "$STATE"; return 0; }
  [ "$cur" = "$(cat "$STATE")" ] && return 0
  echo "owner is using the mouse (at $cur); waiting for ${IDLE}s of stillness" >&2
  last=$cur
  while [ $still -lt $IDLE ]; do
    sleep 1
    cur=$(cliclick p)
    if [ "$cur" = "$last" ]; then still=$((still + 1)); else last=$cur; still=0; fi
  done
  echo "$cur" > "$STATE"
  echo "owner idle for ${IDLE}s; take a fresh screenshot before acting" >&2
  exit 3
}
case "$1" in
  shot) out="${2:-${TMPDIR:-/tmp}/screen.jpg}"; screencapture -x -m -t jpg "$out" && sips -Z $W "$out" >/dev/null && echo "$out" ;;
  click) guard; cliclick "c:$(pt "$2" "$3")"; record ;;
  dclick) guard; cliclick "dc:$(pt "$2" "$3")"; record ;;
  move) guard; cliclick "m:$(pt "$2" "$3")"; record ;;
  type) guard; cliclick "t:$2"; record ;;
  *) sed -n '2,13p' "$0"; exit 1 ;;
esac
