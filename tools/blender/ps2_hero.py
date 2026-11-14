# Текстуры подъезда / квартиры / гаража, нарисованные под референсы Obscure (docs/references):
# плитка с грязной затиркой, деревянный пол, побелка и масляная краска с разводами, потолок с подтёками.
# Размеры и раскладка (сколько плиток / досок на текстуру) совпадают со старыми — UV моделей не меняются.
# Используется из build_mvp_assets.py (tex_pod_wall, tex_pod_green, tex_simple, tex_misc).
import numpy as np
from ps2_style import (noise, smoothstep, blur, soften, desat, quantize, mottle, water_stains, drips,
                       floor_grime, grout_dirt, footprints, crack, lum)


def C(*c):
    return np.array(c, np.float32)


def _grain(h, w, rng, along_x=True, lines=40, amount=0.18):
    """Волокна дерева / мазки: шум, сильно вытянутый вдоль оси."""
    n = noise(w, h, 3, lines, rng, oct=3) if along_x else noise(w, h, lines, 3, rng, oct=3)
    return 1 + (n - 0.5) * 2 * amount


def finish(arr, soft=1.5, bits=5):
    """Общий «PS2-финиш»: мягкость + 15-битный цвет."""
    return quantize(np.clip(soften(arr, soft), 0, 1), bits)


