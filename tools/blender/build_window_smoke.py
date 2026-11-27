# Анимация «Юрчик курит в окно» (MenuSmoke) для кадра главного меню (YUR-19, scenes/ui/menu_yard.tscn).
#
# Окно его комнаты на 9-м этаже (tools/blender/build_menu_yard.py): правая половина распахнута, подоконник
# внутри на 0.85 м, рама в проёме, снаружи — отлив с валиком снега. Юрчик лёг животом на подоконник и
# высунулся по плечи: локти — на снегу на отливе, предплечья вперёд, кисти над краем. Курит медленно, петлёй:
#   rest   правая с сигаретой лежит на снегу, сигарета торчит вверх, тлеет; взгляд — вниз во двор;
#   raise  предплечье поднимается от локтя, кисть ладонью к лицу, фильтр — в губы;
#   drag   затяжка (огонёк ярче, json "drag");
#   lower  рука опускается на снег, голова чуть вверх — задержал дым;
#   exhale медленный выдох вверх-вперёд (json "exhale": дым изо рта);
#   flick  стряхивает пепел — два коротких кивка кистью; дальше тишина до начала петли.
# Клип зациклен: первый и последний кадр совпадают, дыхание и покачивание — с целым числом периодов.
#
# Всё считается в пространстве узла Юрчика в сцене меню: ноги в NODE, лицом в +X мира. В Blender это
# пространство арматуры: вперёд −Y, вправо −X, вверх Z. Мир Godot → здесь: X = −(z − z0), Y = −(x − x0), Z = y − y0.
# Позы — аналитический IK без констрейнтов (seat_poses.py).
#
# Сигарета и рот: в json — их точки в пространстве скелета Godot на кадре REF (x = X, y = Z, z = −Y) и сам
# кадр; menu_yard.gd ставит сигарету на BoneAttachment3D кисти и дым на кость головы, пересчитав смещение
# от позы кости на этом кадре (так не надо сводить оси костей Blender и Godot).
#
# Запуск — только в живом Blender через Blender MCP (правило проекта):
#   exec(open(r"<проект>/tools/blender/build_window_smoke.py", encoding="utf-8").read(), {"__name__": "__main__"})
# Пишет assets/animations/menu/yurchik_smoke.glb (клип MenuSmoke) и assets/animations/menu/smoke.json.
# PREVIEW = True в globals — без экспорта: ставит декорацию меню вокруг и рендерит кадры в PREVIEW_DIR.
import bpy, os, sys, math, json, importlib
from mathutils import Matrix, Vector

ROOT = r"C:\Users\mrs\Documents\yuranchik_game"
SRC = os.path.join(ROOT, "assets", "animations", "gmod", "yurchik_gmod.glb")
SET = os.path.join(ROOT, "assets", "models", "menu", "menu_yard.gltf")
OUT_DIR = os.path.join(ROOT, "assets", "animations", "menu")
OUT = os.path.join(OUT_DIR, "yurchik_smoke.glb")
OUT_JSON = os.path.join(OUT_DIR, "smoke.json")
SCENE = "MenuSmoke"
CLIP = "MenuSmoke"
FPS = 30

NODE = (-0.62, 23.0, 0.42)          # Godot: где стоит узел Юрчика — в открытой половине, ближе к камере
CAM = ((1.2, 24.6, 2.0), (-0.2, 22.8, -18.0))   # камера меню (menu_yard.gd) — для превью

# --- кадры (петля 12 с) ---
F_RAISE0, F_MOUTH = 54, 96          # рука пошла к губам … фильтр в губах
F_DRAG1 = 138                       # конец затяжки
F_DOWN = 180                        # рука снова на снегу
F_EXH0, F_EXH1 = 196, 262           # выдох
F_FLICK0, F_FLICK1 = 292, 312       # стряхивает пепел
LEN = 360
REF = 0                             # кадр, на котором в json точки сигареты и рта

# --- тело ---
PELVIS_BACK = 0.03                  # м — таз назад (к комнате), чтобы бёдра не входили в подоконник
PELVIS_DOWN = 0.03                  # м — колени чуть согнуты
PELVIS_PITCH = 25.0                 # ° — наклон таза вперёд (из бёдер)
SPINE_PITCH = 33.0                  # ° — наклон корпуса сверх таза
LOOK_REST = Vector((-5.5, -10.0, -2.2))     # куда смотрит: вперёд из окна, вниз во двор, чуть вправо (к камере)
LOOK_EXHALE = Vector((-4.5, -10.0, 1.4))    # на выдохе — подбородок вверх
SPINE_SIDE = 7.0                    # ° — корпус чуть вправо, к открытому краю и камере
BREATH = 120                        # кадров на вдох-выдох (3 за петлю)

