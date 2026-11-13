# -*- coding: utf-8 -*-
# Собирает БЛОКАУТ микрорайона «Паскот» (этап A в docs/CITY_PLAN.md) из серых коробок (scripts/tools/blockout_box.gd):
#   scenes/levels/district.tscn       — корень: окружение, игрок, точки телепорта, подсцены зон
#   scenes/district/*.tscn            — рельеф и зоны
#
# v2 (2026-11-12): ПЛОТНАЯ планировка по просьбе автора — район ужат до ~200×215 м, проходы 3–5 м,
# дворы-колодцы 10–25 м с арками сквозь дома, проспект узкий, стадион маленький, пустырь застроен стройгородком.
#
# ВНИМАНИЕ: запускается, пока блокаут не принят автором. После приёмки источник правды — сами .tscn,
# правки делаются в редакторе мышью; повторный запуск затрёт ручные правки.
#   python tools/make_district_blockout.py
# В конце скрипт сам проверяет: не пересекаются ли сплошные блоки и не стоят ли точки телепорта внутри стен.
#
# Оси: X — восток, −Z — север, Y — вверх, метры. Центр района — (0, 0, 0).
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# высоты земли
PROSPECT, HUB, SOUTH, G1, G2, G3, PIT = 6.0, 3.0, 0.0, -2.5, -5.0, -7.5, -5.0
BOTTOM = -20.0
TINT = {PROSPECT: "Color(0.66, 0.64, 0.6, 1)", HUB: "Color(0.6, 0.58, 0.54, 1)", SOUTH: "Color(0.53, 0.51, 0.47, 1)",
        G1: "Color(0.48, 0.46, 0.42, 1)", G2: "Color(0.43, 0.41, 0.38, 1)", G3: "Color(0.38, 0.36, 0.33, 1)"}
PIT_TINT = "Color(0.34, 0.31, 0.28, 1)"
KHR_TINT = "Color(0.5, 0.42, 0.38, 1)"     # хрущёвки — кирпич

SOLIDS = []   # (x0, x1, y0, y1, z0, z1, kind, name) — для проверки пересечений
BUILDINGS = []   # дома для tools/blender/build_district.py (tools/district_buildings.json)
WRITE = "--json-only" not in sys.argv   # --json-only: только обновить список домов, сцены и карту не трогать
BLOCKS = []      # все блоки для tools/blender/build_district_props.py (tools/district_blocks.json)
FLAT = []     # (x0, x1, z0, z1, top, kind, label, tint) — всё, что рисуется на карте docs/city_map.svg


