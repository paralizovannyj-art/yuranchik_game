"""Сцена «PhonePose»: правая рука Юрчика держит телефон — поза ставится руками в Blender и уходит в игру.

Что в сцене (всё — как в игре, scripts/ui/phone.gd и scripts/player/phone_arm.gd):
  * PoseCam — камера от первого лица: место и наклон из игры, FOV 72° по вертикали, кадр 854×480;
  * PhoneRoot — узел телефона: OPEN_POS / OPEN_ROT относительно камеры, масштаб 1.6; в нём модель phone.gltf;
  * PoseRig / PoseMesh — копия скелета и меша Юрчика из сцены Yurchik3 (её строит build_yurchik_v3.py);
    голова и шея скрыты, чтобы не заслоняли камеру;
  * HandGoal — пустышка внутри PhoneRoot: кисть (кость HandR) копирует её положение, поворот и масштаб,
    плечо и предплечье тянутся к ней IK (в игре так же — двухзвенный IK);
  * пальцы — обычные повороты костей (R-поворот в позе), их и надо подгонять.
Референс-фото: положите картинку в docs/references/phone_hold_ref.png (или .jpg) — она встанет полупрозрачной
подложкой в вид из камеры (Numpad 0).

Использование (в открытом Blender, после сборки build_yurchik_v3.py):
    exec(open(r"<repo>/tools/blender/pose_phone_hold.py", encoding="utf-8").read(), ns)  # ns["YUR_ROOT"] = <repo>
    setup()            — построить сцену и загрузить позу из assets/models/phone_hold.json
    save_pose()        — записать текущую позу (HandGoal + повороты пальцев) в assets/models/phone_hold.json
    render(path)       — кадр из PoseCam (Workbench) — сравнить с референсом
В JSON повороты костей — кватернионы [x, y, z, w] в осях узла телефона; оси PhoneRoot совпадают с осями
узла Phone в Godot, а оси костей — с осями костей в Godot, поэтому игра берёт их как есть.
"""
import bpy
import json
import math
import os
from mathutils import Matrix, Quaternion, Vector

