# Пропсы микрорайона «Паскот» (этап B, docs/CITY_PLAN.md): гаражи, машины, трамвай, заборы, теплотрасса,
# лестницы, стройка, дворовые мелочи — каждая модель ровно по габариту своего серого блока.
#
# Вход:   tools/district_blocks.json   (пишет tools/make_district_blockout.py --json-only)
# Выход:  assets/models/district/props/<модель>.gltf   — по одной на каждый уникальный (тип, размер, вариант)
#         tools/district_props.json                     — какой блок какой моделью заменить (для этапа C)
#         в Blender: сцена «DistrictProps» (все уникальные модели в ряд) и копии на своих местах в сцене «District»
#
# Запуск в открытом Blender (Blender MCP / вкладка Scripting):
#   DISTRICT_ROOT = r"<папка проекта>"; exec(open(DISTRICT_ROOT + r"\tools\blender\build_district_props.py", encoding="utf-8").read())
# Текстуры (один раз):  blender -b --python tools/blender/district_textures_props.py
#
# Локальные оси модели: X — ширина блока (sx), −Y Blender = +Z Godot — «перёд», Z — вверх; опора — центр низа.
# У лестниц низ у −Y (Godot +Z), верх у +Y — как у BlockoutBox.
import bpy
import json
import math
import os
import random
import zlib
from mathutils import Vector

ROOT = globals().get("DISTRICT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
OUT = os.path.join(ROOT, "assets", "models", "district", "props")

ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), ns)
ns["TEX"] = os.path.join(ROOT, "assets", "textures")
B, mat, M = ns["B"], ns["mat"], ns["M"]
ns["build_materials"]()
M["brick"] = mat("BrickDark", "brick_dark")
M["veh"] = mat("Vehicles", "vehicles", rough=0.5)
M["cfence"] = mat("FenceConcrete", "fence_concrete")
M["pipe"] = mat("PipeInsul", "pipe_insul", rough=0.6)
M["yellow"] = mat("PaintYellow", "paint_yellow", rough=0.6)

SIDES = ('+X', '-X', '+Y', '-Y')
TOP = ('+Z',)
ALL = SIDES + ('+Z', '-Z')


def bx(b, x0, y0, z0, x1, y1, z1, m, faces=SIDES + TOP, scale=(2, 2)):
    b.box((min(x0, x1), min(y0, y1), min(z0, z1)), (max(x0, x1), max(y0, y1), max(z0, z1)), {k: m for k in faces}, scale=scale)


def snow(b, x0, y0, x1, y1, z, t=0.14):
    bx(b, x0, y0, z, x1, y1, z + t, M["snow"], scale=(3, 3))


def AR(c0, c1, row, pad=0.012):
    """Прямоугольник атласа vehicles: колонки c0..c1 (из 4), ряд row (0 — верхний)."""
    return (c0 / 4 + pad, 1 - (row + 1) / 4 + pad, c1 / 4 - pad, 1 - row / 4 - pad)


def gd(i):
    """Одна из 4 створок атласа garage_doors: зелёный, синий, рыжий профнастил, ржавый металл."""
    return (M["gdoor"], (i / 4 + 0.01, 0.02, (i + 1) / 4 - 0.01, 0.98))


def opoly(b, pts, uvs, m, c):
    """Полигон, развёрнутый наружу от точки c (чтобы не думать о порядке обхода)."""
    pts = [Vector(p) for p in pts]
    n = Vector((0, 0, 0))
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        n += Vector(((p.y - q.y) * (p.z + q.z), (p.z - q.z) * (p.x + q.x), (p.x - q.x) * (p.y + q.y)))
    fc = sum(pts, Vector((0, 0, 0))) / len(pts)
    if n.dot(fc - Vector(c)) < 0:
        pts.reverse()
        uvs = list(reversed(uvs))
    b.poly([tuple(p) for p in pts], uvs, m)


def extrude(b, prof, a0, a1, axis, mats, cap, c):
    """Вытянуть замкнутый профиль [(p, z), ...] вдоль оси 'x' или 'y' от a0 до a1.
    mats[i] — материал грани между точками i и i+1: материал или (материал, прямоугольник UV); cap — торцы."""
    P = (lambda a, p, z: (a, p, z)) if axis == 'x' else (lambda a, p, z: (p, a, z))
    n = len(prof)
    for i in range(n):
        (p0, z0), (p1, z1) = prof[i], prof[(i + 1) % n]
        m = mats[i]
        if m is None:
            continue
        pts = [P(a0, p0, z0), P(a1, p0, z0), P(a1, p1, z1), P(a0, p1, z1)]
        if isinstance(m, tuple):
            mm, (u0, v0, u1, v1) = m
            uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        else:
            mm = m
            L = math.hypot(p1 - p0, z1 - z0)
            uvs = [(a0 / 3, 0), (a1 / 3, 0), (a1 / 3, L / 3), (a0 / 3, L / 3)]
        opoly(b, pts, uvs, mm, c)
    if cap is not None:
        mm, (u0, v0, u1, v1) = cap
        ps = [q[0] for q in prof]; zs = [q[1] for q in prof]
        pu = lambda p: u0 + (p - min(ps)) / (max(ps) - min(ps) + 1e-6) * (u1 - u0)
        zv = lambda z: v0 + (z - min(zs)) / (max(zs) - min(zs) + 1e-6) * (v1 - v0)
        for a in (a0, a1):
            opoly(b, [P(a, p, z) for p, z in prof], [(pu(p), zv(z)) for p, z in prof], mm, c)


def rail_line(b, p0, p1, h=1.0, step=2.0, m=None, mid=True):
    """Перила от p0 до p1 (точки по низу): стойки, поручень, средняя перекладина."""
    m = m or M["metal"]
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    n = max(1, round(L / step))
    for i in range(n + 1):
        q = p0.lerp(p1, i / n)
        b.cyl(q, q + Vector((0, 0, h)), 0.03, 0.03, m, segs=4)
    up = Vector((0, 0, h))
    b.cyl(p0 + up, p1 + up, 0.035, 0.035, m, segs=4)
    if mid:
        b.cyl(p0 + up * 0.5, p1 + up * 0.5, 0.025, 0.025, m, segs=4)


