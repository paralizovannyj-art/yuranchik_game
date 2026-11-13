# Мелкие детали микрорайона «Паскот» (этап F, docs/CITY_PLAN.md): мусор, покрышки, бочки, ящики, баки,
# катушки, кольца, люки, сосульки, объявления, граффити, таблички и вывески (без текста — текст ставит Godot).
#
# Выход:  assets/models/district/details/<модель>.gltf — по одной модели на файл;
#         в Blender: сцена «DistrictDetails» (все модели в ряд).
# Расставляет их tools/apply_district_details.py.
#
# Запуск в открытом Blender (Blender MCP / вкладка Scripting):
#   DISTRICT_ROOT = r"<папка проекта>"; exec(open(DISTRICT_ROOT + r"\tools\blender\build_district_details.py", encoding="utf-8").read())
# Текстуры (один раз):  blender -b --python tools/blender/district_textures_details.py
#
# Оси модели: X — ширина, −Y Blender (= +Z Godot) — «перёд», Z — вверх; опора — центр низа.
# Настенные (объявления, граффити, таблички): центр в начале координат, лицом к −Y.
# Сосульки: начало координат — верхняя кромка, висят вниз. «_nocol» в имени — без коллизии.
import bpy
import json
import math
import os
import random

ROOT = globals().get("DISTRICT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
OUT = os.path.join(ROOT, "assets", "models", "district", "details")

ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), ns)
ns["TEX"] = os.path.join(ROOT, "assets", "textures")
B, mat, M = ns["B"], ns["mat"], ns["M"]
ns["build_materials"]()
M["brick"] = mat("BrickDark", "brick_dark")
M["det"] = mat("Details", "details", "details_emission", rough=0.8)
for key, name, tex in (("graf", "Graffiti", "graffiti"), ("note", "Notices", "notices")):
    M[key] = mat(name, tex)
    nt = M[key].node_tree
    img = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    nt.links.new(img.outputs["Alpha"], nt.nodes["Principled BSDF"].inputs["Alpha"])

R = random.Random(606)
SIDES = ('+X', '-X', '+Y', '-Y')
ALL = SIDES + ('+Z', '-Z')


def A(c, r, pad=0.012):
    """Клетка атласа details: колонка c, ряд r (0 — верхний)."""
    return (M["det"], (c / 4 + pad, 1 - (r + 1) / 4 + pad, (c + 1) / 4 - pad, 1 - r / 4 - pad))


TIRE, BARREL, BAG, BIN = A(0, 0), A(1, 0), A(2, 0), A(3, 0)
CRATE, CARD, CONC, RUST = A(0, 1), A(1, 1), A(2, 1), A(3, 1)
HATCH, BLUE, WHITE, LIGHT = A(0, 2), A(1, 2), A(2, 2), A(3, 2)
ICE, THAW, SPOOL, STEEL = A(0, 3), A(1, 3), A(2, 3), A(3, 3)


def bx(b, x0, y0, z0, x1, y1, z1, m, faces=SIDES + ('+Z',)):
    b.box((min(x0, x1), min(y0, y1), min(z0, z1)), (max(x0, x1), max(y0, y1), max(z0, z1)), {k: m for k in faces}, scale=(3, 3))


def uvr(rect, u, v):
    u0, v0, u1, v1 = rect
    return (u0 + (u1 - u0) * u, v0 + (v1 - v0) * v)


