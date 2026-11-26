# Свои сидячие позы Юрчика за компом (вместо позы Sit из GMod) — для build_chair_sit.py.
#
# Позы строятся на скелете Юрчика v3 в пространстве арматуры у стола: вперёд (к столу) −Y, вправо −X, вверх Z,
# тело стоит в SitSpot (кресло у стола — центр на SIT_BACK позади). Каждая поза — словарь
# {кость: matrix_basis}, собранный из простых целей:
#   таз — на подушке, чуть завален назад; корпус — наклон вперёд / вбок / поворот; голова — смотрит в точку;
#   ноги — IK к стопам на полу; руки — IK к запястью + поворот кисти (пальцы, тыл кисти), кручение делится
#   между предплечьем и запястьем; пальцы — сгиб по суставам.
# Позы:
#   rest   — сидит прямо, ладони на бёдрах (садится, разворачивается, подтягивается к столу);
#   desk   — у стола: левая на WASD, правая на мышке, корпус чуть вперёд, взгляд в монитор;
#   mouse_l / mouse_r / mouse_f / mouse_b — правая рука с мышкой сдвинута по коврику (живая рука в Godot);
#   click  — указательный правой нажал левую кнопку мыши; tap_* — пальцы левой нажали клавишу;
#   power  — наклонился вправо-вниз, указательный правой на кнопке питания системника.
# Запуск — из build_chair_sit.py (живой Blender через Blender MCP).
import bpy, math
from mathutils import Matrix, Vector, Quaternion

# --- окружение у стола (пространство арматуры, м; промерено по моделям yurchik_room в stairwell.tscn) ---
DESK_EDGE_Y = -0.11            # передний край стола (к Юрчику)
DESK_TOP = 0.74
KEY_TOP = 0.77                 # верх клавиш
MOUSE_C = Vector((-0.278, -0.26, 0.779))   # мышь: середина, верх
MOUSE_LMB = Vector((0.010, -0.030, -0.004))   # кончик указательного на левой кнопке — от середины мыши
MOUSE_TRAVEL = Vector((0.045, 0.030))      # насколько ездит мышь по коврику (вправо-влево, вперёд-назад), м
KEY_W = Vector((0.192, -0.252, KEY_TOP + 0.006))   # клавиша W (средний палец левой)
# позы мыши по коврику: имя → сдвиг в долях MOUSE_TRAVEL (x — вправо, y — вперёд); середина — поза desk
MOUSE_GRID = {"mouse_r": (1, 0), "mouse_l": (-1, 0), "mouse_f": (0, 1), "mouse_b": (0, -1),
              "mouse_fr": (1, 1), "mouse_fl": (-1, 1), "mouse_br": (1, -1), "mouse_bl": (-1, -1)}
BUTTON = Vector((-0.425, -0.199, 0.239))   # кнопка питания на передней стенке системника

SEAT_PELVIS = Vector((0.0, 0.335, 0.612))  # голова кости Pelvis сидя (верх подушки — 0.555, проседает на ~3 см)
PELVIS_TILT = -10.0                         # ° — таз завален назад (сидя крестец уходит назад)
PELVIS_FOLLOW = 0.70                        # доля наклона корпуса сверх 15°, которую берёт таз

FINGERS = ("Index", "Middle", "Ring", "Pinky")


def _upd():
    bpy.context.view_layer.update()


def rot_about(pivot, axis, ang):
    return Matrix.Translation(pivot) @ Matrix.Rotation(ang, 4, axis) @ Matrix.Translation(-pivot)


def set_world_rot(pb, rot3):
    """Повернуть кость в пространстве арматуры, голова остаётся на месте."""
    m = rot3.to_4x4()
    m.translation = pb.head.copy()
    pb.matrix = m
    _upd()


def trunk(pb, rest, lean=0.0, side=0.0, twist=0.0):
    """Корпус: rest-ориентация кости, повёрнутая наклоном вперёд (lean°, к −Y), вбок вправо (side°, к −X)
    и поворотом вправо (twist°, сверху по часовой)."""
    r = (Matrix.Rotation(math.radians(-twist), 3, 'Z') @ Matrix.Rotation(math.radians(-side), 3, 'Y')
         @ Matrix.Rotation(math.radians(lean), 3, 'X'))
    set_world_rot(pb, r @ rest)


