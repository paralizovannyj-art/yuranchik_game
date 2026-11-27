# Кадр главного меню (YUR-19): двор Юрчика зимой на закате, Юрчик курит, высунувшись из окна.
#
# По референсам docs/references/main_menu/: главный кадр (image-20261127-134919.png) — камера снаружи у стены
# его панельки, слева окно 9-го этажа, справа от окна кондиционер в сосульках, фасад уходит вдаль, справа
# внизу двор в снегу, за ним склады с белыми крышами и стена шестнадцатиэтажек под розовым небом.
# Двор — по фото из окна: трансформаторная и гаражи в граффити, розовый домик за забором из профнастила,
# детская площадка, парковка вдоль дома, голые деревья и тополя, дом с красными «шапками» на крыше.
#
# Мир — как в Godot (метры, Y вверх): стена дома Юрчика — плоскость x = 0, дом — в сторону −X, двор — в +X;
# фасад тянется вдоль Z. Камера меню стоит снаружи у окна и смотрит вдоль фасада в −Z (см. menu_yard.tscn).
# В Blender: X = x, Y = −z, Z = y (export_yup переводит обратно).
#
# Окно Юрчика — настоящий проём в стене с комнатой за ним (тёплый свет, цветы на подоконнике);
# правая (ближняя к камере, +z) створка открыта внутрь, в проём Юрчик и высовывается.
# Все остальные окна — квадраты атласа menu_windows (горят — по menu_windows_emission).
# Оттенки стен, машин, домов — цветами вершин (ps2_import.gd умножает на них текстуру).
#
# Запуск — в живом Blender через Blender MCP:
#   MENU_ROOT = r"<папка проекта>"; exec(open(MENU_ROOT + r"\tools\blender\build_menu_yard.py", encoding="utf-8").read())
# Строит всё в своей сцене MenuYard (другие сцены не трогает) и пишет assets/models/menu/menu_yard.gltf
# и assets/models/menu/menu_yard.json (точки для Godot: место Юрчика, фонари, окно).
import bpy
import json
import math
import os
import random
from mathutils import Vector

ROOT = globals().get("MENU_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
OUT_DIR = os.path.join(ROOT, "assets", "models", "menu")
OUT = os.path.join(OUT_DIR, "menu_yard.gltf")
OUT_JSON = os.path.join(OUT_DIR, "menu_yard.json")
SCENE = "MenuYard"

ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), ns)
ns["TEX"] = os.path.join(ROOT, "assets", "textures")
mat, Base = ns["mat"], ns["B"]

rnd = random.Random(1927)

# ------------------------------------------------------------------ размеры
FLOOR_H = 2.8
PLINTH = 0.6
FLOORS = 12
BAY = 3.0                          # шаг окон по фасаду
BAYS_Z = (13.5, -82.5)             # фасад дома Юрчика от … до (z); середины клеток — через 3 м от z = 0 (окно Юрчика)
HOME_DEPTH = 12.0
YUR_FLOOR = 8                      # 9-й этаж (счёт с 0)
YB = PLINTH + YUR_FLOOR * FLOOR_H  # пол его комнаты, 23.0
WALL_T = 0.3                       # толщина стены
OPEN_Z = (-0.75, 0.75)             # проём окна по z
OPEN_Y = (YB + 0.85, YB + 2.35)    # подоконник … верх проёма
FRAME_X = -0.12                    # плоскость рамы (утоплена в проём)
SASH_ANGLE = 100.0                 # ° — правая створка распахнута внутрь, к стене комнаты
ROOM_X = (-3.6, -WALL_T)
ROOM_Z = (-1.8, 1.8)
ROOM_H = 2.7
SPOT = (-0.62, YB, 0.36)           # где стоит Юрчик (ноги), лицом в +X — в открытую створку

# двор: карта снега (как в menu_yard_textures.py)
GROUND_ORIGIN = (0.0, -150.0)
GROUND_SIZE = 160.0

LIGHTS = []                        # для Godot: {"kind", "pos", "color", "energy", "range"}


def P(x, y, z):
    """Godot (x, y, z) → Blender."""
    return Vector((x, -z, y))


GK = {"+x": "+X", "-x": "-X", "+z": "-Y", "-z": "+Y", "up": "+Z", "down": "-Z"}


class B(Base):
    """Построитель меша из build_yard.py + цвет вершин у каждой грани (оттенок × текстура)."""
    def __init__(self):
        super().__init__()
        self.col = []
        self.cur = (1.0, 1.0, 1.0)

    def poly(self, pts, uvs, m):
        super().poly(pts, uvs, m)
        self.col.append(self.cur)

    def gbox(self, x0, x1, y0, y1, z0, z1, faces, scale=(1.0, 1.0)):
        """Коробка в координатах Godot; faces — {'+x'|'-x'|'+z'|'-z'|'up'|'down': мат | (мат, rect)}."""
        self.box(P(x0, y0, z1), P(x1, y1, z0), {GK[k]: v for k, v in faces.items()}, scale)

    def gquad(self, pts, uvs, m):
        """Четырёхугольник по точкам Godot (обход — против часовой, если смотреть на лицевую сторону)."""
        self.poly([P(*p) for p in pts], uvs, m)

    def build(self, name, coll):
        ob = super().build(name, coll)
        me = ob.data
        ca = me.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
        for pi, poly in enumerate(me.polygons):
            c = self.col[pi]
            for l in poly.loop_indices:
                ca.data[l].color = (c[0], c[1], c[2], 1.0)
        me.color_attributes.active_color = ca
        return ob


# ------------------------------------------------------------------ материалы
M = {}


def amat(name, tex):
    """Вырез по альфе (деревья) — двусторонний."""
    m = mat(name, tex, rough=0.9)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    t = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    r = nt.nodes.new("ShaderNodeMath")
    r.operation = 'ROUND'
    nt.links.new(t.outputs["Alpha"], r.inputs[0])
    nt.links.new(r.outputs[0], bsdf.inputs["Alpha"])
    m.use_backface_culling = False
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = 'DITHERED'
    return m


def flat(name, rgba, emit=0.0, rough=0.8):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = rgba
    return m


