"""Step 1: turn a Character Creator export into a light, unrigged mesh ready for Mixamo's auto-rigger.

    blender -b -P scripts/blender/cc_prep.py -- <original CC .fbx> <work dir>

Drops hidden helper meshes, removes rig/shape keys/weights, decimates, merges opacity maps into colour (RGBA PNG),
kills specular, caps textures at 1024px (head 2048), joins everything into one mesh, and writes
<work>/prepped.blend + <work>/for_mixamo.fbx. Then run fix_texture_names.py before uploading.

The CONFIG block is Amber's (CGTrader CC4 model); adjust object names and ratios per character.
Origin: amber-pipeline/amber_prep.py (2026-11, written by the earlier assistant); see docs/CHARACTER_PIPELINE.md.
"""
import bpy, os, sys
import numpy as np

SRC, OUT = sys.argv[sys.argv.index('--') + 1:][:2]
os.makedirs(OUT, exist_ok=True)

# ---- CONFIG (per character) ----
DROP = {'Underwear_Bottoms', 'CC_Base_EyeOcclusion', 'CC_Base_TearLine'}
RATIOS = {'CC_Base_Body': 0.12, 'CC_Base_Teeth': 0.08, 'CC_Base_Tongue': 0.25, 'CC_Base_Eye': 0.5, 'Jeans': 0.12,
          'Crop_T_Shirt': 0.18, 'Punk_Leather_Jacket': 0.25, 'Boots': 0.2, 'Bra': 0.4}
DEFAULT_RATIO = 0.3
UNSUBDIV = {'Bang': 2, 'Bun': 2, 'Real_Hair': 2, 'Hair_Base': 2, 'Camila_Brow': 1}  # hair cards: un-subdivide, keeps card shapes
TEX_MAX, KEEP_FULL = 1024, ('Std_Skin_Head',)  # face texture stays sharp
BODY = 'CC_Base_Body'
# --------------------------------

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.name in DROP: bpy.data.objects.remove(o, do_unlink=True)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    # bake the bind shape, drop skeleton links and facial shape keys
    for m in list(o.modifiers):
        if m.type == 'ARMATURE': o.modifiers.remove(m)
    if o.data.shape_keys: o.shape_key_clear()
    o.vertex_groups.clear()
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw  # keep world placement when unparenting
for o in list(bpy.data.objects):
    if o.type == 'ARMATURE': bpy.data.objects.remove(o, do_unlink=True)

def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)
before = sum(tris(o) for o in meshes)
for o in meshes:
    bpy.context.view_layer.objects.active = o
    md = o.modifiers.new('dec', 'DECIMATE')
    if o.name in UNSUBDIV: md.decimate_type = 'UNSUBDIV'; md.iterations = UNSUBDIV[o.name]
    else: md.ratio = RATIOS.get(o.name, DEFAULT_RATIO)
    bpy.ops.object.modifier_apply(modifier=md.name)
for o in meshes: print(f'{o.name:24} {tris(o):7d}')
print('TRIS before', before, 'after', sum(tris(o) for o in meshes))

# Merge each see-through mask into its colour texture (RGBA), so hair/brows/lashes keep their soft edges
def px(im): a = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32); im.pixels.foreach_get(a); return a.reshape(im.size[1], im.size[0], 4)
merged = 0
for m in bpy.data.materials:
    if not m.use_nodes: continue
    nt = m.node_tree; bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf: continue
    base = next((l.from_node for l in nt.links if l.to_node == bsdf and l.to_socket.name == 'Base Color' and l.from_node.type == 'TEX_IMAGE'), None)
    alpha = next((l for l in nt.links if l.to_node == bsdf and l.to_socket.name == 'Alpha' and l.from_node.type == 'TEX_IMAGE'), None)
    # drop specular maps (skin and leather look like chrome) and set a soft, satin response
    for l in [l for l in nt.links if l.to_node == bsdf and l.to_socket.name.startswith('Specular')]: nt.links.remove(l)
    bsdf.inputs['Specular IOR Level'].default_value = 0.25
    bsdf.inputs['Roughness'].default_value = 0.62 if 'Skin' in m.name else 0.5
    if base and alpha and base.image:
        op = alpha.from_node.image
        if op is None: continue
        w, h = base.image.size
        if tuple(op.size) != (w, h): op.scale(w, h)
        c = px(base.image).copy(); o = px(op)
        c[..., 3] = o[..., 0] if alpha.from_socket.name == 'Color' else o[..., 3]
        rgba = bpy.data.images.new(base.image.name + '_RGBA', w, h, alpha=True)
        rgba.pixels.foreach_set(c.ravel()); rgba.file_format = 'PNG'; rgba.alpha_mode = 'STRAIGHT'; rgba.pack()
        base.image = rgba
        nt.links.remove(alpha); nt.links.new(base.outputs['Alpha'], bsdf.inputs['Alpha'])
        merged += 1
print('MERGED alpha into colour for', merged, 'materials')

for im in bpy.data.images:
    if not im.name.startswith(KEEP_FULL) and (im.size[0] > TEX_MAX or im.size[1] > TEX_MAX):
        im.scale(min(TEX_MAX, im.size[0]), min(TEX_MAX, im.size[1]))
    if not im.name.endswith('_RGBA') and 'Opacity' not in im.name: im.file_format = 'JPEG'
    im.pack()

bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = next(o for o in meshes if o.name == BODY)
bpy.ops.object.join()
body = bpy.context.view_layer.objects.active; body.name = 'Character'
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
print('DIMS', tuple(round(v, 3) for v in body.dimensions))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'prepped.blend'))
print('saved', os.path.join(OUT, 'prepped.blend'), '- next: fix_texture_names.py')
