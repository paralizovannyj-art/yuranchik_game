# Перенос анимаций игрока Garry's Mod (SMD, скелет ValveBiped) на скелет Юрчика v3.
#
# Источник: https://github.com/robotboy655/gmod-animations — исходники SMD/QC анимаций игрока GMod.
#   Авторы: Maxime Lebled, Facepunch Studios LTD / Valve Software (см. assets/animations/gmod/CREDITS.txt).
#   Контент — CC BY-ND 3.0 и Source SDK EULA: только для локальной сборки, не для публикации.
# Цель:     скелет «Yurchik3» из tools/blender/yurchik_v3.blend.
# Результат: assets/animations/gmod/yurchik_gmod.glb — модель + только эти анимации; Godot импортирует
#   файл как AnimationLibrary «gmod» (см. yurchik_gmod.glb.import), yurchik_anim.gd подключает её к модели.
#
# Как переносим (тот же приём, что в retarget_ual_yurchik.py): SMD читается прямо здесь (формат текстовый,
# Blender Source Tools не нужен), для каждого кадра считаются мировые матрицы костей ValveBiped.
# Для нашей кости берём кость-источник и её поворот относительно rest-позы источника (reference.smd)
# в мировых осях — delta. Rest-позы разные, поэтому сначала доворачиваем нашу кость так, чтобы в rest
# она смотрела туда же, куда кость-источник (q0):  world = delta · q0 · rest_our.
# Ступни и голова — без q0 (сохраняем наш разворот носков и посадку головы).
# Оси совпадают: у ValveBiped и у Юрчика Z вверх, вперёд -Y, левый бок +X; единицы — дюймы,
# смещение таза масштабируется по высоте таза.
# Root motion (LX LY в QC) у циклов вырезается: таз остаётся на месте, а скорость, с которой должен
# идти герой, чтобы опорная стопа не скользила, печатается в отчёте (foot_speed) и сохраняется
# в assets/animations/gmod/clips.json — её читает yurchik_anim.gd.
# Пальцы не переносятся: правая кисть держит молоток, позу пальцев задаёт модель.
#
# Запуск (из корня проекта, Blender 5.2+):
#   git clone --depth 1 https://github.com/robotboy655/gmod-animations tools/blender/gmod-animations
#   blender -b tools/blender/yurchik_v3.blend --python tools/blender/retarget_gmod_yurchik.py
#   (другой путь к исходникам:  ... --python tools/blender/retarget_gmod_yurchik.py -- <путь>)
# yurchik_v3.blend не сохраняется — скрипт только читает скелет и пишет GLB.
import bpy, os, sys, json, math
from mathutils import Matrix, Vector, Quaternion, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath), "..", ".."))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SRC = os.path.abspath(ARGS[0]) if ARGS else os.path.join(ROOT, "tools", "blender", "gmod-animations")
OUT_DIR = os.path.join(ROOT, "assets", "animations", "gmod")
OUT = os.path.join(OUT_DIR, "yurchik_gmod.glb")
FPS = 30            # кадры клипов пересэмплируются в 30 к/с (как у остальных анимаций Юрчика)
INCH = 0.0254
VB = "ValveBiped.Bip01_"

# наша кость → (кость-источник для поворота, начало и конец направления кости в rest для q0)
MAP = {
    "Pelvis": ("Pelvis", "Pelvis", "Spine2"),
    "Spine": ("Spine4", "Spine", "Neck1"),
    "Head": ("Head1", None, None),
    "UpperArmL": ("L_UpperArm", "L_UpperArm", "L_Forearm"),
    "ForearmL": ("L_Forearm", "L_Forearm", "L_Hand"),
    "HandL": ("L_Hand", "L_Hand", "L_Finger2"),
    "UpperArmR": ("R_UpperArm", "R_UpperArm", "R_Forearm"),
    "ForearmR": ("R_Forearm", "R_Forearm", "R_Hand"),
    "HandR": ("R_Hand", "R_Hand", "R_Finger2"),
    "ThighL": ("L_Thigh", "L_Thigh", "L_Calf"),
    "ShinL": ("L_Calf", "L_Calf", "L_Foot"),
    "FootL": ("L_Foot", None, None),
    "ThighR": ("R_Thigh", "R_Thigh", "R_Calf"),
    "ShinR": ("R_Calf", "R_Calf", "R_Foot"),
    "FootR": ("R_Foot", None, None),
}

