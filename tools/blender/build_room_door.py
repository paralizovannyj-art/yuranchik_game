# -*- coding: utf-8 -*-
# Дверь в комнату Юрчика — по фото настоящей двери: старая межкомнатная дверь, крашенная белой краской,
# внизу — накладная филёнка (рамка из штапика), вверху — остеклённая часть, на которую сверху наброшено
# бежевое махровое полотенце (свешивается в комнату почти до середины двери, на сторону коридора — коротко).
# Ручка — старая нажимная, на высоте ~0.9 м, со стороны защёлки. Петли — со стороны стены с мангой.
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_room_door.py
# или через Blender MCP: exec(open(r"<путь>\tools\blender\build_room_door.py", encoding="utf-8").read())
#   (скрипт строит всё в своей сцене RoomDoor и не трогает остальные сцены).
# Результат: assets/textures/rd_*.png, assets/models/room_door.gltf (объект RoomDoor_nocol).
#
# Начало координат модели — нижний конец оси петель. Створка (закрыта) идёт от петель вдоль +Y на 0.83 м,
# толщина — вдоль +X (x = 0 — сторона комнаты, x = 0.04 — сторона коридора), высота — вдоль +Z.
# В Godot (stairwell.tscn → RoomDoor/Hinge) модель стоит на оси петель и поворачивается вместе с узлом Hinge.
import bpy, os, sys, math
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from tex_lib import save
from ps2_hero import C, finish
from ps2_style import noise
import photo_tex as PT

_ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), _ns)
B, mat = _ns["B"], _ns["mat"]
OUT = os.path.join(ROOT, "assets", "models")
R = np.random.default_rng(4848)               # грязь и сколы на текстурах

# --- размеры створки ---
Y0, Y1 = 0.0, 0.85             # во всю ширину проёма — по бокам без щелей
Z0, Z1 = 0.015, 2.05           # сверху вплотную, снизу щель 1.5 см — из-под двери пробивается свет
T = 0.04                       # толщина
W, HT = Y1 - Y0, Z1 - Z0
HANDLE_Y, HANDLE_Z = 0.765, 0.90


# =====================================================================================
#  Текстуры
# =====================================================================================
def tex_paint():
    """Белая масляная краска в несколько слоёв: пожелтела, мазки кисти вдоль створки, у ручки — засаленное пятно,
    внизу — следы ботинок и пыль, по краям — сколы до старого голубоватого слоя."""
    w, h = 128, 256
    # основа — фото крашеного дерева (CC0 ambientCG PaintedWood009C): мазки кисти вдоль створки, неровный слой
    paint = np.rot90(PT.flatten(PT.lib("ambientcg/PaintedWood009C"), 80))
    arr = PT.recolor(PT.resize(paint[:512, :256], w, h), (0.86, 0.85, 0.80), contrast=0.8, shadow_deg=4)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1.0 - yy / h                                                                    # 0 — низ двери, 1 — верх
    u = xx / w
    # засаленное пятно у ручки (со стороны защёлки)
    hu, hv = (HANDLE_Y - Y0) / W, (HANDLE_Z - Z0) / HT
    d = np.sqrt(((u - hu) / 0.16) ** 2 + ((v - hv) / 0.07) ** 2)
    g = np.clip(1.0 - d, 0, 1) ** 1.5 * (0.6 + 0.4 * noise(w, h, 12, 24, R, oct=2))
    arr = arr * (1 - 0.32 * g[..., None]) + C(0.45, 0.40, 0.32) * 0.32 * g[..., None]
    # низ: пыль и следы обуви
    low = np.clip(1.0 - v / 0.12, 0, 1) ** 1.3
    arr *= (1 - 0.25 * low * (0.5 + 0.5 * noise(w, h, 10, 4, R, oct=3)))[..., None]
    for _ in range(9):                                                                  # чёрные мазки от подошв
        cx, cy = R.uniform(0.1, 0.9), R.uniform(0.01, 0.12)
        d = np.sqrt(((u - cx) / R.uniform(0.04, 0.09)) ** 2 + ((v - cy) / R.uniform(0.004, 0.01)) ** 2)
        arr *= (1 - 0.18 * np.clip(1 - d, 0, 1))[..., None]
    # сколы: до старого голубовато-серого слоя
    chips = noise(w, h, 30, 60, R, oct=2) > 0.80
    edge = (np.minimum(u, 1 - u) < 0.06) | (v < 0.05) | (v > 0.97)
    mask = chips & (edge | (R.random((h, w)) < 0.15))
    arr[mask] = arr[mask] * 0.4 + C(0.62, 0.68, 0.70) * 0.6
    arr *= (0.97 + 0.05 * R.random((h, w)).astype(np.float32))[..., None]
    save("rd_paint", finish(arr, 1.0, crisp=0.2))


