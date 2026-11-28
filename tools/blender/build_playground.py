# Детская площадка под окном Юрчика (YUR-49, этап 1) — одна модель на меню и на локацию.
#
# Референсы — вложения YUR-49: фото площадки из окна Юрчика (осень, сверху), план площадки и листы ассетов.
# По фото (зимой всё в снегу после метели):
#   • вдоль проезда — бордюр, полоса тротуара с низкими зелёными дугами, на самом проезде — тумбы из двух покрышек
#     (жёлтая на зелёной) со стойкой;
#   • первый ряд — квадратные клумбы в решётчатых оградках: в одной круглый куст, в трёх — голые деревья;
#   • слева (к парковке) — две зелёные лавки и урна;
#   • в глубине — качели: стенка-скалодром, сиденье на цепях, лесенка; рядом домик-башня (жёлтые доски,
#     красная двускатная крыша, лесенка к дому);
#   • справа — Г-образная лавка и песочница-беседка с плоской оцинкованной крышей (зелёные борта, жёлтые сиденья);
#   • по заднему краю — ряд вкопанных наполовину крашеных покрышек.
#
# Координаты — как в плане двора menu_yard_plan.py (Godot, метры): окно Юрчика в начале, фасад — плоскость x = 0,
# двор — в +x, фасад тянется вдоль z. Меню ставит модель как есть; локация — поворотом под свой дом
# (scenes/yard/playground.tscn, scenes/district/z2_home_yard.tscn).
#
# Запуск в живом Blender через Blender MCP (сначала playground_textures.py, если текстур ещё нет):
#   PG_ROOT = r"<папка проекта>"; exec(open(PG_ROOT + r"\tools\blender\build_playground.py", encoding="utf-8").read())
# Строит всё в своей сцене Playground и пишет assets/models/yard/playground.gltf:
#   Playground                — всё, обо что можно удариться (получает коллизию при импорте, ps2_import.gd);
#   PlaygroundTrees_nocol     — деревья и куст в клумбах (их не достать — вокруг оградки);
#   PlaygroundGround_nocol    — площадка и тротуар (асфальт под утоптанным снегом), бордюры.
import bpy
import math
import os
import random
from mathutils import Vector

