# -*- coding: utf-8 -*-
# Этап D (docs/CITY_PLAN.md): свет и атмосфера района. Правит существующие сцены, повторный запуск безопасен.
#   - временные OmniLight «LampLight» блокаута → фонари scenes/props/street_light.tscn на головах столбов
#     (столбы стоят «через один»: свет есть только у тех, где он был в блокауте), каждый третий мигает;
#   - фонари проспекта развёрнуты плафоном к дороге;
#   - ориентиры (группа landmark — не гаснут вдали и получают ореол): красные огни трубы, прожектор крана,
#     мигающий прожектор школы;
#   - пар над теплотрассой (scenes/props/steam.tscn);
#   - district.tscn: узел LightBudget (тени только у ближайших), темнее общий фон и луна.
#   python tools/apply_district_lights.py
import math
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ZONES = ["terrain", "z1_prospect", "z2_home_yard", "z3_school", "z4_south_yards", "z5_boiler", "z6_garages",
         "z7_wasteland", "z8_west_yard"]
LANDMARKS = {"ChimneyRed": 3.0, "ChimneyRed2": 2.2, "CraneLamp": 4.0, "FloodLight": 5.0}
STEAM = {"z5_boiler": [("SteamJoint", 59, 4.0, 43), ("SteamEnd", -45.5, 2.0, 43), ("SteamArch", 23, 5.7, 43),
                       ("SteamLeak1", -20, 1.5, 43), ("SteamLeak2", 70, 1.5, 43)]}


def f(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def xform(x, y, z, yaw=0.0):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return "Transform3D(%s, 0, %s, 0, 1, 0, %s, 0, %s, %s, %s, %s)" % (f(c), f(s), f(-s), f(c), f(x), f(y), f(z))


def sections(text):
    return [p.rstrip("\n") for p in re.split(r"\n(?=\[)", text.rstrip("\n"))]


def origin(sec):
    m = re.search(r"transform = Transform3D\(([^)]*)\)", sec)
    v = [float(t) for t in m.group(1).split(",")]
    return v[9], v[10], v[11]


def add_ext(out, ids, path, typ):
    if path in ids:
        return ids[path]
    used = set(ids.values())
    k = 1
    while "L%d" % k in used:
        k += 1
    ids[path] = "L%d" % k
    last = max(i for i, s in enumerate(out) if s.startswith("[ext_resource") or s.startswith("[gd_scene"))
    out.insert(last + 1, '[ext_resource type="%s" path="%s" id="%s"]' % (typ, path, ids[path]))
    return ids[path]


def zone(fname, counter):
    path = os.path.join(ROOT, "scenes", "district", fname + ".tscn")
    secs = sections(open(path, encoding="utf-8").read())
    ids = {}
    for s in secs:
        m = re.match(r'\[ext_resource [^\]]*path="([^"]+)"[^\]]*id="([^"]+)"', s)
        if m:
            ids[m.group(1)] = m.group(2)
    names = {re.match(r'\[node name="([^"]+)"', s).group(1) for s in secs if s.startswith("[node")}
    out, lamps, stats = [], [], {"lamps": 0, "landmarks": 0, "steam": 0, "rotated": 0}
    for s in secs:
        m = re.match(r'\[node name="([^"]+)" type="OmniLight3D" parent="\."\]', s)
        if m and m.group(1).startswith("LampLight"):
            lamps.append(origin(s))
            continue
        if m and m.group(1) in LANDMARKS and "landmark" not in s:
            s = s.replace('parent="."]', 'parent="." groups=["landmark"]]', 1)
            s += "\nmetadata/halo_size = %s" % f(LANDMARKS[m.group(1)])
            if m.group(1) == "FloodLight":
                fid = add_ext(out, ids, "res://scripts/world/flicker_light.gd", "Script")
                s += '\nscript = ExtResource("%s")\nflicker_chance = 0.35\nmin_factor = 0.1' % fid
            stats["landmarks"] += 1
        if fname == "z1_prospect" and re.match(r'\[node name="LampPole\d*_mdl"', s) and "Transform3D(-1," not in s:
            x, y, z = origin(s)
            s = re.sub(r"transform = Transform3D\([^)]*\)", "transform = " + xform(x, y, z, 180), s)
            stats["rotated"] += 1
        out.append(s)
    if lamps:
        sid = add_ext(out, ids, "res://scenes/props/street_light.tscn", "PackedScene")
        for x, y, z in lamps:
            counter[0] += 1
            yaw = 180 if fname == "z1_prospect" else 0
            n = "StreetLight%d" % counter[0]
            sec = '[node name="%s" parent="." instance=ExtResource("%s")]\ntransform = %s' % (n, sid, xform(x, y - 6.2, z, yaw))
            if counter[0] % 3 == 0:
                sec += "\nflicker = true"
            out.append(sec)
            stats["lamps"] += 1
    for n, x, y, z in STEAM.get(fname, []):
        if n in names:
            continue
        sid = add_ext(out, ids, "res://scenes/props/steam.tscn", "PackedScene")
        out.append('[node name="%s" parent="." instance=ExtResource("%s")]\ntransform = %s' % (n, sid, xform(x, y, z)))
        stats["steam"] += 1
    open(path, "w", encoding="utf-8", newline="\n").write("\n\n".join(out) + "\n")
    print("%-16s %s" % (fname, stats))


def root_scene():
    path = os.path.join(ROOT, "scenes", "levels", "district.tscn")
    s = open(path, encoding="utf-8").read()
    if "LightBudget" not in s:
        s = s.replace('[ext_resource type="Script" path="res://scripts/levels/district.gd" id="lvl"]',
                      '[ext_resource type="Script" path="res://scripts/levels/district.gd" id="lvl"]\n'
                      '[ext_resource type="Script" path="res://scripts/world/light_budget.gd" id="budget"]', 1)
        s = s.rstrip("\n") + '\n\n[node name="LightBudget" type="Node" parent="."]\nscript = ExtResource("budget")\n'
    s = s.replace("ambient_light_energy = 0.55", "ambient_light_energy = 0.3")
    s = re.sub(r'(\[node name="Moon"[^\[]*?)light_energy = 0\.35', r"\1light_energy = 0.22", s)
    open(path, "w", encoding="utf-8", newline="\n").write(s)
    print("district.tscn: LightBudget, ambient 0.3, moon 0.22")


counter = [0]
for z in ZONES:
    zone(z, counter)
root_scene()
