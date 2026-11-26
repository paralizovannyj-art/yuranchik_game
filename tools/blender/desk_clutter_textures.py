# -*- coding: utf-8 -*-
# Текстуры мелочи на столе Юрчика: бутылки воды «Моршинська» 1,5 л и «Миргородська» 0,5 л, белая кружка «MAYSKIY» с сердцем
# с чаем, белая миска с синей каймой, остатками борща и ложкой.
# Рисуется в обычном Python (numpy + Pillow), без Blender:
#   python tools/blender/desk_clutter_textures.py
# Результат: assets/textures/dc_atlas.png (512x512, RGBA: альфа — только у прозрачного пластика бутылок).
# Модели — build_desk_clutter.py (запускать после этого скрипта). Прямоугольники атласа — словарь A ниже
# (build_desk_clutter.py берёт его отсюда же).
import os, sys
import numpy as np
try:                                       # в Blender Pillow нет — там нужен только словарь A
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TEX = os.path.join(ROOT, "assets", "textures")
FONTS = r"C:\Windows\Fonts"
SIZE = 512
SS = 2                                     # суперсэмплинг этикеток — чистые буквы

# (x0, y0, x1, y1) в пикселях, начало сверху-слева
A = {
    "m_label": (0, 0, 512, 104),           # «Моршинська»: белая этикетка вокруг плеча бутылки
    "y_label": (0, 112, 512, 208),         # «Миргородська»: синяя этикетка
    "clear": (0, 216, 256, 344),           # прозрачный пластик с водой (альфа)
    "clear_top": (256, 216, 320, 280),     # дно/плечо — тот же пластик, без рёбер
    "cap_g": (320, 216, 384, 248), "cap_b": (384, 216, 448, 248),
    "capt_g": (320, 248, 352, 280), "capt_b": (352, 248, 384, 280),
    "ring": (448, 216, 512, 248),          # кольцо горлышка (белое)
    "mug_out": (0, 352, 256, 440),         # кружка снаружи: белая «MAYSKIY» с сердцем
    "mug_in": (256, 352, 320, 416),        # кружка внутри: белая эмаль с налётом чая
    "tea": (320, 352, 384, 416),           # чай сверху
    "handle": (384, 352, 416, 384),        # ручка кружки (белая)
    "bowl_out": (0, 448, 256, 512),        # миска снаружи: белая, синяя кайма у края
    "bowl_in": (256, 448, 320, 512),       # миска внутри: белая, разводы борща
    "soup": (320, 448, 384, 512),          # остатки борща на дне
    "steel": (384, 448, 448, 512),         # ложка
}


def C(*c):
    return np.array(c, np.float32)


def font(name, px):
    return ImageFont.truetype(os.path.join(FONTS, name), max(4, int(px)))


def noise(h, w, cells, rng):
    g = rng.random((cells + 1, cells + 1)).astype(np.float32)
    yy = np.linspace(0, cells, h, endpoint=False); xx = np.linspace(0, cells, w, endpoint=False)
    y0, x0 = yy.astype(int), xx.astype(int)
    fy, fx = (yy - y0)[:, None], (xx - x0)[None, :]
    a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy


def rgba_of(img):
    return np.asarray(img.convert("RGBA"), np.float32) / 255.0


def label_img(w, h, bg):
    im = Image.new("RGBA", (w * SS, h * SS), tuple(int(c * 255) for c in bg) + (255,))
    return im, ImageDraw.Draw(im)


def down(im, w, h):
    return rgba_of(im.resize((w, h), Image.LANCZOS))


def fir(d, cx, base, hgt, col):
    """Ёлка из трёх ярусов треугольников (как на этикетке «Моршинської»)."""
    for k in range(3):
        top = base - hgt * (0.38 + 0.31 * k)
        wd = hgt * (0.42 - 0.09 * k)
        bot = base - hgt * 0.30 * k
        d.polygon([(cx, top - hgt * 0.30), (cx - wd, bot), (cx + wd, bot)], fill=col)
    d.rectangle([cx - hgt * 0.04, base, cx + hgt * 0.04, base + hgt * 0.08], fill=(70, 60, 40, 255))


