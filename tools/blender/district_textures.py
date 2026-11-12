# Текстуры домов микрорайона (этап B, docs/CITY_PLAN.md). PS2-стиль: 64 px на окно, запечённая грязь.
# Запуск (пути берутся от расположения файла, работает и из worktree):
#   blender -b --python tools/blender/district_textures.py
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import numpy as np
import tex_lib
tex_lib.TEX_DIR = os.path.join(ROOT, "assets", "textures")
tex_lib.LIB = os.path.join(ROOT, "assets", "texture_library", "ambientcg")
from tex_lib import fbm, streaks, rgb, fill, save, photo, tile

R = np.random.default_rng(2026)

FRAMES = [rgb((0.72, 0.70, 0.64)), rgb((0.34, 0.24, 0.16)), rgb((0.86, 0.86, 0.84)), rgb((0.55, 0.52, 0.45))]
LIGHTS = [rgb((1.0, 0.70, 0.36)), rgb((1.0, 0.82, 0.55)), rgb((0.95, 0.55, 0.28)), rgb((0.45, 0.65, 1.0))]
CURTAINS = [rgb((0.6, 0.15, 0.1)), rgb((0.75, 0.65, 0.4)), rgb((0.25, 0.4, 0.3)), rgb((0.8, 0.8, 0.75))]


def window(arr, emi, x0, x1, y0, y1, lit, mullions=1, sill=True):
    """Окно с рамой, шторами, отливом и ржавым потёком. lit — горит ли свет."""
    fr = FRAMES[R.integers(0, 4)] * (0.85 + R.random() * 0.2)
    cur = R.random() < 0.65
    curc = CURTAINS[R.integers(0, 4)]
    lc = LIGHTS[R.integers(0, 3) if R.random() < 0.9 else 3]
    gh, gw = y1 - y0, x1 - x0
    yy = np.linspace(0, 1, gh, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, gw, dtype=np.float32)[None, :]
    if lit:
        glass = lc[None, None, :] * (0.65 + 0.35 * yy[..., None]) * np.ones((gh, gw, 1), np.float32)
        if cur:
            folds = 0.75 + 0.25 * np.sin(xx * 40)[..., None]
            side = ((xx < 0.28) | (xx > 0.72))[..., None]
            glass = np.where(side, glass * curc * 1.4 * folds, glass)
        arr[y0:y1, x0:x1] = glass * 0.7
        emi[y0:y1, x0:x1] = glass
    else:
        refl = 0.04 + 0.08 * (1 - yy) * (((xx + yy * 0.6) % 0.35) < 0.12)
        glass = np.ones((gh, gw, 3), np.float32) * refl[..., None] * rgb((0.8, 0.95, 1.3))
        if cur and R.random() < 0.5:
            glass = glass * 0.4 + curc * 0.10
        arr[y0:y1, x0:x1] = glass
    arr[y0:y0+3, x0:x1] = fr; arr[y1-3:y1, x0:x1] = fr
    arr[y0:y1, x0:x0+3] = fr; arr[y0:y1, x1-3:x1] = fr
    emi[y0:y0+3, x0:x1] = 0; emi[y1-3:y1, x0:x1] = 0
    emi[y0:y1, x0:x0+3] = 0; emi[y0:y1, x1-3:x1] = 0
    for k in range(1, mullions + 1):
        mx = x0 + gw * k // (mullions + 1) if mullions > 1 else (x0 + gw // 3 if R.random() < 0.5 else x0 + gw // 2)
        arr[y0:y1, mx-1:mx+2] = fr
        emi[y0:y1, mx-1:mx+2] = 0
    if sill:
        arr[y1:y1+3, x0-3:x1+3] = rgb((0.30, 0.31, 0.32))
        run = np.clip(np.linspace(1, 0, 12, dtype=np.float32), 0, 1)[:, None, None]
        for k in range(R.integers(1, 4)):
            sx = R.integers(x0, x1 - 3)
            seg = arr[y1+3:y1+15, sx:sx+3]
            n = seg.shape[0]
            seg *= (1 - run[:n] * 0.45)
            seg += run[:n] * rgb((0.10, 0.04, 0.0))