# ======================================================================================================
# СТРОЕНИЯ
# ======================================================================================================
def garage_row(b, sx, sy, sz, r, v):
    """Ряд гаражей: ворота на −Y, плоская крыша под снегом ровно на высоте блока (по крышам ходят)."""
    hx, hy = sx / 2, sz / 2
    n = max(1, round(sx / 3.3))
    gw = sx / n
    wh = sy - 0.22
    b.box((-hx, -hy, 0), (hx, hy, wh), {'+X': M["gwall"], '-X': M["gwall"], '+Y': M["gwall"]}, scale=(2, 2))
    for i in range(n):
        x0 = -hx + i * gw
        b.box((x0, -hy, 0), (x0 + 0.3, -hy + 0.01, wh), {'-Y': M["gwall"]}, scale=(2, 2))
        b.box((x0 + gw - 0.3, -hy, 0), (x0 + gw, -hy + 0.01, wh), {'-Y': M["gwall"]}, scale=(2, 2))
        b.box((x0 + 0.3, -hy, 2.0), (x0 + gw - 0.3, -hy + 0.01, wh), {'-Y': M["gwall"]}, scale=(2, 2))
        b.box((x0 + 0.3, -hy + 0.12, 0), (x0 + gw - 0.3, -hy + 0.13, 2.0), {'-Y': gd(r.randint(0, 3))})
        for xs in (x0 + 0.3, x0 + gw - 0.3):                                   # откосы ниши ворот
            b.box((xs - 0.005, -hy, 0), (xs + 0.005, -hy + 0.12, 2.0), {'+X': M["gwall"], '-X': M["gwall"]}, scale=(2, 2))
    bx(b, -hx - 0.1, -hy - 0.35, wh, hx + 0.1, hy, wh + 0.1, M["roof"], faces=SIDES + ('-Z',), scale=(3, 3))
    bx(b, -hx - 0.1, -hy - 0.35, wh + 0.1, hx + 0.1, hy, sy, M["snow"], scale=(4, 4))


def shell_row(b, sx, sy, sz, r, v):
    """Ряд гаражей-«ракушек»: металлические укрытия со скошенным верхом, между ними щели."""
    along_x = sx >= sz
    L, D = (sx, sz) if along_x else (sz, sx)
    n = max(1, round(L / 2.9))
    w = L / n
    for i in range(n):
        a0 = -L / 2 + i * w + 0.12
        a1 = a0 + w - 0.24
        d = D / 2 - 0.05
        prof = [(-d, 0), (d, 0), (d, sy * 0.62), (d * 0.45, sy - 0.14), (-d * 0.7, sy - 0.14), (-d, sy * 0.75)]
        k = r.randint(0, 3)
        side = gd(k)
        mats = [None, side, M["snow"], M["snow"], M["snow"], side]
        extrude(b, prof, a0, a1, 'x' if along_x else 'y', mats, side, (0, 0, sy / 2) if True else None)


def sheds(b, sx, sy, sz, r, v):
    """Ряд дощатых сараев: двери через каждые ~2 м, односкатная крыша под снегом."""
    hx, hy = sx / 2, sz / 2
    hf, hb = sy - 0.2, sy - 0.6
    bx(b, -hx, -hy, 0, hx, hy, hb, M["wood"], faces=('+X', '-X', '+Y'), scale=(2, 1))
    b.box((-hx, -hy, 0), (hx, hy, hf), {'-Y': M["wood"]}, scale=(2, 1))
    n = max(1, round(sx / 2.2))
    for i in range(n):
        x = -hx + sx * (i + 0.5) / n
        b.box((x - 0.45, -hy - 0.03, 0.05), (x + 0.45, -hy, 1.9), {'-Y': (M["door"], (0.05, 0.05, 0.95, 0.95))})
        b.box((x + sx / n / 2 - 0.04, -hy - 0.05, 0), (x + sx / n / 2 + 0.04, -hy, hf), {k: M["bark"] for k in ('-Y', '+X', '-X')}, scale=(1, 2))
    roof = [(-hx - 0.2, -hy - 0.35, hf + 0.2), (hx + 0.2, -hy - 0.35, hf + 0.2), (hx + 0.2, hy + 0.15, hb + 0.2), (-hx - 0.2, hy + 0.15, hb + 0.2)]
    b.poly(roof, [(p[0] / 3, p[1] / 3) for p in roof], M["snow"])
    low = [(p[0], p[1], p[2] - 0.2) for p in roof]
    b.poly(list(reversed(low)), [(p[0] / 3, p[1] / 3) for p in reversed(low)], M["roof"])
    for i in range(4):
        p, q = roof[i], roof[(i + 1) % 4]
        opoly(b, [low[i], low[(i + 1) % 4], q, p], [(0, 0), (1, 0), (1, 0.1), (0, 0.1)], M["snow"], (0, 0, 0))


def cabin(b, sx, sy, sz, r, v):
    """Строительная бытовка из профнастила: дверь, окошко, полозья, снег на крыше."""
    hx, hy = sx / 2, sz / 2
    k = v % 2
    b.box((-hx, -hy, 0.25), (hx, hy, sy - 0.12), {f: gd(k) for f in SIDES})
    for y in (-hy + 0.3, hy - 0.5):
        bx(b, -hx - 0.2, y, 0, hx + 0.2, y + 0.2, 0.25, M["metal"], faces=ALL, scale=(1, 1))
    b.box((hx - 1.5, -hy - 0.03, 0.3), (hx - 0.6, -hy, 2.2), {'-Y': gd(3)})
    b.box((-hx + 0.8, -hy - 0.03, 1.2), (-hx + 2.0, -hy, 2.0), {'-Y': (M["veh"], AR(0, 1, 3))})
    bx(b, -hx - 0.08, -hy - 0.08, sy - 0.12, hx + 0.08, hy + 0.08, sy, M["snow"], faces=ALL, scale=(3, 3))


def guardhouse(b, sx, sy, sz, r, v):
    hx, hy = sx / 2, sz / 2
    bx(b, -hx, -hy, 0, hx, hy, sy - 0.25, M["brick"], faces=SIDES, scale=(2.5, 2.5))
    b.box((-0.4, -hy - 0.03, 0), (0.5, -hy, 2.0), {'-Y': (M["door"], (0, 0, 1, 1))})
    b.box((-hx - 0.03, -0.6, 1.0), (-hx, 0.6, 1.9), {'-X': (M["balcony"], (0.52, 0.5, 0.98, 0.95))})
    bx(b, -hx - 0.3, -hy - 0.5, sy - 0.25, hx + 0.3, hy + 0.2, sy - 0.12, M["roof"], faces=SIDES + ('-Z',), scale=(3, 3))
    bx(b, -hx - 0.3, -hy - 0.5, sy - 0.12, hx + 0.3, hy + 0.2, sy, M["snow"], scale=(3, 3))


def transformer(b, sx, sy, sz, r, v):
    hx, hy = sx / 2, sz / 2
    bx(b, -hx, -hy, 0, hx, hy, sy - 0.3, M["brick"], faces=SIDES, scale=(2.5, 2.5))
    for x in (-hx + 0.9, 0.3):
        b.box((x, -hy - 0.04, 0.1), (x + 1.3, -hy, 2.2), {'-Y': gd(3)})
    for x in (-hx + 0.6, hx - 1.4):
        b.box((x, hy, 2.0), (x + 0.8, hy + 0.04, 2.5), {'+Y': gd(3)})
    bx(b, -hx - 0.25, -hy - 0.25, sy - 0.3, hx + 0.25, hy + 0.25, sy - 0.14, M["plinth"], faces=SIDES + ('-Z',), scale=(3.6, 0.9))
    bx(b, -hx - 0.25, -hy - 0.25, sy - 0.14, hx + 0.25, hy + 0.25, sy, M["snow"], scale=(3, 3))


