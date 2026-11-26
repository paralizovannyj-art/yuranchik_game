# Анимация «Юрчик садится за компьютер» (ChairSit) для скелета Юрчика v3 + путь кресла.
#
# Кресло стоит в узком проходе между стеной и диваном, задвинутое под стол. Обойти его нельзя, поэтому
# Юрчик садится так, как садятся в тесной комнате:
#   A  подходит к спинке сзади-слева, кладёт правую руку на левый верхний угол спинки;
#   B  откатывает кресло на себя и сам шагает назад;
#   C  толкает угол спинки вправо — кресло поворачивается сиденьем к нему, отпускает, кресло докручивается;
#   D  шагает вперёд вдоль кресла и разворачивается к нему спиной;
#   E  садится (переход стойка → сидя, как в старом SitDown);
#   F  поворачивается вместе с креслом к столу;
#   G  вытягивает ноги, упирается пятками и подтягивается к столу;
#   H  кладёт руки на стол: левая — на WASD, правая — на мышку, корпус чуть вперёд.
# Сидячие позы — свои (tools/blender/seat_poses.py), не GMod: ладони на бёдрах, пока садится и подъезжает,
# у стола — клава и мышь. Ноги всё время, пока сидит, стоят на полу (IK).
# Встаёт — тот же клип задом наперёд от конца до кадра «sit» (E): кресло остаётся отодвинутым и повёрнутым.
# Если кресло уже отодвинуто, посадка начинается сразу с кадра «sit».
#
# Всё считается в пространстве «места у компа» — маркер PcSeat/SitSpot в stairwell.tscn: узел игрока на всё
# время посадки стоит в нём и не двигается, всё движение — в костях (таз). В Blender это пространство
# арматуры: вперёд (к столу) −Y, вправо −X, вверх Z. В Godot (модель повёрнута на 180°): x = −X, y = Z, z = Y.
#
# Ноги и правая рука — IK (цели-пустышки), потом всё запекается в обычные ключи (nla.bake) и уходит в glb.
# Путь кресла и точка, куда смотрит камера, — покадрово в assets/animations/sit/chair_sit.json (pc_seat.gd).
#
# Запуск — только в живом Blender через Blender MCP (правило проекта):
#   exec(open(r"<проект>/tools/blender/build_chair_sit.py", encoding="utf-8").read(), {"__name__": "__main__"})
# Скрипт строит всё в своей сцене ChairSit (другие сцены не трогает) и пишет
# assets/animations/sit/yurchik_sit.glb (клип ChairSit и клипы-позы у стола, см. EXTRA) и
# assets/animations/sit/chair_sit.json.
import bpy, os, sys, math, json, importlib
from mathutils import Matrix, Vector, Quaternion

ROOT = r"C:\Users\mrs\Documents\yuranchik_game"
SRC = os.path.join(ROOT, "assets", "animations", "gmod", "yurchik_gmod.glb")
CHAIR = os.path.join(ROOT, "assets", "models", "gaming_chair.gltf")
OUT_DIR = os.path.join(ROOT, "assets", "animations", "sit")
OUT = os.path.join(OUT_DIR, "yurchik_sit.glb")
OUT_JSON = os.path.join(OUT_DIR, "chair_sit.json")
SCENE = "ChairSit"
FPS = 30

SIT_BACK = 0.35      # м — таз уходит назад от места, где стоял (= от SitSpot до центра кресла у стола)

# --- кресло (центр — газлифт; поворот a: 0 — сиденьем к столу, + — против часовой сверху, то есть влево) ---
C_REST = (0.0, 0.07, -4.0)     # задвинуто под стол (подлокотники перед краем стола)
C_OUT = (0.0, 0.65, 90.0)      # откачено и повёрнуто сиденьем влево (к дивану)
C_FINAL = (0.0, SIT_BACK, 0.0)  # сидит у стола: центр кресла на SIT_BACK позади SitSpot
# Ладонь лежит на верхнем крае спинки у левого угла (координаты кресла: вперёд +Y, верх спинки z ≈ 1.30–1.38).
# Кисть: ладонь вниз на спинку, пальцы через верх вперёд и чуть вниз. Запястье — за краем, на ширину ладони
# назад от точки хвата и на толщину кисти выше.
GRAB_PALM = Vector((-0.24, -0.43, 1.36))   # середина ладони (на коже кресла)
GRAB_FINGERS = Vector((0.0, 0.89, -0.45)).normalized()   # пальцы — свешиваются через верх вперёд-вниз
GRAB_UP = Vector((0.0, 0.0, 1.0))           # тыльная сторона кисти — вверх
PALM_LEN = 0.075                            # м — от запястья до середины ладони
TWIST_FOREARM = 0.70                        # доля поворота ладони, которую берёт предплечье (остальное — запястье)
ELBOW_POLE_ANGLE = 90.0                     # угол полюса IK руки: при −90 локоть задирался выше плеча
WRIST_MAX = 60.0                            # градусы — сильнее запястье не сгибается (дальше кисть идёт за предплечьем)
FOREARM_TWIST_MAX = 95.0                    # пронация предплечья не больше (живая рука ~90°)
WRIST_TWIST_MAX = 30.0                      # кручение кисти относительно предплечья не больше: лишнее берёт предплечье
SPIN_HAND_FOLLOW = 0.35                     # пока крутит кресло, кисть поворачивается только на эту долю поворота спинки

# --- кадры ---
# grab — рука на спинке; pull — кресло поехало; spin — начал крутить; release — отпустил; sit — стоит перед
# креслом, начинает садиться; seated — сел боком; swivel — повернулся к столу; lift — руки над краем стола;
# hover — кисти зависли над клавой и мышью;
# desk — руки на клаве и мышке; end — конец клипа (поза desk)
F_GRAB, F_PULL, F_SPIN, F_RELEASE, F_SIT, F_SEATED, F_SWIVEL = 14, 16, 36, 50, 86, 134, 162
F_LIFT0, F_LIFT, F_DESK, F_END = 202, 216, 234, 240
F_HOVER = 228        # кисти зависли над клавой и мышью (дальше — ложатся на них)
LEN = F_END
F_FREE = 72          # рука совсем ушла со спинки (отпускает плавно, F_RELEASE–F_FREE)