def tube(b, c, z0, z1, ro, ri, m, segs=10, top=True, axis='z'):
    """Кольцо/цилиндр вокруг оси: наружная стенка, внутренняя (если ri > 0) и верх. axis='x' — лежит на боку."""
    mt, rect = m
    P = (lambda a, r, z: (c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2] + z)) if axis == 'z' else \
        (lambda a, r, z: (c[0] + z, c[1] + r * math.cos(a), c[2] + r * math.sin(a)))
    flip = axis == 'x'
    def q(pts, uvs):
        if flip:
            pts, uvs = pts[::-1], uvs[::-1]
        b.poly(pts, uvs, mt)
    for i in range(segs):
        a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
        u0, u1 = i / segs, (i + 1) / segs
        q([P(a0, ro, z0), P(a1, ro, z0), P(a1, ro, z1), P(a0, ro, z1)], [uvr(rect, u0, 0), uvr(rect, u1, 0), uvr(rect, u1, 1), uvr(rect, u0, 1)])
        if ri > 0:
            q([P(a1, ri, z0), P(a0, ri, z0), P(a0, ri, z1), P(a1, ri, z1)], [uvr(rect, u1, 0), uvr(rect, u0, 0), uvr(rect, u0, 1), uvr(rect, u1, 1)])
            for z, rev in ((z1, False), (z0, True)) if top else ():
                pts = [P(a0, ri, z), P(a0, ro, z), P(a1, ro, z), P(a1, ri, z)]
                uvs = [uvr(rect, u0, 0.3), uvr(rect, u0, 0.7), uvr(rect, u1, 0.7), uvr(rect, u1, 0.3)]
                q(pts[::-1] if rev else pts, uvs[::-1] if rev else uvs)
    if ri <= 0 and top:
        for z, rev in ((z1, False), (z0, True)):
            pts = [P(2 * math.pi * i / segs, ro, z) for i in range(segs)]
            uvs = [uvr(rect, 0.5 + 0.5 * math.cos(2 * math.pi * i / segs), 0.5 + 0.5 * math.sin(2 * math.pi * i / segs)) for i in range(segs)]
            q(pts[::-1] if rev else pts, uvs[::-1] if rev else uvs)


def blob(b, c, rx, ry, rz, m, segs=6):
    """Комок (мешок, снежный ком): приплюснутый шар из трёх поясов."""
    mt, rect = m if isinstance(m, tuple) else (m, (0, 0, 1, 1))
    lat = [-0.5 * math.pi, -0.2 * math.pi, 0.2 * math.pi, 0.5 * math.pi]
    P = lambda a, t: (c[0] + rx * math.cos(t) * math.cos(a), c[1] + ry * math.cos(t) * math.sin(a), c[2] + rz * (1 + math.sin(t)))
    for j in range(3):
        for i in range(segs):
            a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
            pts = [P(a0, lat[j]), P(a1, lat[j]), P(a1, lat[j + 1]), P(a0, lat[j + 1])]
            uvs = [uvr(rect, i / segs, j / 3), uvr(rect, (i + 1) / segs, j / 3), uvr(rect, (i + 1) / segs, (j + 1) / 3), uvr(rect, i / segs, (j + 1) / 3)]
            if j == 0:
                pts, uvs = pts[1:], uvs[1:]
            elif j == 2:
                pts, uvs = pts[:3], uvs[:3]
            b.poly(pts, uvs, mt)


def snowcap(b, x0, y0, x1, y1, z, t=0.1):
    bx(b, x0, y0, z, x1, y1, z + t, M["snow"])


