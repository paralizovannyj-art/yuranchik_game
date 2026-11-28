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
BAYS_Z = (13.5, -67.5)             # фасад дома Юрчика от … до (z); середины клеток — через 3 м от z = 0 (окно Юрчика)
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

# план двора по спутнику и видео из окна — общий с menu_yard_textures.py
PL = {"__name__": "menu_plan"}
exec(open(os.path.join(HERE, "menu_yard_plan.py"), encoding="utf-8").read(), PL)
TOWER_Z = -43.5                    # западнее — 16-этажная башня того же дома (спутник)
TOWER_FLOORS = 16

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
    M["fac_cream"] = mat("MenuFacCream", "menu_fac_cream", "menu_fac_cream_emission")
    M["fac_ochre"] = mat("MenuFacOchre", "menu_fac_ochre", "menu_fac_ochre_emission")
    M["fac_brick"] = mat("MenuFacBrick", "menu_fac_brick", "menu_fac_brick_emission")
    M["corr"] = two_sided(mat("MenuCorrugated", "eb_corrugated", rough=0.6))
    M["white"] = mat("MenuWhiteMetal", "eb_white", rough=0.6)
    M["fence"] = mat("MenuFenceConcrete", "fence_concrete")
    M["parquet"] = mat("MenuParquet", "parquet")
    M["wallpaper"] = mat("MenuWallpaper", "wallpaper")
    M["bark"] = two_sided(mat("MenuBark", "menu_bark"))
    M["twigs"] = amat("MenuTwigs", "menu_twigs")
    M["tsnow"] = two_sided(mat("MenuTreeSnow", "snow"))
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
    for f in range(TOWER_FLOORS):
        y0 = PLINTH + f * FLOOR_H
        for i in range(nb):
            za = BAYS_Z[0] - i * BAY
            zb = za - BAY
            zc = (za + zb) / 2
            if f >= (TOWER_FLOORS if zc < TOWER_Z else FLOORS):
                continue
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
    ttop = PLINTH + TOWER_FLOORS * FLOOR_H
    b.cur = (0.45, 0.44, 0.44)
    b.gbox(-0.3, 0.05, top, top + 0.9, TOWER_Z, BAYS_Z[0], {"+x": M["plaster"], "up": M["snow"]}, (4.0, 4.0))
    b.gbox(-0.3, 0.05, ttop, ttop + 0.9, BAYS_Z[1], TOWER_Z, {"+x": M["plaster"], "up": M["snow"]}, (4.0, 4.0))
    # торец башни над крышей дома (виден на фоне неба)
    b.gquad([(-12.0, top, TOWER_Z), (0.0, top, TOWER_Z), (0.0, ttop + 0.9, TOWER_Z), (-12.0, ttop + 0.9, TOWER_Z)],
            [(0, 0), (3, 0), (3, 3), (0, 3)], M["plaster"])
    # кондиционер Юрчика справа от окна — крупный, с сосульками (главный кадр)
    ac_unit(b, 0.0, -1.55, YB + 1.5, icicles=True, w=0.82, h=0.56, d=0.3)
    # трубка от кондиционера вниз по стене и провод с крыши во двор
    b.cur = (1, 1, 1)
    b.cyl(P(0.04, YB + 1.5, -1.22), P(0.04, 0.6, -1.22), 0.014, 0.014, M["dark"], segs=5)
    wire = [P(0.06, top - 2.5, -7.0)]
    a, c = Vector((0.06, top - 2.5, -7.0)), Vector((78.0, 30.0, -30.0))
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
# Всё расставлено по плану menu_yard_plan.py (PL): спутник Google Earth + видео из окна Юрчика.
def ground(coll):
    b = B()
    x0, z0, sx, sz = PL["GX0"], PL["GZ0"], PL["GSX"], PL["GSZ"]
    b.cur = (1, 1, 1)
    # карта двора: u по x, v по z (v = 1 у z0 — верх картинки)
    b.gquad([(x0, 0, z0 + sz), (x0 + sx, 0, z0 + sz), (x0 + sx, 0, z0), (x0, 0, z0)],
            [(0, 0), (1, 0), (1, 1), (0, 1)], M["ground"])
    # вокруг — просто снег до горизонта (без нахлёста, чтобы не мерцало)
    far = 1500.0
    T = 8.0
    def q(xa, xb, za, zb):
        b.gquad([(xa, 0, zb), (xb, 0, zb), (xb, 0, za), (xa, 0, za)],
                [(xa / T, zb / T), (xb / T, zb / T), (xb / T, za / T), (xa / T, za / T)], M["snow"])
    q(-far, x0, -far, far)               # под домом и за ним
    q(x0 + sx, far, -far, far)           # дальше от дома
    q(x0, x0 + sx, -far, z0)             # за проспектом
    q(x0, x0 + sx, z0 + sz, far)         # за камерой
    return b.build("Ground_nocol", coll)


