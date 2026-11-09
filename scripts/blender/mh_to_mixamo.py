# MetaHuman (Unreal FBX export) -> Mixamo-convention FBX that index.html can load and play Mixamo dances on.
#
#   Blender -b --python scripts/blender/mh_to_mixamo.py -- \
#       --body body.fbx --face face.fbx --maps <DCC export Maps dir> --hair <hair dir> --ref avatars/Janine.fbx --out avatars/X.fbx
#
# What it does:
#  1. imports the MetaHuman body and face (A-pose, UE bone names, ~340 body / ~870 face bones);
#  2. poses arms, legs, hands and fingers so each bone points the same way as the reference Mixamo
#     skeleton's bone (T-pose), and applies that pose to the meshes;
#  3. builds a Mixamo skeleton (mixamorig:Hips ... fingers) at the MetaHuman joint positions, with each
#     bone's roll copied from the reference skeleton, so Mixamo dance quaternions drive it correctly;
#  4. merges every MetaHuman vertex group (twist, corrective, facial bones) into its nearest mapped ancestor;
#  5. binds the hair cards (Unreal groom cards FBX) to the head; spring bones come later;
#  6. sets up materials from the DCC export maps and writes an FBX with embedded textures.
import bpy, sys, os, math, argparse
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--body", required=True); ap.add_argument("--face", required=True)
ap.add_argument("--outfit"); ap.add_argument("--arkit"); ap.add_argument("--maps"); ap.add_argument("--hair"); ap.add_argument("--hair-lod", default="0")
ap.add_argument("--ref", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--keep-face-shapes", default="")  # comma list of MetaHuman shape names to keep (debug)
A = ap.parse_args(argv)

P = "mixamorig:"
L = {  # MetaHuman bone -> Mixamo bone (without prefix); sides expanded below
    "pelvis": "Hips", "spine_01": "Spine", "spine_03": "Spine1", "spine_05": "Spine2", "neck_01": "Neck", "head": "Head",
}
for s, S in (("l", "Left"), ("r", "Right")):
    L.update({f"clavicle_{s}": f"{S}Shoulder", f"upperarm_{s}": f"{S}Arm", f"lowerarm_{s}": f"{S}ForeArm", f"hand_{s}": f"{S}Hand",
              f"thigh_{s}": f"{S}UpLeg", f"calf_{s}": f"{S}Leg", f"foot_{s}": f"{S}Foot", f"ball_{s}": f"{S}ToeBase"})
    for f, F in (("thumb", "Thumb"), ("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("pinky", "Pinky")):
        for i in (1, 2, 3):
            L[f"{f}_0{i}_{s}"] = f"{S}Hand{F}{i}"
MIX_PARENT = {}  # mixamo name -> parent mixamo name (from the reference)
MIX_ORDER = []

def log(*a): print("[mh2mix]", *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

def import_fbx(path, **kw):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, **kw)
    return [o for o in bpy.data.objects if o not in before]

def bake_transforms(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ---- reference Mixamo skeleton: bone directions and roll axes in world space (meters, Z up, -Y forward)
ref_objs = import_fbx(A.ref, automatic_bone_orientation=False)
ref = next(o for o in ref_objs if o.type == "ARMATURE")
REF = {}
for b in ref.data.bones:
    n = b.name.split(":")[-1]
    m = ref.matrix_world @ b.matrix_local
    REF[n] = dict(y=Vector(m.col[1][:3]).normalized(), z=Vector(m.col[2][:3]).normalized(),
                  head=ref.matrix_world @ b.head_local, parent=b.parent.name.split(":")[-1] if b.parent else None)
    MIX_ORDER.append(n)
    MIX_PARENT[n] = REF[n]["parent"]
for o in ref_objs: bpy.data.objects.remove(o, do_unlink=True)
log("reference bones:", len(REF))

# ---- MetaHuman
body_objs = import_fbx(A.body)
face_objs = import_fbx(A.face)
barm = next(o for o in body_objs if o.type == "ARMATURE"); bmesh = next(o for o in body_objs if o.type == "MESH")
farm = next(o for o in face_objs if o.type == "ARMATURE"); fmesh = next(o for o in face_objs if o.type == "MESH")
omesh = None
if A.outfit:
    out_objs = import_fbx(A.outfit)
    omesh = next(o for o in out_objs if o.type == "MESH")
    oarm = next(o for o in out_objs if o.type == "ARMATURE")
    for m in omesh.modifiers:
        if m.type == "ARMATURE": m.object = barm
    omesh.parent = barm
    bpy.data.objects.remove(oarm, do_unlink=True)
for o in (barm, farm): o.data.pose_position = "POSE"
log("body bones", len(barm.data.bones), "face bones", len(farm.data.bones), "face shapes", len(fmesh.data.shape_keys.key_blocks) if fmesh.data.shape_keys else 0)

# Face shape keys: keep them aside (ARKit set is baked separately); they block applying the pose.
if fmesh.data.shape_keys:
    keep = set(filter(None, A.keep_face_shapes.split(",")))
    for kb in list(fmesh.data.shape_keys.key_blocks)[::-1]:
        if kb.name != "Basis" and kb.name.split("__")[-1] not in keep: fmesh.shape_key_remove(kb)
    if len(fmesh.data.shape_keys.key_blocks) == 1: fmesh.shape_key_clear()

def world_head(arm, name):
    return arm.matrix_world @ arm.pose.bones[name].head

def child_of(name):
    """MetaHuman joint whose position defines this bone's direction."""
    mix = L[name]
    kids = [k for k, v in MIX_PARENT.items() if v == mix]
    pref = [k for k in kids if "Middle1" in k] or [k for k in kids if k.endswith(("ForeArm", "Hand", "Leg", "Foot", "ToeBase")) or k[-1:] in "23"] or kids
    inv = {v: k for k, v in L.items()}
    for k in pref:
        if k in inv: return inv[k]
    return None

ALIGN = [k for k in L if any(t in L[k] for t in ("Shoulder", "Arm", "Hand", "UpLeg", "Leg", "Foot")) and "ToeBase" not in L[k]]
# parents first: sort by depth in the MetaHuman hierarchy
ALIGN.sort(key=lambda n: len(barm.data.bones[n].parent_recursive) if n in barm.data.bones else 0)

bpy.context.view_layer.objects.active = barm
bpy.ops.object.mode_set(mode="POSE")
for n in ALIGN:
    c = child_of(n)
    if not c or n not in barm.pose.bones or c not in barm.pose.bones: continue
    h, t = world_head(barm, n), world_head(barm, c)
    cur = (t - h).normalized(); tgt = REF[L[n]]["y"]
    q = cur.rotation_difference(tgt)
    pb = barm.pose.bones[n]
    mw = barm.matrix_world @ pb.matrix
    R = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h)
    pb.matrix = barm.matrix_world.inverted() @ (R @ mw)
    bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode="OBJECT")
# copy the same pose onto the face armature (shared bone names)
for pb in sorted(farm.pose.bones, key=lambda p: len(p.parent_recursive)):
    if pb.name in barm.pose.bones:
        pb.matrix = farm.matrix_world.inverted() @ barm.matrix_world @ barm.pose.bones[pb.name].matrix
        bpy.context.view_layer.update()
log("posed to T")

def add_arkit(mesh, path):
    """ARKit shapes baked from the MetaHuman face rig (bake_arkit.py): per-vertex deltas in this mesh's local space."""
    import numpy as np
    D = np.load(path); n = len(mesh.data.vertices)
    co = np.empty(n * 3, np.float32); mesh.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    if D["base"].shape[0] != n: log("ARKit vertex count mismatch", D["base"].shape[0], n); return
    mesh.shape_key_add(name="Basis", from_mix=False)
    for k in D.files:
        if k == "base": continue
        kb = mesh.shape_key_add(name=k[0].lower() + k[1:], from_mix=False)
        kb.data.foreach_set("co", (co + D[k]).ravel())
    log("ARKit shapes:", len(D.files) - 1)

def apply_armature(mesh):
    bpy.ops.object.select_all(action="DESELECT"); bpy.context.view_layer.objects.active = mesh; mesh.select_set(True)
    for m in mesh.modifiers:
        if m.type == "ARMATURE": bpy.ops.object.modifier_apply(modifier=m.name)
    if mesh is fmesh and A.arkit: add_arkit(mesh, A.arkit)
    # Unreal FBX imports put a 0.01 scale on the armature object; bake the world transform into the mesh
    mw = mesh.matrix_world.copy(); mesh.parent = None; mesh.matrix_world = mw
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for m in (bmesh, fmesh) + ((omesh,) if omesh else ()): apply_armature(m)

# joint positions (world) after posing
J = {L[n]: world_head(barm, n).copy() for n in L if n in barm.pose.bones}
# end joints: extend each chain end by the last segment
for n in list(L.values()):
    kids = [k for k, v in MIX_PARENT.items() if v == n]
    for k in kids:
        if k not in J and k in REF:
            par = MIX_PARENT[n]
            seg = (J[n] - J[par]) if par in J else REF[k]["head"] - REF[n]["head"]
            if k == "HeadTop_End": J[k] = J[n] + Vector((0, 0, 0.21 * (J["Head"].z / 1.53)))
            elif k.endswith("Toe_End"): J[k] = J[n] + (REF[k]["head"] - REF[n]["head"])
            else: J[k] = J[n] + REF[k]["y"] * 0 + seg.normalized() * max(seg.length * 0.8, 0.01)
# MetaHuman hierarchy for vertex-group merging, captured before the source armatures are deleted
MH_PARENT = {}
for arm in (barm, farm):
    for b in arm.data.bones: MH_PARENT.setdefault(b.name, b.parent.name if b.parent else None)

# ---- new Mixamo armature
adata = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", adata)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = {}
for n in MIX_ORDER:
    if n not in J: continue
    e = adata.edit_bones.new(P + n); eb[n] = e
    e.head = J[n]
    kids = [k for k, v in MIX_PARENT.items() if v == n and k in J]
    pick = ([k for k in kids if "Middle1" in k or k in ("Spine", "Spine1", "Spine2", "Neck", "Head", "HeadTop_End")] or
            [k for k in kids if not any(s in k for s in ("Shoulder", "UpLeg", "Thumb", "Index", "Ring", "Pinky"))] or kids)
    tail = J[pick[0]] if pick else J[n] + REF[n]["y"] * 0.03
    if (tail - e.head).length < 1e-4: tail = e.head + REF[n]["y"] * 0.03
    e.tail = tail
    e.align_roll(REF[n]["z"])
for n, e in eb.items():
    par = MIX_PARENT.get(n)
    if par in eb: e.parent = eb[par]
bpy.ops.object.mode_set(mode="OBJECT")
log("mixamo bones:", len(adata.bones))

# ---- vertex groups: merge every MetaHuman group into its mapped ancestor
def target_of(name):
    n = name
    while n is not None:
        if n in L: return P + L[n]
        n = MH_PARENT.get(n)
    return P + "Head" if name.startswith("FACIAL") else P + "Hips"

def remap_groups(mesh):
    import numpy as np
    vg = mesh.vertex_groups
    nv = len(mesh.data.vertices)
    acc = {}
    idx = {g.index: g.name for g in vg}
    for v in mesh.data.vertices:
        for g in v.groups:
            if g.weight <= 0: continue
            t = target_of(idx[g.group])
            acc.setdefault(t, {}); acc[t][v.index] = acc[t].get(v.index, 0) + g.weight
    vg.clear()
    for t, d in acc.items():
        g = vg.new(name=t)
        for i, w in d.items(): g.add([i], min(w, 1.0), "REPLACE")
    m = mesh.modifiers.new("Armature", "ARMATURE"); m.object = arm
    mesh.parent = arm
for m in (bmesh, fmesh) + ((omesh,) if omesh else ()): remap_groups(m)
for o in (barm, farm): bpy.data.objects.remove(o, do_unlink=True)
log("weights merged")

# ---- tidy the face: drop hidden/shell geometry that only Unreal's shaders use
def drop_material_faces(mesh, names):
    import bmesh as bm_
    slots = [i for i, s in enumerate(mesh.material_slots) if s.material and any(k in s.material.name for k in names)]
    if not slots: return
    b = bm_.new(); b.from_mesh(mesh.data)
    bm_.ops.delete(b, geom=[f for f in b.faces if f.material_index in slots], context="FACES")
    b.to_mesh(mesh.data); b.free()
drop_material_faces(fmesh, ("M_Hide", "EyeShell", "LacrimalFluid"))
bpy.ops.object.select_all(action="DESELECT"); bpy.context.view_layer.objects.active = fmesh; fmesh.select_set(True)
bpy.ops.object.material_slot_remove_unused()

# ---- hair cards and eyebrow cards (Unreal groom cards, fitted to this head by the MetaHuman build)
def bind_to_head(o):
    g = o.vertex_groups.new(name=P + "Head"); g.add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
    m = o.modifiers.new("Armature", "ARMATURE"); m.object = arm; o.parent = arm

hair_objs, brow_objs = [], []
if A.hair and os.path.isdir(A.hair):
    for f in sorted(os.listdir(A.hair)):
        is_hair = f.startswith("cards_") and f.endswith(f"_lod{A.hair_lod}.fbx")
        is_brow = f == "brows_lod0.fbx"
        if not (is_hair or is_brow): continue
        for o in import_fbx(os.path.join(A.hair, f)):
            if o.type != "MESH": bpy.data.objects.remove(o, do_unlink=True); continue
            bake_transforms([o]); o.name = ("Hair_" + f[6:8]) if is_hair else "Brows"
            bind_to_head(o)
            (hair_objs if is_hair else brow_objs).append(o)
    log("hair meshes:", [(o.name, len(o.data.vertices)) for o in hair_objs + brow_objs])

# ---- generated RGBA textures (colour + coverage in alpha, which the page alpha-tests on hair/brow/lash materials)
import numpy as np
TEX = os.path.join(os.path.dirname(os.path.abspath(A.out)), "tex"); os.makedirs(TEX, exist_ok=True)
def load_np(path, size=None):
    im = bpy.data.images.load(path)
    if size and im.size[0] != size: im.scale(size, size)
    w, h = im.size; a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels); bpy.data.images.remove(im); return a
def save_rgba(name, rgb, alpha):
    h, w = alpha.shape; px = np.concatenate([rgb, alpha[..., None]], 2).astype(np.float32)
    im = bpy.data.images.new(name, w, h, alpha=True); im.pixels = px.ravel()
    im.filepath_raw = os.path.join(TEX, name + ".png"); im.file_format = "PNG"; im.save(); return im
def strand_texture(name, src, size, dark, light, gain=1.0):
    a = load_np(src, size); cov = np.clip(a[..., 0] * gain, 0, 1)
    shade = np.clip(0.55 + 0.9 * a[..., 2], 0, 1.4)[..., None]   # depth channel: deeper strands darker
    rgb = np.clip(np.array(dark)[None, None] * (1 - a[..., 1:2]) + np.array(light)[None, None] * a[..., 1:2], 0, 1) * shade
    return save_rgba(name, np.clip(rgb, 0, 1), cov)

# ---- materials
def img(path, size=2048):
    """Opaque maps go into the FBX as JPEG (quality 88), so the page downloads far less."""
    if not (path and os.path.exists(path)): return None
    import subprocess
    out = os.path.join(TEX, os.path.splitext(os.path.basename(path))[0] + ".jpg")
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "88", "-Z", str(size), path, "--out", out], check=True, capture_output=True)
    return bpy.data.images.load(out, check_existing=True)

