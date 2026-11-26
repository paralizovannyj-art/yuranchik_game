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
#   G  вытягивает ноги, упирается пятками и подтягивается к столу.
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
# assets/animations/sit/yurchik_sit.glb (клип ChairSit) и assets/animations/sit/chair_sit.json.
import bpy, os, math, json
from mathutils import Matrix, Vector

ROOT = r"C:\Users\mrs\Documents\yuranchik_game"
SRC = os.path.join(ROOT, "assets", "animations", "gmod", "yurchik_gmod.glb")
CHAIR = os.path.join(ROOT, "assets", "models", "gaming_chair.gltf")
OUT_DIR = os.path.join(ROOT, "assets", "animations", "sit")
OUT = os.path.join(OUT_DIR, "yurchik_sit.glb")
OUT_JSON = os.path.join(OUT_DIR, "chair_sit.json")
SCENE = "ChairSit"
FPS = 30

SIT_LIFT = 0.56      # м — подъём позы Sit: таз на подушке кресла (верх сиденья 0.52 — build_gaming_chair.py)
SIT_BACK = 0.35      # м — таз уходит назад от места, где стоял (= от SitSpot до центра кресла у стола)

# --- кресло (центр — газлифт; поворот a: 0 — сиденьем к столу, + — против часовой сверху, то есть влево) ---
C_REST = (0.0, 0.07, -4.0)     # задвинуто под стол (подлокотники перед краем стола)
C_OUT = (0.0, 0.65, 90.0)      # откачено и повёрнуто сиденьем влево (к дивану)
C_FINAL = (0.0, SIT_BACK, 0.0)  # сидит у стола: центр кресла на SIT_BACK позади SitSpot
GRAB = Vector((-0.25, -0.55, 1.37))    # запястье на левом верхнем углу спинки (координаты кресла: вперёд +Y)
GRAB_FINGERS = Vector((0.0, 0.55, -0.85)).normalized()   # пальцы — через верх спинки вперёд-вниз

# --- кадры ---
F_GRAB, F_RELEASE, F_SIT, F_SEATED, F_SWIVEL, F_END = 10, 46, 74, 122, 146, 186
LEN = F_END


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
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


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
    (0, (0.36, 0.95, 0.0)),
    (F_GRAB, (0.36, 0.95, 0.0)),
    (21, (0.37, 1.08, 0.0)),
    (32, (0.38, 1.25, 0.0)),
    (F_RELEASE, (0.345, 1.32, -14.0)),
    (52, (0.35, 1.24, 0.0)),
    (60, (0.36, 0.94, 45.0)),
    (68, (0.355, 0.70, 84.0)),
    (72, (0.35, 0.65, 90.0)),
]
# шаги: стопа (L/R), кадр отрыва, кадр постановки, куда (место тела, под которое встаёт стопа)
STEPS = {
    "L": [(20, 28, (0.38, 1.25, 0.0)), (38, 45, (0.35, 1.33, -12.0)), (49, 57, (0.36, 1.04, 30.0)), (60, 68, (0.355, 0.70, 84.0)),
          (68, 73, (0.35, 0.65, 90.0))],
    "R": [(12, 20, (0.37, 1.12, 0.0)), (26, 32, (0.38, 1.25, 0.0)), (33, 40, (0.34, 1.31, -14.0)),
          (54, 62, (0.36, 0.86, 60.0)), (65, 72, (0.35, 0.65, 90.0))],
}
FOOT_START = (0.36, 0.95, 0.0)
STEP_LIFT = 0.07

# кресло (x, y, a)
CHAIR_KEYS = [
    (0, C_REST),
    (F_GRAB + 2, C_REST),
    (32, (0.0, 0.42, 5.0)),
    (F_RELEASE, (0.0, 0.53, 38.0)),
    (56, (0.0, 0.62, 74.0)),
    (66, C_OUT),
]
# ключи посадки (из старого SitDown): (кадр от F_SIT, доля поз стойка→сидя, вниз, назад, наклон корпуса °)
SIT_KEYS = [
    (0, 0.00, 0.00, 0.00, 0.0),
    (10, 0.18, 0.10, 0.05, 14.0),
    (22, 0.55, 0.48, 0.45, 32.0),
    (32, 0.92, 0.97, 0.90, 22.0),
    (38, 1.00, 1.03, 1.00, 8.0),
    (48, 1.00, 1.00, 1.00, 0.0),
]
F_LAND = F_SIT + 36        # таз опустился на подушку — кресло проседает
# подтягивание к столу (G)
F_REACH0, F_REACH1, F_PULL0, F_PULL1, F_SETTLE1 = 148, 156, 157, 173, 182
HEEL_REACH = 0.13          # м — насколько вытягивает ноги вперёд, прежде чем упереться пятками


