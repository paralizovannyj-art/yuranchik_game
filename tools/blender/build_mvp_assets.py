# -*- coding: utf-8 -*-
# Ассеты MVP: подъезд (лестничная клетка на 4 этажа + квартира Юрчика), гараж с открывающимися воротами,
# предметы (бутылка, кирпич, аптечка, бинт, шаурма, ключи, молоток) и их иконки для инвентаря.
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_mvp_assets.py
# Результат: assets/textures/*.png, assets/models/stairwell.gltf, garage_yur.gltf, item_*.gltf, assets/ui/icons/*.png
#
# Оси Blender: Z — вверх. Подъезд: вход в точке (0, 0, 0), вглубь дома — +Y (в Godot это -Z).
# Имена объектов: «nocol» в имени — без коллизии (ступени, перила); суффикс «-colonly» — только коллизия (пандусы лестниц).
import bpy, os, sys, math
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import tex_lib
from tex_lib import *
import ps2_hero

_ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), _ns)
B, mat = _ns["B"], _ns["mat"]
OUT = os.path.join(ROOT, "assets", "models")
ICONS = os.path.join(ROOT, "assets", "ui", "icons")
R = np.random.default_rng(2026)
RH = np.random.default_rng(2077)                                   # отдельный генератор для ps2_hero
ONLY = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


# =====================================================================================
#  Текстуры
# =====================================================================================
def scribble(arr, x, y, n, color, rng, step=5):
    """Каракули маркером: ломаная из n отрезков."""
    h, w, _ = arr.shape
    for _ in range(n):
        nx = int(np.clip(x + rng.integers(-step * 3, step * 3 + 1), 1, w - 2))
        ny = int(np.clip(y + rng.integers(-step * 2, step * 2 + 1), 1, h - 2))
        k = max(abs(nx - x), abs(ny - y), 1)
        for i in range(k + 1):
            px = int(x + (nx - x) * i / k); py = int(y + (ny - y) * i / k)
            arr[py:py + 2, px:px + 1] = color
        x, y = nx, ny


def tex_pod_wall():
    # Побелка + зелёная краска с разводами, как стены в Obscure (рисует ps2_hero)
    save("pod_wall", ps2_hero.pod_wall(RH, draw_text))


def tex_pod_green():
    save("pod_green", ps2_hero.pod_green(RH, draw_text))


def tex_simple():
    save("pod_ceiling", ps2_hero.ceiling(RH, 128))                                # потолок с подтёками
    save("pod_floor", ps2_hero.tile_floor(RH, 256, 6))                            # плитка 6x6 с грязной затиркой
    save("pod_step", ps2_hero.step(RH))
    save("garage_in", photo("Bricks105", 128, 128, relief=1.0, sat=0.55, gain=0.55))
    save("garage_floor", ps2_hero.finish(ps2_hero.concrete(RH, 128, 128, (0.36, 0.36, 0.34), oil=0.8), 1.4))
    save("parquet", ps2_hero.wood_floor(RH, 256, 256, 10))                        # доски, как пол в Obscure


def tex_doors():
    w, h, dw = 256, 128, 64
    arr = np.zeros((h, w, 3), np.float32)
    yy, xx = np.mgrid[0:h, 0:dw]
    nz = lambda: (0.8 + 0.4 * fbm(dw, h, 6, 12, R))[..., None]

    def dermantin(tone, num):
        d = np.ones((h, dw, 3), np.float32) * rgb(tone) * nz()
        lines = ((xx + yy) % 16 < 1) | ((xx - yy) % 16 < 1)
        d = np.where(lines[..., None], d * 0.55, d)
        studs = ((xx + yy) % 16 < 2) & ((xx - yy) % 16 < 2)
        d = np.where(studs[..., None], rgb((0.62, 0.55, 0.35)), d)
        d[:3] *= 0.4; d[-2:] *= 0.4; d[:, :3] *= 0.4; d[:, -3:] *= 0.4
        d[22:34, 20:44] = rgb((0.55, 0.50, 0.36))                    # табличка с номером
        draw_text(d, num, 23, 24, 1, rgb((0.08, 0.07, 0.06)))
        draw_text(d, num, 24, 24, 1, rgb((0.08, 0.07, 0.06)))
        d[62:72, 52:56] = rgb((0.50, 0.48, 0.42))                    # ручка
        d[46:49, 31:34] = rgb((0.05, 0.05, 0.05))                    # глазок
        return d

    arr[:, 0:64] = dermantin((0.26, 0.14, 0.09), "41")
    steel = tile(photo("PaintedMetal006", 64, 64, relief=0.8, sat=0.2, gain=0.7), dw, h) * rgb((0.75, 0.78, 0.82))
    steel[:3] *= 0.4; steel[-2:] *= 0.4; steel[:, :3] *= 0.4; steel[:, -3:] *= 0.4
    steel[8:60, 8:56] *= 0.88; steel[68:120, 8:56] *= 0.88
    steel[62:72, 50:55] = rgb((0.62, 0.62, 0.60)); steel[46:49, 31:34] = rgb((0.04, 0.04, 0.04))
    draw_text(steel, "42", 26, 14, 1, rgb((0.75, 0.75, 0.70)))
    arr[:, 64:128] = steel
    wood = tile(photo("Planks023A", 64, 64, relief=0.8, sat=0.7, gain=0.5), dw, h) * rgb((0.85, 0.55, 0.40))
    wood[:3] *= 0.4; wood[-2:] *= 0.4; wood[:, :3] *= 0.4; wood[:, -3:] *= 0.4
    for (a, b_) in ((10, 56), (66, 118)):
        wood[a:b_, 10:54] *= 0.78; wood[a + 3:b_ - 3, 13:51] *= 1.25
    wood[60:70, 52:56] = rgb((0.55, 0.52, 0.40))
    draw_text(wood, "44", 26, 3, 1, rgb((0.75, 0.70, 0.55)))
    arr[:, 128:192] = wood
    arr[:, 192:256] = dermantin((0.30, 0.07, 0.06), "47")           # дверь Юрчика
    save("apt_doors", arr)


