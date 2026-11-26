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
# мышь (mouse.gltf в yurchik_room, промерено по мешу): X −0.288…−0.225, Y −0.341…−0.228, низ 0.743, верх 0.779;
# горб плоский от Y −0.32 до −0.26 (0.777–0.779), спереди и сзади скат; левая кнопка — к +X от середины
MOUSE_C = Vector((-0.256, -0.284, 0.779))  # мышь: середина, верх
MOUSE_TRAVEL = Vector((0.045, 0.030))      # насколько ездит мышь по коврику (вправо-влево, вперёд-назад), м
# Кончики пальцев — хвост третьей фаланги, это ось пальца у самого кончика: подушечка на ~6 мм ниже.
PAD = 0.006
# правая на мышке (хват ладонью): кончики — от середины мыши; указательный и средний на кнопках у переднего края,
# безымянный и мизинец — по правому боку, большой — по левому
MOUSE_TIPS = {"Index": Vector((0.011, -0.040, -0.006 + PAD)), "Middle": Vector((-0.011, -0.044, -0.009 + PAD)),
              "Ring": Vector((-0.034, -0.022, -0.017 + PAD)), "Pinky": Vector((-0.036, 0.004, -0.025 + PAD)),
              "Thumb": Vector((0.036, 0.002, -0.022 + PAD))}
MOUSE_KNUCKLE = Vector((0.0, 0.048, 0.010))   # костяшка среднего — над задним скатом (пальцы 10 см — во всю мышь)
MOUSE_WRIST_Z = 0.787                         # запястье над ковриком: ниже рукав (обхват ~5 см) ложится на стол
# клавиатура (keyboard.gltf, промерено по колпачкам): верх клавиш 0.764–0.767; ряды Y: QWERTY −0.258, ASDF −0.239,
# ZXCV −0.220, нижний −0.201; X: W 0.1895, A 0.204, S 0.185, D 0.166, левый Shift 0.225, пробел — правее 0.18
KEYS_L = {"Middle": Vector((0.1895, -0.258, 0.767 + PAD)),    # W
          "Ring": Vector((0.204, -0.239, 0.766 + PAD)),       # A
          "Index": Vector((0.166, -0.239, 0.766 + PAD)),      # D
          "Pinky": Vector((0.226, -0.220, 0.765 + PAD)),      # Shift
          "Thumb": Vector((0.150, -0.202, 0.764 + PAD))}      # пробел
KEY_W = KEYS_L["Middle"]
KEYS_KNUCKLE_Z = 0.808                        # костяшки левой над клавишами (~4 см над колпачками)
KEYS_WRIST_Z = 0.795                          # запястье у переднего края клавы, рукав чуть выше стола
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


def _chain(pb, side, finger):
    return [pb["%s%s%d" % (finger, side, i)] for i in (1, 2, 3)]


def straighten(pb, side, finger):
    """Палец прямо по продолжению пястной кости (в стойке правая кисть сжата под молоток — сгибы до 86°)."""
    prev = (pb["%s%s1" % (finger, side)].head - pb["Hand" + side].head).normalized()
    for b in _chain(pb, side, finger):
        _aim(b, b.head + prev)
        prev = (b.tail - b.head).normalized()


def bend_finger(pb, side, finger, curls, spread, oppose=0.0):
    """Палец заново: выпрямлен (кроме большого), потом сгиб по суставам (curls, °) и отвод spread°.
    У большого ещё oppose° — поворот под ладонь вокруг оси кисти (к остальным пальцам, как при хвате)."""
    if finger == "Thumb":
        k, b = hand_axes(pb, side)
        hm = pb["Hand" + side].matrix.to_3x3()
        kw, bw = hm @ k, hm @ b
        t1 = pb["Thumb%s1" % side]
        if oppose:
            # знак: основание большого уходит под ладонь (против тыла)
            d0 = t1.tail - t1.head
            for sgn in (1.0, -1.0):
                r = Matrix.Rotation(math.radians(abs(oppose)) * sgn, 3, kw)
                if (r @ d0).dot(bw) <= d0.dot(bw):
                    break
            if oppose < 0.0:
                r = r.inverted()
            set_world_rot(t1, r @ t1.matrix.to_3x3())
        if spread:
            set_world_rot(t1, Matrix.Rotation(math.radians(spread), 3, bw) @ t1.matrix.to_3x3())
        thumb(pb, side, curls)
    else:
        straighten(pb, side, finger)
        curl(pb, side, finger, list(curls), spread)


