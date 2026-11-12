# -*- coding: utf-8 -*-
# Собирает игровой уровень scenes/levels/yard.tscn из «теста вайба» (scenes/levels/vibe_test.tscn):
# к готовому двору добавляются враги, предметы, двери-замки, гараж Юрчика, границы и точки появления Сергея.
#
# Нужен один раз (и если переделывался vibe_test.tscn). После этого уровень правится прямо в редакторе Godot:
# врагов и предметы можно двигать мышью, а их параметры — менять в инспекторе.
#   python tools/make_yard_scene.py
import os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
src = open(os.path.join(ROOT, "scenes", "levels", "vibe_test.tscn"), encoding="utf-8").read()

# --- заголовок и корень ---
src = src.replace('[gd_scene format=3 uid="uid://cc3t5wpp7opn4"]', "[gd_scene format=3]")
src = re.sub(r' unique_id=\d+', "", src)
EXT = '''[ext_resource type="Script" path="res://scripts/levels/yard.gd" id="lvl"]
[ext_resource type="PackedScene" path="res://scenes/characters/enemy.tscn" id="enemy"]
[ext_resource type="PackedScene" path="res://scenes/characters/sergey.tscn" id="sergey"]
[ext_resource type="Script" path="res://scripts/world/interactable.gd" id="inter"]
[ext_resource type="Script" path="res://scripts/world/pickup.gd" id="pick"]
[ext_resource type="PackedScene" path="res://assets/models/garage_yur.gltf" id="gyur"]
'''
i = src.index("[sub_resource")
src = src[:i] + EXT + "\n" + src[i:]

# --- земля: плоскость-коллизия → толстая плита (по ней строится навигация врагов) ---
src = src.replace('[sub_resource type="WorldBoundaryShape3D" id="WorldBoundaryShape3D_bjkw8"]',
                  '[sub_resource type="BoxShape3D" id="WorldBoundaryShape3D_bjkw8"]\nsize = Vector3(200, 1, 200)')
src = src.replace('[node name="@CollisionShape3D@22686" type="CollisionShape3D" parent="GroundBody"]\n',
                  '[node name="GroundShape" type="CollisionShape3D" parent="GroundBody"]\ntransform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, -0.5, 0)\n')

SUBS = '''[sub_resource type="BoxShape3D" id="wall_ns"]
size = Vector3(60, 5, 1)

[sub_resource type="BoxShape3D" id="wall_ew"]
size = Vector3(1, 5, 42)

[sub_resource type="BoxShape3D" id="wall_gn"]
size = Vector3(7, 5, 3.8)

[sub_resource type="BoxShape3D" id="wall_gs"]
size = Vector3(7, 5, 13.6)

[sub_resource type="StandardMaterial3D" id="mat_counter"]
albedo_color = Color(0.13, 0.13, 0.14, 1)
metallic = 0.6
roughness = 0.5

[sub_resource type="BoxMesh" id="mesh_counter"]
material = SubResource("mat_counter")
size = Vector3(1.5, 0.05, 0.34)

'''
i = src.index('[node name="VibeTest"')
src = src[:i] + SUBS + src[i:]
src = src.replace('[node name="VibeTest" type="Node3D"]',
                  '[node name="Yard" type="Node3D"]\nscript = ExtResource("lvl")\nsergey_scene = ExtResource("sergey")\n'
                  'enemy_scene = ExtResource("enemy")\nnav_bounds = AABB(-30, -1, -10, 62, 6, 44)')

# --- игрок: старт на юге двора, лицом к дому ---
src = re.sub(r'(\[node name="Player" type="CharacterBody3D" parent="\." instance=ExtResource\("19_t5v6d"\)\]\n)transform = [^\n]*\nscript = [^\n]*\n',
             r'\1transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 24)\n', src)
assert "0, 0, 24)" in src


def T(x, y, z, yaw=0.0):
    import math
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    f = lambda v: ("%.4f" % v).rstrip("0").rstrip(".") if abs(v) > 1e-9 else "0"
    return "Transform3D(%s, 0, %s, 0, 1, 0, %s, 0, %s, %s, %s, %s)" % (f(c), f(s), f(-s), f(c), f(x), f(y), f(z))


out = []


def enemy(name, x, z, yaw=0.0, **props):
    out.append('[node name="%s" parent="Enemies" instance=ExtResource("enemy")]\ntransform = %s' % (name, T(x, 0, z, yaw)))
    for k, v in props.items():
        out.append("%s = %s" % (k, ('"%s"' % v) if isinstance(v, str) else v))
    out.append("")


def pickup(name, item, x, y, z, parent="Items", yaw=0.0):
    out.append('[node name="%s" type="Node3D" parent="%s"]\ntransform = %s\nscript = ExtResource("pick")\nitem_id = "%s"\n'
               % (name, parent, T(x, y, z, yaw), item))


def use(name, x, y, z, prompt, need="", locked="", radius=2.0, one_shot=False):
    out.append('[node name="%s" type="Node3D" parent="."]\ntransform = %s\nscript = ExtResource("inter")\nprompt = "%s"\nradius = %s'
               % (name, T(x, y, z), prompt, radius))
    if need:
        out.append('need_item = "%s"\nlocked_text = "%s"' % (need, locked))
    if one_shot:
        out.append("one_shot = true")
    out.append("")