def car(b, x, z, yaw, color):
    """Машина под снегом: кузов, кабина, снежные шапки на капоте, крыше и багажнике. yaw = 0 — длиной вдоль x."""
    L, W = 4.2, 1.75
    ca, sa = math.cos(yaw), math.sin(yaw)
    def tr(px, py, pz):
        return (x + px * ca - pz * sa, py, z + px * sa + pz * ca)
    def obox(a0, a1, y0, y1, c0, c1, m_sides, m_top, col):
        pts = [tr(a0, y0, c0), tr(a1, y0, c0), tr(a1, y0, c1), tr(a0, y0, c1),
               tr(a0, y1, c0), tr(a1, y1, c0), tr(a1, y1, c1), tr(a0, y1, c1)]
        b.cur = col
        for f in [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            b.gquad([pts[i] for i in f], [(0, 0), (1, 0), (1, 1), (0, 1)], m_sides)
        b.cur = (1, 1, 1)
        b.gquad([pts[4], pts[5], pts[6], pts[7]][::-1], [(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)], m_top)
    obox(-L / 2, L / 2, 0.15, 0.78, -W / 2, W / 2, M["paint"], M["snow"], color)
    obox(-0.9, 1.1, 0.78, 1.3, -W / 2 + 0.12, W / 2 - 0.12, M["glass"], M["snow"], (1, 1, 1))
    obox(-0.85, 1.05, 1.3, 1.42, -W / 2 + 0.15, W / 2 - 0.15, M["snow"], M["snow"], (1, 1, 1))
    obox(-L / 2 + 0.05, -0.95, 0.78, 0.86, -W / 2 + 0.05, W / 2 - 0.05, M["snow"], M["snow"], (1, 1, 1))
    obox(1.15, L / 2 - 0.05, 0.78, 0.84, -W / 2 + 0.05, W / 2 - 0.05, M["snow"], M["snow"], (1, 1, 1))
    obox(-L / 2 + 0.3, L / 2 - 0.3, 0.0, 0.15, -W / 2 + 0.05, W / 2 - 0.05, M["dark"], M["dark"], (1, 1, 1))


CAR_COLORS = [(0.12, 0.12, 0.14), (0.85, 0.85, 0.87), (0.15, 0.2, 0.35), (0.45, 0.1, 0.1), (0.55, 0.55, 0.58),
              (0.92, 0.92, 0.92), (0.9, 0.9, 0.92), (0.2, 0.22, 0.25)]


def cars(coll):
    b = B()
    r = random.Random(5)
    col = lambda: r.choice(CAR_COLORS)
    # карманы у дома (видео 21–23 с: белые, тёмные, синяя) — носом к проезду
    x0, x1, z0, z1 = PL["PARKING"]
    z = z1 - 1.3
    while z > z0 + 1.2:
        if r.random() < 0.82:
            car(b, (x0 + x1) / 2 + 0.2, z, math.radians(r.uniform(-3, 3) + (180 if r.random() < 0.3 else 0)), col())
        z -= 2.6
    # пара машин у края проезда напротив площадки (видео 3 с)
    for zz in (18.0, 24.5, 31.0):
        car(b, 9.3, zz, math.radians(90 + r.uniform(-2, 2)), col())
    # вдоль дома с красными шапками
    z = -47.0
    while z < 55:
        if r.random() < 0.55:
            car(b, 75.0, z, math.radians(90 + r.uniform(-3, 3)), col())
        z += r.uniform(4.6, 7.0)
    # стоянка рынка (видео 0, 5–6 с): ряды по 2.6 м
    mx0, mx1, mz0, mz1 = PL["MARKET_PARKING"]
    for xr in (mx0 + 3.0, mx0 + 8.2, mx0 + 18.0, mx0 + 23.2):
        z = mz0 + 1.5
        while z < mz1 - 1.5:
            if r.random() < 0.55:
                car(b, xr, z, math.radians(r.uniform(-4, 4)), col())
            z += 2.6
    # проспект: у бордюров стоят, посередине едут
    a0, a1 = PL["AVENUE_Z"]
    for zz, p in ((a1 - 1.4, 0.45), (a0 + 1.4, 0.45), (a1 - 6.0, 0.18), (a1 - 10.0, 0.14), (a0 + 6.0, 0.18), (a0 + 10.0, 0.14)):
        x = -70.0
        while x < 235:
            if r.random() < p:
                car(b, x, zz, math.radians(r.uniform(-1.5, 1.5)), col())
            x += r.uniform(5.0, 8.0)
    # улица у 16-этажек справа (видео 12–13 с)
    x = 18.0
    while x < 150:
        if r.random() < 0.6:
            car(b, x, 79.5, math.radians(r.uniform(-2, 2)), col())
        x += r.uniform(4.8, 7.5)
    return b.build("Cars_nocol", coll)


# ------------------------------------------------------------------ деревья
# Голые зимние деревья (орех, клён, акация; у дома напротив — тополя) настоящими ветками: ствол и ветки —
# гранёные трубки с корой, на верхней стороне каждой ветки — снежный валик (метель завалила снегом все
# ветки), ствол с наветренной стороны залеплен снегом, у комля — сугроб. Концы веток — пучки тонких
# веточек со снегом (карточки menu_twigs). Дальние деревья (в дымке) проще: без веток второго порядка.
WIND = Vector((0.5, 0.0, 0.85)).normalized()     # откуда мела метель: с этой стороны стволы залеплены снегом
CAM_XZ = (2.5, 2.4)                              # камера меню — чтобы упростить дальние деревья
RING = 5


def _frame(d):
    s = d.cross(Vector((0.0, 1.0, 0.0)))
    if s.length < 1e-3:
        s = Vector((1.0, 0.0, 0.0))
    s.normalize()
    return s, s.cross(d).normalized()


def _tube(b, pts, radii, v0=0.0):
    """Трубка по точкам (Godot): грани коры; смотрящие вверх и залепленные метелью — снег.
    Сверху на каждом не слишком крутом участке — снежный валик (две наклонные грани)."""
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        sd, up = _frame(d)
        ring = []
        for k in range(RING):
            n = sd * math.cos(2 * math.pi * k / RING) + up * math.sin(2 * math.pi * k / RING)
            ring.append((p + n * radii[i], n))
        rings.append(ring)
    vs = [v0]
    for i in range(1, len(pts)):
        vs.append(vs[-1] + (pts[i] - pts[i - 1]).length / 2.4)
    for i in range(len(pts) - 1):
        for k in range(RING):
            a, c = rings[i][k], rings[i][(k + 1) % RING]
            e, f = rings[i + 1][(k + 1) % RING], rings[i + 1][k]
            nrm = (a[1] + c[1] + e[1] + f[1]).normalized()
            snowy = nrm.y > 0.4 or nrm.dot(WIND) > 0.65
            b.cur = (1, 1, 1) if snowy else (0.92, 0.9, 0.88)
            u0, u1 = k / RING, (k + 1) / RING
            b.gquad([tuple(a[0]), tuple(c[0]), tuple(e[0]), tuple(f[0])],
                    [(u0, vs[i]), (u1, vs[i]), (u1, vs[i + 1]), (u0, vs[i + 1])],
                    M["tsnow"] if snowy else M["bark"])
        # снежный валик сверху (на крутых участках снег не держится)
        flat_k = 1.0 - abs((pts[i + 1] - pts[i]).normalized().y)
        if flat_k < 0.25:
            continue
        b.cur = (1, 1, 1)
        q = []
        for j in (i, i + 1):
            dd = (pts[min(j + 1, len(pts) - 1)] - pts[max(j - 1, 0)]).normalized()
            side = dd.cross(Vector((0.0, 1.0, 0.0)))
            side = side.normalized() if side.length > 1e-3 else Vector((1.0, 0.0, 0.0))
            r = radii[j]
            t = min(0.2, max(0.05, r * 1.8)) * flat_k
            c0 = pts[j] + Vector((0.0, r * 0.35, 0.0))
            q.append((c0 + side * r * 1.05, pts[j] + Vector((0.0, r + t, 0.0)), c0 - side * r * 1.05))
        for (m0, m1) in ((0, 1), (1, 2)):
            b.gquad([tuple(q[0][m0]), tuple(q[1][m0]), tuple(q[1][m1]), tuple(q[0][m1])],
                    [(0, 0), (1, 0), (1, 0.3), (0, 0.3)], M["tsnow"])


def _twig_card(b, tip, d, size, r):
    """Пучок веточек со снегом на конце ветки: две скрещённые карточки вдоль ветки (чуть вверх)."""
    d = (d.normalized() + Vector((0.0, 0.6, 0.0))).normalized()
    s1, s2 = _frame(d)
    rot = r.uniform(0, math.pi)
    p0 = tip - d * size * 0.12
    b.cur = (1, 1, 1)
    for k in range(2):
        a = rot + k * math.pi / 2
        sd = s1 * math.cos(a) + s2 * math.sin(a)
        b.gquad([tuple(p0 - sd * size / 2), tuple(p0 + sd * size / 2), tuple(p0 + sd * size / 2 + d * size),
                 tuple(p0 - sd * size / 2 + d * size)], [(0, 0), (1, 0), (1, 1), (0, 1)], M["twigs"])


def _rot(v, axis, ang):
    from mathutils import Matrix
    return Matrix.Rotation(ang, 3, axis.normalized()) @ v


def _branch(b, p, d, L, rad, depth, r, cards):
    """Ветка из 3 участков, слегка изгибается вверх и случайно; дети — на 40–90 % длины."""
    pts, radii = [p.copy()], [rad]
    cur, dd = p.copy(), d.normalized()
    for i in range(3):
        dd = (dd + Vector((r.gauss(0, 0.18), 0.12 + r.gauss(0, 0.08), r.gauss(0, 0.18)))).normalized()
        cur = cur + dd * (L / 3)
        pts.append(cur.copy())
        radii.append(rad * (1 - 0.55 * (i + 1) / 3))
    _tube(b, pts, radii, r.uniform(0, 1))
    if depth > 0:
        for _ in range(r.choice((2, 3))):
            t = r.uniform(0.4, 0.9)
            k = min(2, int(t * 3))
            base = pts[k].lerp(pts[k + 1], t * 3 - k)
            axis = dd.cross(Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))))
            if axis.length < 1e-3:
                continue
            cd = _rot(dd, axis, math.radians(r.uniform(25, 55)))
            _branch(b, base, cd, L * r.uniform(0.45, 0.65), rad * 0.55, depth - 1, r, cards)
    if depth == 0 or cards:
        _twig_card(b, pts[-1], dd, max(1.4, L * 1.0), r)


