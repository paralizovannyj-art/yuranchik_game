# -*- coding: utf-8 -*-
# Окно в комнате Юрчика — по фото настоящего окна: белый пластиковый (ПВХ) стеклопакет, пожелтевший от времени,
# две части — слева глухая (стекло прямо в раме), справа поворотная створка в своей раме, ручка — на левой стойке
# створки (у импоста), опущена вниз, петли — справа сверху и снизу. Вокруг — глубокие оштукатуренные откосы,
# покрашенные как стена, у рамы грязные. Внизу — белый пластиковый подоконник с загнутым носиком и серыми
# заглушками на торцах. Стекло мутное, полупрозрачное (за ним — вид из окна, build_window_view.py).
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_room_window.py
# или через Blender MCP: exec(open(r"<путь>\tools\blender\build_room_window.py", encoding="utf-8").read())
#   (скрипт строит всё в своей сцене RoomWindow и не трогает остальные сцены).
# Результат: assets/textures/rw_*.png, assets/models/room_window.gltf: RoomWindow (рама, с коллизией при импорте),
#   RoomWindowSash_nocol (створка, пивот на оси петель) и в ней RoomWindowHandle_nocol (ручка, пивот на шейке).
# В Godot (stairwell.tscn → RoomWindow) стоит в точке (X0, WY0, WZ0) комнаты = (-10.5, 9.3, -1.76) без поворота.
#
# Начало координат — левый нижний угол проёма на плоскости стены со стороны комнаты (как в build_yurchik_room.py:
# точка (X0, WY0, WZ0)). Проём идёт вдоль +Y на 1.37 м и вверх (+Z) на 1.44 м, вглубь стены — вдоль -X:
# рама стоит на глубине 0.15–0.22 м, подоконник выступает в комнату (+X) на 0.2 м.
import bpy, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from tex_lib import save
from ps2_hero import C, finish
from ps2_style import noise
import photo_tex as PT

_ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), _ns)
B, mat = _ns["B"], _ns["mat"]
OUT = os.path.join(ROOT, "assets", "models")
R = np.random.default_rng(5151)

# --- размеры (как в комнате: проём 1.37 x 1.44 м, подоконник на 0.9 м от пола) ---
W, H = 1.37, 1.44
XF0, XF1 = -0.22, -0.15        # рама: задняя и лицевая плоскость (профиль 70 мм)
FW = 0.06                      # ширина рамы на виде
IY = 0.505 * W                 # ось импоста — на фото створки почти поровну
IW = 0.07                      # ширина импоста
SW = 0.068                     # ширина профиля створки (на фото шире рамы)
LAP = 0.008                    # створка заходит на раму
XS0, XS1 = -0.205, -0.138      # створка выступает из рамы в комнату на 12 мм
HANDLE_Z = 0.655               # ручка — чуть ниже середины, как на фото
BW = 0.018                     # штапик


