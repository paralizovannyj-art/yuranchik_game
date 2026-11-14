# -*- coding: utf-8 -*-
# Квартал за гаражами (docs/CITY_PLAN.md, зона 6): с крыш гаражей горизонт закрывают дома — много разных,
# в три ряда вглубь, с просветами, в которых видны дома следующего ряда. Без этого за гаражами
# открывалась пустая балка, а дальние дома стояли в 350+ м тонкой полосой.
#
# Дома — готовые модели района (девятиэтажки, хрущёвки, башня) из assets/models/district/*.gltf.
# Они стоят за бровкой балки (z > 102): дойти до них нельзя, основание ниже бровки и с гаражей не видно.
# Туман сцены действует на них как на остальной район — дальние ряды уходят в дымку.
#
# Пишет узел SouthBlocks в scenes/district/z6_garages.tscn. Повторный запуск пересобирает его
# с той же раскладкой (фиксированный seed).
#   python tools/apply_district_south_blocks.py
import math
import os
import random
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCENE = os.path.join(ROOT, "scenes", "district", "z6_garages.tscn")
R = random.Random(20261114)

# модель → длина фасада (м) и этажность (для подбора по рядам)
NINE = {"homeyard_southrow": 38.6, "homeyard_westwing": 38.6, "westyard_eastrow": 24.6, "westyard_northrow": 18.6,
        "westyard_southrow": 26.6, "westyard_westrow": 38.6, "school_eastwall": 61.6, "terrain_northfacades": 40.6}
FIVE = {"southyards_khrnorth": 54.8, "southyards_khrsouth": 43.8, "southyards_khrwest": 32.8,
        "homeyard_eastkhr": 18.8, "boilerhouse_khr1": 28.8}
TOWER = {"westyard_tower": 16.6}
DEPTH = 15.0                     # глубина корпуса — для домов, стоящих торцом
X0, X1 = -330.0, 330.0           # за гаражами (−100…100) и с запасом по бокам — для косых взглядов с крыш

# ряд: (z от, z до, высота основания, веса типов (9 эт., 5 эт., башня), промежутки между домами, доля «торцом»)
ROWS = [
    (110, 120, -14.0, (0.65, 0.25, 0.10), (4, 12), 0.2),
    (138, 152, -17.0, (0.60, 0.10, 0.30), (6, 18), 0.25),
    (170, 188, -21.0, (0.50, 0.00, 0.50), (10, 26), 0.3),
]


def pick(weights):
    kind = R.choices(("nine", "five", "tower"), weights=weights)[0]
    pool = {"nine": NINE, "five": FIVE, "tower": TOWER}[kind]
    name = R.choice(sorted(pool))
    return name, pool[name]


def layout():
    out = []
    for z0, z1, y, weights, gap, side_ratio in ROWS:
        x = X0 + R.uniform(0, 20)
        while x < X1:
            name, length = pick(weights)
            side = name not in TOWER and R.random() < side_ratio
            span = DEPTH if side else length
            cx = x + span / 2
            cz = R.uniform(z0, z1)
            yaw = R.choice((0.0, 180.0)) + (90.0 if side else 0.0) + R.uniform(-4, 4)
            out.append((name, cx, y + R.uniform(-1.0, 0.5), cz, yaw))
            x += span + R.uniform(*gap)
    return out


def main():
    s = open(SCENE, encoding="utf-8").read()
    # убрать прежний квартал (узлы и их модели) — скрипт можно запускать повторно
    s = re.sub(r'\n\[node name="SouthBlocks" type="Node3D" parent="\."\]\n(?:.|\n)*?(?=\n\[node name="(?!SouthBlock)|\Z)', "", s)
    s = re.sub(r'\[ext_resource type="PackedScene" path="[^"]*" id="sb_[^"]*"\]\n\n', "", s)
    items = layout()
    used = sorted({n for n, *_ in items})
    res = "".join('[ext_resource type="PackedScene" path="res://assets/models/district/%s.gltf" id="sb_%s"]\n\n' % (n, n)
                  for n in used)
    i = s.index('[node name="Garages"')
    s = s[:i] + res + s[i:]
    nodes = '\n[node name="SouthBlocks" type="Node3D" parent="."]\n'
    for k, (n, x, y, z, yaw) in enumerate(items):
        a = math.radians(yaw)
        c, sn = math.cos(a), math.sin(a)
        nodes += ('\n[node name="SouthBlock%d" parent="SouthBlocks" instance=ExtResource("sb_%s")]\n'
                  'transform = Transform3D(%.4f, 0, %.4f, 0, 1, 0, %.4f, 0, %.4f, %.2f, %.2f, %.2f)\n'
                  % (k, n, c, sn, -sn, c, x, y, z))
    s = s.rstrip("\n") + "\n" + nodes
    open(SCENE, "w", encoding="utf-8", newline="\n").write(s)
    print("z6_garages.tscn: домов за гаражами %d, моделей %d" % (len(items), len(used)))


main()
