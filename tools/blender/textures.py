# Генерация всех текстур двора. Запуск в Blender:
# exec(open(r"...\tools\blender\textures.py", encoding="utf-8").read())
import sys
sys.path.insert(0, r"C:\Users\mrs\Documents\yuranchik_game\tools\blender")
import importlib
import numpy as np
import tex_lib
importlib.reload(tex_lib)
from tex_lib import *

R = np.random.default_rng(1977)


def concrete_base(w, h, rng, tone=(0.56, 0.55, 0.52), grime=0.35):
    n1 = fbm(w, h, 6, 6, rng)
    n2 = fbm(w, h, 32, 32, rng, oct=3)
    pores = rng.random((h, w)).astype(np.float32)
    v = 1.0 + (n1 - 0.5) * 0.25 + (n2 - 0.5) * 0.12 - (pores > 0.93) * 0.12
    arr = fill(h, w, tone) * v[..., None]
    # пятна грязи
    dirt = np.clip((fbm(w, h, 4, 4, rng) - 0.5) * 2.5, 0, 1) * grime
    arr *= (1 - dirt[..., None] * 0.5)
    arr += dirt[..., None] * rgb((0.05, 0.04, 0.0))
    return arr


# ---------- ФАСАД ----------
def facade():
    cols, rows, cell = 8, 9, 64
    w, h = cols * cell, rows * cell
    src = photo("Concrete036", 192, relief=0.9, sat=0.55, gain=1.05)
    arr = np.zeros((h, w, 3), np.float32)
    emi = np.zeros((h, w, 3), np.float32)
    # каждая панель — свой кусок фото бетона и чуть свой тон
    for r in range(rows):
        for c in range(cols):
            oy, ox = R.integers(0, 192 - cell, 2)
            arr[r*cell:(r+1)*cell, c*cell:(c+1)*cell] = src[oy:oy+cell, ox:ox+cell] * (1 + (R.random() - 0.5) * 0.1)
    arr = arr * 0.85 + concrete_base(w, h, R) * 0.15
    # потёки по всему фасаду + сильнее внизу
    st = streaks(w, h, R, 0.5) * fbm(w, h, 6, 4, R)
    grad = np.linspace(0.5, 1.4, h, dtype=np.float32)[:, None]
    arr *= (1 - st[..., None] * 0.22 * grad[..., None])
    # швы с чёрной мастикой (типично для панелек)
    for r in range(rows + 1):
        y = min(r * cell, h - 2)
        arr[y:y+2, :] = arr[y:y+2, :] * 0.25 + rgb((0.03, 0.03, 0.03))
    for c in range(cols + 1):
        x = min(c * cell, w - 2)
        arr[:, x:x+2] = arr[:, x:x+2] * 0.25 + rgb((0.03, 0.03, 0.03))
    # мастика течёт по швам — тёмные кляксы
    blot = (fbm(w, h, 40, 40, R, oct=2) > 0.75)
    seam_mask = np.zeros((h, w), bool)
    for r in range(rows + 1):
        seam_mask[max(0, r*cell-3):r*cell+4, :] = True
    for c in range(cols + 1):
        seam_mask[:, max(0, c*cell-3):c*cell+4] = True
    arr[blot & seam_mask] *= 0.35

    frames = [rgb((0.72, 0.70, 0.64)), rgb((0.34, 0.24, 0.16)), rgb((0.86, 0.86, 0.84)), rgb((0.55, 0.52, 0.45))]
    lights = [rgb((1.0, 0.70, 0.36)), rgb((1.0, 0.82, 0.55)), rgb((0.95, 0.55, 0.28)), rgb((0.45, 0.65, 1.0))]
    curtains = [rgb((0.6, 0.15, 0.1)), rgb((0.75, 0.65, 0.4)), rgb((0.25, 0.4, 0.3)), rgb((0.8, 0.8, 0.75))]
    for r in range(rows):
        for c in range(cols):
            ox, oy = c * cell, r * cell
            x0, x1, y0, y1 = ox + 10, ox + 54, oy + 14, oy + 46
            fr = frames[R.integers(0, 4)] * (0.85 + R.random() * 0.2)
            lit = R.random() < 0.3
            cur = R.random() < 0.65
            curc = curtains[R.integers(0, 4)]
            lc = lights[R.integers(0, 3) if R.random() < 0.9 else 3]
            gh, gw = y1 - y0, x1 - x0
            yy = np.linspace(0, 1, gh, dtype=np.float32)[:, None]
            xx = np.linspace(0, 1, gw, dtype=np.float32)[None, :]
            if lit:
                glass = lc[None, None, :] * (0.65 + 0.35 * yy[..., None])
                if cur:
                    folds = 0.75 + 0.25 * np.sin(xx * 40)[..., None]
                    side = ((xx < 0.28) | (xx > 0.72))[..., None]
                    glass = np.where(side, glass * curc * 1.4 * folds, glass)
                arr[y0:y1, x0:x1] = glass * 0.7
                emi[y0:y1, x0:x1] = glass
            else:
                refl = 0.05 + 0.10 * (1 - yy) * (((xx + yy * 0.6) % 0.35) < 0.12)
                glass = np.ones((gh, gw, 3), np.float32) * refl[..., None] * rgb((0.8, 0.95, 1.3))
                if cur and R.random() < 0.5:
                    glass = glass * 0.4 + curc * 0.12
                arr[y0:y1, x0:x1] = glass
            # рама: контур, вертикальный импост, фрамуга
            arr[y0:y0+3, x0:x1] = fr; arr[y1-3:y1, x0:x1] = fr
            arr[y0:y1, x0:x0+3] = fr; arr[y0:y1, x1-3:x1] = fr
            mx = x0 + gw // 3 if R.random() < 0.5 else x0 + gw // 2
            arr[y0:y1, mx-1:mx+2] = fr
            arr[y0+10:y0+12, x0:mx] = fr
            emi[y0:y0+3, x0:x1] = 0; emi[y1-3:y1, x0:x1] = 0
            emi[y0:y1, x0:x0+3] = 0; emi[y0:y1, x1-3:x1] = 0
            emi[y0:y1, mx-1:mx+2] = 0; emi[y0+10:y0+12, x0:mx] = 0
            # отлив и ржавый потёк под ним
            arr[y1:y1+3, x0-3:x1+3] = rgb((0.30, 0.31, 0.32))
            run = np.clip(np.linspace(1, 0, 14, dtype=np.float32), 0, 1)[:, None, None]
            for k in range(R.integers(1, 4)):
                sx = R.integers(x0, x1 - 3)
                arr[y1+3:y1+17, sx:sx+3] *= (1 - run * 0.45)
                arr[y1+3:y1+17, sx:sx+3] += run * rgb((0.10, 0.04, 0.0))
    save("facade_albedo", arr)
    save("facade_emission", emi)