# имя в игре ← (файл SMD, fps источника, флаги). Флаги:
#   loop — зацикленный клип; inplace — убрать горизонтальное смещение таза (root motion);
#   ground — опустить/поднять клип целиком, чтобы самая низкая стопа стояла на земле;
#   frames=(a, b) — вырезка кадров источника.
# fps и вырезки — из gm_base_m.qci / gm_sequences.qci.
CLIPS = [
    # ---- базовый набор: стойка, ходьба, бег, присед, прыжок
    ("Idle", "base_m/Idle02.smd", 30, {"loop", "ground"}),
    ("Walk", "base_m/WalkN.smd", 30, {"loop", "inplace", "ground"}),
    ("WalkBack", "base_m/WalkS.smd", 30, {"loop", "inplace", "ground"}),
    ("WalkLeft", "base_m/WalkW.smd", 30, {"loop", "inplace", "ground"}),
    ("WalkRight", "base_m/WalkE.smd", 30, {"loop", "inplace", "ground"}),
    ("Run", "base_m/runN.smd", 30, {"loop", "inplace", "ground"}),
    ("RunBack", "base_m/runS.smd", 30, {"loop", "inplace", "ground"}),
    ("RunLeft", "base_m/runW.smd", 30, {"loop", "inplace", "ground"}),
    ("RunRight", "base_m/runE.smd", 30, {"loop", "inplace", "ground"}),
    ("CrouchIdle", "base_m/crouch_idle.smd", 20, {"loop", "ground"}),
    ("CrouchWalk", "base_m/crouch_walkN.smd", 30, {"loop", "inplace", "ground"}),
    ("CrouchWalkBack", "base_m/crouch_walkS.smd", 30, {"loop", "inplace", "ground"}),
    ("CrouchWalkLeft", "base_m/crouch_walkW.smd", 30, {"loop", "inplace", "ground"}),
    ("CrouchWalkRight", "base_m/crouch_walkE.smd", 30, {"loop", "inplace", "ground"}),
    ("Jump", "GMod/jump_c.smd", 30, {"inplace", "jump"}),   # собирается как $MakeJump — см. compose_jump
    ("JumpLand", "GMod/jump_land.smd", 60, {"inplace", "ground"}, (0, 40)),
    # ---- стойки
    ("IdleAngry", "base_m/Idle_Angry.smd", 25, {"loop", "ground"}),
    ("IdleScared", "base_m/Idle_scared.smd", 25, {"loop", "ground"}),
    ("IdleSubtle", "base_m/Idle_subtle.smd", 30, {"loop", "ground"}),
    ("FistsIdle", "GMod/fists_idle.smd", 30, {"loop", "ground"}),
    ("Cower", "base_m/Cower.smd", 30, {"ground"}),
    ("RunPanicked", "base_m/Run_panicked.smd", 30, {"loop", "inplace", "ground"}),
    ("Swim", "GMod/swim_n.smd", 50, {"loop", "inplace"}),
    ("SwimIdle", "GMod/swim_c.smd", 40, {"loop"}),
    ("Sit", "GMod/sit_generic.smd", 30, {"loop"}),
    ("SitZen", "GMod/sit_zen.smd", 30, {"loop"}),
    # ---- удары и бросок
    ("FistsAttack", "GMod/fists_attack_01.smd", 30, {"ground"}),
    ("MeleeHit1", "GMod/meleeweapon_hit1.smd", 30, {"ground"}),
    ("MeleeHit2", "GMod/meleeweapon_hit2.smd", 30, {"ground"}),
    ("MeleeHit3", "GMod/meleeweapon_hit3.smd", 30, {"ground"}),
    ("Melee2Attack", "GMod/melee2_attack_01.smd", 45, {"ground"}),
    ("Shove", "GMod/MeleeAttack01.smd", 36, {"ground"}),
    ("PunchA", "GMod/FightPose_PunchA.smd", 30, {"ground"}),
    ("PunchB", "GMod/FightPose_PunchB.smd", 30, {"ground"}),
    ("FistBlock", "GMod/FightPose_block.smd", 30, {"ground"}),
    ("GrenadeThrow", "GMod/grenThrow.smd", 30, {"ground"}),
    ("ItemDrop", "GMod/grenDrop.smd", 30, {"ground"}),
    ("ItemPlace", "GMod/grenPlace.smd", 30, {"ground"}),
    ("ItemGive", "GMod/Heal.smd", 30, {"ground"}),
    # ---- получил удар (flinching)
    ("FlinchHead", "flinching/head_01.smd", 30, {"ground"}),
    ("FlinchHead2", "flinching/head_02.smd", 30, {"ground"}),
    ("FlinchStomach", "flinching/stomach_01.smd", 30, {"ground"}),
    ("FlinchStomach2", "flinching/stomach_02.smd", 30, {"ground"}),
    ("FlinchBack", "flinching/back_01.smd", 30, {"ground"}),
    ("FlinchShoulderL", "flinching/shoulder_left.smd", 30, {"ground"}),
    ("FlinchShoulderR", "flinching/shoulder_right.smd", 30, {"ground"}),
    ("Flinch1", "flinching/flinch_01.smd", 30, {"ground"}),
    ("Flinch2", "flinching/flinch_02.smd", 30, {"ground"}),
    # ---- смерть
    ("Death1", "GMod/death_01.smd", 30, set()),
    ("Death2", "GMod/death_02.smd", 30, set()),
    ("Death3", "GMod/death_03.smd", 30, set()),
    ("Death4", "GMod/death_04.smd", 34, set()),
    # ---- жесты и «таунты»
    ("Wave", "GMod/gesture_wave.smd", 32, {"ground"}),
    ("Agree", "GMod/gesture_agree.smd", 36, {"ground"}),
    ("Disagree", "GMod/gesture_disagree.smd", 30, {"ground"}),
    ("Bow", "GMod/gesture_bow.smd", 32, {"ground"}),
    ("Beckon", "GMod/gesture_comeon.smd", 30, {"ground"}),
    ("Salute", "GMod/gesture_salute.smd", 30, {"ground"}),
    ("SignalForward", "GMod/signal_forward.smd", 30, {"ground"}),
    ("SignalHalt", "GMod/signal_halt.smd", 25, {"ground"}),
    ("SignalGroup", "GMod/signal_group.smd", 30, {"ground"}),
    ("Cheer", "base_m/Cheer1.smd", 20, {"ground"}),
    ("Dance", "GMod/taunt_dance.smd", 32, {"ground"}),
    ("Laugh", "GMod/taunt_laugh.smd", 35, {"ground"}),
    ("Muscle", "GMod/taunt_muscle.smd", 35, {"ground"}),
    ("Robot", "GMod/taunt_robot.smd", 35, {"ground"}),
    ("Persistence", "GMod/taunt_persistence.smd", 30, {"ground"}),
    # ---- переходы
    ("StandToCrouch", "transitions/Stand_to_crouch.smd", 30, {"inplace", "ground"}),
    ("CrouchToStand", "transitions/Crouch_to_stand.smd", 30, {"inplace", "ground"}),
]


