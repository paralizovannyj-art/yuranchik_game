# -*- coding: utf-8 -*-
# Крупные планы Юрчика для проверки модели (YUR-9): шапка снизу и спереди, сумка сзади и сбоку, ботинки.
# Запуск через Blender MCP в открытом yurchik_v3.blend:
#   YUR_SHOTS_OUT = r"<папка>"; exec(open(r"<проект>\tools\blender\yur_closeups.py", encoding="utf-8").read())
# Рендерит EEVEE в YUR_SHOTS_OUT/<имя>.png, модель — в позе покоя или в позе клипа (YUR_SHOTS_ACTION = "Gm_Idle", если клипы GMod загружены в сцену).
# Камеру и сцену возвращает как было.
import bpy, os
from mathutils import Vector

OUT = globals().get("YUR_SHOTS_OUT", os.path.join(os.path.dirname(bpy.data.filepath), "_shots"))
ONLY = globals().get("YUR_SHOTS_ONLY")
ACTION = globals().get("YUR_SHOTS_ACTION")               # None — поза покоя (A-поза)
ACTION_FRAME = globals().get("YUR_SHOTS_FRAME", 1)
SHOTS = {  # имя: (камера, точка взгляда, фокусное)
    "head_below": ((0.0, -0.30, 1.40), (0.0, -0.05, 1.64), 35),
    "head_below_side": ((0.22, -0.18, 1.42), (0.0, -0.05, 1.64), 35),
    "beanie_front": ((0.0, -0.55, 1.68), (0.0, -0.05, 1.67), 60),
    "head_back": ((0.10, 0.55, 1.60), (0.0, -0.05, 1.62), 50),
    "bag_back": ((-0.30, 0.85, 0.95), (-0.17, 0.09, 0.88), 50),
    "bag_side": ((-0.95, 0.42, 0.92), (-0.17, 0.09, 0.88), 50),
    "bag_front": ((-0.55, -0.70, 0.95), (-0.17, 0.09, 0.88), 50),
    "bag_below": ((-0.45, 0.30, 0.45), (-0.17, 0.09, 0.85), 40),
    "boots_side": ((0.75, -0.55, 0.16), (0.08, -0.06, 0.07), 45),
    "boots_front": ((0.05, -0.80, 0.22), (0.0, -0.06, 0.07), 45),
    "boots_back": ((0.30, 0.70, 0.20), (0.0, 0.0, 0.07), 45),
    "full": ((1.6, -3.4, 1.1), (0.0, 0.0, 0.9), 50),
}


def shoot():
    sc = bpy.context.window.scene
    os.makedirs(OUT, exist_ok=True)
    arm = next((o for o in sc.objects if o.type == 'ARMATURE'), None)
    keep = (sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath, sc.render.engine,
            arm.data.pose_position if arm else None)
    cd = bpy.data.cameras.get("YurShotCam") or bpy.data.cameras.new("YurShotCam")
    cam = bpy.data.objects.get("YurShotCam") or bpy.data.objects.new("YurShotCam", cd)
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cd.clip_start = 0.01
    sc.camera = cam
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 640, 640
    keep_anim = None
    if arm and ACTION:                                    # поза из клипа (например, Gm_Idle, кадр ACTION_FRAME)
        ad = arm.animation_data or arm.animation_data_create()
        keep_anim = (ad.action, ad.use_nla, sc.frame_current)
        ad.use_nla = False; ad.action = bpy.data.actions[ACTION]
        sc.frame_set(ACTION_FRAME)
    elif arm:
        arm.data.pose_position = 'REST'
    done = []
    try:
        for name, (loc, tgt, lens) in SHOTS.items():
            if ONLY and name not in ONLY:
                continue
            cam.location = loc; cd.lens = lens
            cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = os.path.join(OUT, name + ".png")
            bpy.ops.render.render(write_still=True)
            done.append(sc.render.filepath)
    finally:
        sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.render.filepath, sc.render.engine = keep[:5]
        if arm:
            arm.data.pose_position = keep[5]
        if keep_anim:
            ad.action, ad.use_nla = keep_anim[0], keep_anim[1]
            sc.frame_set(keep_anim[2])
        bpy.data.objects.remove(cam, do_unlink=True)
    return done


result = {"shots": shoot()}
