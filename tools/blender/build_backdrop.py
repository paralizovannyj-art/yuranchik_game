# Декорации за краем района «Паскот» (этап E, docs/CITY_PLAN.md): город не обрывается.
#   север  — вторая линия высоток за проспектом;
#   запад  — соседний микрорайон;
#   восток — ТЭЦ: две трубы с красными огнями, градирня, корпуса, прожекторы;
#   юг     — балка (тёмный провал с голыми деревьями и парой домиков), за ней огни дальнего района.
# Туда нельзя дойти: всё без коллизий («nocol» в именах), без теней, один файл.
#
# Выход:  assets/models/district/backdrop.gltf, объекты:
#   BackdropNorth/West/East/South_nocol — дома-коробки (материал BackdropHouse: окна рисует шейдер shaders/backdrop_house.gdshader)
#   BackdropTrees_nocol                 — голые деревья и тополя (тот же материал, без окон)
#   BackdropGlow_nocol                  — дальние огни: квадраты, повёрнутые к району (материал BackdropGlow)
#   BackdropBalka_nocol                 — земля балки и дальнего берега (материал Snow)
# Материалы в Godot подменяет scripts/world/backdrop.gd (по имени материала).
#
# Что шейдер читает из модели:
#   UV  — метры по фасаду (u) и по высоте (v);
#   UV2 — x: номер дома + оттенок стены (дробная часть), y: доля горящих окон (0..1);
#         y = -1 — глухая стена/крыша/ствол, y = -2 — полосы дымовой трубы.
#   у огней UV2 — x: цвет (0 натрий, 1 красный, 2 белый, 3 окно), y: 1 — мигает.
#
# Запуск в открытом Blender (Blender MCP / вкладка Scripting):
#   DISTRICT_ROOT = r"<папка проекта>"; exec(open(DISTRICT_ROOT + r"\tools\blender\build_backdrop.py", encoding="utf-8").read())
# Координаты в скрипте — как в Godot (X вправо, Y вверх, Z на юг); в Blender переводятся в (x, -z, y).
import bpy
import math
import os
import random