def tex_glass():
    """Узорчатое стекло «изморозь» (как в старых межкомнатных дверях) — молочное, рябое: стекло двустворчатой
    двери с фото прихожей (hall_1_to_room.webp)."""
    w, h = 64, 128
    g = PT.flatten(PT.rectify(PT.load("hall_1_to_room.webp"), [(178, 730), (262, 735), (262, 1040), (190, 1040)], 40, 150, ss=3), 10)
    arr = PT.recolor(PT.resize(g[8:92, 6:-6], w, h), (0.70, 0.72, 0.70), contrast=0.9)   # без края створки и светлого угла внизу
    save("rd_glass", finish(arr, 1.0, crisp=0.1))


def tex_towel():
    """Бежевое махровое полотенце, как на фото: серо-бежевое, ворс крупным зерном, внизу — тканая полоса-кайма,
    по ткани — тени складок вдоль, пара застиранных пятен. v = 0 — край на стороне коридора, v = 1 — нижний край в комнате."""
    w, h = 128, 256
    # махра — фото (CC0 Poly Haven terry_cloth), кусок ~0.4 x 0.8 м
    t = PT.flatten(PT.lib("polyhaven/terry_cloth"), 60)
    arr = PT.recolor(PT.resize(t[:1024, :512], w, h), (0.70, 0.64, 0.55), contrast=1.1, shadow_deg=4)
    arr *= (0.88 + 0.16 * noise(w, h, 6, 10, R, oct=3))[..., None]                    # неровно выцвело
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1.0 - yy / h
    # кайма у нижнего края (в комнате) и у короткого края (в коридоре): гладкая тканая полоса
    for a, b_ in ((0.955, 0.985), (0.015, 0.045)):
        band_ = (v > a) & (v < b_)
        arr[band_] = C(0.66, 0.60, 0.51) * (0.95 + 0.06 * np.sin(xx[band_] * 1.6))[..., None]
    arr[(v > 0.992) | (v < 0.008)] *= 0.85                                               # подвёрнутый край
    for _ in range(3):                                                                  # застиранные пятна
        cx, cy, r = R.uniform(0.15, 0.85), R.uniform(0.4, 0.9), R.uniform(0.05, 0.1)
        d = np.sqrt(((xx / w - cx) / r) ** 2 + ((v - cy) / (r * 0.5)) ** 2)
        arr *= (1 - 0.1 * np.clip(1 - d, 0, 1) ** 0.6)[..., None]
    save("rd_towel", finish(arr, 1.0, crisp=0.15))


def tex_metal():
    """Старая латунная ручка: потемнела, на нажимной части стёрта до блеска."""
    s = 32
    # потёртая поверхность — фото пластика в царапинах (CC0 ambientCG Plastic006), перекрашено в латунь
    arr = PT.recolor(PT.resize(PT.flatten(PT.lib("ambientcg/Plastic006"), 60)[:128, :128], s, s), (0.55, 0.45, 0.28), contrast=0.8)
    save("rd_metal", finish(arr, 1.0, crisp=0.1))


# =====================================================================================
#  Геометрия
# =====================================================================================
SPEC = {'+X': (1, 3, 7, 5), '-X': (2, 0, 4, 6), '+Y': (3, 2, 6, 7), '-Y': (0, 1, 5, 4), '+Z': (4, 5, 7, 6), '-Z': (0, 2, 3, 1)}


