# Локация «Восточный ж/д мост» (YUR-7): пешеходный мост над путями станции Одеса-Східна, зима.
# Планировка — по спутнику Google Maps и фото из задачи YUR-7 (сравнение — в описании PR):
#   * мост ~168 м: от улицы Жолио-Кюри (город) над четырьмя восточными путями, двумя боковыми платформами
#     с четырьмя главными путями, полосой с вокзалом и грузовым парком из семи путей; на краю поля
#     поворачивает на 90° и длинным спуском идёт вдоль парка к полю;
#   * со стороны поля — степь с бурьяном, грунтовки, замёрзший пруд, ЛЭП и село (частный сектор);
#   * со стороны города — гаражи, рынок «Сільський», тополя, девятиэтажки и шестнадцатиэтажки вдали.
# Ночью — зелёные ртутные лампы на мосту и платформе у вокзала, натрий в городе и на прожекторной мачте.
#
# Запуск в открытом Blender (через Blender MCP):
#   EB_ROOT = r"<папка проекта>"; exec(open(EB_ROOT + r"\tools\blender\build_east_bridge.py", encoding="utf-8").read())
# Текстуры (один раз или после правок) — tools/blender/east_bridge_textures.py.
#
# Выход — assets/models/east_bridge/*.gltf, по одному на часть локации, и lights.json (фонари для Godot),
# сцена Blender «EastBridge», файл tools/blender/east_bridge.blend.
#
# Оси Blender: Z — вверх, X — вдоль путей (+X — на северо-восток), Y — поперёк путей:
#   +Y — северо-запад (вокзал, грузовой парк, поле, село), −Y — юго-восток (город). В Godot: (x, z, -y).
# Ноль — уровень земли и головки шпал; мост — вдоль Y на X = 0.
# Имена объектов:
#   «…_nocol»    — без коллизии (перила, провода, рельсы, ступени: по лестницам ходят по невидимым пандусам);
#   «…-colonly»  — только коллизия, без меша (суффикс Godot): пандусы под ступенями, стенки вдоль перил, вагоны.
import bpy
import json
import math
import os
import random
from mathutils import Vector

ROOT = globals().get("EB_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
OUT = os.path.join(ROOT, "assets", "models", "east_bridge")

# построитель мешей и материалы двора — из build_yard.py (без его main)
ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), ns)
ns["TEX"] = os.path.join(ROOT, "assets", "textures")
B, mat, M = ns["B"], ns["mat"], ns["M"]

ALL = ('+X', '-X', '+Y', '-Y', '+Z', '-Z')
SIDES = ('+X', '-X', '+Y', '-Y')
OPEN = ('+X', '-X', '+Y', '-Y', '+Z')

# ------------------------------------------------------------------ план станции (по спутнику)
TRACKS_EAST = [-47.5, -42.5, -37.5]                    # старые пути за городской платформой (спутник: полоса Y −50…−35)
TRACKS_MAIN = [-10.1, -5.0, 3.2, 8.6]                  # главные: 2 + 2, между парами — широкое междупутье
TRACKS_YARD = [55.0, 60.5, 66.0, 71.5, 77.0, 82.5, 88.0]   # грузовой парк со стороны поля
TRACKS = TRACKS_EAST + TRACKS_MAIN + TRACKS_YARD
BALLAST = [(-51.0, -34.0), (-12.0, 10.5), (51.0, 91.5)]
PLATFORMS = [(-16.7, -12.0), (10.5, 16.8)]             # боковые: городская (синяя ограда), у вокзала (зелёная)
PLAT_X = (-115.0, 145.0)
PLAT_H = 1.1
FAR = 260.0                                            # пути и провода тянутся до горизонта
XMAX = 110.0                                           # играбельная зона по X
Y_CITY, Y_FIELD = -104.0, 260.0                        # играбельная зона по Y: улица в городе … поле у села
STREET = (-98.0, -90.0)                                # улица Жолио-Кюри
DECK = 7.4                                             # верх настила моста
DECK_T = 0.85
BR_W = 3.0
BR_Y = (-72.0, 95.5)                                   # мост по Y; на −Y лестница на улицу, на +Y — поворот вдоль парка
LEG_Y = 94.0                                           # ось спуска к полю (вдоль −X)
BENTS = [-72.0, -61.0, -51.5, -40.0, -27.0, -14.35, -0.9, 13.65, 22.0, 27.0, 40.0, 50.0, 63.25, 74.25, 85.25, 94.0]
SE_STAIR, NW_STAIR = -14.35, 22.0                      # оси лестниц: городская — над платформой, у вокзала — за платформой
NW_STEPS_X = 21.5                                      # у вокзала: проходы в ограде и ступени с земли на платформу (±X)
SW = 2.5                                               # ширина лестниц на платформы
WIRE_C, WIRE_M = 5.8, 7.2                              # контактный провод и несущий трос
GANTRY_X = [-150.0, -98.0, -46.0, 12.0, 60.0, 96.0, 145.0]   # жёсткие поперечины над главными путями
PORTAL_X = [-137.0, -82.0, -27.0, 28.0, 83.0, 138.0]         # порталы над парком и восточными путями
RISE, RUN = 0.168, 0.30                                # ступень
RAIL_H = 1.1

LIGHTS = []                                            # фонари для Godot: голова плафона + основание + цвет
rnd = random.Random(2024)


def gd(p):
    """Blender (x, y, z) → Godot (x, y, z)."""
    return [round(p[0], 3), round(p[2], 3), round(-p[1], 3)]


def lamp(kind, color, base, head, energy=None):
    LIGHTS.append({"kind": kind, "color": color, "base": gd(base), "head": gd(head), "energy": energy})


# ------------------------------------------------------------------ материалы
def amat(name, tex, emi=None):
    """Материал с вырезом по альфе (решётки, сетка, трава, деревья) — двусторонний."""
    m = mat(name, tex, emi, rough=0.8)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    t = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.startswith(tex))
    r = nt.nodes.new("ShaderNodeMath")
    r.operation = 'ROUND'
    nt.links.new(t.outputs["Alpha"], r.inputs[0])
    nt.links.new(r.outputs[0], bsdf.inputs["Alpha"])
    m.use_backface_culling = False
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = 'DITHERED'
    return m


