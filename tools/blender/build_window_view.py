# -*- coding: utf-8 -*-
# Вид из окна комнаты Юрчика (задача YUR-25) — по трём фотографиям из настоящего окна, но зимой, днём, в метель
# (референс из задачи: серо-белая пелена, дома напротив еле проступают сквозь снег).
#
# Что за окном (как на фото, окно смотрит на запад, −X; справа — север, +Y):
#   * прямо напротив, через двор, — длинная жёлто-кремовая десятиэтажка с красными «шапками»-крышами над подъездами;
#   * справа — ряд высоких (16 этажей) розовато-коричневых башен, уходящих вдаль;
#   * слева — пустырь и низкие крыши рынка, за ними далёкие многоэтажки;
#   * внизу — тротуар и проезд вдоль нашего дома, машины на парковке, фонари, двор с голыми деревьями,
#     трансформаторная будка в граффити, домик с коричневой крышей, детская площадка, гаражи;
#   * на фасаде слева от окна — наружный блок кондиционера, через небо тянутся провода.
# Пасмурный зимний день: всё в свежем снегу, рассеянный серый свет, окна почти не горят, небо — ровная пелена.
# Свет «запечён» в текстуры свечения. В игре материалы заменяются шейдером shaders/window_view.gdshader
# (scripts/tools/ps2_import.gd): свой светло-серый туман метели по расстоянию, без ламп и тумана подъезда.
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_window_view.py
# или через Blender MCP: exec(open(".../build_window_view.py").read()) — строит в отдельной сцене «WindowView».
# Результат: assets/textures/wv_*.png, assets/models/window_view.gltf (всё одним объектом WindowView_nocol + небо).
# Координаты — те же, что у комнаты (build_yurchik_room.py): модель ставится в stairwell.tscn без смещения.
import bpy, os, sys, math, random
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else None
if not HERE or not os.path.exists(os.path.join(HERE, "build_yard.py")):
    HERE = r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from tex_lib import save
from ps2_hero import C, finish
from ps2_style import noise, smoothstep, blur, soften, quantize

_ns = {"NO_MAIN": True, "__file__": os.path.join(HERE, "build_yard.py")}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), _ns)
B, mat = _ns["B"], _ns["mat"]
OUT = os.path.join(ROOT, "assets", "models")
R = np.random.default_rng(2525)

# --- окно комнаты (как в build_yurchik_room.py) ---
X0, Z = -10.5, 8.4
XW = X0 - 0.22                          # плоскость стекла
FX = XW - 0.23                          # наружная плоскость фасада
WY0, WY1, WZ0, WZ1 = 1.76, 3.13, Z + 0.9, Z + 2.34
EYE = Vector((-9.4, 2.45, Z + 1.6))

# --- план двора ---
GX0, GS = FX, 128.0                     # подробная карта снега: x от фасада на 128 м к западу, y −64…64
GY0 = -64.0
WALK_X = -13.0                          # тротуар вдоль дома
DRIVE_X = -17.5                         # проезд
PARK_X = -22.5                          # парковка (машины носом к проезду)
LAMPS = [(-23.4, -21.0), (-23.4, 5.0), (-23.4, 31.0), (-80.0, -10.0), (-80.0, 22.0)]
BX, BD, BY0, BY1 = -84.0, 12.0, -52.0, 44.0          # жёлтая десятиэтажка напротив: фасад, глубина, длина
FLOOR, B_FLOORS, B_PL = 2.8, 10, 1.4
TP = (-51.0, -20.0, -44.0, -14.0, 3.4)               # трансформаторная будка в граффити
HOUSE = (-43.0, 15.0, -36.0, 22.0, 3.0)              # домик с коричневой крышей
PLAY = (-31.0, -5.0)                                 # детская площадка
GAR = (-74.0, 36.0, -56.0, 42.0, 2.4)                # гаражи
MARKET = (-72.0, -62.0, -36.0, -44.0, 4.6)           # рынок слева
PATHS = [[(-24.0, -34.0), (-40.0, -24.0), (-60.0, -6.0), (-83.0, -16.0)],
         [(-24.0, 18.0), (-34.0, 8.0), (-48.0, 2.0), (-62.0, -4.0)],
         [(-48.0, 2.0), (-60.0, 20.0), (-83.0, 32.0)],
         [(-13.0, 9.0), (-24.0, 12.0)], [(-13.0, -27.0), (-24.0, -30.0)]]


# =====================================================================================
#  Атлас однотонных клеток (8 x 8 по 32 px) + свечение
# =====================================================================================
CELLS = {}          # имя -> (индекс, цвет, свечение)
_CL = [
    ("snow", (0.80, 0.82, 0.87), 0.17), ("bark", (0.10, 0.085, 0.075), 0.03), ("bark_snow", (0.62, 0.63, 0.66), 0.12),
    ("birch", (0.62, 0.60, 0.55), 0.08), ("metal", (0.33, 0.34, 0.35), 0.05), ("lamp", (1.0, 0.70, 0.36), 1.0),
    ("black", (0.03, 0.03, 0.035), 0.0), ("car_red", (0.42, 0.07, 0.05), 0.07), ("car_blue", (0.09, 0.14, 0.28), 0.07),
    ("car_white", (0.74, 0.74, 0.71), 0.07), ("car_black", (0.05, 0.05, 0.055), 0.06), ("car_silver", (0.48, 0.49, 0.51), 0.07),
    ("car_green", (0.18, 0.23, 0.20), 0.07), ("car_glass", (0.04, 0.05, 0.065), 0.05), ("red_roof", (0.55, 0.10, 0.07), 0.10),
    ("brown_roof", (0.30, 0.16, 0.10), 0.06), ("house", (0.70, 0.55, 0.50), 0.07), ("concrete", (0.45, 0.44, 0.42), 0.06),
    ("plinth", (0.40, 0.37, 0.32), 0.07), ("ac", (0.78, 0.78, 0.75), 0.09), ("sign_green", (0.25, 0.95, 0.45), 0.9),
    ("sign_white", (0.95, 0.92, 0.82), 0.75), ("door_lamp", (1.0, 0.86, 0.62), 1.0), ("brick", (0.50, 0.36, 0.30), 0.05),
    ("garage", (0.25, 0.20, 0.17), 0.05), ("pvc", (0.82, 0.82, 0.79), 0.10), ("sill", (0.58, 0.58, 0.58), 0.08),
    ("wire", (0.015, 0.015, 0.02), 0.0), ("play_blue", (0.15, 0.25, 0.50), 0.06), ("play_yellow", (0.70, 0.55, 0.10), 0.07),
    ("yellow", (0.78, 0.70, 0.48), 0.06), ("red_snowy", (0.62, 0.38, 0.36), 0.12), ("door", (0.22, 0.17, 0.13), 0.06),
    ("tail", (0.9, 0.08, 0.05), 0.25), ("window_lit", (1.0, 0.78, 0.45), 0.8),
]
for i, (n, c, e) in enumerate(_CL):
    CELLS[n] = (i, c, e)
