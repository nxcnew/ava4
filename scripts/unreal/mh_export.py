# Build a rigged, textured MetaHuman character and export everything the Blender step needs.
# Run inside the Unreal editor (through the bridge) after setting CHAR and NAME, e.g. prepend:
#   CHAR = "/Game/EditableCharacters/Elise/MHC_Elise"; NAME = "Elise"
# Output: ~/Docs/me/Projects/blu.dj/ava4-unreal/export/<NAME>/
#   face.fbx body.fbx [outfit.fbx]  hair/cards_g<group>_lod<n>.fbx hair/brows_lod<n>.fbx hair/*_Attribute.png
#   dcc/<asset>/Maps/*.png  hair/groom.json (the character's own hair colour settings)  arkit_anim.fbx
# Needs: the character rigged with JOINTS_AND_BLEND_SHAPES and its high-res textures downloaded.
# Never leave transient MetaHuman preview actors in the level while building: the build can crash on them.
import os, json
OUT = os.path.expanduser(f"~/Docs/me/Projects/blu.dj/ava4-unreal/export/{NAME}")
BUILT = f"/Game/Hero/Built/{NAME}"
os.makedirs(OUT + "/hair", exist_ok=True)
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
reg = unreal.AssetRegistryHelpers.get_asset_registry()
ch = unreal.load_asset(CHAR)
sub.try_add_object_to_edit(ch)
assert sub.can_build_meta_human(ch, True), "not buildable (rig or textures missing?)"

def ex(obj, fn, opts=None, exporter=None):
    t = unreal.AssetExportTask(); t.object = obj; t.filename = os.path.join(OUT, fn)
    t.automated = True; t.prompt = False; t.replace_identical = True
    if opts: t.options = opts
    if exporter: t.exporter = exporter
    ok = unreal.Exporter.run_asset_export_task(t); print("export", fn, ok); return ok
def fbxo():
    o = unreal.FbxExportOption(); o.export_morph_targets = True; o.level_of_detail = False; o.collision = False; o.vertex_color = True; return o

# ---- build into a folder named after the character
bp = unreal.MetaHumanCharacterEditorBuildParameters(); bp.absolute_build_path = "/Game/Hero/Built"; bp.name_override = NAME
sub.build_meta_human(ch, bp)
assets = {str(a.package_name): str(a.asset_class_path.asset_name) for a in reg.get_assets_by_path(BUILT, recursive=True)}
find = lambda cls, key="": sorted(p for p, c in assets.items() if c == cls and key in p)
face = find("SkeletalMesh", "/Face/")[0]; body = find("SkeletalMesh", "/Body/")[0]
ex(unreal.load_asset(face), "face.fbx", fbxo()); ex(unreal.load_asset(body), "body.fbx", fbxo())
for o in find("SkeletalMesh", "/Clothing/"): ex(unreal.load_asset(o), "outfit.fbx", fbxo())

# ---- grooms: cards meshes, card atlases and the character's own hair colour parameters
groom_info = {}
for g in find("GroomAsset"):
    gname = g.split("/")[-1]; kind = "hair" if gname.startswith("Hair") else "brows" if gname.startswith("Eyebrows") else None
    if not kind: continue
    ga = unreal.load_asset(g)
    src = ga.get_path_name()
    for card in ga.get_editor_property("hair_groups_cards"):
        gi, li = card.get_editor_property("group_index"), card.get_editor_property("lod_index")
        mesh = card.get_editor_property("imported_mesh")
        if mesh and li <= 1:
            ex(mesh, f"hair/{'cards_g%d' % gi if kind == 'hair' else 'brows'}_lod{li}.fbx", fbxo())
    # card atlas: the "Attribute" texture next to the cards mesh in the source groom folder
    for p in find("Texture2D", gname) + [str(a.package_name) for a in reg.get_assets_by_path("/".join(unreal.load_asset(g).get_editor_property("hair_groups_cards")[0].get_editor_property("imported_mesh").get_path_name().split("/")[:-1]), recursive=False) if "Attribute" in str(a.asset_name)]:
        if "Attribute" in p:
            ex(unreal.load_asset(p), f"hair/{'Hair' if kind == 'hair' else 'Brows'}_Attribute.png", exporter=unreal.TextureExporterPNG()); break
# hair colour: scalar/vector parameters on the built hair material instances
for m in find("MaterialInstanceConstant"):
    if "/Grooms/" not in m and "Hair" not in m: continue
    mi = unreal.load_asset(m); params = {}
    for pv in mi.get_editor_property("scalar_parameter_values"): params[str(pv.parameter_info.name)] = pv.parameter_value
    for pv in mi.get_editor_property("vector_parameter_values"):
        c = pv.parameter_value; params[str(pv.parameter_info.name)] = [c.r, c.g, c.b, c.a]
    groom_info[m.split("/")[-1]] = params
json.dump(groom_info, open(os.path.join(OUT, "hair", "groom.json"), "w"), indent=1)
print("groom materials:", list(groom_info))

# ---- DCC maps (face/body/teeth/eye textures with make-up baked in)
p = unreal.MetaHumanDCCExportParams(); p.external_path = OUT + "/dcc"; p.bake_make_up = True; p.compress_in_zip_file = False
unreal.MetaHumanCharacterExportBlueprintLibrary.export_dcc(ch, p)

# ---- ARKit bake: Epic's ARKit mapping played through this face's rig, baked by Sequencer
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
fm = unreal.load_asset(face); anim = unreal.load_asset("/MetaHumanCharacter/Face/ARKit/AS_MetaHuman_ARKit_Mapping")
act = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 3000, 0)); act.skeletal_mesh_component.set_skinned_asset_and_update(fm)
at = unreal.AssetToolsHelpers.get_asset_tools()
for pth in (f"{BUILT}/Bake/LS_ARKit", f"{BUILT}/Bake/AS_ARKit_Baked"):
    if unreal.EditorAssetLibrary.does_asset_exist(pth): unreal.EditorAssetLibrary.delete_asset(pth)
seq = at.create_asset("LS_ARKit", f"{BUILT}/Bake", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(30, 1)); seq.set_tick_resolution(unreal.FrameRate(30000, 1))
binding = seq.add_possessable(act)
sec = binding.add_track(unreal.MovieSceneSkeletalAnimationTrack).add_section(); sec.set_range(0, 65)
prm = sec.get_editor_property("params"); prm.set_editor_property("animation", anim)
pr = unreal.MovieSceneTimeWarpVariant(); pr.set_fixed_play_rate(1.25); prm.set_editor_property("play_rate", pr)  # 24 fps poses on 30 fps frames
sec.set_editor_property("params", prm); seq.set_playback_start(0); seq.set_playback_end(65)
f = unreal.AnimSequenceFactory(); f.set_editor_property("target_skeleton", fm.skeleton)
baked = at.create_asset("AS_ARKit_Baked", f"{BUILT}/Bake", unreal.AnimSequence, f)
opt = unreal.AnimSeqExportOption(); opt.set_editor_property("export_morph_targets", True)
print("arkit bake:", unreal.SequencerTools.export_anim_sequence(world, seq, baked, opt, binding, False))
eas.destroy_actor(act)
baked.set_preview_skeletal_mesh(fm)
o = unreal.FbxExportOption(); o.export_morph_targets = True; o.export_preview_mesh = True; o.level_of_detail = False; o.collision = False
ex(baked, "arkit_anim.fbx", o)
print("done", OUT)
