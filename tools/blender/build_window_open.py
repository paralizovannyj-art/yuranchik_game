# Анимация «Юрчик открывает окно» (WindowOpen) для скелета Юрчика v3 + дорожки створки, ручки и взгляда.
#
# Пластиковое окно в его комнате (assets/models/room_window.gltf, scripts/world/room_window.gd): правая створка
# на петлях справа, ручка — у импоста, на высоте 1.57 м от пола, за подоконником (0.9 м). Юрчик стоит перед
# ручкой, между комодом и креслом, и открывает окно так, как открывают его в жизни:
#   A  тянется правой рукой через подоконник к ручке, корпус чуть вперёд, кисть раскрывается;
#   B  берётся за ручку кулаком (большой палец сверху, у шейки);
#   C  поворачивает ручку вниз → вбок (кисть проворачивается ладонью вниз);
#   D  створка с «чпоком» отлипает от уплотнителя и он ведёт её за ручку на себя и вправо до упора (~78°),
#      корпус поворачивается следом, вес чуть назад;
#   E  отпускает ручку, рука возвращается в стойку; взгляд — в открытое окно, на улицу.
# Закрывает — тот же клип задом наперёд (room_window.gd): тянется к ручке открытой створки, толкает её
# на место, ручку вниз, отпускает.
#
# Всё считается в пространстве «места у окна» — маркер RoomWindowUse/WindowSpot в stairwell.tscn: узел игрока
# стоит в нём и не двигается, всё движение — в костях. В Blender это пространство арматуры: вперёд (к окну) −Y,
# вправо −X, вверх Z. В Godot (модель повёрнута на 180°): x = −X, y = Z, z = Y.
# Позы — аналитический IK без констрейнтов (seat_poses.py): одна и та же поза при каждом запуске.
# Дорожки створки и ручки (градусы) и точка взгляда — покадрово в assets/animations/window/window_open.json.
#
# Запуск — только в живом Blender через Blender MCP (правило проекта):
#   exec(open(r"<проект>/tools/blender/build_window_open.py", encoding="utf-8").read(), {"__name__": "__main__"})
# Скрипт строит всё в своей сцене WindowOpen (другие сцены не трогает) и пишет
# assets/animations/window/yurchik_window.glb (клип WindowOpen) и assets/animations/window/window_open.json.
import bpy, os, sys, math, json, importlib
from mathutils import Matrix, Vector, Quaternion

ROOT = r"C:\Users\mrs\Documents\yuranchik_game"
SRC = os.path.join(ROOT, "assets", "animations", "gmod", "yurchik_gmod.glb")
WINDOW = os.path.join(ROOT, "assets", "models", "room_window.gltf")
OUT_DIR = os.path.join(ROOT, "assets", "animations", "window")
OUT = os.path.join(OUT_DIR, "yurchik_window.glb")
OUT_JSON = os.path.join(OUT_DIR, "window_open.json")
SCENE = "WindowOpen"
CLIP = "WindowOpen"
FPS = 30

# --- где что стоит (Godot, мир stairwell.tscn) ---
# узел окна RoomWindow: базис X = (0, 0, −1), Y = вверх, Z = (1, 0, 0)
WIN_ORIGIN = (-8.26, 9.3, 5.68)
# место у окна (WindowSpot): узел игрока, смотрит на окно (+Z мира). Между комодом (x > −8.33) и кучей
# одежды у кресла (x < −9.14); подоконник — с z 5.47, батарея под ним — 5.54
SPOT = (-8.95, 8.4, 5.17)

OPEN_ANGLE = 78.0          # ° — створка до упора (= open_angle в room_window.gd)
HANDLE_ANGLE = 90.0        # ° — ручка вниз → вбок