def tex_misc():
    # почтовые ящики
    w, h = 128, 64
    a = np.ones((h, w, 3), np.float32) * rgb((0.16, 0.30, 0.36)) * (0.75 + 0.5 * fbm(w, h, 8, 4, R))[..., None]
    for r in range(2):
        for c in range(4):
            x0, y0 = c * 32, r * 32
            a[y0:y0 + 1, x0:x0 + 32] *= 0.4; a[y0:y0 + 32, x0:x0 + 1] *= 0.4
            a[y0 + 6:y0 + 9, x0 + 6:x0 + 26] = rgb((0.03, 0.03, 0.03))
            a[y0 + 20:y0 + 24, x0 + 14:x0 + 18] = rgb((0.45, 0.45, 0.42))
    rust = np.clip(fbm(w, h, 10, 5, R) - 0.62, 0, 1)[..., None] * 4
    a = a * (1 - rust) + rgb((0.30, 0.14, 0.06)) * rust
    save("mailboxes", a)
    # окно на лестнице: ночь и оранжевое зарево снизу
    w = h = 64
    g = np.linspace(0, 1, h)[:, None]
    glass = (rgb((0.03, 0.05, 0.10)) * (1 - g)[..., None] + rgb((0.50, 0.28, 0.12)) * (g ** 2)[..., None]) * np.ones((h, w, 1), np.float32)
    glass *= (0.7 + 0.6 * fbm(w, h, 6, 6, R))[..., None]
    frame = np.zeros((h, w), bool)
    frame[:4] = frame[-4:] = True; frame[:, :4] = frame[:, -4:] = True; frame[:, 30:34] = True; frame[20:23] = True
    col_ = np.where(frame[..., None], rgb((0.50, 0.48, 0.42)) * (0.7 + 0.4 * fbm(w, h, 8, 8, R))[..., None], glass)
    save("pod_window", col_)
    save("pod_window_emission", np.where(frame[..., None], 0.0, glass * 0.9))
    # батарея
    xx = np.arange(64)[None, :]
    rib = 0.55 + 0.45 * np.abs(np.sin(xx / 64 * np.pi * 8))
    rad_ = np.ones((64, 64, 3), np.float32) * rgb((0.55, 0.52, 0.45)) * rib[..., None] * (0.7 + 0.5 * fbm(64, 64, 6, 6, R))[..., None]
    rad_[:5] *= 0.6; rad_[-5:] *= 0.6
    save("radiator", rad_)
    # обои
    save("wallpaper", ps2_hero.wallpaper(RH, 128))
    # ковёр на стене
    w, h = 128, 96
    yy, xx = np.mgrid[0:h, 0:w]
    ax = np.abs(xx - w / 2 + 0.5); ay = np.abs(yy - h / 2 + 0.5)
    cp = np.ones((h, w, 3), np.float32) * rgb((0.40, 0.07, 0.06))
    cream, dark, blue = rgb((0.66, 0.56, 0.38)), rgb((0.10, 0.05, 0.05)), rgb((0.10, 0.14, 0.28))
    cp = np.where((((ax + ay) % 22) < 2.5)[..., None], cream, cp)
    cp = np.where((((ax * 0.75 + ay) % 22 > 10) & ((ax * 0.75 + ay) % 22 < 12))[..., None], blue, cp)
    med = (ax / 26 + ay / 20) < 1
    cp = np.where(med[..., None], dark, cp)
    cp = np.where(((ax / 20 + ay / 15) < 1)[..., None], cream, cp)
    cp = np.where(((ax / 13 + ay / 10) < 1)[..., None], rgb((0.40, 0.07, 0.06)), cp)
    border = (ax > w / 2 - 9) | (ay > h / 2 - 9)
    cp = np.where(border[..., None], dark, cp)
    cp = np.where((border & (((xx + yy) % 8) < 3))[..., None], cream, cp)
    cp *= (0.7 + 0.5 * fbm(w, h, 24, 18, R, oct=2))[..., None]
    save("carpet", cp)
    # ткань дивана, телевизор
    fab = np.ones((64, 64, 3), np.float32) * rgb((0.22, 0.25, 0.17)) * (0.6 + 0.8 * R.random((64, 64, 1)).astype(np.float32) * 0.5 + 0.3 * fbm(64, 64, 4, 4, R)[..., None])
    save("fabric", fab)
    tv = np.ones((64, 64, 3), np.float32) * rgb((0.08, 0.075, 0.07))
    scr = R.random((44, 52, 1)).astype(np.float32)
    tv[8:52, 6:58] = rgb((0.05, 0.06, 0.08)) + scr * rgb((0.10, 0.12, 0.16))
    emi = np.zeros((64, 64, 3), np.float32)
    emi[8:52, 6:58] = scr * rgb((0.35, 0.42, 0.55))
    save("tv", tv); save("tv_emission", emi)