def two_sided(m):
    m.use_backface_culling = False
    return m


def materials():
    M["plaster"] = mat("MenuPlaster", "menu_plaster")
    M["win"] = mat("MenuWindows", "menu_windows", "menu_windows_emission", rough=0.4)
    M["ground"] = mat("MenuGround", "menu_ground")
    M["snow"] = mat("Snow", "snow")
    M["garage"] = mat("MenuGarage", "menu_garage")
    M["ac"] = mat("MenuAc", "menu_ac", rough=0.6)
    M["facade"] = mat("MenuFacadeA", "facade_albedo", "facade_emission")
    M["facade_b"] = mat("MenuFacadeB", "facade_b_albedo", "facade_b_emission")
    M["facade_c"] = mat("MenuFacadeC", "facade_c_albedo", "facade_c_emission")
    M["corr"] = two_sided(mat("MenuCorrugated", "eb_corrugated", rough=0.6))
    M["white"] = mat("MenuWhiteMetal", "eb_white", rough=0.6)
    M["fence"] = mat("MenuFenceConcrete", "fence_concrete")
    M["parquet"] = mat("MenuParquet", "parquet")
    M["wallpaper"] = mat("MenuWallpaper", "wallpaper")
    M["tree"] = amat("MenuTree", "eb_tree")
    M["poplar"] = amat("MenuPoplar", "eb_poplar")
    M["frame"] = flat("MenuPvc", (0.86, 0.86, 0.84, 1), rough=0.5)
    M["glass"] = two_sided(flat("MenuGlass", (0.05, 0.05, 0.06, 1), rough=0.08))
    M["paint"] = flat("MenuPaint", (0.9, 0.9, 0.9, 1), rough=0.45)       # машины, лавки, горка: цвет — в вершинах
    M["dark"] = flat("MenuDarkMetal", (0.08, 0.08, 0.085, 1), rough=0.6)
    M["ice"] = flat("MenuIce", (0.72, 0.8, 0.88, 1), rough=0.15)
    M["leaf"] = two_sided(flat("MenuLeaf", (0.12, 0.26, 0.10, 1), rough=0.7))
    M["pot"] = flat("MenuPot", (0.45, 0.22, 0.12, 1), rough=0.8)
    M["lamp_o"] = flat("MenuLampOrange", (1.0, 0.55, 0.2, 1), emit=3.0)
    M["lamp_w"] = flat("MenuLampWarm", (1.0, 0.8, 0.55, 1), emit=2.0)


# ------------------------------------------------------------------ дом Юрчика
WIN_W, WIN_H, WIN_SILL = 1.5, 1.5, 0.85
WIN_KIND = {"dark": 0, "curtain": 1, "lit": 2, "lit_curtain": 3}


def win_uv(kind):
    u0 = WIN_KIND[kind] * 0.25
    return [(u0, 0.0), (u0 + 0.25, 0.0), (u0 + 0.25, 1.0), (u0, 1.0)]


def pick_window(r):
    x = r.random()
    return "dark" if x < 0.68 else "curtain" if x < 0.9 else "lit" if x < 0.97 else "lit_curtain"


def facade_window(b, x, zc, y0, kind, face=+1):
    """Окно-квадрат атласа на стене x (face +1 — смотрит в +X)."""
    x = x + 0.02 * face
    z0, z1 = zc - WIN_W / 2, zc + WIN_W / 2
    y1 = y0 + WIN_H
    b.cur = (1, 1, 1)
    if face > 0:
        b.gquad([(x, y0, z1), (x, y0, z0), (x, y1, z0), (x, y1, z1)], win_uv(kind), M["win"])
    else:
        b.gquad([(x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0)], win_uv(kind), M["win"])


def ac_unit(b, x, zc, y0, face=+1, icicles=True, w=0.8, h=0.55, d=0.28):
    """Наружный блок кондиционера на стене x: корпус, решётка вентилятора, снег сверху, сосульки, кронштейны."""
    xs = sorted((x, x + d * face))
    z0, z1 = zc - w / 2, zc + w / 2
    b.cur = (0.95, 0.94, 0.92)
    front = "+x" if face > 0 else "-x"
    b.gbox(xs[0], xs[1], y0, y0 + h, z0, z1,
           {front: (M["ac"], (0, 0, 1, 1)), "+z": M["plaster"], "-z": M["plaster"], "down": M["plaster"], "up": M["plaster"]})
    # снег: шапка с наплывом за край
    b.cur = (1, 1, 1)
    b.gbox(xs[0] - 0.01, xs[1] + 0.03, y0 + h, y0 + h + 0.07, z0 - 0.02, z1 + 0.03,
           {"+x": M["snow"], "-x": M["snow"], "+z": M["snow"], "-z": M["snow"], "up": M["snow"]}, (1.0, 1.0))
    # кронштейны
    b.cur = (0.6, 0.6, 0.6)
    for zz in (z0 + 0.08, z1 - 0.08):
        b.gbox(xs[0], xs[1] + 0.02, y0 - 0.04, y0, zz - 0.02, zz + 0.02,
               {"+x": M["dark"], "up": M["dark"], "down": M["dark"], "+z": M["dark"], "-z": M["dark"]})
    if icicles:
        xf = (xs[1] if face > 0 else xs[0]) + 0.01 * face
        n = rnd.randint(6, 10)
        for i in range(n):
            zz = z0 + (i + rnd.uniform(0.2, 0.8)) * w / n
            L = rnd.uniform(0.05, 0.32)
            r = rnd.uniform(0.008, 0.018)
            b.cur = (1, 1, 1)
            b.cyl(P(xf, y0 + 0.01, zz), P(xf + rnd.uniform(-0.01, 0.01), y0 - L, zz), r, 0.001, M["ice"], segs=5)


