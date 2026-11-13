# -*- coding: utf-8 -*-
# Этап F (docs/CITY_PLAN.md): плотность деталей. Собирает scenes/district/details.tscn и подключает её к district.tscn.
#   - россыпь по зонам: мусор, покрышки, бочки, ящики, баки, катушки, кольца, кирпич, арматура, люки,
#     сугробы у стен, брошенные машины, снеговики;
#   - на стенах: сосульки (гаражи, козырьки, ларьки, остановка, трубы), объявления у подъездов, граффити;
#   - таблички домов, проспекта, школы, остановки и вывески ларьков (текст — scripts/data/district_names.gd).
# Сцена details.tscn каждый раз собирается ЗАНОВО (правки руками в ней пропадут) — расстановка одна и та же,
# пока не изменился SEED или списки ниже. Что и где стоит в остальных сценах, скрипт не меняет.
#   python tools/apply_district_details.py
#
# Правила, чтобы детали не мешали ходить:
#   - на лестницах, пандусах, под арками, на проезде вдоль района и на проверочных маршрутах
#     (tools/tests/test_district.gd) стоят только предметы без коллизии;
#   - предмет с коллизией стоит либо вплотную к стене (и за ним остаётся свободный проход ≥ 2,8 м),
#     либо на открытом месте не ближе 1,8 м от любой преграды.
import json
import math
import os
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SEED = 1113
R = random.Random(SEED)
D = "res://assets/models/district/details/%s.gltf"
P = "res://assets/models/district/props/%s.gltf"

blocks = json.load(open(os.path.join(ROOT, "tools", "district_blocks.json"), encoding="utf-8"))
buildings = json.load(open(os.path.join(ROOT, "tools", "district_buildings.json"), encoding="utf-8"))
props = {(m["zone"], m["node"]): m for m in json.load(open(os.path.join(ROOT, "tools", "district_props.json"), encoding="utf-8"))}


# ---------------------------------------------------------------- геометрия района
def to_local(e, x, z):
    c, s = math.cos(math.radians(e["yaw"])), math.sin(math.radians(e["yaw"]))
    dx, dz = x - e["cx"], z - e["cz"]
    return c * dx - s * dz, s * dx + c * dz


def to_world(e, lx, lz, yaw=None):
    a = math.radians(e["yaw"] if yaw is None else yaw)
    c, s = math.cos(a), math.sin(a)
    return e["cx"] + c * lx + s * lz, e["cz"] - s * lx + c * lz


def is_floor(e):
    return e["kind"] == "ground" and e["shape"] == "box"


def is_obstacle(e):
    if e["shape"] != "box":
        return True                                   # лестницы и пандусы — на них ничего не ставим
    if e["kind"] in ("ground",):
        return False
    if e["kind"] in ("road", "snow", "rail") and e["sy"] <= 0.2:
        return False                                  # асфальт, поле, рельсы — плоские
    return True


FLOORS = [e for e in blocks if is_floor(e) and abs(e["cx"]) < 150 and abs(e["cz"]) < 150]
OBST = [e for e in blocks if is_obstacle(e) and abs(e["cx"]) < 150]
ARCHES = [e for e in blocks if e["base"].endswith("Arch")]


def floor_y(x, z):
    best = None
    for e in FLOORS:
        lx, lz = to_local(e, x, z)
        if abs(lx) <= e["sx"] / 2 and abs(lz) <= e["sz"] / 2:
            top = e["y"] + e["sy"]
            best = top if best is None else max(best, top)
    return best