def look(pb, rest, target, fwd_local):
    """Голова смотрит на target: лицо (ось fwd_local кости) — в точку, макушка — как можно ближе к вверху."""
    want = (target - pb.head).normalized()
    cur = (rest @ fwd_local).normalized()
    # сначала разворот по горизонтали, потом наклон — без крена
    yaw = math.atan2(-want.x, -want.y) - math.atan2(-cur.x, -cur.y)
    pitch = math.atan2(-want.z, Vector((want.x, want.y)).length) - math.atan2(-cur.z, Vector((cur.x, cur.y)).length)
    r = Matrix.Rotation(yaw, 3, 'Z')
    side_axis = r @ Vector((1.0, 0.0, 0.0))
    set_world_rot(pb, Matrix.Rotation(pitch, 3, side_axis) @ r @ rest)


def two_bone(arm, up, low, target, pole):
    """Аналитический IK на две кости: low.tail в target, колено/локоть — в сторону pole. Без констрейнтов:
    поза одна и та же при каждом запуске, без перескоков решателя."""
    a = up.head.copy()
    l1, l2 = (low.head - up.head).length, (low.tail - low.head).length
    d = target - a
    dist = min(max(d.length, 1e-4), (l1 + l2) * 0.999)
    dn = d.normalized()
    cos_a = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
    ang = math.acos(max(-1.0, min(1.0, cos_a)))
    pv = (pole - a)
    pv = (pv - dn * pv.dot(dn)).normalized()
    mid = a + (dn * math.cos(ang) + pv * math.sin(ang)) * l1
    # верхняя кость: ось Y — к mid, поворот кратчайший от текущей оси (крутка руки сохраняется)
    _aim(up, mid)
    _aim(low, target)


def _aim(pb, to):
    cur = (pb.tail - pb.head).normalized()
    want = (to - pb.head).normalized()
    q = cur.rotation_difference(want)
    set_world_rot(pb, q.to_matrix() @ pb.matrix.to_3x3())


def hand_axes(pb, side):
    """Оси кисти в её локальном пространстве: k — от запястья к костяшке среднего, back — тыл кисти."""
    hand = pb["Hand" + side]
    hb = hand.bone.matrix_local
    k = (hb.inverted() @ pb["Middle" + side + "1"].bone.head_local)
    k = k.normalized() if k.length > 1e-6 else Vector((0, 1, 0))
    # тыл кисти — по костяшкам: от указательного к мизинцу поперёк кисти (в покое ладонь смотрит внутрь и назад)
    bones = pb.id_data.data.bones
    across = bones["Pinky" + side + "1"].head_local - bones["Index" + side + "1"].head_local
    kw = (bones["Middle" + side + "1"].head_local - bones["Hand" + side].head_local).normalized()
    back_w = across.cross(kw) if side == "R" else kw.cross(across)
    back = hb.to_3x3().inverted() @ back_w
    back = (back - k * back.dot(k)).normalized()
    return k, back


def hand_world(pb, side, knuckle_dir, back_dir):
    """Поворот кисти в мире: костяшки — по knuckle_dir, тыл кисти — по back_dir."""
    k, b = hand_axes(pb, side)
    kw = knuckle_dir.normalized()
    bw = (back_dir - kw * back_dir.dot(kw)).normalized()
    local = Matrix((k, b, k.cross(b))).transposed()
    world = Matrix((kw, bw, kw.cross(bw))).transposed()
    return world @ local.inverted()


def place_hand(arm, side, wrist, knuckle_dir, back_dir, pole, forearm_share=0.6):
    """Рука: запястье в wrist, кисть повёрнута как надо. Кручение кисти вокруг предплечья делится:
    forearm_share берёт предплечье (пронация, как у живой руки), остальное — запястье."""
    pb = arm.pose.bones
    up, fore, hand = pb["UpperArm" + side], pb["Forearm" + side], pb["Hand" + side]
    two_bone(arm, up, fore, wrist, pole)
    want = hand_world(pb, side, knuckle_dir, back_dir)
    axis = (fore.tail - fore.head).normalized()
    cur = hand.matrix.to_3x3()
    delta = (want @ cur.inverted()).to_quaternion()
    v = Vector((delta.x, delta.y, delta.z))
    tw = 2.0 * math.atan2(v.dot(axis), delta.w)
    tw = (tw + math.pi) % (2 * math.pi) - math.pi
    ft = max(min(tw * forearm_share, math.radians(90.0)), math.radians(-90.0))
    set_world_rot(fore, Matrix.Rotation(ft, 3, axis) @ fore.matrix.to_3x3())
    set_world_rot(hand, want)
    return hand_report(pb, side)


