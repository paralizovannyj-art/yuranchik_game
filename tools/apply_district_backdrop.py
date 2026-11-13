# -*- coding: utf-8 -*-
# Этап E (docs/CITY_PLAN.md): подключает декорации за краем района. Повторный запуск безопасен.
#   - district.tscn: узел Backdrop (scenes/district/backdrop.tscn — дальние дома, ТЭЦ, балка, огни);
#   - terrain.tscn: плоская земля южнее района убрана из вида (её место занимает балка из модели фона),
#     боковые плиты OuterW/OuterE укорочены до южного края района.
#   python tools/apply_district_backdrop.py
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def patch(rel, fn):
    path = os.path.join(ROOT, rel)
    s = open(path, encoding="utf-8").read()
    t = fn(s)
    if t != s:
        open(path, "w", encoding="utf-8", newline="\n").write(t)
    print("%-32s %s" % (rel, "изменён" if t != s else "без изменений"))


def root_scene(s):
    if "backdrop.tscn" in s:
        return s
    a = '[ext_resource type="PackedScene" path="res://scenes/district/z8_west_yard.tscn" id="z8_west_yard"]'
    assert a in s
    s = s.replace(a, a + '\n[ext_resource type="PackedScene" path="res://scenes/district/backdrop.tscn" id="backdrop"]')
    return s.rstrip("\n") + '\n\n[node name="Backdrop" parent="." instance=ExtResource("backdrop")]\n'


def terrain(s):
    for name, x in (("OuterW", "-400.5"), ("OuterE", "400.5")):
        a = ('[node name="%s" type="Node3D" parent="."]\ntransform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, %s, -20, 0)\n'
             'script = ExtResource("bb")\nsize = Vector3(599, 20, 1400)' % (name, x))
        if a in s:      # было Z -700…700, стало Z -700…102: южнее начинается балка
            s = s.replace(a, a.replace("-20, 0)", "-20, -299)").replace("1400)", "802)"))
    a = 'size = Vector3(202, 8, 598)\nkind = "ground"\n'
    if a in s and a + "show_mesh = false" not in s:
        s = s.replace(a, a + "show_mesh = false\n")
    return s


patch("scenes/levels/district.tscn", root_scene)
patch("scenes/district/terrain.tscn", terrain)
