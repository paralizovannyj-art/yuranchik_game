# PS2-обработка текстур по референсам из docs/references: Obscure, метро, трейлер Fleshbite.
# Что делает текстуру «той самой»:
#   * мягкая, чуть размытая картинка (низкое разрешение + билинейная фильтрация), без мелкого фото-шума;
#   * крупная грязь: пятна, разводы от воды с тёмной каймой, потёки сверху вниз, темнее у пола;
#   * приглушённый цвет с тёплым грязным оттенком, 15-битный цвет (RGB555, как в VRAM PS2).
# Все массивы — float32 [H, W, 3], 0..1, (0,0) = верх-лево (как в tex_lib).
# tex_lib.save() вызывает ps2_pass() сам, по таблице PRESETS ниже: менять вид текстуры — здесь.
import numpy as np


# ------------------------------------------------------------------ шум (свой, чтобы не зависеть от tex_lib)
def _vnoise(w, h, cx, cy, rng):
    g = rng.random((cy, cx)).astype(np.float32)
    x = np.arange(w, dtype=np.float32) * cx / w
    y = np.arange(h, dtype=np.float32) * cy / h
    x0 = np.floor(x).astype(int); fx = x - x0; x1 = (x0 + 1) % cx; x0 %= cx
    y0 = np.floor(y).astype(int); fy = y - y0; y1 = (y0 + 1) % cy; y0 %= cy
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = g[np.ix_(y0, x0)]; b = g[np.ix_(y0, x1)]
    c = g[np.ix_(y1, x0)]; d = g[np.ix_(y1, x1)]
    fx = fx[None, :]; fy = fy[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def noise(w, h, cx, cy, rng, oct=4, gain=0.5):
    """Тайлящийся fbm 0..1 (cx, cy — сколько «клеток» на текстуру по осям)."""
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    for i in range(oct):
        out += _vnoise(w, h, max(1, int(cx * 2 ** i)), max(1, int(cy * 2 ** i)), rng) * amp
        tot += amp; amp *= gain
    return out / tot


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def lum(arr):
    return arr @ np.array([0.299, 0.587, 0.114], np.float32)


# ------------------------------------------------------------------ базовые операции
def blur(arr, sigma, wrap=True):
    """Гауссово размытие (по умолчанию с заворотом краёв — для тайлящихся текстур)."""
    if sigma <= 0:
        return arr
    r = max(1, int(np.ceil(sigma * 2.5)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1, dtype=np.float32) / sigma) ** 2)
    k /= k.sum()
    out = arr.astype(np.float32)
    for axis in (0, 1):
        if wrap:
            acc = np.zeros_like(out)
            for i, kv in enumerate(k):
                acc += np.roll(out, i - r, axis=axis) * kv
        else:
            pad = [(0, 0)] * out.ndim; pad[axis] = (r, r)
            p = np.pad(out, pad, mode="edge")
            n = out.shape[axis]
            acc = sum(np.take(p, np.arange(i, i + n), axis=axis) * kv for i, kv in enumerate(k))
        out = acc
    return out


def soften(arr, amount):
    """«PS2-мягкость»: сжать в 1/amount раз и растянуть обратно билинейно + лёгкое размытие."""
    if amount <= 1:
        return arr
    h, w, _ = arr.shape
    sh, sw = max(4, int(h / amount)), max(4, int(w / amount))
    ys = (np.arange(sh) + 0.5) * h / sh - 0.5
    xs = (np.arange(sw) + 0.5) * w / sw - 0.5
    small = _bilinear(blur(arr, amount * 0.45), ys, xs)
    ys2 = (np.arange(h) + 0.5) * sh / h - 0.5
    xs2 = (np.arange(w) + 0.5) * sw / w - 0.5
    return _bilinear(small, ys2, xs2)


