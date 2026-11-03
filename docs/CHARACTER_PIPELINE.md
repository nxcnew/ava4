# Character pipeline

How a character becomes a working avatar in Dance Arena. This includes the spring-bone and face-shape contract the page relies on. Amber is the worked example: a CGTrader Character Creator 4 model, rigged through Mixamo. The same steps will be needed for other characters.

The scripts are in [scripts/blender/](../scripts/blender/) and listed in [scripts/README.md](../scripts/README.md). They need Blender (`blender -b -P <script> -- <args>`) or the `bpy` pip module. Neither is installed on this Mac yet.

## 1. Basics

### Mixamo exports

- **Characters:** FBX Binary, T-pose, **With Skin**.
- **Dances:** **Without Skin**.

### Mixamo auto-rigger limits

- **Weights:** it weights the whole merged mesh like skin, so hair and clothes stretch and look glued on.
- **Skeleton:** it returns a reduced skeleton. Amber got 33 bones, with only the index finger.
- **Its own viewer:** it makes realistic characters look plastic. Judge characters in the page instead.

### Mixamo bulk API

- **Endpoints:** `/api/v1/products`, `/api/v1/animations/export` and `/api/v1/characters/{id}/monitor`.
- **Export keys:** use the gms_hash keys `model-id` and `arm-space`. Snake_case keys fail.
- **Rate limits:** retry with backoff on 429.

### Mixamo returns the mesh vertex-for-vertex

The returned mesh has the same vertex order as the upload, with positions within a micron. That's why the original weights and shapes can be transferred back by position.

### Blender round-trip of a Mixamo rig

- **Bind pose:** it stays identical, under 0.03° per bone.
- **Armature node:** the export adds an "Armature" node with scale 100. The page's hips rescale absorbs it.
- **Dances:** Mixamo dances still work unchanged.

## 2. Steps (Character Creator source)

| Step | Script | What it does |
|---|---|---|
| 1 | `cc_prep.py <cc.fbx> <work>` | Drops helper meshes (underwear, EyeOcclusion, TearLine). Strips rig, shape keys and weights. Decimates: body 12%, jeans 12%, jacket 25%; hair cards are un-subdivided ×2. Merges opacity into colour as `_RGBA` PNG. Kills specular. Textures go to 1024px, except the head at 2048. Joins everything into one mesh and saves `prepped.blend`. |
| 2 | `fix_texture_names.py <work>` | Gives packed images `.png`/`.jpg` names, then exports `for_mixamo.fbx`. |
| 3 | manual | Upload to Mixamo, place markers, auto-rig, then download T-pose With Skin. |
| 4 | `cc_weights.py <mixamo.fbx> <cc.fbx>` | Renames CC vertex groups to Mixamo bones (`mx()`, table below). Transfers the original hand-made weights per garment, matched by material name. Hair pieces are joined first. |
| 5 | `add_springs_face.py <mixamo.fbx> <cc.fbx> <out.fbx>` | Runs step 4, then adds spring chains and weights and transfers face shapes. Splits the face into its own triangulated mesh and exports. |
| 6 | repo | Put the result in `avatars/`. `shrink-fbx.py` runs if it's over 15MB, then `make-manifest.sh`. |

### Per-character settings

Each script has a `CONFIG` block holding Amber's values:

- object names;
- decimation ratios;
- hair and jacket thresholds;
- face material names.

These must be re-measured for each new character.

### CC → Mixamo bone map

CC keeps most of the weight on twist bones, so the twist bones carry the main mappings.

| Character Creator | Mixamo |
|---|---|
| Pelvis, Hip | Hips |
| Waist | Spine |
| Spine01 | Spine1 |
| Spine02, Breast, RibsTwist | Spine2 |
| NeckTwist* | Neck |
| Head, JawRoot, Eye, Teeth*, Tongue* | Head |
| Clavicle | Shoulder |
| UpperarmTwist* | Arm |
| ForearmTwist*, ElbowShareBone | ForeArm |
| Index1-3 | HandIndex1-3 (or Hand if the rig lacks them) |
| Hand, other fingers | Hand |
| ThighTwist* | UpLeg |
| CalfTwist*, KneeShareBone | Leg |
| Foot | Foot |
| *Toe1 | ToeBase |

