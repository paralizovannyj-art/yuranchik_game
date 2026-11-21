# -*- coding: utf-8 -*-
# «Фото vs игра»: склеивает референс-фото и кадр из Godot рядом в один PNG (для сравнения квартиры с фото).
# Запуск через Blender MCP:
#   exec(open(r"<корень>/tools/blender/compare_shots.py", encoding="utf-8").read(),
#        {"PAIRS": [(фото, кадр, выход, (x0, y0, x1, y1) или None), ...]})
# crop — вырезать из кадра область (например, только 3D-вид из скриншота редактора). Высота результата — 720 px.
import bpy, numpy as np


def _load(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1].copy()    # сверху вниз
    bpy.data.images.remove(im)
    return a


def _fit(a, hh):
    s = hh / a.shape[0]
    ys = np.minimum((np.arange(hh) / s).astype(int), a.shape[0] - 1)
    xs = np.minimum((np.arange(int(a.shape[1] * s)) / s).astype(int), a.shape[1] - 1)
    return a[ys][:, xs]


def compose(photo, shot, out, crop=None, hh=720):
    p = _fit(_load(photo), hh)
    g = _load(shot)
    if crop:
        x0, y0, x1, y1 = crop
        g = g[y0:y1, x0:x1]
    g = _fit(g, hh)
    W = p.shape[1] + 12 + g.shape[1]
    o = np.zeros((hh, W, 4), np.float32); o[..., 3] = 1
    o[:, :p.shape[1]] = p
    o[:, p.shape[1] + 12:] = g
    img = bpy.data.images.new("cmp", W, hh, alpha=True)
    img.pixels.foreach_set(o[::-1].ravel())
    img.filepath_raw = out; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)


for (ph, sh, out, cr) in globals().get("PAIRS", []):
    compose(ph, sh, out, cr)
