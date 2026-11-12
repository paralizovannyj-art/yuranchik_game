# Дома микрорайона «Паскот» (этап B, docs/CITY_PLAN.md): параметрическая сборка low-poly моделей
# ровно по габаритам серых блоков. Список домов — tools/district_buildings.json
# (его пишет tools/make_district_blockout.py --json-only). Результат — assets/models/district/<id>.gltf.
#
# Запуск:  blender -b --python tools/blender/build_district.py
# Сначала (один раз или после правок текстур):  blender -b --python tools/blender/district_textures.py
#
# Модель: длина L вдоль X, фасад с подъездами смотрит в −Y Blender (= +Z Godot), точка опоры — центр низа.
# В Godot дом ставится в (cx, y, cz) с поворотом yaw из json.
import bpy
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
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
ARCH_W_PAD = 0.0


def block(name, coll, seed, L, D, NF, FH, PL, fmat, rows, arches=(), entrances=None, kind="panel"):
    """Дом-параллелепипед: фасады текстурой, арки сквозь первый этаж, подъезды, балконы, крыша в снегу."""
    r = random.Random(seed)
    b = B()
    hw, hd = L / 2, D / 2
    top = PL + FH * NF
    AT = PL + FH                                    # верх арки = граница 1-го и 2-го этажа
    cols = max(1, round(L / CELL))
    cw = L / cols
    colsD = max(1, round(D / CELL))
    cwD = D / colsD
    wall = M["brick"] if kind in ("khr", "boiler") else M["wall"]
    all_facade = kind in ("tower", "school", "school_main")
    uo = r.randint(0, 7) / 8.0
    vo = r.randint(0, rows - 1) / rows if not kind.startswith("school") else 0.0

    def fac(side, a, c, z0, z1, m=fmat, shop=False):
        if shop:
            u = lambda t: t / (cw * 8) + uo
            v = lambda z: z / AT
        else:
            w_ = cw if side in "FB" else cwD
            u = lambda t: t / (w_ * 8) + uo + (0.37 if side in "BL" else 0.0)
            v = lambda z: (z - PL) / (FH * rows) + vo
        if side == "F":
            pts = [(a, -hd, z0), (c, -hd, z0), (c, -hd, z1), (a, -hd, z1)]
            ts = [a + hw, c + hw, c + hw, a + hw]
        elif side == "B":
            pts = [(c, hd, z0), (a, hd, z0), (a, hd, z1), (c, hd, z1)]
            ts = [hw - c, hw - a, hw - a, hw - c]
        elif side == "R":
            pts = [(hw, a, z0), (hw, c, z0), (hw, c, z1), (hw, a, z1)]
            ts = [a + hd, c + hd, c + hd, a + hd]
        else:
            pts = [(-hw, c, z0), (-hw, a, z0), (-hw, a, z1), (-hw, c, z1)]
            ts = [hd - c, hd - a, hd - a, hd - c]
        b.poly(pts, [(u(t), v(p[2])) for t, p in zip(ts, pts)], m)

    # --- сплошные участки и арки вдоль дома ---
    segs, cur = [], -hw
    for a, c in sorted(arches) + [(hw, hw)]:
        if a > cur + 0.01:
            segs.append((cur, a))
        cur = max(cur, c)
    shop = kind == "north"
    base = AT if shop else PL
    for a, c in segs:
        fac("F", a, c, base, top)
        if shop:
            fac("F", a, c, 0, AT, M["shop"], shop=True)
        if kind != "north":
            fac("B", a, c, PL, top)
        faces = {'-Y': M["plinth"], '+Y': M["plinth"]}
        if a <= -hw + 0.01:
            faces['-X'] = M["plinth"]
        if c >= hw - 0.01:
            faces['+X'] = M["plinth"]
        if not shop:
            b.box((a - (0.06 if '-X' in faces else 0), -hd - 0.06, 0), (c + (0.06 if '+X' in faces else 0), hd + 0.06, PL),
                  faces, scale=(3.6, 0.9))
    for a, c in arches:
        fac("F", a, c, AT, top)
        fac("B", a, c, AT, top)
        b.box((a - 0.02, -hd - 0.06, 0), (a, hd + 0.06, AT), {'+X': M["wall"]}, scale=(5.4, 5.6))
        b.box((c, -hd - 0.06, 0), (c + 0.02, hd + 0.06, AT), {'-X': M["wall"]}, scale=(5.4, 5.6))
        b.box((a, -hd, AT), (c, hd, AT + 0.02), {'-Z': M["wall"]}, scale=(5.4, 5.6))
    # --- торцы ---
    if all_facade:
        fac("R", -hd, hd, PL, top)
        fac("L", -hd, hd, PL, top)
    else:
        b.box((-hw, -hd, PL), (hw, hd, top), {'+X': wall, '-X': wall}, scale=(5.4, 5.6) if wall is M["wall"] else (2.5, 2.5))
    # --- крыша в снегу и парапет ---
    b.box((-hw, -hd, PL), (hw, hd, top), {'+Z': M["snow"]}, scale=(6, 6))
    for (mn, mx) in [((-hw - .1, -hd - .1, top), (hw + .1, -hd + .15, top + .6)),
                     ((-hw - .1, hd - .15, top), (hw + .1, hd + .1, top + .6)),
                     ((-hw - .1, -hd, top), (-hw + .15, hd, top + .6)),
                     ((hw - .15, -hd, top), (hw + .1, hd, top + .6))]:
        b.box(mn, mx, {k: M["wall"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(5.4, 5.6))
        b.box(mn, mx, {'+Z': M["snow"]}, scale=(3, 3))

    # --- подъезды ---
    if entrances is None and kind == "school_main":
        entrances = [0.0]
    if entrances is None and kind in ("panel", "khr", "tower"):
        n = max(1, round(L / 12.5))
        entrances = [-hw + L * (i + 0.5) / n for i in range(n)]
    entrances = [x for x in (entrances or []) if all(not (a - 2.2 < x < c + 2.2) for a, c in arches)]
    wide = 2.0 if kind == "school_main" else 0.7
    for x in entrances:
        y0 = -hd - 0.5
        b.box((x - wide - 0.5, y0, 0), (x + wide + 0.5, -hd, 2.6), {'+X': M["wall"], '-X': M["wall"]}, scale=(5.4, 5.6))
        b.box((x - wide - 0.5, y0, 0), (x - wide, -hd, 2.6), {'-Y': M["wall"]}, scale=(5.4, 5.6))
        b.box((x + wide, y0, 0), (x + wide + 0.5, -hd, 2.6), {'-Y': M["wall"]}, scale=(5.4, 5.6))
        b.box((x - wide, y0, 2.2), (x + wide, -hd, 2.6), {'-Y': M["wall"]}, scale=(5.4, 5.6))
        nd = 2 if kind == "school_main" else 1
        for k in range(nd):
            xa = x - wide + k * (2 * wide / nd)
            b.box((xa, y0 + 0.05, 0), (xa + 2 * wide / nd, -hd, 2.2), {'-Y': (M["door"], (0, 0, 1, 1))})
        b.box((x - wide - 0.8, -hd - 1.8, 2.6), (x + wide + 0.8, -hd, 2.78),
              {k: M["plinth"] for k in ('+X', '-X', '-Y', '-Z')}, scale=(3.6, 0.9))
        b.box((x - wide - 0.8, -hd - 1.8, 2.78), (x + wide + 0.8, -hd, 2.95),
              {k: M["snow"] for k in ('+Z', '-Y', '+X', '-X')}, scale=(3, 3))
        b.box((x - wide - 0.7, -hd - 1.6, 0), (x + wide + 0.7, y0, 0.15), {k: M["plinth"] for k in ('+X', '-X', '-Y', '+Z')}, scale=(3.6, 0.9))
        if NF >= 9:                                                   # машинное помещение лифта
            b.box((x - 1.6, -2.0, top), (x + 1.6, 2.5, top + 2.6), {k: M["wall"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(5.4, 5.6))
            b.box((x - 1.7, -2.1, top + 2.6), (x + 1.7, 2.6, top + 2.8), {k: M["snow"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(3, 3))

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
        for front in (True, False):
            if kind == "north" and not front:
                continue
            for ci in range(cols):
                if ci % (4 if front else 6) != (1 if front else 3):
                    continue
                x = -hw + (ci + 0.5) * cw
                if any(a - 1.6 < x < c + 1.6 for a, c in arches):
                    first = 2
                else:
                    first = 1
                if front and any(abs(x - e) < 2.4 for e in entrances):
                    continue
                for fl in range(first, NF):
                    balcony(x, PL + fl * FH, front, r.random() < glaze_p)
    # --- мелочи: кондиционеры, водостоки, антенны ---
    if kind in ("panel", "khr", "tower", "north"):
        for i in range(max(2, cols // 3)):
            ci = r.randint(0, cols - 1); fl = r.randint(1, NF - 1)
            x = -hw + (ci + 0.5) * cw + 0.9; z = PL + fl * FH + 0.4
            if ci % 4 == 1:
                continue
            b.box((x - 0.4, -hd - 0.3, z), (x + 0.4, -hd, z + 0.55), {k: M["metal"] for k in ('-Y', '+X', '-X', '+Z', '-Z')}, scale=(0.8, 0.55))
        for x in (-hw + 0.3, hw - 0.3):
            b.cyl((x, -hd - 0.12, 0.2), (x, -hd - 0.12, top), 0.07, 0.07, M["metal"], segs=6, su=2)
        for i in range(max(2, cols // 4)):
            x = r.uniform(-hw + 1, hw - 1); y = r.uniform(-hd + 1, hd - 1); h = r.uniform(1.5, 3.0)
            b.cyl((x, y, top), (x, y, top + h), 0.025, 0.02, M["metal"], segs=4)
            b.cyl((x - 0.6, y, top + h - 0.3), (x + 0.6, y, top + h - 0.3), 0.015, 0.015, M["metal"], segs=4)
    return b.build(name, coll)


def boiler(name, coll, seed, L, D, H):
    """Котельная: закопчённый кирпич, высокие заводские окна с отсветом топки, ворота, пристройка."""
    b = B()
    hw, hd = L / 2, D / 2
    b.box((-hw, -hd, 0), (hw, hd, H), {k: M["brick"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(2.5, 2.5))
    b.box((-hw, -hd, 0), (hw, hd, H), {'+Z': M["snow"]}, scale=(6, 6))
    b.box((-hw - 0.15, -hd - 0.15, H), (hw + 0.15, hd + 0.15, H + 0.5), {k: M["plinth"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(3.6, 0.9))
    n = max(2, int(L // 6))
    for i in range(n):
        x = -hw + L * (i + 0.5) / n
        if i == n // 2:                                               # ворота вместо окна
            b.box((x - 1.8, -hd - 0.04, 0), (x + 1.8, -hd, 3.6), {'-Y': (M["gdoor"], (0.75, 0, 1, 1))})
        else:
            b.box((x - 1.6, -hd - 0.04, 3.0), (x + 1.6, -hd, 7.5), {'-Y': (M["indwin"], (0, 0, 1, 1))})
        b.box((x - 1.6, hd, 3.0), (x + 1.6, hd + 0.04, 7.5), {'+Y': (M["indwin"], (0, 0, 1, 1))})
    for y in (-hd / 2, hd / 2):
        b.box((hw, y - 1.5, 3.0), (hw + 0.04, y + 1.5, 7.5), {'+X': (M["indwin"], (0, 0, 1, 1))})
    # пристройка и вентиляционные трубы на крыше
    b.box((-hw - 3.0, -hd + 2, 0), (-hw, -hd + 9, 4.0), {k: M["brick"] for k in ('-X', '+Y', '-Y')}, scale=(2.5, 2.5))
    b.box((-hw - 3.0, -hd + 2, 0), (-hw, -hd + 9, 4.0), {'+Z': M["snow"]}, scale=(4, 4))
    for x in (-hw + 4, hw - 5):
        b.cyl((x, 2, H), (x, 2, H + 3.5), 0.45, 0.45, M["metal"], segs=8, caps=True, su=2)
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
    sc = bpy.context.scene
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    os.makedirs(OUT, exist_ok=True)
    stats = {}
    for i, s in enumerate(specs):
        coll = sc.collection
        t = s["type"]
        if t == "boiler":
            ob = boiler(s["id"], coll, i, s["L"], s["D"], s["h"])
        elif t == "chimney":
            ob = chimney(s["id"], coll, s["h"])
        else:
            NF, FH, PL, mats, rows = TYPES[t]
            kind = "school" if t.startswith("school") else t
            fm = M[mats[i % len(mats)]]
            ob = block(s["id"], coll, 100 + i, s["L"], s["D"], NF, FH, PL, fm, rows,
                       arches=[tuple(a) for a in s["arches"]], entrances=s["entrances"],
                       kind="school_main" if t == "school_main" else kind)
        stats[s["id"]] = len(ob.data.polygons)
        for o in sc.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, s["id"] + ".gltf"), use_selection=True, export_keep_originals=True,
                                  export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    for k, v in stats.items():
        print("%-28s %5d polys" % (k, v))
    print("total polys:", sum(stats.values()))


main()