def fit_finger(arm, side, finger, tip, base):
    """Подбор сгиба пальца, чтобы кончик лёг в tip. Свободны сгиб в костяшке, сгиб среднего сустава (дальний
    сустав идёт за ним в доле base[2]/base[1], как у живого пальца) и отвод в сторону; старт — форма base.
    Кисть уже стоит. Возвращает (сгибы по суставам °, отвод °, промах м)."""
    pb = arm.pose.bones
    chain = _chain(pb, side, finger)
    saved = [b.matrix_basis.copy() for b in chain]
    k3 = base[2] / base[1] if base[1] else 0.5
    # костяшка, средний сустав, отвод, (у большого) поворот под ладонь
    lim = ((-10.0, 80.0), (0.0, 100.0), (-30.0, 30.0), (-20.0, 50.0))
    n = 4 if finger == "Thumb" else 3

    def angles(x):
        return [x[0], x[1], x[1] * k3]

    def ev(x):
        for b, m in zip(chain, saved):
            b.matrix_basis = m
        _upd()
        bend_finger(pb, side, finger, angles(x), x[2], x[3])
        return (finger_tip(pb, side, finger) - tip).length

    x = [float(base[0]), float(base[1]), 0.0, 0.0]
    err = ev(x)
    step = 16.0
    while step > 0.25:
        moved = False
        for i in range(n):
            for d in (step, -step):
                y = list(x)
                y[i] = min(max(y[i] + d, lim[i][0]), lim[i][1])
                e = ev(y)
                if e < err - 1e-6:
                    x, err, moved = y, e, True
        if not moved:
            step *= 0.5
    ev(x)
    return angles(x), x[2], err, x[3]


def place_hand_fit(arm, side, knuckle, wrist_z, knuckle_dir, back_dir, pole, tips, bases, lead, forearm_share=0.6,
                   slack=0.025):
    """Кисть лежит, пальцы тянутся к своим точкам. Костяшки — в knuckle (горизонталь подбирается так, чтобы
    ведущий палец lead доставал свою точку без перегиба), запястье — на высоте wrist_z, кисть повёрнута по
    knuckle_dir/back_dir. Сгиб каждого пальца подбирается (fit_finger). Костяшки уходят от knuckle не дальше
    slack по горизонтали: ладонь лежит там, где задумано, остальное добирают пальцы."""
    pb = arm.pose.bones
    hl = (pb["Middle" + side + "1"].head - pb["Hand" + side].head).length
    base = snapshot(arm)
    kn = knuckle.copy()
    fits = {}
    for _ in range(6):
        d = knuckle_dir.normalized()
        flat = Vector((d.x, d.y, 0.0)).normalized()
        dz = kn.z - wrist_z
        wrist = kn - flat * math.sqrt(max(hl * hl - dz * dz, 1e-6)) - Vector((0, 0, dz))
        kd = (kn - wrist).normalized()
        apply(arm, base)
        rep = place_hand(arm, side, wrist, kd, back_dir, pole, forearm_share)
        fits = {f: fit_finger(arm, side, f, tips[f], bases[f]) for f in tips}
        miss = tips[lead] - finger_tip(pb, side, lead)
        miss.z = 0.0
        if miss.length < 0.0015:
            break
        kn += miss * 0.8
        sh = kn - knuckle
        sh.z = 0.0
        if sh.length > slack:
            kn = knuckle + sh.normalized() * slack
    rep = dict(rep)
    rep["knuckle"] = [round(v, 3) for v in pb["Middle" + side + "1"].head]
    rep["wrist"] = [round(v, 3) for v in pb["Hand" + side].head]
    rep["fingers"] = {f: {"curl": [round(a) for a in c], "spread": round(sp, 1), "miss_mm": round(e * 1000.0, 1)}
                      for f, (c, sp, e, _o) in fits.items()}
    rep["_fits"] = fits
    return rep


