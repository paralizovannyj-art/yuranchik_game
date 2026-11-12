# -*- coding: utf-8 -*-
# Собирает БЛОКАУТ микрорайона «Паскот» (этап A в docs/CITY_PLAN.md) из серых коробок (scripts/tools/blockout_box.gd):
#   scenes/levels/district.tscn       — корень: окружение, игрок, точки телепорта, подсцены зон
#   scenes/district/*.tscn            — рельеф и зоны
#
# ВНИМАНИЕ: запускается ОДИН раз (и пока блокаут не принят автором). После приёмки источник правды — сами .tscn,
# правки делаются в редакторе мышью; повторный запуск затрёт ручные правки.
#   python tools/make_district_blockout.py
#
# Оси: X — восток, −Z — север, Y — вверх, метры. Центр района — (0, 0, 0).
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# высоты земли
PROSPECT, HUB, SOUTH, G1, G2, G3, PIT = 6.0, 3.0, 0.0, -2.5, -5.0, -7.5, -5.0
BOTTOM = -20.0
TINT = {PROSPECT: "Color(0.66, 0.64, 0.6, 1)", HUB: "Color(0.6, 0.58, 0.54, 1)", SOUTH: "Color(0.53, 0.51, 0.47, 1)",
        G1: "Color(0.48, 0.46, 0.42, 1)", G2: "Color(0.43, 0.41, 0.38, 1)", G3: "Color(0.38, 0.36, 0.33, 1)"}
PIT_TINT = "Color(0.34, 0.31, 0.28, 1)"