def tex_items():
    """Атлас предметов 128x128."""
    a = np.zeros((128, 128, 3), np.float32) + 0.2
    # бутылка: зелёное стекло + этикетка (0..32, 0..64)
    g = np.ones((64, 32, 3), np.float32) * rgb((0.10, 0.26, 0.12)) * (0.7 + 0.6 * fbm(32, 64, 4, 8, R))[..., None]
    g[:, 5:9] *= 1.9                                                   # блик
    g[30:52] = rgb((0.70, 0.64, 0.48)) * (0.8 + 0.3 * fbm(32, 22, 6, 4, R))[..., None]
    g[36:40, 4:28] = rgb((0.45, 0.10, 0.08)); g[44:46, 6:26] = rgb((0.15, 0.13, 0.10))
    a[0:64, 0:32] = g
    # кирпич (32..96, 0..32)
    br = photo("Bricks105", 256, 256, relief=1.0, sat=0.8, gain=0.75)[40:72, 30:94]
    a[0:32, 32:96] = br * rgb((1.0, 0.72, 0.6)) * (0.8 + 0.4 * fbm(64, 32, 8, 4, R))[..., None]
    # бинт (96..128, 0..32)
    bn = np.ones((32, 32, 3), np.float32) * rgb((0.70, 0.69, 0.64))
    bn[::3] *= 0.86; bn[:, ::3] *= 0.92
    a[0:32, 96:128] = bn * (0.85 + 0.25 * fbm(32, 32, 4, 4, R))[..., None]
    # аптечка: лицевая сторона с зелёным крестом (32..96, 32..64), бок (96..128, 32..64)
    mk = np.ones((32, 64, 3), np.float32) * rgb((0.72, 0.71, 0.66)) * (0.85 + 0.25 * fbm(64, 32, 6, 3, R))[..., None]
    mk[4:28, 27:37] = rgb((0.10, 0.42, 0.16)); mk[11:21, 20:44] = rgb((0.10, 0.42, 0.16))
    mk[:2] *= 0.6; mk[-2:] *= 0.6; mk[:, :2] *= 0.6; mk[:, -2:] *= 0.6
    a[32:64, 32:96] = mk
    a[32:64, 96:128] = rgb((0.62, 0.61, 0.57)) * (0.8 + 0.3 * fbm(32, 32, 4, 4, R))[..., None]
    # шаурма: лаваш (0..64, 64..96), фольга (64..96, 64..96)
    lv = np.ones((32, 64, 3), np.float32) * rgb((0.66, 0.52, 0.32)) * (0.7 + 0.6 * fbm(64, 32, 8, 5, R))[..., None]
    lv -= (np.clip(fbm(64, 32, 12, 6, R) - 0.62, 0, 1) * 2.5)[..., None] * rgb((0.3, 0.3, 0.25))   # поджарки
    a[64:96, 0:64] = lv
    a[64:96, 64:96] = rgb((0.55, 0.56, 0.58)) * (0.5 + 1.0 * R.random((32, 32, 1)).astype(np.float32) * 0.6 + 0.3)
    # металл ключей (96..128, 64..96), бирка (0..32, 96..128), дерево ручки (32..64, 96..128), сталь молотка (64..96, 96..128)
    a[64:96, 96:128] = rgb((0.60, 0.52, 0.30)) * (0.7 + 0.5 * fbm(32, 32, 6, 6, R))[..., None]
    tag = np.ones((32, 32, 3), np.float32) * rgb((0.55, 0.12, 0.10)); tag[10:22, 6:26] = rgb((0.75, 0.72, 0.62))
    a[96:128, 0:32] = tag
    a[96:128, 32:64] = rgb((0.42, 0.30, 0.18)) * (0.6 + 0.7 * fbm(32, 32, 2, 12, R))[..., None]
    a[96:128, 64:96] = rgb((0.30, 0.31, 0.33)) * (0.6 + 0.7 * fbm(32, 32, 6, 6, R))[..., None]
    a[96:128, 96:128] = rgb((0.45, 0.46, 0.50)) * (0.7 + 0.5 * fbm(32, 32, 6, 6, R))[..., None]   # сталь ключа
    save("items", a)


def RC(x0, y0, x1, y1):
    """Прямоугольник атласа items (пиксели, начало сверху-слева) → UV-rect."""
    return (x0 / 128, 1 - y1 / 128, x1 / 128, 1 - y0 / 128)


# =====================================================================================
#  Помощники геометрии
# =====================================================================================
def quad(b, pts, m, hint, scale=(1.0, 1.0)):
    pts = [Vector(p) for p in pts]
    n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
    if n.dot(Vector(hint)) < 0:
        pts = pts[::-1]; n = -n
    su, sv = scale
    ax = max(range(3), key=lambda i: abs(n[i]))
    if ax == 2:
        uvs = [(p.x / su, p.y / sv) for p in pts]
    elif ax == 0:
        uvs = [(p.y / su, p.z / sv) for p in pts]
    else:
        uvs = [(p.x / su, p.z / sv) for p in pts]
    b.poly(pts, uvs, m)