## 3. The naming contract (asset ↔ index.html)

The page animates any avatar that follows these names. No per-avatar code is needed.

### Spring bones

- **Names:** `spring_<chain>_<n>`, numbered from 1 at the root, plus `spring_<chain>_end`. The end bone is unweighted and only marks the last tip.
- **Parenting:** the chain root is parented to the body bone it hangs from (Head, Spine2, Spine1). Each next bone is parented to the previous one.
- **Connection and roll:** neither matters.
- **Kind:** the chain name sets the physics kind (`SPRING_TUNE` in index.html):

| Name contains | Kind | stiff | drag | grav | Feel |
|---|---|---|---|---|---|
| hair, bang, fringe, pony, braid | hair | 2.4 | 0.32 | 0 | Light and lively. No gravity, because modelled hair already hangs. |
| jacket, coat, skirt, dress, cloth, cape, hem | cloth | 4.5 | 0.5 | 0.8 | Heavier, damped. |
| anything else | other | 3.0 | 0.4 | 0.5 | In between. |

Tuning ranges:

- **stiff:** 1.5-6; higher snaps back faster.
- **drag:** 0.2-0.7; 0 is bouncy, 1 has no momentum.
- **Long skirt idea:** stiff 3, drag 0.5, grav 1.0.

### Face shapes

These are FBX blendshapes with CC **or** ARKit names (`FACE_SHAPES` in index.html):

| Role | CC | ARKit |
|---|---|---|
| blink | Eye_Blink_L/R | eyeBlinkLeft/Right |
| smile | Mouth_Smile_L/R | mouthSmileLeft/Right |
| cheek raise | Cheek_Raise_L/R | cheekSquintLeft/Right |
| eye squint | Eye_Squint_L/R | eyeSquintLeft/Right |
| brow outer up | Brow_Raise_Outer_L/R | browOuterUpLeft/Right |
| brow inner up | Brow_Raise_Inner_L/R | browInnerUp |

Shapes with other names are ignored. Amber also carries Eye_Wide, Brow_Drop and Mouth_Press for later.

### Shape-carrying meshes

Any mesh that carries shapes must be:

- **Separate:** a small face mesh, not the whole body.
- **All triangles:** see gotchas 1 and 2.

## 4. How Amber's chains were built (step 5 detail)

### Hair islands

Hair cards are found by union-find over the hair faces. Each island is classified by its centroid and lowest point. Axes are Blender's: front is −Y, up is +Z; heights are in metres.

| Chain | Rule | Bones | Spring share over t |
|---|---|---|---|
| hairBack L/R | lowest < 1.50, centroid y > 0.04 | 3 | smoothstep 0.45-0.8 (hugs the skull longer) |
| hairBang L/R | centroid y < −0.03, lowest < 1.60 | 2 | 0.2-0.6 |
| hairSide L/R | \|x\| > 0.06, lowest < 1.52 | 3 | 0.3-0.7 |
| rest (bun…) | stays rigid on Head | - | - |

Whole islands are classified, never single vertices, so a strand is never split between moving and still.

### Jacket panels

| Chain | Region | Root | Bones | Spring share over t |
|---|---|---|---|---|
| jacketFrontL/R | front, \|x\| < 0.19, below 1.30 | 1.28 (chest), parent Spine2 | 2 | 0.40-0.95 (below the bust) |
| jacketBack | back, \|x\| < 0.19, below 1.16 | 1.16, parent Spine1 | 2 | 0.25-0.95 |

Jacket weights fade out towards the side seams (\|x\| 0.13 → 0.185), so the panels never tear away from them.

### Chain geometry

- **Hair root:** the mean of the cluster's top 8% of vertices.
- **Hair tip:** the mean of its bottom 6%.
- **Bones:** split evenly from root to tip.

### Weights

1. `t` is the projection of each vertex onto the root→tip line.
2. The spring share is `s` = smoothstep(t).
3. Body weights are scaled by (1−s).
4. The chain bones get `s`, blended linearly between neighbouring bones.
5. Everything is normalised.