def shift_hand(arm, side, offset, pole):
    """Та же кисть с теми же пальцами, сдвинутая на offset (запястье и вся кисть едут параллельно)."""
    pb = arm.pose.bones
    k, b = hand_axes(pb, side)
    hm = pb["Hand" + side].matrix.to_3x3()
    return place_hand(arm, side, pb["Hand" + side].head + offset, hm @ k, hm @ b, pole)


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
        # (минус — разогнуть: в стойке пальцы уже чуть согнуты)
        tip0 = bone.tail - bone.head
        for sgn in (1.0, -1.0):
            r = Matrix.Rotation(math.radians(abs(a)) * sgn, 3, lat)
            if (r @ tip0).dot(bw) <= tip0.dot(bw):
                break
        if a < 0.0:
            r = r.inverted()
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
    # Форма сгиба пальцев (доли по суставам); сколько сгибать — подбирает fit_finger под свою клавишу или кнопку.
    # Печатающие пальцы — дугой: основная фаланга полого, кончик круче. На мышке — почти прямые, лежат на кнопках.
    KEY_BASES = {"Index": (30, 40, 20), "Middle": (30, 40, 20), "Ring": (30, 40, 20), "Pinky": (30, 40, 20),
                 "Thumb": (6, 12, 8)}
    MOUSE_BASES = {"Index": (16, 18, 8), "Middle": (16, 18, 8), "Ring": (30, 34, 18), "Pinky": (34, 38, 22),
                   "Thumb": (6, 14, 8)}

    def left_keys(self):
        # левая — на WASD: кончики на W/A/D, мизинец на Shift, большой на пробеле; кисть низко над передним краем
        # клавы, пальцы дугой вперёд и чуть вправо, кисть слегка на ребре (пронация неполная)
        kn = KEY_W + Vector((0.040, 0.070, 0.0))
        kn.z = KEYS_KNUCKLE_Z
        return place_hand_fit(self.arm, "L", kn, KEYS_WRIST_Z, Vector((-0.30, -1.0, 0.0)),
                              Vector((0.25, 0.0, 1.0)), self.pb["UpperArmL"].head + Vector((0.45, 0.25, -0.5)),
                              KEYS_L, self.KEY_BASES, "Middle")

    def right_mouse(self, off, center=None):
        """Правая на мышке (хват ладонью): ладонь лежит на горбе, указательный и средний вдоль кнопок, безымянный
        и мизинец обнимают правый бок, большой — левый. off — сдвиг мыши по коврику; fits — сгибы пальцев из
        средней позы — отчёт right_mouse без сдвига (мышь сдвинулась — рука едет вместе с ней, хват тот же)."""
        c = MOUSE_C + Vector((-off.x, -off.y, 0.0))
        tips = {f: c + v for f, v in MOUSE_TIPS.items()}
        kn = c + MOUSE_KNUCKLE
        pole = self.pb["UpperArmR"].head + Vector((-0.55, 0.3, -0.45))
        kd, back = Vector((0.10, -1.0, 0.0)), Vector((-0.15, 0.0, 1.0))
        if center is None:
            return place_hand_fit(self.arm, "R", kn, MOUSE_WRIST_Z, kd, back, pole, tips, self.MOUSE_BASES, "Index")
        kn = Vector(center["knuckle"]) + Vector((-off.x, -off.y, 0.0))
        hl = (self.pb["MiddleR1"].head - self.pb["HandR"].head).length
        flat = Vector((kd.x, kd.y, 0.0)).normalized()
        dz = kn.z - MOUSE_WRIST_Z
        wrist = kn - flat * math.sqrt(hl * hl - dz * dz) - Vector((0, 0, dz))
        rep = place_hand(self.arm, "R", wrist, (kn - wrist), back, pole)
        for f, (c, sp, _e, op) in center["_fits"].items():
            bend_finger(self.pb, "R", f, c, sp, op)
        rep = dict(rep)
        rep["miss_mm"] = {f: round((finger_tip(self.pb, "R", f) - tips[f]).length * 1000.0, 1) for f in tips}
        return rep

    def point(self):
        pb = self.pb
        curl(pb, "R", "Index", [2, 4, 2])
        for f in ("Middle", "Ring", "Pinky"):
            curl(pb, "R", f, [55, 65, 35])
        thumb(pb, "R", [20, 30, 20])

    def left_grip(self):
        """Левая упирается в край стола (пока тянется к кнопке): ладонь на кромке, кончики пальцев — на столешнице
        перед клавой (полоса Y −0.11…−0.18), большой — на кромке."""
        rep = place_hand_fit(self.arm, "L", Vector((0.11, -0.112, 0.786)), 0.80, Vector((-0.25, -1.0, 0.0)),
                             Vector((0.1, 0.1, 1.0)), self.pb["UpperArmL"].head + Vector((0.5, 0.2, -0.3)),
                             GRIP_TIPS, self.KEY_BASES, "Middle", slack=0.01)
        return {k: v for k, v in rep.items() if k != "_fits"}

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


