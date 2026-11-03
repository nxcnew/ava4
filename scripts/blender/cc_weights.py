"""Step 4 (library + standalone): put the original Character Creator skin weights onto Mixamo's auto-rigged mesh.

    blender -b -P scripts/blender/cc_weights.py -- <mixamo .fbx> <original CC .fbx>

Mixamo weights the whole merged mesh like skin, so hair and clothes look glued on. Mixamo returns the uploaded mesh
vertex-for-vertex, so the hand-made CC weights can be transferred by position, garment by garment (matched through
material names), after renaming CC vertex groups to Mixamo bones (mx()).
Leaves globals for add_springs_face.py: arm, tgt (rigged mesh), src (original meshes, already renamed), bones, base().
Origin: amber-pipeline/amber_base.py.
"""
import bpy, re, sys
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

MIXAMO_FBX, CC_FBX = sys.argv[sys.argv.index('--') + 1:][:2]

# ---- CONFIG (per character) ----
SKIP = r'Underwear|EyeOcclusion|TearLine'            # meshes that were dropped in cc_prep.py
HAIR_PARTS = ('Bang', 'Bun', 'Real_Hair', 'Hair_Base')  # joined first, so cards weight as one garment
# --------------------------------

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MIXAMO_FBX)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); tgt = next(o for o in bpy.data.objects if o.type == 'MESH')
mx_objs = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=CC_FBX)
src = [o for o in bpy.data.objects if o not in mx_objs and o.type == 'MESH' and not re.search(SKIP, o.name)]
for o in [o for o in bpy.data.objects if o not in mx_objs and o not in src]: bpy.data.objects.remove(o, do_unlink=True)
for o in src:
    for m in list(o.modifiers): o.modifiers.remove(m)
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw  # without this the meshes jump and weights are garbage
bpy.context.view_layer.update()

# Sanity check: source and target should coincide (median distance in mm should be ~0)
kd = KDTree(len(tgt.data.vertices))
for v in tgt.data.vertices: kd.insert(tgt.matrix_world @ v.co, v.index)
kd.balance()
for o in src:
    vs = o.data.vertices; step = max(1, len(vs) // 300)
    d = sorted(kd.find(o.matrix_world @ vs[i].co)[2] for i in range(0, len(vs), step))
    print('ALIGN', o.name, round(d[len(d) // 2] * 1000, 2), 'mm')

def mx(n):
    """CC bone name -> Mixamo bone name (without the mixamorig: prefix). CC keeps most weight on twist bones."""
    n = n.replace('CC_Base_', '')
    side = 'Left' if n.startswith('L_') else 'Right' if n.startswith('R_') else ''
    b = n[2:] if side else n
    if b in ('Pelvis', 'Hip'): return 'Hips'
    if b == 'Waist': return 'Spine'
    if b == 'Spine01': return 'Spine1'
    if b in ('Spine02', 'Breast', 'RibsTwist'): return 'Spine2'
    if b.startswith('NeckTwist'): return 'Neck'
    if b in ('Head', 'JawRoot', 'Eye') or b.startswith(('Teeth', 'Tongue')): return 'Head'
    if b == 'Clavicle': return side + 'Shoulder'
    if b.startswith('UpperarmTwist'): return side + 'Arm'
    if b.startswith('ForearmTwist') or b == 'ElbowShareBone': return side + 'ForeArm'
    m = re.match(r'Index(\d)$', b)
    if m: return side + 'HandIndex' + m.group(1)
    if b == 'Hand' or re.match(r'(Thumb|Mid|Ring|Pinky)\d$', b): return side + 'Hand'
    if b.startswith('ThighTwist'): return side + 'UpLeg'
    if b.startswith('CalfTwist') or b == 'KneeShareBone': return side + 'Leg'
    if b == 'Foot': return side + 'Foot'
    if b.endswith('Toe1'): return side + 'ToeBase'
    return None

bones = {b.name for b in arm.data.bones}
for o in src:
    me = o.data; n = len(me.vertices); W = {}
    gi = {g.index: g.name for g in o.vertex_groups}
    for v in me.vertices:
        for g in v.groups:
            t = mx(gi[g.group])
            if t is None: print('UNMAPPED', gi[g.group]); continue
            t = 'mixamorig:' + t
            if t not in bones and 'Index' in t: t = 'mixamorig:' + re.sub(r'Index\d', '', t.split(':')[1])  # rig without finger bones
            W.setdefault(t, np.zeros(n, np.float32))[v.index] += g.weight
    o.vertex_groups.clear()
    for t, w in W.items():
        g = o.vertex_groups.new(name=t)
        for i in np.nonzero(w > 1e-4)[0]: g.add([int(i)], float(w[i]), 'REPLACE')
    print('SRC', o.name, n, sorted(W))

names = [o.name for o in src]
bpy.ops.object.select_all(action='DESELECT')
for n in HAIR_PARTS: bpy.data.objects[n].select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects[HAIR_PARTS[-1]]; bpy.ops.object.join()
bpy.context.view_layer.objects.active.name = 'HairAll'
src = [bpy.data.objects[n] for n in names if n not in HAIR_PARTS] + [bpy.data.objects['HairAll']]

# Per-garment masks on the target from material names, then a data transfer from the matching source part
tm = [s.material.name if s.material else '' for s in tgt.material_slots]
base = lambda s: re.sub(r'\.\d+$', '', s)  # second imports get .001 suffixes; strip before comparing
for g in list(tgt.vertex_groups): tgt.vertex_groups.remove(g)
for b in sorted(bones): tgt.vertex_groups.new(name=b)
bpy.context.view_layer.objects.active = tgt
for o in src:
    mats = {base(s.material.name) for s in o.material_slots if s.material}
    slots = {i for i, n in enumerate(tm) if base(n) in mats}
    vs = set()
    for p in tgt.data.polygons:
        if p.material_index in slots: vs.update(p.vertices)
    if not vs: print('NO MATCH', o.name, mats); continue
    mk = tgt.vertex_groups.new(name='MASK_' + o.name); mk.add(list(vs), 1.0, 'REPLACE')
    md = tgt.modifiers.new('DT', 'DATA_TRANSFER'); md.object = o; md.use_object_transform = True
    md.use_vert_data = True; md.data_types_verts = {'VGROUP_WEIGHTS'}; md.vert_mapping = 'POLYINTERP_NEAREST'
    md.layers_vgroup_select_src = 'ALL'; md.layers_vgroup_select_dst = 'NAME'; md.mix_mode = 'REPLACE'; md.mix_factor = 1.0
    md.vertex_group = mk.name
    bpy.ops.object.modifier_move_to_index(modifier='DT', index=0)
    bpy.ops.object.modifier_apply(modifier='DT')
    g = tgt.vertex_groups.get('MASK_' + o.name)
    if g: tgt.vertex_groups.remove(g)
    print('DT', o.name, len(vs))
bpy.ops.object.select_all(action='DESELECT'); tgt.select_set(True)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
print('UNWEIGHTED', sum(1 for v in tgt.data.vertices if not v.groups), 'of', len(tgt.data.vertices))
