"""Step 2: give every packed image a .png/.jpg name, then export the FBX to upload to Mixamo.

    blender -b -P scripts/blender/fix_texture_names.py -- <work dir>      (reads <work>/prepped.blend)

three.js's FBXLoader picks the image decoder from the file extension; an image with no extension never loads
(Amber's hair was invisible until this ran). Writes <work>/for_mixamo.fbx.
Origin: amber-pipeline/amber_fixnames.py.
"""
import bpy, os, sys

OUT = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'prepped.blend'))
for im in bpy.data.images:
    if im.packed_file is None: continue
    ext = '.png' if im.file_format == 'PNG' else '.jpg'
    stem = os.path.splitext(os.path.basename(im.name))[0]
    im.name = stem + ext
    im.filepath_raw = '//' + stem + ext
    print(im.name, im.file_format)
body = bpy.data.objects['Character']
for o in bpy.data.objects: o.select_set(o is body)
bpy.context.view_layer.objects.active = body
p = os.path.join(OUT, 'for_mixamo.fbx')
bpy.ops.export_scene.fbx(filepath=p, use_selection=True, path_mode='COPY', embed_textures=True,
    add_leaf_bones=False, bake_anim=False, axis_forward='-Z', axis_up='Y', apply_scale_options='FBX_SCALE_ALL')
print('FBX MB', round(os.path.getsize(p) / 1e6, 1), '- next: upload to Mixamo, auto-rig, download T-pose With Skin')