def nearest(x, z, y):
    """Ближайшая преграда на этой высоте: (расстояние до её края, направление от неё наружу)."""
    best = (99.0, (1.0, 0.0), None)
    for e in OBST:
        if e["y"] > y + 2.2 or e["y"] + e["sy"] < y + 0.15:
            continue                                  # выше головы (арка, труба на опорах) или ниже ног
        if abs(e["cx"] - x) > e["sx"] / 2 + e["sz"] / 2 + 6 or abs(e["cz"] - z) > e["sx"] / 2 + e["sz"] / 2 + 6:
            continue
        lx, lz = to_local(e, x, z)
        ox, oz = abs(lx) - e["sx"] / 2, abs(lz) - e["sz"] / 2
        if ox <= 0 and oz <= 0:
            return (-1.0, (1.0, 0.0), e)
        d = math.hypot(max(ox, 0), max(oz, 0))
        if d < best[0]:
            nlx = math.copysign(max(ox, 0), lx)
            nlz = math.copysign(max(oz, 0), lz)
            ln = math.hypot(nlx, nlz) or 1.0
            wx, wz = to_world({"cx": 0, "cz": 0, "yaw": e["yaw"]}, nlx / ln, nlz / ln)
            best = (d, (wx, wz), e)
    return best


# проверочные маршруты (старт → конец): их нельзя перегораживать
ROUTES = [((-35, -19), (-35, -5)), ((14, -70), (14, -84)), ((23, -66), (23, -88)), ((23, -19), (23, 4)), ((-55, -68), (-55, -110)),
          ((-25, -48), (-47, -48)), ((-18, -8), (-18, 11)), ((15, 32), (15, 48)), ((-30, 45), (-30, 50)), ((-60.5, 45), (-60.5, 59)),
          ((23, 40), (23, 96)), ((-71.5, 42.5), (-71.5, 36)), ((-81, 22), (-81, 47)), ((78, -34.5), (84, -34.5)), ((15, -81.5), (15, -100)),
          ((-82, -66), (-82, -80)), ((-57, -20), (-57, -6))]
# проезд вдоль района, проезжая часть проспекта, школьное поле — держим свободными
CLEAR = [(19.4, -80, 26.6, 101), (-100, -98, 100, -85.2), (35, -47, 77, -22.5)]


def seg_dist(p, a, b):
    ax, az, bx, bz = a[0], a[1], b[0], b[1]
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - az) * dz) / (dx * dx + dz * dz)))
    return math.hypot(p[0] - ax - dx * t, p[1] - az - dz * t)


def in_way(x, z, r):
    if any(seg_dist((x, z), a, b) < 1.9 + r for a, b in ROUTES):
        return True
    if any(x0 - r < x < x1 + r and z0 - r < z < z1 + r for x0, z0, x1, z1 in CLEAR):
        return True
    for e in ARCHES:
        lx, lz = to_local(e, x, z)
        if abs(lx) < e["sx"] / 2 + 1.5 + r and abs(lz) < e["sz"] / 2 + 1.5 + r:
            return True
    return False


# ---------------------------------------------------------------- сцена
ext, nodes, counts = {}, [], {}


def res(path, typ="PackedScene"):
    if path not in ext:
        ext[path] = ("r%d" % (len(ext) + 1), typ)
    return ext[path][0]


