# Инфраструктура микрорайона «Паскот» (этап B, docs/CITY_PLAN.md): набор модульных low-poly моделей —
# подпорные стенки, лестницы с перилами, пандусы, бордюры и тротуар, трамвайные пути, опоры и провода,
# подземный переход (портал и павильон выхода), остановка, теплотрасса.
# Результат — assets/models/district/infra_*.gltf и сцена «Infra» (стенд: модели в ряд), tools/blender/infra.blend.
#
# Запуск в открытом Blender (через Blender MCP или вкладку Scripting):
#   DISTRICT_ROOT = r"<папка проекта>"; exec(open(DISTRICT_ROOT + r"\tools\blender\build_infra.py", encoding="utf-8").read())
# или без окна:  blender -b --python tools/blender/build_infra.py
# Текстуры (один раз или после правок):  blender -b --python tools/blender/infra_textures.py
#
# Оси Blender: Z — вверх, «перед» модели смотрит в −Y (в Godot это +Z). Точка опоры — центр низа.
# Лестницы и пандусы поднимаются в сторону +Y. Размеры повторяют серые блоки блокаута
# (tools/make_district_blockout.py). Вывесок и названий нет — их даст автор.
# Объекты с «nocol» в имени импортируются без коллизии (scripts/tools/ps2_import.gd): по ступеням
# ходят через невидимые пандусы, провода не мешают.
import bpy
import math
import os
from mathutils import Vector

ROOT = globals().get("DISTRICT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
OUT = os.path.join(ROOT, "assets", "models", "district")

# построитель мешей и материалы двора — из build_yard.py (без его main)
ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), ns)
ns["TEX"] = os.path.join(ROOT, "assets", "textures")
B, mat, M = ns["B"], ns["mat"], ns["M"]
ns["build_materials"]()
M["retwall"] = mat("RetWall", "retwall")
M["paving"] = mat("Paving", "paving")
M["asphalt"] = mat("AsphaltSnow", "asphalt_snow")
M["pipe"] = mat("PipeWrap", "pipe_wrap", rough=0.7)
M["stop"] = mat("StopWall", "stop_wall", rough=0.6)
M["sign"] = mat("UnderpassSign", "underpass_sign", "underpass_sign_emission", rough=0.5)
M["slush"] = mat("Slush", "slush")

ALL = ('+X', '-X', '+Y', '-Y', '+Z', '-Z')
SIDES = ('+X', '-X', '+Y', '-Y')
SNOWF = ('+X', '-X', '+Y', '-Y', '+Z')
CONC = (3.6, 0.9)        # шаг текстуры бетона (plinth)
WALL = (3.0, 3.0)        # шаг текстуры подпорной стенки


def fx(m, keys=ALL):
    return {k: m for k in keys}


def quad(b, pts, m, out, s=(1.0, 1.0), uvs=None):
    """Грань с нормалью в сторону out. Без uvs — мировая проекция по главной оси нормали."""
    pts = [Vector(p) for p in pts]
    n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
    if n.dot(Vector(out)) < 0:
        pts.reverse()
        n = -n
        if uvs:
            uvs = list(reversed(uvs))
    if not uvs:
        ax = max(range(3), key=lambda i: abs(n[i]))
        if ax == 2:
            uvs = [(p.x / s[0], p.y / s[1]) for p in pts]
        elif ax == 0:
            uvs = [(p.y / s[0], p.z / s[1]) for p in pts]
        else:
            uvs = [(p.x / s[0], p.z / s[1]) for p in pts]
    b.poly(pts, uvs, m)


def snow_cap(b, mn, mx, h=0.1):
    b.box((mn[0], mn[1], mx[2]), (mx[0], mx[1], mx[2] + h), fx(M["snow"], SNOWF), scale=(3, 3))


# ------------------------------------------------------------------ подпорная стенка, перила, бордюр, тротуар
def retwall(name, coll, L, H):
    """Секция подпорной стенки: лицо смотрит в −Y (в нижний двор), контрфорсы, оголовок, сугроб у подножия."""
    b = B()
    hw = L / 2
    b.box((-hw, 0, 0), (hw, 0.4, H), fx(M["retwall"], ('-Y', '+X', '-X')), scale=WALL)
    b.box((-hw, -0.1, H), (hw, 0.5, H + 0.14), fx(M["plinth"], ('-Y', '+Y', '+X', '-X', '-Z')), scale=CONC)
    snow_cap(b, (-hw, -0.1, H), (hw, 0.5, H + 0.14))
    n = max(1, round(L / 3.0))
    for i in range(n):
        x = -hw + L * (i + 0.5) / n
        b.box((x - 0.25, -0.3, 0), (x + 0.25, 0, H - 0.5), fx(M["retwall"], ('-Y', '+X', '-X')), scale=WALL)
        quad(b, [(x - 0.25, -0.3, H - 0.5), (x + 0.25, -0.3, H - 0.5), (x + 0.25, 0, H - 0.15), (x - 0.25, 0, H - 0.15)],
             M["snow"], (0, -1, 1), (3, 3))
        b.cyl((x + L / n / 2 - 0.2, -0.02, 0.55), (x + L / n / 2 - 0.2, -0.16, 0.5), 0.06, 0.06, M["metal"], segs=5)   # дренаж
    quad(b, [(-hw, -0.9, 0), (hw, -0.9, 0), (hw, 0, 0.5), (-hw, 0, 0.5)], M["snow"], (0, -1, 1), (3, 3))
    return b.build(name, coll)


