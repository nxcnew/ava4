# Scripts manifest

Every helper script for this project, with what it's for and how to run it. Add a row when a script is added, and remove the row when the script is deleted.

| Script | Purpose | Run | Needs |
|---|---|---|---|
| `../make-manifest.sh` | Rebuilds `manifest.json`: file sizes for every asset folder, plus the shape and colour of each wall image. Run it after any asset change. The autopush watcher also runs it. | `./make-manifest.sh` | python3, sips (macOS) |
| `../shrink-fbx.py` | Shrinks textures embedded in a binary FBX in place: 2048px maximum, 256px for spec/gloss maps, JPEG when there's no alpha. Keeps the original in `<dir>-original/`. The watcher runs it on FBX files over 15MB. | `python3 -B ./shrink-fbx.py avatars/X.fbx` | python3, sips |
| `shrink-walls.sh` | Converts wallpaper PNGs in `walls/` to JPEG (quality 92, visually lossless) with the same name, and moves the originals to `walls-original/` (gitignored). Skips images with transparency. The watcher runs it on any PNG in `walls/` before committing. | `scripts/shrink-walls.sh [walls/x.png ...]` | sips (macOS) |
| `faces.swift` | Finds faces in images with macOS Vision and prints them as JSON (`[x, top, w, h]` fractions). `make-manifest.sh` runs it on `walls/` and stores the result as `look.faces`. | `swift scripts/faces.swift walls/*.png` | swift (Xcode command-line tools) |
| `blender/cc_prep.py` | Character pipeline step 1: turns a Character Creator export into a light, unrigged mesh. | `blender -b -P scripts/blender/cc_prep.py -- <cc.fbx> <work>` | Blender 4.x |
| `blender/fix_texture_names.py` | Step 2: names packed images `.png`/`.jpg` and exports `for_mixamo.fbx`. | `blender -b -P scripts/blender/fix_texture_names.py -- <work>` | Blender |
| `blender/cc_weights.py` | Step 4: copies the original CC skin weights onto Mixamo's rigged mesh. Step 5 also uses it as a library. | `blender -b -P scripts/blender/cc_weights.py -- <mixamo.fbx> <cc.fbx>` | Blender |
| `blender/add_springs_face.py` | Step 5: adds spring-bone chains and face shapes, splits off the face mesh, exports the finished avatar. | `blender -b -P scripts/blender/add_springs_face.py -- <mixamo.fbx> <cc.fbx> <out.fbx>` | Blender |

**The Blender scripts:**

- Each has a `CONFIG` block holding Amber's values: object names, ratios, thresholds and material names. Re-measure them for each new character.
- The full walkthrough is in [docs/CHARACTER_PIPELINE.md](../docs/CHARACTER_PIPELINE.md).
- They came from the earlier `amber-pipeline/` folder. Paths are now arguments, and Amber-specific values are gathered into `CONFIG`; the logic is unchanged.
- Two other changes:
  - The output objects are renamed: `Amber` → `Character` and `Amber_Face` → `Face`.
  - `cc_prep.py` no longer writes an extra `for_mixamo_v2.fbx`; the upload file comes from step 2.

**Not in the repo:** the autopush watcher is a Claude session tool and lives outside the repo. It's described in [docs/KNOWLEDGE.md](../docs/KNOWLEDGE.md).