def make_mat(name, base=None, normal=None, rough=0.5, alpha=False, color=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
    # Blender's default emission colour is white at strength 0; the FBX exporter writes the white and three.js glows.
    for k in ("Emission Color", "Emission"):
        if k in bsdf.inputs and bsdf.inputs[k].type == "RGBA": bsdf.inputs[k].default_value = (0, 0, 0, 1)
    if color: bsdf.inputs["Base Color"].default_value = color
    if base:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = base; nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha: nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"])
    if normal:
        normal.colorspace_settings.name = "Non-Color"
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = normal
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(t.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if alpha and hasattr(m, "blend_method"): m.blend_method = "HASHED"
    return m

MP = A.maps or ""
mp = lambda f: os.path.join(MP, f)
lash = None
if os.path.exists(mp("Eyelashes_Color.png")):
    la = load_np(mp("Eyelashes_Color.png"), 1024)
    lum = la[..., :3].mean(2)
    lash = save_rgba("Hero_Lashes", np.zeros(la.shape[:2] + (3,), np.float32) + 0.02, np.clip((1 - lum) * 2.2, 0, 1))
mats = {
    "Face": make_mat("Hero_Face", img(mp("Head_Basecolor.png")), img(mp("Head_Normal.png")), rough=0.45),
    "Body": make_mat("Hero_Body", img(mp("Body_Basecolor.png")), img(mp("Body_Normal.png"), 1024), rough=0.5),
    "Teeth": make_mat("Hero_Teeth", img(mp("Teeth_Color.png"), 512), None, rough=0.3),
    "EyeL": make_mat("Hero_Eye", img(mp("Eyes_Color.png"), 512), None, rough=0.05),
    "Lash": make_mat("Hero_Lashes", lash, alpha=True, rough=0.6),
}
def assign(mesh):
    for s in mesh.material_slots:
        n = s.material.name if s.material else ""
        s.material = (mats["Face"] if "Skin" in n or "Face_Skin" in n else mats["Body"] if "Body" in n else mats["Teeth"] if "Teeth" in n
                      else mats["EyeL"] if "Eye" in n and "lash" not in n.lower() else mats["Lash"] if "lash" in n.lower() else s.material)
assign(fmesh); assign(bmesh)
if hair_objs:
    ht = strand_texture("Hero_Hair", os.path.join(A.hair, "CardsAtlas_Attribute.png"), 2048, (0.055, 0.032, 0.018), (0.30, 0.17, 0.08), gain=2.2)
    hm = make_mat("Hero_Hair", ht, alpha=True, rough=0.45)
    for o in hair_objs: o.data.materials.clear(); o.data.materials.append(hm)
if brow_objs and os.path.exists(os.path.join(A.hair, "Brows_Attribute.png")):
    bt = strand_texture("Hero_Brows", os.path.join(A.hair, "Brows_Attribute.png"), 1024, (0.03, 0.02, 0.015), (0.06, 0.04, 0.03), gain=1.3)
    bm = make_mat("Hero_Brows", bt, alpha=True, rough=0.6)
    for o in brow_objs: o.data.materials.clear(); o.data.materials.append(bm)
fmesh.name = "Hero_Head"; bmesh.name = "Hero_Body"
if omesh:
    omesh.name = "Hero_Outfit"
    om = make_mat("Hero_Outfit", rough=0.8, color=(0.75, 0.75, 0.78, 1))
    omesh.data.materials.clear(); omesh.data.materials.append(om)
# Unreal's vertex colours are shader masks, not colours; the page would tint the skin with them.
for o in [fmesh, bmesh] + ([omesh] if omesh else []) + hair_objs + brow_objs:
    while o.data.color_attributes: o.data.color_attributes.remove(o.data.color_attributes[0])
hair_objs += brow_objs

# ---- export
# Mixamo files are Y-up with no rotation on any node above the Hips; the page plays dance quaternions straight
# onto the bones, so a leftover axis-conversion rotation would tip every dance over. Rotate the rig into Y-up here
# (Blender -Y forward becomes +Z), bake that into the data, and export with no axis conversion.
os.makedirs(os.path.dirname(os.path.abspath(A.out)), exist_ok=True)
parts = [fmesh, bmesh] + hair_objs + ([omesh] if omesh else [])
for o in parts:   # unparent with world transform kept, so the armature can be baked on its own
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
for o in [arm] + parts:
    o.matrix_world = Matrix.Rotation(math.radians(-90), 4, "X") @ o.matrix_world
bpy.ops.object.select_all(action="DESELECT")
for o in [arm] + parts: o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in parts: o.parent = arm
bpy.ops.object.select_all(action="DESELECT")
for o in [arm] + parts: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=A.out, use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
                         primary_bone_axis="Y", secondary_bone_axis="X", bake_anim=False, path_mode="COPY", embed_textures=True,
                         mesh_smooth_type="FACE", use_armature_deform_only=True, apply_scale_options="FBX_SCALE_ALL",
                         axis_forward="Y", axis_up="Z")
log("wrote", A.out, os.path.getsize(A.out) // 1024, "KB")