def m_label(w, h):
    """«Моршинська»: белая этикетка, красное название, зелёный ельник справа, зелёная плашка «негазована»."""
    im, d = label_img(w, h, (0.97, 0.97, 0.96))
    W, H = w * SS, h * SS
    red, green, dgreen = (214, 32, 52, 255), (64, 170, 70, 255), (30, 120, 52, 255)
    for half in (0, 1):                    # название два раза по кругу — видно с любой стороны
        x0 = half * W // 2
        f = font("segoeuib.ttf", H * 0.27)
        d.text((x0 + W * 0.03, H * 0.14), "Моршинська", font=f, fill=red)
        tw = d.textlength("Моршинська", font=f)
        d.text((x0 + W * 0.035 + tw * 0.62, H * 0.50), "1,5 L", font=font("segoeuib.ttf", H * 0.14), fill=(120, 120, 125, 255))
        fb = font("segoeuib.ttf", H * 0.14)
        bw = d.textlength("негазована", font=fb)
        d.rounded_rectangle([x0 + W * 0.035, H * 0.56, x0 + W * 0.055 + bw, H * 0.78], radius=H * 0.05, fill=green)
        d.text((x0 + W * 0.045, H * 0.575), "негазована", font=fb, fill=(255, 255, 255, 255))
        fx = x0 + W * 0.035 + tw + W * 0.035
        for k, (dx, hh, col) in enumerate(((0.0, 0.45, green), (0.022, 0.62, dgreen), (0.046, 0.50, green), (0.066, 0.36, dgreen))):
            fir(d, fx + W * dx, H * 0.86, H * hh, col)
        d.text((x0 + W * 0.035, H * 0.82), "мінеральна вода  ·  Карпати", font=font("segoeuib.ttf", H * 0.10), fill=(90, 110, 95, 255))
    d.rectangle([0, 0, W, H * 0.04], fill=(205, 210, 212, 255))           # тонкие серые кромки этикетки
    d.rectangle([0, H * 0.96, W, H], fill=(205, 210, 212, 255))
    return down(im, w, h)


def y_label(w, h):
    """«Миргородська»: тёмно-синяя этикетка, белое название, красная лента, белый герб-колодец."""
    im, d = label_img(w, h, (0.08, 0.20, 0.52))
    W, H = w * SS, h * SS
    d.rectangle([0, H * 0.70, W, H * 0.80], fill=(205, 30, 40, 255))
    d.rectangle([0, H * 0.06, W, H * 0.09], fill=(200, 210, 230, 255))
    for half in (0, 1):
        x0 = half * W // 2
        # круглый значок: бювет
        cx, cy, r = x0 + W * 0.07, H * 0.40, H * 0.22
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 255), width=int(H * 0.03))
        d.polygon([(cx, cy - r * 0.65), (cx - r * 0.55, cy - r * 0.1), (cx + r * 0.55, cy - r * 0.1)], fill=(255, 255, 255, 255))
        d.rectangle([cx - r * 0.4, cy - r * 0.1, cx + r * 0.4, cy + r * 0.55], outline=(255, 255, 255, 255), width=int(H * 0.025))
        f = font("georgiab.ttf", H * 0.24)
        d.text((x0 + W * 0.13, H * 0.20), "Миргородська", font=f, fill=(255, 255, 255, 255))
        d.text((x0 + W * 0.13, H * 0.52), "лікувально-столова  0,5 л", font=font("segoeuib.ttf", H * 0.12), fill=(190, 210, 240, 255))
        d.text((x0 + W * 0.15, H * 0.695), "ТМ МИРГОРОД", font=font("segoeuib.ttf", H * 0.10), fill=(255, 255, 255, 255))
    return down(im, w, h)