def seams(arr, rows, cols, cw, ch, dark=0.25):
    h, w, _ = arr.shape
    for r in range(rows + 1):
        y = min(r * ch, h - 2)
        arr[y:y+2, :] = arr[y:y+2, :] * dark + rgb((0.03, 0.03, 0.03))
    for c in range(cols + 1):
        x = min(c * cw, w - 2)
        arr[:, x:x+2] = arr[:, x:x+2] * dark + rgb((0.03, 0.03, 0.03))


def grime(arr, strength=0.22):
    h, w, _ = arr.shape
    st = streaks(w, h, R, 0.5) * fbm(w, h, 6, 4, R)
    grad = np.linspace(0.5, 1.4, h, dtype=np.float32)[:, None]
    arr *= (1 - st[..., None] * strength * grad[..., None])


def panel_facade(name, lit_p, tint, src_id="Concrete036", rows=9):
    """Панелька, вариант: другой тон бетона и другой рисунок горящих окон."""
    cols, cell = 8, 64
    w, h = cols * cell, rows * cell
    src = photo(src_id, 192, relief=0.9, sat=0.5, gain=1.05, tint=tint)
    arr = np.zeros((h, w, 3), np.float32)
    emi = np.zeros((h, w, 3), np.float32)
    for r in range(rows):
        for c in range(cols):
            oy, ox = R.integers(0, 192 - cell, 2)
            arr[r*cell:(r+1)*cell, c*cell:(c+1)*cell] = src[oy:oy+cell, ox:ox+cell] * (1 + (R.random() - 0.5) * 0.12)
    grime(arr)
    seams(arr, rows, cols, cell, cell)
    for r in range(rows):
        for c in range(cols):
            window(arr, emi, c*cell + 10, c*cell + 54, r*cell + 14, r*cell + 46, R.random() < lit_p)
    save(name + "_albedo", arr)
    save(name + "_emission", emi)


def khr_facade():
    """Хрущёвка: кирпич, 5 этажей, окна поменьше."""
    cols, rows, cw, ch = 8, 5, 64, 64
    w, h = cols * cw, rows * ch
    arr = tile(photo("Bricks105", 256, relief=1.0, sat=0.75, gain=0.8, tint=(0.95, 0.8, 0.72)), w, h)
    emi = np.zeros((h, w, 3), np.float32)
    grime(arr, 0.3)
    arr *= (0.85 + fbm(w, h, 5, 3, R)[..., None] * 0.3)
    for r in range(rows + 1):                       # бетонные пояса перекрытий
        y = min(r * ch, h - 3)
        arr[y:y+3, :] = rgb((0.42, 0.41, 0.39)) * (0.8 + R.random() * 0.2)
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c*cw + 14, r*ch + 16
            arr[y0-4:y0, x0-2:x0+38] = rgb((0.5, 0.49, 0.46))     # перемычка над окном
            window(arr, emi, x0, x0 + 36, y0, y0 + 30, R.random() < 0.12)
    save("khr_albedo", arr)
    save("khr_emission", emi)


def school_facade():
    """Школа: жёлтая штукатурка, большие трёхстворчатые окна, почти всё темно."""
    cols, rows, cw, ch = 8, 3, 64, 72
    w, h = cols * cw, rows * ch
    arr = tile(photo("PaintedPlaster006", 256, relief=0.8, sat=0.7, tint=(1.0, 0.86, 0.55), gain=0.95), w, h)
    emi = np.zeros((h, w, 3), np.float32)
    grime(arr, 0.3)
    lit_cell = (R.integers(0, rows), R.integers(0, cols))
    for r in range(rows):
        y = r * ch
        arr[y:y+3, :] *= 0.55
        for c in range(cols):
            window(arr, emi, c*cw + 6, c*cw + 58, y + 16, y + 56, (r, c) == lit_cell, mullions=2)
    arr[-10:] *= np.linspace(1.0, 0.6, 10, dtype=np.float32)[:, None, None]
    save("school_albedo", arr)
    save("school_emission", emi)