ROOT = globals().get("YUR_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
POSE_JSON = os.path.join(ROOT, "assets", "models", "phone_hold.json")
PHONE_GLTF = os.path.join(ROOT, "assets", "models", "phone.gltf")
SCENE = "PhonePose"
SRC_SCENE = "Yurchik3"

# --- из игры ---
# камера в осях скелета Godot (Skeleton3D → Camera): столбцы X, Y, Z и начало
CAM_G = ((-1.0, 0.0, 0.0), (0.0, 0.992809, 0.119712), (0.0, 0.119712, -0.992809), (0.0, 1.620001, 0.185852))
CAM_FOV = 72.0                                    # по вертикали (keep_aspect = KEEP_HEIGHT)
RES = (854, 480)
OPEN_POS = (0.03, -0.042, -0.185)                  # scripts/ui/phone.gd
OPEN_ROT = (10.0, -10.0, -8.0)                     # градусы, порядок Godot YXZ
PHONE_SCALE = 1.6
FINGERS = ["Index", "Middle", "Ring", "Pinky", "Thumb"]
POSE_BONES = ["HandR"] + [f"{n}R{k}" for n in FINGERS for k in (1, 2, 3)]


def g2b(v):
    """Godot (x, y, z) → Blender (x, −z, y)."""
    return Vector((v[0], -v[2], v[1]))


def cam_matrix():
    x, y, z, o = (g2b(c) for c in CAM_G)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = o
    return m


def phone_local():
    rx, ry, rz = (math.radians(a) for a in OPEN_ROT)
    rot = Matrix.Rotation(ry, 4, 'Y') @ Matrix.Rotation(rx, 4, 'X') @ Matrix.Rotation(rz, 4, 'Z')   # Godot YXZ
    return Matrix.Translation(OPEN_POS) @ rot @ Matrix.Scale(PHONE_SCALE, 4)


def _link(sc, ob):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    sc.collection.objects.link(ob)
    return ob


def _empty(sc, name, parent=None, size=0.01, kind='ARROWS'):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = kind; ob.empty_display_size = size
    sc.collection.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def setup(load=True):
    src = bpy.data.scenes.get(SRC_SCENE)
    if src is None or "Yurchik3" not in src.objects:
        raise RuntimeError("нет сцены Yurchik3 — сначала соберите tools/blender/build_yurchik_v3.py")
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    if bpy.context.window:
        bpy.context.window.scene = sc

    # --- камера ---
    cd = bpy.data.cameras.get("PoseCam") or bpy.data.cameras.new("PoseCam")
    cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(CAM_FOV); cd.clip_start = 0.01
    cam = bpy.data.objects.new("PoseCam", cd)
    sc.collection.objects.link(cam)
    cam.matrix_world = cam_matrix()
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = RES
    cd.background_images.clear()
    for ext in ("png", "jpg", "jpeg"):
        p = os.path.join(ROOT, "docs", "references", "phone_hold_ref." + ext)
        if os.path.exists(p):
            bg = cd.background_images.new()
            bg.image = bpy.data.images.load(p, check_existing=True)
            bg.alpha = 0.5; bg.display_depth = 'FRONT'; bg.frame_method = 'FIT'
            cd.show_background_images = True
            break

    # --- телефон ---
    root = _empty(sc, "PhoneRoot", cam, 0.02)
    root.matrix_parent_inverse = Matrix.Identity(4)
    root.matrix_basis = phone_local()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=PHONE_GLTF)
    new = [o for o in bpy.data.objects if o not in before]
    fix = Matrix.Rotation(math.radians(-90), 4, 'X')       # импорт glTF: (u, v, w) → (u, −w, v); возвращаем оси модели
    for o in new:
        _link(sc, o)
        o.name = "Phone_" + o.name
        if o.parent is None:
            mb = o.matrix_basis.copy()
            o.parent = root; o.matrix_parent_inverse = Matrix.Identity(4)
            o.matrix_basis = fix @ mb

    # --- Юрчик: своя копия скелета (поза в Yurchik3 не трогается) ---
    arm = src.objects["Yurchik3"].copy(); arm.name = "PoseRig"
    sc.collection.objects.link(arm)
    body = src.objects["Yurchik3Mesh"].copy(); body.name = "PoseMesh"
    sc.collection.objects.link(body)
    body.parent = arm
    for m in body.modifiers:
        if m.type == 'ARMATURE':
            m.object = arm
    for g in ("Head", "Neck"):                              # голова не заслоняет камеру
        if g in body.vertex_groups:
            mk = body.modifiers.new("Hide" + g, 'MASK'); mk.vertex_group = g; mk.invert_vertex_group = True
    arm.show_in_front = True; arm.data.display_type = 'STICK'

    goal = _empty(sc, "HandGoal", root, 0.03)
    pb = arm.pose.bones
    for b in pb:
        b.rotation_mode = 'QUATERNION'
        b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0); b.scale = (1, 1, 1)
        for c in list(b.constraints):
            b.constraints.remove(c)
    ct = pb["HandR"].constraints.new('COPY_TRANSFORMS'); ct.target = goal
    ik = pb["ForearmR"].constraints.new('IK'); ik.target = goal; ik.chain_count = 2
    pole = _empty(sc, "ElbowPole", None, 0.05, 'SPHERE')    # локоть вниз-вправо (как pole в phone_arm.gd)
    pole.location = arm.data.bones["UpperArmR"].head_local + g2b((-0.6, -1.0, -0.15)).normalized() * 0.5
    ik.pole_target = pole; ik.pole_angle = math.radians(45)
    w = bpy.data.worlds.get("PoseWorld") or bpy.data.worlds.new("PoseWorld")
    w.color = (0.12, 0.12, 0.13)
    sc.world = w
    if load and os.path.exists(POSE_JSON):
        load_pose()
    shade(sc)
    return sc


def shade(sc):
    sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_backface_culling = True; sh.background_type = 'WORLD'
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.view_settings.view_transform = 'Standard'


def _objs():
    sc = bpy.data.scenes[SCENE]
    return sc, sc.objects["PoseRig"], sc.objects["PhoneRoot"], sc.objects["HandGoal"]


