# Анимация «Юрчик садится в кресло» (SitDown) для скелета Юрчика v3.
#
# Берёт из assets/animations/gmod/yurchik_gmod.glb позу стойки (Idle, кадр 0) и позу сидя (Sit — sit_generic из GMod)
# и собирает между ними переход: Юрчик стоит перед креслом, чуть сгибает колени, наклоняет корпус вперёд
# (противовес), уводит таз назад и вниз, мягко садится и выпрямляется. Встаёт — тот же клип задом наперёд
# (yurchik_anim.gd проигрывает его в обратную сторону).
#
# Координаты Blender: Z вверх, вперёд −Y. У позы Sit из GMod таз на уровне сиденья (z ≈ 0), стопы ниже
# нуля — поэтому сидячая поза поднимается на SIT_LIFT, чтобы стопы стояли на полу. Таз в конце уезжает
# назад на SIT_BACK: точка, где Юрчик стоит перед посадкой, — на SIT_BACK впереди тазобедренных суставов
# в кресле (это смещение повторяет scripts/world/pc_seat.gd).
#
# Запуск — только в живом Blender через Blender MCP (правило проекта):
#   exec(open(r"<проект>/tools/blender/build_sit_down.py", encoding="utf-8").read(), {"__name__": "__main__"})
# Скрипт очищает текущую сцену, импортирует yurchik_gmod.glb и пишет assets/animations/sit/yurchik_sit.glb.
import bpy, os, math
from mathutils import Matrix, Vector, Quaternion

ROOT = r"C:\Users\mrs\Documents\yuranchik_game"
SRC = os.path.join(ROOT, "assets", "animations", "gmod", "yurchik_gmod.glb")
OUT_DIR = os.path.join(ROOT, "assets", "animations", "sit")
OUT = os.path.join(OUT_DIR, "yurchik_sit.glb")

SIT_LIFT = 0.56      # м — подъём позы Sit: таз на подушке кресла (верх сиденья 0.52 — build_gaming_chair.py)
SIT_BACK = 0.35      # м — насколько таз уходит назад от места, где Юрчик стоял
FPS = 30
LEN = 48             # кадров — 1.6 с

# ключи: (кадр, доля перехода стойка→сидя для костей, доля пути таза вниз, доля пути таза назад, наклон корпуса °)
KEYS = [
    (0,  0.00, 0.00, 0.00, 0.0),
    (10, 0.18, 0.10, 0.05, 14.0),    # колени пошли, корпус вперёд
    (22, 0.55, 0.48, 0.45, 32.0),    # таз назад и вниз, корпус сильно вперёд — противовес
    (32, 0.92, 0.97, 0.90, 22.0),    # почти сел
    (38, 1.00, 1.03, 1.00, 8.0),     # просел в подушку
    (48, 1.00, 1.00, 1.00, 0.0),     # сидит ровно
]


def sample(arm, action):
    arm.animation_data.action = bpy.data.actions[action]
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    return {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}


def lerp_basis(a, b, t):
    la, ra, sa = a.decompose()
    lb, rb, sb = b.decompose()
    return Matrix.LocRotScale(la.lerp(lb, t), ra.slerp(rb, t), sa.lerp(sb, t))


def main():
    scene = bpy.context.scene
    for o in list(scene.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes, bpy.data.cameras):   # повторный запуск — с чистого листа
        for d in list(coll):
            coll.remove(d)
    bpy.ops.import_scene.gltf(filepath=SRC)
    arm = bpy.data.objects["Yurchik"]
    scene.render.fps = FPS
    stand = sample(arm, "Idle")
    sit = sample(arm, "Sit")

    pelvis = arm.pose.bones["Pelvis"]
    to_local = pelvis.bone.matrix_local.to_3x3().inverted()   # смещение в осях арматуры → в осях кости
    lift_local = to_local @ Vector((0.0, 0.0, SIT_LIFT))
    back_local = to_local @ Vector((0.0, SIT_BACK, 0.0))
    # «чистый» путь таза: высота и сдвиг назад идут по своим кривым (отдельно от поворотов)
    ls, rs, ss = stand["Pelvis"].decompose()
    lt, rt, st = sit["Pelvis"].decompose()
    lt = lt + lift_local + back_local

    act = bpy.data.actions.new("SitDown")
    arm.animation_data.action = act
    for frame, t, down, back, bend in KEYS:
        for pb in arm.pose.bones:
            pb.matrix_basis = lerp_basis(stand[pb.name], sit[pb.name], t)
        # таз: высота (по оси Z арматуры) и сдвиг назад (по Y) — со своими долями
        arm_ls = pelvis.bone.matrix_local.to_3x3() @ ls
        arm_lt = pelvis.bone.matrix_local.to_3x3() @ lt
        arm_l = Vector((arm_ls.x + (arm_lt.x - arm_ls.x) * t,
                        arm_ls.y + (arm_lt.y - arm_ls.y) * back,
                        arm_ls.z + (arm_lt.z - arm_ls.z) * down))
        pelvis.matrix_basis = Matrix.LocRotScale(to_local @ arm_l, rs.slerp(rt, t), Vector((1, 1, 1)))
        bpy.context.view_layer.update()
        # наклон корпуса вперёд вокруг поясницы (ось X арматуры; + — верх уходит к −Y, то есть вперёд)
        if bend != 0.0:
            spine = arm.pose.bones["Spine"]
            pivot = spine.head.copy()
            r = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(bend), 4, 'X') @ Matrix.Translation(-pivot)
            spine.matrix = r @ spine.matrix
            bpy.context.view_layer.update()
        for pb in arm.pose.bones:
            pb.keyframe_insert("location", frame=frame)
            pb.keyframe_insert("rotation_quaternion", frame=frame)
            pb.keyframe_insert("scale", frame=frame)

    # только этот клип в экспорт
    ad = arm.animation_data
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    tr = ad.nla_tracks.new()
    tr.name = "SitDown"
    tr.strips.new("SitDown", 0, act)
    ad.action = None
    scene.frame_start, scene.frame_end = 0, LEN

    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in scene.objects:
        if o.name in ("Yurchik", "YurchikMesh") or o.parent == arm and o.type == 'MESH':
            o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(
        filepath=OUT, use_selection=True, use_active_scene=True, export_format='GLB',
        export_apply=False, export_skins=True, export_materials='NONE', export_image_format='NONE',
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_frame_step=1, export_optimize_animation_size=True, export_anim_single_armature=True,
        export_def_bones=False, export_reset_pose_bones=True, export_bake_animation=False)
    # для просмотра в окне Blender: клип активный, проигрывается по пробелу
    ad.action = act
    for tr in list(ad.nla_tracks):
        tr.mute = True
    return OUT


if __name__ == "__main__":
    main()