def wall_side():
    w = h = 256
    arr = tile(photo("Concrete034", 128, relief=1.0, sat=0.5, tint=(0.66, 0.65, 0.62)), w, h)
    arr *= concrete_base(w, h, R, tone=(1, 1, 1), grime=0.5)
    st = streaks(w, h, R, 0.6) * fbm(w, h, 4, 4, R)
    arr *= (1 - st[..., None] * 0.25)
    for k in range(0, 256, 128):
        arr[k:k+2, :] *= 0.3
        arr[:, k:k+2] *= 0.3
    save("wall_side", arr)


def plinth():
    w, h = 256, 64
    arr = tile(photo("Tiles140", 128, relief=0.7, sat=0.4, gain=1.2)[::2, ::2], w, h)
    arr[:12] *= np.linspace(0.5, 1, 12, dtype=np.float32)[:, None, None]
    save("plinth", arr)


def roof():
    w = h = 128
    n = fbm(w, h, 8, 8, R)
    arr = fill(h, w, (0.12, 0.12, 0.13)) * (0.8 + n[..., None] * 0.4)
    save("roof", arr)


def door():
    w, h = 128, 256
    p = photo("PaintedMetal013", w, h, relief=0.9)
    rm = rust_mask("PaintedMetal013", w, h)[..., None]
    arr = p * rgb((0.55, 0.22, 0.15)) * (1 - rm) + p * rm
    arr[8:16, :] *= 0.6; arr[-16:-8, :] *= 0.6
    arr[:, 8:12] *= 0.6; arr[:, -12:-8] *= 0.6
    arr[90:112, 96:112] = rgb((0.15, 0.15, 0.15))
    arr[94:98, 99:109] = rgb((0.5, 0.6, 0.5))
    arr[120:150, 14:20] = rgb((0.4, 0.4, 0.38))
    save("door", arr)


def balcony():
    a = photo("Concrete036", 128, relief=1.0, sat=0.5)
    a *= (1 - (streaks(128, 128, R, 0.8) * fbm(128, 128, 3, 3, R))[..., None] * 0.3)
    a[:6] *= 0.5
    b = photo("Planks023A", 128, relief=0.8, tint=(1.1, 0.95, 0.85))
    for x0 in range(4, 124, 30):
        b[10:70, x0+3:x0+27] = rgb((0.05, 0.06, 0.08)) + (fbm(24, 60, 2, 4, R)[..., None] * 0.08)
    b[70:74] *= 0.5
    save("balcony", np.concatenate([a, b], axis=1))


def snow():
    arr = photo("Snow013", 256, relief=1.0, sat=0.6, tint=(0.95, 0.98, 1.04))
    d = np.clip((fbm(256, 256, 5, 5, R) - 0.62) * 3, 0, 1)
    arr = arr * (1 - d[..., None] * 0.3) + d[..., None] * rgb((0.1, 0.09, 0.07))
    save("snow", arr)