def home(coll):
    """Фасад дома Юрчика: стена клетками (панели — оттенком вершин), окна атласом, кондиционеры, цоколь.
    Клетка его окна — с настоящим проёмом и откосами."""
    b = B()
    r = random.Random(47)
    nb = int(round((BAYS_Z[0] - BAYS_Z[1]) / BAY))
    for f in range(FLOORS):
        y0 = PLINTH + f * FLOOR_H
        for i in range(nb):
            za = BAYS_Z[0] - i * BAY
            zb = za - BAY
            zc = (za + zb) / 2
            tone = 0.42 + r.uniform(-0.03, 0.03)
            b.cur = (tone * 0.95, tone * 0.95, tone * 1.02)
            mine = (f == YUR_FLOOR and abs(zc) < 0.01)
            if not mine:
                b.gquad([(0, y0, za), (0, y0, zb), (0, y0 + FLOOR_H, zb), (0, y0 + FLOOR_H, za)],
                        [(za / 4, y0 / 4), (zb / 4, y0 / 4), (zb / 4, (y0 + FLOOR_H) / 4), (za / 4, (y0 + FLOOR_H) / 4)],
                        M["plaster"])
                kind = pick_window(r)
                # соседнее окно справа от кондиционера Юрчика не рисуем: в главном кадре теснит кондиционер
                if not (f == YUR_FLOOR and abs(zc + BAY) < 0.01):
                    facade_window(b, 0.0, zc, y0 + WIN_SILL, kind)
                if r.random() < 0.16 and f > 0:
                    ac_unit(b, 0.0, zc + r.choice((-1, 1)) * 1.15, y0 + r.uniform(1.0, 1.9), icicles=r.random() < 0.7,
                            w=0.7, h=0.5, d=0.25)
            else:
                # стена вокруг проёма (4 куска), откосы
                o0, o1 = OPEN_Z
                h0, h1 = OPEN_Y
                parts = [(za, o1, y0, y0 + FLOOR_H), (o0, zb, y0, y0 + FLOOR_H), (o1, o0, y0, h0), (o1, o0, h1, y0 + FLOOR_H)]
                for (p, q, s, t) in parts:
                    b.gquad([(0, s, p), (0, s, q), (0, t, q), (0, t, p)],
                            [(p / 4, s / 4), (q / 4, s / 4), (q / 4, t / 4), (p / 4, t / 4)], M["plaster"])
                b.cur = (0.62, 0.60, 0.58)
                X = -WALL_T
                b.gquad([(0, h0, o0), (0, h0, o1), (X, h0, o1), (X, h0, o0)], [(0, 0), (1, 0), (1, 0.2), (0, 0.2)], M["plaster"])
                b.gquad([(0, h1, o1), (0, h1, o0), (X, h1, o0), (X, h1, o1)], [(0, 0), (1, 0), (1, 0.2), (0, 0.2)], M["plaster"])
                b.gquad([(0, h0, o1), (0, h1, o1), (X, h1, o1), (X, h0, o1)], [(0, 0), (1, 0), (1, 0.2), (0, 0.2)], M["plaster"])
                b.gquad([(0, h1, o0), (0, h0, o0), (X, h0, o0), (X, h1, o0)], [(0, 0), (1, 0), (1, 0.2), (0, 0.2)], M["plaster"])
    # цоколь
    b.cur = (0.36, 0.35, 0.35)
    b.gquad([(0, 0, BAYS_Z[0]), (0, 0, BAYS_Z[1]), (0, PLINTH, BAYS_Z[1]), (0, PLINTH, BAYS_Z[0])],
            [(0, 0), (nb * 0.75, 0), (nb * 0.75, 0.15), (0, 0.15)], M["plaster"])
    # торец и крыша не видны из камеры — только парапет сверху (линия на фоне неба вдали)
    top = PLINTH + FLOORS * FLOOR_H
    b.cur = (0.45, 0.44, 0.44)
    b.gbox(-0.3, 0.05, top, top + 0.9, BAYS_Z[1], BAYS_Z[0], {"+x": M["plaster"], "up": M["snow"]}, (4.0, 4.0))
    # кондиционер Юрчика справа от окна — крупный, с сосульками (главный кадр)
    ac_unit(b, 0.0, -1.55, YB + 1.5, icicles=True, w=0.82, h=0.56, d=0.3)
    # трубка от кондиционера вниз по стене и провод с крыши во двор
    b.cur = (1, 1, 1)
    b.cyl(P(0.04, YB + 1.5, -1.22), P(0.04, 0.6, -1.22), 0.014, 0.014, M["dark"], segs=5)
    wire = [P(0.06, top - 2.5, -7.0)]
    a, c = Vector((0.06, top - 2.5, -7.0)), Vector((88.0, 9.0, -92.0))
    for k in range(1, 25):
        t = k / 24
        p = a.lerp(c, t)
        p.y -= 6.0 * 4 * t * (1 - t)                     # провисание
        wire.append(P(p.x, p.y, p.z))
    for p0, p1 in zip(wire, wire[1:]):
        b.cyl(p0, p1, 0.02, 0.02, M["dark"], segs=4)
    return b.build("HomeFacade_nocol", coll)