def f(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def xform(x, y, z, yaw=0.0):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    # в .tscn базис записывается по строкам: поворот на yaw против часовой (если смотреть сверху)
    return "Transform3D(%s, 0, %s, 0, 1, 0, %s, 0, %s, %s, %s, %s)" % (f(c), f(s), f(-s), f(c), f(x), f(y), f(z))


class Scene:
    def __init__(self, root):
        self.root, self.lines, self.names = root, [], {}

    def uniq(self, name):
        n = self.names.get(name, 0)
        self.names[name] = n + 1
        return name if n == 0 else "%s%d" % (name, n + 1)

    def boxc(self, name, cx, cz, y, sx, sy, sz, kind, label="", shape="box", yaw=0.0, tint=None, solid=True, parent="."):
        name = self.uniq(name)
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

    def box(self, name, x0, x1, z0, z1, y, h, kind, label="", shape="box", yaw=0.0, tint=None, solid=True):
        """Прямоугольник на карте (X x0..x1, Z z0..z1), низ на высоте y, высота h. yaw 0/180 — как есть, ±90 — длина вдоль Z."""
        sx, sz = x1 - x0, z1 - z0
        if abs(abs(yaw) - 90) < 1e-6:
            sx, sz = sz, sx
        self.boxc(name, (x0 + x1) / 2, (z0 + z1) / 2, y, sx, h, sz, kind, label, shape, yaw, tint, solid)

    def ground(self, name, x0, x1, z0, z1, top, tint=None, label=""):
        self.box(name, x0, x1, z0, z1, BOTTOM, top - BOTTOM, "ground", label, tint=tint or TINT[top])

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

    def lamp(self, x, z, y, color="Color(1, 0.62, 0.3, 1)", on=True, energy=2.2):
        self.box("LampPole", x - 0.12, x + 0.12, z - 0.12, z + 0.12, y, 7.5, "prop")
        if on:
            self.light("LampLight", x, y + 7.2, z, color, energy, 15.0)

    def car(self, x, z, y, yaw=0.0, label=""):
        self.boxc("Car", x, z, y, 1.7, 1.45, 4.2, "car", label, yaw=yaw)

    def drift(self, x, z, y, sx=4.0, sz=2.0, h=1.2, yaw=0.0):
        self.boxc("Drift", x, z, y, sx, h, sz, "snow", yaw=yaw)

    def tree(self, x, z, y):
        self.boxc("Tree", x, z, y, 0.5, 7.0, 0.5, "tree")

    def write(self, path):
        head = '[gd_scene format=3]\n\n[ext_resource type="Script" path="res://scripts/tools/blockout_box.gd" id="bb"]\n\n'
        body = '[node name="%s" type="Node3D"]\n\n' % self.root + "\n".join(self.lines)
        full = os.path.join(ROOT, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8", newline="\n").write(head + body)
        print("written", path, "-", len(self.lines), "nodes")


# =====================================================================================================
# РЕЛЬЕФ: земля всех уровней, переходы между ними, перила, подземный переход, границы
# =====================================================================================================
t = Scene("Terrain")
# подземный переход (X TX0..TX1): портал в подпорной стенке со стороны двора (+3 → пол +2),
# тоннель под проспектом, лестница наверх на северный тротуар (+6)
TX0, TX1 = -70.0, -64.0
t.ground("Prospect", -150, TX0, -150, -112, PROSPECT)
t.ground("Prospect", TX1, 150, -150, -112, PROSPECT)
t.ground("TunnelCapN", TX0, TX1, -150, -147, PROSPECT)
t.ground("TunnelFloor", TX0, TX1, -147, -106, 2.0, tint=PIT_TINT, label="Подземный переход")
t.box("TunnelRoof", TX0, TX1, -140, -112, 5.4, 0.6, "ground", tint=TINT[PROSPECT])
t.box("TunnelStairsN", TX0, TX1, -147, -140, 2.0, 4.0, "ground", shape="stairs", tint=TINT[PROSPECT])
t.box("TunnelRampS", TX0, TX1, -112, -106, 2.0, 1.0, "ground", shape="ramp", yaw=180, tint=TINT[HUB])
t.line_z("TunnelRail", TX0 + 0.1, -147, -140, PROSPECT, 1.0, "rail")
t.line_z("TunnelRail", TX1 - 0.1, -147, -140, PROSPECT, 1.0, "rail")
t.line_x("TunnelRail", -139.9, TX0, TX1, PROSPECT, 1.0, "rail")

# +3: двор Юрчика, западный двор, школа
t.ground("Hub", -150, TX0, -112, -20, HUB)
t.ground("Hub", TX1, 150, -112, -20, HUB)
t.ground("Hub", TX0, TX1, -106, -20, HUB)
# 0: южные дворы, котельная; пустырь с котлованом
t.ground("South", -60, 150, -20, 60, SOUTH)
t.ground("Wasteland", -150, -60, -20, 25, SOUTH)
t.ground("Wasteland", -150, -60, 75, 145, SOUTH)
t.ground("Wasteland", -150, -140, 25, 75, SOUTH)
t.ground("Wasteland", -95, -60, 25, 75, SOUTH)
t.ground("Pit", -140, -95, 25, 75, PIT, tint=PIT_TINT, label="Котлован −5 м")
t.box("PitRamp", -101, -95, 45, 75, PIT, 5.0, "ground", shape="ramp", yaw=180, tint=PIT_TINT)
# террасы гаражей
t.ground("Garages1", -60, 150, 60, 85, G1)
t.ground("Garages2", -60, 150, 85, 110, G2)
t.ground("Garages3", -60, 150, 110, 145, G3)

# переходы между уровнями
t.box("StairsProspect", 25, 33, -112, -106.5, HUB, 3.0, "ground", "Лестница на проспект", shape="stairs", tint=TINT[HUB])
t.box("RampProspect", 35, 45, -112, -100, HUB, 3.0, "road", shape="ramp")
t.box("StairsWide", -26, -14, -20, -14.5, SOUTH, 3.0, "ground", "Широкая лестница", shape="stairs", tint=TINT[SOUTH])
t.box("StairsSchool", 84, 90, -20, -14.5, SOUTH, 3.0, "ground", shape="stairs", tint=TINT[SOUTH])
t.box("StairsWest", -110, -104, -20, -14.5, SOUTH, 3.0, "ground", shape="stairs", tint=TINT[SOUTH])
t.box("RampSouth", 35, 45, -20, -8, SOUTH, 3.0, "road", shape="ramp")
for z, lo in ((60, G1), (85, G2), (110, G3)):
    t.box("RampGarages", 35, 45, z, z + 10, lo, 2.5, "road", shape="ramp")
    t.box("StairsGarages", -59.5, -56.5, z, z + 4.5, lo, 2.5, "ground", shape="stairs", tint=TINT[lo])

# перила вдоль подпорных стенок
t.line_x("Parapet", -112.1, -150, 150, PROSPECT, 1.0, "rail", gaps=[(25, 33), (35, 45)])
t.line_x("Parapet", -20.1, -150, 150, HUB, 1.0, "rail", gaps=[(-26, -14), (84, 90), (-110, -104), (35, 45)])
t.line_z("Parapet", -60.1, 60, 145, SOUTH, 1.0, "rail")
# дорога-проезд (полоса на земле, без коллизии)
for z0, z1, y in ((-100, -20, HUB), (-8, 60, SOUTH), (70, 85, G1), (95, 110, G2), (120, 145, G3)):
    t.box("Road", 35, 45, z0, z1, y, 0.03, "road", solid=False)

# границы района (позже — дома, заборы и завалы; см. раздел 1 плана)
t.box("NorthFacades", -150, 150, -172, -150, PROSPECT, 27.0, "building", "Дома северной стороны проспекта (стена)")
t.box("Edge", -151, -150, -150, -112, PROSPECT, 5.0, "boundary", "Завал: трамвай поперёк + машины")
t.box("Edge", 150, 151, -150, -112, PROSPECT, 5.0, "boundary", "Завал: маршрутка + фура")
t.box("Edge", -151, -150, -112, -20, HUB, 3.5, "boundary", "Забор / торцы домов")
t.box("Edge", -151, -150, -20, 145, SOUTH, 3.5, "boundary", "Стройзабор")
t.box("Edge", 150, 151, -112, -20, HUB, 3.5, "boundary", "Забор")
t.box("Edge", 150, 151, -20, 60, SOUTH, 3.5, "boundary", "Бетонный забор «ёлочка»")
t.box("Edge", 150, 151, 60, 145, G3, 11.0, "boundary", "Забор")
t.box("Edge", -151, -60, 145, 146, SOUTH, 3.5, "boundary", "Стройзабор")
t.box("Edge", -60, 151, 145, 146, G3, 3.5, "boundary", "Забор над обрывом балки")
# земля за краем (без коллизии): на юге — провал балки
t.box("OuterW", -700, -151, -700, 700, BOTTOM, -BOTTOM, "ground", solid=False, tint=TINT[SOUTH])
t.box("OuterE", 151, 700, -700, 700, BOTTOM, -BOTTOM, "ground", solid=False, tint=TINT[SOUTH])
t.box("OuterN", -151, 151, -700, -172, BOTTOM, -BOTTOM, "ground", solid=False, tint=TINT[SOUTH])
t.box("OuterS", -151, 151, 146, 700, BOTTOM, -12 - BOTTOM, "ground", solid=False, tint=TINT[G3])
t.write("scenes/district/terrain.tscn")

# =====================================================================================================
# 1. ПРОСПЕКТ (+6)
# =====================================================================================================
p = Scene("Prospect")
y = PROSPECT
p.box("Roadway", -150, 150, -142, -118, y, 0.03, "road", solid=False)
p.box("TramStrip", -150, 150, -133, -127, y, 0.04, "snow", solid=False)
for zr in (-131.5, -128.5):
    p.box("TramRail", -150, 150, zr - 0.05, zr + 0.05, y, 0.12, "rail", solid=False)
for x in range(-137, 150, 25):
    p.box("TramPole", x - 0.18, x + 0.18, -130.2, -129.8, y, 9.0, "prop", "Опора трамвая" if x == -12 else "")
p.box("StopWall", -10, 10, -116.5, -116.3, y, 2.6, "prop")
p.box("StopRoof", -10, 10, -119, -116.3, y + 2.6, 0.2, "prop", "Остановка трамвая", solid=False)
for i, (x0, col) in enumerate(((-26, "Color(0.7, 0.3, 0.2, 1)"), (-20, "Color(0.75, 0.6, 0.25, 1)"),
                               (12, "Color(0.3, 0.55, 0.35, 1)"), (18, "Color(0.7, 0.3, 0.2, 1)"))):
    p.box("Kiosk", x0, x0 + 4, -116, -113.5, y, 2.6, "prop", "Ларьки" if i == 0 else "", tint=col)
    p.light("KioskLight", x0 + 2, y + 2.0, -112.8, "Color(1, 0.75, 0.5, 1)", 1.2, 7.0)
p.box("TunnelSign", -70.5, -69.9, -148.5, -147.9, y, 2.4, "prop", "Выход из перехода")
# завалы на концах проспекта
p.boxc("Tram", -140, -131, y, 2.6, 3.6, 15.0, "car", "Трамвай", yaw=70)
p.car(-133, -122, y, 20)
p.car(-131, -139, y, -35)
p.drift(-146, -116, y, 6, 3, 1.6)
p.drift(-146, -146, y, 6, 3, 1.6)
p.boxc("Minibus", 138, -137, y, 2.2, 2.6, 6.0, "car", "Маршрутка", yaw=30)
p.boxc("Truck", 142, -124, y, 2.5, 3.8, 13.0, "car", "Фура", yaw=-15)
p.car(131, -131, y, 80)
# машины у тротуара и сугробы
for x in (-95, -70, 85, 110):
    p.car(x, -119.5, y, 90)
for x in (-60, -30, 30, 90, 120):
    p.drift(x, -118.6, y, 5, 1.4, 1.0)
for x in range(-140, 150, 30):
    p.lamp(x, -113, y, on=(x // 30) % 2 == 0)
p.write("scenes/district/z1_prospect.tscn")

# =====================================================================================================
# 2. ДВОР ЮРЧИКА (+3)
# =====================================================================================================
h = Scene("HomeYard")
y = HUB
h.box("HomeBuilding", -45, -2, -104, -92, y, 26.0, "building", "Дом Юрчика · 9 эт., 4 подъезда")
for i in range(4):
    x = -45 + 43 * (i + 0.5) / 4
    h.box("Porch", x - 1.3, x + 1.3, -92, -90.4, y, 0.3, "prop", "Подъезд Юрчика" if i == 1 else "")
    h.box("Canopy", x - 1.5, x + 1.5, -92, -90.2, y + 2.6, 0.15, "prop", solid=False)
    if i == 1:
        h.light("EntranceLight", x, y + 2.4, -90.6, "Color(1, 0.75, 0.45, 1)", 1.5, 8.0)
h.box("WestBuilding", -60, -48, -84, -32, y, 26.0, "building", "9 эт.")
h.box("Slide", -31, -29.5, -72, -68, y, 2.0, "prop", "Детплощадка")
h.box("Swing", -22, -19, -73, -72, y, 2.2, "prop")
h.box("Carousel", -25, -23, -63, -61, y, 0.6, "prop")
h.box("Sandbox", -18, -15, -64, -61, y, 0.3, "prop")
h.box("Turnik", -7, -5, -56.1, -55.9, y, 2.4, "prop")
for x, z in ((-36, -80), (-10, -80), (-28, -52)):
    h.box("Bench", x - 0.9, x + 0.9, z - 0.25, z + 0.25, y, 0.5, "prop")
h.box("Kiosk", 8, 12, -64, -61, y, 2.6, "prop", "Ларёк «Продукты»", tint="Color(0.7, 0.3, 0.2, 1)")
h.light("KioskLight", 10, y + 2.0, -60.3, "Color(1, 0.75, 0.5, 1)", 1.3, 7.0)
h.box("Transformer", 22, 27, -100, -96, y, 3.0, "industrial", "Трансформаторная")
h.box("Bins", 14, 17, -89, -88, y, 1.2, "prop")
for x, z in ((-40, -86), (5, -86), (-38, -40), (-5, -45), (20, -40), (28, -75)):
    h.tree(x, z, y)
for x, z, yaw in ((-12, -88.5, 90), (-3, -88.5, 90), (2, -70, 0)):
    h.car(x, z, y, yaw)
for x, z, sx, sz, hh in ((-44, -90, 5, 2, 1.3), (0, -90.5, 4, 1.6, 1.1), (-46, -60, 2.2, 6, 1.4), (15, -50, 5, 2, 1.0)):
    h.drift(x, z, y, sx, sz, hh)
for x, z, on in ((-20, -84, True), (-35, -60, False), (0, -60, True), (15, -30, False), (-25, -30, True)):
    h.lamp(x, z, y, on=on)
h.write("scenes/district/z2_home_yard.tscn")

# =====================================================================================================
# ЗАПАДНЫЙ ДВОР (+3)
# =====================================================================================================
w = Scene("WestYard")
y = HUB
w.box("Tower", -135, -117, -100, -82, y, 46.0, "building", "Свечка · 16 эт.")
w.box("Tower", -105, -87, -70, -52, y, 46.0, "building", "Свечка · 16 эт.")
w.box("ParkingLot", -145, -113, -65, -41, y, 0.03, "road", "Стоянка", solid=False)
for i in range(5):
    for j, z in enumerate((-61, -45)):
        if (i + j) % 3 != 2:
            w.car(-141 + i * 6, z, y, 0)
for x in (-82, -77, -72):
    w.box("ShellGarage", x - 1.5, x + 1.5, -38, -33, y, 2.2, "garage", "Гаражи-«ракушки»" if x == -82 else "")
for x, z in ((-140, -75), (-110, -95), (-120, -30), (-90, -30), (-75, -90)):
    w.tree(x, z, y)
w.drift(-128, -38, y, 6, 2.5, 1.5)
w.drift(-100, -48, y, 3, 2.2, 1.2)
for x, z, on in ((-125, -70, True), (-95, -40, False), (-80, -60, True)):
    w.lamp(x, z, y, on=on)
w.write("scenes/district/z8_west_yard.tscn")

# =====================================================================================================
# 3. ШКОЛА (+3)
# =====================================================================================================
s = Scene("School")
y = HUB
s.line_z("Fence", 48, -108, -24, y, 2.2, "fence", gaps=[(-64, -56)], thick=0.15, label="Ворота школы")
s.line_x("Fence", -108, 48, 145, y, 2.2, "fence", thick=0.15)
s.line_z("Fence", 145, -108, -24, y, 2.2, "fence", thick=0.15)
s.line_x("Fence", -24, 48, 145, y, 2.2, "fence", gaps=[(82, 92)], thick=0.15)
s.box("SchoolMain", 60, 120, -102, -90, y, 11.0, "school", "Школа · 3 эт.")
s.box("SchoolWing", 60, 72, -90, -74, y, 11.0, "school")
s.box("SchoolWing", 108, 120, -90, -74, y, 11.0, "school")
s.box("Porch", 86, 94, -90, -88, y, 0.45, "prop", "Крыльцо")
s.box("PorchRoof", 85.5, 94.5, -90, -87.5, y + 3.0, 0.2, "prop", solid=False)
s.box("Field", 63, 131, -64, -32, y, 0.03, "snow", "Стадион", solid=False, tint="Color(0.62, 0.68, 0.58, 1)")
s.boxc("Tribune", 135, -48, y, 28.0, 2.5, 6.0, "prop", "Трибуна", shape="stairs", yaw=-90)
s.box("Obstacles", 120, 135, -78, -70, y, 1.2, "prop", "Турники, полоса препятствий")
s.box("FloodPole", 127.8, 128.2, -66.2, -65.8, y, 14.0, "prop", "Прожектор")
s.light("FloodLight", 127, y + 13.5, -65, "Color(0.82, 0.9, 1, 1)", 4.0, 40.0)
for x in range(55, 145, 12):
    s.tree(x, -105.5, y)
s.drift(70, -40, y, 6, 3, 1.4)
s.drift(100, -28, y, 8, 2, 1.2)
s.write("scenes/district/z3_school.tscn")

# =====================================================================================================
# 4. ЮЖНЫЕ ДВОРЫ (0)
# =====================================================================================================
so = Scene("SouthYards")
y = SOUTH
so.box("Khrushchevka", -45, 15, -6, 5, y, 15.0, "building", "Хрущёвка · 5 эт.", tint="Color(0.5, 0.42, 0.38, 1)")
so.box("Khrushchevka", -30, 30, 22, 33, y, 15.0, "building", "Хрущёвка · 5 эт.", tint="Color(0.5, 0.42, 0.38, 1)")
so.box("Khrushchevka", 50, 90, 4, 15, y, 15.0, "building", "Хрущёвка · 5 эт.", tint="Color(0.5, 0.42, 0.38, 1)")
so.box("Dovecote", -52, -47, 36, 41, y, 5.0, "garage", "Голубятня")
so.box("Sheds", -48, -28, 44, 48, y, 2.5, "garage", "Сараи")
for x, z in ((-10, 12), (5, 14), (-40, 15), (65, 25)):
    so.box("Dryer", x - 2, x + 2, z - 0.05, z + 0.05, y, 2.0, "prop", "Сушилка" if x == -10 else "")
for x, z, yaw in ((22, -10, 90), (-50, 10, 0), (60, -5, 90), (25, 40, 0), (95, 30, 0)):
    so.car(x, z, y, yaw)
for x, z in ((-55, -12), (20, 18), (75, 40), (-15, 40)):
    so.tree(x, z, y)
for x, z, sx, sz, hh in ((-40, 8, 8, 2, 1.4), (10, 36, 6, 2.5, 1.5), (60, 18, 6, 2, 1.2), (-55, 30, 2.5, 8, 1.5)):
    so.drift(x, z, y, sx, sz, hh)
for x, z, on in ((-25, -10, True), (0, 16, False), (25, 15, True), (70, -8, True), (-5, 40, False)):
    so.lamp(x, z, y, on=on)
so.write("scenes/district/z4_south_yards.tscn")

# =====================================================================================================
# 5. КОТЕЛЬНАЯ (0) + ТЕПЛОТРАССА
# =====================================================================================================
b = Scene("BoilerHouse")
y = SOUTH
b.line_z("Fence", 96, -15, 57, y, 2.5, "fence", gaps=[(30, 38)], thick=0.3, label="Бетонный забор котельной")
b.line_x("Fence", -15, 96, 150, y, 2.5, "fence", thick=0.3)
b.line_x("Fence", 57, 96, 150, y, 2.5, "fence", thick=0.3)
b.box("Boiler", 105, 140, -5, 17, y, 10.0, "industrial", "Котельная")
b.box("Chimney", 130, 134, 34, 38, y, 45.0, "industrial", "Труба котельной · 45 м")
b.light("ChimneyRed", 132, 44.5, 36, "Color(1, 0.1, 0.05, 1)", 6.0, 18.0)
b.light("ChimneyRed", 132, 30.0, 36, "Color(1, 0.1, 0.05, 1)", 4.0, 12.0)
b.box("Coal", 107, 117, 28, 36, y, 1.6, "road", "Уголь")
b.lamp(100, 20, y)
# теплотрасса: главная нитка вдоль Z = 52 (низко, 1.5 м), П-арка над проездом
PZ0, PZ1 = 51.3, 52.7
b.box("Pipe", -90, 33.4, PZ0, PZ1, y, 1.5, "pipe", "Теплотрасса (можно пройти поверху)")
b.box("Pipe", 46.6, 105, PZ0, PZ1, y, 1.5, "pipe")
b.box("PipeEnd", -91, -89, 50.5, 53.5, y, 2.0, "pipe")
b.box("ArchPost", 33.4, 34, PZ0, PZ1, y, 5.7, "pipe")
b.box("ArchPost", 46, 46.6, PZ0, PZ1, y, 5.7, "pipe")
b.box("ArchTop", 33.4, 46.6, PZ0, PZ1, 4.5, 1.2, "pipe", "П-арка над проездом")
# переходы-лесенки через трубы
for x in (-75.0, -20.0, 75.0):
    b.box("PipeStepN", x - 0.8, x + 0.8, 46.6, 50.6, y, 1.7, "rail", "Лесенка через трубы" if x == -20 else "", shape="stairs", yaw=180)
    b.box("PipeBridge", x - 0.8, x + 0.8, 50.6, 53.4, 1.5, 0.2, "rail")
    b.box("PipeStepS", x - 0.8, x + 0.8, 53.4, 57.4, y, 1.7, "rail", shape="stairs")
# ответвление на север к школе — поднято на опорах, под ним можно пройти
b.box("PipeBranch", 91.3, 92.7, -26, PZ0, 3.2, 0.8, "pipe", "Теплотрасса на опорах")
for z in range(-14, 51, 8):
    b.box("PipePost", 91.8, 92.2, z - 0.2, z + 0.2, y, 3.2, "pipe")
b.box("PipeJoint", 91, 93, 50.5, 53.5, y, 4.0, "pipe")
b.write("scenes/district/z5_boiler.tscn")

# =====================================================================================================
# 6. ГАРАЖНЫЙ КООПЕРАТИВ (террасы)
# =====================================================================================================
g = Scene("Garages")
for (z0, z1, lo, lab) in ((60, 66, G1, "Гаражи · по крышам можно пройти"), (85, 91, G2, "Гаражи"),
                          (110, 116, G3, "Гаражи"), (132, 138, G3, "")):
    g.box("GarageRow", -55, 30, z0, z1, lo, 2.5, "garage", lab)
    g.box("GarageRow", 50, 145, z0, z1, lo, 2.5, "garage")
g.box("Guardhouse", 46, 50, 53, 57, SOUTH, 2.6, "prop", "Сторожка, шлагбаум")
g.box("Barrier", 35, 45, 57.9, 58.1, SOUTH + 0.9, 0.12, "rail", solid=False)
g.light("GuardBulb", 48, 2.4, 52.6, "Color(1, 0.85, 0.6, 1)", 1.0, 8.0)
g.drift(40, 141.5, G3, 10, 7, 3.0)
g.box("Blockage", 34.5, 45.5, 140, 140.4, G3, 0.1, "boundary", "Завал: машины + сугроб", solid=False)
g.car(37, 135, G3, 40)
g.car(43, 136.5, G3, -60)
for x, z, lo in ((-20, 75, G1), (100, 80, G1), (10, 100, G2), (120, 104, G2), (-40, 125, G3), (80, 126, G3)):
    g.drift(x, z, lo, 5, 2, 1.3)
for x, z, lo in ((0, 73, G1), (90, 97, G2), (-30, 122, G3)):
    g.car(x, z, lo, 90)
g.write("scenes/district/z6_garages.tscn")

# =====================================================================================================
# 7. ПУСТЫРЬ И НЕДОСТРОЙ (0)
# =====================================================================================================
n = Scene("Wasteland")
y = SOUTH
# каркас недостроя X -135..-90, Z 92..105: 4 перекрытия, 3 доступных этажа, лестничные марши без стен
SL = 0.3
def slab(x0, x1, z0, z1, top, label=""):
    n.box("Slab", x0, x1, z0, z1, top - SL, SL, "construction", label)
for top, holes in ((3, "a"), (6, "b"), (9, "a")):
    slab(-135, -90, 92, 98, top)
    if holes == "a":
        slab(-131, -90, 98, 105, top)
    else:
        slab(-135, -95, 98, 105, top)
        slab(-92, -90, 98, 105, top)
slab(-135, -90, 92, 105, 12, "Недострой · 3 этажа доступны")
n.box("Flight", -134, -131, 98, 103, 0, 3, "construction", "Лестница", shape="stairs")
n.box("Flight", -95, -92, 98, 103, 3, 3, "construction", shape="stairs")
n.box("Flight", -134, -131, 98, 103, 6, 3, "construction", shape="stairs")
for x in (-134.5, -126, -117, -108, -99, -90.5):
    for z in (92.5, 104.5):
        n.box("Column", x - 0.25, x + 0.25, z - 0.25, z + 0.25, y, 11.7, "construction")
n.box("CraneTower", -81, -79, 87, 89, y, 40.0, "construction", "Башенный кран")
n.box("CraneJib", -105, -55, 87.5, 88.5, 40.0, 1.5, "construction", solid=False)
n.box("CraneCab", -83, -79, 86, 90, 38.0, 2.0, "construction", solid=False)
n.light("CraneLamp", -70, 39, 88, "Color(1, 0.85, 0.35, 1)", 6.0, 45.0)
for x, z, hh in ((-88, 41, 1.2), (-86, 46, 1.8), (-75, 30, 0.6), (-110, 12, 1.2)):
    n.box("Slabs", x - 3, x + 3, z - 0.8, z + 0.8, y, hh, "prop", "Плиты" if x == -88 else "")
n.box("Cabin", -145, -139, 125, 127.5, y, 2.6, "garage", "Бытовки", tint="Color(0.36, 0.42, 0.3, 1)")
n.box("Cabin", -136, -130, 125, 127.5, y, 2.6, "garage", tint="Color(0.36, 0.42, 0.3, 1)")
for x, z, sx, sz, hh in ((-120, 5, 8, 3, 1.5), (-80, 70, 4, 6, 1.3), (-130, 135, 6, 3, 1.6), (-70, 120, 5, 2, 1.2)):
    n.drift(x, z, y, sx, sz, hh)
for x, z in ((-140, -10), (-100, -5), (-70, 10), (-145, 85)):
    n.tree(x, z, y)
n.lamp(-105, -12, y)
n.write("scenes/district/z7_wasteland.tscn")

# =====================================================================================================
# КОРЕНЬ: district.tscn
# =====================================================================================================
ZONES = ["terrain", "z1_prospect", "z2_home_yard", "z3_school", "z4_south_yards", "z5_boiler", "z6_garages",
         "z7_wasteland", "z8_west_yard"]
# (x, y, z, yaw): yaw 0 — лицом на север, 180 — на юг, 90 — на запад, −90 — на восток
TELEPORTS = [(-20, HUB, -82, 180), (0, PROSPECT, -114.5, 0), (90, HUB, -60, 0), (20, SOUTH, 12, 0),
             (100, SOUTH, 34, -90), (40, G1, 78, 180), (-80, SOUTH, 20, 180), (-120, HUB, -30, 0)]

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
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, -20, 21, -82)
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
open(os.path.join(ROOT, "scenes", "levels", "district.tscn"), "w", encoding="utf-8", newline="\n").write(out)
print("written scenes/levels/district.tscn")