def f(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def xform(x, y, z, yaw):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return "Transform3D(%s, 0, %s, 0, 1, 0, %s, 0, %s, %s, %s, %s)" % (f(c), f(s), f(-s), f(c), f(x), f(y), f(z))


def add(group, model, x, y, z, yaw):
    counts[group] = counts.get(group, 0) + 1
    name = "%s%d" % (model.split("/")[-1].split(".")[0].replace("_nocol", "").title().replace("_", ""), counts[group])
    nodes.append((group, '[node name="%s" parent="%s" instance=ExtResource("%s")]\ntransform = %s' % (name, group, res(model), xform(x, y, z, yaw))))


def add_sign(group, key, style, x, y, z, yaw):
    counts[group] = counts.get(group, 0) + 1
    nodes.append((group, '[node name="Sign%d" type="Node3D" parent="%s"]\ntransform = %s\nscript = ExtResource("%s")\nkey = "%s"\nstyle = "%s"'
                  % (counts[group], group, xform(x, y, z, yaw), res("res://scripts/world/district_sign.gd", "Script"), key, style)))


# ---------------------------------------------------------------- россыпь
# модель, радиус (м), есть ли коллизия, как ставить: "any" — где угодно, "wall" — только вплотную к стене
ITEMS = {
    "tire": (D % "tire_nocol", 0.4, False, "any"), "tire_stack": (D % "tire_stack", 0.45, True, "any"),
    "tire_bed": (D % "tire_bed_nocol", 0.5, False, "any"), "barrel": (D % "barrel", 0.4, True, "any"),
    "barrels": (D % "barrels", 0.9, True, "any"), "crate": (D % "crate", 0.55, True, "any"),
    "crate_stack": (D % "crate_stack", 1.1, True, "any"), "bags": (D % "bags_nocol", 0.9, False, "any"),
    "dumpster": (D % "dumpster", 1.1, True, "wall"), "spool": (D % "spool", 0.95, True, "any"),
    "pallet": (D % "pallet_nocol", 0.75, False, "any"), "pallet_stack": (D % "pallet_stack", 0.8, True, "any"),
    "bricks": (D % "bricks", 0.9, True, "any"), "ring": (D % "ring", 0.9, True, "any"), "rings": (D % "rings", 2.0, True, "any"),
    "rebar": (D % "rebar_nocol", 2.4, False, "any"), "manhole": (D % "manhole_nocol", 0.9, False, "any"),
    "snowman": (D % "snowman", 0.6, True, "any"),
    "drift": ([P % "drift_drift_4x1x1_2_0", P % "drift_drift_4x1x1_2_1", P % "drift_drift_4x1x1_2_2"], 2.1, True, "wall"),
    "car": ([P % ("car_car_1_7x1_45x4_2_v%d" % i) for i in range(4)], 2.3, True, "wall"),
}
HALF_DEPTH = {"drift": 0.6, "car": 0.85, "dumpster": 0.45}       # полуширина поперёк стены
placed = []


def try_place(group, item, x, z):
    model, r, collide, mode = ITEMS[item]
    y = floor_y(x, z)
    if y is None or abs(x) > 99 or z > 100.3 or z < -98:
        return False
    d, n, blk = nearest(x, z, y)
    if d < 0:
        return False
    if any(math.hypot(x - px, z - pz) < r + pr + 0.35 for px, pz, pr in placed):
        return False
    yaw = R.uniform(0, 360)
    if not collide:
        if d < r * 0.6 + 0.1:
            return False
        if item == "manhole" and (d < 1.2 or abs(y - round(y * 2) / 2) > 0.01):
            return False
    else:
        if in_way(x, z, r):
            return False
        if mode == "wall" or d < 1.8 + r:
            # вплотную к стене: придвигаем к ней и проверяем, что за предметом остался проход
            if d > 3.0 or blk is None:
                return False
            hd = HALF_DEPTH.get(item, r)
            gap = 0.12 if item != "car" else R.uniform(0.5, 0.9)
            x, z = x - n[0] * (d - hd - gap), z - n[1] * (d - hd - gap)
            y2 = floor_y(x, z)
            if y2 is None or abs(y2 - y) > 0.01 or in_way(x, z, r):
                return False
            if any(math.hypot(x - px, z - pz) < r + pr + 0.35 for px, pz, pr in placed):
                return False
            for k in (0.5, 1.1, 1.7, 2.3, 2.8):
                qx, qz = x + n[0] * (hd + k), z + n[1] * (hd + k)
                fy = floor_y(qx, qz)
                if fy is None or abs(fy - y) > 0.01 or nearest(qx, qz, y)[0] < 0.25:
                    return False
            for side in (-1, 1):                      # и по бокам предмет ни во что не упирается
                qx, qz = x + side * (-n[1]) * r, z + side * n[0] * r
                if nearest(qx, qz, y)[0] < 0.05 and item in ("car", "drift"):
                    return False
            yaw = math.degrees(math.atan2(n[0], n[1]))                 # «перёд» модели — от стены
            if item == "car":
                yaw += 90 if R.random() < 0.5 else -90                  # машина — вдоль стены
    m = model if isinstance(model, str) else R.choice(model)
    add(group, m, x, y, z, yaw)
    placed.append((x, z, r))
    return True


def scatter(group, rect, must, pool, n):
    x0, z0, x1, z1 = rect
    for item in must:
        for _ in range(400):
            if try_place(group, item, R.uniform(x0, x1), R.uniform(z0, z1)):
                break
    names = [k for k, w in pool.items() for _ in range(w)]
    done = tries = 0
    while done < n and tries < n * 60:
        tries += 1
        if try_place(group, R.choice(names), R.uniform(x0, x1), R.uniform(z0, z1)):
            done += 1


scatter("Wasteland", (-98, 0, -48, 45), ["rings", "spool", "spool", "barrels", "car"],
        {"tire": 4, "tire_stack": 2, "barrel": 3, "bricks": 4, "rebar": 3, "pallet": 3, "pallet_stack": 2, "ring": 2, "bags": 2, "crate": 1, "drift": 2}, 44)
scatter("Boiler", (61, -11, 99, 40), ["barrels", "barrels", "rings", "spool"],
        {"barrel": 4, "crate": 2, "crate_stack": 2, "pallet": 3, "pallet_stack": 2, "tire": 3, "bags": 2, "bricks": 2, "drift": 2}, 24)
scatter("Boiler", (-50, 34.5, 60, 41.5), [], {"bags": 3, "tire": 3, "pallet": 2, "crate": 2, "barrel": 2, "drift": 2}, 16)
scatter("Garages", (-99, 47, 99, 101), ["car", "car", "car", "dumpster"],
        {"tire": 6, "tire_stack": 3, "barrel": 3, "crate": 3, "bags": 4, "pallet": 3, "bricks": 2, "drift": 4, "pallet_stack": 1, "manhole": 1}, 50)
scatter("HomeYard", (-45, -64, 19, -17), ["dumpster", "snowman", "car", "car"],
        {"bags": 3, "tire_bed": 4, "crate": 2, "drift": 4, "manhole": 2, "tire": 1}, 16)
scatter("WestYard", (-99, -80, -47, -18), ["dumpster", "car"], {"bags": 3, "tire_bed": 3, "crate": 2, "drift": 4, "manhole": 1, "tire": 1}, 13)
scatter("SouthYards", (-50, -8, 19, 34), ["dumpster", "snowman", "car", "car"],
        {"bags": 3, "tire_bed": 4, "crate": 2, "drift": 4, "manhole": 2, "pallet": 1, "tire": 2}, 18)
scatter("SouthYards", (27, -8, 59, 34), ["dumpster", "car"], {"bags": 3, "tire_bed": 3, "crate": 1, "drift": 3, "manhole": 1}, 10)
scatter("School", (27, -64, 99, -17), [], {"bags": 2, "drift": 5, "tire": 3, "crate": 1, "manhole": 1}, 10)
scatter("Prospect", (-99, -85, 99, -80.3), [], {"crate": 3, "crate_stack": 2, "bags": 4, "drift": 3, "tire": 1}, 14)
for (x, z) in ((23, -60), (23, -30), (23, 12), (23, 33), (23, 61), (-60, -88.5), (8, -94), (70, -89), (-30, -93.5)):
    y = floor_y(x, z)                                 # люки на проезде и проспекте
    if y is not None:
        add("Roads", D % "manhole_nocol", x, y + (0.03 if z < -80 or x == 23 else 0), z, R.uniform(0, 360))
for (x, yaw) in ((35.6, 90), (76.4, -90)):            # ворота школьного поля
    add("School", D % "goal_nocol", x, floor_y(x, -34.5) + 0.03, -34.5, yaw)

# ---------------------------------------------------------------- на стенах
def icicle_row(group, e, yaw, y, lz, share, length=None):
    L = length or e["sx"]
    n = max(1, int(L // 4))
    for i in range(n):
        if R.random() < share:
            x, z = to_world(e, -L / 2 + (i + 0.5) * L / n, lz, yaw)
            add(group, D % "icicles_4_nocol", x, y, z, yaw)


for e in blocks:
    base, key = e["base"], (e["zone"], e["node"])
    if base == "GarageRow":
        yaw = e["yaw"] + props.get(key, {}).get("yaw", 0)
        icicle_row("Garages", e, yaw, e["y"] + e["sy"] - 0.12, e["sz"] / 2 + 0.33, 0.4)
    elif base == "Canopy":
        x, z = to_world(e, 0, e["sz"] / 2 + 0.02)
        add("HomeYard", D % "icicles_2_nocol", x, e["y"], z, e["yaw"])
    elif base == "Kiosk":
        yaw = e["yaw"] + props.get(key, {}).get("yaw", 0)
        x, z = to_world(e, 0, e["sz"] / 2 + 0.38, yaw)
        add(e["zone"], D % "icicles_4_nocol", x, e["y"] + e["sy"] - 0.1, z, yaw)
    elif base == "StopRoof":
        icicle_row("Prospect", e, 180, e["y"], e["sz"] / 2 + 0.02, 0.75)
    elif base == "Pipe":
        for side in (-0.36, 0.36):
            icicle_row("Boiler", e, 0, e["y"] + 0.86, side, 0.3)
    elif base == "PipeBranch":
        icicle_row("Boiler", e, 90, e["y"] + 0.16, 0, 0.35, length=e["sz"])

# граффити: торцы гаражных рядов, бетонные заборы котельной и стройки, глухие торцы домов
g = 0
rows = [e for e in blocks if e["base"] == "GarageRow"]
R.shuffle(rows)
for e in rows[:12]:
    side = R.choice((-1, 1))
    x, z = to_world(e, side * (e["sx"] / 2 + 0.03), R.uniform(-1.2, 1.2))
    add("Garages", D % ("graffiti_%d_nocol" % (g % 8)), x, e["y"] + R.uniform(1.0, 1.5), z, e["yaw"] + 90 * side)
    g += 1
for e in blocks:
    if e["base"] in ("Fence", "BuildFence") and e["zone"] in ("BoilerHouse", "Wasteland"):
        along_z = e["sz"] > e["sx"]
        L = e["sz"] if along_z else e["sx"]
        for t in (R.uniform(-0.35, -0.1), R.uniform(0.1, 0.35)):
            side = R.choice((-1, 1))
            th = (e["sx"] if along_z else e["sz"]) / 2 + 0.03
            lx, lz = (side * th, t * L) if along_z else (t * L, side * th)
            x, z = to_world(e, lx, lz)
            yaw = e["yaw"] + (90 * side if along_z else (0 if side > 0 else 180))
            add("Boiler" if e["zone"] == "BoilerHouse" else "Wasteland", D % ("graffiti_%d_nocol" % (g % 8)), x, e["y"] + R.uniform(1.0, 1.5), z, yaw)
            g += 1

ZONE = {"homeyard": "HomeYard", "westyard": "WestYard", "school": "School", "southyards": "SouthYards", "boilerhouse": "SouthYards", "terrain": "Prospect"}
shops = 0
for s in buildings:
    t = s["type"]
    if t in ("boiler", "chimney"):
        continue
    grp = ZONE[s["id"].split("_")[0]]
    e = {"cx": s["cx"], "cz": s["cz"], "yaw": s["yaw"]}
    hw, hd = s["L"] / 2, s["D"] / 2
    arches = [tuple(a) for a in s["arches"]]
    ent = s["entrances"]
    if ent is None and t == "school_main":
        ent = [0.0]
    if ent is None and t in ("panel", "khr", "tower"):
        n = max(1, round(s["L"] / 12.5))
        ent = [-hw + s["L"] * (i + 0.5) / n for i in range(n)]
    ent = [x for x in (ent or []) if all(not (a - 2.6 < x < c + 2.6) for a, c in arches)]
    # объявления у подъездов
    for lx in ent:
        if t != "school_main" and R.random() < 0.65:
            x, z = to_world(e, lx + R.choice((-1.9, 1.9)), hd + 0.04)
            add(grp, D % "notices_nocol", x, s["y"] + 1.6, z, s["yaw"])
    # номер дома — на углу фасада; у школы — табличка у крыльца
    if t == "school_main":
        x, z = to_world(e, 4.6, hd + 0.04)
        add_sign(grp, "school", "school", x, s["y"] + 2.0, z, s["yaw"])
    elif "house." + s["id"] in open(os.path.join(ROOT, "scripts", "data", "district_names.gd"), encoding="utf-8").read():
        x, z = to_world(e, -hw + 1.4, hd + 0.04)
        add_sign(grp, "house." + s["id"], "house", x, s["y"] + 2.7, z, s["yaw"])
    if t == "north" and s["L"] >= 40:                  # световые вывески над витринами северной стороны (у ларьков надпись своя)
        for lx in ([-8.0, 10.0] if s["L"] < 60 else [-62.0, -38.0, -12.0, 14.0, 40.0, 64.0]):
            shops += 1
            x, z = to_world(e, lx, hd + 0.72)
            add_sign(grp, "shop.%d" % shops, "shop", x, s["y"] + 4.14, z, s["yaw"])
    if t == "north":                                   # название проспекта на северной стороне
        for lx in ([-hw + 4.0] if s["L"] < 60 else [-hw + 4.0, 0.0, hw - 6.0]):
            x, z = to_world(e, lx, hd + 0.04)
            add_sign(grp, "street", "street", x, s["y"] + 2.7, z, s["yaw"])
    # граффити на глухом торце дома
    if t in ("panel", "khr") and R.random() < 0.55:
        side = R.choice((-1, 1))
        x, z = to_world(e, side * (hw + 0.04), R.uniform(-hd * 0.5, hd * 0.5))
        if nearest(x + (x - s["cx"]) * 0.01, z + (z - s["cz"]) * 0.01, s["y"])[0] > 0.6:
            add(grp, D % ("graffiti_%d_nocol" % (g % 8)), x, s["y"] + R.uniform(1.1, 1.5), z, s["yaw"] + 90 * side)
            g += 1

for e in blocks:
    if e["base"] == "StopWall":
        x, z = to_world(e, 5.5, e["sz"] / 2 + 0.03, 180)
        add_sign("Prospect", "stop", "street", x, e["y"] + 2.0, z, 180)

# ---------------------------------------------------------------- запись
groups = ["Prospect", "HomeYard", "WestYard", "School", "SouthYards", "Boiler", "Garages", "Wasteland", "Roads"]
out = ["[gd_scene format=3]", ""]
for path, (rid, typ) in ext.items():
    out.append('[ext_resource type="%s" path="%s" id="%s"]' % (typ, path, rid))
out += ["", '[node name="Details" type="Node3D"]']
for grp in groups:
    out += ["", '[node name="%s" type="Node3D" parent="."]' % grp]
    for gname, text in nodes:
        if gname == grp:
            out += ["", text]
assert all(gname in groups for gname, _ in nodes), set(gname for gname, _ in nodes) - set(groups)
open(os.path.join(ROOT, "scenes", "district", "details.tscn"), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

path = os.path.join(ROOT, "scenes", "levels", "district.tscn")
s = open(path, encoding="utf-8").read()
if "details.tscn" not in s:
    a = '[ext_resource type="PackedScene" path="res://scenes/district/backdrop.tscn" id="backdrop"]'
    assert a in s
    s = s.replace(a, a + '\n[ext_resource type="PackedScene" path="res://scenes/district/details.tscn" id="details"]')
    s = s.rstrip("\n") + '\n\n[node name="Details" parent="." instance=ExtResource("details")]\n'
    open(path, "w", encoding="utf-8", newline="\n").write(s)
print("details.tscn: %d nodes, %d models" % (len(nodes), len(ext)))
for grp in groups:
    print("  %-11s %d" % (grp, counts.get(grp, 0)))