def railing(name, coll, L, H=1.0):
    """Секция перил вдоль подпорной стенки: стойки, два пояса, прутья."""
    b = B()
    hw = L / 2
    n = max(1, round(L / 2.0))
    for i in range(n + 1):
        x = -hw + L * i / n
        b.box((x - 0.035, -0.035, 0), (x + 0.035, 0.035, H), fx(M["green"], SNOWF), scale=(0.5, 1))
    for z in (0.14, H - 0.06):
        b.box((-hw, -0.025, z), (hw, 0.025, z + 0.05), fx(M["green"], ('+Y', '-Y', '+Z', '-Z')), scale=(1, 1))
    x = -hw + 0.2
    while x < hw - 0.05:
        b.box((x - 0.012, -0.012, 0.19), (x + 0.012, 0.012, H - 0.06), fx(M["green"], SIDES), scale=(0.5, 1))
        x += 0.2
    b.box((-hw, -0.03, H - 0.01), (hw, 0.03, H + 0.03), fx(M["snow"], ('+Y', '-Y', '+Z')), scale=(3, 3))
    return b.build(name, coll)


def curb(name, coll, L):
    b = B()
    hw = L / 2
    b.box((-hw, -0.08, 0), (hw, 0.08, 0.2), fx(M["plinth"], SNOWF), scale=CONC)
    return b.build(name, coll)


def sidewalk(name, coll, L, W):
    """Тротуар: плитка в снегу, со стороны −Y бордюр."""
    b = B()
    hw, hd = L / 2, W / 2
    b.box((-hw, -hd + 0.16, 0), (hw, hd, 0.14), {'+Z': M["paving"]}, scale=(2, 2))
    b.box((-hw, -hd + 0.16, 0), (hw, hd, 0.14), fx(M["plinth"], ('+X', '-X', '+Y')), scale=CONC)
    b.box((-hw, -hd, 0), (hw, -hd + 0.16, 0.18), fx(M["plinth"], SNOWF), scale=CONC)
    return b.build(name, coll)


# ------------------------------------------------------------------ лестницы и пандусы
def stairs(name, coll, W, rise, run):
    """Бетонная лестница: натоптанная середина ступеней, снег по краям, боковые стенки-косоуры, перила.
    Низ — у −Y, верх — у +Y."""
    b = B()
    hw = W / 2
    n = max(2, round(rise / 0.155))
    th, td = rise / n, run / n
    y0 = -run / 2
    step_z = lambda y: min(n, int((y - y0) / td) + 1) * th
    for i in range(n):
        ya, yb, z = y0 + i * td, y0 + (i + 1) * td, (i + 1) * th
        quad(b, [(-hw, ya, z - th), (hw, ya, z - th), (hw, ya, z), (-hw, ya, z)], M["plinth"], (0, -1, 0), CONC)
        edge = min(0.9, W * 0.22)
        for xa, xb, m in ((-hw, -hw + edge, M["snow"]), (-hw + edge, hw - edge, M["slush"]), (hw - edge, hw, M["snow"])):
            quad(b, [(xa, ya, z), (xb, ya, z), (xb, yb, z), (xa, yb, z)], m, (0, 0, 1), (4, 4))
    quad(b, [(-hw, y0 + run, 0), (hw, y0 + run, 0), (hw, y0 + run, rise), (-hw, y0 + run, rise)], M["retwall"], (0, 1, 0), WALL)
    ch = 0.35                                            # боковые стенки выше ступеней на ch
    for sx in (-1, 1):
        xi, xo = sx * hw, sx * (hw + 0.3)
        lo0, lo1, hi0, hi1 = (y0, 0), (y0 + run, 0), (y0, ch), (y0 + run, rise + ch)
        for x, out in ((xo, sx), (xi, -sx)):
            quad(b, [(x, lo0[0], lo0[1]), (x, lo1[0], lo1[1]), (x, hi1[0], hi1[1]), (x, hi0[0], hi0[1])], M["retwall"], (out, 0, 0), WALL)
        quad(b, [(xi, hi0[0], hi0[1]), (xo, hi0[0], hi0[1]), (xo, hi1[0], hi1[1]), (xi, hi1[0], hi1[1])], M["snow"], (0, 0, 1), (3, 3))
        quad(b, [(xi, y0, 0), (xo, y0, 0), (xo, y0, ch), (xi, y0, ch)], M["retwall"], (0, -1, 0), WALL)
        quad(b, [(xi, y0 + run, 0), (xo, y0 + run, 0), (xo, y0 + run, rise + ch), (xi, y0 + run, rise + ch)], M["retwall"], (0, 1, 0), WALL)
        xr = sx * (hw + 0.15)                            # перила по стенке
        zc = lambda y: ch + (y - y0) / run * rise
        k = max(2, round(run / 1.4))
        for j in range(k + 1):
            y = y0 + 0.1 + (run - 0.2) * j / k
            b.cyl((xr, y, zc(y)), (xr, y, zc(y) + 0.9), 0.025, 0.025, M["green"], segs=5)
        b.cyl((xr, y0 + 0.1, zc(y0 + 0.1) + 0.9), (xr, y0 + run - 0.1, zc(y0 + run - 0.1) + 0.9), 0.03, 0.03, M["green"], segs=5)
    if W >= 8:                                           # широкая лестница — поручень посередине
        k = max(2, round(run / 1.4))
        for j in range(k + 1):
            y = y0 + 0.15 + (run - 0.3) * j / k
            b.cyl((0, y, step_z(y) - th), (0, y, step_z(y) + 0.9), 0.025, 0.025, M["green"], segs=5)
        ya, yb = y0 + 0.15, y0 + run - 0.15
        b.cyl((0, ya, step_z(ya) + 0.9), (0, yb, step_z(yb) + 0.9), 0.03, 0.03, M["green"], segs=5)
    return b.build(name, coll)