def my_window(coll):
    """Рама окна Юрчика (ПВХ): левая половина глухая, правая (к камере, +z) распахнута внутрь;
    отлив снаружи в снегу, подоконник внутри с цветами."""
    b = B()
    o0, o1 = OPEN_Z
    h0, h1 = OPEN_Y
    X = FRAME_X
    t = 0.07                       # ширина профиля
    d = 0.07                       # глубина профиля
    fx = (X - d / 2, X + d / 2)
    F = {"+x": M["frame"], "-x": M["frame"], "+z": M["frame"], "-z": M["frame"], "up": M["frame"], "down": M["frame"]}
    b.cur = (1, 1, 1)
    b.gbox(fx[0], fx[1], h0, h0 + t, o0, o1, F)                 # низ
    b.gbox(fx[0], fx[1], h1 - t, h1, o0, o1, F)                 # верх
    b.gbox(fx[0], fx[1], h0, h1, o0, o0 + t, F)                 # лево (−z)
    b.gbox(fx[0], fx[1], h0, h1, o1 - t, o1, F)                 # право (+z)
    b.gbox(fx[0], fx[1], h0, h1, -0.04, 0.04, F)                # импост
    # глухое стекло (−z половина)
    b.gquad([(X, h0 + t, -0.04), (X, h0 + t, o0 + t), (X, h1 - t, o0 + t), (X, h1 - t, -0.04)],
            [(0, 0), (1, 0), (1, 1), (0, 1)], M["glass"])
    # открытая створка: петли у правого края проёма (+z), повёрнута внутрь комнаты
    hz = o1 - t
    a = math.radians(SASH_ANGLE)
    sw = hz - 0.04                                               # ширина створки
    dx, dz = -math.sin(a) * sw, -math.cos(a) * sw                # от петли к свободному краю
    hx = X - d / 2
    def sp(s, y):                                                # точка створки: s — 0 у петли … 1 у края
        return (hx + dx * s, y, hz + dz * s)
    y0, y1 = h0 + t, h1 - t
    # рама створки (толщина видна в торце) и стекло
    for (s0, s1) in ((0.0, 0.1), (0.9, 1.0)):
        p = [sp(s0, y0), sp(s1, y0), sp(s1, y1), sp(s0, y1)]
        b.gquad(p, [(0, 0), (1, 0), (1, 1), (0, 1)], M["frame"])
        b.gquad(list(reversed(p)), [(0, 0), (1, 0), (1, 1), (0, 1)], M["frame"])
    for (ya, yb_) in ((y0, y0 + 0.07), (y1 - 0.07, y1)):
        p = [sp(0.1, ya), sp(0.9, ya), sp(0.9, yb_), sp(0.1, yb_)]
        b.gquad(p, [(0, 0), (1, 0), (1, 1), (0, 1)], M["frame"])
        b.gquad(list(reversed(p)), [(0, 0), (1, 0), (1, 1), (0, 1)], M["frame"])
    b.gquad([sp(0.1, y0 + 0.07), sp(0.9, y0 + 0.07), sp(0.9, y1 - 0.07), sp(0.1, y1 - 0.07)],
            [(0, 0), (1, 0), (1, 1), (0, 1)], M["glass"])
    # ручка створки
    hp = sp(0.86, (y0 + y1) / 2)
    b.cur = (0.95, 0.95, 0.95)
    b.gbox(hp[0] - 0.03, hp[0] + 0.03, hp[1] - 0.09, hp[1] + 0.02, hp[2] - 0.015, hp[2] + 0.015, F)
    # отлив снаружи и снег на нём (большой сугроб на переднем плане главного кадра)
    b.cur = (0.8, 0.8, 0.82)
    b.gbox(-0.02, 0.24, h0 - 0.05, h0 - 0.01, o0 - 0.06, o1 + 0.06,
           {"+x": M["frame"], "down": M["frame"], "+z": M["frame"], "-z": M["frame"], "up": M["frame"]})
    b.cur = (1, 1, 1)
    snow_ledge(b, 0.0, 0.27, h0 - 0.01, o0 - 0.05, o1 + 0.05)
    # подоконник внутри
    b.cur = (0.92, 0.92, 0.9)
    b.gbox(-WALL_T - 0.26, -WALL_T + 0.02, h0 - 0.04, h0, o0 - 0.15, o1 + 0.15,
           {"+x": M["frame"], "-x": M["frame"], "up": M["frame"], "+z": M["frame"], "-z": M["frame"]})
    # цветы в горшках на подоконнике (у глухой половины) — как на референсе
    for (zz, hh, kind) in ((-0.55, 0.42, "tall"), (-0.22, 0.30, "bush")):
        pot(b, -WALL_T - 0.13, h0, zz, hh, kind)
    return b.build("MyWindow_nocol", coll)


def snow_ledge(b, x0, x1, y0, z0, z1, hgt=0.11, n=10):
    """Снег на отливе: валик со скруглённой верхушкой и неровным краем."""
    prof = [(0.0, 0.0), (0.15, 0.6), (0.45, 1.0), (0.8, 0.85), (1.0, 0.0)]   # поперёк (доля x, доля высоты)
    rows = []
    for i in range(n + 1):
        z = z0 + (z1 - z0) * i / n
        k = hgt * (0.8 + 0.4 * rnd.random()) * (0.6 if i in (0, n) else 1.0)
        rows.append([(x0 + (x1 - x0) * px, y0 + k * py, z) for px, py in prof])
    for i in range(n):
        for j in range(len(prof) - 1):
            a, c = rows[i], rows[i + 1]
            b.gquad([a[j], a[j + 1], c[j + 1], c[j]], [(0, 0), (0.2, 0), (0.2, 0.2), (0, 0.2)], M["snow"])
    for row, flip in ((rows[0], False), (rows[-1], True)):
        pts = [P(*p) for p in row]
        b.poly(pts if not flip else list(reversed(pts)), [(0, 0)] * len(pts), M["snow"])


def pot(b, x, y, z, h, kind):
    b.cur = (1, 1, 1)
    b.cyl(P(x, y, z), P(x, y + 0.13, z), 0.06, 0.08, M["pot"], segs=7, caps=True)
    r = random.Random(int(z * 100))
    for k in range(9 if kind == "bush" else 6):
        a = r.uniform(0, 2 * math.pi)
        ln = h * r.uniform(0.6, 1.0)
        tip = Vector((x + math.cos(a) * ln * 0.45, y + 0.13 + ln, z + math.sin(a) * ln * 0.45))
        base = Vector((x, y + 0.12, z))
        side = Vector((-math.sin(a), 0, math.cos(a))) * 0.05
        mid = base.lerp(tip, 0.55)
        b.gquad([tuple(base), tuple(mid + side), tuple(tip), tuple(mid - side)], [(0, 0), (1, 0), (1, 1), (0, 1)], M["leaf"])


