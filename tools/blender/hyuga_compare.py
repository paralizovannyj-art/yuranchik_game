# -*- coding: utf-8 -*-
# Сравнение Хьюги с фото: рендер модели под теми же ракурсами, что на фото (перспективная камера «телефона»,
# объёмный студийный свет, текстура), и склейка «фото | модель» в один PNG на каждый ракурс.
# Запуск через Blender MCP после build_hyuga.py:
#   exec(open(r"<проект>\tools\blender\hyuga_compare.py", encoding="utf-8").read(),
#        {"__file__": r"<проект>\tools\blender\hyuga_compare.py", "HYUGA_COMPARE_OUT": r"<папка>"})
import bpy, os, math
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(globals().get("__file__")))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = globals().get("HYUGA_COMPARE_OUT") or os.path.join(ROOT, "docs", "references", "hyuga", "preview")
REF = os.path.join(ROOT, "docs", "references", "hyuga")

# ракурс: фото, откуда камера (направление от собаки), куда смотрит, расстояние, фокусное,
# поворот головы как на фото (град.: + влево / + вверх)
VIEWS = [
    ("side", "hyuga_photo_side.png", (-1.0, -0.15, 0.75), (0.0, -0.02, 0.20), 1.25, 26, (-45, 12)),
    ("back", "hyuga_photo_back.png", (0.15, 0.70, 1.0), (0.0, 0.0, 0.18), 1.15, 26, (50, -15)),
    ("front", "hyuga_photo_front.png", (0.10, -0.80, 1.0), (0.0, -0.05, 0.22), 0.95, 26, (0, 38)),
]
W, H = 600, 800


def load_px(path, w, h):
    im = bpy.data.images.load(path, check_existing=False)
    if im.size[0] != w or im.size[1] != h:
        im.scale(w, h)
    a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)


def rot_bone(arm, name, axis, deg):
    """Поворот кости вокруг её начала по оси пространства скелета."""
    pb = arm.pose.bones[name]
    m0 = pb.matrix.copy(); h = m0.translation.copy()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ m0
    bpy.context.view_layer.update()


def pose_head(arm, yaw, pitch):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    for name, k in (("Neck", 0.4), ("Head", 0.6)):
        rot_bone(arm, name, 'Z', yaw * k)          # +Z: морда (−Y) поворачивается к +X — влево
        rot_bone(arm, name, 'X', -pitch * k)       # −X: морда поднимается


def main():
    sc = bpy.data.scenes["Hyuga"]
    if bpy.context.window.scene is not sc:
        bpy.context.window.scene = sc
    arm = sc.objects["Hyuga"]
    ad = arm.animation_data
    keep_action = ad.action
    ad.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    keep = (sc.render.engine, sc.camera)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_cavity = False
    sh.studio_light = 'Default'
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    wd = bpy.data.worlds.get("HyugaPreview") or bpy.data.worlds.new("HyugaPreview")
    wd.color = (0.30, 0.30, 0.30); sc.world = wd
    cd = bpy.data.cameras.new("HyugaCmpCam")
    cam = bpy.data.objects.new("HyugaCmpCam", cd); sc.collection.objects.link(cam); sc.camera = cam
    os.makedirs(OUT, exist_ok=True)
    outs = []
    for tag, photo, d, tgt, dist, lens, (yaw, pitch) in VIEWS:
        pose_head(arm, yaw, pitch)
        cd.lens = lens; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
        d = Vector(d).normalized(); t = Vector(tgt)
        cam.location = t + d * dist
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        tmp = os.path.join(OUT, "_cmp_tmp.png")
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        m = load_px(tmp, W, H); os.remove(tmp)
        p = load_px(os.path.join(REF, photo), W, H)
        pair = np.concatenate([p, m], axis=1)
        img = bpy.data.images.new("cmp", pair.shape[1], pair.shape[0], alpha=True)
        img.pixels.foreach_set(pair.ravel())
        path = os.path.join(OUT, "compare_%s.png" % tag)
        img.filepath_raw = path; img.file_format = 'PNG'; img.save(); bpy.data.images.remove(img)
        outs.append(path)
    bpy.data.objects.remove(cam, do_unlink=True); bpy.data.cameras.remove(cd)
    sc.render.engine, sc.camera = keep
    pose_head(arm, 0, 0)
    ad.action = keep_action
    return outs


result = {"files": main()}