def tree3d(b, x, z, h, poplar, r):
    far = math.hypot(x - CAM_XZ[0], z - CAM_XZ[1]) > 90.0
    base = Vector((x, 0.0, z))
    R0 = h * (0.018 if poplar else 0.024)
    lean = Vector((r.gauss(0, 0.05), 1.0, r.gauss(0, 0.05))).normalized()
    tl = h * (0.92 if poplar else 0.42)
    trunk = [base + lean * tl * t + (Vector((r.gauss(0, 0.04), 0, r.gauss(0, 0.04))) if t > 0 else Vector())
             for t in (0, 0.35, 0.7, 1.0)]
    _tube(b, trunk, [R0 * 1.15, R0, R0 * 0.85, R0 * (0.4 if poplar else 0.7)])
    top = trunk[-1]
    if poplar:
        for _ in range(5 if far else 11):
            t = r.uniform(0.2, 0.95)
            p = base + lean * tl * t
            a = r.uniform(0, 2 * math.pi)
            d = Vector((math.cos(a) * 0.4, 1.0, math.sin(a) * 0.4))
            _branch(b, p, d, h * 0.24 * (1.15 - abs(t - 0.5)), R0 * 0.35, 0, r, True)
    else:
        n = r.choice((4, 5, 5, 6))
        a0 = r.uniform(0, 2 * math.pi)
        for i in range(n):
            a = a0 + i * 2 * math.pi / n + r.gauss(0, 0.25)
            e = math.radians(r.uniform(28, 58))
            p = base + lean * tl * r.uniform(0.75, 1.0)
            d = Vector((math.cos(a) * math.cos(e), math.sin(e), math.sin(a) * math.cos(e)))
            _branch(b, p, d, h * r.uniform(0.36, 0.5), R0 * 0.62, 0 if far else 1, r, far)
        _branch(b, top, lean + Vector((r.gauss(0, 0.15), 0, r.gauss(0, 0.15))), h * 0.48, R0 * 0.55,
                0 if far else 1, r, far)
    # сугроб у комля, с подветренной стороны длиннее
    b.cur = (1, 1, 1)
    rr = R0 * 7
    apex = base + Vector((0.0, R0 * 1.8, 0.0))

    def rim(a):
        v = Vector((math.cos(a), 0.0, math.sin(a)))
        return base + v * rr - WIND * rr * 0.8 * max(0.0, v.dot(-WIND)) + Vector((0.0, 0.02, 0.0))
    for k in range(6):
        a1, a2 = 2 * math.pi * k / 6, 2 * math.pi * (k + 1) / 6
        b.gquad([tuple(rim(a2)), tuple(rim(a1)), tuple(apex), tuple(apex)], [(0, 0), (1, 0), (0.5, 1), (0.5, 1)],
                M["tsnow"])


