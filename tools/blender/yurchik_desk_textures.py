# -*- coding: utf-8 -*-
# Текстуры рабочего места Юрчика v2 (стол, коврик, монитор, клавиатура, мышь, колонки, обычный системник 2011 под столом).
# Рисуется в обычном Python (numpy + Pillow — буквы на клавишах, логотипы), без Blender:
#   python tools/blender/yurchik_desk_textures.py
# Результат: assets/textures/yd_atlas.png (1024x1024) и yd_glow.png (свечение включённого компа).
# Раскладка — yurchik_desk_layout.py. Модели — build_yurchik_desk.py (запускать после этого скрипта).
# Всё рисуется вдвое крупнее и уменьшается — чистые края без «лесенки»; потом мягкий PS2-финиш (ps2_hero.finish).
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import yurchik_desk_layout as L
from ps2_hero import finish
from ps2_style import noise, blur

TEX = os.path.join(ROOT, "assets", "textures")
R = np.random.default_rng(2010)
SS = 2                                    # суперсэмплинг
FONTS = r"C:\Windows\Fonts"


def font(name, px):
    return ImageFont.truetype(os.path.join(FONTS, name), max(4, int(px * SS)))


def C(*c):
    return np.array(c, np.float32)


def to_arr(img):
    return np.asarray(img.convert("RGB"), np.float32) / 255.0


def to_img(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))


def down(img, w, h):
    return img.resize((w, h), Image.LANCZOS)


def grain(w, h, amp=0.06, cells=24):
    """Мелкая неровность поверхности (множитель около 1)."""
    return (1 - amp / 2 + amp * noise(w, h, cells, cells, R))[..., None] * \
           (1 - amp / 3 + amp * 2 / 3 * R.random((h, w, 1)).astype(np.float32))


def specks(arr, n, col, size=(1, 2), alpha=(0.3, 0.8)):
    """Пыль и крошки."""
    h, w, _ = arr.shape
    for _ in range(n):
        x, y = int(R.integers(0, w)), int(R.integers(0, h))
        s = int(R.integers(size[0], size[1] + 1))
        a = float(R.uniform(*alpha))
        arr[y:y + s, x:x + s] = arr[y:y + s, x:x + s] * (1 - a) + C(*col) * a
    return arr


def rgb255(c):
    return tuple(int(max(0, min(1, v)) * 255) for v in c)