def clear(w, h, rng):
    """Прозрачный пластик с водой: голубоватый, блики полосами вдоль бутылки, рёбра (тёмные кольца) поперёк."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / w
    col = np.ones((h, w, 3), np.float32) * C(0.70, 0.84, 0.92)
    a = np.ones((h, w), np.float32) * 0.18
    for c in (0.12, 0.62):                                    # два блика по кругу (видно с любой стороны)
        hl = np.exp(-((u - c) / 0.025) ** 2)
        col += hl[..., None] * 0.5; a += hl * 0.40
    for c in (0.32, 0.82):                                    # тёмная сторона — край стенки толще
        sh = np.exp(-((u - c) / 0.05) ** 2)
        col -= sh[..., None] * C(0.25, 0.18, 0.12); a += sh * 0.15
    a *= 0.9 + 0.2 * noise(h, w, 6, rng)
    return np.concatenate([np.clip(col, 0, 1), np.clip(a, 0, 1)[..., None]], -1)


def cap(w, h, col):
    xx = np.arange(w, dtype=np.float32)
    rib = 0.85 + 0.15 * (np.sin(xx / w * np.pi * 2 * 24) > 0)              # мелкое рифление крышки
    arr = np.ones((h, w, 3), np.float32) * C(*col) * rib[None, :, None]
    arr[: h // 6] *= 1.15                                                    # светлая кромка сверху
    return np.concatenate([np.clip(arr, 0, 1), np.ones((h, w, 1), np.float32)], -1)


def cap_top(w, h, col):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot(xx - w / 2 + 0.5, yy - h / 2 + 0.5) / (w / 2)
    arr = np.ones((h, w, 3), np.float32) * C(*col) * (1.12 - 0.25 * r)[..., None]
    arr[(r > 0.55) & (r < 0.62)] *= 0.75                                     # кольцо на торце
    return np.concatenate([np.clip(arr, 0, 1), np.ones((h, w, 1), np.float32)], -1)


def heart_pts(cx, cy, r, n=60):
    """Сердечко (классическая кривая) с центром (cx, cy) и «радиусом» r."""
    pts = []
    for k in range(n):
        t = 2 * np.pi * k / n
        x = 16 * np.sin(t) ** 3
        y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
        pts.append((cx + x / 17 * r, cy - y / 17 * r))
    return pts


def mug_out(w, h, rng):
    """Белая кружка «MAYSKIY» (с фото): красное название, под ним красное сердце-контур с надписью от руки;
    рисунок по бокам от ручки, кружка не новая — серый налёт и потёки чая от края."""
    im, d = label_img(w, h, (0.92, 0.91, 0.88))
    W, H = w * SS, h * SS
    red = (200, 40, 45, 255)
    for half in (0, 1):
        cx = half * W // 2 + W * 0.25
        f = font("arialbd.ttf", H * 0.15)
        tw = d.textlength("MAYSKIY", font=f)
        d.text((cx - tw / 2, H * 0.14), "MAYSKIY", font=f, fill=red)
        d.line(heart_pts(cx, H * 0.60, H * 0.30) + heart_pts(cx, H * 0.60, H * 0.30)[:1], fill=red, width=int(H * 0.022))
        fs = font("segoepr.ttf", H * 0.085)
        for k, line in enumerate(("Твій", "улюблений", "чай")):
            lw = d.textlength(line, font=fs)
            d.text((cx - lw / 2, H * (0.46 + 0.09 * k)), line, font=fs, fill=red)
    arr = down(im, w, h)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    drip = (noise(h, w, 9, rng) > 0.62) * np.clip(1 - yy / (h * 0.5), 0, 1)          # потёки от края
    grime = 0.80 + 0.22 * noise(h, w, 6, rng)
    arr[..., :3] *= grime[..., None]
    arr[..., :3] = arr[..., :3] * (1 - drip[..., None] * 0.25) + C(0.55, 0.42, 0.28) * drip[..., None] * 0.25
    u = np.arange(w, dtype=np.float32) / w
    hl = sum(np.exp(-((u - c) / 0.03) ** 2) for c in (0.05, 0.55))
    arr[..., :3] += hl[None, :, None] * 0.12
    arr[: h // 16, :, :3] *= 0.85                                                       # грязный ободок
    return np.concatenate([np.clip(arr[..., :3], 0, 1), arr[..., 3:]], -1)


def plain(w, h, col, rng, amp=0.08):
    arr = np.ones((h, w, 3), np.float32) * C(*col) * (1 - amp + 2 * amp * noise(h, w, 4, rng))[..., None]
    return np.concatenate([np.clip(arr, 0, 1), np.ones((h, w, 1), np.float32)], -1)


def mug_in(w, h, rng):
    """Кружка изнутри (u — по кругу, v сверху — край): белая, в коричневых кольцах налёта от чая, ниже уровня —
    сплошной налёт."""
    arr = plain(w, h, (0.88, 0.86, 0.82), rng, 0.05)
    yy = np.arange(h, dtype=np.float32)[:, None] / h + 0.04 * (noise(h, w, 4, rng) - 0.5)
    stain = np.clip((yy - 0.55) / 0.10, 0, 1)
    for c in (0.18, 0.30, 0.42):                                                     # кольца прошлых чаепитий
        stain = np.maximum(stain, 0.55 * np.exp(-((yy - c) / 0.018) ** 2))
    stain *= 0.7 + 0.5 * noise(h, w, 7, rng)
    arr[..., :3] = arr[..., :3] * (1 - stain[..., None] * 0.6) + C(0.42, 0.24, 0.10) * stain[..., None] * 0.6
    arr[..., :3] = np.clip(arr[..., :3], 0, 1)
    return arr


def tea(w, h, rng):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot(xx - w / 2 + 0.5, yy - h / 2 + 0.5) / (w / 2)
    arr = np.ones((h, w, 3), np.float32) * C(0.30, 0.13, 0.04)
    arr *= (0.85 + 0.25 * np.clip(r, 0, 1))[..., None]
    hl = np.exp(-(((xx - w * 0.36) / (w * 0.10)) ** 2 + ((yy - h * 0.34) / (h * 0.06)) ** 2))
    arr += hl[..., None] * C(0.45, 0.40, 0.32)                               # мягкий блик лампы на чае
    return np.concatenate([arr, np.ones((h, w, 1), np.float32)], -1)


def bowl_out(w, h, rng):
    """Миска снаружи (v сверху — край): белая, синяя кайма у края, ниже — тонкая синяя полоска."""
    arr = plain(w, h, (0.92, 0.92, 0.90), rng, 0.04)
    arr[: int(h * 0.12), :, :3] = C(0.12, 0.25, 0.62)
    arr[int(h * 0.20):int(h * 0.24), :, :3] = C(0.20, 0.35, 0.70)
    u = np.arange(w, dtype=np.float32) / w
    hl = sum(np.exp(-((u - c) / 0.04) ** 2) for c in (0.1, 0.6))
    arr[..., :3] += hl[None, :, None] * 0.12
    return arr


def bowl_in(w, h, rng):
    """Миска изнутри (v сверху — край, снизу — дно): белая, ближе ко дну — красноватые потёки борща."""
    arr = plain(w, h, (0.93, 0.92, 0.89), rng, 0.03)
    arr[: int(h * 0.07), :, :3] = C(0.12, 0.25, 0.62)                       # кайма заходит на край
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    streak = (np.sin(xx / w * np.pi * 2 * 7 + noise(h, w, 3, rng) * 6) * 0.5 + 0.5) ** 3
    amt = np.clip((yy / h - 0.45) / 0.5, 0, 1) * (0.35 + 0.65 * streak)
    arr[..., :3] = arr[..., :3] * (1 - amt[..., None] * 0.6) + C(0.70, 0.18, 0.12) * amt[..., None] * 0.6
    return arr


def soup(w, h, rng):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    arr = np.ones((h, w, 3), np.float32) * C(0.62, 0.12, 0.08) * (0.8 + 0.35 * noise(h, w, 5, rng))[..., None]
    fat = noise(h, w, 9, rng) > 0.78                                          # жирные пятнышки
    arr[fat] = C(0.85, 0.45, 0.20)
    bits = noise(h, w, 14, rng) > 0.83                                        # капуста / свёкла
    arr[bits] = C(0.80, 0.70, 0.45)
    return np.concatenate([arr, np.ones((h, w, 1), np.float32)], -1)


def steel(w, h, rng):
    u = np.arange(w, dtype=np.float32) / w
    g = 0.55 + 0.35 * np.exp(-((u - 0.4) / 0.12) ** 2) - 0.15 * u
    arr = np.ones((h, w, 3), np.float32) * C(0.82, 0.84, 0.86) * g[None, :, None]
    arr *= (0.95 + 0.08 * noise(h, w, 8, rng))[..., None]
    return np.concatenate([np.clip(arr, 0, 1), np.ones((h, w, 1), np.float32)], -1)


def main():
    rng = np.random.default_rng(1500)
    at = np.zeros((SIZE, SIZE, 4), np.float32)
    at[..., :3] = 0.5; at[..., 3] = 1.0

    def put(name, arr):
        x0, y0, x1, y1 = A[name]
        at[y0:y1, x0:x1] = arr[: y1 - y0, : x1 - x0]

    def wh(name):
        x0, y0, x1, y1 = A[name]
        return x1 - x0, y1 - y0

    put("m_label", m_label(*wh("m_label")))
    put("y_label", y_label(*wh("y_label")))
    put("clear", clear(*wh("clear"), rng))
    ct = clear(*wh("clear_top"), rng); put("clear_top", ct)
    put("cap_g", cap(*wh("cap_g"), (0.20, 0.62, 0.22)))
    put("cap_b", cap(*wh("cap_b"), (0.10, 0.28, 0.72)))
    put("capt_g", cap_top(*wh("capt_g"), (0.22, 0.66, 0.24)))
    put("capt_b", cap_top(*wh("capt_b"), (0.12, 0.30, 0.76)))
    put("ring", plain(*wh("ring"), (0.90, 0.92, 0.92), rng, 0.03))
    put("mug_out", mug_out(*wh("mug_out"), rng))
    put("mug_in", mug_in(*wh("mug_in"), rng))
    put("tea", tea(*wh("tea"), rng))
    put("handle", plain(*wh("handle"), (0.86, 0.85, 0.81), rng, 0.10))
    put("bowl_out", bowl_out(*wh("bowl_out"), rng))
    put("bowl_in", bowl_in(*wh("bowl_in"), rng))
    put("soup", soup(*wh("soup"), rng))
    put("steel", steel(*wh("steel"), rng))
    # лёгкий PS2-финиш: 15-битный цвет (альфа не трогаем)
    rgb = np.round(np.clip(at[..., :3], 0, 1) * 31) / 31
    out = np.concatenate([rgb, at[..., 3:]], -1)
    path = os.path.join(TEX, "dc_atlas.png")
    Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA").save(path)
    print("saved", path)


if __name__ == "__main__":
    main()
