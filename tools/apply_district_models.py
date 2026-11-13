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


def xform(x, y, z, yaw=0.0):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return "Transform3D(%s, 0, %s, 0, 1, 0, %s, 0, %s, %s, %s, %s)" % (f(c), f(s), f(-s), f(c), f(x), f(y), f(z))


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
        (plan[z]["hide"] if p["nocol"] else plan[z]["remove"]).add(n)
        plan[z]["add"].append((n + "_mdl", p["model"], xform(b["cx"], b["y"], b["cz"], b["yaw"] + p["yaw"])))

    total = {"removed": 0, "hidden": 0, "added": 0, "restored": 0, "remodeled": 0}
    for z, fname in FILES.items():
        path = os.path.join(ROOT, "scenes", "district", fname + ".tscn")
        secs = split_sections(open(path, encoding="utf-8").read())
        ext_path = {}
        for s in secs:
            m = re.match(r'\[ext_resource [^\]]*path="([^"]+)"[^\]]*id="([^"]+)"', s)
            if m:
                ext_path[m.group(2)] = m.group(1)
        want = {name: model for name, model, tr in plan[z]["add"]}
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
        for name, model, tr in plan[z]["add"]:
            if name in present:
                continue
            if model not in ext_ids:
                ext_ids[model] = "m%d" % (len(ext_ids) + 1)
                new_ext.append('[ext_resource type="PackedScene" path="%s" id="%s"]' % (model, ext_ids[model]))
            new_nodes.append('[node name="%s" parent="." instance=ExtResource("%s")]\ntransform = %s' % (name, ext_ids[model], tr))
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
                                                          len([1 for a in plan[z]["add"] if a[0] not in present])))
    print(total)


main()