def brick_dark():
    """Закопчённый кирпич котельной и трубы."""
    w = h = 256
    arr = photo("Bricks105", w, relief=1.1, sat=0.7, gain=0.7, tint=(0.9, 0.62, 0.5))
    soot = np.clip((fbm(w, h, 4, 4, R) - 0.4) * 2.2, 0, 1)
    arr *= (1 - soot[..., None] * 0.55)
    grime(arr, 0.35)
    save("brick_dark", arr)


def ind_window():
    """Заводское окно из мелких стёкол: часть выбита, за некоторыми — отсвет топки."""
    w = h = 128
    arr = fill(h, w, (0.05, 0.06, 0.07))
    emi = np.zeros((h, w, 3), np.float32)
    glow = rgb((1.0, 0.45, 0.15))
    n = 6
    cs = w // n
    for r in range(n):
        for c in range(n):
            y0, x0 = r*cs + 2, c*cs + 2
            k = R.random()
            if k < 0.22:
                col = rgb((0.01, 0.01, 0.012))                       # выбито
            elif k < 0.45:
                g = glow * (0.25 + 0.5 * R.random()) * (0.5 + 0.5 * r / n)
                col = g * 0.6
                emi[y0:y0+cs-3, x0:x0+cs-3] = g
            else:
                col = rgb((0.10, 0.13, 0.16)) * (0.6 + R.random() * 0.8)
            arr[y0:y0+cs-3, x0:x0+cs-3] = col
    frame = rgb((0.16, 0.13, 0.11))
    for k in range(n + 1):
        p = min(k * cs, w - 2)
        arr[p:p+2, :] = frame; arr[:, p:p+2] = frame
        emi[p:p+2, :] = 0; emi[:, p:p+2] = 0
    save("ind_window", arr)
    save("ind_window_emission", emi)


def shopfront():
    """Первый этаж проспекта: тёмные витрины и вывески-заглушки (названия даст автор — см. раздел 4 плана)."""
    cols, cw, h = 8, 64, 96
    w = cols * cw
    arr = tile(photo("Concrete034", 128, relief=0.9, sat=0.4, tint=(0.5, 0.5, 0.52)), w, h)
    emi = np.zeros((h, w, 3), np.float32)
    signs = [rgb((0.1, 0.35, 0.2)), rgb((0.5, 0.08, 0.06)), rgb((0.1, 0.2, 0.45)), rgb((0.45, 0.35, 0.08))]
    for c in range(cols):
        x0 = c * cw
        kind = R.random()
        if kind < 0.2:
            continue                                                 # глухая стена
        sc = signs[R.integers(0, 4)] * (0.6 + R.random() * 0.5)
        arr[6:24, x0+4:x0+60] = sc * (0.8 + fbm(56, 18, 6, 2, R)[..., None] * 0.4)
        if R.random() < 0.3:
            emi[6:24, x0+4:x0+60] = arr[6:24, x0+4:x0+60] * 0.8
        arr[28:88, x0+4:x0+60] = rgb((0.03, 0.04, 0.05))             # витрина
        yy = np.linspace(0, 1, 60, dtype=np.float32)[:, None, None]
        arr[28:88, x0+4:x0+60] += rgb((0.05, 0.07, 0.1)) * (1 - yy) * 0.6
        arr[28:88, x0+31:x0+33] = rgb((0.25, 0.25, 0.26))
        arr[28:30, x0+4:x0+60] = rgb((0.25, 0.25, 0.26)); arr[86:88, x0+4:x0+60] = rgb((0.25, 0.25, 0.26))
        if R.random() < 0.35:                                        # решётка
            for gx in range(x0 + 6, x0 + 60, 6):
                arr[30:86, gx:gx+1] = rgb((0.18, 0.18, 0.18))
    arr[88:] *= 0.6
    grime(arr, 0.2)
    save("shopfront", arr)
    save("shopfront_emission", emi)


panel_facade("facade_b", 0.12, (0.86, 0.9, 0.98))          # холодная серо-голубая, почти всё спит
panel_facade("facade_c", 0.08, (1.0, 0.95, 0.85), rows=8)  # свечка: тёплый бетон, 8 рядов (16 этажей = 2 повтора)
khr_facade()
school_facade()
brick_dark()
ind_window()
shopfront()
print("district textures: ok")