### Face shapes

- **Source:** the original high-res CC meshes, which keep their shape keys.
- **Matching:** each target vertex above 1.40 m is matched to the closest point on the **same material's** surface (BVH). Lids and lashes are millimetres apart, so matching across materials fails.
- **Deltas:** the shape deltas are interpolated barycentrically and converted from source local to world to target local.

### Face split

- **Normals:** custom normals are frozen first, so the neck cut doesn't show.
- **Split:** the face mesh (head skin, lashes, brows) is separated out.
- **Triangulate:** the face mesh is triangulated.
- **Clean up:** the body loses its shape keys.

### Result

22 spring bones and 18 face shapes, 12 of them used; 32 MB.

## 5. Gotchas (three.js r160 FBXLoader and Blender)

### 1. Quad morph bug

- **Cause:** `genMorphGeometry` passes the morph *deltas* as positions to earcut, so n-gons triangulate differently from the base mesh.
- **Symptom:** shattered faces.
- **Fix:** shape-carrying meshes must be all triangles.

### 2. Morph memory

- **Cause:** FBXLoader de-indexes geometry, and three keeps morphs in a float texture of about expandedVerts × targets × 16 B. For Amber's whole body (~863k expanded vertices) with 18 targets, that's ~250 MB.
- **Fix:** a face-only mesh (~40k expanded vertices) needs ~10 MB.

### 3. Duplicate bones

- **Cause:** with two or more skinned meshes, FBXLoader adds a zero-length bone with the same name as a child of each bone.
- **Fix:** code that walks bone chains must skip them. `buildSprings` does.

### 4. Worker drops unknown data

- **Cause:** the page's FBX worker serialises geometry by hand.
- **Fix:** any new mesh feature must be added to both `serialize` and `rebuildScene`. Morphs were added on 2026-11-02 (v2 in [KNOWLEDGE.md](KNOWLEDGE.md)).

### 5. `canonBone` prefixes every bone with `mixamorig`

- **Effect:** springs become `mixamorigspring_…`.
- **Rule:** always detect them with `/spring_/` anywhere in the name.

### 6. Texture decoder by extension

- **Cause:** the loader picks the decoder from the image name; packed images with no `.png`/`.jpg` never load.
- **Fix:** run step 2 (`fix_texture_names.py`).

### 7. Unparenting in Blender

Keep the world matrix: `mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw`. Otherwise the meshes jump and the weights come out as garbage.

### 8. Duplicate material names

A second import suffixes material names `.001`. Strip the suffix (`re.sub(r'\.\d+$', '', n)`) before comparing, or matching silently does nothing.

### 9. Script names

Never name a script `inspect.py`, because it shadows the stdlib module and breaks bpy. Run Python with `-I`.

## 6. Spec for a commissioned avatar

- **Target:** real-time web, 30-60k triangles, 2K textures, hair cards.
- **Skeleton:** Mixamo-compatible (mixamorig names), plus spring chains per section 3 (ponytail, bangs, skirt, coat tails…).
- **Face:** ARKit 52 blendshapes on a **separate, triangulated** head mesh.
- **Format:** GLB preferred, or FBX while the page stays on FBXLoader. GLTFLoader would avoid gotchas 1 and 3, and GLB files are smaller.

## 7. Testing what worked

### Numeric checks over visuals

Software GL is about 1 fps, so short effects like blinks can't be judged by eye. Check values instead:

- morph influences;
- bone angle versus rest, over time.

### Data or GPU?

To tell whether a visual bug is in the data or the GPU path, bake skinned and morphed vertices on the CPU (`mesh.getVertexPosition(i, v)`) into a static mesh and render that.

### Blender check

Re-import the exported FBX and measure the shape deltas per region before blaming the loader.

### Earlier headless harness

The earlier assistant's harness (not available in this sandbox):

- Playwright Chromium with `--use-gl=swiftshader --enable-unsafe-swiftshader`;
- a local import map;
- `window.__arena` hooks.

The current approach is in [KNOWLEDGE.md](KNOWLEDGE.md), "Testing".
