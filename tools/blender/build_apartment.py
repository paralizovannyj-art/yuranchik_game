# -*- coding: utf-8 -*-
# Квартира 47: прихожая и узкий коридор от входной двери до двери в комнату Юрчика — по двум фото настоящей квартиры
# (docs/references/apartment/hall_1_to_room.webp — к комнате, hall_2_to_entrance.webp — к выходу; план —
# docs/references/apartment/plan_options.svg, выбран вариант А).
#
# Что на фото (квартира Г-образная):
#   * прихожая от входной двери: тёмно-коричневая входная дверь, над ней бра, рядом выключатель; на полу длинная
#     тёмно-зелёная ковровая дорожка с узором из листьев винограда и лоз, со светлой каймой;
#     вдоль одной стены — бежевый шкаф-купе почти до потолка, открытая полочка с жёлтой лампой, гора пакетов и обуви,
#     над полочкой картина и постер с собакой; вдоль другой — двустворчатая дверь с янтарным рифлёным стеклом
#     (перед ней пылесос и плетёная корзина), крючки с зонтом, узкая белая дверь у входа;
#   * в конце прихожей — выступ стены (угол в белой крупной «шубе») и балка над проходом; за ним поворот налево
#     в узкий коридор (~1 м): пол — ламинат «под дерево», коричневый плинтус, справа чёрная тумбочка и две белые
#     филёнчатые двери, в конце — дверь комнаты Юрчика (со стеклом и полотенцем, build_room_door.py);
#   * отделка везде одна: стены — бежево-жёлтая декоративная штукатурка «под камень» (крупные плиты с трещинами-швами,
#     рельеф), потолок — белый с голубоватыми разводами («иней»), по периметру белый потолочный карниз.
#
# Этот скрипт строит ОБОЛОЧКУ: стены с проёмами дверей, выступ и балку, пол, потолок, карнизы, плинтусы, дорожку.
# Двери, мебель и мелочь — отдельные модели (шаг 2). Комната Юрчика — build_yurchik_room.py, в stairwell.tscn она
# повёрнута на 90° (узел YurchikRoom) так, что её дверь — в конце коридора.
#
# Координаты Blender (как у подъезда, build_mvp_assets.py): Z вверх, пол квартиры z = 8.4, потолок 2.7 м.
#   прихожая  x −7.3…−3.2, y 0.45…2.2   (вход — стена x = −3.2, проём y 0.8…1.7, как DOOR_Y0..DOOR_Y1 подъезда)
#   коридор   x −7.3…−6.3, y −2.18…0.45 (в конце — проём двери комнаты x −7.25…−6.40)
#   выступ    x −6.3…−6.0, y 0.45…0.70; балка над входом в коридор x −7.3…−6.3, y 0.45…0.70, низ на z 10.75
# В Godot: (x, y, z)_Blender → (x, z, −y)_Godot.
#
# Запуск — только через Blender MCP (живой Blender), строит в отдельной сцене «Apartment», открытый файл не трогает:
#   exec(open(r"<корень>/tools/blender/build_apartment.py", encoding="utf-8").read(),
#        {"__file__": r"<корень>/tools/blender/build_apartment.py", "__name__": "__main__"})
# Результат: assets/textures/ap_*.png и квартира по предметам — assets/models/apartment/<предмет>.gltf
# (точка опоры у основания по центру) + assets/models/apartment/layout.json (позиции в координатах Godot).
# Имена объектов: <Предмет> — с коллизией (Godot строит её по сетке, ps2_import.gd), <Предмет>_nocol — без коллизии.
import bpy, os, sys, math, json
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from tex_lib import save
from ps2_hero import C, finish
from ps2_style import noise, smoothstep, mottle, blur

_ns = {"NO_MAIN": True, "__file__": os.path.join(HERE, "build_yard.py")}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), _ns)
B, mat = _ns["B"], _ns["mat"]
OUT = os.path.join(ROOT, "assets", "models")
ITEM_DIR = os.path.join(OUT, "apartment")

