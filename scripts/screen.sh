#!/bin/bash
# Desktop control for driving GUI apps (Epic launcher, Unreal, MetaHuman Creator).
#   scripts/screen.sh shot [out.jpg]     screenshot of the main display, 1400 px wide
#   scripts/screen.sh click X Y          left-click at X,Y in that screenshot's pixels
#   scripts/screen.sh dclick X Y         double-click
#   scripts/screen.sh move X Y           move the mouse only
#   scripts/screen.sh type "text"        type text into the focused field
# Screenshot pixels are scaled to screen points, so coordinates read off the image can be used directly.
# Needs screen recording and Accessibility allowed for the calling app, and cliclick (brew install cliclick).
set -e
W=1400
points_w() { osascript -l JavaScript -e 'ObjC.import("AppKit"); $.NSScreen.screens.objectAtIndex(0).frame.size.width'; }
pt() { python3 -c "s=$(points_w)/$W; print(f'{round($1*s)},{round($2*s)}')"; }
case "$1" in
  shot) out="${2:-${TMPDIR:-/tmp}/screen.jpg}"; screencapture -x -m -t jpg "$out" && sips -Z $W "$out" >/dev/null && echo "$out" ;;
  click) cliclick "c:$(pt "$2" "$3")" ;;
  dclick) cliclick "dc:$(pt "$2" "$3")" ;;
  move) cliclick "m:$(pt "$2" "$3")" ;;
  type) cliclick "t:$2" ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
esac