def sample(arm, action):
    arm.animation_data.action = bpy.data.actions[action]
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    return {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}


def lerp_basis(a, b, t):
    la, ra, sa = a.decompose()
    lb, rb, sb = b.decompose()
    return Matrix.LocRotScale(la.lerp(lb, t), ra.slerp(rb, t), sa.lerp(sb, t))


def smooth(x):
    # smootherstep: скорость и ускорение на концах — ноль, фазы стыкуются без толчка
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


def mono3(keys, f):
    return tuple(mono([(k[0], k[1][c]) for k in keys], f) for c in range(len(keys[0][1])))


def body(x, y, yaw):
    """Место тела: стоит в (x, y), повёрнут на yaw° (0 — лицом к столу, вдоль −Y)."""
    return Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')


def chair_mat(x, y, a, dz=0.0):
    # кресло в своём файле смотрит вдоль +Y, а «к столу» — это −Y: поворот 180° + a
    return Matrix.Translation((x, y, dz)) @ Matrix.Rotation(math.radians(180.0 + a), 4, 'Z')


# ----------------------------------------------------------------------------- ключи движения
# место тела (x, y, yaw) в фазах A–D (стоит/шагает)
BODY_KEYS = [
    (0, (0.36, 1.02, 0.0)),
    (13, (0.36, 1.02, 0.0)),          # вес назад чуть раньше, чем поедет кресло: таз трогается без рывка
    (27, (0.37, 1.17, 0.0)),
    (F_SPIN, (0.38, 1.32, 0.0)),
    (F_RELEASE, (0.35, 1.38, -14.0)),
    (57, (0.35, 1.29, 2.0)),
    (67, (0.36, 1.00, 42.0)),
    (77, (0.355, 0.735, 80.0)),
    (85, (0.35, 0.65, 90.0)),          # подходит и останавливается мягко, прямо перед посадкой
]
# шаги: стопа (L/R), кадр отрыва, кадр постановки, куда (место тела, под которое встаёт стопа)
STEPS = {
    "L": [(24, 33, (0.38, 1.32, 0.0)), (42, 50, (0.35, 1.39, -12.0)), (53, 63, (0.36, 1.10, 25.0)),
          (69, 79, (0.355, 0.73, 80.0))],
    "R": [(16, 25, (0.37, 1.19, 0.0)), (31, 38, (0.38, 1.32, 0.0)), (38, 46, (0.34, 1.37, -14.0)),
          (60, 70, (0.36, 0.90, 55.0)), (77, 86, (0.35, 0.65, 90.0))],
}
FOOT_START = (0.36, 1.02, 0.0)
STEP_LIFT = 0.07

# кресло (x, y, a)
CHAIR_KEYS = [
    (0, C_REST),
    (F_PULL, C_REST),
    (F_SPIN, (0.0, 0.42, 5.0)),
    (F_RELEASE, (0.0, 0.53, 38.0)),
    (60, (0.0, 0.62, 74.0)),
    (70, C_OUT),
]
# ключи посадки (из старого SitDown): (кадр от F_SIT, доля поз стойка→сидя, вниз, назад, наклон корпуса °)
SIT_KEYS = [
    (0, 0.00, 0.00, 0.00, 0.0),
    (10, 0.18, 0.10, 0.05, 14.0),
    (22, 0.55, 0.46, 0.45, 30.0),
    (31, 0.90, 0.86, 0.88, 22.0),
    (39, 0.99, 0.985, 0.99, 10.0),
    (48, 1.00, 1.00, 1.00, 0.0),
]
F_LAND = F_SIT + 36        # таз опустился на подушку — кресло проседает
# подтягивание к столу (G)
F_REACH0, F_REACH1, F_PULL0, F_PULL1, F_SETTLE1 = 164, 173, 174, 196, 206
SOFT_LEG = (0.965, 0.025)                   # доли длины ноги: с какого расстояния бедро–щиколотка нога «мягчеет» и запас до прямой
HEEL_REACH = 0.13          # м — насколько вытягивает ноги вперёд, прежде чем упереться пятками


# Растяжение времени (после запекания): (с кадра, по кадр, во сколько раз медленнее). Переходы плавные (±WARP_EDGE),
# поэтому скорость нигде не скачет. Все кадры выше — «кадры замысла»; в клипе и JSON — уже растянутые.
WARP = [(-8, 16, 1.4), (44, 72, 1.3), (172, 198, 1.25)]
WARP_EDGE = 5.0


def warp_rate(d):
    r = 1.0
    for a, b, k in WARP:
        r += (k - 1.0) * ramp(d, a - WARP_EDGE, a + WARP_EDGE) * (1.0 - ramp(d, b - WARP_EDGE, b + WARP_EDGE))
    return r


_WARP_STEP = 0.01


def _warp_table():
    o, t = 0.0, [0.0]
    n = int(LEN / _WARP_STEP)
    for i in range(n):
        d = i * _WARP_STEP
        o += 0.5 * (warp_rate(d) + warp_rate(d + _WARP_STEP)) * _WARP_STEP
        t.append(o)
    return t


def warp_out(d):
    """Кадр замысла → кадр клипа."""
    t = _warp_table() if "_WT" not in globals() else globals()["_WT"]
    globals()["_WT"] = t
    x = min(max(d / _WARP_STEP, 0.0), len(t) - 1.0)
    i = min(int(x), len(t) - 2)
    return t[i] + (t[i + 1] - t[i]) * (x - i)