def _bilinear(arr, ys, xs):
    h, w = arr.shape[:2]
    y0 = np.floor(ys).astype(int); fy = (ys - y0).astype(np.float32)
    x0 = np.floor(xs).astype(int); fx = (xs - x0).astype(np.float32)
    y1 = (y0 + 1) % h; x1 = (x0 + 1) % w; y0 %= h; x0 %= w
    fy = fy[:, None, None]; fx = fx[None, :, None]
    a = arr[np.ix_(y0, x0)]; b = arr[np.ix_(y0, x1)]
    c = arr[np.ix_(y1, x0)]; d = arr[np.ix_(y1, x1)]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def desat(arr, s):
    l = lum(arr)[..., None]
    return l + (arr - l) * s


def quantize(arr, bits=5):
    """15-битный цвет (RGB555) — лёгкая «ступенчатость» плавных переходов, как в VRAM PS2."""
    q = (1 << bits) - 1
    return np.round(np.clip(arr, 0, 1) * q) / q


# ------------------------------------------------------------------ грязь
def mottle(h, w, rng, cells=3, amount=0.3):
    """Крупные светлые/тёмные пятна (множитель ~1)."""
    n = noise(w, h, cells, cells, rng, oct=3)
    return 1 + (n - 0.5) * 2 * amount


def water_stains(h, w, rng, cells=3, cover=0.35, rim=0.35, fill=0.12):
    """Разводы от воды: пятно чуть темнее и рыжее, по краю — тёмная кайма («как на потолке»).
    Возвращает (inside 0..1, rim 0..1)."""
    n = noise(w, h, cells, cells, rng, oct=5, gain=0.55)
    t = np.quantile(n, 1 - cover)
    inside = smoothstep(t - 0.01, t + 0.06, n) * fill
    ring = np.exp(-((n - t) / 0.008) ** 2) * rim
    # второе, вложенное кольцо — «высохло несколько раз»
    t2 = t + 0.05
    ring += np.exp(-((n - t2) / 0.006) ** 2) * rim * 0.4
    # кайма неровная: местами пропадает
    ring *= 0.35 + 0.65 * noise(w, h, cells * 6, cells * 6, rng, oct=2)
    return inside, np.clip(blur(ring[..., None], 0.6)[..., 0], 0, 1)


def drips(h, w, rng, density=1.0, length=0.6, strength=1.0):
    """Вертикальные потёки сверху вниз (0..1). Бесшовные: у каждого потёка своё начало по высоте,
    а хвост заворачивается через низ текстуры наверх — при повторе по вертикали шва нет."""
    cols = noise(w, 1, max(2, int(w / 3 * density)), 1, rng, oct=2)[0]
    cols = np.clip((cols - 0.58) * 5.0, 0, 1) * (0.4 + 0.6 * rng.random(w).astype(np.float32))
    cols = blur(cols[None, :, None], 0.8)[0, :, 0]
    group = max(2, int(w / 8))                                         # соседние столбцы — один потёк
    start = (noise(w, 1, group, 1, rng, oct=1)[0] * 3.0 % 1.0) * h
    L = (0.3 + noise(w, 1, group, 1, rng, oct=1)[0]) * length * h
    yy = np.arange(h, dtype=np.float32)[:, None]
    d = (yy - start[None, :]) % h
    fade = np.clip(1 - d / L[None, :], 0, 1) ** 2
    wob = noise(w, h, max(2, int(w / 3)), 24, rng, oct=2)
    wide = noise(w, h, 4, 2, rng, oct=2)                              # мягкое широкое «затекание»
    return np.clip((cols[None, :] * (0.5 + wob) + wide * 0.35) * fade * strength, 0, 1)


