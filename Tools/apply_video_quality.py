"""Matte_2P_v2: show the Spout video at original quality, keeping BP_SpoutTarget and the glitch effect.

1. Cam_Front post process: no exposure bias, no vignette/bloom/grain/motion blur, local exposure
   contrast 1.0, blue correction 0 (tone curve 0 and expand gamut 0 as before).
2. M_RVM_Composite: exact sRGB decode instead of pow(x, 2.2), and sample the videos at exact screen
   pixels (ScreenPosition.ViewportUV) instead of the plane's TexCoord. The plane fills the frame, so
   the glitch bands and shifts stay where they were.
Project settings (DefaultEngine.ini) add r.AntiAliasingMethod=0 and r.ScreenPercentage=100.

Run headless with the editor closed:
  UnrealEditor-Cmd.exe Matte_2P_v2.uproject -run=pythonscript -script="<this file>"
Safe to run again (skips what is already applied). Backup of the originals: Saved/QualityBackup_20261023.
"""
import re
import unreal

mel = unreal.MaterialEditingLibrary

# ---------- camera ----------
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/Maps/Main")
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() != "Cam_Front":
        continue
    cc = a.get_component_by_class(unreal.CameraComponent)
    pp = cc.get_editor_property("post_process_settings")
    for prop, val in [("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL), ("auto_exposure_bias", 0.0),
                      ("auto_exposure_apply_physical_camera_exposure", False), ("tone_curve_amount", 0.0),
                      ("expand_gamut", 0.0), ("blue_correction", 0.0), ("vignette_intensity", 0.0),
                      ("bloom_intensity", 0.0), ("film_grain_intensity", 0.0), ("motion_blur_amount", 0.0),
                      ("scene_fringe_intensity", 0.0), ("lens_flare_intensity", 0.0),
                      ("local_exposure_highlight_contrast_scale", 1.0), ("local_exposure_shadow_contrast_scale", 1.0),
                      ("local_exposure_detail_strength", 1.0)]:
        pp.set_editor_property("override_" + prop, True)
        pp.set_editor_property(prop, val)
    cc.set_editor_property("post_process_settings", pp)
    unreal.log_warning("QUALITY camera post process set")
les.save_current_level()

# ---------- composite material ----------
m = unreal.load_asset("/Game/M_RVM_Composite")
cn = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
code = cn.get_editor_property("code")


def srgb(mt):
    x = f"max({mt.group(1)}, 0.0)"
    return f"lerp(pow(({x} + 0.055) / 1.055, 2.4), {x} / 12.92, step({x}, 0.04045))"


new = re.sub(r"pow\(max\(([^;]*?\.rgb), 0\.0\), 2\.2\)", srgb, code)
cn.set_editor_property("code", new)
unreal.log_warning(f"QUALITY sRGB decode: replaced {code.count('2.2)') - new.count('2.2)')} pow 2.2")

names = [str(i.get_editor_property("input_name")) for i in cn.get_editor_property("inputs")]
uv_src = mel.get_inputs_for_material_expression(m, cn)[names.index("UV")]
if not isinstance(uv_src, unreal.MaterialExpressionScreenPosition):
    scr = mel.create_material_expression(m, unreal.MaterialExpressionScreenPosition, -900, 200)
    mel.connect_material_expressions(scr, "ViewportUV", cn, "UV")
    unreal.log_warning("QUALITY UV -> ScreenPosition.ViewportUV")
mel.recompile_material(m)
unreal.EditorAssetLibrary.save_loaded_asset(m)
unreal.log_warning("QUALITY done")
