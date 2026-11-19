# Локация «Восточный ж/д мост» (YUR-7): пешеходный мост над путями станции Одесса-Восточная, зима.
# Референсы — фото из задачи YUR-7 (мост с белыми перилами и сеткой над проводами, лестницы на островные
# платформы с будками, решётчатые ригели контактной сети, товарные составы, панельки на горизонте;
# ночью — зелёные ртутные и оранжевые натриевые фонари).
#
# Запуск в открытом Blender (через Blender MCP):
#   EB_ROOT = r"<папка проекта>"; exec(open(EB_ROOT + r"\tools\blender\build_east_bridge.py", encoding="utf-8").read())
# Текстуры (один раз или после правок) — tools/blender/east_bridge_textures.py.
#
# Выход — assets/models/east_bridge/*.gltf, по одному на часть локации, и lights.json (фонари для Godot),
# сцена Blender «EastBridge», файл tools/blender/east_bridge.blend.
#
# Оси Blender: Z — вверх, X — вдоль путей (восток), Y — поперёк путей (север). В Godot: (x, z, -y).
# Ноль — уровень земли и головки шпал; мост — вдоль Y на X = 0.
# Имена объектов:
#   «…_nocol»    — без коллизии (перила, провода, рельсы, ступени: по лестницам ходят по невидимым пандусам);
#   «…-colonly»  — только коллизия, без меша (суффикс Godot): пандусы под ступенями, стенки вдоль перил, вагоны.
import bpy
import json
import math
import os
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

# ------------------------------------------------------------------ план станции
TRACKS = [-44.0, -39.0, -34.0, -29.5, -18.5, -13.5, -8.5, -3.5, 7.5, 12.5, 17.5, 22.5]   # оси путей по Y
PLATFORMS = [(-27.75, -20.25), (-1.75, 5.75)]        # островные платформы (Y от, до)
PLAT_X = 70.0                                         # платформы X −70…70, дальше пандусы к путям
PLAT_H = 1.0
YARD = (-49.0, 28.0)                                  # щебёночное поле путей по Y
GROUND = (-80.0, 62.0)                                # играбельная земля по Y (за ней — заборы)
XMAX = 100.0                                          # играбельная зона по X
FAR = 170.0                                           # пути и провода тянутся до горизонта
DECK = 7.4                                            # верх настила моста
DECK_T = 0.6
BR_W = 3.0                                            # ширина моста
BR_Y = (-56.0, 34.0)                                  # мост по Y; дальше лестницы на землю
BENTS = [-50.0, -36.5, -24.0, -11.0, 2.0, 15.0, 27.0]  # опоры моста (пары колонн)
WIRE_C, WIRE_M = 5.8, 6.5                             # контактный провод и несущий трос
GANTRY_X = [-140.0, -105.0, -70.0, -35.0, 35.0, 70.0, 105.0, 140.0]
GANTRY_Y = (-48.0, 27.0)
RISE, RUN = 0.168, 0.30                               # ступень

LIGHTS = []                                           # фонари для Godot: голова плафона + основание + цвет


def gd(p):
    """Blender (x, y, z) → Godot (x, y, z)."""
    return [round(p[0], 3), round(p[2], 3), round(-p[1], 3)]


def lamp(kind, color, base, head, energy=None):
    LIGHTS.append({"kind": kind, "color": color, "base": gd(base), "head": gd(head), "energy": energy})


# ------------------------------------------------------------------ материалы
def amat(name, tex):
    """Материал с вырезом по альфе (решётки, сетка) — двусторонний."""
    m = mat(name, tex, rough=0.8)
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


def flat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = rgba
    m.diffuse_color = rgba
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
        "house": flat("BackdropHouse", (0.05, 0.055, 0.07, 1)),
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


def bar(b, p0, p1, w, m, keys=SIDES, s=(1.0, 1.0)):
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
    mid = (p0 + p1) / 2
    for i in range(4):
        j = (i + 1) % 4
        b.poly([c[i], c[j], e[j], e[i]], [(0, 0), (w / s[0], 0), (w / s[0], L / s[1]), (0, L / s[1])], m)
    # торцы не нужны: бруски упираются в другие детали
    return mid


def build(b, name, coll):
    return b.build(name, coll)


# ------------------------------------------------------------------ земля, пути, платформы
def ground(coll):
    b = B()
    y0, y1 = YARD
    quad(b, [(-FAR, y0, 0), (FAR, y0, 0), (FAR, y1, 0), (-FAR, y1, 0)], M["ballast"], (0, 0, 1), (4, 4))
    for ya, yb in ((GROUND[0] - 40, y0), (y1, GROUND[1] + 40)):
        quad(b, [(-FAR, ya, 0), (FAR, ya, 0), (FAR, yb, 0), (-FAR, yb, 0)], M["snow"], (0, 0, 1), (6, 6))
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