def chair_at(f):
    """(x, y, a, dz) кресла на кадре f."""
    if f <= F_SEATED:
        x, y, a = mono3(CHAIR_KEYS, f)
    elif f <= F_SWIVEL:
        x, y, a = C_OUT[0], C_OUT[1], C_OUT[2] * (1.0 - ramp(f, F_SEATED, F_SWIVEL))
    else:
        u = ramp(f, F_PULL0, F_PULL1)
        x, y, a = 0.0, C_OUT[1] + (C_FINAL[1] - C_OUT[1]) * u, 0.0
    dz = -0.018 * math.sin(math.pi * min(max((f - F_LAND + 4) / 14.0, 0.0), 1.0))
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
            return body(*p), STEP_LIFT * math.sin(math.pi * u)
        prev = to
    return body(*prev), 0.0


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
    sit = sample(arm, "Sit")
    arm.animation_data.action = None

    pb = arm.pose.bones
    pelvis = pb["Pelvis"]
    p_rest = pelvis.bone.matrix_local
    # таз в пространстве тела: стойка и сидя (поднят на подушку и сдвинут назад)
    P_idle = p_rest @ idle["Pelvis"]
    P_sit = p_rest @ sit["Pelvis"]
    P_sit = Matrix.Translation((0.0, SIT_BACK, SIT_LIFT)) @ P_sit
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
    ch.target, ch.pole_target, ch.chain_count, ch.pole_angle = hand_t, elbow, 2, math.radians(-90)
    ch2 = pb["HandR"].constraints.new('COPY_ROTATION')
    ch2.target = hand_t
    leg_cons = [c for c in cons]
    hand_cons = [ch, ch2]

    # рука на спинке: ориентация кисти — от стойки, повернуть «пальцы» на нужное направление
    hand_idle = None
    for b in pb:
        b.matrix_basis = idle[b.name]
    bpy.context.view_layer.update()
    hand_idle = pb["HandR"].matrix.copy()

    def hand_on_chair(cm):
        pos = cm @ GRAB
        fingers = (cm.to_3x3() @ GRAB_FINGERS).normalized()
        cur = (hand_idle.to_3x3() @ Vector((0, 1, 0))).normalized()
        rot = cur.rotation_difference(fingers).to_matrix()
        # ладонью вниз на спинку: доворот вокруг пальцев
        roll = Matrix.Rotation(math.radians(80.0), 3, fingers)
        m = (roll @ rot @ hand_idle.to_3x3()).to_4x4()
        m.translation = pos
        return m

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
            bend = 10.0 * ramp(f, 0, F_GRAB) * (1.0 - ramp(f, F_RELEASE, 56))
        else:
            B = body(0.35, 0.65, 90.0) if f <= F_SEATED else seat_body(f)
            k = min(f - F_SIT, 48)
            keys = SIT_KEYS
            i = max(j for j in range(len(keys)) if keys[j][0] <= k)
            if i == len(keys) - 1:
                _, t_fk, down, back, bend = keys[-1]
            else:
                a, b2 = keys[i], keys[i + 1]
                u = smooth((k - a[0]) / float(b2[0] - a[0]))
                t_fk, down, back, bend = [a[j] + (b2[j] - a[j]) * u for j in range(1, 5)]
            if f > F_SEATED:
                # подтягивается: корпус чуть вперёд, когда тянет ногами
                bend += 7.0 * math.sin(math.pi * ramp(f, F_REACH0, F_PULL1))
        for b in pb:
            b.matrix_basis = lerp_basis(idle[b.name], sit[b.name], t_fk)
        loc = Vector((li.x + (ls.x - li.x) * t_fk, li.y + (ls.y - li.y) * back, li.z + (ls.z - li.z) * down))
        pelvis.matrix = B @ Matrix.LocRotScale(loc, ri.slerp(rs, t_fk), Vector((1, 1, 1)))
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
        if f < F_SIT + 4:
            leg_w = 1.0 - ramp(f, F_SIT, F_SIT + 4)
            for s in "LR":
                place, lift = foot_place(s, f)
                m = place @ foot_idle[s]
                m = Matrix.Translation((0, 0, lift)) @ m
                tg[s].matrix_world = m
                fwd = place.to_3x3() @ Vector((0, -1, 0))
                pole[s].matrix_world = Matrix.Translation(m.translation + fwd * 0.8 + Vector((0, 0, 0.5)))
        elif f >= F_REACH0 - 4:
            leg_w = ramp(f, F_REACH0 - 4, F_REACH0) * (1.0 - ramp(f, F_SETTLE1, F_END))
            for s in "LR":
                fwd_b = seat_body(f).to_3x3() @ Vector((0, -1, 0))
                if f < F_PULL0:
                    # вытягивает ноги вперёд, пятки чуть над полом
                    u = ramp(f, F_REACH0, F_REACH1)
                    base = seat_body(f) @ foot_sit[s]
                    m = Matrix.Translation(fwd_b * HEEL_REACH * u + Vector((0, 0, 0.03 * math.sin(math.pi * u)))) @ base
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
                    m = Matrix.Translation((0, 0, 0.025 * math.sin(math.pi * u))) @ m
                tg[s].matrix_world = m
                pole[s].matrix_world = Matrix.Translation(m.translation + fwd_b * 0.8 + Vector((0, 0, 0.6)))
        else:
            leg_w = 0.0
        for c in leg_cons:
            c.influence = leg_w
            c.keyframe_insert("influence", frame=f)
        for s in "LR":
            tg[s].keyframe_insert("location", frame=f)
            tg[s].keyframe_insert("rotation_euler", frame=f)
            pole[s].keyframe_insert("location", frame=f)

        # --- правая рука на спинке ---
        if f < 60:
            hand_w = ramp(f, 1, F_GRAB) * (1.0 - ramp(f, F_RELEASE, 58))
            hm = hand_on_chair(chair_mat(*chairs[min(f, F_RELEASE)]))   # отпустил — рука уходит от того места
            if f > F_RELEASE:
                hm = Matrix.Translation(B.to_3x3() @ Vector((0.0, 0.10, 0.06)) * ramp(f, F_RELEASE, 58)) @ hm
            hand_t.matrix_world = hm
            bodyrot = B.to_3x3()
            sh = B @ shoulder_r
            elbow.matrix_world = Matrix.Translation(sh + bodyrot @ Vector((-0.5, 0.45, -0.35)))
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
        if f < F_RELEASE + 4:
            look = (cm @ GRAB).lerp(B @ Vector((0, -1.5, 1.2)), 1.0 - ramp(f, 0, F_GRAB))
        elif f < F_SEATED:
            look = head + fwd * 1.4 + Vector((0, 0, -0.75))
        else:
            look = head + fwd * 1.6 + Vector((0, 0, -0.35))
        looks.append(look)

    # взгляд сглажен (окно 11 кадров) — без рывков на сменах фаз
    sm = []
    for i in range(len(looks)):
        acc, n = Vector(), 0
        for j in range(max(0, i - 5), min(len(looks), i + 6)):
            acc += looks[j]
            n += 1
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

    # --- экспорт клипа ---
    ad = arm.animation_data
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    tr = ad.nla_tracks.new()
    tr.name = "ChairSit"
    tr.strips.new("ChairSit", 0, act)
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
        "fps": FPS, "frames": LEN + 1,
        "marks": {"grab": F_GRAB, "release": F_RELEASE, "sit": F_SIT, "land": F_LAND, "seated": F_SEATED,
                  "swivel": F_SWIVEL, "pull0": F_PULL0, "pull1": F_PULL1, "end": F_END},
        # где стоит перед тем, как сесть (кадр sit): точка в пространстве SitSpot и поворот, рад
        "stand": g((0.35, 0.65, 0.0)) + [round(math.radians(90.0), 4)],
        "start": g((FOOT_START[0], FOOT_START[1], 0.0)) + [0.0],
        # кресло: x, y, z, поворот (рад, вокруг Y; 0 — сиденьем к столу)
        "chair": [g((c[0], c[1], c[3])) + [round(math.radians(c[2]), 4)] for c in chairs],
        "look": [g(v) for v in sm],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    scene.frame_set(0)
    return {"glb": OUT, "json": OUT_JSON, "frames": LEN + 1}


if __name__ == "__main__":
    result = main()