def place_hand_tip(arm, side, tip, finger, knuckle_dir, back_dir, pole, fingers_fn, forearm_share=0.6):
    """Как place_hand, но в точку ставится кончик пальца finger (пальцы согнуты fingers_fn): запястье
    подбирается за несколько шагов — сдвигается на промах кончика."""
    pb = arm.pose.bones
    base = snapshot(arm)
    wrist = tip - knuckle_dir.normalized() * 0.17
    rep = None
    for _ in range(6):
        apply(arm, base)
        rep = place_hand(arm, side, wrist, knuckle_dir, back_dir, pole, forearm_share)
        fingers_fn()
        miss = tip - finger_tip(pb, side, finger)
        if miss.length < 0.001:
            break
        wrist = wrist + miss
    rep = dict(rep)
    rep["tip_miss_mm"] = round((tip - finger_tip(pb, side, finger)).length * 1000.0, 1)
    rep["reach"] = round((wrist - pb["UpperArm" + side].head).length / (
        (pb["Forearm" + side].head - pb["UpperArm" + side].head).length + pb["Forearm" + side].bone.length), 3)
    return rep


def hand_report(pb, side):
    fore, hand = pb["Forearm" + side], pb["Hand" + side]
    fa = (fore.tail - fore.head).normalized()
    k, _ = hand_axes(pb, side)
    kw = hand.matrix.to_3x3() @ k
    bend = math.degrees(fa.angle(kw))
    rel = (fore.matrix.to_3x3().inverted() @ hand.matrix.to_3x3()).to_quaternion()
    rest_rel = (fore.bone.matrix_local.to_3x3().inverted() @ hand.bone.matrix_local.to_3x3()).to_quaternion()
    r = rest_rel.inverted() @ rel
    twist = math.degrees(2.0 * math.atan2(r.y, r.w))
    twist = (twist + 180.0) % 360.0 - 180.0
    ftw = (fore.bone.matrix_local.to_3x3().inverted() @ pb["UpperArm" + side].bone.matrix_local.to_3x3())
    return {"wrist_bend": round(bend, 1), "wrist_twist": round(twist, 1)}


def curl(pb, side, finger, angles, spread=0.0):
    """Сгиб пальца по трём суставам (°; + — к ладони). Ось сгиба — поперёк кисти; spread° — отвод в сторону."""
    k, b = hand_axes(pb, side)
    hm = pb["Hand" + side].matrix.to_3x3()
    kw, bw = hm @ k, hm @ b
    lat = kw.cross(bw).normalized()
    for i, a in enumerate(angles):
        bone = pb["%s%s%d" % (finger, side, i + 1)]
        if i == 0 and spread:
            set_world_rot(bone, Matrix.Rotation(math.radians(spread), 3, bw) @ bone.matrix.to_3x3())
        if a == 0.0:
            continue
        # знак: кончик уходит к ладони (против тыла кисти)
        tip0 = bone.tail - bone.head
        for sgn in (1.0, -1.0):
            r = Matrix.Rotation(math.radians(a) * sgn, 3, lat)
            if (r @ tip0).dot(bw) <= tip0.dot(bw):
                break
        set_world_rot(bone, r @ bone.matrix.to_3x3())


def thumb(pb, side, angles, toward=None):
    """Большой палец: сгиб по суставам вокруг оси поперёк его плоскости (к ладони)."""
    k, b = hand_axes(pb, side)
    hm = pb["Hand" + side].matrix.to_3x3()
    bw = hm @ b
    for i, a in enumerate(angles):
        bone = pb["Thumb%s%d" % (side, i + 1)]
        d = (bone.tail - bone.head).normalized()
        ax = d.cross(-bw).normalized()
        set_world_rot(bone, Matrix.Rotation(math.radians(a), 3, ax) @ bone.matrix.to_3x3())