def marker(name, x, z, yaw=0.0):
    out.append('[node name="%s" type="Marker3D" parent="."]\ntransform = %s\n' % (name, T(x, 0, z, yaw)))


# --- гараж Юрчика (в конце ряда гаражей) и то, что в нём лежит ---
out.append('[node name="GarageYur" parent="." instance=ExtResource("gyur")]\ntransform = Transform3D(0, 0, -1, 0, 1, 0, 1, 0, 0, 24, 0, 12.4)\n')
out.append('[node name="GarageLight" type="OmniLight3D" parent="GarageYur"]\ntransform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 1.8, 1.95, -0.4)\n'
           'light_color = Color(1, 0.8, 0.55, 1)\nlight_energy = 1.6\nshadow_enabled = true\nomni_range = 7.0\nomni_attenuation = 1.3\n')
pickup("KeyHome", "key_home", 1.8, 0.87, -2.4, "GarageYur")
pickup("Medkit", "medkit", 0.9, 0.87, -2.45, "GarageYur", 12)
pickup("GarageBottle", "bottle", 2.75, 0.87, -2.5, "GarageYur")

# --- прилавок ларька: ключ от гаража и шаурма ---
out.append('[node name="Counter" type="MeshInstance3D" parent="Kiosk"]\ntransform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.0, 1.15)\nmesh = SubResource("mesh_counter")\n')
pickup("KeyGarage", "key_garage", -0.3, 1.03, 1.17, "Kiosk")
pickup("Shawarma", "shawarma", 0.35, 1.03, 1.17, "Kiosk")

# --- двери и замки ---
use("HomeDoor", -4.05, 1.0, -7.3, "Открыть дверь подъезда", "key_home",
    "Заперто. Ключей в кармане нет — остались в гараже, в куртке.", 2.3)
use("GarageLock", 20.7, 1.0, 14.2, "Открыть гараж", "key_garage",
    "Навесной замок. Ключ от гаража остался у ларька «Продукты» — на прилавке.", 2.0, True)
use("OtherDoor", 4.05, 1.0, -7.3, "Дёрнуть дверь", "key_none", "Чужой подъезд. Заперто.", 2.0)

# --- предметы во дворе ---
out.append('[node name="Items" type="Node3D" parent="."]\n')
pickup("Bottle1", "bottle", -1.5, 0, 20.5)
pickup("Brick1", "brick", 2.2, 0, 21.5, yaw=30)
pickup("Bottle2", "bottle", -2.3, 0, 9.7)
pickup("Bottle3", "bottle", -7.6, 0, -0.5)
pickup("Bandage1", "bandage", -9.4, 0.03, -0.6)
pickup("Bottle4", "bottle", 8.3, 0, -0.7)
pickup("Brick2", "brick", 19.6, 0, -2.6, yaw=-20)
pickup("Bandage2", "bandage", 16.5, 0.03, 9.5)

# --- офники ---
out.append('[node name="Enemies" type="Node3D" parent="."]\n')
enemy("OfnikFirst", -2.0, 14.0, 0, variant="a", wander_radius=0.0)          # стоит спиной — можно подкрасться
enemy("OfnikLamp", -6.5, 0.8, 200, variant="b", wander_radius=0.0)
enemy("OfnikRoad", 9.0, -3.4, 90, variant="c", wander_radius=5.0)
enemy("OfnikKiosk1", -11.4, 2.2, 150, variant="c", wander_radius=0.0)
enemy("OfnikKiosk2", -14.8, 2.8, 30, variant="a", wander_radius=2.5)
enemy("OfnikGarage", 18.0, 5.0, 0, variant="b", wander_radius=4.0)
enemy("OfnikFar", 13.5, 16.0, 270, variant="c", wander_radius=3.0)

# --- точки появления: Сергей и двое офников, которые выходят наперерез у подъезда ---
marker("SergeySpawn", 9.0, 11.0, -90)
marker("AmbushA", -10.0, -4.0, 180)
marker("AmbushB", 2.5, -4.6, 180)

# --- невидимые границы двора ---
out.append('[node name="Bounds" type="StaticBody3D" parent="."]\n')
for name, shape, x, z in (("N", "wall_ns", 0, -8.5), ("S", "wall_ns", 0, 30.5), ("W", "wall_ew", -26.5, 11), ("E", "wall_ew", 27.6, 11),
                          ("GN", "wall_gn", 24.5, -6.1), ("GS", "wall_gs", 24.5, 23.0)):
    out.append('[node name="%s" type="CollisionShape3D" parent="Bounds"]\ntransform = %s\nshape = SubResource("%s")\n' % (name, T(x, 2.0, z), shape))

dst = os.path.join(ROOT, "scenes", "levels", "yard.tscn")
open(dst, "w", encoding="utf-8", newline="\n").write(src.rstrip("\n") + "\n\n" + "\n".join(out))
print("written", dst)
