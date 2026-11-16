# Перенос анимаций Quaternius «Universal Animation Library» (CC0) на скелет Юрчика v3.
#
# Источник: tools/blender/ual/UAL1_Standard.glb (без root motion), лицензия CC0 —
#   https://quaternius.itch.io/universal-animation-library
# Цель:     скелет «Yurchik3» из tools/blender/yurchik_v3.blend (15 костей тела + по 15 костей пальцев, A-поза).
#           Пальцы не переносятся: в клипах они в покое (кулак), позу пальцев задаёт игра.
#
# Как переносим: для каждой нашей кости берём кость-источник и её поворот относительно
# собственной rest-позы в мировых осях (delta). Rest-позы у скелетов разные (у них T-поза,
# у нас A-поза), поэтому сначала доворачиваем нашу кость так, чтобы в rest она смотрела туда же,
# куда кость-источник (q0), и уже потом применяем delta:  world = delta · q0 · rest_our.
# Ступни берём без q0 — чтобы сохранить наш разворот носков.
#
# Стойка, ходьба, ходьба назад и бег (Idle, Walk, WalkBack, Run) не переносятся, а строятся
# процедурно — make_cycle() и таблица LOCOMOTION ниже. Остальные клипы (удары, броски, смерть) — из UAL.
#
# Запуск (из корня проекта, Blender 5.2+):
#   blender -b tools/blender/yurchik_v3.blend --python tools/blender/retarget_ual_yurchik.py
# Скрипт перезаписывает анимации в yurchik_v3.blend и экспортирует assets/models/yurchik.gltf
# (модель + анимации). Если пересобрать модель build_yurchik_v3.py — запустить этот скрипт снова.
import bpy, os, sys, json, math
from mathutils import Matrix, Vector, Quaternion

ROOT = os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath), "..", ".."))
SRCS = {
    "UAL1": os.path.join(ROOT, "tools", "blender", "ual", "UAL1_Standard.glb"),
    "UAL2": os.path.join(ROOT, "tools", "blender", "ual", "UAL2_Standard.glb"),
}
OUT = os.path.join(ROOT, "assets", "models", "yurchik.gltf")
FPS = 30

# наша кость → кость-источник
MAP = {
    "Pelvis": "pelvis", "Spine": "spine_03", "Head": "Head",
    "UpperArmL": "upperarm_l", "ForearmL": "lowerarm_l", "HandL": "hand_l",
    "UpperArmR": "upperarm_r", "ForearmR": "lowerarm_r", "HandR": "hand_r",
    "ThighL": "thigh_l", "ShinL": "calf_l", "FootL": "foot_l",
    "ThighR": "thigh_r", "ShinR": "calf_r", "FootR": "foot_r",
}
NO_ALIGN = {"FootL", "FootR"}

# имя в игре ← (библиотека, клип-источник, задом наперёд)
CLIPS = [
    ("Sprint", "UAL1", "Sprint_Loop", False),
    # удар молотком: из «рубки дерева» — замах (кадры 18–28) → удар (0–6) → доводка (до 14)
    ("Attack", "UAL2", "TreeChopping_Loop", False, [(18, 28), (0, 14)]),
    # стойка «готов к удару» (ПКМ): молоток занесён у головы — кадр 19 рубки; играется на верх тела
    ("AimIdle", "UAL2", "TreeChopping_Loop", False, [(19, 19), (19, 19)]),
    # удары кулаком — когда молоток убран в сумку (Q): джеб и кросс по очереди
    ("Punch", "UAL1", "Punch_Jab", False),
    ("Punch2", "UAL1", "Punch_Cross", False),        # второй удар — чередуется с первым
    ("HitChest", "UAL1", "Hit_Chest", False),
    ("HitHead", "UAL1", "Hit_Head", False),
    ("Death", "UAL1", "Death01", False),
    ("Interact", "UAL1", "Interact", False),
    ("PickUp", "UAL1", "PickUp_Table", False),
    # MVP: бросок, лечение, вырывание из захвата, падение и подъём
    ("Throw", "UAL2", "OverhandThrow", False),
    ("Consume", "UAL2", "Consume", False),
    ("Push", "UAL1", "Push_Loop", False),
    ("Knockback", "UAL2", "Hit_Knockback", False),
    ("GetUp", "UAL2", "LayToIdle", False),
]