def dovecote(b, sx, sy, sz, r, v):
    """Голубятня на четырёх ногах: зелёная будка, вольер, двускатная крыша, лесенка."""
    hx, hy = sx / 2 - 0.3, sz / 2 - 0.3
    for x in (-hx, hx):
        for y in (-hy, hy):
            b.cyl((x, y, 0), (x, y, 2.2), 0.07, 0.07, M["metal"], segs=5, su=2)
    bx(b, -hx, -hy, 2.0, hx, hy, 2.15, M["wood"], faces=ALL, scale=(2, 1))
    b.box((-hx, -hy, 2.15), (hx, hy, 3.9), {k: M["green"] for k in SIDES}, scale=(1.3, 1.0))
    b.box((-hx - 0.02, -hy * 0.6, 2.6), (-hx, hy * 0.6, 3.5), {'-X': (M["balcony"], (0.52, 0.5, 0.98, 0.95))})
    prof = [(-hy - 0.3, 3.9), (hy + 0.3, 3.9), (0, sy)]
    extrude(b, prof, -hx - 0.3, hx + 0.3, 'x', [M["roof"], M["snow"], M["snow"]], (M["green"], (0, 0, 1, 1)), (0, 0, 4.2))
    b.cyl((hx * 0.5, -hy - 0.9, 0), (hx * 0.5, -hy, 2.1), 0.03, 0.03, M["metal"], segs=4)
    b.cyl((hx * 0.5 + 0.5, -hy - 0.9, 0), (hx * 0.5 + 0.5, -hy, 2.1), 0.03, 0.03, M["metal"], segs=4)


def kiosk(b, sx, sy, sz, r, v):
    hx, hy = sx / 2, sz / 2
    b.box((-hx, -hy, 0), (hx, hy, sy - 0.3), {'-Y': (M["kiosk"], (0, 0, 1, 1))})
    side = (M["kiosk"], (0, 0.02, 1, 0.3))
    b.box((-hx, -hy, 0), (hx, hy, sy - 0.3), {'+X': side, '-X': side, '+Y': side})
    bx(b, -hx - 0.25, -hy - 0.6, sy - 0.3, hx + 0.25, hy + 0.1, sy - 0.16, M["metal"], faces=SIDES + ('-Z',), scale=(1, 1))
    bx(b, -hx - 0.25, -hy - 0.6, sy - 0.16, hx + 0.25, hy + 0.1, sy, M["snow"], scale=(3, 3))
    bx(b, -hx + 0.3, -hy - 0.25, 0.95, hx - 0.3, -hy, 1.0, M["metal"], faces=ALL, scale=(1, 1))      # прилавок


def stop_wall(b, sx, sy, sz, r, v):
    """Задняя стенка остановки с лавкой."""
    hx = sx / 2
    n = max(1, round(sx / 2.7))
    for i in range(n + 1):
        x = -hx + sx * i / n
        bx(b, x - 0.05, -0.05, 0, x + 0.05, 0.05, sy, M["green"], scale=(0.5, 1))
    b.box((-hx, -0.02, 0.4), (hx, 0.02, sy - 0.1), {'-Y': gd(1), '+Y': gd(1)})
    bx(b, -hx + 0.5, -0.5, 0.42, hx - 0.5, -0.1, 0.48, M["wood"], faces=ALL, scale=(2, 0.5))
    for i in range(n):
        x = -hx + sx * (i + 0.5) / n
        bx(b, x - 0.04, -0.45, 0, x + 0.04, -0.15, 0.42, M["metal"], scale=(0.5, 0.5))


def stop_roof(b, sx, sy, sz, r, v):
    """Навес остановки: плита под снегом на стойках (стойки уходят вниз на 2,6 м)."""
    hx, hy = sx / 2, sz / 2
    bx(b, -hx, -hy, 0, hx, hy, 0.1, M["green"], faces=ALL, scale=(1.3, 1))
    bx(b, -hx, -hy, 0.1, hx, hy, sy + 0.12, M["snow"], scale=(3, 3))
    n = max(1, round(sx / 4))
    for i in range(n + 1):
        x = -hx + 0.1 + (sx - 0.2) * i / n
        b.cyl((x, hy - 0.15, -2.6), (x, hy - 0.15, 0), 0.05, 0.05, M["green"], segs=5, su=2)   # +Y Blender = −Z Godot: край у дороги


# ======================================================================================================
# ТРАНСПОРТ
# ======================================================================================================
def wheels(b, hx, ys, rr=0.32, w=0.22):
    for y in ys:
        for x in (-hx, hx - w):
            b.box((x, y - rr, 0), (x + w, y + rr, 2 * rr), {k: (M["veh"], AR(1, 2, 3)) for k in ALL})


def car(b, sx, sy, sz, r, v):
    """Легковушка под снегом: длина вдоль Y, цвет — один из четырёх."""
    hx = sx / 2 - 0.03
    hl = sz / 2
    paint = (M["veh"], AR(v % 4, v % 4 + 1, 0))
    glass = (M["veh"], AR(0, 1, 3))
    prof = [(-hl + 0.05, 0.28), (hl - 0.05, 0.28), (hl, 0.68), (hl * 0.55, 0.80), (hl * 0.26, 1.26),
            (-hl * 0.36, 1.26), (-hl * 0.64, 0.84), (-hl, 0.80)]
    mats = [M["roof"], paint, M["snow"], glass, M["snow"], glass, M["snow"], paint]
    extrude(b, prof, -hx, hx, 'x', mats, paint, (0, 0, 0.7))
    for x in (-hx - 0.012, hx + 0.002):
        b.box((x, -hl * 0.57, 0.88), (x + 0.01, hl * 0.22, 1.2), {'+X': glass, '-X': glass})
    wheels(b, hx + 0.02, (-hl * 0.62, hl * 0.62))
    bx(b, -hx * 0.85, -hl * 0.33, 1.26, hx * 0.85, hl * 0.22, sy, M["snow"], scale=(3, 3))


def tram(b, sx, sy, sz, r, v):
    """Трамвайный вагон: красный низ, кремовый верх с окнами, токоприёмник, снег на крыше."""
    hx, hl = sx / 2, sz / 2
    z0, z1 = 0.55, sy - 0.75
    n = round(sz / 1.9)
    for x, s in ((-hx, -1), (hx, 1)):
        pts = [(x, -hl, z0), (x, hl, z0), (x, hl, z1), (x, -hl, z1)]
        opoly(b, pts, [(0, 0.5 + 0.004), (n / 4, 0.5 + 0.004), (n / 4, 0.75 - 0.004), (0, 0.75 - 0.004)], M["veh"], (0, 0, 1.5))
    for y in (-hl, hl):
        opoly(b, [(-hx, y, z0), (hx, y, z0), (hx, y, z1), (-hx, y, z1)],
              [(0.02, 0.5 + 0.004), (0.23, 0.5 + 0.004), (0.23, 0.75 - 0.004), (0.02, 0.75 - 0.004)], M["veh"], (0, 0, 1.5))
    bx(b, -hx, -hl, z0 - 0.02, hx, hl, z0, M["roof"], faces=('-Z',), scale=(3, 3))
    prof = [(-hx, z1), (hx, z1), (hx * 0.75, z1 + 0.3), (-hx * 0.75, z1 + 0.3)]
    extrude(b, prof, -hl, hl, 'y', [None, M["snow"], M["snow"], M["snow"]], (M["veh"], AR(0, 1, 0)), (0, 0, 1.5))
    for y in (-hl * 0.6, hl * 0.6):                                           # тележки
        bx(b, -hx + 0.25, y - 1.1, 0, hx - 0.25, y + 1.1, z0, M["roof"], faces=SIDES, scale=(3, 3))
    for y in (-0.7, 0.7):                                                     # токоприёмник
        b.cyl((0, y, z1 + 0.3), (0, 0, sy), 0.03, 0.03, M["metal"], segs=4)
    b.cyl((-0.6, 0, sy), (0.6, 0, sy), 0.03, 0.03, M["metal"], segs=4)