def warp_frames():
    """Для каждого кадра клипа — кадр замысла (дробный)."""
    t = _warp_table()
    globals()["_WT"] = t
    total = t[-1]
    nout = int(round(total))
    res, j = [], 0
    for o in range(nout + 1):
        target = o * total / nout
        while j < len(t) - 2 and t[j + 1] < target:
            j += 1
        u = (target - t[j]) / (t[j + 1] - t[j]) if t[j + 1] > t[j] else 0.0
        res.append(min((j + u) * _WARP_STEP, float(LEN)))
    return res


def lerp_seq(seq, d):
    i = min(int(d), len(seq) - 2)
    u = d - i
    a, b = seq[i], seq[i + 1]
    if isinstance(a, Vector):
        return a.lerp(b, u)
    return tuple(a[c] + (b[c] - a[c]) * u for c in range(len(a)))


def _fcurves(obj):
    ad = obj.animation_data
    act = ad.action
    try:
        from bpy_extras.anim_utils import action_get_channelbag_for_slot
        cb = action_get_channelbag_for_slot(act, ad.action_slot)
        return list(cb.fcurves) if cb else []
    except Exception:
        return list(act.fcurves)


def retime(scene, objs):
    """Пересэмплирует ключи объектов по растяжению времени; возвращает кадры замысла для кадров клипа."""
    dmap = warp_frames()
    n = len(dmap)
    for obj in objs:
        if not obj.animation_data or not obj.animation_data.action:
            continue
        for fc in _fcurves(obj):
            vals = [fc.evaluate(d) for d in dmap]
            fc.keyframe_points.clear()
            fc.keyframe_points.add(n)
            co = []
            for o, v in enumerate(vals):
                co += [float(o), v]
            fc.keyframe_points.foreach_set("co", co)
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
            fc.update()
    scene.frame_start, scene.frame_end = 0, n - 1
    return dmap


def chair_at(f):
    """(x, y, a, dz) кресла на кадре f."""
    if f <= F_SEATED:
        x, y, a = mono3(CHAIR_KEYS, f)
    elif f <= F_SWIVEL:
        x, y, a = C_OUT[0], C_OUT[1], C_OUT[2] * (1.0 - ramp(f, F_SEATED, F_SWIVEL))
    else:
        u = ramp(f, F_PULL0, F_PULL1)
        x, y, a = 0.0, C_OUT[1] + (C_FINAL[1] - C_OUT[1]) * u, 0.0
    dz = -0.018 * math.sin(math.pi * min(max((f - F_LAND + 4) / 16.0, 0.0), 1.0)) ** 2   # проседает под ним без толчка
    return x, y, a, dz


def seat_body(f):
    """Место тела, пока сидит (E–G): впереди центра кресла на SIT_BACK, повёрнуто вместе с креслом."""
    x, y, a, _ = chair_at(f)
    return Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(a), 4, 'Z') @ Matrix.Translation((0.0, -SIT_BACK, 0.0))


def foot_place(foot, f):
    """Матрица «места тела» под стопой и подъём стопы над полом (фазы A–D)."""
    prev = FOOT_START
    for lift, land, to in STEPS[foot]:
        if f < lift:
            return body(*prev), 0.0
        if f < land:
            u = (f - lift) / float(land - lift)
            s = smooth(u)
            p = tuple(prev[i] + (to[i] - prev[i]) * s for i in range(3))
            return body(*p), STEP_LIFT * math.sin(math.pi * u) ** 2
        prev = to
    return body(*prev), 0.0


def hand_weight(f):
    """Насколько правая рука на спинке: тянется (кадры 1–F_GRAB), держит, отпускает (F_RELEASE–F_FREE)."""
    if f >= F_FREE:
        return 0.0
    return ramp(f, 1, F_GRAB) * (1.0 - ramp(f, F_RELEASE, F_FREE))