def platforms(coll):
    b = B()
    for ya, yb in PLATFORMS:
        b.box((-PLAT_X, ya, 0), (PLAT_X, yb, PLAT_H), {'+Z': M["platform"]}, scale=(4, 4))
        b.box((-PLAT_X, ya, 0), (PLAT_X, yb, PLAT_H), {'+Y': M["pedge"], '-Y': M["pedge"]}, scale=(4, 1))
        for sx in (-1, 1):                                    # пандусы с торцов к путям
            x0, x1 = sx * PLAT_X, sx * (PLAT_X + 7.0)
            quad(b, [(x0, ya, PLAT_H), (x1, ya, 0.05), (x1, yb, 0.05), (x0, yb, PLAT_H)], M["platform"], (sx * 0.15, 0, 1), (4, 4))
            for ys, out in ((ya, -1), (yb, 1)):
                quad(b, [(x0, ys, 0), (x1, ys, 0), (x1, ys, 0.05), (x0, ys, PLAT_H)], M["pedge"], (0, out, 0), (4, 1))
        # белая полоса безопасности вдоль края — тонкая плашка
        for ys in (ya + 0.3, yb - 0.6):
            b.box((-PLAT_X, ys, PLAT_H), (PLAT_X, ys + 0.3, PLAT_H + 0.01), {'+Z': (M["white"], (0, 0, 40, 0.3))})
    return build(b, "EbPlatforms", coll)


def fences(coll):
    """Бетонные заборы по краям (юг, север) и невидимые стенки по X — дальше не пройти."""
    b = B()
    for y in (GROUND[0], GROUND[1]):
        for x0 in range(int(-XMAX), int(XMAX), 4):
            b.box((x0, y - 0.08, 0), (x0 + 4, y + 0.08, 2.4), fx(M["fence"], ('+Y', '-Y')), scale=(4, 2.4))
            b.box((x0, y - 0.1, 2.4), (x0 + 4, y + 0.1, 2.48), fx(M["snow"], ('+Y', '-Y', '+Z')), scale=(3, 3))
        for x0 in range(int(-XMAX), int(XMAX) + 1, 4):
            b.box((x0 - 0.12, y - 0.14, 0), (x0 + 0.12, y + 0.14, 2.6), fx(M["fence"], OPEN), scale=(1, 2.6))
    f = build(b, "EbFences", coll)
    w = B()
    for x in (-XMAX, XMAX):
        w.box((x - 0.5, GROUND[0], -1), (x + 0.5, GROUND[1], 12), fx(M["plinth"], ALL))
    return f, build(w, "EbBounds-colonly", coll)


