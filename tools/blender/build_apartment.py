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
#   * в конце прихожей — выступ стены (та же штукатурка, что и стены) (балки над проходом нет); за ним поворот налево
#     в узкий коридор (~1 м): пол — ламинат «под дерево», коричневый плинтус, справа чёрная тумбочка и две белые
#     филёнчатые двери, в конце — дверь комнаты Юрчика (со стеклом и полотенцем, build_room_door.py);
#   * отделка везде одна: стены — бежево-жёлтая декоративная штукатурка «под камень» (крупные плиты с трещинами-швами,
#     рельеф), потолок — белый с голубоватыми разводами («иней»), по периметру белый потолочный карниз.
#
# Этот скрипт строит ОБОЛОЧКУ: стены с проёмами дверей, выступ, пол, потолок, карнизы, плинтусы, дорожку.
# Двери, мебель и мелочь — отдельные модели (шаг 2). Комната Юрчика — build_yurchik_room.py, в stairwell.tscn она
# повёрнута на 90° (узел YurchikRoom) так, что её дверь — в конце коридора.
#
# Координаты Blender (как у подъезда, build_mvp_assets.py): Z вверх, пол квартиры z = 8.4, потолок 2.7 м.
#   прихожая  x −8.45…−3.2, y 0.45…2.2  (вход — стена x = −3.2, проём y 0.8…1.7, как DOOR_Y0..DOOR_Y1 подъезда)
#   коридор   x −8.45…−7.45, y −2.18…0.45 (в конце — проём двери комнаты x −8.40…−7.55)
#   выступ    x −7.45…−7.15, y 0.45…0.82
#   (прихожая удлинена на EXT = 1.15 м: вставка — в простенке между двустворчатой и узкой белой дверью, x = X_CUT;
#    всё западнее, вместе с комнатой Юрчика, сдвинуто на 1.15 м к −x)
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
import photo_tex as PT

_ns = {"NO_MAIN": True, "__file__": os.path.join(HERE, "build_yard.py")}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), _ns)
B, mat = _ns["B"], _ns["mat"]
OUT = os.path.join(ROOT, "assets", "models")
ITEM_DIR = os.path.join(OUT, "apartment")

# --- размеры (см. шапку) ---
Z, H = 8.4, 2.7
ZT = Z + H
EXT = 1.15                                           # удлинение прихожей: всё западнее простенка между двустворчатой
                                                     # и узкой белой дверью (x < X_CUT) сдвинуто на EXT к −x
X_CUT = -4.05                                        # где вставлен кусок (середина простенка до удлинения)
HX0, HX1, HY0, HY1 = -7.3 - EXT, -3.2, 0.45, 2.2    # прихожая
CX0, CX1, CY0 = -7.3 - EXT, -6.3 - EXT, -2.18        # коридор (до наружной грани стены комнаты)
PX1, PY1 = -6.15 - EXT, 0.95                         # выступ (тонкий простенок 15 см, длина 50 см): x CX1…PX1, y HY0…PY1
BEAM = 0.50                                          # балка от простенка поперёк прихожей к северной стене: опускается на 50 см
T = 0.12                                             # глубина проёмов (толщина стены у дверей)
DH = 2.05                                            # высота дверных проёмов
# проёмы: (начало, конец, высота, сквозной?) — вдоль стены
ENTRY = (0.8, 1.7)                                   # входная дверь (стена x = HX1), сквозной в подъезд
ROOM_DOOR = (-7.25 - EXT, -6.40 - EXT)                         # дверь комнаты (стена y = CY0), сквозной в комнату
DOUBLE_DOOR = (-5.25 - EXT, -3.90 - EXT)             # двустворчатая со стеклом, 1.35 м (стена y = HY0)
WC_DOOR = (-4.00, -3.30)                             # белая у входа, 0.70 м — обычная межкомнатная (стена y = HY0)
WEST_DOORS = ((0.60, 1.40), (-1.90, -1.10))          # две белые двери справа по коридору (стена x = HX0)
RUNNER = (PX1 + 0.03, HX1 - 0.03, HY0 + 0.10, HY1 - 0.10)  # ковёр x0, x1, y0, y1: почти весь пол прихожей — от стен
                                                     # по бокам 10 см, у торцов 3 см (фото 2), с запада — до выступа; шкаф и полочка стоят на нём