# Сумка висит на правом боку, а у игрока GMod руки опущены вплотную к телу — правая проходила бы сквозь сумку.
# В этих клипах вся правая рука (плечо, предплечье, кисть) отводится наружу на BAG_OUT градусов вокруг оси корпуса
# «вперёд-назад»: мах вперёд-назад сохраняется, рука просто идёт снаружи сумки. Как bag_out в retarget_ual_yurchik.py.
# Удары, жесты, плавание и прочие клипы не трогаем — там рука должна идти точно как в источнике.
BAG_OUT = {"UpperArmR": 15.0, "ForearmR": 18.0, "HandR": 18.0}   # градусы: рука идёт вплотную к сумке
BAG_CLIPS = {"Idle", "Walk", "WalkBack", "WalkLeft", "WalkRight", "Run", "RunBack", "RunLeft", "RunRight",
             "CrouchIdle", "CrouchWalk", "CrouchWalkBack", "CrouchWalkLeft", "CrouchWalkRight", "Jump", "JumpLand",
             "IdleAngry", "IdleScared", "IdleSubtle", "RunPanicked", "StandToCrouch", "CrouchToStand"}


# ----------------------------------------------------------------------------- SMD
def find_file(rel):
    """Путь к SMD без учёта регистра (в репозитории имена записаны по-разному)."""
    d = SRC
    for part in rel.split("/"):
        names = {n.lower(): n for n in os.listdir(d)}
        if part.lower() not in names:
            raise FileNotFoundError(os.path.join(d, part))
        d = os.path.join(d, names[part.lower()])
    return d