def minibus(b, sx, sy, sz, r, v):
    hx, hl = sx / 2, sz / 2
    z0, z1 = 0.45, sy - 0.14
    for x in (-hx, hx):
        opoly(b, [(x, -hl, z0), (x, hl, z0), (x, hl, z1), (x, -hl, z1)],
              [(0, 0.25 + 0.004), (0.75, 0.25 + 0.004), (0.75, 0.5 - 0.004), (0, 0.5 - 0.004)], M["veh"], (0, 0, 1.3))
    yel = (M["veh"], (0.02, 0.27, 0.06, 0.33))
    glass = (M["veh"], AR(0, 1, 3))
    b.box((-hx, -hl, z0), (hx, hl, z1), {'+Y': yel, '-Y': yel})
    b.box((-hx + 0.12, -hl - 0.02, 1.25), (hx - 0.12, -hl, z1 - 0.15), {'-Y': glass})
    b.box((-hx + 0.12, hl, 1.35), (hx - 0.12, hl + 0.02, z1 - 0.2), {'+Y': glass})
    bx(b, -hx, -hl, z0 - 0.02, hx, hl, z0, M["roof"], faces=('-Z',), scale=(3, 3))
    bx(b, -hx, -hl, z1, hx, hl, sy, M["snow"], scale=(3, 3))
    wheels(b, hx + 0.02, (-hl * 0.62, hl * 0.62), rr=0.38)


def truck(b, sx, sy, sz, r, v):
    """Фура: кабина и тентованный полуприцеп."""
    hx, hl = sx / 2, sz / 2
    cab = (M["veh"], AR(2, 3, 0))
    glass = (M["veh"], AR(0, 1, 3))
    tarp = (M["veh"], AR(2, 3, 3))
    yc = -hl + 2.3
    b.box((-hx, -hl, 0.6), (hx, yc, 2.9), {k: cab for k in SIDES + TOP})
    b.box((-hx + 0.15, -hl - 0.02, 1.7), (hx - 0.15, -hl, 2.7), {'-Y': glass})
    for x in (-hx - 0.02, hx):
        b.box((x, -hl + 0.3, 1.7), (x + 0.02, yc - 0.5, 2.6), {'+X': glass, '-X': glass})
    bx(b, -hx, -hl, 2.9, hx, yc, 3.05, M["snow"], scale=(3, 3))
    bx(b, -hx + 0.1, yc, 0.9, hx - 0.1, hl, 1.15, M["roof"], faces=ALL, scale=(3, 3))
    b.box((-hx, yc + 0.4, 1.15), (hx, hl, sy - 0.14), {k: tarp for k in SIDES})
    bx(b, -hx, yc + 0.4, sy - 0.14, hx, hl, sy, M["snow"], scale=(3, 3))
    wheels(b, hx + 0.02, (-hl + 1.1, yc + 1.2, hl - 2.6, hl - 1.3), rr=0.45, w=0.3)


# ======================================================================================================
# СНЕГ, СТОЛБЫ
# ======================================================================================================
def mound(b, sx, sy, sz, r, m, n=6, power=0.4):
    def hz(i, j):
        u = i / n * 2 - 1; w = j / n * 2 - 1
        d = max(0.0, 1 - max(abs(u), abs(w)) ** 3)
        return sy * d ** power * (0.8 + 0.2 * r.random()) if 0 < i < n and 0 < j < n else 0.0
    H = [[hz(i, j) for j in range(n + 1)] for i in range(n + 1)]
    for i in range(n):
        for j in range(n):
            pts, uvs = [], []
            for (a, c) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                x = (a / n - 0.5) * sx; y = (c / n - 0.5) * sz
                pts.append((x, y, H[a][c])); uvs.append((x / 3, y / 3))
            b.poly(pts, uvs, m)


def drift(b, sx, sy, sz, r, v):
    mound(b, sx, sy, sz, r, M["snow"])


def coal(b, sx, sy, sz, r, v):
    mound(b, sx, sy, sz, r, M["roof"], power=0.8)
    mound(b, sx * 0.5, sy * 0.25, sz * 0.5, r, M["snow"], n=4)


def lamp_pole(b, sx, sy, sz, r, v):
    b.cyl((0, 0, 0), (0, 0, sy - 0.5), 0.11, 0.07, M["metal"], segs=6, su=2)
    b.cyl((0, 0, sy - 0.55), (0, -0.4, sy - 0.1), 0.05, 0.045, M["metal"], segs=5)
    b.cyl((0, -0.4, sy - 0.1), (0, -1.3, sy), 0.045, 0.04, M["metal"], segs=5)
    bx(b, -0.18, -1.95, sy - 0.12, 0.18, -1.25, sy + 0.08, M["metal"], scale=(0.5, 0.5))
    b.box((-0.14, -1.9, sy - 0.15), (0.14, -1.32, sy - 0.12), {'-Z': (M["glass"], (0, 0, 1, 1))})
    snow(b, -0.18, -1.95, 0.18, -1.25, sy + 0.08, 0.07)


def tram_pole(b, sx, sy, sz, r, v):
    """Опора контактной сети: столб и две консоли над путями."""
    b.cyl((0, 0, 0), (0, 0, sy), 0.16, 0.1, M["metal"], segs=6, su=2)
    for s in (-1, 1):
        b.cyl((0, 0, sy - 0.6), (0, s * 2.3, sy - 0.9), 0.04, 0.04, M["metal"], segs=4)
        b.cyl((0, 0, sy - 0.1), (0, s * 2.3, sy - 0.9), 0.02, 0.02, M["metal"], segs=3)
        b.cyl((0, s * 1.2, sy - 0.75), (0, s * 1.2, sy - 1.0), 0.05, 0.05, M["plinth"], segs=5)


