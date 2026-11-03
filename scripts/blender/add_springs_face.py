"""Step 5: run cc_weights.py, then add spring-bone chains (hair, jacket) and face shapes, split the face into its own
triangulated mesh, and export the finished character.

    blender -b -P scripts/blender/add_springs_face.py -- <mixamo .fbx> <original CC .fbx> <out .fbx>

Follows the naming contract index.html expects (docs/CHARACTER_PIPELINE.md): bones spring_<chain>_<n> + spring_<chain>_end,
face shapes with CC or ARKit names on a separate, all-triangle mesh. Thresholds below are Amber's (metres, Blender axes:
front is -Y, up is +Z); re-measure them for any other character.
Origin: amber-pipeline/amber_v4.py (produced avatars/Amber.fbx: 22 spring bones, 18 face shapes, 32 MB).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_FBX = sys.argv[sys.argv.index('--') + 3]
exec(open(os.path.join(HERE, 'cc_weights.py')).read())  # leaves arm, tgt, src, bones, base, re, np, Vector
import bmesh
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

# ---- CONFIG (per character) ----
HAIR_MATS = r'Hair|Scalp'
FACE_SRC_BODY, FACE_SRC_BROW = 'CC_Base_Body', 'Camila_Brow'
FACE_MATS = ('Std_Skin_Head', 'Std_Eyelash', 'Female_Brow_Transparency', 'Female_Brow_Base_Transparency')
FACE_ZMIN = 1.40   # only vertices above this height get face shapes
KEYS = ['Eye_Blink_L', 'Eye_Blink_R', 'Eye_Squint_L', 'Eye_Squint_R', 'Eye_Wide_L', 'Eye_Wide_R', 'Mouth_Smile_L', 'Mouth_Smile_R',
        'Cheek_Raise_L', 'Cheek_Raise_R', 'Brow_Raise_Inner_L', 'Brow_Raise_Inner_R', 'Brow_Raise_Outer_L', 'Brow_Raise_Outer_R',
        'Brow_Drop_L', 'Brow_Drop_R', 'Mouth_Press_L', 'Mouth_Press_R']
def hair_chain(c, zmin):
    """Which chain a hair island belongs to, from its centroid c and lowest point; None keeps it rigid on Head."""
    side = 'L' if c[0] > 0 else 'R'
    if zmin < 1.50 and c[1] > 0.04: return 'hairBack' + side
    if c[1] < -0.03 and zmin < 1.60: return 'hairBang' + side
    if abs(c[0]) > 0.06 and zmin < 1.52: return 'hairSide' + side
    return None
def jacket_regions(J, JP):
    fr = (JP[:, 1] < -0.03) & (np.abs(JP[:, 0]) < 0.19) & (JP[:, 2] < 1.30)
    return {'jacketFrontL': J[fr & (JP[:, 0] > 0)], 'jacketFrontR': J[fr & (JP[:, 0] < 0)],
            'jacketBack': J[(JP[:, 1] > 0.04) & (np.abs(JP[:, 0]) < 0.19) & (JP[:, 2] < 1.16)]}
JACKET_ROOT_Z = {'front': 1.28, 'back': 1.16}
SIDE_SEAM = (0.13, 0.185)  # jacket weights fade out towards the side seams, so panels never tear away
# --------------------------------

me = tgt.data; NV = len(me.vertices)
CO = np.array([(tgt.matrix_world @ v.co)[:] for v in me.vertices])
tm = [s.material.name if s.material else '' for s in tgt.material_slots]
def vmask(pred):
    m = np.zeros(NV, bool)
    for p in me.polygons:
        if pred(tm[p.material_index]): m[list(p.vertices)] = True
    return m
hairV = vmask(lambda n: re.search(HAIR_MATS, n) is not None)
jackV = vmask(lambda n: 'jacket' in n.lower())

# Hair cards are separate islands: union-find them, so a strand is never split between moving and not moving
par = np.arange(NV)
def find(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
for p in me.polygons:
    if not hairV[p.vertices[0]]: continue
    vs = list(p.vertices); r0 = find(vs[0])
    for v in vs[1:]:
        r = find(v)
        if r != r0: par[r] = r0
roots = np.array([find(i) if hairV[i] else -1 for i in range(NV)])
clusters = {}
for r in np.unique(roots[roots >= 0]):
    idx = np.nonzero(roots == r)[0]; P = CO[idx]
    k = hair_chain(P.mean(0), P[:, 2].min())
    if k: clusters.setdefault(k, []).append(idx)
clusters = {k: np.concatenate(v) for k, v in clusters.items()}
J = np.nonzero(jackV)[0]; jc = jacket_regions(J, CO[J])
for k, v in {**clusters, **jc}.items(): print('CLUSTER', k, len(v), CO[v].min(0).round(3), CO[v].max(0).round(3))

def smooth(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
# chains: (name, verts, parent bone, nbones, root, tip, spring share(t, P))
chains = []
for k, v in clusters.items():
    P = CO[v]; z = P[:, 2]; top = P[z >= np.percentile(z, 92)].mean(0); bot = P[z <= np.percentile(z, 6)].mean(0)
    n = 2 if 'Bang' in k else 3
    lo, hi = (0.2, 0.6) if 'Bang' in k else (0.45, 0.8) if 'Back' in k else (0.3, 0.7)  # back hair hugs the skull longer
    chains.append((k, v, 'mixamorig:Head', n, top, bot, lambda t, P, lo=lo, hi=hi: smooth(lo, hi, t)))
for k, v in jc.items():
    P = CO[v]
    if k == 'jacketBack': root = np.array([0, P[:, 1].mean(), JACKET_ROOT_Z['back']]); parent = 'mixamorig:Spine1'
    else: root = np.array([np.median(P[:, 0]), np.percentile(P[:, 1], 20), JACKET_ROOT_Z['front']]); parent = 'mixamorig:Spine2'
    tip = np.array([root[0], root[1], P[:, 2].min()])
    lo, hi = (0.25, 0.95) if k == 'jacketBack' else (0.40, 0.95)
    chains.append((k, v, parent, 2, root, tip, lambda t, P, lo=lo, hi=hi: smooth(lo, hi, t) * (1 - smooth(*SIDE_SEAM, np.abs(P[:, 0])))))

# Bones, split evenly root -> tip, plus an unweighted _end bone marking the last tip
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones; inv = arm.matrix_world.inverted()
chain_bones = {}
for (k, v, parent, n, root, tip, _) in chains:
    pts = [Vector(root + (tip - root) * i / n) for i in range(n + 1)]
    prev = eb[parent]; names = []
    for i in range(n + 1):
        nm = f'spring_{k}_{i + 1}' if i < n else f'spring_{k}_end'
        b = eb.new(nm); a = inv @ pts[i]; d = (inv @ pts[min(i + 1, n)]) - a if i < n else (inv @ pts[n]) - (inv @ pts[n - 1])
        b.head = a; b.tail = a + d * (1 if i < n else 0.3); b.parent = prev; b.use_connect = False
        prev = b; names.append(nm)
    chain_bones[k] = names
bpy.ops.object.mode_set(mode='OBJECT')

# Weights: body weights scaled by (1 - s), chain bones get s spread linearly between neighbouring bones
for (k, v, parent, n, root, tip, share) in chains:
    P = CO[v]; d = tip - root; L = np.linalg.norm(d); t = np.clip(((P - root) @ d) / (L * L), 0, 1)
    s = share(t, P)
    names = chain_bones[k][:n]
    for nm in names:
        if tgt.vertex_groups.get(nm) is None: tgt.vertex_groups.new(name=nm)
    gs = [tgt.vertex_groups[nm] for nm in names]
    for j, vi in enumerate(v):
        if s[j] < 1e-3: continue
        u = t[j] * n - 0.5
        ws = np.array([max(0, 1 - abs(u - i)) for i in range(n)])
        if ws.sum() < 1e-6: ws[int(np.clip(round(u), 0, n - 1))] = 1
        ws /= ws.sum()
        for g in tgt.vertex_groups:
            if g.name in names: continue
            try: w = g.weight(int(vi))
            except RuntimeError: continue
            g.add([int(vi)], w * (1 - s[j]), 'REPLACE')
        for i, g in enumerate(gs):
            if ws[i] > 1e-4: g.add([int(vi)], float(s[j] * ws[i]), 'REPLACE')
    print('WEIGHTED', k, int((s > 0.01).sum()))

# Face shapes from the original high-res meshes: closest point on the SAME material's surface, barycentric deltas
if not me.shape_keys: tgt.shape_key_add(name='Basis', from_mix=False)
orig = np.empty(NV * 3, np.float32); me.vertices.foreach_get('co', orig); orig = orig.reshape(-1, 3)
Tinv = np.array(tgt.matrix_world.inverted().to_3x3())
deltas = {k: np.zeros((NV, 3), np.float32) for k in KEYS}
def transfer(srcobj, tmat_pred, smat_pred, zmin):
    sm = srcobj.data; M = srcobj.matrix_world; R = np.array(M.to_3x3())
    sv = np.array([(M @ v.co)[:] for v in sm.vertices])
    sk = sm.shape_keys.key_blocks; basis = np.empty(len(sv) * 3, np.float32); sk[0].data.foreach_get('co', basis); basis = basis.reshape(-1, 3)
    sd = {}
    for k in KEYS:
        if k in sk:
            a = np.empty(len(sv) * 3, np.float32); sk[k].data.foreach_get('co', a)
            sd[k] = (a.reshape(-1, 3) - basis) @ R.T @ Tinv.T  # source local delta -> world -> target local
    smats = [base(s.material.name) if s.material else '' for s in srcobj.material_slots]
    tris = []
    for p in sm.polygons:
        if not smat_pred(smats[p.material_index]): continue
        v = list(p.vertices)
        for i in range(1, len(v) - 1): tris.append((v[0], v[i], v[i + 1]))
    tris = np.array(tris)
    bvh = BVHTree.FromPolygons([tuple(map(float, x)) for x in sv], [tuple(map(int, t)) for t in tris])
    tv = np.nonzero(vmask(tmat_pred) & (CO[:, 2] > zmin))[0]; n = far = 0
    for vi in tv:
        loc, nor, ti, dist = bvh.find_nearest(Vector(CO[vi]))
        if ti is None: continue
        if dist > 0.004: far += 1; continue
        a, b_, c = tris[ti]
        w = barycentric_transform(loc, Vector(sv[a]), Vector(sv[b_]), Vector(sv[c]), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
        for k, d in sd.items(): deltas[k][vi] = w.x * d[a] + w.y * d[b_] + w.z * d[c]
        n += 1
    print('TRANSFER', srcobj.name, n, 'far', far)
body = bpy.data.objects[FACE_SRC_BODY]; brow = bpy.data.objects[FACE_SRC_BROW]
transfer(body, lambda n: n == 'Std_Skin_Head', lambda n: n == 'Std_Skin_Head', FACE_ZMIN)
transfer(body, lambda n: n == 'Std_Eyelash', lambda n: n == 'Std_Eyelash', FACE_ZMIN)
transfer(brow, lambda n: 'Brow' in n, lambda n: True, FACE_ZMIN)
for k in KEYS:
    d = deltas[k]; sk = tgt.shape_key_add(name=k, from_mix=False); sk.data.foreach_set('co', (orig + d).ravel())
    print('KEY', k, round(float(np.abs(d).max()) * 1000, 2), 'mm', int((np.abs(d).max(1) > 1e-6).sum()))
bpy.ops.object.select_all(action='DESELECT'); tgt.select_set(True); bpy.context.view_layer.objects.active = tgt
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
for o in src: bpy.data.objects.remove(o, do_unlink=True)

# Split the face into its own mesh (only it carries shapes: three.js morph memory scales with the whole mesh).
# Freeze today's smooth normals first so the neck cut doesn't show.
try: me.normals_split_custom_set([tuple(n.vector) for n in me.corner_normals])
except Exception as e: print('NORMALS', e)
facemats = {i for i, n in enumerate(tm) if base(n) in FACE_MATS}
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
for p in me.polygons: p.select = p.material_index in facemats
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.separate(type='SELECTED'); bpy.ops.object.mode_set(mode='OBJECT')
face = next(o for o in bpy.context.selected_objects if o != tgt); face.name = 'Face'
# three.js r160 FBXLoader re-splits quads using the *shape* data for morph targets, which shatters them: triangles only
bpy.ops.object.select_all(action='DESELECT'); face.select_set(True); bpy.context.view_layer.objects.active = face
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY'); bpy.ops.object.mode_set(mode='OBJECT')
print('FACE TRIS', all(len(p.vertices) == 3 for p in face.data.polygons))
bpy.context.view_layer.objects.active = tgt; bpy.ops.object.select_all(action='DESELECT'); tgt.select_set(True)
bpy.ops.object.shape_key_remove(all=True)
for o in (tgt, face):
    print('PART', o.name, len(o.data.vertices), len(o.data.polygons), 'keys', len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0)
bpy.ops.object.select_all(action='DESELECT'); tgt.select_set(True); face.select_set(True); arm.select_set(True)
bpy.ops.export_scene.fbx(filepath=OUT_FBX, use_selection=True, path_mode='COPY', embed_textures=True, add_leaf_bones=False,
                         bake_anim=False, axis_forward='-Z', axis_up='Y')
print('FBX MB', round(os.path.getsize(OUT_FBX) / 1e6, 1))