# --- размеры (см. шапку) ---
Z, H = 8.4, 2.7
ZT = Z + H
HX0, HX1, HY0, HY1 = -7.3, -3.2, 0.45, 2.2          # прихожая
CX0, CX1, CY0 = -7.3, -6.3, -2.18                    # коридор (до наружной грани стены комнаты)
PX1, PY1 = -6.0, 0.70                                # выступ: x CX1…PX1, y HY0…PY1
BEAM_Z = Z + 2.35                                    # низ балки над входом в коридор
T = 0.12                                             # глубина проёмов (толщина стены у дверей)
DH = 2.05                                            # высота дверных проёмов
# проёмы: (начало, конец, высота, сквозной?) — вдоль стены
ENTRY = (0.8, 1.7)                                   # входная дверь (стена x = HX1), сквозной в подъезд
ROOM_DOOR = (-7.25, -6.40)                           # дверь комнаты (стена y = CY0), сквозной в комнату
DOUBLE_DOOR = (-5.90, -4.70)                         # двустворчатая со стеклом (стена y = HY0)
WC_DOOR = (-4.00, -3.40)                             # узкая белая у входа (стена y = HY0)
WEST_DOORS = ((0.60, 1.40), (-1.90, -1.10))          # две белые двери справа по коридору (стена x = HX0)
RUNNER = (-6.45, -3.55, 0.85, 1.67)                  # ковровая дорожка x0, x1, y0, y1