# =====================================================================================
#  Текстуры — из фото квартиры (docs/references/apartment, фотобашинг, photo_tex.py) и CC0 (texture_library).
#  Плотность у стен, пола и потолка — 128 px на метр (тайл 2 x 2 м = 256 px).
# =====================================================================================
PPM = 128
H1, H2 = "hall_1_to_room.webp", "hall_2_to_entrance.webp"


def _piece(photo, quad, wm, hm, sigma=10, mean=0.5, sharpen=0.0):
    """Кусок фото: выпрямить перспективу (размер — по метрам, PPM), убрать свет, привести яркость к mean."""
    a = PT.flatten(PT.rectify(PT.load(photo), quad, max(4, int(wm * PPM)), max(4, int(hm * PPM)), ss=3), sigma)
    if sharpen:                                                                        # трещины и швы чётче
        a = a + (a - PT.blur(a, 1.5)) * sharpen
    return np.clip(a * (mean / max(float(PT.lum(a).mean()), 1e-4)), 0, 1.5)


def tex_wall():
    """Стены: бежево-кремовые обои «под камень» с трещинами-швами — склейка кусков стены с фото 1
    (у двустворчатой двери, над ней, над дверью комнаты). Тайл 2 x 2 м, 256 px."""
    rng = np.random.default_rng(4701)
    p1 = _piece(H1, [(330, 360), (520, 370), (520, 1150), (330, 1150)], 0.53, 2.0, sharpen=0.7)
    p3 = _piece(H1, [(20, 330), (170, 335), (170, 600), (20, 590)], 0.45, 0.7, sharpen=0.7)
    p2 = _piece(H1, [(820, 515), (1075, 515), (1075, 665), (820, 665)], 0.95, 0.55, sharpen=0.7)
    pieces, x = [], 0
    for k in range(5):
        src = p1 if k % 2 == 0 else np.flip(p1, 1)
        pieces.append((src, x, int(rng.integers(0, 256)))); x += src.shape[1] - 10
    pieces += [(p3, 30, 20), (p2, 150, 150), (np.flip(p3, 1), 190, 60)]
    arr = PT.seamless(PT.bash(256, 256, pieces, feather=10), 0.2, rng)
    arr = PT.recolor(arr, (0.79, 0.73, 0.56), contrast=1.9, chroma=0.15, shadow_deg=6)
    arr = PT.grime(256, 256, rng, 3, 0.12)(arr)                                        # засаленные пятна
    save("ap_wall", finish(arr, 1.0, crisp=0.35))


def tex_ceiling():
    """Потолок: белая фактурная штукатурка с голубовато-серыми разводами «иней» — потолок коридора с фото 1
    (кусок 1 x 1.8 м) и его отражения. Тайл 2 x 2 м, 256 px."""
    rng = np.random.default_rng(4703)
    a = _piece(H1, [(700, 0), (1235, 0), (1095, 495), (815, 495)], 1.0, 1.8, sigma=7)[8:-10, 6:-6]
    a = PT.resize(a, 128, 256)
    pieces = [(a, 0, 0), (np.flip(a, 0), 128, 90), (np.flip(a, 1), 64, 170)]
    arr = PT.seamless(PT.bash(256, 256, pieces, feather=12), 0.2, rng)
    arr = PT.duotone(arr, (0.50, 0.62, 0.68), (0.88, 0.88, 0.85), contrast=1.5, bias=0.3)     # белый + голубые разводы
    save("ap_ceiling", finish(arr, 1.2, crisp=0.25))


def tex_laminate(name="ap_laminate"):
    """Ламинат «под дерево» — доски 1.2 x 0.15 м вразбежку, каждая доска — кусок пола коридора с фото 1
    (у двери комнаты). Тот же — в комнате (yr_laminate, решение автора). Тайл 2 x 2 м, 256 px, доски вдоль u."""
    rng = np.random.default_rng(4704)
    src = _piece(H1, [(560, 1548), (1060, 1572), (1100, 2000), (540, 2000)], 1.5, 1.0, sigma=14)[24:128, 0:186]
    arr = PT.planks(256, 256, 13, int(1.2 * PPM), src, rng, tone_var=0.1)
    arr = PT.recolor(arr, (0.68, 0.51, 0.37), contrast=1.15, chroma=0.5)
    arr = PT.grime(256, 256, rng, 3, 0.22, (0.45, 0.40, 0.33))(arr)                    # затоптано
    save(name, finish(arr, 1.1, crisp=0.3))