ROOT = globals().get("DISTRICT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "assets", "models", "district", "backdrop.gltf")
R = random.Random(20261113)

EDGE = 101.0            # край играбельной зоны по X; по Z: -110 (север) … 102 (юг)
BALKA_Z0 = 102.0


class Mesh:
    """Копилка граней одного объекта. Точки — в координатах Godot."""

    def __init__(self, name):
        self.name, self.v, self.f, self.uv, self.uv2, self.mi = name, [], [], [], [], []

    def poly(self, pts, uvs, uv2, mat=0, out=None):
        """out — точка, от которой грань должна смотреть наружу (None — порядок точек как есть)."""
        if out is not None:
            a, b, c = pts[0], pts[1], pts[2]
            n = ((b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
                 (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
                 (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
            if sum(n[i] * (a[i] - out[i]) for i in range(3)) < 0:
                pts, uvs = pts[::-1], uvs[::-1]
        i0 = len(self.v)
        # Godot (x, y, z) → Blender (x, -z, y) — это поворот, порядок обхода не меняется
        self.v += [(p[0], -p[2], p[1]) for p in pts]
        self.f.append(list(range(i0, i0 + len(pts))))
        self.uv += list(uvs)
        self.uv2 += [uv2] * len(pts)
        self.mi.append(mat)

    def build(self, mats, coll):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.v, [], self.f)
        l1 = me.uv_layers.new(name="UVMap")
        l2 = me.uv_layers.new(name="UV2")
        for i, uv in enumerate(self.uv):
            l1.data[i].uv = uv
            l2.data[i].uv = self.uv2[i]
        for m in mats:
            me.materials.append(m)
        for p, mi in zip(me.polygons, self.mi):
            p.material_index = mi
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        coll.objects.link(ob)
        return ob


def rot(x, z, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return x * c + z * s, -x * s + z * c


def box(m, cx, cz, w, d, y0, y1, yaw, uv2, top_uv2=None, bottom=False):
    """Коробка: 4 стены (UV в метрах) и крыша. w — вдоль локальной X, d — вдоль локальной Z."""
    cs = []
    for lx, lz in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
        rx, rz = rot(lx, lz, yaw)
        cs.append((cx + rx, cz + rz))
    c = (cx, (y0 + y1) / 2, cz)
    u = 0.0
    for i in range(4):
        (ax, az), (bx_, bz) = cs[i], cs[(i + 1) % 4]
        ln = math.hypot(bx_ - ax, bz - az)
        m.poly([(ax, y0, az), (bx_, y0, bz), (bx_, y1, bz), (ax, y1, az)],
               [(u, 0), (u + ln, 0), (u + ln, y1 - y0), (u, y1 - y0)], uv2, out=c)
        u += ln + 7.0
    t2 = top_uv2 or (uv2[0], -1.0)
    m.poly([(x, y1, z) for x, z in cs], [(0, 0), (1, 0), (1, 1), (0, 1)], t2, out=c)
    if bottom:
        m.poly([(x, y0, z) for x, z in cs], [(0, 0), (1, 0), (1, 1), (0, 1)], t2, out=c)


def tube(m, x, z, y0, y1, r0, r1, segs, uv2, cap=True, mid=None):
    """Труба/ствол: усечённый конус. mid=(доля высоты, радиус) — перехват (градирня)."""
    rings = [(y0, r0)] + ([(y0 + (y1 - y0) * mid[0], mid[1])] if mid else []) + [(y1, r1)]
    for (ya, ra), (yb, rb) in zip(rings, rings[1:]):
        for i in range(segs):
            a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
            p = [(x + ra * math.cos(a0), ya, z + ra * math.sin(a0)), (x + ra * math.cos(a1), ya, z + ra * math.sin(a1)),
                 (x + rb * math.cos(a1), yb, z + rb * math.sin(a1)), (x + rb * math.cos(a0), yb, z + rb * math.sin(a0))]
            m.poly(p, [(i, ya), (i + 1, ya), (i + 1, yb), (i, yb)], uv2, out=(x, (ya + yb) / 2, z))
    if cap:
        m.poly([(x + r1 * math.cos(2 * math.pi * i / segs), y1, z + r1 * math.sin(2 * math.pi * i / segs)) for i in range(segs)],
               [(0, 0)] * segs, (uv2[0], -1.0), out=(x, y0, z))


def stick(m, p0, p1, r0, r1, uv2):
    """Ветка: трёхгранная палка от p0 к p1."""
    d = [p1[i] - p0[i] for i in range(3)]
    ln = math.sqrt(sum(k * k for k in d)) or 1.0
    d = [k / ln for k in d]
    a = (0, 1, 0) if abs(d[1]) < 0.9 else (1, 0, 0)
    u = (d[1] * a[2] - d[2] * a[1], d[2] * a[0] - d[0] * a[2], d[0] * a[1] - d[1] * a[0])
    ul = math.sqrt(sum(k * k for k in u))
    u = [k / ul for k in u]
    w = (d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0])
    ring = lambda p, r: [tuple(p[i] + r * (u[i] * math.cos(t) + w[i] * math.sin(t)) for i in range(3)) for t in (0, 2.094, 4.189)]
    A, Bq = ring(p0, r0), ring(p1, r1)
    c = tuple((p0[i] + p1[i]) / 2 for i in range(3))
    for i in range(3):
        j = (i + 1) % 3
        m.poly([A[i], A[j], Bq[j], Bq[i]], [(0, 0), (1, 0), (1, 1), (0, 1)], uv2, out=c)


# ---------------------------------------------------------------- дома
SEED = [0]


def code(lit, tone=None):
    """UV2 дома: новый номер + оттенок стены, доля горящих окон."""
    SEED[0] += 1
    t = R.uniform(0.15, 0.95) if tone is None else tone
    return (SEED[0] + 0.05 + t * 0.9, lit)


def house(m, kind, cx, cz, yaw, y0, lit):
    """kind: 16 — башня-свечка, 12 — «чешка», 9 — длинная панелька, 5 — хрущёвка."""
    if kind == 16:
        w, d, h = R.choice([(26, 18), (30, 16), (22, 22)]) + (R.choice([48, 50, 53]),)
    elif kind == 12:
        w, d, h = R.uniform(38, 56), 14, 36
    elif kind == 9:
        w, d, h = R.uniform(58, 118), 12.5, 27.5
    else:
        w, d, h = R.uniform(55, 90), 12, 15.5
    uv2 = code(lit)
    box(m, cx, cz, w, d, y0 - 3, y0 + h, yaw, uv2)
    dark = (uv2[0], -1.0)
    # надстройки на крыше — машинные отделения лифтов, выходы: ломают ровную линию силуэта
    n = 1 if kind == 16 else max(1, int(w // 28))
    for i in range(n):
        lx = (i + 0.5) / n * w - w / 2 + R.uniform(-3, 3)
        rx, rz = rot(lx, R.uniform(-1.5, 1.5), yaw)
        box(m, cx + rx, cz + rz, R.uniform(4.5, 7), R.uniform(4, 6), y0 + h, y0 + h + R.uniform(2.4, 3.6), yaw, dark)
    if kind in (16, 12) and R.random() < 0.6:                          # антенна
        rx, rz = rot(R.uniform(-w / 3, w / 3), 0, yaw)
        stick(m, (cx + rx, y0 + h, cz + rz), (cx + rx, y0 + h + R.uniform(7, 12), cz + rz), 0.25, 0.12, dark)
    return w, d


def quarter(m, x0, x1, z0, z1, y0, kinds, lit, cell=(96, 74), fill=0.82, along_z=False):
    """Микрорайон: сетка с разбросом, в каждой клетке дом вдоль или поперёк."""
    nx, nz = max(1, round((x1 - x0) / cell[0])), max(1, round((z1 - z0) / cell[1]))
    for i in range(nx):
        for j in range(nz):
            cx = x0 + (i + 0.5) * (x1 - x0) / nx + R.uniform(-12, 12)
            cz = z0 + (j + 0.5) * (z1 - z0) / nz + R.uniform(-9, 9)
            if R.random() > fill:
                continue
            k = R.choice(kinds)
            yaw = R.choice([0, 0, 0, math.pi / 2]) + R.uniform(-0.05, 0.05)
            if k == 16:
                yaw = R.choice([0, math.pi / 2])
            if along_z:                                   # рядом с краем района: только торцом к нему
                yaw = math.pi / 2
            house(m, k, cx, cz, yaw, y0, R.uniform(*lit))
            LAMPS.append((cx + R.uniform(-30, 30), y0 + 8, cz + R.uniform(-30, 30)))


# ---------------------------------------------------------------- огни
LAMPS = []            # кандидаты на далёкие фонари (возле домов)


def glow(m, p, size, color, blink=0.0):
    """Квадрат-огонёк, повёрнутый лицом к району (центр карты)."""
    dx, dz = -p[0], -p[2]
    ln = math.hypot(dx, dz) or 1.0
    rx, rz = -dz / ln, dx / ln                 # вправо, если смотреть от огня на район
    s = size / 2
    m.poly([(p[0] - rx * s, p[1] - s, p[2] - rz * s), (p[0] + rx * s, p[1] - s, p[2] + rz * s),
            (p[0] + rx * s, p[1] + s, p[2] + rz * s), (p[0] - rx * s, p[1] + s, p[2] - rz * s)],
           [(0, 0), (1, 0), (1, 1), (0, 1)], (float(color), blink), out=(p[0] * 3, p[1], p[2] * 3))


# ---------------------------------------------------------------- балка
def balka_h(x, z):
    """Высота земли южнее района: спуск в балку, дно, подъём на дальний берег."""
    edge = -12.0 if abs(x) <= EDGE + 1 else 0.0
    wob = 3.5 * math.sin(x * 0.011 + 1.3) + 2.0 * math.sin(x * 0.027 + z * 0.01)
    far = -7.0 + 1.5 * math.sin(x * 0.008)
    bottom = -31.0 + wob
    zc = z + 22.0 * math.sin(x * 0.006 + 0.5)             # балка слегка петляет
    if zc < 196:
        t = max(0.0, min(1.0, (zc - BALKA_Z0) / (196 - BALKA_Z0)))
        t = t * t * (3 - 2 * t)
        return edge + (bottom - edge) * t
    if zc < 236:
        return bottom + 1.2 * math.sin(z * 0.2)
    t = max(0.0, min(1.0, (zc - 236) / 96.0))
    t = t * t * (3 - 2 * t)
    return bottom + (far - bottom) * t


def balka(m):
    xs = sorted(set([-560 + 28 * i for i in range(41)] + [-EDGE - 3, -EDGE - 0.5, EDGE + 0.5, EDGE + 3]))
    zs = [BALKA_Z0 + 13.0 * i for i in range(21)] + [400, 470, 560, 660]
    H = {(x, z): balka_h(x, z) for x in xs for z in zs}
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            xa, xb, za, zb = xs[i], xs[i + 1], zs[j], zs[j + 1]
            p = [(xa, H[xa, za], za), (xa, H[xa, zb], zb), (xb, H[xb, zb], zb), (xb, H[xb, za], za)]
            m.poly(p, [(q[0] / 6.0, q[2] / 6.0) for q in p], (0, 0))


def tree(m, x, z, poplar=False):
    y = balka_h(x, z) - 0.3
    dark = (0.05 + R.uniform(0.0, 0.25) * 0.9, -1.0)
    if poplar:                                     # пирамидальный тополь: метла из крутых веток
        h = R.uniform(15, 22)
        stick(m, (x, y, z), (x, y + h, z), 0.38, 0.05, dark)
        for i in range(11):
            t = 0.18 + 0.75 * i / 11
            a = R.uniform(0, 6.28)
            ln = h * (0.34 - 0.2 * t)
            r = ln * 0.24
            stick(m, (x, y + h * t, z), (x + r * math.cos(a), y + h * t + ln, z + r * math.sin(a)), 0.13, 0.03, dark)
        return
    h = R.uniform(7, 11.5)
    lean = (R.uniform(-0.7, 0.7), R.uniform(-0.7, 0.7))
    top = (x + lean[0], y + h * 0.55, z + lean[1])
    stick(m, (x, y, z), top, 0.32, 0.2, dark)
    for i in range(R.randint(4, 6)):
        a = R.uniform(0, 6.28)
        ln = R.uniform(2.8, 5.0)
        up = R.uniform(0.5, 1.1)
        b0 = top
        b1 = (b0[0] + ln * math.cos(a) * 0.8, b0[1] + ln * up, b0[2] + ln * math.sin(a) * 0.8)
        stick(m, b0, b1, 0.16, 0.06, dark)
        for _ in range(2):
            a2 = a + R.uniform(-0.9, 0.9)
            l2 = ln * R.uniform(0.4, 0.65)
            q = tuple(b0[k] + (b1[k] - b0[k]) * R.uniform(0.45, 0.8) for k in range(3))
            stick(m, q, (q[0] + l2 * math.cos(a2) * 0.7, q[1] + l2 * 0.75, q[2] + l2 * math.sin(a2) * 0.7), 0.07, 0.02, dark)


# ---------------------------------------------------------------- ТЭЦ
def power_plant(m, g):
    px, pz, y = 335.0, 5.0, 0.0
    ind = lambda lit=0.0: code(lit, tone=R.uniform(0.05, 0.3))
    # главный корпус: котельный цех выше, турбинный ниже, бункерная этажерка между ними
    box(m, px, pz, 46, 132, y - 2, y + 30, 0, ind(0.22))
    box(m, px + 34, pz - 8, 30, 104, y - 2, y + 44, 0, ind(0.08))
    box(m, px + 12, pz - 8, 14, 104, y + 30, y + 37, 0, ind())
    box(m, px - 40, pz + 30, 28, 46, y - 2, y + 14, 0, ind(0.3))               # админкорпус
    box(m, px - 52, pz - 48, 40, 22, y - 2, y + 9, 0, ind(0.1))                # склад
    box(m, px + 10, pz - 96, 70, 26, y - 2, y + 12, 0, ind(0.05))              # цех
    for i in range(4):                                                          # фильтры/баки
        tube(m, px - 34 + i * 13, pz - 86, y - 2, y + 11, 5, 5, 8, ind())
    # галерея топливоподачи — наклонная
    a, b = (px - 70, y + 4, pz + 92), (px + 20, y + 34, pz + 62)
    for k in range(6):
        t0, t1 = k / 6, (k + 1) / 6
        q0 = tuple(a[i] + (b[i] - a[i]) * t0 for i in range(3))
        q1 = tuple(a[i] + (b[i] - a[i]) * t1 for i in range(3))
        box(m, (q0[0] + q1[0]) / 2, (q0[2] + q1[2]) / 2, math.hypot(q1[0] - q0[0], q1[2] - q0[2]) + 1.5, 5,
            (q0[1] + q1[1]) / 2 - 2, (q0[1] + q1[1]) / 2 + 2, math.atan2(-(q1[2] - q0[2]), q1[0] - q0[0]), ind(), bottom=True)
        if k % 2 == 0:
            stick(m, (q0[0], y - 2, q0[2]), (q0[0], q0[1] - 1, q0[2]), 0.7, 0.7, ind())
    # две дымовые трубы: низ глухой, верх в полоску, красные огни в три яруса
    for (cx, cz, h, r0, r1) in ((px + 62, pz - 34, 132, 7.0, 3.6), (px + 74, pz + 46, 104, 6.0, 3.2)):
        s = code(-1.0, tone=0.2)
        ys = y + h * 0.55
        rm = r0 + (r1 - r0) * 0.55
        tube(m, cx, cz, y - 2, ys, r0, rm, 10, s, cap=False)
        tube(m, cx, cz, ys, y + h, rm, r1, 10, (s[0], -2.0))
        for k, t in enumerate((1.0, 0.72, 0.45)):
            rr = r0 + (r1 - r0) * t + 0.6
            dx, dz = -cx, -cz
            ln = math.hypot(dx, dz)
            for side in (-1, 1):                    # два огня на ярус, по краям трубы
                gx, gz = cx + dx / ln * rr * 0.4 + side * (-dz / ln) * rr, cz + dz / ln * rr * 0.4 + side * (dx / ln) * rr
                g_y = y + h * t - (0.5 if k else 1.0)
                glow(g, (gx, g_y, gz), 7.5 if k == 0 else 6.0, 1, blink=1.0 if k == 0 else 0.0)
    # градирня
    tube(m, px - 20, pz + 142, y - 2, y + 58, 27, 19, 14, code(-1.0, tone=0.35), cap=False, mid=(0.68, 16.5))
    # прожекторные мачты и огни площадки
    for (fx, fz, fy) in ((px - 66, pz - 20, 26), (px - 30, pz + 70, 30), (px - 60, pz + 120, 24), (px - 10, pz - 70, 28)):
        stick(m, (fx, y, fz), (fx, y + fy, fz), 0.5, 0.3, ind())
        glow(g, (fx, y + fy, fz), 9.0, 2)
    for i in range(9):
        glow(g, (px - 78, y + 7, pz - 100 + i * 28 + R.uniform(-4, 4)), 4.0, 0 if i % 3 else 2)
    # забор промзоны и низкие склады перед ТЭЦ
    box(m, px - 92, pz + 10, 1.0, 300, y - 1, y + 3.2, 0, ind())
    for i in range(5):
        box(m, px - 120 - R.uniform(0, 25), pz - 110 + i * 56 + R.uniform(-8, 8), R.uniform(18, 30), R.uniform(30, 44),
            y - 2, y + R.uniform(6, 9), 0, ind(0.04))


# ---------------------------------------------------------------- сборка
def main():
    for o in [o for o in bpy.data.objects if o.name.startswith("Backdrop")]:
        bpy.data.objects.remove(o, do_unlink=True)
    for me in [me for me in bpy.data.meshes if me.name.startswith("Backdrop") and me.users == 0]:
        bpy.data.meshes.remove(me)
    coll = bpy.data.collections.get("Backdrop") or bpy.data.collections.new("Backdrop")
    root = bpy.context.view_layer.layer_collection.collection      # сцена того слоя, из которого экспортируем
    if coll.name not in root.children:
        root.children.link(coll)

    def material(name, color):
        mt = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mt.use_nodes = True
        bsdf = mt.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.95
        return mt

    m_house = material("BackdropHouse", (0.05, 0.055, 0.07, 1))
    m_glow = material("BackdropGlow", (1.0, 0.5, 0.15, 1))
    m_snow = material("BackdropSnow", (0.8, 0.82, 0.88, 1))

    north, west, east, south = Mesh("BackdropNorth_nocol"), Mesh("BackdropWest_nocol"), Mesh("BackdropEast_nocol"), Mesh("BackdropSouth_nocol")
    trees, g, ground = Mesh("BackdropTrees_nocol"), Mesh("BackdropGlow_nocol"), Mesh("BackdropBalka_nocol")

    # север: за проспектом вторая линия высоток, дальше — обычный спальник (включая углы)
    quarter(north, -330, 330, -212, -160, 6, [16, 16, 12], (0.2, 0.42), cell=(62, 50), fill=0.9)
    quarter(north, -560, 560, -480, -216, 0, [9, 9, 16, 12, 5], (0.12, 0.34))
    quarter(north, -560, -340, -200, -140, 0, [9, 5], (0.12, 0.3))
    quarter(north, 340, 560, -200, -140, 0, [9, 5], (0.12, 0.3))
    # запад: соседний микрорайон
    quarter(west, -235, -140, -140, 96, 0, [9, 9, 5, 12], (0.14, 0.36), cell=(48, 80), along_z=True)
    quarter(west, -560, -240, -140, 96, 0, [9, 16, 12, 9, 5], (0.1, 0.3))
    # восток: ряд хрущёвок перед промзоной, по бокам от ТЭЦ — жильё
    quarter(east, 138, 205, -140, 96, 0, [5, 5, 9], (0.12, 0.3), cell=(36, 100), fill=0.75, along_z=True)
    quarter(east, 420, 560, -140, 96, 0, [9, 5], (0.08, 0.2))
    power_plant(east, g)
    # юг: дальний район за балкой — огней меньше, они мельче
    far_y = lambda x: -7.0 + 1.5 * math.sin(x * 0.008)
    for (z0, z1) in ((352, 420), (430, 520), (530, 640)):
        nx = 12
        for i in range(nx):
            cx = -560 + (i + 0.5) * 1120 / nx + R.uniform(-14, 14)
            cz = R.uniform(z0, z1)
            if R.random() < 0.85:
                house(south, R.choice([9, 9, 5, 16, 12]), cx, cz, R.choice([0, 0, math.pi / 2]) + R.uniform(-0.1, 0.1), far_y(cx), R.uniform(0.1, 0.28))
                LAMPS.append((cx + R.uniform(-30, 30), far_y(cx) + 8, cz - R.uniform(10, 30)))

    balka(ground)
    # частный сектор на дне балки: несколько домиков, в двух-трёх горит окно
    for i in range(9):
        hx, hz = -430 + i * 105 + R.uniform(-30, 30), R.uniform(200, 232) - 22.0 * math.sin((-430 + i * 105) * 0.006 + 0.5)
        hy = balka_h(hx, hz)
        yaw = R.uniform(0, 3.14)
        box(south, hx, hz, R.uniform(8, 11), R.uniform(6, 8), hy - 1.5, hy + 3.2, yaw, code(0.0, tone=0.3))
        box(south, hx, hz, 6.5, 4.5, hy + 3.2, hy + 4.6, yaw, code(0.0, tone=0.1))            # «крыша»
        if i % 3 != 1:
            glow(g, (hx, hy + 1.8, hz - 4.5), 2.2, 3)
        if i % 4 == 0:
            glow(g, (hx + 7, hy + 6, hz - 5), 4.5, 0)

    # деревья: на склонах и дне балки; тополя — рядами по бровке и у дальних домов
    for _ in range(150):
        x, z = R.uniform(-470, 470), R.uniform(112, 330)
        if abs(x) < 200 or R.random() < 0.6:
            tree(trees, x, z)
    for i in range(36):
        x = -500 + i * 28 + R.uniform(-6, 6)
        if R.random() < 0.75:
            tree(trees, x, 338 - 22.0 * math.sin(x * 0.006 + 0.5) + R.uniform(-5, 5), poplar=True)
    for x in (-180, -168, -156, -144, 128, 141, 153, 166):
        tree(trees, x + R.uniform(-2, 2), 109 + R.uniform(-2, 3), poplar=True)

    # дальние фонари: у домов (через один), цепочка вдоль дороги за балкой и вдоль второй линии севера
    for i, p in enumerate(LAMPS):
        if i % 2 == 0 and (abs(p[0]) > 150 or p[2] < -150 or p[2] > 300):
            glow(g, p, 3.4 if abs(p[2]) < 330 else 4.2, 0 if i % 7 else 2)
    for i in range(44):
        x = -540 + i * 25 + R.uniform(-3, 3)
        if i % 9 not in (4, 5):                                    # разрывы — перегоревшие
            glow(g, (x, far_y(x) + 7.5, 344 - 22.0 * math.sin(x * 0.006 + 0.5)), 3.6, 0)
    for i in range(30):
        x = -420 + i * 29 + R.uniform(-3, 3)
        if i % 6 != 2:
            glow(g, (x, 8.5, -141), 3.0, 0)

    obs = [north.build([m_house], coll), west.build([m_house], coll), east.build([m_house], coll), south.build([m_house], coll),
           trees.build([m_house], coll), g.build([m_glow], coll), ground.build([m_snow], coll)]
    for o in obs:
        for p in o.data.polygons:
            p.use_smooth = False

    vl = bpy.context.view_layer
    for o in vl.objects:                                          # экспортируем только фон
        o.select_set(False, view_layer=vl)
    for o in obs:
        o.select_set(True, view_layer=vl)
    vl.objects.active = obs[0]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, use_active_scene=True, export_format='GLTF_SEPARATE', export_yup=True,
                              export_apply=True, export_texcoords=True, export_normals=True, export_materials='EXPORT',
                              export_image_format='NONE')
    stats = {o.name: len(o.data.polygons) for o in obs}
    stats["houses"] = SEED[0]
    return stats


BACKDROP_STATS = main()