def flood_pole(b, sx, sy, sz, r, v):
    b.cyl((0, 0, 0), (0, 0, sy), 0.2, 0.12, M["metal"], segs=6, su=2)
    bx(b, -1.2, -0.1, sy - 0.2, 1.2, 0.1, sy - 0.1, M["metal"], faces=ALL, scale=(1, 1))
    for x in (-0.9, 0, 0.9):
        bx(b, x - 0.3, -0.35, sy - 0.1, x + 0.3, 0.05, sy + 0.4, M["metal"], scale=(0.5, 0.5))
        b.box((x - 0.25, -0.37, sy - 0.05), (x + 0.25, -0.35, sy + 0.35), {'-Y': (M["glass"], (0, 0, 1, 1))})


# ======================================================================================================
# ЗАБОРЫ, ПЕРИЛА
# ======================================================================================================
def _axis(sx, sz):
    """Длинная сторона блока: (L, вдоль X?, перевод (t, o) → (x, y))."""
    if sx >= sz:
        return sx, (lambda t, o=0.0: (t, o))
    return sz, (lambda t, o=0.0: (o, t))


def fence_metal(b, sx, sy, sz, r, v):
    """Школьный забор: стойки, две перекладины, частые прутья."""
    L, P = _axis(sx, sz)
    n = max(1, round(L / 3.0))
    for i in range(n + 1):
        x, y = P(-L / 2 + L * i / n)
        bx(b, x - 0.05, y - 0.05, 0, x + 0.05, y + 0.05, sy, M["green"], scale=(0.5, 1))
    for z in (0.25, sy - 0.25):
        b.cyl(P(-L / 2) + (z,), P(L / 2) + (z,), 0.03, 0.03, M["green"], segs=4)
    t = -L / 2 + 0.3
    while t < L / 2:
        b.cyl(P(t) + (0.25,), P(t) + (sy - 0.05,), 0.014, 0.014, M["green"], segs=3)
        t += 0.3


def fence_panel(b, sx, sy, sz, r, v, m=None, cap=True, pw=2.5):
    """Глухой забор из плит (бетонная «ёлочка» / доски): плиты между столбами, снег поверху."""
    m = m or M["cfence"]
    L, P = _axis(sx, sz)
    th = 0.07
    n = max(1, round(L / pw))
    lo = max(0.0, sy - 2.6)                                                    # всё, что ниже плит, — подпорная стена
    for i in range(n):
        t0, t1 = -L / 2 + L * i / n, -L / 2 + L * (i + 1) / n
        (xa, ya), (xb, yb) = P(t0, -th), P(t1, th)
        rect = (m, (0, 0, 1, 1))
        faces = {'+X': rect, '-X': rect} if sx < sz else {'+Y': rect, '-Y': rect}
        b.box((min(xa, xb), min(ya, yb), lo), (max(xa, xb), max(ya, yb), sy), faces)
        x, y = P(t0)
        bx(b, x - 0.12, y - 0.12, 0, x + 0.12, y + 0.12, sy + 0.05, M["wall"], scale=(5.4, 5.6))
    x, y = P(L / 2)
    bx(b, x - 0.12, y - 0.12, 0, x + 0.12, y + 0.12, sy + 0.05, M["wall"], scale=(5.4, 5.6))
    (xa, ya), (xb, yb) = P(-L / 2, -0.3), P(L / 2, 0.3)
    if lo > 0:
        bx(b, xa, ya, 0, xb, yb, lo, M["wall"], faces=SIDES + TOP, scale=(5.4, 5.6))
    if cap:
        (xa, ya), (xb, yb) = P(-L / 2, -th - 0.03), P(L / 2, th + 0.03)
        bx(b, xa, ya, sy, xb, yb, sy + 0.1, M["snow"], scale=(3, 3))


def fence_wood(b, sx, sy, sz, r, v):
    fence_panel(b, sx, sy, sz, r, v, m=M["wood"], pw=2.0)


def railing(b, sx, sy, sz, r, v):
    L, P = _axis(sx, sz)
    rail_line(b, P(-L / 2) + (0,), P(L / 2) + (0,), h=sy)


# ======================================================================================================
# ТЕПЛОТРАССА
# ======================================================================================================
def pipe_run(b, sx, sy, sz, r, v, supports=True):
    """Две трубы в обмотке на бетонных опорах; сверху плоская снежная шапка — по ней можно идти."""
    L, P = _axis(sx, sz)
    rr = 0.3
    zc = sy - rr - 0.06
    for o in (-0.36, 0.36):
        b.cyl(P(-L / 2, o) + (zc,), P(L / 2, o) + (zc,), rr, rr, M["pipe"], segs=8, su=3)
    (xa, ya), (xb, yb) = P(-L / 2, -0.62), P(L / 2, 0.62)
    bx(b, xa, ya, zc + rr * 0.55, xb, yb, sy, M["snow"], scale=(3, 3))
    if supports and zc - rr > 0.15:
        n = max(1, round(L / 6.0))
        for i in range(n + 1):
            (xa, ya), (xb, yb) = P(-L / 2 + 0.3 + (L - 0.6) * i / n - 0.2, -0.6), P(-L / 2 + 0.3 + (L - 0.6) * i / n + 0.2, 0.6)
            bx(b, xa, ya, 0, xb, yb, zc - rr * 0.6, M["wall"], scale=(5.4, 5.6))


def arch_top(b, sx, sy, sz, r, v):
    pipe_run(b, sx, sy, sz, r, v, supports=False)


def pipe_block(b, sx, sy, sz, r, v):
    """Узел: трубы уходят в землю / поворот вверх, задвижка."""
    for o in (-0.36, 0.36):
        b.cyl((0, o, 0), (0, o, sy - 0.2), 0.32, 0.32, M["pipe"], segs=8, su=3)
    bx(b, -sx / 2, -sz / 2, 0, sx / 2, sz / 2, 0.5, M["wall"], scale=(5.4, 5.6))
    bx(b, -0.5, -0.9, sy - 0.2, 0.5, 0.9, sy, M["snow"], scale=(3, 3))
    b.cyl((0.35, 0, sy * 0.5), (0.7, 0, sy * 0.5), 0.2, 0.2, M["metal"], segs=8, caps=True)


def pipe_post(b, sx, sy, sz, r, v):
    bx(b, -sx / 2, -sz / 2, 0, sx / 2, sz / 2, sy, M["wall"], scale=(5.4, 5.6))
    bx(b, -0.8, -0.15, sy - 0.2, 0.8, 0.15, sy, M["wall"], scale=(5.4, 5.6))


def arch_post(b, sx, sy, sz, r, v):
    for o in (-0.36, 0.36):
        b.cyl((0, o, 0), (0, o, sy), 0.3, 0.3, M["pipe"], segs=8, su=3)


def stairs_metal(b, sx, sy, sz, r, v):
    """Сварная лесенка через трубы: косоуры, ступени-решётки, перила (коллизию даёт невидимый пандус блока)."""
    hx = sx / 2
    lo, hi = (0, -sz / 2, 0), (0, sz / 2, sy)
    for x in (-hx + 0.04, hx - 0.04):
        b.cyl((x, lo[1], 0.05), (x, hi[1], sy), 0.05, 0.05, M["metal"], segs=4)
        rail_line(b, (x, lo[1], 0), (x, hi[1], sy), h=0.95, step=1.4)
    n = max(2, round(sy / 0.2))
    for i in range(n):
        y = -sz / 2 + sz * (i + 0.5) / n
        z = sy * (i + 1) / n
        bx(b, -hx + 0.06, y - 0.14, z - 0.03, hx - 0.06, y + 0.14, z, M["metal"], faces=ALL, scale=(0.5, 0.5))