def load_pose(path=POSE_JSON):
    sc, arm, root, goal = _objs()
    data = json.load(open(path, encoding="utf-8"))
    hs = data.get("hand_scale", 1.4)
    q = data["bones"]["HandR"]
    goal.matrix_basis = Matrix.LocRotScale(Vector(data["origin"]), Quaternion((q[3], q[0], q[1], q[2])),
                                           Vector((1, 1, 1)) * (hs / PHONE_SCALE))
    pw = root.matrix_world.to_quaternion()
    pb = arm.pose.bones
    for k in (1, 2, 3):                                     # от основания к кончикам: родитель уже стоит
        bpy.context.view_layer.update()
        for n in FINGERS:
            b = pb[f"{n}R{k}"]
            if b.name not in data["bones"]:
                continue
            q = data["bones"][b.name]
            want = arm.matrix_world.to_quaternion().inverted() @ pw @ Quaternion((q[3], q[0], q[1], q[2]))
            par = b.parent
            base = (par.matrix @ par.bone.matrix_local.inverted() @ b.bone.matrix_local).to_quaternion()
            b.rotation_quaternion = base.inverted() @ want
    bpy.context.view_layer.update()


def save_pose(path=POSE_JSON):
    sc, arm, root, goal = _objs()
    bpy.context.view_layer.update()
    rinv = root.matrix_world.inverted()
    bones = {}
    for n in POSE_BONES:
        m = rinv @ arm.matrix_world @ arm.pose.bones[n].matrix
        q = m.to_quaternion().normalized()
        bones[n] = [round(q.x, 6), round(q.y, 6), round(q.z, 6), round(q.w, 6)]
    o = (rinv @ arm.matrix_world @ arm.pose.bones["HandR"].matrix).translation
    hs = goal.matrix_basis.to_scale()[0] * PHONE_SCALE
    data = {"about": "Поза правой кисти с телефоном (tools/blender/pose_phone_hold.py). Повороты костей — кватернионы "
                     "[x, y, z, w] в осях телефона (узел Phone в Godot), origin — начало кости HandR в тех же осях.",
            "hand_scale": round(hs, 4), "origin": [round(o.x, 6), round(o.y, 6), round(o.z, 6)], "bones": bones}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


# --- подгонка позы: точки — в мм телефона (u вправо, v вверх, w к зрителю; ребро u ±28, верх v 55.5,
#     спинка w −8.5, лицо w +6) ---
def to_arm(mm):
    sc, arm, root, goal = _objs()
    return arm.matrix_world.inverted() @ root.matrix_world @ (Vector(mm) * 0.001)


def aim(name, target_mm):
    """Повернуть кость (минимальным поворотом), чтобы она смотрела на точку target_mm."""
    sc, arm, root, goal = _objs()
    bpy.context.view_layer.update()
    pb = arm.pose.bones[name]
    loc, rot, scl = pb.matrix.decompose()
    cur = (rot @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference((to_arm(target_mm) - pb.head).normalized())
    pb.matrix = Matrix.LocRotScale(loc, q @ rot, scl)
    bpy.context.view_layer.update()


def twist(name, deg):
    """Повернуть кость вокруг её оси (куда смотрит ноготь)."""
    sc, arm, root, goal = _objs()
    pb = arm.pose.bones[name]
    pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion((0, 1, 0), math.radians(deg))
    bpy.context.view_layer.update()


def move_hand(d_mm=(0, 0, 0), rot_w=0.0, pivot_mm=(-12, 4, -20)):
    """Сдвинуть кисть (HandGoal) на d_mm и повернуть на rot_w° вокруг оси w (к зрителю) через pivot_mm."""
    sc, arm, root, goal = _objs()
    pv = Vector(pivot_mm) * 0.001
    goal.matrix_basis = (Matrix.Translation(Vector(d_mm) * 0.001) @ Matrix.Translation(pv)
                         @ Matrix.Rotation(math.radians(rot_w), 4, 'Z') @ Matrix.Translation(-pv) @ goal.matrix_basis)
    bpy.context.view_layer.update()


def joints():
    """Начало и конец костей пальцев в мм телефона."""
    sc, arm, root, goal = _objs()
    bpy.context.view_layer.update()
    inv = root.matrix_world.inverted() @ arm.matrix_world
    return {n: [round(x) for x in (inv @ arm.pose.bones[n].head) * 1000] + [round(x) for x in (inv @ arm.pose.bones[n].tail) * 1000]
            for n in POSE_BONES[1:]}


def render(path):
    sc, *_ = _objs()
    shade(sc)
    sc.render.filepath = path
    if bpy.context.window:
        bpy.context.window.scene = sc
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return path


if __name__ == "__main__" and not globals().get("YUR_NO_SETUP"):
    setup()
