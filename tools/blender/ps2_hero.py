# Текстуры подъезда / квартиры / гаража, нарисованные под референсы (docs/references):
#   Obscure  — бежевая плитка с грязной затиркой, доски, побелка с разводами, потолок с подтёками;
#   Fleshbite — у каждой плитки грязная середина и светлая фаска, облупленная краска с нарисованной тенью,
#               трещины в штукатурке, глубокие тени и насыщенный цвет (бордовое дерево, тёмные обои с узором).
# Размеры и раскладка (сколько плиток / досок на текстуру) совпадают со старыми — UV моделей не меняются.
# Используется из build_mvp_assets.py (tex_pod_wall, tex_pod_green, tex_simple, tex_misc).
import numpy as np
from ps2_style import (noise, smoothstep, blur, soften, desat, quantize, mottle, water_stains, drips,
                       floor_grime, grout_dirt, clarity, crush, peel, cracks)


def C(*c):
    return np.array(c, np.float32)


def finish(arr, soft=1.25, bits=5, crisp=0.45):
    """Общий финиш: PS2-мягкость, хрусткая грязь (Fleshbite), глубокие тени, 15-битный цвет."""
    out = soften(np.clip(arr, 0, 1), soft)
    out = clarity(out, crisp)
    return quantize(crush(np.clip(out, 0, 1), 0.02, 1.08), bits)


