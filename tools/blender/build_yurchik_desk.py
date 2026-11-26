# -*- coding: utf-8 -*-
# Рабочее место Юрчика v2: игровой стол, монитор, системник ПОД столом, клавиатура, мышь, колонки, коврик.
# По фото стола (docs/references/apartment/ee0800e3-….jpg): чёрный «игровой» стол со срезанными передними углами
# и Y-образными стальными ножками, во весь перёд — большой коврик с красным драконом, системник стоит на полу
# под правым краем стола — обычный чёрный корпус 2011 года, без окна и подсветки (горят только диоды).
# Компьютер — 2010–2011 год (Windows 7): монитор ASUS 19" 5:4 (экран игры 1280x1024 — pc_seat.gd),
# клавиатура со стандартной раскладкой 104 клавиши (латиница + кириллица), мышь, колонки 2.0.
#
# Порядок:
#   1) python tools/blender/yurchik_desk_textures.py           — текстуры yd_atlas.png, yd_glow.png
#   2) через Blender MCP: exec(open(r"<путь>\tools\blender\build_yurchik_desk.py", encoding="utf-8").read(),
#                              {"__file__": r"<путь>\tools\blender\build_yurchik_desk.py", "__name__": "__main__"})
#      (строит всё в своей сцене YurchikDesk, остальные сцены не трогает)
# Результат: assets/models/yurchik_room/{desk,mousepad,monitor,pc_tower,keyboard,mouse,speaker_left,speaker_right}.gltf
# и их позиции в assets/models/yurchik_room/layout.json (дописываются к позициям остальной комнаты).
# В сцене предметы потом можно двигать руками — layout.json хранит только позиции из сборки.
# В stairwell.tscn эти предметы — дочерние узлы YurchikRoom (позиции из layout.json).
#
# Имена, которые ищет игра: PCScreen_nocol — экран (pc_seat.gd рисует на нём Windows), Keyboard_nocol — откуда
# стучат клавиши, SpeakerLeft / SpeakerRight — колонки; *Glow_nocol и *Led_nocol — то, что светится только у
# включённого компа (pc_seat.gd прячет их, пока комп выключен).
# Без «_nocol» — жёсткое (ps2_import.gd делает коллизию по сетке): Desk, Monitor, PcTower.
# Рёбра корпусов скошены модификатором Bevel (применяется при экспорте) — на гранях ловится свет лампы.
import bpy, bmesh, os, sys, math, json
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import importlib
import yurchik_desk_layout as L
importlib.reload(L)

_ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), _ns)
mat = _ns["mat"]
ITEM_DIR = os.path.join(ROOT, "assets", "models", "yurchik_room")
SCENE = "YurchikDesk"

DX0, DX1, DY0, DY1, DT, Z, MX = L.DX0, L.DX1, L.DY0, L.DY1, L.DT, L.Z, L.MX
UV = L.uv
GUV = lambda n: L.uv(n, L.G, L.GLOW)


# =====================================================================================
#  Построитель сетки
# =====================================================================================
class Mesh:
    def __init__(self, smooth=False, bevel=0.0):
        self.v, self.f, self.uv, self.mi, self.mats = [], [], [], [], []
        self.smooth, self.bevel = smooth, bevel

    def poly(self, pts, uvs, m):
        if m not in self.mats:
            self.mats.append(m)
        base = len(self.v)
        self.v += [tuple(p) for p in pts]
        self.f.append(tuple(range(base, base + len(pts))))
        self.uv.append([tuple(u) for u in uvs])
        self.mi.append(self.mats.index(m))

    def quad(self, pts, m, rect):
        u0, v0, u1, v1 = rect
        self.poly(pts, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], m)

    def build(self, name, coll):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in self.mats:
            me.materials.append(m)
        uvl = me.uv_layers.new(name="UVMap")
        for pi, poly in enumerate(me.polygons):
            poly.material_index = self.mi[pi]
            for k, li in enumerate(poly.loop_indices):
                uvl.data[li].uv = self.uv[pi][k]
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)   # общие вершины — иначе фаска не встанет
        bm.to_mesh(me); bm.free()
        for p in me.polygons:
            p.use_smooth = self.smooth
        me.validate(); me.update()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        if self.bevel:
            bv = ob.modifiers.new("Bevel", 'BEVEL')
            bv.width, bv.segments, bv.limit_method = self.bevel, 1, 'ANGLE'
            bv.angle_limit = math.radians(40)
            bv.harden_normals = False
        return ob