def floor_grime(h, w, rng, height=0.25, strength=0.5):
    """Темнее у пола (низ текстуры), с рваной границей."""
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    edge = noise(w, h, max(2, w // 24), 4, rng, oct=3)
    g = smoothstep(1 - height * (0.6 + 0.8 * edge), 1.0, yy)
    return g * strength


def grout_dirt(h, w, nx, ny, width=1.0, rng=None, spread=3.0):
    """Маска затирки сетки плитки nx x ny: 1 на шве, мягко спадает (грязь копится у шва)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cw, ch = w / nx, h / ny
    dx = np.abs(((xx + 0.5) % cw) - 0.5); dx = np.minimum(dx, cw - dx)
    dy = np.abs(((yy + 0.5) % ch) - 0.5); dy = np.minimum(dy, ch - dy)
    d = np.minimum(dx, dy)
    line = (d < width).astype(np.float32)
    halo = np.exp(-d / spread)
    return line, halo


def footprints(h, w, rng, count=6, color=(0.05, 0.045, 0.04), alpha=0.35):
    """Грязные следы ботинок: пары овалов с тёмной подошвой (слой: маска 0..1)."""
    m = np.zeros((h, w), np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x, y = rng.random() * w, rng.random() * h
    ang = rng.random() * np.pi * 2
    sz = min(w, h) / 22
    for i in range(count):
        side = 1 if i % 2 else -1
        px = x + np.cos(ang + np.pi / 2) * side * sz * 0.8
        py = y + np.sin(ang + np.pi / 2) * side * sz * 0.8
        ca, sa = np.cos(ang), np.sin(ang)
        u = ((xx - px) * ca + (yy - py) * sa) / (sz * 1.4)
        v = (-(xx - px) * sa + (yy - py) * ca) / (sz * 0.55)
        sole = (u * u + v * v) < 1
        heel = ((u + 1.7) ** 2 * 2.2 + v * v) < 0.55
        tread = (np.sin(u * 9) > 0.1)
        m = np.maximum(m, ((sole & tread) | heel).astype(np.float32) * (0.5 + 0.5 * rng.random()))
        x += ca * sz * 3.2; y += sa * sz * 3.2
        ang += (rng.random() - 0.5) * 0.25
    return blur(m[..., None], 0.7)[..., 0] * alpha


def crack(h, w, rng, length=None, width=1):
    """Тонкая ломаная трещина (маска 0..1)."""
    m = np.zeros((h, w), np.float32)
    x, y = rng.random() * w, rng.random() * h
    ang = rng.random() * np.pi * 2
    steps = int(length or max(w, h) * 0.6)
    for _ in range(steps):
        ang += (rng.random() - 0.5) * 0.9
        x = (x + np.cos(ang)) % w; y = (y + np.sin(ang)) % h
        m[int(y):int(y) + width, int(x):int(x) + width] = 1
        if rng.random() < 0.01:   # ответвление
            bx, by, ba = x, y, ang + (rng.random() - 0.5) * 2
            for _ in range(int(steps * 0.2)):
                ba += (rng.random() - 0.5) * 0.9
                bx = (bx + np.cos(ba)) % w; by = (by + np.sin(ba)) % h
                m[int(by), int(bx)] = 0.8
    return m



def clarity(arr, amount, radius=3.0):
    """«Хрусткая» грязь как во Fleshbite: усилить местный контраст (средние детали), не трогая общий тон."""
    if amount <= 0:
        return arr
    return arr + (arr - blur(arr, radius)) * amount


def crush(arr, black=0.03, gamma=1.12):
    """Глубже тени: чуть опустить чёрную точку и прижать тёмные полутона."""
    return np.clip((arr - black) / (1 - black), 0, 1) ** gamma


def peel(h, w, rng, cells=10, cover=0.26, shadow=2):
    """Облупившаяся краска/штукатурка как во Fleshbite: маска сколов + нарисованная тень под краем
    и светлая кромка сверху. Возвращает (chip, shade, rim) — всё 0..1."""
    n = noise(w, h, cells, cells, rng, oct=4)
    t = np.quantile(n, 1 - cover)
    chip = smoothstep(t, t + 0.02, n)
    sh = np.roll(np.roll(chip, -shadow, axis=0), -shadow, axis=1)     # край скола отбрасывает тень вниз-вправо
    shade = np.clip(chip - sh, 0, 1)
    rim = np.clip(np.roll(np.roll(chip, shadow, axis=0), shadow, axis=1) - chip, 0, 1)
    return chip, blur(shade[..., None], 0.8)[..., 0], blur(rim[..., None], 0.6)[..., 0]


def cracks(h, w, rng, cells=6, width=0.012):
    """Сетка тонких трещин в штукатурке (линии по «гребням» шума)."""
    n = noise(w, h, cells, cells, rng, oct=3)
    m = np.exp(-((n - 0.5) / width) ** 2)
    m *= smoothstep(0.45, 0.6, noise(w, h, 3, 3, rng, oct=2))           # трещины не везде
    return np.clip(m, 0, 1)


# ------------------------------------------------------------------ общий проход
# Стиль = Obscure (мягкость, разводы, потёки) + метро (зеленоватый бетон, потёки на колоннах)
#       + Fleshbite (хрусткая грязь, глубокие тени, насыщенный цвет).
# soften — во сколько раз «уменьшить разрешение» (1 = не трогать); sat — насыщенность; tint — оттенок;
# contrast — контраст вокруг среднего; clarity — хрусткость грязи; crush — глубина теней;
# mottle/stains/drips/floor — сила грязи.
DEFAULT = dict(soften=1.3, sat=0.88, tint=(1.0, 0.98, 0.93), contrast=1.08, clarity=0.45, crush=True,
               mottle=0.20, mottle_cells=3, stains=0.0, stain_cells=3, drips=0.0, floor=0.0, quant=True)

PRESETS = {
    # стены, фасады, бетон — разводы и потёки
    "wall":    dict(soften=1.35, mottle=0.26, stains=0.75, drips=0.6, clarity=0.55),
    "facade":  dict(soften=1.15, mottle=0.18, stains=0.4, drips=0.3, stain_cells=4, clarity=0.35),
    "floor":   dict(soften=1.3, mottle=0.24, stains=0.5, clarity=0.5),
    "metal":   dict(soften=1.3, sat=0.85, mottle=0.22, stains=0.3, drips=0.35, clarity=0.55),
    "wood":    dict(soften=1.25, sat=0.95, mottle=0.18, stains=0.25, clarity=0.5),
    "snow":    dict(soften=1.6, sat=0.75, tint=(0.98, 0.99, 1.0), contrast=1.0, clarity=0.3, crush=False, mottle=0.10),
    "sign":    dict(soften=1.15, sat=0.92, mottle=0.14, stains=0.2, clarity=0.3),
    "fabric":  dict(soften=1.2, sat=0.92, mottle=0.18, clarity=0.4),
    "atlas":   dict(soften=1.1, sat=0.92, mottle=0.0, contrast=1.05, clarity=0.3),    # атласы мелких деталей
    "decal":   dict(soften=1.1, sat=0.9, mottle=0.12, contrast=1.05, clarity=0.3),     # граффити, объявления (с альфой)
    # персонажи и предметы: без разводов (они легли бы поперёк лица), только хрусткость, тени и лёгкая грязь
    "char":    dict(soften=1.0, sat=0.92, tint=(1.0, 0.98, 0.95), contrast=1.1, clarity=0.6, mottle=0.08, mottle_cells=6),
    "item":    dict(soften=1.0, sat=0.95, contrast=1.08, clarity=0.5, mottle=0.06, mottle_cells=6),
    "hero":    dict(soften=1.0, sat=1.0, tint=(1, 1, 1), contrast=1.0, clarity=0.0, crush=False, mottle=0.0),  # уже нарисованы
}

# какая текстура — какой пресет. Нет в таблице — не трогаем (иконки интерфейса, lamp_glass).
TEXTURES = {
    # двор / дома
    "facade_albedo": "facade", "facade_b_albedo": "facade", "facade_c_albedo": "facade",
    "khr_albedo": "facade", "school_albedo": "facade", "brick_dark": "wall", "wall_side": "wall",
    "plinth": "wall", "roof": "floor", "balcony": "facade", "door": "metal",
    "garage_doors": "metal", "garage_wall": "wall", "metal": "metal", "green_metal": "metal",
    "bark": "wood", "wood": "wood", "kiosk": "sign", "shopfront": "sign", "ind_window": "facade",
    "snow": "snow", "slush": "floor",
    # пропсы и детали
    "vehicles": "atlas", "fence_concrete": "wall", "pipe_insul": "metal", "paint_yellow": "metal",
    "details": "atlas", "graffiti": "decal", "notices": "decal",
    # инфраструктура / подземный переход (метро-референс)
    "retwall": "wall", "paving": "floor", "asphalt_snow": "floor", "pipe_wrap": "metal",
    "stop_wall": "wall", "underpass_sign": "sign",
    # подъезд / квартира / гараж (Obscure + Fleshbite) — рисует ps2_hero
    "pod_wall": "hero", "pod_green": "hero", "pod_ceiling": "hero", "pod_floor": "hero",
    "pod_step": "hero", "garage_in": "wall", "garage_floor": "hero", "parquet": "hero",
    "apt_doors": "sign", "mailboxes": "metal", "pod_window": "atlas", "radiator": "metal",
    "wallpaper": "hero", "carpet": "fabric", "fabric": "fabric", "tv": "atlas",
    # персонажи и предметы
    "yur3_atlas": "char", "sergey": "char", "enemy_a": "char", "enemy_b": "char", "enemy_c": "char",
    "items": "item",
}

# у этих текстур есть «пара»-свечение: его надо размыть так же, чтобы окна совпали
EMISSION_OF = {
    "facade_emission": "facade_albedo", "facade_b_emission": "facade_b_albedo",
    "facade_c_emission": "facade_c_albedo", "khr_emission": "khr_albedo", "school_emission": "school_albedo",
    "ind_window_emission": "ind_window", "kiosk_emission": "kiosk", "shopfront_emission": "shopfront",
    "underpass_sign_emission": "underpass_sign", "pod_window_emission": "pod_window", "tv_emission": "tv",
    "details_emission": "details",
}


def preset_for(name):
    if name in EMISSION_OF:
        base = PRESETS[TEXTURES[EMISSION_OF[name]]]
        return dict(DEFAULT, **base, emission=True)
    if name in TEXTURES:
        return dict(DEFAULT, **PRESETS[TEXTURES[name]])
    return None


def ps2_pass(arr, name, seed=None):
    """PS2-обработка готовой текстуры по её имени (RGB или RGBA — альфа не меняется).
    Неизвестные имена возвращаются как есть."""
    p = preset_for(name)
    if p is None:
        return arr
    alpha = None
    if arr.shape[2] == 4:
        alpha = arr[..., 3:4].copy()
        arr = arr[..., :3]
    h, w, _ = arr.shape
    rng = np.random.default_rng(seed if seed is not None else (sum(map(ord, name)) * 7919))
    out = soften(arr.astype(np.float32), p["soften"])
    if not p.get("emission"):
        out = clarity(out, p["clarity"])
        if p["contrast"] != 1.0:
            m = out.mean(axis=(0, 1), keepdims=True)
            out = m + (out - m) * p["contrast"]
        out = desat(np.clip(out, 0, 1), p["sat"]) * np.array(p["tint"], np.float32)
        if p["mottle"]:
            out *= mottle(h, w, rng, p["mottle_cells"], p["mottle"])[..., None]
        if p["stains"]:
            inside, ring = water_stains(h, w, rng, p["stain_cells"], cover=0.3)
            brown = np.array((0.80, 0.72, 0.58), np.float32)
            out = out * (1 - inside[..., None] * p["stains"]) * (1 - (1 - brown) * inside[..., None] * p["stains"])
            out *= 1 - ring[..., None] * p["stains"]
        if p["drips"]:
            out *= 1 - drips(h, w, rng, 0.8, 0.7)[..., None] * 0.4 * p["drips"]
        if p["floor"]:
            out *= 1 - floor_grime(h, w, rng, 0.3, p["floor"])[..., None]
        if p["crush"]:
            out = crush(np.clip(out, 0, 1))
        if p["quant"]:
            out = quantize(out)
    out = np.clip(out, 0, 1)
    if alpha is not None:
        out = np.concatenate([out, alpha], axis=2)
    return out