def _blocked():
    """Прямоугольники (x0, x1, z0, z1), где деревьям не место: дома, асфальт, стоянки."""
    bx = [PL["BOX_MAIN"][:4], PL["BOX_ANNEX"][:4], PL["PINK_FENCE"], PL["WHITE_HUT"], PL["RED_CAP"][:4],
          PL["MARKET_HALL"][:4], PL["MARKET_PARKING"], (-80, 240, PL["AVENUE_Z"][0] - 5, PL["AVENUE_Z"][1] + 4),
          PL["STRIP"][:4], (PL["WALK_X"][0], PL["DRIVE_X"][1], -70, 60), PL["PARKING"],
          PL["PLAYGROUND"], (68, 77, -55, 59), (-28, 10.4, -84, -66), (-28, -20, -84, -30)]
    bx += [g for g in PL["GARAGES"]] + [w[:4] for w in PL["MARKET_WINGS"]] + [e[:4] for e in PL["EAST_ROW"]]
    out = []
    for (a, c, e, f) in bx:
        out.append((min(a, c) - 1.0, max(a, c) + 1.0, min(e, f) - 1.0, max(e, f) + 1.0))
    return out


def trees(coll):
    b = B()
    r = random.Random(11)
    spots = []                                   # (x, z, высота, тополь)
    def scatter(x0, x1, z0, z1, n, h0, h1, pop=0.0):
        for _ in range(n):
            spots.append((r.uniform(x0, x1), r.uniform(z0, z1), r.uniform(h0, h1), r.random() < pop))
    # клумбы площадки: деревья в них теперь строит build_playground.py (общая модель с локацией, YUR-49); здесь
    # прежние четыре только «растут вхолостую» — чтобы случайные числа и все остальные деревья кадра не сдвинулись
    for (cx, cz) in OLD_PLANTERS:
        spots.append((cx, cz, r.uniform(6.5, 8.5), False))
    # голые деревья между проездом и первой тропинкой — передний план кадра из окна (видео 1–3 с)
    scatter(16, 30, -64, 34, 18, 6, 11, 0.08)
    scatter(11, 17, 14, 40, 6, 6, 9)
    # большая группа у западного края двора (спутник E −52…−33, N 24…43)
    scatter(13, 27, -47, -31, 8, 8, 12)
    # берёзки на газоне у стены
    for z in (-30.0, -18.0, 22.0, 36.0):
        spots.append((1.5, z + r.uniform(-2, 2), r.uniform(7, 9), False))
    # поле: одиночное большое дерево у забора и редкие кусты/деревца
    spots.append((LONE_TREE[0], LONE_TREE[1], 12.5, False))
    zs = PL["Z_SHIFT"]
    for p in ((70.0, -123.0, 7.0), (36.0, -47.0, 5.5), (53.0, -26.0, 6.5), (55.0, -48.0, 5.0), (32.0, -70.0, 6.0),
              (46.0, -64.0, 4.5), (64.0, -18.0, 7.0), (62.0, 8.0, 8.0)):
        spots.append((p[0], p[1] + zs, p[2], False))
    # вдоль бетонного забора — кусты и бурьян
    (fx0, fz0), (fx1, fz1) = PL["FIELD_FENCE"]
    for k in range(14):
        t = r.random()
        spots.append((fx0 + (fx1 - fx0) * t, fz0 + (fz1 - fz0) * t + r.uniform(1.5, 3.5), r.uniform(2.5, 5.0), False))
    # у дома с красными шапками — ряд деревьев перед фасадом
    scatter(60, 67, -29, 53, 12, 7, 11, 0.1)
    # у розового домика и гаражей: тополя и клёны
    for p in ((30.0, 44.0, 9.0, False), (51.0, 30.0, 13.0, True), (52.0, 40.0, 11.0, False), (28.0, 24.0, 8.0, False),
              (46.0, 44.0, 9.0, False), (34.0, 18.0, 7.5, False)):
        spots.append((p[0], p[1] + zs, p[2], p[3]))
    # пустырь за забором — редкие деревья, вдоль полосы складов и проспекта — ряды
    scatter(-40, 110, -163, -126, 8, 5, 9)
    x = -70.0
    while x < 235:
        spots.append((x + r.uniform(-2, 2), PL["AVENUE_Z"][1] + 2.0, r.uniform(7, 10), r.random() < 0.15))
        spots.append((x + r.uniform(-2, 2), PL["AVENUE_Z"][0] - 2.5, r.uniform(7, 10), r.random() < 0.15))
        x += r.uniform(8, 12)
    # между рынком и домом напротив, за домом напротив
    scatter(96, 136, -49, -5, 8, 7, 11)
    scatter(96, 160, -5, 75, 14, 8, 12, 0.2)
    blocked = _blocked()
    ghost = B()
    for (x, z, h, pop) in spots:
        if (x, z) in OLD_PLANTERS:
            tree3d(ghost, x, z, h, pop, r)
            continue
        if any(a <= x <= c and e <= z <= f for (a, c, e, f) in blocked):
            continue
        tree3d(b, x, z, h * (1.3 if pop else 1.0), pop, r)
    return b.build("Trees_nocol", coll)


LONE_TREE = PL["LONE_TREE"]
OLD_PLANTERS = [(13.5, -6.5), (13.5, 2.0), (19.5, -6.5), (22.0, 9.5)]   # клумбы до YUR-49 (только для trees())


def walls_box(b, x0, x1, y0, y1, z0, z1, m_wall, wall_scale, m_roof=None, sides=("+x", "-x", "+z", "-z")):
    f = {k: m_wall for k in sides}
    b.gbox(x0, x1, y0, y1, z0, z1, f, wall_scale)
    if m_roof:
        b.cur, keep = (1, 1, 1), b.cur
        b.gbox(x0 - 0.15, x1 + 0.15, y1, y1 + 0.18, z0 - 0.15, z1 + 0.15,
               {"up": m_roof, "+x": m_roof, "-x": m_roof, "+z": m_roof, "-z": m_roof}, (4.0, 4.0))
        b.cur = keep


