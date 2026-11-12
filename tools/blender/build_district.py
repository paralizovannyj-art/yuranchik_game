# Дома микрорайона «Паскот» (этап B, docs/CITY_PLAN.md): параметрическая сборка low-poly моделей
# ровно по габаритам серых блоков. Список домов — tools/district_buildings.json
# (его пишет tools/make_district_blockout.py --json-only). Результат — assets/models/district/<id>.gltf
# и сцена «District» в Blender (дома разложены в ряд), сохраняется в tools/blender/district.blend.
#
# v2: ОБЪЁМНЫЕ фасады — окна утоплены в стену, выступают лестничные клетки, карнизы, навесы,
# у хрущёвок скатные крыши, вдоль стен снежные откосы.
#
# Запуск в открытом Blender (через Blender MCP или вкладку Scripting):
#   DISTRICT_ROOT = r"<папка проекта>"; exec(open(DISTRICT_ROOT + r"\tools\blender\build_district.py", encoding="utf-8").read())
# или без окна:  blender -b --python tools/blender/build_district.py
# Текстуры (один раз или после правок):  blender -b --python tools/blender/district_textures.py
#
# Модель: длина L вдоль X, фасад с подъездами смотрит в −Y Blender (= +Z Godot), точка опоры — центр низа.
# В Godot дом ставится в (cx, y, cz) с поворотом yaw из json.
import bpy
import json
import math
import os
import random

ROOT = globals().get("DISTRICT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
OUT = os.path.join(ROOT, "assets", "models", "district")

# построитель мешей и материалы двора — из build_yard.py (без его main)
ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), ns)
ns["TEX"] = os.path.join(ROOT, "assets", "textures")
B, mat, M = ns["B"], ns["mat"], ns["M"]
ns["build_materials"]()
M["facade_b"] = mat("FacadeB", "facade_b_albedo", "facade_b_emission")
M["facade_c"] = mat("FacadeC", "facade_c_albedo", "facade_c_emission")
M["khr"] = mat("Khr", "khr_albedo", "khr_emission")
M["school"] = mat("School", "school_albedo", "school_emission")
M["brick"] = mat("BrickDark", "brick_dark")
M["indwin"] = mat("IndWindow", "ind_window", "ind_window_emission")
M["shop"] = mat("Shopfront", "shopfront", "shopfront_emission")

CELL = 2.7          # ширина одного окна на фасаде, м
RECESS = 0.2        # насколько окно утоплено в стену
# где в ячейке текстуры нарисовано окно: (слева, справа, низ, верх) в долях ячейки
WIN = {"panel": (10 / 64, 54 / 64, 1 - 46 / 64, 1 - 14 / 64), "khr": (14 / 64, 50 / 64, 1 - 46 / 64, 1 - 16 / 64),
       "school": (6 / 64, 58 / 64, 1 - 56 / 72, 1 - 16 / 72)}
SNOW_FACES = ('+X', '-X', '+Y', '-Y', '+Z')