# =====================================================================================
#  Текстуры
# =====================================================================================
def save_rgba(name, rgb, alpha):
    """PNG с прозрачностью в assets/textures (tex_lib.save пишет только RGB)."""
    h, w, _ = rgb.shape
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=True)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(rgb, 0, 1)
    rgba[..., 3] = np.clip(alpha, 0, 1)
    img.pixels.foreach_set(rgba[::-1].ravel())
    path = os.path.join(ROOT, "assets", "textures", name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    return path


def tex_pvc():
    """Белый ПВХ, пожелтевший: неровная желтизна пятнами, серые точки грязи, редкие царапины. Тайл 0.5 м."""
    s = 64
    # основа — фото матового пластика (CC0 ambientCG Plastic013A), кусок ~0.5 м
    arr = PT.recolor(PT.resize(PT.flatten(PT.lib("ambientcg/Plastic013A"), 80), s, s), (0.86, 0.85, 0.79), contrast=0.9)
    yel = noise(s, s, 3, 3, R, oct=2)
    arr = arr * (1 - 0.10 * yel[..., None]) + C(0.80, 0.72, 0.52) * 0.10 * yel[..., None]
    specks = R.random((s, s)) < 0.006
    arr[specks] *= 0.85
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    for _ in range(3):                                                    # тонкие царапины
        cx, cy, a = R.uniform(0, s), R.uniform(0, s), R.uniform(0, math.pi)
        d = np.abs((xx - cx) * math.sin(a) - (yy - cy) * math.cos(a))
        along = np.abs((xx - cx) * math.cos(a) + (yy - cy) * math.sin(a))
        arr *= (1 - 0.08 * ((d < 0.6) & (along < R.uniform(5, 14))))[..., None]
    arr *= (0.98 + 0.04 * R.random((s, s)).astype(np.float32))[..., None]
    save("rw_pvc", finish(arr, 1.0, crisp=0.15))


def tex_seal():
    """Чёрный резиновый уплотнитель вокруг стекла."""
    s = 16
    arr = PT.recolor(PT.resize(PT.flatten(PT.lib("ambientcg/Plastic006"), 60)[:128, :128], s, s), (0.10, 0.10, 0.10), contrast=1.2)
    save("rw_seal", finish(arr, 1.0, crisp=0.0))


def tex_fit():
    """Фурнитура: ручка и накладки петель — тот же белый пластик, но чище и чуть теплее; петли — серые колпачки."""
    s = 32
    pl = PT.resize(PT.flatten(PT.lib("ambientcg/Plastic013A"), 80)[:256, :256], s, s)       # CC0 ambientCG Plastic013A
    arr = PT.recolor(pl, (0.88, 0.86, 0.80), contrast=0.9)
    arr[:, s // 2:] = PT.recolor(pl, (0.62, 0.62, 0.60), contrast=0.9)[:, s // 2:]
    save("rw_fit", finish(arr, 1.0, crisp=0.1))


def tex_reveal():
    """Откос: штукатурка, покрашенная той же желтоватой краской, что стена. u — глубина (0 у рамы, 1 у комнаты),
    v — вдоль откоса. У рамы — серая полоса грязи и трещина от монтажной пены, по краю у комнаты —
    серая линия угла, по полю — бурые разводы и облупившиеся пятна, как на стене над окном."""
    w, h = 64, 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, 1 - yy / h
    # основа — стена у окна с фото комнаты (cbc47…jpg, полоса слева от окна): разводы и пятна шпаклёвки
    ph = PT.flatten(PT.crop(PT.load("cbc47ca0-bf80-4454-94af-6537039bbe80.jpg"), 70, 100, 158, 380), 30)
    arr = PT.recolor(PT.resize(ph, w, h), (0.84, 0.80, 0.70), contrast=1.5, chroma=0.15, shadow_deg=5)
    near = np.clip(1 - u / 0.22, 0, 1) ** 1.6                                   # грязь у рамы
    arr *= (1 - 0.35 * near * (0.6 + 0.4 * noise(w, h, 6, 20, R, oct=2)))[..., None]
    crack = (u < 0.05) & (noise(w, h, 2, 40, R, oct=2) > 0.45)
    arr[crack] *= 0.6
    arr[u > 0.95] *= 0.82                                                       # угол откоса
    arr *= (0.97 + 0.05 * R.random((h, w)).astype(np.float32))[..., None]
    save("rw_reveal", finish(arr, 1.0, crisp=0.2))


def tex_glass():
    """Стекло: серо-синее, мутное, полупрозрачное. Вверху светлее (на фото там отражается лампа и белёсый
    налёт), внизу у штапика — грязь и засохшие потёки, по всему полю — пятна от капель и разводы тряпки."""
    s = 128
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    v = 1 - yy / s
    alpha = np.full((s, s), 0.22, np.float32)
    rgb = np.ones((s, s, 3), np.float32) * C(0.30, 0.32, 0.36)
    haze = np.clip((v - 0.55) / 0.45, 0, 1) ** 1.5 * (0.6 + 0.4 * noise(s, s, 3, 3, R, oct=2))   # белёсый верх
    alpha += 0.30 * haze
    rgb = rgb * (1 - haze[..., None] * 0.6) + C(0.78, 0.80, 0.82) * haze[..., None] * 0.6
    # разводы и налёт — с фото окна комнаты (cbc47…jpg, левая створка): светлые места стекла — гуще налёт
    g = PT.lum(PT.flatten(PT.crop(PT.load("cbc47ca0-bf80-4454-94af-6537039bbe80.jpg"), 240, 205, 318, 330), 12))
    g = PT.blur(PT.resize(g[..., None], s, s), 1.5)[..., 0]
    alpha += 0.12 * np.clip((g - g.mean()) / (g.std() * 3 + 1e-4), 0, 1)
    for _ in range(180):                                                       # капли
        cx, cy, r = R.uniform(0, s), R.uniform(0, s), R.uniform(0.6, 2.0)
        d = np.hypot(xx - cx, yy - cy)
        alpha = np.maximum(alpha, np.clip(1 - d / r, 0, 1) * R.uniform(0.25, 0.45))
    for _ in range(14):                                                        # потёки
        cx, y0 = R.uniform(6, s - 6), R.uniform(10, s * 0.7)
        m = (np.abs(xx - cx - np.sin(yy * 0.25) * 0.8) < 0.7) & (yy > y0) & (yy < y0 + R.uniform(10, 40))
        alpha = np.where(m, np.maximum(alpha, 0.32), alpha)
    low = np.clip((v - 0.0) / 0.12, 0, 1)                                      # грязь у нижнего штапика
    alpha += (1 - low) * 0.25
    rgb = rgb * low[..., None] + C(0.40, 0.37, 0.32) * (1 - low[..., None])
    alpha *= 0.9 + 0.2 * noise(s, s, 8, 8, R)
    save_rgba("rw_glass", finish(rgb, 1.0, crisp=0.1), np.clip(alpha, 0.12, 0.75))


# =====================================================================================
#  Геометрия
# =====================================================================================
def bx(b, mn, mx, m, skip=(), s=0.5):
    """Ящик со всеми гранями (кроме skip), мировая проекция текстуры с шагом s метров на тайл."""
    faces = {k: m for k in ('+X', '-X', '+Y', '-Y', '+Z', '-Z') if k not in skip}
    b.box(mn, mx, faces, scale=(s, s))


def quad_x(b, x, y0, y1, z0, z1, m, uv=(0, 0, 1, 1), facing=1):
    """Прямоугольник в плоскости x = const, смотрит в +X (в комнату) или -X."""
    u0, v0, u1, v1 = uv
    pts = [Vector((x, y0, z0)), Vector((x, y1, z0)), Vector((x, y1, z1)), Vector((x, y0, z1))]
    uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    if facing < 0:
        pts, uvs = pts[::-1], uvs[::-1]
    b.poly(pts, uvs, m)


def glazing(b, M, y0, y1, z0, z1, xg, xface):
    """Стекло в проёме (y0..y1, z0..z1) на глубине xg, со штапиком и уплотнителем со стороны комнаты (до xface)."""
    quad_x(b, xg, y0, y1, z0, z1, M["glass"], facing=1)
    quad_x(b, xg - 0.001, y0, y1, z0, z1, M["glass"], facing=-1)              # видно и с улицы
    P, S = M["pvc"], M["seal"]
    xb = xface - 0.004                                                         # штапик чуть утоплен
    bx(b, (xg, y0, z0), (xb, y0 + BW, z1), P, skip=('-X',))
    bx(b, (xg, y1 - BW, z0), (xb, y1, z1), P, skip=('-X',))
    bx(b, (xg, y0 + BW, z0), (xb, y1 - BW, z0 + BW), P, skip=('-X', '-Y', '+Y'))
    bx(b, (xg, y0 + BW, z1 - BW), (xb, y1 - BW, z1), P, skip=('-X', '-Y', '+Y'))
    # уплотнитель — тонкая чёрная полоска по внутреннему краю штапика
    e, t = 0.004, xg + 0.006
    bx(b, (xg, y0 + BW, z0 + BW), (t, y0 + BW + e, z1 - BW), S, skip=('-X',))
    bx(b, (xg, y1 - BW - e, z0 + BW), (t, y1 - BW, z1 - BW), S, skip=('-X',))
    bx(b, (xg, y0 + BW + e, z0 + BW), (t, y1 - BW - e, z0 + BW + e), S, skip=('-X', '-Y', '+Y'))
    bx(b, (xg, y0 + BW + e, z1 - BW - e), (t, y1 - BW - e, z1 - BW), S, skip=('-X', '-Y', '+Y'))
    # уплотнитель с улицы — просто чёрная рамка у стекла
    bx(b, (xg - 0.006, y0, z0), (xg, y1, z0 + 0.004), S, skip=('+X',))


def frame(b, M):
    P = M["pvc"]
    # коробка рамы
    bx(b, (XF0, 0, 0), (XF1, FW, H), P)
    bx(b, (XF0, W - FW, 0), (XF1, W, H), P)
    bx(b, (XF0, FW, 0), (XF1, W - FW, FW), P, skip=('-Y', '+Y'))
    bx(b, (XF0, FW, H - FW), (XF1, W - FW, H), P, skip=('-Y', '+Y'))
    # импост
    bx(b, (XF0, IY - IW / 2, FW), (XF1, IY + IW / 2, H - FW), P, skip=('-Z', '+Z'))
    # левая глухая часть: стекло прямо в раме
    glazing(b, M, FW, IY - IW / 2, FW, H - FW, -0.192, XF1)
    # чуть заметные дренажные заглушки на нижней раме снаружи
    for y in (0.25, IY + 0.3):
        bx(b, (XF0 - 0.002, y, 0.012), (XF0, y + 0.03, 0.022), M["seal"], skip=('+X',))


# Ось петель створки (на ней — серые колпачки) и ось ручки: от них считаются пивоты отдельных объектов.
SASH_Y0, SASH_Y1 = IY + IW / 2 - LAP, W - FW + LAP
HINGE = (XS1 - 0.004, SASH_Y1 + 0.004)                     # x, y вертикальной оси петель
HANDLE_AXIS = (XS1, SASH_Y0 + SW / 2, HANDLE_Z + 0.012)      # центр шейки ручки на лицевой плоскости створки


def sash(b, M, bh=None, bf=None):
    """Правая поворотная створка: своя рама, заходит на коробку на LAP и выступает в комнату.
    b — сама створка, bh — ручка (отдельный объект, крутится), bf — то, что остаётся на коробке (накладки петель,
    тёмная щель вокруг створки). Без bh/bf всё идёт в b."""
    bh, bf = bh or b, bf or b
    P = M["pvc"]
    y0, y1 = IY + IW / 2 - LAP, W - FW + LAP
    z0, z1 = FW - LAP, H - FW + LAP
    bx(b, (XS0, y0, z0), (XS1, y0 + SW, z1), P)
    bx(b, (XS0, y1 - SW, z0), (XS1, y1, z1), P)
    bx(b, (XS0, y0 + SW, z0), (XS1, y1 - SW, z0 + SW), P, skip=('-Y', '+Y'))
    bx(b, (XS0, y0 + SW, z1 - SW), (XS1, y1 - SW, z1), P, skip=('-Y', '+Y'))
    glazing(b, M, y0 + SW, y1 - SW, z0 + SW, z1 - SW, -0.178, XS1)
    # тень-щель между створкой и коробкой: тёмная полоска на лицевой плоскости рамы вокруг створки
    g = 0.003
    S = M["seal"]
    for (ya, yb, za, zb) in ((y0 - g, y0, z0 - g, z1 + g), (y1, y1 + g, z0 - g, z1 + g),
                             (y0, y1, z0 - g, z0), (y0, y1, z1, z1 + g)):
        quad_x(bf, XF1 + 0.0005, ya, yb, za, zb, S, uv=(0, 0, 1, 1))
    # ручка — на левой стойке створки, опущена вниз (закрыто)
    F = M["fit"]
    hy = y0 + SW / 2
    b0 = b
    b = bh
    bx(b0, (XS1, hy - 0.016, HANDLE_Z - 0.045), (XS1 + 0.011, hy + 0.016, HANDLE_Z + 0.045), F, s=0.1)      # розетка
    b.cyl((XS1 + 0.002, hy, HANDLE_Z + 0.012), (XS1 + 0.030, hy, HANDLE_Z + 0.012), 0.012, 0.011, F, segs=8, caps=True)  # шейка
    # рычаг: от шейки вниз, слегка расширяется к концу и отогнут к стеклу
    lz0, lz1 = HANDLE_Z + 0.028, HANDLE_Z - 0.125
    pts_top = [(XS1 + 0.020, hy - 0.012), (XS1 + 0.042, hy - 0.012), (XS1 + 0.042, hy + 0.012), (XS1 + 0.020, hy + 0.012)]
    pts_bot = [(XS1 + 0.016, hy - 0.014), (XS1 + 0.036, hy - 0.014), (XS1 + 0.036, hy + 0.014), (XS1 + 0.016, hy + 0.014)]
    top = [Vector((x, y, lz0)) for x, y in pts_top]
    bot = [Vector((x, y, lz1)) for x, y in pts_bot]
    for i in range(4):
        j = (i + 1) % 4
        b.poly([bot[i], bot[j], top[j], top[i]], [(0, 0), (0.45, 0), (0.45, 1), (0, 1)], F)
    b.poly(top[::-1], [(0.2, 0.5)] * 4, F)
    b.poly(bot, [(0.2, 0.5)] * 4, F)
    # петли справа: серые колпачки на стыке створки и коробки + белые накладки
    for (za, zb) in ((z1 - 0.13, z1 - 0.03), (z0 + 0.03, z0 + 0.12)):
        b0.cyl((XS1 - 0.004, y1 + 0.004, za), (XS1 - 0.004, y1 + 0.004, zb), 0.010, 0.010, F, segs=8, caps=True, su=0.1)
        bx(bf, (XF1, y1 - 0.002, za + 0.01), (XS1 - 0.002, y1 + 0.016, zb - 0.01), F, s=0.1)


def reveals(b, M):
    """Откосы: от лицевой плоскости рамы до стены, слегка расходятся к комнате (как на фото)."""
    Rm = M["reveal"]
    fl = 0.03                                                                  # раскрытие откоса на глубину
    def face(pts, uvs):                                                        # обход задан «снаружи» — разворачиваем
        b.poly(pts[::-1], uvs[::-1], Rm)
    # левый: смотрит в +Y
    face([Vector((XF1, 0, 0)), Vector((0, -fl, 0)), Vector((0, -fl, H + fl)), Vector((XF1, 0, H))],
         [(0, 0), (1, 0), (1, H / 1.6), (0, H / 1.6)])
    # правый: смотрит в -Y
    face([Vector((0, W + fl, 0)), Vector((XF1, W, 0)), Vector((XF1, W, H)), Vector((0, W + fl, H + fl))],
         [(1, 0.3), (0, 0.3), (0, 0.3 + H / 1.6), (1, 0.3 + H / 1.6)])
    # верхний: смотрит вниз
    face([Vector((XF1, 0, H)), Vector((0, -fl, H + fl)), Vector((0, W + fl, H + fl)), Vector((XF1, W, H))],
         [(0, 0.6), (1, 0.6), (1, 0.6 + W / 1.6), (0, 0.6 + W / 1.6)])


def sill(b, M):
    """Подоконник ПВХ: плита 2 см, выступает в комнату, спереди — скруглённый носик со свесом вниз,
    на торцах — серые заглушки. Заходит под раму."""
    P, F = M["pvc"], M["fit"]
    sy0, sy1 = -0.07, W + 0.07
    x0, x1 = XF1 - 0.02, 0.20
    bx(b, (x0, sy0, -0.02), (x1, sy1, 0.0), P, skip=('+X',), s=0.6)
    b.cyl((x1, sy0, -0.012), (x1, sy1, -0.012), 0.012, 0.012, P, segs=8, caps=False, su=0.6)   # носик
    bx(b, (x1 - 0.014, sy0, -0.042), (x1 + 0.004, sy1, -0.02), P, skip=('-X', '+Z'), s=0.6)    # свес вниз
    # заглушки на торцах — серые
    for (ya, yb) in ((sy0 - 0.006, sy0), (sy1, sy1 + 0.006)):
        bx(b, (x0, ya, -0.044), (x1 + 0.014, yb, 0.003), F, s=0.05)


def preview(sc):
    """Для проверки: кусок стены с проёмом, камера и свет — как на фото. В glTF не попадают."""
    pw = B()
    wall = mat("RwPreviewWall", "rw_reveal", rough=0.95)
    T = 0.6
    for (ya, yb, za, zb) in ((-0.9, -0.03, -1.0, 2.2), (W + 0.03, W + 0.9, -1.0, 2.2),
                             (-0.03, W + 0.03, H + 0.03, 2.2), (-0.03, W + 0.03, -1.0, -0.05)):
        pw.box((0, ya, za), (0.001, yb, zb), {'+X': wall}, scale=(1.6, 1.6))
    ob = pw.build("RwPreviewWall", sc.collection)
    cam = sc.objects.get("RwCam")
    if not cam:
        cam = bpy.data.objects.new("RwCam", bpy.data.cameras.new("RwCam"))
        sc.collection.objects.link(cam)
    cam.location = (2.1, W / 2 - 0.05, 0.75)
    cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    cam.data.lens = 26
    sc.camera = cam
    li = sc.objects.get("RwLamp")
    if not li:
        li = bpy.data.objects.new("RwLamp", bpy.data.lights.new("RwLamp", 'POINT'))
        sc.collection.objects.link(li)
    li.location = (1.6, W / 2 - 0.3, 1.9)
    li.data.energy = 220
    li.data.color = (1.0, 0.93, 0.8)
    sc.render.resolution_x, sc.render.resolution_y = 600, 680
    if not sc.world:
        sc.world = bpy.data.worlds.new("RwWorld")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.06, 0.08, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.4
    return ob


def mat_alpha(name, tex):
    m = mat(name, tex, rough=0.15)
    nt = m.node_tree
    t = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    nt.links.new(t.outputs["Alpha"], nt.nodes["Principled BSDF"].inputs["Alpha"])
    m.surface_render_method = 'BLENDED'
    return m


def main():
    if bpy.context.window:
        sc = bpy.data.scenes.get("RoomWindow") or bpy.data.scenes.new("RoomWindow")
        bpy.context.window.scene = sc
    else:
        sc = bpy.context.scene
    for ob in list(sc.objects):
        if ob.type == 'MESH':
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in [m for m in bpy.data.meshes if (m.name.startswith("RoomWindow") or m.name.startswith("RwPreviewWall")) and m.users == 0]:
        bpy.data.meshes.remove(me)
    tex_pvc(); tex_seal(); tex_fit(); tex_reveal(); tex_glass()
    M = {"pvc": mat("RwPvc", "rw_pvc", rough=0.45), "seal": mat("RwSeal", "rw_seal", rough=0.8),
         "fit": mat("RwFit", "rw_fit", rough=0.4), "reveal": mat("RwReveal", "rw_reveal", rough=0.95),
         "glass": mat_alpha("RwGlass", "rw_glass")}
    b, bs, bh = B(), B(), B()
    frame(b, M)
    sash(bs, M, bh, b)
    reveals(b, M)
    sill(b, M)
    ob = b.build("RoomWindow", sc.collection)
    # створка и ручка — отдельные объекты с пивотом на своей оси (в Godot открываются скриптом room_window.gd);
    # «_nocol» — без автоколлизии при импорте (у створки коллизию-ящик ставит скрипт)
    so = bs.build("RoomWindowSash_nocol", sc.collection)
    ho = bh.build("RoomWindowHandle_nocol", sc.collection)
    sp = Vector((HINGE[0], HINGE[1], 0.0))
    hp = Vector(HANDLE_AXIS)
    so.data.transform(Matrix.Translation(-sp)); so.location = sp
    ho.data.transform(Matrix.Translation(-hp)); ho.location = hp - sp
    ho.parent = so
    for o in (ob, so, ho):
        for poly in o.data.polygons:
            poly.use_smooth = False
    if bpy.context.window:
        preview(sc)
    for o in sc.objects:
        o.select_set(o in (ob, so, ho))
    bpy.context.view_layer.objects.active = ob if bpy.context.view_layer.objects.get(ob.name) else None
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "room_window.gltf"), use_selection=True, use_active_scene=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    return {"polys": len(ob.data.polygons), "sash": len(so.data.polygons), "handle": len(ho.data.polygons)}


RESULT = main()
print("BUILD_ROOM_WINDOW", RESULT)