# ----------------------------------------------------------------------------- процедурная локомоция
# Стойка, ходьба, ходьба назад и бег строятся здесь, а не переносятся из UAL: у клипов библиотеки
# сгорбленный бег и «деловая» ходьба, а нужна расслабленная походка в духе старых ПК-песочниц:
# прямой корпус, свободный мах руками, мягкое покачивание таза; бег спортивный, руки согнуты.
#
# Цикл задан по фазе p ∈ [0, 1) правой ноги (левая — p + 0.5). Углы в градусах.
# Юрчик смотрит в -Y, +X — его левый бок, Z — вверх. Параметры (k):
#   hip_mid / hip_amp / hip_peak — бедро: среднее, размах, фаза, где нога дальше всего впереди;
#   lean, pelvis_lean, lean_pulse — наклон корпуса и таза вперёд, «пружина» корпуса дважды за цикл;
#   pelvis_yaw, shoulder_yaw — таз доворачивается за ногой, плечи навстречу;
#   sway, pelvis_roll, spine_bend — таз над опорной ногой, крен таза, сколько крена гасит корпус;
#   head_pitch, head_nod, head_follow — голова;
#   arm_mid / arm_amp / arm_phase / arm_lag — плечо (рука в противофазе своей ноге);
#   elbow / elbow_amp / elbow_lag — сгиб локтя; arm_out, forearm_in, arm_in, hand_in — разводка рук;
#   hammer_arm, hammer_twist, hammer_flex — рука с молотком машет меньше, кисть доворачивает рукоять
#   вокруг предплечья и сгибается в запястье (не больше ~25°: кисть видна от первого лица и без молотка,
#   сильный сгиб выглядит как вывих);
#   wrist — расслабленная кисть; flight / flight_from — подлёт в фазе полёта (только бег);
#   lean_side — постоянный перенос веса вбок (стойка: вес на правой ноге).
# Куртка у Юрчика объёмная: arm_out и forearm_in держат кисти снаружи от неё, иначе запястья проходят сквозь полы.
# Кривые по фазе ноги: knee — сгиб колена, foot — наклон опорной стопы (+ носок вверх),
# ankle — стопа в махе относительно голени, plant — сколько стопа держит землю (1) или идёт за голенью (0).
BASE = {
    "hip_mid": 0.0, "hip_amp": 0.0, "hip_peak": 0.9,
    "lean": 0.0, "pelvis_lean": 0.0, "lean_pulse": 0.0,
    "pelvis_yaw": 0.0, "shoulder_yaw": 1.0,
    "sway": 0.0, "pelvis_roll": 0.0, "spine_bend": 0.6, "lean_side": 0.0,
    "head_pitch": 0.0, "head_nod": 0.0, "head_follow": 0.3,
    "arm_mid": 0.0, "arm_amp": 0.0, "arm_phase": 0.4, "arm_lag": 0.05,
    "elbow": 10.0, "elbow_amp": 0.0, "elbow_lag": 0.1,
    "arm_out": 0.15, "forearm_in": 0.0, "arm_in": 0.0, "hand_in": 0.0,
    "hammer_arm": 0.8, "hammer_twist": 50.0, "hammer_flex": 0.0, "wrist": 0.0,
    "flight": 0.0, "flight_from": 0.32,
}