def ramp(name, coll, W, L, rise):
    """Пандус проезда: раскатанные колеи, бордюры под снегом, боковые подпорные стенки."""
    b = B()
    hw, hl = W / 2, L / 2
    quad(b, [(-hw, -hl, 0), (hw, -hl, 0), (hw, hl, rise), (-hw, hl, rise)], M["asphalt"], (0, 0, 1),
         uvs=[(0, 0), (W / 6.0, 0), (W / 6.0, L / 6.0), (0, L / 6.0)])
    quad(b, [(-hw, hl, 0), (hw, hl, 0), (hw, hl, rise), (-hw, hl, rise)], M["retwall"], (0, 1, 0), WALL)
    for sx in (-1, 1):
        xi, xo = sx * hw, sx * (hw + 0.3)
        quad(b, [(xo, -hl, 0), (xo, hl, 0), (xo, hl, rise + 0.25), (xo, -hl, 0.25)], M["retwall"], (sx, 0, 0), WALL)
        quad(b, [(xi, -hl, 0), (xi, hl, rise), (xi, hl, rise + 0.25), (xi, -hl, 0.25)], M["plinth"], (-sx, 0, 0), CONC)
        quad(b, [(xi, -hl, 0.25), (xo, -hl, 0.25), (xo, hl, rise + 0.25), (xi, hl, rise + 0.25)], M["snow"], (0, 0, 1), (3, 3))
        quad(b, [(xi, -hl, 0), (xo, -hl, 0), (xo, -hl, 0.25), (xi, -hl, 0.25)], M["plinth"], (0, -1, 0), CONC)
        quad(b, [(xi, hl, 0), (xo, hl, 0), (xo, hl, rise + 0.25), (xi, hl, rise + 0.25)], M["retwall"], (0, 1, 0), WALL)
    return b.build(name, coll)


# ------------------------------------------------------------------ трамвай
def tram_track(name, coll, L):
    """Трамвайный путь: одна колея 1,52 м, шпалы местами торчат из снега."""
    b = B()
    hw = L / 2
    b.box((-hw, -2, 0), (hw, 2, 0.05), fx(M["snow"], ('+Z', '+Y', '-Y')), scale=(3, 3))
    for y in (-0.76, 0.76):
        b.box((-hw, y - 0.035, 0.05), (hw, y + 0.035, 0.17), fx(M["metal"], ('+Z', '+Y', '-Y')), scale=(0.5, 0.5))
    x = -hw + 0.35
    while x < hw:
        b.box((x - 0.12, -1.25, 0.05), (x + 0.12, 1.25, 0.1), fx(M["wood"], ('+Z', '+X', '-X')), scale=(2, 0.5))
        x += 0.7
    for xa, xb in ((-hw, -hw + L * 0.3), (-hw + L * 0.55, -hw + L * 0.8)):          # снег замёл шпалы кусками
        b.box((xa, -0.72, 0.05), (xb, 0.72, 0.13), fx(M["snow"], ('+Z', '+X', '-X')), scale=(3, 3))
    return b.build(name, coll)


