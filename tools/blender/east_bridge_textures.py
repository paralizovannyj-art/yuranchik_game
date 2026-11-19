# Текстуры локации «Восточный ж/д мост» (YUR-7): станция Одесса-Восточная зимой.
# PS2-стиль, как у района: низкое разрешение, запечённая грязь, снег.
# Запуск в открытом Blender (через Blender MCP):
#   EB_ROOT = r"<папка проекта>"; exec(open(EB_ROOT + r"\tools\blender\east_bridge_textures.py", encoding="utf-8").read())
# Все текстуры — с префиксом eb_ в assets/textures/. Таблица PS2-обработки — tools/blender/ps2_style.py (TEXTURES).
import os
import sys

ROOT = globals().get("EB_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import importlib
import numpy as np
import bpy
import tex_lib
import ps2_style
importlib.reload(ps2_style)
importlib.reload(tex_lib)
tex_lib.TEX_DIR = os.path.join(ROOT, "assets", "textures")
tex_lib.LIB = os.path.join(ROOT, "assets", "texture_library", "ambientcg")
from tex_lib import fbm, vnoise, streaks, rgb, fill, save, photo, tile, draw_text, text_width, FONT

R = np.random.default_rng(7007)
SNOW = rgb((0.80, 0.83, 0.90))

# недостающие буквы для вывески «ОДЕСА-СХІДНА»
FONT.setdefault('Х', ["10001", "10001", "01010", "00100", "01010", "10001", "10001"])
FONT.setdefault('І', ["01110", "00100", "00100", "00100", "00100", "00100", "01110"])


def save_rgba(name, arr):
    """Как tex_lib.save, но с альфой (решётки, сетка-рабица). PS2-обработка не трогает альфу."""
    arr = ps2_style.ps2_pass(arr, name)
    h, w, _ = arr.shape
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=True)
    if img.size[0] != w or img.size[1] != h:
        img.scale(w, h)
    img.alpha_mode = 'STRAIGHT'
    img.pixels.foreach_set(np.clip(arr[::-1], 0, 1).astype(np.float32).ravel())
    path = os.path.join(tex_lib.TEX_DIR, name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    img.filepath = path
    return path


def gravel(w, h, rng, cells=90):
    """Щебень: мелкие пятна разной яркости с тенью снизу."""
    a = vnoise(w, h, cells, cells, rng)
    b = vnoise(w, h, cells // 2, cells // 2, rng)
    g = np.clip((a - 0.35) * 2.2, 0, 1) * 0.7 + b * 0.3
    sh = np.roll(g, 2, axis=0)
    g = g - np.clip(sh - g, 0, 1) * 0.6
    return np.clip(g, 0, 1)


def snow_cover(w, h, rng, amount, cells=5):
    n = fbm(w, h, cells, cells, rng)
    return np.clip((n - (1 - amount)) * 3.5, 0, 1)


def snow_tex(w, h, rng):
    return SNOW * (0.82 + fbm(w, h, 20, 20, rng, oct=2)[..., None] * 0.2)


# ------------------------------------------------------------------ пути
def ballast():
    """Щебень междупутья 4×4 м, почти весь под снегом, проталины тёмного щебня."""
    w = h = 256
    g = gravel(w, h, R)
    base = rgb((0.30, 0.28, 0.26)) * (0.45 + g[..., None] * 0.9)
    base *= 1 - streaks(w, h, R, 0.4)[..., None] * 0.15
    rust = np.clip((fbm(w, h, 6, 6, R) - 0.55) * 3, 0, 1)[..., None]
    base = base * (1 - rust * 0.4) + rgb((0.30, 0.17, 0.08)) * rust * 0.4
    m = snow_cover(w, h, R, 0.72)[..., None]
    arr = base * (1 - m) + snow_tex(w, h, R) * m
    save("eb_ballast", arr)


def trackbed():
    """Путь: полоса 3,2 м поперёк (u) × 3,3 м вдоль (v), 6 бетонных шпал по 0,55 м.
    Между шпалами щебень со снегом, под рельсами ржавые полосы."""
    w = h = 256
    g = gravel(w, h, R)
    arr = rgb((0.27, 0.25, 0.23)) * (0.45 + g[..., None] * 0.9)
    v = (np.arange(h, dtype=np.float32) + 0.5) / h * 3.3
    u = (np.arange(w, dtype=np.float32) + 0.5) / w * 3.2
    sl = (np.abs((v % 0.55) - 0.275) < 0.135)[:, None] & ((u > 0.25) & (u < 2.95))[None, :]
    conc = rgb((0.47, 0.46, 0.44)) * (0.8 + fbm(w, h, 30, 30, R, oct=3)[..., None] * 0.35)
    edge = (np.abs((v % 0.55) - 0.275) > 0.11)[:, None] & sl
    arr = np.where(sl[..., None], conc, arr)
    arr = np.where(edge[..., None], arr * 0.7, arr)
    m = snow_cover(w, h, R, 0.62, cells=6)
    m = np.where(sl, m * 0.55, np.clip(m + 0.15, 0, 1))[..., None]         # на шпалах снега меньше — их видно
    arr = arr * (1 - m) + snow_tex(w, h, R) * m
    for ur in (1.6 - 0.76, 1.6 + 0.76):                                      # ржавчина и мазут под рельсами
        d = np.exp(-((u - ur) / 0.09) ** 2)[None, :, None]
        arr = arr * (1 - d * 0.55) + rgb((0.20, 0.11, 0.05)) * d * 0.55
    save("eb_trackbed", arr)


# ------------------------------------------------------------------ мост и платформы
def white_paint():
    """Перила и столбы моста: белая краска 1×1 м, ржавые сколы и серые потёки."""
    w = h = 128
    arr = rgb((0.80, 0.80, 0.76)) * (0.9 + fbm(w, h, 8, 8, R)[..., None] * 0.15)
    chip = np.clip((fbm(w, h, 12, 12, R, oct=4) - 0.70) * 6, 0, 1)[..., None]
    arr = arr * (1 - chip) + rgb((0.36, 0.20, 0.10)) * chip
    st = streaks(w, h, R, 0.8)[..., None] * 0.25
    arr = arr * (1 - st) + rgb((0.35, 0.33, 0.30)) * st
    save("eb_white", arr)


def deck():
    """Настил моста 3×3 м (u — поперёк): бетон, по краям снег, посередине натоптанная серая каша."""
    w = h = 256
    base = photo("Concrete034", w, relief=0.8, sat=0.3, gain=0.6, tint=(0.9, 0.92, 0.98))
    u = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    path = np.exp(-((u - 0.5) / 0.26) ** 2) * (0.8 + fbm(w, h, 3, 8, R) * 0.4)
    snow = snow_cover(w, h, R, 0.85, cells=4) * (1 - path * 0.85)
    slush = base * 0.55 + rgb((0.30, 0.30, 0.32)) * 0.45
    m = np.clip(snow, 0, 1)[..., None]
    arr = slush * (1 - m) + snow_tex(w, h, R) * m
    for p in (0, 128):                                                        # швы плит настила
        arr[p:p + 2, :] *= 0.55
    save("eb_deck", arr)


def platform():
    """Платформа 4×4 м: старый асфальт с трещинами, утоптанный снег пятнами."""
    w = h = 256
    base = photo("Road013A", w, relief=0.8, sat=0.3, gain=0.6) * 0.5 + rgb((0.30, 0.30, 0.31)) * 0.5
    m = snow_cover(w, h, R, 0.75, cells=5)[..., None]
    arr = base * (1 - m) + snow_tex(w, h, R) * 0.92 * m
    save("eb_platform", arr)


def platform_edge():
    """Край платформы 4×1 м: бетонная стенка с белой полосой сверху и потёками."""
    w, h = 256, 64
    base = photo("Concrete012", w, h, relief=0.9, sat=0.3, gain=0.55, tint=(0.9, 0.92, 0.96))
    base *= 1 - streaks(w, h, R, 0.8)[..., None] * 0.35
    base[:9] = rgb((0.82, 0.82, 0.78)) * (0.85 + fbm(w, 9, 20, 2, R)[..., None] * 0.2)
    base[9:11] *= 0.5
    base[-8:] = base[-8:] * 0.4 + SNOW * 0.6
    save("eb_platform_edge", base)


def booth():
    """Будка на платформе 2×2 м: голубой профнастил, ржавые потёки, обрывки граффити."""
    w = h = 128
    arr = photo("CorrugatedSteel007A", w, relief=1.0, sat=0.6, gain=1.25, tint=(0.75, 0.95, 1.1))
    rust = streaks(w, h, R, 0.5) * (fbm(w, h, 4, 2, R) > 0.5)
    arr = arr * (1 - rust[..., None] * 0.5) + rgb((0.32, 0.16, 0.06)) * rust[..., None] * 0.5
    x, y = 24.0, 84.0                                                          # каракули маркером: случайная ломаная
    for _ in range(260):
        x = float(np.clip(x + R.normal(0.6, 1.6), 18, 100))
        y = float(np.clip(y + R.normal(0, 2.4), 62, 104))
        arr[int(y) - 1:int(y) + 1, int(x) - 1:int(x) + 1] = rgb((0.82, 0.82, 0.84))
    save("eb_booth", arr)


def cabinet():
    """Релейные шкафы и трансформаторные будки 1×1 м: серая краска, ржавые края."""
    w = h = 128
    arr = rgb((0.46, 0.48, 0.48)) * (0.85 + fbm(w, h, 6, 6, R)[..., None] * 0.3)
    rust = np.clip((fbm(w, h, 8, 8, R, oct=4) - 0.68) * 5, 0, 1)[..., None]
    arr = arr * (1 - rust) + rgb((0.30, 0.17, 0.08)) * rust
    arr *= 1 - streaks(w, h, R, 0.7)[..., None] * 0.3
    save("eb_cabinet", arr)


# ------------------------------------------------------------------ вагоны
def tank():
    """Цистерна: развёртка котла, верх атласа — жёлтая, низ — чёрная. Грязь и мазут снизу, светлые потёки."""
    w = h = 256
    arr = np.zeros((h, w, 3), np.float32)
    for k, col in enumerate(((0.72, 0.56, 0.14), (0.10, 0.10, 0.10))):
        y0, y1 = k * 128, (k + 1) * 128
        part = rgb(col) * (0.85 + fbm(w, 128, 8, 4, R)[..., None] * 0.3)
        v = np.linspace(0, 1, 128, dtype=np.float32)[:, None, None]
        dirt = np.clip(np.abs(v - 0.5) * 2.2 - 0.6, 0, 1) * 0.8                    # грязь у «низа» котла
        part = part * (1 - dirt) + rgb((0.08, 0.06, 0.05)) * dirt
        drip = streaks(w, 128, R, 1.2)[..., None] * (0.25 if k == 0 else 0.12)
        part = part * (1 - drip) + rgb((0.35, 0.30, 0.22)) * drip
        arr[y0:y1] = part
    save("eb_tank", arr)


def gondola():
    """Полувагон: борт целиком (u — длина 13,9 м, v — высота 2,1 м). Ржавый, с рёбрами и граффити."""
    w, h = 256, 64
    arr = photo("Metal021", w, h, relief=0.9, sat=0.8, gain=0.9, tint=(0.95, 0.75, 0.6))
    for x in np.linspace(6, w - 6, 13).astype(int):                               # стойки кузова
        arr[:, x - 2:x + 2] *= 0.55
        arr[:, x + 2:x + 3] *= 1.25
    arr[:5] *= 0.6
    arr[-6:] *= 0.5
    gx = R.integers(30, 160)
    blot = np.zeros((h, w), bool)
    x, y = float(gx), 30.0                                                        # тег баллончиком: ломаная линия
    for _ in range(220):
        x = float(np.clip(x + R.normal(0.35, 1.2), gx, gx + 70))
        y = float(np.clip(y + R.normal(0, 2.0), 16, 50))
        blot[int(y) - 1:int(y) + 1, int(x):int(x) + 2] = True
    arr[blot] = arr[blot] * 0.35 + rgb((0.70, 0.72, 0.78)) * 0.65
    save("eb_gondola", arr)


def container():
    """Контейнеры 12 м: атлас из 4 строк (красный, синий, охра, серо-зелёный), гофра, потёки."""
    w = h = 256
    cols = ((0.55, 0.13, 0.10), (0.12, 0.22, 0.42), (0.70, 0.52, 0.16), (0.32, 0.38, 0.34))
    arr = np.zeros((h, w, 3), np.float32)
    x = np.arange(w, dtype=np.float32)
    rib = (0.85 + 0.15 * np.sign(np.sin(x / w * 2 * np.pi * 36)))[None, :, None]
    for k, c in enumerate(cols):
        part = rgb(c) * rib * (0.85 + fbm(w, 64, 10, 3, R)[..., None] * 0.3)
        part *= 1 - streaks(w, 64, R, 1.0)[..., None] * 0.3
        part[:3] *= 0.6
        part[-3:] *= 0.5
        arr[k * 64:(k + 1) * 64] = part
    save("eb_container", arr)


def coach():
    """Пассажирский вагон: борт 24 м × 3 м, синий с жёлтой полосой, 10 окон; в двух горит тусклый свет."""
    w, h = 512, 64
    arr = rgb((0.10, 0.20, 0.42)) * (0.85 + fbm(w, h, 16, 3, R)[..., None] * 0.3)
    emi = np.zeros((h, w, 3), np.float32)
    arr[38:41] = rgb((0.75, 0.62, 0.15))
    arr[-8:] *= 0.45
    lit = {3, 7}
    for i in range(10):
        x0 = int(40 + i * 44)
        glass = rgb((0.04, 0.05, 0.07))
        if i in lit:
            glass = rgb((0.9, 0.72, 0.42))
            emi[14:32, x0:x0 + 30] = glass
        arr[14:32, x0:x0 + 30] = glass
        arr[13:14, x0:x0 + 30] = rgb((0.6, 0.6, 0.6))
    for x0 in (10, w - 26):                                                       # двери в тамбурах
        arr[8:58, x0:x0 + 16] *= 0.75
    arr *= 1 - streaks(w, h, R, 1.0)[..., None] * 0.25
    save("eb_coach", arr)
    save("eb_coach_emission", emi)


# ------------------------------------------------------------------ контактная сеть, сетка, фонари
def lattice():
    """Решётка ригеля и опор контактной сети: панель 2 м × 1 м, пояса сверху/снизу, раскосы «W». Альфа."""
    w, h = 128, 64
    a = np.zeros((h, w), np.float32)
    a[:5] = 1
    a[-5:] = 1
    a[:, :4] = 1
    a[:, -4:] = 1
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for x0, x1 in ((0, 64), (64, 128)):
        for flip in (False, True):
            xa, xb = (x0, x1) if not flip else (x1, x0)
            d = np.abs((yy - 0) * (xb - xa) - (xx - xa) * (h - 1)) / np.hypot(xb - xa, h - 1)
            a[(d < 2.6) & (xx >= min(x0, x1)) & (xx <= max(x0, x1))] = 1
    col = rgb((0.30, 0.27, 0.24)) * (0.8 + fbm(w, h, 8, 4, R)[..., None] * 0.4)
    rust = np.clip((fbm(w, h, 6, 6, R) - 0.5) * 3, 0, 1)[..., None]
    col = col * (1 - rust * 0.5) + rgb((0.35, 0.18, 0.08)) * rust * 0.5
    col[:3] = col[:3] * 0.4 + SNOW * 0.6                                         # снег на верхнем поясе
    save_rgba("eb_lattice", np.concatenate([col, a[..., None]], axis=2))


def chainlink():
    """Сетка-рабица ограждения над контактной сетью: ромбы 1×1 м (8×8 ячеек). Альфа."""
    w = h = 128
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    p = 16.0
    d1 = np.abs(((xx + yy) % p) - p / 2)
    d2 = np.abs(((xx - yy) % p) - p / 2)
    a = ((d1 > p / 2 - 1.1) | (d2 > p / 2 - 1.1)).astype(np.float32)
    a[:3] = 1
    a[-3:] = 1
    col = rgb((0.62, 0.63, 0.62)) * (0.8 + fbm(w, h, 6, 6, R)[..., None] * 0.3)
    save_rgba("eb_mesh", np.concatenate([col, a[..., None]], axis=2))


def lamps():
    """Плафоны фонарей: зелёный (ртутная лампа, как на ночных фото станции) и натриевый оранжевый."""
    for name, c in (("eb_lamp_green", (0.55, 1.0, 0.55)), ("eb_lamp_orange", (1.0, 0.62, 0.25))):
        arr = fill(16, 16, c)
        arr[:, :] *= 0.85 + 0.15 * np.linspace(0, 1, 16, dtype=np.float32)[:, None, None]
        save(name, arr)


# ------------------------------------------------------------------ вокзал
def station():
    """Стены павильона «Одеса-Східна» 3×3 м: светлая облупленная штукатурка."""
    w = h = 256
    arr = photo("PaintedPlaster006", w, relief=0.9, sat=0.5, gain=1.15, tint=(1.0, 0.97, 0.88))
    save("eb_station", arr)


def station_sign():
    """Вывеска на фронтоне: синие буквы на белом."""
    txt = "ОДЕСА-СХІДНА"
    sc = 3
    w, h = 256, 32
    arr = fill(h, w, (0.86, 0.86, 0.82))
    x = (w - text_width(txt, sc)) // 2
    draw_text(arr, txt, x, (h - 7 * sc) // 2, sc, rgb((0.10, 0.25, 0.65)))
    save("eb_sign_station", arr)


def main():
    for fn in (ballast, trackbed, white_paint, deck, platform, platform_edge, booth, cabinet,
               tank, gondola, container, coach, lattice, chainlink, lamps, station, station_sign):
        fn()
    return {"textures": sorted(f for f in os.listdir(tex_lib.TEX_DIR) if f.startswith("eb_") and f.endswith(".png"))}


result = main()
print(result)