LOCOMOTION = {
    # спокойная стойка: вес на правой ноге, левое колено чуть согнуто, руки висят, лёгкое покачивание и дыхание
    "Idle": {
        "frames": 90,
        "k": dict(BASE, sway=0.012, pelvis_roll=1.5, lean_side=0.018, lean=1.0, lean_pulse=1.2,
                  head_pitch=-1.0, head_nod=1.0, arm_mid=-3.0, arm_amp=1.5, elbow=14.0, elbow_amp=2.0,
                  arm_out=0.30, forearm_in=-0.08, wrist=2.0, hammer_twist=0.0, hammer_flex=20.0),
        "knee": [(0.0, 6), (0.5, 6)],
        "foot": [(0.0, 0), (0.5, 0)],
        "ankle": [(0.0, 0), (0.5, 0)],
        "plant": [(0.0, 1), (0.5, 1)],
    },
    # прогулочный шаг: опора 0–0.6, мах 0.6–1; корпус прямой, руки свободно машут, локти чуть согнуты
    "Walk": {
        "frames": 34,                  # ~1.13 с на цикл — ~106 шагов в минуту, без спешки
        "k": dict(BASE, hip_mid=2.0, hip_amp=22.0, hip_peak=0.95, lean=2.0, pelvis_lean=1.0, lean_pulse=0.8,
                  pelvis_yaw=5.0, shoulder_yaw=1.2, sway=0.018, pelvis_roll=4.0, spine_bend=0.7,
                  head_pitch=1.0, head_nod=1.2, arm_mid=-2.0, arm_amp=20.0, arm_phase=0.45, arm_lag=0.06,
                  elbow=16.0, elbow_amp=10.0, elbow_lag=0.08, arm_out=0.32, forearm_in=-0.1, hammer_arm=0.7, wrist=6.0,
                  hammer_twist=0.0, hammer_flex=20.0),
        "knee": [(0.0, 4), (0.12, 16), (0.35, 6), (0.55, 34), (0.7, 62), (0.85, 30), (0.96, 4)],
        "foot": [(0.0, 16), (0.1, 0), (0.4, -2), (0.58, -28), (0.72, -10), (0.9, 12)],
        "ankle": [(0.0, 0), (0.6, -14), (0.72, -4), (0.85, 4), (0.95, 2)],
        "plant": [(0.0, 1), (0.55, 1), (0.66, 0), (0.92, 0), (0.98, 1)],
    },
    # спортивный бег: небольшой наклон вперёд, руки согнуты под прямым углом и работают перед корпусом
    "Run": {
        "frames": 20,                  # 0.667 с — ~180 шагов в минуту
        "k": dict(BASE, hip_mid=6.0, hip_amp=30.0, hip_peak=0.9, lean=10.0, pelvis_lean=5.0, lean_pulse=2.5,
                  pelvis_yaw=7.0, shoulder_yaw=1.2, sway=0.02, pelvis_roll=5.0, spine_bend=0.6,
                  head_pitch=4.0, head_nod=1.8, arm_mid=-4.0, arm_amp=32.0, arm_phase=0.4, arm_lag=0.04,
                  elbow=92.0, elbow_amp=12.0, elbow_lag=0.08, arm_out=0.4, forearm_in=-0.12,
                  arm_in=0.02, hand_in=0.0, hammer_arm=0.75, wrist=6.0, flight=0.035, flight_from=0.32),
        "knee": [(0.0, 20), (0.12, 40), (0.3, 22), (0.45, 75), (0.6, 105), (0.78, 60), (0.9, 20), (0.96, 14)],
        "foot": [(0.0, 8), (0.08, 0), (0.22, -4), (0.34, -38), (0.5, -26), (0.7, -6), (0.88, 6)],
        "ankle": [(0.0, 0), (0.3, -8), (0.45, -16), (0.6, -5), (0.8, 6), (0.92, 5)],
        "plant": [(0.0, 1), (0.28, 1), (0.42, 0), (0.86, 0), (0.95, 1)],
    },
}