def room(coll):
    """Комната за окном: стены в обоях, пол, потолок, полка, абажур. Видна кусочком через проём."""
    b = B()
    x0, x1 = ROOM_X
    z0, z1 = ROOM_Z
    y0, y1 = YB, YB + ROOM_H
    b.cur = (1.0, 0.9, 0.78)
    b.gquad([(x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1)], [(0, 0), (3.6, 0), (3.6, 2.7), (0, 2.7)], M["wallpaper"])   # дальняя (смотрит в +X)
    b.gquad([(x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1)], [(0, 0), (3.3, 0), (3.3, 2.7), (0, 2.7)], M["wallpaper"])   # +z, смотрит в −z
    b.gquad([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], [(0, 0), (3.3, 0), (3.3, 2.7), (0, 2.7)], M["wallpaper"])   # −z, смотрит в +z
    # стена с окном изнутри (смотрит в −X), вокруг проёма
    o0, o1 = OPEN_Z
    h0, h1 = OPEN_Y
    for (p, q, s, t) in ((z1, o1, y0, y1), (o0, z0, y0, y1), (o1, o0, y0, h0), (o1, o0, h1, y1)):
        b.gquad([(x1, s, q), (x1, s, p), (x1, t, p), (x1, t, q)], [(0, 0), (1, 0), (1, 1), (0, 1)], M["wallpaper"])
    b.cur = (0.8, 0.8, 0.8)
    b.gquad([(x0, y0, z0), (x0, y0, z1), (x1, y0, z1), (x1, y0, z0)], [(0, 0), (3.6, 0), (3.6, 3.3), (0, 3.3)], M["parquet"])
    b.cur = (0.85, 0.83, 0.8)
    b.gquad([(x0, y1, z1), (x0, y1, z0), (x1, y1, z0), (x1, y1, z1)], [(0, 0), (1, 0), (1, 1), (0, 1)], M["plaster"])
    # полка с книгами на дальней стене и шкаф у −z
    b.cur = (0.45, 0.32, 0.22)
    b.gbox(x0, x0 + 0.3, y0 + 1.3, y0 + 1.33, -1.2, 0.2, {"+x": M["plaster"], "up": M["plaster"], "down": M["plaster"]})
    for k in range(9):
        zz = -1.15 + k * 0.14
        b.cur = random.Random(k).choice([(0.5, 0.15, 0.12), (0.2, 0.3, 0.45), (0.7, 0.6, 0.4), (0.25, 0.35, 0.2)])
        b.gbox(x0, x0 + 0.22, y0 + 1.33, y0 + 1.33 + 0.2 + (k % 3) * 0.03, zz, zz + 0.1,
               {"+x": M["paint"], "up": M["paint"], "+z": M["paint"], "-z": M["paint"]})
    b.cur = (0.35, 0.24, 0.16)
    b.gbox(x0, x0 + 0.6, y0, y0 + 2.1, z0, z0 + 1.0, {"+x": M["plaster"], "+z": M["plaster"], "up": M["plaster"]})
    # абажур под потолком
    b.cur = (1, 1, 1)
    lp = (-1.9, y1 - 0.45, 0.0)
    b.cyl(P(lp[0], y1, lp[2]), P(lp[0], lp[1] + 0.2, lp[2]), 0.008, 0.008, M["dark"], segs=4)
    b.cyl(P(lp[0], lp[1] + 0.2, lp[2]), P(lp[0], lp[1], lp[2]), 0.08, 0.22, M["lamp_w"], segs=8)
    LIGHTS.append({"kind": "room", "pos": [lp[0], lp[1] - 0.05, lp[2]], "color": [1.0, 0.72, 0.42], "energy": 1.5, "range": 6.0})
    return b.build("Room_nocol", coll)


# ------------------------------------------------------------------ двор
def ground(coll):
    b = B()
    x0, z0 = GROUND_ORIGIN
    S = GROUND_SIZE
    b.cur = (1, 1, 1)
    # карта двора: u по x, v по z (сверху вниз — как в картинке: v = 1 у z0)
    b.gquad([(x0, 0, z0 + S), (x0 + S, 0, z0 + S), (x0 + S, 0, z0), (x0, 0, z0)],
            [(0, 0), (1, 0), (1, 1), (0, 1)], M["ground"])
    # вокруг — просто снег до горизонта (без нахлёста, чтобы не мерцало)
    far = 900.0
    T = 8.0
    def q(xa, xb, za, zb):
        b.gquad([(xa, 0, zb), (xb, 0, zb), (xb, 0, za), (xa, 0, za)],
                [(xa / T, zb / T), (xb / T, zb / T), (xb / T, za / T), (xa / T, za / T)], M["snow"])
    q(-60, x0, -far, 40)                 # под домом и левее
    q(x0 + S, far, -far, 40)             # правее двора
    q(x0, x0 + S, -far, z0)              # за двором
    q(x0, x0 + S, z0 + S, 40)            # ближе (за камерой)
    return b.build("Ground_nocol", coll)


def car(b, x, z, yaw, color):
    """Машина под снегом: кузов, кабина, снежные шапки на капоте, крыше и багажнике."""
    L, W = 4.2, 1.75
    ca, sa = math.cos(yaw), math.sin(yaw)
    def tr(px, py, pz):
        return (x + px * ca - pz * sa, py, z + px * sa + pz * ca)
    def obox(a0, a1, y0, y1, c0, c1, m_sides, m_top, col):
        # повернутая коробка: a — вдоль машины, c — поперёк
        pts = [tr(a0, y0, c0), tr(a1, y0, c0), tr(a1, y0, c1), tr(a0, y0, c1),
               tr(a0, y1, c0), tr(a1, y1, c0), tr(a1, y1, c1), tr(a0, y1, c1)]
        b.cur = col
        faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        for f in faces:
            b.gquad([pts[i] for i in f], [(0, 0), (1, 0), (1, 1), (0, 1)], m_sides)
        b.cur = (1, 1, 1)
        b.gquad([pts[4], pts[5], pts[6], pts[7]][::-1], [(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)], m_top)
    obox(-L / 2, L / 2, 0.15, 0.78, -W / 2, W / 2, M["paint"], M["snow"], color)
    obox(-0.9, 1.1, 0.78, 1.3, -W / 2 + 0.12, W / 2 - 0.12, M["glass"], M["snow"], (1, 1, 1))
    # снег на крыше горкой
    obox(-0.85, 1.05, 1.3, 1.42, -W / 2 + 0.15, W / 2 - 0.15, M["snow"], M["snow"], (1, 1, 1))
    obox(-L / 2 + 0.05, -0.95, 0.78, 0.86, -W / 2 + 0.05, W / 2 - 0.05, M["snow"], M["snow"], (1, 1, 1))
    obox(1.15, L / 2 - 0.05, 0.78, 0.84, -W / 2 + 0.05, W / 2 - 0.05, M["snow"], M["snow"], (1, 1, 1))
    # колёса — тёмная полоса снизу
    obox(-L / 2 + 0.3, L / 2 - 0.3, 0.0, 0.15, -W / 2 + 0.05, W / 2 - 0.05, M["dark"], M["dark"], (1, 1, 1))


