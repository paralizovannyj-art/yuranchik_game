# -*- coding: utf-8 -*-
# Этап C (docs/CITY_PLAN.md): заменить серые блоки блокаута на модели домов и пропсов.
# Правит СУЩЕСТВУЮЩИЕ сцены scenes/district/*.tscn (они — источник правды после приёмки блокаута), а не пересобирает их:
#   - дома (tools/district_buildings.json) и пропсы (tools/district_props.json) добавляются как экземпляры моделей;
#   - их серые блоки удаляются (у моделей своя коллизия — её добавляет scripts/tools/ps2_import.gd);
#   - у моделей без коллизии («_nocol»: лестницы, навесы, стрела крана…) серый блок остаётся, но невидимым
#     (show_mesh = false) — он даёт гладкий пандус под ступенями.
# Запуск повторно безопасен: уже вставленные модели второй раз не добавляются.
#   python tools/apply_district_models.py
import json
import math
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FILES = {"Terrain": "terrain", "Prospect": "z1_prospect", "HomeYard": "z2_home_yard", "School": "z3_school",
         "SouthYards": "z4_south_yards", "BoilerHouse": "z5_boiler", "Garages": "z6_garages", "Wasteland": "z7_wasteland",
         "WestYard": "z8_west_yard"}
# блоки, которые входят в модели домов (крыльца, козырьки — часть модели)
BUILDING_EXTRA = {"HomeYard": ("Porch", "Canopy"), "School": ("Porch", "PorchRoof")}