ROOT = globals().get("PG_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
OUT_DIR = os.path.join(ROOT, "assets", "models", "yard")
OUT = os.path.join(OUT_DIR, "playground.gltf")
SCENE = "Playground"

# материалы, построитель, деревья — из кадра меню (тот же двор), без сборки самого кадра
MY = {"MENU_ROOT": ROOT, "MENU_NO_MAIN": True, "__name__": "menu_yard_lib"}
exec(compile(open(os.path.join(HERE, "build_menu_yard.py"), encoding="utf-8").read(), "build_menu_yard.py", "exec"), MY)
B, M, P, PL, tree3d, mat = MY["B"], MY["M"], MY["P"], MY["PL"], MY["tree3d"], MY["mat"]

# ------------------------------------------------------------------ план площадки
PAD = PL["PLAYGROUND"]                     # (x0, x1, z0, z1) — асфальт площадки вместе с тротуаром
WALK_X1 = 12.0                             # тротуар вдоль проезда: x 10.4 … 12.0
PLANTER = 2.6                              # клумба 2.6 × 2.6
PLANTERS = PL["PLANTERS"]                  # (x, z, "tree" | "bush") — общие с картой земли меню
BENCHES = [(13.6, -9.35, 90.0), (17.6, -9.35, 90.0)]       # (x, z, поворот): лицом во двор площадки
BIN = (15.6, -9.55)
SWING = (20.0, -5.6, 0.0)                  # стенка, качели и лесенка вдоль z
TOWER = (20.1, -2.2, 0.0)                  # домик-башня, лесенкой к дому
L_BENCH = (21.0, 1.2)                      # угол Г-образной лавки
SANDBOX = (22.0, 6.4)                      # песочница-беседка
TIRE_ROW = (24.55, -3.5, 12.5, 0.72)       # x, z от, z до, шаг
ARCHES = [-7.5, -4.0, 6.5, 9.5]            # дуги на тротуаре (x = 11.9)
BOLLARDS = [(9.6, -0.6), (8.7, 5.2)]       # тумбы из покрышек на проезде

# цвета краски (умножают светлую текстуру)
YELLOW = (0.88, 0.68, 0.18)
RED = (0.78, 0.26, 0.24)
GREEN = (0.24, 0.5, 0.28)
DARK_GREEN = (0.16, 0.24, 0.2)
GALV = (0.85, 0.86, 0.86)
TIRE_COLORS = [(0.78, 0.22, 0.18), (0.9, 0.75, 0.2), (0.22, 0.4, 0.75), (0.3, 0.6, 0.3)]
WHITE = (1.0, 1.0, 1.0)
UP = Vector((0.0, 1.0, 0.0))


class F:
    """Своя система координат предмета: начало (ox, oz) на земле, поворот yaw° вокруг Y (как rotation.y в Godot).
    Перед предмета — локальный −x."""
    def __init__(self, ox, oz, yaw=0.0, oy=0.0):
        a = math.radians(yaw)
        self.o = Vector((ox, oy, oz))
        self.c, self.s = math.cos(a), math.sin(a)

    def p(self, x, y, z):
        return Vector((self.o.x + x * self.c + z * self.s, self.o.y + y, self.o.z - x * self.s + z * self.c))


ID = F(0.0, 0.0)


def _normal(pts):
    n = Vector((0.0, 0.0, 0.0))
    for i, a in enumerate(pts):
        b2 = pts[(i + 1) % len(pts)]
        n.x += (a.y - b2.y) * (a.z + b2.z)
        n.y += (a.z - b2.z) * (a.x + b2.x)
        n.z += (a.x - b2.x) * (a.y + b2.y)
    return n.normalized() if n.length > 1e-9 else n


def _planar(pts, s):
    n = _normal(pts)
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    if ay >= ax and ay >= az:
        return [(p.x / s, -p.z / s) for p in pts]
    if ax >= az:
        return [(-p.z / s if n.x > 0 else p.z / s, p.y / s) for p in pts]
    return [(p.x / s if n.z > 0 else -p.x / s, p.y / s) for p in pts]


def face(b, f, pts, m, c, out=None, uvs=None, s=1.0):
    """Многоугольник по локальным точкам; out — куда должна смотреть лицевая сторона (порядок развернётся сам)."""
    pts = [Vector(p) for p in pts]
    if out is not None and _normal(pts).dot(Vector(out)) < 0:
        pts = pts[::-1]
        if uvs is not None:
            uvs = uvs[::-1]
    if uvs is None:
        uvs = _planar(pts, s)
    b.cur = c
    b.gquad([tuple(f.p(*p)) for p in pts], uvs, m)


def box(b, f, x0, x1, y0, y1, z0, z1, m, c, snow=True, s=1.0, skip=("down",), top=None):
    """Коробка в локальных координатах; верх — снег (если snow), низ по умолчанию не нужен."""
    sides = {
        "+x": ([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], (1, 0, 0)),
        "-x": ([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], (-1, 0, 0)),
        "+z": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
        "-z": ([(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)], (0, 0, -1)),
        "up": ([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], (0, 1, 0)),
        "down": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
    }
    for k, (pts, out) in sides.items():
        if k in skip:
            continue
        if k == "up" and (snow or top):
            face(b, f, pts, top or M["snow"], WHITE, out, s=s)
        else:
            face(b, f, pts, m, c, out, s=s)


def tube(b, f, a, z, r, m, c, segs=6):
    """Труба от точки a до z (локально)."""
    b.cur = c
    b.cyl(P(*f.p(*a)), P(*f.p(*z)), r, r, m, segs=segs)


def snow_ridge(b, f, a, z, r, t=0.05):
    """Снежный валик поверх горизонтальной трубы/бруса a → z."""
    a, z = Vector(a), Vector(z)
    d = (z - a).normalized()
    side = d.cross(UP)
    if side.length < 1e-3:
        return
    side.normalize()
    q = [(p + side * r * 1.05 + UP * r * 0.3, p + UP * (r + t), p - side * r * 1.05 + UP * r * 0.3) for p in (a, z)]
    for (i, j) in ((0, 1), (1, 2)):
        face(b, f, [q[0][i], q[1][i], q[1][j], q[0][j]], M["snow"], WHITE, out=UP + (side if i == 0 else -side) * 0.5,
             uvs=[(0, 0), (1, 0), (1, 0.3), (0, 0.3)])


def torus(b, f, c, axis, e1, R, rw, rh, ph0, ph1, nph, nth, color, m):
    """Покрышка: тор вокруг оси axis (e1 ⟂ axis), дуга от ph0 до ph1 (рад). Грани, смотрящие вверх, — в снегу."""
    c, axis, e1 = Vector(c), Vector(axis), Vector(e1)
    e2 = axis.cross(e1)
    def pt(ph, th):
        e = e1 * math.cos(ph) + e2 * math.sin(ph)
        return c + e * (R + rw * math.cos(th)) + axis * rh * math.sin(th), (e * math.cos(th) / rw + axis * math.sin(th) / rh).normalized()
    for i in range(nph):
        a0 = ph0 + (ph1 - ph0) * i / nph
        a1 = ph0 + (ph1 - ph0) * (i + 1) / nph
        for j in range(nth):
            t0, t1 = 2 * math.pi * j / nth, 2 * math.pi * (j + 1) / nth
            q = [pt(a0, t0), pt(a1, t0), pt(a1, t1), pt(a0, t1)]
            n = (q[0][1] + q[1][1] + q[2][1] + q[3][1]).normalized()
            snowy = n.y > 0.55
            face(b, f, [p for p, _ in q], M["snow"] if snowy else m, WHITE if snowy else color, out=n,
                 uvs=[(i / nph, j / nth), ((i + 1) / nph, j / nth), ((i + 1) / nph, (j + 1) / nth), (i / nph, (j + 1) / nth)])


def lathe(b, f, cx, cz, prof, segs, m_side, c_side, snow_y=0.5, jitter=None):
    """Тело вращения по профилю [(радиус, высота)] снизу вверх; грани круче snow_y по нормали — в снегу.
    jitter = (random, доля) — бугристый край (куст)."""
    k_r = [[1.0] * segs for _ in prof]
    if jitter:
        jr, amt = jitter
        k_r = [[1.0 + jr.uniform(-amt, amt) for _ in range(segs)] for _ in prof]
    for k in range(len(prof) - 1):
        (r0, y0), (r1, y1) = prof[k], prof[k + 1]
        for i in range(segs):
            i1 = (i + 1) % segs
            a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
            ra0, ra1 = r0 * k_r[k][i], r0 * k_r[k][i1]
            rb0, rb1 = r1 * k_r[k + 1][i], r1 * k_r[k + 1][i1]
            pts = [Vector((cx + ra0 * math.cos(a0), y0, cz + ra0 * math.sin(a0))), Vector((cx + ra1 * math.cos(a1), y0, cz + ra1 * math.sin(a1))),
                   Vector((cx + rb1 * math.cos(a1), y1, cz + rb1 * math.sin(a1))), Vector((cx + rb0 * math.cos(a0), y1, cz + rb0 * math.sin(a0)))]
            mid = sum(pts, Vector()) / 4
            out = (mid - Vector((cx, (y0 + y1) / 2 - 0.3, cz))).normalized()
            n = _normal(pts)
            if n.dot(out) < 0:
                n = -n
            snowy = n.y > snow_y
            if r1 < 1e-4:
                pts = pts[:3]
            face(b, f, pts, M["snow"] if snowy else m_side, WHITE if snowy else c_side, out=out)


# ------------------------------------------------------------------ предметы площадки
def bench(b, f, length=1.8, back=True):
    """Зелёная лавка: сиденье из трёх брусков, спинка из трёх, ножки — тёмные трубы. Лицом в −x."""
    hl = length / 2
    for z in (-hl + 0.15, hl - 0.15):
        tube(b, f, (-0.2, 0.0, z), (-0.2, 0.42, z), 0.025, M["pg_paint"], DARK_GREEN, segs=4)
        tube(b, f, (0.18, 0.0, z), (0.2, 0.42, z), 0.025, M["pg_paint"], DARK_GREEN, segs=4)
        tube(b, f, (-0.22, 0.4, z), (0.22, 0.4, z), 0.02, M["pg_paint"], DARK_GREEN, segs=4)
        if back:
            tube(b, f, (0.2, 0.42, z), (0.28, 0.88, z), 0.02, M["pg_paint"], DARK_GREEN, segs=4)
    for i in range(3):
        x0 = -0.24 + i * 0.16
        box(b, f, x0, x0 + 0.13, 0.42, 0.46, -hl, hl, M["pg_planks"], GREEN, s=0.6)
    if back:
        for i in range(3):
            y0 = 0.52 + i * 0.13
            x = 0.21 + (y0 - 0.42) * 0.17
            box(b, f, x, x + 0.035, y0, y0 + 0.1, -hl, hl, M["pg_planks"], GREEN, s=0.6)


def l_bench(b):
    """Г-образная лавка без спинки: два прогона сидений на брусках-ногах (угол — L_BENCH)."""
    x, z = L_BENCH
    runs = [(x - 0.2, x + 0.2, z, z + 2.4), (x, x + 2.0, z - 0.2, z + 0.2)]
    for (x0, x1, z0, z1) in runs:
        alongz = (z1 - z0) > (x1 - x0)
        n = 4
        for k in range(n):
            t = (k + 0.5) / n
            if alongz:
                zz = z0 + 0.15 + (z1 - z0 - 0.3) * (k / (n - 1))
                box(b, ID, x0 + 0.05, x1 - 0.05, 0.0, 0.4, zz - 0.04, zz + 0.04, M["pg_paint"], DARK_GREEN, snow=False)
            else:
                xx = x0 + 0.15 + (x1 - x0 - 0.3) * (k / (n - 1))
                box(b, ID, xx - 0.04, xx + 0.04, 0.0, 0.4, z0 + 0.05, z1 - 0.05, M["pg_paint"], DARK_GREEN, snow=False)
        if alongz:
            for i in range(3):
                a = x0 + i * 0.135
                box(b, ID, a, a + 0.12, 0.4, 0.44, z0, z1, M["pg_planks"], GREEN, s=0.6)
        else:
            for i in range(3):
                a = z0 + i * 0.135
                box(b, ID, x0 + 0.4, x1, 0.4, 0.44, a, a + 0.12, M["pg_planks"], GREEN, s=0.6)


def litter_bin(b):
    x, z = BIN
    lathe(b, ID, x, z, [(0.24, 0.0), (0.25, 0.62), (0.26, 0.66)], 8, M["pg_paint"], (0.45, 0.5, 0.55), snow_y=0.8)
    face(b, ID, [(x + 0.25 * math.cos(a), 0.6, z + 0.25 * math.sin(a)) for a in [2 * math.pi * i / 8 for i in range(8)]],
         M["snow"], WHITE, out=(0, 1, 0))


def tower(b):
    """Домик-башня: площадка на 1 м, жёлтые стены с окнами, перила спереди, красная крыша, лесенка к дому."""
    x, z, yaw = TOWER
    f = F(x, z, yaw)
    h = 0.7
    fl = 1.0
    for (px, pz) in ((-h, -h), (h, -h), (-h, h), (h, h)):
        box(b, f, px - 0.05, px + 0.05, 0.0, 2.2, pz - 0.05, pz + 0.05, M["pg_paint"], YELLOW, s=0.5)
    for (a, c2, e, g) in ((-h, h, -h, -h + 0.06), (-h, h, h - 0.06, h), (-h, -h + 0.06, -h, h), (h - 0.06, h, -h, h)):
        box(b, f, a, c2, 0.0, 0.14, e, g, M["pg_planks"], YELLOW, s=0.6)               # нижняя рама
    box(b, f, -h, h, fl, fl + 0.06, -h, h, M["pg_planks"], YELLOW, s=0.7)               # пол площадки
    box(b, f, -h, h, fl - 0.18, fl, -h, -h + 0.03, M["pg_planks"], YELLOW, snow=False)   # подзор
    box(b, f, -h, h, fl - 0.18, fl, h - 0.03, h, M["pg_planks"], YELLOW, snow=False)
    top = fl + 1.05
    win = (fl + 0.4, fl + 0.82)
    # стены: зад (+x) и бока (±z) — доски, в каждой окно 0.6 м
    for side in ("+x", "-z", "+z"):
        def wall(a0, a1, y0, y1):
            if side == "+x":
                box(b, f, h - 0.04, h, y0, y1, a0, a1, M["pg_planks"], YELLOW, s=0.7)
            else:
                zz = -h if side == "-z" else h - 0.04
                box(b, f, a0, a1, y0, y1, zz, zz + 0.04, M["pg_planks"], YELLOW, s=0.7)
        wall(-h, h, fl + 0.06, win[0])
        wall(-h, h, win[1], top)
        wall(-h, -0.3, win[0], win[1])
        wall(0.3, h, win[0], win[1])
    # перед (−x): перила с балясинами и проходом к лесенке
    rail_y = fl + 0.6
    for (z0, z1) in ((-h, -0.25), (0.25, h)):
        box(b, f, -h, -h + 0.05, rail_y, rail_y + 0.06, z0, z1, M["pg_planks"], YELLOW, s=0.6)
        zz = z0 + 0.06
        while zz < z1 - 0.05:
            box(b, f, -h + 0.005, -h + 0.045, fl + 0.06, rail_y, zz, zz + 0.04, M["pg_paint"], YELLOW, snow=False)
            zz += 0.12
    box(b, f, -h, -h + 0.05, top - 0.12, top, -h, h, M["pg_planks"], YELLOW, s=0.6)     # верхняя балка над входом
    # крыша: конёк от дома во двор (вдоль x), фронтоны спереди и сзади
    e = 0.85
    y0, y1 = top + 0.12, top + 0.75
    for sg in (-1, 1):
        pts = [(-e, y0, sg * e), (e, y0, sg * e), (e, y1, 0.0), (-e, y1, 0.0)]
        face(b, f, pts, M["pg_planks"], RED, out=(0, 1, sg * 0.8), s=0.7)
        face(b, f, pts, M["pg_planks"], (RED[0] * 0.7, RED[1] * 0.7, RED[2] * 0.7), out=(0, -1, -sg * 0.8), s=0.7)
        # снег на скате — до кромки не доходит, красный край видно
        k = 0.82
        sp = [(-e + 0.06, y0 + (y1 - y0) * (1 - k) + 0.04, sg * e * k), (e - 0.06, y0 + (y1 - y0) * (1 - k) + 0.04, sg * e * k),
              (e - 0.06, y1 + 0.05, 0.0), (-e + 0.06, y1 + 0.05, 0.0)]
        face(b, f, sp, M["snow"], WHITE, out=(0, 1, sg * 0.8), s=0.7)
    for sx in (-h, h):
        face(b, f, [(sx, top, -h), (sx, top, h), (sx, y1 - 0.08, 0.0)], M["pg_planks"], YELLOW,
             out=(1 if sx > 0 else -1, 0, 0), s=0.7)
        face(b, f, [(sx, top, -h), (sx, top, h), (sx, y1 - 0.08, 0.0)], M["pg_planks"], YELLOW,
             out=(-1 if sx > 0 else 1, 0, 0), s=0.7)
    box(b, f, -h, h, top, top + 0.12, -h, -h + 0.04, M["pg_planks"], YELLOW, snow=False)
    box(b, f, -h, h, top, top + 0.12, h - 0.04, h, M["pg_planks"], YELLOW, snow=False)
    # лесенка к дому
    lx0, lx1 = -h - 0.85, -h
    for zz in (-0.24, 0.24):
        tube(b, f, (lx0, 0.0, zz), (lx1, fl + 0.06, zz), 0.035, M["pg_paint"], YELLOW, segs=5)
        tube(b, f, (lx1 - 0.05, fl + 0.06, zz), (lx1 - 0.05, fl + 0.85, zz), 0.03, M["pg_paint"], YELLOW, segs=5)
    for k in range(1, 5):
        t = k / 5
        xr, yr = lx0 + (lx1 - lx0) * t, (fl + 0.06) * t
        box(b, f, xr - 0.06, xr + 0.06, yr - 0.03, yr, -0.24, 0.24, M["pg_planks"], YELLOW, s=0.5)


def swing(b):
    """Качели: тёмно-зелёная рама, слева стенка-скалодром, в середине сиденье на цепях, справа лесенка."""
    x, z, yaw = SWING
    f = F(x, z, yaw)
    pm, col = M["pg_paint"], DARK_GREEN
    H = 2.3
    for zz in (-1.1, 1.1):                                           # А-рамы по краям качелей
        tube(b, f, (-0.8, 0.0, zz), (0.0, H, zz), 0.045, pm, col)
        tube(b, f, (0.8, 0.0, zz), (0.0, H, zz), 0.045, pm, col)
        tube(b, f, (-0.5, 0.8, zz), (0.5, 0.8, zz), 0.03, pm, col, segs=5)
    tube(b, f, (0.0, H, -1.9), (0.0, H, 1.9), 0.05, pm, col)          # верхняя балка
    snow_ridge(b, f, (0.0, H, -1.9), (0.0, H, 1.9), 0.05)
    for zz in (-1.9, 1.9):                                           # стойки крайних пролётов
        tube(b, f, (0.0, 0.0, zz), (0.0, H, zz), 0.045, pm, col)
    # стенка-скалодром: тёмная плита с белыми зацепами
    box(b, f, -0.03, 0.03, 0.25, 1.95, -1.85, -1.15, M["pg_paint"], (0.2, 0.24, 0.26), s=0.8)
    r = random.Random(49)
    for k in range(9):
        hy = 0.4 + (k // 2) * 0.33 + r.uniform(-0.05, 0.05)
        hz = -1.68 + (k % 2) * 0.34 + r.uniform(-0.06, 0.06)
        for sx in (-1, 1):
            box(b, f, sx * 0.03, sx * 0.07, hy, hy + 0.06, hz - 0.05, hz + 0.05, M["pg_paint"], (0.9, 0.9, 0.86), snow=False,
                skip=("down", "+x" if sx < 0 else "-x"))
    # лесенка
    for zz in (1.15, 1.85):
        tube(b, f, (0.0, 0.0, zz), (0.0, H, zz), 0.03, pm, col, segs=5)
    yy = 0.3
    while yy < H - 0.1:
        tube(b, f, (0.0, yy, 1.15), (0.0, yy, 1.85), 0.02, pm, col, segs=4)
        snow_ridge(b, f, (0.0, yy, 1.15), (0.0, yy, 1.85), 0.02, 0.025)
        yy += 0.27
    # сиденье на цепях
    for zz in (-0.24, 0.24):
        tube(b, f, (0.0, H - 0.03, zz), (0.0, 0.47, zz * 0.92), 0.008, M["dark"], (1, 1, 1), segs=3)
    box(b, f, -0.13, 0.13, 0.42, 0.47, -0.25, 0.25, M["pg_paint"], YELLOW, s=0.5)
    box(b, f, 0.1, 0.13, 0.47, 0.6, -0.25, 0.25, M["pg_paint"], YELLOW, snow=False)


def sandbox(b):
    """Песочница-беседка: зелёные борта с жёлтыми сиденьями по краю, жёлто-зелёные стойки, плоская оцинкованная
    крыша с наклоном к дому, внутри — снег вместо песка."""
    x, z = SANDBOX
    f = F(x, z)
    h = 1.1
    for (a, c2, e, g) in ((-h, h, -h, -h + 0.06), (-h, h, h - 0.06, h), (-h, -h + 0.06, -h, h), (h - 0.06, h, -h, h)):
        box(b, f, a, c2, 0.0, 0.34, e, g, M["pg_planks"], GREEN, snow=False, s=0.7)
    for (a, c2, e, g) in ((-h, h, -h, -h + 0.2), (-h, h, h - 0.2, h), (-h, -h + 0.2, -h + 0.2, h - 0.2), (h - 0.2, h, -h + 0.2, h - 0.2)):
        box(b, f, a, c2, 0.34, 0.38, e, g, M["pg_planks"], YELLOW, s=0.7)
    box(b, f, -h + 0.06, h - 0.06, 0.0, 0.26, -h + 0.06, h - 0.06, M["snow"], WHITE, skip=("down", "+x", "-x", "+z", "-z"))
    for (px, pz) in ((-h + 0.05, -h + 0.05), (h - 0.05, -h + 0.05), (-h + 0.05, h - 0.05), (h - 0.05, h - 0.05)):
        ytop = 1.95 if px < 0 else 2.12
        box(b, f, px - 0.045, px + 0.045, 0.0, 1.0, pz - 0.045, pz + 0.045, M["pg_paint"], GREEN, snow=False)
        box(b, f, px - 0.045, px + 0.045, 1.0, ytop, pz - 0.045, pz + 0.045, M["pg_paint"], YELLOW, snow=False)
    # обвязка под крышей и сама крыша (выше сзади)
    e = 1.3
    ya, yb = 1.95, 2.12
    for zz in (-h + 0.05, h - 0.05):
        tube(b, f, (-h, ya - 0.04, zz), (h, yb - 0.04, zz), 0.035, M["pg_paint"], GREEN, segs=4)
    face(b, f, [(-e, ya, -e), (-e, ya, e), (e, yb, e), (e, yb, -e)], M["pg_roof"], GALV, out=(-0.08, -1, 0), s=1.0)
    face(b, f, [(-e, ya + 0.03, -e), (-e, ya + 0.03, e), (e, yb + 0.03, e), (e, yb + 0.03, -e)], M["pg_roof"], GALV,
         out=(-0.08, 1, 0), s=1.0)
    k = 0.08
    face(b, f, [(-e + k, ya + 0.1, -e + k), (-e + k, ya + 0.1, e - k), (e - k, yb + 0.1, e - k), (e - k, yb + 0.1, -e + k)],
         M["snow"], WHITE, out=(-0.08, 1, 0), s=1.0)
    for (a, b2, s2) in (((-e, ya, -e), (e, yb, -e), -1), ((-e, ya, e), (e, yb, e), 1)):
        face(b, f, [a, b2, (b2[0], b2[1] + 0.1, b2[2] - s2 * k), (a[0], a[1] + 0.1, a[2] - s2 * k)], M["snow"], WHITE,
             out=(0, 0.3, s2))
    face(b, f, [(-e, ya, e), (-e, ya, -e), (-e + k, ya + 0.1, -e + k), (-e + k, ya + 0.1, e - k)], M["snow"], WHITE, out=(-1, 0.3, 0))
    face(b, f, [(e, yb, -e), (e, yb, e), (e - k, yb + 0.1, e - k), (e - k, yb + 0.1, -e + k)], M["snow"], WHITE, out=(1, 0.3, 0))


def planter_fence(b, cx, cz):
    """Решётчатая оградка клумбы 2.6 × 2.6: рейки — альфа-текстурой на двусторонних гранях, бруски по углам."""
    h = PLANTER / 2
    H = 0.5
    f = F(cx, cz)
    for (p0, p1) in (((-h, -h), (h, -h)), ((h, -h), (h, h)), ((h, h), (-h, h)), ((-h, h), (-h, -h))):
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        face(b, f, [(p0[0], 0.0, p0[1]), (p1[0], 0.0, p1[1]), (p1[0], H, p1[1]), (p0[0], H, p0[1])], M["pg_lattice"], WHITE,
             uvs=[(0, 0), (L, 0), (L, 1), (0, 1)])
    for (px, pz) in ((-h, -h), (h, -h), (-h, h), (h, h), (0, -h), (0, h), (-h, 0), (h, 0)):
        box(b, f, px - 0.04, px + 0.04, 0.0, H + 0.08, pz - 0.04, pz + 0.04, M["pg_planks"], (0.5, 0.36, 0.24), s=0.5)


def planter_inside(bt, cx, cz, kind, r):
    """Земля клумбы под снегом (пологий холм) и дерево или круглый вечнозелёный куст."""
    h = PLANTER / 2 - 0.05
    f = F(cx, cz)
    face(bt, f, [(-h, 0.12, h), (h, 0.12, h), (h, 0.12, -h), (-h, 0.12, -h)], M["snow"], WHITE, out=(0, 1, 0), s=1.5)
    if kind == "tree":
        tree3d(bt, cx + r.uniform(-0.2, 0.2), cz + r.uniform(-0.2, 0.2), r.uniform(6.5, 8.5), False, r)
    else:
        prof = [(0.45, 0.1), (0.72, 0.3), (0.78, 0.6), (0.66, 0.9), (0.36, 1.12), (0.0, 1.2)]
        lathe(bt, f, 0.0, 0.0, prof, 9, M["leaf"], (0.6, 0.66, 0.58), snow_y=0.55, jitter=(r, 0.12))


def tire_row(b):
    x, z0, z1, step = TIRE_ROW
    r = random.Random(7)
    z = z0
    i = 0
    while z <= z1 + 1e-6:
        c = TIRE_COLORS[i % len(TIRE_COLORS)]
        torus(b, ID, (x + r.uniform(-0.04, 0.04), 0.02, z), (1, 0, 0), (0, 0, 1), 0.27, 0.07, 0.1,
              math.radians(-12), math.radians(192), 8, 6, c, M["pg_paint"])
        z += step
        i += 1


def bollards(b):
    for (x, z) in BOLLARDS:
        torus(b, ID, (x, 0.1, z), (0, 1, 0), (1, 0, 0), 0.25, 0.12, 0.1, 0.0, 2 * math.pi, 10, 6, (0.3, 0.55, 0.32), M["pg_paint"])
        torus(b, ID, (x, 0.3, z), (0, 1, 0), (1, 0, 0), 0.25, 0.12, 0.1, 0.0, 2 * math.pi, 10, 6, (0.88, 0.75, 0.2), M["pg_paint"])
        face(b, ID, [(x + 0.2 * math.cos(a), 0.34, z + 0.2 * math.sin(a)) for a in [2 * math.pi * i / 8 for i in range(8)]],
             M["snow"], WHITE, out=(0, 1, 0))
        tube(b, ID, (x, 0.0, z), (x, 0.75, z), 0.045, M["pg_paint"], (0.55, 0.55, 0.55))
        face(b, ID, [(x + 0.05 * math.cos(a), 0.76, z + 0.05 * math.sin(a)) for a in [2 * math.pi * i / 6 for i in range(6)]],
             M["snow"], WHITE, out=(0, 1, 0))


def arches(b):
    for z in ARCHES:
        f = F(11.9, z)
        for zz in (-0.3, 0.3):
            tube(b, f, (0.0, 0.0, zz), (0.0, 0.5, zz), 0.035, M["pg_paint"], GREEN, segs=5)
        tube(b, f, (0.0, 0.5, -0.3), (0.0, 0.5, 0.3), 0.035, M["pg_paint"], GREEN, segs=5)
        snow_ridge(b, f, (0.0, 0.5, -0.3), (0.0, 0.5, 0.3), 0.035, 0.035)


def ground(bg):
    """Асфальт под снегом: площадка с тротуаром, бордюр со стороны проезда и парковки, поребрик тротуара."""
    x0, x1, z0, z1 = PAD
    # зимой асфальт площадки под утоптанным снегом — чуть серее нетронутого вокруг
    face(bg, ID, [(x0, 0.02, z1), (x1, 0.02, z1), (x1, 0.02, z0), (x0, 0.02, z0)], M["snow"], (0.86, 0.86, 0.88), out=(0, 1, 0), s=3.0)
    curb = (0.78, 0.78, 0.76)
    box(bg, ID, x0 - 0.15, x0, 0.0, 0.15, z0 - 0.15, z1 + 0.15, M["plaster"], curb)
    box(bg, ID, x0, x1, 0.0, 0.15, z0 - 0.15, z0, M["plaster"], curb)
    box(bg, ID, x0, x1, 0.0, 0.15, z1, z1 + 0.15, M["plaster"], curb)
    box(bg, ID, WALK_X1 - 0.06, WALK_X1 + 0.06, 0.0, 0.08, z0, z1, M["plaster"], curb)


# ------------------------------------------------------------------ сборка
def materials():
    MY["materials"]()
    M["pg_paint"] = mat("PgPaint", "pg_paint", rough=0.55)
    M["pg_planks"] = mat("PgPlanks", "pg_planks", rough=0.8)
    M["pg_roof"] = MY["two_sided"](mat("PgRoof", "pg_roof", rough=0.5))
    M["pg_lattice"] = MY["amat"]("PgLattice", "pg_lattice")


def main():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    for ob in list(sc.collection.all_objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(sc.collection.children):
        bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    coll = bpy.data.collections.new("Playground")
    sc.collection.children.link(coll)
    materials()
    b, bt, bg = B(), B(), B()
    for (x, z, yaw) in BENCHES:
        bench(b, F(x, z, yaw))
    l_bench(b)
    litter_bin(b)
    tower(b)
    swing(b)
    sandbox(b)
    for (cx, cz, _) in PLANTERS:
        planter_fence(b, cx, cz)
    tire_row(b)
    bollards(b)
    arches(b)
    r = random.Random(4949)
    for (cx, cz, kind) in PLANTERS:
        planter_inside(bt, cx, cz, kind, r)
    ground(bg)
    obs = [b.build("Playground", coll), bt.build("PlaygroundTrees_nocol", coll), bg.build("PlaygroundGround_nocol", coll)]
    stats = {ob.name: len(ob.data.polygons) for ob in obs}
    os.makedirs(OUT_DIR, exist_ok=True)
    if bpy.context.window:
        bpy.context.window.scene = sc
    for ob in sc.objects:
        ob.select_set(ob in obs)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, use_active_scene=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True,
                              export_vertex_color='ACTIVE', export_animations=False)
    return {"polys": stats, "total": sum(stats.values())}


result = main()
print(result)