def cars(coll):
    b = B()
    r = random.Random(5)
    colors = [(0.12, 0.12, 0.14), (0.8, 0.8, 0.82), (0.15, 0.2, 0.35), (0.45, 0.1, 0.1), (0.55, 0.55, 0.58), (0.9, 0.9, 0.9)]
    z = 8.0
    while z > -60:
        if r.random() < 0.8:
            car(b, 9.6, z, math.radians(r.uniform(-4, 4)), r.choice(colors))
        z -= r.uniform(2.6, 3.2)
    # пара машин у проезда вдоль дома и у гаражей
    for (x, zz, yaw) in ((3.0, -24.0, 90), (3.0, -46.0, 92), (31.0, -6.0, 15), (52.0, -30.0, 75)):
        car(b, x, zz, math.radians(yaw), r.choice(colors))
    return b.build("Cars_nocol", coll)


def tree_card(b, x, z, h, poplar=False, r=None):
    """Дерево-билборд: 3 перекрещенных квадрата текстуры (вид сверху-сбоку не пропадает)."""
    w = h * (0.5 if poplar else 1.0)
    m = M["poplar"] if poplar else M["tree"]
    a0 = r.uniform(0, math.pi)
    b.cur = (1, 1, 1)
    for k in range(3):
        a = a0 + k * math.pi / 3
        dx, dz = math.cos(a) * w / 2, math.sin(a) * w / 2
        b.gquad([(x - dx, 0, z - dz), (x + dx, 0, z + dz), (x + dx, h, z + dz), (x - dx, h, z - dz)],
                [(0, 0), (1, 0), (1, 1), (0, 1)], m)


def trees(coll):
    b = B()
    r = random.Random(11)
    spots = []
    # ряд вдоль проезда у дома и вдоль парковки
    for z in range(10, -140, -7):
        spots.append((r.uniform(13.0, 16.0), z + r.uniform(-2, 2), r.uniform(7, 11), r.random() < 0.15))
    # двор — по фото: группы у площадки, у трансформаторной, у домика, вдоль дальней тропинки
    groups = [(20, -24, 6, 4), (26, -52, 7, 5), (40, -36, 5, 4), (58, -20, 6, 3), (70, -32, 6, 4),
              (36, -70, 8, 5), (60, -68, 6, 4), (90, -28, 8, 4), (18, -80, 8, 5), (50, -95, 10, 6),
              (100, -40, 10, 4), (120, -110, 14, 6), (30, -110, 10, 5), (80, -120, 12, 5)]
    for (cx, cz, rad, n) in groups:
        for _ in range(n):
            spots.append((cx + r.uniform(-rad, rad), cz + r.uniform(-rad, rad), r.uniform(6, 12), r.random() < 0.2))
    # не в домах и не на машинах
    blocked = [(24, 29.5, -31.5, -25.5), (33.5, 48.5, -20.5, -7.5), (40.5, 55.5, -60.5, -43.5), (7.0, 12.2, -62, 10),
               (55, 155, -100, -34), (12, 25, -46, -34)]
    for (x, z, h, pop) in spots:
        if any(a <= x <= c and e <= z <= f for (a, c, e, f) in blocked):
            continue
        tree_card(b, x, z, h * (1.3 if pop else 1.0), pop, r)
    return b.build("Trees_nocol", coll)


def walls_box(b, x0, x1, y0, y1, z0, z1, m_wall, wall_scale, m_roof=None, sides=("+x", "-x", "+z", "-z")):
    f = {k: m_wall for k in sides}
    b.gbox(x0, x1, y0, y1, z0, z1, f, wall_scale)
    if m_roof:
        b.cur, keep = (1, 1, 1), b.cur
        b.gbox(x0 - 0.15, x1 + 0.15, y1, y1 + 0.18, z0 - 0.15, z1 + 0.15,
               {"up": m_roof, "+x": m_roof, "-x": m_roof, "+z": m_roof, "-z": m_roof}, (4.0, 4.0))
        b.cur = keep


