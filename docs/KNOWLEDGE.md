# Dance Arena - project knowledge

Running context for this project: what was decided, why, and what's still open. [CLAUDE.md](../CLAUDE.md) covers how the code is laid out. This file covers history and reasoning, and [CHARACTER_PIPELINE.md](CHARACTER_PIPELINE.md) covers making characters.

**How to update:** add a new version at the top of the log for each meaningful step. Keep the sections below the log current; edit them in place, don't just append.

## Version log

### v23 - 2026-11-03 - Studio side walls also use other shapes that crop well

**Problem:** 106 of 157 wall images never appeared. 48 are 3:2, 14 are 16:9 and 13 square; the side-wall pool only took 8:3 once there were two of them, and the back wall only takes 3:1 and wider.

**Change (owner's choice):** the left wall picks from the 33 non-8:3 images that crop well about 35% of the time.

- **Crops well:** one face, fitting whole in the full-width strip, at 1000 px or more.
- **Otherwise:** an 8:3 image.
- **Right wall:** the closest colour match from 8:3 plus the good crops.
- **Back wall:** unchanged (3:1+), still colour-matched.

### v22 - 2026-11-03 - Studio back wall the right way round

**Change:** the back wall's image is no longer pre-flipped. It reads correctly on the wall, and the mirror shows its true, reversed reflection, as a real mirror does. This is the owner's call and replaces the old "flip so the mirror reads correctly" rule. Images with text will now read backwards in the mirror, as in real life.

### v21 - 2026-11-03 - Stage show: wider spacing, running on and off, next lineup cues up; natural-colour camera feed

**Spacing:** `ENVS.festival.spread = 2.1`. `stageSlots` scales the layout by the scene's spread; switching scenes relays the stage out.

**Running:**

- **When:** on the main stage (`stageRun()`), moves over 3 m are runs at 3.2 m/s.
- **Clip:** `walkState(plainOnly, run)` uses a clip named run/jog/sprint from walks/ if there is one. If not, the plain walk plays 1.9x faster (`st.rate`).
- **To do:** the owner should add a Mixamo "Running" (in place) as `walks/walk - Running.fbx`.

**Cue-up (`cueNextLineup`, run every frame):**

- **When:** about 9 s before a song ends (`songBuf.duration` minus the play position), the next lineup is picked (`pickLineup`, the same rules as before).
- **Waiting spots:** newcomers (`av.cued`) jog from the wings to spots beside the dance area on their own side, x +-6.8..8.6, z -1.4.., and wait there facing the stage, visible.
- **Change-over:** `rotateStage` uses the cued lineup. Newcomers run to their spots; the outgoing run all the way back to the wings.
- **Reset:** `clearStage` and scene switches reset any cue.

**Camera feed:** dancers always appear in their natural colours. Neon silhouettes and the tinted triptych sides were dropped. Over art, a little of the art's colour spills onto them (15%).

### v20 - 2026-11-03 - One collapse/expand everywhere; pin for desktop; touch player fades

**Collapse / expand**, the same on every device:

- **Header arrow (`#panelCollapse`):** slides the panel away.
- **Edge tab (`#panelExpand`):** a real button, "< Controls", shown whenever the panel is away. It brings the panel back.
- **Portrait phones:** keep the bottom sheet, with the same chevron (down when open, up when collapsed).
- **Why:** phone landscape (wider than 760px) used the desktop panel, whose only control was a hover-based auto-hide, so it couldn't be operated by touch.

**Pin (`#panelPin`), desktop with a mouse only:**

- **Pinned (default):** the panel stays open.
- **Unpinned:** the old auto-hide: it slides away when the mouse leaves and returns at the right edge. Saved in localStorage as before.
- **Touch screens:** the pin is hidden.

**Touch screens (`hover: none`):**

- **Panel:** starts collapsed. Open, it closes 3 s after the last touch, scroll or change inside it; tapping the stage closes it.
- **Player:** fades to 0.18 opacity, wakes on touch (taps act at once) and fades 3 s later. It was stuck at 0.9.

### v19 - 2026-11-03 - Phone layout: player on top, self-closing controls sheet; screen timing fix

**Phones** (max-width 760px):

- **Player:** moves to the top edge. The HUD (title, beat readout) sits under it at 76 px.
- **Controls panel:** a bottom sheet that starts collapsed and never stays open. `setSheet` closes it 3 s after the last pointerdown, input, change, scroll or keydown inside it. Tapping the stage closes it at once.
- **CSS order:** the phone player rule must come after the base `.player` rule (a later media block), otherwise the base `bottom` wins and the bar stretches.
- **Desktop:** unchanged.

**Screen timing:** stills and the camera feed are timed in bars, and a new song or a seek back restarts the bar count. Without a reset, a still stayed up until the new song reached the old bar number, which could span several songs. `updateScreen` now resets the timings when the bar count drops.

### v18 - 2026-11-03 - Performance: adaptive resolution, lighter crowd, screen skips hidden work

**Problem:** the owner reported zooming on the main stage getting stuck. Profiling showed the JS per frame was small (festUpdate about 0.2 ms, arena about 0.3 ms). The load was on the GPU: about 514k triangles per frame, plus the LED screen's fractal shader running per pixel at Retina resolution.

**Fixes:**

- **`watchFps`:** the page measures fps every 0.5 s. Three slow windows in a row (under 45 fps) step the pixel ratio down by 0.25, to a floor of 1. Eight fast windows (over 57 fps) step it back up to min(devicePixelRatio, 2). It ignores hidden tabs.
- **Screen shader:** skips the generative looks while a still fully covers the screen (`uArtMix > 0.98` and no camera feed).
- **Crowd geometry:** lower segment counts (limbs 5-sided and open-ended, lathe 8, head 8x6, shoulders 6x4, fists 5x4, hair caps 9x5). Triangles went from about 514k to 320k per frame.

### v17 - 2026-11-03 - Screen art filters, camera styles, booth face, dim crowd, originals guard

**Art filters** (in the screen shader, the equivalent of CSS filters):

- **What they are:** the screen is inside the WebGL canvas, so CSS can't reach it. Since the owner's follow-up, the filters are colour-only: no greyscale, inversion, chrome, sweeps or ripples, which "looked weird".
- **Set (`uArtFx`, 20% plain):** 1 slow hue drift, 2 a soft tint in the stage palette (35%), 3 saturation richer on each kick, 4 split toning (shadows one stage colour, highlights the other, 40%), 5 hue swinging +-0.06 over each bar.

**Camera feed:**

- **What it films:** only the dancers (layer 5; lights are enabled on that layer too), on black, so they can be keyed by brightness.
- **Styles (`uCamFx`):** 0 broadcast, 1 giants over the art or generative look, 2 triptych with mirrored tinted sides, 3 neon gradient silhouettes.
- **Frequency:** about 1 phrase in 7, at least 90 s apart (owner: slightly more than before, not too often).

**Robustness:** a screen image that fails to load is dropped from the pool, with a 5 s pause. Before, it was retried every frame.

**Booth face:** a dim dot-grid LED texture tinted with the theme colour (`festBoothFace`). Before, it was a `festStrip` plane flashing at full brightness.

**Crowd:** back to subtle silhouettes. Colours are muted 45% towards grey and scaled by `DIM` 0.075.

**Guard:** `scripts/pre-commit`, installed in `.git/hooks`, refuses commits that stage `*-original/` or `.secrets/` files, including the watcher's commits.

### v16 - 2026-11-03 - Stage screen art and live camera; realistic crowd; speakers on the truss; lights snap on the kick

**Stage screen (`updateScreen`):**

- **Art:** from `screens/` (new library folder), or, until there is any, the 3:1-and-wider wallpapers.
- **Cycle:** on phrase starts (every 8 bars) the big screen cross-fades between its generative looks (8-16 bars) and a still image (8-16 bars). The still slowly zooms and drifts (Ken Burns, uniform `uArtXf`) and pulses with the beat. With no music it rests on a drifting still.
- **Loading:** one image is downloaded and decoded at a time, only when it is next. At most two textures exist; old ones are disposed.
- **Live camera:** rarely (about 1 phrase in 10, at least 2 minutes apart, only with dancers on stage), 8 bars of a camera feed. `bcCam` dollies along the stage front, rendering into a 512x196 target every other frame, only while the feed shows. The main screen is hidden during that render so it never films itself.
- **Side screens:** `festSideMat` shares the uniforms but has no art or feed.

**`screens/` folder:** in `LIB_DIRS`, `make-manifest.sh` dirs, the watcher's ASSETS and `shrink-walls.sh` (PNG to JPEG). `screens-original/` is gitignored.

**Crowd realism:**

- **Outfits:** painted per fragment from body part, object-space position and `aStyle`:
  - tops: stripes, a front/back print, two-tone, crop tops;
  - waist and legs: a waistband, shorts, skirt and dress hems;
  - sleeves: long, short or none.
- **Colours:** weighted to black, white, grey, denim and muted tones.
- **Hair:** tilted back (real hairline), plus a side part, long, ponytail, bun, lumpy curls and rarer beanies. 6% bald.
- **Light:** `DIM` 0.22, down from 0.42.
- **Bobbing:** offsets up to about 0.1 beat (about 50 ms), with per-person bob height.

**Stage:**

- Removed the hanging line arrays and the subwoofer stacks (lasers ran through them).
- Two 5-cabinet speaker hangs sit on the middle truss over the dancers.
- Removed the DJ figure and the side-stage guests; kept the booth and the 2 crew members.

**Moving lights:**

- The rig heads and the festival beam fixtures now start their move on the kick and settle in the first third of the beat (`easeOut`). Before, they held for 30% of the beat and glided to land on the next one, which read as late.
- In quiet passages they glide over 2 beats (was a hold for a bar).

**Testing:** `runtest.sh` copies the real `manifest.json` and uses a fresh Chrome profile per run (a cached manifest caused false 404s).

### v15 - 2026-11-03 - Busy stage; laser looks like real laser shows; wall PNG fix

**Busy stage:** everything is cheap and mostly instanced.

- **DJ booth:** a riser at the back centre (`FEST_DJ`) with an LED face that reacts to the music (`festStrip`). It has decks, a mixer and a laptop, and the DJ bobs on the riser.
- **Backline and rigging:** stacked flight cases in the back corners, 4 truss legs, 2 mic stands, a camera on a tripod, and monitor desks with lit screens at the front corners.
- **People on stage:** 7 guests in each back corner, moving to the music (a few with a hand up), and a crew member at each desk. They're made by the crowd's `makePerson` and have a `base` floor height.
- **Clear zones:** the dancers' slots (x within +-2.25, z within +-0.9) and the walk-in paths from the wings are kept clear.

**Lasers** (research: parallel arrays, fans, tunnels and liquid-sky sheets, mirrored rigs, mostly one colour):

- **Looks (`LASER_LOOKS`):** parallel, breathing fans, mirrored V sweep, tunnel, sky sheet, centre-out tilt wave, and criss-cross.
- **Symmetry:** every look is mirrored left/right by each head's side.
- **Timing:** a look holds 2 bars while moving. Criss-cross comes up about 1 time in 10, with only 3 beams per head.
- **Parallel looks:** 3 emitters per head, offset 0.3 m, all in the same direction.
- **Colour per 4 bars:** 65% one colour for every beam (`LASER_MONO`: classic green, white, cyan, theme); 28% a gradient mirrored from the centre out; 7% mixed.
- **Width:** beams are slightly broader, 0.02 m at the far end.

**Wall PNGs:**

- **Bug:** the watcher's check `ls walls/*.png walls/*.PNG` failed whenever no uppercase `.PNG` existed, so 50 PNGs went up unconverted.
- **Fix:** the check is now `ls walls | grep -qi '\.png$'`. Those 50 are converted; they remain in the history (about 120 MB).

### v14 - 2026-11-03 - Lasers into the crowd; crowd clothes, hair, smoother bodies; Light Director design

**Lasers:**

- **Aim:** each beam is aimed at a point inside the crowd (`laserTarget`) and ends just past it, so beams never run on towards the camera.
- **One row at a time:** in a laser show one row leads each bar (floor, truss, towers in turn). All rows fire together only on the downbeat of a hit bar. That removes the "web".

**Crowd:**

- **Per-person colours:** every vertex carries a `part` tag (skin, top, trousers, sleeves). Each person carries instanced colours for skin tone, top, bottom (15% a coloured skirt or trousers) and sleeves (short sleeves show skin). `crowdMat` patches Lambert with `onBeforeCompile`, so there are no extra draw calls.
- **Hair:** 5 instanced styles (short, long, bun, curly, beanie). About 10% are bald. Colours are mostly natural.
- **Body shape:** the torso is a `LatheGeometry` profile that rounds over the shoulders into the neck, with shoulder balls. This replaced the cylinder and capsule "planks".
- **Raised arms:** bent at the elbow. Mostly one hand up (left or right, open or fist); both hands is rare.

**Design:** [LIGHT_DIRECTOR.md](LIGHT_DIRECTOR.md) covers the light and pyro coordinator: research, analysis features, the section and accent model, the beat engine (nothing holds still for more than one beat) and a build order. Not built yet.

### v13 - 2026-11-03 - Main stage show: monitors, flame machines, lasers, punchy-section cues, a new look each load

**Stage front:** at `FRONT_Z = 4.45` there is a row of wedge monitors, 0.4 m tall (below the knee), instanced.

- **Flame machines:** 6 hexagonal columns (`FLAME_X`) in some of the gaps.
- **Spark fountains:** 4 low boxes (`SPARK_X`) in others.
- All pyro comes out of these machines.

**Flames:**

- One billboard per machine (it turns to face the camera around the vertical) with an fbm, domain-warped fire shader.
- Colours run from a white core through yellow and orange to red edges, with a blue root at the nozzle.
- A burst shoots up in about 0.16 s, burns, then the valve shuts and the fireball lifts off. This replaced the old glow-sprite "blurs".

**Sparks:** `Points` gerbs, white-gold, with gravity.

**Fireworks:**

- Shells climb on a comet trail and burst on a chosen beat (`riseSecs`).
- Kinds: peony, ring, willow (slow, gold, drooping) and glitter (twinkling).

**Lasers:** 20 heads in uniform rows (7 along the stage floor, 7 on the front truss, 3 up each tower), 7 beams each, in one InstancedMesh of 140 beams. This was halved from 40 heads at the owner's request.

- **Shape:** each beam is a 4-sided open cone, a point at the head widening to 0.012 m at 30 m: hair-thin and pointed.

- **Beams:** 30 m long, fading along their length through vertex colours.
- **Heads:** each is a dark box with a faint aperture glow.
- **Patterns** (`laserAim`, one per bar): fans, sweeping fans, criss-cross, rolling waves, tunnels converging on the crowd, and sheets over the crowd.

**Cues (owner's rules):**

- **Punchy sections:** pyro and big lasers only happen in "punchy" sections. `songAnalysis` now returns `punch: [[first beat index, bars]]`, the strongest 3 of all candidates.
  - **Candidate:** 16+ bars with a beat in every bar (no chill beat), averaging over 1.05x the song's median bar punch (loudness x hit strength).
  - **Starting point:** after a gap, or at an energy jump (the next 4 bars over 1.35x the previous 4).
- **Within a section:** a cue every 4 bars on the downbeat, for up to 32 bars, while the beat holds. Sections alternate between pyro and lasers, starting at random.
  - **Pyro:** all flames, fountains for 4 beats, a 4-shell mixed volley on the first hit and one shell after that.
  - **Lasers:** all 140 beams, full brightness on hit bars and 0.6 between.
- **Outside sections:** only a few soft beams from the top row.
- **Firing:** cues fire on the first frame of each new beat, so slow frames can't skip one.

**A new look each load (`FEST_THEMES`):**

- The themes are neon, ice, inferno, jungle, sunset, royal and chrome.
- A theme sets the structure finish (`festDark`), the deck, the hemisphere/key light and fog colours, and the festival-only palette (`FEST_PAL`) used by the screens, LED edges, beams, lasers and fireworks. The shared `PALETTE` (club, rig, rooftop) is unchanged.
- Hemisphere light is a little brighter than before, 0.55-0.7.

**Testing:** `scratchpad/runtest.sh` with `testsrv.py` serves an instrumented copy. It logs over GET `/__log` and saves canvas frames over POST `/__shot`. Always muted.

### v12 - 2026-11-03 - Camera limits; phones lift and lower with the music

**Camera:**

- `maxDistance` is the scene's `cam.max + 1.5` (was +3).
- `keepCamera()` runs after `controls.update()`. It keeps the camera at y >= 0.35 in every scene, and in the studio inside the side walls and in front of the back wall.
- `maxPolarAngle` is untouched.

**Phones (festival crowd):**

- **Arm:** each holder's right arm is its own instanced mesh (`phoneArms`), pivoting at the shoulder. The phone box is attached to the hand.
- **Motion:** with no music, all arms are down. While music plays, each holder first lifts a random 2-16 s in, keeps the phone up for 8-28 s, lowers it for 5-23 s, and repeats. They lift at 0.4/s and lower at 0.6/s.
- **Screen and flash:** the screen brightens as the phone comes up. The flash (75% of holders) shows only near the top of the lift.
- **Variety:** each phone has its own size, portrait or landscape grip (30% landscape) and screen tint.

### v11 - 2026-11-03 - Freeze fix, three matching walls, JPEG walls, history squashed

**Picture froze after the first song (main stage, club, rooftop):**

- **Cause:** at a song change the beat is briefly negative. The "dancers" look in `RIG_LOOKS` indexed `ds[(i + k) % n]`, which is negative in JS, so it got `undefined` and threw.
- **Why it froze:** three.js stops the `setAnimationLoop` callback after an error, so the picture froze while the audio played on.
- **Fix:** the look now uses `mod()`. The frame body is now `frame()` inside a try/catch that logs each distinct error once, so a bad frame can never freeze the page again.
- **How it was found:** an instrumented copy in headless Chrome with 7 dancers. Always run it with `--mute-audio`.

**Crowd follow-up (v10):**

- **Raised arms are rare:** both arms up is about 4% of bobbers and 1% of the rest. One arm up is about 6% of bobbers.
- **Hands:** open palms (four splayed fingers and a thumb) or fists.
- **Phones:** about 3% hold up a phone. Each has a lit screen box (instanced) and a flash glow (`Points` with `glowTex`).

**Studio walls:** all three share a hue. Left is random; right and back are the closest `lookDist` matches to it.

**Walls are JPEG:**

- Quality 92, 42 MB instead of 184 MB of PNG.
- `scripts/shrink-walls.sh` converts them; the watcher runs it on new PNGs.
- Originals go to `walls-original/` (gitignored).

**History squashed:** GitHub counted the repo at 1.0 GB, 825 MB of which was old unshrunk avatar FBX versions in the history.

- With the owner's OK, main was replaced by one commit of the current files and force-pushed.
- The old history survives only in the local branch `backup-before-wipe`.

### v10 - 2026-11-03 - Festival crowd: fewer people, human shapes, mostly still

**Owner feedback:** too many bobbing heads, all of them moving, and they looked like minions with cylinder bodies.

**Change (`festCrowd`):**

- **Fewer people:** 420 instead of 1300, each at least 0.55 m from the next (rejection sampling), so nobody overlaps.
- **Human shape:** each person is a merged silhouette of legs, a torso wider at the shoulders, shoulders, neck, head and arms. There are two instanced meshes, arms down and arms up. Arms up goes to about a third of the bobbers and 5% of the rest.
- **Variety:** per-person height and width, and a yaw of up to +-0.45 rad.
- **Motion:**
  - 62% stand still, 24% bob on the beat and 14% sway.
  - Leaning only happens among the movers.
  - Everyone is still when there's no music; the old idle drift is gone.
- **Import:** `mergeGeometries` now comes from `three/addons/utils/BufferGeometryUtils.js`.

### v9 - 2026-11-03 - New wall images made to the walls' shapes

**New images:** the owner added 48 ChatGPT images to `walls/`:

- 8:3 at 2048 x 768, for the side walls;
- 3:1 at 2172 x 724, for the back wall;
- one 16:9 image.

All are fictional people, about 2.3 MB PNG each, and are left as they came.

**Choosing images (`randomWalls`):**

- **Back wall:** a 3:1-or-wider image (`PANO = 2.85`). If there are none, it falls back to any image of 1.2:1 or wider, as before.
- **Side walls:** everything narrower than the back-wall tier.
- **Side-wall pool:** a new first tier, `shaped`, holds images within 6% of the wall's 8:3. They show whole, with no crop, so face framing doesn't matter for them. The v8 tiers follow behind it. The library now has 25 shaped side images and 25 images of 3:1 or wider. With that many shaped images, the old 1254 px squares no longer reach the side walls.

**Prompt used:** see the conversation of 2026-11-02. Side images are 8:3 with one performer and the face upper-middle. Back images are wide, with no text, because the wall is mirrored.

### v8 - 2026-11-02 - Side walls: always full width, single sharp faces

**Owner rule:** a wallpaper always fills 100% of a side wall's width. No zoom-out, no mirrored edges. This replaces the zoom-out in v6 and v7.

**Framing:** `faceWindow` frames the biggest face inside the full-width strip and reports `fits`. A face fits when it's whole and no other face is cut by the edges.

**Choosing side-wall images (`randomWalls`):** the first pool with at least two images wins:

1. one face that fits, at 1000 px or more;
2. one face that fits;
3. any image whose faces fit;
4. any image.

Today the first pool holds 4 of the 1254 px portraits. `manifest.json` looks now carry `px`, the long side in pixels.

**Why it looked worse lately (checked against the first commit):**

- **Rendering is unchanged:** same wall size, stretch, texture settings and renderer.
- **What changed:**
  - Wide images were taken off the side walls (owner request, v2). Those were stretched about half as much.
  - Framing on faces (v6) put faces where the pixels show most.
- **Source images:** about 510 px across, unchanged since the first commit.

### v7 - 2026-11-02 - Every face framed whole; wallpaper resolution noted

**Framing (`faceWindow`)**

- **Which faces:** every face at least 15% of the main face's size, with 20% headroom and chin plus neck below.
- **Zoom-out limit:** the slice may grow to fit them down to 80% of the wall width. Faces that still don't fit are dropped, farthest from the main face first.
- **Partial faces:** a face left out is kept fully out of view, never cut across the edge.
- **One big face:** if it alone doesn't fit, it's framed snugly.

**Result on the current side images:** 0 of 22 have a face cut by the edge. The narrowest is 89% of the wall width.

**Wallpaper resolution:** never compressed; unchanged since the first commit. Most are about 510 px across (the largest 1254 px). On a 17.6 m side wall the visible strip is about 200 px tall, so it looks pixelated or dithered. Higher-resolution source images (2048 px+) are the real fix.

### v6 - 2026-11-02 - Wallpapers framed on the main face

**The problem**

- **Geometry:** the side walls are 2.67:1 and the side images are about square. At full width, only about 37% of an image's height shows, and pinning to the top cut faces off.

**How faces are found**

- **Ahead of time:** `make-manifest.sh` now runs `scripts/faces.swift` (macOS Vision) and stores the faces in `look.faces`.
- **Fallback:** without a manifest (`file://`, dropped folders), the page uses the browser's `FaceDetector` where one exists. Otherwise it keeps the image pinned to the top.

**How the slice is chosen (`faceWindow`)**

- **Framing:** the visible slice is framed on the biggest face, with about 15% of the face height as headroom and the chin included. This drops empty space at the top.
- **Tall faces:** if the face is taller than the slice, the image zooms out just enough to fit it. The sides then continue mirrored (`MirroredRepeatWrapping`).
- **Current images:** 3 of the 22 side images zoom out, to 88-91% of the wall width. The rest fill the width.
- **Wide back-wall images:** unchanged; they fill the height and crop the sides.

### v5 - 2026-11-02 - Chill sway, wallpaper top, reversed drag, studio door, decor

**Chill**

- **During quiet passages while music plays:** dancers sway on the beat to "Happy Idle", as in the original build.
- **No music:** dancers stand on "Idle 1" at its natural speed, which is almost still.
- **Switching:** the two cross-fade with `liveMix`.

**Wallpapers:** tall images are pinned to the top edge of the wall, so heads are never cut off. Before, they were 80% towards the top.

**Mouse drag:** reversing it with `controls.rotateSpeed = -1` was tried and undone at the owner's request. The default direction stays.

**Studio door**

- **The opening:** a real doorway cut into the right wall and its wallpaper (`doorwayWall`).
- **The door:** hinged at the back edge, it opens into the room.
  - **Room side:** carries the cut-out piece of the right wallpaper, sharing that wall's material and UVs, so closed, the wallpaper runs unbroken.
  - **Fittings:** brass knobs, an auto-closer body and a two-link arm to a header bracket.
- **Behind it:** a dark corridor (an inside-faced box).
- **Entering and leaving:** studio characters now start and end in the corridor (`DOOR.x = ROOM.side + 1.3`). The door opens fast when a walker is within 1.9 m, then closes slowly and eases shut (`updateDoor`).
- **Kept:** the yellow frame.
- **Changed:** the skirting LED strip now stops at the doorway.

**Decor above the mirror:** a backlit walnut slat band between brass rails, wall-washer pucks, and a pink neon script "Move · Feel · Become" (middle dots, U+00B7) on a smoked-glass plate. It's static, matching the studio's no-pulse rule. The mirror height is unchanged.

### v4 - 2026-11-02 - Jamendo key out of the public page

- **Removed:** `index.html` no longer contains the Jamendo client id.
- **Where the page gets it:** the browser's local storage (`jamKey`). The key is saved as soon as it's pasted into the panel, and again on search.
- **Owner's copy:** kept in `.secrets/keys.env` (gitignored), so it can be handed back on request.
- **Still public:** the key remains in git history from earlier commits.

### v3 - 2026-11-02 - Amber pipeline absorbed

- **Source:** the earlier assistant's `amber-pipeline/` handover (a long handover doc plus 4 Blender scripts) was folded in.
- **Scripts:** now in `scripts/blender/`, with paths as arguments and per-character `CONFIG` blocks. They're listed in [scripts/README.md](../scripts/README.md).
- **Pipeline doc:** the character know-how is now in [CHARACTER_PIPELINE.md](CHARACTER_PIPELINE.md). That covers the steps, the CC→Mixamo bone map, the spring/face naming contract, how Amber's chains were built, FBXLoader gotchas and a commission spec.
- **Not in the repo:** `amber-pipeline/` itself is gitignored. The watcher had already pushed it once (commit 3d03593) before it was ignored.
- **Next:** do the same for other characters; the approach is still to be discussed.

### v2 - 2026-11-01 to 2026-11-02 - GitHub, web loading, floor behaviour

**Hosting and loading**

- **Repo:** `nxcnew/ava4` (public), served by GitHub Pages from `main`. Every change goes straight to main (owner rule).
- **Manifest:** Pages has no directory listings, so `manifest.json` (from `make-manifest.sh`) lists the files, their sizes and the wall "looks".
- **Lazy web loading:**
  - Only 2 random starters (never Amber) and 6 dances load up front.
  - Other characters download when ticked, with a progress bar and a dimmed row until ready.
  - Songs load lazily.
- **FBX size:**
  - `shrink-fbx.py` cut the avatars from 667MB to ~145MB by shrinking embedded textures.
  - Not used: assimp FBX→GLB conversion, because it added pivot nodes and dropped a texture.

**Wallpapers**

- Picked at random. The side walls are paired by hue.
- Wide images (aspect ≥ 1.2) go only on the back wall/mirror.
- The back wall exists both in the mirror and when orbiting directly, as two mirrored copies on separate layers.
- The background settings were removed from the panel.

**Small casts**

- With ≤4 avatars, everyone dances on the floor from the start.
- Ticked avatars walk in from the door, and the others walk to new slots. Nothing slides.
- Plain walk for entering and between songs; a dancy walk only sometimes mid-song.
- Starts on the plain "Idle 1" at natural speed. Not clapping, and not beat-synced.

**Scene**

- **Studio ceiling:** 3×3 light panels.
- **Orbit:** 360° horizontally; the vertical range is unchanged on purpose.
- **Festival crowd:** half the bobbing heads, a lower bob (0.12), and random slight left/right leans.

**Avatars and motion**

- **Grounding:** padded body bones (hands, head, knees, hips…) can't go below the floor, which fixes inverted poses. Freeze went from a hand 14cm under the floor to 4cm above it.
- **Hips rescale range:** widened to `1e-4 < r < 1e4` (user edit) so metre/cm rigs both work.
- **Pasted by the owner:**
  - `avatarMaterial` (MeshStandardMaterial + RoomEnvironment). It was already present.
  - Spring bones + faces runtime, and morph targets through the FBX worker.

### v1 - before 2026-11-01 - original build (earlier assistant, claude.ai)

- **The app:** a single-file three.js app with:
  - a beat-tracking worker;
  - beat-locked dance playback;
  - crowd moods;
  - five venues;
  - a player bar;
  - an FBX parse worker;
  - avatar materials.
- **Amber:** a CGTrader CC4 model, rebuilt through Mixamo with the original weights, 22 spring bones and 18 face shapes.
- **Source:** the details come from the handover, folded into this file and [CHARACTER_PIPELINE.md](CHARACTER_PIPELINE.md).

## Owner preferences (keep them)

**Writing and process**

- **Punctuation:** plain hyphens in writing, never em dashes.
- **Real people:** never depict a real celebrity or real person, in wallpapers or avatars.
- **Instructions:** give step-by-step instructions one step at a time.
- **When unsure:** ask rather than guess.
- **Pasted code:** when the owner pastes code with "don't change anything else", apply exactly that.
- **Testing:** the owner tests on the live Pages site and from `file://`, so push every change to main.

**Jamendo key**

API keys never go in the page source or the repo. The Jamendo client id is pasted into the panel once per browser and kept in local storage. The owner's copy lives in `.secrets/keys.env` (gitignored); give it back when asked.

**Behaviour rules**

- **Stage size:** at most 5-6 dancers on stage. The count is random and rotates each song.
- **Small casts:** ≤4 avatars all dance together (`SMALL_CAST`; the handover said 5).
- **Spacing:** dancers never overlap, and the camera zoom follows the count.
- **Entrances and exits:** avatars walk in and out. Leavers are unloaded from memory.
- **Repositioning:** always a walk, never a slide or a jump.
- **No music, no dancing:** nobody dances with the music stopped or paused.
- **Crowd:** never does sit/stand loops. Calm moves only when the music is calm or stopped.
- **Studio:** bright static lights, light floor and walls, studio floor markings, full-wall wallpapers.
- **Festival:** performers only on stage, kept light on the processor.
- **Right panel:** slides to the edge, returns on hover and fades when idle. Opening it must not reframe the arena.
- **Player bar:** nearly invisible until hovered.

## Core systems, the reasoning behind them

### Beat tracking (worker)

1. Spectral-flux onsets.
2. Tempo by autocorrelation.
3. An Ellis-style dynamic-programming beat tracker.
4. Downbeats from kick-band strength plus harmonic novelty.
5. Chill from beat-hit density.

`nowBeat()` follows the beat grid, so tempo drift is tracked. Accuracy is about 3-11 ms on synthetic songs.

### Dance sync

- **Direct time setting:** action time is set directly, not advanced by `dt`: `clipTime = offset + (beat - segStart) * mult * period`. Every dancer is frame-locked to the music and to each other.
- **Clip period:** comes from the hips bounce.
- **Travel removal:** `stabilize` removes root travel. **Known cost:** the feet slide, because hip travel is removed but the feet aren't planted. The owner sees this as "hovering left/right". Not fixed yet.

### Lights

- **Club:** steps on bar/beat cues. Free-running phases drifted out of sync.
- **Studio:** static. Pulses are gated on `liveMix`, so silence doesn't throb.

### Avatar materials

FBX Phong is rebuilt as MeshStandardMaterial:

- **Roughness by name:** skin 0.58, leather 0.5, hair 0.65, others 0.8.
- **Environment:** RoomEnvironment at 0.45.
- **Hair-like materials:** alphaTest and alphaToCoverage, double-sided.
- **Dark diffuse factor:** when a map exists, it's forced to white. Otherwise black T-shirts.

### FBX worker

- **Effect:** the main-thread freeze went from ~440 ms to ~24 ms per 39 MB character.
- **Rule:** any new mesh feature must be added to both `serialize` and `rebuildScene`.

## Problems solved (quick reference)

| Symptom | Cause | Fix |
|---|---|---|
| Hair invisible | Packed textures had no file extension | `fix_texture_names.py` |
| Skin plastic, leather chrome | FBX Phong specular | `avatarMaterial` |
| T-shirt and jeans black | Dark diffuse factor × map | Force the colour to white when a map exists |
| Amber flying or vanishing | Metre rig vs cm clips, rescale window 0.2-5 | Window widened to 1e-4 to 1e4 |
| Hair and jacket glued to skin | Mixamo auto-weights | `cc_weights.py` |
| Dancing before Play | Chill clip picked late | Lazy `pickChillClip`; rotate only when `musicOn()` |
| Lights drifting | Speed × phase | Cue-based stepping |
| Page stutters on load | Main-thread FBX parse | Worker |
| Face shapes shattered | FBXLoader quad morph bug | Triangulate the face mesh |
| ~250 MB of graphics memory per avatar | Morphs on the whole body | Separate face mesh |
| Springs not found | Duplicate zero-length bones | Skip same-name children |
| Assets 404 on Pages | No directory listings | `manifest.json` |
| Second starter slid into place | Glide on reflow | Floor plan reserved before loading; walks only |
| Hands under the floor in freezes | Only the feet were grounded | Padded body-bone floor constraint |
| Idle bobbing | Breathing Idle beat-synced at ~1.3× | "Idle 1" at natural speed |

## Testing

### Current approach (Claude Code on this Mac)

- **No headless browser:** headless Chrome can't run inside the sandbox.
- **Node simulation instead:** the page's animation functions are extracted from index.html and run in Node against three@0.160.0 with real FBX files. This measures heights, slides and bone angles numerically.
- **Syntax check:** `node --check` on the extracted module.

### Earlier approach

Playwright with swiftshader; see [CHARACTER_PIPELINE.md](CHARACTER_PIPELINE.md) §7.

## Tooling

### Autopush watcher

- **Where it lives:** a bash loop in the Claude session scratchpad, not in the repo.
- **What it does:**
  - waits for the tree to settle;
  - shrinks any new FBX over 15MB;
  - reruns `make-manifest.sh` if assets changed;
  - commits and pushes to main.
- **Pausing:** a pause file holds it back during multi-file edits.
- **Restarting:** it has to be recreated in each new session.
- **Caution:** it pushes *anything* untracked. Add folders that must stay local to `.gitignore` before they appear.

### Other tools

- **Pages build status:** `gh api repos/nxcnew/ava4/pages/builds/latest`.
- **Blender:** not installed yet; the Blender scripts need it.

## Open items

1. **Foot sliding during dances:** a side effect of `stabilize`. The fix would be foot planting while the feet are down.
2. **Pre-play "blip out and in":** reported by the owner, not reproduced. Suspected main-thread FBX parse hitches on `file://`.
3. **Springs and faces at full frame rate:** never watched live. Tune `SPRING_TUNE` and the smile/brow strength.
4. **Studio lighting for realistic faces:** a soft key light on the dancers, without darkening the room.
5. **Character pipeline for other characters:** to be discussed.
6. **Possible move to GLB:** would avoid the FBXLoader morph and duplicate-bone bugs.
7. **Google Drive "Mixamo" / Amber_Blender folder:** set its sharing back to Restricted. It was shared as "anyone with link: Editor".
8. **Realism limits:**
   - no subsurface skin;
   - jacket sleeves and body follow the torso;
   - no eye or jaw motion on Mixamo rigs.
