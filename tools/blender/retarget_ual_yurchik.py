# Перенос анимаций Quaternius «Universal Animation Library» (CC0) на скелет Юрчика v3.
#
# Источник: tools/blender/ual/UAL1_Standard.glb (без root motion), лицензия CC0 —
#   https://quaternius.itch.io/universal-animation-library
# Цель:     скелет «Yurchik3» из tools/blender/yurchik_v3.blend (15 костей, A-поза).
#
# Как переносим: для каждой нашей кости берём кость-источник и её поворот относительно
# собственной rest-позы в мировых осях (delta). Rest-позы у скелетов разные (у них T-поза,
# у нас A-поза), поэтому сначала доворачиваем нашу кость так, чтобы в rest она смотрела туда же,
# куда кость-источник (q0), и уже потом применяем delta:  world = delta · q0 · rest_our.
# Ступни берём без q0 — чтобы сохранить наш разворот носков.
#
# Запуск (из корня проекта, Blender 5.2):
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
    ("Idle", "UAL1", "Idle_Loop", False),
    ("Walk", "UAL1", "Walk_Loop", False),
    ("WalkBack", "UAL1", "Walk_Loop", True),
    ("Jog", "UAL1", "Jog_Fwd_Loop", False),
    ("Sprint", "UAL1", "Sprint_Loop", False),
    # удар молотком: из «рубки дерева» — замах (кадры 18–28) → удар (0–6) → доводка (до 14)
    ("Attack", "UAL2", "TreeChopping_Loop", False, [(18, 28), (0, 14)]),
    # стойка «готов к удару» (ПКМ): молоток занесён у головы — кадр 19 рубки; играется на верх тела
    ("AimIdle", "UAL2", "TreeChopping_Loop", False, [(19, 19), (19, 19)]),
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
    return stats


def export():
    sc = bpy.context.scene
    arm = bpy.data.objects["Yurchik3"]
    body = bpy.data.objects["Yurchik3Mesh"]
    ham = bpy.data.objects["Hammer3"]
    for o in sc.objects:
        o.select_set(o in (arm, body, ham))
    bpy.context.view_layer.objects.active = arm
    ren = [(arm, "Yurchik"), (body, "YurchikMesh"), (ham, "Hammer")]
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