def tex_runner():
    """Ковёр — с фото 2: тёмно-зелёное поле с бурыми виноградными листьями и лозами (середина
    дорожки, без шкафа и корзины), светлая оливковая кайма — оттуда же. Одна текстура на весь ковёр,
    128 px на метр (u — поперёк, по y; v — вдоль, по x); поле — кусок фото, повторённый зеркально."""
    rng = np.random.default_rng(4705)
    x0, x1, y0, y1 = RUNNER
    w, h = int(round((y1 - y0) * PPM)), int(round((x1 - x0) * PPM))
    full = PT.rectify(PT.load(H2), [(700, 1055), (868, 1055), (1140, 2000), (470, 2000)], 128, 448, ss=3)
    field = PT.resize(PT.flatten(full[16:380, 26:112], 24), 88, 296)                  # масштаб листьев как на фото
    tile = np.concatenate([field, field[:, ::-1]], 1)
    tile = np.concatenate([tile, tile[::-1]], 0)
    canvas = np.tile(tile, (h // tile.shape[0] + 1, (w - 20) // tile.shape[1] + 1, 1))[:h, :w - 20]
    border = PT.flatten(PT.rectify(PT.load(H2), [(862, 1080), (884, 1080), (960, 1420), (930, 1420)], 8, 200, ss=3), 20)
    border = PT.recolor(border, (0.46, 0.43, 0.29), contrast=1.2, chroma=0.3)
    band = np.concatenate([border, border[::-1]] * (h // 400 + 1), 0)[:h]
    arr = np.zeros((h, w, 3), np.float32)
    arr[:, 10:w - 10] = canvas
    arr[:, 3:10] = band[:, :7]; arr[:, w - 10:w - 3] = np.flip(band[:, :7], 1)
    bandx = np.concatenate([border, border[::-1]] * (w // 400 + 1), 0)[:w]           # кайма по торцам
    arr[3:10, 3:w - 3] = np.transpose(bandx[3:w - 3, :7], (1, 0, 2))
    arr[h - 10:h - 3, 3:w - 3] = np.flip(np.transpose(bandx[3:w - 3, :7], (1, 0, 2)), 0)
    arr[:, :3] = (0.06, 0.12, 0.09); arr[:, -3:] = (0.06, 0.12, 0.09)                 # тёмная кромка
    arr[:3, :] = (0.06, 0.12, 0.09); arr[-3:, :] = (0.06, 0.12, 0.09)
    arr = PT.tone(arr, rgb=(0.16, 0.20, 0.13), contrast=1.7)
    arr *= PT.blur(rng.random((h, w, 1)).astype(np.float32), 14) * 0.3 + 0.85         # затоптано пятнами
    arr *= (1 - 0.18 * np.exp(-((np.arange(w) - w / 2) / (w * 0.23)) ** 2))[None, :, None]   # вытерто посередине
    save("ap_runner", finish(np.clip(arr, 0, 1), 1.05, crisp=0.3))


TRIM = {"plinth": (0, 0, 64, 16), "molding": (0, 16, 64, 32), "dark": (0, 32, 64, 48), "white": (0, 48, 64, 64)}


def RT(name):
    x0, y0, x1, y1 = TRIM[name]
    return (x0 / 64, 1 - y1 / 64, x1 / 64, 1 - y0 / 64)


def tex_trim():
    """Мелкий атлас: коричневый крашеный плинтус (фото 1), белый потолочный карниз с тенью в изгибе, тёмная
    «пустота» за закрытыми дверями, белая краска (наличники). Краска — CC0 ambientCG PaintedWood009C."""
    paint = PT.flatten(PT.lib("ambientcg/PaintedWood009C"), 80)
    a = np.zeros((64, 64, 3), np.float32)
    yy = np.mgrid[0:16, 0:64][0].astype(np.float32)
    pl = PT.recolor(PT.resize(paint[:256, :], 64, 16), (0.30, 0.13, 0.08), contrast=1.6)
    pl[:3] *= 1.3; pl[3:4] *= 0.7                                                    # скруглённый верх
    a[0:16] = pl
    mo = PT.recolor(PT.resize(paint[256:512, :], 64, 16), (0.86, 0.85, 0.82), contrast=0.6)
    a[16:32] = mo * (0.70 + 0.30 * np.abs(np.sin(yy / 16 * math.pi * 1.5)))[..., None]  # профиль карниза
    a[32:48] = C(0.03, 0.025, 0.02)
    a[48:64] = PT.recolor(PT.resize(paint[512:768, :], 64, 16), (0.81, 0.80, 0.76), contrast=0.6)
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
    for s_ in bpy.data.scenes:                                  # выделение в других сценах (стартовый куб) тоже уходит в экспорт
        for vl_ in s_.view_layers:
            for o in s_.objects:
                o.select_set(o in obs and s_ == bpy.context.scene, view_layer=vl_)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".gltf"), use_selection=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)


def export_items(I, coll):
    """Каждый предмет — своя коллекция ap_<имя>, точка опоры у основания по центру, свой .gltf; layout.json — позиции в Godot."""
    os.makedirs(ITEM_DIR, exist_ok=True)
    lp = os.path.join(ITEM_DIR, "layout.json")                  # общий для оболочки и мебели (build_apartment_props.py)
    layout = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {}
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
    with open(lp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    return {k: layout[k] for k in I.items}


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
        rv = m if through else (M["trim"], RT("white"))               # у глухих дверей откосы белые, как наличник
        box(a - 0.01, a, z0, z0 + oh, back, c, {'+' + sk: rv})        # откосы
        box(bb, bb + 0.01, z0, z0 + oh, back, c, {'-' + sk: rv})
        box(a, bb, z0 + oh, z0 + oh + 0.01, back, c, {'-Z': rv})
        # порожек: закрывает пол в глубине проёма (иначе под створкой видна пустота — светлая щель)
        sill = (M["trim"], RT("plinth"))
        box(a, bb, z0 - 0.03, z0 + 0.01, c + n * 0.012, back - n * 0.004, {'+Z': sill, key: sill})
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
    # --- выступ — тонкий простенок той же текстурой; от его верха поперёк прихожей до северной стены — балка ---
    w = M["wall"]
    sh.box((CX1, HY0, Z), (PX1, PY1, ZT), {'+Y': w, '+X': w, '-X': w}, scale=(2.0, 2.0))
    sh.box((CX1, PY1, ZT - BEAM), (PX1, HY1, ZT), {'+X': w, '-X': w, '-Z': w}, scale=(2.0, 2.0))

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
    strip(tr, M, 'x', HX0, +1, [(CY0, HY1)], "molding")
    strip(tr, M, 'x', CX1, -1, [(CY0, HY1)], "molding")            # простенок и балка со стороны коридора
    strip(tr, M, 'x', PX1, +1, [(HY0, HY1)], "molding")            # простенок и балка со стороны двустворчатой
    strip(tr, M, 'y', CY0, +1, [(CX0, CX1)], "molding")

    # --- ковровая дорожка: тонкая, без коллизии, одна текстура на всю длину ---
    x0, x1, y0, y1 = RUNNER
    rn = I("runner", nocol=True)

    def rq(xa, xb, ya, yb, uv, z=Z + 0.006):
        rn.poly([Vector((xa, ya, z)), Vector((xb, ya, z)), Vector((xb, yb, z)), Vector((xa, yb, z))],
                [uv(xa, ya), uv(xb, ya), uv(xb, yb), uv(xa, yb)], M["runner"])

    UV = lambda x, y: ((y - y0) / (y1 - y0), (x - x0) / (x1 - x0))                     # u — поперёк, v — вдоль (по x)
    rq(x0, x1, y0, y1, UV)

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
    tex_wall(); tex_ceiling(); tex_laminate(); tex_runner(); tex_trim()
    M = {
        "wall": mat("ApWall", "ap_wall"),
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