def gable(b, x0, x1, y0, y1, z0, z1, m=None, ends=None):
    """Двускатная крыша, конёк вдоль z; ends — материал фронтонов (по умолчанию штукатурка)."""
    m = m or M["snow"]
    e = ends or M["plaster"]
    xm = (x0 + x1) / 2
    b.gquad([(x0, y0, z1), (x0, y0, z0), (xm, y1, z0), (xm, y1, z1)][::-1], [(0, 0), (1, 0), (1, 1), (0, 1)], m)
    b.gquad([(x1, y0, z0), (x1, y0, z1), (xm, y1, z1), (xm, y1, z0)][::-1], [(0, 0), (1, 0), (1, 1), (0, 1)], m)
    b.gquad([(x0, y0, z1), (x1, y0, z1), (xm, y1, z1), (xm, y1, z1)], [(0, 0), (1, 0), (0.5, 1), (0.5, 1)], e)
    b.gquad([(x1, y0, z0), (x0, y0, z0), (xm, y1, z0), (xm, y1, z0)], [(0, 0), (1, 0), (0.5, 1), (0.5, 1)], e)


def shed_roof_x(b, x0, x1, y0, y1, z0, z1, m):
    """Односкатная крыша: высокий край у x0, низкий у x1."""
    b.gquad([(x1, y1, z0), (x1, y1, z1), (x0, y0, z1), (x0, y0, z0)][::-1], [(0, 0), (1, 0), (1, 1), (0, 1)], m)