def f(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def xform(x, y, z, yaw=0.0, sx=1.0):
    """Положение + поворот вокруг вертикали; sx — растяжение модели вдоль её длины (локальная X)."""
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return "Transform3D(%s, 0, %s, 0, 1, 0, %s, 0, %s, %s, %s, %s)" % (f(c * sx), f(s), f(-s * sx), f(c), f(x), f(y), f(z))


INFRA = "res://assets/models/district/infra_%s.gltf"
# перила перехода из props/ не ставим: парапет есть у павильона infra_underpass_exit
SKIP_PROPS = {("Terrain", "TunnelRail"), ("Terrain", "TunnelRail2"), ("Terrain", "TunnelRail3")}


def infra_plan(plan):
    """Часть 2 этапа C: набор infra_* там, где у props/ замены нет (решение автора 2026-11-13)."""
    T, P = plan["Terrain"], plan["Prospect"]
    # пандусы проезда на местах серых пандусов
    for node, cz, y, m in (("RampProspect", -75, 3, "ramp_w6_h3"), ("RampSouth", -10, 0, "ramp_w6_h3"),
                           ("RampGarages", 52, -2.5, "ramp_w6_h25"), ("RampGarages2", 70, -5, "ramp_w6_h25"),
                           ("RampGarages3", 88, -7.5, "ramp_w6_h25")):
        T["remove"].add(node)
        T["add"].append((node + "_infra", INFRA % m, xform(23, y, cz)))
    # подземный переход: спуск к порталу, портал в подпорной стенке, павильон над северной лестницей
    T["remove"].add("TunnelRampS")
    T["add"].append(("UnderpassRamp_infra", INFRA % "underpass_ramp", xform(-55, 3, -77)))
    T["add"].append(("UnderpassPortal_infra", INFRA % "underpass_portal", xform(-55, 3, -80)))
    T["add"].append(("UnderpassExit_infra", INFRA % "underpass_exit", xform(-55, 6, -103.5)))
    for n in ("TunnelRail_mdl", "TunnelRail2_mdl", "TunnelRail3_mdl"):
        T["remove"].add(n)

    # подпорные стенки вдоль двух больших уступов; куски по 6 м чуть растягиваются, чтобы заполнить пролёт целиком
    def wall(tag, z, y, spans):
        k = 0
        for a, b in spans:
            n = max(1, round((b - a) / 6.0))
            w = (b - a) / n
            for i in range(n):
                k += 1
                T["add"].append(("RetWall%s%d_infra" % (tag, k), INFRA % "retwall_6x3", xform(a + w * (i + 0.5), y, z + 0.02, sx=w / 6.0)))
    wall("N", -80, 3, [(-100, -58.7), (-51.3, 10), (26.3, 100)])                      # проспект над дворами
    wall("S", -15, 0, [(-100, -60), (-54, -40), (-30, 19.7), (26.3, 50), (56, 100)])  # дворы над южной полосой
    # проспект: путь, провода и тротуары — только вид, без коллизии (узел Decor), чуть утоплены в землю
    for n in ("TramStrip", "TramRail", "TramRail2"):
        P["remove"].add(n)
    for i in range(20):
        P["add"].append(("TramTrack%d_infra" % (i + 1), INFRA % "tram_track_10", xform(-95 + 10 * i, 6 - 0.04, -91), "Decor"))
    for i in range(9):
        P["add"].append(("TramWire%d_infra" % (i + 1), INFRA % "tram_wire_20", xform(-80 + 20 * i, 6, -91), "Decor"))
    for k, x in enumerate((-95, 95)):
        P["add"].append(("TramWireEnd%d_infra" % (k + 1), INFRA % "tram_wire_20", xform(x, 6, -91, sx=0.5), "Decor"))
    for i in range(50):
        P["add"].append(("SidewalkS%d_infra" % (i + 1), INFRA % "sidewalk_4x2", xform(-98 + 4 * i, 6 - 0.1, -84, 180), "Decor"))
        P["add"].append(("SidewalkN%d_infra" % (i + 1), INFRA % "sidewalk_4x2", xform(-98 + 4 * i, 6 - 0.1, -98), "Decor"))


def split_sections(text):
    """Разбить .tscn на секции, каждая начинается с '[' в начале строки."""
    parts = re.split(r"\n(?=\[)", text.rstrip("\n"))
    return [p.rstrip("\n") for p in parts]


def node_name(sec):
    m = re.match(r'\[node name="([^"]+)"', sec)
    return m.group(1) if m else None


def main():
    blocks = json.load(open(os.path.join(ROOT, "tools", "district_blocks.json"), encoding="utf-8"))
    blk_by = {(b["zone"], b["node"]): b for b in blocks}
    buildings = json.load(open(os.path.join(ROOT, "tools", "district_buildings.json"), encoding="utf-8"))
    props = json.load(open(os.path.join(ROOT, "tools", "district_props.json"), encoding="utf-8"))

    plan = {z: {"remove": set(), "hide": set(), "add": []} for z in FILES}
    for bd in buildings:
        z = bd["zone"]
        for b in blocks:
            if b["zone"] == z and (b["base"] == bd["name"] or b["base"] == bd["name"] + "Arch"):
                plan[z]["remove"].add(b["node"])
        plan[z]["add"].append(("%s_mdl" % bd["id"].split("_", 1)[1].title().replace("_", ""),
                               "res://assets/models/district/%s.gltf" % bd["id"], xform(bd["cx"], bd["y"], bd["cz"], bd["yaw"])))
    for z, bases in BUILDING_EXTRA.items():
        for b in blocks:
            if b["zone"] == z and b["base"] in bases:
                plan[z]["remove"].add(b["node"])
    for p in props:
        z, n = p["zone"], p["node"]
        b = blk_by[(z, n)]
        if (z, n) in SKIP_PROPS:
            plan[z]["remove"].add(n)
            continue
        (plan[z]["hide"] if p["nocol"] else plan[z]["remove"]).add(n)
        plan[z]["add"].append((n + "_mdl", p["model"], xform(b["cx"], b["y"], b["cz"], b["yaw"] + p["yaw"])))

    infra_plan(plan)

    total = {"removed": 0, "hidden": 0, "added": 0, "restored": 0, "remodeled": 0}
    for z, fname in FILES.items():
        path = os.path.join(ROOT, "scenes", "district", fname + ".tscn")
        secs = split_sections(open(path, encoding="utf-8").read())
        ext_path = {}
        for s in secs:
            m = re.match(r'\[ext_resource [^\]]*path="([^"]+)"[^\]]*id="([^"]+)"', s)
            if m:
                ext_path[m.group(2)] = m.group(1)
        want = {a[0]: a[1] for a in plan[z]["add"]}
        out, ext_ids = [], {}
        for s in secs:
            m = re.match(r'\[ext_resource [^\]]*path="([^"]+)"[^\]]*id="([^"]+)"', s)
            if m:
                ext_ids[m.group(1)] = m.group(2)
            n = node_name(s)
            if n in plan[z]["remove"]:
                total["removed"] += 1
                continue
            mi = re.search(r'instance=ExtResource\("([^"]+)"\)', s)
            if n in want and mi and ext_path.get(mi.group(1)) != want[n]:
                total["remodeled"] += 1                  # модель пересобрана под другим именем — вставим заново
                continue
            if n in plan[z]["hide"] and "show_mesh = false" not in s:
                s += "\nshow_mesh = false"
                total["hidden"] += 1
            out.append(s)
        present = {node_name(s) for s in out}
        # серые блоки под моделями без коллизии, удалённые раньше (модель тогда была с коллизией), — вернуть невидимыми
        for n in sorted(plan[z]["hide"] - present):
            b = blk_by[(z, n)]
            if "bb" not in ext_ids.values():
                out.insert(1, '[ext_resource type="Script" path="res://scripts/tools/blockout_box.gd" id="bb"]')
                ext_ids["res://scripts/tools/blockout_box.gd"] = "bb"
            L = ['[node name="%s" type="Node3D" parent="."]' % n, "transform = " + xform(b["cx"], b["y"], b["cz"], b["yaw"]),
                 'script = ExtResource("bb")', "size = Vector3(%s, %s, %s)" % (f(b["sx"]), f(b["sy"]), f(b["sz"])),
                 'kind = "%s"' % b["kind"]]
            if b["shape"] != "box":
                L.append('shape = "%s"' % b["shape"])
            L.append("show_mesh = false")
            out.append("\n".join(L))
            total["restored"] += 1
        present = {node_name(s) for s in out}
        new_ext, new_nodes = [], []
        for a in plan[z]["add"]:
            name, model, tr = a[0], a[1], a[2]
            parent = a[3] if len(a) > 3 else "."
            if name in present:
                continue
            if parent == "Decor" and "Decor" not in present:
                new_ext.append('[ext_resource type="Script" path="res://scripts/world/no_collision.gd" id="nocol"]')
                new_nodes.append('[node name="Decor" type="Node3D" parent="."]\nscript = ExtResource("nocol")')
                present.add("Decor")
            if model not in ext_ids:
                used = set(ext_ids.values())
                k = len(ext_ids) + 1
                while "m%d" % k in used:
                    k += 1
                ext_ids[model] = "m%d" % k
                new_ext.append('[ext_resource type="PackedScene" path="%s" id="%s"]' % (model, ext_ids[model]))
            new_nodes.append('[node name="%s" parent="%s" instance=ExtResource("%s")]\ntransform = %s' % (name, parent, ext_ids[model], tr))
            total["added"] += 1
        last_ext = max(i for i, s in enumerate(out) if s.startswith("[ext_resource") or s.startswith("[gd_scene"))
        out = out[:last_ext + 1] + new_ext + out[last_ext + 1:] + new_nodes
        body = "\n".join(s for s in out if not s.startswith("[ext_resource"))
        kept = []
        for s in out:                                    # убрать ссылки на ресурсы, которыми больше ничто не пользуется
            m = re.match(r'\[ext_resource [^\]]*id="([^"]+)"', s)
            if m and 'ExtResource("%s")' % m.group(1) not in body:
                total["unused_ext"] = total.get("unused_ext", 0) + 1
                continue
            kept.append(s)
        out = kept
        open(path, "w", encoding="utf-8", newline="\n").write("\n\n".join(out) + "\n")
        print("%-28s removed %3d  hidden %2d  added %3d" % (fname, len([1 for n in plan[z]["remove"] if n in present]),
                                                          len([1 for n in plan[z]["hide"] if n in present]),
                                                          len(new_nodes)))
    print(total)


main()