FACES = {'+X': (1, 3, 7, 5), '-X': (2, 0, 4, 6), '+Y': (3, 2, 6, 7), '-Y': (0, 1, 5, 4), '+Z': (4, 5, 7, 6), '-Z': (0, 2, 3, 1)}


def box(b, mn, mx, m, rect, faces=None, skip=(), xf=None):
    """Ящик по углам; каждая грань — целиком в прямоугольник атласа (faces переопределяет грани). xf — матрица."""
    pts = [Vector((mx[0] if i & 1 else mn[0], mx[1] if i & 2 else mn[1], mx[2] if i & 4 else mn[2])) for i in range(8)]
    if xf is not None:
        pts = [xf @ p for p in pts]
    for k, idx in FACES.items():
        if k in skip:
            continue
        mm, r = (faces or {}).get(k, (m, rect))
        b.quad([pts[i] for i in idx], mm, r)


def tube(b, p0, p1, w, h, m, rect, up=Vector((0, 0, 1))):
    """Прямоугольная труба от p0 до p1 (сечение w x h)."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    side = ax.cross(up)
    if side.length < 1e-4:
        side = ax.cross(Vector((0, 1, 0)))
    side.normalize()
    nrm = side.cross(ax).normalized()
    c = lambda p, sx, sy: p + side * (w / 2 * sx) + nrm * (h / 2 * sy)
    ring0 = [c(p0, -1, -1), c(p0, 1, -1), c(p0, 1, 1), c(p0, -1, 1)]
    ring1 = [c(p1, -1, -1), c(p1, 1, -1), c(p1, 1, 1), c(p1, -1, 1)]
    for i in range(4):
        j = (i + 1) % 4
        b.quad([ring0[i], ring0[j], ring1[j], ring1[i]], m, rect)
    b.quad(ring0[::-1], m, rect)
    b.quad(ring1, m, rect)


def cyl(b, p0, p1, r, m, rect, segs=8, caps=True, rect_cap=None):
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    t = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
    u = ax.cross(t).normalized(); w = ax.cross(u)
    ring = lambda p, a: p + (u * math.cos(a) + w * math.sin(a)) * r
    u0, v0, u1, v1 = rect
    for i in range(segs):
        a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
        b.poly([ring(p0, a0), ring(p0, a1), ring(p1, a1), ring(p1, a0)],
               [(u0 + (u1 - u0) * i / segs, v0), (u0 + (u1 - u0) * (i + 1) / segs, v0),
                (u0 + (u1 - u0) * (i + 1) / segs, v1), (u0 + (u1 - u0) * i / segs, v1)], m)
    if caps:
        cu0, cv0, cu1, cv1 = rect_cap or rect
        cuv = lambda a: (cu0 + (cu1 - cu0) * (0.5 + 0.5 * math.cos(a)), cv0 + (cv1 - cv0) * (0.5 + 0.5 * math.sin(a)))
        angs = [2 * math.pi * i / segs for i in range(segs)]
        b.poly([ring(p1, a) for a in angs], [cuv(a) for a in angs], m)
        b.poly([ring(p0, a) for a in angs[::-1]], [cuv(a) for a in angs[::-1]], m)


def prism(b, pts2, z0, z1, m, top_rect, side_rect, bottom_rect=None, bbox=None):
    """Призма по многоугольнику (против часовой сверху): верх — плоская проекция в top_rect по рамке bbox,
    бока — side_rect, растянутый по периметру."""
    xs, ys = [p[0] for p in pts2], [p[1] for p in pts2]
    bx0, by0, bx1, by1 = bbox or (min(xs), min(ys), max(xs), max(ys))
    u0, v0, u1, v1 = top_rect
    puv = lambda p: (u0 + (u1 - u0) * (p[0] - bx0) / (bx1 - bx0), v0 + (v1 - v0) * (p[1] - by0) / (by1 - by0))
    b.poly([(x, y, z1) for x, y in pts2], [puv(p) for p in pts2], m)
    br = bottom_rect or top_rect
    bu0, bv0, bu1, bv1 = br
    buv = lambda p: (bu0 + (bu1 - bu0) * (p[0] - bx0) / (bx1 - bx0), bv0 + (bv1 - bv0) * (p[1] - by0) / (by1 - by0))
    b.poly([(x, y, z0) for x, y in pts2[::-1]], [buv(p) for p in pts2[::-1]], m)
    per = sum((Vector(pts2[(i + 1) % len(pts2)]) - Vector(pts2[i])).length for i in range(len(pts2)))
    su0, sv0, su1, sv1 = side_rect
    s = 0.0
    for i in range(len(pts2)):
        a, c = pts2[i], pts2[(i + 1) % len(pts2)]
        ln = (Vector(c) - Vector(a)).length
        ua, uc = su0 + (su1 - su0) * (s / per), su0 + (su1 - su0) * ((s + ln) / per)
        b.poly([(a[0], a[1], z0), (c[0], c[1], z0), (c[0], c[1], z1), (a[0], a[1], z1)],
               [(ua, sv0), (uc, sv0), (uc, sv1), (ua, sv1)], m)
        s += ln


def sub(rect, fx0, fy0, fx1, fy1):
    """Кусок прямоугольника UV: доли от левого-нижнего угла."""
    u0, v0, u1, v1 = rect
    return (u0 + (u1 - u0) * fx0, v0 + (v1 - v0) * fy0, u0 + (u1 - u0) * fx1, v0 + (v1 - v0) * fy1)


# =====================================================================================
#  Предметы
# =====================================================================================
def build_items(M):
    at, gl, glow, scr = M["atlas"], M["gloss"], M["glow"], M["screen"]
    items = {}

    def part(item, name, **kw):
        it = items.setdefault(item, {})
        if name not in it:
            it[name] = Mesh(**kw)
        return it[name]

    MET, MAT, GLO = UV("metal"), UV("matte"), UV("gloss")

    # --- стол: столешница со срезанными передними углами, Y-ножки, задняя балка ---
    desk = part("desk", "Desk", bevel=0.003)
    ch = L.CHAMFER
    top = [(DX0 + ch, DY0), (DX1 - ch, DY0), (DX1, DY0 + ch), (DX1, DY1), (DX0, DY1), (DX0, DY0 + ch)]
    zt0 = DT - L.TOP_T
    prism(desk, top, zt0, DT, at, UV("desk_top"), UV("edge"), bottom_rect=MAT)
    for xs in (DX0 + 0.06, DX1 - 0.06):
        ym = (DY0 + DY1) / 2 + 0.03
        box(desk, (xs - 0.03, DY0 + 0.05, Z + 0.008), (xs + 0.03, DY1 - 0.05, Z + 0.04), at, MET)   # опора на полу
        for y_ in (DY0 + 0.07, DY1 - 0.07):                                                           # регулируемые пятки
            cyl(desk, (xs, y_, Z), (xs, y_, Z + 0.008), 0.016, at, UV("cable"), segs=8)
        tube(desk, (xs, ym, Z + 0.04), (xs, ym, Z + 0.42), 0.055, 0.04, at, MET)                     # стойка
        tube(desk, (xs, ym, Z + 0.40), (xs, DY0 + 0.09, zt0 - 0.03), 0.045, 0.035, at, MET)          # «рога» Y к углам
        tube(desk, (xs, ym, Z + 0.40), (xs, DY1 - 0.09, zt0 - 0.03), 0.045, 0.035, at, MET)
        box(desk, (xs - 0.025, DY0 + 0.06, zt0 - 0.03), (xs + 0.025, DY1 - 0.06, zt0), at, MET)    # рама под столешницей
        for y_ in (DY0 + 0.20, DY1 - 0.20):                                                          # винты
            cyl(desk, (xs - 0.026, y_, zt0 - 0.015), (xs - 0.031, y_, zt0 - 0.015), 0.006, at, UV("steel"), segs=6)
    box(desk, (DX0 + 0.06, DY1 - 0.11, zt0 - 0.05), (DX1 - 0.06, DY1 - 0.07, zt0), at, MET)          # задняя балка
    box(desk, (DX0 + 0.06, DY0 + 0.10, zt0 - 0.025), (DX1 - 0.06, DY0 + 0.13, zt0), at, MET)         # передняя планка
    # крючок для наушников на левой ножке
    hx = DX0 + 0.06 - 0.03
    tube(desk, (hx, DY0 + 0.20, zt0 - 0.015), (hx - 0.05, DY0 + 0.20, zt0 - 0.015), 0.012, 0.012, at, MET)
    tube(desk, (hx - 0.05, DY0 + 0.20, zt0 - 0.021), (hx - 0.05, DY0 + 0.20, zt0 + 0.012 - 0.03), 0.012, 0.012, at, MET)

    # --- коврик с драконом: перед стола, под клавиатурой и мышью ---
    pad = part("mousepad", "Mousepad_nocol")
    px0, px1, py0, py1 = -7.31, -6.55, DY0 + 0.015, DY0 + 0.015 + 0.338
    box(pad, (px0, py0, DT), (px1, py1, DT + 0.003), at, UV("cable"), faces={'+Z': (at, UV("pad"))})

    # --- монитор ---
    F = L.MON_FRONT_Y
    W2, H, z0 = L.MON_W / 2, L.MON_H, L.MON_Z0
    bx, bt, bb = L.MON_BEZ
    rec = 0.004                                                  # матрица утоплена в рамку
    mon = part("monitor", "Monitor", bevel=0.003)
    mf = UV("mon_front")
    fuv = lambda x, z: (mf[0] + (mf[2] - mf[0]) * (x - (MX - W2)) / (2 * W2), mf[1] + (mf[3] - mf[1]) * (z - z0) / H)
    ox0, ox1, oz0, oz1 = MX - W2, MX + W2, z0, z0 + H
    ix0, ix1, iz0, iz1 = ox0 + bx, ox1 - bx, z0 + bb, oz1 - bt
    O = [(ox0, oz0), (ox1, oz0), (ox1, oz1), (ox0, oz1)]
    I = [(ix0, iz0), (ix1, iz0), (ix1, iz1), (ix0, iz1)]
    for k in range(4):                                           # рамка: 4 трапеции вокруг экрана
        a, c = O[k], O[(k + 1) % 4]
        ia, ic = I[k], I[(k + 1) % 4]
        pts = [a, c, ic, ia]
        mon.poly([(x, F, z) for x, z in pts], [fuv(x, z) for x, z in pts], gl)
        dark = sub(MAT, 0, 0, 0.1, 0.1)                          # внутренний бортик матрицы
        mon.quad([(ia[0], F, ia[1]), (ic[0], F, ic[1]), (ic[0], F + rec, ic[1]), (ia[0], F + rec, ia[1])][::-1], at, dark)
    # корпус панели: бока и зад
    box(mon, (ox0, F, oz0), (ox1, F + 0.024, oz1), gl, GLO, skip=('-Y',))
    # горб сзади: усечённая пирамида с решёткой
    bz0, bz1 = z0 + 0.05, z0 + 0.30
    back0 = [(MX - 0.17, F + 0.024, bz0), (MX + 0.17, F + 0.024, bz0), (MX + 0.17, F + 0.024, bz1), (MX - 0.17, F + 0.024, bz1)]
    back1 = [(MX - 0.12, F + 0.07, bz0 + 0.03), (MX + 0.12, F + 0.07, bz0 + 0.03), (MX + 0.12, F + 0.07, bz1 - 0.03), (MX - 0.12, F + 0.07, bz1 - 0.03)]
    mon.quad([back1[1], back1[0], back1[3], back1[2]], at, UV("mon_back"))
    for k in range(4):
        j = (k + 1) % 4
        mon.quad([back0[j], back0[k], back1[k], back1[j]], at, MAT)
    # экран — отдельный объект, UV 0..1 на всю матрицу (игра рисует на нём Windows)
    s = part("monitor", "PCScreen_nocol")
    s.quad([(ix0, F + rec, iz0), (ix1, F + rec, iz0), (ix1, F + rec, iz1), (ix0, F + rec, iz1)], scr, (0, 0, 1, 1))
    # подставка: овальное основание, наклонная шея, шарнир
    st = part("monitor", "Monitor_nocol", bevel=0.002)
    cyb = F + 0.065
    n = 20
    oval = [(MX + 0.115 * math.cos(2 * math.pi * i / n), cyb + 0.082 * math.sin(2 * math.pi * i / n)) for i in range(n)]
    prism(st, oval, DT, DT + 0.012, gl, UV("stand"), GLO)
    tube(st, (MX, cyb + 0.035, DT + 0.01), (MX, F + 0.05, z0 + 0.14), 0.06, 0.022, gl, GLO, up=Vector((1, 0, 0)))
    cyl(st, (MX - 0.04, F + 0.05, z0 + 0.14), (MX + 0.04, F + 0.05, z0 + 0.14), 0.016, gl, GLO, segs=10)
    # диод питания (светится только у включённого)
    led = part("monitor", "MonitorLed_nocol")
    lx, lz, lr = MX + 0.183, z0 + 0.014, 0.004
    led.quad([(lx - lr, F - 0.0006, lz - lr), (lx + lr, F - 0.0006, lz - lr), (lx + lr, F - 0.0006, lz + lr), (lx - lr, F - 0.0006, lz + lr)],
             glow, GUV("mon_led"))

    # --- системник под правым краем стола, на полу ---
    tw, td, th = 0.20, 0.44, 0.43
    tx1 = DX1 - 0.06 - 0.045                                     # между ним и правой ножкой — щель
    tx0, ty0 = tx1 - tw, DY0 + 0.09
    ty1, tz0 = ty0 + td, Z + 0.015
    tz1 = tz0 + th
    tow = part("pc_tower", "PcTower", bevel=0.003)
    box(tow, (tx0, ty0 + 0.012, tz0), (tx1, ty1, tz1), at, MAT,
        faces={'-X': (at, UV("tower_s")), '+Z': (at, UV("tower_t")), '-Y': (at, MAT)})
    box(tow, (tx0 + 0.004, ty0, tz0 + 0.003), (tx1 - 0.004, ty0 + 0.012, tz1 - 0.003), at, MAT,   # передняя панель
        faces={'-Y': (at, UV("tower_f"))}, skip=('+Y',))
    for (fx, fy) in ((tx0 + 0.03, ty0 + 0.05), (tx1 - 0.03, ty0 + 0.05), (tx0 + 0.03, ty1 - 0.05), (tx1 - 0.03, ty1 - 0.05)):
        cyl(tow, (fx, fy, Z), (fx, fy, tz0), 0.014, at, UV("cable"), segs=8)
    # диоды питания (зелёный) и диска (оранжевый) — горят, только пока комп включён; места — как на куске tower_f
    g = part("pc_tower", "PcTowerGlow_nocol")
    fy_, lr = ty0 - 0.0008, 0.0035
    for (px, name) in ((54, "power"), (74, "hdd")):
        lx = tx0 + 0.004 + (tw - 0.008) * px / 128
        lz = tz1 - 0.003 - (th - 0.006) * 132 / 276
        g.quad([(lx - lr, fy_, lz - lr), (lx + lr, fy_, lz - lr), (lx + lr, fy_, lz + lr), (lx - lr, fy_, lz + lr)], glow, GUV(name))

    # --- колонки 2.0 по бокам монитора ---
    for nm, x in (("speaker_left", MX - 0.31), ("speaker_right", MX + 0.31)):
        sp = part(nm, L_name(nm) + "_nocol", bevel=0.004)
        sw, sd, sh = 0.09, 0.09, 0.18
        y0 = DY1 - 0.22
        front = UV("spk_front")
        box(sp, (x - sw / 2, y0, DT), (x + sw / 2, y0 + sd, DT + sh), at, UV("spk_side"),
            faces={'-Y': (at, front), '+Z': (at, MAT), '+Y': (at, MAT)})

    # --- клавиатура: клин-корпус и 104 клавиши (каждая берёт свой кусок картинки клавиатуры) ---
    kb = part("keyboard", "Keyboard_nocol")
    kr = UV("kb")
    kx0, ky0, kz0 = MX - L.KB_W / 2, DY0 + 0.07, DT + 0.003
    zf, zb = 0.011, 0.020                                         # толщина спереди и сзади

    def kz(y):                                                    # верх корпуса над точкой (y от переднего края)
        return kz0 + zf + (zb - zf) * y / L.KB_D

    def kuv(x, y):
        return (kr[0] + (kr[2] - kr[0]) * x / L.KB_W, kr[1] + (kr[3] - kr[1]) * y / L.KB_D)

    P = lambda x, y, z: (kx0 + x, ky0 + y, z)
    c4 = [(0, 0), (L.KB_W, 0), (L.KB_W, L.KB_D), (0, L.KB_D)]
    kb.poly([P(x, y, kz(y)) for x, y in c4], [kuv(x, y) for x, y in c4], at)                  # верх
    kb.poly([P(x, y, kz0) for x, y in c4[::-1]], [kuv(x, y) for x, y in c4[::-1]], at)        # низ
    edge_r = sub(UV("matte"), 0, 0, 1, 0.2)
    for i in range(4):
        (xa, ya), (xc, yc) = c4[i], c4[(i + 1) % 4]
        kb.quad([P(xa, ya, kz0), P(xc, yc, kz0), P(xc, yc, kz(yc)), P(xa, ya, kz(ya))], at, edge_r)
    u = L.KEY_U
    ksr = UV("key_side")
    for (x, y, w, h, lab, ru) in L.key_rows():
        xa = L.KB_MARGIN_X + x * u
        yb = L.KB_D - (L.KB_MARGIN_BACK + y * u)                 # задний край клавиши (y от переднего края корпуса)
        yf = yb - h * u
        g0, ins = 0.0016, 0.0032
        bx0, bx1, by0_, by1_ = xa + g0, xa + w * u - g0, yf + g0, yb - g0
        tx0_, tx1_, ty0_, ty1_ = xa + ins, xa + w * u - ins, yf + ins * 1.3, yb - ins * 0.8
        lo = [(bx0, by0_), (bx1, by0_), (bx1, by1_), (bx0, by1_)]
        hi = [(tx0_, ty0_), (tx1_, ty0_), (tx1_, ty1_), (tx0_, ty1_)]
        hk = 0.0085
        kb.poly([P(x_, y_, kz(y_) + hk) for x_, y_ in hi], [kuv(x_, y_) for x_, y_ in hi], at)
        for i in range(4):
            j = (i + 1) % 4
            kb.quad([P(*lo[i], kz(lo[i][1]) + 0.0005), P(*lo[j], kz(lo[j][1]) + 0.0005),
                     P(*hi[j], kz(hi[j][1]) + hk), P(*hi[i], kz(hi[i][1]) + hk)], at, ksr)
    # провод клавиатуры — назад под монитор
    cb = part("keyboard", "KeyboardCable_nocol")
    pts = [(MX - 0.12, ky0 + L.KB_D, kz0 + 0.01), (MX - 0.13, ky0 + L.KB_D + 0.05, DT + 0.004), (MX - 0.08, F + 0.03, DT + 0.004),
           (MX - 0.05, DY1 - 0.03, DT + 0.004), (MX - 0.05, DY1 + 0.01, DT - 0.05)]
    for a_, b_ in zip(pts, pts[1:]):
        cyl(cb, a_, b_, 0.0025, at, UV("cable"), segs=4, caps=False)

    # --- мышь: обтекаемая, гладкая ---
    ms = part("mouse", "Mouse_nocol", smooth=True)
    mcx, mcy, yaw = MX + 0.33, DY0 + 0.15, math.radians(-8)
    ML, MW, MH = 0.112, 0.062, 0.036
    rot = Matrix.Rotation(yaw, 3, 'Z')
    mr = UV("mouse")
    NR, NS = 12, 10
    rings = []
    for i in range(NR + 1):
        t = i / NR                                                # 0 — зад, 1 — перёд
        wid = MW / 2 * (0.62 + 0.38 * math.sin(math.pi * min(1, t * 1.15) ** 0.9)) * (0.88 if t > 0.85 else 1)
        hgt = MH * (0.25 + 0.75 * math.sin(math.pi * (0.15 + 0.75 * t)) ** 0.7) * (1 - 0.6 * max(0, t - 0.8) / 0.2)
        if i in (0, NR):                                          # торцы почти сходятся — без «дыры»
            wid *= 0.35; hgt *= 0.55
        y = -ML / 2 + ML * t
        ring = []
        for j in range(NS + 1):
            a = math.pi * j / NS
            x = -math.cos(a) * wid
            z = math.sin(a) ** 0.6 * hgt
            ring.append((x, y, z))
        rings.append(ring)

    def mw(p):
        v = rot @ Vector(p)
        return (mcx + v.x, mcy + v.y, DT + 0.003 + v.z)

    muv = lambda p: (mr[0] + (mr[2] - mr[0]) * (p[0] / MW + 0.5), mr[1] + (mr[3] - mr[1]) * (p[1] / ML + 0.5))
    for i in range(NR):
        for j in range(NS):
            q = [rings[i][j + 1], rings[i][j], rings[i + 1][j], rings[i + 1][j + 1]]
            ms.poly([mw(p) for p in q], [muv(p) for p in q], at)
    ms.poly([mw(rings[i][0]) for i in range(NR + 1)] + [mw(rings[i][NS]) for i in range(NR, -1, -1)],
            [muv(rings[i][0]) for i in range(NR + 1)] + [muv(rings[i][NS]) for i in range(NR, -1, -1)], at)   # дно
    for i in (0, NR):                                             # торцы
        ring = rings[i] if i == 0 else rings[i][::-1]
        ms.poly([mw(p) for p in ring], [muv(p) for p in ring], at)
    # колёсико в прорези между кнопками
    tw_ = 0.78
    iw = round(tw_ * NR)
    wz = max(p[2] for p in rings[iw])
    wy = -ML / 2 + ML * tw_
    cyl(ms, mw((-0.0035, wy, wz - 0.0055)), mw((0.0035, wy, wz - 0.0055)), 0.0075, at, UV("key_side"), segs=10)
    mc = part("mouse", "MouseCable_nocol")
    head = mw((0, ML / 2, 0.006))
    pts = [head, (head[0] - 0.01, head[1] + 0.07, DT + 0.004), (MX + 0.22, F + 0.02, DT + 0.004), (MX + 0.06, DY1 - 0.03, DT + 0.004),
           (MX + 0.05, DY1 + 0.01, DT - 0.05)]
    for a_, b_ in zip(pts, pts[1:]):
        cyl(mc, a_, b_, 0.0022, at, UV("cable"), segs=4, caps=False)
    return items


def L_name(item):
    return "".join(w.capitalize() for w in item.split("_"))


# =====================================================================================
def export_items(items, coll):
    with open(os.path.join(ITEM_DIR, "layout.json"), encoding="utf-8") as f:
        layout = json.load(f)
    tris = {}
    for item, parts in items.items():
        sub_ = bpy.data.collections.new("yd_" + item)
        coll.children.link(sub_)
        obs = [mb.build(nm, sub_) for nm, mb in parts.items()]
        pts = [v.co for ob in obs for v in ob.data.vertices]
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        A = Vector((round((lo[0] + hi[0]) / 2, 3), round((lo[1] + hi[1]) / 2, 3), round(lo[2], 3)))
        for ob in obs:
            ob.data.transform(Matrix.Translation(-A))
        for o in bpy.data.objects:                              # выделение — во всех сценах (экспорт берёт и чужие)
            try:
                o.select_set(o in obs)
            except RuntimeError:
                pass
        bpy.context.view_layer.objects.active = obs[0]
        bpy.ops.export_scene.gltf(filepath=os.path.join(ITEM_DIR, item + ".gltf"), use_selection=True,
                                  export_keep_originals=True, export_format='GLTF_SEPARATE', export_apply=True, export_yup=True,
                                  use_active_scene=True)
        for ob in obs:
            ob.location = A
        dg = bpy.context.evaluated_depsgraph_get()
        tris[item] = sum(sum(len(p.vertices) - 2 for p in ob.evaluated_get(dg).data.polygons) for ob in obs)
        layout[item] = [round(A.x, 3), round(A.z, 3), round(-A.y, 3)]      # Blender Z-up → Godot Y-up
    with open(os.path.join(ITEM_DIR, "layout.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    return {k: layout[k] for k in items}, tris


def main():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = sc
    old = bpy.data.collections.get("YurchikDesk")                # прошлая сборка; камеры и свет предпросмотра не трогаем
    if old:
        for c in [old] + list(old.children_recursive):
            for ob in list(c.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
        for c in list(old.children_recursive) + [old]:
            bpy.data.collections.remove(c)
    for me in list(bpy.data.meshes):                              # сетки прошлой сборки — иначе имена с .001
        if me.users == 0:
            bpy.data.meshes.remove(me)
    coll = bpy.data.collections.new("YurchikDesk")
    sc.collection.children.link(coll)
    M = {
        "atlas": mat("YdAtlas", "yd_atlas", rough=0.65),
        "gloss": mat("YdGloss", "yd_atlas", rough=0.3),
        "glow": mat("YdGlow", "yd_glow", "yd_glow", rough=0.5),
        "screen": mat("YrScreen", "yr_screen", "yr_screen_emission", rough=0.2),
    }
    items = build_items(M)
    layout, tris = export_items(items, coll)
    bpy.context.view_layer.update()
    res = {"layout": layout, "tris": tris, "total_tris": sum(tris.values())}
    print("BUILD_YUR_DESK " + json.dumps(res))
    return res


if __name__ == "__main__":
    result = main()