def f(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def xform(x, y, z, yaw=0.0):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    # в .tscn базис записывается по строкам: поворот на yaw против часовой (если смотреть сверху)
    return "Transform3D(%s, 0, %s, 0, 1, 0, %s, 0, %s, %s, %s, %s)" % (f(c), f(s), f(-s), f(c), f(x), f(y), f(z))


def record_building(zone, name, btype, x0, x1, z0, z1, y, h, front="S", arches=(), entrances=None):
    """Запомнить дом для сборки модели: длина L идёт вдоль фасада, локальная ось X модели — вдоль дома."""
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    along_x = front in "NS"
    L, D = (x1 - x0, z1 - z0) if along_x else (z1 - z0, x1 - x0)
    c = cx if along_x else cz
    sign = {"S": 1, "N": -1, "E": -1, "W": 1}[front]
    loc = lambda w: round(sign * (w - c), 3)
    n = sum(1 for b in BUILDINGS if b["zone"] == zone and b["name"] == name)
    BUILDINGS.append({
        "id": "%s_%s%s" % (zone.lower(), name.lower(), "" if n == 0 else str(n + 1)), "zone": zone, "name": name,
        "type": btype, "cx": cx, "cz": cz, "y": y, "L": L, "D": D, "h": h,
        "yaw": {"S": 0, "N": 180, "E": 90, "W": -90}[front],
        "arches": [sorted((loc(a), loc(b))) for a, b in arches],
        "entrances": None if entrances is None else sorted(loc(e) for e in entrances)})


class Scene:
    def __init__(self, root):
        self.root, self.lines, self.names = root, [], {}

    def uniq(self, name):
        n = self.names.get(name, 0)
        self.names[name] = n + 1
        return name if n == 0 else "%s%d" % (name, n + 1)

    def boxc(self, name, cx, cz, y, sx, sy, sz, kind, label="", shape="box", yaw=0.0, tint=None, solid=True, parent="."):
        base = name
        name = self.uniq(name)
        BLOCKS.append({"zone": self.root, "node": name, "base": base, "kind": kind, "shape": shape, "solid": solid,
                       "cx": round(cx, 3), "cz": round(cz, 3), "y": round(y, 3), "sx": round(sx, 3), "sy": round(sy, 3),
                       "sz": round(sz, 3), "yaw": yaw})
        L = ['[node name="%s" type="Node3D" parent="%s"]' % (name, parent), "transform = " + xform(cx, y, cz, yaw),
             'script = ExtResource("bb")', "size = Vector3(%s, %s, %s)" % (f(sx), f(sy), f(sz)), 'kind = "%s"' % kind]
        if shape != "box":
            L.append('shape = "%s"' % shape)
        if label:
            L.append('label = "%s"' % label)
        if tint:
            L.append("tint = " + tint)
        if not solid:
            L.append("solid = false")
        self.lines.append("\n".join(L) + "\n")
        a = abs(yaw) % 180
        hx0, hz0 = (sx / 2, sz / 2) if a < 45 or a > 135 else (sz / 2, sx / 2)
        if abs(cx) < 120 and abs(cz) < 130:
            FLAT.append((cx - hx0, cx + hx0, cz - hz0, cz + hz0, y + sy, kind, label, tint, shape))
        if solid and kind not in ("ground", "road") and (a < 1e-6 or abs(a - 90) < 1e-6):
            hx, hz = (sx / 2, sz / 2) if a < 1e-6 else (sz / 2, sx / 2)
            SOLIDS.append((cx - hx, cx + hx, y, y + sy, cz - hz, cz + hz, kind, "%s/%s" % (self.root, name)))

    def box(self, name, x0, x1, z0, z1, y, h, kind, label="", shape="box", yaw=0.0, tint=None, solid=True):
        """Прямоугольник на карте (X x0..x1, Z z0..z1), низ на высоте y, высота h. yaw 0/180 — как есть, ±90 — длина вдоль Z."""
        sx, sz = x1 - x0, z1 - z0
        if abs(abs(yaw) - 90) < 1e-6:
            sx, sz = sz, sx
        self.boxc(name, (x0 + x1) / 2, (z0 + z1) / 2, y, sx, h, sz, kind, label, shape, yaw, tint, solid)

    def ground(self, name, x0, x1, z0, z1, top, tint=None, label=""):
        self.box(name, x0, x1, z0, z1, BOTTOM, top - BOTTOM, "ground", label, tint=tint or TINT[top])

    def bld(self, name, x0, x1, z0, z1, y, h, label="", arches=(), kind="building", tint=None, ah=4.0,
            front="S", btype=None, entrances=None):
        """Дом с арками-проходами сквозь первый этаж. arches — отрезки вдоль длинной стороны дома (ширина ~4 м).
        front — куда смотрит фасад с подъездами (N/S/E/W); entrances — координаты подъездов вдоль дома (иначе авто)."""
        along_x = front in "NS"
        record_building(self.root, name, btype or ("khr" if tint == KHR_TINT else "tower" if h > 40 else "panel"),
                        x0, x1, z0, z1, y, h, front, arches, entrances)
        lo, hi = (x0, x1) if along_x else (z0, z1)
        cur = lo
        for a, b in sorted(arches) + [(hi, hi)]:
            if a > cur + 0.01:
                if along_x:
                    self.box(name, cur, a, z0, z1, y, h, kind, label, tint=tint)
                else:
                    self.box(name, x0, x1, cur, a, y, h, kind, label, tint=tint)
                label = ""
            if b > a:
                if along_x:
                    self.box(name + "Arch", a, b, z0, z1, y + ah, h - ah, kind, "Арка", tint=tint)
                else:
                    self.box(name + "Arch", x0, x1, a, b, y + ah, h - ah, kind, "Арка", tint=tint)
            cur = max(cur, b)

    def line_x(self, name, z, x0, x1, y, h, kind, gaps=(), thick=0.2, label=""):
        """Забор/перила вдоль X (на линии z) с проёмами gaps=[(a, b), ...]."""
        cur = x0
        for a, b in sorted(gaps) + [(x1, x1)]:
            if a > cur + 0.05:
                self.box(name, cur, min(a, x1), z - thick / 2, z + thick / 2, y, h, kind, label)
                label = ""
            cur = max(cur, b)

    def line_z(self, name, x, z0, z1, y, h, kind, gaps=(), thick=0.2, label=""):
        cur = z0
        for a, b in sorted(gaps) + [(z1, z1)]:
            if a > cur + 0.05:
                self.box(name, x - thick / 2, x + thick / 2, cur, min(a, z1), y, h, kind, label)
                label = ""
            cur = max(cur, b)

    def light(self, name, x, y, z, color, energy=2.0, rng=14.0):
        self.lines.append('[node name="%s" type="OmniLight3D" parent="."]\ntransform = %s\nlight_color = %s\n'
                          'light_energy = %s\nomni_range = %s\nomni_attenuation = 1.2\n'
                          % (self.uniq(name), xform(x, y, z), color, f(energy), f(rng)))

    def lamp(self, x, z, y, color="Color(1, 0.62, 0.3, 1)", on=True, energy=2.0):
        self.box("LampPole", x - 0.12, x + 0.12, z - 0.12, z + 0.12, y, 6.5, "prop")
        if on:
            self.light("LampLight", x, y + 6.2, z, color, energy, 13.0)

    def car(self, x, z, y, yaw=0.0, label=""):
        self.boxc("Car", x, z, y, 1.7, 1.45, 4.2, "car", label, yaw=yaw)

    def drift(self, x, z, y, sx=4.0, sz=2.0, h=1.2, yaw=0.0):
        self.boxc("Drift", x, z, y, sx, h, sz, "snow", yaw=yaw)

    def tree(self, x, z, y):
        self.boxc("Tree", x, z, y, 0.5, 7.0, 0.5, "tree")

    def write(self, path):
        head = '[gd_scene format=3]\n\n[ext_resource type="Script" path="res://scripts/tools/blockout_box.gd" id="bb"]\n\n'
        body = '[node name="%s" type="Node3D"]\n\n' % self.root + "\n".join(self.lines)
        if not WRITE:
            return
        full = os.path.join(ROOT, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8", newline="\n").write(head + body)
        print("written", path, "-", len(self.lines), "nodes")


# Общая сетка района (Z — с севера на юг):
#   проспект +6          Z −100…−80   (ниша у перехода до −110)
#   дворы +3             Z −80…−15    (западный двор | двор Юрчика | проезд X 20…26 | школа)
#   подпорная стенка 3 м Z = −15
#   южная полоса 0       Z −15…47     (стройка | южные дворы | хрущёвки и котельная)
#   гаражи террасами     Z 47…65 (−2,5), 65…83 (−5), 83…101 (−7,5)
#   X −100…100
SPINE = (20.0, 26.0)        # внутриквартальный проезд
TX0, TX1 = -58.0, -52.0     # подземный переход

# =====================================================================================================
# РЕЛЬЕФ: земля всех уровней, переходы между ними, перила, подземный переход, границы
# =====================================================================================================
t = Scene("Terrain")
# проспект +6 и ниша на северной стороне, где выходит переход
t.ground("Prospect", -100, TX0, -100, -80, PROSPECT)
t.ground("Prospect", TX1, 100, -100, -80, PROSPECT)
t.ground("Niche", -60, TX0, -110, -100, PROSPECT)
t.ground("Niche", TX1, -50, -110, -100, PROSPECT)
t.ground("TunnelCapN", TX0, TX1, -110, -107, PROSPECT)
# подземный переход: портал в подпорной стенке со стороны двора (+3 → пол +2), тоннель, лестница в нишу (+6)
t.ground("TunnelFloor", TX0, TX1, -107, -74, 2.0, tint=PIT_TINT, label="Подземный переход")
t.box("TunnelRoof", TX0, TX1, -100, -80, 5.4, 0.6, "ground", tint=TINT[PROSPECT])
t.box("TunnelStairsN", TX0, TX1, -107, -100, 2.0, 4.0, "ground", shape="stairs", tint=TINT[PROSPECT])
t.box("TunnelRampS", TX0, TX1, -80, -74, 2.0, 1.0, "ground", shape="ramp", yaw=180, tint=TINT[HUB])
t.line_z("TunnelRail", TX0 - 0.1, -107, -100, PROSPECT, 1.0, "rail")
t.line_z("TunnelRail", TX1 + 0.1, -107, -100, PROSPECT, 1.0, "rail")
t.line_x("TunnelRail", -99.9, TX0, TX1, PROSPECT, 1.0, "rail")
# +3: дворы и школа
t.ground("Hub", -100, TX0, -80, -15, HUB)
t.ground("Hub", TX1, 100, -80, -15, HUB)
t.ground("Hub", TX0, TX1, -74, -15, HUB)
# 0: южная полоса с котлованом
t.ground("South", -100, 100, -15, 14, SOUTH)
t.ground("South", -100, -98, 14, 44, SOUTH)
t.ground("South", -78, 100, 14, 44, SOUTH)
t.ground("South", -100, 100, 44, 47, SOUTH)
t.ground("Pit", -98, -78, 14, 44, PIT, tint=PIT_TINT, label="Котлован −5 м")
t.box("PitRamp", -84, -78, 20, 44, PIT, 5.0, "ground", shape="ramp", yaw=180, tint=PIT_TINT)
# террасы гаражей
t.ground("Garages1", -100, 100, 47, 65, G1)
t.ground("Garages2", -100, 100, 65, 83, G2)
t.ground("Garages3", -100, 100, 83, 101, G3)

# переходы между уровнями
t.box("StairsProspect", 10, 18, -80, -74.5, HUB, 3.0, "ground", "Лестница на проспект", shape="stairs", tint=TINT[HUB])
t.box("RampProspect", SPINE[0], SPINE[1], -80, -70, HUB, 3.0, "road", shape="ramp")
t.box("StairsWide", -40, -30, -15, -9.5, SOUTH, 3.0, "ground", "Лестница вниз", shape="stairs", tint=TINT[SOUTH])
t.box("StairsWest", -60, -54, -15, -9.5, SOUTH, 3.0, "ground", shape="stairs", tint=TINT[SOUTH])
t.box("StairsSchool", 50, 56, -15, -9.5, SOUTH, 3.0, "ground", shape="stairs", tint=TINT[SOUTH])
t.box("RampSouth", SPINE[0], SPINE[1], -15, -5, SOUTH, 3.0, "road", shape="ramp")
GBANDS = ((47.0, G1), (65.0, G2), (83.0, G3))
for z, lo in GBANDS:
    t.box("RampGarages", SPINE[0], SPINE[1], z, z + 10, lo, 2.5, "road", shape="ramp")
    t.box("StairsGarages", -61.5, -59.5, z, z + 4.5, lo, 2.5, "ground", shape="stairs", tint=TINT[lo])

# перила вдоль подпорных стенок
t.line_x("Parapet", -80.1, -100, 100, PROSPECT, 1.0, "rail", gaps=[(10, 18), SPINE])
t.line_x("Parapet", -15.1, -100, 100, HUB, 1.0, "rail", gaps=[(-40, -30), (-60, -54), (50, 56), SPINE])
# проезд — полоса на земле, без коллизии
for z0, z1, y in ((-70, -15, HUB), (-5, 47, SOUTH)) + tuple((z + 10, z + 18, lo) for z, lo in GBANDS):
    t.box("Road", SPINE[0], SPINE[1], z0, z1, y, 0.03, "road", solid=False)

# границы района (позже — дома, заборы и завалы)
t.bld("NorthFacades", -100, -60, -112, -100, PROSPECT, 27.0, "Дома северной стороны проспекта (стена)", btype="north")
t.bld("NorthFacades", -50, 100, -112, -100, PROSPECT, 27.0, "Дома северной стороны проспекта (стена)", btype="north")
t.bld("NorthFacades", -60, -50, -114, -110, PROSPECT, 27.0, btype="north")
t.box("Edge", -101, -100, -100, -80, PROSPECT, 5.0, "boundary", "Завал: трамвай поперёк + машины")
t.box("Edge", 100, 101, -100, -80, PROSPECT, 5.0, "boundary", "Завал: маршрутка + фура")
t.box("Edge", -101, -100, -80, -15, HUB, 3.5, "boundary", "Забор / торцы домов")
t.box("Edge", -101, -100, -15, 47, SOUTH, 3.5, "boundary", "Стройзабор")
t.box("Edge", -101, -100, 47, 101, G3, 11.0, "boundary", "Забор")
t.box("Edge", 100, 101, -80, -15, HUB, 3.5, "boundary", "Забор")
t.box("Edge", 100, 101, -15, 47, SOUTH, 3.5, "boundary", "Бетонный забор «ёлочка»")
t.box("Edge", 100, 101, 47, 101, G3, 11.0, "boundary", "Забор")
t.box("Edge", -100, 100, 101, 102, G3, 3.5, "boundary", "Забор над обрывом балки")
# земля за краем (без коллизии): на юге — провал балки
t.box("OuterW", -700, -101, -700, 700, BOTTOM, -BOTTOM, "ground", solid=False, tint=TINT[SOUTH])
t.box("OuterE", 101, 700, -700, 700, BOTTOM, -BOTTOM, "ground", solid=False, tint=TINT[SOUTH])
t.box("OuterN", -101, 101, -700, -114, BOTTOM, -BOTTOM, "ground", solid=False, tint=TINT[SOUTH])
t.box("OuterS", -101, 101, 102, 700, BOTTOM, -12 - BOTTOM, "ground", solid=False, tint=TINT[G3])
t.write("scenes/district/terrain.tscn")

# =====================================================================================================
# 1. ПРОСПЕКТ (+6): узкий — по полосе в каждую сторону и трамвай посередине
# =====================================================================================================
p = Scene("Prospect")
y = PROSPECT
p.box("Roadway", -100, 100, -97, -85, y, 0.03, "road", solid=False)
p.box("TramStrip", -100, 100, -93, -89, y, 0.04, "snow", solid=False)
for zr in (-92.0, -90.0):
    p.box("TramRail", -100, 100, zr - 0.05, zr + 0.05, y, 0.12, "rail", solid=False)
for x in range(-90, 100, 20):
    p.box("TramPole", x - 0.18, x + 0.18, -91.2, -90.8, y, 9.0, "prop", "Опора трамвая" if x == -10 else "")
p.box("StopWall", -8, 8, -82.3, -82.1, y, 2.6, "prop")
p.box("StopRoof", -8, 8, -84.5, -82.1, y + 2.6, 0.2, "prop", "Остановка трамвая", solid=False)
for i, (x0, col) in enumerate(((-40, "Color(0.7, 0.3, 0.2, 1)"), (-34, "Color(0.75, 0.6, 0.25, 1)"),
                               (30, "Color(0.3, 0.55, 0.35, 1)"), (36, "Color(0.7, 0.3, 0.2, 1)"))):
    p.box("Kiosk", x0, x0 + 4, -84.5, -82.5, y, 2.6, "prop", "Ларьки" if i == 0 else "", tint=col)
    p.light("KioskLight", x0 + 2, y + 2.0, -81.8, "Color(1, 0.75, 0.5, 1)", 1.2, 6.0)
p.box("TunnelSign", -59.5, -59, -109.5, -109, y, 2.4, "prop", "Выход из перехода")
# завалы на концах проспекта
p.boxc("Tram", -92, -91, y, 2.6, 3.6, 15.0, "car", "Трамвай", yaw=70)
p.car(-85, -86.5, y, 20)
p.car(-84, -95.5, y, -35)
p.drift(-97.5, -82, y, 4, 3, 1.6)
p.boxc("Minibus", 90, -93, y, 2.2, 2.6, 6.0, "car", "Маршрутка", yaw=30)
p.boxc("Truck", 94, -88, y, 2.5, 3.8, 13.0, "car", "Фура", yaw=-15)
p.car(84, -90, y, 80)
for x in (-70, -20, 50, 70):
    p.car(x, -86.2, y, 90)
for x in (-65, -16, 56, 80):
    p.drift(x, -81.2, y, 4, 1.2, 1.0)
for x in (-75, -25, 25, 75):
    p.lamp(x, -81.0, y, on=x in (-75, 25))
p.write("scenes/district/z1_prospect.tscn")

# =====================================================================================================
# 2. ДВОР ЮРЧИКА (+3): двор-колодец X −30…6, Z −63…−38, вход арками и узкими проходами
# =====================================================================================================
h = Scene("HomeYard")
y = HUB
h.bld("HomeBuilding", -38, 8, -77, -65, y, 26.0, "Дом Юрчика · 9 эт., 4 подъезда",
      entrances=[-30 + 38 * (i + 0.5) / 4 for i in range(4)])
for i in range(4):
    x = -30 + 38 * (i + 0.5) / 4       # подъезды выходят во двор (западный край дома закрыт крылом)
    h.box("Porch", x - 1.3, x + 1.3, -65, -63.4, y, 0.3, "prop", "Подъезд Юрчика" if i == 1 else "")
    h.box("Canopy", x - 1.5, x + 1.5, -65, -63.2, y + 2.6, 0.15, "prop", solid=False)
    if i == 1:
        h.light("EntranceLight", x, y + 2.4, -63.6, "Color(1, 0.75, 0.45, 1)", 1.5, 8.0)
h.bld("WestWing", -42, -30, -65, -27, y, 26.0, "9 эт.", arches=[(-50, -46)], front="E")
h.bld("SouthRow", -30, 8, -38, -27, y, 26.0, "9 эт.", arches=[(-14, -10)], front="N")
h.bld("EastKhr", 6, 16, -60, -42, y, 15.0, "Хрущёвка · 5 эт.", tint=KHR_TINT, front="W")
# во дворе
h.box("Slide", -27, -25.5, -59, -56, y, 2.0, "prop", "Детплощадка")
h.box("Swing", -21, -18, -58.5, -57.5, y, 2.2, "prop")
h.box("Carousel", -24, -22, -54, -52, y, 0.6, "prop")
h.box("Sandbox", -19, -16, -54, -51, y, 0.3, "prop")
h.box("Sheds", -30, -12, -46, -43, y, 2.5, "garage", "Сараи")
h.box("Kiosk", 2, 6, -56, -53.5, y, 2.6, "prop", "Ларёк «Продукты»", tint="Color(0.7, 0.3, 0.2, 1)")
h.light("KioskLight", 4, y + 2.0, -52.8, "Color(1, 0.75, 0.5, 1)", 1.3, 7.0)
h.box("Turnik", -8, -6, -48.1, -47.9, y, 2.4, "prop")
for x, z in ((-10, -55), (2, -50)):
    h.box("Bench", x - 0.9, x + 0.9, z - 0.25, z + 0.25, y, 0.5, "prop")
h.car(-6, -60, y, 90)
h.car(3, -42, y, 90)
h.drift(-14, -40.5, y, 6, 2, 1.3)
h.drift(-26, -40.5, y, 4, 2, 1.2)
h.tree(-12, -57, y)
h.tree(-2, -46, y)
# полоса за домами, у подпорной стенки
h.box("Transformer", -26, -21, -24, -20, y, 3.0, "industrial", "Трансформаторная")
h.box("ShellGarages", -18, -4, -24, -19, y, 2.2, "garage", "Гаражи-«ракушки»")
h.car(12, -20, y, 0)
h.drift(5, -17, y, 6, 2, 1.2)
for x, z, on in ((-14, -62.5, True), (-2, -40, False), (12, -62.5, True), (-35, -20, True), (12, -30, False)):
    h.lamp(x, z, y, on=on)
h.write("scenes/district/z2_home_yard.tscn")

# =====================================================================================================
# ЗАПАДНЫЙ ДВОР (+3): свечка и колодец из 9-этажек, рядом ряды «ракушек»
# =====================================================================================================
w = Scene("WestYard")
y = HUB
w.bld("Tower", -100, -84, -78, -62, y, 46.0, "Свечка · 16 эт.")
w.bld("NorthRow", -80, -62, -78, -66, y, 26.0, "9 эт.")
w.bld("EastRow", -74, -62, -62, -38, y, 26.0, "9 эт.", front="W")
w.bld("WestRow", -100, -88, -58, -20, y, 26.0, "9 эт.", arches=[(-42, -38)], front="E")
w.bld("SouthRow", -88, -62, -32, -20, y, 26.0, "9 эт.", arches=[(-78, -74)], front="N")
for x, z in ((-85, -55), (-85, -49), (-77, -52), (-77, -44)):
    w.car(x, z, y, 0)
w.drift(-81, -36, y, 6, 2, 1.4)
w.box("ShellRow", -59, -55, -56, -26, y, 2.2, "garage", "Гаражи-«ракушки»")
w.box("ShellRow", -51, -47, -56, -26, y, 2.2, "garage")
w.drift(-53, -60, y, 4, 2.5, 1.3)
w.lamp(-81, -45, y)
w.lamp(-58, -68, y)
w.write("scenes/district/z8_west_yard.tscn")

# =====================================================================================================
# 3. ШКОЛА (+3): тесный участок за забором, маленький стадион, вдоль — глухая 9-этажка
# =====================================================================================================
s = Scene("School")
y = HUB
s.line_z("Fence", 28, -78, -17, y, 2.2, "fence", gaps=[(-50, -44)], thick=0.15, label="Ворота школы")
s.line_x("Fence", -78, 28, 86, y, 2.2, "fence", thick=0.15)
s.line_z("Fence", 86, -78, -17, y, 2.2, "fence", thick=0.15)
s.line_x("Fence", -17, 28, 86, y, 2.2, "fence", gaps=[(49, 57)], thick=0.15)
s.bld("EastWall", 89, 100, -78, -17, y, 26.0, "9 эт.", front="W")
s.box("SchoolMain", 34, 80, -75, -64, y, 11.0, "school", "Школа · 3 эт.")
record_building("School", "SchoolMain", "school_main", 34, 80, -75, -64, y, 11.0)
record_building("School", "SchoolWing", "school_wing", 34, 44, -64, -52, y, 11.0, "E")
record_building("School", "SchoolWing", "school_wing", 70, 80, -64, -52, y, 11.0, "W")
s.box("SchoolWing", 34, 44, -64, -52, y, 11.0, "school")
s.box("SchoolWing", 70, 80, -64, -52, y, 11.0, "school")
s.box("Porch", 53, 61, -64, -62.5, y, 0.45, "prop", "Крыльцо")
s.box("PorchRoof", 52.5, 61.5, -64, -61.5, y + 3.0, 0.2, "prop", solid=False)
s.box("Field", 34, 78, -48, -21, y, 0.03, "snow", "Стадион (маленький)", solid=False, tint="Color(0.62, 0.68, 0.58, 1)")
s.boxc("Tribune", 82, -34.5, y, 25.0, 2.5, 6.0, "prop", "Трибуна", shape="stairs", yaw=-90)
s.box("Obstacles", 46, 68, -51, -49.5, y, 1.2, "prop", "Турники, полоса препятствий")
s.box("FloodPole", 75.8, 76.2, -50.2, -49.8, y, 14.0, "prop", "Прожектор")
s.light("FloodLight", 75, y + 13.5, -49, "Color(0.82, 0.9, 1, 1)", 4.0, 35.0)
for x in (32, 84):
    s.tree(x, -76.5, y)
s.drift(40, -25, y, 6, 2, 1.3)
s.drift(31, -60, y, 2, 6, 1.4)
s.write("scenes/district/z3_school.tscn")

# =====================================================================================================
# 4. ЮЖНЫЕ ДВОРЫ (0): колодец из хрущёвок с арками
# =====================================================================================================
so = Scene("SouthYards")
y = SOUTH
so.bld("KhrNorth", -42, 12, -5, 6, y, 15.0, "Хрущёвка · 5 эт.", arches=[(-20, -16)], tint=KHR_TINT)
so.bld("KhrWest", -42, -31, 6, 38, y, 15.0, "Хрущёвка · 5 эт.", arches=[(20, 24)], tint=KHR_TINT, front="E")
so.bld("KhrSouth", -31, 12, 27, 38, y, 15.0, "Хрущёвка · 5 эт.", arches=[(-5, -1)], tint=KHR_TINT, front="N")
so.box("Dovecote", -28, -24, 9, 13, y, 5.0, "garage", "Голубятня")
so.box("Sheds", -18, 4, 15, 18, y, 2.5, "garage", "Сараи")
so.box("Dryer", -12, -8, 10.95, 11.05, y, 2.0, "prop", "Сушилка")
so.box("Dryer", -2, 2, 22.95, 23.05, y, 2.0, "prop")
so.car(6, 10, y, 0)
so.drift(-20, 24, y, 6, 2, 1.4)
so.car(16, 15, y, 0)
so.drift(18.5, 30, y, 3, 6, 1.4)   # сбоку от прохода, не загораживает лесенку через трубы
so.tree(8, -8, y)
for x, z, on in ((-25, -7, True), (-10, 20, True), (15, 0, False)):
    so.lamp(x, z, y, on=on)
so.write("scenes/district/z4_south_yards.tscn")

# =====================================================================================================
# 5. ХРУЩЁВКИ У ПРОЕЗДА, КОТЕЛЬНАЯ (0) + ТЕПЛОТРАССА
# =====================================================================================================
b = Scene("BoilerHouse")
y = SOUTH
b.bld("Khr1", 29, 57, -6, 5, y, 15.0, "Хрущёвка · 5 эт.", arches=[(41, 45)], tint=KHR_TINT)
b.box("ShellRow", 31, 55, 8, 11, y, 2.2, "garage", "Гаражи-«ракушки»")
b.bld("Khr2", 29, 57, 16, 27, y, 15.0, "Хрущёвка · 5 эт.", tint=KHR_TINT, front="N")
b.car(35, 33, y, 90)
b.drift(48, 31, y, 6, 2, 1.3)
b.line_z("Fence", 60, -12, 41, y, 2.5, "fence", gaps=[(18, 24)], thick=0.3, label="Бетонный забор котельной")
b.line_x("Fence", -12, 60, 100, y, 2.5, "fence", thick=0.3)
b.line_x("Fence", 41, 60, 100, y, 2.5, "fence", thick=0.3)
b.box("Boiler", 66, 92, -8, 10, y, 10.0, "industrial", "Котельная")
record_building("BoilerHouse", "Boiler", "boiler", 66, 92, -8, 10, y, 10.0, "N")
record_building("BoilerHouse", "Chimney", "chimney", 90, 94, 28, 32, y, 45.0)
b.box("Chimney", 90, 94, 28, 32, y, 45.0, "industrial", "Труба котельной · 45 м")
b.light("ChimneyRed", 92, 44.5, 30, "Color(1, 0.1, 0.05, 1)", 6.0, 18.0)
b.light("ChimneyRed", 92, 30.0, 30, "Color(1, 0.1, 0.05, 1)", 4.0, 12.0)
b.box("Coal", 66, 74, 22, 30, y, 1.6, "road", "Уголь")
b.lamp(63, 15, y)
# теплотрасса: главная нитка вдоль Z = 43 (низко, 1.5 м), П-арка над проездом, две лесенки-перехода
PZ0, PZ1 = 42.3, 43.7
b.box("Pipe", -45, SPINE[0] - 0.6, PZ0, PZ1, y, 1.5, "pipe", "Теплотрасса (можно пройти поверху)")
b.box("Pipe", SPINE[1] + 0.6, 98, PZ0, PZ1, y, 1.5, "pipe")
b.box("PipeEnd", -46, -45, 41.5, 44.5, y, 2.0, "pipe")
b.box("ArchPost", SPINE[0] - 0.6, SPINE[0], PZ0, PZ1, y, 5.7, "pipe")
b.box("ArchPost", SPINE[1], SPINE[1] + 0.6, PZ0, PZ1, y, 5.7, "pipe")
b.box("ArchTop", SPINE[0] - 0.6, SPINE[1] + 0.6, PZ0, PZ1, 4.5, 1.2, "pipe", "П-арка над проездом")
for x in (15.0, 40.0):
    b.box("PipeStepN", x - 0.8, x + 0.8, 38.1, 42.1, y, 1.7, "rail", "Лесенка через трубы" if x < 20 else "", shape="stairs", yaw=180)
    b.box("PipeBridge", x - 0.8, x + 0.8, 42.1, 43.9, 1.5, 0.2, "rail")
    b.box("PipeStepS", x - 0.8, x + 0.8, 43.9, 47.9, y, 1.7, "rail", shape="stairs")
# ответвление на север к школе — на опорах 3,2 м, под ним узкий проход между хрущёвкой и забором котельной
BX0, BX1 = 58.3, 59.7
b.box("PipeBranch", BX0, BX1, -21, PZ0, 3.2, 0.8, "pipe", "Теплотрасса на опорах")
for z in range(-9, 41, 8):
    b.box("PipePost", 58.8, 59.2, z - 0.2, z + 0.2, y, 3.2, "pipe")
b.box("PipeJoint", 58, 60, 41.5, 44.5, y, 4.0, "pipe")
b.write("scenes/district/z5_boiler.tscn")

# =====================================================================================================
# 6. ГАРАЖНЫЙ КООПЕРАТИВ: на каждой террасе два ряда гаражей и проулок 5 м между ними
# =====================================================================================================
g = Scene("Garages")
SEGS = ((-98, -62), (-59, -23), (-20, 17), (29, 62), (65, 98))
for k, (z, lo) in enumerate(GBANDS):
    for j, (a, bb) in enumerate(SEGS):
        g.box("GarageRow", a, bb, z, z + 6, lo, 2.5, "garage", "Гаражи · по крышам можно пройти" if k == 0 and j == 2 else "")
        g.box("GarageRow", a, bb, z + 11, z + 17, lo, 2.5, "garage", "Гаражи" if j == 2 else "")
g.box("Guardhouse", 27, 30, 44, 46.8, SOUTH, 2.6, "prop", "Сторожка, шлагбаум")
g.box("Barrier", SPINE[0], SPINE[1], 46.4, 46.6, SOUTH + 0.9, 0.12, "rail", solid=False)
g.light("GuardBulb", 28.5, 2.4, 43.5, "Color(1, 0.85, 0.6, 1)", 1.0, 8.0)
g.drift(23, 98.5, G3, 6, 5, 3.0)
g.box("Blockage", SPINE[0], SPINE[1], 95.8, 96, G3, 0.1, "boundary", "Завал: машины + сугроб", solid=False)
g.car(22, 93, G3, 40)
for x, z, lo in ((-40, 55.5, G1), (50, 55.5, G1), (-80, 73.5, G2), (10, 73.5, G2), (-5, 91.5, G3), (80, 91.5, G3)):
    g.drift(x, z, lo, 5, 2, 1.3)
for x, z, lo in ((-75, 55.5, G1), (75, 73.5, G2), (-40, 91.5, G3)):
    g.car(x, z, lo, 90)
g.write("scenes/district/z6_garages.tscn")

# =====================================================================================================
# 7. СТРОЙКА (0): стройгородок из бытовок и штабелей, котлован, каркас недостроя, кран
# =====================================================================================================
n = Scene("Wasteland")
y = SOUTH
SL = 0.3
def slab(x0, x1, z0, z1, top, label=""):
    n.box("Slab", x0, x1, z0, z1, top - SL, SL, "construction", label)
# каркас X −74…−47, Z 30…43: 4 перекрытия, 3 доступных этажа, марши без стен
for top, holes in ((3, "a"), (6, "b"), (9, "a")):
    slab(-74, -47, 30, 36, top)
    if holes == "a":
        slab(-70, -47, 36, 43, top)
    else:
        slab(-74, -52, 36, 43, top)
        slab(-49, -47, 36, 43, top)
slab(-74, -47, 30, 43, 12, "Недострой · 3 этажа доступны")
n.box("Flight", -73, -70, 36, 41, 0, 3, "construction", "Лестница", shape="stairs")
n.box("Flight", -52, -49, 36, 41, 3, 3, "construction", shape="stairs")
n.box("Flight", -73, -70, 36, 41, 6, 3, "construction", shape="stairs")
for x in (-73.5, -65, -56, -47.5):
    for z in (30.5, 42.5):
        n.box("Column", x - 0.25, x + 0.25, z - 0.25, z + 0.25, y, 11.7, "construction")
n.box("CraneTower", -62, -60, 20, 22, y, 35.0, "construction", "Башенный кран")
n.box("CraneJib", -85, -40, 20.5, 21.5, 35.0, 1.5, "construction", solid=False)
n.box("CraneCab", -64, -60, 19, 23, 33.0, 2.0, "construction", solid=False)
n.light("CraneLamp", -50, 34, 21, "Color(1, 0.85, 0.35, 1)", 6.0, 40.0)
# стройгородок: два ряда бытовок и штабели плит — проходы 3–4,5 м
for x0 in (-98, -89, -80, -71):
    n.box("Cabin", x0, x0 + 6, -12, -9.5, y, 2.6, "garage", "Бытовки" if x0 == -98 else "", tint="Color(0.36, 0.42, 0.3, 1)")
for x0 in (-94, -85, -76, -67):
    n.box("Cabin", x0, x0 + 6, -5, -2.5, y, 2.6, "garage", tint="Color(0.36, 0.42, 0.3, 1)")
for x0, x1, z0, hh in ((-98, -92, 3, 1.2), (-88, -82, 3, 1.8), (-76, -70, 3, 1.2), (-95, -89, 8, 2.0), (-70, -64, 8, 1.4)):
    n.box("Slabs", x0, x1, z0, z0 + 1.6, y, hh, "prop", "Плиты" if x0 == -88 else "")
n.line_z("BuildFence", -46, -2, 41, y, 2.5, "fence", gaps=[(15, 19)], thick=0.2, label="Стройзабор")
n.drift(-60, 10, y, 4, 2, 1.3)
n.drift(-75, 26, y, 3, 5, 1.4)
n.lamp(-80, -7.5, y)
n.write("scenes/district/z7_wasteland.tscn")

# =====================================================================================================
# КОРЕНЬ: district.tscn
# =====================================================================================================
ZONES = ["terrain", "z1_prospect", "z2_home_yard", "z3_school", "z4_south_yards", "z5_boiler", "z6_garages",
         "z7_wasteland", "z8_west_yard"]
# (x, y, z, yaw): yaw 0 — лицом на север, 180 — на юг, 90 — на запад, −90 — на восток
TELEPORTS = [(-5, HUB, -55, 180), (15, PROSPECT, -82, 0), (57, HUB, -35, 0), (-10, SOUTH, 22, 180),
             (64, SOUTH, 21, -90), (0, G1, 55.5, 90), (-70, SOUTH, 1.5, 180), (-81, HUB, -48, 0)]

ext = ['[ext_resource type="Script" path="res://scripts/levels/district.gd" id="lvl"]',
       '[ext_resource type="PackedScene" path="res://scenes/characters/player.tscn" id="player"]',
       '[ext_resource type="Shader" path="res://shaders/city_night_sky.gdshader" id="sky"]',
       '[ext_resource type="Shader" path="res://shaders/ps2_post.gdshader" id="post"]']
for z in ZONES:
    ext.append('[ext_resource type="PackedScene" path="res://scenes/district/%s.tscn" id="%s"]' % (z, z))

SUBS = '''[sub_resource type="ShaderMaterial" id="sky_mat"]
shader = ExtResource("sky")
shader_parameter/zenith_color = Color(0.012, 0.016, 0.03, 1)
shader_parameter/mid_color = Color(0.07, 0.065, 0.07, 1)
shader_parameter/horizon_color = Color(0.42, 0.25, 0.14, 1)
shader_parameter/ground_color = Color(0.05, 0.04, 0.035, 1)
shader_parameter/glow_height = 0.28
shader_parameter/glow_energy = 1.3
shader_parameter/cloud_amount = 0.6
shader_parameter/cloud_speed = 0.004

[sub_resource type="Sky" id="sky_res"]
sky_material = SubResource("sky_mat")
radiance_size = 0

[sub_resource type="Environment" id="env"]
background_mode = 2
background_color = Color(0.015, 0.02, 0.035, 1)
sky = SubResource("sky_res")
ambient_light_source = 2
ambient_light_color = Color(0.3, 0.42, 0.6, 1)
ambient_light_energy = 0.55
tonemap_mode = 2
tonemap_exposure = 1.15
glow_enabled = true
glow_intensity = 1.3
glow_strength = 1.2
glow_bloom = 0.08
glow_hdr_threshold = 0.75
fog_enabled = true
fog_light_color = Color(0.13, 0.1, 0.085, 1)
fog_density = 0.012
fog_aerial_perspective = 0.75
fog_sky_affect = 0.2
volumetric_fog_enabled = true
volumetric_fog_density = 0.018
volumetric_fog_albedo = Color(0.85, 0.85, 0.9, 1)
volumetric_fog_anisotropy = 0.55
volumetric_fog_length = 60.0
volumetric_fog_ambient_inject = 0.12
volumetric_fog_sky_affect = 0.0

[sub_resource type="ParticleProcessMaterial" id="pm_snow"]
emission_shape = 3
emission_box_extents = Vector3(35, 1, 35)
direction = Vector3(0, -1, 0)
spread = 20.0
initial_velocity_min = 0.6
initial_velocity_max = 1.2
gravity = Vector3(0.35, -0.5, 0.1)
turbulence_enabled = true
turbulence_noise_strength = 0.4
turbulence_noise_scale = 6.0

[sub_resource type="StandardMaterial3D" id="mat_flake"]
albedo_color = Color(0.95, 0.97, 1, 1)
billboard_mode = 3
particles_anim_h_frames = 1
particles_anim_v_frames = 1
particles_anim_loop = false

[sub_resource type="QuadMesh" id="mesh_flake"]
material = SubResource("mat_flake")
size = Vector2(0.05, 0.05)

[sub_resource type="ShaderMaterial" id="mat_post"]
shader = ExtResource("post")
shader_parameter/blur_px = 0.55
shader_parameter/color_levels = 32.0
shader_parameter/dither_strength = 1.0
shader_parameter/black_crush = 0.06
shader_parameter/s_curve = 0.55
shader_parameter/saturation = 0.78
shader_parameter/exposure = 1.1
shader_parameter/shadow_tint = Color(0.03, 0.05, 0.09, 1)
shader_parameter/highlight_tint = Color(1, 0.94, 0.86, 1)
shader_parameter/halo = 0.25
shader_parameter/grain = 0.045
shader_parameter/vignette = 0.55
'''

nodes = ['''[node name="District" type="Node3D"]
script = ExtResource("lvl")
bake_navigation = false

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("env")

[node name="Moon" type="DirectionalLight3D" parent="."]
transform = Transform3D(0.894, -0.293, 0.338, 0, 0.756, 0.655, -0.447, -0.586, 0.676, 0, 60, 0)
light_color = Color(0.5, 0.65, 0.95, 1)
light_energy = 0.35
shadow_enabled = true
directional_shadow_max_distance = 80.0

[node name="Snowfall" type="GPUParticles3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, -5, 21, -55)
amount = 6000
lifetime = 16.0
preprocess = 16.0
visibility_aabb = AABB(-40, -25, -40, 80, 30, 80)
process_material = SubResource("pm_snow")
draw_pass_1 = SubResource("mesh_flake")

[node name="PS2Post" type="CanvasLayer" parent="."]
layer = 10

[node name="Filter" type="ColorRect" parent="PS2Post"]
material = SubResource("mat_post")
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
mouse_filter = 2
''']
for z in ZONES:
    node_name = "Terrain" if z == "terrain" else "".join(w.capitalize() for w in z.split("_")[1:])
    nodes.append('[node name="%s" parent="." instance=ExtResource("%s")]\n' % (node_name, z))
x0, y0, z0, yaw0 = TELEPORTS[0]
nodes.append('[node name="Player" parent="." instance=ExtResource("player")]\ntransform = %s\n' % xform(x0, y0, z0, yaw0))
nodes.append('[node name="Teleports" type="Node3D" parent="."]\n')
for i, (x, yy, z, yaw) in enumerate(TELEPORTS):
    nodes.append('[node name="Tp%d" type="Marker3D" parent="Teleports"]\ntransform = %s\n' % (i + 1, xform(x, yy + 0.1, z, yaw)))

out = "[gd_scene format=3]\n\n" + "\n".join(ext) + "\n\n" + SUBS + "\n" + "\n".join(nodes)
if WRITE:
    open(os.path.join(ROOT, "scenes", "levels", "district.tscn"), "w", encoding="utf-8", newline="\n").write(out)
    print("written scenes/levels/district.tscn")

# =====================================================================================================
# КАРТА docs/city_map.svg — рисуется из тех же данных, что и сцены (1 единица = 1 метр, север вверху)
# =====================================================================================================
MAP_COL = {"building": "#5d6474", "school": "#b59a4a", "garage": "#6e5844", "industrial": "#8a4a3a",
           "construction": "#a07a3a", "prop": "#8a8a8a", "car": "#5a6a8a", "tree": "#3e5a3a", "fence": "#3a3f46",
           "boundary": "#b23b3b", "rail": "#9a9a9a", "snow": "#eef2f7", "pipe": "#d98a2b", "road": "#4a4d55"}
LEVEL_COL = {6.0: "#ece7dc", 3.0: "#d9d4c8", 2.0: "#8f8a80", 0.0: "#c3beb2", -2.5: "#b3ada1", -5.0: "#a39d91", -7.5: "#938d81"}


def svg_color(tint):
    import re as _re
    m = _re.match(r"Color\(([\d.]+), ([\d.]+), ([\d.]+)", tint or "")
    return "#%02x%02x%02x" % tuple(int(float(v) * 255) for v in m.groups()) if m else None


svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-112 -118 345 232" width="1380" height="928" font-family="Arial, sans-serif">',
       '<rect x="-112" y="-118" width="345" height="232" fill="#1c2130"/>']
labels = []
for x0, x1, z0, z1, top, kind, label, tint, shape in FLAT:
    if kind == "ground":
        if x1 - x0 > 300:
            continue
        col = LEVEL_COL.get(top, "#857f78") if top > -20 else None
        if top <= PIT + 0.01 and tint == PIT_TINT:
            col = "#857f78"
        if shape in ("stairs", "ramp"):
            col = "#8c8578"
    else:
        col = MAP_COL.get(kind, "#777")
        if kind in ("building", "garage") and tint:
            col = svg_color(tint) or col
    if not col:
        continue
    extra = ' stroke="#222" stroke-width="0.15"' if kind not in ("ground", "road", "snow") else ""
    svg.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"%s/>' % (f(x0), f(z0), f(x1 - x0), f(z1 - z0), col, extra))
    if label and kind in ("building", "school", "industrial", "construction", "garage") and label != "Арка":
        labels.append((x0, x1, z0, z1, label))
for x0, x1, z0, z1, label in labels:
    vertical = (z1 - z0) > (x1 - x0) * 1.5
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    rot = ' transform="rotate(-90 %s %s)"' % (f(cx), f(cz)) if vertical else ""
    svg.append('<text x="%s" y="%s" font-size="2.6" fill="#fff" text-anchor="middle" dominant-baseline="middle"%s>%s</text>'
               % (f(cx), f(cz), rot, label.replace("«", "").replace("»", "")))
ZONE_TITLES = [(0, -90.5, "1. ПРОСПЕКТ (+6)"), (-12, -50, "2. ДВОР ЮРЧИКА (+3)"), (-81, -46, "ЗАПАДНЫЙ ДВОР"),
               (57, -38, "3. ШКОЛА (+3)"), (-10, 21, "4. ЮЖНЫЕ ДВОРЫ (0)"), (80, 36, "5. КОТЕЛЬНАЯ (0)"),
               (-40, 74, "6. ГАРАЖИ (−2,5 / −5 / −7,5)"), (-80, 8, "7. СТРОЙКА (0)")]
for x, z, tt in ZONE_TITLES:
    svg.append('<text x="%s" y="%s" font-size="4" font-weight="bold" fill="#111" stroke="#fff" stroke-width="0.6" '
               'paint-order="stroke" text-anchor="middle">%s</text>' % (f(x), f(z), tt))
for i, (x, yy, z, _) in enumerate(TELEPORTS):
    svg.append('<circle cx="%s" cy="%s" r="2" fill="#ff7a1a" stroke="#fff" stroke-width="0.4"/>'
               '<text x="%s" y="%s" font-size="2.6" fill="#fff" text-anchor="middle" dominant-baseline="middle">F%d</text>'
               % (f(x), f(z), f(x), f(z + 0.1), i + 1))
LEG = [("#ece7dc", "+6 м — проспект"), ("#d9d4c8", "+3 м — дворы и школа"), ("#c3beb2", "0 м — южная полоса"),
       ("#a39d91", "−2,5…−7,5 м — террасы гаражей"), ("#857f78", "−5 м котлован, +2 м переход"), ("#8c8578", "лестницы и пандусы"),
       ("#5d6474", "панельные дома (9 и 16 эт.)"), ("#80695f", "хрущёвки (5 эт.)"), ("#6e5844", "гаражи, сараи, ракушки"),
       ("#d98a2b", "теплотрасса"), ("#eef2f7", "сугробы"), ("#5a6a8a", "машины"), ("#b23b3b", "граница района"),
       ("#ff7a1a", "F1–F8 — точки телепорта")]
svg.append('<g transform="translate(112 -108)" font-size="4" fill="#e6e9f0">')
svg.append('<text x="0" y="0" font-size="6" font-weight="bold">Паскот — микрорайон</text>')
svg.append('<text x="0" y="7" font-size="3.4" fill="#9fb0d0">v2, плотная планировка · ~200×215 м · проходы 3–5 м</text>')
svg.append('<text x="0" y="12" font-size="3.4" fill="#9fb0d0">Нарисовано tools/make_district_blockout.py по данным блокаута</text>')
for k, (col, txt) in enumerate(LEG):
    yy = 22 + k * 7
    svg.append('<rect x="0" y="%d" width="7" height="4.5" fill="%s" stroke="#999" stroke-width="0.2"/><text x="10" y="%s">%s</text>'
               % (yy - 3.5, col, f(yy + 0.5), txt))
svg.append('<text x="0" y="%d" font-size="3.4" fill="#9fb0d0">Арки — проходы сквозь первый этаж домов (подпись «Арка» в игре).</text>' % (22 + len(LEG) * 7 + 4))
svg.append('<text x="0" y="%d" font-size="3.4" fill="#9fb0d0">Север — вверху. 10 м ≈ 6 с шагом, ≈ 2 с бегом.</text>' % (22 + len(LEG) * 7 + 10))
svg.append('</g></svg>')
if WRITE:
    open(os.path.join(ROOT, "docs", "city_map.svg"), "w", encoding="utf-8", newline="\n").write("\n".join(svg) + "\n")
    print("written docs/city_map.svg")
import json
open(os.path.join(ROOT, "tools", "district_buildings.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(BUILDINGS, ensure_ascii=False, indent=1) + "\n")
print("written tools/district_buildings.json -", len(BUILDINGS), "buildings")
open(os.path.join(ROOT, "tools", "district_blocks.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(BLOCKS, ensure_ascii=False, indent=0) + "\n")
print("written tools/district_blocks.json -", len(BLOCKS), "blocks")

# =====================================================================================================
# ПРОВЕРКИ
# =====================================================================================================
EPS = 0.05
problems = 0
for i in range(len(SOLIDS)):
    a = SOLIDS[i]
    for j in range(i + 1, len(SOLIDS)):
        c = SOLIDS[j]
        if (a[0] < c[1] - EPS and c[0] < a[1] - EPS and a[2] < c[3] - EPS and c[2] < a[3] - EPS
                and a[4] < c[5] - EPS and c[4] < a[5] - EPS):
            if {a[6], c[6]} <= {"pipe", "fence", "rail"} and "pipe" in {a[6], c[6]} or {a[6], c[6]} in ({"construction"}, {"fence"}):
                continue          # трубы проходят сквозь заборы и перила; колонны недостроя — сквозь перекрытия
            print("OVERLAP:", a[7], "<->", c[7])
            problems += 1
for i, (x, yy, z, _) in enumerate(TELEPORTS):
    for a in SOLIDS:
        if a[0] - 0.3 < x < a[1] + 0.3 and a[4] - 0.3 < z < a[5] + 0.3 and a[2] < yy + 1.8 and yy + 0.1 < a[3]:
            print("TELEPORT %d inside %s" % (i + 1, a[7]))
            problems += 1
print("checks:", len(SOLIDS), "solid blocks,", problems, "problems")
sys.exit(1 if problems else 0)