def pipe_bridge(b, sx, sy, sz, r, v):
    hx, hy = sx / 2, sz / 2
    bx(b, -hx, -hy, 0, hx, hy, sy, M["metal"], faces=ALL, scale=(0.5, 0.5))
    for x in (-hx + 0.04, hx - 0.04):
        rail_line(b, (x, -hy, sy), (x, hy, sy), h=0.95, step=0.9)


# ======================================================================================================
# ЛЕСТНИЦЫ (видимые ступени; коллизия — пандус серого блока)
# ======================================================================================================
def stairs_concrete(b, sx, sy, sz, r, v, snowy=True, rails=True):
    hx = sx / 2
    n = max(2, round(sy / 0.17))
    d = sz / n
    for i in range(n):
        y0 = -sz / 2 + i * d
        z = sy * (i + 1) / n
        b.box((-hx, y0, 0), (hx, y0 + d, z), {'-Y': M["plinth"], '+X': M["wall"], '-X': M["wall"]}, scale=(3.6, 0.9))
        b.box((-hx, y0, 0), (hx, y0 + d, z), {'+Z': M["snow"] if snowy else M["wall"]}, scale=(3, 3))
    if rails:
        xs = [-hx + 0.08, hx - 0.08] + ([0.0] if sx >= 8 else [])
        for x in xs:
            rail_line(b, (x, -sz / 2 + d * 0.5, sy / n), (x, sz / 2 - d * 0.5, sy), h=0.95, step=1.6)


def flight(b, sx, sy, sz, r, v):
    stairs_concrete(b, sx, sy, sz, r, v, snowy=False, rails=False)


def tribune(b, sx, sy, sz, r, v):
    """Трибуна стадиона: бетонные ярусы с дощатыми лавками под снегом."""
    hx = sx / 2
    n = 5
    d = sz / n
    for i in range(n):
        y0 = -sz / 2 + i * d
        z = sy * (i + 1) / n
        b.box((-hx, y0, 0), (hx, y0 + d, z), {'-Y': M["wall"], '+X': M["wall"], '-X': M["wall"], '+Z': M["wall"]}, scale=(5.4, 5.6))
        bx(b, -hx + 0.3, y0 + 0.35, z, hx - 0.3, y0 + 0.75, z + 0.12, M["wood"], scale=(2, 0.5))
        bx(b, -hx + 0.3, y0 + 0.35, z + 0.12, hx - 0.3, y0 + 0.75, z + 0.2, M["snow"], scale=(3, 3))
    b.box((-hx, sz / 2 - 0.05, 0), (hx, sz / 2, sy), {'+Y': M["wall"]}, scale=(5.4, 5.6))
    rail_line(b, (-hx, sz / 2 - 0.1, sy), (hx, sz / 2 - 0.1, sy), h=1.0, step=2.5)


# ======================================================================================================
# СТРОЙКА
# ======================================================================================================
def slab(b, sx, sy, sz, r, v):
    bx(b, -sx / 2, -sz / 2, 0, sx / 2, sz / 2, sy, M["wall"], faces=ALL, scale=(5.4, 5.6))


def column(b, sx, sy, sz, r, v):
    bx(b, -sx / 2, -sz / 2, 0, sx / 2, sz / 2, sy, M["wall"], faces=SIDES, scale=(5.4, 5.6))
    for dx in (-0.1, 0.1):                                                    # арматура торчит сверху
        b.cyl((dx, 0, sy), (dx * 1.5, 0.05, sy + 0.7), 0.012, 0.012, M["metal"], segs=3)


def slab_stack(b, sx, sy, sz, r, v):
    n = max(1, int(sy / 0.3))
    t = sy / n
    for i in range(n):
        o = r.uniform(-0.1, 0.1)
        bx(b, -sx / 2 + o, -sz / 2, i * t + 0.06, sx / 2 + o, sz / 2, (i + 1) * t, M["wall"], faces=ALL, scale=(5.4, 5.6))
        for x in (-sx / 4, sx / 4):
            bx(b, x - 0.06, -sz / 2, i * t, x + 0.06, sz / 2, i * t + 0.06, M["wood"], faces=SIDES, scale=(2, 0.5))
    snow(b, -sx / 2, -sz / 2, sx / 2, sz / 2, sy - 0.02, 0.12)