def load_smd(path):
    """Читает SMD: возвращает список кадров {имя кости: мировая матрица (дюймы)}.
    Кость, которой нет в кадре, берётся из предыдущего кадра (так делает studiomdl)."""
    names, parent, frames = {}, {}, []
    mode, cur = None, None
    with open(path, encoding="latin-1") as fh:
        for ln in fh:
            t = ln.split()
            if not t:
                continue
            if t[0] in ("nodes", "skeleton", "triangles", "vertexanimation"):
                mode = t[0]
                continue
            if t[0] == "end":
                mode = None
                continue
            if mode == "nodes":
                q = ln.split('"')
                i = int(t[0])
                names[i] = q[1]
                parent[i] = int(q[2])
            elif mode == "skeleton":
                if t[0] == "time":
                    cur = dict(frames[-1]) if frames else {}
                    frames.append(cur)
                    continue
                v = [float(x) for x in t[1:7]]
                cur[int(t[0])] = Matrix.Translation(v[:3]) @ Euler(v[3:6], 'XYZ').to_matrix().to_4x4()
    out = []
    for fr in frames:
        world = {}

        def get(i):
            if i not in world:
                m = fr.get(i, Matrix.Identity(4))
                world[i] = m if parent[i] < 0 else get(parent[i]) @ m
            return world[i]

        out.append({names[i]: get(i) for i in names})
    return out


def resample(frames, src_fps, span):
    """Кадры источника (с вырезкой span) → кадры в FPS с интерполяцией матриц."""
    if span:
        frames = frames[span[0]:span[1] + 1]
    n = len(frames)
    if n < 2:
        return frames
    length = (n - 1) / src_fps
    count = max(2, int(round(length * FPS)) + 1)
    out = []
    for i in range(count):
        x = min(i / FPS * src_fps, n - 1)
        a = int(math.floor(x))
        b = min(a + 1, n - 1)
        t = x - a
        fr = {}
        for k, ma in frames[a].items():
            mb = frames[b].get(k, ma)
            la, ra, _ = ma.decompose()
            lb, rb, _ = mb.decompose()
            fr[k] = Matrix.Translation(la.lerp(lb, t)) @ ra.slerp(rb, t).to_matrix().to_4x4()
        out.append(fr)
    return out