# --- кадры ---
# reach — рука пошла; near — кисть у ручки, раскрыта; grab — кулак на ручке; turn0/turn1 — поворот ручки;
# pop — створка отлипла; open — створка у упора; release — отпускает; let — кисть отошла от ручки;
# free — рука в стойке; end — конец клипа
F_REACH, F_NEAR, F_GRAB = 3, 19, 25
F_TURN0, F_TURN1 = 29, 39
F_POP = 43
F_OPEN = 86
F_RELEASE, F_LET, F_FREE, F_END = 92, 100, 118, 124
LEN = F_END

# хват: кулак вокруг ручки — пястные кости к окну, тыл кисти вправо, большой палец сверху
GRIP_DOWN = 0.075          # м — середина кулака ниже оси ручки (рычаг 14 см)
GRIP_OUT = 0.022           # м — рычаг торчит из створки к комнате
# рычаг в кулаке: под средними фалангами (проксимальные — вниз от костяшек, средние — назад под рычагом),
# измерено по суставам: костяшка среднего — 8.7 см от запястья, проксимальная фаланга 4.5 см
FIST_IN = 0.083            # м — от запястья вдоль кисти до оси рычага в кулаке
FIST_PALM = 0.030          # м — ось рычага в кулаке на столько глубже тыла кисти (к ладони)
APPROACH = Vector((0.0, 0.07, -0.04))   # кисть подходит к ручке спереди-снизу (к Юрчику и вниз)
LET_BACK = Vector((0.0, 0.08, -0.03))   # отпустив, кисть отходит так же

# тело: (кадр, наклон корпуса вперёд °, поворот вправо °, таз вперёд м, таз вправо м, наклон корпуса вправо °)
BODY_KEYS = [
    (0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (F_REACH, 0.0, 0.0, 0.0, 0.0, 0.0),
    (F_NEAR, 9.0, -3.0, 0.03, 0.0, 0.0),
    (F_GRAB, 10.0, -3.0, 0.035, 0.0, 0.0),
    (F_TURN1, 13.0, -4.0, 0.05, 0.0, 0.0),        # ручка вбок — кулак уходит вправо-вверх: ближе к окну
    (F_POP + 6, 11.0, -1.0, 0.04, 0.01, 1.0),
    (F_OPEN, 1.0, 10.0, -0.015, -0.015, -2.0),    # створка у упора: ручка справа у плеча — корпус чуть влево, рука вбок
    (F_LET, 1.0, 8.0, -0.015, -0.01, -1.0),
    (F_FREE, 0.0, 3.0, 0.0, 0.0, 0.0),
    (F_END, 0.0, 2.0, 0.0, 0.0, 0.0),
]
# шаг правой (отрыв, постановка, сдвиг, разворот носка вправо °). С места у окна (SPOT) до ручки открытой
# створки рукой достаёт и так (0.38 м от плеча), поэтому шага нет; сдвиг тела вправо подводил кисть к лицу
STEP_R = (F_POP + 12, F_POP + 28, Vector((0.0, 0.0, 0.0)), 0.0)
STEP_LIFT = 0.06
PELVIS_TWIST = 0.4         # доля поворота корпуса, которую берёт таз (ноги стоят)
PELVIS_DOWN = 0.012        # м — колени чуть мягче, пока тянется (иначе нога в струну)

# пальцы: раскрыта (тянется) и кулак на ручке; (сгибы по суставам, °)
OPEN_CURL = [12, 12, 8]
GRIP_CURL = {"Index": [62, 78, 48], "Middle": [66, 82, 50], "Ring": [68, 84, 50], "Pinky": [70, 84, 48]}
GRIP_THUMB = [18, 28, 22]
OPEN_THUMB = [0, 4, 4]


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def ramp(f, f0, f1):
    return smooth((f - f0) / float(f1 - f0)) if f1 != f0 else float(f >= f1)


def mono(keys, f):
    """Монотонный кубический сплайн (Фритч–Карлсон) по ключам [(кадр, число)]: плавно, без перелётов."""
    xs = [k[0] for k in keys]
    ys = [k[1] for k in keys]
    if f <= xs[0]:
        return ys[0]
    if f >= xs[-1]:
        return ys[-1]
    n = len(xs)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
    m[0] = 0.0
    m[-1] = 0.0
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / math.sqrt(s)
                m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    i = max(j for j in range(n - 1) if xs[j] <= f)
    h = xs[i + 1] - xs[i]
    t = (f - xs[i]) / h
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i]
            + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1])