def finger_tip(pb, side, finger):
    return pb["%s%s3" % (finger, side)].tail.copy()


def leg(arm, side, ankle, yaw_deg, foot_rest_world, knee_out=0.25):
    """Нога: щиколотка в ankle, стопа плоско на полу (поза стопы стойки, повёрнутая на yaw°)."""
    pb = arm.pose.bones
    th, sh, ft = pb["Thigh" + side], pb["Shin" + side], pb["Foot" + side]
    out = 1.0 if side == "L" else -1.0
    knee_pole = th.head + Vector((out * knee_out, -1.0, 0.25))
    two_bone(arm, th, sh, ankle, knee_pole)
    r = Matrix.Rotation(math.radians(yaw_deg * out), 3, 'Z') @ foot_rest_world
    set_world_rot(ft, r)


def snapshot(arm):
    return {b.name: b.matrix_basis.copy() for b in arm.pose.bones}


def apply(arm, pose):
    for b in arm.pose.bones:
        b.matrix_basis = pose[b.name]
    _upd()


class Poser:
    """Строитель поз на арматуре arm от стойки idle ({кость: matrix_basis})."""

    def __init__(self, arm, idle):
        self.arm, self.idle = arm, idle
        self.pb = pb = arm.pose.bones
        apply(arm, idle)
        self.foot_rest = {s: pb["Foot" + s].matrix.to_3x3() for s in "LR"}
        self.rest_m = {n: pb[n].bone.matrix_local.to_3x3() for n in ("Pelvis", "Spine", "Head")}

    def seat(self, lean, side=0.0, twist=0.0, dx=0.0, dy=0.0, dz=0.0, tilt=PELVIS_TILT):
        """Таз на подушке (сдвиг dx — вправо, dy — вперёд, к столу), корпус наклонён (см. trunk)."""
        apply(self.arm, self.idle)
        # сильный наклон идёт и из бёдер: таз доворачивается вперёд, иначе весь изгиб — в пояснице
        r = Matrix.Rotation(math.radians(tilt + PELVIS_FOLLOW * max(0.0, lean - 15.0)), 3, 'X')
        m = (Matrix.Rotation(math.radians(-twist * 0.3), 3, 'Z')
             @ Matrix.Rotation(math.radians(-side * 0.2), 3, 'Y') @ r @ self.rest_m["Pelvis"]).to_4x4()
        m.translation = SEAT_PELVIS + Vector((-dx, -dy, dz))
        self.pb["Pelvis"].matrix = m
        _upd()
        trunk(self.pb["Spine"], self.rest_m["Spine"], lean, side, twist)

    def legs(self, feet_y=-0.075, feet_x=0.135, yaw=9.0, shift_x=0.0):
        for s in "LR":
            out = 1.0 if s == "L" else -1.0
            leg(self.arm, s, Vector((out * feet_x - shift_x, feet_y, 0.10)), yaw, self.foot_rest[s])

    def look(self, at):
        h = self.pb["Head"]
        look(h, h.matrix.to_3x3(), at, Vector((0.0, 0.0, 1.0)))   # лицо — ось Z кости головы (в покое ≈ −Y)

    def relaxed_fingers(self, side, base=(18, 22, 14)):
        for f in FINGERS:
            curl(self.pb, side, f, [base[0] + (4 if f in ("Ring", "Pinky") else 0), base[1], base[2]])
        thumb(self.pb, side, [8, 10, 8])

    # ------------------------------------------------------------------ руки у стола
    def left_fingers(self):
        pb = self.pb
        curl(pb, "L", "Index", [20, 24, 12], spread=-2)    # D
        curl(pb, "L", "Middle", [14, 22, 10])              # W
        curl(pb, "L", "Ring", [20, 26, 12], spread=3)      # A
        curl(pb, "L", "Pinky", [30, 30, 16], spread=6)     # Shift рядом
        thumb(pb, "L", [14, 18, 10])                       # над пробелом

    def left_keys(self):
        # левая — на WASD: средний на W, кисть над краем стола, пальцы вперёд и чуть вправо, кисть слегка на ребре
        return place_hand_tip(self.arm, "L", KEY_W, "Middle", Vector((-0.30, -1.0, -0.02)),
                              Vector((0.25, 0.0, 1.0)), self.pb["UpperArmL"].head + Vector((0.45, 0.25, -0.5)),
                              self.left_fingers)

    def right_fingers(self):
        pb = self.pb
        curl(pb, "R", "Index", [6, 12, 8])                 # на левой кнопке, почти прямой
        curl(pb, "R", "Middle", [8, 12, 8], spread=-2)     # на правой
        curl(pb, "R", "Ring", [16, 22, 12], spread=-5)     # сбоку мыши
        curl(pb, "R", "Pinky", [20, 24, 14], spread=-9)
        thumb(pb, "R", [6, 14, 8])                         # с другого бока

    def right_mouse(self, off):
        # правая — на мышке: кончик указательного на левой кнопке, ладонь на спинке, запястье над ковриком
        c = MOUSE_C + Vector((-off.x, -off.y, 0.0))
        return place_hand_tip(self.arm, "R", c + MOUSE_LMB, "Index", Vector((0.10, -1.0, -0.30)),
                              Vector((-0.15, 0.0, 1.0)), self.pb["UpperArmR"].head + Vector((-0.55, 0.3, -0.45)),
                              self.right_fingers)

    def point(self):
        pb = self.pb
        curl(pb, "R", "Index", [2, 4, 2])
        for f in ("Middle", "Ring", "Pinky"):
            curl(pb, "R", f, [55, 65, 35])
        thumb(pb, "R", [20, 30, 20])

    def left_grip(self):
        """Левая держится за край стола (пока тянется к кнопке)."""
        rep = place_hand(self.arm, "L", Vector((0.12, -0.085, 0.788)), Vector((-0.25, -1.0, -0.15)),
                         Vector((0.1, 0.1, 1.0)), self.pb["UpperArmL"].head + Vector((0.5, 0.2, -0.3)))
        self.relaxed_fingers("L", (30, 40, 20))
        return rep

    def power(self, p):
        """Поза у кнопки питания; p — словарь параметров корпуса (lean, side, twist, dx, dy)."""
        pb = self.pb
        self.seat(p["lean"], p["side"], p["twist"], p.get("dx", 0.0), p.get("dy", 0.0))
        self.legs(feet_y=-0.10, shift_x=p.get("dx", 0.0) * 0.5)
        self.look(BUTTON + Vector((0, 0.02, 0.02)))
        rep = {"R": place_hand_tip(self.arm, "R", BUTTON + Vector((0, 0.010, 0)), "Index",
                                   Vector((-0.10, -1.0, -0.55)), Vector((-0.15, 0.25, 1.0)),
                                   pb["UpperArmR"].head + Vector((-0.6, 0.2, 0.1)), self.point)}
        rep["L"] = self.left_grip()
        rep["head"] = [round(v, 3) for v in pb["Head"].head]
        rep["shoulderR"] = [round(v, 3) for v in pb["UpperArmR"].head]
        return rep