# ----------------------------------------------------------------------------- перенос
def bake_clip(dst, order, name, frames, flags, q0, src_rest, hip_scale, ground_z):
    bones = dst.data.bones
    rest = {n: bones[n].matrix_local for n in order}
    pel = VB + "Pelvis"
    n_fr = len(frames)
    # root motion: линейный тренд горизонтального смещения таза между первым и последним кадром
    drift = Vector((0, 0, 0))
    if "inplace" in flags and n_fr > 1:
        d = (frames[-1][pel].translation - frames[0][pel].translation) * INCH * hip_scale
        drift = Vector((d.x, d.y, 0.0))
    root_speed = drift.length / ((n_fr - 1) / FPS) if n_fr > 1 else 0.0

    spine_back = rest["Spine"].to_3x3().inverted() @ Vector((0, 1, 0))   # «назад» в осях кости Spine
    poses = []
    for i, fr in enumerate(frames):
        mats = {}
        for n in order:
            s = VB + MAP[n][0]
            sw = fr[s]
            delta = sw.to_quaternion() @ src_rest[s].to_quaternion().inverted()
            rot = delta @ q0[n] @ rest[n].to_quaternion()
            if n in BAG_OUT and name in BAG_CLIPS:   # правая рука — наружу, мимо сумки (вокруг оси корпуса «назад»)
                back = (mats["Spine"].to_3x3() @ spine_back).normalized()
                rot = Quaternion(back, math.radians(BAG_OUT[n])) @ rot
            b = bones[n]
            if b.parent is None:
                off = (sw.translation - src_rest[s].translation) * INCH * hip_scale
                if "inplace" in flags:
                    off -= drift * (i / (n_fr - 1))
                    if "loop" not in flags:   # разовый клип: и среднюю линию убираем
                        start = (frames[0][pel].translation - src_rest[pel].translation) * INCH * hip_scale
                        off -= Vector((start.x, start.y, 0.0))
                loc = rest[n].translation + off
            else:
                rel = b.parent.matrix_local.inverted() @ b.matrix_local
                loc = (mats[b.parent.name] @ rel).translation
            mats[n] = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
        poses.append(mats)

    def foot_point(m, f):  # самая низкая точка стопы — лодыжка или носок
        toe = m.translation + m.to_3x3() @ Vector((0, bones[f].length, 0))
        return toe if toe.z < m.translation.z else m.translation.copy()

    def foot_low(m, f):
        return foot_point(m, f).z

    # земля — по опорной стопе: медиана покадрового минимума обеих стоп. Глобальный минимум не годится:
    # в ходьбе GMod носок ноги в махе проходит ниже опорной стопы, и клип «повис» бы на 3 см
    lift = 0.0
    if "ground" in flags:
        lows = sorted(min(foot_low(p["FootL"], "FootL"), foot_low(p["FootR"], "FootR")) for p in poses)
        lift = ground_z - lows[len(lows) // 2]
    up = Matrix.Translation((0, 0, lift))

    dad = dst.animation_data
    ac = bpy.data.actions.new("Gm_" + name)
    dad.action = ac
    feet = {"FootL": [], "FootR": []}
    for i, mats in enumerate(poses):
        mats = {n: up @ m for n, m in mats.items()}
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
            m = mats[f]
            feet[f].append((foot_point(m, f), m.translation.copy(),
                            m.translation + m.to_3x3() @ Vector((0, bones[f].length, 0))))

    # скорость опорной стопы (самая низкая точка у земли два кадра подряд): с ней должен идти герой
    # опора: точка стопы у земли (не выше уровня опорной стопы + 1.5 см) и не летит вперёд (не мах)
    fwd = drift.normalized() if drift.length > 1e-4 else Vector((0, -1, 0))  # куда идёт герой
    stance = ground_z if "ground" in flags else min(p[0].z for pts in feet.values() for p in pts)

    def planted(pts, j, k):
        if pts[j][k].z > stance + 0.015:
            return False
        a, b = pts[max(j - 1, 0)][k], pts[min(j + 1, n_fr - 1)][k]
        return (b.xy - a.xy).dot(fwd.xy) <= 0.0

    speeds = []
    for pts in feet.values():
        for j in range(n_fr - 1):
            if planted(pts, j, 0) and planted(pts, j + 1, 0):
                speeds.append((pts[j + 1][0].xy - pts[j][0].xy).length * FPS)
    speeds.sort()
    foot_speed = speeds[len(speeds) // 2] if speeds else 0.0
    # проскальзывание: вернуть движение вперёд со скоростью foot_speed (так клип играет в игре)
    # и посмотреть, на сколько пятка и носок уезжают, пока стоят на земле; худший отрезок, см
    slide = 0.0
    if "loop" in flags and "inplace" in flags and foot_speed > 0.1:
        for pts in feet.values():
            for k in (1, 2):                      # пятка, носок
                seg = []
                for j in range(n_fr + 1):
                    if j < n_fr and planted(pts, j, k):
                        seg.append(pts[j][k].xy + fwd.xy * foot_speed * (j / FPS))
                    elif seg:
                        if len(seg) > 2:
                            slide = max(slide, max((a - seg[0]).length for a in seg))
                        seg = []

    tr = dad.nla_tracks.new()
    tr.name = name          # имя анимации в glTF / Godot
    tr.mute = True
    st = tr.strips.new(ac.name, 0, ac)
    st.name = name
    dad.action = None
    return {"frames": n_fr, "len_s": round((n_fr - 1) / FPS, 3), "loop": "loop" in flags,
            "root_speed": round(root_speed, 3),
            "foot_speed": round(foot_speed, 3), "slide_cm": round(slide * 100, 1),
            "lift": round(lift, 3)}


# ----------------------------------------------------------------------------- прыжок
# В GMod прыжок собирается в QC макросом $MakeJump (macro_gestures.qci), а не играется как есть:
#   основа — jump_c (ноги и таз: присед-замах, толчок, группировка, снижение, поза падения);
#   верх тела по весам UpperBodyBlend — поза стойки в мировых осях (worldspaceblend): в самом jump_c
#     руки в reference-позе (почти T-поза), их всегда закрывает поза оружия/стойки;
#   сверху — слой gmod_jump_delta = jump_c − reference (вес jump_delta: корпус 0.6, шея 0.5, ноги 0):
#     наклон корпуса и мах руками прыжка поверх позы стойки.
# Позой стойки берём первый кадр нашего Idle (base_m/Idle02) — руки как в стойке и ходьбе.
JUMP_POSE = ("base_m/Idle02.smd", 0)
JUMP_UPPER = {"Spine4": 0.9, "Head1": 0.9}           # UpperBodyBlend: Spine4 0.9, ключицы и руки — 1.0
JUMP_DELTA = {"Head1": 0.5}                          # jump_delta: шея 0.5, остальной верх — 0.6
JUMP_DELTA_DEFAULT = 0.6
LEGS_SRC = ("Pelvis", "L_Thigh", "L_Calf", "L_Foot", "R_Thigh", "R_Calf", "R_Foot")


def compose_jump(frames, pose, ref):
    """jump_c → прыжок как в игре GMod: ноги и таз из jump_c, верх — поза стойки + дельта прыжка."""
    upper = [MAP[n][0] for n in MAP if MAP[n][0] not in LEGS_SRC]
    out = []
    for fr in frames:
        new = dict(fr)
        for b in upper:
            s = VB + b
            qj = fr[s].to_quaternion()
            w = JUMP_UPPER.get(b, 1.0)
            blended = qj.slerp(pose[s].to_quaternion(), w)
            d = qj @ ref[s].to_quaternion().inverted()
            dw = Quaternion().slerp(d, JUMP_DELTA.get(b, JUMP_DELTA_DEFAULT))
            new[s] = Matrix.Translation(fr[s].translation) @ (dw @ blended).to_matrix().to_4x4()
        out.append(new)
    return out


def main():
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.render.fps_base = 1.0
    dst = bpy.data.objects["Yurchik3"]
    if dst.matrix_world != Matrix.Identity(4):
        raise RuntimeError("Yurchik3 должен стоять в начале координат без поворота")

    # в памяти убираем чужие NLA-дорожки (UAL), чтобы в GLB попали только эти клипы; .blend не сохраняется
    dad = dst.animation_data or dst.animation_data_create()
    for tr in list(dad.nla_tracks):
        dad.nla_tracks.remove(tr)
    dad.action = None
    for pb in dst.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)

    order = [b.name for b in dst.data.bones if b.name in MAP]  # родители раньше детей
    bones = dst.data.bones
    src_rest = load_smd(find_file("GMod/reference.smd"))[0]

    def bdir(m):  # направление нашей кости (ось Y) в мире
        return (m.to_3x3() @ Vector((0, 1, 0))).normalized()

    q0 = {}
    for n, (_, a, b) in MAP.items():
        if a is None:
            q0[n] = Quaternion()
            continue
        sdir = (src_rest[VB + b].translation - src_rest[VB + a].translation).normalized()
        q0[n] = bdir(bones[n].matrix_local).rotation_difference(sdir)
    hip_scale = bones["Pelvis"].head_local.z / (src_rest[VB + "Pelvis"].translation.z * INCH)
    # земля для стоп — как в rest-позе Юрчика
    ground_z = min(min(bones[f].head_local.z, bones[f].tail_local.z) for f in ("FootL", "FootR"))

    stats, missing = {}, []
    for name, rel, src_fps, flags, *rest in CLIPS:
        try:
            path = find_file(rel)
        except FileNotFoundError as e:
            missing.append(str(e))
            continue
        frames = resample(load_smd(path), src_fps, rest[0] if rest else None)
        need = {VB + MAP[n][0] for n in order}
        if not need.issubset(frames[0]):
            missing.append(rel + ": нет костей " + ", ".join(sorted(need - set(frames[0]))))
            continue
        if "jump" in flags:
            pose = load_smd(find_file(JUMP_POSE[0]))[JUMP_POSE[1]]
            frames = compose_jump(frames, pose, src_rest)
        stats[name] = bake_clip(dst, order, name, frames, flags, q0, src_rest, hip_scale, ground_z)
        stats[name]["src"] = rel + (" + верх %s, кадр %d (как $MakeJump)" % JUMP_POSE if "jump" in flags else "")
    return stats, missing


def export():
    sc = bpy.context.scene
    arm = bpy.data.objects["Yurchik3"]
    body = bpy.data.objects["Yurchik3Mesh"]
    ham = bpy.data.objects["Hammer3"]
    for o in sc.objects:
        o.select_set(o in (arm, body, ham))
    bpy.context.view_layer.objects.active = arm
    # те же имена узлов, что в assets/models/yurchik.gltf — пути дорожек анимаций совпадают
    for o, n in ((arm, "Yurchik"), (body, "YurchikMesh"), (ham, "Hammer")):
        o.name = n
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=OUT, use_selection=True, use_active_scene=True, export_format='GLB',
        export_apply=False, export_skins=True, export_materials='NONE', export_image_format='NONE',
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_frame_step=1, export_optimize_animation_size=True, export_anim_single_armature=True,
        export_def_bones=False, export_reset_pose_bones=True, export_bake_animation=False)


stats, missing = main()
export()
with open(os.path.join(OUT_DIR, "clips.json"), "w", encoding="utf-8") as fh:
    json.dump(stats, fh, ensure_ascii=False, indent=1, sort_keys=True)
print("RETARGET" + json.dumps({"clips": stats, "missing": missing}, ensure_ascii=False))