def yard_buildings(coll):
    b = B()
    # --- бетонная коробка в граффити (подстанция): основной блок + пристройка-загородка без крыши
    x0, x1, z0, z1, h = PL["BOX_MAIN"]
    b.cur = (1.0, 0.98, 0.96)
    walls_box(b, x0, x1, 0, h, z0, z1, M["garage"], (8.0, 4.0), M["snow"])
    # парапет по краю крыши и две вытяжки
    b.cur = (0.85, 0.84, 0.82)
    for (a, c, e, f) in ((x0, x1, z0, z0 + 0.25), (x0, x1, z1 - 0.25, z1), (x0, x0 + 0.25, z0, z1), (x1 - 0.25, x1, z0, z1)):
        b.gbox(a, c, h, h + 0.35, e, f, {"+x": M["garage"], "-x": M["garage"], "+z": M["garage"], "-z": M["garage"],
                                         "up": M["snow"]}, (8.0, 4.0))
    for (vx, vz) in ((x0 + 3.0, z0 + 4.0), (x0 + 5.5, z1 - 3.5)):
        b.cur = (0.45, 0.45, 0.45)
        b.gbox(vx - 0.35, vx + 0.35, h + 0.18, h + 0.75, vz - 0.35, vz + 0.35,
               {"+x": M["dark"], "-x": M["dark"], "+z": M["dark"], "-z": M["dark"], "up": M["snow"]})
    # тёмные окошки-продухи под крышей и дверь на стороне к дому Юрчика (−x)
    b.cur = (1, 1, 1)
    for k in range(4):
        zc = z0 + 1.8 + k * 2.8
        b.gbox(x0 - 0.03, x0, h - 1.3, h - 0.6, zc - 0.5, zc + 0.5, {"-x": M["dark"]})
    b.gbox(x0 - 0.03, x0, 0, 2.2, z1 - 4.0, z1 - 2.8, {"-x": M["dark"]})
    # пристройка: четыре стены без крыши, внутри снег и хлам
    a0, a1, c0, c1, hh = PL["BOX_ANNEX"]
    b.cur = (0.95, 0.93, 0.9)
    t = 0.3
    for (p, q, e, f) in ((a0, a1, c1 - t, c1), (a0, a0 + t, c0, c1), (a0, a1, c0, c0 + t)):
        walls_box(b, p, q, 0, hh, e, f, M["garage"], (8.0, 4.0), M["snow"])
    b.cur = (1, 1, 1)
    b.gbox(a0 + t, a1, 0.0, 0.6, c0 + t, c1 - t, {"up": M["snow"]}, (2.0, 2.0))
    b.cur = (0.5, 0.45, 0.4)
    b.gbox(a0 + 1.5, a0 + 3.0, 0.6, 1.2, c0 + 2.0, c0 + 3.2, {"+x": M["dark"], "-x": M["dark"], "+z": M["dark"],
                                                                 "-z": M["dark"], "up": M["snow"]})

    # --- забор из бетонных плит в граффити поперёк поля
    (fx0, fz0), (fx1, fz1) = PL["FIELD_FENCE"]
    n = int(math.hypot(fx1 - fx0, fz1 - fz0) / 3.0)
    b.cur = (0.92, 0.9, 0.88)
    for k in range(n):
        if k in (9, 10, 27):                                  # проломы
            continue
        pa = (fx0 + (fx1 - fx0) * k / n, fz0 + (fz1 - fz0) * k / n)
        pb = (fx0 + (fx1 - fx0) * (k + 1) / n, fz0 + (fz1 - fz0) * (k + 1) / n)
        hgt = 2.2 + (0.1 if k % 3 == 0 else 0.0)
        for side in (1, -1):
            dz = 0.09 * side
            pts = [(pa[0], 0, pa[1] + dz), (pb[0], 0, pb[1] + dz), (pb[0], hgt, pb[1] + dz), (pa[0], hgt, pa[1] + dz)]
            u0 = (k % 8) / 8
            b.gquad(pts if side > 0 else pts[::-1], [(u0, 0), (u0 + 0.375, 0), (u0 + 0.375, 0.55), (u0, 0.55)], M["garage"])
        b.cur, keep = (1, 1, 1), b.cur
        b.gquad([(pa[0], hgt + 0.06, pa[1] - 0.12), (pb[0], hgt + 0.06, pb[1] - 0.12), (pb[0], hgt + 0.06, pb[1] + 0.12),
                 (pa[0], hgt + 0.06, pa[1] + 0.12)][::-1], [(0, 0), (1, 0), (1, 0.1), (0, 0.1)], M["snow"])
        b.cur = keep

    # --- розовый домик с оранжевой крышей за дощатым забором (видео 9–15 с)
    x0, x1, z0, z1 = PL["PINK_HOUSE"]
    b.cur = (0.98, 0.7, 0.7)
    walls_box(b, x0, x1, 0, 3.0, z0, z1, M["plaster"], (3.0, 3.0))
    b.cur = (0.95, 0.45, 0.25)
    gable(b, x0 - 0.5, x1 + 0.5, 3.0, 4.6, z0 + 3.5, z1 + 0.5, m=M["paint"], ends=M["plaster"])
    b.cur = (1, 1, 1)
    gable(b, x0 + 0.6, x1 - 0.6, 3.75, 4.66, z0 + 3.5, z1 + 0.5)             # снег на коньке
    b.cur = (0.8, 0.8, 0.82)                                                  # плоская часть крыши со стороны −z
    b.gbox(x0 - 0.3, x1 + 0.3, 3.0, 3.2, z0 - 0.3, z0 + 3.5, {"+x": M["plaster"], "-x": M["plaster"], "-z": M["plaster"],
                                                              "up": M["snow"]})
    b.cur = (0.95, 0.95, 0.95)                                                # белая пристройка с гофрой
    walls_box(b, x0 - 3.0, x0, 0, 2.4, z0 + 1.0, z0 + 6.0, M["plaster"], (3.0, 3.0), M["snow"])
    b.cur = (1, 1, 1)
    for (zc, kind) in ((z0 + 5.5, "lit"), (z1 - 2.5, "curtain")):
        facade_window(b, x0, zc, 0.9, kind, face=-1)
    # тарелка-антенна на крыше
    b.cyl(P(x0 + 1.0, 4.0, z1 - 1.0), P(x0 + 1.0, 5.1, z1 - 1.0), 0.03, 0.03, M["dark"], segs=4)
    b.cyl(P(x0 + 0.85, 5.15, z1 - 1.0), P(x0 + 1.15, 5.15, z1 - 1.0), 0.42, 0.42, M["paint"], segs=8)
    # дощатый забор
    fx0, fx1, fz0, fz1 = PL["PINK_FENCE"]
    b.cur = (0.42, 0.3, 0.24)
    for (a, c, e, f) in ((fx0, fx1, fz0, fz0 + 0.06), (fx0, fx1, fz1 - 0.06, fz1), (fx0, fx0 + 0.06, fz0, fz1),
                         (fx1 - 0.06, fx1, fz0, fz1)):
        b.gbox(a, c, 0, 2.0, e, f, {"+x": M["corr"], "-x": M["corr"], "+z": M["corr"], "-z": M["corr"]}, (4.0, 2.0))
        b.cur, keep = (1, 1, 1), b.cur
        b.gbox(a, c, 2.0, 2.06, e - 0.02, f + 0.02, {"up": M["snow"]}, (4.0, 4.0))
        b.cur = keep

    # --- белая будка в граффити с тёмной плоской крышей
    x0, x1, z0, z1 = PL["WHITE_HUT"]
    b.cur = (1.15, 1.15, 1.15)
    walls_box(b, x0, x1, 0, 3.0, z0, z1, M["garage"], (8.0, 4.0))
    b.cur = (0.25, 0.25, 0.27)
    b.gbox(x0 - 0.3, x1 + 0.3, 3.0, 3.25, z0 - 0.3, z1 + 0.3, {"+x": M["dark"], "-x": M["dark"], "+z": M["dark"],
                                                               "-z": M["dark"]})
    b.cur = (1, 1, 1)
    b.gbox(x0 - 0.3, x1 + 0.3, 3.25, 3.4, z0 - 0.3, z1 + 0.3, {"up": M["snow"]}, (4.0, 4.0))

    # --- гаражи с тёмными крышами за зелёным забором
    for (x0, x1, z0, z1) in PL["GARAGES"]:
        n = int((x1 - x0) / 3.5)
        for k in range(n):
            a = x0 + k * (x1 - x0) / n
            c = a + (x1 - x0) / n
            b.cur = (0.8 + 0.1 * (k % 3), 0.78 + 0.08 * (k % 2), 0.75)
            b.gbox(a, c - 0.05, 0, 2.5, z0, z1, {"+z": M["corr"], "-z": M["corr"], "+x": M["plaster"], "-x": M["plaster"]},
                   (2.0, 2.0))
        b.cur = (0.28, 0.24, 0.22)
        shed_roof_x(b, x0 - 0.2, x1 + 0.2, 2.7, 2.7, z0 - 0.3, z1 + 0.3, M["dark"])
        b.cur = (1, 1, 1)
        shed_roof_x(b, x0 - 0.2, x1 + 0.2, 2.74, 2.74, z0 - 0.1, z1 + 0.1, M["snow"])
    b.cur = (0.3, 0.55, 0.35)
    b.gbox(48.0, 94.0, 0, 2.0, 58.0, 58.06, {"+z": M["corr"], "-z": M["corr"]}, (8.0, 2.0))

    # --- у дома Юрчика: газон с низким зелёным заборчиком, бордюр, покрышки
    b.cur = (0.25, 0.5, 0.3)
    zA, zB = PL["DRIVE_Z"]
    for z in range(int(zB), int(zA), 2):
        b.cyl(P(LAWN_X1, 0, z), P(LAWN_X1, 0.55, z), 0.025, 0.025, M["paint"], segs=4)
    b.cyl(P(LAWN_X1, 0.5, zB), P(LAWN_X1, 0.5, zA), 0.02, 0.02, M["paint"], segs=4)
    b.cur = (0.75, 0.75, 0.75)
    x0, x1, z0, z1 = PL["PLAYGROUND"]
    # бордюр вдоль парковки; дальше, вдоль площадки, — свой у неё (build_playground.py)
    b.gbox(x0 - 0.15, x0, 0, 0.15, PL["PARKING"][2], z0 - 0.15, {"+x": M["plaster"], "-x": M["plaster"], "up": M["snow"]})
    rr = random.Random(3)
    for z in range(int(z1) + 2, int(z1) + 18, 3):
        b.cur = rr.choice([(0.85, 0.8, 0.2), (0.3, 0.6, 0.3), (0.9, 0.9, 0.3)])
        b.cyl(P(x0 + 0.6, 0, z), P(x0 + 0.6, 0.3, z), 0.38, 0.38, M["paint"], segs=8, caps=True)

    # детская площадка — отдельная общая модель меню и локации (build_playground.py, YUR-49)
    return b.build("YardBuildings_nocol", coll)