def lerp_basis(a, b, t):
    la, ra, sa = a.decompose()
    lb, rb, sb = b.decompose()
    return Matrix.LocRotScale(la.lerp(lb, t), ra.slerp(rb, t), sa.lerp(sb, t))


# --- створка и ручка по кадрам ---
SASH_KEYS = [(F_POP, 0.0), (F_POP + 3, 4.0), (F_POP + 9, 10.0), (F_OPEN - 10, OPEN_ANGLE - 4.0),
             (F_OPEN, OPEN_ANGLE)]


def sash_at(f):
    return mono(SASH_KEYS, f) if f > F_POP else 0.0


def handle_at(f):
    return HANDLE_ANGLE * ramp(f, F_TURN0, F_TURN1)


def body_at(f):
    return tuple(mono([(k[0], k[i]) for k in BODY_KEYS], f) for i in range(1, 6))


def foot_offset(s, f):
    """Сдвиг стопы (м), её разворот (°) и подъём над полом на кадре f."""
    if s != "R":
        return Vector(), 0.0, 0.0
    f0, f1, off, yaw = STEP_R
    u = min(max((f - f0) / float(f1 - f0), 0.0), 1.0)
    lift = STEP_LIFT * math.sin(math.pi * u) ** 2 if off.length > 1e-6 else 0.0
    return off * smooth(u), yaw * smooth(u), lift


def hand_weight(f):
    """Насколько правая рука ведёт кисть к ручке (0 — висит сама, как в стойке)."""
    return ramp(f, F_REACH, F_GRAB) * (1.0 - ramp(f, F_LET, F_FREE))


# Godot (мир) → пространство арматуры у окна: X = dx, Y = −dz, Z = dy
C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def g2b_point(p):
    return Vector((p[0] - SPOT[0], -(p[2] - SPOT[2]), p[1] - SPOT[1]))