def _bevel(h, w, nx, ny, size=3.0):
    """Фаска плитки/панели: светлая кромка сверху-слева, тёмная снизу-справа (свет «запечён»)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cw, ch = w / nx, h / ny
    fx = (xx + 0.5) % cw; fy = (yy + 0.5) % ch
    hi = np.maximum(np.exp(-fx / size), np.exp(-fy / size))
    lo = np.maximum(np.exp(-(cw - fx) / size), np.exp(-(ch - fy) / size))
    return hi, lo


# ------------------------------------------------------------------ плитка пола
def tile_floor(rng, size=256, n=6, base=(0.62, 0.55, 0.44), grout=(0.20, 0.15, 0.10)):
    h = w = size
    arr = np.ones((h, w, 3), np.float32) * C(*base)
    cw = w / n
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ti, tj = (yy // cw).astype(int), (xx // cw).astype(int)
    tone = 1 + (rng.random((n, n)).astype(np.float32) - 0.5) * 0.16
    hue = (rng.random((n, n, 3)).astype(np.float32) - 0.5) * 0.03
    arr *= tone[ti, tj][..., None]
    arr += hue[ti, tj]
    # Fleshbite: в середине каждой плитки — въевшаяся грязь пятнами, края чище
    fx = (xx % cw) / cw - 0.5; fy = (yy % cw) / cw - 0.5
    centre = 1 - np.clip(np.maximum(np.abs(fx), np.abs(fy)) * 2, 0, 1) ** 3
    dirt = smoothstep(0.40, 0.80, noise(w, h, n * 5, n * 5, rng, oct=3))
    arr *= (1 - centre * dirt * 0.20)[..., None]
    arr *= (1 + (noise(w, h, 40, 40, rng, oct=2) - 0.5) * 0.14)[..., None]       # керамика
    arr *= mottle(h, w, rng, 3, 0.20)[..., None]
    # фаска и затирка
    hi, lo = _bevel(h, w, n, n, 2.2)
    arr *= (1 + hi * 0.22 - lo * 0.30)[..., None]
    line, halo = grout_dirt(h, w, n, n, width=0.9, spread=2.0)
    dvar = noise(w, h, 8, 8, rng, oct=3)
    arr *= (1 - halo * (0.10 + 0.20 * dvar))[..., None]
    arr = arr * (1 - line[..., None]) + C(*grout) * (0.7 + 0.6 * dvar)[..., None] * line[..., None]
    # разводы и тёмные пятна
    inside, ring = water_stains(h, w, rng, 3, cover=0.30, rim=0.22, fill=0.07)
    arr *= (1 - inside[..., None] * C(0.5, 0.7, 1.1))
    arr *= (1 - ring[..., None] * 0.35)
    grime = smoothstep(0.58, 0.85, noise(w, h, 4, 4, rng, oct=4))
    arr = arr * (1 - grime[..., None] * 0.35) + grime[..., None] * C(0.04, 0.03, 0.02)
    return finish(arr, 1.25, crisp=0.5)


# ------------------------------------------------------------------ деревянный пол
def wood_floor(rng, w=256, h=256, rows=10, base=(0.27, 0.13, 0.08)):
    """Доски: тёплое красно-коричневое дерево (Fleshbite), стыки вразбежку, тёмные щели (Obscure)."""
    arr = np.zeros((h, w, 3), np.float32)
    rh = h / rows
    grain = noise(w, h, 2, rows * 6, rng, oct=4)
    knots = smoothstep(0.80, 0.9, noise(w, h, 10, rows * 2, rng, oct=2))
    gloss = np.zeros((h, w), np.float32)
    for r in range(rows):
        y0, y1 = int(round(r * rh)), int(round((r + 1) * rh))
        x = -rng.random() * w * 0.6
        while x < w:
            L = w * (0.45 + rng.random() * 0.5)
            a, b = int(max(0, x)), int(min(w, x + L))
            col = C(*base) * (0.75 + rng.random() * 0.45) * (1 + (rng.random(3).astype(np.float32) - 0.5) * 0.10)
            arr[y0:y1, a:b] = col
            if a > 0:
                arr[y0:y1, a:a + 1] *= 0.30                                     # торцевой стык
            x += L
        yy = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None]
        gloss[y0:y1] = np.exp(-((yy - 0.3) / 0.25) ** 2)                       # лак ловит свет посередине доски
        arr[y0:y0 + 1] *= 0.20                                                  # щель между досками
        arr[y0 + 1:y0 + 2] *= 0.70
        arr[y1 - 1:y1] *= 1.15                                                  # фаска
    arr *= (0.62 + 0.76 * grain)[..., None]                                    # волокна
    arr *= (1 - knots * 0.4)[..., None]
    fib = noise(w, h, 2, rows * 16, rng, oct=2)
    arr *= (1 - smoothstep(0.55, 0.7, fib) * 0.35)[..., None]                  # тёмные прожилки
    arr *= (1 + gloss * 0.14 * noise(w, h, 3, 3, rng))[..., None]
    arr *= mottle(h, w, rng, 3, 0.22)[..., None]
    worn = smoothstep(0.5, 0.75, noise(w, h, 2, 2, rng, oct=3))
    arr = arr * (1 + worn[..., None] * C(0.25, 0.18, 0.10))                  # затёртое — светлее и суше
    spill = smoothstep(0.70, 0.78, noise(w, h, 5, 5, rng, oct=4))
    arr = arr * (1 - spill[..., None] * 0.6) + spill[..., None] * C(0.05, 0.015, 0.01)
    arr = desat(arr, 0.78)                                                    # под тёплой лампой не рыжее
    return finish(arr, 1.2, crisp=0.5)


# ------------------------------------------------------------------ штукатурка / краска
def plaster(rng, w, h, color, streak=0.3, stains=0.45, rough=0.08, crack=0.35):
    """Побелка/краска: крупные пятна, разводы с каймой, потёки сверху, сетка трещин (Fleshbite)."""
    arr = np.ones((h, w, 3), np.float32) * C(*color)
    arr *= (1 + (noise(w, h, 24, 24, rng, oct=3) - 0.5) * 2 * rough)[..., None]
    arr *= mottle(h, w, rng, 2, 0.18)[..., None]
    arr *= mottle(h, w, rng, 5, 0.10)[..., None]
    inside, ring = water_stains(h, w, rng, 2, cover=0.35, rim=0.35, fill=0.14)
    arr *= (1 - inside[..., None] * C(0.55, 0.75, 1.15) * stains * 2)
    arr *= (1 - ring[..., None] * stains)
    arr *= (1 - drips(h, w, rng, 1.0, 0.8)[..., None] * streak)
    if crack:
        arr *= (1 - cracks(h, w, rng, 5)[..., None] * crack)
    return arr


def peeled(arr, rng, under, cells=10, cover=0.22):
    """Облупить слой: под ним `under`, у края скола — тень вниз-вправо и светлая кромка (Fleshbite)."""
    h, w, _ = arr.shape
    chip, shade, rim = peel(h, w, rng, cells, cover, 2)
    out = arr * (1 - chip[..., None]) + under * chip[..., None]
    out *= (1 - shade * 0.55)[..., None]
    out *= (1 + rim * 0.25)[..., None]
    return out


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


def _under(rng, w, h):
    return C(0.46, 0.44, 0.39) * (0.85 + 0.3 * noise(w, h, 16, 16, rng))[..., None]


def pod_wall(rng, draw_text, w=256, h=256):
    """Стена подъезда: побелка сверху, зелёная масляная краска снизу (граница на 44%)."""
    line = int(h * 0.44)
    top = plaster(rng, w, h, (0.64, 0.62, 0.55), streak=0.30, stains=0.35, crack=0.2)
    low = plaster(rng, w, h, (0.17, 0.30, 0.26), streak=0.25, stains=0.25, rough=0.06, crack=0.2)
    low = peeled(low, rng, _under(rng, w, h), 16, 0.10)
    top = peeled(top, rng, C(0.50, 0.47, 0.42), 14, 0.04)                        # кое-где отвалилась побелка
    arr = top.copy(); arr[line:] = low[line:]
    arr[line - 2:line + 1] *= 0.40                                            # полоса-разделитель
    arr[line + 1:line + 4] *= 1.12
    arr *= (1 - floor_grime(h, w, rng, 0.35, 0.6))[..., None]                 # грязь у пола
    soot = smoothstep(0.66, 0.85, noise(w, h, 3, 3, rng, oct=4)) * smoothstep(0.0, 0.4, np.linspace(1, 0, h))[:, None]
    arr *= (1 - soot * 0.4)[..., None]                                        # копоть сверху
    scribble(arr, 60, 150, 14, C(0.05, 0.05, 0.06), rng)
    scribble(arr, 190, 170, 10, C(0.38, 0.05, 0.04), rng)
    draw_text(arr, "ОН ТУТ", 132, 122, 2, C(0.06, 0.06, 0.07))
    return finish(arr, 1.3, crisp=0.5)


def pod_green(rng, draw_text, w=256, h=256):
    arr = plaster(rng, w, h, (0.17, 0.30, 0.26), streak=0.30, stains=0.3, rough=0.06, crack=0.2)
    arr = peeled(arr, rng, _under(rng, w, h), 15, 0.10)
    draw_text(arr, "ПАСКОТ", 40, 96, 3, C(0.05, 0.05, 0.06))
    scribble(arr, 180, 60, 16, C(0.55, 0.52, 0.46), rng)
    scribble(arr, 90, 200, 12, C(0.05, 0.05, 0.06), rng)
    return finish(arr, 1.3, crisp=0.5)


def ceiling(rng, size=128):
    """Потолок: побелка с жёлтыми подтёками, копотью и трещинами."""
    arr = plaster(rng, size, size, (0.56, 0.54, 0.48), streak=0.0, stains=0.0, rough=0.05, crack=0.2)
    for cells, cov in ((2, 0.30), (3, 0.18)):
        inside, ring = water_stains(size, size, rng, cells, cover=cov, rim=0.45, fill=0.20)
        arr *= (1 - inside[..., None] * C(0.35, 0.55, 1.1))
        arr *= (1 - ring[..., None] * 0.55)
    soot = smoothstep(0.6, 0.9, noise(size, size, 2, 2, rng, oct=4))
    arr *= (1 - soot * 0.5)[..., None]
    arr = peeled(arr, rng, C(0.44, 0.42, 0.37), 10, 0.04)
    return finish(arr, 1.3)


def concrete(rng, w, h, color=(0.42, 0.42, 0.40), oil=0.0, stains=0.35, streak=0.0):
    """Бетон «как в метро»: крупные пятна, поры, разводы, мелкие трещины."""
    arr = np.ones((h, w, 3), np.float32) * C(*color)
    arr *= (1 + (noise(w, h, 20, 20, rng, oct=3) - 0.5) * 0.20)[..., None]
    pores = rng.random((h, w)).astype(np.float32) > 0.985
    arr[pores] *= 0.7
    arr *= mottle(h, w, rng, 3, 0.24)[..., None]
    inside, ring = water_stains(h, w, rng, 3, cover=0.3, rim=0.3, fill=0.12)
    arr *= (1 - inside[..., None] * stains * 1.5)
    arr *= (1 - ring[..., None] * stains)
    arr *= (1 - cracks(h, w, rng, 4)[..., None] * 0.3)
    if streak:
        arr *= (1 - drips(h, w, rng, 1.0, 0.8)[..., None] * streak)
    if oil:
        o = smoothstep(0.66, 0.74, noise(w, h, 4, 4, rng, oct=5))
        arr = arr * (1 - o[..., None] * oil) + o[..., None] * oil * C(0.03, 0.028, 0.025)
    return arr


def step(rng, w=128, h=64):
    arr = concrete(rng, w, h, (0.47, 0.46, 0.43), stains=0.25)
    arr[:10] *= 1.25                                                          # стёртая кромка
    arr[-6:] *= 0.5
    arr *= (1 - floor_grime(h, w, rng, 0.4, 0.35))[..., None]
    return finish(arr, 1.25)


def wallpaper(rng, size=128):
    """Советские обои с узором (как тёмные обои с орнаментом во Fleshbite): выцветшие, в подтёках,
    потемнели на стыках. Бесшовные по обеим осям (без сколов — на повторе они читаются узором)."""
    h = w = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    bg = C(0.42, 0.30, 0.20)
    orn = C(0.62, 0.50, 0.33)
    # орнамент «дамаск»: ромбическая решётка + цветок в узле (период 32 x 32 — делит 128 без шва)
    u = (xx % 32) / 32 - 0.5; v = (yy % 32) / 32 - 0.5
    u2 = ((xx + 16) % 32) / 32 - 0.5; v2 = ((yy + 16) % 32) / 32 - 0.5
    flower = np.exp(-((np.abs(u) * 3.2) ** 2 + (np.abs(v) * 2.2) ** 2) * 3) * (0.6 + 0.4 * np.cos(np.arctan2(v, u) * 6))
    leaf = np.exp(-((np.abs(u2) * 6) ** 2 + (np.abs(v2) * 3) ** 2) * 3)
    lattice = np.exp(-((np.abs(np.abs(u) + np.abs(v) - 0.5)) / 0.03) ** 2) * 0.6
    m = np.clip(flower * 1.3 + leaf * 0.8 + lattice, 0, 1)
    wp = bg * (1 - m[..., None]) + orn * m[..., None]
    wp = blur(wp, 0.5)
    wp *= (1 + (noise(w, h, 24, 24, rng, oct=2) - 0.5) * 0.10)[..., None]     # бумага
    seam = ((xx % 64) < 1.5).astype(np.float32)                              # стыки полотнищ
    wp *= (1 - seam * 0.35)[..., None]
    wp *= mottle(h, w, rng, 2, 0.20)[..., None]
    inside, ring = water_stains(h, w, rng, 2, cover=0.28, rim=0.35, fill=0.16)
    wp *= (1 - inside[..., None] * C(0.4, 0.6, 1.1))
    wp *= (1 - ring[..., None] * 0.4)
    wp *= (1 - drips(h, w, rng, 0.8, 0.9)[..., None] * 0.3)
    return finish(wp, 1.2, crisp=0.45)