def pbox(b, mn, mx, m, skip=()):
    """Ящик, развёртка — проекция на плоскость створки (u — по ширине, v — по высоте): пятна текстуры
    (засаленное у ручки, грязь внизу) ложатся на своё место на любой детали. Торцы — та же проекция."""
    c = [Vector((mx[0] if i & 1 else mn[0], mx[1] if i & 2 else mn[1], mx[2] if i & 4 else mn[2])) for i in range(8)]
    for k, idx in SPEC.items():
        if k in skip:
            continue
        pts = [c[i] for i in idx]
        if k[1] == 'Y':                                                  # торец по ширине — тонкая полоска у края
            uvs = [((p.y - Y0) / W + p.x * 0.5, (p.z - Z0) / HT) for p in pts]
        else:
            uvs = [((p.y - Y0) / W, (p.z - Z0) / HT) for p in pts]
        b.poly(pts, uvs, m)


def cyl(b, p0, p1, r, m, segs=8, caps=True):
    b.cyl(p0, p1, r, r, m, segs=segs, caps=False)
    if caps:
        for pc, sgn in ((Vector(p1), 1), (Vector(p0), -1)):
            ax = (Vector(p1) - Vector(p0)).normalized() * sgn
            t = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
            u_ = ax.cross(t).normalized(); w_ = ax.cross(u_)
            pts = [pc + (u_ * math.cos(2 * math.pi * i / segs) + w_ * math.sin(2 * math.pi * i / segs)) * r for i in range(segs)]
            b.poly(pts, [(0.5, 0.5)] * segs, m)


def leaf(b, M):
    P = M["paint"]
    S0, S1 = 0.13, 0.72                     # внутренние края стоек (петлевой и замковой)
    RB, RM0, RM1, RT = 0.16, 0.86, 1.00, 1.89   # нижняя обвязка, средняя (низ/верх), верхняя
    # обвязка: стойки и перекладины на всю толщину; низ — сплошное полотно (филёнка накладная)
    pbox(b, (0, Y0, Z0), (T, S0, Z1), P)
    pbox(b, (0, S1, Z0), (T, Y1, Z1), P)
    pbox(b, (0, S0, Z0), (T, S1, RM1), P)                                              # низ целиком до верха средней перекладины
    pbox(b, (0, S0, RT), (T, S1, Z1), P)
    # остекление: стекло посередине толщины, штапик с обеих сторон
    gm = M["glass"]
    gx0, gx1 = 0.017, 0.023
    for x in (gx0, gx1):
        sgn = -1 if x == gx0 else 1
        pts = [Vector((x, S0, RM1)), Vector((x, S1, RM1)), Vector((x, S1, RT)), Vector((x, S0, RT))]
        if sgn < 0:
            pts = pts[::-1]
        b.poly(pts, [(0, 0), (1, 0), (1, 1), (0, 1)] if sgn > 0 else [(0, 1), (1, 1), (1, 0), (0, 0)], gm)
    bw = 0.016
    for (xa, xb) in ((-0.004, gx0), (gx1, T + 0.004)):
        pbox(b, (xa, S0, RM1), (xb, S0 + bw, RT), P)
        pbox(b, (xa, S1 - bw, RM1), (xb, S1, RT), P)
        pbox(b, (xa, S0 + bw, RM1), (xb, S1 - bw, RM1 + bw), P)
        pbox(b, (xa, S0 + bw, RT - bw), (xb, S1 - bw, RT), P)
    # накладная филёнка внизу: рамка из штапика на обеих сторонах
    my0, my1, mz0, mz1, mw, mt = S0, S1, 0.18, 0.74, 0.022, 0.007
    for (xa, xb) in ((-mt, 0.0), (T, T + mt)):
        pbox(b, (xa, my0, mz0), (xb, my0 + mw, mz1), P, skip=('+X',) if xa < 0 else ('-X',))
        pbox(b, (xa, my1 - mw, mz0), (xb, my1, mz1), P, skip=('+X',) if xa < 0 else ('-X',))
        pbox(b, (xa, my0 + mw, mz0), (xb, my1 - mw, mz0 + mw), P, skip=('+X',) if xa < 0 else ('-X',))
        pbox(b, (xa, my0 + mw, mz1 - mw), (xb, my1 - mw, mz1), P, skip=('+X',) if xa < 0 else ('-X',))
    # петли (закрашены той же краской) — на ребре со стороны комнаты
    for z in (0.22, 1.80):
        cyl(b, (-0.004, Y0 - 0.002, z), (-0.004, Y0 - 0.002, z + 0.11), 0.009, P, segs=6)
    # замок: планка на торце, ручки с розетками с обеих сторон
    me = M["metal"]
    pbox(b, (0.012, Y1, HANDLE_Z - 0.11), (0.028, Y1 + 0.002, HANDLE_Z + 0.11), me)
    for xs, sgn in ((0.0, -1), (T, 1)):
        cyl(b, (xs, HANDLE_Y, HANDLE_Z), (xs + sgn * 0.008, HANDLE_Y, HANDLE_Z), 0.026, me, segs=10)     # розетка
        cyl(b, (xs, HANDLE_Y, HANDLE_Z - 0.075), (xs + sgn * 0.005, HANDLE_Y, HANDLE_Z - 0.075), 0.013, me, segs=8)  # скважина
        cyl(b, (xs + sgn * 0.008, HANDLE_Y, HANDLE_Z), (xs + sgn * 0.05, HANDLE_Y, HANDLE_Z), 0.009, me, segs=8)   # шейка
        cyl(b, (xs + sgn * 0.05, HANDLE_Y + 0.01, HANDLE_Z), (xs + sgn * 0.05, HANDLE_Y - 0.115, HANDLE_Z - 0.008), 0.0095, me, segs=8)  # ручка — к петлям
    # отверстие от старого шпингалета под стеклом — тёмная точка нарисована не будет, но ржавый шуруп есть
    cyl(b, (-0.002, 0.42, 0.93), (0.0, 0.42, 0.93), 0.004, me, segs=5)


