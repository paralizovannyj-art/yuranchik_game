# -*- coding: utf-8 -*-
# Сравнение Хьюги с листом модели docs/references/hyuga/hyuga_sheet_v2.webp.
# Лист нарисован почти ортогонально и в одном масштабе (≈1.523 мм на пиксель листа: холка 0.30 м), поэтому модель
# рендерится ортокамерой в ТОМ ЖЕ масштабе и с той же линией земли: на каждый вид — «лист | модель | наложение 50/50»
# (по наложению видно расхождение силуэта и пропорций). Плюс 3/4 и поза сна рядом с «Resting pose» листа.
# Итог — docs/references/hyuga/preview/compare_<вид>.png и общий compare_sheet.png.
# Запуск через Blender MCP после build_hyuga.py:
#   exec(open(r"<проект>\tools\blender\hyuga_compare.py", encoding="utf-8").read(),
#        {"__file__": r"<проект>\tools\blender\hyuga_compare.py", "HYUGA_COMPARE_OUT": r"<папка>"})
import bpy, os, math
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(globals().get("__file__")))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = globals().get("HYUGA_COMPARE_OUT") or os.path.join(ROOT, "docs", "references", "hyuga", "preview")
SHEET = os.path.join(ROOT, "docs", "references", "hyuga", "hyuga_sheet_v2.webp")
K = 0.001523            # метров на пиксель листа
UP = 2                  # во сколько раз увеличивать вырезки листа

# вид: вырезка листа (x0, y0, x1, y1), откуда смотрит камера, где на листе y=0 (центр корпуса) или x=0,
# строка земли на листе, отразить ли лист по горизонтали
VIEWS = [
    ("front", (90, 60, 250, 372), (0, -1, 0), 174, 362, False),
    ("left", (290, 60, 640, 372), (1, 0, 0), 499, 360, False),
    ("right", (640, 60, 990, 372), (-1, 0, 0), 847, 360, True),
    ("back", (190, 400, 360, 712), (0, 1, 0), 275, 702, False),
]
REST = (490, 430, 960, 715)


def sheet_px():
    im = bpy.data.images.load(SHEET, check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1]                    # сверху вниз


def crop(S, box, flip=False, up=UP):
    x0, y0, x1, y1 = box
    c = S[y0:y1, x0:x1]
    if flip:
        c = c[:, ::-1]
    return np.repeat(np.repeat(c, up, 0), up, 1)


def load_px(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1]


def save(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new("cmp", w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save(); bpy.data.images.remove(img)


def fit_h(a, h):
    """Масштаб по высоте (ближайший сосед) — для склейки разных панелей в один ряд."""
    ys = (np.arange(h) * a.shape[0] / h).astype(int)
    w = int(round(a.shape[1] * h / a.shape[0]))
    xs = (np.arange(w) * a.shape[1] / w).astype(int)
    return a[ys][:, xs]


def row(panels, h, gap=6):
    ps = [fit_h(p, h) for p in panels]
    W = sum(p.shape[1] for p in ps) + gap * (len(ps) - 1)
    out = np.zeros((h, W, 4), np.float32); out[..., 3] = 1
    x = 0
    for p in ps:
        out[:, x:x + p.shape[1]] = p; x += p.shape[1] + gap
    return out


def render(sc, cam, cd, path, res):
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    a = load_px(path); os.remove(path)
    return a


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
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    keep = (sc.render.engine, sc.camera)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'FLAT'; sh.color_type = 'TEXTURE'; sh.show_cavity = False   # плоский: видна запечённая текстура
    sh.show_shadows = False
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    wd = bpy.data.worlds.get("HyugaPreview") or bpy.data.worlds.new("HyugaPreview")
    wd.color = (0.03, 0.035, 0.04); sc.world = wd
    cd = bpy.data.cameras.new("HyugaCmpCam"); cd.type = 'ORTHO'
    cam = bpy.data.objects.new("HyugaCmpCam", cd); sc.collection.objects.link(cam); sc.camera = cam
    os.makedirs(OUT, exist_ok=True)
    S = sheet_px()
    tmp = os.path.join(OUT, "_cmp_tmp.png")
    rows, outs = [], []
    for tag, box, d, c0, ground, flip in VIEWS:
        x0, y0, x1, y1 = box
        w, h = x1 - x0, y1 - y0
        ref = crop(S, box, flip)
        cd.ortho_scale = max(w, h) * K
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        lat = (cx - c0) * K * (-1 if tag == "back" else 1)
        z = (ground - cy) * K
        d = Vector(d)
        if abs(d.x) > 0.5:
            tgt = Vector((0, lat, z))
        else:
            tgt = Vector((lat, 0, z))
        cam.location = tgt + d * 2.0
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        m = render(sc, cam, cd, tmp, (w * UP, h * UP))
        mix = ref * 0.5 + m * 0.5
        trip = row([ref, m, mix], h * UP)
        path = os.path.join(OUT, "compare_%s.png" % tag)
        save(trip, path); outs.append(path)
        rows.append(trip)
    # 3/4 спереди-слева (на листе такого вида нет — для оценки объёма) и поза сна рядом с «Resting pose»
    cd.ortho_scale = 0.62
    d = Vector((0.75, -1.0, 0.45)).normalized()
    cam.location = Vector((0, -0.02, 0.22)) + d * 2.0
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    q34 = render(sc, cam, cd, tmp, (640, 640))
    sleep = bpy.data.actions.get("Sleep")
    if sleep:
        ad.action = sleep
        sc.frame_set(0)
        bpy.context.view_layer.update()
        cd.ortho_scale = 0.50
        d = Vector((1.0, 1.0, 1.1)).normalized()           # со стороны морды и лап, сверху-сбоку, как на листе
        cam.location = Vector((0, 0, 0.09)) + d * 2.0
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sl = render(sc, cam, cd, tmp, (800, 560))
        ad.action = None
        rest = row([crop(S, REST, up=1), sl], 560)
        save(rest, os.path.join(OUT, "compare_sleep.png")); outs.append(os.path.join(OUT, "compare_sleep.png"))
    save(q34, os.path.join(OUT, "hyuga_q34.png")); outs.append(os.path.join(OUT, "hyuga_q34.png"))
    # общий лист: виды сбоку, спереди+сзади, 3/4 + сон
    H = 420
    top = row([rows[1], rows[2]], H)
    mid = row([rows[0], rows[3]] + ([q34] if not sleep else []), H)
    parts = [top, mid]
    if sleep:
        parts.append(row([q34, rest], H))
    W = max(p.shape[1] for p in parts)
    sheet = np.zeros((sum(p.shape[0] for p in parts) + 6 * (len(parts) - 1), W, 4), np.float32); sheet[..., 3] = 1
    y = 0
    for p in parts:
        sheet[y:y + p.shape[0], :p.shape[1]] = p; y += p.shape[0] + 6
    save(sheet, os.path.join(OUT, "compare_sheet.png")); outs.append(os.path.join(OUT, "compare_sheet.png"))
    bpy.data.objects.remove(cam, do_unlink=True); bpy.data.cameras.remove(cd)
    sc.render.engine, sc.camera = keep
    ad.action = keep_action
    return outs


result = {"files": main()}