def fix_hand(scene, arm, hand_rots):
    """Кисть на спинке после запекания IK. IK ставит запястье в точку, но ладонь остаётся как у висящей руки —
    ребром к спинке. Нужный поворот ладони вокруг оси предплечья делится: TWIST_FOREARM берёт предплечье
    (пронация, как у живой руки), остальное — запястье; изгиб запястья не больше WRIST_MAX, кручение кисти
    не больше WRIST_TWIST_MAX. Оборот считается от полного захвата и разворачивается по кадрам без перескока
    через ±180°, потом умножается на вес захвата; кручение предплечья сглажено по времени."""
    pb = arm.pose.bones
    fore, hand = pb["ForearmR"], pb["HandR"]
    frames = [f for f in sorted(hand_rots) if hand_weight(f) > 0.0]

    def raw_twist(f):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        cur = hand.matrix.to_3x3()
        axis = (fore.tail - fore.head).normalized()
        delta = hand_rots[f].to_quaternion() @ cur.to_quaternion().inverted()
        v = Vector((delta.x, delta.y, delta.z))
        t = 2.0 * math.atan2(v.dot(axis), delta.w)
        return (t + math.pi) % (2.0 * math.pi) - math.pi

    # оборот ладони вокруг предплечья без перескоков: на полном захвате — в сторону пронации (−80…+280°),
    # дальше и раньше по кадрам — ближайший к соседнему кадру оборот (иначе на подходе руки кисть щёлкает на 150°)
    raw = {f: raw_twist(f) for f in frames}
    full = {}
    seed = min(frames, key=lambda f: abs(f - F_GRAB))
    t = raw[seed]
    if t < math.radians(-80.0):
        t += 2.0 * math.pi
    full[seed] = t
    i0 = frames.index(seed)
    for order in (frames[i0 + 1:], list(reversed(frames[:i0]))):
        prev = full[seed]
        for f in order:
            t = raw[f]
            t += 2.0 * math.pi * round((prev - t) / (2.0 * math.pi))
            full[f] = t
            prev = t

    rest_rel = (fore.bone.matrix_local.inverted() @ hand.bone.matrix_local).to_quaternion()

    def tilt(q, axis):
        return math.degrees((q.to_matrix() @ Vector((0, 1, 0))).angle(axis))

    goals = {}
    for f in frames:
        want = hand_rots[f].to_quaternion()
        w = hand_weight(f)
        scene.frame_set(f)
        bpy.context.view_layer.update()
        axis = (fore.tail - fore.head).normalized()
        ang = max(min(full[f] * TWIST_FOREARM, math.radians(85.0)), math.radians(-60.0)) * w
        piv = fore.head.copy()
        fore.matrix = (Matrix.Translation(piv) @ Matrix.Rotation(ang, 4, axis) @ Matrix.Translation(-piv)) @ fore.matrix
        bpy.context.view_layer.update()
        cur = hand.matrix.to_quaternion()
        axis = (fore.tail - fore.head).normalized()
        # остаток до нужной ладони = изгиб (swing) × оборот вокруг предплечья (twist). Оборот берётся
        # с развёрнутым углом full − ang, а не короткой дугой slerp: та при остатке около 180° на подходе
        # руки меняет сторону, и кисть щёлкает на 150° за кадр
        r = want @ cur.inverted()
        rv = Vector((r.x, r.y, r.z))
        tw_short = 2.0 * math.atan2(rv.dot(axis), r.w)
        swing = r @ Quaternion(axis, tw_short).inverted()
        rem = full[f] - ang
        ident = Quaternion()

        def goal(k):
            return ident.slerp(swing, k) @ Quaternion(axis, rem * k) @ cur

        # запястье не больше WRIST_MAX от линии предплечья: доля пути k ищется делением пополам —
        # плавно меняется от кадра к кадру (ступенчатый поиск давал рывки)
        k = w
        if tilt(goal(k), axis) > WRIST_MAX:
            lo, hi = 0.0, k
            for _ in range(20):
                mid = 0.5 * (lo + hi)
                if tilt(goal(mid), axis) > WRIST_MAX:
                    hi = mid
                else:
                    lo = mid
            k = lo
        gq = goal(k)
        # кисть сама почти не крутится (кручение — это предплечье): лишнее сверх WRIST_TWIST_MAX
        # доворачивает предплечье вокруг своей оси, кисть в мире остаётся там же
        rel = rest_rel.inverted() @ (fore.matrix.to_quaternion().inverted() @ gq)
        tw = 2.0 * math.atan2(rel.y, rel.w)
        tw = (tw + math.pi) % (2.0 * math.pi) - math.pi
        lim = math.radians(WRIST_TWIST_MAX)
        extra = tw - max(min(tw, lim), -lim)
        if abs(extra) > 1e-6:
            fore.matrix = (Matrix.Translation(piv) @ Matrix.Rotation(extra, 4, axis) @ Matrix.Translation(-piv)) @ fore.matrix
            bpy.context.view_layer.update()
        m = gq.to_matrix().to_4x4()
        m.translation = hand.head.copy()
        hand.matrix = m
        bpy.context.view_layer.update()
        goals[f] = m.copy()
        for b in (fore, hand):
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("rotation_quaternion", frame=f)

    # кручение предплечья сглаживается по времени (σ 2 кадра) и не больше FOREARM_TWIST_MAX:
    # на подходе руки поза IK сама подкручивает руку, и без этого предплечье на кадр уходит за 100°.
    # Кисть в мире остаётся, где была
    def split(q):
        tw = Quaternion((q.w, 0.0, q.y, 0.0)).normalized()
        a = 2.0 * math.atan2(tw.y, tw.w)
        return q @ tw.inverted(), (a + math.pi) % (2.0 * math.pi) - math.pi

    parts = {}
    for f in frames:
        scene.frame_set(f)
        parts[f] = split(fore.rotation_quaternion.copy())
    lim = math.radians(FOREARM_TWIST_MAX)
    for f in frames:
        num = den = 0.0
        for g in range(f - 6, f + 7):
            if g in parts:
                wt = math.exp(-0.5 * ((g - f) / 2.0) ** 2)
                num += wt * parts[g][1]; den += wt
        a = max(min(num / den, lim), -lim)
        scene.frame_set(f)
        fore.rotation_quaternion = parts[f][0] @ Quaternion(Vector((0.0, 1.0, 0.0)), a)
        bpy.context.view_layer.update()
        hand.matrix = goals[f]
        bpy.context.view_layer.update()
        for b in (fore, hand):
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("rotation_quaternion", frame=f)


ARM_BONES = {"%s%s" % (n, side) for side in "LR" for n in ("UpperArm", "Forearm", "Hand")} | {
    "%s%s%d" % (f, side, i) for side in "LR" for f in ("Index", "Middle", "Ring", "Pinky", "Thumb") for i in (1, 2, 3)}
ARM_KEYS = [(0, 0.0), (6, 0.3), (14, 0.82), (22, 1.0)]   # (кадр от F_SIT, доля стойка → ладони на бёдрах)
MONITOR = Vector((-0.02, -0.5, 1.03))   # середина экрана (пространство арматуры у стола)
# клипы-позы для живых рук в Godot (yurchik_anim.gd): имя клипа → поза seat_poses.py
EXTRA = {"DeskMouseC": "desk", "DeskMouseL": "mouse_l", "DeskMouseR": "mouse_r", "DeskMouseF": "mouse_f",
         "DeskMouseB": "mouse_b", "DeskMouseFR": "mouse_fr", "DeskMouseFL": "mouse_fl", "DeskMouseBR": "mouse_br",
         "DeskMouseBL": "mouse_bl", "DeskClick": "click", "DeskTapIndex": "tap_index", "DeskTapMiddle": "tap_middle",
         "DeskTapRing": "tap_ring", "DeskTapThumb": "tap_thumb"}
# PowerReach: цепочка поз и ключи (кадр, место на цепочке); на 3 — палец на кнопке
# (hover_r — правая приподнялась над мышью, power_back — кисть выше края стола, пальцы ещё вперёд: туда и обратно
# рука идёт через них, иначе пальцы на переходах проходят сквозь мышь и столешницу)
P_CHAIN = ["desk", "hover_r", "power_back", "power_lift", "power_mid", "power", "power_mid", "power_back", "hover_r",
           "desk"]