# ------------------------------------------------------------------ плитка пола (Obscure, школа)
def tile_floor(rng, size=256, n=6, base=(0.63, 0.57, 0.46), grout=(0.36, 0.27, 0.18), prints=False):
    h = w = size
    arr = np.ones((h, w, 3), np.float32) * C(*base)
    cw = w / n
    # у каждой плитки свой тон и лёгкий перекос освещённости
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ti, tj = (yy // cw).astype(int), (xx // cw).astype(int)
    tone = 1 + (rng.random((n, n)).astype(np.float32) - 0.5) * 0.10
    hue = (rng.random((n, n, 3)).astype(np.float32) - 0.5) * 0.025
    arr *= tone[ti, tj][..., None]
    arr += hue[ti, tj]
    lx = ((xx % cw) / cw - 0.5); ly = ((yy % cw) / cw - 0.5)
    arr *= (1 - (lx * 0.05 + ly * 0.07))[..., None]
    # мелкая керамическая фактура + крупные пятна
    arr *= (1 + (noise(w, h, 32, 32, rng, oct=2) - 0.5) * 0.10)[..., None]
    arr *= mottle(h, w, rng, 3, 0.20)[..., None]
    # грязь копится у швов, сам шов — рыже-бурый
    line, halo = grout_dirt(h, w, n, n, width=0.9, spread=2.0)
    dirt_var = noise(w, h, 8, 8, rng, oct=3)
    arr *= (1 - halo * (0.10 + 0.22 * dirt_var))[..., None]
    arr = arr * (1 - line[..., None]) + C(*grout) * (0.7 + 0.6 * dirt_var)[..., None] * line[..., None]
    # разводы от высохшей воды
    inside, ring = water_stains(h, w, rng, 3, cover=0.30, rim=0.22, fill=0.07)
    arr *= (1 - inside[..., None] * C(0.5, 0.7, 1.1))
    arr *= (1 - ring[..., None] * 0.35)
    # грязь: размытые серо-бурые пятна (не лужи)
    grime = smoothstep(0.58, 0.85, noise(w, h, 4, 4, rng, oct=4))
    arr = arr * (1 - grime[..., None] * 0.30) + grime[..., None] * C(0.04, 0.035, 0.02)
    if prints:
        fp = footprints(h, w, rng, 6, alpha=0.28)
        arr *= (1 - fp[..., None])
    return finish(arr, 1.5)        # без трещин: на повторяющейся плитке они читаются как узор


# ------------------------------------------------------------------ деревянный пол (Obscure, коридор)
def wood_floor(rng, w=256, h=256, rows=10, base=(0.27, 0.175, 0.105)):
    arr = np.zeros((h, w, 3), np.float32)
    rh = h / rows
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    row = (yy // rh).astype(int)
    grain = noise(w, h, 2, rows * 6, rng, oct=4)
    knots = smoothstep(0.80, 0.9, noise(w, h, 10, rows * 2, rng, oct=2))
    for r in range(rows):
        y0, y1 = int(round(r * rh)), int(round((r + 1) * rh))
        # стыки досок: длина 0.5..1 ширины, со сдвигом от ряда к ряду
        x = -rng.random() * w * 0.6
        while x < w:
            L = w * (0.45 + rng.random() * 0.5)
            a, b = int(max(0, x)), int(min(w, x + L))
            col = C(*base) * (0.78 + rng.random() * 0.4) * (1 + (rng.random(3).astype(np.float32) - 0.5) * 0.08)
            arr[y0:y1, a:b] = col
            if a > 0:
                arr[y0:y1, a:a + 1] *= 0.35                                     # торцевой стык
            x += L
        arr[y0:y0 + 1] *= 0.30                                                  # щель между досками
        arr[y0 + 1:y0 + 2] *= 0.75
        arr[y1 - 1:y1] *= 1.12                                                  # фаска ловит свет
    arr *= (0.65 + 0.7 * grain)[..., None]                                     # волокна
    arr *= (1 - knots * 0.35)[..., None]
    fib = noise(w, h, 2, rows * 16, rng, oct=2)
    arr *= (1 - smoothstep(0.55, 0.7, fib) * 0.30)[..., None]                  # тёмные прожилки
    arr = desat(arr, 0.82)
    arr *= mottle(h, w, rng, 3, 0.22)[..., None]
    # затёртая середина светлее, тёмные пятна (кровь/грязь — как в Obscure)
    worn = smoothstep(0.5, 0.75, noise(w, h, 2, 2, rng, oct=3))
    arr *= (1 + worn * 0.18)[..., None]
    spill = smoothstep(0.70, 0.78, noise(w, h, 5, 5, rng, oct=4))
    arr = arr * (1 - spill[..., None] * 0.55) + spill[..., None] * C(0.06, 0.02, 0.01)
    return finish(arr, 1.4)


# ------------------------------------------------------------------ штукатурка / краска
def plaster(rng, w, h, color, streak=0.3, stains=0.45, rough=0.08):
    """Мягкая побелка/краска: крупные пятна, разводы с каймой, потёки сверху."""
    arr = np.ones((h, w, 3), np.float32) * C(*color)
    arr *= (1 + (noise(w, h, 24, 24, rng, oct=3) - 0.5) * 2 * rough)[..., None]
    arr *= mottle(h, w, rng, 2, 0.16)[..., None]
    arr *= mottle(h, w, rng, 5, 0.08)[..., None]
    inside, ring = water_stains(h, w, rng, 2, cover=0.35, rim=0.35, fill=0.14)
    arr *= (1 - inside[..., None] * C(0.55, 0.75, 1.15) * stains * 2)
    arr *= (1 - ring[..., None] * stains)
    arr *= (1 - drips(h, w, rng, 1.0, 0.8)[..., None] * streak)
    return arr


def scribble(arr, x, y, n, color, rng, step=5, width=2):
    h, w, _ = arr.shape
    for _ in range(n):
        nx = int(np.clip(x + rng.integers(-step * 3, step * 3 + 1), 1, w - 2))
        ny = int(np.clip(y + rng.integers(-step * 2, step * 2 + 1), 1, h - 2))
        k = max(abs(nx - x), abs(ny - y), 1)
        for i in range(k + 1):
            px = int(x + (nx - x) * i / k); py = int(y + (ny - y) * i / k)
            arr[py:py + width, px:px + 1] = color
        x, y = nx, ny


def pod_wall(rng, draw_text, w=256, h=256):
    """Стена подъезда: побелка сверху, зелёная масляная краска снизу (граница на 44%)."""
    line = int(h * 0.44)
    top = plaster(rng, w, h, (0.64, 0.62, 0.55), streak=0.30, stains=0.35)
    low = plaster(rng, w, h, (0.22, 0.32, 0.28), streak=0.25, stains=0.25, rough=0.06)
    # краска облупилась — под ней серая штукатурка
    chips = smoothstep(0.74, 0.77, noise(w, h, 10, 10, rng, oct=4))
    under = C(0.45, 0.43, 0.38) * (0.85 + 0.3 * noise(w, h, 16, 16, rng))[..., None]
    low = low * (1 - chips[..., None]) + under * chips[..., None]
    arr = top.copy(); arr[line:] = low[line:]
    arr[line - 2:line + 1] *= 0.45                                          # полоса-разделитель
    arr[line + 1:line + 4] *= 1.1
    arr *= (1 - floor_grime(h, w, rng, 0.35, 0.55))[..., None]               # грязь у пола
    soot = smoothstep(0.66, 0.85, noise(w, h, 3, 3, rng, oct=4)) * smoothstep(0.0, 0.4, np.linspace(1, 0, h))[:, None]
    arr *= (1 - soot * 0.35)[..., None]                                       # копоть сверху
    scribble(arr, 60, 150, 14, C(0.06, 0.06, 0.07), rng)
    scribble(arr, 190, 170, 10, C(0.32, 0.06, 0.05), rng)
    draw_text(arr, "ОН ТУТ", 132, 122, 2, C(0.07, 0.07, 0.08))
    return finish(arr, 1.6)


def pod_green(rng, draw_text, w=256, h=256):
    arr = plaster(rng, w, h, (0.22, 0.32, 0.28), streak=0.30, stains=0.3, rough=0.06)
    chips = smoothstep(0.75, 0.78, noise(w, h, 9, 9, rng, oct=4))
    under = C(0.44, 0.42, 0.37) * (0.85 + 0.3 * noise(w, h, 16, 16, rng))[..., None]
    arr = arr * (1 - chips[..., None]) + under * chips[..., None]
    draw_text(arr, "ПАСКОТ", 40, 96, 3, C(0.06, 0.06, 0.07))
    scribble(arr, 180, 60, 16, C(0.52, 0.50, 0.44), rng)
    scribble(arr, 90, 200, 12, C(0.06, 0.06, 0.07), rng)
    return finish(arr, 1.6)


def ceiling(rng, size=128):
    """Потолок: побелка с жёлтыми подтёками и копотью."""
    arr = plaster(rng, size, size, (0.56, 0.54, 0.48), streak=0.0, stains=0.0, rough=0.05)
    for cells, cov in ((2, 0.30), (3, 0.18)):
        inside, ring = water_stains(size, size, rng, cells, cover=cov, rim=0.45, fill=0.20)
        arr *= (1 - inside[..., None] * C(0.35, 0.55, 1.1))
        arr *= (1 - ring[..., None] * 0.55)
    soot = smoothstep(0.6, 0.9, noise(size, size, 2, 2, rng, oct=4))
    arr *= (1 - soot * 0.45)[..., None]
    return finish(arr, 1.6)


def concrete(rng, w, h, color=(0.42, 0.42, 0.40), oil=0.0, stains=0.35, streak=0.0):
    """Мягкий бетон «как в метро»: крупные пятна, редкие поры, разводы."""
    arr = np.ones((h, w, 3), np.float32) * C(*color)
    arr *= (1 + (noise(w, h, 20, 20, rng, oct=3) - 0.5) * 0.16)[..., None]
    pores = rng.random((h, w)).astype(np.float32) > 0.985
    arr[pores] *= 0.75
    arr *= mottle(h, w, rng, 3, 0.22)[..., None]
    inside, ring = water_stains(h, w, rng, 3, cover=0.3, rim=0.3, fill=0.12)
    arr *= (1 - inside[..., None] * stains * 1.5)
    arr *= (1 - ring[..., None] * stains)
    if streak:
        arr *= (1 - drips(h, w, rng, 1.0, 0.8)[..., None] * streak)
    if oil:
        o = smoothstep(0.66, 0.74, noise(w, h, 4, 4, rng, oct=5))
        arr = arr * (1 - o[..., None] * oil) + o[..., None] * oil * C(0.04, 0.035, 0.03)
    return arr


def step(rng, w=128, h=64):
    arr = concrete(rng, w, h, (0.47, 0.46, 0.43), stains=0.25)
    arr[:10] *= 1.22                                                          # стёртая кромка
    arr[-6:] *= 0.55
    arr *= (1 - floor_grime(h, w, rng, 0.4, 0.3))[..., None]
    return finish(arr, 1.4)


def wallpaper(rng, size=128):
    """Советские обои: выцветший узор, подтёки, отклеившиеся стыки."""
    h = w = size
    yy, xx = np.mgrid[0:h, 0:w]
    wp = np.ones((h, w, 3), np.float32) * C(0.55, 0.47, 0.34)
    wp = np.where(((xx % 16) < 2)[..., None], wp * 0.92, wp)
    fl = (((xx % 16) - 9) ** 2 + ((yy % 24) - 12) ** 2) < 10
    wp = np.where(fl[..., None], wp * C(1.12, 0.96, 0.86), wp)
    wp = blur(wp, 0.6)
    wp *= mottle(h, w, rng, 2, 0.18)[..., None]
    inside, ring = water_stains(h, w, rng, 2, cover=0.28, rim=0.35, fill=0.16)
    wp *= (1 - inside[..., None] * C(0.4, 0.6, 1.1))
    wp *= (1 - ring[..., None] * 0.4)
    wp *= (1 - drips(h, w, rng, 0.8, 0.9)[..., None] * 0.25)                 # (обои повторяются по высоте —
    return finish(wp, 1.4)                                                     #  без «грязи у пола», чтобы не было полос)