GRIP_Z = DESK_TOP + PAD + 0.005   # чуть над столом: между позами power_mid и power кисть проседает на ~1.5 см
GRIP_TIPS = {"Index": Vector((0.087, -0.164, GRIP_Z)), "Middle": Vector((0.106, -0.167, GRIP_Z)),
             "Ring": Vector((0.126, -0.164, GRIP_Z)), "Pinky": Vector((0.144, -0.155, GRIP_Z)),
             "Thumb": Vector((0.072, -0.122, GRIP_Z))}
DESK = {"lean": 18.0, "twist": -8.0, "dy": 0.08}
HOVER = Vector((0.0, 0.015, 0.05))    # насколько кисти над клавой и мышью перед тем, как лечь (назад, вверх)
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
    mouse_c = report["desk_R"] = P.right_mouse(Vector((0.0, 0.0)))
    poses["desk"] = snapshot(arm)
    report["tips_mouse"] = {f: [round(v, 3) for v in finger_tip(pb, "R", f)] for f in ("Index", "Middle")}
    # мышь по коврику (только правая рука; X — вправо, Y — вперёд от Юрчика)
    for key, (ox, oy) in MOUSE_GRID.items():
        off = Vector((ox * MOUSE_TRAVEL.x, oy * MOUSE_TRAVEL.y))
        apply(arm, poses["desk"])
        report[key] = P.right_mouse(off, mouse_c)
        poses[key] = snapshot(arm)
    # hover: кисти той же формы зависли над клавой и мышью (подлетают к ним сверху-сзади, потом ложатся) —
    # иначе на переходе от lift пальцы, ещё согнутые, проходят сквозь мышь и клавиши
    apply(arm, poses["desk"])
    for s, pole in (("L", Vector((0.45, 0.25, -0.5))), ("R", Vector((-0.55, 0.3, -0.45)))):
        report["hover_" + s] = shift_hand(arm, s, HOVER, pb["UpperArm" + s].head + pole)
    poses["hover"] = snapshot(arm)
    # hover_r: только правая поднялась над мышью (к кнопке питания и обратно — левая остаётся на клавишах)
    apply(arm, poses["desk"])
    shift_hand(arm, "R", HOVER, pb["UpperArmR"].head + Vector((-0.55, 0.3, -0.45)))
    poses["hover_r"] = snapshot(arm)
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
        # (запястья не дальше Y 0.02: пальцы свисают на ~12 см вперёд и иначе на подъёме цепляют край стола)
        report["lift_" + s] = place_hand(arm, s, Vector((x, 0.02, 0.87)), Vector((-out * 0.25, -1.0, -0.15)),
                                         Vector((out * 0.2, 0.0, 1.0)),
                                         pb["UpperArm" + s].head + Vector((out * 0.5, 0.3, -0.45)))
        P.relaxed_fingers(s, (16, 20, 12))
    poses["lift"] = snapshot(arm)

    # ---------------------------------------------------------------- power_lift: правая ушла с мышки вверх-назад
    # (к кнопке рука идёт мимо края стола: сначала к себе и над краем, потом вниз снаружи от колена)
    apply(arm, poses["desk"])
    # (кисть уже свесилась пальцами вниз и стоит над краем стола: дальше она идёт вниз, и пальцы, смотрящие
    # вперёд, прошли бы сквозь столешницу)
    report["power_lift_R"] = place_hand(arm, "R", Vector((-0.30, -0.02, 0.88)), Vector((-0.1, -0.6, -1.0)),
                                        Vector((-0.5, -0.5, 0.5)), pb["UpperArmR"].head + Vector((-0.6, 0.3, -0.3)))
    P.relaxed_fingers("R", (16, 20, 12))
    shift_hand(arm, "L", HOVER, pb["UpperArmL"].head + Vector((0.45, 0.25, -0.5)))   # левая тоже приподнялась
    poses["power_lift"] = snapshot(arm)
    # power_back: обратно к мыши — кисть сначала поднялась выше края стола и уже смотрит пальцами вперёд
    apply(arm, poses["desk"])
    # (запястье ближе к себе, пальцы вперёд-вниз: поднимаются мимо кромки стола, а не сквозь неё)
    report["power_back_R"] = place_hand(arm, "R", Vector((-0.30, 0.05, 0.93)), Vector((-0.1, -1.0, -0.55)),
                                        Vector((-0.4, 0.0, 1.0)), pb["UpperArmR"].head + Vector((-0.6, 0.3, -0.3)))
    P.relaxed_fingers("R", (16, 20, 12))
    shift_hand(arm, "L", HOVER, pb["UpperArmL"].head + Vector((0.45, 0.25, -0.5)))   # левая над клавой
    poses["power_back"] = snapshot(arm)

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