# ------------------------------------------------------------------ мост
def railing(b, p0, p1, h=1.1, posts=2.0):
    """Перила по прямой p0→p1 (по низу). Стойки, три пояса, частые прутья; всё — белая краска."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    n = max(1, round(L / posts))
    up = Vector((0, 0, 1))
    for i in range(n + 1):
        q = p0 + d * (i / n)
        bar(b, q, q + up * h, 0.07, M["white"])
    for z in (0.1, h * 0.5, h - 0.04):
        bar(b, p0 + up * z, p1 + up * z, 0.05, M["white"], s=(1, 1))
    k = max(1, int(L / 0.22))
    for i in range(1, k):
        q = p0 + d * (i / k)
        bar(b, q + up * 0.1, q + up * (h - 0.04), 0.022, M["white"])


def mesh_panel(b, p0, p1, z0, h):
    """Сетка-рабица над проводами: полотно (двустороннее) и рамка."""
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    a, c = p0 + Vector((0, 0, z0)), p1 + Vector((0, 0, z0))
    b.poly([a, c, c + Vector((0, 0, h)), a + Vector((0, 0, h))], [(0, 0), (L, 0), (L, h), (0, h)], M["mesh"])
    for q in (a, c):
        bar(b, q, q + Vector((0, 0, h)), 0.06, M["white"])
    bar(b, a + Vector((0, 0, h)), c + Vector((0, 0, h)), 0.05, M["white"])


def lamp_post(b, x, y, side, z0):
    """Изогнутый фонарный столб на мосту (как на фото): труба от перил вверх, дуга над настилом, плафон."""
    s = -side                                             # дуга смотрит внутрь моста
    base = Vector((x, y, z0))
    top = base + Vector((0, 0, 4.4))
    bar(b, base, top, 0.11, M["white"])
    pts = [top]
    for i in range(1, 5):
        a = math.radians(90 * i / 4)
        pts.append(top + Vector((s * 0.7 * (1 - math.cos(a)), 0, 0.55 * math.sin(a))))
    for p, q in zip(pts, pts[1:]):
        bar(b, p, q, 0.08, M["white"])
    head = pts[-1] + Vector((s * 0.35, 0, -0.02))
    b.box((pts[-1].x + (0 if s > 0 else -0.6), y - 0.17, head.z - 0.12), (pts[-1].x + (0.6 if s > 0 else 0), y + 0.17, head.z + 0.06),
          fx(M["metal"], ('+X', '-X', '+Y', '-Y', '+Z')), scale=(1, 1))
    b.box((pts[-1].x + (0.05 if s > 0 else -0.55), y - 0.13, head.z - 0.2), (pts[-1].x + (0.55 if s > 0 else -0.05), y + 0.13, head.z - 0.12),
          fx(M["lamp_g"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(1, 1))
    lamp("bridge", "green", base, (head.x, head.y, head.z - 0.25))


def flight(b, col, x0, y0, z0, dx, dy, width, n, ramp_b):
    """Марш лестницы вниз из (x0, y0, z0) в направлении (dx, dy); width — ширина поперёк.
    Ступени и косоуры (без коллизии) + невидимый пандус. Возвращает (x, y, z) низа марша."""
    px, py = -dy, dx                                     # поперёк марша
    hw = width / 2
    for i in range(n):
        a, c = i * RUN, (i + 1) * RUN
        zt = z0 - (i + 1) * RISE
        pts = lambda s, t, z: (x0 + dx * s + px * t, y0 + dy * s + py * t, z)
        quad(b, [pts(a, -hw, zt), pts(c, -hw, zt), pts(c, hw, zt), pts(a, hw, zt)], M["deck"], (0, 0, 1), (3, 3))
        quad(b, [pts(a, -hw, zt), pts(a, hw, zt), pts(a, hw, zt + RISE), pts(a, -hw, zt + RISE)], M["plinth"], (dx, dy, 0), (3.6, 0.9))
    L = n * RUN
    H = n * RISE
    for t in (-hw - 0.15, hw + 0.15):                     # косоуры — бетонные балки по бокам
        p = lambda s, z: (x0 + dx * s + px * t, y0 + dy * s + py * t, z)
        out = (px * (1 if t > 0 else -1), py * (1 if t > 0 else -1), 0)
        quad(b, [p(0, z0 + 0.15), p(L, z0 - H + 0.15), p(L, z0 - H - 0.45), p(0, z0 - 0.45)], M["plinth"], out, (3.6, 0.9))
    p = lambda s, t, z: (x0 + dx * s + px * t, y0 + dy * s + py * t, z)
    quad(b, [p(0, -hw - 0.15, z0 - 0.45), p(L, -hw - 0.15, z0 - H - 0.45), p(L, hw + 0.15, z0 - H - 0.45), p(0, hw + 0.15, z0 - 0.45)],
         M["plinth"], (0, 0, -1), (3.6, 0.9))
    for t in (-hw - 0.1, hw + 0.1):                       # наклонные перила
        q0, q1 = Vector(p(0, t, z0)), Vector(p(L, t, z0 - H))
        nn = max(2, round(L / 1.6))
        for i in range(nn + 1):
            q = q0.lerp(q1, i / nn)
            bar(b, q, q + Vector((0, 0, 1.0)), 0.06, M["white"])
        for zz in (0.1, 0.5, 0.96):
            bar(b, q0 + Vector((0, 0, zz)), q1 + Vector((0, 0, zz)), 0.05, M["white"])
        k = int(L / 0.25)
        for i in range(1, k):
            q = q0.lerp(q1, i / k)
            bar(b, q + Vector((0, 0, 0.1)), q + Vector((0, 0, 0.96)), 0.022, M["white"])
    # пандус-коллизия: клин под ступенями, верх — линия носков ступеней
    zt0, zt1 = z0, z0 - H
    corners = [p(0, -hw, zt0), p(L, -hw, zt1), p(L, hw, zt1), p(0, hw, zt0)]
    low = [(c[0], c[1], c[2] - 0.3) for c in corners]
    quad(ramp_b, corners, M["plinth"], (0, 0, 1))
    quad(ramp_b, low, M["plinth"], (0, 0, -1))
    for t in (-hw - 0.05, hw + 0.05):                     # стенки вдоль перил (две стороны — коллизия с обеих)
        for o in (1, -1):
            quad(ramp_b, [p(0, t, zt0), p(L, t, zt1), p(L, t, zt1 + 1.2), p(0, t, zt0 + 1.2)], M["plinth"], (px * o, py * o, 0))
    return x0 + dx * L, y0 + dy * L, z0 - H


def landing(b, ramp_b, x0, y0, x1, y1, z, base=0.0, rails=()):
    """Площадка между маршами: плита, колонны вниз, перила по сторонам rails ((p0, p1), …)."""
    xa, xb, ya, yb = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    b.box((xa, ya, z - 0.35), (xb, yb, z), {'+Z': M["deck"]}, scale=(3, 3))
    b.box((xa, ya, z - 0.35), (xb, yb, z), fx(M["plinth"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(3.6, 0.9))
    ramp_b.box((xa, ya, z - 0.35), (xb, yb, z), fx(M["plinth"], ALL))
    for x in (xa + 0.3, xb - 0.3):
        for y in (ya + 0.3, yb - 0.3):
            b.box((x - 0.2, y - 0.2, base), (x + 0.2, y + 0.2, z - 0.35), fx(M["plinth"], SIDES), scale=(3.6, 0.9))
            ramp_b.box((x - 0.2, y - 0.2, base), (x + 0.2, y + 0.2, z - 0.35), fx(M["plinth"], ALL))
    for p0, p1 in rails:
        railing(b, (p0[0], p0[1], z), (p1[0], p1[1], z), h=1.0, posts=1.6)
        ramp_b.box((min(p0[0], p1[0]) - 0.05, min(p0[1], p1[1]) - 0.05, z), (max(p0[0], p1[0]) + 0.05, max(p0[1], p1[1]) + 0.05, z + 1.2),
                   fx(M["plinth"], ALL))


def bridge(coll):
    b, col = B(), B()
    hw = BR_W / 2
    y0, y1 = BR_Y
    zb = DECK - DECK_T
    # настил: верх — своя развёртка (u поперёк), низ и бока — бетон
    quad(b, [(-hw, y0, DECK), (hw, y0, DECK), (hw, y1, DECK), (-hw, y1, DECK)], M["deck"], (0, 0, 1),
         uvs=[(0, y0 / 3), (1, y0 / 3), (1, y1 / 3), (0, y1 / 3)])
    b.box((-hw - 0.15, y0, zb), (hw + 0.15, y1, DECK), fx(M["plinth"], ('+X', '-X', '-Z')), scale=(3.6, 0.9))
    b.box((-hw - 0.15, y0, DECK), (-hw, y1, DECK + 0.12), fx(M["plinth"], ('+X', '-X', '+Z')), scale=(3.6, 0.9))
    b.box((hw, y0, DECK), (hw + 0.15, y1, DECK + 0.12), fx(M["plinth"], ('+X', '-X', '+Z')), scale=(3.6, 0.9))
    col.box((-hw - 0.15, y0, zb), (hw + 0.15, y1, DECK), fx(M["plinth"], ALL))
    # опоры: пара колонн и ригель
    for yb in BENTS:
        on_pl = any(a < yb < c for a, c in PLATFORMS)
        z0 = PLAT_H if on_pl else 0.0
        for x in (-1.05, 1.05):
            b.box((x - 0.25, yb - 0.25, z0), (x + 0.25, yb + 0.25, zb), fx(M["plinth"], SIDES), scale=(3.6, 0.9))
            col.box((x - 0.25, yb - 0.25, z0), (x + 0.25, yb + 0.25, zb), fx(M["plinth"], ALL))
        b.box((-hw - 0.3, yb - 0.4, zb - 0.5), (hw + 0.3, yb + 0.4, zb), fx(M["plinth"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(3.6, 0.9))
        b.box((-hw - 0.3, yb - 0.4, zb), (hw + 0.3, yb + 0.4, zb + 0.05), fx(M["snow"], ('+Y', '-Y')), scale=(3, 3))
    # проёмы в перилах под лестницы на платформы: (сторона, центр по Y)
    gaps = {1: [], -1: []}
    stair_y = {1: (PLATFORMS[0][0] + PLATFORMS[0][1]) / 2, -1: (PLATFORMS[1][0] + PLATFORMS[1][1]) / 2}
    SW = 2.2
    for side, yc in stair_y.items():
        gaps[side].append((yc - SW / 2 - 0.1, yc + SW / 2 + 0.1))
    for side in (-1, 1):
        x = side * (hw + 0.05)
        segs = [y0]
        for a, c in gaps[side]:
            segs += [a, c]
        segs.append(y1)
        for a, c in zip(segs[0::2], segs[1::2]):
            railing(b, (x, a, DECK + 0.12), (x, c, DECK + 0.12))
            col.box((x - 0.06, a, DECK), (x + 0.06, c, DECK + 1.4), fx(M["plinth"], ALL))
        for yc in TRACKS:                                  # сетка над проводами — над каждым путём
            if not any(a - 2.2 < yc < c + 2.2 for a, c in gaps[side]):
                mesh_panel(b, (x, yc - 2.0, 0), (x, yc + 2.0, 0), DECK + 1.25, 1.9)
    # фонари: через 15 м, по очереди слева и справа
    for i, y in enumerate((-50.0, -35.0, -16.0, -3.0, 10.0, 22.0, 32.0)):
        side = 1 if i % 2 else -1
        lamp_post(b, side * (hw + 0.12), y, side, DECK + 0.12)
    # лестницы на платформы: с восточной стороны на первую, с западной — на вторую
    n1 = 19                                               # 19 × 0.168 ≈ 3,2 м на марш
    for side, yc in stair_y.items():
        x0 = side * hw
        xa, ya, za = flight(b, col, x0, yc, DECK, side, 0, SW, n1, col)
        xl = xa + side * 2.0
        e = SW / 2 + 0.15                                   # площадка в линию с маршами: перила только по бокам
        landing(b, col, xa, yc - e, xl, yc + e, za, base=PLAT_H, rails=[((xa, yc - e), (xl, yc - e)), ((xa, yc + e), (xl, yc + e))])
        xe, ye, ze = flight(b, col, xl, yc, za, side, 0, SW, round((za - PLAT_H) / RISE), col)
    # лестницы на землю с концов моста: прямо по оси моста, два марша и площадка
    n2 = 22
    for sgn, ye in ((-1, y0), (1, y1)):
        xa, ya, za = flight(b, col, 0, ye, DECK, 0, sgn, BR_W, n2, col)
        yl = ya + sgn * 2.0
        landing(b, col, -hw - 0.15, ya, hw + 0.15, yl, za, rails=[((-hw - 0.15, ya), (-hw - 0.15, yl)), ((hw + 0.15, ya), (hw + 0.15, yl))])
        flight(b, col, 0, yl, za, 0, sgn, BR_W, round(za / RISE), col)
    vis = build(b, "EbBridge_nocol", coll)
    return vis, build(col, "EbBridgeCol-colonly", coll)


# ------------------------------------------------------------------ контактная сеть, прожекторы, светофоры
def lattice_box(b, x, ya, yb, z0, z1, d):
    """Ригель: коробка из решётчатых граней вдоль Y (u — по 2 м)."""
    L = yb - ya
    h = z1 - z0
    for xs in (x - d / 2, x + d / 2):
        b.poly([(xs, ya, z0), (xs, yb, z0), (xs, yb, z1), (xs, ya, z1)], [(0, 0), (L / 2, 0), (L / 2, 1), (0, 1)], M["lattice"])
    for zs in (z0, z1):
        b.poly([(x - d / 2, ya, zs), (x - d / 2, yb, zs), (x + d / 2, yb, zs), (x + d / 2, ya, zs)], [(0, 0), (L / 2, 0), (L / 2, 1), (0, 1)], M["lattice"])
    b.box((x - d / 2, ya, z1), (x + d / 2, yb, z1 + 0.06), fx(M["snow"], ('+Z', '+X', '-X')), scale=(3, 3))


def lattice_mast(b, x, y, h, w=0.6):
    for (ax, ay), (bx_, by) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        p0 = (x + ax * w / 2, y + ay * w / 2)
        p1 = (x + bx_ * w / 2, y + by * w / 2)
        b.poly([(p0[0], p0[1], 0), (p1[0], p1[1], 0), (p1[0], p1[1], h), (p0[0], p0[1], h)], [(0, 0), (0, 1), (h / 2, 1), (h / 2, 0)], M["lattice"])
    b.box((x - w / 2 - 0.1, y - w / 2 - 0.1, 0), (x + w / 2 + 0.1, y + w / 2 + 0.1, 0.4), fx(M["plinth"], OPEN), scale=(3.6, 0.9))


def catenary(coll):
    b, wires, col = B(), B(), B()
    ya, yb = GANTRY_Y
    for x in GANTRY_X:
        for y in (ya, yb):
            lattice_mast(b, x, y, 10.6)
            col.box((x - 0.35, y - 0.35, 0), (x + 0.35, y + 0.35, 10.6), fx(M["plinth"], ALL))
        lattice_box(b, x, ya - 0.4, yb + 0.4, 9.4, 10.4, 0.7)
        for yc in TRACKS:                                  # подвесы к несущему тросу и изоляторы
            bar(wires, (x, yc, 9.4), (x, yc, WIRE_M), 0.035, M["metal"])
            bar(wires, (x, yc, WIRE_M + 0.6), (x, yc, WIRE_M + 0.2), 0.09, M["white"])
    for yc in TRACKS:                                      # провода: несущий трос и контактный, струны между ними
        for z in (WIRE_C, WIRE_M):
            wires.box((-FAR, yc - 0.015, z - 0.015), (FAR, yc + 0.015, z + 0.015), fx(M["metal"], ('+Y', '-Y', '-Z', '+Z')), scale=(8, 1))
        x = -FAR
        while x < FAR:
            wires.box((x - 0.01, yc - 0.01, WIRE_C), (x + 0.01, yc + 0.01, WIRE_M), fx(M["metal"], ('+X', '-Y')), scale=(1, 1))
            x += 8.75
    # прожекторные мачты (как на дневном фото): высокая труба, площадка, четыре прожектора
    for x, y in ((-30.0, -41.5), (46.0, 10.0)):
        bar(b, (x, y, 0), (x, y, 18.0), 0.45, M["metal"], s=(1, 3))
        b.box((x - 1.2, y - 1.2, 18.0), (x + 1.2, y + 1.2, 18.25), fx(M["metal"], ALL), scale=(1, 1))
        for i in range(4):
            a = i * math.pi / 2 + math.pi / 4
            hx, hy = x + math.cos(a) * 0.8, y + math.sin(a) * 0.8
            b.box((hx - 0.35, hy - 0.35, 18.3), (hx + 0.35, hy + 0.35, 18.9), fx(M["metal"], ('+X', '-X', '+Y', '-Y', '+Z')), scale=(1, 1))
            b.box((hx - 0.3, hy - 0.3, 18.2), (hx + 0.3, hy + 0.3, 18.3), fx(M["lamp_o"], ('-Z', '+X', '-X', '+Y', '-Y')), scale=(1, 1))
        col.box((x - 0.3, y - 0.3, 0), (x + 0.3, y + 0.3, 18), fx(M["plinth"], ALL))
        lamp("mast", "orange", (x, y, 0), (x, y, 18.0), energy=90.0)
    # светофоры в концах платформ: столбик, головка с двумя огнями (зелёный горит)
    for x, y in ((-74.0, -31.8), (74.0, -16.2), (-74.0, -5.8), (74.0, 9.8)):
        bar(b, (x, y, 0), (x, y, 4.2), 0.14, M["metal"])
        b.box((x - 0.18, y - 0.18, 4.2), (x + 0.18, y + 0.18, 5.2), fx(M["metal"], ALL), scale=(1, 1))
        fs = -1 if x > 0 else 1
        b.box((x + fs * 0.18, y - 0.1, 4.75), (x + fs * 0.2, y + 0.1, 4.95), fx(M["lamp_g"], ('+X', '-X')), scale=(1, 1))
        col.box((x - 0.2, y - 0.2, 0), (x + 0.2, y + 0.2, 5.2), fx(M["plinth"], ALL))
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


def gondola_car(b, col, x0, y):
    L = 13.9
    x1 = x0 + L
    bogies(b, x0, x1, y)
    za, zb_ = 1.2, 3.3
    b.box((x0, y - 1.55, za), (x1, y + 1.55, zb_), {'+Y': (M["gondola"], (1, 0, 0, 1)), '-Y': (M["gondola"], (0, 0, 1, 1))})
    b.box((x0, y - 1.55, za), (x1, y + 1.55, zb_), fx(M["metal"], ('+X', '-X', '-Z')), scale=(1.5, 1.5))
    b.box((x0, y - 1.55, zb_), (x1, y + 1.55, zb_ + 0.08), fx(M["metal"], ('+Y', '-Y', '+Z')), scale=(2, 1))
    # груз — щебень горкой, присыпан снегом
    hx = [(x0 + 0.2, zb_ - 0.2), (x0 + L * 0.3, zb_ + 0.55), (x0 + L * 0.7, zb_ + 0.6), (x1 - 0.2, zb_ - 0.2)]
    for (xa, za_), (xb, zb2) in zip(hx, hx[1:]):
        quad(b, [(xa, y - 1.45, zb_ - 0.1), (xb, y - 1.45, zb_ - 0.1), (xb, y, zb2), (xa, y, za_)], M["ballast"], (0, -0.3, 1), (4, 4))
        quad(b, [(xa, y + 1.45, zb_ - 0.1), (xb, y + 1.45, zb_ - 0.1), (xb, y, zb2), (xa, y, za_)], M["ballast"], (0, 0.3, 1), (4, 4))
    col.box((x0, y - 1.6, 0.2), (x1, y + 1.6, zb_ + 0.6), fx(M["plinth"], ALL))


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


def trains(coll):
    b, col = B(), B()
    x = -96.0                                              # цистерны — у южного края, до самого моста
    for i in range(7):
        tank_car(b, col, x, TRACKS[0], 0 if i % 3 != 1 else 1)
        x += 12.8
    x = 9.0                                                # полувагоны со щебнем — за мостом на восток
    for i in range(6):
        gondola_car(b, col, x, TRACKS[2])
        x += 14.6
    x = -95.0                                              # контейнеры — у северного края
    for i in range(6):
        container_car(b, col, x, TRACKS[-1], i % 4)
        x += 14.3
    x = 14.0                                               # пассажирский состав, стоит в отстое
    for i in range(3):
        coach_car(b, col, x, TRACKS[6])
        x += 25.3
    return build(b, "EbTrains_nocol", coll), build(col, "EbTrainsCol-colonly", coll)


# ------------------------------------------------------------------ платформенные мелочи, вокзал
def booth(b, col, x, y, w, d, h, m, door_side=-1):
    b.box((x - w / 2, y - d / 2, PLAT_H), (x + w / 2, y + d / 2, PLAT_H + h), fx(m, SIDES), scale=(2, 2))
    b.box((x - w / 2 - 0.2, y - d / 2 - 0.2, PLAT_H + h), (x + w / 2 + 0.2, y + d / 2 + 0.2, PLAT_H + h + 0.12), fx(M["metal"], ALL), scale=(1, 1))
    b.box((x - w / 2 - 0.2, y - d / 2 - 0.2, PLAT_H + h + 0.12), (x + w / 2 + 0.2, y + d / 2 + 0.2, PLAT_H + h + 0.3), fx(M["snow"], OPEN), scale=(3, 3))
    yd = y + door_side * (d / 2 + 0.01)
    b.box((x - 0.45, yd - 0.01, PLAT_H), (x + 0.45, yd + 0.01, PLAT_H + 2.0), fx(M["door"], ('+Y', '-Y')), scale=(0.9, 2.0))
    b.box((x + 0.7, yd - 0.01, PLAT_H + 1.0), (x + 1.3, yd + 0.01, PLAT_H + 1.6), fx(M["metal"], ('+Y', '-Y')), scale=(0.6, 0.6))
    col.box((x - w / 2, y - d / 2, PLAT_H), (x + w / 2, y + d / 2, PLAT_H + h), fx(M["plinth"], ALL))


def bench(b, col, x, y):
    for dx in (-0.8, 0.8):
        b.box((x + dx - 0.05, y - 0.2, PLAT_H), (x + dx + 0.05, y + 0.2, PLAT_H + 0.45), fx(M["metal"], SIDES), scale=(1, 1))
    b.box((x - 1.0, y - 0.22, PLAT_H + 0.45), (x + 1.0, y + 0.22, PLAT_H + 0.5), fx(M["wood"], ALL), scale=(1, 1))
    b.box((x - 1.0, y - 0.22, PLAT_H + 0.5), (x + 1.0, y + 0.22, PLAT_H + 0.56), fx(M["snow"], OPEN), scale=(3, 3))
    col.box((x - 1.0, y - 0.25, PLAT_H), (x + 1.0, y + 0.25, PLAT_H + 0.5), fx(M["plinth"], ALL))


def platform_lamp(b, x, y, color):
    """Фонарь платформы: бетонный столб и консоль с плафоном."""
    b.cyl((x, y, PLAT_H), (x, y, PLAT_H + 6.5), 0.14, 0.09, M["plinth"], segs=6, su=2)
    b.box((x - 0.04, y - 0.04, PLAT_H + 6.4), (x + 0.04, y + 1.2, PLAT_H + 6.48), fx(M["metal"], ALL), scale=(1, 1))
    m = M["lamp_g"] if color == "green" else M["lamp_o"]
    b.box((x - 0.22, y + 0.9, PLAT_H + 6.22), (x + 0.22, y + 1.35, PLAT_H + 6.42), fx(M["metal"], ('+X', '-X', '+Y', '-Y', '+Z')), scale=(1, 1))
    b.box((x - 0.18, y + 0.95, PLAT_H + 6.14), (x + 0.18, y + 1.3, PLAT_H + 6.22), fx(m, ('-Z', '+X', '-X', '+Y', '-Y')), scale=(1, 1))
    lamp("platform", color, (x, y, PLAT_H), (x, y + 1.12, PLAT_H + 6.1))


def props(coll):
    b, col = B(), B()
    (a1, b1), (a2, b2) = PLATFORMS
    c1, c2 = (a1 + b1) / 2, (a2 + b2) / 2
    booth(b, col, -16.0, c1, 3.0, 2.2, 2.5, M["booth"], door_side=1)
    booth(b, col, 22.0, c2, 2.6, 2.0, 2.4, M["white"], door_side=-1)
    booth(b, col, 46.0, c1, 2.0, 1.6, 2.2, M["cabinet"], door_side=-1)
    for x in (-40.0, -28.0, 30.0):
        bench(b, col, x, c1 + 1.6)
    for x in (-30.0, 36.0, 50.0):
        bench(b, col, x, c2 - 1.6)
    for x in (-60.0, -42.0, -24.0, 24.0, 42.0, 60.0):     # P1 — зелёные, P2 — натриевые
        platform_lamp(b, x, c1 - 2.0, "green")
    for x in (-58.0, -40.0, -22.0, 20.0, 40.0, 58.0):
        platform_lamp(b, x, c2 + 1.0, "orange" if x > 0 else "green")
    # релейные шкафы и будки у путей
    for x, y in ((-20.0, -46.5), (-62.0, -46.8), (30.0, -31.7), (-48.0, 25.2), (58.0, 25.0), (-8.0, -16.0)):
        b.box((x - 0.4, y - 0.3, 0), (x + 0.4, y + 0.3, 1.6), fx(M["cabinet"], SIDES), scale=(1, 1.6))
        b.box((x - 0.45, y - 0.35, 1.6), (x + 0.45, y + 0.35, 1.75), fx(M["snow"], OPEN), scale=(3, 3))
        col.box((x - 0.4, y - 0.3, 0), (x + 0.4, y + 0.3, 1.6), fx(M["plinth"], ALL))
    # павильон «Одеса-Східна» на северной стороне (как на фото): стены, двускатная крыша на столбах, вывеска на фронтоне
    sx0, sx1, sy0, sy1, wh = -26.0, -8.0, 44.0, 52.0, 3.4
    b.box((sx0 + 2, sy0 + 1.5, 0), (sx1 - 2, sy1, wh), fx(M["station"], SIDES), scale=(3, 3))
    col.box((sx0 + 2, sy0 + 1.5, 0), (sx1 - 2, sy1, wh), fx(M["plinth"], ALL))
    for x in (sx0 + 0.5, sx1 - 0.5):
        b.box((x - 0.25, sy0 + 0.2, 0), (x + 0.25, sy0 + 0.7, wh), fx(M["station"], SIDES), scale=(3, 3))
        col.box((x - 0.25, sy0 + 0.2, 0), (x + 0.25, sy0 + 0.7, wh), fx(M["plinth"], ALL))
    yr = (sy0 + sy1) / 2
    ov = 0.8
    for ya, yb in ((sy0 - ov, yr), (sy1 + ov, yr)):
        pts = [(sx0 - ov, ya, wh), (sx1 + ov, ya, wh), (sx1 + ov, yb, wh + 2.2), (sx0 - ov, yb, wh + 2.2)]
        quad(b, pts, M["snow"], (0, ya - yr, 1), (3, 3))
        quad(b, [(p[0], p[1], p[2] - 0.15) for p in pts], M["roof"], (0, 0, -1), (3, 3))
    for xe, s in ((sx0 - ov, -1), (sx1 + ov, 1)):
        quad(b, [(xe, sy0 - ov, wh), (xe, sy1 + ov, wh), (xe, yr, wh + 2.2)], M["station"], (s, 0, 0), (3, 3))
    b.box((sx0 + 3, sy0 - ov - 0.02, wh + 0.2), (sx1 - 3, sy0 - ov, wh + 0.9), {'-Y': (M["sign"], (0, 0, 1, 1))})
    for x in range(int(sx0) + 4, int(sx1) - 2, 3):          # окна-проёмы тёмные, одно светится
        b.box((x, sy0 + 1.49, 1.0), (x + 1.4, sy0 + 1.5, 2.4), fx(M["glass"] if x == int(sx0) + 7 else M["metal"], ('-Y',)), scale=(1.4, 1.4))
    lamp("station", "orange", (-17.0, sy0 - 0.5, 0), (-17.0, sy0 - 0.5, wh - 0.3), energy=6.0)
    # фонари на земле у лестниц моста
    for x, y, c in ((4.0, -74.0, "orange"), (-4.0, 50.0, "green")):
        b.cyl((x, y, 0), (x, y, 7.4), 0.13, 0.07, M["metal"], segs=8, su=2)
        b.cyl((x, y, 7.3), (x - 1.4 * (1 if x > 0 else -1), y, 7.7), 0.05, 0.045, M["metal"], segs=6)
        hx = x - 1.5 * (1 if x > 0 else -1)
        b.box((hx - 0.3, y - 0.18, 7.55), (hx + 0.3, y + 0.18, 7.75), fx(M["metal"], ALL), scale=(1, 1))
        b.box((hx - 0.25, y - 0.14, 7.47), (hx + 0.25, y + 0.14, 7.55), fx(M["lamp_o"] if c == "orange" else M["lamp_g"], ('-Z',)), scale=(1, 1))
        col.box((x - 0.15, y - 0.15, 0), (x + 0.15, y + 0.15, 7.4), fx(M["plinth"], ALL))
        lamp("ground", c, (x, y, 0), (hx, y, 7.4))
    return build(b, "EbProps", coll), build(col, "EbPropsCol-colonly", coll)


# ------------------------------------------------------------------ фон: панельки, гаражи, дальние огни
def backdrop(coll):
    """Дома за заборами (шейдер окон shaders/backdrop_house.gdshader, как у района): UV — метры, UV2 — (номер+оттенок, доля окон)."""
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
        """Дальний огонь: квадрат лицом к станции."""
        ang = math.atan2(-y, -x)
        tx, ty = -math.sin(ang) * s, math.cos(ang) * s
        poly([(x - tx, y - ty, z - s), (x + tx, y + ty, z - s), (x + tx, y + ty, z + s), (x - tx, y - ty, z + s)],
             [(0, 0), (1, 0), (1, 1), (0, 1)], (kind, 0.0), 1)

    k = 0
    # юг: ряд девятиэтажек за забором, за ними свечки
    for i, x in enumerate(range(-150, 160, 70)):
        house(k, x + (i % 2) * 12, -105 - (i % 3) * 6, 60, 12, 27.5, 0.35); k += 1
    for x in (-120, -40, 30, 95):
        house(k, x, -150, 18, 18, 48, 0.3); k += 1
    # север: девятиэтажки и шестнадцатиэтажки (на ночных фото — за путями)
    for i, x in enumerate(range(-160, 170, 64)):
        house(k, x, 92 + (i % 2) * 10, 54, 12, 27.5 if i % 3 else 45, 0.4); k += 1
    for x in (-90, 10, 120):
        house(k, x, 140, 60, 12, 30, 0.3); k += 1
    # частный сектор и склады у путей (низкие, на восток и запад, за краем)
    for side in (-1, 1):
        for i in range(6):
            house(k, side * (190 + i * 22), -60 + i * 25, 16, 10, 6 if i % 2 else 9, 0.12); k += 1
    # дальние огни: натрий над путями на востоке и западе, огни города
    for side in (-1, 1):
        for i in range(10):
            glow(side * (180 + i * 18), -40 + (i * 13) % 70, 10, 0.9, 0.0)
    for i in range(14):
        glow(-200 + i * 30, 170, 6 + (i % 3) * 4, 0.7, 0.0)

    m = bpy.data.meshes.new("EbBackdrop_nocol")
    m.from_pydata(me["v"], [], me["f"])
    l1 = m.uv_layers.new(name="UVMap")
    l2 = m.uv_layers.new(name="UV2")
    for i in range(len(me["uv"])):
        l1.data[i].uv = me["uv"][i]
        l2.data[i].uv = me["uv2"][i]
    m.materials.append(M["house"])
    m.materials.append(M["glow"])
    for p, mi in zip(m.polygons, me["mi"]):
        p.material_index = mi
    m.update()
    ob = bpy.data.objects.new("EbBackdrop_nocol", m)
    coll.objects.link(ob)
    return ob


# ------------------------------------------------------------------ сборка и экспорт
PARTS = [
    ("eb_ground", lambda c: [ground(c), *tracks(c), platforms(c), *fences(c)]),
    ("eb_bridge", lambda c: list(bridge(c))),
    ("eb_catenary", lambda c: list(catenary(c))),
    ("eb_trains", lambda c: list(trains(c))),
    ("eb_props", lambda c: list(props(c))),
    ("eb_backdrop", lambda c: [backdrop(c)]),
]


def main(export=True):
    LIGHTS.clear()
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
        stats[name] = sum(len(o.data.polygons) for o in obs)
        groups.append((name, obs))
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
