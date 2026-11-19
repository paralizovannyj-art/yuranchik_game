# Собирает сцену локации «Восточный ж/д мост» (YUR-7) из моделей Blender:
#   scenes/east_bridge/eb_location.tscn — модели (assets/models/east_bridge/*.gltf), фон и фонари;
#   фонари ставятся по assets/models/east_bridge/lights.json, который пишет tools/blender/build_east_bridge.py.
# Ночная игровая сцена (scenes/levels/east_bridge.tscn) и дневная для катсцены (scenes/levels/east_bridge_day.tscn)
# подключают её целиком — свет, туман и небо у них свои.
# Ещё создаёт .import-файлы моделей (импорт через scripts/tools/ps2_import.gd), если их нет.
#
# Запуск:  python tools/make_east_bridge_scenes.py
# Сцена собирается заново — правки руками в eb_location.tscn пропадут (фонари двигайте в build_east_bridge.py).
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MODELS = "assets/models/east_bridge"
PARTS = [("Ground", "eb_ground"), ("Bridge", "eb_bridge"), ("Catenary", "eb_catenary"),
         ("Trains", "eb_trains"), ("Props", "eb_props"), ("City", "eb_city"), ("Field", "eb_field")]

GREEN = (0.45, 1.0, 0.42)          # ртутные лампы станции — как на ночных фото
PALE_GREEN = (0.62, 0.95, 0.70)    # лампы моста: зеленовато-белые
ORANGE = (1.0, 0.52, 0.18)         # натрий
WHITE = (0.85, 0.9, 1.0)           # холодная прожекторная мачта в парке
COLORS = {"green": GREEN, "orange": ORANGE, "white": WHITE}
# по виду фонаря: (имя, яркость конуса, дальность, угол) — None = как в scenes/props/street_light.tscn
KINDS = {
    "bridge": ("BridgeLamp", 12.0, None, None),
    "platform": ("PlatformLamp", 60.0, 26.0, 70.0),
    "station": ("StationLamp", 6.0, 7.0, 70.0),
    "mast": ("Floodlight", 260.0, 40.0, 75.0),
    "street": ("StreetLamp", 36.0, None, None),
    "village": ("VillageLamp", 24.0, None, None),
}
FLICKER = {("BridgeLamp", 4), ("PlatformLamp", 3), ("PlatformLamp", 8)}   # старые лампы мигают

IMPORT = """[remap]

importer="scene"
importer_version=1
type="PackedScene"

[params]

nodes/root_type=""
nodes/root_name=""
nodes/root_script=null
mesh_library/use_node_names_as_mesh_names=false
array_mesh/deduplicate_surfaces=true
nodes/apply_root_scale=true
nodes/root_scale=1.0
nodes/import_as_skeleton_bones=false
nodes/use_name_suffixes=true
nodes/use_node_type_suffixes=true
meshes/ensure_tangents=true
meshes/generate_lods=true
meshes/create_shadow_meshes=true
meshes/light_baking=1
meshes/lightmap_texel_size=0.2
meshes/force_disable_compression=false
skins/use_named_skins=true
animation/import=true
animation/fps=30
animation/trimming=false
animation/remove_immutable_tracks=true
animation/import_rest_as_RESET=false
import_script/path="res://scripts/tools/ps2_import.gd"
materials/extract=0
materials/extract_format=0
materials/extract_path=""
_subresources={}
gltf/naming_version=2
gltf/embedded_image_handling=1
gltf/texture_map_mode=1
"""


def col(c):
    return "Color(%g, %g, %g, 1)" % c


def main():
    for _, f in PARTS + [("Backdrop", "eb_backdrop")]:
        p = os.path.join(ROOT, MODELS, f + ".gltf.import")
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(IMPORT)
    lights = json.load(open(os.path.join(ROOT, MODELS, "lights.json"), encoding="utf-8"))
    out = ['[gd_scene format=3]', '']
    for _, f in PARTS:
        out.append('[ext_resource type="PackedScene" path="res://%s/%s.gltf" id="%s"]' % (MODELS, f, f))
    out += ['[ext_resource type="PackedScene" path="res://%s/eb_backdrop.gltf" id="eb_backdrop"]' % MODELS,
            '[ext_resource type="Script" path="res://scripts/world/backdrop.gd" id="bd"]',
            '[ext_resource type="PackedScene" path="res://scenes/props/street_light.tscn" id="sl"]', '',
            '[node name="EastBridgeLocation" type="Node3D"]', '']
    for node, f in PARTS:
        out += ['[node name="%s" parent="." instance=ExtResource("%s")]' % (node, f), '']
    out += ['[node name="Backdrop" type="Node3D" parent="."]', 'script = ExtResource("bd")', '',
            '[node name="Model" parent="Backdrop" instance=ExtResource("eb_backdrop")]', '',
            '[node name="Lights" type="Node3D" parent="."]', '']
    count = {}
    overrides = []
    for L in lights:
        name, energy, rng, angle = KINDS[L["kind"]]
        count[name] = count.get(name, 0) + 1
        n = "%s%d" % (name, count[name])
        b, h = L["base"], L["head"]
        off = (h[0] - b[0], h[1] - b[1], h[2] - b[2])
        out += ['[node name="%s" parent="Lights" instance=ExtResource("sl")]' % n,
                'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, %g, %g, %g)' % tuple(b),
                'color = %s' % col(PALE_GREEN if (L["kind"], L["color"]) == ("bridge", "green") else COLORS[L["color"]]),
                'energy = %g' % energy,
                'head_offset = Vector3(%g, %g, %g)' % off]
        if (name, count[name]) in FLICKER:
            out.append('flicker = true')
        out.append('')
        if rng:
            overrides += ['[node name="Spot" parent="Lights/%s"]' % n, 'spot_range = %g' % rng, 'spot_angle = %g' % angle, '']
    out += overrides
    path = os.path.join(ROOT, "scenes", "east_bridge", "eb_location.tscn")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out))
    print("lights:", count)


if __name__ == "__main__":
    main()