LAWN_X1 = PL["LAWN_X"][1]


def facade_window_z(b, xc, z, y0, kind):
    """Окно атласа на стене, смотрящей в +z."""
    x0, x1 = xc - WIN_W / 2, xc + WIN_W / 2
    b.gquad([(x0, y0, z), (x1, y0, z), (x1, y0 + WIN_H * 0.8, z), (x0, y0 + WIN_H * 0.8, z)], win_uv(kind), M["win"])


def market(coll):
    """Рынок «Сім'я» (белый корпус, крылья с синими крышами) и полоса низких магазинов вдоль проспекта."""
    b = B()
    blue = (0.22, 0.4, 0.78)
    x0, x1, z0, z1, h = PL["MARKET_HALL"]
    b.cur = (0.95, 0.95, 0.97)
    walls_box(b, x0, x1, 0, h, z0, z1, M["white"], (4.0, h), M["snow"])
    b.cur = blue
    b.gbox(x0 - 0.03, x1 + 0.03, h - 1.2, h - 0.5, z0 - 0.03, z1 + 0.03,
           {"+x": M["paint"], "-x": M["paint"], "+z": M["paint"], "-z": M["paint"]})
    for (a0, a1, c0, c1, hh) in PL["MARKET_WINGS"]:
        b.cur = (0.95, 0.95, 0.97)
        walls_box(b, a0, a1, 0, hh, c0, c1, M["white"], (4.0, hh))
        # синяя крыша скатом наружу, снег лежит пятнами — видна синяя кромка
        b.cur = blue
        b.gbox(a0 - 0.4, a1 + 0.4, hh, hh + 0.35, c0 - 0.4, c1 + 0.4,
               {"+x": M["paint"], "-x": M["paint"], "+z": M["paint"], "-z": M["paint"]})
        b.cur = (1, 1, 1)
        b.gbox(a0 - 0.3, a1 + 0.3, hh + 0.35, hh + 0.45, c0 - 0.3, c1 + 0.3, {"up": M["snow"]}, (4.0, 4.0))
        # витрины и ворота на стороне к двору (−x)
        rr = random.Random(int(a0 * 7 + c0))
        k = 0
        z = c0 + 3.0
        while z < c1 - 2.0:
            b.cur = (1, 1, 1)
            facade_window(b, a0, z, 1.0, "lit" if rr.random() < 0.35 else "dark", face=-1)
            z += 5.0
            k += 1
        b.cur = (0.6, 0.15, 0.12)
        b.gbox(a0 - 0.03, a0, 0, 3.2, c1 - 9.0, c1 - 5.5, {"-x": M["paint"]})
    # полоса низких магазинов/складов вдоль проспекта, с проходами
    x0, x1, z0, z1, h = PL["STRIP"]
    rr = random.Random(17)
    x = x0
    while x < x1:
        L = rr.uniform(18, 34)
        hh = h * rr.uniform(0.8, 1.25)
        b.cur = rr.choice([(0.92, 0.92, 0.94), (0.85, 0.84, 0.82), (0.95, 0.9, 0.82)])
        walls_box(b, x, min(x + L, x1), 0, hh, z0, z1, M["white"], (4.0, hh), M["snow"])
        for k in range(int(L / 6)):
            b.cur = (1, 1, 1)
            facade_window_z(b, x + 3 + k * 6, z1 + 0.03, 1.4, "lit" if rr.random() < 0.3 else "dark")
        x += L + rr.uniform(3, 8)
    return b.build("Market_nocol", coll)


# ------------------------------------------------------------------ высотки вокруг двора
TILE = (22.4, 25.2)                # facade_*: 7 окон × 9 этажей
TILE_OF = {"fac_cream": (12.0, 11.2), "fac_ochre": (12.0, 11.2), "fac_brick": (12.0, 11.2)}   # menu_fac_*: 4 клетки × 4 этажа


