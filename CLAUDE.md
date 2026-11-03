# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Dance Arena: a single-page three.js app (`index.html`, no build step, no package.json, no tests). Rigged Mixamo-style FBX characters dance to songs in switchable environments (studio, club, festival main stage, hilltop, rooftop), with a crowd, walk-ins and a player bar.

Published from `main` via GitHub Pages: https://nxcnew.github.io/ava4 (repo `nxcnew/ava4`). The user also opens `index.html` directly from disk (`file://`).

## Project docs (read these, keep them current)

- [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md): versioned log of what changed and why, owner preferences, problems solved, open items. Add a new version entry at the top for each meaningful step.
- [docs/CHARACTER_PIPELINE.md](docs/CHARACTER_PIPELINE.md): turning a character (e.g. Character Creator) into a Mixamo-rigged avatar with spring bones and face shapes; the naming contract index.html relies on; FBXLoader gotchas.
- [docs/AVATAR_BRIEF.md](docs/AVATAR_BRIEF.md): look, rig and physics brief for the new hero avatar (studio and stage outfits).
- [scripts/README.md](scripts/README.md): manifest of every helper script. Put new one-off or reusable scripts in `scripts/` and add a row.

## Workflow rules

- **Commit and push every change to `main` straight away**, including the user's own edits. The user tests on the live Pages site, so main must always be current. Check that Pages has picked up the commit with `gh api repos/nxcnew/ava4/pages/builds/latest`.
- When the user pastes code with "don't change anything else", apply exactly those edits and nothing more.
- Keys and secrets never go in index.html or the repo, because the repo is public. The Jamendo client id is entered in the panel and kept in the browser's local storage. The owner's copy is in `.secrets/keys.env` (gitignored); read it if they ask for the key.
- Push related multi-file changes together. For example, index.html and manifest.json must go up in the same commit when the manifest format changes, or the live page breaks.

## Commands

```sh
./make-manifest.sh                   # rebuild manifest.json after adding/removing/changing any asset file
python3 -B ./shrink-fbx.py avatars/X.fbx   # shrink embedded textures in a big FBX in place (original kept in avatars-original/)
python3 -m http.server               # serve locally over http (same code path as Pages)
```

There is no linter or test suite. To syntax-check the inline module script, extract it and run `node --check` on the result:

```sh
sed -n '/<script type="module">/,/<\/script>/p' index.html | sed '1d;$d' > /tmp/m.mjs && node --check /tmp/m.mjs
```

## Asset library

Folders next to `index.html`:

| Folder | Contents |
|---|---|
| `avatars/` | Character FBX files |
| `dances/` | Dance animation FBX files |
| `walks/` | Walk animation FBX files |
| `crowd/` | Crowd and idle animation FBX files |
| `songs/` | Audio files |
| `walls/` | Wallpaper images |

- **Adding a file:** drop it in and rerun `make-manifest.sh`. GitHub Pages has no directory listings, so the page reads `manifest.json` (`{dir: {file: {size, look?}}}`) to know what exists and how big each file is.
- **Wallpaper `look`:** `look` holds each wall image's aspect ratio and average hue/lightness. It is computed by the same formula as `imageLook()` in index.html; keep the two in sync.
- **Big FBX files:** Mixamo/Character Creator FBX files embed huge PNG textures. `shrink-fbx.py` rewrites the binary FBX, capping images at 2048px and spec/gloss maps at 256px, and converts images to JPEG when they have no alpha. Run it on anything over ~15MB before committing.
- **Wallpapers are JPEG:** PNGs dropped into `walls/` are converted to JPEG (quality 92) by `scripts/shrink-walls.sh` before they are committed.
- **Originals:** `*-original/` folders hold the unshrunk originals and are gitignored.
- **Size budget:** keep the repo well under GitHub's 1 GB (Pages' published-site limit is also 1 GB). The history was squashed on 2026-11-03 to drop 825 MB of old avatar versions; shrink assets before they are committed so they never enter history.

## Architecture of index.html

The file is one module script divided by `/* ---------------- Section ---------------- */` banners. Grep for them to navigate.

### Loading

- **Lazy downloads:** `RemoteFile` streams a URL with progress and exposes a File-like interface (`load()`, `arrayBuffer()`, `ready`, `progress`).
- **Starting cast:** only `START_CHARACTERS` random avatars (minus `NOT_AT_START`) and a few dances load up front.
- **Background downloads:** other avatars download when their checkbox is ticked. Their roster rows stay dimmed with a progress bar until the avatar is ready. Songs load lazily.

### FBX worker

- **Where it runs:** `WORKER_BODY` is a template string run as a module Worker. It parses FBX with FBXLoader.
- **What it sends back:** geometry, morph targets, textures as ImageBitmaps, and clips, all as transferables.
- **Rebuild:** `rebuildScene` reconstructs the scene on the main thread.
- **Changing the payload:** if you change what the worker sends, update both sides.

### Animation pipeline

- **Bone names:** `canonBone` normalises bone names across rigs.
- **Beat analysis:** `analyzeClip` finds a clip's beat period from the hips bounce.
- **In-place dances:** `stabilize` removes hip X/Z travel so dances stay on their spot.
- **Beat sync:** playback is synced to the song via `mult()`/`clipTime`.
- **Blending:** several clips blend in layers (`stateLayers` → `applyLayers`). `withChill` blends in an idle (`chillClip`, played at natural speed) when there is no music or beat.
- **Units:** hips position is rescaled when source and target rigs use different units (cm vs m).

### Grounding

`groundFeet` keeps the feet on the floor. It also keeps padded body bones (`av.body`) above the floor so inverted poses don't sink.

### Secondary motion

- **Spring bones:** `buildSprings`/`updateSprings` run a verlet solver on bones named `spring_*` (hair, cloth), with sphere colliders around the head, chest and belly.
- **Faces:** `buildFace`/`updateFace` drive Character Creator/ARKit blendshapes: blinks, smiles, brow lifts.
- **Per frame:** both run each frame after `applyLayers`.

### Arena and floor

- **Positions:** the arena has crowd seats, stage slots and a `DOOR`.
- **Small casts:** with ≤`SMALL_CAST` avatars, everyone dances on the floor. Newcomers walk in from the door and the others walk to new slots (`placeOnFloor`).
- **Positions never jump:** don't add sliding or teleporting between positions; every reposition is a walk.
- **Walk clips:** `walkState` picks a plain walk for entering and between songs, and a dancy walk only sometimes mid-song.

### Studio scene

- **Mirror:** the Studio has a Reflector mirror wall.
- **Back-wall copies:** the wall behind the camera exists twice, one copy on layer `MIRROR_ONLY` and one on `DIRECT_ONLY`. The image is the right way round on the wall; the mirror shows its true, reversed reflection.
- **Wallpaper pairing:** `randomWalls` reserves wide images (aspect ≥ 1.2) for the back wall/mirror. It gives the side walls hue-matched non-wide images.

### Camera

OrbitControls allows 360° rotation horizontally. The vertical range (`maxPolarAngle = Math.PI * 0.53`) is deliberately tuned; don't change it.