AC_REGION = (6, 0)          # строка, колонка: 2 x 2 клетки — лицевая сторона кондиционера (решётка и вентилятор)


def cell(name):
    i = CELLS[name][0]
    u = (i % 8 + 0.5) / 8
    v = 1 - (i // 8 + 0.5) / 8
    return (u, v, u, v)


def tex_atlas():
    s = 256
    alb = np.zeros((s, s, 3), np.float32)
    emi = np.zeros((s, s, 3), np.float32)
    for n, (i, c, e) in CELLS.items():
        r, k = i // 8, i % 8
        alb[r * 32:(r + 1) * 32, k * 32:(k + 1) * 32] = C(*c)
        if e > 0.5 and n not in ("window_lit",):                            # днём лампы и вывески не горят
            c = (0.55, 0.56, 0.58) if n in ("lamp", "door_lamp", "tail") else tuple(x * 0.6 for x in c)
        emi[r * 32:(r + 1) * 32, k * 32:(k + 1) * 32] = C(*c) * (0.5 if n == "window_lit" else DAY)
    # лицевая сторона кондиционера: белый корпус, слева круглая решётка вентилятора, справа рёбра
    r0, c0 = AC_REGION[0] * 32, AC_REGION[1] * 32
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    face = np.ones((64, 64, 3), np.float32) * C(0.76, 0.76, 0.73)
    rr = np.hypot(xx - 24, yy - 32)
    fan = rr < 20
    grille = fan & ((np.floor(rr) % 4) < 2)
    face[fan] = C(0.22, 0.22, 0.22)
    face[grille] = C(0.55, 0.55, 0.53)
    fins = (xx > 48) & (xx < 60) & (yy > 8) & (yy < 56) & ((yy.astype(int) % 4) < 2)
    face[fins] = C(0.30, 0.30, 0.30)
    face[2:6, 50:60] = C(0.40, 0.40, 0.40)
    face *= (0.85 + 0.25 * noise(64, 64, 4, 4, R))[..., None]
    face[56:] *= C(0.75, 0.68, 0.58)                                     # ржавые потёки снизу
    alb[r0:r0 + 64, c0:c0 + 64] = face
    emi[r0:r0 + 64, c0:c0 + 64] = face * DAY
    save("wv_atlas", finish(alb, 1.0, crisp=0.2))
    save("wv_atlas_emission", emi.astype(np.float32))


# =====================================================================================
#  Окна домов
# =====================================================================================
WARM = [C(1.0, 0.72, 0.40), C(1.0, 0.80, 0.52), C(0.95, 0.62, 0.30), C(1.0, 0.88, 0.70), C(0.90, 0.55, 0.35)]
COLD = [C(0.55, 0.70, 1.0), C(0.75, 0.85, 1.0)]


DAYLIT = 0.15          # днём горит только каждое ~7-е окно из тех, что горели бы ночью
DAY = 0.82             # рассеянный свет пасмурного дня: свечение = цвет * DAY


def lit_window(alb, emi, x0, y0, x1, y1, rng, p=0.27, glass=(0.05, 0.06, 0.075)):
    """Окно днём: стекло отражает серое небо (бывают шторы и тюль), редкое — с включённым светом."""
    p *= DAYLIT
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    if x1 <= x0 or y1 <= y0:
        return
    if rng.random() < p:
        col = COLD[rng.integers(len(COLD))] if rng.random() < 0.08 else WARM[rng.integers(len(WARM))]
        k = rng.uniform(0.35, 1.0)
        h, w = y1 - y0, x1 - x0
        g = np.ones((h, w), np.float32)
        kind = rng.random()
        if kind < 0.35:                                                # шторы по бокам
            cw = max(1, int(w * rng.uniform(0.2, 0.4)))
            g[:, :cw] *= 0.35; g[:, w - cw:] *= 0.35
        elif kind < 0.55:                                              # тюль — неровно
            g *= 0.6 + 0.4 * rng.random((h, w)).astype(np.float32)
        elif kind < 0.65:                                              # жалюзи
            g[::2] *= 0.45
        alb[y0:y1, x0:x1] = col * 0.6 * g[..., None]
        emi[y0:y1, x0:x1] = col * (0.35 + 0.2 * k) * g[..., None]
    else:
        refl = C(0.30, 0.31, 0.33) + C(*glass)
        sh = rng.uniform(0.55, 1.1)
        h, w = y1 - y0, x1 - x0
        g = np.ones((h, w), np.float32)
        if rng.random() < 0.35:                                        # за стеклом шторы — темнее
            g *= rng.uniform(0.5, 0.8)
        g[: max(1, h // 4)] *= 1.15                                    # блик неба сверху
        alb[y0:y1, x0:x1] = refl * sh * g[..., None]


def tex_yellow():
    """Жёлтая десятиэтажка (фото 1 и 2): кремово-жёлтые панели, стопки застеклённых лоджий (белый пластик,
    у кого-то — старое дерево), между ними окна; кондиционеры. 24 колонки по 3 м x 10 этажей (72 x 28 м)."""
    w, h = 1024, 512
    rng = np.random.default_rng(251)
    cols, fl = 24, B_FLOORS
    cw, fh = w / cols, h / fl
    alb = np.ones((h, w, 3), np.float32) * C(0.80, 0.71, 0.48)
    alb *= (0.88 + 0.22 * noise(w, h, 24, 12, rng))[..., None]
    emi = np.zeros((h, w, 3), np.float32)
    for k in range(1, fl):                                                       # швы панелей
        y = int(k * fh); alb[y:y + 2] *= 0.8
    for k in range(cols + 1):
        x = int(k * cw); alb[:, x:x + 1] *= 0.86
    kinds = ["win", "log", "log", "win", "win", "log", "win", "win"] * 3          # лоджии парами, как на фото
    for c in range(cols):
        x0 = c * cw
        for f in range(fl):
            ytop = h - (f + 1) * fh                                              # строка верха этажа
            if kinds[c] == "log":
                frame = C(0.84, 0.84, 0.80) if rng.random() < 0.7 else C(0.42, 0.30, 0.20)
                gx0, gx1 = x0 + 2, x0 + cw - 2
                alb[int(ytop + 3):int(ytop + fh - 1), int(gx0):int(gx1)] = frame
                par = C(0.86, 0.86, 0.82) if rng.random() < 0.6 else C(0.70, 0.66, 0.55)
                alb[int(ytop + fh * 0.58):int(ytop + fh - 1), int(gx0):int(gx1)] = par * rng.uniform(0.85, 1.05)
                n = 3
                for j in range(n):                                               # створки остекления
                    a = gx0 + 2 + j * (gx1 - gx0 - 4) / n
                    lit_window(alb, emi, a + 1, ytop + 6, a + (gx1 - gx0 - 4) / n - 1, ytop + fh * 0.55, rng, p=0.18)
            else:
                ww = cw * 0.5
                a = x0 + (cw - ww) / 2
                alb[int(ytop + fh * 0.18) - 1:int(ytop + fh * 0.72) + 1, int(a) - 1:int(a + ww) + 1] = C(0.85, 0.85, 0.81)
                lit_window(alb, emi, a + 1, ytop + fh * 0.18 + 1, a + ww / 2 - 0.5, ytop + fh * 0.72, rng)
                lit_window(alb, emi, a + ww / 2 + 0.5, ytop + fh * 0.18 + 1, a + ww - 1, ytop + fh * 0.72, rng)
            if rng.random() < 0.3:                                               # кондиционер
                ax = int(x0 + rng.uniform(0.1, 0.7) * cw); ay = int(ytop + fh * 0.62)
                alb[ay:ay + 6, ax:ax + 9] = C(0.80, 0.80, 0.77)
                alb[ay + 6:ay + 14, ax + 2:ax + 4] *= 0.8                        # потёк
    alb[:int(fh * 0.12)] = C(0.86, 0.84, 0.78)                                   # карниз
    yy = np.arange(h, dtype=np.float32)[:, None, None]
    emi = np.maximum(emi, alb * DAY)
    save("wv_yellow", finish(alb, 1.05, crisp=0.25))
    save("wv_yellow_emission", quantize(soften(np.clip(emi, 0, 1), 1.0)))


def tex_tower():
    """Башни справа (фото 3): 16 этажей, розовато-коричневые простенки, светлые стопки лоджий,
    окна попарно. Две разные грани по 8 колонок x 3 м (половины текстуры), 16 этажей x 2.8 м."""
    w, h = 1024, 512
    rng = np.random.default_rng(252)
    cols, fl = 16, 16
    cw, fh = w / cols, h / fl
    alb = np.ones((h, w, 3), np.float32) * C(0.55, 0.42, 0.36)
    alb *= (0.85 + 0.25 * noise(w, h, 32, 16, rng))[..., None]
    emi = np.zeros((h, w, 3), np.float32)
    kinds = ["pier", "log", "win", "win", "log", "win", "log", "pier"] * 2
    for c in range(cols):
        x0 = c * cw
        if kinds[c] == "log":
            alb[:, int(x0 + 2):int(x0 + cw - 2)] = C(0.80, 0.74, 0.64) * (0.9 + 0.15 * noise(int(x0 + cw - 2) - int(x0 + 2), h, 2, 8, rng))[..., None]
        for f in range(fl):
            ytop = h - (f + 1) * fh
            alb[int(ytop):int(ytop) + 1] *= 0.82
            if kinds[c] == "pier":
                lit_window(alb, emi, x0 + cw * 0.3, ytop + fh * 0.25, x0 + cw * 0.7, ytop + fh * 0.75, rng, p=0.2)
            elif kinds[c] == "log":
                lit_window(alb, emi, x0 + 5, ytop + 3, x0 + cw - 5, ytop + fh * 0.55, rng, p=0.2, glass=(0.10, 0.11, 0.12))
            else:
                lit_window(alb, emi, x0 + cw * 0.15, ytop + fh * 0.22, x0 + cw * 0.48, ytop + fh * 0.75, rng)
                lit_window(alb, emi, x0 + cw * 0.52, ytop + fh * 0.22, x0 + cw * 0.85, ytop + fh * 0.75, rng)
    alb[:4] = C(0.62, 0.60, 0.56)
    emi = np.maximum(emi, alb * DAY)
    save("wv_tower", finish(alb, 1.05, crisp=0.25))
    save("wv_tower_emission", quantize(soften(np.clip(emi, 0, 1), 1.0)))


def tex_tp():
    """Трансформаторная будка (фото 2): серый бетон, снизу граффити до высоты руки, решётчатые двери.
    Развёртка по периметру 26 м x 3.4 м."""
    w, h = 512, 64
    rng = np.random.default_rng(253)
    alb = np.ones((h, w, 3), np.float32) * C(0.46, 0.45, 0.43)
    alb *= (0.8 + 0.3 * noise(w, h, 40, 4, rng))[..., None]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    PAL = [C(0.15, 0.35, 0.75), C(0.85, 0.85, 0.85), C(0.80, 0.25, 0.30), C(0.15, 0.15, 0.15), C(0.30, 0.65, 0.40), C(0.85, 0.60, 0.15)]
    for _ in range(26):                                                          # «пузырчатые» буквы
        cx, cy = rng.uniform(0, w), rng.uniform(h * 0.35, h * 0.85)
        rx, ry = rng.uniform(6, 22), rng.uniform(4, 12)
        m = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) < 1
        col = PAL[rng.integers(len(PAL))]
        alb[m] = col * rng.uniform(0.7, 1.0)
        edge = m ^ ((((xx - cx) / (rx - 1.5)) ** 2 + ((yy - cy) / (ry - 1.5)) ** 2) < 1)
        alb[edge] = C(0.08, 0.08, 0.08)
    for x in (60, 190, 330, 450):                                                # двери
        alb[18:h, x:x + 22] = C(0.28, 0.27, 0.25)
        alb[18:h:3, x:x + 22] *= 0.6
    alb[:6] = C(0.36, 0.35, 0.33)
    save("wv_tp", finish(alb, 1.0, crisp=0.3))
    save("wv_tp_emission", (alb * DAY).astype(np.float32))


def tex_ground():
    """Снег двора 128 x 128 м сверху: тротуар и проезд вдоль дома (метель их почти замела, колеи едва видны),
    тропинки, сугробы. Пасмурный день — ровный серый свет без пятен."""
    s = 1024
    rng = np.random.default_rng(254)
    ii, jj = np.mgrid[0:s, 0:s].astype(np.float32)
    X = GX0 - (ii + 0.5) / s * GS                                                # строка — к западу
    Y = GY0 + (jj + 0.5) / s * GS                                                # столбец — к северу
    snow = C(0.84, 0.86, 0.90)
    n = noise(s, s, 24, 24, rng)
    alb = np.ones((s, s, 3), np.float32) * snow
    alb *= (0.93 + 0.10 * n)[..., None]
    walk = (X <= GX0) & (X > WALK_X)
    drive = (X <= WALK_X) & (X > DRIVE_X)
    park = (X <= DRIVE_X) & (X > PARK_X)
    alb[walk] = C(0.74, 0.75, 0.78) * (0.92 + 0.12 * n[walk])[..., None]
    alb[drive] = C(0.64, 0.64, 0.67) * (0.88 + 0.2 * n[drive])[..., None]
    for tx in (-14.4, -15.9):                                                    # колеи
        rut = np.abs(X - tx - 0.15 * np.sin(Y * 0.21)) < 0.18
        alb[rut] *= 0.8
    alb[park] = C(0.72, 0.73, 0.76) * (0.9 + 0.15 * n[park])[..., None]
    curb = (np.abs(X - PARK_X) < 0.25)
    alb[curb] = C(0.90, 0.91, 0.94)                                              # отвал снега вдоль бордюра
    def seg_dist(ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
        return np.hypot(X - (ax + t * dx), Y - (ay + t * dy))
    for path in PATHS:                                                           # тропинки, полузаметённые
        for (a, b_) in zip(path[:-1], path[1:]):
            d = seg_dist(a[0], a[1], b_[0], b_[1])
            m = d < 0.75
            alb[m] *= (0.86 + 0.08 * n[m])[..., None]
    alb = finish(alb, 1.2, crisp=0.2)
    emi = alb * DAY * C(0.97, 0.99, 1.03)
    save("wv_ground", alb)
    save("wv_ground_emission", quantize(soften(np.clip(emi, 0, 1), 1.2)))


def tex_sky():
    """Небо на купол: u — азимут, v — высота (e = −4° + 94° * v^1.8). Сплошная серая пелена, к горизонту светлее;
    едва заметные тёмные клочья облаков. В игре почти всё небо закроет туман метели."""
    w, h = 1024, 512
    rng = np.random.default_rng(255)
    v = 1 - (np.arange(h, dtype=np.float32) + 0.5) / h                         # строка 0 — зенит
    e = -4.0 + 94.0 * v ** 1.8
    t = np.clip(e / 40.0, 0, 1)[:, None, None]
    hor = C(0.70, 0.71, 0.73); zen = C(0.56, 0.57, 0.60)
    sky = np.broadcast_to(hor + (zen - hor) * t, (h, w, 3)).copy()
    cl = noise(w, h, 16, 6, rng, oct=5)
    sky *= (0.96 + 0.08 * cl)[..., None]
    sky = quantize(soften(np.clip(sky, 0, 1), 1.0))
    save("wv_sky", sky)
    save("wv_sky_emission", sky)


# =====================================================================================
#  Геометрия
# =====================================================================================
def abox(b, mn, mx, m, name, faces=('+X', '-X', '+Y', '-Y', '+Z', '-Z')):
    b.box(mn, mx, {k: (m, cell(name)) for k in faces})


def tri(b, pts, m, name):
    u = cell(name)
    b.poly(pts, [(u[0], u[1])] * len(pts), m)


def tube(b, p0, p1, r0, r1, m, name, snow_name=None, segs=5):
    """Труба одной клетки атласа; грани, смотрящие вверх, — «в снегу» (snow_name)."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    t = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
    u = ax.cross(t).normalized(); w = ax.cross(u)
    ring = lambda p, r, a: p + (u * math.cos(a) + w * math.sin(a)) * r
    for i in range(segs):
        a0 = 2 * math.pi * i / segs; a1 = 2 * math.pi * (i + 1) / segs
        pts = [ring(p0, r0, a0), ring(p0, r0, a1), ring(p1, r1, a1), ring(p1, r1, a0)]
        nrm = (u * math.cos((a0 + a1) / 2) + w * math.sin((a0 + a1) / 2))
        nm = snow_name if (snow_name and nrm.z > 0.45) else name
        c = cell(nm)
        b.poly(pts, [(c[0], c[1])] * 4, m)


def tree(b, m, base, rng, kind):
    bark = "birch" if kind == "birch" else "bark"
    def br(p, d, L, r, depth):
        end = p + d * L
        tube(b, p, end, r, r * 0.62, m, bark, "bark_snow", segs=5 if depth < 2 else 3)
        if depth >= 3:
            return
        k = rng.randint(3, 5) if depth == 0 else rng.randint(2, 3)
        for i in range(k):
            t = rng.uniform(0.35, 0.95) if depth == 0 else rng.uniform(0.5, 1.0)
            sp = p + d * L * t
            up = 1.6 if kind == "poplar" else 0.7
            nd = (d * up + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.15, 0.8)))).normalized()
            br(sp, nd, L * rng.uniform(0.45, 0.62), r * 0.55, depth + 1)
    h = {"poplar": rng.uniform(9, 13), "birch": rng.uniform(6, 9), "elm": rng.uniform(5, 8)}[kind]
    d0 = Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 1)).normalized()
    br(Vector(base), d0, h * 0.5, 0.14 + h * 0.012, 0)


def car(b, m, x, y, rng):
    """Машина носом к проезду (вдоль X), на крыше и капоте шапки снега."""
    col = rng.choice(["car_red", "car_blue", "car_white", "car_black", "car_silver", "car_silver", "car_green", "car_white"])
    L, W = rng.uniform(4.0, 4.6), rng.uniform(1.65, 1.8)
    x0, x1, y0, y1 = x - L / 2, x + L / 2, y - W / 2, y + W / 2
    abox(b, (x0, y0, 0.12), (x1, y1, 0.32), m, "black", ('+X', '-X', '+Y', '-Y'))
    abox(b, (x0, y0, 0.32), (x1, y1, 0.82), m, col, ('+X', '-X', '+Y', '-Y'))
    c0, c1 = x0 + L * 0.28, x0 + L * 0.78
    abox(b, (c0, y0 + 0.08, 0.82), (c1, y1 - 0.08, 1.35), m, "car_glass", ('+X', '-X', '+Y', '-Y'))
    sn = rng.uniform(0.08, 0.22)                                                 # толщина снега
    abox(b, (x0 - 0.02, y0 - 0.02, 0.82), (c0, y1 + 0.02, 0.82 + sn * 0.7), m, "snow", ('+X', '-X', '+Y', '-Y', '+Z'))
    abox(b, (c1, y0 - 0.02, 0.82), (x1 + 0.02, y1 + 0.02, 0.82 + sn * 0.7), m, "snow", ('+X', '-X', '+Y', '-Y', '+Z'))
    abox(b, (c0 - 0.02, y0 + 0.06, 1.35), (c1 + 0.02, y1 - 0.06, 1.35 + sn), m, "snow", ('+X', '-X', '+Y', '-Y', '+Z'))


def lamp(b, m, x, y, toward):
    tube(b, (x, y, 0), (x, y, 7.2), 0.11, 0.07, m, "metal", segs=5)
    hx = x + 1.3 * toward
    tube(b, (x, y, 7.1), (hx, y, 7.4), 0.05, 0.05, m, "metal", segs=4)
    abox(b, (hx - 0.35, y - 0.16, 7.28), (hx + 0.35, y + 0.16, 7.48), m, "metal", ('+X', '-X', '+Y', '-Y', '+Z'))
    abox(b, (hx - 0.3, y - 0.13, 7.22), (hx + 0.3, y + 0.13, 7.28), m, "lamp", ('-Z', '+X', '-X', '+Y', '-Y'))
    abox(b, (hx - 0.33, y - 0.14, 7.48), (hx + 0.33, y + 0.14, 7.55), m, "snow", ('+Z', '+X', '-X', '+Y', '-Y'))


def gable(b, m, x0, x1, y0, y1, z, hr, side, roof):
    """Двускатная «шапка», конёк вдоль X; фронтон — красный."""
    yc = (y0 + y1) / 2
    tri(b, [(x1, y0, z), (x1, y1, z), (x1, yc, z + hr)], m, side)
    tri(b, [(x0, y1, z), (x0, y0, z), (x0, yc, z + hr)], m, side)
    tri(b, [(x1, y0, z), (x1, yc, z + hr), (x0, yc, z + hr), (x0, y0, z)], m, roof)
    tri(b, [(x1, y1, z), (x0, y1, z), (x0, yc, z + hr), (x1, yc, z + hr)], m, roof)


def hip(b, m, x0, y0, x1, y1, z, hr, roof):
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    k = min(x1 - x0, y1 - y0) * 0.3
    a, c = (xc - k, yc, z + hr), (xc + k, yc, z + hr)
    if (y1 - y0) > (x1 - x0):
        a, c = (xc, yc - k, z + hr), (xc, yc + k, z + hr)
        tri(b, [(x0, y0, z), (x1, y0, z), a], m, roof)
        tri(b, [(x1, y1, z), (x0, y1, z), c], m, roof)
        tri(b, [(x1, y0, z), (x1, y1, z), c, a], m, roof)
        tri(b, [(x0, y1, z), (x0, y0, z), a, c], m, roof)
    else:
        tri(b, [(x0, y1, z), (x0, y0, z), a], m, roof)
        tri(b, [(x1, y0, z), (x1, y1, z), c], m, roof)
        tri(b, [(x0, y0, z), (x1, y0, z), c, a], m, roof)
        tri(b, [(x1, y1, z), (x0, y1, z), a, c], m, roof)


def tower(b, M, cx, cy, wx, wy, floors, half, rng):
    x0, x1, y0, y1 = cx - wx / 2, cx + wx / 2, cy - wy / 2, cy + wy / 2
    zt = 1.2 + floors * FLOOR
    vt = floors / 16.0
    abox(b, (x0, y0, 0), (x1, y1, 1.2), M["atlas"], "plinth", ('+X', '-X', '+Y', '-Y'))
    span = lambda L: L / 48.0
    u0 = 0.5 * half
    b.box((x0, y0, 1.2), (x1, y1, zt), {'-Y': (M["tower"], (u0, 0, u0 + span(wx), vt)),
                                       '+Y': (M["tower"], (0.5 - u0, 0, 0.5 - u0 + span(wx), vt)),
                                       '+X': (M["tower"], (u0 + 0.1, 0, u0 + 0.1 + span(wy), vt)),
                                       '-X': (M["tower"], (u0 + 0.2, 0, u0 + 0.2 + span(wy), vt))})
    abox(b, (x0, y0, zt), (x1, y1, zt + 0.15), M["atlas"], "snow", ('+Z', '+X', '-X', '+Y', '-Y'))
    sx = cx + rng.uniform(-wx * 0.25, wx * 0.25)
    abox(b, (sx - 2.5, cy - 3, zt), (sx + 2.5, cy + 3, zt + 3.4), M["atlas"], "brick", ('+X', '-X', '+Y', '-Y'))
    abox(b, (sx - 2.6, cy - 3.1, zt + 3.4), (sx + 2.6, cy + 3.1, zt + 3.55), M["atlas"], "snow", ('+Z', '+X', '-X', '+Y', '-Y'))


def build(M):
    import bpy
    rng = random.Random(25)
    nrng = np.random.default_rng(25)
    sc = bpy.context.scene
    coll = sc.collection
    b = B()
    at = M["atlas"]

    # --- наружный откос окна, отлив со снегом, кусок фасада вокруг ---
    abox(b, (FX, WY0 - 0.01, WZ0), (XW, WY0, WZ1), at, "pvc", ('+Y',))
    abox(b, (FX, WY1, WZ0), (XW, WY1 + 0.01, WZ1), at, "pvc", ('-Y',))
    abox(b, (FX, WY0, WZ1), (XW, WY1, WZ1 + 0.01), at, "concrete", ('-Z',))
    abox(b, (FX - 0.12, WY0 - 0.05, WZ0 - 0.06), (XW, WY1 + 0.05, WZ0), at, "sill", ('+Z', '-X', '+Y', '-Y'))
    abox(b, (FX - 0.10, WY0, WZ0), (XW - 0.03, WY1, WZ0 + 0.09), at, "snow", ('+Z', '-X', '+Y', '-Y', '+X'))
    for (ya, yb, za, zb) in ((WY0 - 3.0, WY0, Z - 3.0, Z + 6.0), (WY1, WY1 + 3.0, Z - 3.0, Z + 6.0),
                             (WY0, WY1, Z - 3.0, WZ0 - 0.06), (WY0, WY1, WZ1, Z + 6.0)):
        b.box((FX - 0.01, ya, za), (FX, yb, zb), {'-X': (M["yellow"], (0.02, 0.15, 0.03, 0.16))})
    # кондиционер слева от окна на кронштейнах (фото 2)
    ay0, ay1, az0, az1, ax = WY0 - 1.15, WY0 - 0.25, Z + 1.45, Z + 2.05, FX - 0.34
    r0, c0 = AC_REGION
    b.box((ax, ay0, az0), (FX, ay1, az1), {'-X': (at, (c0 / 8, 1 - (r0 + 2) / 8, (c0 + 2) / 8, 1 - r0 / 8)),
                                          '+Y': (at, cell("ac")), '-Y': (at, cell("ac")), '-Z': (at, cell("ac"))})
    abox(b, (ax - 0.02, ay0 - 0.02, az1), (FX, ay1 + 0.02, az1 + 0.07), at, "snow", ('+Z', '-X', '+Y', '-Y'))
    for yy in (ay0 + 0.1, ay1 - 0.1):
        tube(b, (FX, yy, az0 - 0.25), (ax - 0.05, yy, az0 - 0.02), 0.02, 0.02, at, "metal", segs=3)
        tube(b, (ax - 0.05, yy, az0 - 0.02), (FX, yy, az0 - 0.02), 0.02, 0.02, at, "metal", segs=3)
    tube(b, (FX - 0.05, ay1 - 0.1, az0), (FX - 0.05, ay1 + 0.4, az0 - 3.0), 0.015, 0.015, at, "black", segs=3)   # дренаж

    # --- земля: подробная карта и дальний снег ---
    g = M["ground"]
    b.poly([(GX0, GY0, 0), (GX0, GY0 + GS, 0), (GX0 - GS, GY0 + GS, 0), (GX0 - GS, GY0, 0)],
           [(0, 1), (1, 1), (1, 0), (0, 0)], g)
    BIG = 520.0
    for (xa, ya, xb, yb) in ((GX0 - GS, -BIG, GX0 - BIG, BIG), (GX0, GY0 + GS, GX0 - GS, BIG), (GX0, -BIG, GX0 - GS, GY0),
                             (GX0 + 60, -BIG, GX0, BIG)):
        xa, xb = max(xa, xb), min(xa, xb)
        ya, yb = min(ya, yb), max(ya, yb)
        tri(b, [(xa, ya, -0.02), (xa, yb, -0.02), (xb, yb, -0.02), (xb, ya, -0.02)], at, "snow")

    # --- машины на парковке ---
    y = -40.0
    while y < 40.0:
        if rng.random() < 0.82 and not (-3 < y < 0.5):
            car(b, at, (DRIVE_X + PARK_X) / 2 - rng.uniform(-0.2, 0.3), y + rng.uniform(-0.15, 0.15), rng)
        y += rng.uniform(2.5, 3.0)
    car(b, at, -15.2, -12.0, rng)                                                # одна стоит в проезде
    # бордюрные сугробы
    for k in range(18):
        yy = -44 + k * 5 + rng.uniform(-1, 1)
        abox(b, (PARK_X - 0.6, yy, 0), (PARK_X + 0.2, yy + rng.uniform(2, 4), rng.uniform(0.3, 0.6)), at, "snow", ('+X', '-X', '+Y', '-Y', '+Z'))

    # --- фонари ---
    for (lx, ly) in LAMPS:
        lamp(b, at, lx, ly, 1 if lx > -50 else -1)

    # --- провода через небо (фото 1 и 2) ---
    def wire(p0, p1, sag):
        p0, p1 = Vector(p0), Vector(p1)
        n = 14
        pts = [p0.lerp(p1, i / n) - Vector((0, 0, sag * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]
        for a, c in zip(pts[:-1], pts[1:]):
            tube(b, a, c, 0.025, 0.025, at, "wire", segs=3)
    wire((FX - 0.3, 9.0, Z + 5.5), (-96.0, 64.0, 46.0), 5.0)
    wire((FX - 0.3, 9.4, Z + 5.9), (-96.0, 64.6, 46.4), 5.4)
    wire((FX - 0.3, -6.0, Z + 4.0), (-70.0, -48.0, 9.5), 4.0)
    tube(b, (-70.0, -48.0, 0), (-70.0, -48.0, 10), 0.14, 0.1, at, "concrete", segs=5)

    # --- жёлтая десятиэтажка напротив ---
    ym = M["yellow"]
    zt = B_PL + B_FLOORS * FLOOR
    abox(b, (BX - BD, BY0, 0), (BX, BY1, B_PL), at, "plinth", ('+X', '+Y', '-Y'))
    L = BY1 - BY0
    b.box((BX - BD, BY0, B_PL), (BX, BY0 + 72.0, zt), {'+X': (ym, (0, 0, 1, 1))})
    b.box((BX - BD, BY0 + 72.0, B_PL), (BX, BY1, zt), {'+X': (ym, (0, 0, (L - 72.0) / 72.0, 1))})
    b.box((BX - BD, BY0, B_PL), (BX, BY1, zt), {'+Y': (ym, (0.2, 0, 0.2 + BD / 72.0, 1)), '-Y': (ym, (0.6, 0, 0.6 + BD / 72.0, 1))})
    abox(b, (BX - BD, BY0, zt), (BX + 0.2, BY1, zt + 0.25), at, "snow", ('+Z', '+X', '+Y', '-Y'))
    for k, yc in enumerate((-40.0, -16.0, 8.0, 32.0)):
        abox(b, (BX, yc - 0.8, 0), (BX + 0.05, yc + 0.8, 2.2), at, "door", ('+X',))
        abox(b, (BX, yc - 1.3, 2.45), (BX + 1.6, yc + 1.3, 2.6), at, "concrete", ('+X', '+Y', '-Y', '-Z'))
        abox(b, (BX, yc - 1.3, 2.6), (BX + 1.6, yc + 1.3, 2.85), at, "snow", ('+Z', '+X', '+Y', '-Y'))
        abox(b, (BX + 0.05, yc - 0.18, 2.3), (BX + 0.25, yc + 0.18, 2.44), at, "door_lamp", ('+X', '-Z', '+Y', '-Y'))
        # красные «шапки» на крыше над подъездами (фото 1 и 2)
        gable(b, at, BX - BD + 0.5, BX + 0.3, yc - 4.0, yc + 4.0, zt + 0.25, 2.6, "red_roof", "red_snowy")
        abox(b, (BX - BD + 0.5, yc - 4.0, zt + 0.25), (BX + 0.3, yc + 4.0, zt + 0.9), at, "red_roof", ('+X', '+Y', '-Y'))
    gable(b, at, BX - BD + 0.5, BX + 0.3, BY1 - 5.5, BY1 + 0.3, zt + 0.25, 2.2, "red_roof", "red_snowy")
    abox(b, (BX - 4, -28.0, zt + 0.25), (BX - 1, -26.0, zt + 1.5), at, "concrete", ('+X', '-X', '+Y', '-Y'))
    abox(b, (BX - 4, 19.0, zt + 0.25), (BX - 1, 21.0, zt + 1.5), at, "concrete", ('+X', '-X', '+Y', '-Y'))

    # --- башни справа (север), уходящие вдаль, и дальние дома ---
    tm = M
    for k in range(7):
        tower(b, tm, -60.0 - k * 27.0, 79.0 + k * 3.5 + rng.uniform(-1, 1), 24.0, 16.0, 16 if k % 3 else 14, k % 2, rng)
    for (cx, cy, fl) in ((-150.0, -95.0, 16), (-185.0, -60.0, 12), (-130.0, -140.0, 14), (-215.0, -120.0, 16),
                         (-175.0, 5.0, 16), (-205.0, 40.0, 14), (-160.0, -30.0, 12), (-120.0, 150.0, 16), (-60.0, 140.0, 16)):
        tower(b, tm, cx, cy, 24.0, 16.0, fl, rng.randint(0, 1), rng)

    # --- трансформаторная будка в граффити ---
    x0, y0, x1, y1, h = TP
    per = 2 * ((x1 - x0) + (y1 - y0))
    u = lambda a, c: (a / per, 0, c / per, 1)
    wx_, wy_ = x1 - x0, y1 - y0
    b.box((x0, y0, 0), (x1, y1, h), {'+X': (M["tp"], u(0, wy_)), '-Y': (M["tp"], u(wy_, wy_ + wx_)),
                                     '-X': (M["tp"], u(wy_ + wx_, 2 * wy_ + wx_)), '+Y': (M["tp"], u(2 * wy_ + wx_, per))})
    abox(b, (x0 - 0.15, y0 - 0.15, h), (x1 + 0.15, y1 + 0.15, h + 0.3), at, "snow", ('+Z', '+X', '-X', '+Y', '-Y'))
    abox(b, (x0 + 1, y0 + 1, h + 0.3), (x0 + 3.5, y0 + 3, h + 1.5), at, "concrete", ('+X', '-X', '+Y', '-Y'))
    abox(b, (x0 + 0.9, y0 + 0.9, h + 1.5), (x0 + 3.6, y0 + 3.1, h + 1.65), at, "snow", ('+Z', '+X', '-X', '+Y', '-Y'))

    # --- домик с коричневой крышей (фото 3) ---
    x0, y0, x1, y1, h = HOUSE
    abox(b, (x0, y0, 0), (x1, y1, h), at, "house", ('+X', '-X', '+Y', '-Y'))
    hip(b, at, x0 - 0.4, y0 - 0.4, x1 + 0.4, y1 + 0.4, h, 1.4, "red_snowy")
    abox(b, (x1, y0 + 2, 0.9), (x1 + 0.03, y0 + 3.2, 2.0), at, "window_lit", ('+X',))
    for yy in np.arange(y0 - 3, y1 + 3, 0.4):                                    # деревянный забор
        abox(b, (x1 + 2.5, yy, 0), (x1 + 2.56, yy + 0.12, 1.3), at, "garage", ('+X', '-X', '+Y', '-Y'))

    # --- детская площадка ---
    px, py = PLAY
    for yy in (py - 1.5, py + 1.5):                                              # качели
        tube(b, (px - 1, yy, 0), (px, yy, 2.4), 0.05, 0.05, at, "play_blue", segs=4)
        tube(b, (px + 1, yy, 0), (px, yy, 2.4), 0.05, 0.05, at, "play_blue", segs=4)
    tube(b, (px, py - 1.5, 2.4), (px, py + 1.5, 2.4), 0.05, 0.05, at, "play_blue", "snow", segs=4)
    abox(b, (px - 0.2, py - 0.3, 0.45), (px + 0.2, py + 0.3, 0.52), at, "play_yellow")
    tube(b, (px - 6, py + 4, 0), (px - 6, py + 4, 2.2), 0.07, 0.07, at, "metal", segs=5)       # грибок
    n8 = 8
    for i in range(n8):
        a0, a1 = 2 * math.pi * i / n8, 2 * math.pi * (i + 1) / n8
        tri(b, [(px - 6 + 1.6 * math.cos(a0), py + 4 + 1.6 * math.sin(a0), 2.0), (px - 6 + 1.6 * math.cos(a1), py + 4 + 1.6 * math.sin(a1), 2.0),
                (px - 6, py + 4, 2.7)], at, "red_snowy")
    for i in range(6):                                                           # песочница/лавки — сугробы-коробки
        abox(b, (px - 9 + i * 0.5, py - 6, 0), (px - 8.6 + i * 0.5, py - 3, 0.4), at, "snow", ('+X', '-X', '+Y', '-Y', '+Z'))

    # --- гаражи ---
    x0, y0, x1, y1, h = GAR
    for k in range(6):
        gx = x0 + k * 3.0
        abox(b, (gx, y0, 0), (gx + 3.0, y1, h - k % 2 * 0.15), at, "garage", ('-Y', '+X', '-X'))
        abox(b, (gx - 0.05, y0 - 0.2, h - k % 2 * 0.15), (gx + 3.05, y1, h + 0.25 - k % 2 * 0.15), at, "snow", ('+Z', '-Y', '+X', '-X'))

    # --- рынок слева: низкие ангары, вывески ---
    x0, y0, x1, y1, h = MARKET
    for k in range(4):
        xa = x0 + k * 9.0
        abox(b, (xa, y0, 0), (xa + 8.6, y1, h + k % 2 * 0.6), at, "concrete", ('+X', '-X', '+Y', '-Y'))
        abox(b, (xa - 0.1, y0 - 0.1, h + k % 2 * 0.6), (xa + 8.7, y1 + 0.1, h + 0.3 + k % 2 * 0.6), at, "snow", ('+Z', '+X', '-X', '+Y', '-Y'))
    abox(b, (x1, -50.0, 3.0), (x1 + 0.1, -46.0, 3.8), at, "sign_green", ('+X', '+Y'))
    abox(b, (x0 + 20, y1, 3.2), (x0 + 26, y1 + 0.1, 3.8), at, "sign_white", ('+Y',))
    abox(b, (x1, -58.0, 0.6), (x1 + 0.05, -54.0, 2.4), at, "window_lit", ('+X',))

    # --- деревья ---
    blocked = [(TP[0] - 2, TP[1] - 2, TP[2] + 2, TP[3] + 2), (HOUSE[0] - 2, HOUSE[1] - 2, HOUSE[2] + 4, HOUSE[3] + 2),
               (PLAY[0] - 10, PLAY[1] - 7, PLAY[0] + 3, PLAY[1] + 7), (GAR[0] - 1, GAR[1] - 1, GAR[2] + 1, GAR[3] + 1),
               (MARKET[0] - 1, MARKET[1] - 1, MARKET[2] + 1, MARKET[3] + 1)]
    spots = []
    for yy in np.arange(-42, 46, 7.0):                                           # тополя вдоль парковки
        spots.append((PARK_X - 2.2 + rng.uniform(-0.6, 0.6), yy + rng.uniform(-1.5, 1.5), "poplar" if rng.random() < 0.6 else "elm"))
    tries = 0
    while len(spots) < 62 and tries < 2000:
        tries += 1
        x, yy = rng.uniform(-28, -79), rng.uniform(-60, 62)
        if any(a <= x <= c and bb <= yy <= d for (a, bb, c, d) in blocked):
            continue
        if any((x - sx) ** 2 + (yy - sy) ** 2 < 16 for (sx, sy, _) in spots):
            continue
        spots.append((x, yy, rng.choice(["elm", "elm", "birch", "poplar"])))
    for (x, yy, kind) in spots:
        tree(b, at, (x, yy, 0), rng, kind)
        abox(b, (x - 0.6, yy - 0.6, 0), (x + 0.6, yy + 0.6, 0.12), at, "snow", ('+Z', '+X', '-X', '+Y', '-Y'))

    main = b.build("WindowView_nocol", coll)

    # --- купол неба ---
    s = B()
    NA, NE, RAD = 48, 16, 560.0
    cx, cy = EYE.x, EYE.y
    def pt(i, j):
        v = j / NE
        e = math.radians(-4.0 + 94.0 * v ** 1.8)
        a = 2 * math.pi * i / NA
        return (cx + RAD * math.cos(e) * math.cos(a), cy + RAD * math.cos(e) * math.sin(a), RAD * math.sin(e) - 2.0)
    for i in range(NA):
        for j in range(NE):
            pts = [pt(i, j), pt(i, j + 1), pt(i + 1, j + 1), pt(i + 1, j)]       # внутрь купола
            uvs = [(i / NA, j / NE), (i / NA, (j + 1) / NE), ((i + 1) / NA, (j + 1) / NE), ((i + 1) / NA, j / NE)]
            s.poly(pts, uvs, M["sky"])
    sky = s.build("WindowSky_nocol", coll)
    return main, sky


def export(name, obs):
    for o in bpy.context.scene.objects:
        o.select_set(o in obs)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".gltf"), use_selection=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True,
                              use_active_scene=True)


def main():
    sc = bpy.data.scenes.get("WindowView") or bpy.data.scenes.new("WindowView")
    if bpy.context.window:
        bpy.context.window.scene = sc
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):                                     # старые сборки (повторный запуск через MCP)
        if me.name.startswith(("WindowView_nocol", "WindowSky_nocol")) and me.users == 0:
            bpy.data.meshes.remove(me)
    bpy.context.view_layer.update()
    tex_atlas(); tex_yellow(); tex_tower(); tex_tp(); tex_ground(); tex_sky()
    M = {"atlas": mat("WvAtlas", "wv_atlas", "wv_atlas_emission"), "yellow": mat("WvYellow", "wv_yellow", "wv_yellow_emission"),
         "tower": mat("WvTower", "wv_tower", "wv_tower_emission"), "tp": mat("WvTP", "wv_tp", "wv_tp_emission"),
         "ground": mat("WvGround", "wv_ground", "wv_ground_emission"), "sky": mat("WvSky", "wv_sky", "wv_sky_emission")}
    main_ob, sky = build(M)
    export("window_view", [main_ob, sky])
    return {"faces": len(main_ob.data.polygons), "sky": len(sky.data.polygons)}


RESULT = main()
print("BUILD_WINDOW_VIEW " + str(RESULT))