def tram_pole(name, coll):
    """Опора контактной сети: стоит сбоку от пути (в +Y от его оси на 1,7 м), консоль тянется в −Y над путём."""
    b = B()
    b.box((-0.3, -0.3, 0), (0.3, 0.3, 0.35), fx(M["plinth"], SNOWF), scale=CONC)
    b.cyl((0, 0, 0.35), (0, 0, 9.0), 0.17, 0.1, M["metal"], segs=8, caps=True, su=2)
    b.cyl((0, 0, 6.5), (0, -3.2, 6.5), 0.05, 0.04, M["metal"], segs=5)                 # консоль
    b.cyl((0, 0, 8.0), (0, -3.0, 6.55), 0.02, 0.02, M["metal"], segs=4)                # тяга
    b.cyl((0, 0, 5.6), (0, -1.2, 6.45), 0.025, 0.025, M["metal"], segs=4)              # подкос
    for y in (-1.7, -2.9):
        b.cyl((0, y, 6.5), (0, y, 6.1), 0.045, 0.045, M["green"], segs=5)              # изоляторы
    b.cyl((0, 0, 8.6), (0, 1.3, 8.9), 0.05, 0.04, M["metal"], segs=5)                  # светильник в сторону тротуара
    b.box((-0.18, 1.2, 8.82), (0.18, 1.9, 9.0), fx(M["metal"], SNOWF), scale=(0.5, 0.5))
    b.box((-0.14, 1.26, 8.79), (0.14, 1.84, 8.82), {'-Z': (M["glass"], (0, 0, 1, 1))})
    return b.build(name, coll)


def tram_wire(name, coll, L):
    """Пролёт контактной сети между опорами: контактный провод, несущий трос с провисом, струны."""
    b = B()
    hw = L / 2
    b.cyl((-hw, 0, 5.95), (hw, 0, 5.95), 0.014, 0.014, M["metal"], segs=3)
    pts = [(-hw + L * i / 4, 6.1 + 0.3 * abs(i - 2) / 2 + (0.0 if i in (0, 4) else -0.05)) for i in range(5)]
    for (xa, za), (xb, zb) in zip(pts, pts[1:]):
        b.cyl((xa, 0, za), (xb, 0, zb), 0.01, 0.01, M["metal"], segs=3)
    for x, z in pts[1:4]:
        b.cyl((x, 0, 5.95), (x, 0, z), 0.006, 0.006, M["metal"], segs=3)
    return b.build(name, coll)