def place_window(scene):
    """Модель окна в пространстве «места у окна» (для дорожек и обзорных рендеров)."""
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=WINDOW)
    new = [o for o in scene.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    wb = Matrix(((0, 0, 1), (0, 1, 0), (-1, 0, 0)))   # колонки: X = (0, 0, −1), Y = вверх, Z = (1, 0, 0) — узел окна в мире Godot
    mg = wb.to_4x4()
    mg.translation = Vector(WIN_ORIGIN) - Vector(SPOT)
    mb = C @ mg @ C.inverted()
    for r in roots:
        r.matrix_world = mb @ r.matrix_world
    bpy.context.view_layer.update()
    sash = next(o for o in new if o.name.startswith("RoomWindowSash_nocol"))
    handle = next(o for o in new if o.name.startswith("RoomWindowHandle_nocol"))
    return new, sash, handle


FINGER_WRAP = (0.019, -0.008)  # м — кончик пальца за рычагом (к запястью) и к ладони: палец обвил рычаг


def fit_fist(arm, sp, grip_w, bar, lev, fingers):
    """Кулак на рычаге: сгиб каждого пальца подбирается (seat_poses.fit_finger), чтобы кончик лёг под рычаг
    (пальцы обхватывают его), большой — сверху на рычаг у указательного. Возвращает локальные позы костей
    пальцев (от положения кисти не зависят) и промахи кончиков, мм."""
    pb = arm.pose.bones
    hand = pb["HandR"]
    # хват в осях кисти — кисть ставим только поворотом (кость сцеплена с предплечьем), точки — от неё
    bar_l = grip_w.inverted() @ bar
    lev_l = grip_w.to_3x3().inverted() @ lev
    sp.set_world_rot(hand, grip_w.to_3x3())
    m = hand.matrix.copy()
    k_loc, b_loc = sp.hand_axes(pb, "R")
    kw, bw = (m.to_3x3() @ k_loc).normalized(), (m.to_3x3() @ b_loc).normalized()
    bw_ = m @ bar_l
    lw_ = (m.to_3x3() @ lev_l).normalized()
    # Сгиб в кулак — свой, с одной осью поперёк кисти и одним знаком на все суставы. curl() из seat_poses
    # выбирает знак по тому, уходит ли кончик от тыла кисти, — при сгибе больше 90° средняя фаланга уже
    # смотрит назад, и дальний сустав загибался наружу (кончики на 4 см ниже рычага).
    lat = kw.cross(bw).normalized()
    sgn = 1.0 if (Matrix.Rotation(0.1, 3, lat) @ kw).dot(bw) < 0.0 else -1.0

    def fist_curl(f, a1, a2, a3):
        for b in sp._chain(pb, "R", f):
            b.matrix_basis = Matrix()
        bpy.context.view_layer.update()
        sp.straighten(pb, "R", f)
        # без веера: в покое указательный и мизинец расходятся от середины на 1–3 см к кончикам,
        # в кулаке пальцы сходятся — убираем боковую составляющую у первой фаланги (остальные идут за ней)
        b1 = pb[f + "R1"]
        d = b1.tail - b1.head
        sp._aim(b1, b1.head + d - lat * d.dot(lat) * 0.85)
        for i, a in enumerate((a1, a2, a3)):
            bone = pb["%sR%d" % (f, i + 1)]
            sp.set_world_rot(bone, Matrix.Rotation(math.radians(a) * sgn, 3, lat) @ bone.matrix.to_3x3())

    miss = {}
    for f in sp.FINGERS:
        mcp = pb[f + "R1"].head
        s = (mcp - bw_).dot(lw_)
        tip = bw_ + lw_ * s - kw * FINGER_WRAP[0] - bw * FINGER_WRAP[1]
        x = [float(GRIP_CURL[f][0]), float(GRIP_CURL[f][1])]

        def ev(x):
            fist_curl(f, x[0], x[1], x[1] * 0.75)
            return (sp.finger_tip(pb, "R", f) - tip).length
        err = ev(x)
        step = 16.0
        while step > 0.25:
            moved = False
            for i in range(2):
                for d in (step, -step):
                    y = list(x)
                    y[i] = min(max(y[i] + d, 0.0), 105.0)
                    e = ev(y)
                    if e < err - 1e-6:
                        x, err, moved = y, e, True
            if not moved:
                step *= 0.5
        ev(x)
        miss[f] = round(err * 1000.0, 1)
        miss[f + "_curl"] = [round(x[0]), round(x[1])]
    # большой — в обхват: кончик на средней фаланге указательного, снаружи кулака. Основание — как в
    # GRIP_THUMB, две дальние фаланги — двухкостный IK на эту точку, сустав — наружу от ладони
    sp.thumb(pb, "R", GRIP_THUMB)
    idx2 = pb["IndexR2"]
    tip = (idx2.head + idx2.tail) * 0.5 + kw * 0.009
    t2, t3 = pb["ThumbR2"], pb["ThumbR3"]
    sp.two_bone(arm, t2, t3, tip, t3.head + bw * 0.05 + kw * 0.02)
    miss["Thumb"] = round((t3.tail - tip).length * 1000.0, 1)
    return {n: pb[n].matrix_basis.copy() for n in fingers}, miss


def main():
    scene = bpy.data.scenes.get(SCENE)
    if scene is None:
        scene = bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = scene
    for o in list(scene.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)
    for a in [a for a in bpy.data.actions if a.name.startswith(CLIP)]:
        bpy.data.actions.remove(a)
    bpy.ops.import_scene.gltf(filepath=SRC)
    arm = scene.objects["Yurchik"]
    scene.render.fps = FPS
    win_objs, sash, handle = place_window(scene)
    sash_rest = sash.matrix_basis.copy()
    handle_rest = handle.matrix_basis.copy()

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
    shoulder = pb["UpperArmR"].head.copy()
    k_loc, b_loc = sp.hand_axes(pb, "R")

    # пальцы: раскрытая кисть и кулак — локальные позы костей пальцев (не зависят от того, где кисть)
    fingers = [b.name for b in pb if b.name[:-2] in sp.FINGERS + ("Thumb",) and b.name[-2] == "R"]
    sp.apply(arm, idle)
    for f in sp.FINGERS:
        sp.straighten(pb, "R", f)
        sp.curl(pb, "R", f, OPEN_CURL)
    sp.thumb(pb, "R", OPEN_THUMB)
    open_f = {n: pb[n].matrix_basis.copy() for n in fingers}
    sp.apply(arm, idle)

    # хват на ручке в её собственных осях (ручка закрыта, створка закрыта)
    sash.matrix_basis = sash_rest
    handle.matrix_basis = handle_rest
    bpy.context.view_layer.update()
    hw = handle.matrix_world.copy()
    pivot = hw.translation.copy()
    bar = pivot + Vector((0.0, GRIP_OUT, -GRIP_DOWN))        # середина кулака на рычаге
    knuckle = Vector((0.0, -1.0, 0.18)).normalized()          # пястные — к окну, чуть вверх (рука снизу)
    back = Vector((-1.0, 0.0, 0.0))                           # тыл кисти — вправо
    rot = sp.hand_world(pb, "R", knuckle, back)
    wrist = bar - knuckle * FIST_IN + back * FIST_PALM
    grip_w = rot.to_4x4()
    grip_w.translation = wrist
    GRIP_LOCAL = hw.inverted() @ grip_w
    grip_f, fist = fit_fist(arm, sp, grip_w, bar, Vector((0, 0, -1)), fingers)
    sp.apply(arm, idle)

    sign = {"sash": 1.0, "handle": 1.0}

    def handle_world(f):
        sash.matrix_basis = sash_rest @ Matrix.Rotation(math.radians(sash_at(f) * sign["sash"]), 4, 'Z')
        handle.matrix_basis = handle_rest @ Matrix.Rotation(math.radians(handle_at(f) * sign["handle"]), 4, 'X')
        bpy.context.view_layer.update()
        return handle.matrix_world.copy()

    # оси в Blender: рычаг из «вниз» должен уйти вправо (−X), створка — в комнату (+Y); иначе знак наоборот
    hw90 = handle_world(F_TURN1)
    lever = hw90.to_3x3() @ (hw.to_3x3().inverted() @ Vector((0, 0, -1)))
    if lever.x > 0.0:
        sign["handle"] = -1.0
    if handle_world(F_OPEN).translation.y < hw.translation.y:
        sign["sash"] = -1.0
    act = bpy.data.actions.new(CLIP)
    arm.animation_data.action = act
    for o in (sash, handle):
        o.animation_data_create()
    looks, sashes, handles, report, rolls = [], [], [], [], []
    for f in range(0, LEN + 1):
        scene.frame_set(f)
        hw_f = handle_world(f)
        sash.keyframe_insert("rotation_quaternion" if sash.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f)
        handle.keyframe_insert("rotation_quaternion" if handle.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f)
        sashes.append(sash_at(f))
        handles.append(handle_at(f))

        sp.apply(arm, idle)
        lean, twist, fwd, right, side = body_at(f)
        # таз: вперёд к окну (потом назад), вправо — вес на правую, чуть ниже, часть поворота корпуса
        reach_soft = ramp(f, F_REACH, F_NEAR) * (1.0 - ramp(f, F_OPEN, F_FREE))
        piv = P_idle.translation.copy()
        pelvis.matrix = (Matrix.Translation(Vector((-right, -fwd, -PELVIS_DOWN * reach_soft)))
                         @ sp.rot_about(piv, Vector((0, 0, 1)), math.radians(-twist * PELVIS_TWIST)) @ P_idle)
        bpy.context.view_layer.update()
        # корпус: наклон вперёд, вправо и остаток поворота вправо (вокруг основания позвоночника)
        sh = spine.head.copy()
        yaw_m = Matrix.Rotation(math.radians(-twist), 3, 'Z')
        r = (sp.rot_about(sh, Vector((0, 0, 1)), math.radians(-twist * (1.0 - PELVIS_TWIST)))
             @ sp.rot_about(sh, yaw_m @ Vector((0, 1, 0)), math.radians(-side))
             @ sp.rot_about(sh, yaw_m @ Vector((1, 0, 0)), math.radians(lean)))
        spine.matrix = r @ spine.matrix
        bpy.context.view_layer.update()
        # ноги: левая стоит, правая шагает вправо-назад; стопы плоско
        for s in "LR":
            out = 1.0 if s == "L" else -1.0
            th, shn, ft = pb["Thigh" + s], pb["Shin" + s], pb["Foot" + s]
            off, fyaw, lift = foot_offset(s, f)
            ank = ankle_idle[s] + off + Vector((0.0, 0.0, lift))
            sp.two_bone(arm, th, shn, ank, th.head + Vector((out * 0.1, -1.0, 0.2)))
            sp.set_world_rot(ft, Matrix.Rotation(math.radians(-fyaw), 3, 'Z') @ foot_idle[s].to_3x3())
        bpy.context.view_layer.update()

        # --- правая рука ---
        w = hand_weight(f)
        on = hw_f @ GRIP_LOCAL
        # Кулак проворачивается вокруг рычага: пока створка поворачивается, рычаг (а с ним жёсткий хват)
        # разворачивается на 78°, и костяшки смотрели бы на самого Юрчика — запястье выкручено, рука не
        # достаёт. Живая рука держит рычаг так, что предплечье идёт от плеча: поворачиваем хват вокруг оси
        # рычага, чтобы костяшки смотрели от плеча (вес — с конца поворота ручки, тогда угол ещё мал).
        bar_now = hw_f @ (hw.inverted() @ bar)
        lev = (hw_f.to_3x3() @ (hw.to_3x3().inverted() @ Vector((0, 0, -1)))).normalized()
        to_bar = bar_now - pb["UpperArmR"].head
        d = (to_bar - lev * to_bar.dot(lev)).normalized()
        kn = on.to_3x3() @ k_loc
        kn = (kn - lev * kn.dot(lev)).normalized()
        roll = math.atan2(lev.dot(kn.cross(d)), kn.dot(d)) * ramp(f, F_TURN1, F_POP + 12)
        on = sp.rot_about(bar_now, lev, roll) @ on
        rolls.append(math.degrees(roll))
        if w > 0.0:
            fk = pb["HandR"].matrix.copy()
            if f <= F_GRAB:
                # подход: сначала к точке перед ручкой (спереди-снизу), потом кулак на рычаг
                near = Matrix.Translation(APPROACH) @ on
                tgt = lerp_basis(near, on, ramp(f, F_NEAR - 2, F_GRAB))
                m = lerp_basis(fk, tgt, ramp(f, F_REACH, F_NEAR))
            elif f <= F_RELEASE:
                m = on
            else:
                off = Matrix.Translation(LET_BACK) @ on
                m = lerp_basis(on, off, ramp(f, F_RELEASE, F_LET))
                m = lerp_basis(m, fk, ramp(f, F_LET - 2, F_FREE))
            sh_r = pb["UpperArmR"].head.copy()
            # локоть вниз и вправо; когда створка уходит вправо — больше назад
            pole = sh_r + Vector((-0.35, 0.15, -0.6)).lerp(Vector((-0.2, 0.25, -0.7)), sash_at(f) / OPEN_ANGLE)
            rot_m = m.to_3x3()
            sp.place_hand(arm, "R", m.translation, rot_m @ k_loc, rot_m @ b_loc, pole, forearm_share=0.65)
        # пальцы: стойка → раскрыта → кулак → раскрыта → стойка
        if f <= F_GRAB:
            wo, wg = ramp(f, F_REACH, F_NEAR), ramp(f, F_NEAR, F_GRAB)
        else:
            wo, wg = 1.0 - ramp(f, F_LET, F_FREE), 1.0 - ramp(f, F_RELEASE, F_LET - 2)
        for n in fingers:
            pb[n].matrix_basis = lerp_basis(lerp_basis(idle[n], open_f[n], wo), grip_f[n], wg)
        bpy.context.view_layer.update()

        # --- взгляд: вперёд → на ручку → за ручкой, пока ведёт створку → в открытое окно ---
        bar_now = hw_f @ (hw.inverted() @ bar)
        ahead = Vector((0.0, -1.2, 1.45))
        street = Vector((-0.32, -1.9, 1.35))
        lk = ahead.lerp(bar_now, ramp(f, 0, F_NEAR) * 0.9)
        lk = lk.lerp(street, ramp(f, F_OPEN - 18, F_FREE))
        looks.append(lk)
        sp.look(head, head.matrix.to_3x3(), lk, Vector((0.0, 0.0, 1.0)))
        if 0.0 < w:
            hand_err = (pb["HandR"].head - on.translation).length if F_GRAB <= f <= F_RELEASE else None
        else:
            hand_err = None
        report.append(hand_err)
        for b in pb:
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("rotation_quaternion", frame=f)
            b.keyframe_insert("scale", frame=f)

    # взгляд сглажен (гаусс, σ ≈ 4 кадра) — без рывков на сменах фаз
    sm = []
    for i in range(len(looks)):
        acc, n = Vector(), 0.0
        for j in range(max(0, i - 12), min(len(looks), i + 13)):
            wt = math.exp(-((j - i) / 5.5) ** 2)
            acc += looks[j] * wt
            n += wt
        sm.append(acc / n)

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
    scene.frame_start, scene.frame_end = 0, LEN
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in scene.objects:
        if o.name in ("Yurchik", "YurchikMesh") or (o.parent == arm and o.type == 'MESH'):
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

    def g(v):
        return [round(-v[0], 4), round(v[2], 4), round(v[1], 4)]
    data = {
        "fps": FPS, "frames": LEN + 1,
        "marks": {"grab": F_GRAB, "turn0": F_TURN0, "turn1": F_TURN1, "pop": F_POP, "open": F_OPEN,
                  "release": F_RELEASE, "free": F_FREE, "end": F_END},
        # створка (поворот на петлях) и ручка (вниз → вбок), градусы
        "sash": [round(v, 3) for v in sashes],
        "handle": [round(v, 3) for v in handles],
        # куда смотрит камера — пространство WindowSpot
        "look": [g(v) for v in sm],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    scene.frame_set(F_TURN1)
    errs = [e for e in report if e is not None]
    return {"glb": OUT, "json": OUT_JSON, "frames": LEN + 1, "signs": sign, "lever_at_turn1": [round(c, 2) for c in lever],
            "handle_pivot": [round(c, 3) for c in pivot], "shoulder": [round(c, 3) for c in shoulder],
            "hand_miss_max_mm": round(max(errs) * 1000.0, 1) if errs else None,
            "fist_tip_miss_mm": fist, "fist_roll_deg": [round(rolls[i]) for i in range(0, LEN + 1, 8)]}


if __name__ == "__main__":
    result = main()