# --- руки (точки — в пространстве узла, м) ---
# локти на валике снега (отлив — 0.62…0.89 м от ног, верх снега ~0.95), кисти над краем отлива
# локоть лежит на нижнем брусе рамы (верх 0.92 м, 0.47…0.54 м от ног), предплечье — вперёд по снегу на отливе
ELBOW_L = Vector((0.19, -0.52, 0.955))
FORE_L = Vector((-0.35, -1.0, 0.04))        # куда идёт предплечье от локтя
KN_L = Vector((-0.25, -1.0, -0.55))         # кисть свисает с края, пальцы вниз-вперёд
BACK_L = Vector((0.25, -0.3, 1.0))
ELBOW_R = Vector((-0.17, -0.52, 0.955))
FORE_R = Vector((0.30, -1.0, 0.16))         # правое чуть приподнято — кисть с сигаретой над снегом
KN_R = Vector((0.25, -1.0, -0.2))           # кисть с сигаретой: пальцы вперёд, тыл вверх — сигарета торчит вверх
BACK_R = Vector((-0.25, 0.1, 1.0))
POLE_R_MOUTH = Vector((-0.35, -0.25, -0.75))

# сигарета между указательным и средним (у средних фаланг), фильтр — к ладони
CIG_LEN = 0.085
CIG_FILTER = 0.024                  # м — сколько торчит со стороны ладони
FINGERS_SMOKE = {"Index": [14, 18, 10], "Middle": [16, 18, 10], "Ring": [52, 64, 36], "Pinky": [58, 66, 36]}
THUMB_SMOKE = [10, 22, 18]
FINGERS_L = {"Index": [30, 38, 22], "Middle": [34, 40, 24], "Ring": [38, 44, 26], "Pinky": [42, 46, 26]}
THUMB_L = [10, 16, 12]

MOUTH_IDLE = Vector((0.0, -0.145, 1.565))   # губы в стойке (по сетке YurchikMesh)


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def ramp(f, f0, f1):
    return smooth((f - f0) / float(f1 - f0)) if f1 != f0 else float(f >= f1)


def lerp_basis(a, b, t):
    la, ra, sa = a.decompose()
    lb, rb, sb = b.decompose()
    return Matrix.LocRotScale(la.lerp(lb, t), ra.slerp(rb, t), sa.lerp(sb, t))


def mouth_w(f):
    """Насколько правая кисть у губ (0 — лежит на снегу)."""
    return ramp(f, F_RAISE0, F_MOUTH) * (1.0 - ramp(f, F_DRAG1, F_DOWN))


def exhale_w(f):
    return ramp(f, F_DOWN - 10, F_EXH0 + 10) * (1.0 - ramp(f, F_EXH1 - 10, F_EXH1 + 30))


def flick(f):
    """Стряхивает пепел: два коротких кивка кистью (рад)."""
    if not (F_FLICK0 <= f <= F_FLICK1):
        return 0.0
    u = (f - F_FLICK0) / float(F_FLICK1 - F_FLICK0)
    return math.radians(14.0) * math.sin(u * 2.0 * math.pi * 2.0) * math.sin(u * math.pi)


def g2c(p):
    return Vector((-(p[2] - NODE[2]), -(p[0] - NODE[0]), p[1] - NODE[1]))


def c2skel(v):
    """Пространство арматуры → пространство скелета Godot (glTF, Y вверх)."""
    return [round(v.x, 5), round(v.z, 5), round(-v.y, 5)]


