# Bake ARKit blend shapes from a MetaHuman face animation recorded in Unreal.
#   Blender -b --python scripts/blender/bake_arkit.py -- arkit_anim.fbx out.npz
# arkit_anim.fbx: Epic's AS_MetaHuman_ARKit_Mapping (one ARKit pose per frame) played through the face rig
# (RigLogic) in Sequencer and baked to an AnimSequence, exported with the face mesh. Each frame's evaluated
# mesh (joints + corrective shapes) minus frame 0 (neutral) becomes one shape, stored per vertex in the
# face mesh's own local space and vertex order, so mh_to_mixamo.py can add it to the same mesh.
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], a[1]
NAMES = ["Default", "EyeBlinkLeft", "EyeLookDownLeft", "EyeLookInLeft", "EyeLookOutLeft", "EyeLookUpLeft", "EyeSquintLeft", "EyeWideLeft",
         "EyeBlinkRight", "EyeLookDownRight", "EyeLookInRight", "EyeLookOutRight", "EyeLookUpRight", "EyeSquintRight", "EyeWideRight",
         "JawForward", "JawLeft", "JawRight", "JawOpen", "MouthFunnel", "MouthPucker", "MouthLeft", "MouthRight",
         "MouthSmileLeft", "MouthSmileRight", "MouthFrownLeft", "MouthFrownRight", "MouthDimpleLeft", "MouthDimpleRight",
         "MouthStretchLeft", "MouthStretchRight", "MouthRollLower", "MouthRollUpper", "MouthShrugLower", "MouthShrugUpper",
         "MouthPressLeft", "MouthPressRight", "MouthLowerDownLeft", "MouthLowerDownRight", "MouthUpperUpLeft", "MouthUpperUpRight",
         "BrowDownLeft", "BrowDownRight", "BrowInnerUp", "BrowOuterUpLeft", "BrowOuterUpRight", "CheekPuff", "CheekSquintLeft",
         "CheekSquintRight", "NoseSneerLeft", "NoseSneerRight", "TongueOut"]
if len(a) > 2: NAMES = a[2].split(",")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
me = next(o for o in bpy.data.objects if o.type == "MESH")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
sc = bpy.context.scene
act = arm.animation_data.action if arm.animation_data else None
f0, f1 = (int(act.frame_range[0]), int(act.frame_range[1])) if act else (sc.frame_start, sc.frame_end)
print("[arkit] verts", len(me.data.vertices), "frames", f0, f1, "fps", sc.render.fps, "shape keys", len(me.data.shape_keys.key_blocks) if me.data.shape_keys else 0,
      "shape anim", bool(me.data.shape_keys and me.data.shape_keys.animation_data and me.data.shape_keys.animation_data.action))
dg = bpy.context.evaluated_depsgraph_get()
def coords(frame):
    sc.frame_set(frame); dg.update()
    ev = me.evaluated_get(dg); m = ev.to_mesh()
    c = np.empty(len(m.vertices) * 3, np.float32); m.vertices.foreach_get("co", c); ev.to_mesh_clear()
    return c.reshape(-1, 3)
base = coords(f0)
D = {}
for i, n in enumerate(NAMES):
    if i == 0 or f0 + i > f1: continue
    d = coords(f0 + i) - base
    mx = float(np.abs(d).max())
    D[n] = d.astype(np.float32)
    print(f"[arkit] {n:22s} max {mx:.3f}  moved {(np.linalg.norm(d, axis=1) > 0.01).sum()}")
np.savez_compressed(out, base=base, **D)
print("[arkit] wrote", out, len(D))