P_KEYS = [(0, 0.0), (5, 1.0), (10, 2.0), (16, 3.0), (26, 4.0), (36, 5.0), (46, 5.0), (58, 6.0), (70, 7.0), (77, 8.0),
          (82, 9.0)]
P_PRESS = 38


def pose_action(arm, name, frames):
    """Действие с позами по кадрам (frames — список {кость: matrix_basis})."""
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    for f, pose in enumerate(frames):
        for b in arm.pose.bones:
            b.matrix_basis = pose[b.name]
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("rotation_quaternion", frame=f)
            b.keyframe_insert("scale", frame=f)
    arm.animation_data.action = None
    return act


def power_reach(arm, poses):
    """Кадры клипа PowerReach (у стола → кнопка → у стола) и точки взгляда. Место на цепочке поз — монотонный
    сплайн по P_KEYS (на промежуточных позах не останавливается), потом сглаживание (гаусс, σ 2.5 кадра)."""
    import seat_poses
    n = P_KEYS[-1][0] + 1
    raw = []
    for f in range(n):
        p = mono(P_KEYS, f)
        i = min(int(p), len(P_CHAIN) - 2)
        a, b = poses[P_CHAIN[i]], poses[P_CHAIN[i + 1]]
        raw.append({k: lerp_basis(a[k], b[k], p - i) for k in a})
    pad = 8
    seq = [raw[0]] * pad + raw + [raw[-1]] * pad
    out = []
    for f in range(n):
        c = f + pad
        res = {}
        for k in raw[0]:
            loc, q0, acc_q, acc_l, wsum = Vector(), None, Quaternion((0, 0, 0, 0)), Vector(), 0.0
            for j in range(c - pad, c + pad + 1):
                w = math.exp(-0.5 * ((j - c) / 2.5) ** 2)
                l, q, _ = seq[j][k].decompose()
                if q0 is None:
                    q0 = q
                if q.dot(q0) < 0.0:
                    q = -q
                acc_q = Quaternion((acc_q.w + q.w * w, acc_q.x + q.x * w, acc_q.y + q.y * w, acc_q.z + q.z * w))
                acc_l += l * w
                wsum += w
            acc_q.normalize()
            res[k] = Matrix.LocRotScale(acc_l / wsum, acc_q, Vector((1, 1, 1)))
        out.append(res)
    out[0], out[-1] = poses["desk"], poses["desk"]
    # взгляд: монитор → кнопка → монитор (по месту на цепочке)
    looks = []
    for f in range(n):
        p = mono(P_KEYS, f)
        p = p if p <= 5.0 else 10.0 - p
        p = max(0.0, p - 2.0)            # hover_r и power_back — ещё смотрит в монитор; кнопка — на 3
        looks.append(MONITOR.lerp(seat_poses.BUTTON + Vector((0, 0.03, 0.02)), smooth((p - 0.5) / 2.0)))
    return out, looks


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
    for a in list(bpy.data.actions):    # повторный запуск — с чистого листа
        bpy.data.actions.remove(a)
    bpy.ops.import_scene.gltf(filepath=SRC)
    arm = scene.objects["Yurchik"]
    bpy.ops.import_scene.gltf(filepath=CHAIR)
    chair = scene.objects["GamingChair_nocol"]
    chair.rotation_mode = 'XYZ'
    for o in list(scene.objects):
        if o.name.startswith("GamingChairCol") or o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o, do_unlink=True)
    scene.render.fps = FPS
    idle = sample(arm, "Idle")
    arm.animation_data.action = None
    # свои сидячие позы (seat_poses.py): rest — ладони на бёдрах, lift — руки над краем стола,
    # desk — клава и мышь; остальные — клипы-позы для Godot (EXTRA) и PowerReach
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals()
                    else os.path.join(ROOT, "tools", "blender"))
    import seat_poses
    importlib.reload(seat_poses)
    poses, pose_report = seat_poses.build(arm, idle)
    sit = poses["rest"]

    pb = arm.pose.bones
    pelvis = pb["Pelvis"]
    p_rest = pelvis.bone.matrix_local
    # таз в пространстве тела: стойка и сидя (поза rest уже на подушке, в пространстве «тела у стола»)
    P_idle = p_rest @ idle["Pelvis"]
    P_sit = p_rest @ sit["Pelvis"]
    li, ri, _ = P_idle.decompose()
    ls, rs, _ = P_sit.decompose()

    # поза стойки в пространстве арматуры: стопы и запястье (для целей IK)
    for b in pb:
        b.matrix_basis = idle[b.name]
    bpy.context.view_layer.update()
    foot_idle = {s: pb["Foot" + s].matrix.copy() for s in "LR"}
    shoulder_r = pb["UpperArmR"].head.copy()
    # поза сидя (тело в начале координат): стопы — для подтягивания к столу
    for b in pb:
        b.matrix_basis = sit[b.name]
    pelvis.matrix = P_sit
    bpy.context.view_layer.update()
    foot_sit = {s: pb["Foot" + s].matrix.copy() for s in "LR"}
    seat_poses.apply(arm, poses["desk"])
    foot_desk = {s: pb["Foot" + s].matrix.copy() for s in "LR"}

    # --- цели IK ---
    def empty(name):
        e = bpy.data.objects.new(name, None)
        e.empty_display_size = 0.08
        scene.collection.objects.link(e)
        return e
    tg = {s: empty("FootTgt" + s) for s in "LR"}
    pole = {s: empty("KneePole" + s) for s in "LR"}
    hand_t = empty("HandTgtR")
    elbow = empty("ElbowPoleR")
    cons = []
    for s in "LR":
        c = pb["Shin" + s].constraints.new('IK')
        c.target, c.pole_target, c.chain_count, c.pole_angle = tg[s], pole[s], 2, math.radians(-90)
        c2 = pb["Foot" + s].constraints.new('COPY_ROTATION')
        c2.target = tg[s]
        cons += [c, c2]
    ch = pb["ForearmR"].constraints.new('IK')
    ch.target, ch.pole_target, ch.chain_count, ch.pole_angle = hand_t, elbow, 2, math.radians(ELBOW_POLE_ANGLE)
    leg_cons = [c for c in cons]
    leg_len = {s: pb["Thigh" + s].length + pb["Shin" + s].length for s in "LR"}
    foot_len = pb["FootL"].length

    def soft_leg(m, hip, L, fwd):
        """Мягкий предел длины ноги: колено никогда не выпрямляется до упора. Иначе нога-опора, от которой
        ушло тело, вытягивается в струну, и на отрыве колено щёлкает (5° → 24° за кадр). Лишнее
        расстояние поднимает щиколотку к бедру (пятка отрывается), стопа наклоняется носком вниз."""
        to = m.translation - hip
        d = to.length
        L0, band = SOFT_LEG[0] * L, SOFT_LEG[1] * L
        if d <= L0:
            return m
        d2 = L0 + band * (1.0 - math.exp(-(d - L0) / band))
        new = hip + to.normalized() * d2
        rise = (new - m.translation).length
        tilt = math.asin(min(rise / foot_len, 0.9))
        side = Vector((0, 0, 1)).cross(fwd).normalized()
        r = Matrix.Translation(new) @ Matrix.Rotation(tilt, 4, side) @ Matrix.Translation(-m.translation)
        return r @ m
    hand_cons = [ch]

    # Кисть на спинке. Оси кости кисти: Y — к пальцам; «тыл кисти» — та ось, что в покое смотрит наружу
    # от бедра (для правой руки −X арматуры). По ним строим нужный поворот кисти в мире.
    hb = pb["HandR"].bone.matrix_local.to_3x3()
    back_local = (hb.inverted() @ Vector((-1.0, 0.0, 0.0))).normalized()
    back_local = (back_local - Vector((0, 1, 0)) * back_local.y).normalized()

    def hand_rot_on_chair(cm):
        y = (cm.to_3x3() @ GRAB_FINGERS).normalized()
        up = cm.to_3x3() @ GRAB_UP
        b = (up - y * up.dot(y)).normalized()                   # тыл кисти — вверх, поперёк пальцев
        # мировой базис (x, y=пальцы, z) такой, что локальная back_local уходит в b
        lz = back_local
        lx = Vector((0, 1, 0)).cross(lz).normalized()
        wz = b
        wx = y.cross(wz).normalized()
        local = Matrix((lx, Vector((0, 1, 0)), lz)).transposed()
        world = Matrix((wx, y, wz)).transposed()
        return world @ local.inverted()

    def hand_on_chair(cm, cm_rot):
        rot = hand_rot_on_chair(cm_rot)
        palm = cm @ GRAB_PALM
        wrist = palm - (rot @ Vector((0, 1, 0))) * PALM_LEN + (rot @ back_local) * 0.02
        m = rot.to_4x4()
        m.translation = wrist
        return m

    hand_rots = {}
    act_fk = bpy.data.actions.new("ChairSitFK")
    arm.animation_data.action = act_fk
    looks = []
    chairs = []
    for f in range(0, LEN + 1):
        scene.frame_set(f)
        cx, cy, ca, cdz = chair_at(f)
        cm = chair_mat(cx, cy, ca, cdz)
        chair.matrix_world = cm
        chair.keyframe_insert("location", frame=f)
        chair.keyframe_insert("rotation_euler", frame=f)
        chairs.append((cx, cy, ca, cdz))

        # --- тело ---
        if f < F_SIT:
            B = body(*mono3(BODY_KEYS, f))
            t_fk, down, back, bend = 0.0, 0.0, 0.0, 0.0
            # наклон к спинке, пока тянет и крутит кресло
            bend = 10.0 * ramp(f, 0, F_GRAB) * (1.0 - ramp(f, F_RELEASE, 62))
        else:
            B = body(0.35, 0.65, 90.0) if f <= F_SEATED else seat_body(f)
            k = min(f - F_SIT, 48)
            t_fk, down, back, bend = [mono([(kk[0], kk[j]) for kk in SIT_KEYS], k) for j in range(1, 5)]
            if f > F_SEATED:
                # подтягивается: корпус чуть вперёд, когда тянет ногами
                bend += 7.0 * math.sin(math.pi * ramp(f, F_REACH0, F_PULL1))
        # руки садятся раньше тела: ладони уже на бёдрах, пока таз опускается, — иначе висящие руки
        # проходят сквозь подлокотники
        t_arm = mono(ARM_KEYS, f - F_SIT) if f >= F_SIT else 0.0
        for b in pb:
            b.matrix_basis = lerp_basis(idle[b.name], sit[b.name], t_arm if b.name in ARM_BONES else t_fk)
        loc = Vector((li.x + (ls.x - li.x) * t_fk, li.y + (ls.y - li.y) * back, li.z + (ls.z - li.z) * down))
        pelvis.matrix = B @ Matrix.LocRotScale(loc, ri.slerp(rs, t_fk), Vector((1, 1, 1)))
        if f > F_LIFT0:
            # руки на стол: сначала вверх перед собой (lift), потом вперёд, зависли над клавой и мышью (hover),
            # и ложатся на них (desk); корпус наклоняется к столу, таз чуть вперёд по подушке
            w1, w2 = ramp(f, F_LIFT0, F_LIFT), ramp(f, F_LIFT, F_HOVER)   # вперёд — когда пальцы уже над столом
            w3 = ramp(f, F_HOVER - 4, F_DESK)
            for b in pb:
                b.matrix_basis = lerp_basis(lerp_basis(lerp_basis(sit[b.name], poses["lift"][b.name], w1),
                                                       poses["hover"][b.name], w2), poses["desk"][b.name], w3)
            pelvis.matrix = B @ (p_rest @ pelvis.matrix_basis)
        bpy.context.view_layer.update()
        if bend != 0.0:
            spine = pb["Spine"]
            pivot = spine.head.copy()
            axis = B.to_3x3() @ Vector((1, 0, 0))
            r = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(bend), 4, axis) @ Matrix.Translation(-pivot)
            spine.matrix = r @ spine.matrix
            bpy.context.view_layer.update()
        for b in pb:
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("rotation_quaternion", frame=f)
            b.keyframe_insert("scale", frame=f)

        # --- ноги ---
        if f < F_SIT:
            leg_w = 1.0
            for s in "LR":
                place, lift = foot_place(s, f)
                m = place @ foot_idle[s]
                m = Matrix.Translation((0, 0, lift)) @ m
                m = soft_leg(m, arm.matrix_world @ pb["Thigh" + s].head, leg_len[s], place.to_3x3() @ Vector((0, -1, 0)))
                tg[s].matrix_world = m
                fwd = place.to_3x3() @ Vector((0, -1, 0))
                pole[s].matrix_world = Matrix.Translation(m.translation + fwd * 0.8 + Vector((0, 0, 0.5)))
        else:
            # сидит: стопы на полу всё время (IK). К концу клипа IK уходит — остаётся поза desk, в ней стопы там же
            leg_w = 1.0 - ramp(f, F_DESK, F_END)
            for s in "LR":
                Bs = B if f <= F_SEATED else seat_body(f)
                fwd_b = Bs.to_3x3() @ Vector((0, -1, 0))
                if f < F_REACH0 - 4:
                    stand = foot_place(s, F_SIT)[0] @ foot_idle[s]
                    seated = Bs @ foot_sit[s]
                    if f < F_LAND - 4:
                        m = stand                          # садится: стопы стоят, где стоял
                    elif f < F_LAND + 14:
                        # сел — переставляет ноги в посадку (чуть приподнимая)
                        u = ramp(f, F_LAND - 4, F_LAND + 14)
                        m = Matrix.Translation((0, 0, 0.02 * math.sin(math.pi * u) ** 2)) @ lerp_basis(stand, seated, u)
                    elif f < F_SWIVEL:
                        # крутится к столу вместе с креслом — ноги чуть над полом
                        u = (f - (F_LAND + 14)) / float(F_SWIVEL - (F_LAND + 14))
                        m = Matrix.Translation((0, 0, 0.03 * math.sin(math.pi * u) ** 2)) @ seated
                    else:
                        m = seated
                elif f < F_PULL0:
                    # вытягивает ноги вперёд, пятки чуть над полом
                    u = ramp(f, F_REACH0, F_REACH1)
                    base = seat_body(f) @ foot_sit[s]
                    m = Matrix.Translation(fwd_b * HEEL_REACH * u + Vector((0, 0, 0.03 * math.sin(math.pi * u) ** 2))) @ base
                elif f < F_PULL1:
                    # пятки стоят, кресло едет к ним
                    base = seat_body(F_PULL0) @ foot_sit[s]
                    m = Matrix.Translation(fwd_b * HEEL_REACH) @ base
                else:
                    # ноги возвращаются в обычную посадку
                    u = ramp(f, F_PULL1, F_SETTLE1)
                    planted = seat_body(F_PULL0) @ foot_sit[s]
                    planted = Matrix.Translation(fwd_b * HEEL_REACH) @ planted
                    rest = seat_body(f) @ foot_sit[s]
                    m = lerp_basis(planted, rest, u)
                    m = Matrix.Translation((0, 0, 0.025 * math.sin(math.pi * u) ** 2)) @ m
                if f > F_LIFT0:
                    # у стола — стопы чуть дальше под стол (поза desk)
                    u = ramp(f, F_LIFT0, F_DESK)
                    m = Matrix.Translation((0, 0, 0.015 * math.sin(math.pi * u) ** 2)) @ lerp_basis(m, Bs @ foot_desk[s], u)
                tg[s].matrix_world = m
                out = 1.0 if s == "L" else -1.0
                side = Bs.to_3x3() @ Vector((out, 0, 0))
                k = ramp(f, F_SIT, F_SIT + 20)           # колени чуть врозь, как сидят (от стойки — плавно)
                pole[s].matrix_world = Matrix.Translation(m.translation + fwd_b * 0.8 + side * 0.15 * k
                                                          + Vector((0, 0, 0.5 + 0.1 * k)))
        for c in leg_cons:
            c.influence = leg_w
            c.keyframe_insert("influence", frame=f)
        for s in "LR":
            tg[s].keyframe_insert("location", frame=f)
            tg[s].keyframe_insert("rotation_euler", frame=f)
            pole[s].keyframe_insert("location", frame=f)

        # --- правая рука на спинке ---
        if f < F_FREE:
            hand_w = hand_weight(f)
            fh = min(f, F_RELEASE)
            ch_now = chairs[fh]
            # пока крутит кресло, кисть поворачивается не вся вместе со спинкой: ладонь едет по краю
            a_spin = chair_at(F_SPIN)[2]
            a_hand = ch_now[2] if fh <= F_SPIN else a_spin + SPIN_HAND_FOLLOW * (ch_now[2] - a_spin)
            hm = hand_on_chair(chair_mat(*ch_now), chair_mat(ch_now[0], ch_now[1], a_hand, ch_now[3]))
            if f > F_RELEASE:
                # отпустил: цель руки плавно переезжает со спинки туда, где рука висит сама (поза без IK).
                # Иначе тело уже развернулось, точка на спинке оказывается за спиной, и IK переворачивает локоть
                for c in hand_cons:
                    c.influence = 0.0
                bpy.context.view_layer.update()
                fk = arm.matrix_world @ pb["HandR"].matrix
                hm = lerp_basis(hm, fk, ramp(f, F_RELEASE, F_FREE - 6))
            hand_t.matrix_world = hm
            hand_rots[f] = hm.to_3x3()
            bodyrot = B.to_3x3()
            sh = B @ shoulder_r
            # локоть — наружу от плеча и чуть вниз-назад (рука сверху на спинке): так запястье гнётся меньше
            pole_v = Vector((-0.8, 0.2, -0.15)).lerp(Vector((-0.25, 0.8, -0.2)), ramp(f, F_RELEASE, F_FREE - 6))
            elbow.matrix_world = Matrix.Translation(sh + bodyrot @ pole_v)   # отпустил — локоть назад, как у висящей руки
        else:
            hand_w = 0.0
        for c in hand_cons:
            c.influence = hand_w
            c.keyframe_insert("influence", frame=f)
        hand_t.keyframe_insert("location", frame=f)
        hand_t.keyframe_insert("rotation_euler", frame=f)
        elbow.keyframe_insert("location", frame=f)

        # --- куда смотрит камера ---
        fwd = B.to_3x3() @ Vector((0, -1, 0))
        head = B @ Vector((0, 0, 1.6 if f < F_SIT + 10 else 1.2))
        # взгляд перетекает без переключений: прямо → на руку на спинке → вперёд по телу → в монитор.
        # Раньше на отпускании он резко перескакивал с руки (−43° влево) на корпус, который уже шёл вправо
        early = B @ Vector((0, -1.5, 1.2))
        walk = (B @ Vector((0, 0, 1.6))) + fwd * 1.4 + Vector((0, 0, -0.75))
        base = early.lerp(walk, ramp(f, F_SPIN - 6, F_RELEASE + 12))
        if f >= F_SIT:
            base = base.lerp(head + fwd * 1.4 + Vector((0, 0, -0.75)), ramp(f, F_SIT, F_SIT + 12))
        base = base.lerp(head + fwd * 1.6 + Vector((0, 0, -0.35)), ramp(f, F_SEATED - 10, F_SEATED + 10))
        base = base.lerp(B @ MONITOR, ramp(f, F_LIFT0, F_DESK))   # руки на столе — смотрит в монитор
        w_palm = ramp(f, 0, F_GRAB) * (1.0 - ramp(f, F_SPIN - 8, F_RELEASE + 2))
        look = base.lerp(cm @ GRAB_PALM, w_palm)
        looks.append(look)

    # взгляд сглажен (гаусс, σ ≈ 5 кадров) — без рывков на сменах фаз
    sm = []
    for i in range(len(looks)):
        acc, n = Vector(), 0
        for j in range(max(0, i - 14), min(len(looks), i + 15)):
            w = math.exp(-((j - i) / 7.0) ** 2)
            acc += looks[j] * w
            n += w
        sm.append(acc / n)

    # --- запекание: IK → обычные ключи костей ---
    scene.frame_start, scene.frame_end = 0, LEN
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=0, frame_end=LEN, step=1, only_selected=False, visual_keying=True,
                     clear_constraints=True, clear_parents=False, use_current_action=False,
                     clean_curves=False, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    act = arm.animation_data.action
    act.name = "ChairSit"
    bpy.data.actions.remove(act_fk)
    fix_hand(scene, arm, hand_rots)

    # --- растяжение времени: быстрые места (рука тянется к спинке, отпускает и разворот) медленнее ---
    dmap = retime(scene, [arm, chair])
    nout = len(dmap) - 1
    chairs = [lerp_seq(chairs, d) for d in dmap]
    sm = [lerp_seq(sm, d) for d in dmap]

    def M(d):
        return int(round(warp_out(d)))

    # --- клипы-позы у стола и PowerReach ---
    extra = {name: pose_action(arm, name, [poses[key], poses[key]]) for name, key in EXTRA.items()}
    power_frames, power_look = power_reach(arm, poses)
    extra["PowerReach"] = pose_action(arm, "PowerReach", power_frames)

    # --- экспорт клипов ---
    ad = arm.animation_data
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    for name, a in [("ChairSit", act)] + list(extra.items()):
        tr = ad.nla_tracks.new()
        tr.name = name
        st = tr.strips.new(name, 0, a)
        if hasattr(st, "action_slot") and len(getattr(a, "slots", [])) and st.action_slot is None:
            st.action_slot = a.slots[0]
    ad.action = None
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
    for t in list(ad.nla_tracks):
        t.mute = True

    # --- путь кресла и взгляд → Godot (пространство SitSpot: x = −X, y = Z, z = Y) ---
    def g(v):
        return [round(-v[0], 4), round(v[2], 4), round(v[1], 4)]
    data = {
        "fps": FPS, "frames": nout + 1,
        "marks": {k: M(v) for k, v in (("grab", F_GRAB), ("pull", F_PULL), ("spin", F_SPIN), ("release", F_RELEASE),
                                       ("sit", F_SIT), ("land", F_LAND), ("seated", F_SEATED), ("swivel", F_SWIVEL),
                                       ("pull0", F_PULL0), ("pull1", F_PULL1), ("lift", F_LIFT0), ("desk", F_DESK),
                                       ("end", F_END))},
        # где стоит перед тем, как сесть (кадр sit): точка в пространстве SitSpot и поворот, рад
        "stand": g((0.35, 0.65, 0.0)) + [round(math.radians(90.0), 4)],
        "start": g((FOOT_START[0], FOOT_START[1], 0.0)) + [0.0],
        # кресло: x, y, z, поворот (рад, вокруг Y; 0 — сиденьем к столу)
        "chair": [g((c[0], c[1], c[3])) + [round(math.radians(c[2]), 4)] for c in chairs],
        "look": [g(v) for v in sm],
        # тянется к кнопке питания (клип PowerReach): кадр нажатия и куда смотрит камера
        "power": {"frames": len(power_frames), "marks": {"press": P_PRESS, "end": len(power_frames) - 1},
                  "look": [g(v) for v in power_look]},
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    scene.frame_set(0)
    return {"glb": OUT, "json": OUT_JSON, "frames": nout + 1}


if __name__ == "__main__":
    result = main()