# =====================================================================================
#  Куски атласа
# =====================================================================================
def desk_top(w, h):
    """Карбон «ёлочкой» (саржа 2x2), по краю — тонкая кромка, потёртости там, где лежат руки, кольцо от кружки, крошки."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cell = 6.0
    i, j = np.floor(xx / cell), np.floor(yy / cell)
    fx, fy = xx / cell - i, yy / cell - j
    o = ((i + j // 2 + (j % 2)) % 2).astype(bool)                 # направление волокна
    along = np.where(o, fy, fx)
    tow = 0.55 + 0.45 * np.cos((along - 0.5) * math.pi)          # «трубка» жгута: светлая середина
    sheen = np.where(o, 1.0, 0.72)                                # жгуты одного направления бликуют сильнее
    base = 0.075 + 0.085 * tow * sheen
    a = np.repeat(base[..., None], 3, axis=2) * C(1.0, 1.0, 1.06)
    a *= grain(w, h, 0.10, 16)
    # потёртость под руками (перед клавиатурой) и у мыши: глянец стёрт, чуть светлее и серее
    for cx, cy, rx, ry, k in ((0.47, 0.86, 0.22, 0.10, 0.35), (0.76, 0.80, 0.08, 0.09, 0.30)):
        d = ((xx / w - cx) / rx) ** 2 + ((yy / h - cy) / ry) ** 2
        m = np.clip(1 - d, 0, 1)[..., None] * k
        a = a * (1 - m) + (a.mean(axis=2, keepdims=True) * 1.25 + 0.02) * m
    # кольцо от кружки (у левого края, где стоит кружка)
    cx, cy = 0.105 * w, 0.62 * h
    r = np.hypot(xx - cx, yy - cy)
    ring = np.exp(-((r - 0.036 / 1.16 * w) / 1.2) ** 2) * 0.55
    a = a * (1 - ring[..., None] * 0.5) + C(0.16, 0.11, 0.06) * ring[..., None] * 0.5
    # кромка: светлая фаска по периметру
    e = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy])
    a *= (1 + 0.6 * np.exp(-e / 1.5))[..., None]
    a = specks(a, 140, (0.35, 0.33, 0.30), (1, 1), (0.15, 0.5))   # пыль
    a = specks(a, 8, (0.30, 0.24, 0.16), (1, 2), (0.3, 0.6))      # крошки
    return a


def edge(w, h):
    a = np.ones((h, w, 3), np.float32) * C(0.05, 0.05, 0.055) * grain(w, h, 0.12, 32)
    yy = np.arange(h, dtype=np.float32)[:, None, None]
    a *= 0.75 + 0.6 * np.exp(-yy / 3.0)                         # верхняя фаска ловит свет
    a[-2:] *= 0.6
    return a


def metal(w, h):
    """Порошковая краска: шагрень, сколы до светлой стали."""
    a = np.ones((h, w, 3), np.float32) * C(0.08, 0.08, 0.085)
    a *= (0.85 + 0.3 * noise(w, h, 40, 40, R))[..., None]
    for _ in range(4):
        x, y = int(R.integers(2, w - 6)), int(R.integers(2, h - 4))
        a[y:y + 1, x:x + int(R.integers(2, 4))] = C(0.20, 0.20, 0.21)
    return a


def plastic(w, h, base, gloss=False):
    a = np.ones((h, w, 3), np.float32) * C(*base) * grain(w, h, 0.05 if gloss else 0.14, 24)
    if gloss:                                                     # длинный мягкий отблеск
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        a += (np.exp(-((xx * 0.6 + yy - h * 0.45) / (h * 0.18)) ** 2) * 0.05)[..., None]
    return a


def speaker_front(w, h, knob):
    img = Image.new("RGB", (w * SS, h * SS), rgb255((0.09, 0.09, 0.095)))
    d = ImageDraw.Draw(img)
    s = SS
    cx = w * s / 2
    # НЧ-динамик: резиновый подвес, диффузор, пылезащитный колпачок
    cy, R0 = h * s * 0.66, w * s * 0.40
    d.ellipse((cx - R0, cy - R0, cx + R0, cy + R0), fill=rgb255((0.16, 0.16, 0.17)))
    for k in range(10):
        r = R0 * (0.88 - k * 0.055)
        v = 0.05 + 0.015 * (k % 2) + 0.004 * k
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgb255((v, v, v * 1.05)))
    r = R0 * 0.3
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgb255((0.11, 0.11, 0.12)))
    d.ellipse((cx - r * 0.5, cy - r * 0.8, cx, cy - r * 0.3), fill=rgb255((0.2, 0.2, 0.21)))
    # пищалка
    ty, tr = h * s * 0.24, w * s * 0.16
    d.ellipse((cx - tr, ty - tr, cx + tr, ty + tr), fill=rgb255((0.30, 0.30, 0.31)))
    d.ellipse((cx - tr * 0.7, ty - tr * 0.7, cx + tr * 0.7, ty + tr * 0.7), fill=rgb255((0.08, 0.08, 0.09)))
    d.ellipse((cx - tr * 0.3, ty - tr * 0.3, cx + tr * 0.3, ty + tr * 0.3), fill=rgb255((0.22, 0.22, 0.24)))
    if knob:                                                      # ручка громкости и метка у правой колонки
        ky, kr = h * s * 0.095, w * s * 0.1
        d.ellipse((cx - kr, ky - kr, cx + kr, ky + kr), fill=rgb255((0.32, 0.32, 0.34)))
        d.ellipse((cx - kr * 0.8, ky - kr * 0.8, cx + kr * 0.8, ky + kr * 0.8), fill=rgb255((0.14, 0.14, 0.15)))
        d.line((cx, ky - kr * 0.8, cx, ky - kr * 0.2), fill=rgb255((0.8, 0.8, 0.8)), width=s)
    f = font("arialbd.ttf", 5)
    d.text((cx, h * s * 0.97), "SVEN", font=f, fill=rgb255((0.45, 0.45, 0.47)), anchor="ms")
    a = to_arr(down(img, w, h)) * grain(w, h, 0.08, 12)
    a[:1] *= 1.6; a[:, :1] *= 1.4
    return a


def speaker_side(w, h):
    a = np.ones((h, w, 3), np.float32) * C(0.05, 0.045, 0.045)
    a *= (0.8 + 0.4 * noise(w, h, 2, 30, R))[..., None]           # МДФ «под дерево» — вытянутые волокна
    return a


def dragon_pad(w, h):
    """Большой коврик: чёрный, красный «трайбл»-дракон, прошитый край, логотип справа (как на фото)."""
    s = SS
    img = Image.new("RGB", (w * s, h * s), rgb255((0.06, 0.05, 0.05)))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(7)

    def flame(pts, w0, col):
        """Сужающийся мазок по ломаной (кривой Безье)."""
        p = np.array(pts, np.float32)
        tt = np.linspace(0, 1, 60)
        n = len(p) - 1
        curve = np.zeros((len(tt), 2), np.float32)
        for k in range(n + 1):
            b = math.comb(n, k) * tt ** k * (1 - tt) ** (n - k)
            curve += b[:, None] * p[k]
        for k in range(len(curve) - 1):
            wk = w0 * (1 - tt[k]) ** 0.8 + 1
            x0, y0 = curve[k] * s; x1, y1 = curve[k + 1] * s
            d.line((x0, y0, x1, y1), fill=col, width=int(wk * s))
            d.ellipse((x0 - wk * s / 2, y0 - wk * s / 2, x0 + wk * s / 2, y0 + wk * s / 2), fill=col)

    red, deep, hot = rgb255((0.55, 0.05, 0.03)), rgb255((0.26, 0.025, 0.02)), rgb255((0.80, 0.22, 0.05))
    # тело дракона — большая S-кривая через коврик, от неё — языки пламени и «перья»
    spine = [(0.05 * w, 0.78 * h), (0.30 * w, 0.15 * h), (0.55 * w, 1.05 * h), (0.88 * w, 0.25 * h)]
    for lay, col, wd in ((0, deep, 58), (1, red, 38), (2, hot, 5)):
        flame(spine, wd, col)
        for k in range(16):
            t = (k + 0.5) / 16
            bx = (1 - t) ** 3 * spine[0][0] + 3 * (1 - t) ** 2 * t * spine[1][0] + 3 * (1 - t) * t ** 2 * spine[2][0] + t ** 3 * spine[3][0]
            by = (1 - t) ** 3 * spine[0][1] + 3 * (1 - t) ** 2 * t * spine[1][1] + 3 * (1 - t) * t ** 2 * spine[2][1] + t ** 3 * spine[3][1]
            rs = np.random.default_rng(100 + k)
            ang = rs.uniform(-2.6, -0.5) if k % 2 else rs.uniform(0.5, 2.6)
            L_ = rs.uniform(0.10, 0.22) * h
            tip = (bx + math.cos(ang) * L_ * 1.6, by + math.sin(ang) * L_)
            mid = (bx + math.cos(ang + 0.6) * L_ * 0.8, by + math.sin(ang + 0.6) * L_ * 0.6)
            flame([(bx, by), mid, tip], (wd * 0.7) if lay < 2 else 2, col)
    # второй завиток — хвост, обвивающий левый нижний угол
    tail = [(0.02 * w, 0.30 * h), (0.25 * w, 0.95 * h), (0.40 * w, 0.55 * h), (0.30 * w, 0.40 * h)]
    for col, wd in ((deep, 30), (red, 18), (hot, 3)):
        flame(tail, wd, col)
    # голова справа: глаз и рога
    hx, hy = 0.88 * w, 0.25 * h
    d.polygon([((hx - 18) * s, (hy - 8) * s), ((hx + 30) * s, (hy - 22) * s), ((hx + 14) * s, (hy + 4) * s)], fill=red)
    d.polygon([((hx - 6) * s, (hy - 14) * s), ((hx + 6) * s, (hy - 40) * s), ((hx + 6) * s, (hy - 12) * s)], fill=deep)
    d.ellipse(((hx + 6) * s, (hy - 12) * s, (hx + 12) * s, (hy - 8) * s), fill=hot)
    img = img.filter(ImageFilter.GaussianBlur(0.6 * s))
    d = ImageDraw.Draw(img)
    # логотип справа снизу, прошивка по краю
    f = font("arialbd.ttf", 10)
    d.text((w * s * 0.93, h * s * 0.90), "ARENA", font=f, fill=rgb255((0.55, 0.55, 0.55)), anchor="rs")
    d.ellipse((w * s * 0.93 - 50 * s, h * s * 0.90 - 13 * s, w * s * 0.93 - 40 * s, h * s * 0.90 - 3 * s), fill=rgb255((0.7, 0.2, 0.05)))
    m = 3 * s
    for k in range(0, (w + h) * 2 * s, 5 * s):                  # прошивка: короткие стежки
        for (x0, y0, x1, y1) in ((k, m, k + 3 * s, m), (k, h * s - m, k + 3 * s, h * s - m)):
            if x1 < w * s:
                d.line((x0, y0, x1, y1), fill=rgb255((0.30, 0.10, 0.08)), width=s)
        for (x0, y0, x1, y1) in ((m, k, m, k + 3 * s), (w * s - m, k, w * s - m, k + 3 * s)):
            if y1 < h * s:
                d.line((x0, y0, x0, y1), fill=rgb255((0.30, 0.10, 0.08)), width=s)
    a = to_arr(down(img, w, h))
    a *= grain(w, h, 0.18, 40)                                    # ткань
    # затёртое пятно под ладонью мыши и следы пальцев
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dd = ((xx / w - 0.78) / 0.12) ** 2 + ((yy / h - 0.62) / 0.25) ** 2
    a = a * (1 - 0.3 * np.clip(1 - dd, 0, 1))[..., None] + C(0.07, 0.06, 0.055) * (0.3 * np.clip(1 - dd, 0, 1))[..., None]
    a = specks(a, 90, (0.4, 0.38, 0.35), (1, 1), (0.2, 0.5))
    return a


def mon_front(w, h):
    """Рамка монитора: глянцевый чёрный, светлая фаска по внешнему краю, на нижней планке — ASUS, кнопки, диод."""
    s = SS
    k = w / L.MON_W                                               # пикселей на метр
    img = Image.new("RGB", (w * s, h * s), rgb255((0.07, 0.07, 0.075)))
    d = ImageDraw.Draw(img)
    bx, bt, bb = L.MON_BEZ
    sx0, sy0 = bx * k * s, bt * k * s
    sx1, sy1 = (L.MON_W - bx) * k * s, (L.MON_H - bb) * k * s
    d.rectangle((sx0 - 2 * s, sy0 - 2 * s, sx1 + 2 * s, sy1 + 2 * s), fill=rgb255((0.015, 0.015, 0.018)))   # утопленный край матрицы
    d.rectangle((sx0, sy0, sx1, sy1), fill=rgb255((0.02, 0.02, 0.025)))
    cy = (sy1 + h * s) / 2
    d.text((w * s / 2, cy + 3 * s), "ASUS", font=font("arialbd.ttf", 7.5), fill=rgb255((0.62, 0.63, 0.66)), anchor="mm")
    d.text((sx0 + 2 * s, cy + 2 * s), "VW193", font=font("arial.ttf", 4), fill=rgb255((0.35, 0.35, 0.37)), anchor="lm")
    for i in range(4):                                            # сенсорные кнопки справа
        x = sx1 - (52 - i * 11) * s
        d.ellipse((x - 1.6 * s, cy - 1.6 * s + s, x + 1.6 * s, cy + 1.6 * s + s), outline=rgb255((0.35, 0.35, 0.38)), width=s)
    x = sx1 - 6 * s                                               # кнопка питания (диод — отдельный светящийся кусочек)
    d.ellipse((x - 2.5 * s, cy - 1.5 * s, x + 2.5 * s, cy + 3.5 * s), fill=rgb255((0.12, 0.12, 0.14)))
    a = to_arr(down(img, w, h))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    e = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy])
    a *= (1 + 1.2 * np.exp(-e / 1.4))[..., None]                 # фаска по внешнему краю
    a += (np.exp(-((xx * 0.5 + yy - h * 0.2) / (h * 0.25)) ** 2) * 0.035)[..., None]   # мягкий отблеск глянца
    a = specks(a, 40, (0.3, 0.3, 0.3), (1, 1), (0.15, 0.4))      # пыль на глянце
    return a


def mon_back(w, h):
    a = plastic(w, h, (0.05, 0.05, 0.055))
    yy, xx = np.mgrid[0:h, 0:w]
    for row in range(6):                                          # вентиляционные прорези сверху
        y0 = 18 + row * 8
        for col in range(14):
            x0 = 30 + col * 14
            a[y0:y0 + 3, x0:x0 + 10] = C(0.008, 0.008, 0.01)
    for (cx, cy) in ((108, 140), (148, 140), (108, 180), (148, 180)):    # VESA 100
        a[(xx - cx) ** 2 + (yy - cy) ** 2 < 10] = C(0.02, 0.02, 0.02)
        a[(xx - cx) ** 2 + (yy - cy) ** 2 < 3] = C(0.25, 0.25, 0.27)
    img = to_img(a); d = ImageDraw.Draw(img)                       # наклейка с серийником
    d.rectangle((150, 200, 220, 232), fill=rgb255((0.62, 0.62, 0.60)))
    f = ImageFont.truetype(os.path.join(FONTS, "arial.ttf"), 6)
    for i, t in enumerate(("ASUS VW193S", "S/N: 9BLMTF041823", "MADE IN CHINA")):
        d.text((153, 203 + i * 9), t, font=f, fill=(40, 40, 40))
    for i in range(18):
        d.line((156 + i * 3, 228, 156 + i * 3, 231), fill=(30, 30, 30), width=1 + (i % 3 == 0))
    return to_arr(img)


def tower_front(w, h):
    """Обычный системник 2011 года (как у всех): чёрная пластиковая морда, DVD-привод, заглушка, кардридер,
    круглая кнопка питания и сброс, два диода (питание — зелёный, диск — оранжевый), USB и аудио спереди,
    внизу — щели воздухозаборника. Диоды горят отдельно (yd_glow), здесь — погасшие."""
    s = SS
    img = Image.new("RGB", (w * s, h * s), rgb255((0.08, 0.08, 0.085)))
    d = ImageDraw.Draw(img)
    m = 9 * s
    dark, bay, txt = rgb255((0.03, 0.03, 0.035)), rgb255((0.10, 0.10, 0.105)), rgb255((0.55, 0.55, 0.57))
    # DVD-привод
    y = 14
    d.rectangle((m, y * s, w * s - m, (y + 26) * s), fill=bay)
    d.line((m + 3 * s, (y + 11) * s, w * s - m - 3 * s, (y + 11) * s), fill=dark, width=s)          # щель лотка
    d.text((m + 5 * s, (y + 19) * s), "DVD-RW", font=font("arialbd.ttf", 4.5), fill=txt, anchor="lm")
    d.rectangle((w * s - m - 16 * s, (y + 16) * s, w * s - m - 5 * s, (y + 21) * s), fill=rgb255((0.16, 0.16, 0.17)))
    # заглушка второго отсека 5.25" и отсек 3.5" с кардридером
    y = 44
    d.rectangle((m, y * s, w * s - m, (y + 26) * s), fill=rgb255((0.09, 0.09, 0.095)))
    d.line((m, (y + 26) * s, w * s - m, (y + 26) * s), fill=dark, width=s)
    y = 76
    d.rectangle((m + 18 * s, y * s, w * s - m - 18 * s, (y + 14) * s), fill=bay)
    d.rectangle((m + 26 * s, (y + 5) * s, w * s - m - 26 * s, (y + 8) * s), fill=dark)              # щель для карт
    # кнопка питания, сброс, диоды
    cx, cy = w * s / 2, 116 * s
    d.ellipse((cx - 9 * s, cy - 9 * s, cx + 9 * s, cy + 9 * s), fill=rgb255((0.04, 0.04, 0.045)))
    d.ellipse((cx - 7.5 * s, cy - 7.5 * s, cx + 7.5 * s, cy + 7.5 * s), fill=rgb255((0.15, 0.15, 0.16)))
    d.arc((cx - 3.5 * s, cy - 3.5 * s, cx + 3.5 * s, cy + 3.5 * s), -60, 240, fill=txt, width=s)
    d.line((cx, cy - 4.5 * s, cx, cy), fill=txt, width=s)
    for lx, col in ((54, (0.08, 0.16, 0.08)), (74, (0.18, 0.11, 0.04))):                         # диоды (погасшие)
        d.ellipse(((lx - 1.6) * s, (132 - 1.6) * s, (lx + 1.6) * s, (132 + 1.6) * s), fill=rgb255(col))
    d.ellipse((cx - 2 * s, 139 * s, cx + 2 * s, 143 * s), fill=rgb255((0.05, 0.05, 0.055)))     # сброс
    # USB и аудио
    for x in (30, 46):
        d.rectangle((x * s, 156 * s, (x + 12) * s, 161 * s), fill=rgb255((0.01, 0.01, 0.01)))
        d.rectangle(((x + 1) * s, 156 * s, (x + 11) * s, 158 * s), fill=rgb255((0.50, 0.50, 0.53)))
    for x, c in ((70, (0.25, 0.55, 0.2)), (82, (0.70, 0.35, 0.5))):
        d.ellipse((x * s, 155 * s, (x + 7) * s, 162 * s), fill=rgb255(c))
        d.ellipse(((x + 2) * s, 157 * s, (x + 5) * s, 160 * s), fill=rgb255((0.02, 0.02, 0.02)))
    d.text((cx, 178 * s), "Codegen", font=font("arialbi.ttf", 6), fill=txt, anchor="mm")
    # щели воздухозаборника внизу
    for k in range(14):
        yy = (192 + k * 5) * s
        d.rounded_rectangle((m + 4 * s, yy, w * s - m - 4 * s, yy + 2 * s), s, fill=rgb255((0.015, 0.015, 0.018)))
    a = to_arr(down(img, w, h)) * grain(w, h, 0.08, 16)
    a[:, :2] *= 1.6; a[:2] *= 1.6
    a = specks(a, 30, (0.35, 0.33, 0.3), (1, 1), (0.2, 0.5))
    return a


def tower_side(w, h):
    """Глухая стальная боковая стенка (к креслу): выштампованная решётка под вентилятор, рёбра жёсткости,
    два барашковых винта у заднего края (слева в куске — задняя сторона корпуса), пыль."""
    a = np.ones((h, w, 3), np.float32) * C(0.085, 0.085, 0.09) * grain(w, h, 0.07, 18)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy, r = w * 0.40, h * 0.40, h * 0.17
    rr = np.hypot(xx - cx, yy - cy)
    holes = (rr < r) & ((xx % 6) < 3) & ((yy % 6) < 3)
    a[holes] = C(0.01, 0.01, 0.012)
    a *= (1 - 0.35 * np.exp(-((rr - r - 3) / 1.5) ** 2))[..., None]   # выштамповка вокруг решётки
    for ry in (0.12, 0.88):                                           # рёбра жёсткости
        y0 = int(h * ry)
        a[y0:y0 + 1] *= 1.5; a[y0 + 2:y0 + 3] *= 0.55
    for sy in (0.2, 0.8):                                             # винты у заднего края
        sx, syy = 7, int(h * sy)
        a[(np.hypot(xx - sx, yy - syy) < 4)] = C(0.30, 0.30, 0.32)
        a[(np.hypot(xx - sx, yy - syy) < 1.5)] = C(0.12, 0.12, 0.13)
    a[:, :2] *= 1.5; a[:2] *= 1.5; a[-2:] *= 0.6
    return specks(a, 70, (0.38, 0.36, 0.33), (1, 1), (0.2, 0.5))


def tower_top(w, h):
    a = plastic(w, h, (0.05, 0.05, 0.055))
    yy, xx = np.mgrid[0:h, 0:w]
    hole = ((xx // 4 + yy // 4) % 2 == 0) & (xx % 4 < 2) & (yy % 4 < 2) & (yy > 30) & (yy < h - 40) & (xx > 16) & (xx < w - 16)
    a[hole] = C(0.008, 0.008, 0.01)
    return specks(a, 60, (0.4, 0.38, 0.35), (1, 1), (0.25, 0.6))  # пыль сверху


def stand(w, h):
    a = plastic(w, h, (0.045, 0.045, 0.05), gloss=True)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = ((xx / w - 0.5) / 0.5) ** 2 + ((yy / h - 0.5) / 0.5) ** 2
    a *= (1 + 0.8 * np.exp(-(1 - np.clip(r, 0, 1)) / 0.04))[..., None]   # светлый обод
    return specks(a, 50, (0.35, 0.35, 0.35), (1, 1), (0.2, 0.5))


def mouse(w, h):
    s = SS
    img = Image.new("RGB", (w * s, h * s), rgb255((0.055, 0.055, 0.06)))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 14 * s, h * s), fill=rgb255((0.20, 0.20, 0.22)))           # серые бока
    d.rectangle((w * s - 14 * s, 0, w * s, h * s), fill=rgb255((0.20, 0.20, 0.22)))
    d.line((w * s / 2, 0, w * s / 2, h * s * 0.42), fill=rgb255((0.01, 0.01, 0.01)), width=2 * s)    # раздел кнопок
    d.line((14 * s, h * s * 0.42, w * s - 14 * s, h * s * 0.42), fill=rgb255((0.02, 0.02, 0.02)), width=s)
    d.rounded_rectangle((w * s / 2 - 6 * s, 22 * s, w * s / 2 + 6 * s, 50 * s), 5 * s, fill=rgb255((0.01, 0.01, 0.01)))
    d.rounded_rectangle((w * s / 2 - 4 * s, 24 * s, w * s / 2 + 4 * s, 48 * s), 4 * s, fill=rgb255((0.22, 0.22, 0.24)))
    for k in range(6):
        d.line((w * s / 2 - 4 * s, (26 + k * 4) * s, w * s / 2 + 4 * s, (26 + k * 4) * s), fill=rgb255((0.1, 0.1, 0.1)), width=s)
    d.text((w * s / 2, h * s * 0.72), "A4TECH", font=font("arialbd.ttf", 6), fill=rgb255((0.45, 0.45, 0.47)), anchor="mm")
    a = to_arr(down(img, w, h)) * grain(w, h, 0.06, 10)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a += (np.exp(-((xx - w * 0.35) / (w * 0.12)) ** 2 - ((yy - h * 0.6) / (h * 0.3)) ** 2) * 0.05)[..., None]   # затёртый глянец под ладонью
    return a


def keyboard(w, h):
    """Клавиатура сверху целиком в масштабе модели: корпус, крышки клавиш, латиница белым, кириллица красным."""
    s = SS
    k = w / L.KB_W                                                 # пикселей на метр
    img = Image.new("RGB", (w * s, h * s), rgb255((0.06, 0.06, 0.065)))
    d = ImageDraw.Draw(img)
    u = L.KEY_U
    ox, oy = L.KB_MARGIN_X, L.KB_MARGIN_BACK
    f_big, f_small, f_ru = font("arial.ttf", 9.5), font("arial.ttf", 5.2), font("arial.ttf", 7)
    for (x, y, kw, kh, lab, ru) in L.key_rows():
        x0, y0 = (ox + x * u) * k * s, (oy + y * u) * k * s
        x1, y1 = (ox + (x + kw) * u) * k * s, (oy + (y + kh) * u) * k * s
        gap = 0.0016 * k * s
        d.rounded_rectangle((x0 + gap, y0 + gap, x1 - gap, y1 - gap), 2 * s, fill=rgb255((0.13, 0.13, 0.14)))
        ins = 0.0032 * k * s                                       # верх клавиши (вогнутый, чуть светлее)
        d.rounded_rectangle((x0 + ins, y0 + ins * 0.8, x1 - ins, y1 - ins * 1.3), 2 * s, fill=rgb255((0.19, 0.19, 0.20)))
        tx, ty = x0 + ins + 2 * s, y0 + ins + 1 * s
        if len(lab) == 1 and not ru:
            d.text(((x0 + x1) / 2, (y0 + y1) / 2 - s), lab, font=f_big, fill=rgb255((0.85, 0.85, 0.86)), anchor="mm")
        elif len(lab) == 1:
            d.text((tx, ty), lab, font=f_big, fill=rgb255((0.85, 0.85, 0.86)), anchor="la")
            d.text((x1 - ins - 2 * s, y1 - ins * 1.3 - 2 * s), ru, font=f_ru, fill=rgb255((0.80, 0.22, 0.18)), anchor="rd")
        elif lab:
            d.text((tx, ty + s), lab, font=f_small, fill=rgb255((0.80, 0.80, 0.82)), anchor="la")
    # диоды Num / Caps / Scroll и надпись над цифровым блоком
    for i, t in enumerate(("1", "A", "↓")):
        cx = (ox + (19.0 + i * 1.2) * u) * k * s
        d.ellipse((cx - 2 * s, 8 * s, cx + 2 * s, 12 * s), fill=rgb255((0.05, 0.15, 0.05)))
        d.text((cx, 18 * s), t, font=f_small, fill=rgb255((0.5, 0.5, 0.52)), anchor="mm")
    d.text((ox * k * s + 2 * s, 12 * s), "Genius", font=font("arialbi.ttf", 7), fill=rgb255((0.55, 0.55, 0.57)), anchor="lm")
    a = to_arr(down(img, w, h)) * grain(w, h, 0.05, 30)
    # затёртые клавиши: WASD, пробел — чуть блестят
    for (lx, ly, lw) in ((2.75, 2.5, 1), (2.0, 3.5, 3), (4.0, 5.5, 6.25)):
        x0, y0 = int((ox + lx * u) * k), int((oy + ly * u) * k)
        a[y0 + 3:y0 + int(u * k) - 3, x0 + 3:x0 + int(lw * u * k) - 3] *= 1.35
    return specks(a, 80, (0.45, 0.40, 0.33), (1, 1), (0.3, 0.7))  # крошки между клавиш


# =====================================================================================
def build():
    a = np.zeros((L.ATLAS, L.ATLAS, 3), np.float32) + 0.05

    def put(name, arr):
        x0, y0, x1, y1 = L.A[name]
        a[y0:y1, x0:x1] = arr[:y1 - y0, :x1 - x0]

    def sz(name):
        x0, y0, x1, y1 = L.A[name]
        return x1 - x0, y1 - y0

    put("desk_top", desk_top(*sz("desk_top")))
    put("edge", edge(*sz("edge")))
    put("metal", metal(*sz("metal")))
    put("gloss", plastic(*sz("gloss"), (0.07, 0.07, 0.075), gloss=True))
    put("matte", plastic(*sz("matte"), (0.09, 0.09, 0.095)))
    put("spk_front", speaker_front(*sz("spk_front"), knob=True))
    put("spk_side", speaker_side(*sz("spk_side")))
    put("pad", dragon_pad(*sz("pad")))
    put("mon_front", mon_front(*sz("mon_front")))
    put("mon_back", mon_back(*sz("mon_back")))
    put("tower_f", tower_front(*sz("tower_f")))
    put("kb", keyboard(*sz("kb")))
    put("tower_s", tower_side(*sz("tower_s")))
    put("mouse", mouse(*sz("mouse")))
    put("tower_t", tower_top(*sz("tower_t")))
    put("stand", stand(*sz("stand")))
    put("cable", plastic(*sz("cable"), (0.03, 0.03, 0.03)))
    put("key_side", plastic(*sz("key_side"), (0.11, 0.11, 0.115)))
    put("steel", plastic(*sz("steel"), (0.45, 0.45, 0.47)))
    atlas = finish(a, soft=0.6, bits=6, crisp=0.25)
    to_img(atlas).save(os.path.join(TEX, "yd_atlas.png"))

    gw, gh = L.GLOW
    g = np.zeros((gh, gw, 3), np.float32)
    yy, xx = np.mgrid[0:32, 0:32].astype(np.float32)
    dot = np.exp(-(np.hypot(xx - 15.5, yy - 15.5) / 7) ** 2)[..., None]
    x0, y0, x1, y1 = L.G["power"]
    g[y0:y1, x0:x1] = dot * C(0.3, 1.0, 0.35)                     # диод питания — зелёный
    x0, y0, x1, y1 = L.G["hdd"]
    g[y0:y1, x0:x1] = dot * C(1.0, 0.55, 0.1)
    x0, y0, x1, y1 = L.G["mon_led"]
    g[y0:y1, x0:x1] = dot * C(0.3, 0.6, 1.0)
    to_img(np.clip(g, 0, 1)).save(os.path.join(TEX, "yd_glow.png"))
    print("yd_atlas.png, yd_glow.png готовы")


if __name__ == "__main__":
    build()