# =====================================================================================
#  Текстуры (низкое разрешение, PS2: мягко, 15-битный цвет — finish())
# =====================================================================================
def _voronoi(w, h, n, rng, jitter=0.85, ny=None):
    """Тайлящийся Вороной: расстояния до ближайшей и второй точки (в пикселях) и номер клетки.
    n клеток по ширине, ny — по высоте (по умолчанию столько же)."""
    ny = ny or n
    cw, ch = w / n, h / ny
    P = (np.stack(np.meshgrid(np.arange(n), np.arange(ny), indexing="xy"), -1) + 0.5
         + (rng.random((ny, n, 2)) - 0.5) * jitter) * np.array([cw, ch])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    gx, gy = (xx // cw).astype(int), (yy // ch).astype(int)
    d1 = np.full((h, w), 1e9, np.float32); d2 = d1.copy(); idx = np.zeros((h, w), int)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            cx_, cy_ = gx + ox, gy + oy
            px = P[cy_ % ny, cx_ % n, 0] + np.floor_divide(cx_, n) * w
            py = P[cy_ % ny, cx_ % n, 1] + np.floor_divide(cy_, ny) * h
            d = np.hypot(xx - px, yy - py)
            cid = (cy_ % ny) * n + (cx_ % n)
            closer = d < d1
            d2 = np.where(closer, d1, np.minimum(d2, d)); idx = np.where(closer, cid, idx); d1 = np.minimum(d1, d)
    return d1, d2, idx


def tex_wall():
    """Стены: бежево-жёлтая декоративная штукатурка «под камень» (как на обоих фото): крупные плиты 0.5–0.7 м,
    чуть вытянутые по горизонтали, как кладка; между ними тонкие бледные швы-трещины с тенью снизу и светлой кромкой
    сверху (рельеф «запечён», свет сверху-слева); плиты немного разного тона, мелкая рельефная шероховатость,
    тёплые желтовато-зелёные разводы. Тайл 2 x 2 м, 256 px."""
    rng = np.random.default_rng(4701)
    w = h = 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    wx = (noise(w, h, 5, 5, rng, oct=3) - 0.5) * 14
    wy = (noise(w, h, 5, 5, rng, oct=3) - 0.5) * 10
    d1, d2, idx = _voronoi(w, h, 3, rng, 0.8, ny=4)
    sx = ((xx + wx) % w).astype(int); sy = ((yy + wy) % h).astype(int)
    d1, d2, idx = d1[sy, sx], d2[sy, sx], idx[sy, sx]
    edge = d2 - d1                                                   # 0 на шве
    seam = np.exp(-(edge / 1.1) ** 2)
    below = np.clip(np.roll(seam, -1, 0) - seam, 0, 1)               # тень у нижнего края шва
    above = np.clip(np.roll(np.roll(seam, 2, 0), 1, 1) - seam, 0, 1) # светлая кромка сверху
    tone = (0.93 + 0.12 * rng.random(16).astype(np.float32))[idx]
    arr = np.ones((h, w, 3), np.float32) * C(0.87, 0.79, 0.58)
    arr *= tone[..., None]
    arr *= (0.95 + 0.05 * smoothstep(0.0, 16.0, edge))[..., None]   # плита чуть выпуклая
    # мелкий рельеф «шпателя»: бугорки с тенью
    bump = noise(w, h, 48, 48, rng, oct=2)
    relief = bump - np.roll(np.roll(bump, 1, 0), 1, 1)
    arr *= (0.98 + 0.6 * relief)[..., None]
    arr *= (0.93 + 0.10 * noise(w, h, 12, 12, rng, oct=3))[..., None]
    arr *= (1 + 0.18 * above)[..., None]
    arr *= (1 - 0.32 * seam - 0.15 * below)[..., None]
    # тонкие волосяные трещины внутри плит (не везде)
    n2 = noise(w, h, 6, 6, rng, oct=3)
    hair = np.exp(-((n2 - 0.5) / 0.006) ** 2) * smoothstep(0.58, 0.72, noise(w, h, 3, 3, rng, oct=2))
    arr *= (1 - 0.22 * hair)[..., None]
    # разводы: местами светлее, местами желто-зелёные потемнения
    arr *= mottle(h, w, rng, 2, 0.12)[..., None]
    patina = smoothstep(0.55, 0.8, noise(w, h, 3, 3, rng, oct=3))
    arr = arr * (1 - 0.12 * patina[..., None] * C(0.3, 0.15, 0.9))
    save("ap_wall", finish(arr, 1.1, crisp=0.35))


def tex_coarse():
    """Выступ стены: белая крупная фактурная штукатурка «шуба» (фото 2, справа на переднем плане). Тайл 1 м, 128 px."""
    rng = np.random.default_rng(4702)
    w = h = 128
    bumps = blur(noise(w, h, 24, 24, rng, oct=3)[..., None], 0.7)[..., 0]
    hl = np.clip(bumps - np.roll(np.roll(bumps, 1, 0), 1, 1), -1, 1)      # свет сверху-слева
    arr = np.ones((h, w, 3), np.float32) * C(0.84, 0.81, 0.73)
    arr *= (0.86 + 0.28 * smoothstep(0.35, 0.7, bumps))[..., None]
    arr *= (1 + 2.2 * hl)[..., None]
    arr *= (0.94 + 0.08 * noise(w, h, 4, 4, rng, oct=2))[..., None]
    save("ap_coarse", finish(arr, 1.05, crisp=0.5))


def tex_ceiling():
    """Потолок: белая фактурная штукатурка с голубовато-серыми разводами «иней» (оба фото): извилистые пятна
    шпателя, у края пятна тень. Тайл 2 x 2 м, 256 px."""
    rng = np.random.default_rng(4703)
    w = h = 256
    wx = noise(w, h, 5, 5, rng, oct=3); wy = noise(w, h, 5, 5, rng, oct=3)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sx = ((xx + (wx - 0.5) * 60) % w).astype(int); sy = ((yy + (wy - 0.5) * 60) % h).astype(int)
    n = noise(w, h, 9, 9, rng, oct=4)[sy, sx]
    frost = smoothstep(0.56, 0.62, n) * (1 - smoothstep(0.66, 0.74, n))            # «лепестки» разводов
    frost = np.maximum(frost, 0.5 * smoothstep(0.30, 0.33, n) * (1 - smoothstep(0.35, 0.40, n)))
    shade = np.clip(np.roll(np.roll(frost, -2, 0), -2, 1) - frost, 0, 1)
    arr = np.ones((h, w, 3), np.float32) * C(0.90, 0.90, 0.87)
    blue = C(0.68, 0.78, 0.80)
    arr = arr * (1 - frost[..., None] * 0.6) + blue * frost[..., None] * 0.6
    arr *= (1 - 0.18 * shade)[..., None]
    arr *= (0.94 + 0.08 * noise(w, h, 30, 30, rng, oct=2))[..., None]
    arr *= mottle(h, w, rng, 2, 0.08)[..., None]
    save("ap_ceiling", finish(arr, 1.2, crisp=0.3))


def tex_laminate():
    """Ламинат «под дерево» (фото 1): тёплые медово-рыжие доски 1.2 x 0.2 м вразбежку, тёмные волокна, тёмные стыки,
    доски заметно разного тона, у стен грязнее. Тайл 2 x 2 м, 256 px."""
    rng = np.random.default_rng(4704)
    w = h = 256
    rows = 10
    rh = h / rows
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    row = (yy // rh).astype(int)
    shift = (rng.random(rows) * w).astype(np.float32)
    PL = 154.0                                                       # 1.2 м
    xs = (xx + shift[row]) % w
    plank = (xs // PL).astype(int) + row * 7
    tone = (0.80 + 0.32 * rng.random(200)).astype(np.float32)
    grain = noise(w, h, 3, 60, rng, oct=4)
    arr = np.ones((h, w, 3), np.float32) * C(0.80, 0.54, 0.34)
    arr *= tone[plank % 200][..., None]
    arr *= (0.80 + 0.30 * grain)[..., None]
    streak = np.abs(np.sin((yy + grain * 30 + plank * 3.1) * 1.3)) < 0.12        # тёмные «волокна»
    arr[streak] *= 0.82
    fy = yy % rh; fx = xs % PL
    arr[fy < 1.0] *= 0.5; arr[(fy >= 1.0) & (fy < 2.0)] *= 1.05
    arr[fx < 1.2] *= 0.55
    arr *= mottle(h, w, rng, 2, 0.12)[..., None]
    save("ap_laminate", finish(arr, 1.1, crisp=0.35))


def tex_runner():
    """Ковровая дорожка (оба фото): тёмно-зелёное поле, по нему решётка из виноградных листьев (бурые с оливковым)
    на тонких лозах-завитках, кайма — светлая оливково-бежевая полоса и тёмная кромка. Одна текстура на всю
    дорожку 0.82 x 2.9 м (128 x 448 px), u — поперёк, v — вдоль."""
    rng = np.random.default_rng(4705)
    w, h = 128, 448
    pm = w / (RUNNER[3] - RUNNER[2])                                 # пикселей на метр
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    field = C(0.10, 0.20, 0.15)
    arr = np.ones((h, w, 3), np.float32) * field
    arr *= (0.85 + 0.25 * noise(w, h, 12, 40, rng, oct=3))[..., None]
    # лозы: синусоиды вдоль дорожки
    for k, ph in ((0.30, 0.0), (0.70, math.pi)):
        cx = w * k + 10 * np.sin(yy / (0.14 * pm) + ph)
        vine = np.exp(-((xx - cx) / 1.1) ** 2)
        arr = arr * (1 - vine[..., None] * 0.6) + C(0.38, 0.36, 0.22) * vine[..., None] * 0.6
    # листья: решётка ромбом, 5-лопастная «ладошка» с прожилками
    cell = 0.20 * pm
    inner0, inner1 = 15, w - 15
    for j in range(int(h / cell) + 2):
        for i in range(3):
            cx = inner0 + (i + 0.5 * (j % 2)) * (inner1 - inner0) / 2.5 + rng.uniform(-3, 3)
            cy = j * cell + rng.uniform(-3, 3)
            if not (inner0 + 4 < cx < inner1 - 4):
                continue
            ang = rng.uniform(-0.6, 0.6) + (math.pi if j % 2 else 0.0)
            dx, dy = xx - cx, yy - cy
            r = np.hypot(dx, dy); th = np.arctan2(dy, dx) - ang
            R_ = 0.085 * pm * (0.62 + 0.38 * np.abs(np.cos(2.5 * th)))
            leaf = smoothstep(1.0, 0.85, r / R_)
            col = C(0.36, 0.26, 0.15) if (i + j) % 3 else C(0.40, 0.38, 0.20)
            vein = (np.abs(np.sin(th * 2.5)) < 0.12) & (r < R_ * 0.9)
            lc = np.ones((h, w, 3), np.float32) * col
            lc[vein] *= 0.6
            arr = arr * (1 - leaf[..., None]) + lc * leaf[..., None]
            # гроздь «ягод» рядом с листом
            bx, by = cx + math.cos(ang + 2.2) * 0.07 * pm, cy + math.sin(ang + 2.2) * 0.07 * pm
            for q in range(5):
                ox_, oy_ = bx + rng.uniform(-4, 4), by + rng.uniform(-4, 4)
                berry = smoothstep(2.6, 1.8, np.hypot(xx - ox_, yy - oy_))
                arr = arr * (1 - berry[..., None]) + C(0.30, 0.30, 0.20) * berry[..., None]
    # кайма: тёмная кромка, светлая полоса, тонкая тёмная, узорчик «волной»
    e = np.minimum(xx, w - 1 - xx); ev = np.minimum(yy, h - 1 - yy)
    edge = np.minimum(e, ev)
    band = (edge >= 3) & (edge < 9)
    arr[edge < 3] = C(0.06, 0.12, 0.09)
    arr[band] = C(0.52, 0.48, 0.30) * (0.9 + 0.15 * np.sin(np.where(e < ev, yy, xx) / 2.2))[band][..., None]
    arr[(edge >= 9) & (edge < 10)] = C(0.10, 0.16, 0.10)
    arr *= (0.9 + 0.15 * noise(w, h, 4, 14, rng, oct=2))[..., None]                # затоптано
    save("ap_runner", finish(arr, 1.05, crisp=0.35))


TRIM = {"plinth": (0, 0, 64, 16), "molding": (0, 16, 64, 32), "dark": (0, 32, 64, 48), "white": (0, 48, 64, 64)}


def RT(name):
    x0, y0, x1, y1 = TRIM[name]
    return (x0 / 64, 1 - y1 / 64, x1 / 64, 1 - y0 / 64)


def tex_trim():
    """Мелкий атлас: коричневый плинтус (фото 1), белый потолочный карниз с тенью в изгибе, тёмная «пустота» за
    закрытыми дверями, белая краска (наличники)."""
    rng = np.random.default_rng(4706)
    a = np.zeros((64, 64, 3), np.float32)
    yy, xx = np.mgrid[0:16, 0:64].astype(np.float32)
    pl = np.ones((16, 64, 3), np.float32) * C(0.30, 0.12, 0.07) * (0.85 + 0.25 * noise(64, 16, 8, 2, rng, oct=2))[..., None]
    pl[:3] *= 1.35; pl[3:4] *= 0.7                                                   # скруглённый верх с бликом
    a[0:16] = pl
    mo = np.ones((16, 64, 3), np.float32) * C(0.88, 0.87, 0.84)
    mo *= (0.70 + 0.30 * np.abs(np.sin(yy / 16 * math.pi * 1.5)))[..., None]       # профиль карниза: тени в изгибах
    a[16:32] = mo
    a[32:48] = C(0.03, 0.025, 0.02)
    a[48:64] = C(0.82, 0.81, 0.77) * (0.95 + 0.08 * noise(64, 16, 6, 2, rng, oct=2))[..., None]
    save("ap_trim", finish(a, 1.0, crisp=0.2))


# =====================================================================================
#  Геометрия
# =====================================================================================
def camel(item):
    return "".join(w_.capitalize() for w_ in item.split("_"))


class Items:
    """Предметы квартиры: I("shell") — сетка с коллизией, I("trim", nocol=True) — без коллизии (…_nocol)."""
    def __init__(self):
        self.items = {}

    def __call__(self, item, nocol=False):
        parts = self.items.setdefault(item, {})
        key = "nocol" if nocol else "solid"
        if key not in parts:
            parts[key] = (B(), camel(item) + ("_nocol" if nocol else ""))
        return parts[key][0]


def export(name, obs):
    sc = bpy.context.scene
    for o in sc.objects:
        o.select_set(o in obs)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".gltf"), use_selection=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)


def export_items(I, coll):
    """Каждый предмет — своя коллекция ap_<имя>, точка опоры у основания по центру, свой .gltf; layout.json — позиции в Godot."""
    os.makedirs(ITEM_DIR, exist_ok=True)
    layout = {}
    for item, parts in I.items.items():
        sub = bpy.data.collections.new("ap_" + item)
        coll.children.link(sub)
        for (_, nm) in parts.values():                    # сетки с прошлой сборки — иначе имена станут «.001»
            for me in [m_ for m_ in bpy.data.meshes if m_.name == nm or m_.name.startswith(nm + ".")]:
                if me.users == 0:
                    bpy.data.meshes.remove(me)
        obs = [b.build(nm, sub) for (b, nm) in parts.values()]
        pts = [v.co for ob in obs for v in ob.data.vertices]
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        A = Vector((round((lo[0] + hi[0]) / 2, 3), round((lo[1] + hi[1]) / 2, 3), round(lo[2], 3)))
        for ob in obs:
            ob.data.transform(Matrix.Translation(-A))
        export(os.path.join("apartment", item), obs)
        for ob in obs:
            ob.location = A
        layout[item] = [round(A.x, 3), round(A.z, 3), round(-A.y, 3)]      # Blender Z-up → Godot Y-up
    with open(os.path.join(ITEM_DIR, "layout.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    return layout


def wall(b, M, axis, c, n, s0, s1, openings=(), tex="wall", z0=Z, z1=ZT, scale=(2.0, 2.0), reveals=True):
    """Стена-плоскость (видна только изнутри квартиры).
    axis — 'x' (стена x = c, вдоль y) или 'y' (стена y = c, вдоль x); n = +1/−1 — куда смотрит лицевая сторона;
    s0..s1 — протяжённость вдоль стены; openings — [(a, b, высота, сквозной)]: у каждого проёма откосы глубиной T,
    у глухого (закрытая дверь-декор) в глубине тёмная заглушка."""
    m = M[tex]
    key = ('+' if n > 0 else '-') + axis.upper()
    def box(sa, sb, za, zb, d0, d1, faces):
        if axis == 'x':
            b.box((min(d0, d1), sa, za), (max(d0, d1), sb, zb), faces, scale=scale)
        else:
            b.box((sa, min(d0, d1), za), (sb, max(d0, d1), zb), faces, scale=scale)
    sk = 'Y' if axis == 'x' else 'X'                                  # ось вдоль стены
    cuts = sorted(openings)
    s = s0
    for (a, bb, oh, through) in cuts:
        if a > s:
            box(s, a, z0, z1, c, c - n * 0.01, {key: m})
        box(a, bb, z0 + oh, z1, c, c - n * 0.01, {key: m})           # над проёмом
        back = c - n * T
        if not reveals:                                               # откосы рисует соседняя модель (подъезд)
            s = bb
            continue
        box(a - 0.01, a, z0, z0 + oh, back, c, {'+' + sk: m})         # откосы
        box(bb, bb + 0.01, z0, z0 + oh, back, c, {'-' + sk: m})
        box(a, bb, z0 + oh, z0 + oh + 0.01, back, c, {'-Z': m})
        if not through:
            box(a, bb, z0, z0 + oh, back, back - n * 0.01, {key: (M["trim"], RT("dark"))})
        s = bb
    if s < s1:
        box(s, s1, z0, z1, c, c - n * 0.01, {key: m})


def strip(b, M, axis, c, n, segs, kind):
    """Плинтус (kind='plinth', у пола) или карниз (kind='molding', под потолком, скос 45°) вдоль стены."""
    tr = (M["trim"], RT(kind))
    for (sa, sb) in segs:
        if sb - sa < 0.02:
            continue
        if kind == "plinth":
            if axis == 'x':
                b.box((min(c, c + n * 0.015), sa, Z), (max(c, c + n * 0.015), sb, Z + 0.07),
                      {('+' if n > 0 else '-') + 'X': tr, '+Z': tr})
            else:
                b.box((sa, min(c, c + n * 0.015), Z), (sb, max(c, c + n * 0.015), Z + 0.07),
                      {('+' if n > 0 else '-') + 'Y': tr, '+Z': tr})
        else:
            d = 0.075
            u0, v0, u1, v1 = tr[1]
            if axis == 'x':
                p = [(c, sa, ZT - d), (c, sb, ZT - d), (c + n * d, sb, ZT), (c + n * d, sa, ZT)]
                if n < 0: p = [p[1], p[0], p[3], p[2]]
            else:
                p = [(sb, c, ZT - d), (sa, c, ZT - d), (sa, c + n * d, ZT), (sb, c + n * d, ZT)]
                if n < 0: p = [p[1], p[0], p[3], p[2]]
            b.poly([Vector(q) for q in p], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], tr[0])


def gaps(s0, s1, holes, pad=0.08):
    """Отрезки стены s0..s1 без дверных проёмов (с наличником pad)."""
    out, s = [], s0
    for (a, b_) in sorted(holes):
        if a - pad > s:
            out.append((s, a - pad))
        s = max(s, b_ + pad)
    if s < s1:
        out.append((s, s1))
    return out


def apartment(M):
    coll = bpy.context.scene.collection
    I = Items()
    sh = I("apartment_shell")
    tr = I("apartment_trim", nocol=True)

    # --- пол: ламинат в прихожей и коридоре, порог под входной дверью до плиты подъезда ---
    sh.box((HX0, HY0, Z - 0.1), (HX1, HY1, Z), {'+Z': M["laminate"]}, scale=(2.0, 2.0))
    sh.box((CX0, CY0, Z - 0.1), (CX1, HY0, Z), {'+Z': M["laminate"]}, scale=(2.0, 2.0))
    sh.box((HX1, ENTRY[0], Z - 0.1), (HX1 + 0.2, ENTRY[1], Z), {'+Z': M["laminate"]}, scale=(2.0, 2.0))
    # --- потолок ---
    sh.box((HX0, HY0, ZT), (HX1, HY1, ZT + 0.1), {'-Z': M["ceiling"]}, scale=(2.0, 2.0))
    sh.box((CX0, CY0, ZT), (CX1, HY0, ZT + 0.1), {'-Z': M["ceiling"]}, scale=(2.0, 2.0))

    # --- стены ---
    wall(sh, M, 'y', HY1, -1, HX0, HX1)                                                    # северная: шкаф, полочка
    wall(sh, M, 'x', HX1, -1, HY0, HY1, [(ENTRY[0], ENTRY[1], DH, True)], reveals=False)  # с входной дверью (откосы — у подъезда)
    wall(sh, M, 'y', HY0, +1, PX1, HX1, [(DOUBLE_DOOR[0], DOUBLE_DOOR[1], DH, False),        # южная: двустворчатая,
                                         (WC_DOOR[0], WC_DOOR[1], DH, False)])               # узкая белая
    wall(sh, M, 'x', HX0, +1, CY0, HY1, [(a, b_, DH, False) for (a, b_) in WEST_DOORS])     # западная: две двери
    wall(sh, M, 'x', CX1, -1, CY0, HY0)                                                    # левая стена коридора
    wall(sh, M, 'y', CY0, +1, CX0, CX1, [(ROOM_DOOR[0], ROOM_DOOR[1], DH, True)])          # торец: дверь комнаты
    # --- выступ (угол в «шубе») и балка над входом в коридор ---
    co = M["coarse"]
    sh.box((CX1, HY0, Z), (PX1, PY1, ZT), {'+Y': co, '+X': co, '-X': co}, scale=(1.0, 1.0))
    sh.box((CX0, HY0, BEAM_Z), (CX1, PY1, ZT), {'+Y': M["wall"], '-Y': M["wall"], '-Z': M["wall"]}, scale=(2.0, 2.0))

    # --- плинтусы (коричневые) и потолочный карниз (белый) ---
    south_holes = [DOUBLE_DOOR, WC_DOOR]
    strip(tr, M, 'y', HY1, -1, [(HX0, HX1)], "plinth")
    strip(tr, M, 'x', HX1, -1, gaps(HY0, HY1, [ENTRY]), "plinth")
    strip(tr, M, 'y', HY0, +1, gaps(PX1, HX1, south_holes), "plinth")
    strip(tr, M, 'x', HX0, +1, gaps(CY0, HY1, WEST_DOORS), "plinth")
    strip(tr, M, 'x', CX1, -1, [(CY0, PY1)], "plinth")
    strip(tr, M, 'y', PY1, +1, [(CX1, PX1)], "plinth")
    strip(tr, M, 'x', PX1, +1, [(HY0, PY1)], "plinth")
    strip(tr, M, 'y', CY0, +1, gaps(CX0, CX1, [ROOM_DOOR]), "plinth")
    strip(tr, M, 'y', HY1, -1, [(HX0, HX1)], "molding")
    strip(tr, M, 'x', HX1, -1, [(HY0, HY1)], "molding")
    strip(tr, M, 'y', HY0, +1, [(PX1, HX1)], "molding")
    strip(tr, M, 'y', PY1, +1, [(CX1, PX1)], "molding")
    strip(tr, M, 'x', HX0, +1, [(CY0, HY0), (PY1, HY1)], "molding")
    strip(tr, M, 'x', CX1, -1, [(CY0, HY0)], "molding")
    strip(tr, M, 'y', CY0, +1, [(CX0, CX1)], "molding")

    # --- ковровая дорожка: тонкая, без коллизии, одна текстура на всю длину ---
    x0, x1, y0, y1 = RUNNER
    rn = I("runner", nocol=True)
    rn.poly([Vector((x0, y0, Z + 0.006)), Vector((x1, y0, Z + 0.006)), Vector((x1, y1, Z + 0.006)), Vector((x0, y1, Z + 0.006))],
            [(0, 0), (0, 1), (1, 1), (1, 0)], M["runner"])                      # v — вдоль дорожки (по x)

    layout = export_items(I, coll)
    return {"items": len(layout), "layout": layout,
            "polys": {k: sum(len(b.f) for (b, _) in v.values()) for k, v in I.items.items()}}


def main():
    sc = bpy.data.scenes.get("Apartment") or bpy.data.scenes.new("Apartment")
    bpy.context.window.scene = sc
    bpy.context.view_layer.update()
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(sc.collection.children):
        if c.name.startswith("ap_"):
            bpy.data.collections.remove(c)
    tex_wall(); tex_coarse(); tex_ceiling(); tex_laminate(); tex_runner(); tex_trim()
    M = {
        "wall": mat("ApWall", "ap_wall"), "coarse": mat("ApCoarse", "ap_coarse"),
        "ceiling": mat("ApCeiling", "ap_ceiling"), "laminate": mat("ApLaminate", "ap_laminate", rough=0.5),
        "runner": mat("ApRunner", "ap_runner"), "trim": mat("ApTrim", "ap_trim", rough=0.7),
    }
    res = apartment(M)
    vl = sc.view_layers[0]
    for o in sc.objects:                                     # не оставлять выделение: другой экспорт его подхватит
        o.select_set(False, view_layer=vl)
    vl.objects.active = None
    print("BUILD_APARTMENT " + json.dumps(res))
    return res


if __name__ == "__main__":
    RESULT = main()