def slush():
    w = h = 256
    s = photo("Snow012", w, relief=0.8, sat=0.7)
    road = photo("Road013A", w, relief=0.8, sat=0.5, gain=1.1)
    s = s * 0.8 + 0.12
    lum = s @ np.array([0.3, 0.6, 0.1], np.float32)
    m = np.clip((lum - 0.3) * 1.5, 0, 1) * 0.85
    xs = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    rut = ((np.abs(xs - 0.3) < 0.08) | (np.abs(xs - 0.7) < 0.08)).astype(np.float32)
    m = m * (1 - rut * 0.8)
    arr = road * (1 - m[..., None]) + s * m[..., None]
    save("slush", arr)


def garage():
    srcs = [("CorrugatedSteel006A", (0.75, 0.8, 0.75)), ("CorrugatedSteel007A", (0.55, 0.65, 0.8)),
            ("CorrugatedSteel007A", (0.75, 0.45, 0.3)), ("Metal021", (1, 1, 1))]
    rust_src = rust_mask("PaintedMetal006", 256)
    rust_col = photo("Metal021", 256, sat=1.3)
    parts = []
    for i, (aid, tint) in enumerate(srcs):
        a = photo(aid, 128, relief=1.4, tint=tint, sat=0.8)
        oy, ox = (i * 37) % 128, (i * 71) % 128
        rm = rust_src[oy:oy+128, ox:ox+128] * 0.9
        rm = np.maximum(rm, (np.linspace(0, 1, 128, dtype=np.float32)[:, None] ** 3) * (fbm(128, 128, 20, 3, R) > 0.5))
        rc = rust_col[oy:oy+128, ox:ox+128] * rgb((1.1, 0.75, 0.5))
        a = a * (1 - rm[..., None]) + rc * rm[..., None]
        a[:, 62:66] *= 0.4
        a[60:66, 52:58] = rgb((0.1, 0.1, 0.1))
        parts.append(a)
    save("garage_doors", np.concatenate(parts, axis=1))
    a = photo("Concrete012", 128, relief=1.0, sat=0.6, gain=0.9)
    a *= (1 - (streaks(128, 128, R, 0.8) * fbm(128, 128, 3, 3, R))[..., None] * 0.3)
    save("garage_wall", a)


def metal():
    save("metal", photo("Metal021", 128, relief=0.8, sat=0.8))


def green_metal():
    save("green_metal", photo("PaintedMetal006", 128, relief=0.8, sat=0.8, gain=0.75))


def bark():
    save("bark", photo("Bark006", 64, 128, relief=1.0, sat=0.25, gain=0.55))


def wood():
    save("wood", photo("Planks023A", 128, 64, relief=0.8))


def kiosk():
    w, h = 256, 256
    body = photo("CorrugatedSteel007A", w, relief=1.0, tint=(0.35, 0.55, 0.9), sat=1.0, gain=0.8)
    rm = rust_mask("PaintedMetal013", w)[..., None] * 0.8
    a = body * (1 - rm) + photo("Metal021", w) * rgb((1.0, 0.7, 0.45)) * rm
    emi = np.zeros_like(a)
    a[0:64] = rgb((0.7, 0.08, 0.06))
    t = "ПРОДУКТЫ"
    sx = (w - text_width(t, 3)) // 2
    draw_text(a, t, sx, 10, 3, rgb((1.0, 0.92, 0.5)))
    t2 = "24 ЧАСА"
    sx2 = (w - text_width(t2, 2)) // 2
    draw_text(a, t2, sx2, 40, 2, rgb((1.0, 1.0, 1.0)))
    a[0:64] *= (0.85 + fbm(w, 64, 8, 2, R)[..., None] * 0.3)
    emi[0:64] = a[0:64] * 0.9
    inner = rgb((1.0, 0.85, 0.55)) * (0.6 + fbm(w, 112, 6, 4, R)[..., None] * 0.5)
    for y in range(20, 112, 28):
        inner[y:y+4] *= 0.3
        for x in range(0, w, 10):
            col = rgb(tuple(R.random(3) * 0.8 + 0.1))
            inner[y-14:y, x+2:x+8] = col
    grate = ((np.arange(w) % 24 < 2)[None, :] | (np.arange(112) % 24 < 2)[:, None])
    inner[grate] = rgb((0.1, 0.1, 0.1))
    a[64:176] = inner * 0.8
    emi[64:176] = inner * 0.7
    emi[64:176][grate] = 0
    save("kiosk", a)
    save("kiosk_emission", emi)


def lamp_glass():
    save("lamp_glass", fill(32, 32, (1.0, 0.75, 0.45)))


facade(); wall_side(); plinth(); roof(); door(); balcony()
snow(); slush(); garage(); metal(); green_metal(); bark(); wood(); kiosk(); lamp_glass()
result = {"ok": True}