def slab(b, x0, x1, z0, z1, fl, fac, face, tint, caps=False):
    """Панельный дом: фасад к камере — текстура окон, остальное — штукатурка, снег на крыше."""
    h = PLINTH + fl * FLOOR_H
    su, sv = TILE_OF.get(fac, TILE)
    m = M[fac]
    b.cur = (tint[0] * 0.6, tint[1] * 0.6, tint[2] * 0.6)
    faces = {k: M["plaster"] for k in ("+x", "-x", "+z", "-z") if k != face}
    b.gbox(x0, x1, 0, h, z0, z1, faces, (6.0, 6.0))
    b.cur = tint
    if face == "+z":
        q, L = [(x0, PLINTH, z1), (x1, PLINTH, z1), (x1, h, z1), (x0, h, z1)], x1 - x0
        base = [(x0, 0, z1), (x1, 0, z1), (x1, PLINTH, z1), (x0, PLINTH, z1)]
    elif face == "-z":
        q, L = [(x1, PLINTH, z0), (x0, PLINTH, z0), (x0, h, z0), (x1, h, z0)], x1 - x0
        base = [(x1, 0, z0), (x0, 0, z0), (x0, PLINTH, z0), (x1, PLINTH, z0)]
    else:   # "-x"
        q, L = [(x0, PLINTH, z1), (x0, PLINTH, z0), (x0, h, z0), (x0, h, z1)], z1 - z0
        base = [(x0, 0, z1), (x0, 0, z0), (x0, PLINTH, z0), (x0, PLINTH, z1)]
    b.gquad(q, [(0, 0), (L / su, 0), (L / su, (h - PLINTH) / sv), (0, (h - PLINTH) / sv)], m)
    b.cur = (0.3, 0.29, 0.29)
    b.gquad(base, [(0, 0), (1, 0), (1, 0.1), (0, 0.1)], M["plaster"])
    b.cur = (1, 1, 1)
    b.gbox(x0, x1, h, h + 0.4, z0, z1, {"up": M["snow"], "+x": M["snow"], "-x": M["snow"], "+z": M["snow"], "-z": M["snow"]},
           (6.0, 6.0))
    # надстройки над лестницами и лифтами
    n = max(1, int(L / 24))
    for k in range(n):
        c = (k + 0.5) / n
        if face == "-x":
            zc, xc = z0 + c * (z1 - z0), x0 + 5.0
        else:
            zc, xc = (z0 + z1) / 2, x0 + c * (x1 - x0)
        b.cur = (tint[0] * 0.75, tint[1] * 0.75, tint[2] * 0.75)
        b.gbox(xc - 2.0, xc + 2.0, h + 0.4, h + 3.0, zc - 2.0, zc + 2.0,
               {"+x": M["plaster"], "-x": M["plaster"], "+z": M["plaster"], "-z": M["plaster"], "up": M["snow"]}, (3.0, 3.0))
    if caps:
        # красные «шапки»: скаты к фасаду с белыми фронтонами между ними (видео 0, 5–8 с), сверху снег
        n = int(L / 14)
        for k in range(n):
            zc = z0 + (k + 0.5) * L / n
            b.cur = (0.72, 0.12, 0.1)
            gable(b, x0 - 0.4, x0 + 4.4, h + 0.4, h + 2.5, zc - 5.2, zc + 5.2, m=M["paint"], ends=M["plaster"])
            b.cur = (1, 1, 1)
            gable(b, x0 + 1.3, x0 + 2.7, h + 1.93, h + 2.56, zc - 5.15, zc + 5.15)          # снег только у конька


# дома за пределами плана — силуэты в дымке (дальше ряда за проспектом)
BACK_BLOCKS = [
    (-150, 20, -315, -303, 16, "fac_ochre", "+z", (0.95, 0.85, 0.8)),
    (40, 260, -335, -323, 14, "fac_ochre", "+z", (0.9, 0.8, 0.78)),
    (270, 420, -305, -293, 16, "fac_ochre", "+z", (1.0, 0.85, 0.75)),
    (200, 214, -45, 55, 9, "fac_cream", "-x", (0.95, 0.85, 0.8)),
    (230, 244, -155, -75, 12, "fac_ochre", "-x", (0.98, 0.85, 0.75)),
]


def blocks(coll):
    b = B()
    # дом с красными шапками напротив (фасадом к двору — в −x)
    x0, x1, z0, z1, fl = PL["RED_CAP"]
    slab(b, x0, x1, z0, z1, fl, "fac_cream", "-x", (1.0, 1.0, 1.0), caps=True)
    # ряд 16-этажек справа: фасадом к двору (в −z), кирпично-бежевые
    tints = [(1.0, 1.0, 1.0), (0.97, 0.93, 0.9), (1.0, 0.97, 0.95)]
    for i, (a0, a1, c0, c1, fl) in enumerate(PL["EAST_ROW"]):
        slab(b, a0, a1, c0, c1, fl, "fac_brick", "-z", tints[i % len(tints)])
    # ряд высоток за проспектом — фасадом к нам (+z), охра и персик
    z0, z1 = PL["FAR_ROW_Z"]
    rr = random.Random(29)
    for i, (a0, a1, fl) in enumerate(PL["FAR_ROW"]):
        t = rr.choice([(1.0, 1.0, 1.0), (1.0, 0.94, 0.9), (0.98, 0.98, 0.94), (1.0, 0.9, 0.86)])
        slab(b, a0, a1, z0 + rr.uniform(-2, 2), z1, fl, "fac_ochre", "+z", t)
    for (a0, a1, c0, c1, fl, fac, face, tint) in BACK_BLOCKS:
        slab(b, a0, a1, c0, c1, fl, fac, face, tint)
    return b.build("Blocks_nocol", coll)


def lamps(coll):
    """Фонари: вдоль проспекта с обеих сторон (оранжевые точки у подножия высоток) и несколько во дворе."""
    b = B()
    a0, a1 = PL["AVENUE_Z"]
    pts = [(x, a1 + 0.8, 9.0, -1) for x in range(-60, 235, 30)] + [(x + 15, a0 - 0.8, 9.0, 1) for x in range(-60, 235, 30)]
    pts += [(11.0, -48.0, 6.0, 1), (11.0, 16.0, 6.0, 1), (34.0, -47.0, 5.0, 1), (48.0, 35.0, 6.0, 1), (67.0, -15.0, 6.0, 1),
            (67.0, 35.0, 6.0, 1), (100.0, -65.0, 7.0, 1)]
    for i, (x, z, hgt, d) in enumerate(pts):
        b.cur = (1, 1, 1)
        b.cyl(P(x, 0, z), P(x, hgt, z), 0.08, 0.06, M["dark"], segs=5)
        b.cyl(P(x, hgt, z), P(x, hgt + 0.1, z + 1.2 * d), 0.04, 0.04, M["dark"], segs=4)
        b.gbox(x - 0.15, x + 0.15, hgt - 0.12, hgt + 0.05, z + 0.9 * d - 0.3, z + 0.9 * d + 0.3,
               {"down": M["lamp_o"], "up": M["dark"], "+x": M["dark"], "-x": M["dark"], "+z": M["dark"], "-z": M["dark"]})
        far = z < -150
        if not far or i % 2 == 0:
            LIGHTS.append({"kind": "street", "pos": [x, hgt - 0.3, z + 0.9 * d], "color": [1.0, 0.55, 0.22],
                           "energy": 4.0, "range": 22.0 if far else 16.0})
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
           market(coll), blocks(coll), lamps(coll)]
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


if not globals().get("MENU_NO_MAIN"):          # build_playground.py берёт отсюда материалы и деревья, не собирая кадр
    result = main()
    print(result)