def yard_buildings(coll):
    b = B()
    # трансформаторная посреди двора (центр главного кадра)
    b.cur = (0.95, 0.93, 0.92)
    walls_box(b, 24.0, 29.5, 0, 2.8, -31.5, -25.5, M["garage"], (8.0, 4.0), M["snow"])
    # бетонная коробка в граффити с пристройкой-загородкой (справа внизу главного кадра)
    b.cur = (1.0, 1.0, 1.0)
    walls_box(b, 34.0, 42.0, 0, 3.8, -20.0, -8.0, M["garage"], (8.0, 4.0), M["snow"])
    for (vx, vz) in ((37.0, -12.0), (39.5, -17.0)):
        b.cur = (0.5, 0.5, 0.5)
        b.gbox(vx - 0.3, vx + 0.3, 3.98, 4.4, vz - 0.3, vz + 0.3,
               {"+x": M["dark"], "-x": M["dark"], "+z": M["dark"], "-z": M["dark"], "up": M["snow"]})
    b.cur = (0.9, 0.9, 0.9)
    for (x0, x1, z0, z1) in ((42.0, 48.0, -12.25, -12.0), (42.0, 48.0, -20.0, -19.75), (47.75, 48.0, -20.0, -12.0)):
        walls_box(b, x0, x1, 0, 2.3, z0, z1, M["garage"], (8.0, 4.0), M["snow"])
    # розовый домик за забором из профнастила (фото из окна)
    b.cur = (0.95, 0.62, 0.6)
    walls_box(b, 44.0, 51.0, 0, 3.0, -56.0, -48.0, M["plaster"], (3.0, 3.0))
    gable(b, 43.6, 51.4, 3.0, 4.4, -56.4, -47.6)
    b.cur = (0.55, 0.42, 0.35)
    for (x0, x1, z0, z1) in ((41.0, 55.0, -60.0, -59.9), (41.0, 55.0, -44.1, -44.0), (41.0, 41.1, -60.0, -44.0),
                             (54.9, 55.0, -60.0, -44.0)):
        b.gbox(x0, x1, 0, 2.0, z0, z1, {"+x": M["corr"], "-x": M["corr"], "+z": M["corr"], "-z": M["corr"]}, (4.0, 2.0))
        b.cur, keep = (1, 1, 1), b.cur
        b.gbox(x0, x1, 2.0, 2.06, z0 - 0.02, z1 + 0.02, {"up": M["snow"]}, (4.0, 4.0))
        b.cur = keep
    # детская площадка у дома: горка-домик с красной крышей, качели, лавки
    b.cur = (0.85, 0.75, 0.3)
    b.gbox(17.0, 18.6, 0, 1.6, -40.6, -39.0, {"+x": M["paint"], "-x": M["paint"], "+z": M["paint"], "-z": M["paint"]})
    b.cur = (0.75, 0.15, 0.12)
    gable(b, 16.8, 18.8, 1.6, 2.4, -40.8, -38.8, m=M["paint"])
    b.cur = (0.25, 0.45, 0.3)
    for (x, z) in ((14.0, -36.0), (14.0, -44.0), (22.5, -45.5)):
        b.gbox(x - 0.9, x + 0.9, 0.35, 0.45, z - 0.25, z + 0.25,
               {"+x": M["paint"], "-x": M["paint"], "+z": M["paint"], "-z": M["paint"], "up": M["snow"]})
    b.cur = (1, 1, 1)
    for (x0, z0, x1, z1) in ((20.0, -36.0, 20.0, -38.5),):
        for zz in (z0, z1):
            b.cyl(P(x0 - 0.8, 0, zz), P(x0, 2.2, zz), 0.04, 0.04, M["dark"], segs=4)
            b.cyl(P(x0 + 0.8, 0, zz), P(x0, 2.2, zz), 0.04, 0.04, M["dark"], segs=4)
        b.cyl(P(x0, 2.2, z0), P(x0, 2.2, z1), 0.04, 0.04, M["dark"], segs=4)
    return b.build("YardBuildings_nocol", coll)


def gable(b, x0, x1, y0, y1, z0, z1, m=None):
    """Двускатная крыша под снегом, конёк вдоль z."""
    m = m or M["snow"]
    xm = (x0 + x1) / 2
    b.gquad([(x0, y0, z1), (x0, y0, z0), (xm, y1, z0), (xm, y1, z1)][::-1], [(0, 0), (1, 0), (1, 1), (0, 1)], m)
    b.gquad([(x1, y0, z0), (x1, y0, z1), (xm, y1, z1), (xm, y1, z0)][::-1], [(0, 0), (1, 0), (1, 1), (0, 1)], m)
    b.gquad([(x0, y0, z1), (x1, y0, z1), (xm, y1, z1), (xm, y1, z1)], [(0, 0), (1, 0), (0.5, 1), (0.5, 1)], M["plaster"])
    b.gquad([(x1, y0, z0), (x0, y0, z0), (xm, y1, z0), (xm, y1, z0)], [(0, 0), (1, 0), (0.5, 1), (0.5, 1)], M["plaster"])


def warehouses(coll):
    """Склады с белыми крышами за двором (средний план справа) и бетонный забор перед ними."""
    b = B()
    sheds = [(60, 110, -48, -36, 6.0), (70, 125, -70, -56, 7.0), (95, 150, -95, -80, 5.5), (55, 85, -88, -76, 4.5),
             (112, 160, -60, -50, 6.5)]
    for (x0, x1, z0, z1, h) in sheds:
        b.cur = (0.95, 0.95, 0.97)
        walls_box(b, x0, x1, 0, h, z0, z1, M["white"], (4.0, h), M["snow"])
        # синяя полоса под крышей (как на фото)
        b.cur = (0.25, 0.42, 0.75)
        b.gbox(x0 - 0.02, x1 + 0.02, h - 0.9, h - 0.3, z0 - 0.02, z1 + 0.02,
               {"+x": M["paint"], "-x": M["paint"], "+z": M["paint"], "-z": M["paint"]})
        # окна-полосы и ворота
        for k in range(int((x1 - x0) / 9)):
            xx = x0 + 4 + k * 9
            b.cur = (1, 1, 1)
            facade_window_z(b, xx, z1 + 0.03, 1.6, "lit" if (k * 7 + int(x0)) % 5 == 0 else "dark")
    b.cur = (0.8, 0.8, 0.8)
    b.gbox(55.0, 135.0, 0, 2.2, -34.2, -34.0, {"+z": M["fence"], "-z": M["fence"], "up": M["snow"]}, (2.0, 2.2))
    return b.build("Warehouses_nocol", coll)


def facade_window_z(b, xc, z, y0, kind):
    """Окно атласа на стене, смотрящей в +z."""
    x0, x1 = xc - WIN_W / 2, xc + WIN_W / 2
    b.gquad([(x0, y0, z), (x1, y0, z), (x1, y0 + WIN_H * 0.8, z), (x0, y0 + WIN_H * 0.8, z)], win_uv(kind), M["win"])