def tram_stop(name, coll, L=16.0):
    """Остановка-навес: задняя стенка и торцы (профлист + грязное стекло), лавка, навес под снегом. Открыта в −Y."""
    b = B()
    hw = L / 2
    n = int(L // 4)
    for i in range(n + 1):
        x = -hw + i * 4.0
        b.box((x - 0.05, 1.05, 0), (x + 0.05, 1.15, 2.6), fx(M["metal"], SIDES), scale=(0.5, 1))
        b.cyl((x, -1.2, 0), (x, -1.2, 2.6), 0.04, 0.04, M["metal"], segs=5)
    for i in range(n):
        x = -hw + i * 4.0
        u0 = 0.0 if i % 2 == 0 else 1.0
        rect = (u0, 0, 1 - u0, 1)
        b.box((x + 0.05, 1.08, 0.25), (x + 3.95, 1.12, 2.3), {'-Y': (M["stop"], rect), '+Y': (M["stop"], rect)})
    for sx in (-1, 1):
        x = sx * hw
        b.box((x - 0.02, -0.4, 0.25), (x + 0.02, 1.05, 2.3), {'+X': (M["stop"], (0, 0, 0.36, 1)), '-X': (M["stop"], (0, 0, 0.36, 1))})
    b.box((-hw - 0.3, -1.5, 2.6), (hw + 0.3, 1.35, 2.72), fx(M["metal"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(1, 1))
    snow_cap(b, (-hw - 0.25, -1.45, 2.6), (hw + 0.25, 1.3, 2.72), 0.2)
    for xa, xb in ((-hw + 0.6, -0.6), (0.6, hw - 0.6)):                              # лавки
        for y in (0.5, 0.68, 0.86):
            b.box((xa, y, 0.42), (xb, y + 0.14, 0.47), fx(M["wood"], ALL), scale=(2, 0.5))
        k = max(2, round((xb - xa) / 2.0))
        for j in range(k + 1):
            x = xa + 0.15 + (xb - xa - 0.3) * j / k
            b.box((x - 0.04, 0.5, 0), (x + 0.04, 1.0, 0.42), fx(M["metal"], SIDES), scale=(0.5, 0.5))
    b.box((hw - 1.3, -0.25, 0.08), (hw - 0.7, 0.25, 0.85), fx(M["green"], SIDES), scale=(1.3, 1.0))      # урна
    b.box((hw - 1.3, -0.25, 0.85), (hw - 0.7, 0.25, 0.9), fx(M["snow"], SNOWF), scale=(2, 2))
    return b.build(name, coll)


# ------------------------------------------------------------------ подземный переход
def underpass_portal(name, coll, W=6.0, H=3.0, clear=2.4):
    """Портал перехода в подпорной стенке: плоскость стенки — y = 0, проём шириной W, перемычка, указатель, лампа.
    Ноль по высоте — земля двора; пол перехода на 1 м ниже (к порталу ведёт infra_underpass_ramp)."""
    b = B()
    hw = W / 2
    for sx in (-1, 1):
        xa, xb = sorted((sx * hw, sx * (hw + 0.6)))
        b.box((xa, -0.4, -1.0), (xb, 0, H), fx(M["retwall"], ('-Y', '+X', '-X')), scale=WALL)
        quad(b, [(sx * hw, 0, -1.0), (sx * hw, 1.2, -1.0), (sx * hw, 1.2, clear), (sx * hw, 0, clear)], M["retwall"], (-sx, 0, 0), WALL)
    b.box((-hw - 0.6, -0.5, clear), (hw + 0.6, 0, H), fx(M["plinth"], ('-Y', '-Z', '+X', '-X')), scale=CONC)
    quad(b, [(-hw, 0, clear), (hw, 0, clear), (hw, 1.2, clear), (-hw, 1.2, clear)], M["plinth"], (0, 0, -1), CONC)
    snow_cap(b, (-hw - 0.7, -0.6, clear), (hw + 0.7, 0.1, H), 0.16)
    b.box((-1.2, -0.56, clear + 0.1), (1.2, -0.5, clear + 0.5), {'-Y': (M["sign"], (0, 0, 1, 1))})
    b.box((-1.24, -0.55, clear + 0.06), (1.24, -0.5, clear + 0.54), fx(M["metal"], ('+X', '-X', '+Z', '-Z')), scale=(0.5, 0.5))
    b.box((-0.45, -0.34, clear - 0.07), (0.45, -0.12, clear), fx(M["metal"], SIDES), scale=(0.5, 0.5))
    b.box((-0.45, -0.34, clear - 0.07), (0.45, -0.12, clear), {'-Z': (M["glass"], (0, 0, 1, 1))})
    return b.build(name, coll)


def underpass_ramp(name, coll, W=6.0, L=6.0, drop=1.0):
    """Спуск к порталу перехода: выемка во дворе, пол уходит вниз на drop в сторону +Y (к порталу), по бокам стенки с парапетом."""
    b = B()
    hw, hl = W / 2, L / 2
    quad(b, [(-hw, -hl, 0), (hw, -hl, 0), (hw, hl, -drop), (-hw, hl, -drop)], M["asphalt"], (0, 0, 1),
         uvs=[(0, 0), (W / 6.0, 0), (W / 6.0, L / 6.0), (0, L / 6.0)])
    for sx in (-1, 1):
        xi, xo = sx * hw, sx * (hw + 0.3)
        quad(b, [(xi, -hl, 0), (xi, hl, -drop), (xi, hl, 0.45), (xi, -hl, 0.45)], M["retwall"], (-sx, 0, 0), WALL)
        quad(b, [(xo, -hl, 0), (xo, hl, 0), (xo, hl, 0.45), (xo, -hl, 0.45)], M["retwall"], (sx, 0, 0), WALL)
        quad(b, [(xi, -hl, 0.45), (xo, -hl, 0.45), (xo, hl, 0.45), (xi, hl, 0.45)], M["snow"], (0, 0, 1), (3, 3))
        quad(b, [(xi, -hl, 0), (xo, -hl, 0), (xo, -hl, 0.45), (xi, -hl, 0.45)], M["retwall"], (0, -1, 0), WALL)
    return b.build(name, coll)


def underpass_exit(name, coll, W=6.0, L=7.0):
    """Павильон над лестницей перехода: парапет с трёх сторон, навес на стойках, остекление. Выход — в +Y.
    Ноль — земля проспекта, центр — середина проёма лестницы W×L."""
    b = B()
    hw, hl = W / 2, L / 2
    walls = [((-hw - 0.3, -hl - 0.3, 0), (-hw, hl, 1.0)), ((hw, -hl - 0.3, 0), (hw + 0.3, hl, 1.0)),
             ((-hw, -hl - 0.3, 0), (hw, -hl, 1.0))]
    for mn, mx in walls:
        b.box(mn, mx, fx(M["plinth"], SIDES + ('+Z',)), scale=CONC)
    top = 2.7
    for sx in (-1, 1):
        x = sx * (hw + 0.15)
        for y in (-hl - 0.15, -hl / 3, hl / 3, hl - 0.1):
            b.cyl((x, y, 1.0), (x, y, top), 0.05, 0.05, M["metal"], segs=5)
        b.box((x - 0.02, -hl - 0.15, 1.0), (x + 0.02, hl - 0.1, top - 0.1),
              {'+X': (M["stop"], (0, 0.5, 2, 1)), '-X': (M["stop"], (0, 0.5, 2, 1))})
    b.box((-hw - 0.15, -hl - 0.17, 1.0), (hw + 0.15, -hl - 0.13, top - 0.1),
          {'+Y': (M["stop"], (0, 0.5, 2, 1)), '-Y': (M["stop"], (0, 0.5, 2, 1))})
    b.box((-hw - 0.6, -hl - 0.6, top), (hw + 0.6, hl + 0.5, top + 0.12), fx(M["metal"], ('+X', '-X', '+Y', '-Y', '-Z')), scale=(1, 1))
    snow_cap(b, (-hw - 0.55, -hl - 0.55, top), (hw + 0.55, hl + 0.45, top + 0.12), 0.22)
    b.box((-1.2, hl + 0.5, top - 0.36), (1.2, hl + 0.56, top + 0.04), {'+Y': (M["sign"], (0, 0, 1, 1))})
    b.box((-0.45, hl - 0.4, top - 0.07), (0.45, hl - 0.18, top), fx(M["metal"], SIDES), scale=(0.5, 0.5))
    b.box((-0.45, hl - 0.4, top - 0.07), (0.45, hl - 0.18, top), {'-Z': (M["glass"], (0, 0, 1, 1))})
    return b.build(name, coll)


# ------------------------------------------------------------------ теплотрасса
PR, PY, PZ = 0.3, 0.36, 1.15     # радиус трубы в изоляции, полурасстояние между двумя нитками, высота оси низкой трассы


def pipes(b, a, c, off):
    a, c, off = Vector(a), Vector(c), Vector(off)
    for s in (-1, 1):
        b.cyl(a + off * s, c + off * s, PR, PR, M["pipe"], segs=8, su=2.0)


def collar(b, p, r=0.4):
    """Металлический короб на стыке/повороте труб — закрывает пересечение цилиндров."""
    p = Vector(p)
    b.box(p - Vector((r, r, r)), p + Vector((r, r, r)), fx(M["metal"]), scale=(0.8, 0.8))


def support(b, x, y=0.0, top=None):
    top = PZ - PR + 0.03 if top is None else top
    b.box((x - 0.2, y - 0.8, 0), (x + 0.2, y + 0.8, top), fx(M["plinth"], SNOWF), scale=CONC)


def pipe_straight(name, coll, L):
    """Низкая теплотрасса вдоль X: две нитки на бетонных опорах, сверху слежавшийся снег — по нему можно пройти."""
    b = B()
    hw = L / 2
    pipes(b, (-hw, 0, PZ), (hw, 0, PZ), (0, PY, 0))
    n = max(1, round(L / 3.0))
    for i in range(n):
        support(b, -hw + L * (i + 0.5) / n)
    b.box((-hw, -0.52, PZ + PR - 0.06), (hw, 0.52, PZ + PR + 0.05), fx(M["snow"], ('+Z', '+Y', '-Y')), scale=(3, 3))
    return b.build(name, coll)


def pipe_corner(name, coll):
    """Поворот низкой трассы на 90°: приходит с −X, уходит в +Y."""
    b = B()
    for s in (-1, 1):
        c = Vector((s * PY, -s * PY, PZ))
        b.cyl((-1.5, -s * PY, PZ), c, PR, PR, M["pipe"], segs=8, su=2.0)
        b.cyl(c, (s * PY, 1.5, PZ), PR, PR, M["pipe"], segs=8, su=2.0)
        collar(b, c, 0.36)
    b.box((-0.9, -0.9, 0), (0.9, 0.9, PZ - PR + 0.03), fx(M["plinth"], SNOWF), scale=CONC)
    return b.build(name, coll)


def pipe_end(name, coll):
    """Тепловая камера на конце трассы: бетонный короб с люком, трубы входят со стороны +X."""
    b = B()
    b.box((-0.5, -1.5, 0), (0.5, 1.5, 2.0), fx(M["retwall"], SIDES), scale=WALL)
    snow_cap(b, (-0.55, -1.55, 0), (0.55, 1.55, 2.0), 0.14)
    b.box((-0.56, -0.4, 0.3), (-0.5, 0.4, 1.5), {'-X': (M["door"], (0, 0, 1, 1))})
    return b.build(name, coll)


def pipe_arch(name, coll, span=6.0):
    """П-образная арка труб над проездом: стойки-фермы по бокам, трубы на высоте 4,5–5,7 м. Проезд — вдоль Y."""
    b = B()
    xo = span / 2 + 0.3                                  # ось вертикальных труб
    zt = 5.1
    for sx in (-1, 1):
        x = sx * xo
        pipes(b, (sx * (xo + 0.3), 0, PZ), (x, 0, PZ), (0, PY, 0))
        pipes(b, (x, 0, PZ), (x, 0, zt), (0, PY, 0))
        for s in (-1, 1):
            collar(b, (x, s * PY, PZ), 0.36)
            collar(b, (x, s * PY, zt), 0.36)
        for y in (-0.85, 0.85):                          # ферма: две стойки и перемычки
            b.cyl((x, y, 0), (x, y, zt + 0.5), 0.06, 0.06, M["metal"], segs=5, su=2)
        for z in (1.9, 3.3, 4.6):
            b.cyl((x, -0.85, z), (x, 0.85, z), 0.04, 0.04, M["metal"], segs=4)
        b.cyl((x, -0.85, 1.9), (x, 0.85, 3.3), 0.03, 0.03, M["metal"], segs=4)
        b.cyl((x, 0.85, 3.3), (x, -0.85, 4.6), 0.03, 0.03, M["metal"], segs=4)
        b.box((x - 0.3, -1.0, 0), (x + 0.3, 1.0, 0.3), fx(M["plinth"], SNOWF), scale=CONC)
    pipes(b, (-xo, 0, zt), (xo, 0, zt), (0, PY, 0))
    b.box((-xo, -0.5, zt + PR - 0.05), (xo, 0.5, zt + PR + 0.06), fx(M["snow"], ('+Z', '+Y', '-Y')), scale=(3, 3))
    return b.build(name, coll)


def pipe_high(name, coll, L):
    """Теплотрасса на опорах (низ труб на 3,2 м): под ней можно пройти. Опора — посередине секции."""
    b = B()
    hw = L / 2
    z = 3.6
    pipes(b, (-hw, 0, z), (hw, 0, z), (0, PY, 0))
    b.box((-0.2, -0.2, 0), (0.2, 0.2, 3.2), fx(M["plinth"], SIDES), scale=CONC)
    b.box((-0.25, -0.85, 3.2), (0.25, 0.85, z - PR + 0.03), fx(M["plinth"], ALL), scale=CONC)
    b.box((-0.35, -0.35, 0), (0.35, 0.35, 0.25), fx(M["plinth"], SNOWF), scale=CONC)
    b.box((-hw, -0.5, z + PR - 0.05), (hw, 0.5, z + PR + 0.06), fx(M["snow"], ('+Z', '+Y', '-Y')), scale=(3, 3))
    return b.build(name, coll)


def pipe_joint(name, coll):
    """Узел: трубы поднимаются из камеры с низкой трассы (вдоль X) на высокую (уходит в +Y)."""
    b = B()
    b.box((-1.0, -1.5, 0), (1.0, 1.5, 1.7), fx(M["retwall"], SIDES), scale=WALL)
    snow_cap(b, (-1.05, -1.55, 0), (1.05, 1.55, 1.7), 0.14)
    for s in (-1, 1):
        x = s * PY
        b.cyl((x, 0, 1.7), (x, 0, 3.6), PR, PR, M["pipe"], segs=8, su=2.0)
        collar(b, (x, 0, 3.6), 0.36)
        b.cyl((x, 0, 3.6), (x, 1.5, 3.6), PR, PR, M["pipe"], segs=8, su=2.0)
    b.cyl((0, 0.2, 2.3), (0, 0.2, 2.7), 0.22, 0.22, M["green"], segs=6, caps=True)      # задвижка
    b.cyl((0, 0.2, 2.7), (0, 0.2, 3.0), 0.03, 0.03, M["metal"], segs=4)
    b.cyl((-0.25, 0.2, 3.0), (0.25, 0.2, 3.0), 0.03, 0.03, M["metal"], segs=4)
    return b.build(name, coll)


def pipe_crossing(name, coll, W=1.6, rise=1.7, run=4.0, deck=1.8):
    """Железная лесенка-переход через теплотрассу: марш, площадка над трубами, марш. Идёт вдоль Y."""
    b = B()
    hw = W / 2
    n = 9
    th, td = rise / n, run / n
    for sy in (-1, 1):
        ye, yd = sy * (deck / 2 + run), sy * deck / 2    # низ марша и край площадки
        for i in range(1, n):
            y = ye + (yd - ye) * i / n
            lo, hi = sorted((y - sy * 0.02, y + sy * (td - 0.02)))
            b.box((-hw + 0.04, lo, i * th - 0.04), (hw - 0.04, hi, i * th), fx(M["metal"], ('+Z', '-Z', '+Y', '-Y')), scale=(0.5, 0.5))
        for x in (-hw, hw):
            b.cyl((x, ye, 0), (x, yd, rise), 0.045, 0.045, M["green"], segs=5)                    # косоуры
            b.cyl((x, ye, 0.95), (x, yd, rise + 0.95), 0.03, 0.03, M["green"], segs=5)            # поручни
            for t in (0.0, 0.5):
                y = ye + (yd - ye) * t
                b.cyl((x, y, rise * t), (x, y, rise * t + 0.95), 0.025, 0.025, M["green"], segs=4)
    b.box((-hw, -deck / 2, rise - 0.07), (hw, deck / 2, rise), fx(M["metal"], ALL), scale=(0.5, 0.5))
    b.box((-hw + 0.1, -deck / 2 + 0.1, rise), (hw - 0.1, deck / 2 - 0.1, rise + 0.04), fx(M["snow"], SNOWF), scale=(2, 2))
    for x in (-hw, hw):
        b.cyl((x, -deck / 2, rise + 0.95), (x, deck / 2, rise + 0.95), 0.03, 0.03, M["green"], segs=5)
        for y in (-deck / 2, deck / 2):
            b.cyl((x, y, rise - 0.07), (x, y, rise + 0.95), 0.025, 0.025, M["green"], segs=4)
            b.cyl((x, y, 0), (x, y, rise), 0.035, 0.035, M["green"], segs=4)
    return b.build(name, coll)


# ------------------------------------------------------------------ список моделей
SPECS = [   # (файл, функция, аргументы, без коллизии?)
    ("infra_retwall_6x3", retwall, (6.0, 3.0), False),
    ("infra_retwall_6x25", retwall, (6.0, 2.5), False),
    ("infra_railing_4", railing, (4.0,), False),
    ("infra_curb_4", curb, (4.0,), False),
    ("infra_sidewalk_4x2", sidewalk, (4.0, 2.0), False),
    ("infra_stairs_w6_h3", stairs, (6.0, 3.0, 5.5), True),        # StairsWest, StairsSchool
    ("infra_stairs_w8_h3", stairs, (8.0, 3.0, 5.5), True),        # StairsProspect
    ("infra_stairs_w10_h3", stairs, (10.0, 3.0, 5.5), True),      # StairsWide
    ("infra_stairs_w2_h25", stairs, (2.0, 2.5, 4.5), True),       # StairsGarages
    ("infra_stairs_w6_h4", stairs, (6.0, 4.0, 7.0), True),        # TunnelStairsN
    ("infra_ramp_w6_h3", ramp, (6.0, 10.0, 3.0), False),          # RampProspect, RampSouth
    ("infra_ramp_w6_h25", ramp, (6.0, 10.0, 2.5), False),         # RampGarages
    ("infra_underpass_ramp", underpass_ramp, (), False),          # TunnelRampS
    ("infra_tram_track_10", tram_track, (10.0,), False),
    ("infra_tram_pole", tram_pole, (), False),
    ("infra_tram_wire_20", tram_wire, (20.0,), True),
    ("infra_tram_stop", tram_stop, (16.0,), False),
    ("infra_underpass_portal", underpass_portal, (), False),
    ("infra_underpass_exit", underpass_exit, (), False),
    ("infra_pipe_straight_6", pipe_straight, (6.0,), False),
    ("infra_pipe_corner", pipe_corner, (), False),
    ("infra_pipe_end", pipe_end, (), False),
    ("infra_pipe_arch", pipe_arch, (), False),
    ("infra_pipe_high_8", pipe_high, (8.0,), False),
    ("infra_pipe_joint", pipe_joint, (), False),
    ("infra_pipe_crossing", pipe_crossing, (), True),
]


def main():
    if bpy.app.background:
        sc = bpy.context.scene                      # без окна экспорт работает только с текущей сценой
    else:
        sc = bpy.data.scenes.get("Infra") or bpy.data.scenes.new("Infra")
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    if bpy.context.window:
        bpy.context.window.scene = sc
    os.makedirs(OUT, exist_ok=True)
    stats, obs = {}, []
    for fid, fn, args, nocol in SPECS:
        ob = fn(fid + ("_nocol" if nocol else ""), sc.collection, *args)
        stats[fid] = len(ob.data.polygons)
        obs.append((ob, fid))
    vl = sc.view_layers[0]
    for other in bpy.data.scenes:                   # в других сценах ничего не должно быть выделено, иначе попадёт в экспорт
        for layer in other.view_layers:
            for o in other.objects:
                o.select_set(False, view_layer=layer)
    for ob, fid in obs:
        for o in sc.objects:
            o.select_set(False, view_layer=vl)
        ob.select_set(True, view_layer=vl)
        vl.objects.active = ob
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, fid + ".gltf"), use_selection=True, export_keep_originals=True,
                                  export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    # стенд: после экспорта раскладываем модели рядами для осмотра
    x, y, row_h = 0.0, 0.0, 0.0
    for ob, fid in obs:
        xs = [v[0] for v in ob.bound_box]
        ys = [v[1] for v in ob.bound_box]
        w, d = max(xs) - min(xs), max(ys) - min(ys)
        if x + w > 60:
            x, y, row_h = 0.0, y - row_h - 6.0, 0.0
        ob.location = (x - min(xs), y - max(ys), 0)
        x += w + 4.0
        row_h = max(row_h, d)
    if not bpy.app.background:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "infra.blend"))
    return {"models": len(stats), "polys": sum(stats.values()), "max": max(stats.items(), key=lambda kv: kv[1])}


result = main()
print(result)