def towel(b, M):
    """Полотенце, наброшенное на верх двери: короткий свес в коридор, сверху — через торец, длинный в комнату.
    Сетка: столбцы по ширине (y), строки — по пути ткани от края в коридоре до нижнего края в комнате."""
    tm = M["towel"]
    ty0, ty1 = 0.045, 0.805                    # на фото полотенце чуть уже двери, у петель виден край створки
    NY, top = 18, Z1 + 0.006
    back_len, front_len = 0.26, 1.20           # свес в коридор / в комнату (низ около 0.82 м: ручку не видно, как на фото)
    gap = 0.012
    # путь в плоскости (x, z): параметр s — длина вдоль ткани
    path = []
    nb, nt_, nf = 6, 4, 26
    for i in range(nb + 1):                                                            # сторона коридора, снизу вверх
        path.append((T + gap, top - back_len * (1 - i / nb), "back", i / nb))
    for i in range(1, nt_):                                                            # через торец
        a = math.pi * i / nt_
        path.append((T / 2 + (T / 2 + gap) * math.cos(a), top + 0.006 * math.sin(a), "top", 0))
    for i in range(nf + 1):                                                            # сторона комнаты, сверху вниз
        path.append((-gap, top - front_len * i / nf, "front", i / nf))
    S = [0.0]
    for k in range(1, len(path)):
        S.append(S[-1] + math.hypot(path[k][0] - path[k - 1][0], path[k][1] - path[k - 1][1]))
    total = S[-1]
    ph = (5.569455185187808, 1.881138401198921, 1.0948766503375371, 0.05247816283283724)   # фазы складок (как были)
    grid = []
    for j in range(NY + 1):
        y = ty0 + (ty1 - ty0) * j / NY
        yn = (y - ty0) / (ty1 - ty0)
        col = []
        for k, (x, z, part, t) in enumerate(path):
            if part == "front":
                # складки: вдоль, к низу глубже; по краям ткань чуть заворачивается к двери
                amp = 0.004 + 0.022 * t ** 1.4
                fold = 0.5 + 0.5 * math.sin(2 * math.pi * yn * 5.3 + ph[0]) * math.cos(2 * math.pi * yn * 2.1 + ph[1])
                x2 = x - amp * fold - 0.004 * t
                edge = min(yn, 1 - yn)
                if edge < 0.06:
                    x2 += (0.06 - edge) / 0.06 * 0.010 * t
                # неровный нижний край: провисает между складками, с одной стороны длиннее (как на фото)
                z2 = z - t * (0.008 * math.sin(2 * math.pi * yn * 1.3 + ph[2]) + 0.03 * (1 - yn) + 0.006 * fold)
                # бугор над штапиком и ручкой стекла — ткань чуть отходит
                if 1.0 < z2 < 1.9 and 0.13 < y < 0.71:
                    x2 -= 0.003
                # под полотенцем — ручка: ткань оттопыривается бугром (на фото ручки не видно)
                dh = math.hypot((y - (HANDLE_Y - 0.05)) / 0.11, (z2 - HANDLE_Z) / 0.16)
                if dh < 1.0:
                    x2 -= 0.058 * (1 - dh * dh) ** 1.5
                col.append(Vector((x2, y, z2)))
            elif part == "back":
                amp = 0.004 * (1 - t)
                fold = math.sin(2 * math.pi * yn * 4.1 + ph[3])
                col.append(Vector((x + amp * (0.5 + 0.5 * fold), y, z - (1 - t) * 0.015 * fold)))
            else:
                col.append(Vector((x, y, z)))
        grid.append(col)
    nrow = len(path)
    for j in range(NY):
        for k in range(nrow - 1):
            a, b_, c, d = grid[j][k], grid[j + 1][k], grid[j + 1][k + 1], grid[j][k + 1]
            uv = [(j / NY, S[k] / total), ((j + 1) / NY, S[k] / total), ((j + 1) / NY, S[k + 1] / total), (j / NY, S[k + 1] / total)]
            b.poly([a, b_, c, d], uv, tm)                                               # лицевая
            b.poly([d, c, b_, a], uv[::-1], tm)                                         # изнанка — ткань видна с обеих сторон