DESK = {"lean": 18.0, "twist": -8.0, "dy": 0.08}
POWER = {"lean": 58.0, "side": 40.0, "twist": 0.0, "dy": 0.08, "dx": 0.06}


def build(arm, idle):
    """Все позы: {имя: {кость: matrix_basis}} и отчёт с замерами."""
    P = Poser(arm, idle)
    pb = P.pb
    poses, report = {}, {}

    # ---------------------------------------------------------------- rest: ладони на бёдрах
    P.seat(lean=4.0)
    P.legs()
    P.look(Vector((0.0, -1.6, 1.05)))
    for s in "LR":
        out = 1.0 if s == "L" else -1.0
        th, sh = pb["Thigh" + s], pb["Shin" + s]
        on = th.head.lerp(sh.head, 0.5) + Vector((out * -0.02, 0.0, 0.085))   # запястье над бедром
        report["rest_" + s] = place_hand(arm, s, on, (sh.head - th.head) + Vector((-out * 0.08, 0, -0.10)),
                                         Vector((out * 0.25, 0.0, 1.0)),
                                         pb["UpperArm" + s].head + Vector((out * 0.5, 0.35, -0.4)))
        P.relaxed_fingers(s, (8, 12, 8))
    poses["rest"] = snapshot(arm)

    # ---------------------------------------------------------------- desk: клава и мышь
    P.seat(DESK["lean"], 0.0, DESK["twist"], 0.0, DESK["dy"])
    P.legs(feet_y=-0.10 - DESK["dy"] * 0.5)
    P.look(Vector((-0.02, -0.5, 1.03)))
    report["desk_L"] = P.left_keys()
    report["desk_R"] = P.right_mouse(Vector((0.0, 0.0)))
    poses["desk"] = snapshot(arm)
    report["tips_mouse"] = {f: [round(v, 3) for v in finger_tip(pb, "R", f)] for f in ("Index", "Middle")}
    # мышь по коврику (только правая рука; X — вправо, Y — вперёд от Юрчика)
    for key, (ox, oy) in MOUSE_GRID.items():
        off = Vector((ox * MOUSE_TRAVEL.x, oy * MOUSE_TRAVEL.y))
        apply(arm, poses["desk"])
        report[key] = P.right_mouse(off)
        poses[key] = snapshot(arm)
    # клик и нажатия клавиш — только пальцы (в Godot смешиваются поверх)
    apply(arm, poses["desk"])
    curl(pb, "R", "Index", [6, 4, 2])
    poses["click"] = snapshot(arm)
    for f in ("Index", "Middle", "Ring"):
        apply(arm, poses["desk"])
        curl(pb, "L", f, [9, 5, 3])
        poses["tap_" + f.lower()] = snapshot(arm)
    apply(arm, poses["desk"])
    thumb(pb, "L", [0, 10, 6])
    poses["tap_thumb"] = snapshot(arm)

    # ---------------------------------------------------------------- lift: руки подняты над краем стола
    # (переход с бёдер на клаву и мышь: сначала руки вверх перед собой, потом вперёд над столом)
    P.seat(DESK["lean"] * 0.6, 0.0, DESK["twist"] * 0.6, 0.0, DESK["dy"])
    P.legs(feet_y=-0.10 - DESK["dy"] * 0.5)
    P.look(Vector((-0.02, -0.5, 1.03)))
    for s, x in (("L", 0.20), ("R", -0.22)):
        out = 1.0 if s == "L" else -1.0
        report["lift_" + s] = place_hand(arm, s, Vector((x, -0.03, 0.86)), Vector((-out * 0.25, -1.0, -0.15)),
                                         Vector((out * 0.2, 0.0, 1.0)),
                                         pb["UpperArm" + s].head + Vector((out * 0.5, 0.3, -0.45)))
        P.relaxed_fingers(s, (16, 20, 12))
    poses["lift"] = snapshot(arm)

    # ---------------------------------------------------------------- power_lift: правая ушла с мышки вверх-назад
    # (к кнопке рука идёт мимо края стола: сначала к себе и над краем, потом вниз снаружи от колена)
    apply(arm, poses["desk"])
    report["power_lift_R"] = place_hand(arm, "R", Vector((-0.30, -0.05, 0.85)), Vector((-0.1, -1.0, -0.6)),
                                        Vector((-0.4, 0.0, 1.0)), pb["UpperArmR"].head + Vector((-0.6, 0.3, -0.3)))
    P.relaxed_fingers("R", (16, 20, 12))
    poses["power_lift"] = snapshot(arm)

    # ---------------------------------------------------------------- power: кнопка на системнике
    report["power"] = P.power(POWER)
    poses["power"] = snapshot(arm)
    # на полпути: правая рука уже ушла с мышки вниз, снаружи от правого колена (мимо края стола), корпус наклоняется
    mid = {k: POWER[k] * 0.55 for k in POWER}
    P.seat(mid["lean"], mid["side"], mid["twist"], mid.get("dx", 0.0), mid["dy"])
    P.legs(feet_y=-0.10, shift_x=mid.get("dx", 0.0) * 0.5)
    P.look(BUTTON + Vector((0.05, 0.25, 0.25)))
    report["power_mid_R"] = place_hand(arm, "R", Vector((-0.33, 0.02, 0.56)), Vector((-0.05, -0.6, -1.0)),
                                       Vector((-0.6, 0.3, 0.5)), pb["UpperArmR"].head + Vector((-0.6, 0.3, 0.0)))
    P.relaxed_fingers("R", (20, 26, 14))
    report["power_mid_L"] = P.left_grip()
    poses["power_mid"] = snapshot(arm)
    return poses, report