def cylr(b, p0, p1, r0, r1, m, rect, segs=8, caps=True):
    """Цилиндр/конус с развёрткой в прямоугольник атласа."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    t = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
    u = ax.cross(t).normalized(); w = ax.cross(u)
    ring = lambda p, r, a: p + (u * math.cos(a) + w * math.sin(a)) * r
    u0, v0, u1, v1 = rect
    for i in range(segs):
        a0 = 2 * math.pi * i / segs; a1 = 2 * math.pi * (i + 1) / segs
        ua, ub = u0 + (u1 - u0) * i / segs, u0 + (u1 - u0) * (i + 1) / segs
        b.poly([ring(p0, r0, a0), ring(p0, r0, a1), ring(p1, r1, a1), ring(p1, r1, a0)], [(ua, v0), (ub, v0), (ub, v1), (ua, v1)], m)
    if caps:
        c = ((u0 + u1) / 2, (v0 + v1) / 2)
        if r1 > 1e-4:
            b.poly([ring(p1, r1, 2 * math.pi * i / segs) for i in range(segs)], [c] * segs, m)
        if r0 > 1e-4:
            b.poly([ring(p0, r0, -2 * math.pi * i / segs) for i in range(segs)], [c] * segs, m)


def rbox(b, mn, mx, m, rect, faces=('+X', '-X', '+Y', '-Y', '+Z', '-Z')):
    b.box(mn, mx, {k: (m, rect) for k in faces})


def export(name, obs):
    sc = bpy.context.scene
    for o in sc.objects:
        o.select_set(o in obs)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".gltf"), use_selection=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)


def clear_scene():
    for ob in list(bpy.context.scene.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


# =====================================================================================
#  Подъезд
# =====================================================================================
FH, HALL_D, HALL_W, SH_W = 2.8, 2.6, 3.0, 1.4
FL_Y0, FL_Y1, BACK = 2.6, 5.6, 7.0
NST = 9
RISE, RUN = 1.4 / NST, 3.0 / NST
TOP = 3 * FH + 2.6
APT_FLOOR = 3
DOOR_Y0, DOOR_Y1, DOOR_H = 0.8, 1.7, 2.05


def stairwell(M):
    coll = bpy.context.scene.collection
    b = B(); st = B(); rp = B()
    wall = M["pod_wall"]; green = M["pod_green"]; ceil = M["pod_ceiling"]; floor = M["pod_floor"]; step = M["pod_step"]
    WS = (2.8, 2.8)
    Z3 = APT_FLOOR * FH

    # --- перекрытия ---
    b.box((-SH_W, FL_Y0, -0.2), (SH_W, BACK, 0), {'+Z': floor}, scale=(1, 1))
    for k in range(4):
        z0 = k * FH
        f = {'+Z': floor}
        if k > 0:
            f['-Z'] = ceil
        b.box((-HALL_W, 0, z0 - 0.2), (HALL_W, HALL_D, z0), f, scale=(1, 1))
        if k > 0:
            b.box((-SH_W, HALL_D - 0.01, z0 - 0.2), (SH_W, HALL_D, z0), {'+Y': step}, scale=(1, 0.5))
    b.box((-HALL_W, 0, TOP), (HALL_W, HALL_D, TOP + 0.2), {'-Z': ceil}, scale=(1, 1))
    b.box((-SH_W, FL_Y0, TOP), (SH_W, BACK, TOP + 0.2), {'-Z': ceil}, scale=(1, 1))
    for k in range(3):
        h = k * FH + 1.4
        b.box((-SH_W, FL_Y1, h - 0.2), (SH_W, BACK, h), {'+Z': floor, '-Z': ceil, '-Y': step}, scale=(1, 0.5))

    # --- стены шахты ---
    b.box((-SH_W - 0.2, FL_Y0, 0), (-SH_W, BACK, TOP), {'+X': green}, scale=WS)
    b.box((SH_W, FL_Y0, 0), (SH_W + 0.2, BACK, TOP), {'-X': green}, scale=WS)
    b.box((-SH_W, BACK, 0), (SH_W, BACK + 0.2, TOP), {'-Y': green}, scale=WS)

    # --- стены площадок ---
    for k in range(4):
        z0 = k * FH; z1 = z0 + (FH if k < 3 else 2.6)
        b.box((-HALL_W, -0.2, z0), (HALL_W, 0, z1), {'+Y': wall}, scale=WS)
        b.box((-HALL_W, HALL_D, z0), (-SH_W, HALL_D + 0.2, z1), {'-Y': wall}, scale=WS)
        b.box((SH_W, HALL_D, z0), (HALL_W, HALL_D + 0.2, z1), {'-Y': wall}, scale=WS)
        b.box((HALL_W, 0, z0), (HALL_W + 0.2, HALL_D, z1), {'-X': wall}, scale=WS)
        if k == APT_FLOOR:                                            # проём двери Юрчика
            b.box((-HALL_W - 0.2, 0, z0), (-HALL_W, DOOR_Y0, z1), {'+X': wall, '+Y': step}, scale=WS)
            b.box((-HALL_W - 0.2, DOOR_Y1, z0), (-HALL_W, HALL_D, z1), {'+X': wall, '-Y': step}, scale=WS)
            b.box((-HALL_W - 0.2, DOOR_Y0, z0 + DOOR_H), (-HALL_W, DOOR_Y1, z1), {'+X': wall, '-Z': step}, scale=WS)
        else:
            b.box((-HALL_W - 0.2, 0, z0), (-HALL_W, HALL_D, z1), {'+X': wall}, scale=WS)
        # двери квартир (декор)
        dv = lambda v: (M["doors"], (v / 4, 0, (v + 1) / 4, 1))
        if k != APT_FLOOR:
            b.box((-HALL_W, 0.8, z0), (-HALL_W + 0.04, 1.7, z0 + DOOR_H), {'+X': dv((k + 1) % 3), '+Y': step, '-Y': step, '+Z': step})
        b.box((HALL_W - 0.04, 0.8, z0), (HALL_W, 1.7, z0 + DOOR_H), {'-X': dv(k % 3), '+Y': step, '-Y': step, '+Z': step})
        if k > 0:
            for x, v in ((-1.85, (k + 2) % 3), (1.85, (k + 1) % 3)):
                b.box((x - 0.45, 0, z0), (x + 0.45, 0.04, z0 + DOOR_H), {'+Y': dv(v), '+X': step, '-X': step, '+Z': step})
        # лампочка под потолком
        if k != 2:
            b.box((-0.06, 1.24, z1 - 0.26), (0.06, 1.36, z1 - 0.12), {kk: (M["glass"], (0, 0, 1, 1)) for kk in ('+X', '-X', '+Y', '-Y', '-Z')})
        b.cyl((0, 1.3, z1 - 0.12), (0, 1.3, z1 - 0.2), 0.012, 0.012, M["metal"], segs=4)
    # первый этаж: входная дверь изнутри, почтовые ящики, щиток
    b.box((-0.7, 0, 0), (0.7, 0.05, 2.2), {'+Y': (M["door"], (0, 0, 1, 1)), '+X': M["metal"], '-X': M["metal"], '+Z': M["metal"]})
    b.box((-2.7, 0, 1.0), (-1.3, 0.07, 1.7), {'+Y': (M["mail"], (0, 0, 1, 1)), '+X': M["metal"], '-X': M["metal"], '+Z': M["metal"], '-Z': M["metal"]})
    b.box((1.5, 0, 1.2), (2.2, 0.12, 2.0), {k_: M["metal"] for k_ in ('+Y', '+X', '-X', '+Z', '-Z')}, scale=(0.7, 0.8))
    # закуток под лестницей закрыт стенкой
    quad(b, [(0.1, 3.03, 0), (0.1, BACK, 0), (0.1, BACK, 1.2), (0.1, FL_Y1, 1.2)], step, (-1, 0, 0))

    # --- окна и батареи на межэтажных площадках ---
    for k in range(3):
        h = k * FH + 1.4
        b.box((-0.6, BACK - 0.02, h + 0.9), (0.6, BACK, h + 2.0), {'-Y': (M["window"], (0, 0, 1, 1))})
        b.box((-0.75, BACK - 0.12, h + 0.82), (0.75, BACK, h + 0.9), {k_: step for k_ in ('-Y', '+Z', '+X', '-X')}, scale=(1, 0.5))
        b.box((-0.5, BACK - 0.13, h + 0.15), (0.5, BACK - 0.02, h + 0.72),
              {'-Y': (M["radiator"], (0, 0, 2, 1)), '+Z': M["metal"], '+X': M["metal"], '-X': M["metal"]})

    # --- марши ---
    for k in range(3):
        z0 = k * FH; h = z0 + 1.4
        for i in range(NST):
            ya, yb = FL_Y0 + i * RUN, FL_Y0 + (i + 1) * RUN
            st.box((0.1, ya, z0 + i * RISE), (SH_W, yb, z0 + (i + 1) * RISE), {'+Z': step, '-Y': step, '-X': step}, scale=(1, 0.5))
            yb2, ya2 = FL_Y1 - i * RUN, FL_Y1 - (i + 1) * RUN
            st.box((-SH_W, ya2, h + i * RISE), (-0.1, yb2, h + (i + 1) * RISE), {'+Z': step, '+Y': step, '+X': step}, scale=(1, 0.5))
        # низ маршей и косоуры
        quad(b, [(0.1, FL_Y0, z0 - 0.2), (SH_W, FL_Y0, z0 - 0.2), (SH_W, FL_Y1, h - 0.2), (0.1, FL_Y1, h - 0.2)], ceil, (0, 0, -1))
        quad(b, [(-SH_W, FL_Y1, h - 0.2), (-0.1, FL_Y1, h - 0.2), (-0.1, FL_Y0, z0 + FH - 0.2), (-SH_W, FL_Y0, z0 + FH - 0.2)], ceil, (0, 0, -1))
        quad(st, [(0.1, FL_Y0, z0 - 0.2), (0.1, FL_Y1, h - 0.2), (0.1, FL_Y1, h), (0.1, FL_Y0, z0)], step, (-1, 0, 0), scale=(1, 0.5))
        quad(st, [(-0.1, FL_Y1, h - 0.2), (-0.1, FL_Y0, z0 + FH - 0.2), (-0.1, FL_Y0, z0 + FH), (-0.1, FL_Y1, h)], step, (1, 0, 0), scale=(1, 0.5))
        # пандусы-коллизии (по середине ступеней)
        o = RUN / 2
        quad(rp, [(0.1, FL_Y0 - o, z0), (SH_W, FL_Y0 - o, z0), (SH_W, FL_Y1 - o, h), (0.1, FL_Y1 - o, h)], step, (0, 0, 1))
        quad(rp, [(-SH_W, FL_Y1 + o, h), (-0.1, FL_Y1 + o, h), (-0.1, FL_Y0 + o, z0 + FH), (-SH_W, FL_Y0 + o, z0 + FH)], step, (0, 0, 1))
        # стыки пандусов с площадками и невидимые «перила», чтобы нельзя было шагнуть с марша на марш
        quad(rp, [(0.1, FL_Y1 - o, h), (SH_W, FL_Y1 - o, h), (SH_W, FL_Y1 + 0.05, h), (0.1, FL_Y1 + 0.05, h)], step, (0, 0, 1))
        quad(rp, [(-SH_W, FL_Y0 + o, z0 + FH), (-0.1, FL_Y0 + o, z0 + FH), (-0.1, FL_Y0 - 0.05, z0 + FH), (-SH_W, FL_Y0 - 0.05, z0 + FH)], step, (0, 0, 1))
        e = 0.55; dz = 1.4 * e / 3.0                                 # перила короче маршей: за торцы не цепляются на повороте
        quad(rp, [(0.1, FL_Y0 + e, z0 + dz), (0.1, FL_Y1 - e, h - dz), (0.1, FL_Y1 - e, h - dz + 1.0), (0.1, FL_Y0 + e, z0 + dz + 1.0)], step, (1, 0, 0))
        quad(rp, [(-0.1, FL_Y1 - e, h + dz), (-0.1, FL_Y0 + e, z0 + FH - dz), (-0.1, FL_Y0 + e, z0 + FH - dz + 1.0), (-0.1, FL_Y1 - e, h + dz + 1.0)], step, (-1, 0, 0))
        # перила
        for (x, ya, za, yb, zb) in ((0.06, FL_Y0, z0, FL_Y1, h), (-0.06, FL_Y1, h, FL_Y0, z0 + FH)):
            st.cyl((x, ya, za + 0.92), (x, yb, zb + 0.92), 0.025, 0.025, M["green_metal"], segs=4)
            for t in (0.0, 0.25, 0.5, 0.75, 1.0):
                y = ya + (yb - ya) * t; z = za + (zb - za) * t
                st.cyl((x, y, z + 0.05), (x, y, z + 0.92), 0.012, 0.012, M["metal"], segs=4)
        st.cyl((0.06, FL_Y1, h + 0.92), (-0.06, FL_Y1, h + 0.92), 0.025, 0.025, M["green_metal"], segs=4)
        st.cyl((-0.06, FL_Y0, z0 + FH + 0.92), (0.06, FL_Y0, z0 + FH + 0.92), 0.025, 0.025, M["green_metal"], segs=4)

    # --- квартира Юрчика ---
    wp, pq = M["wallpaper"], M["parquet"]
    AH = 2.5
    cx0, cx1, cy0, cy1 = -6.2, -HALL_W - 0.2, 0.2, 2.3            # коридор
    rx0, rx1, ry0, ry1 = -10.2, -6.2, -0.6, 3.6                   # комната
    WP = (1.0, 1.0)
    b.box((cx0, cy0, Z3 - 0.1), (cx1, cy1, Z3), {'+Z': pq}, scale=(1.5, 1.5))
    b.box((rx0, ry0, Z3 - 0.1), (rx1, ry1, Z3), {'+Z': pq}, scale=(1.5, 1.5))
    b.box((cx0, cy0, Z3 + AH), (cx1, cy1, Z3 + AH + 0.1), {'-Z': ceil}, scale=(1, 1))
    b.box((rx0, ry0, Z3 + AH), (rx1, ry1, Z3 + AH + 0.1), {'-Z': ceil}, scale=(1, 1))
    b.box((cx0, cy0 - 0.2, Z3), (cx1, cy0, Z3 + AH), {'+Y': wp}, scale=WP)
    b.box((cx0, cy1, Z3), (cx1, cy1 + 0.2, Z3 + AH), {'-Y': wp}, scale=WP)
    # стена у входа (со стороны квартиры)
    b.box((cx1, cy0, Z3), (cx1 + 0.01, DOOR_Y0, Z3 + AH), {'-X': wp}, scale=WP)
    b.box((cx1, DOOR_Y1, Z3), (cx1 + 0.01, cy1, Z3 + AH), {'-X': wp}, scale=WP)
    b.box((cx1, DOOR_Y0, Z3 + DOOR_H), (cx1 + 0.01, DOOR_Y1, Z3 + AH), {'-X': wp}, scale=WP)
    # стена между коридором и комнатой с проёмом y 0.6..1.9
    for (ya, yb, za, zb) in ((ry0, 0.6, Z3, Z3 + AH), (1.9, ry1, Z3, Z3 + AH), (0.6, 1.9, Z3 + 2.05, Z3 + AH)):
        b.box((cx0 - 0.12, ya, za), (cx0, yb, zb), {'+X': wp, '-X': wp, '+Y': wp, '-Y': wp, '-Z': wp}, scale=WP)
    b.box((rx0 - 0.2, ry0, Z3), (rx0, ry1, Z3 + AH), {'+X': wp}, scale=WP)
    b.box((rx0, ry0 - 0.2, Z3), (rx1, ry0, Z3 + AH), {'+Y': wp}, scale=WP)
    b.box((rx0, ry1, Z3), (rx1, ry1 + 0.2, Z3 + AH), {'-Y': wp}, scale=WP)
    wood, fab = M["wood"], M["fabric"]
    allf = lambda m: {k_: m for k_ in ('+X', '-X', '+Y', '-Y', '+Z')}
    # прихожая: вешалка с курткой, полка для обуви
    b.box((-5.6, cy0, Z3 + 1.65), (-4.2, cy0 + 0.06, Z3 + 1.75), allf(wood), scale=(1, 1))
    b.box((-5.3, cy0 + 0.02, Z3 + 0.75), (-4.8, cy0 + 0.20, Z3 + 1.68), allf(fab), scale=(0.5, 0.5))
    b.box((-5.6, cy0, Z3), (-4.4, cy0 + 0.32, Z3 + 0.38), allf(wood), scale=(1, 1))
    # комната: диван, ковёр, стенка, стол с телевизором, окно, люстра
    b.box((rx0 + 0.02, 0.4, Z3), (rx0 + 0.95, 2.6, Z3 + 0.42), allf(fab), scale=(0.6, 0.6))
    b.box((rx0 + 0.02, 0.4, Z3 + 0.42), (rx0 + 0.28, 2.6, Z3 + 0.88), allf(fab), scale=(0.6, 0.6))
    b.box((rx0, 0.3, Z3 + 1.0), (rx0 + 0.02, 2.7, Z3 + 2.35), {'+X': (M["carpet"], (0, 0, 1, 1))})
    b.box((-9.4, ry1 - 0.5, Z3), (-6.9, ry1, Z3 + 2.0), allf(wood), scale=(1.2, 1.0))
    b.box((-9.3, ry1 - 0.52, Z3 + 0.9), (-7.0, ry1 - 0.5, Z3 + 1.9), {'-Y': (M["window"], (0.1, 0.4, 0.45, 0.62))})   # стекло серванта
    b.box((-7.3, ry0 + 0.1, Z3), (-6.5, ry0 + 0.7, Z3 + 0.62), allf(wood), scale=(1, 1))
    tvr = (M["tv"], (0, 0, 1, 1)); tvs = (M["tv"], (0, 0, 0.08, 0.08))
    b.box((-7.2, ry0 + 0.15, Z3 + 0.62), (-6.6, ry0 + 0.6, Z3 + 1.08), {'+Y': tvr, '-X': tvs, '+X': tvs, '+Z': tvs, '-Y': tvs})
    b.box((-9.3, ry0, Z3 + 0.9), (-8.0, ry0 + 0.02, Z3 + 2.1), {'+Y': (M["window"], (0, 0, 1, 1))})
    b.box((-9.5, ry0 + 0.02, Z3 + 0.2), (-9.25, ry0 + 0.1, Z3 + 2.3), allf(fab), scale=(0.3, 2))    # шторы
    b.box((-8.05, ry0 + 0.02, Z3 + 0.2), (-7.8, ry0 + 0.1, Z3 + 2.3), allf(fab), scale=(0.3, 2))
    b.box((-8.3, 1.4, Z3 + AH - 0.3), (-8.1, 1.6, Z3 + AH - 0.12), {kk: (M["glass"], (0, 0, 1, 1)) for kk in ('+X', '-X', '+Y', '-Y', '-Z')})
    b.box((cx0 + 1.4, 1.2, Z3 + AH - 0.22), (cx0 + 1.52, 1.32, Z3 + AH - 0.1), {kk: (M["glass"], (0, 0, 1, 1)) for kk in ('+X', '-X', '+Y', '-Y', '-Z')})

    main = b.build("Stairwell", coll)
    steps = st.build("Stairs_nocol", coll)
    ramps = rp.build("StairRamp-colonly", coll)
    # дверь квартиры Юрчика — отдельный объект, origin на петлях
    d = B()
    dr = (M["doors"], (0.75, 0, 1, 1))
    d.box((-0.05, 0, 0), (0, DOOR_Y1 - DOOR_Y0, DOOR_H), {'+X': dr, '-X': dr, '+Y': step, '-Y': step, '+Z': step})
    door = d.build("AptDoor", coll)
    door.location = (-HALL_W, DOOR_Y0, Z3)
    export("stairwell", [main, steps, ramps, door])
    return {"stairwell_polys": len(main.data.polygons) + len(steps.data.polygons)}


# =====================================================================================
#  Гараж
# =====================================================================================
def garage(M):
    coll = bpy.context.scene.collection
    b = B()
    gw, gd, gh, t = 3.6, 6.0, 2.6, 0.15
    gwall, brick, fl = M["gwall"], M["garage_in"], M["garage_floor"]
    y0, y1 = -gd / 2, gd / 2
    b.box((0, y0, 0), (gw, y1, gh), {'+X': gwall, '-X': gwall, '+Y': gwall}, scale=(2, 2))
    ox0, ox1, oh = 0.4, 3.2, 2.2
    b.box((0, y0, 0), (ox0, y0 + t, gh), {'-Y': gwall, '+Y': brick, '+X': gwall}, scale=(2, 2))
    b.box((ox1, y0, 0), (gw, y0 + t, gh), {'-Y': gwall, '+Y': brick, '-X': gwall}, scale=(2, 2))
    b.box((ox0, y0, oh), (ox1, y0 + t, gh), {'-Y': gwall, '+Y': brick, '-Z': gwall}, scale=(2, 2))
    b.box((0, y0, 0), (t, y1, gh - t), {'+X': brick}, scale=(1.5, 1.5))
    b.box((gw - t, y0, 0), (gw, y1, gh - t), {'-X': brick}, scale=(1.5, 1.5))
    b.box((0, y1 - t, 0), (gw, y1, gh - t), {'-Y': brick}, scale=(1.5, 1.5))
    b.box((0, y0, gh - t), (gw, y1, gh), {'-Z': M["pod_ceiling"]}, scale=(1, 1))
    b.box((t, y0 - 0.3, -0.05), (gw - t, y1 - t, 0.02), {'+Z': fl, '-Y': fl}, scale=(2, 2))
    b.box((-0.2, y0 - 0.4, gh), (gw + 0.2, y1 + 0.2, gh + 0.15), {k: M["roof"] for k in ('+X', '-X', '+Y', '-Y', '-Z')}, scale=(3, 3))
    b.box((-0.1, y0 - 0.3, gh + 0.15), (gw + 0.1, y1 + 0.1, gh + 0.32), {k: M["snow"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(4, 4))
    wood, metal = M["wood"], M["metal"]
    allf = lambda m: {k_: m for k_ in ('+X', '-X', '+Y', '-Y', '+Z')}
    # верстак у задней стены, полка слева, ящики, канистра
    b.box((0.3, y1 - 0.95, 0.80), (3.3, y1 - t, 0.86), allf(wood), scale=(1, 1))
    for x in (0.35, 3.15):
        b.box((x, y1 - 0.9, 0), (x + 0.08, y1 - 0.25, 0.80), allf(wood), scale=(1, 1))
    b.box((t, -1.6, 1.25), (t + 0.35, 1.2, 1.29), allf(wood), scale=(1, 1))
    b.box((t + 0.03, -1.3, 1.29), (t + 0.3, -0.9, 1.55), allf(M["green_metal"]), scale=(0.5, 0.5))
    b.box((t + 0.05, 0.2, 1.29), (t + 0.3, 0.7, 1.48), allf(wood), scale=(0.5, 0.5))
    b.box((2.7, 0.9, 0), (3.3, 1.6, 0.5), allf(wood), scale=(0.7, 0.7))
    b.box((2.75, -0.2, 0), (3.1, 0.25, 0.42), allf(M["green_metal"]), scale=(0.5, 0.5))
    b.cyl((gw / 2, 0.4, gh - t), (gw / 2, 0.4, gh - 0.45), 0.008, 0.008, metal, segs=4)
    b.box((gw / 2 - 0.05, 0.35, gh - 0.56), (gw / 2 + 0.05, 0.45, gh - 0.45), {kk: (M["glass"], (0, 0, 1, 1)) for kk in ('+X', '-X', '+Y', '-Y', '-Z')})
    main = b.build("GarageYur", coll)
    leaves = []
    for name, hx, sgn, u0 in (("GarageDoorL", ox0, 1, 0.25), ("GarageDoorR", ox1, -1, 0.375)):
        d = B()
        wd = (ox1 - ox0) / 2
        xa, xb = (0, wd) if sgn > 0 else (-wd, 0)
        r = (M["gdoor"], (u0, 0, u0 + 0.125, 1))
        d.box((xa, -0.05, 0), (xb, 0, oh), {'-Y': r, '+Y': r, '+X': metal, '-X': metal, '+Z': metal})
        ob = d.build(name, coll)
        ob.location = (hx, y0, 0)
        leaves.append(ob)
    export("garage_yur", [main] + leaves)
    return {"garage_polys": len(main.data.polygons)}


# =====================================================================================
#  Предметы и иконки
# =====================================================================================
ITEMS = {}


def item(name, cells, view=(0.45, -1.0, 0.55), roll=0.0):
    def deco(fn):
        ITEMS[name] = (fn, cells, view, roll)
        return fn
    return deco


@item("bottle", (1, 2))
def it_bottle(b, m):
    glass, label = RC(0, 0, 32, 30), RC(0, 30, 32, 52)
    cylr(b, (0, 0, 0), (0, 0, 0.06), 0.034, 0.034, m, RC(0, 52, 32, 64))
    cylr(b, (0, 0, 0.06), (0, 0, 0.15), 0.034, 0.034, m, label, caps=False)
    cylr(b, (0, 0, 0.15), (0, 0, 0.20), 0.034, 0.014, m, glass, caps=False)
    cylr(b, (0, 0, 0.20), (0, 0, 0.27), 0.014, 0.012, m, glass)


@item("brick", (2, 1), view=(0.5, -1.0, 0.7))
def it_brick(b, m):
    rbox(b, (-0.125, -0.06, 0), (0.125, 0.06, 0.065), m, RC(32, 0, 96, 32))


@item("medkit", (2, 2), view=(0.35, -1.0, 0.75))
def it_medkit(b, m):
    side = RC(96, 32, 128, 64)
    rbox(b, (-0.13, -0.09, 0), (0.13, 0.09, 0.09), m, side, ('+X', '-X', '+Y', '-Y', '-Z'))
    b.box((-0.13, -0.09, 0), (0.13, 0.09, 0.09), {'+Z': (m, RC(32, 32, 96, 64))})
    rbox(b, (-0.04, -0.012, 0.09), (0.04, 0.012, 0.105), m, RC(96, 64, 128, 96))                  # ручка


@item("bandage", (1, 1), view=(0.6, -1.0, 0.6))
def it_bandage(b, m):
    cylr(b, (-0.035, 0, 0.03), (0.035, 0, 0.03), 0.03, 0.03, m, RC(96, 0, 128, 32), segs=8)


@item("shawarma", (1, 2), view=(0.25, -1.0, 0.35))
def it_shawarma(b, m):
    cylr(b, (0, 0, 0), (0, 0, 0.09), 0.028, 0.034, m, RC(64, 64, 96, 96))
    cylr(b, (0, 0, 0.09), (0, 0, 0.21), 0.034, 0.030, m, RC(0, 64, 64, 96))


@item("key_garage", (1, 1), view=(0.15, -1.0, 0.9))
def it_key_garage(b, m):
    steel, tag = RC(96, 96, 128, 128), RC(0, 96, 32, 128)
    cylr(b, (0, 0.03, 0), (0, 0.03, 0.006), 0.016, 0.016, m, steel, segs=6)
    rbox(b, (-0.004, -0.045, 0), (0.004, 0.02, 0.005), m, steel)
    rbox(b, (-0.004, -0.045, 0), (0.010, -0.032, 0.005), m, steel)
    rbox(b, (-0.022, 0.045, 0), (0.022, 0.085, 0.004), m, tag)


@item("key_home", (1, 1), view=(0.15, -1.0, 0.9))
def it_key_home(b, m):
    brass, steel = RC(96, 64, 128, 96), RC(96, 96, 128, 128)
    for dx, rot, r in ((-0.012, 0.35, brass), (0.014, -0.3, steel)):
        c, s = math.cos(rot), math.sin(rot)
        tf = lambda x, y, z: (dx + x * c - y * s, x * s + y * c, z)
        cylr(b, tf(0, 0.028, 0), tf(0, 0.028, 0.005), 0.014, 0.014, m, r, segs=6)
        for (x0, yy0, x1, yy1) in ((-0.004, -0.045, 0.004, 0.016), (-0.004, -0.045, 0.009, -0.034)):
            pts = [tf(x0, yy0, 0.005), tf(x1, yy0, 0.005), tf(x1, yy1, 0.005), tf(x0, yy1, 0.005)]
            quad(b, pts, m, (0, 0, 1))
            b.uv[-1] = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    cylr(b, (0, 0.048, 0.002), (0, 0.048, 0.005), 0.020, 0.020, m, steel, segs=8)


@item("hammer", (1, 3), view=(0.5, -1.0, 0.25))
def it_hammer(b, m):
    wood, steel = RC(32, 96, 64, 128), RC(64, 96, 96, 128)
    cylr(b, (0, 0, 0), (0, 0, 0.30), 0.016, 0.013, m, wood, segs=6)
    rbox(b, (-0.055, -0.016, 0.275), (0.035, 0.016, 0.315), m, steel)
    rbox(b, (0.035, -0.012, 0.283), (0.075, 0.012, 0.307), m, steel)


def icon(name, ob, cells, view, roll):
    sc = bpy.context.scene
    w, h = cells[0] * 64, cells[1] * 64
    sc.render.resolution_x, sc.render.resolution_y = w, h
    d = Vector(view).normalized()
    cam = sc.camera
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    rot = cam.rotation_euler.to_matrix()
    right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    xs = [p.dot(right) for p in pts]; ys = [p.dot(up) for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    pw, ph = max(xs) - min(xs), max(ys) - min(ys)
    m = max(w, h)
    cam.data.ortho_scale = max(pw / (w / m), ph / (h / m)) * 1.12
    cam.location = right * cx + up * cy + d * 3
    sc.render.filepath = os.path.join(ICONS, name + ".png")
    bpy.ops.render.render(write_still=True)


def items(M):
    sc = bpy.context.scene
    coll = sc.collection
    os.makedirs(ICONS, exist_ok=True)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
    sc.display.shading.show_object_outline = True
    sc.display.shading.object_outline_color = (0.0, 0.0, 0.0)
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    cam_d = bpy.data.cameras.new("IconCam"); cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new("IconCam", cam_d); coll.objects.link(cam); sc.camera = cam
    out = {}
    for name, (fn, cells, view, roll) in ITEMS.items():
        b = B()
        fn(b, M["items"])
        ob = b.build("Item_" + name, coll)
        export("item_" + name, [ob])
        for o in sc.objects:
            o.hide_render = o is not ob and o is not cam
        icon(name, ob, cells, view, roll)
        out[name] = len(ob.data.polygons)
    return out


# =====================================================================================
def main():
    clear_scene()
    if not ONLY or "tex" in ONLY:
        tex_pod_wall(); tex_pod_green(); tex_simple(); tex_doors(); tex_misc(); tex_items()
    M = {
        "pod_wall": mat("PodWall", "pod_wall"), "pod_green": mat("PodGreen", "pod_green"),
        "pod_ceiling": mat("PodCeiling", "pod_ceiling"), "pod_floor": mat("PodFloor", "pod_floor", rough=0.6),
        "pod_step": mat("PodStep", "pod_step"), "doors": mat("AptDoors", "apt_doors", rough=0.7),
        "door": mat("Door", "door", rough=0.6), "mail": mat("Mailboxes", "mailboxes", rough=0.6),
        "window": mat("PodWindow", "pod_window", "pod_window_emission", rough=0.4), "radiator": mat("Radiator", "radiator", rough=0.6),
        "metal": mat("Metal", "metal", rough=0.6), "green_metal": mat("GreenMetal", "green_metal", rough=0.6),
        "glass": mat("LampGlass", "lamp_glass", "lamp_glass", rough=0.3),
        "wallpaper": mat("Wallpaper", "wallpaper"), "parquet": mat("Parquet", "parquet", rough=0.5),
        "carpet": mat("Carpet", "carpet"), "fabric": mat("Fabric", "fabric"), "wood": mat("Wood", "wood"),
        "tv": mat("TV", "tv", "tv_emission", rough=0.4),
        "gwall": mat("GarageWall", "garage_wall"), "gdoor": mat("GarageDoors", "garage_doors", rough=0.6),
        "garage_in": mat("GarageIn", "garage_in"), "garage_floor": mat("GarageFloor", "garage_floor", rough=0.7),
        "roof": mat("Roof", "roof"), "snow": mat("Snow", "snow"),
        "items": mat("Items", "items", rough=0.6),
    }
    info = {}
    if not ONLY or "stairwell" in ONLY:
        info.update(stairwell(M)); clear_scene()
    if not ONLY or "garage" in ONLY:
        info.update(garage(M)); clear_scene()
    if not ONLY or "items" in ONLY:
        info.update(items(M))
    print("BUILD_MVP " + str(info))


main()