def cyc(keys, p):
    """Гладкая замкнутая кривая (Catmull-Rom) по ключам [(фаза, значение)]."""
    n = len(keys)
    ext = [(keys[i % n][0] + (i // n), keys[i % n][1]) for i in range(-1, 2 * n + 1)]
    p = p % 1.0
    for j in range(1, len(ext) - 2):
        (p0, v0), (p1, v1), (p2, v2), (p3, v3) = ext[j - 1], ext[j], ext[j + 1], ext[j + 2]
        if p1 <= p < p2:
            t = (p - p1) / (p2 - p1)
            m1 = (v2 - v0) / (p2 - p0) * (p2 - p1)
            m2 = (v3 - v1) / (p3 - p1) * (p2 - p1)
            t2, t3 = t * t, t * t * t
            return (2 * t3 - 3 * t2 + 1) * v1 + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * v2 + (t3 - t2) * m2
    return keys[0][1]


def make_cycle(dst, order, name, spec, reverse=False):
    """Строит зацикленный клип name на скелете Юрчика по спецификации из LOCOMOTION: позы по фазе,
    таз опускается так, чтобы опорная стопа стояла на земле (плюс подлёт в фазе полёта).
    reverse — проиграть цикл задом наперёд (ходьба назад). Возвращает статистику, как bake_clip."""
    X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    k = spec["k"]
    frames = spec["frames"]

    def R(axis, deg):
        return Quaternion(axis, math.radians(deg))

    bones = dst.data.bones
    rest_q = {n: bones[n].matrix_local.to_quaternion() for n in order}
    rest_dir = {n: (bones[n].tail_local - bones[n].head_local).normalized() for n in order}
    ankle_z = bones["FootL"].head_local.z
    toe_z = bones["FootL"].tail_local.z

    def aim(n, d):  # повернуть кость из rest так, чтобы она смотрела в d (без лишнего скручивания)
        return rest_dir[n].rotation_difference(d.normalized()) @ rest_q[n]

    def sag(side, ang, out):  # направление в плоскости шага: ang от «вниз», > 0 — вперёд
        a = math.radians(ang)
        return Vector((side * out, -math.sin(a), -math.cos(a)))

    def pose(p):
        ph = {-1: p % 1.0, 1: (p + 0.5) % 1.0}          # -1 — правая, +1 — левая
        hip = {s: k["hip_mid"] + k["hip_amp"] * math.cos(2 * math.pi * (ph[s] - k["hip_peak"])) for s in ph}
        yaw = k["pelvis_yaw"] * (hip[-1] - hip[1]) / (2 * k["hip_amp"]) if k["hip_amp"] else 0.0
        syaw = -yaw * k["shoulder_yaw"]
        st = math.cos(2 * math.pi * (p - 0.15))         # +1 — середина опоры на правую, -1 — на левую
        roll = k["pelvis_roll"] * st + k["lean_side"] * 120.0
        sway = -k["sway"] * st - k["lean_side"]
        lean = k["lean"] + k["lean_pulse"] * math.cos(4 * math.pi * (p - 0.1))
        rot = {"Pelvis": R(Z, yaw) @ R(Y, roll) @ R(X, k["pelvis_lean"]) @ rest_q["Pelvis"],
               "Spine": R(Z, syaw) @ R(Y, -roll * k["spine_bend"]) @ R(X, lean) @ rest_q["Spine"],
               "Head": R(Z, syaw * k["head_follow"]) @ R(Y, roll * 0.25)
               @ R(X, k["head_pitch"] + k["head_nod"] * math.cos(4 * math.pi * (p - 0.2))) @ rest_q["Head"]}
        for s, sfx in ((1, "L"), (-1, "R")):
            ry = R(Z, yaw)
            knee = cyc(spec["knee"], ph[s])
            if k["lean_side"] and s > 0:                 # стойка: ненагруженная левая нога чуть согнута
                knee += 8.0
            rot["Thigh" + sfx] = aim("Thigh" + sfx, ry @ sag(s, hip[s], 0.04))
            rot["Shin" + sfx] = aim("Shin" + sfx, ry @ sag(s, hip[s] - knee, 0.03))
            on_ground = ry @ R(X, -cyc(spec["foot"], ph[s])) @ rest_q["Foot" + sfx]
            sd = rot["Shin" + sfx] @ rest_q["Shin" + sfx].inverted()
            in_air = sd @ R(X, -cyc(spec["ankle"], ph[s])) @ rest_q["Foot" + sfx]
            w = min(max(cyc(spec["plant"], ph[s]), 0.0), 1.0)
            rot["Foot" + sfx] = in_air.slerp(on_ground, w)
            # рука в противофазе своей ноге
            amp = k["arm_amp"] * (k["hammer_arm"] if s < 0 else 1.0)
            pa = ph[s] - k["arm_phase"] - k["arm_lag"]
            c = math.cos(2 * math.pi * pa)
            fwd = max(c, 0.0)
            sh = k["arm_mid"] + amp * c
            el = k["elbow"] + k["elbow_amp"] * math.cos(2 * math.pi * (ph[s] - k["arm_phase"] - k["elbow_lag"]))
            rs = R(Z, syaw)
            rot["UpperArm" + sfx] = aim("UpperArm" + sfx, rs @ sag(s, sh, k["arm_out"] - k["arm_in"] * fwd))
            rot["Forearm" + sfx] = aim("Forearm" + sfx,
                                       rs @ sag(s, sh + el, -k["forearm_in"] - k["hand_in"] * fwd))
            fd = rot["Forearm" + sfx] @ rest_q["Forearm" + sfx].inverted()
            twist = k["hammer_twist"] if s < 0 else 0.0
            fdir = rot["Forearm" + sfx] @ Vector((0, 1, 0))
            flop = k["wrist"] * (0.5 if s < 0 else 1.0) * math.sin(2 * math.pi * (pa - 0.1))
            flex = k["hammer_flex"] if s < 0 else 0.0
            rot["Hand" + sfx] = R(rs @ X, flop + flex) @ R(fdir, twist) @ fd @ rest_q["Hand" + sfx]
        mats = {}
        for n in order:
            b = bones[n]
            if b.parent is None:
                loc = b.head_local + Vector((sway, 0, 0))
            else:
                rel = b.parent.matrix_local.inverted() @ b.matrix_local
                loc = (mats[b.parent.name] @ rel).translation
            mats[n] = Matrix.Translation(loc) @ rot[n].to_matrix().to_4x4()

        def ground(f):  # насколько стопа над землёй: ниже всего пятка (лодыжка) или носок
            m = mats[f]
            toe = m.translation + m.to_3x3() @ Vector((0, bones[f].length, 0))
            return min(m.translation.z - ankle_z, toe.z - toe_z)

        lift = -min(ground("FootL"), ground("FootR"))
        q = p % 0.5
        if k["flight"] and k["flight_from"] < q < 0.5:
            lift += k["flight"] * math.sin(math.pi * (q - k["flight_from"]) / (0.5 - k["flight_from"]))
        up = Matrix.Translation((0, 0, lift))
        return {n: up @ m for n, m in mats.items()}

    dad = dst.animation_data
    ac = bpy.data.actions.new("Yur_" + name)
    ac.use_fake_user = True
    dad.action = ac
    for pb in dst.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    feet = {"FootL": [], "FootR": []}
    for i in range(frames + 1):
        t = i / frames
        mats = pose(1.0 - t if reverse else t)
        for n in order:
            b = bones[n]
            pb = dst.pose.bones[n]
            if b.parent is None:
                basis = b.matrix_local.inverted() @ mats[n]
            else:
                rel = b.parent.matrix_local.inverted() @ b.matrix_local
                basis = rel.inverted() @ mats[b.parent.name].inverted() @ mats[n]
            loc, q, _ = basis.decompose()
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=i, group=n)
            if b.parent is None:
                pb.location = loc
                pb.keyframe_insert("location", frame=i, group=n)
        for f in feet:
            feet[f].append(mats[f].translation.copy())
    # скорость опорной стопы: с такой скоростью должен идти герой, чтобы ноги не скользили
    speeds = []
    for pts in feet.values():
        zmin = min(v.z for v in pts)
        for j in range(frames):
            if pts[j].z < zmin + 0.01 and pts[j + 1].z < zmin + 0.01:
                speeds.append(abs(pts[j + 1].y - pts[j].y) * FPS)
    speeds.sort()
    tr = dad.nla_tracks.new()
    tr.name = name
    tr.mute = True
    st = tr.strips.new(ac.name, 0, ac)
    st.name = name
    dad.action = None
    return {"frames": frames + 1, "len_s": round(frames / FPS, 3),
            "foot_speed": round(speeds[len(speeds) // 2], 3) if speeds else 0.0}


def rot_between(a, b):
    a = a.normalized(); b = b.normalized()
    return a.rotation_difference(b)


def bake_clip(sc, src, dst, sac, name, reverse, q0, src_rest, dst_rest, hip_scale, order, segs=None):
    sw, dw = src.matrix_world, dst.matrix_world
    sad = src.animation_data
    sad.action = sac
    if sad.action_slot is None and len(sac.slots):
        sad.action_slot = sac.slots[0]
    f0, f1 = [int(round(x)) for x in sac.frame_range]
    frames = list(range(f0, f1 + 1))
    if segs:  # вырезка: список отрезков кадров источника (включительно)
        frames = [f for a, b in segs for f in range(a, b + 1)]

    dad = dst.animation_data
    ac = bpy.data.actions.new("Yur_" + name)
    ac.use_fake_user = True
    dad.action = ac
    for pb in dst.pose.bones:
        pb.rotation_mode = 'QUATERNION'

    feet = {"FootL": [], "FootR": []}
    for i, f in enumerate(frames):
        sc.frame_set(frames[-1 - i] if reverse else f)
        # целевые матрицы костей в пространстве нашего скелета
        mats = {}
        for n in order:
            s = MAP[n]
            sp = sw @ src.pose.bones[s].matrix
            delta = sp.to_quaternion() @ src_rest[s].to_quaternion().inverted()
            rot = dw.inverted().to_quaternion() @ (delta @ q0[n] @ dst_rest[n].to_quaternion())
            b = dst.data.bones[n]
            if b.parent is None:
                off = (sp.translation - src_rest[s].translation) * hip_scale
                loc = dw.inverted() @ (dst_rest[n].translation + off)
            else:
                rel = b.parent.matrix_local.inverted() @ b.matrix_local
                loc = (mats[b.parent.name] @ rel).translation
            mats[n] = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
        for n in order:
            b = dst.data.bones[n]
            pb = dst.pose.bones[n]
            if b.parent is None:
                basis = b.matrix_local.inverted() @ mats[n]
            else:
                rel = b.parent.matrix_local.inverted() @ b.matrix_local
                basis = rel.inverted() @ mats[b.parent.name].inverted() @ mats[n]
            loc, q, _ = basis.decompose()
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=i, group=n)
            if b.parent is None:
                pb.location = loc
                pb.keyframe_insert("location", frame=i, group=n)
        for k in feet:
            feet[k].append(tuple((dw @ mats[k]).translation))

    # скорость «опорной» ступни: где нога ниже всего, она стоит на земле
    speeds = []
    n_fr = len(frames)
    for k, pts in feet.items():
        zmin = min(p[2] for p in pts)
        for j in range(n_fr - 1):
            if pts[j][2] < zmin + 0.025 and pts[j + 1][2] < zmin + 0.025:
                speeds.append((pts[j + 1][1] - pts[j][1]) * FPS)
    speeds.sort()

    tr = dad.nla_tracks.new()
    tr.name = name          # имя анимации в glTF / Godot
    tr.mute = True
    st = tr.strips.new(ac.name, 0, ac)
    st.name = name
    dad.action = None
    return {"frames": n_fr, "len_s": round((n_fr - 1) / FPS, 3),
            "foot_speed": round(speeds[len(speeds) // 2], 3) if speeds else 0.0}


def main():
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.render.fps_base = 1.0
    dst = bpy.data.objects["Yurchik3"]

    # старые анимации Юрчика — убрать (скрипт можно запускать повторно)
    dad = dst.animation_data or dst.animation_data_create()
    for tr in list(dad.nla_tracks):
        dad.nla_tracks.remove(tr)
    dad.action = None
    for ac in list(bpy.data.actions):
        if ac.name.startswith("Yur_"):
            bpy.data.actions.remove(ac)

    order = [b.name for b in dst.data.bones if b.name in MAP]  # родители раньше детей
    dw = dst.matrix_world
    dst_rest = {n: (dw @ dst.data.bones[n].matrix_local) for n in MAP}
    stats = {}

    for key, path in SRCS.items():
        clips = [c for c in CLIPS if c[1] == key]
        if not clips:
            continue
        before = set(bpy.data.objects)
        before_actions = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=path)
        imported = [o for o in bpy.data.objects if o not in before]
        src = [o for o in imported if o.type == 'ARMATURE'][0]
        src_actions = {a.name: a for a in bpy.data.actions if a not in before_actions}
        sad = src.animation_data or src.animation_data_create()
        for tr in list(sad.nla_tracks):
            sad.nla_tracks.remove(tr)

        sw = src.matrix_world
        src_rest = {n: (sw @ src.data.bones[n].matrix_local) for n in MAP.values()}

        def bdir(m):  # направление кости (ось Y) в мире
            return (m.to_3x3() @ Vector((0, 1, 0))).normalized()

        q0 = {n: (Quaternion() if n in NO_ALIGN else rot_between(bdir(dst_rest[n]), bdir(src_rest[s])))
              for n, s in MAP.items()}
        hip_scale = dst.data.bones["Pelvis"].head_local.z / src.data.bones["pelvis"].head_local.z

        for name, _, sname, reverse, *rest in clips:
            sac = src_actions.get(sname) or next(a for n, a in src_actions.items() if n.split(".")[0] == sname)
            stats[name] = bake_clip(sc, src, dst, sac, name, reverse, q0, src_rest, dst_rest, hip_scale, order,
                                    rest[0] if rest else None)

        # источник больше не нужен
        for o in imported:
            bpy.data.objects.remove(o, do_unlink=True)
        for a in src_actions.values():
            bpy.data.actions.remove(a)
        for blk in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
            for d in list(blk):
                if d.users == 0:
                    blk.remove(d)
    for name, spec in LOCOMOTION.items():
        stats[name] = make_cycle(dst, order, name, spec)
    stats["WalkBack"] = make_cycle(dst, order, "WalkBack", LOCOMOTION["Walk"], reverse=True)
    return stats


def export():
    sc = bpy.context.scene
    arm = bpy.data.objects["Yurchik3"]
    body = bpy.data.objects["Yurchik3Mesh"]
    ham = bpy.data.objects["Hammer3"]
    ham_l = bpy.data.objects["HammerL3"]          # молоток в левой руке — пока правая держит телефон
    for o in sc.objects:
        o.select_set(o in (arm, body, ham, ham_l))
    bpy.context.view_layer.objects.active = arm
    ren = [(arm, "Yurchik"), (body, "YurchikMesh"), (ham, "Hammer"), (ham_l, "HammerL")]
    old = [(o, o.name) for o, _ in ren]
    try:
        for o, n in ren:
            o.name = n
        bpy.ops.export_scene.gltf(
            filepath=OUT, use_selection=True, use_active_scene=True, export_format='GLTF_SEPARATE',
            export_keep_originals=True, export_apply=False, export_skins=True,
            export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
            export_frame_step=1, export_optimize_animation_size=True, export_anim_single_armature=True,
            export_def_bones=False, export_reset_pose_bones=True, export_bake_animation=False)
    finally:
        for o, n in old:
            o.name = n


stats = main()
bpy.ops.wm.save_mainfile()
export()
print("RETARGET" + json.dumps(stats))
