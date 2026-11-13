# Текстуры пропсов микрорайона (этап B): машины и трамвай (один атлас), бетонный забор, обмотка труб, жёлтая краска.
# Запуск:  blender -b --python tools/blender/district_textures_props.py
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import numpy as np
import tex_lib
tex_lib.TEX_DIR = os.path.join(ROOT, "assets", "textures")
tex_lib.LIB = os.path.join(ROOT, "assets", "texture_library", "ambientcg")
from tex_lib import fbm, streaks, rgb, fill, save, photo, tile, rust_mask

R = np.random.default_rng(777)


def dirty(arr, strength=0.35):
    h, w, _ = arr.shape
    arr *= (0.85 + fbm(w, h, 6, 6, R)[..., None] * 0.3)
    grad = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None] ** 2          # грязь снизу
    arr *= 1 - grad * strength
    arr += grad * strength * rgb((0.10, 0.09, 0.07))
    return arr


def vehicles():
    """Атлас 256×256, 4 ряда по 64 px: краска кузовов | борт трамвая | борт маршрутки | стекло, резина, тент, ржавчина."""
    a = np.zeros((256, 256, 3), np.float32)
    # ряд 0: четыре цвета кузова
    for i, c in enumerate(((0.74, 0.74, 0.70), (0.45, 0.12, 0.10), (0.15, 0.25, 0.42), (0.20, 0.33, 0.22))):
        a[0:64, i*64:(i+1)*64] = dirty(fill(64, 64, c))
    # ряд 1: борт трамвая — кремовый верх с окнами, красный низ
    row = np.zeros((64, 256, 3), np.float32)
    row[0:36] = rgb((0.80, 0.74, 0.58))
    row[36:64] = rgb((0.55, 0.10, 0.08))
    row[34:37] = rgb((0.15, 0.13, 0.12))
    for i in range(4):
        x0 = i * 64
        row[6:30, x0+8:x0+56] = rgb((0.05, 0.07, 0.09)) + np.linspace(0.10, 0.0, 24, dtype=np.float32)[:, None, None] * rgb((0.5, 0.7, 1.0))
        row[6:30, x0+31:x0+33] = rgb((0.2, 0.2, 0.2))
    a[64:128] = dirty(row, 0.45)
    # ряд 2: борт маршрутки — жёлтый с лентой окон
    row = fill(64, 256, (0.80, 0.62, 0.10))
    for i in range(4):
        x0 = i * 64
        row[6:28, x0+6:x0+58] = rgb((0.05, 0.07, 0.09)) + np.linspace(0.08, 0.0, 22, dtype=np.float32)[:, None, None] * rgb((0.5, 0.7, 1.0))
    row[40:44] = rgb((0.12, 0.12, 0.12))
    a[128:192] = dirty(row, 0.5)
    # ряд 3: стекло | резина | тент | ржавчина
    yy = np.linspace(0, 1, 64, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, 64, dtype=np.float32)[None, :]
    glass = (0.04 + 0.10 * (1 - yy) * (((xx + yy * 0.6) % 0.4) < 0.15))[..., None] * rgb((0.8, 0.95, 1.3))
    a[192:256, 0:64] = glass
    a[192:256, 64:128] = fill(64, 64, (0.05, 0.05, 0.055)) * (0.7 + fbm(64, 64, 8, 8, R)[..., None] * 0.6)
    tarp = fill(64, 64, (0.30, 0.36, 0.42)) * (0.75 + 0.25 * np.sin(xx * 30)[..., None]) * (0.8 + fbm(64, 64, 4, 4, R)[..., None] * 0.4)
    a[192:256, 128:192] = dirty(tarp, 0.4)
    a[192:256, 192:256] = photo("Metal021", 64, relief=0.8, sat=1.1, gain=0.8)
    save("vehicles", a)


def fence_concrete():
    """Советский бетонный забор «ёлочка»: плита с ромбами в раме."""
    w = h = 128
    arr = photo("Concrete034", w, relief=0.9, sat=0.4, tint=(0.62, 0.62, 0.6))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx = (xx / 32.0) % 1.0
    fy = (yy / 32.0) % 1.0
    d = np.abs(fx - 0.5) + np.abs(fy - 0.5)                    # ромб в каждой клетке
    light = np.where(fy < 0.5, 1.12, 0.82)                    # верхние грани светлее, нижние темнее
    bump = np.where(d < 0.46, light, 0.9)
    arr *= bump[..., None]
    arr[:6] *= 0.6; arr[-10:] *= 0.55; arr[:, :4] *= 0.6; arr[:, -4:] *= 0.6
    st = streaks(w, h, R, 0.6) * fbm(w, h, 4, 4, R)
    arr *= (1 - st[..., None] * 0.3)
    save("fence_concrete", arr)


def pipe_wrap():
    """Обмотка теплотрассы: серая фольга с хомутами, местами рваная — торчит жёлтая вата."""
    w, h = 128, 64
    arr = fill(h, w, (0.56, 0.57, 0.56)) * (0.75 + fbm(w, h, 10, 6, R)[..., None] * 0.5)
    arr *= (0.7 + 0.3 * np.sin(np.linspace(0, np.pi, h, dtype=np.float32))[:, None, None])   # объём по окружности
    for x in range(0, w, 32):
        arr[:, x:x+2] *= 0.35
    torn = np.clip((fbm(w, h, 5, 3, R) - 0.62) * 6, 0, 1)[..., None]
    wool = rgb((0.62, 0.50, 0.22)) * (0.7 + fbm(w, h, 20, 12, R)[..., None] * 0.5)
    arr = arr * (1 - torn) + wool * torn
    st = streaks(w, h, R, 0.5)
    arr *= (1 - st[..., None] * 0.2)
    save("pipe_insul", arr)


def paint_yellow():
    """Облезлая жёлтая краска стройтехники с ржавчиной."""
    w = h = 64
    p = photo("PaintedMetal013", w, relief=0.8)
    rm = rust_mask("PaintedMetal013", w)[..., None]
    arr = p * rgb((1.5, 1.2, 0.25)) * (1 - rm) + p * rm
    save("paint_yellow", np.clip(arr, 0, 1))


vehicles()
fence_concrete()
pipe_wrap()
paint_yellow()
print("props textures: ok")