def place_set(scene):
    """Декорация меню вокруг Юрчика (для превью): мир Blender после импорта (X, Y, Z) = (x, −z, y)."""
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=SET)
    new = [o for o in scene.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    # X' = Yw + z0 (Yw = −z → −(z − z0)), Y' = −Xw + x0 (−(x − x0)), Z' = Zw − y0
    m = Matrix(((0, 1, 0, NODE[2]), (-1, 0, 0, NODE[0]), (0, 0, 1, -NODE[1]), (0, 0, 0, 1)))
    for r in roots:
        r.matrix_world = m @ r.matrix_world
    bpy.context.view_layer.update()
    return new


def main():
    G = globals()
    preview = G.get("PREVIEW", False)
    scene = bpy.data.scenes.get(SCENE)
    if scene is None:
        scene = bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = scene
    for o in list(scene.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes, bpy.data.cameras):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)
    for a in [a for a in bpy.data.actions if a.name.startswith(CLIP)]:
        bpy.data.actions.remove(a)
    bpy.ops.import_scene.gltf(filepath=SRC)
    # в других сценах файла может быть свой «Yurchik» — тогда у импорта имя с .001; берём по типу
    arm = next(o for o in scene.objects if o.type == 'ARMATURE')
    body_mesh = next(o for o in scene.objects if o.type == 'MESH' and o.name.startswith("YurchikMesh"))
    for o in list(scene.objects):
        if o.type == 'MESH' and o is not body_mesh:
            bpy.data.objects.remove(o, do_unlink=True)     # молоток и прочее из GMod-рига
    scene.render.fps = FPS

    sys.path.insert(0, os.path.join(ROOT, "tools", "blender"))
    import seat_poses as sp
    importlib.reload(sp)

    pb = arm.pose.bones
    arm.animation_data_create()
    arm.animation_data.action = bpy.data.actions["Idle"]
    scene.frame_set(0)
    bpy.context.view_layer.update()
    idle = {b.name: b.matrix_basis.copy() for b in pb}
    arm.animation_data.action = None
    sp.apply(arm, idle)

    pelvis, spine, head = pb["Pelvis"], pb["Spine"], pb["Head"]
    P_idle = pelvis.matrix.copy()
    foot_idle = {s: pb["Foot" + s].matrix.copy() for s in "LR"}
    ankle_idle = {s: pb["Foot" + s].head.copy() for s in "LR"}
    mouth_local = head.matrix.inverted() @ MOUTH_IDLE
    k_loc, b_loc = sp.hand_axes(pb, "R")

    # пальцы: правая держит сигарету, левая расслаблена — локальные позы (от положения кисти не зависят)
    fingers_r = [b.name for b in pb if b.name[:-2] in sp.FINGERS + ("Thumb",) and b.name[-2] == "R"]
    fingers_l = [b.name for b in pb if b.name[:-2] in sp.FINGERS + ("Thumb",) and b.name[-2] == "L"]
    for f in sp.FINGERS:
        sp.straighten(pb, "R", f)
        sp.curl(pb, "R", f, FINGERS_SMOKE[f], spread={"Index": 3.0, "Middle": -2.0}.get(f, 0.0))
        sp.straighten(pb, "L", f)
        sp.curl(pb, "L", f, FINGERS_L[f])
    sp.thumb(pb, "R", THUMB_SMOKE)
    sp.thumb(pb, "L", THUMB_L)
    smoke_f = {n: pb[n].matrix_basis.copy() for n in fingers_r}
    relax_l = {n: pb[n].matrix_basis.copy() for n in fingers_l}
    # сигарета в осях кисти: середина — между средними фалангами указательного и среднего, ось — к тылу
    hm = pb["HandR"].matrix.copy()
    c = (pb["IndexR2"].head + pb["MiddleR2"].head) * 0.5
    kw, bw = (hm.to_3x3() @ k_loc).normalized(), (hm.to_3x3() @ b_loc).normalized()
    c = c - bw * 0.004
    axis = (bw * 0.92 + kw * 0.25).normalized()
    cig_filter_l = hm.inverted() @ (c - axis * CIG_FILTER)
    cig_tip_l = hm.inverted() @ (c + axis * (CIG_LEN - CIG_FILTER))
    sp.apply(arm, idle)

    def body(f):
        sp.apply(arm, idle)
        br = math.sin(2.0 * math.pi * f / BREATH)
        sway = math.sin(2.0 * math.pi * f / LEN)
        lift = exhale_w(f)
        piv = P_idle.translation.copy()
        pelvis.matrix = (Matrix.Translation(Vector((0.0, PELVIS_BACK, -PELVIS_DOWN)))
                         @ sp.rot_about(piv, Vector((1, 0, 0)), math.radians(PELVIS_PITCH))
                         @ sp.rot_about(piv, Vector((0, 0, 1)), math.radians(1.5 * sway)) @ P_idle)
        bpy.context.view_layer.update()
        sh = spine.head.copy()
        spine.matrix = (sp.rot_about(sh, Vector((0, 1, 0)), math.radians(-SPINE_SIDE))
                        @ sp.rot_about(sh, Vector((1, 0, 0)), math.radians(SPINE_PITCH - 1.2 * br - 3.0 * lift))
                        @ sp.rot_about(sh, Vector((0, 0, 1)), math.radians(-4.0 + 2.0 * sway))
                        @ spine.matrix)
        bpy.context.view_layer.update()
        for s in "LR":
            out = 1.0 if s == "L" else -1.0
            th, shn, ft = pb["Thigh" + s], pb["Shin" + s], pb["Foot" + s]
            sp.two_bone(arm, th, shn, ankle_idle[s], th.head + Vector((out * 0.1, -1.0, 0.2)))
            sp.set_world_rot(ft, foot_idle[s].to_3x3())
        bpy.context.view_layer.update()

    def place(side, wrist, kn, back, pole, fingers):
        sp.place_hand(arm, side, wrist, kn, back, pole, forearm_share=0.6)
        for n, mb in fingers.items():
            pb[n].matrix_basis = mb
        bpy.context.view_layer.update()

    def rest_arm(side, elbow, fore):
        """Рука лежит: локоть — на опоре (на длине плеча от плечевого сустава, ближе всего к elbow),
        предплечье — по fore. Возвращает локоть и запястье (локоть же — полюс IK)."""
        up, lo = pb["UpperArm" + side], pb["Forearm" + side]
        l1, l2 = (lo.head - up.head).length, (lo.tail - lo.head).length
        s = up.head.copy()
        e = s + (elbow - s).normalized() * l1
        return e, e + fore.normalized() * l2

    act = bpy.data.actions.new(CLIP)
    arm.animation_data.action = act
    rep = {"elbow_z": [], "elbow_y": [], "cig_mouth_mm": [], "head_y": [], "shoulder": []}
    marks = {}
    for f in range(0, LEN + 1):
        ff = f % LEN                        # последний кадр = первый
        scene.frame_set(f)
        body(ff)
        # голова: взгляд во двор; к губам — чуть вниз на кисть; на выдохе — подбородок вверх
        mw, ew = mouth_w(ff), exhale_w(ff)
        tgt = LOOK_REST.lerp(LOOK_EXHALE, ew)
        tgt = tgt + Vector((0.0, 0.0, -1.5)) * mw
        sp.look(head, head.matrix.to_3x3(), head.head + tgt, Vector((0.0, 0.0, 1.0)))
        bpy.context.view_layer.update()
        mouth = head.matrix @ mouth_local

        # левая: лежит на снегу, чуть дышит
        br = math.sin(2.0 * math.pi * ff / BREATH)
        el, wl = rest_arm("L", ELBOW_L + Vector((0, 0, 0.003 * br)), FORE_L)
        place("L", wl, KN_L, BACK_L, el, relax_l)

        # правая: на снегу ↔ у губ (кисть ладонью к лицу, фильтр в губы)
        R_rest = sp.hand_world(pb, "R", KN_R, BACK_R)
        flk = flick(ff)
        if flk:
            # кивок кистью вокруг поперечной оси: кончик сигареты — вниз
            lat = (R_rest @ k_loc).cross(R_rest @ b_loc).normalized()
            R_rest = Matrix.Rotation(flk, 3, lat) @ R_rest
        rest_m = R_rest.to_4x4()
        er, wr = rest_arm("R", ELBOW_R + Vector((0, 0, 0.003 * br)), FORE_R)
        rest_m.translation = wr
        hfwd = (head.matrix.to_3x3() @ (head.bone.matrix_local.to_3x3().inverted() @ Vector((0.0, -1.0, 0.0)))).normalized()
        hup = (head.matrix.to_3x3() @ (head.bone.matrix_local.to_3x3().inverted() @ Vector((0.0, 0.0, 1.0)))).normalized()
        hleft = hup.cross(hfwd).normalized()          # влево от лица (+X в покое)
        kn_m = (hup * 0.75 + hleft * 0.55 - hfwd * 0.1).normalized()
        back_m = (hfwd * 1.0 - hleft * 0.35).normalized()
        R_m = sp.hand_world(pb, "R", kn_m, back_m)
        mouth_m = R_m.to_4x4()
        mouth_m.translation = (mouth + hfwd * 0.004) - R_m @ cig_filter_l
        # путь к губам — дугой: кисть поднимается от снега вверх, а не сквозь подбородок
        m = lerp_basis(rest_m, mouth_m, mw)
        m = Matrix.Translation(Vector((0.0, 0.03, 0.06)) * math.sin(math.pi * mw)) @ m
        pole = er.lerp(pb["UpperArmR"].head + POLE_R_MOUTH, mw)
        place("R", m.translation, m.to_3x3() @ k_loc, m.to_3x3() @ b_loc, pole, smoke_f)

        if F_MOUTH <= ff <= F_DRAG1:
            rep["cig_mouth_mm"].append(round(((pb["HandR"].matrix @ cig_filter_l) - mouth).length * 1000, 1))
        if ff % 30 == 0:
            rep["elbow_z"].append([round(pb["ForearmL"].head.z, 3), round(pb["ForearmR"].head.z, 3)])
            rep["elbow_y"].append([round(pb["ForearmL"].head.y, 3), round(pb["ForearmR"].head.y, 3)])
            rep["head_y"].append([round(head.head.y, 3), round(head.head.z, 3)])
            rep["shoulder"].append([round(c, 3) for c in pb["UpperArmR"].head])
        if f == REF:
            hmr = pb["HandR"].matrix
            marks = {"filter": c2skel(hmr @ cig_filter_l), "tip": c2skel(hmr @ cig_tip_l), "mouth": c2skel(mouth),
                     "hand_head": c2skel(pb["HandR"].head), "head_head": c2skel(head.head)}
        for b in pb:
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("rotation_quaternion", frame=f)
            b.keyframe_insert("scale", frame=f)

    scene.frame_start, scene.frame_end = 0, LEN
    out = {"report": rep, "marks": marks}
    if preview:
        out["renders"] = render_preview(scene, arm, G.get("PREVIEW_DIR"), G.get("PREVIEW_FRAMES", [0, F_MOUTH + 10]))
        return out

    # --- экспорт клипа ---
    ad = arm.animation_data
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    tr = ad.nla_tracks.new()
    tr.name = CLIP
    st = tr.strips.new(CLIP, 0, act)
    if hasattr(st, "action_slot") and len(getattr(act, "slots", [])) and st.action_slot is None:
        st.action_slot = act.slots[0]
    ad.action = None
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in scene.objects:
        if o is arm or o is body_mesh:
            o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(
        filepath=OUT, use_selection=True, use_active_scene=True, export_format='GLB',
        export_apply=False, export_skins=True, export_materials='NONE', export_image_format='NONE',
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_frame_step=1, export_optimize_animation_size=True, export_anim_single_armature=True,
        export_def_bones=False, export_reset_pose_bones=True, export_bake_animation=False)
    ad.action = act
    tr.mute = True
    data = {
        "fps": FPS, "frames": LEN + 1, "ref": REF,
        "marks": {"raise": F_RAISE0, "mouth": F_MOUTH, "drag_end": F_DRAG1, "down": F_DOWN,
                  "exhale0": F_EXH0, "exhale1": F_EXH1, "flick0": F_FLICK0, "flick1": F_FLICK1},
        # точки в пространстве скелета Godot на кадре ref: фильтр и кончик сигареты, губы, головы костей
        "points": marks,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    out["glb"] = OUT
    return out


def render_preview(scene, arm, out_dir, frames):
    """Декорация меню вокруг + камера меню; рендер workbench в out_dir."""
    place_set(scene)
    cam_d = bpy.data.cameras.new("SmokeCam")
    cam_d.lens_unit = 'FOV'
    cam_d.angle_y = math.radians(62.0)
    cam_d.sensor_fit = 'VERTICAL'
    cam = bpy.data.objects.new("SmokeCam", cam_d)
    scene.collection.objects.link(cam)
    cp = globals().get("PREVIEW_CAM", CAM)
    p, t = g2c(cp[0]), g2c(cp[1])
    cam.location = p
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = (t - p).to_track_quat('-Z', 'Y')
    scene.camera = cam
    cam2_d = bpy.data.cameras.new("SmokeSide")
    cam2_d.lens = 35
    cam2 = bpy.data.objects.new("SmokeSide", cam2_d)
    scene.collection.objects.link(cam2)
    p2, t2 = Vector((1.6, 0.35, 1.9)), Vector((0.0, -0.5, 1.0))
    cam2.location = p2
    cam2.rotation_mode = 'QUATERNION'
    cam2.rotation_quaternion = (t2 - p2).to_track_quat('-Z', 'Y')
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'OBJECT'
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.image_settings.file_format = 'PNG'
    for o in scene.objects:
        if o.type == 'MESH':
            o.color = (0.9, 0.55, 0.3, 1) if o.parent == arm or o.name.startswith("YurchikMesh") else (0.7, 0.7, 0.75, 1)
    paths = []
    for f in frames:
        scene.frame_set(f)
        for cname, c in (("menu", cam), ("side", cam2)):
            scene.camera = c
            for o in scene.objects:
                if o.name.startswith(("HomeFacade", "Room_", "Blocks", "Cars", "Trees", "Lamps")):
                    o.hide_render = cname == "side"
            path = os.path.join(out_dir, "smoke_%s_%03d.png" % (cname, f))
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            paths.append(path)
    scene.camera = cam
    return paths


if __name__ == "__main__":
    result = main()