def main():
    # своя сцена, чтобы не трогать комнату и подъезд, открытые в Blender
    if bpy.context.window:
        sc = bpy.data.scenes.get("RoomDoor") or bpy.data.scenes.new("RoomDoor")
        bpy.context.window.scene = sc
    else:                                          # фоновый запуск (-b): чистая сцена по умолчанию
        sc = bpy.context.scene
    for ob in list(sc.objects):
        if ob.type == 'MESH':
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in [m for m in bpy.data.meshes if m.name.startswith("RoomDoor_nocol") and m.users == 0]:
        bpy.data.meshes.remove(me)                 # иначе новый меш получит имя .001, и оно уйдёт в glTF
    tex_paint(); tex_glass(); tex_towel(); tex_metal()
    M = {"paint": mat("RdPaint", "rd_paint", rough=0.6), "glass": mat("RdGlass", "rd_glass", rough=0.2),
         "towel": mat("RdTowel", "rd_towel", rough=1.0), "metal": mat("RdMetal", "rd_metal", rough=0.45, metal=0.6)}
    b = B()
    leaf(b, M)
    towel(b, M)
    ob = b.build("RoomDoor_nocol", sc.collection)
    # Створка — плоские грани: гладкое затенение только у полотенца
    for poly in ob.data.polygons:
        poly.use_smooth = ob.data.materials[poly.material_index].name == "RdTowel"
    for o in sc.objects:
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob if bpy.context.view_layer.objects.get(ob.name) else None
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "room_door.gltf"), use_selection=True, use_active_scene=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    return {"polys": len(ob.data.polygons)}


RESULT = main()
print("BUILD_ROOM_DOOR", RESULT)