def flat(name, rgba, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba
    if emit:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = rgba
    return m


def two_sided(m):
    m.use_backface_culling = False
    return m


def materials():
    ns["build_materials"]()
    E = {
        "ballast": mat("EbBallast", "eb_ballast"),
        "trackbed": mat("EbTrackbed", "eb_trackbed"),
        "white": mat("EbWhitePaint", "eb_white", rough=0.6),
        "deck": mat("EbDeck", "eb_deck"),
        "platform": mat("EbPlatform", "eb_platform"),
        "pedge": mat("EbPlatformEdge", "eb_platform_edge"),
        "booth": mat("EbBooth", "eb_booth", rough=0.6),
        "cabinet": mat("EbCabinet", "eb_cabinet", rough=0.6),
        "tank": mat("EbTank", "eb_tank", rough=0.5),
        "gondola": mat("EbGondola", "eb_gondola", rough=0.7),
        "container": mat("EbContainer", "eb_container", rough=0.6),
        "coach": mat("EbCoach", "eb_coach", "eb_coach_emission", rough=0.5),
        "lattice": amat("EbLattice", "eb_lattice"),
        "mesh": amat("EbMesh", "eb_mesh"),
        "lamp_g": mat("EbLampGreen", "eb_lamp_green", "eb_lamp_green", rough=0.3),
        "lamp_o": mat("EbLampOrange", "eb_lamp_orange", "eb_lamp_orange", rough=0.3),
        "station": mat("EbStation", "eb_station"),
        "sign": mat("EbStationSign", "eb_sign_station", rough=0.5),
        "fence": mat("FenceConcrete", "fence_concrete"),
        "blue": mat("EbBluePaint", "eb_blue_paint", rough=0.6),
        "greenp": mat("EbGreenPaint", "eb_green_paint", rough=0.6),
        "pole": mat("EbConcretePole", "eb_concrete_pole"),
        "girder": mat("EbGirder", "eb_girder"),
        "pier": mat("EbPier", "eb_pier"),
        "sheet": two_sided(mat("EbSheet", "eb_sheet", rough=0.6)),
        "field": mat("EbField", "eb_field"),
        "road": mat("EbRoad", "eb_road"),
        "ice": mat("EbIce", "eb_ice", rough=0.3),
        "grass": amat("EbGrass", "eb_grass"),
        "tree": amat("EbTree", "eb_tree"),
        "poplar": amat("EbPoplar", "eb_poplar"),
        "house": mat("EbHouse", "eb_house", "eb_house_emission"),
        "corr": two_sided(mat("EbCorrugated", "eb_corrugated", rough=0.6)),
        "yellow": flat("EbYellowPaint", (0.80, 0.64, 0.18, 1)),
        "lamp_w": flat("EbLampWhite", (0.85, 0.9, 1.0, 1), emit=2.0),
        "dark": flat("EbDarkGlass", (0.03, 0.035, 0.04, 1)),
        "house_bd": flat("BackdropHouse", (0.05, 0.055, 0.07, 1)),
        "glow": flat("BackdropGlow", (1.0, 0.5, 0.15, 1)),
    }
    M.update(E)


def fx(m, keys=ALL):
    return {k: m for k in keys}


def quad(b, pts, m, out, s=(1.0, 1.0), uvs=None):
    """Грань с нормалью в сторону out. Без uvs — мировая проекция по главной оси нормали (шаг s, м на тайл)."""
    pts = [Vector(p) for p in pts]
    n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
    if n.dot(Vector(out)) < 0:
        pts.reverse()
        if uvs:
            uvs = list(reversed(uvs))
    if not uvs:
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        ax = max(range(3), key=lambda i: abs(n[i]))
        if ax == 2:
            uvs = [(p.x / s[0], p.y / s[1]) for p in pts]
        elif ax == 0:
            uvs = [(p.y / s[0], p.z / s[1]) for p in pts]
        else:
            uvs = [(p.x / s[0], p.z / s[1]) for p in pts]
    b.poly(pts, uvs, m)


def bar(b, p0, p1, w, m, s=(1.0, 1.0)):
    """Брусок квадратного сечения w от p0 до p1 (любой наклон)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0)
    L = d.length
    d.normalize()
    t = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(t).normalized() * (w / 2)
    v = d.cross(u).normalized() * (w / 2)
    c = [p0 + u + v, p0 - u + v, p0 - u - v, p0 + u - v]
    e = [q + d * L for q in c]
    for i in range(4):
        j = (i + 1) % 4
        b.poly([c[i], c[j], e[j], e[i]], [(0, 0), (w / s[0], 0), (w / s[0], L / s[1]), (0, L / s[1])], m)
    return (p0 + p1) / 2


def strut(b, p, z0, z1, along, w, m):
    """Тонкий пруток перил: две грани (лицом поперёк линии перил) — вдвое дешевле бруска."""
    along = Vector(along).normalized()
    n = Vector((-along.y, along.x, 0))
    a = Vector(p) - along * (w / 2)
    c = Vector(p) + along * (w / 2)
    for o in (n, -n):
        q = [a + o * w * 0.5, c + o * w * 0.5]
        quad(b, [(q[0].x, q[0].y, z0), (q[1].x, q[1].y, z0), (q[1].x, q[1].y, z1), (q[0].x, q[0].y, z1)], m, (o.x, o.y, 0),
             uvs=[(0, 0), (0.05, 0), (0.05, z1 - z0), (0, z1 - z0)])


def crossed(b, x, y, z, w, h, m, ang=0.0, uv=(0, 0, 1, 1)):
    """Билборд из двух скрещённых квадов (трава, деревья)."""
    u0, v0, u1, v1 = uv
    for a in (ang, ang + math.pi / 2):
        dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2
        b.poly([(x - dx, y - dy, z), (x + dx, y + dy, z), (x + dx, y + dy, z + h), (x - dx, y - dy, z + h)],
               [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], m)


def build(b, name, coll):
    return b.build(name, coll)


# ------------------------------------------------------------------ земля, пути, платформы
def ground(coll):
    b = B()
    X = 700.0
    for ya, yb in BALLAST:
        quad(b, [(-FAR, ya, 0), (FAR, ya, 0), (FAR, yb, 0), (-FAR, yb, 0)], M["ballast"], (0, 0, 1), (4, 4))
    # снег между группами путей и в городе
    for ya, yb in ((-600.0, BALLAST[0][0]), (BALLAST[0][1], BALLAST[1][0]), (BALLAST[1][1], BALLAST[2][0])):
        quad(b, [(-X, ya, 0), (X, ya, 0), (X, yb, 0), (-X, yb, 0)], M["snow"], (0, 0, 1), (6, 6))
    # за парком — поле до самого села
    quad(b, [(-X, BALLAST[2][1], 0), (X, BALLAST[2][1], 0), (X, 900.0, 0), (-X, 900.0, 0)], M["field"], (0, 0, 1), (8, 8))
    # улица Жолио-Кюри
    ya, yb = STREET
    quad(b, [(-X, ya, 0.02), (X, ya, 0.02), (X, yb, 0.02), (-X, yb, 0.02)], M["platform"], (0, 0, 1), (4, 4))
    return build(b, "EbGround", coll)


def tracks(coll):
    """Путевое полотно — полоса с нарисованными шпалами (с коллизией), рельсы отдельно (без коллизии)."""
    bed, rails = B(), B()
    for yc in TRACKS:
        ya, yb = yc - 1.6, yc + 1.6
        z = 0.06
        quad(bed, [(-FAR, ya, z), (FAR, ya, z), (FAR, yb, z), (-FAR, yb, z)], M["trackbed"], (0, 0, 1),
             uvs=[(0, -FAR / 3.3), (0, FAR / 3.3), (1, FAR / 3.3), (1, -FAR / 3.3)])
        for ys, out in ((ya, -1), (yb, 1)):
            quad(bed, [(-FAR, ys, 0), (FAR, ys, 0), (FAR, ys, z), (-FAR, ys, z)], M["ballast"], (0, out, 0), (4, 0.25))
        for yr in (yc - 0.76, yc + 0.76):
            rails.box((-FAR, yr - 0.036, z), (FAR, yr + 0.036, z + 0.15), fx(M["metal"], ('+Y', '-Y', '+Z')), scale=(4, 0.5))
    return build(bed, "EbTrackbed", coll), build(rails, "EbRails_nocol", coll)


def tube_fence(b, col, p0, p1, m, h=1.1, posts=2.5, gaps=()):
    """Трубчатая ограда платформы: стойки и две трубы (по X), коллизия — стенка."""
    x0, x1, y = p0[0], p1[0], p0[1]
    cuts = sorted(gaps)
    segs, a = [], x0
    for g0, g1 in cuts:
        segs.append((a, g0))
        a = g1
    segs.append((a, x1))
    for a, c in segs:
        n = max(1, round((c - a) / posts))
        for i in range(n + 1):
            x = a + (c - a) * i / n
            bar(b, (x, y, PLAT_H), (x, y, PLAT_H + h), 0.06, m)
        for z in (0.45, h - 0.03):
            bar(b, (a, y, PLAT_H + z), (c, y, PLAT_H + z), 0.05, m, s=(1, 1))
        col.box((a, y - 0.05, PLAT_H), (c, y + 0.05, PLAT_H + 1.4), fx(M["plinth"], ALL))


def platforms(coll):
    b, rail, col = B(), B(), B()
    xa, xb = PLAT_X
    for i, (ya, yb) in enumerate(PLATFORMS):
        b.box((xa, ya, 0), (xb, yb, PLAT_H), {'+Z': M["platform"]}, scale=(4, 4))
        b.box((xa, ya, 0), (xb, yb, PLAT_H), {'+Y': M["pedge"], '-Y': M["pedge"]}, scale=(4, 1))
        for sx, x0 in ((-1, xa), (1, xb)):                     # пандусы с торцов
            x1 = x0 + sx * 8.0
            quad(b, [(x0, ya, PLAT_H), (x1, ya, 0.05), (x1, yb, 0.05), (x0, yb, PLAT_H)], M["platform"], (sx * 0.15, 0, 1), (4, 4))
            for ys, out in ((ya, -1), (yb, 1)):
                quad(b, [(x0, ys, 0), (x1, ys, 0), (x1, ys, 0.05), (x0, ys, PLAT_H)], M["pedge"], (0, out, 0), (4, 1))
        # белая полоса безопасности — только у края к путям
        ys = ya + 0.3 if i == 0 else yb - 0.6
        b.box((xa, ys, PLAT_H), (xb, ys + 0.3, PLAT_H + 0.01), {'+Z': (M["white"], (0, 0, 40, 0.3))})
    # ограды по дальнему от путей краю: городская — синяя, у вокзала — зелёная (проход к вокзалу X 30…36)
    tube_fence(rail, col, (xa, PLATFORMS[0][0] + 0.15), (xb, 0), M["blue"])
    sx0, sx1 = NW_STEPS_X - SW / 2, NW_STEPS_X + SW / 2
    # у вокзала синяя ограда — только у лестниц с моста (X −35…30), дальше по краю белёный бордюр (панорама p2 ya180/ya225)
    tube_fence(rail, col, (-35.0, PLATFORMS[1][1] - 0.15), (30.0, 0), M["blue"], gaps=[(-sx1, -sx0), (sx0, sx1)])
    for c0, c1 in ((xa, -35.0), (36.0, xb)):
        b.box((c0, PLATFORMS[1][1] - 0.3, PLAT_H), (c1, PLATFORMS[1][1], PLAT_H + 0.18), fx(M["white"], ('+Y', '-Y', '+Z', '+X', '-X')), scale=(1, 1))
    yp = PLATFORMS[1][1]
    n = 7
    for s_ in (-1, 1):                                       # 7 ступеней вниз от края платформы к лестницам с моста
        xa_, xb_ = sorted((s_ * sx0, s_ * sx1))
        for i in range(n):
            ya_, yb_ = yp + i * RUN, yp + (i + 1) * RUN
            z = PLAT_H - (i + 1) * PLAT_H / n
            b.box((xa_, ya_, 0), (xb_, yb_, z), fx(M["pedge"], ('+X', '-X', '+Y', '+Z')), scale=(4, 1))
        quad(col, [(xa_, yp, PLAT_H), (xb_, yp, PLAT_H), (xb_, yp + n * RUN, 0.0), (xa_, yp + n * RUN, 0.0)], M["plinth"], (0, 0.3, 1))
        quad(col, [(xa_, yp, PLAT_H - 0.3), (xb_, yp, PLAT_H - 0.3), (xb_, yp + n * RUN, -0.3), (xa_, yp + n * RUN, -0.3)], M["plinth"], (0, 0, -1))
    return build(b, "EbPlatforms", coll), build(rail, "EbPlatformRails_nocol", coll), build(col, "EbPlatformRailsCol-colonly", coll)


def bounds(coll):
    """Невидимые стенки по краю играбельной зоны и бетонный забор вдоль городской улицы (за ним — рынок и дома)."""
    b, w = B(), B()
    y = Y_CITY - 0.5
    for x0 in range(int(-XMAX), int(XMAX), 4):
        if -62 <= x0 < -26:                                     # тут стена рынка
            continue
        b.box((x0, y - 0.08, 0), (x0 + 4, y + 0.08, 2.4), fx(M["fence"], ('+Y', '-Y')), scale=(4, 2.4))
        b.box((x0, y - 0.1, 2.4), (x0 + 4, y + 0.1, 2.48), fx(M["snow"], ('+Y', '-Y', '+Z')), scale=(3, 3))
        b.box((x0 - 0.12, y - 0.14, 0), (x0 + 0.12, y + 0.14, 2.6), fx(M["fence"], OPEN), scale=(1, 2.6))
    for x in (-XMAX, XMAX):
        w.box((x - 0.5, Y_CITY, -1), (x + 0.5, Y_FIELD, 14), fx(M["plinth"], ALL))
    for y in (Y_CITY, Y_FIELD):
        w.box((-XMAX, y - 0.5, -1), (XMAX, y + 0.5, 14), fx(M["plinth"], ALL))
    return build(b, "EbFences", coll), build(w, "EbBounds-colonly", coll)


# ------------------------------------------------------------------ мост
def railing(b, p0, p1, h=RAIL_H, posts=2.2, skip=()):
    """Перила (как на фото): квадратные стойки через ~2,2 м, поручень, второй пояс на 0,87 м, нижний на 0,1 м;
    частые прутья (0,15 м, фото 10002, 10009, 10019) только между нижним и вторым поясом. skip — куски (t0, t1) вдоль линии без прутьев
    (там сплошной лист ограждения)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    n = max(1, round(L / posts))
    up = Vector((0, 0, 1))
    for i in range(n + 1):
        q = p0 + d * (i / n)
        bar(b, q, q + up * h, 0.07, M["white"])
    for z in (0.10, 0.87, h - 0.04):
        bar(b, p0 + up * z, p1 + up * z, 0.05, M["white"])
    k = max(1, int(L / 0.15))
    for i in range(1, k):
        t = i / k
        if any(a <= t * L <= c for a, c in skip):
            continue
        q = p0 + d * t
        strut(b, q, q.z + 0.10, q.z + 0.87, (d.x, d.y, 0), 0.02, M["white"])


def guard_panel(b, x, ya, yb, z0):
    """Над путём с контактной сетью: сплошной лист ниже поручня и рамы с сеткой-рабицей до 2,4 м над настилом."""
    side = 1 if x > 0 else -1
    xs = x - side * 0.02
    quad(b, [(xs, ya, z0 + 0.10), (xs, yb, z0 + 0.10), (xs, yb, z0 + 1.06), (xs, ya, z0 + 1.06)], M["sheet"], (side, 0, 0),
         uvs=[(0, 0), ((yb - ya) / 4, 0), ((yb - ya) / 4, 1), (0, 1)])
    zt = z0 + 2.4
    b.poly([(x, ya, z0 + RAIL_H), (x, yb, z0 + RAIL_H), (x, yb, zt), (x, ya, zt)],
           [(0, 0), (yb - ya, 0), (yb - ya, zt - z0 - RAIL_H), (0, zt - z0 - RAIL_H)], M["mesh"])
    n = max(1, math.ceil((yb - ya) / 1.4))
    for i in range(n + 1):
        y = ya + (yb - ya) * i / n
        bar(b, (x, y, z0 + RAIL_H - 0.05), (x, y, zt), 0.08 if i in (0, n) else 0.05, M["white"])
    bar(b, (x, ya, zt), (x, yb, zt), 0.06, M["white"])


def lamp_post(b, x, y, z0, arm, color="green", kind="bridge"):
    """Фонарь моста (фото 10019): труба 3,2 м от перил, загиб и наклонная консоль ~1 м над настилом, плоская «кобра»."""
    arm = Vector(arm).normalized()
    base = Vector((x, y, z0))
    top = base + Vector((0, 0, 3.2))
    bar(b, base, top, 0.09, M["white"])
    p2 = top + arm * 0.25 + Vector((0, 0, 0.22))
    p3 = p2 + arm * 0.95 + Vector((0, 0, 0.5))
    bar(b, top, p2, 0.08, M["white"])
    bar(b, p2, p3, 0.07, M["white"])
    hc = p3 + arm * 0.2
    ex, ey = (0.3, 0.1) if abs(arm.x) > 0.5 else (0.1, 0.3)
    b.box((hc.x - ex, hc.y - ey, hc.z - 0.1), (hc.x + ex, hc.y + ey, hc.z + 0.04), fx(M["metal"], OPEN), scale=(1, 1))
    lm = M["lamp_g"] if color == "green" else M["lamp_o"]
    b.box((hc.x - ex * 0.8, hc.y - ey * 0.8, hc.z - 0.15), (hc.x + ex * 0.8, hc.y + ey * 0.8, hc.z - 0.1),
          fx(lm, ('+X', '-X', '+Y', '-Y', '-Z')), scale=(1, 1))
    lamp(kind, color, tuple(base), (hc.x, hc.y, hc.z - 0.2))
    return top + Vector((0, 0, 0.1))


def cable(b, p0, p1, sag=0.6, n=6):
    """Провисший провод между фонарями."""
    pts = []
    for i in range(n + 1):
        t = i / n
        q = Vector(p0).lerp(Vector(p1), t)
        q.z -= sag * 4 * t * (1 - t)
        pts.append(q)
    for a, c in zip(pts, pts[1:]):
        bar(b, a, c, 0.02, M["metal"])


def flight(b, col, x0, y0, z0, dx, dy, width, n):
    """Марш лестницы вниз из (x0, y0, z0) в направлении (dx, dy); width — ширина поперёк.
    Ступени, центральный косоур (без коллизии), перила + невидимый пандус. Возвращает (x, y, z) низа марша."""
    px, py = -dy, dx                                     # поперёк марша
    hw = width / 2
    p = lambda s, t, z: (x0 + dx * s + px * t, y0 + dy * s + py * t, z)
    for i in range(n):
        a, c = i * RUN, (i + 1) * RUN
        zt = z0 - (i + 1) * RISE
        quad(b, [p(a, -hw, zt), p(c, -hw, zt), p(c, hw, zt), p(a, hw, zt)], M["deck"], (0, 0, 1), (3, 3))
        quad(b, [p(a, -hw, zt), p(a, hw, zt), p(a, hw, zt + RISE), p(a, -hw, zt + RISE)], M["plinth"], (dx, dy, 0), (3.6, 0.9))
        for t in (-hw, hw):                              # торцы ступеней
            o = 1 if t > 0 else -1
            quad(b, [p(a, t, zt - 0.12), p(c, t, zt - 0.12), p(c, t, zt), p(a, t, zt)], M["plinth"], (px * o, py * o, 0), (3.6, 0.9))
        quad(b, [p(a, -hw, zt - 0.12), p(c, -hw, zt - 0.12), p(c, hw, zt - 0.12), p(a, hw, zt - 0.12)], M["plinth"], (0, 0, -1), (3.6, 0.9))
    L, H = n * RUN, n * RISE
    for t in (-0.3, 0.3):                                # центральный наклонный косоур (фото 10026)
        o = 1 if t > 0 else -1
        quad(b, [p(0, t, z0 - 0.1), p(L, t, z0 - H - 0.1), p(L, t, z0 - H - 0.6), p(0, t, z0 - 0.6)], M["plinth"], (px * o, py * o, 0), (3.6, 0.9))
    quad(b, [p(0, -0.3, z0 - 0.6), p(L, -0.3, z0 - H - 0.6), p(L, 0.3, z0 - H - 0.6), p(0, 0.3, z0 - 0.6)], M["plinth"], (0, 0, -1), (3.6, 0.9))
    for t in (-hw - 0.05, hw + 0.05):                    # наклонные перила
        q0, q1 = Vector(p(0, t, z0)), Vector(p(L, t, z0 - H))
        nn = max(2, round(L / 1.5))
        for i in range(nn + 1):
            q = q0.lerp(q1, i / nn)
            bar(b, q, q + Vector((0, 0, 1.0)), 0.06, M["white"])
        for zz in (0.10, 0.78, 0.96):
            bar(b, q0 + Vector((0, 0, zz)), q1 + Vector((0, 0, zz)), 0.05, M["white"])
        k = int(L / 0.15)
        for i in range(1, k):
            q = q0.lerp(q1, i / k)
            strut(b, q, q.z + 0.10, q.z + 0.78, (dx, dy, 0), 0.02, M["white"])
    # пандус-коллизия: клин под ступенями, верх — линия носков ступеней
    zt0, zt1 = z0, z0 - H
    corners = [p(0, -hw, zt0), p(L, -hw, zt1), p(L, hw, zt1), p(0, hw, zt0)]
    quad(col, corners, M["plinth"], (0, 0, 1))
    quad(col, [(c[0], c[1], c[2] - 0.3) for c in corners], M["plinth"], (0, 0, -1))
    for t in (-hw - 0.05, hw + 0.05):                    # стенки вдоль перил (две стороны — коллизия с обеих)
        for o in (1, -1):
            quad(col, [p(0, t, zt0), p(L, t, zt1), p(L, t, zt1 + 1.2), p(0, t, zt0 + 1.2)], M["plinth"], (px * o, py * o, 0))
    return x0 + dx * L, y0 + dy * L, z0 - H


def landing(b, col, x0, y0, x1, y1, z, base=0.0, rails=(), columns=1):
    """Площадка: плита, колонна(ы) под ней, перила по сторонам rails ((p0, p1), …)."""
    xa, xb, ya, yb = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    b.box((xa, ya, z - 0.35), (xb, yb, z), {'+Z': M["deck"]}, scale=(3, 3))
    b.box((xa, ya, z - 0.35), (xb, yb, z), fx(M["plinth"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(3.6, 0.9))
    col.box((xa, ya, z - 0.35), (xb, yb, z), fx(M["plinth"], ALL))
    cx, cy = (xa + xb) / 2, (ya + yb) / 2
    long_x = (xb - xa) > (yb - ya)
    pts = [(cx, cy)] if columns == 1 else \
        [((xa + 0.6, cy) if long_x else (cx, ya + 0.6)), ((xb - 0.6, cy) if long_x else (cx, yb - 0.6))]
    for x, y in pts:
        if z - 0.35 - base > 0.2:
            b.box((x - 0.24, y - 0.24, base), (x + 0.24, y + 0.24, z - 0.35), fx(M["plinth"], SIDES), scale=(3.6, 0.9))
            col.box((x - 0.24, y - 0.24, base), (x + 0.24, y + 0.24, z - 0.35), fx(M["plinth"], ALL))
    for p0, p1 in rails:
        railing(b, (p0[0], p0[1], z), (p1[0], p1[1], z), h=1.0, posts=1.6)
        col.box((min(p0[0], p1[0]) - 0.05, min(p0[1], p1[1]) - 0.05, z), (max(p0[0], p1[0]) + 0.05, max(p0[1], p1[1]) + 0.05, z + 1.2),
                fx(M["plinth"], ALL))


def platform_stair(b, col, yc, side, base=PLAT_H):
    """Лестница вниз от края настила вдоль путей (−X или +X): 3 ступени, площадка 3 м,
    марш, площадка 2,5 м, марш до платформы или земли base (фото 10007, 10022, 10026; панорамы p1, p2)."""
    hw = BR_W / 2
    e = SW / 2 + 0.1
    x, _, z = flight(b, col, side * hw, yc, DECK, side, 0, SW, 3)
    for ln, n in ((3.0, 17), (2.5, None)):
        xl = x + side * ln
        landing(b, col, x, yc - e, xl, yc + e, z, base=base, rails=[((x, yc - e), (xl, yc - e)), ((x, yc + e), (xl, yc + e))])
        n = n or max(1, round((z - base) / RISE))
        x, _, z = flight(b, col, xl, yc, z, side, 0, SW, n)
    return x


def bridge(coll):
    b, col, lamps_b = B(), B(), B()
    hw = BR_W / 2
    y0, y1 = BR_Y
    zb = DECK - DECK_T
    # настил: верх — своя развёртка (u поперёк), низ и бока — бетонная балка 0,85 м
    quad(b, [(-hw, y0, DECK), (hw, y0, DECK), (hw, y1, DECK), (-hw, y1, DECK)], M["deck"], (0, 0, 1),
         uvs=[(0, y0 / 3), (1, y0 / 3), (1, y1 / 3), (0, y1 / 3)])
    b.box((-hw - 0.15, y0, zb), (hw + 0.15, y1, DECK), fx(M["girder"], ('+X', '-X', '-Z', '+Y')), scale=(3, DECK_T))
    b.box((-hw - 0.15, y0, DECK), (-hw, y1, DECK + 0.12), fx(M["plinth"], ('+X', '-X', '+Z')), scale=(3.6, 0.9))
    b.box((hw, y0, DECK), (hw + 0.15, y1, DECK + 0.12), fx(M["plinth"], ('+X', '-X', '+Z')), scale=(3.6, 0.9))
    col.box((-hw - 0.15, y0, zb), (hw + 0.15, y1, DECK), fx(M["plinth"], ALL))
    # опоры: везде одна квадратная колонна 0,6 м с фасками и консоль-«шапка» поперёк моста под балкой
    # (панорама p2 ya045/ya090, фото 10006, 10026)
    for yb in BENTS:
        on_pl = next((True for a, c in PLATFORMS if a < yb < c), False)
        z0 = PLAT_H if on_pl else 0.0
        r, c = 0.30, 0.07
        ring = [(-r + c, -r), (r - c, -r), (r, -r + c), (r, r - c), (r - c, r), (-r + c, r), (-r, r - c), (-r, -r + c)]
        for (ax, ay), (bx_, by) in zip(ring, ring[1:] + ring[:1]):
            nx, ny = by - ay, -(bx_ - ax)
            quad(b, [(ax, yb + ay, z0), (bx_, yb + by, z0), (bx_, yb + by, zb - 0.45), (ax, yb + ay, zb - 0.45)], M["pier"], (nx, ny, 0), (3, 3))
        # консоль: снизу скошена, поперёк моста почти на всю ширину балки
        cw, cd = 1.25, 0.45
        b.box((-cw, yb - cd, zb - 0.25), (cw, yb + cd, zb), fx(M["girder"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(3, 3))
        quad(b, [(-r, yb - cd, zb - 0.45), (r, yb - cd, zb - 0.45), (cw, yb - cd, zb - 0.25), (-cw, yb - cd, zb - 0.25)], M["girder"], (0, -1, 0), (3, 3))
        quad(b, [(r, yb + cd, zb - 0.45), (-r, yb + cd, zb - 0.45), (-cw, yb + cd, zb - 0.25), (cw, yb + cd, zb - 0.25)], M["girder"], (0, 1, 0), (3, 3))
        quad(b, [(r, yb - cd, zb - 0.45), (r, yb + cd, zb - 0.45), (cw, yb + cd, zb - 0.25), (cw, yb - cd, zb - 0.25)], M["girder"], (1, 0, -1), (3, 3))
        quad(b, [(-r, yb + cd, zb - 0.45), (-r, yb - cd, zb - 0.45), (-cw, yb - cd, zb - 0.25), (-cw, yb + cd, zb - 0.25)], M["girder"], (-1, 0, -1), (3, 3))
        col.box((-r, yb - r, z0), (r, yb + r, zb), fx(M["plinth"], ALL))
    # проёмы в перилах: лестницы на платформы и спуск к полю
    e = SW / 2 + 0.1
    gaps = {-1: [(SE_STAIR - e, SE_STAIR + e), (NW_STAIR - e, NW_STAIR + e), (LEG_Y - 1.5, y1)],
            1: [(SE_STAIR - e, SE_STAIR + e), (NW_STAIR - e, NW_STAIR + e)]}
    for side in (-1, 1):
        x = side * (hw + 0.05)
        segs = [y0]
        for a, c in sorted(gaps[side]):
            segs += [a, c]
        segs.append(y1)
        for a, c in zip(segs[0::2], segs[1::2]):
            if c - a < 0.3:
                continue
            skip = []
            for yc in TRACKS:
                ya, yb_ = max(a, yc - 2.0), min(c, yc + 2.0)
                if yb_ - ya > 0.5:
                    skip.append((ya - a, yb_ - a))
                    guard_panel(b, x, ya, yb_, DECK + 0.12)
            railing(b, (x, a, DECK + 0.12), (x, c, DECK + 0.12), skip=skip)
            col.box((x - 0.06, a, DECK), (x + 0.06, c, DECK + 1.4), fx(M["plinth"], ALL))
    # торец моста у поворота к полю
    railing(b, (-hw - 0.05, y1 + 0.05, DECK + 0.12), (hw + 0.05, y1 + 0.05, DECK + 0.12))
    col.box((-hw, y1 - 0.06, DECK), (hw, y1 + 0.06, DECK + 1.4), fx(M["plinth"], ALL))
    # фонари — все по юго-западной стороне (−X), через 12 м, консоль над настилом; между ними провисший провод
    tops = []
    for y in range(90, -67, -12):
        c = "orange" if y == -66 else "green"
        tops.append(lamp_post(lamps_b, -(hw + 0.12), float(y), DECK + 0.12, (1, 0, 0), color=c))
    for a, c in zip(tops, tops[1:]):
        cable(lamps_b, a, c)
    # лестницы-«Т»: на городскую платформу — оба марша на неё (панорама p1 ya045/ya135);
    # у вокзала — за платформой, на землю за зелёной оградой (панорама p2 ya090/ya135, фото 10016)
    platform_stair(b, col, SE_STAIR, -1)
    platform_stair(b, col, SE_STAIR, 1)
    platform_stair(b, col, NW_STAIR, -1, base=0.0)
    platform_stair(b, col, NW_STAIR, 1, base=0.0)
    # городская лестница: прямо по оси моста, два марша и площадка
    xa, ya, za = flight(b, col, 0, y0, DECK, 0, -1, BR_W, 22)
    yl = ya - 2.0
    landing(b, col, -hw - 0.15, yl, hw + 0.15, ya, za, rails=[((-hw - 0.15, ya), (-hw - 0.15, yl)), ((hw + 0.15, ya), (hw + 0.15, yl))], columns=2)
    flight(b, col, 0, yl, za, 0, -1, BR_W, round(za / RISE))
    # спуск к полю: вдоль парка на юго-запад, шесть маршей и пять длинных площадок (средний уклон ~1:7)
    e = BR_W / 2 + 0.15
    x, z = -hw, DECK
    lamp_x = []
    for i, n in enumerate((7, 7, 7, 7, 8, 8)):
        x, _, z = flight(b, col, x, LEG_Y, z, -1, 0, BR_W, n)
        if i < 5:
            xl = x - 7.7
            landing(b, col, x, LEG_Y - e, xl, LEG_Y + e, z, rails=[((x, LEG_Y - e), (xl, LEG_Y - e)), ((x, LEG_Y + e), (xl, LEG_Y + e))], columns=2)
            lamp_x.append(((x + xl) / 2, z))
            x = xl
    # фонари спуска — со стороны парка, консолью к дорожке
    ltops = [tops[0]]
    for i, (lx, lz) in enumerate(lamp_x):
        if i % 2 == 0:
            ltops.append(lamp_post(lamps_b, lx, LEG_Y - e - 0.07, lz + 0.05, (0, 1, 0)))
    for a, c in zip(ltops, ltops[1:]):
        cable(lamps_b, a, c, sag=0.8, n=8)
    vis = build(b, "EbBridge_nocol", coll)
    return vis, build(lamps_b, "EbBridgeLamps_nocol", coll), build(col, "EbBridgeCol-colonly", coll)


# ------------------------------------------------------------------ контактная сеть, прожекторы, светофоры
def lattice_box(b, x, ya, yb, z0, z1, d, axis='Y'):
    """Ригель: коробка из решётчатых граней вдоль оси axis (u — по 2 м)."""
    L = yb - ya
    for xs in (x - d / 2, x + d / 2):
        pts = [(xs, ya, z0), (xs, yb, z0), (xs, yb, z1), (xs, ya, z1)]
        if axis == 'X':
            pts = [(p[1], p[0], p[2]) for p in pts]
        b.poly(pts, [(0, 0), (L / 2, 0), (L / 2, 1), (0, 1)], M["lattice"])
    for zs in (z0, z1):
        pts = [(x - d / 2, ya, zs), (x - d / 2, yb, zs), (x + d / 2, yb, zs), (x + d / 2, ya, zs)]
        if axis == 'X':
            pts = [(p[1], p[0], p[2]) for p in pts]
        b.poly(pts, [(0, 0), (L / 2, 0), (L / 2, 1), (0, 1)], M["lattice"])
    mn, mx = (x - d / 2, ya, z1), (x + d / 2, yb, z1 + 0.06)
    if axis == 'X':
        mn, mx = (ya, x - d / 2, z1), (yb, x + d / 2, z1 + 0.06)
    b.box(mn, mx, fx(M["snow"], ('+Z', '+X', '-X', '+Y', '-Y')), scale=(3, 3))


def concrete_pole(b, col, x, y, h, r0=0.22, r1=0.15):
    """Конический бетонный столб контактной сети (фото 10005, 10021) с оголовком."""
    b.cyl((x, y, 0), (x, y, h), r0, r1, M["pole"], segs=8, su=2)
    b.box((x - r1 - 0.03, y - r1 - 0.03, h), (x + r1 + 0.03, y + r1 + 0.03, h + 0.12), fx(M["metal"], OPEN), scale=(1, 1))
    b.box((x - r1 - 0.03, y - r1 - 0.03, h + 0.12), (x + r1 + 0.03, y + r1 + 0.03, h + 0.18), fx(M["snow"], ('+Z',)), scale=(3, 3))
    col.box((x - r0, y - r0, 0), (x + r0, y + r0, h), fx(M["plinth"], ALL))


def hanger(wires, x, yc, z_from):
    """Подвес к несущему тросу: тяга вниз и изолятор."""
    bar(wires, (x, yc, z_from), (x, yc, WIRE_M + 0.6), 0.035, M["metal"])
    bar(wires, (x, yc, WIRE_M + 0.6), (x, yc, WIRE_M), 0.09, M["white"])


def floodlight_tower(b, col, x, y, h, face, color):
    """Прожекторная мачта (фото 10033): стальная труба с лестницей в ограждении, площадка с перилами,
    прожекторы по одной стороне."""
    bar(b, (x, y, 0), (x, y, h), 0.5, M["metal"], s=(1, 3))
    col.box((x - 0.3, y - 0.3, 0), (x + 0.3, y + 0.3, h), fx(M["plinth"], ALL))
    lx, ly = x - face[0] * 0.55, y - face[1] * 0.55                  # лестница — с тыла
    for o in (-0.22, 0.22):
        ox, oy = -face[1] * o, face[0] * o
        bar(b, (lx + ox, ly + oy, 0.3), (lx + ox, ly + oy, h), 0.04, M["metal"])
    z = 2.5
    while z < h:                                                      # обручи ограждения лестницы
        ring = []
        for i in range(7):
            a = math.pi * i / 6
            ring.append((lx - face[0] * 0.35 * math.sin(a) - face[1] * 0.35 * math.cos(a),
                         ly - face[1] * 0.35 * math.sin(a) + face[0] * 0.35 * math.cos(a), z))
        for a, c in zip(ring, ring[1:]):
            bar(b, a, c, 0.03, M["metal"])
        z += 1.6
    b.box((x - 1.3, y - 1.3, h), (x + 1.3, y + 1.3, h + 0.2), fx(M["metal"], ALL), scale=(1, 1))
    for (ax, ay), (bx_, by) in (((-1.3, -1.3), (1.3, -1.3)), ((1.3, -1.3), (1.3, 1.3)), ((1.3, 1.3), (-1.3, 1.3)), ((-1.3, 1.3), (-1.3, -1.3))):
        bar(b, (x + ax, y + ay, h + 1.0), (x + bx_, y + by, h + 1.0), 0.04, M["metal"])
        bar(b, (x + ax, y + ay, h + 0.2), (x + ax, y + ay, h + 1.0), 0.04, M["metal"])
    lm = M["lamp_o"] if color == "orange" else M["lamp_w"]
    px, py = -face[1], face[0]
    for i in range(4):
        o = -1.05 + i * 0.7
        hx, hy = x + face[0] * 1.0 + px * o, y + face[1] * 1.0 + py * o
        b.box((hx - 0.3, hy - 0.3, h + 0.3), (hx + 0.3, hy + 0.3, h + 0.9), fx(M["metal"], OPEN), scale=(1, 1))
        b.box((hx + face[0] * 0.3 - 0.25 * abs(py), hy + face[1] * 0.3 - 0.25 * abs(px), h + 0.35),
              (hx + face[0] * 0.31 + 0.25 * abs(py), hy + face[1] * 0.31 + 0.25 * abs(px), h + 0.85), fx(lm, SIDES), scale=(1, 1))
    lamp("mast", color, (x, y, 0), (x + face[0] * 1.5, y + face[1] * 1.5, h + 0.4))


def catenary(coll):
    b, wires, col = B(), B(), B()
    ya, yb = PLATFORMS[0][0] + 0.6, PLATFORMS[1][1] - 0.5
    for x in GANTRY_X:                                    # жёсткие поперечины над главными путями: мачты на платформах
        for y in (ya, yb):
            concrete_pole(b, col, x, y, 10.4)
        lattice_box(b, x, ya - 0.3, yb + 0.3, 9.4, 10.4, 0.8)
        for y in (ya + 6, 0.0, yb - 6):                   # стойки с изоляторами над ригелем
            bar(b, (x, y, 10.4), (x, y, 11.6), 0.08, M["metal"])
        bar(b, (x, ya + 6, 11.6), (x, yb - 6, 11.6), 0.06, M["metal"])
        for yc in TRACKS_MAIN:
            hanger(wires, x, yc, 9.4)
    for x in PORTAL_X:                                    # порталы: два столба и лёгкий ригель на 2–3 пути
        for a, c in ((-52.0, -33.4), (51.6, 68.75), (68.75, 91.2)):
            for y in (a, c):
                concrete_pole(b, col, x, y, 9.6, 0.2, 0.14)
            lattice_box(b, x, a, c, 8.7, 9.2, 0.45)
            for yc in TRACKS:
                if a < yc < c:
                    hanger(wires, x, yc, 8.7)
    for yc in TRACKS:                                     # провода: несущий трос и контактный, струны между ними
        for z in (WIRE_C, WIRE_M):
            wires.box((-FAR, yc - 0.015, z - 0.015), (FAR, yc + 0.015, z + 0.015), fx(M["metal"], ('+Y', '-Y', '-Z', '+Z')), scale=(8, 1))
        x = -FAR
        while x < FAR:
            wires.box((x - 0.01, yc - 0.01, WIRE_C), (x + 0.01, yc + 0.01, WIRE_M), fx(M["metal"], ('+X', '-Y')), scale=(1, 1))
            x += 8.75
    # прожекторные мачты: тёплая у моста над парком, холодная белая на дальнем краю парка
    floodlight_tower(b, col, -8.0, 49.0, 19.0, (0, 1), "orange")
    floodlight_tower(b, col, 60.0, 92.5, 19.0, (0, -1), "white")
    # светофоры: трёхлинзовые головки висят на ригеле над главными путями (фото 10005), карликовые — у путей
    for yc in TRACKS_MAIN:
        bar(b, (12.0, yc, 9.4), (12.0, yc, 8.4), 0.06, M["metal"])
        b.box((11.8, yc - 0.22, 7.2), (12.2, yc + 0.22, 8.4), fx(M["dark"], ALL), scale=(1, 1))
        b.box((11.78, yc - 0.12, 7.95), (11.8, yc + 0.12, 8.2), fx(M["lamp_g"], ('-X',)), scale=(1, 1))
    for x, y in ((-62.0, -7.6), (70.0, 5.9), (-40.0, -45.0), (35.0, 63.2)):
        b.box((x - 0.25, y - 0.2, 0), (x + 0.25, y + 0.2, 0.55), fx(M["dark"], OPEN), scale=(1, 1))
        b.box((x - 0.26, y - 0.08, 0.3), (x - 0.25, y + 0.08, 0.45), fx(M["lamp_w"], ('-X',)), scale=(1, 1))
    return build(b, "EbCatenary_nocol", coll), build(wires, "EbWires_nocol", coll), build(col, "EbCatenaryCol-colonly", coll)


# ------------------------------------------------------------------ подвижной состав
def bogies(b, x0, x1, y):
    for xc in (x0 + 2.2, x1 - 2.2):
        b.box((xc - 1.3, y - 1.05, 0.25), (xc + 1.3, y + 1.05, 1.0), fx(M["metal"], OPEN), scale=(1, 1))
        for xw in (xc - 0.9, xc + 0.9):
            for yw in (y - 0.76, y + 0.76):
                b.cyl((xw, yw - 0.07, 0.5), (xw, yw + 0.07, 0.5), 0.47, 0.47, M["metal"], segs=8, caps=True)


def tank_car(b, col, x0, y, row):
    L = 12.0
    x1 = x0 + L
    bogies(b, x0, x1, y)
    b.box((x0 + 0.3, y - 1.4, 1.0), (x1 - 0.3, y + 1.4, 1.3), fx(M["metal"], ALL), scale=(2, 0.3))
    zc, r, segs = 2.75, 1.45, 12
    ta, tb = x0 + 0.9, x1 - 0.9
    v0 = 0.5 if row == 0 else 0.0
    for i in range(segs):
        a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
        pa = lambda x, a: (x, y + r * math.cos(a), zc + r * math.sin(a))
        va = lambda a: v0 + 0.5 * (0.5 + 0.5 * math.sin(a))          # верх котла — верх полосы, низ — грязь
        b.poly([pa(ta, a0), pa(tb, a0), pa(tb, a1), pa(ta, a1)], [(0, va(a0)), (1, va(a0)), (1, va(a1)), (0, va(a1))], M["tank"])
    for xe, s in ((ta, -1), (tb, 1)):                                   # днища — плоские конусы
        tip = (xe + s * 0.5, y, zc)
        for i in range(segs):
            a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
            p0 = (xe, y + r * math.cos(a0), zc + r * math.sin(a0))
            p1 = (xe, y + r * math.cos(a1), zc + r * math.sin(a1))
            quad(b, [p0, p1, tip, tip], M["tank"], (s, 0, 0), uvs=[(0, v0 + 0.3), (0.05, v0 + 0.3), (0.02, v0 + 0.25), (0.02, v0 + 0.25)])
    b.box((x0 + 1.2, y - 0.55, zc + r - 0.12), (x1 - 1.2, y + 0.55, zc + r + 0.02), fx(M["snow"], OPEN), scale=(3, 3))
    b.cyl(((x0 + x1) / 2, y, zc + r - 0.1), ((x0 + x1) / 2, y, zc + r + 0.45), 0.45, 0.45, M["metal"], segs=8, caps=True)   # горловина
    col.box((x0, y - 1.5, 0.2), (x1, y + 1.5, zc + r), fx(M["plinth"], ALL))


def gondola_car(b, col, x0, y, load=True):
    L = 13.9
    x1 = x0 + L
    bogies(b, x0, x1, y)
    za, zb_ = 1.2, 3.3
    b.box((x0, y - 1.55, za), (x1, y + 1.55, zb_), {'+Y': (M["gondola"], (1, 0, 0, 1)), '-Y': (M["gondola"], (0, 0, 1, 1))})
    b.box((x0, y - 1.55, za), (x1, y + 1.55, zb_), fx(M["metal"], ('+X', '-X', '-Z')), scale=(1.5, 1.5))
    b.box((x0, y - 1.55, zb_), (x1, y + 1.55, zb_ + 0.08), fx(M["metal"], ('+Y', '-Y', '+Z')), scale=(2, 1))
    if load:                                                            # щебень горкой, присыпан снегом
        hx = [(x0 + 0.2, zb_ - 0.2), (x0 + L * 0.3, zb_ + 0.55), (x0 + L * 0.7, zb_ + 0.6), (x1 - 0.2, zb_ - 0.2)]
        for (xa, za_), (xb, zb2) in zip(hx, hx[1:]):
            quad(b, [(xa, y - 1.45, zb_ - 0.1), (xb, y - 1.45, zb_ - 0.1), (xb, y, zb2), (xa, y, za_)], M["ballast"], (0, -0.3, 1), (4, 4))
            quad(b, [(xa, y + 1.45, zb_ - 0.1), (xb, y + 1.45, zb_ - 0.1), (xb, y, zb2), (xa, y, za_)], M["ballast"], (0, 0.3, 1), (4, 4))
    else:
        b.box((x0 + 0.1, y - 1.45, za + 0.3), (x1 - 0.1, y + 1.45, za + 0.32), fx(M["snow"], ('+Z',)), scale=(3, 3))
    col.box((x0, y - 1.6, 0.2), (x1, y + 1.6, zb_ + 0.6), fx(M["plinth"], ALL))


def box_car(b, col, x0, y):
    """Крытый вагон: высокий ржавый кузов (текстура полувагона), крыша под снегом."""
    L = 14.7
    x1 = x0 + L
    bogies(b, x0, x1, y)
    za, zb_ = 1.2, 4.3
    b.box((x0, y - 1.55, za), (x1, y + 1.55, zb_), {'+Y': (M["gondola"], (1, 0, 0, 1)), '-Y': (M["gondola"], (0, 0, 1, 1))})
    b.box((x0, y - 1.55, za), (x1, y + 1.55, zb_), fx(M["metal"], ('+X', '-X', '-Z')), scale=(1.5, 1.5))
    prof = [(-1.6, zb_), (-0.8, zb_ + 0.3), (0.8, zb_ + 0.3), (1.6, zb_)]
    for (ya_, za_), (yb_, zb2) in zip(prof, prof[1:]):
        quad(b, [(x0, y + ya_, za_), (x1, y + ya_, za_), (x1, y + yb_, zb2), (x0, y + yb_, zb2)], M["snow"], (0, (ya_ + yb_) / 2, 1), (3, 3))
    for xe, s in ((x0, -1), (x1, 1)):
        quad(b, [(xe, y + p[0], p[1]) for p in prof], M["metal"], (s, 0, 0), uvs=[(0, 0)] * 4)
    b.box((x0 + L / 2 - 1.5, y - 1.57, za + 0.2), (x0 + L / 2 + 1.5, y + 1.57, zb_ - 0.3), fx(M["metal"], ('+Y', '-Y')), scale=(1.5, 1.5))
    col.box((x0, y - 1.6, 0.2), (x1, y + 1.6, zb_ + 0.3), fx(M["plinth"], ALL))


def container_car(b, col, x0, y, row):
    L = 13.6
    x1 = x0 + L
    bogies(b, x0, x1, y)
    b.box((x0, y - 1.4, 1.0), (x1, y + 1.4, 1.35), fx(M["metal"], ALL), scale=(2, 0.35))
    ca, cb = x0 + 0.7, x1 - 0.7
    v0, v1 = (3 - row) * 0.25, (4 - row) * 0.25
    b.box((ca, y - 1.22, 1.35), (cb, y + 1.22, 3.95), {'+Y': (M["container"], (1, v0, 0, v1)), '-Y': (M["container"], (0, v0, 1, v1)),
                                                       '+X': (M["container"], (0, v0, 0.2, v1)), '-X': (M["container"], (0, v0, 0.2, v1))})
    b.box((ca, y - 1.22, 3.95), (cb, y + 1.22, 4.05), fx(M["snow"], OPEN), scale=(3, 3))
    col.box((x0, y - 1.4, 0.2), (x1, y + 1.4, 4.05), fx(M["plinth"], ALL))


def coach_car(b, col, x0, y):
    L = 24.5
    x1 = x0 + L
    bogies(b, x0 + 1.5, x1 - 1.5, y)
    za, zb_ = 1.1, 4.1
    b.box((x0, y - 1.55, za), (x1, y + 1.55, zb_), {'+Y': (M["coach"], (1, 0, 0, 1)), '-Y': (M["coach"], (0, 0, 1, 1))})
    b.box((x0, y - 1.55, za), (x1, y + 1.55, zb_), fx(M["metal"], ('+X', '-X', '-Z')), scale=(1.5, 1.5))
    prof = [(-1.55, zb_), (-1.2, zb_ + 0.35), (-0.5, zb_ + 0.5), (0.5, zb_ + 0.5), (1.2, zb_ + 0.35), (1.55, zb_)]
    for (ya_, za_), (yb_, zb2) in zip(prof, prof[1:]):
        quad(b, [(x0, y + ya_, za_), (x1, y + ya_, za_), (x1, y + yb_, zb2), (x0, y + yb_, zb2)], M["snow"], (0, (ya_ + yb_) / 2, 1), (3, 3))
    for xe, s in ((x0, -1), (x1, 1)):
        quad(b, [(xe, y + p[0], p[1]) for p in prof], M["metal"], (s, 0, 0), uvs=[(0, 0)] * 6)
    b.box((x0 + 5, y - 1.2, 0.6), (x1 - 5, y + 1.2, za), fx(M["metal"], OPEN), scale=(1, 1))
    col.box((x0, y - 1.6, 0.2), (x1, y + 1.6, zb_ + 0.5), fx(M["plinth"], ALL))


def string(b, col, y, x0, x1, kinds, gaps=()):
    """Состав на пути y от x0 до x1: вагоны по кругу из kinds, с разрывами gaps (номера вагонов)."""
    x, i = x0, 0
    while x < x1:
        k = kinds[i % len(kinds)]
        L = {"tank_y": 12.0, "tank_b": 12.0, "gondola": 13.9, "gondola_e": 13.9, "box": 14.7, "cont": 13.6}[k]
        if i not in gaps:
            if k == "tank_y":
                tank_car(b, col, x, y, 0)
            elif k == "tank_b":
                tank_car(b, col, x, y, 1)
            elif k == "gondola":
                gondola_car(b, col, x, y)
            elif k == "gondola_e":
                gondola_car(b, col, x, y, load=False)
            elif k == "box":
                box_car(b, col, x, y)
            else:
                container_car(b, col, x, y, i % 4)
        x += L + 0.8
        i += 1


def trains(coll):
    b, col = B(), B()
    # грузовой парк (фото 10033, 10016, 10020): ближний к мосту ряд — жёлтые цистерны под снегом
    string(b, col, TRACKS_YARD[0], -150, 40, ["tank_y"], gaps=(9,))
    string(b, col, TRACKS_YARD[1], -140, 62, ["box", "box", "gondola", "box"], gaps=(4, 5))
    string(b, col, TRACKS_YARD[2], -120, 22, ["cont"], gaps=(3,))
    string(b, col, TRACKS_YARD[3], -95, 80, ["gondola", "gondola_e", "box"], gaps=(6,))
    string(b, col, TRACKS_YARD[4], -150, -8, ["tank_b", "tank_y", "tank_b"])
    string(b, col, TRACKS_YARD[5], -60, 40, ["gondola_e", "box"])
    string(b, col, TRACKS_YARD[6], -130, -55, ["tank_b"])
    # главные: полувагоны со щебнем прямо под мостом (10013), пассажирский у платформы вокзала (10016, 10020)
    string(b, col, TRACKS_MAIN[2], -30, 62, ["gondola"])
    x = -232.0
    for i in range(9):
        coach_car(b, col, x, TRACKS_MAIN[3])
        x += 25.3
    # восточные пути: старые крытые вагоны в граффити (10008)
    string(b, col, TRACKS_EAST[1], -120, -20, ["box"], gaps=(2,))
    string(b, col, TRACKS_EAST[2], 30, 115, ["box", "gondola_e"])
    return build(b, "EbTrains_nocol", coll), build(col, "EbTrainsCol-colonly", coll)


# ------------------------------------------------------------------ платформы, вокзал
def booth(b, col, x, y, w, d, h, z0=PLAT_H, kind="blue"):
    """Будка на платформе (10018, 10023): голубой профнастил, односкатная крыша с навесом к путям,
    окно с решёткой и ставнями, дверь с торца. kind="white" — белёная будка с крышей из листов фанеры (10007, 10022)."""
    wall = M["booth"] if kind == "blue" else M["station"]
    b.box((x - w / 2, y - d / 2, z0), (x + w / 2, y + d / 2, z0 + h), fx(wall, SIDES), scale=(2, 2))
    col.box((x - w / 2, y - d / 2, z0), (x + w / 2, y + d / 2, z0 + h), fx(M["plinth"], ALL))
    ov = 0.5
    pts = [(x - w / 2 - 0.2, y - d / 2 - 0.2, z0 + h + 0.25), (x + w / 2 + 0.2, y - d / 2 - 0.2, z0 + h + 0.25),
           (x + w / 2 + 0.2, y + d / 2 + ov, z0 + h - 0.05), (x - w / 2 - 0.2, y + d / 2 + ov, z0 + h - 0.05)]
    quad(b, pts, M["snow"], (0, 0.1, 1), (3, 3))
    quad(b, [(p[0], p[1], p[2] - 0.08) for p in pts], M["metal"] if kind == "blue" else M["wood"], (0, 0, -1), (2, 2))
    quad(b, [(x - w / 2, y - d / 2 - 0.01, z0 + h), (x + w / 2, y - d / 2 - 0.01, z0 + h), (x + w / 2, y - d / 2 - 0.01, z0 + h + 0.2),
             (x - w / 2, y - d / 2 - 0.01, z0 + h + 0.2)], wall, (0, -1, 0), (2, 2))
    yd = y + d / 2 + 0.01
    b.box((x - 0.6, yd, z0 + 1.0), (x + 0.6, yd + 0.02, z0 + 2.0), fx(M["dark"], ('+Y',)), scale=(1, 1))
    for i in range(5):
        xx = x - 0.6 + i * 0.3
        bar(b, (xx, yd + 0.05, z0 + 1.0), (xx, yd + 0.05, z0 + 2.0), 0.025, M["metal"])
    for s in (-1, 1):
        b.box((x + s * 0.6 + (0 if s > 0 else -0.6), yd, z0 + 1.0), (x + s * 0.6 + (0.6 if s > 0 else 0), yd + 0.03, z0 + 2.0),
              fx(M["wood"], ('+Y', '-Y')), scale=(1, 1))
    xd = x - w / 2 - 0.01
    b.box((xd - 0.02, y - 0.45, z0), (xd, y + 0.45, z0 + 2.0), fx(M["door"], ('-X',)), scale=(0.9, 2.0))


def bench(b, col, x, y, face):
    for dx in (-0.8, 0.8):
        b.box((x + dx - 0.05, y - 0.2, PLAT_H), (x + dx + 0.05, y + 0.2, PLAT_H + 0.45), fx(M["metal"], SIDES), scale=(1, 1))
    b.box((x - 1.0, y - 0.22, PLAT_H + 0.45), (x + 1.0, y + 0.22, PLAT_H + 0.5), fx(M["blue"], ALL), scale=(1, 1))
    yb = y - face * 0.2
    b.box((x - 1.0, yb - 0.03, PLAT_H + 0.6), (x + 1.0, yb + 0.03, PLAT_H + 0.95), fx(M["blue"], ALL), scale=(1, 1))
    b.box((x - 1.0, y - 0.22, PLAT_H + 0.5), (x + 1.0, y + 0.22, PLAT_H + 0.56), fx(M["snow"], OPEN), scale=(3, 3))
    col.box((x - 1.0, y - 0.25, PLAT_H), (x + 1.0, y + 0.25, PLAT_H + 0.5), fx(M["plinth"], ALL))


def t_pole(b, col, x, y, color):
    """Фонарь платформы (10022, 10024): бетонный столб 12 м, Т-траверса поперёк путей, плафоны на концах."""
    b.cyl((x, y, PLAT_H), (x, y, PLAT_H + 12.0), 0.18, 0.11, M["pole"], segs=8, su=2)
    col.box((x - 0.18, y - 0.18, PLAT_H), (x + 0.18, y + 0.18, PLAT_H + 12), fx(M["plinth"], ALL))
    z = PLAT_H + 11.8
    b.box((x - 0.05, y - 1.25, z), (x + 0.05, y + 1.25, z + 0.1), fx(M["metal"], ALL), scale=(1, 1))
    m = M["lamp_g"] if color == "green" else M["lamp_o"]
    for s in (-1, 1):
        hy = y + s * 1.2
        b.box((x - 0.22, hy - 0.18, z - 0.18), (x + 0.22, hy + 0.18, z + 0.02), fx(M["metal"], OPEN), scale=(1, 1))
        b.box((x - 0.18, hy - 0.14, z - 0.24), (x + 0.18, hy + 0.14, z - 0.18), fx(m, ('-Z', '+X', '-X', '+Y', '-Y')), scale=(1, 1))
    lamp("platform", color, (x, y, PLAT_H), (x, y, z - 0.3))


def street_lamp(b, col, x, y, arm, kind="street", color="orange", h=7.4, light=True):
    """Уличная «кобра» на бетонном столбе."""
    b.cyl((x, y, 0), (x, y, h), 0.15, 0.09, M["pole"], segs=6, su=2)
    col.box((x - 0.15, y - 0.15, 0), (x + 0.15, y + 0.15, h), fx(M["plinth"], ALL))
    ax, ay = arm
    b.cyl((x, y, h - 0.1), (x + ax * 1.4, y + ay * 1.4, h + 0.3), 0.05, 0.045, M["metal"], segs=6)
    hx, hy = x + ax * 1.6, y + ay * 1.6
    b.box((hx - 0.3, hy - 0.18, h + 0.2), (hx + 0.3, hy + 0.18, h + 0.4), fx(M["metal"], ALL), scale=(1, 1))
    b.box((hx - 0.25, hy - 0.14, h + 0.12), (hx + 0.25, hy + 0.14, h + 0.2), fx(M["lamp_o"] if color == "orange" else M["lamp_w"], ('-Z',)), scale=(1, 1))
    if light:
        lamp(kind, color, (x, y, 0), (hx, hy, h + 0.05))


def gable(b, cx, cy, ang, w, d, wall_h, ridge, wall_m, roof_m=None, ov=0.4, wall_uv=None, lit=0.0, col=None, chimney=True):
    """Дом с двускатной крышей (конёк вдоль локальной оси w), повёрнут на ang вокруг (cx, cy).
    wall_uv(k) — функция клетки атласа стен; без неё — мировая проекция."""
    c, s = math.cos(ang), math.sin(ang)
    P = lambda lx, ly, z: (cx + lx * c - ly * s, cy + lx * s + ly * c, z)
    N = lambda nx, ny: (nx * c - ny * s, nx * s + ny * c, 0)
    hw, hd = w / 2, d / 2
    for (ax, ay), (bx_, by), n in (((-hw, -hd), (hw, -hd), (0, -1)), ((hw, hd), (-hw, hd), (0, 1)),
                                   ((hw, -hd), (hw, hd), (1, 0)), ((-hw, hd), (-hw, -hd), (-1, 0))):
        L = math.hypot(bx_ - ax, by - ay)
        k = max(1, round(L / 4.5))
        for i in range(k):
            t0, t1 = i / k, (i + 1) / k
            p0 = (ax + (bx_ - ax) * t0, ay + (by - ay) * t0)
            p1 = (ax + (bx_ - ax) * t1, ay + (by - ay) * t1)
            pts = [P(p0[0], p0[1], 0), P(p1[0], p1[1], 0), P(p1[0], p1[1], wall_h), P(p0[0], p0[1], wall_h)]
            if wall_uv:
                u0, v0, u1, v1 = wall_uv(rnd.random() < lit)
                quad(b, pts, wall_m, N(*n), uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
            else:
                quad(b, pts, wall_m, N(*n), (3, 3))
    for sx in (-1, 1):                                    # фронтоны
        pts = [P(sx * hw, -hd, wall_h), P(sx * hw, hd, wall_h), P(sx * hw, 0, wall_h + ridge)]
        if wall_uv:
            u0, v0, u1, v1 = wall_uv(False)
            quad(b, pts, wall_m, N(sx, 0), uvs=[(u0 + 0.01, v1 - 0.06), (u1 - 0.01, v1 - 0.06), ((u0 + u1) / 2, v1 - 0.01)])
        else:
            quad(b, pts, wall_m, N(sx, 0), (3, 3))
    roof_m = roof_m or M["roof"]
    ez = wall_h - ov * ridge / hd
    for sy in (-1, 1):                                    # скаты: сверху снег, снизу — кровля
        pts = [P(-hw - ov, sy * (hd + ov), ez), P(hw + ov, sy * (hd + ov), ez), P(hw + ov, 0, wall_h + ridge), P(-hw - ov, 0, wall_h + ridge)]
        nz = Vector(N(0, sy)) * ridge / hd + Vector((0, 0, 1))
        quad(b, pts, M["snow"], tuple(nz), uvs=[(0, 0), (w / 3, 0), (w / 3, (hd + ov) / 3), (0, (hd + ov) / 3)])
        quad(b, [(p[0], p[1], p[2] - 0.12) for p in pts], roof_m, (0, 0, -1), (3, 3))
    if chimney:
        lx, ly = hw * 0.4, hd * 0.3
        zt = wall_h + ridge + 0.7
        for (ax, ay), (bx_, by), n in (((-0.25, -0.25), (0.25, -0.25), (0, -1)), ((0.25, -0.25), (0.25, 0.25), (1, 0)),
                                       ((0.25, 0.25), (-0.25, 0.25), (0, 1)), ((-0.25, 0.25), (-0.25, -0.25), (-1, 0))):
            quad(b, [P(lx + ax, ly + ay, wall_h + ridge * 0.4), P(lx + bx_, ly + by, wall_h + ridge * 0.4), P(lx + bx_, ly + by, zt), P(lx + ax, ly + ay, zt)],
                 M["plinth"], N(*n), (1, 1))
        quad(b, [P(lx - 0.25, ly - 0.25, zt), P(lx + 0.25, ly - 0.25, zt), P(lx + 0.25, ly + 0.25, zt), P(lx - 0.25, ly + 0.25, zt)], M["snow"], (0, 0, 1), (1, 1))
    if col is not None:
        quad(col, [P(-hw, -hd, 0), P(hw, -hd, 0), P(hw, hd, 0), P(-hw, hd, 0)], M["plinth"], (0, 0, -1))
        for (ax, ay), (bx_, by), n in (((-hw, -hd), (hw, -hd), (0, -1)), ((hw, -hd), (hw, hd), (1, 0)),
                                       ((hw, hd), (-hw, hd), (0, 1)), ((-hw, hd), (-hw, -hd), (-1, 0))):
            quad(col, [P(ax, ay, 0), P(bx_, by, 0), P(bx_, by, wall_h + ridge), P(ax, ay, wall_h + ridge)], M["plinth"], N(*n))


def station(b, col):
    """Вокзал «Одеса-Східна» (спутник + фото 10017): к северо-востоку от моста, между главными путями и парком.
    Стены 18 × 9 м, со стороны моста — открытый портик 8 м под общей крышей (крыша по спутнику X 35…62) (две квадратные колонны и фронтон),
    двускатная крыша с коньком вдоль путей, синие буквы на белом фризе по стене к полю."""
    x0, x1, y0, y1, wh = 44.0, 62.0, 25.5, 34.5, 3.3
    yc = (y0 + y1) / 2
    b.box((x0, y0, 0), (x1, y1, wh), fx(M["station"], SIDES), scale=(3, 3))
    col.box((x0, y0, 0), (x1, y1, wh + 2.5), fx(M["plinth"], ALL))
    b.box((x0 - 0.1, y0 - 0.1, 0), (x1 + 0.1, y1 + 0.1, 0.5), fx(M["plinth"], SIDES), scale=(3.6, 0.9))
    for y in (y0 + 0.3, y1 - 0.3):                         # колонны портика
        b.box((36.05, y - 0.25, 0), (36.55, y + 0.25, wh - 0.2), fx(M["station"], SIDES), scale=(3, 3))
        col.box((36.05, y - 0.25, 0), (36.55, y + 0.25, wh), fx(M["plinth"], ALL))
    b.box((36.0, y0 - 0.1, 0), (x0, y1 + 0.1, 0.25), fx(M["plinth"], OPEN), scale=(3.6, 0.9))     # пол портика
    b.box((35.9, y0 - 0.2, wh - 0.6), (x0, y1 + 0.2, wh), fx(M["station"], ('-X', '+Y', '-Y', '-Z')), scale=(3, 3))   # фриз
    ov, ridge = 0.8, 2.5
    for sy in (-1, 1):
        ya = yc + sy * (4.5 + ov)
        pts = [(35.5, ya, wh - 0.2), (62.6, ya, wh - 0.2), (62.6, yc, wh + ridge), (35.5, yc, wh + ridge)]
        quad(b, pts, M["snow"], (0, sy * 0.5, 1), (3, 3))
        quad(b, [(p[0], p[1], p[2] - 0.15) for p in pts], M["roof"], (0, 0, -1), (3, 3))
    for xe, sx in ((35.9, -1), (x1, 1)):                    # фронтоны
        quad(b, [(xe, y0 - 0.2, wh), (xe, y1 + 0.2, wh), (xe, yc, wh + ridge - 0.1)], M["station"], (sx, 0, 0), (3, 3))
    # вывеска: синие буквы на белом фризе по стене к полю (+Y), ближе к портику
    b.box((44.8, y1 + 0.01, 2.55), (52.8, y1 + 0.03, 3.2), {'+Y': (M["sign"], (0, 0, 1, 1))})
    # окна и двери
    for x in (47.0, 51.0, 55.0, 59.0):
        for y, face in ((y0 - 0.01, '-Y'), (y1 + 0.01, '+Y')):
            if face == '+Y' and x < 53:
                continue
            m = M["glass"] if (x, face) == (55.0, '-Y') else M["dark"]
            b.box((x - 0.7, y - 0.01, 1.0), (x + 0.7, y + 0.01, 2.4), fx(m, (face,)), scale=(1.4, 1.4))
    b.box((x0 - 0.02, yc - 0.6, 0.25), (x0, yc + 0.6, 2.4), fx(M["door"], ('-X',)), scale=(1.2, 2.2))
    lamp("station", "orange", (40.0, yc, 0), (40.0, yc, wh - 0.4))
    b.box((39.75, yc - 0.15, wh - 0.65), (40.25, yc + 0.15, wh - 0.6), fx(M["lamp_o"], ('-Z',)), scale=(1, 1))
    # перрон перед вокзалом и дорожка от прохода в ограде
    quad(b, [(30.0, 16.8, 0.03), (66.0, 16.8, 0.03), (66.0, 25.3, 0.03), (30.0, 25.3, 0.03)], M["platform"], (0, 0, 1), (4, 4))
    for x in (30.0, 36.0):                                  # ступени с платформы вниз к перрону
        pass
    quad(col, [(30.0, 16.95, PLAT_H), (36.0, 16.95, PLAT_H), (36.0, 19.5, 0.02), (30.0, 19.5, 0.02)], M["plinth"], (0, 0, 1))
    quad(b, [(30.0, 16.95, PLAT_H), (36.0, 16.95, PLAT_H), (36.0, 19.5, 0.04), (30.0, 19.5, 0.04)], M["platform"], (0, 0.3, 1), (4, 4))
    # служебные постройки: двухэтажное здание дальше по путям и сарай
    b.box((102.0, 27.5, 0), (139.0, 42.5, 7.0), fx(M["station"], SIDES), scale=(3, 3))
    b.box((102.0, 27.5, 7.0), (139.0, 42.5, 7.2), fx(M["snow"], OPEN), scale=(3, 3))
    for i in range(8):
        for z in (1.2, 4.4):
            b.box((104.5 + i * 4.4, 27.49, z), (106.0 + i * 4.4, 27.5, z + 1.5), fx(M["dark"], ('-Y',)), scale=(1, 1))
    col.box((102.0, 27.5, 0), (139.0, 42.5, 7.0), fx(M["plinth"], ALL))
    b.box((67.0, 36.0, 0), (78.0, 41.0, 2.6), fx(M["corr"], SIDES), scale=(4, 3))
    b.box((66.8, 35.8, 2.6), (78.2, 41.2, 2.8), fx(M["snow"], OPEN), scale=(3, 3))
    col.box((67.0, 36.0, 0), (78.0, 41.0, 2.8), fx(M["plinth"], ALL))


def shelter(b, col, x0, x1):
    """Навес на городской платформе (фото 10014, панорама p2): сзади белая стена в граффити,
    спереди квадратные столбы, односкатная дощатая крыша к путям, скамейки вдоль стены."""
    ya, yb = PLATFORMS[0][0] + 0.25, PLATFORMS[0][1] - 0.5
    z0, hw_, hf = PLAT_H, 2.5, 2.9                            # высота стены, высота крыши у стены
    b.box((x0, ya, z0), (x1, ya + 0.22, z0 + hw_), fx(M["station"], ('+Y', '-Y', '+X', '-X', '+Z')), scale=(3, 3))
    col.box((x0, ya, z0), (x1, ya + 0.22, z0 + hw_), fx(M["plinth"], ALL))
    n = max(1, round((x1 - x0) / 4.5))
    for i in range(n + 1):
        x = x0 + 0.15 + (x1 - x0 - 0.3) * i / n
        if abs(x) < 0.9:                                   # тут опора моста
            continue
        for y, h in ((yb - 0.15, hf - 0.25), (ya + 0.35, hf)):
            b.box((x - 0.14, y - 0.14, z0), (x + 0.14, y + 0.14, z0 + h), fx(M["pier"], SIDES), scale=(1.5, 1.5))
        col.box((x - 0.14, yb - 0.29, z0), (x + 0.14, yb, z0 + hf), fx(M["plinth"], ALL))
        b.box((x - 0.08, ya + 0.2, z0 + hf - 0.35), (x + 0.08, yb + 0.1, z0 + hf - 0.2), fx(M["wood"], ALL), scale=(1, 1))
    pts = [(x0 - 0.2, ya - 0.1, z0 + hf + 0.05), (x1 + 0.2, ya - 0.1, z0 + hf + 0.05), (x1 + 0.2, yb + 0.4, z0 + hf - 0.3), (x0 - 0.2, yb + 0.4, z0 + hf - 0.3)]
    quad(b, pts, M["snow"], (0, 0.1, 1), (3, 3))
    quad(b, [(p_[0], p_[1], p_[2] - 0.06) for p_ in pts], M["wood"], (0, 0, -1), (2, 2))
    quad(b, [(x0 - 0.2, yb + 0.4, z0 + hf - 0.36), (x1 + 0.2, yb + 0.4, z0 + hf - 0.36), (x1 + 0.2, yb + 0.4, z0 + hf - 0.3), (x0 - 0.2, yb + 0.4, z0 + hf - 0.3)],
         M["wood"], (0, 1, 0), (2, 2))
    for x in (x0 + 2.5, x0 + 7.0, x1 - 7.0, x1 - 2.5):
        bench(b, col, x, ya + 0.75, 1)


def props(coll):
    b, col = B(), B()
    # навес под мостом на городской платформе, голубая будка у низа юго-западной лестницы (10018, 10023, панорама p1 ya000/ya045),
    # белёная будка с дощатой крышей дальше (10007, 10022, 10024)
    shelter(b, col, -9.0, 9.0)
    yf = PLATFORMS[0][0] + 0.35                              # будки прижаты к ограде — вдоль путей остаётся проход 2 м
    booth(b, col, -23.0, yf + 1.1, 2.8, 2.2, 2.5)
    booth(b, col, -36.0, yf + 1.1, 3.0, 2.2, 2.3, kind="white")
    # голубой павильон на платформе у вокзала, у низа лестницы (спутник 2021: белая крыша X 21…30; фото 10027)
    booth(b, col, 26.0, (PLATFORMS[1][0] + PLATFORMS[1][1]) / 2 + 0.2, 6.0, 2.6, 2.6)
    b.box((-5.0, -19.5, 0), (-3.0, -17.5, 2.3), fx(M["yellow"], SIDES), scale=(1, 1))
    b.box((-5.2, -19.7, 2.3), (-2.8, -17.3, 2.45), fx(M["snow"], OPEN), scale=(3, 3))
    col.box((-5.0, -19.5, 0), (-3.0, -17.5, 2.3), fx(M["plinth"], ALL))
    for x, y, legs in ((-28.0, -40.0, True), (-60.0, -0.9, False), (38.0, 46.0, False), (-70.0, 50.5, False), (24.0, -0.9, False)):
        z0 = 1.0 if legs else 0.0
        if legs:
            for dx in (-0.35, 0.35):
                bar(b, (x + dx, y, 0), (x + dx, y, z0), 0.08, M["metal"])
        b.box((x - 0.45, y - 0.35, z0), (x + 0.45, y + 0.35, z0 + 1.6), fx(M["cabinet"], SIDES), scale=(1, 1.6))
        b.box((x - 0.5, y - 0.4, z0 + 1.6), (x + 0.5, y + 0.4, z0 + 1.75), fx(M["snow"], OPEN), scale=(3, 3))
        col.box((x - 0.45, y - 0.35, 0), (x + 0.45, y + 0.35, z0 + 1.6), fx(M["plinth"], ALL))
    # скамейки (синие) лицом к путям
    for x in (-80.0, -60.0, 30.0):
        bench(b, col, x, PLATFORMS[0][0] + 1.2, 1)
    for x in (-50.0, 25.0, 60.0):
        bench(b, col, x, PLATFORMS[1][1] - 1.2, -1)
    # фонари платформ: городская — натрий, у вокзала — зелёные ртутные
    for x in (-100.0, -74.0, -48.0, -22.0, 4.0, 30.0, 56.0, 82.0, 106.0):           # шаг ~26 м, как на фото 10001
        t_pole(b, col, x, PLATFORMS[0][0] + 0.7, "orange")
        t_pole(b, col, x + 4.0, PLATFORMS[1][1] - 0.7, "green")
    station(b, col)
    # полоса между восточными путями и платформой: штабели плит и сараи
    for x in (-62.0, -55.0):
        for k in range(3):
            b.box((x - 3, -27.5 - 0.6, k * 0.22), (x + 3, -27.5 + 0.6, k * 0.22 + 0.2), fx(M["plinth"], OPEN), scale=(3.6, 0.9))
        col.box((x - 3, -28.1, 0), (x + 3, -26.9, 0.66), fx(M["plinth"], ALL))
    for x in (8.0, 43.0, 49.0):                              # сараи за служебной дорогой (спутник 2021)
        b.box((x - 2.5, -31.5, 0), (x + 2.5, -28.0, 2.4), fx(M["corr"], SIDES), scale=(4, 3))
        b.box((x - 2.7, -31.7, 2.4), (x + 2.7, -27.8, 2.55), fx(M["snow"], OPEN), scale=(3, 3))
        col.box((x - 2.5, -31.5, 0), (x + 2.5, -28.0, 2.55), fx(M["plinth"], ALL))
    # служебная дорога вдоль городской платформы и проезд вдоль моста к улице (спутник 2021)
    strip(b, [(-XMAX, -19.8), (XMAX, -19.8)], 3.4, M["road"])
    strip(b, [(-10.0, -21.5), (-10.0, STREET[1])], 3.2, M["road"])
    return build(b, "EbProps", coll), build(col, "EbPropsCol-colonly", coll)


# ------------------------------------------------------------------ город: улица, гаражи, рынок, тополя
def garage_row(b, col, x0, y, n, face):
    """Ряд гаражей 3,2 × 6 × 2,6 м, ворота в сторону face (±1 по Y)."""
    gw, gd, gh = 3.2, 6.0, 2.6
    L = n * gw
    ya, yb = y - gd / 2, y + gd / 2
    b.box((x0, ya, 0), (x0 + L, yb, gh), {'+X': M["gwall"], '-X': M["gwall"], ('-Y' if face > 0 else '+Y'): M["gwall"]}, scale=(2, 2))
    col.box((x0, ya, 0), (x0 + L, yb, gh + 0.3), fx(M["plinth"], ALL))
    yf = yb if face > 0 else ya
    k = '+Y' if face > 0 else '-Y'
    for i in range(n):
        x = x0 + i * gw
        b.box((x, yf - 0.01, 0), (x + 0.3, yf + 0.01, gh), {k: M["gwall"]}, scale=(2, 2))
        b.box((x + gw - 0.3, yf - 0.01, 0), (x + gw, yf + 0.01, gh), {k: M["gwall"]}, scale=(2, 2))
        b.box((x + 0.3, yf - 0.01, 2.2), (x + gw - 0.3, yf + 0.01, gh), {k: M["gwall"]}, scale=(2, 2))
        v = rnd.randint(0, 3)
        b.box((x + 0.3, yf + face * 0.02, 0), (x + gw - 0.3, yf + face * 0.03, 2.2), {k: (M["gdoor"], (v / 4, 0, (v + 1) / 4, 1))})
    b.box((x0 - 0.2, ya - 0.3, gh), (x0 + L + 0.2, yb + 0.3, gh + 0.15), fx(M["roof"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(3, 3))
    b.box((x0 - 0.1, ya - 0.2, gh + 0.15), (x0 + L + 0.1, yb + 0.2, gh + 0.32), fx(M["snow"], OPEN), scale=(4, 4))


def kiosk(b, col, x, y):
    """Ларёк у улицы, витрина светится (к улице, −Y… +Y)."""
    w, d, h = 3.0, 2.0, 2.6
    b.box((x - w / 2, y - d / 2, 0), (x + w / 2, y + d / 2, h), {'+Y': (M["kiosk"], (0, 0, 1, 1))})
    side = (M["kiosk"], (0, 0.02, 1, 0.3))
    b.box((x - w / 2, y - d / 2, 0), (x + w / 2, y + d / 2, h), {'+X': side, '-X': side, '-Y': side})
    b.box((x - w / 2 - 0.25, y - d / 2 - 0.1, h), (x + w / 2 + 0.25, y + d / 2 + 0.4, h + 0.12), fx(M["metal"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(1, 1))
    b.box((x - w / 2 - 0.2, y - d / 2 - 0.05, h + 0.12), (x + w / 2 + 0.2, y + d / 2 + 0.35, h + 0.28), fx(M["snow"], OPEN), scale=(3, 3))
    col.box((x - w / 2, y - d / 2, 0), (x + w / 2, y + d / 2, h), fx(M["plinth"], ALL))


def city(coll):
    b, col, veg = B(), B(), B()
    # гаражи к северо-востоку от городской лестницы (спутник; на фото 10000, 10013 — заснеженные крыши)
    for y, face in ((-63.0, -1), (-75.0, 1), (-81.5, -1)):
        x = 14.0
        while x < 104.0:
            n = min(9, int((104.0 - x) / 3.2))
            garage_row(b, col, x, y, n, face)
            x += n * 3.2 + 4.0
    # рынок «Сільський»: одноэтажный ангар с низкой крышей южнее улицы
    mx0, mx1, my0, my1, mh = -62.0, -26.0, -150.0, -104.0, 6.0
    b.box((mx0, my0, 0), (mx1, my1, mh), fx(M["corr"], SIDES), scale=(4, 6))
    b.box((mx0 - 0.3, my0 - 0.3, mh), (mx1 + 0.3, my1 + 0.3, mh + 0.25), fx(M["roof"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(3, 3))
    b.box((mx0 - 0.2, my0 - 0.2, mh + 0.25), (mx1 + 0.2, my1 + 0.2, mh + 0.4), fx(M["snow"], OPEN), scale=(4, 4))
    for x in (-56.0, -44.0, -32.0):                        # ворота и витрины к улице
        b.box((x - 2.0, my1 + 0.01, 0), (x + 2.0, my1 + 0.03, 3.2), fx(M["gdoor"], ('+Y',)), scale=(4, 3.2))
    b.box((-50.0, my1 + 0.01, 3.6), (-38.0, my1 + 0.03, 4.8), {'+Y': (M["kiosk"], (0, 0.7, 1, 1))})
    col.box((mx0, my0, 0), (mx1, my1, mh), fx(M["plinth"], ALL))
    # ларьки и фонари вдоль улицы
    for x in (-18.0, -10.0, 14.0):
        kiosk(b, col, x, STREET[0] - 2.5)
    for x in (-24.0, 20.0, 64.0):
        street_lamp(b, col, x, STREET[1] + 0.8, (0, -1))
    # частный сектор к северо-востоку (за гаражами) — двускатные дома
    for i in range(10):
        x = 130.0 + i * 24.0 + rnd.uniform(-4, 4)
        for y in (-70.0, -120.0):
            gable(b, x, y + rnd.uniform(-5, 5), rnd.choice((0.0, math.pi / 2)), rnd.uniform(7, 9), rnd.uniform(8, 10),
                  3.0, 2.4, M["house"], wall_uv=house_uv(rnd.randint(0, 3)), lit=0.2)
    # тополя рядами (10013, 10008) и деревья
    for x in range(8, 104, 9):
        h = rnd.uniform(18, 24)
        crossed(veg, x + rnd.uniform(-1, 1), -88.5 + rnd.uniform(-0.5, 0.5), 0, h * 0.2, h, M["poplar"], rnd.uniform(0, 3))
    for x, y in ((-80.0, -70.0), (-70.0, -64.0), (-95.0, -80.0), (-40.0, -78.0), (-52.0, -66.0), (-15.0, -62.0),
                 (-88.0, -60.0), (-30.0, -84.0), (110.0, -100.0), (-75.0, -112.0)):
        h = rnd.uniform(7, 11)
        crossed(veg, x, y, 0, h, h, M["tree"], rnd.uniform(0, 3))
    for i in range(30):                                    # тополя за рынком и у домов — фон
        x, y = rnd.uniform(-220, 220), rnd.uniform(-240, -130)
        h = rnd.uniform(18, 25)
        crossed(veg, x, y, 0, h * 0.2, h, M["poplar"], rnd.uniform(0, 3))
    return build(b, "EbCity", coll), build(veg, "EbCityTrees_nocol", coll), build(col, "EbCityCol-colonly", coll)


# ------------------------------------------------------------------ поле, пруд, ЛЭП, село
def house_uv(k):
    """Клетка атласа eb_house: столбец k (цвет), строка — окно тёмное или горит."""
    def f(lit):
        u0, u1 = k / 4 + 0.004, (k + 1) / 4 - 0.004
        return (u0, 0.004, u1, 0.496) if lit else (u0, 0.504, u1, 0.996)
    return f


def strip(b, pts, w, m, z=0.03):
    """Дорога-лента по ломаной pts шириной w (u — поперёк, тайл 4 м; v — вдоль, 8 м)."""
    v = 0.0
    for (ax, ay), (bx_, by) in zip(pts, pts[1:]):
        dx, dy = bx_ - ax, by - ay
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * w / 2, dx / L * w / 2
        quad(b, [(ax - nx, ay - ny, z), (ax + nx, ay + ny, z), (bx_ + nx, by + ny, z), (bx_ - nx, by - ny, z)], m, (0, 0, 1),
             uvs=[(0, v / 8), (w / 4, v / 8), (w / 4, (v + L) / 8), (0, (v + L) / 8)])
        v += L


def pylon(b, col, x, y, along, h=30.0):
    """Опора ЛЭП 110 кВ (10033, 10025): решётчатая пирамида 5 → 1,2 м, три траверсы, тросостойка."""
    w0, w1 = 2.5, 0.6
    cs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for (ax, ay), (bx_, by) in zip(cs, cs[1:] + cs[:1]):
        b.poly([(x + ax * w0, y + ay * w0, 0), (x + bx_ * w0, y + by * w0, 0), (x + bx_ * w1, y + by * w1, h), (x + ax * w1, y + ay * w1, h)],
               [(0, 0), (0, 1), (h / 2, 1), (h / 2, 0)], M["lattice"])
    for ax, ay in cs:
        col.box((x + ax * w0 - 0.2, y + ay * w0 - 0.2, 0), (x + ax * w0 + 0.2, y + ay * w0 + 0.2, 4.0), fx(M["plinth"], ALL))
    tips = []
    axis = 'X' if abs(along[1]) > 0.5 else 'Y'             # траверсы поперёк линии
    for z, half in ((h - 12, 4.5), (h - 7, 4.0), (h - 2, 3.5)):
        if axis == 'X':
            lattice_box(b, y, x - half, x + half, z - 0.8, z, 0.9, axis='X')
            tips += [(x - half, y, z - 0.8), (x + half, y, z - 0.8)]
        else:
            lattice_box(b, x, y - half, y + half, z - 0.8, z, 0.9)
            tips += [(x, y - half, z - 0.8), (x, y + half, z - 0.8)]
    bar(b, (x, y, h), (x, y, h + 2.5), 0.25, M["metal"])
    tips.append((x, y, h + 2.5))
    return tips


def power_line(b, wires, col, towers, along):
    prev = None
    for x, y in towers:
        tips = pylon(b, col, x, y, along)
        if prev:
            for p0, p1 in zip(prev, tips):
                ins = 1.6 if p0 != prev[-1] else 0.0
                cable(wires, (p0[0], p0[1], p0[2] - ins), (p1[0], p1[1], p1[2] - ins), sag=4.0, n=6)
        prev = tips
    for p0 in prev[:-1]:                                   # гирлянды изоляторов
        pass


def village(b, veg, x0, y0, ang, streets, n_per_side, lit_p=0.2, plot_w=22.0, depth=45.0):
    """Село: улицы вдоль направления ang, через 2·depth+6 м; по обе стороны — участки plot_w с домом,
    забором из профлиста к улице, деревьями в саду."""
    c, s = math.cos(ang), math.sin(ang)
    P = lambda u, v: (x0 + u * c - v * s, y0 + u * s + v * c)
    for si in range(streets):
        v_st = si * (2 * depth + 6.0)
        for side in (-1, 1):
            for i in range(n_per_side):
                if rnd.random() < 0.12:
                    continue
                u = i * plot_w + rnd.uniform(-2, 2)
                vf = v_st + side * 4.0                      # линия забора у улицы
                hx, hy = P(u + plot_w / 2, v_st + side * (4.0 + 5.0 + 4.5))
                along = rnd.random() < 0.5
                k = rnd.randint(0, 3)
                gable(b, hx, hy, ang + (0 if along else math.pi / 2), rnd.uniform(7.5, 9.5), rnd.uniform(8.5, 11.0),
                      rnd.uniform(2.8, 3.2), rnd.uniform(2.3, 2.8), M["house"], wall_uv=house_uv(k), lit=lit_p)
                # забор к улице: профлист 1,9 м с калиткой
                r = rnd.randint(0, 2)
                v0, v1 = 1 - (r + 1) / 3 + 0.01, 1 - r / 3 - 0.01
                for ua, ub in ((u + 0.5, u + plot_w * 0.6), (u + plot_w * 0.6 + 1.2, u + plot_w - 0.5)):
                    a, e = P(ua, vf), P(ub, vf)
                    L = math.hypot(e[0] - a[0], e[1] - a[1])
                    b.poly([(a[0], a[1], 0), (e[0], e[1], 0), (e[0], e[1], 1.9), (a[0], a[1], 1.9)],
                           [(0, v0), (L / 4, v0), (L / 4, v1), (0, v1)], M["corr"])
                # сад: 1–3 голых дерева
                for t in range(rnd.randint(1, 3)):
                    tx, ty = P(u + rnd.uniform(3, plot_w - 3), v_st + side * rnd.uniform(22, depth - 3))
                    h = rnd.uniform(5, 9)
                    crossed(veg, tx, ty, 0, h, h, M["tree"], rnd.uniform(0, 3))
        # столбы с фонарями вдоль улицы (головка светится, свет — только у ближних)
        for i in range(0, n_per_side * int(plot_w), 45):
            px, py = P(i, v_st - 3.5)
            b.cyl((px, py, 0), (px, py, 8.0), 0.13, 0.08, M["pole"], segs=6, su=2)
            hx, hy = P(i, v_st - 2.0)
            b.box((hx - 0.25, hy - 0.25, 7.8), (hx + 0.25, hy + 0.25, 8.0), fx(M["metal"], OPEN), scale=(1, 1))
            if rnd.random() < 0.5:
                b.box((hx - 0.2, hy - 0.2, 7.74), (hx + 0.2, hy + 0.2, 7.8), fx(M["lamp_o"], ('-Z',)), scale=(1, 1))


def field(coll):
    b, veg, col, wires = B(), B(), B(), B()
    # грунтовки: вдоль парка, ответвление в село мимо пруда, тропа от спуска с моста
    strip(b, [(-350, 115.5), (-97, 115.5), (300, 115.5)], 3.5, M["road"])
    strip(b, [(-97, 117.3), (-82, 250), (-60, 395), (-30, 470)], 3.5, M["road"])
    strip(b, [(-56, 94), (-70, 104), (-80, 113.8)], 1.6, M["road"], z=0.035)
    strip(b, [(-8, 117.3), (20, 200), (55, 300), (70, 390)], 1.4, M["road"], z=0.035)
    # пруд: замёрзший, в кольце камыша
    cx, cy, ra, rb, ang = 0.0, 410.0, 60.0, 27.5, math.radians(-52)
    ring = []
    for i in range(14):
        a = 2 * math.pi * i / 14
        r = 1 + 0.12 * math.sin(a * 3 + 1)
        lx, ly = ra * r * math.cos(a), rb * r * math.sin(a)
        ring.append((cx + lx * math.cos(ang) - ly * math.sin(ang), cy + lx * math.sin(ang) + ly * math.cos(ang)))
    b.poly([(x, y, 0.03) for x, y in ring], [(x / 6, y / 6) for x, y in ring], M["ice"])
    for i, (x, y) in enumerate(ring):
        nx, ny = ring[(i + 1) % len(ring)]
        for t in range(6):
            px, py = x + (nx - x) * t / 6 + rnd.uniform(-2, 2), y + (ny - y) * t / 6 + rnd.uniform(-2, 2)
            crossed(veg, px, py, 0, rnd.uniform(2.0, 3.0), rnd.uniform(1.6, 2.4), M["grass"], rnd.uniform(0, 3))
    # лесополоса по балке: от пруда на северо-восток
    belt = [(0, 395), (200, 295), (365, 215), (520, 160)]
    for (ax, ay), (bx_, by) in zip(belt, belt[1:]):
        L = math.hypot(bx_ - ax, by - ay)
        for i in range(int(L / 6)):
            t = i / (L / 6)
            o = rnd.uniform(-22, 22)
            nx, ny = -(by - ay) / L, (bx_ - ax) / L
            x, y = ax + (bx_ - ax) * t + nx * o, ay + (by - ay) * t + ny * o
            h = rnd.uniform(7, 12)
            crossed(veg, x, y, 0, h, h, M["tree"], rnd.uniform(0, 3))
    # кусты вдоль грунтовки у парка и край поля
    for i in range(46):
        x = rnd.uniform(-300, 280)
        y = 112.0 + rnd.choice((-1, 1)) * rnd.uniform(3, 9)
        h = rnd.uniform(2.5, 5.5)
        crossed(veg, x, y, 0, h * 1.1, h, M["tree"], rnd.uniform(0, 3))
    # сухая трава и бурьян из-под снега: густо у моста, реже дальше
    for i in range(1800):
        x, y = rnd.uniform(-115, 115), rnd.uniform(92, Y_FIELD + 10)
        if abs(y - 115.5) < 2.2:
            continue
        s = rnd.uniform(0.8, 1.6)
        crossed(veg, x, y, 0, s, s * rnd.uniform(0.6, 0.9), M["grass"], rnd.uniform(0, 3))
    for i in range(1400):
        x, y = rnd.uniform(-450, 450), rnd.uniform(Y_FIELD, 620)
        s = rnd.uniform(1.0, 2.2)
        crossed(veg, x, y, 0, s, s * 0.8, M["grass"], rnd.uniform(0, 3))
    for i in range(250):                                   # полоса у вокзала и вдоль путей
        x, y = rnd.uniform(-110, 110), rnd.uniform(18, 50)
        if 34 < x < 66 and 15 < y < 38:
            continue
        s = rnd.uniform(0.7, 1.3)
        crossed(veg, x, y, 0, s, s * 0.7, M["grass"], rnd.uniform(0, 3))
    for x, y in ((20.0, 44.0), (28.0, 40.0), (66.0, 45.0), (75.0, 30.0), (84.0, 46.0), (-20.0, 40.0), (-35.0, 46.0),
                 (-48.0, 38.0), (-62.0, 44.0), (90.0, 22.0)):
        h = rnd.uniform(7, 12)
        crossed(veg, x, y, 0, h, h, M["tree"], rnd.uniform(0, 3))
    for i in range(44):                                    # полоса больших деревьев за платформой у вокзала
        x = rnd.uniform(-105.0, 110.0)
        if 28.0 < x < 66.0:
            continue
        y = rnd.uniform(24.5, 32.0) if -27.0 < x < 27.0 else rnd.uniform(19.0, 30.0)   # у моста — за лестницей
        h = rnd.uniform(9, 15)
        crossed(veg, x, y, 0, h * 1.1, h, M["tree"], rnd.uniform(0, 3))
    # край играбельного поля — снежный вал с кустами
    for i in range(60):
        x = -110 + i * 3.7
        crossed(veg, x + rnd.uniform(-1, 1), Y_FIELD + rnd.uniform(0, 2), 0, 3.0, rnd.uniform(1.5, 3.0), M["tree"], rnd.uniform(0, 3))
    quad(b, [(-XMAX, Y_FIELD - 3, 0.0), (XMAX, Y_FIELD - 3, 0.0), (XMAX, Y_FIELD + 1, 1.1), (-XMAX, Y_FIELD + 1, 1.1)], M["snow"], (0, -1, 1), (6, 6))
    quad(b, [(-XMAX, Y_FIELD + 1, 1.1), (XMAX, Y_FIELD + 1, 1.1), (XMAX, Y_FIELD + 5, 0.0), (-XMAX, Y_FIELD + 5, 0.0)], M["snow"], (0, 1, 1), (6, 6))
    # ЛЭП: одна поперёк путей через поле, другая вдоль, дальше
    power_line(b, wires, col, [(75.0, 150.0), (75.0, 275.0), (75.0, 400.0), (75.0, 525.0), (75.0, 650.0)], (0, 1))
    power_line(b, wires, col, [(-350.0, 345.0), (-120.0, 345.0), (180.0, 345.0), (430.0, 345.0)], (1, 0))
    # сёла: юго-западное (Корсунці) — сразу за краем поля, улицы почти вдоль путей; северное (Польова) — за прудом
    village(b, veg, -112.0, 238.0, math.radians(169), 4, 14, lit_p=0.35)
    village(b, veg, -150.0, 470.0, math.radians(-52), 3, 11, lit_p=0.3)
    village(b, veg, 120.0, 520.0, math.radians(-52), 2, 9, lit_p=0.18)
    # ближние к полю фонари села — настоящие (свет)
    for x, y in ((-114.0, 236.0), (-114.0, 340.0)):
        street_lamp(b, col, x, y, (1, 0), kind="village", h=8.0)
    return (build(b, "EbField", coll), build(veg, "EbFieldPlants_nocol", coll), build(wires, "EbPowerWires_nocol", coll),
            build(col, "EbFieldCol-colonly", coll))


# ------------------------------------------------------------------ фон: панельки в городе, огни сёл
def backdrop(coll):
    """Дома за краем (шейдер окон shaders/backdrop_house.gdshader, как у района): UV — метры, UV2 — (номер+оттенок, доля окон)."""
    me = {"v": [], "f": [], "uv": [], "uv2": [], "mi": []}

    def poly(pts, uvs, uv2, mi=0):
        i0 = len(me["v"])
        me["v"] += pts
        me["f"].append(list(range(i0, i0 + len(pts))))
        me["uv"] += uvs
        me["uv2"] += [uv2] * len(pts)
        me["mi"].append(mi)

    def house(k, cx, cy, w, d, h, lit):
        uv2 = (k + 0.15 + (k * 0.37) % 0.7, lit)
        x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
        u = 0.0
        ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for i in range(4):
            (ax, ay), (bx_, by) = ring[i], ring[(i + 1) % 4]
            ln = math.hypot(bx_ - ax, by - ay)
            poly([(ax, ay, 0), (bx_, by, 0), (bx_, by, h), (ax, ay, h)], [(u, 0), (u + ln, 0), (u + ln, h), (u, h)], uv2)
            u += ln + 7.0
        poly([(x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h)], [(0, 0)] * 4, (uv2[0], -1.0))

    def glow(x, y, z, s, kind=0.0):
        """Дальний огонь: квадрат лицом к мосту."""
        ang = math.atan2(-y, -x)
        tx, ty = -math.sin(ang) * s, math.cos(ang) * s
        poly([(x - tx, y - ty, z - s), (x + tx, y + ty, z - s), (x + tx, y + ty, z + s), (x - tx, y - ty, z + s)],
             [(0, 0), (1, 0), (1, 1), (0, 1)], (kind, 0.0), 1)

    k = 0
    # девятиэтажка с «Копійкой» — длинная, прямо по ходу с моста (10000)
    house(k, 29.0, -157.0, 120.0, 13.0, 27.5, 0.38); k += 1
    # пояс девяти- и двенадцатиэтажек
    for x, y, w, h in ((-150, -215, 60, 27.5), (125, -230, 60, 27.5), (-60, -290, 72, 33.0), (230, -320, 60, 27.5),
                       (-260, -260, 54, 27.5), (40, -380, 84, 33.0), (-200, -380, 60, 27.5), (300, -200, 54, 27.5)):
        house(k, x, y, w, 13.0, h, 0.35); k += 1
    # шестнадцатиэтажки-свечки (10013, 10008)
    for x, y in ((-120, -330), (60, -350), (200, -420), (-30, -430), (330, -380)):
        house(k, x, y, 24.0, 18.0, 48.0, 0.3); k += 1
    # огни: город — натрий над крышами, сёла — тёплые окошки и редкие белые фонари
    for i in range(16):
        glow(-260 + i * 34, -175 - (i % 3) * 40, 8 + (i % 4) * 3, 0.8, 0.0)
    for i in range(46):
        x, y = rnd.uniform(-560, 260), rnd.uniform(240, 700)
        glow(x, y, rnd.uniform(1.5, 6.5), rnd.uniform(0.3, 0.5), 0.0 if rnd.random() < 0.85 else 1.0)

    m = bpy.data.meshes.new("EbBackdrop_nocol")
    m.from_pydata(me["v"], [], me["f"])
    l1 = m.uv_layers.new(name="UVMap")
    l2 = m.uv_layers.new(name="UV2")
    for i in range(len(me["uv"])):
        l1.data[i].uv = me["uv"][i]
        l2.data[i].uv = me["uv2"][i]
    m.materials.append(M["house_bd"])
    m.materials.append(M["glow"])
    for p, mi in zip(m.polygons, me["mi"]):
        p.material_index = mi
    m.update()
    ob = bpy.data.objects.new("EbBackdrop_nocol", m)
    coll.objects.link(ob)
    return ob


# ------------------------------------------------------------------ сборка и экспорт
PARTS = [
    ("eb_ground", lambda c: [ground(c), *tracks(c), *platforms(c), *bounds(c)]),
    ("eb_bridge", lambda c: list(bridge(c))),
    ("eb_catenary", lambda c: list(catenary(c))),
    ("eb_trains", lambda c: list(trains(c))),
    ("eb_props", lambda c: list(props(c))),
    ("eb_city", lambda c: list(city(c))),
    ("eb_field", lambda c: list(field(c))),
    ("eb_backdrop", lambda c: [backdrop(c)]),
]


def main(export=True):
    LIGHTS.clear()
    rnd.seed(2024)
    materials()
    sc = bpy.data.scenes.get("EastBridge") or bpy.data.scenes.new("EastBridge")
    if bpy.context.window:
        bpy.context.window.scene = sc
    for ch in list(sc.collection.children):
        for ob in list(ch.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(ch)
    for ob in list(sc.collection.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    os.makedirs(OUT, exist_ok=True)
    stats = {}
    groups = []
    for name, fn in PARTS:
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
        obs = fn(c)
        stats[name] = sum(len(o.data.polygons) for o in obs if "colonly" not in o.name)
        groups.append((name, obs))
    for o in sc.objects:                                   # коллизию в окне Blender — каркасом, чтобы не закрывала модели
        if "colonly" in o.name:
            o.display_type = 'WIRE'
            o.hide_render = True
    if export:
        vl = sc.view_layers[0]
        for other in bpy.data.scenes:                      # в других сценах ничего не должно быть выделено
            for layer in other.view_layers:
                for o in other.objects:
                    o.select_set(False, view_layer=layer)
        for name, obs in groups:
            for o in sc.objects:
                o.select_set(False, view_layer=vl)
            for o in obs:
                o.select_set(True, view_layer=vl)
            vl.objects.active = obs[0]
            bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".gltf"), use_selection=True, export_keep_originals=True,
                                      export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
        with open(os.path.join(OUT, "lights.json"), "w", encoding="utf-8") as f:
            json.dump(LIGHTS, f, ensure_ascii=False, indent=1)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "east_bridge.blend"))
    return {"polys": stats, "total": sum(stats.values()), "lights": len(LIGHTS)}


result = main(export=globals().get("EB_EXPORT", True))
print(result)