def wallquad(b, w, h, m, rect=(0, 0, 1, 1)):
    u0, v0, u1, v1 = rect
    b.poly([(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], m)


# ---------------------------------------------------------------- модели
def tire(b):
    tube(b, (0, 0, 0), 0, 0.2, 0.33, 0.19, TIRE)


def tire_stack(b):
    for i, (dx, dy) in enumerate(((0, 0), (0.05, -0.03), (-0.04, 0.05))):
        tube(b, (dx, dy, 0), i * 0.2, i * 0.2 + 0.2, 0.33, 0.19, TIRE)
    tube(b, (-0.04, 0.05, 0), 0.6, 0.66, 0.31, 0.2, (M["snow"], (0, 0, 1, 1)))


def tire_bed(b):
    """Клумба из покрышки, наполовину в снегу — обычное дело в одесском дворе."""
    tube(b, (0, 0, 0), 0, 0.2, 0.42, 0.27, WHITE)
    tube(b, (0, 0, 0), 0.0, 0.16, 0.27, 0, (M["snow"], (0, 0, 1, 1)))


def barrel(b, c=(0, 0, 0), cap=True):
    tube(b, c, 0, 0.88, 0.29, 0, BARREL, segs=10)
    if cap:
        tube(b, c, 0.88, 0.95, 0.27, 0, (M["snow"], (0, 0, 1, 1)), segs=8)


def barrels(b):
    barrel(b, (-0.35, 0.1, 0))
    barrel(b, (0.3, 0.25, 0))
    tube(b, (-0.2, -0.55, 0.29), 0, 0.88, 0.29, 0, BARREL, segs=10, axis='x')      # третья лежит


def crate(b, c=(0, 0, 0), w=0.8, d=0.55, h=0.5):
    b.box((c[0] - w / 2, c[1] - d / 2, c[2]), (c[0] + w / 2, c[1] + d / 2, c[2] + h), {k: CRATE for k in ALL})


def crate_stack(b):
    crate(b, (-0.45, 0, 0))
    crate(b, (0.45, 0.05, 0), 0.8, 0.6, 0.45)
    crate(b, (0.05, 0, 0.5), 0.7, 0.5, 0.42)
    snowcap(b, -0.3, -0.25, 0.4, 0.25, 0.92, 0.08)
    b.box((-1.1, -0.5, 0), (-0.55, -0.1, 0.4), {k: CARD for k in ALL})                # картонная коробка рядом


def bags(b):
    for (x, y, rx, ry, rz) in ((0, 0, 0.42, 0.36, 0.3), (0.55, 0.15, 0.36, 0.33, 0.26), (0.2, -0.5, 0.33, 0.3, 0.22), (-0.45, -0.25, 0.3, 0.3, 0.2)):
        blob(b, (x, y, 0), rx, ry, rz, BAG)
    b.box((-0.75, 0.25, 0), (-0.3, 0.6, 0.3), {k: CARD for k in ALL})


def dumpster(b):
    w, d, h = 1.3, 0.9, 1.05
    b.box((-w / 2, -d / 2, 0.08), (w / 2, d / 2, h), {k: BIN for k in SIDES})
    b.box((-w / 2, -d / 2, 0.08), (w / 2, d / 2, 0.75), {'+Z': BAG})                 # нутро
    bx(b, -w / 2 - 0.04, -d / 2 - 0.04, h - 0.06, w / 2 + 0.04, d / 2 + 0.04, h, RUST, faces=SIDES + ('-Z',))
    for sx in (-1, 1):                                                               # ножки-полозья
        b.box((sx * (w / 2 - 0.12) - 0.05, -d / 2, 0), (sx * (w / 2 - 0.12) + 0.05, d / 2, 0.08), {k: RUST for k in SIDES})
    blob(b, (-0.2, 0.05, 0.72), 0.4, 0.34, 0.22, BAG)                                # мусор с горкой
    blob(b, (0.3, -0.1, 0.7), 0.34, 0.3, 0.2, BAG)
    snowcap(b, -w / 2 - 0.04, d / 2 - 0.25, w / 2 + 0.04, d / 2 + 0.04, h, 0.07)
    blob(b, (0.95, 0.1, 0), 0.34, 0.3, 0.22, BAG)                                    # и рядом


def spool(b):
    """Кабельная катушка, стоит на ребре; ось вдоль X."""
    for x in (-0.42, 0.34):
        tube(b, (x, 0, 0.85), 0, 0.08, 0.85, 0, SPOOL, segs=12, axis='x')
    tube(b, (-0.34, 0, 0.85), 0, 0.68, 0.36, 0, STEEL, segs=10, top=False, axis='x')
    snowcap(b, -0.42, -0.3, 0.42, 0.3, 1.66, 0.06)


def pallet(b, z=0.0):
    for y in (-0.36, 0, 0.36):
        b.box((-0.6, y - 0.05, z), (0.6, y + 0.05, z + 0.1), {k: CRATE for k in SIDES})
    for i in range(5):
        x = -0.52 + i * 0.26
        b.box((x - 0.09, -0.4, z + 0.1), (x + 0.09, 0.4, z + 0.13), {k: CRATE for k in SIDES + ('+Z',)})


def pallet_stack(b):
    for i in range(4):
        pallet(b, i * 0.14)
    snowcap(b, -0.6, -0.4, 0.6, 0.4, 0.56, 0.08)


def bricks(b):
    for (x0, y0, x1, y1, z0, z1) in ((-0.7, -0.45, 0.7, 0.45, 0, 0.3), (-0.6, -0.35, 0.35, 0.4, 0.3, 0.52), (-0.5, -0.2, 0.0, 0.3, 0.52, 0.7)):
        b.box((x0, y0, z0), (x1, y1, z1), {k: M["brick"] for k in SIDES + ('+Z',)}, scale=(1.2, 1.2))
    snowcap(b, -0.5, -0.2, 0.0, 0.3, 0.7, 0.07)
    snowcap(b, 0.0, -0.35, 0.35, 0.4, 0.52, 0.06)


def ring(b, c=(0, 0, 0)):
    tube(b, c, 0, 0.9, 0.8, 0.68, CONC, segs=12)


def rings(b):
    ring(b, (-0.85, 0, 0))
    ring(b, (0.85, 0.1, 0))
    tube(b, (-0.45, -1.75, 0.8), 0, 0.9, 0.8, 0.68, CONC, segs=12, axis='x')          # третье лежит на боку
    tube(b, (-0.85, 0, 0), 0.9, 0.97, 0.8, 0.68, (M["snow"], (0, 0, 1, 1)), segs=12)


def rebar(b):
    for y in (-1.4, 1.4):
        b.box((-0.25, y - 0.06, 0), (0.25, y + 0.06, 0.1), {k: CRATE for k in SIDES + ('+Z',)})
    for i in range(7):
        x = -0.18 + i * 0.06 + R.uniform(-0.01, 0.01)
        b.cyl((x, -2.3 + R.uniform(-0.2, 0.2), 0.12 + (i % 2) * 0.03), (x + R.uniform(-0.05, 0.05), 2.3 + R.uniform(-0.2, 0.2), 0.12 + (i % 2) * 0.03),
              0.014, 0.014, RUST[0], segs=3)
        for l in b.uv[-3:]:
            l[:] = [uvr(RUST[1], 0.5, 0.5)] * len(l)


def manhole(b):
    segs = 12
    for (r, z, m) in ((0.8, 0.012, THAW), (0.36, 0.03, HATCH)):
        mt, rect = m
        pts = [(r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z) for i in range(segs)]
        uvs = [uvr(rect, 0.5 + 0.5 * math.cos(2 * math.pi * i / segs), 0.5 + 0.5 * math.sin(2 * math.pi * i / segs)) for i in range(segs)]
        b.poly(pts, uvs, mt)


def icicles(b, L):
    """Ряд сосулек длиной L по X, висят от z=0 вниз."""
    mt, rect = ICE
    b.box((-L / 2, -0.04, -0.03), (L / 2, 0.04, 0.0), {k: ICE for k in ('-Y', '+Y', '-Z')})
    x = -L / 2 + 0.1
    while x < L / 2 - 0.05:
        if R.random() < 0.8:
            ln = R.choice([0.12, 0.18, 0.25, 0.35, 0.5, 0.7]) * R.uniform(0.8, 1.2)
            r = 0.022 + ln * 0.04
            tip = (x + R.uniform(-0.01, 0.01), 0, -ln)
            ring_ = [(x + r * math.cos(a), r * math.sin(a), -0.02) for a in (0.5, 2.6, 4.7)]
            for i in range(3):
                b.poly([ring_[(i + 1) % 3], ring_[i], tip], [uvr(rect, 0.2, 1), uvr(rect, 0.8, 1), uvr(rect, 0.5, 0)], mt)
        x += R.uniform(0.09, 0.26)


def goal(b):
    """Футбольные ворота 5×2 м без сетки."""
    m = WHITE[0]
    def pipe(p0, p1):
        b.cyl(p0, p1, 0.05, 0.05, m, segs=5)
        for l in b.uv[-5:]:
            l[:] = [uvr(WHITE[1], 0.3, 0.3)] * len(l)
    for x in (-2.5, 2.5):
        pipe((x, 0, 0), (x, 0, 2.0))
        pipe((x, 0, 2.0), (x, 1.3, 0))
        pipe((x, 0, 0.02), (x, 1.3, 0.02))
    pipe((-2.5, 0, 2.0), (2.5, 0, 2.0))
    pipe((-2.5, 1.3, 0.02), (2.5, 1.3, 0.02))


def snowman(b):
    snow = (M["snow"], (0, 0, 1, 1))
    blob(b, (0, 0, 0), 0.5, 0.5, 0.42, snow, segs=7)
    blob(b, (0, 0, 0.7), 0.36, 0.36, 0.3, snow, segs=7)
    blob(b, (0, 0, 1.22), 0.25, 0.25, 0.22, snow, segs=7)
    tube(b, (0.02, 0.0, 0), 1.6, 1.88, 0.2, 0, RUST, segs=8)                         # ведро на голове
    for sx in (-1, 1):                                                               # руки-ветки
        b.cyl((sx * 0.3, 0, 1.0), (sx * 0.85, -0.1, 1.25), 0.02, 0.01, M["bark"], segs=3)
    for (x, z) in ((-0.09, 1.5), (0.09, 1.5)):                                       # глаза-угольки (смотрит вперёд, −Y)
        b.box((x - 0.03, -0.26, z - 0.03), (x + 0.03, -0.22, z + 0.03), {k: BAG for k in ('-Y', '+X', '-X', '+Z', '-Z')})


def notices(b):
    wallquad(b, 0.95, 0.95, M["note"])


def graffiti(b, i):
    wallquad(b, 2.6, 0.65, M["graf"], (0, 1 - (i + 1) / 8, 1, 1 - i / 8))


def plate(b, w, h, m, t=0.025):
    b.box((-w / 2, -t, -h / 2), (w / 2, 0, h / 2), {'-Y': m, '+X': STEEL, '-X': STEEL, '+Z': STEEL, '-Z': STEEL})


def sign_shop(b):
    w, h, t = 3.2, 0.55, 0.16
    b.box((-w / 2, -t, -h / 2), (w / 2, 0, h / 2), {'-Y': LIGHT, '+X': STEEL, '-X': STEEL, '+Z': STEEL, '-Z': STEEL})
    snowcap(b, -w / 2, -t, w / 2, 0, h / 2, 0.06)


MODELS = {
    "tire_nocol": tire, "tire_stack": tire_stack, "tire_bed_nocol": tire_bed, "barrel": barrel, "barrels": barrels,
    "crate": crate, "crate_stack": crate_stack, "bags_nocol": bags, "dumpster": dumpster, "spool": spool,
    "pallet_nocol": pallet, "pallet_stack": pallet_stack, "bricks": bricks, "ring": ring, "rings": rings,
    "rebar_nocol": rebar, "manhole_nocol": manhole, "icicles_2_nocol": lambda b: icicles(b, 2.0),
    "icicles_4_nocol": lambda b: icicles(b, 4.0), "goal_nocol": goal, "snowman": snowman, "notices_nocol": notices,
    "plate_house_nocol": lambda b: plate(b, 0.62, 0.36, BLUE), "plate_street_nocol": lambda b: plate(b, 1.5, 0.34, BLUE),
    "plate_school_nocol": lambda b: plate(b, 1.2, 0.5, WHITE), "sign_shop_nocol": sign_shop,
}
for _i in range(8):
    MODELS["graffiti_%d_nocol" % _i] = (lambda i: (lambda b: graffiti(b, i)))(_i)


def main():
    sc = bpy.data.scenes.get("DistrictDetails") or bpy.data.scenes.new("DistrictDetails")
    if bpy.context.window:
        bpy.context.window.scene = sc
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    os.makedirs(OUT, exist_ok=True)
    obs = {}
    for name, fn in MODELS.items():
        b = B()
        fn(b)
        obs[name] = b.build(name, sc.collection)
    for other in bpy.data.scenes:                       # в других сценах ничего не должно быть выделено, иначе попадёт в экспорт
        for layer in other.view_layers:
            for o in other.objects:
                o.select_set(False, view_layer=layer)
    vl = sc.view_layers[0]
    polys = 0
    for name, ob in obs.items():
        polys += len(ob.data.polygons)
        for o in sc.objects:
            o.select_set(False, view_layer=vl)
        ob.select_set(True, view_layer=vl)
        vl.objects.active = ob
        path = os.path.join(OUT, name + ".gltf")
        bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_keep_originals=True,
                                  export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
        d = json.load(open(path, encoding="utf-8"))
        changed = False
        for m in d.get("materials", []):                # граффити и объявления — с вырезом по альфе, без сортировки прозрачности
            if m["name"] in ("Graffiti", "Notices"):
                m["alphaMode"], m["alphaCutoff"] = "MASK", 0.4
                changed = True
        if changed:
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    x = 0.0
    for name, ob in sorted(obs.items()):
        w = max(ob.dimensions.x, 0.6)
        ob.location = (x + w / 2, 0, 0)
        x += w + 1.0
    if bpy.data.filepath:
        bpy.ops.file.make_paths_relative()      # пути к текстурам — относительные, иначе модель не откроется на другом компьютере
        bpy.ops.wm.save_mainfile()
    return {"models": len(obs), "polys": polys}


DETAILS_STATS = main()