def truss(b, p0, p1, w, m, step=2.5):
    """Решётчатая ферма квадратного сечения w от p0 до p1: 4 пояса и раскосы."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    u = ax.cross(Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))).normalized()
    wv = ax.cross(u)
    cs = [(u * sx_ + wv * sy_) * (w / 2) for sx_, sy_ in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for c in cs:
        b.cyl(p0 + c, p1 + c, 0.06, 0.06, m, segs=4, su=1)
    L = (p1 - p0).length
    n = max(1, round(L / step))
    for i in range(n):
        a, c = p0 + ax * (L * i / n), p0 + ax * (L * (i + 1) / n)
        for k in range(4):
            b.cyl(a + cs[k], c + cs[(k + 1) % 4], 0.03, 0.03, m, segs=3)


def crane_tower(b, sx, sy, sz, r, v):
    truss(b, (0, 0, 0), (0, 0, sy), min(sx, sz) - 0.2, M["yellow"])
    bx(b, -sx / 2 - 0.6, -sz / 2 - 0.6, 0, sx / 2 + 0.6, sz / 2 + 0.6, 0.5, M["wall"], scale=(5.4, 5.6))
    snow(b, -sx / 2 - 0.6, -sz / 2 - 0.6, sx / 2 + 0.6, sz / 2 + 0.6, 0.5)


def crane_jib(b, sx, sy, sz, r, v):
    L, P = _axis(sx, sz)
    truss(b, P(-L / 2) + (sy / 2,), P(L / 2) + (sy / 2,), min(sy, 1.0) - 0.1, M["yellow"], step=3.0)
    x, y = P(L * 0.3)
    b.cyl((x, y, sy / 2), (x, y, -9.0), 0.02, 0.02, M["metal"], segs=3)        # трос с крюком
    bx(b, x - 0.25, y - 0.25, -9.6, x + 0.25, y + 0.25, -9.0, M["yellow"], faces=ALL, scale=(1, 1))


def crane_cab(b, sx, sy, sz, r, v):
    bx(b, -sx / 2, -sz / 2, 0, sx / 2, sz / 2, 0.25, M["yellow"], faces=ALL, scale=(1, 1))
    bx(b, 0.3, -1.0, 0.25, 1.9, 1.0, sy, M["yellow"], scale=(1, 1))
    b.box((1.9, -0.8, 0.9), (1.92, 0.8, sy - 0.2), {'+X': (M["veh"], AR(0, 1, 3))})
    bx(b, -sx / 2 + 0.2, -0.8, 0.25, -0.4, 0.8, 1.3, M["wall"], scale=(5.4, 5.6))            # противовес
    snow(b, 0.3, -1.0, 1.9, 1.0, sy)


# ======================================================================================================
# ДВОР
# ======================================================================================================
def slide(b, sx, sy, sz, r, v):
    hx = sx / 2 - 0.2
    for x in (-hx, hx):
        b.cyl((x, sz / 2 - 0.3, 0), (x, sz / 2 - 0.3, sy), 0.04, 0.04, M["green"], segs=4)
        b.cyl((x, sz / 2 - 1.0, 0), (x, sz / 2 - 0.3, sy - 0.5), 0.04, 0.04, M["green"], segs=4)
        b.cyl((x, sz / 2 - 0.4, sy - 0.5), (x, -sz / 2, 0.15), 0.035, 0.035, M["green"], segs=4)
    chute = [(-hx, sz / 2 - 0.4, sy - 0.55), (hx, sz / 2 - 0.4, sy - 0.55), (hx, -sz / 2, 0.1), (-hx, -sz / 2, 0.1)]
    b.poly(chute, [(0, 0), (1, 0), (1, 2), (0, 2)], M["metal"])
    b.poly(list(reversed(chute)), [(0, 2), (1, 2), (1, 0), (0, 0)], M["metal"])


def swing(b, sx, sy, sz, r, v):
    hx = sx / 2 - 0.1
    for x in (-hx, hx):
        for s in (-1, 1):
            b.cyl((x, s * sz / 2, 0), (x, 0, sy), 0.04, 0.04, M["green"], segs=4)
    b.cyl((-hx, 0, sy), (hx, 0, sy), 0.04, 0.04, M["green"], segs=4)
    for x in (-hx * 0.45, hx * 0.45):
        for dx in (-0.2, 0.2):
            b.cyl((x + dx, 0, sy), (x + dx, 0, 0.5), 0.012, 0.012, M["metal"], segs=3)
        bx(b, x - 0.25, -0.1, 0.46, x + 0.25, 0.1, 0.5, M["wood"], faces=ALL, scale=(2, 0.5))
        snow(b, x - 0.25, -0.1, x + 0.25, 0.1, 0.5, 0.06)


def carousel(b, sx, sy, sz, r, v):
    rr = min(sx, sz) / 2
    b.cyl((0, 0, 0), (0, 0, sy - 0.1), 0.08, 0.08, M["metal"], segs=6)
    b.cyl((0, 0, 0.3), (0, 0, 0.36), rr, rr, M["green"], segs=10, caps=True)
    b.cyl((0, 0, 0.36), (0, 0, 0.44), rr * 0.98, rr * 0.98, M["snow"], segs=10, caps=True)
    for i in range(4):
        a = math.pi / 2 * i
        b.cyl((0, 0, sy - 0.15), (math.cos(a) * rr * 0.9, math.sin(a) * rr * 0.9, sy - 0.15), 0.02, 0.02, M["metal"], segs=3)
        b.cyl((math.cos(a) * rr * 0.9, math.sin(a) * rr * 0.9, 0.36), (math.cos(a) * rr * 0.9, math.sin(a) * rr * 0.9, sy - 0.15), 0.02, 0.02, M["metal"], segs=3)


def sandbox(b, sx, sy, sz, r, v):
    hx, hy = sx / 2, sz / 2
    for (x0, y0, x1, y1) in ((-hx, -hy, hx, -hy + 0.12), (-hx, hy - 0.12, hx, hy), (-hx, -hy, -hx + 0.12, hy), (hx - 0.12, -hy, hx, hy)):
        bx(b, x0, y0, 0, x1, y1, sy, M["wood"], scale=(2, 0.5))
    bx(b, -hx + 0.12, -hy + 0.12, 0, hx - 0.12, hy - 0.12, sy * 0.8, M["snow"], faces=TOP, scale=(3, 3))


def dryer(b, sx, sy, sz, r, v):
    hx = sx / 2
    for x in (-hx, hx):
        b.cyl((x, 0, 0), (x, 0, sy), 0.04, 0.04, M["green"], segs=4)
        b.cyl((x, -0.6, sy), (x, 0.6, sy), 0.03, 0.03, M["green"], segs=4)
    for y in (-0.5, 0, 0.5):
        b.cyl((-hx, y, sy), (hx, y, sy - 0.08), 0.006, 0.006, M["metal"], segs=3)


def obstacles(b, sx, sy, sz, r, v):
    """Школьная полоса препятствий: турники разной высоты, брусья, вкопанные покрышки."""
    hx = sx / 2
    x = -hx + 0.5
    for h in (2.3, 1.9, 1.5):
        for dx in (0, 1.8):
            b.cyl((x + dx, 0, 0), (x + dx, 0, h), 0.04, 0.04, M["green"], segs=4)
        b.cyl((x, 0, h - 0.05), (x + 1.8, 0, h - 0.05), 0.02, 0.02, M["metal"], segs=4)
        x += 1.8
    x += 1.5
    for y in (-0.3, 0.3):
        for dx in (0, 2.6):
            b.cyl((x + dx, y, 0), (x + dx, y, 1.3), 0.035, 0.035, M["green"], segs=4)
        b.cyl((x - 0.2, y, 1.3), (x + 2.8, y, 1.3), 0.025, 0.025, M["metal"], segs=4)
    x += 4.5
    while x < hx - 0.6:
        b.cyl((x, 0, 0), (x, 0.01, 0.55), 0.38, 0.38, M["roof"], segs=8)
        x += 1.1


def sign_post(b, sx, sy, sz, r, v):
    b.cyl((0, 0, 0), (0, 0, sy), 0.04, 0.04, M["metal"], segs=5)
    b.box((-0.45, -0.03, sy - 0.75), (0.45, 0.03, sy - 0.05), {'-Y': gd(1), '+Y': gd(1)})


def barrier(b, sx, sy, sz, r, v):
    L, P = _axis(sx, sz)
    b.cyl(P(-L / 2) + (sy / 2,), P(L / 2) + (sy / 2,), 0.05, 0.04, M["yellow"], segs=5, su=1)
    x, y = P(L / 2 + 0.15)
    bx(b, x - 0.15, y - 0.15, -0.9, x + 0.15, y + 0.15, 0.3, M["metal"], scale=(0.5, 0.5))


# base → (функция, вариантов, "nocol" — без собственной коллизии)
BUILDERS = {
    "GarageRow": (garage_row, 1, False), "ShellRow": (shell_row, 1, False), "ShellGarages": (shell_row, 1, False),
    "Sheds": (sheds, 1, False), "Cabin": (cabin, 2, False), "Guardhouse": (guardhouse, 1, False),
    "Transformer": (transformer, 1, False), "Dovecote": (dovecote, 1, False), "Kiosk": (kiosk, 1, False),
    "StopWall": (stop_wall, 1, False), "StopRoof": (stop_roof, 1, True),
    "Car": (car, 4, False), "Tram": (tram, 1, False), "Minibus": (minibus, 1, False), "Truck": (truck, 1, False),
    "Drift": (drift, 1, False), "Coal": (coal, 1, False),
    "LampPole": (lamp_pole, 1, False), "TramPole": (tram_pole, 1, False), "FloodPole": (flood_pole, 1, False),
    "Fence": (fence_metal, 1, False), "BuildFence": (fence_wood, 1, False), "Edge": (fence_panel, 1, False),
    "Parapet": (railing, 1, False), "TunnelRail": (railing, 1, False),
    "Pipe": (pipe_run, 1, False), "PipeBranch": (pipe_run, 1, False), "PipePost": (pipe_post, 1, False),
    "PipeEnd": (pipe_block, 1, False), "PipeJoint": (pipe_block, 1, False), "ArchPost": (arch_post, 1, False),
    "ArchTop": (arch_top, 1, False), "PipeBridge": (pipe_bridge, 1, True),
    "PipeStepN": (stairs_metal, 1, True), "PipeStepS": (stairs_metal, 1, True),
    "StairsProspect": (stairs_concrete, 1, True), "StairsSchool": (stairs_concrete, 1, True),
    "StairsWest": (stairs_concrete, 1, True), "StairsWide": (stairs_concrete, 1, True),
    "StairsGarages": (stairs_concrete, 1, True), "TunnelStairsN": (stairs_concrete, 1, True),
    "Flight": (flight, 1, True), "Tribune": (tribune, 1, True),
    "Slab": (slab, 1, False), "Column": (column, 1, False), "Slabs": (slab_stack, 1, False),
    "CraneTower": (crane_tower, 1, False), "CraneJib": (crane_jib, 1, True), "CraneCab": (crane_cab, 1, True),
    "Slide": (slide, 1, False), "Swing": (swing, 1, False), "Carousel": (carousel, 1, False),
    "Sandbox": (sandbox, 1, False), "Dryer": (dryer, 1, False), "Obstacles": (obstacles, 1, False),
    "TunnelSign": (sign_post, 1, False), "Barrier": (barrier, 1, True),
}
# готовые модели двора — просто подставляются
READY = {"Bench": "res://assets/models/bench.gltf", "Turnik": "res://assets/models/turnik.gltf",
         "Tree": ["res://assets/models/tree_a.gltf", "res://assets/models/tree_b.gltf"]}


def fnum(v):
    return ("%.2f" % v).rstrip("0").rstrip(".").replace(".", "_").replace("-", "m")


def main():
    blocks = json.load(open(os.path.join(ROOT, "tools", "district_blocks.json"), encoding="utf-8"))
    interactive = not bpy.app.background
    if interactive:
        sc = bpy.data.scenes.get("DistrictProps") or bpy.data.scenes.new("DistrictProps")
        if bpy.context.window:
            bpy.context.window.scene = sc
    else:
        sc = bpy.context.scene
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    placed_sc = bpy.data.scenes.get("District") if interactive else None
    if placed_sc:
        old = bpy.data.collections.get("Props")
        if old:
            for ob in list(old.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.collections.remove(old)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    os.makedirs(OUT, exist_ok=True)

    models, manifest, counters = {}, [], {}
    for blk in blocks:
        base = blk["base"]
        if base in READY:
            k = counters.get(base, 0); counters[base] = k + 1
            path = READY[base] if isinstance(READY[base], str) else READY[base][k % len(READY[base])]
            manifest.append({"zone": blk["zone"], "node": blk["node"], "model": path, "yaw": 0, "nocol": False})
            continue
        if base not in BUILDERS:
            continue
        fn, nvar, nocol = BUILDERS[base]
        if base == "Fence" and blk["zone"] == "BoilerHouse":
            fn = fence_panel
        k = counters.get(base, 0); counters[base] = k + 1
        var = k % nvar
        key = "%s_%s_%sx%sx%s%s" % (base.lower(), fn.__name__, fnum(blk["sx"]), fnum(blk["sy"]), fnum(blk["sz"]), ("_v%d" % var) if nvar > 1 else "")
        if base == "Drift":
            key += "_%d" % (k % 3)
        name = key + ("_nocol" if nocol else "")
        if name not in models:
            b = B()
            fn(b, blk["sx"], blk["sy"], blk["sz"], random.Random(zlib.crc32(key.encode())), var)
            models[name] = b.build(name, sc.collection)
        yaw = 0
        if base == "GarageRow" and ((blk["cz"] - 47.0) % 18.0) > 9.0:
            yaw = 180                                                          # второй ряд террасы смотрит воротами на первый
        if base == "Kiosk" and blk["zone"] == "Prospect":
            yaw = 180                                                          # ларьки на проспекте — лицом к дороге
        if base == "Cabin" and blk["cz"] < -8:
            yaw = 180                                                          # два ряда бытовок — дверями друг к другу
        manifest.append({"zone": blk["zone"], "node": blk["node"], "model": "res://assets/models/district/props/%s.gltf" % name,
                         "yaw": yaw, "nocol": nocol, "_ob": name, "_blk": blk})

    for other in bpy.data.scenes:
        for layer in other.view_layers:
            for o in other.objects:
                o.select_set(False, view_layer=layer)
    vl = sc.view_layers[0]
    polys = 0
    for name, ob in models.items():
        polys += len(ob.data.polygons)
        for o in sc.objects:
            o.select_set(False, view_layer=vl)
        ob.select_set(True, view_layer=vl)
        vl.objects.active = ob
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".gltf"), use_selection=True, export_keep_originals=True,
                                  export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    # раскладка уникальных моделей в ряд
    x = 0.0
    for name, ob in sorted(models.items()):
        w = max(ob.dimensions.x, 1.0)
        ob.location = (x + w / 2, 0, 0)
        x += w + 2.0
    # копии на своих местах в сцене District (общие меши, без лишних данных)
    if placed_sc:
        coll = bpy.data.collections.new("Props")
        placed_sc.collection.children.link(coll)
        for m in manifest:
            if "_ob" not in m:
                continue
            blk = m["_blk"]
            ob = bpy.data.objects.new(blk["zone"] + "_" + blk["node"], models[m["_ob"]].data)
            ob.location = (blk["cx"], -blk["cz"], blk["y"])
            ob.rotation_euler = (0, 0, math.radians(blk["yaw"] + m["yaw"]))
            coll.objects.link(ob)
    out = [{k: v for k, v in m.items() if not k.startswith("_")} for m in manifest]
    open(os.path.join(ROOT, "tools", "district_props.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=0) + "\n")
    if interactive and bpy.data.filepath:
        bpy.ops.wm.save_mainfile()
        bpy.ops.file.make_paths_relative()      # пути к текстурам — относительные, иначе модель не откроется на другом компьютере
        bpy.ops.wm.save_mainfile()
    return {"unique_models": len(models), "polys_unique": polys, "blocks_replaced": len(manifest), "blocks_total": len(blocks)}


result = main()
print(result)