def block(name, coll, seed, L, D, NF, FH, PL, fmat, rows, arches=(), entrances=None, kind="panel"):
    """Дом: рельефные фасады (окна в нишах), арки сквозь первый этаж, лестничные клетки, балконы, крыша в снегу."""
    r = random.Random(seed)
    b = B()
    hw, hd = L / 2, D / 2
    top = PL + FH * NF
    AT = PL + FH                                    # верх арки = граница 1-го и 2-го этажа
    brick = kind in ("khr", "boiler")
    wall = M["brick"] if brick else M["wall"]
    wscale = (2.5, 2.5) if brick else (5.4, 5.6)
    school = kind.startswith("school")
    all_facade = kind == "tower" or school
    win = WIN["khr" if kind == "khr" else "school" if school else "panel"]

    # --- развёртка стороны: (t вдоль стены слева направо для смотрящего, i вглубь дома, z) → точка ---
    def pos(side, t, i, z, a, c):
        if side == "F":
            return (a + t, -hd + i, z)
        if side == "B":
            return (c - t, hd - i, z)
        if side == "R":
            return (hw - i, a + t, z)
        return (-hw + i, c - t, z)

    def facade(side, a, c, fl0, m=None):
        """Сетка ячеек-окон на участке стены a..c начиная с этажа fl0; окно каждой ячейки утоплено."""
        m = m or fmat
        n = max(1, int((c - a) / CELL + 0.75))
        w = (c - a) / n
        io, vo = r.randint(0, 7), (0 if school else r.randint(0, rows - 1))
        P = lambda t, i, z: pos(side, t, i, z, a, c)
        for ci in range(n):
            t0, t1 = ci * w, (ci + 1) * w
            ku = (ci + io) % 8
            wt0, wt1 = t0 + w * win[0], t0 + w * win[1]
            for fl in range(fl0, NF):
                z0 = PL + fl * FH
                z1 = z0 + FH
                rb = (fl + vo) % rows
                wz0, wz1 = z0 + FH * win[2], z0 + FH * win[3]
                uv = lambda t, z: ((ku + (t - t0) / w) / 8.0, (rb + (z - z0) / FH) / rows)

                def q(ta, tb, za, zb, i=0.0):
                    b.poly([P(ta, i, za), P(tb, i, za), P(tb, i, zb), P(ta, i, zb)],
                           [uv(ta, za), uv(tb, za), uv(tb, zb), uv(ta, zb)], m)
                q(t0, t1, z0, wz0); q(t0, t1, wz1, z1); q(t0, wt0, wz0, wz1); q(wt1, t1, wz0, wz1)
                q(wt0, wt1, wz0, wz1, RECESS)                                     # стекло в нише
                d = RECESS
                ruv = [(0.02, 0.02), (0.06, 0.02), (0.06, 0.2), (0.02, 0.2)]
                b.poly([P(wt0, 0, wz0), P(wt0, d, wz0), P(wt0, d, wz1), P(wt0, 0, wz1)], ruv, wall)   # откосы
                b.poly([P(wt1, d, wz0), P(wt1, 0, wz0), P(wt1, 0, wz1), P(wt1, d, wz1)], ruv, wall)
                b.poly([P(wt0, 0, wz0), P(wt1, 0, wz0), P(wt1, d, wz0), P(wt0, d, wz0)], ruv, M["snow"] if side in "FB" else wall)
                b.poly([P(wt0, d, wz1), P(wt1, d, wz1), P(wt1, 0, wz1), P(wt0, 0, wz1)], ruv, wall)

    # --- сплошные участки и арки вдоль дома ---
    segs, cur = [], -hw
    for a, c in sorted(arches) + [(hw, hw)]:
        if a > cur + 0.01:
            segs.append((cur, a))
        cur = max(cur, c)
    shop = kind == "north"
    for a, c in segs:
        facade("F", a, c, 1 if shop else 0)
        if shop:
            n = max(1, int((c - a) / CELL + 0.75))
            uo = r.randint(0, 7) / 8.0
            b.poly([(a, -hd, 0), (c, -hd, 0), (c, -hd, AT), (a, -hd, AT)],
                   [(uo, 0), (uo + n / 8.0, 0), (uo + n / 8.0, 1), (uo, 1)], M["shop"])
            b.box((a, -hd - 0.9, AT - 0.12), (c, -hd, AT), {k: M["plinth"] for k in ('-Y', '-Z', '+X', '-X')}, scale=(3.6, 0.9))   # козырёк над витринами
            b.box((a, -hd - 0.9, AT), (c, -hd, AT + 0.14), {k: M["snow"] for k in ('-Y', '+Z', '+X', '-X')}, scale=(3, 3))
        else:
            facade("B", a, c, 0)
            faces = {'-Y': M["plinth"], '+Y': M["plinth"]}
            if a <= -hw + 0.01:
                faces['-X'] = M["plinth"]
            if c >= hw - 0.01:
                faces['+X'] = M["plinth"]
            b.box((a - (0.06 if '-X' in faces else 0), -hd - 0.06, 0), (c + (0.06 if '+X' in faces else 0), hd + 0.06, PL),
                  faces, scale=(3.6, 0.9))
            b.box((a, -hd - 0.06, PL - 0.02), (c, hd + 0.06, PL), {'+Z': M["plinth"]}, scale=(3.6, 0.9))
    for a, c in arches:
        facade("F", a, c, 1)
        facade("B", a, c, 1)
        b.box((a - 0.02, -hd - 0.06, 0), (a, hd + 0.06, AT), {'+X': M["wall"]}, scale=(5.4, 5.6))
        b.box((c, -hd - 0.06, 0), (c + 0.02, hd + 0.06, AT), {'-X': M["wall"]}, scale=(5.4, 5.6))
        b.box((a, -hd, AT), (c, hd, AT + 0.02), {'-Z': M["wall"]}, scale=(5.4, 5.6))
        for ya, yb in ((-hd - 0.25, -hd), (hd, hd + 0.25)):                      # портал арки выступает из стены
            b.box((a - 0.45, ya, 0), (a, yb, AT + 0.45), {k: M["plinth"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(3.6, 0.9))
            b.box((c, ya, 0), (c + 0.45, yb, AT + 0.45), {k: M["plinth"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(3.6, 0.9))
            b.box((a, ya, AT), (c, yb, AT + 0.45), {k: M["plinth"] for k in ('+Y', '-Y', '-Z')}, scale=(3.6, 0.9))
            b.box((a - 0.45, ya, AT + 0.45), (c + 0.45, yb, AT + 0.6), {k: M["snow"] for k in SNOW_FACES}, scale=(3, 3))
    # --- торцы ---
    if all_facade:
        facade("R", -hd, hd, 0)
        facade("L", -hd, hd, 0)
    else:
        b.box((-hw, -hd, PL), (hw, hd, top), {'+X': wall, '-X': wall}, scale=wscale)
        if not brick:                                                             # пояса перекрытий на глухих торцах панелек
            for fl in range(1, NF):
                z = PL + fl * FH
                for x0, x1 in ((-hw - 0.05, -hw), (hw, hw + 0.05)):
                    b.box((x0, -hd, z - 0.07), (x1, hd, z + 0.07), {k: M["plinth"] for k in ('+X', '-X', '+Z', '-Z')}, scale=(3.6, 0.9))

    # --- подъезды (их положения нужны и крыше, и балконам) ---
    if entrances is None and kind == "school_main":
        entrances = [0.0]
    if entrances is None and kind in ("panel", "khr", "tower"):
        n = max(1, round(L / 12.5))
        entrances = [-hw + L * (i + 0.5) / n for i in range(n)]
    entrances = [x for x in (entrances or []) if all(not (a - 2.6 < x < c + 2.6) for a, c in arches)]

    # --- крыша ---
    if kind == "khr":                                                             # вальмовая крыша под снегом, свес 0,4 м
        e, rh = 0.4, 1.7
        b.box((-hw - e, -hd - e, top - 0.12), (hw + e, hd + e, top), {k: M["plinth"] for k in ('+X', '-X', '+Y', '-Y', '-Z')}, scale=(3.6, 0.9))
        x0, x1, y0, y1 = -hw - e, hw + e, -hd - e, hd + e
        rx = max(0.5, hw - hd)                                                    # половина длины конька
        A, Bq, C, Dq = (x0, y0, top), (x1, y0, top), (x1, y1, top), (x0, y1, top)
        R0, R1 = (-rx, 0, top + rh), (rx, 0, top + rh)
        su = lambda p: (p[0] / 3.0, (p[1] + p[2]) / 3.0)
        for pts in ([A, Bq, R1, R0], [C, Dq, R0, R1], [Bq, C, R1], [Dq, A, R0]):
            b.poly(pts, [su(p) for p in pts], M["snow"])
        for x in (-rx * 0.5, rx * 0.5):                                           # вентиляционные трубы
            b.box((x - 0.4, -0.4, top + rh - 0.5), (x + 0.4, 0.4, top + rh + 0.9), {k: M["brick"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(2.5, 2.5))
            b.box((x - 0.45, -0.45, top + rh + 0.9), (x + 0.45, 0.45, top + rh + 1.05), {k: M["snow"] for k in SNOW_FACES}, scale=(3, 3))
    else:
        b.box((-hw, -hd, PL), (hw, hd, top), {'+Z': M["snow"]}, scale=(6, 6))
        b.box((-hw - 0.3, -hd - 0.3, top - 0.18), (hw + 0.3, hd + 0.3, top),                     # карниз
              {k: M["plinth"] for k in ('+X', '-X', '+Y', '-Y', '-Z')}, scale=(3.6, 0.9))
        for (mn, mx) in [((-hw - .3, -hd - .3, top), (hw + .3, -hd - .05, top + .7)),
                         ((-hw - .3, hd + .05, top), (hw + .3, hd + .3, top + .7)),
                         ((-hw - .3, -hd - .05, top), (-hw - .05, hd + .05, top + .7)),
                         ((hw + .05, -hd - .05, top), (hw + .3, hd + .05, top + .7))]:
            b.box(mn, mx, {k: M["wall"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(5.4, 5.6))
            b.box(mn, mx, {'+Z': M["snow"]}, scale=(3, 3))
        for i in range(max(1, int(L // 14))):                                     # вентшахты на крыше
            x = -hw + L * (i + 0.5) / max(1, int(L // 14)) + r.uniform(-1.5, 1.5)
            b.box((x - 0.8, 1.5, top), (x + 0.8, 3.0, top + 1.4), {k: M["wall"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(5.4, 5.6))
            b.box((x - 0.9, 1.4, top + 1.4), (x + 0.9, 3.1, top + 1.58), {k: M["snow"] for k in SNOW_FACES}, scale=(3, 3))

    # --- подъезд: лестничная клетка выступает из фасада на всю высоту ---
    wide = 2.0 if kind == "school_main" else 0.7
    for x in entrances:
        y0 = -hd - 0.55
        bw = wide + 0.8
        if kind == "school_main":                                                 # крыльцо школы: навес на двух столбах
            b.box((x - 3.2, -hd - 3.0, 0), (x + 3.2, -hd, 0.45), {k: M["plinth"] for k in ('+X', '-X', '-Y', '+Z')}, scale=(3.6, 0.9))
            b.box((x - 4.0, -hd - 3.6, 0), (x + 4.0, -hd - 3.0, 0.22), {k: M["plinth"] for k in ('+X', '-X', '-Y', '+Z')}, scale=(3.6, 0.9))
            for cx_ in (x - 2.8, x + 2.8):
                b.box((cx_ - 0.2, -hd - 2.9, 0.45), (cx_ + 0.2, -hd - 2.5, 3.4), {k: M["wall"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(5.4, 5.6))
            b.box((x - 3.4, -hd - 3.2, 3.4), (x + 3.4, -hd, 3.65), {k: M["plinth"] for k in ('+X', '-X', '-Y', '-Z')}, scale=(3.6, 0.9))
            b.box((x - 3.4, -hd - 3.2, 3.65), (x + 3.4, -hd, 3.85), {k: M["snow"] for k in SNOW_FACES}, scale=(3, 3))
            for k in range(2):
                xa = x - wide + k * wide
                b.box((xa, -hd - 0.04, 0.45), (xa + wide, -hd, 2.75), {'-Y': (M["door"], (0, 0, 1, 1))})
            continue
        bay_top = top + (2.9 if NF >= 9 else 0.0)                                 # у высоток клетка переходит в машинное отделение лифта
        b.box((x - bw, y0, 0), (x + bw, -hd, bay_top), {'+X': wall, '-X': wall}, scale=wscale)
        b.box((x - bw, y0, 2.6), (x + bw, -hd, bay_top), {'-Y': wall}, scale=wscale)
        b.box((x - bw, y0, 0), (x - wide, -hd, 2.6), {'-Y': wall}, scale=wscale)
        b.box((x + wide, y0, 0), (x + bw, -hd, 2.6), {'-Y': wall}, scale=wscale)
        b.box((x - wide, y0, 2.2), (x + wide, -hd, 2.6), {'-Y': wall}, scale=wscale)
        b.box((x - wide, y0 + 0.08, 0), (x + wide, -hd, 2.2), {'-Y': (M["door"], (0, 0, 1, 1))})
        for fl in range(1, NF):                                                   # окна лестничных площадок
            z = PL + fl * FH - 0.9
            b.box((x - 0.6, y0 - 0.03, z), (x + 0.6, y0, z + 1.2), {'-Y': (M["balcony"], (0.52, 0.5, 0.98, 0.95))})
        if NF >= 9:
            b.box((x - bw, -hd, top), (x + bw, 2.5, bay_top), {k: wall for k in ('+X', '-X', '+Y')}, scale=wscale)
            b.box((x - bw - 0.1, y0 - 0.1, bay_top), (x + bw + 0.1, 2.6, bay_top + 0.2), {k: M["snow"] for k in SNOW_FACES + ('-Z',)}, scale=(3, 3))
        else:
            b.box((x - bw - 0.1, y0 - 0.1, bay_top), (x + bw + 0.1, -hd, bay_top + 0.2), {k: M["snow"] for k in SNOW_FACES}, scale=(3, 3))
        # козырёк, ступени, боковые стенки крыльца
        b.box((x - bw - 0.3, -hd - 2.1, 2.6), (x + bw + 0.3, y0, 2.78), {k: M["plinth"] for k in ('+X', '-X', '-Y', '-Z')}, scale=(3.6, 0.9))
        b.box((x - bw - 0.3, -hd - 2.1, 2.78), (x + bw + 0.3, y0, 2.98), {k: M["snow"] for k in ('+Z', '-Y', '+X', '-X')}, scale=(3, 3))
        b.box((x - bw, -hd - 1.9, 0), (x + bw, y0, 0.16), {k: M["plinth"] for k in ('+X', '-X', '-Y', '+Z')}, scale=(3.6, 0.9))
        for sx in (x - bw - 0.15, x + bw):
            b.box((sx, -hd - 1.9, 0), (sx + 0.15, y0, 1.0), {k: M["plinth"] for k in ('+X', '-X', '-Y', '+Z')}, scale=(3.6, 0.9))

    # --- балконы: на фасаде часто, сзади реже ---
    def balcony(x, z, front, glazed):
        ya = -hd if front else hd
        yb = ya - 1.1 if front else ya + 1.1
        lo, hi = min(ya, yb), max(ya, yb)
        out = '-Y' if front else '+Y'
        b.box((x - 1.3, lo, z - 0.12), (x + 1.3, hi, z), {k: M["plinth"] for k in ('+X', '-X', out, '-Z')}, scale=(3.6, 0.9))
        b.box((x - 1.3, lo, z), (x + 1.3, hi, z + 0.04), {'+Z': M["snow"]}, scale=(3, 3))
        hgt = 2.55 if glazed else 1.05
        rect = (0.5, 0, 1, 1) if glazed else (0, 0, 0.5, 1)
        yo = yb if front else yb - 0.06
        b.box((x - 1.3, yo, z), (x + 1.3, yo + 0.06, z + hgt), {'-Y': (M["balcony"], rect), '+Y': (M["balcony"], rect)})
        for sx in (x - 1.3, x + 1.24):
            b.box((sx, lo, z), (sx + 0.06, hi, z + hgt), {'+X': (M["balcony"], (0, 0, 0.2, 1)), '-X': (M["balcony"], (0, 0, 0.2, 1))})
        if glazed:
            b.box((x - 1.35, lo - 0.05, z + hgt), (x + 1.35, hi + 0.05, z + hgt + 0.08), {k: M["metal"] for k in (out, '+Z', '-Z', '+X', '-X')}, scale=(1, 1))

    if kind in ("panel", "khr", "tower"):
        glaze_p = 0.2 if kind == "khr" else 0.45
        n = max(1, int(L / CELL + 0.75))
        cw = L / n
        for front in (True, False):
            for ci in range(n):
                if ci % (4 if front else 6) != (1 if front else 3):
                    continue
                x = -hw + (ci + 0.5) * cw
                if any(a - 0.2 < x < c + 0.2 for a, c in arches):
                    continue
                if front and any(abs(x - e) < 3.2 for e in entrances):
                    continue
                for fl in range(1, NF):
                    balcony(x, PL + fl * FH, front, r.random() < glaze_p)

    # --- снежные откосы вдоль стен (район завалило), с разрывами у подъездов и арок ---
    if kind != "north":
        for front in (True, False):
            ys = -hd if front else hd
            yo = ys - 1.0 if front else ys + 1.0
            gaps = sorted([(a - 0.5, c + 0.5) for a, c in arches] + ([(e - 2.6, e + 2.6) for e in entrances] if front else []))
            cur = -hw
            for a, c in gaps + [(hw, hw)]:
                if a > cur + 0.6:
                    h0 = 0.45 + r.random() * 0.35
                    p = [(cur, yo, 0), (a, yo, 0), (a, ys, h0), (cur, ys, h0)]
                    if not front:
                        p = [p[1], p[0], p[3], p[2]]
                    b.poly(p, [(q_[0] / 3.0, q_[1] / 3.0 + q_[2]) for q_ in p], M["snow"])
                cur = max(cur, c)

    # --- мелочи: кондиционеры, водостоки, антенны ---
    if kind in ("panel", "khr", "tower", "north"):
        n = max(1, int(L / CELL + 0.75))
        cw = L / n
        for i in range(max(2, n // 3)):
            ci = r.randint(0, n - 1); fl = r.randint(1, NF - 1)
            x = -hw + (ci + 0.5) * cw + 0.95; z = PL + fl * FH + 0.3
            if ci % 4 == 1 or any(abs(x - e) < 2.0 for e in entrances):
                continue
            b.box((x - 0.4, -hd - 0.3, z), (x + 0.4, -hd, z + 0.5), {k: M["metal"] for k in ('-Y', '+X', '-X', '+Z', '-Z')}, scale=(0.8, 0.55))
        for x in (-hw + 0.3, hw - 0.3):
            b.cyl((x, -hd - 0.12, 0.2), (x, -hd - 0.12, top), 0.07, 0.07, M["metal"], segs=6, su=2)
        if kind != "khr":
            for i in range(max(2, n // 4)):
                x = r.uniform(-hw + 1, hw - 1); y = r.uniform(-hd + 1, 0.5); h = r.uniform(1.5, 3.0)
                b.cyl((x, y, top), (x, y, top + h), 0.025, 0.02, M["metal"], segs=4)
                b.cyl((x - 0.6, y, top + h - 0.3), (x + 0.6, y, top + h - 0.3), 0.015, 0.015, M["metal"], segs=4)
    return b.build(name, coll)


def boiler(name, coll, seed, L, D, H):
    """Котельная: закопчённый кирпич, пилястры, высокие заводские окна в нишах с отсветом топки, фонарь на крыше."""
    b = B()
    hw, hd = L / 2, D / 2
    BR = {k: M["brick"] for k in ('+X', '-X', '+Y', '-Y')}
    b.box((-hw, -hd, 0), (hw, hd, H), BR, scale=(2.5, 2.5))
    b.box((-hw, -hd, 0), (hw, hd, H), {'+Z': M["snow"]}, scale=(6, 6))
    b.box((-hw - 0.25, -hd - 0.25, H - 0.3), (hw + 0.25, hd + 0.25, H + 0.5), {k: M["plinth"] for k in ('+X', '-X', '+Y', '-Y', '-Z')}, scale=(3.6, 0.9))
    b.box((-hw - 0.25, -hd - 0.25, H + 0.5), (hw + 0.25, hd + 0.25, H + 0.62), {k: M["snow"] for k in SNOW_FACES}, scale=(4, 4))
    n = max(2, int(L // 6))
    for i in range(n + 1):                                                        # пилястры
        x = -hw + L * i / n
        for ya, yb in ((-hd - 0.35, -hd), (hd, hd + 0.35)):
            b.box((x - 0.35, ya, 0), (x + 0.35, yb, H - 0.3), BR, scale=(2.5, 2.5))
    for i in range(n):
        x = -hw + L * (i + 0.5) / n
        if i == n // 2:                                                           # ворота вместо окна
            b.box((x - 1.8, -hd - 0.06, 0), (x + 1.8, -hd, 3.6), {'-Y': (M["gdoor"], (0.75, 0, 1, 1))})
            b.box((x - 2.1, -hd - 0.8, 3.6), (x + 2.1, -hd, 3.8), {k: M["snow"] for k in SNOW_FACES + ('-Z',)}, scale=(3, 3))
        else:
            b.box((x - 1.6, -hd - 0.05, 3.0), (x + 1.6, -hd, 7.5), {'-Y': (M["indwin"], (0, 0, 1, 1))})
            b.box((x - 1.75, -hd - 0.3, 2.85), (x + 1.75, -hd, 3.0), {k: M["snow"] for k in SNOW_FACES}, scale=(3, 3))
        b.box((x - 1.6, hd, 3.0), (x + 1.6, hd + 0.05, 7.5), {'+Y': (M["indwin"], (0, 0, 1, 1))})
        b.box((x - 1.75, hd, 2.85), (x + 1.75, hd + 0.3, 3.0), {k: M["snow"] for k in SNOW_FACES}, scale=(3, 3))
    for y in (-hd / 2, hd / 2):
        b.box((hw, y - 1.5, 3.0), (hw + 0.05, y + 1.5, 7.5), {'+X': (M["indwin"], (0, 0, 1, 1))})
    # фонарь (световая надстройка) вдоль крыши
    b.box((-hw + 3, -2.5, H), (hw - 3, 2.5, H + 2.2), BR, scale=(2.5, 2.5))
    b.box((-hw + 2.8, -2.7, H + 2.2), (hw - 2.8, 2.7, H + 2.4), {k: M["snow"] for k in SNOW_FACES + ('-Z',)}, scale=(4, 4))
    # пристройка и вентиляционные трубы
    b.box((-hw - 3.0, -hd + 2, 0), (-hw, -hd + 9, 4.0), {k: M["brick"] for k in ('-X', '+Y', '-Y')}, scale=(2.5, 2.5))
    b.box((-hw - 3.2, -hd + 1.8, 4.0), (-hw, -hd + 9.2, 4.25), {k: M["snow"] for k in SNOW_FACES + ('-Z',)}, scale=(4, 4))
    for x in (-hw + 5, hw - 6):
        b.cyl((x, 4.5, H), (x, 4.5, H + 4.0), 0.45, 0.45, M["metal"], segs=8, caps=True, su=2)
    return b.build(name, coll)


def chimney(name, coll, H):
    """Кирпичная труба: сужается кверху, стальные бандажи, скобы-лестница, площадка у верха."""
    b = B()
    r0, r1 = 1.95, 1.1
    b.box((-2.0, -2.0, 0), (2.0, 2.0, 3.0), {k: M["brick"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(2.5, 2.5))
    b.box((-2.0, -2.0, 0), (2.0, 2.0, 3.0), {'+Z': M["snow"]}, scale=(3, 3))
    b.cyl((0, 0, 3.0), (0, 0, H), r0, r1, M["brick"], segs=10, su=3)
    for z in range(8, int(H), 6):
        rr = r0 + (r1 - r0) * (z - 3.0) / (H - 3.0) + 0.04
        b.cyl((0, 0, z), (0, 0, z + 0.25), rr, rr, M["metal"], segs=10, su=1)
    b.cyl((0, 0, H - 4.0), (0, 0, H - 3.85), r1 + 0.9, r1 + 0.9, M["metal"], segs=10, caps=True, su=1)   # площадка
    b.cyl((0, 0, H), (0, 0, H + 0.4), r1 + 0.12, r1 + 0.12, M["metal"], segs=10, caps=True, su=1)
    b.box((-0.25, -r0 - 0.1, 3.0), (0.25, -r0 + 0.9, H - 4.0), {'-Y': M["metal"]}, scale=(0.5, 0.5))       # скобы
    return b.build(name, coll)


TYPES = {   # тип → (этажей, высота этажа, цоколь, материал фасада, рядов в текстуре)
    "panel": (9, 2.8, 0.9, ("facade", "facade_b"), 9),
    "north": (9, 2.8, 0.9, ("facade", "facade_b"), 9),
    "tower": (16, 2.8, 0.9, ("facade_c",), 8),
    "khr": (5, 2.8, 0.9, ("khr",), 5),
    "school_main": (3, 3.3, 1.0, ("school",), 3),
    "school_wing": (3, 3.3, 1.0, ("school",), 3),
}


def main():
    specs = json.load(open(os.path.join(ROOT, "tools", "district_buildings.json"), encoding="utf-8"))
    if bpy.app.background:
        sc = bpy.context.scene                      # без окна экспорт работает только с текущей сценой
    else:
        sc = bpy.data.scenes.get("District") or bpy.data.scenes.new("District")
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    if bpy.context.window:
        bpy.context.window.scene = sc
    os.makedirs(OUT, exist_ok=True)
    stats, obs = {}, []
    for i, s in enumerate(specs):
        coll = sc.collection
        t = s["type"]
        if t == "boiler":
            ob = boiler(s["id"], coll, i, s["L"], s["D"], s["h"])
        elif t == "chimney":
            ob = chimney(s["id"], coll, s["h"])
        else:
            NF, FH, PL, mats, rows = TYPES[t]
            fm = M[mats[i % len(mats)]]
            ob = block(s["id"], coll, 100 + i, s["L"], s["D"], NF, FH, PL, fm, rows,
                       arches=[tuple(a) for a in s["arches"]], entrances=s["entrances"], kind=t)
        stats[s["id"]] = len(ob.data.polygons)
        obs.append((ob, s))
    vl = sc.view_layers[0]
    for other in bpy.data.scenes:                   # в других сценах ничего не должно быть выделено, иначе попадёт в экспорт
        for layer in other.view_layers:
            for o in other.objects:
                o.select_set(False, view_layer=layer)
    for ob, s in obs:
        for o in sc.objects:
            o.select_set(False, view_layer=vl)
        ob.select_set(True, view_layer=vl)
        vl.objects.active = ob
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, s["id"] + ".gltf"), use_selection=True, export_keep_originals=True,
                                  export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    # после экспорта расставляем дома так, как они стоят в районе (Godot X → Blender X, Godot Z → Blender −Y)
    for ob, s in obs:
        ob.location = (s["cx"], -s["cz"], s["y"])
        ob.rotation_euler = (0, 0, math.radians(s["yaw"]))
    if not bpy.app.background:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "district.blend"))
    return {"buildings": len(stats), "polys": sum(stats.values()), "max": max(stats.items(), key=lambda kv: kv[1])}


result = main()
print(result)