# ------------------------------------------------------------------ высотки вокруг двора
# (x0, x1, z0, z1, этажей, фасад, к камере смотрит, оттенок, красные «шапки»)
BLOCKS = [
    (15, 140, -205, -193, 16, "facade", "+z", (1.0, 0.8, 0.72), False),
    (150, 262, -228, -216, 16, "facade_b", "+z", (1.0, 0.72, 0.58), False),
    (60, 118, -152, -140, 10, "facade_c", "+z", (1.0, 0.88, 0.72), True),
    (140, 152, -170, -112, 18, "facade", "-x", (0.98, 0.66, 0.6), False),
    (176, 190, -165, -100, 22, "facade_b", "-x", (0.95, 0.7, 0.62), False),
    (-90, 10, -262, -250, 14, "facade_b", "+z", (0.95, 0.8, 0.75), False),
    (-120, 420, -340, -328, 14, "facade", "+z", (0.85, 0.72, 0.72), False),
    (270, 330, -190, -150, 16, "facade_c", "-x", (1.0, 0.78, 0.66), False),
]
TILE = (22.4, 25.2)                # facade_*: 7 окон × 9 этажей


def blocks(coll):
    b = B()
    for (x0, x1, z0, z1, fl, fac, face, tint, caps) in BLOCKS:
        h = PLINTH + fl * FLOOR_H
        b.cur = tint
        su, sv = TILE
        m = M[fac]
        # фасад к двору — текстура с окнами (U — по фасаду, V — по этажам), остальные стены — штукатурка
        side_tint = (tint[0] * 0.6, tint[1] * 0.6, tint[2] * 0.6)
        faces = {k: M["plaster"] for k in ("+x", "-x", "+z", "-z")}
        b.cur = side_tint
        b.gbox(x0, x1, 0, h, z0, z1, {k: v for k, v in faces.items() if k != face}, (6.0, 6.0))
        b.cur = tint
        if face == "+z":
            b.gquad([(x0, PLINTH, z1), (x1, PLINTH, z1), (x1, h, z1), (x0, h, z1)],
                    [(0, 0), ((x1 - x0) / su, 0), ((x1 - x0) / su, (h - PLINTH) / sv), (0, (h - PLINTH) / sv)], m)
            b.cur = (0.3, 0.29, 0.29)
            b.gquad([(x0, 0, z1), (x1, 0, z1), (x1, PLINTH, z1), (x0, PLINTH, z1)], [(0, 0), (1, 0), (1, 0.1), (0, 0.1)], M["plaster"])
        else:
            b.gquad([(x0, PLINTH, z1), (x0, PLINTH, z0), (x0, h, z0), (x0, h, z1)],
                    [(0, 0), ((z1 - z0) / su, 0), ((z1 - z0) / su, (h - PLINTH) / sv), (0, (h - PLINTH) / sv)], m)
            b.cur = (0.3, 0.29, 0.29)
            b.gquad([(x0, 0, z1), (x0, 0, z0), (x0, PLINTH, z0), (x0, PLINTH, z1)], [(0, 0), (1, 0), (1, 0.1), (0, 0.1)], M["plaster"])
        b.cur = (1, 1, 1)
        b.gbox(x0, x1, h, h + 0.4, z0, z1, {"up": M["snow"], "+x": M["snow"], "-x": M["snow"], "+z": M["snow"], "-z": M["snow"]}, (6.0, 6.0))
        if caps:
            # красные «шапки» над лестничными клетками (дом с красной крышей на фото)
            n = int((x1 - x0) / 9)
            for k in range(n):
                cx = x0 + 4.5 + k * 9
                b.cur = (0.7, 0.12, 0.1)
                gable(b, cx - 3.6, cx + 3.6, h + 0.4, h + 2.2, z1 - 3.0, z1 + 0.2, m=M["paint"])
                b.cur = (1, 1, 1)
                gable(b, cx - 3.5, cx + 3.5, h + 0.45, h + 2.25, z1 - 2.9, z1 + 0.1)
    return b.build("Blocks_nocol", coll)


def lamps(coll):
    """Фонари: вдоль дальней улицы (оранжевые точки у основания домов) и пара во дворе."""
    b = B()
    pts = [(x, -182.0) for x in range(-20, 280, 28)] + [(x, -134.0) for x in range(20, 140, 30)] + \
          [(12.5, -14.0), (12.5, -52.0), (40.0, -40.0), (66.0, -26.0)]
    for (x, z) in pts:
        hgt = 8.0 if z < -100 else 6.0
        b.cur = (1, 1, 1)
        b.cyl(P(x, 0, z), P(x, hgt, z), 0.08, 0.06, M["dark"], segs=5)
        b.cyl(P(x, hgt, z), P(x + 0.9, hgt + 0.1, z), 0.04, 0.04, M["dark"], segs=4)
        b.gbox(x + 0.6, x + 1.2, hgt - 0.12, hgt + 0.05, z - 0.15, z + 0.15,
               {"down": M["lamp_o"], "up": M["dark"], "+x": M["dark"], "-x": M["dark"], "+z": M["dark"], "-z": M["dark"]})
        LIGHTS.append({"kind": "street", "pos": [x + 0.9, hgt - 0.3, z], "color": [1.0, 0.55, 0.22], "energy": 4.0,
                       "range": 18.0})
    return b.build("Lamps_nocol", coll)


# ------------------------------------------------------------------ сборка
def main():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    for ob in list(sc.collection.all_objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(sc.collection.children):
        bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes):                     # меши прошлой сборки, иначе имена получат «.001»
        if me.users == 0:
            bpy.data.meshes.remove(me)
    coll = bpy.data.collections.new("MenuYard")
    sc.collection.children.link(coll)
    materials()
    LIGHTS.clear()
    obs = [home(coll), my_window(coll), room(coll), ground(coll), cars(coll), trees(coll), yard_buildings(coll),
           warehouses(coll), blocks(coll), lamps(coll)]
    stats = {ob.name: len(ob.data.polygons) for ob in obs}
    os.makedirs(OUT_DIR, exist_ok=True)
    if bpy.context.window:
        bpy.context.window.scene = sc
    for ob in bpy.data.objects:
        ob.select_set(False)
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, use_active_scene=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True,
                              export_vertex_color='ACTIVE', export_animations=False)
    data = {"spot": list(SPOT), "window": {"open_z": list(OPEN_Z), "open_y": list(OPEN_Y), "frame_x": FRAME_X,
                                           "wall_t": WALL_T, "floor_y": YB},
            "lights": LIGHTS}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return {"polys": stats, "total": sum(stats.values()), "lights": len(LIGHTS)}


result = main()
print(result)
