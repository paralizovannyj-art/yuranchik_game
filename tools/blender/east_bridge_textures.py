# Текстуры локации «Восточный ж/д мост» (YUR-7): станция Одесса-Восточная зимой.
# PS2-стиль, как у района: мягкая картинка, запечённые тени и грязь, снег.
# Версия 2: главные текстуры снимаются с маленьких 3D-сцен в Blender (tex_render.py) — щебень из тысяч
# камней, шпалы, сугробы со следами, сухая трава, гофра, окна и рёбра вагонов с настоящим рельефом и тенями.
# Запуск в открытом Blender (через Blender MCP):
#   EB_ROOT = r"<папка проекта>"; exec(open(EB_ROOT + r"\tools\blender\east_bridge_textures.py", encoding="utf-8").read())
#   EB_ONLY = ["eb_ballast", …] — перед exec, чтобы пересобрать только часть.
# Сцены строятся в отдельной сцене EB_TexStudio, рабочие сцены файла не трогаются.
# Все текстуры — с префиксом eb_ в assets/textures/. Таблица PS2-обработки — tools/blender/ps2_style.py (TEXTURES).
import math
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
import tex_render as T
import ps2_style
importlib.reload(ps2_style)
importlib.reload(tex_lib)
importlib.reload(T)
tex_lib.TEX_DIR = os.path.join(ROOT, "assets", "textures")
tex_lib.LIB = os.path.join(ROOT, "assets", "texture_library", "ambientcg")
from tex_lib import fbm, vnoise, streaks, rgb, fill, save, photo, draw_text, text_width, FONT

SNOW = rgb((0.80, 0.83, 0.90))
SNOW_LIN = (0.86, 0.88, 0.92)             # снег в 3D-сценах (sRGB)

# недостающие буквы и цифры для вывесок, номеров вагонов и контейнеров
for _ch, _g in {
    'Х': ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    'І': ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    'З': ["01110", "10001", "00001", "00110", "00001", "10001", "01110"],
    'U': ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    '0': ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    '3': ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    '5': ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    '6': ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    '8': ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    '9': ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
}.items():
    FONT.setdefault(_ch, _g)


def rng_for(name):
    """У каждой текстуры свой генератор: правка одной не меняет остальные."""
    return np.random.default_rng(sum(map(ord, name)) * 7919 + 17)


def save_rgba(name, arr):
    """Как tex_lib.save, но с альфой (решётки, сетка-рабица, трава, деревья). PS2-обработка не трогает альфу."""
    arr = ps2_style.ps2_pass(arr, name)
    h, w, _ = arr.shape
    # временная картинка: картинку из файла сцены (если она ещё не загружена) нельзя перемасштабировать
    img = bpy.data.images.new("_eb_rgba_tmp", w, h, alpha=True)
    img.alpha_mode = 'STRAIGHT'
    img.pixels.foreach_set(np.clip(arr[::-1], 0, 1).astype(np.float32).ravel())
    path = os.path.join(tex_lib.TEX_DIR, name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    old = bpy.data.images.get(name)
    if old is not None and old.source == 'FILE':
        old.reload()
    return path


def snow_tex(w, h, rng):
    return SNOW * (0.82 + fbm(w, h, 20, 20, rng, oct=2)[..., None] * 0.2)


def snow_cover(w, h, rng, amount, cells=5):
    n = fbm(w, h, cells, cells, rng)
    return np.clip((n - (1 - amount)) * 3.5, 0, 1)


# ------------------------------------------------------------------ рисование (numpy)
def disc_stroke(mask, pts, r, soft=0.8):
    """Нарисовать в маске линию из кружков радиуса r (r может быть массивом по точкам)."""
    h, w = mask.shape
    r = np.broadcast_to(np.asarray(r, np.float32), (len(pts),))
    for (x, y), rr in zip(pts, r):
        x0, x1 = int(max(0, x - rr - 2)), int(min(w, x + rr + 3))
        y0, y1 = int(max(0, y - rr - 2)), int(min(h, y + rr + 3))
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot(xx - x, yy - y)
        mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], np.clip((rr - d) / soft + 0.5, 0, 1))


def catmull(pts, n=12):
    """Гладкая кривая через точки (Catmull-Rom)."""
    p = np.asarray(pts, np.float32)
    p = np.concatenate([p[:1], p, p[-1:]])
    out = []
    for i in range(1, len(p) - 2):
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p[i]) + (-p[i - 1] + p[i + 1]) * t + (2 * p[i - 1] - 5 * p[i] + 4 * p[i + 1] - p[i + 2]) * t2
                              + (-p[i - 1] + 3 * p[i] - 3 * p[i + 1] + p[i + 2]) * t3))
    out.append(p[-2])
    return np.array(out)


def spray_tag(arr, rng, x, y, w, h, fill_c, outline=None, width=2.2, letters=4, alpha=0.9, drip=True):
    """Тег баллончиком: несколько «букв» — гладких росчерков, обводка, подтёки краски вниз."""
    H_, W_ = arr.shape[:2]
    m = np.zeros((H_, W_), np.float32)
    lw = w / letters
    for i in range(letters):
        bx = x + i * lw
        k = int(rng.integers(3, 6))
        pts = np.stack([bx + rng.uniform(0, lw * 1.25, k), y + rng.uniform(0, h, k)], 1)
        pts[:, 1] = np.where(np.arange(k) % 2 == 0, y + h * rng.uniform(0.6, 1.0, k), y + h * rng.uniform(0.0, 0.4, k))
        disc_stroke(m, catmull(pts, 14), width * rng.uniform(0.8, 1.2))
    sw = catmull(np.stack([np.linspace(x - lw * 0.2, x + w * 1.05, 4), y + h * 1.08 + rng.normal(0, h * 0.08, 4)], 1), 16)
    disc_stroke(m, sw, width * 0.7)                                                   # подчёркивание
    if drip:
        for _ in range(int(letters * 1.5)):
            px, py = x + rng.uniform(0, w), y + h * rng.uniform(0.5, 1.0)
            L = rng.uniform(3, h * 0.7)
            disc_stroke(m, [(px, py + t) for t in np.arange(0, L, 0.7)], np.linspace(width * 0.45, 0.4, len(np.arange(0, L, 0.7))))
    fog = ps2_style.blur(m[..., None], width * 1.2)[..., 0] * 0.35                   # распыл вокруг
    if outline is not None:
        o = ps2_style.blur(m[..., None], width * 0.6)[..., 0]
        o = np.clip(o * 3.0, 0, 1)
        arr[:] = arr * (1 - o[..., None] * alpha) + rgb(outline) * o[..., None] * alpha
    mm = np.clip(m + fog, 0, 1)[..., None] * alpha
    arr[:] = arr * (1 - mm) + rgb(fill_c) * mm


def poster(arr, rng, x, y, pw, ph, age=0.5):
    """Объявление на клею: бумага, строки текста, рваный край, выцвело."""
    H_, W_ = arr.shape[:2]
    x, y = int(x), int(y)
    x1, y1 = min(W_, x + pw), min(H_, y + ph)
    if x1 <= x or y1 <= y:
        return
    paper = rgb((0.86, 0.84, 0.76)) * rng.uniform(0.75, 1.0)
    reg = arr[y:y1, x:x1]
    tear = (fbm(x1 - x, y1 - y, 3, 3, rng, oct=3) > (0.3 + age * 0.35)).astype(np.float32)
    tear[:max(2, ph // 6)] = 1                                                        # верх приклеен — держится
    p = np.ones(reg.shape, np.float32) * paper
    for ly in range(3, y1 - y - 2, 3):                                                # строки текста
        ln = (rng.random(x1 - x) > 0.35).astype(np.float32) * (np.arange(x1 - x) > 1) * (np.arange(x1 - x) < x1 - x - 2)
        p[ly, :] = p[ly, :] * (1 - ln[:, None] * 0.6)
    if rng.random() < 0.4:
        p[1:3, 1:-1] = rgb((0.65, 0.12, 0.10))                                         # красный заголовок
    a = tear[..., None] * rng.uniform(0.75, 0.95)
    reg[:] = reg * (1 - a) + p * a


def chipped_paint(w, h, rng, c, chip=0.09, rust=(0.36, 0.20, 0.10), under=(0.45, 0.45, 0.43), streak=0.22):
    """Крашеный металл: цвет с выгоранием, сколы до грунта/ржавчины с тенью по краю, ржавые потёки из сколов."""
    arr = rgb(c) * (0.86 + fbm(w, h, 6, 6, rng)[..., None] * 0.24)
    arr *= 1 - (fbm(w, h, 2, 3, rng, oct=2)[..., None] - 0.5) * 0.25                  # выгорание пятнами
    ch, shade, rim = ps2_style.peel(h, w, rng, cells=max(8, w // 10), cover=chip, shadow=1)
    core = np.clip(ps2_style.blur(ch[..., None], 1.2)[..., 0] * 1.4 - 0.4, 0, 1)
    bare = rgb(under) * (1 - core[..., None]) + rgb(rust) * core[..., None]
    arr = arr * (1 - ch[..., None]) + bare * (0.8 + fbm(w, h, 30, 30, rng, oct=2)[..., None] * 0.4) * ch[..., None]
    arr *= 1 - shade[..., None] * 0.45
    arr += rim[..., None] * 0.08
    # ржавчина стекает вниз от сколов
    run = np.zeros((h, w), np.float32)
    src = core.copy()
    for k in range(1, int(h * 0.25)):
        run = np.maximum(run, np.roll(src, k, axis=0) * (1 - k / (h * 0.25)))
    run *= streaks(w, h, rng, 1.6)
    arr = arr * (1 - run[..., None] * 0.5) + rgb(rust) * run[..., None] * 0.5
    st = streaks(w, h, rng, 0.8)[..., None] * streak
    arr = arr * (1 - st) + rgb((0.30, 0.28, 0.26)) * st
    return np.clip(arr, 0, 1)


def resize(arr, w, h):
    """Билинейное изменение размера (numpy)."""
    H_, W_ = arr.shape[:2]
    ys = (np.arange(h) + 0.5) * H_ / h - 0.5
    xs = (np.arange(w) + 0.5) * W_ / w - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, H_ - 1); y1 = np.clip(y0 + 1, 0, H_ - 1); fy = np.clip(ys - y0, 0, 1)[:, None, None]
    x0 = np.clip(np.floor(xs).astype(int), 0, W_ - 1); x1 = np.clip(x0 + 1, 0, W_ - 1); fx = np.clip(xs - x0, 0, 1)[None, :, None]
    a = arr[np.ix_(y0, x0)]; b = arr[np.ix_(y0, x1)]; c = arr[np.ix_(y1, x0)]; d = arr[np.ix_(y1, x1)]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


# ------------------------------------------------------------------ 3D-заготовки для полов
def gravel_bed(sc, rng, W, H, M, density, z0, z1, s0, s1, tint=None, keep=None, snow_top=0.42, name="stones"):
    """Слой щебня: колотые камни, цвет — серый гранит с тёплыми камнями; tint(P, base) — правка цвета по месту."""
    n = int(W * H * density)
    P = np.stack([rng.uniform(0, W, n), rng.uniform(0, H, n), rng.uniform(z0, z1, n)], 1).astype(np.float32)
    if keep is not None:
        P = P[keep(P)]
        n = len(P)
    S = rng.uniform(s0, s1, n).astype(np.float32)
    base = np.array([0.38, 0.37, 0.35], np.float32) * rng.uniform(0.5, 1.15, (n, 1)).astype(np.float32)
    warm = rng.random(n) < 0.18
    base[warm] *= np.array([1.05, 0.9, 0.78], np.float32)
    if tint is not None:
        base = tint(P, base)
    idx, off = T.periodic_copies(P, W, H, M)
    vv, ff, sid = T.stones(rng, P[idx] + off, S[idx])
    mat = T.material("eb_t_stone_%d" % int(snow_top * 100), (1, 1, 1), attr="col", snow_top=snow_top, rough=0.95)
    return T.mesh_object(sc, name, vv, ff, mat, colors=base[idx][sid])


def snow_layer(sc, W, H, M, res, zfun, colfun, name="snow", rough=0.75):
    """Снежный покров: рельеф zfun(X, Y), цвет colfun(X, Y) -> [N, 3] (sRGB)."""
    nx = int(res * (W + 2 * M) / max(W, H))
    ny = int(res * (H + 2 * M) / max(W, H))
    v, f, _ = T.grid(-M, -M, W + M, H + M, nx, ny, zfun)
    mat = T.material("eb_t_snow", (1, 1, 1), attr="col", rough=rough, noise=0.05, noise_scale=6, bump=0.2)
    return T.mesh_object(sc, name, v, f, mat, colors=colfun(v[:, 0], v[:, 1]), smooth=True)


def flat_photo(sc, W, H, M, arr, name, rough=0.85, z=0.0):
    """Плоскость с фото-картинкой, повторяющейся с периодом W × H (бетон, асфальт)."""
    v, f, _ = T.grid(-M, -M, W + M, H + M, 4, 4, lambda X, Y: X * 0 + z)
    uv = np.stack([v[:, 0] / W, v[:, 1] / H], 1)
    return T.mesh_object(sc, name, v, f, T.image_material(name + "_img", arr, rough), uvs=uv)


def trail(rng, x, y, ang, steps, stride=0.36, gait=0.09, wander=0.12):
    """Цепочка следов: [(x, y, угол, размер)] — левый/правый ботинок по очереди."""
    out = []
    s = rng.uniform(0.9, 1.1)
    for i in range(steps):
        side = 1 if i % 2 else -1
        nx_, ny_ = -math.sin(ang), math.cos(ang)
        out.append((x + nx_ * gait * side, y + ny_ * gait * side, ang + rng.normal(0, 0.08), s))
        x += math.cos(ang) * stride
        y += math.sin(ang) * stride
        ang += rng.normal(0, wander)
    return out


def prints_depth(X, Y, W, H, prints, depth=0.03):
    """Вмятины от ботинок в снегу (0..depth), с заворотом через края кадра."""
    d = np.zeros(np.broadcast(X, Y).shape, np.float32)
    for px, py, a, s in prints:
        dx = ((X - px + W / 2) % W) - W / 2
        dy = ((Y - py + H / 2) % H) - H / 2
        ca, sa = math.cos(a), math.sin(a)
        u = (dx * ca + dy * sa) / (0.15 * s)
        v = (-dx * sa + dy * ca) / (0.055 * s)
        r = u * u + v * v
        heel = ((u + 0.72) ** 2 * 6 + v * v)
        tread = 1 - 0.25 * (np.sin(u * 22) > 0.2)
        d = np.maximum(d, (1 - T.smooth01(0.55, 1.0, np.minimum(r, heel))) * tread)
    return d * depth


# ------------------------------------------------------------------ пути
def ballast():
    """Щебень междупутья 4×4 м: колотый гранит, снег сугробами, у краёв сугробов снег грязный."""
    name = "eb_ballast"
    rng = rng_for(name)
    W = H = 4.0
    M = 0.25
    sc = T.studio(W, H, 512, 512, samples=24)
    v, f, _ = T.grid(-M, -M, W + M, H + M, 8, 8, lambda X, Y: X * 0 - 0.035)
    T.mesh_object(sc, "ground", v, f, T.material("eb_t_ground", (0.13, 0.12, 0.11)))
    rust = T.PNoise(W, H, 4, rng, oct=3)

    def tint(P, base):
        r = T.smooth01(0.55, 0.75, rust(P[:, 0], P[:, 1]))[:, None]
        return base * (1 - r * 0.5) + np.array([0.24, 0.15, 0.09], np.float32) * r * 0.5
    gravel_bed(sc, rng, W, H, M, 1000, -0.03, 0.02, 0.03, 0.08, tint)
    mask = T.PNoise(W, H, 7, rng, oct=5)
    det = T.PNoise(W, H, 40, rng, oct=3)
    soot = T.PNoise(W, H, 12, rng, oct=4)

    def z(X, Y):
        m = T.smooth01(0.26, 0.56, mask(X, Y))
        return -0.06 + m * 0.12 + (det(X, Y) - 0.5) * 0.02

    def col(X, Y):
        m = T.smooth01(0.26, 0.75, mask(X, Y))
        d = np.clip((1 - m) * 0.8 + (soot(X, Y) - 0.5) * 0.6, 0, 1)[:, None]
        return np.array(SNOW_LIN, np.float32) * (1 - d) + np.array([0.52, 0.51, 0.50], np.float32) * d
    snow_layer(sc, W, H, M, 520, z, col)
    save(name, T.render(sc, name))


def trackbed():
    """Путь: полоса 3,2 м поперёк (u) × 3,3 м вдоль (v), 6 бетонных шпал по 0,55 м (шпала 2,7 × 0,27 м).
    Между шпалами щебень, снег в шпальных ящиках, скрепления у рельсов (рельсы — отдельная геометрия),
    мазут и ржавчина под рельсами."""
    name = "eb_trackbed"
    rng = rng_for(name)
    W, H = 3.2, 3.3
    M = 0.25
    RAILS = (1.6 - 0.76, 1.6 + 0.76)
    sc = T.studio(W, H, 512, 528, samples=24)
    v, f, _ = T.grid(-M, -M, W + M, H + M, 8, 8, lambda X, Y: X * 0 - 0.08)
    T.mesh_object(sc, "ground", v, f, T.material("eb_t_ground", (0.13, 0.12, 0.11)))

    def oil(P, base):
        d = sum(np.exp(-((P[:, 0] - ur) / 0.16) ** 2) for ur in RAILS)[:, None]
        return base * (1 - d * 0.55) + np.array([0.16, 0.10, 0.06], np.float32) * d * 0.55

    def in_sleeper(P, grow=0.0):
        dv = np.abs((P[:, 1] % 0.55) - 0.275)
        return (dv < 0.135 + grow) & (P[:, 0] > 0.25 - grow) & (P[:, 0] < 2.95 + grow)
    gravel_bed(sc, rng, W, H, M, 1100, -0.07, -0.015, 0.03, 0.075, oil, keep=lambda P: ~in_sleeper(P, -0.03))
    # шпалы: бетон, у каждой свой оттенок, верх чуть уже низа
    parts, cols = [], []
    for k in range(-1, 7):
        vc = 0.275 + k * 0.55
        bv, bf = T.box(0.25, vc - 0.135, -0.14, 2.95, vc + 0.135, -0.005)
        bv[4:, 1] = np.clip(bv[4:, 1], vc - 0.12, vc + 0.12)                          # трапеция в сечении
        parts.append((bv, bf))
        cols.append(np.repeat([np.array([0.55, 0.54, 0.52]) * rng.uniform(0.8, 1.05)], 8, 0))
        for ur in RAILS:                                                                # подкладки и клеммы
            for sx in (-1, 1):
                cv, cf = T.box(ur + sx * 0.05, vc - 0.07, -0.005, ur + sx * 0.12, vc + 0.07, 0.03)
                parts.append((cv, cf))
                cols.append(np.repeat([[0.22, 0.14, 0.09]], 8, 0))
            pv, pf = T.box(ur - 0.09, vc - 0.09, -0.005, ur + 0.09, vc + 0.09, 0.012)
            parts.append((pv, pf))
            cols.append(np.repeat([[0.12, 0.11, 0.10]], 8, 0))
    sv, sf = T.merge(parts)
    T.mesh_object(sc, "sleepers", sv, sf, T.material("eb_t_sleeper", (1, 1, 1), attr="col", noise=0.18, noise_scale=12,
                                                       bump=0.4, snow_top=0.3, rough=0.9), colors=np.concatenate(cols))
    mask = T.PNoise(W, H, 6, rng, oct=5)
    det = T.PNoise(W, H, 40, rng, oct=3)

    def z(X, Y):
        m = T.smooth01(0.3, 0.7, mask(X, Y))
        mid = np.exp(-((X - 1.6) / 0.55) ** 2)                                         # между рельсами снега больше
        return -0.072 + m * 0.075 + mid * 0.02 + (det(X, Y) - 0.5) * 0.015

    def col(X, Y):
        d = sum(np.exp(-((X - ur) / 0.22) ** 2) for ur in RAILS) * 0.7 + (1 - T.smooth01(0.3, 0.8, mask(X, Y))) * 0.4
        d = np.clip(d + (det(X, Y) - 0.5) * 0.3, 0, 1)[:, None]
        return np.array(SNOW_LIN, np.float32) * (1 - d) + np.array([0.42, 0.38, 0.34], np.float32) * d
    snow_layer(sc, W, H, M, 540, z, col)
    save(name, T.render(sc, name))


# ------------------------------------------------------------------ мост и платформы
def white_paint():
    """Перила и столбы моста: белая краска 1×1 м, ржавые сколы и серые потёки."""
    rng = rng_for("eb_white")
    save("eb_white", chipped_paint(256, 256, rng, (0.80, 0.80, 0.76), chip=0.07, under=(0.55, 0.55, 0.52), streak=0.25))


def deck():
    """Настил моста 3×3 м (u — поперёк): бетонные плиты (шов каждые 1,5 м), по краям сугробы,
    посередине натоптанная тропа — серая каша и следы ботинок."""
    name = "eb_deck"
    rng = rng_for(name)
    W = H = 3.0
    M = 0.2
    sc = T.studio(W, H, 512, 512, samples=24)
    slab = photo("Concrete034", 512, relief=0.8, sat=0.3, gain=0.6, tint=(0.9, 0.92, 0.98))
    for p in (0, 256):                                                                  # швы плит
        slab[p:p + 3, :] *= 0.35
        slab[(p + 3) % 512, :] *= 1.15
    flat_photo(sc, W, H, M, slab, "slab", rough=0.6)
    mask = T.PNoise(W, H, 4, rng, oct=5)
    det = T.PNoise(W, H, 30, rng, oct=3)
    wob = T.PNoise(W, H, 2, rng, oct=2)
    prints = []
    for k in range(4):
        prints += trail(rng, 1.5 + rng.normal(0, 0.3), rng.uniform(0, H), math.pi / 2 * (1 if k % 2 else -1) + rng.normal(0, 0.05),
                        int(H / 0.36) + 1, wander=0.05)

    def path(X, Y):
        return np.exp(-((X - 1.5 - (wob(X, Y) - 0.5) * 0.6) / 0.6) ** 2)

    def z(X, Y):
        edge = T.smooth01(0.85, 1.45, np.abs(X - 1.5))
        thick = 0.012 + 0.10 * edge * (0.6 + mask(X, Y) * 0.8) + (mask(X, Y) - 0.5) * 0.04
        thick *= 1 - path(X, Y) * 0.75
        return -0.008 + thick + (det(X, Y) - 0.5) * 0.008 - prints_depth(X, Y, W, H, prints, 0.025)

    def col(X, Y):
        tr = np.clip(path(X, Y) * 0.9 + prints_depth(X, Y, W, H, prints, 8.0), 0, 1)
        tr = np.clip(tr + (det(X, Y) - 0.5) * 0.4, 0, 1)[:, None]
        return np.array(SNOW_LIN, np.float32) * (1 - tr) + np.array([0.50, 0.49, 0.48], np.float32) * tr
    snow_layer(sc, W, H, M, 520, z, col)
    save(name, T.render(sc, name))


def platform():
    """Платформа 4×4 м: старый асфальт с трещинами, утоптанный снег пятнами, цепочки следов."""
    name = "eb_platform"
    rng = rng_for(name)
    W = H = 4.0
    M = 0.2
    sc = T.studio(W, H, 512, 512, samples=24)
    asph = photo("Road013A", 512, relief=0.8, sat=0.3, gain=0.9) * 0.45 + rgb((0.50, 0.50, 0.51)) * 0.55
    flat_photo(sc, W, H, M, asph, "asphalt", rough=0.8)
    mask = T.PNoise(W, H, 5, rng, oct=5)
    det = T.PNoise(W, H, 30, rng, oct=3)
    prints = []
    for _ in range(2):
        prints += trail(rng, rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0, 2 * math.pi), 14, wander=0.2)

    def z(X, Y):
        m = T.smooth01(0.3, 0.55, mask(X, Y))
        return -0.012 + m * 0.045 + (det(X, Y) - 0.5) * 0.01 - prints_depth(X, Y, W, H, prints, 0.02)

    def col(X, Y):
        m = T.smooth01(0.3, 0.7, mask(X, Y))
        d = np.clip((1 - m) * 0.6 + prints_depth(X, Y, W, H, prints, 4.0) + (det(X, Y) - 0.5) * 0.3, 0, 1)[:, None]
        return np.array(SNOW_LIN, np.float32) * (1 - d) + np.array([0.55, 0.55, 0.56], np.float32) * d
    snow_layer(sc, W, H, M, 520, z, col)
    save(name, T.render(sc, name))


def platform_edge():
    """Край платформы 4×1 м: бетонная стенка с белой полосой сверху и потёками."""
    rng = rng_for("eb_platform_edge")
    w, h = 256, 64
    base = photo("Concrete012", w, h, relief=0.9, sat=0.3, gain=0.55, tint=(0.9, 0.92, 0.96))
    base *= 1 - streaks(w, h, rng, 0.8)[..., None] * 0.35
    base[:9] = chipped_paint(w, 9, rng, (0.82, 0.82, 0.78), chip=0.2, under=(0.5, 0.5, 0.48))
    base[9:11] *= 0.5
    base[-8:] = base[-8:] * 0.4 + SNOW * 0.6
    save("eb_platform_edge", base)


# ------------------------------------------------------------------ гофра (рельеф + рисунок)
def trap_wave(x, period, flat=0.3):
    """Трапециевидная гофра 0..1 по координате x (в пикселях)."""
    tri = np.abs(((x / period) % 1.0) - 0.5) * 2
    return np.clip((tri - flat) / (1 - 2 * flat), 0, 1)


def booth():
    """Будка на платформе 2×2 м: голубой профнастил, ржавые потёки, граффити и обрывки объявлений."""
    name = "eb_booth"
    rng = rng_for(name)
    w = h = 256
    W = H = 2.0
    x = np.arange(w, dtype=np.float32)
    hm = np.repeat((trap_wave(x, w / 10) * 0.025)[None, :], h, 0)
    alb = chipped_paint(w, h, rng, (0.50, 0.70, 0.82), chip=0.08, under=(0.55, 0.57, 0.58))
    rust = streaks(w, h, rng, 0.5) * (fbm(w, h, 4, 2, rng) > 0.5)
    alb = alb * (1 - rust[..., None] * 0.5) + rgb((0.32, 0.16, 0.06)) * rust[..., None] * 0.5
    alb[-20:] *= np.linspace(1, 0.55, 20, dtype=np.float32)[:, None, None]             # грязь от снега снизу
    spray_tag(alb, rng, 40, 150, 150, 48, (0.92, 0.92, 0.94), outline=(0.08, 0.08, 0.1), width=3.0, letters=4)
    spray_tag(alb, rng, 70, 70, 80, 30, (0.75, 0.18, 0.2), width=2.0, letters=3, alpha=0.7)
    for _ in range(3):
        poster(alb, rng, rng.integers(10, 200), rng.integers(100, 200), int(rng.integers(20, 34)), int(rng.integers(26, 40)))
    sc = T.studio(W, H, w, h, samples=16)
    T.relief(sc, "booth", hm, W, H, alb, rough=0.6)
    save(name, T.render(sc, name))


def corrugated():
    """Профлист заборов: атлас 3 строки (коричневый, зелёный, серый оцинкованный), вертикальная гофра (12 волн)."""
    name = "eb_corrugated"
    rng = rng_for(name)
    w, h = 256, 192
    W, H = 2.0, 1.5
    rh = h // 3
    x = np.arange(w, dtype=np.float32)
    hm = np.repeat((trap_wave(x, w / 12) * 0.02)[None, :], h, 0)
    alb = np.zeros((h, w, 3), np.float32)
    for k, c in enumerate(((0.40, 0.24, 0.16), (0.22, 0.36, 0.26), (0.55, 0.57, 0.58))):
        if k < 2:
            part = chipped_paint(w, rh, rng, c, chip=0.14, streak=0.3)
        else:                                                                           # оцинковка: «цветы» цинка, белая ржавчина
            part = rgb(c) * (0.88 + vnoise(w, rh, 24, 8, rng)[..., None] * 0.16) * (0.9 + fbm(w, rh, 4, 2, rng)[..., None] * 0.2)
            wr = np.clip((fbm(w, rh, 6, 3, rng) - 0.55) * 4, 0, 1)[..., None]
            part = part * (1 - wr * 0.4) + rgb((0.78, 0.78, 0.74)) * wr * 0.4
            st = streaks(w, rh, rng, 1.0)[..., None] * 0.35
            part = part * (1 - st) + rgb((0.36, 0.22, 0.12)) * st
        part[-8:] *= np.linspace(1, 0.55, 8, dtype=np.float32)[:, None, None]
        alb[k * rh:(k + 1) * rh] = part
    hm[::rh] -= 0.01
    sc = T.studio(W, H, w, h, samples=16)
    T.relief(sc, "corr", hm, W, H, alb, rough=0.6)
    save(name, T.render(sc, name))


def cabinet():
    """Релейные шкафы и трансформаторные будки 1×1 м: серая краска, ржавые края."""
    save("eb_cabinet", chipped_paint(256, 256, rng_for("eb_cabinet"), (0.46, 0.48, 0.48), chip=0.1, streak=0.3))


# ------------------------------------------------------------------ вагоны
def tank():
    """Цистерна: развёртка котла, верхняя половина атласа — жёлтая, нижняя — чёрная (u — вдоль котла,
    v в полосе: верх полосы — верх котла, середина — бок, низ — низ котла).
    Сварные швы, табличка опасного груза на боку, грязь и мазут к низу котла, светлые потёки."""
    rng = rng_for("eb_tank")
    w, h = 512, 512
    hh = h // 2
    arr = np.zeros((h, w, 3), np.float32)
    for k, col in enumerate(((0.72, 0.56, 0.14), (0.10, 0.10, 0.10))):
        part = rgb(col) * (0.85 + fbm(w, hh, 8, 4, rng)[..., None] * 0.3)
        v = np.linspace(0, 1, hh, dtype=np.float32)[:, None, None]
        dirt = np.clip((v - 0.55) * 2.2, 0, 1) * 0.85                                  # грязь у низа котла
        dirt = dirt * (0.7 + fbm(w, hh, 10, 3, rng)[..., None] * 0.6)
        part = part * (1 - dirt) + rgb((0.08, 0.06, 0.05)) * dirt
        drip = ps2_style.drips(hh, w, rng, 1.2, 0.8)[..., None] * (0.35 if k == 0 else 0.15)
        part = part * (1 - drip) + rgb((0.35, 0.30, 0.22)) * drip
        oil = np.clip((fbm(w, hh, 12, 4, rng) - 0.5) * 5, 0, 1)[..., None] * np.clip(v * 2 - 0.2, 0, 1) * 0.5   # мазут под горловиной
        oil *= np.exp(-((np.linspace(0, 1, w)[None, :, None] - 0.5) / 0.12) ** 2)
        part = part * (1 - oil) + rgb((0.03, 0.03, 0.03)) * oil
        for sx in np.linspace(0, w, 6)[1:-1].astype(int):                               # кольцевые швы
            part[:, sx - 1:sx + 1] *= 0.7
            part[:, sx + 1:sx + 2] *= 1.15
        part[hh // 2 - 1:hh // 2 + 1] *= 0.8                                            # продольный шов по боку
        if k == 0:                                                                      # табличка: оранжевая, с номером ООН
            px, py = int(w * 0.22), int(hh * 0.30)
            part[py:py + 40, px:px + 56] = rgb((0.85, 0.42, 0.10))
            part[py + 19:py + 21, px:px + 56] = 0.05
            part[py:py + 40, px:px + 2] = part[py:py + 40, px + 54:px + 56] = 0.05
            part[py:py + 2, px:px + 56] = part[py + 38:py + 40, px:px + 56] = 0.05
            draw_text(part, "33", px + 16, py + 4, 2, rgb((0.05, 0.05, 0.05)))
            draw_text(part, "1203", px + 4, py + 23, 2, rgb((0.05, 0.05, 0.05)))
            draw_text(part, "52863017", int(w * 0.55), int(hh * 0.42), 2, rgb((0.10, 0.10, 0.10)))
        else:
            draw_text(part, "73094152", int(w * 0.55), int(hh * 0.42), 2, rgb((0.75, 0.75, 0.72)))
        part[:6] = part[:6] * 0.5 + SNOW * 0.5                                          # снег на макушке
        arr[k * hh:(k + 1) * hh] = part
    save("eb_tank", arr)


def gondola():
    """Полувагон: борт целиком (u — длина 13,9 м, v — высота 2,1 м), 512×80. Ржавый лист, 13 стоек-«шляп»,
    верхняя обвязка под снегом, нижний пояс, номер и граффити."""
    name = "eb_gondola"
    rng = rng_for(name)
    w, h = 512, 80
    W, H = 13.9, 13.9 * h / w
    alb = photo("Metal021", w, h, relief=0.9, sat=0.8, gain=0.9, tint=(0.95, 0.75, 0.6))
    hm = (fbm(w, h, 12, 3, rng) - 0.5) * 0.03                                           # вмятины листа
    posts = np.linspace(8, w - 8, 13)
    xx = np.arange(w, dtype=np.float32)
    for px in posts:
        d = np.abs(xx - px)
        prof = np.clip((7 - d) / 2.5, 0, 1) * 0.07
        hm = np.maximum(hm, prof[None, :])
        alb[:, (d < 7)] *= 0.85
    hm[:7] = 0.09
    hm[-8:] = np.maximum(hm[-8:], 0.06)
    alb[:7] *= 0.7
    alb[:3] = alb[:3] * 0.3 + SNOW * 0.7
    alb[-8:] *= 0.55
    rust = ps2_style.drips(h, w, rng, 1.0, 0.9)[..., None] * 0.4
    alb = alb * (1 - rust) + rgb((0.30, 0.13, 0.05)) * rust
    gx = int(rng.integers(30, 260))
    spray_tag(alb, rng, gx, 22, 150, 30, (0.85, 0.85, 0.9), outline=(0.12, 0.1, 0.25), width=2.6, letters=5)
    spray_tag(alb, rng, gx + 200, 30, 70, 22, (0.15, 0.55, 0.3), width=2.0, letters=3, alpha=0.75, drip=False)
    draw_text(alb, "60721458", 380, 56, 1, rgb((0.85, 0.85, 0.80)))
    sc = T.studio(W, H, w, h, samples=16, sun_elev=40)
    T.relief(sc, "gondola", hm, W, H, alb, rough=0.7)
    save(name, T.render(sc, name))


def container():
    """Контейнеры 12 м: атлас из 4 строк (красный, синий, охра, серо-зелёный). Гофра, верхняя и нижняя
    обвязка, угловые стойки по краям u, номер на трафарете, ржавые потёки."""
    name = "eb_container"
    rng = rng_for(name)
    w = h = 512
    W = H = 12.0
    rh = h // 4
    cols = ((0.55, 0.13, 0.10), (0.12, 0.22, 0.42), (0.70, 0.52, 0.16), (0.32, 0.38, 0.34))
    codes = ("ТКРU 452197 3", "МСКU 803615 0", "ВСТU 270948 6", "САХU 619052 8")
    x = np.arange(w, dtype=np.float32)
    hm = np.zeros((h, w), np.float32)
    alb = np.zeros((h, w, 3), np.float32)
    for k, c in enumerate(cols):
        y0 = k * rh
        hm[y0:y0 + rh] = (trap_wave(x, 12.8, 0.25) * 0.035)[None, :]
        hm[y0:y0 + 7] = 0.06
        hm[y0 + rh - 9:y0 + rh] = 0.06
        hm[y0:y0 + rh, :6] = 0.08
        hm[y0:y0 + rh, -6:] = 0.08
        hm[y0 + rh - 1] = -0.03
        part = chipped_paint(w, rh, rng, c, chip=0.08, streak=0.35)
        part *= 1 - (np.linspace(0, 1, rh, dtype=np.float32)[:, None, None] < 0.3) * -0.08   # верх выгорел
        rr = ps2_style.drips(rh, w, rng, 1.0, 0.7)[..., None] * 0.35
        part = part * (1 - rr) + rgb((0.30, 0.15, 0.07)) * rr
        part[:7] *= 0.8
        part[-9:] *= 0.6
        part[:3] = part[:3] * 0.35 + SNOW * 0.65
        draw_text(part, codes[k], 16, 14, 1, rgb((0.92, 0.92, 0.88)))
        part[26:46, 18:44] = part[26:46, 18:44] * 0.4 + rgb((0.80, 0.80, 0.76)) * 0.6     # табличка CSC
        alb[y0:y0 + rh] = part
    sc = T.studio(W, H, w, h, samples=16)
    T.relief(sc, "container", hm, W, H, alb, rough=0.6)
    save(name, T.render(sc, name))


def coach():
    """Пассажирский вагон: борт 24 м × 3 м (1024×128), синий с жёлтой полосой, 10 окон в резиновых рамках
    (в двух горит тусклый свет, видны занавески), двери в тамбурах с поручнями, швы обшивки, номер.
    Пара — eb_coach_emission (свет в окнах), считается из того же рисунка — окна совпадают."""
    name = "eb_coach"
    rng = rng_for(name)
    w, h = 1024, 128
    W, H = 24.0, 3.0
    alb = rgb((0.10, 0.20, 0.42)) * (0.85 + fbm(w, h, 16, 3, rng)[..., None] * 0.3)
    hm = np.zeros((h, w), np.float32)
    emi = np.zeros((h, w, 3), np.float32)
    for sx in np.arange(60, w, 58):                                                     # швы обшивки
        hm[:, sx] -= 0.004
        alb[:, sx] *= 0.8
    alb[76:82] = rgb((0.75, 0.62, 0.15)) * (0.9 + fbm(w, 6, 30, 1, rng)[..., None] * 0.2)
    hm[:6] = 0.04
    alb[:6] = rgb((0.35, 0.36, 0.38))
    alb[:2] = alb[:2] * 0.3 + SNOW * 0.7
    hm[112:] = 0.03
    alb[112:] *= 0.45
    lit = {3, 7}
    for i in range(10):
        x0, x1, y0, y1 = 80 + i * 88, 140 + i * 88, 28, 64
        hm[y0 - 3:y1 + 3, x0 - 3:x1 + 3] = 0.012                                         # резиновый уплотнитель
        alb[y0 - 3:y1 + 3, x0 - 3:x1 + 3] = rgb((0.12, 0.12, 0.13))
        hm[y0:y1, x0:x1] = -0.06
        if i in lit:
            g = rgb((0.95, 0.74, 0.44)) * (0.75 + 0.25 * np.linspace(1, 0, y1 - y0, dtype=np.float32)[:, None, None])
            g = np.repeat(g, x1 - x0, 1)
            cur = (np.sin(np.arange(x1 - x0) * 0.9) * 0.5 + 0.5)[None, :, None]           # занавески по краям
            side = ((np.arange(x1 - x0) < 14) | (np.arange(x1 - x0) > x1 - x0 - 15))[None, :, None]
            g = np.where(side, g * (0.55 + cur * 0.25), g)
            alb[y0:y1, x0:x1] = g
            emi[y0:y1, x0:x1] = g
        else:
            g = rgb((0.05, 0.06, 0.08)) * (1 + 0.6 * np.linspace(1, 0, y1 - y0, dtype=np.float32)[:, None, None])
            alb[y0:y1, x0:x1] = g
            alb[y0:y1, x0:x0 + 10] += 0.03
        alb[y0 + 14:y0 + 16, x0:x1] = rgb((0.12, 0.12, 0.13))                           # форточка
        hm[y0 + 14:y0 + 16, x0:x1] = -0.02
        alb[y1 + 3:y1 + 30, x0:x1] *= 1 - streaks(x1 - x0, 27, rng, 1.5)[..., None] * 0.35   # потёки из-под окна
    for x0 in (20, w - 52):                                                              # двери тамбуров
        hm[16:118, x0:x0 + 32] = -0.03
        alb[16:118, x0:x0 + 32] *= 0.8
        alb[16:17, x0:x0 + 32] = alb[117:118, x0:x0 + 32] = rgb((0.06, 0.06, 0.07))
        alb[28:58, x0 + 7:x0 + 25] = rgb((0.05, 0.06, 0.08))
        hm[28:58, x0 + 7:x0 + 25] = -0.07
        for hx in (x0 - 5, x0 + 35):                                                     # поручни
            hm[30:110, hx:hx + 2] = 0.05
            alb[30:110, hx:hx + 2] = rgb((0.65, 0.65, 0.62))
    draw_text(alb, "025-18437", 470, 92, 1, rgb((0.85, 0.80, 0.55)))
    draw_text(alb, "УЗ", 500, 102, 1, rgb((0.85, 0.80, 0.55)))
    grime = np.linspace(0, 1, h, dtype=np.float32)[:, None, None] ** 3 * 0.5            # тормозная пыль к низу
    alb = alb * (1 - grime) + rgb((0.20, 0.14, 0.10)) * grime
    alb *= 1 - ps2_style.drips(h, w, rng, 1.0, 0.6)[..., None] * 0.25
    sc = T.studio(W, H, w, h, samples=16, sun_elev=45)
    T.relief(sc, "coach", hm, W, H, alb, rough=0.5)
    save(name, T.render(sc, name))
    save("eb_coach_emission", emi)


# ------------------------------------------------------------------ контактная сеть, сетка, фонари
def lattice():
    """Решётка ригеля и опор контактной сети: панель 2 м × 1 м, пояса сверху/снизу, раскосы «W». Альфа.
    Уголки «запечены»: светлая кромка сверху-слева, тень снизу-справа."""
    rng = rng_for("eb_lattice")
    w, h = 256, 128
    a = np.zeros((h, w), np.float32)
    a[:9] = 1
    a[-9:] = 1
    a[:, :7] = 1
    a[:, -7:] = 1
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for x0, x1 in ((0, 128), (128, 256)):
        for flip in (False, True):
            xa, xb = (x0, x1) if not flip else (x1, x0)
            d = np.abs((yy - 0) * (xb - xa) - (xx - xa) * (h - 1)) / np.hypot(xb - xa, h - 1)
            a[(d < 4.5) & (xx >= min(x0, x1)) & (xx <= max(x0, x1))] = 1
    col = rgb((0.40, 0.24, 0.16)) * (0.8 + fbm(w, h, 8, 4, rng)[..., None] * 0.4)       # ржаво-коричневая, как на фото
    rust = np.clip((fbm(w, h, 6, 6, rng) - 0.5) * 3, 0, 1)[..., None]
    col = col * (1 - rust * 0.5) + rgb((0.30, 0.15, 0.07)) * rust * 0.5
    lit = np.clip(a - np.roll(np.roll(a, 2, 0), 2, 1), 0, 1)[..., None]                 # кромки
    shd = np.clip(a - np.roll(np.roll(a, -2, 0), -2, 1), 0, 1)[..., None]
    col = col * (1 + lit * 0.35) * (1 - shd * 0.4)
    for bx in range(10, w, 40):                                                         # заклёпки на поясах
        col[3:6, bx:bx + 3] *= 0.6
        col[-6:-3, bx:bx + 3] *= 0.6
    col[:5] = col[:5] * 0.35 + SNOW * 0.65                                              # снег на верхнем поясе
    save_rgba("eb_lattice", np.concatenate([col, a[..., None]], axis=2))


def chainlink():
    """Сетка-рабица ограждения над контактной сетью: тайл 1×1 м, ромбы 16×16 ячеек, проволока с бликом. Альфа."""
    rng = rng_for("eb_mesh")
    w = h = 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    p = 16.0
    d1 = np.abs(((xx + yy) % p) - p / 2)
    d2 = np.abs(((xx - yy) % p) - p / 2)
    e = np.maximum(d1, d2) - (p / 2 - 1.4)
    a = np.clip(e * 1.2 + 0.5, 0, 1)
    shine = np.clip(1 - np.abs(e - 0.4) * 1.5, 0, 1)[..., None]
    col = rgb((0.55, 0.56, 0.55)) * (0.8 + fbm(w, h, 6, 6, rng)[..., None] * 0.3) * (0.8 + shine * 0.4)
    rust = np.clip((fbm(w, h, 5, 5, rng) - 0.55) * 4, 0, 1)[..., None]
    col = col * (1 - rust * 0.6) + rgb((0.35, 0.18, 0.08)) * rust * 0.6
    save_rgba("eb_mesh", np.concatenate([col, a[..., None]], axis=2))


def lamps():
    """Плафоны фонарей: зелёный (ртутная лампа, как на ночных фото станции) и натриевый оранжевый."""
    for name, c in (("eb_lamp_green", (0.55, 1.0, 0.55)), ("eb_lamp_orange", (1.0, 0.62, 0.25))):
        arr = fill(16, 16, c)
        arr[:, :] *= 0.85 + 0.15 * np.linspace(0, 1, 16, dtype=np.float32)[:, None, None]
        save(name, arr)


# ------------------------------------------------------------------ вокзал
def station():
    """Стены павильона «Одеса-Східна» 3×3 м: светлая облупленная штукатурка, под ней серый слой, потёки."""
    rng = rng_for("eb_station")
    w = h = 256
    arr = photo("PaintedPlaster006", w, relief=0.9, sat=0.5, gain=1.15, tint=(1.0, 0.97, 0.88))
    ch, shade, rim = ps2_style.peel(h, w, rng, cells=14, cover=0.05, shadow=1)
    arr = arr * (1 - ch[..., None]) + rgb((0.68, 0.66, 0.62)) * (0.8 + fbm(w, h, 20, 20, rng)[..., None] * 0.3) * ch[..., None]
    arr *= 1 - shade[..., None] * 0.4
    arr *= 1 - ps2_style.drips(h, w, rng, 0.7, 0.5)[..., None] * 0.25
    save("eb_station", arr)


def station_sign():
    """Вывеска на фронтоне: синие буквы на белом, ржавый край, потёки."""
    rng = rng_for("eb_sign_station")
    txt = "ОДЕСА-СХІДНА"
    sc = 3
    w, h = 256, 32
    arr = fill(h, w, (0.86, 0.86, 0.82)) * (0.9 + fbm(w, h, 12, 2, rng)[..., None] * 0.15)
    x = (w - text_width(txt, sc)) // 2
    draw_text(arr, txt, x, (h - 7 * sc) // 2, sc, rgb((0.10, 0.25, 0.65)))
    arr[:2] *= 0.6
    arr[-2:] *= 0.6
    arr *= 1 - streaks(w, h, rng, 1.0)[..., None] * 0.2
    save("eb_sign_station", arr)


# ------------------------------------------------------------------ краска, листы ограждения
def paints():
    save("eb_blue_paint", chipped_paint(256, 256, rng_for("eb_blue_paint"), (0.20, 0.42, 0.70)))     # ограда городской платформы
    save("eb_green_paint", chipped_paint(256, 256, rng_for("eb_green_paint"), (0.26, 0.42, 0.30)))   # ограда со стороны поля
    rng = rng_for("eb_concrete_pole")
    pole = photo("Concrete036", 256, relief=0.9, sat=0.3, gain=0.85, tint=(1.0, 0.98, 0.95)) * 0.6 + rgb((0.62, 0.62, 0.60)) * 0.4
    pole *= 1 - ps2_style.drips(256, 256, rng, 0.9, 0.7)[..., None] * 0.3
    save("eb_concrete_pole", pole)


def sheet():
    """Сплошной лист ограждения моста над контактной сетью: 4×1 м, бело-голубая краска, стыки, граффити."""
    rng = rng_for("eb_sheet")
    w, h = 512, 128
    arr = chipped_paint(w, h, rng, (0.50, 0.56, 0.60), chip=0.1, streak=0.3)
    for x in np.linspace(0, w, 9).astype(int)[:-1]:                                    # стыки листов с болтами
        arr[:, x:x + 2] *= 0.55
        arr[:, x + 2:x + 3] *= 1.15
        for by in (12, 64, 116):
            arr[by:by + 3, x + 4:x + 7] = rgb((0.30, 0.18, 0.10))
    spray_tag(arr, rng, 30, 40, 170, 50, (0.15, 0.25, 0.65), outline=(0.9, 0.9, 0.92), width=3.2, letters=5)
    spray_tag(arr, rng, 260, 50, 90, 36, (0.08, 0.08, 0.08), width=2.2, letters=3, alpha=0.85)
    spray_tag(arr, rng, 380, 34, 110, 44, (0.55, 0.15, 0.20), outline=(0.05, 0.05, 0.05), width=2.8, letters=4)
    save("eb_sheet", arr)


# ------------------------------------------------------------------ поле, дороги, лёд
def field():
    """Поле 8×8 м: тонкий снег, сквозь него торчат пучки сухой полегшей травы, тёмная земля в проталинах."""
    name = "eb_field"
    rng = rng_for(name)
    W = H = 8.0
    M = 0.4
    sc = T.studio(W, H, 512, 512, samples=24)
    en = T.PNoise(W, H, 10, rng, oct=4)
    v, f, _ = T.grid(-M, -M, W + M, H + M, 120, 120, lambda X, Y: (en(X, Y) - 0.5) * 0.06)
    ec = (np.array([0.22, 0.18, 0.13], np.float32) * (0.6 + en(v[:, 0], v[:, 1])[:, None] * 0.8))
    T.mesh_object(sc, "earth", v, f, T.material("eb_t_earth", (1, 1, 1), attr="col", rough=0.95), colors=ec)
    # пучки травы: полегшие стебли-треугольники
    dens = T.PNoise(W, H, 6, rng, oct=3)
    n = 9000
    C = np.stack([rng.uniform(0, W, n), rng.uniform(0, H, n)], 1).astype(np.float32)
    C = C[rng.random(n) < T.smooth01(0.35, 0.65, dens(C[:, 0], C[:, 1]))]
    idx, off = T.periodic_copies(np.c_[C, np.zeros(len(C))], W, H, M)
    C = (C[idx] + off[:, :2]).astype(np.float32)
    k = 9
    nb = len(C) * k
    base = np.repeat(C, k, 0) + rng.normal(0, 0.03, (nb, 2)).astype(np.float32)
    az = np.repeat(rng.uniform(0, 2 * np.pi, len(C)), k) + rng.normal(0, 0.6, nb)
    tilt = rng.uniform(0.6, 1.35, nb)
    L = rng.uniform(0.15, 0.45, nb)
    dirv = np.stack([np.cos(az) * np.sin(tilt), np.sin(az) * np.sin(tilt), np.cos(tilt)], 1) * L[:, None]
    side = np.stack([-np.sin(az), np.cos(az), np.zeros(nb)], 1) * 0.008
    b3 = np.c_[base, np.zeros(nb)]
    V = np.stack([b3 - side, b3 + side, b3 + dirv], 1).reshape(-1, 3).astype(np.float32)
    F = np.arange(nb * 3).reshape(nb, 3)
    bc = np.array([0.60, 0.50, 0.32], np.float32) * rng.uniform(0.55, 1.15, (nb, 1)).astype(np.float32)
    bc[rng.random(nb) < 0.3] *= np.array([0.8, 0.75, 0.7], np.float32)
    cols = np.repeat(bc, 3, 0)
    cols[0::3] *= 0.5
    cols[1::3] *= 0.5
    T.mesh_object(sc, "grass", V, F, T.material("eb_t_blade", (1, 1, 1), attr="col", rough=0.9), colors=cols)
    mask = T.PNoise(W, H, 6, rng, oct=5)
    det = T.PNoise(W, H, 30, rng, oct=3)

    def z(X, Y):
        m = T.smooth01(0.28, 0.6, mask(X, Y))
        return -0.03 + m * 0.11 + (det(X, Y) - 0.5) * 0.02

    def col(X, Y):
        d = np.clip((1 - T.smooth01(0.28, 0.7, mask(X, Y))) * 0.3 + (det(X, Y) - 0.5) * 0.2, 0, 1)[:, None]
        return np.array(SNOW_LIN, np.float32) * (1 - d) + np.array([0.62, 0.60, 0.58], np.float32) * d
    snow_layer(sc, W, H, M, 520, z, col)
    save(name, T.render(sc, name))


def road():
    """Грунтовка по полю: тайл 4 м поперёк × 8 м вдоль (u — поперёк), 256×512. Две колеи до грязи
    с замёрзшими лужами, рисунок протектора в каше, бровки грязного снега, снег между колеями и по краям."""
    name = "eb_road"
    rng = rng_for(name)
    W, H = 4.0, 8.0
    M = 0.3
    sc = T.studio(W, H, 256, 512, samples=24)
    mn = T.PNoise(W, H, 12, rng, oct=4)
    v, f, _ = T.grid(-M, -M, W + M, H + M, 60, 120, lambda X, Y: (mn(X, Y) - 0.5) * 0.02)
    mc = np.array([0.22, 0.18, 0.13], np.float32) * (0.6 + mn(v[:, 0], v[:, 1])[:, None] * 0.8)
    T.mesh_object(sc, "mud", v, f, T.material("eb_t_mud", (1, 1, 1), attr="col", rough=0.6), colors=mc)
    pud = T.PNoise(W, H, 5, rng, oct=4)
    wob = T.PNoise(W, H, 2, rng, oct=2)
    RUTS = (1.12, 2.88)

    def rut_d(X, Y):
        sh = (wob(X, Y) - 0.5) * 0.25
        return np.minimum(np.abs(X - RUTS[0] - sh), np.abs(X - RUTS[1] - sh))
    v, f, _ = T.grid(-M, -M, W + M, H + M, 60, 120, lambda X, Y: X * 0 + 0.006)
    keep = (pud(v[:, 0], v[:, 1]) < 0.45)
    pv = v.copy()
    pv[~keep, 2] = -0.05
    T.mesh_object(sc, "ice", pv, f, T.material("eb_t_puddle", (0.30, 0.32, 0.33), rough=0.25))
    det = T.PNoise(W, H, 30, rng, oct=3)
    mask = T.PNoise(W, H, 4, rng, oct=4)

    def z(X, Y):
        d = rut_d(X, Y)
        rut = 1 - T.smooth01(0.13, 0.28, d)
        berm = np.exp(-((d - 0.33) / 0.07) ** 2) * 0.03
        tread = (np.sin(Y * 2 * np.pi / 0.12 + X * 8) > 0.3) * 0.008 * rut
        side = T.smooth01(1.55, 2.0, np.abs(X - 2.0)) * 0.06
        base = 0.05 + (mask(X, Y) - 0.5) * 0.04 + side
        return base * (1 - rut) - 0.015 * rut + tread + berm + (det(X, Y) - 0.5) * 0.01

    def col(X, Y):
        d = rut_d(X, Y)
        dirt = np.exp(-((d - 0.28) / 0.2) ** 2) * 0.8 + (1 - T.smooth01(0.08, 0.3, d)) * 0.5
        dirt = np.clip(dirt + (det(X, Y) - 0.5) * 0.5, 0, 1)[:, None]
        return np.array(SNOW_LIN, np.float32) * (1 - dirt) + np.array([0.40, 0.36, 0.31], np.float32) * dirt
    snow_layer(sc, W, H, M, 520, z, col)
    save(name, T.render(sc, name))


def ice():
    """Замёрзший пруд 6×6 м: серо-голубой лёд с пузырьками и трещинами, снег пятнами."""
    rng = rng_for("eb_ice")
    w = h = 256
    arr = rgb((0.42, 0.48, 0.52)) * (0.8 + fbm(w, h, 6, 6, rng)[..., None] * 0.35)
    deep = np.clip((fbm(w, h, 3, 3, rng) - 0.5) * 3, 0, 1)[..., None]
    arr = arr * (1 - deep * 0.35) + rgb((0.18, 0.24, 0.28)) * deep * 0.35
    cr = np.zeros((h, w), np.float32)
    for _ in range(5):
        cr = np.maximum(cr, ps2_style.crack(h, w, rng, length=w * 0.8))
    cr = ps2_style.blur(cr[..., None], 0.6)[..., 0]
    arr = arr * (1 - cr[..., None] * 0.5) + rgb((0.85, 0.9, 0.95)) * cr[..., None] * 0.5
    bub = (vnoise(w, h, 90, 90, rng) > 0.8).astype(np.float32)[..., None] * deep
    arr = arr + bub * 0.12
    m = snow_cover(w, h, rng, 0.45, cells=4)[..., None]
    arr = arr * (1 - m) + snow_tex(w, h, rng) * m
    save("eb_ice", arr)


# ------------------------------------------------------------------ трава и деревья (альфа, вид сбоку)
def grass_clump():
    """Пучок сухой травы/бурьяна над снегом: 1×1 м, 256×256, изогнутые стебли и метёлки. Альфа."""
    name = "eb_grass"
    rng = rng_for(name)
    W = H = 1.0
    sc = T.studio(W, H, 256, 256, samples=24, sun_elev=55, transparent=True)
    parts, cols = [], []
    for _ in range(70):
        x0 = rng.uniform(0.12, 0.88)
        top = rng.uniform(0.3, 0.95)
        lean = rng.normal(0, 0.22)
        bend = rng.normal(0, 0.15)
        seg = 8
        t = np.linspace(0, 1, seg + 1, dtype=np.float32)
        xs = x0 + lean * t * top + bend * t ** 2 * top
        ys = t * top
        wd = 0.006 * (1 - t * 0.8) + 0.002
        nx_ = np.gradient(ys)
        ny_ = -np.gradient(xs)
        nn = np.hypot(nx_, ny_) + 1e-6
        L = np.stack([xs - nx_ / nn * wd, ys - ny_ / nn * wd, t * 0.01], 1)
        R_ = np.stack([xs + nx_ / nn * wd, ys + ny_ / nn * wd, t * 0.01], 1)
        V = np.concatenate([L, R_]).astype(np.float32)
        F = np.array([[i, i + 1, seg + 2 + i, seg + 1 + i] for i in range(seg)])
        parts.append((V, F))
        c = np.array([0.58, 0.47, 0.29], np.float32) * rng.uniform(0.55, 1.15)
        cols.append(np.concatenate([c * (0.45 + 0.55 * t[:, None])] * 2))
        if rng.random() < 0.3:                                                          # метёлка на верхушке
            for _ in range(int(rng.integers(5, 10))):
                a = rng.uniform(-0.9, 0.9) + np.pi / 2
                l = rng.uniform(0.02, 0.06)
                px, py = xs[-1], ys[-1]
                bv = np.array([[px - 0.003, py, 0.02], [px + 0.003, py, 0.02],
                               [px + math.cos(a) * l, py + math.sin(a) * l, 0.02]], np.float32)
                parts.append((bv, np.array([[0, 1, 2]])))
                cols.append(np.repeat([[0.45, 0.36, 0.22]], 3, 0))
    sv, sf = T.merge([(v, f) for v, f in parts if f.shape[1] == 4])
    sc_ = np.concatenate([c for (v, f), c in zip(parts, cols) if f.shape[1] == 4])
    T.mesh_object(sc, "blades", sv, sf, T.material("eb_t_blade", (1, 1, 1), attr="col", rough=0.9), colors=sc_)
    tv, tf = T.merge([(v, f) for v, f in parts if f.shape[1] == 3])
    tc = np.concatenate([c for (v, f), c in zip(parts, cols) if f.shape[1] == 3])
    T.mesh_object(sc, "heads", tv, tf, T.material("eb_t_blade", (1, 1, 1), attr="col", rough=0.9), colors=tc)
    save_rgba(name, T.render(sc, name))


def _tree_mesh(rng, x, y, ang, length, radius, depth, spread, shrink, kids, up_bias=0.0):
    """Ветки — конусные трубки (6 граней) в плоскости XY (Y — вверх), слегка изогнутые."""
    parts = []

    def branch(x, y, z, ang, length, radius, depth):
        seg = max(2, int(length / 0.25))
        pts, rr = [], []
        a = ang
        px, py = x, y
        for i in range(seg + 1):
            t = i / seg
            pts.append((px, py))
            rr.append(radius * (1 - t * 0.6))
            a += rng.normal(0, 0.06) + (0 - a) * up_bias * 0.1
            px += math.sin(a) * length / seg
            py += math.cos(a) * length / seg
        pts = np.array(pts, np.float32)
        ring = 6
        V, F = [], []
        for i, ((cx, cy), r) in enumerate(zip(pts, rr)):
            dx, dy = (pts[min(i + 1, seg)] - pts[max(i - 1, 0)])
            n = math.hypot(dx, dy) + 1e-6
            nx_, ny_ = dy / n, -dx / n
            for k in range(ring):
                th = 2 * math.pi * k / ring
                V.append((cx + nx_ * r * math.cos(th), cy + ny_ * r * math.cos(th), z + r * math.sin(th)))
        for i in range(seg):
            for k in range(ring):
                a0, a1 = i * ring + k, i * ring + (k + 1) % ring
                F.append((a0, a1, a1 + ring, a0 + ring))
        parts.append((np.array(V, np.float32), np.array(F, np.int32)))
        if depth > 0:
            for _ in range(kids if depth > 1 else kids + 1):
                t = rng.uniform(0.35, 1.0)
                i = min(seg, int(t * seg))
                bx, by = pts[i]
                sgn = 1 if rng.random() < 0.5 else -1
                branch(float(bx), float(by), z + rng.normal(0, 0.1), a * (1 - up_bias) + sgn * rng.uniform(*spread),
                       length * rng.uniform(*shrink), max(0.02, rr[i] * 0.65), depth - 1)
    branch(x, y, 0.0, ang, length, radius, depth)
    return T.merge(parts)


def trees():
    """Голые деревья для билбордов: eb_tree — раскидистое (орех, акация), 256×256;
    eb_poplar — пирамидальный тополь, 128×256. Объёмные ветки, снег на верхней стороне. Альфа."""
    bark = T.material("eb_t_bark", (0.17, 0.15, 0.13), rough=0.95, noise=0.2, noise_scale=6,
                      snow_top=0.55, snow_axis="Y")
    rng = rng_for("eb_tree")
    W = H = 10.0
    sc = T.studio(W, H, 256, 256, samples=24, sun_elev=60, transparent=True)
    v, f = _tree_mesh(rng, 5.0, 0.0, rng.normal(0, 0.05), 3.4, 0.22, 1, (0.1, 0.25), (0.9, 1.0), 2)
    parts = [(v, f)]
    for i in range(7):
        a = (i - 3) * 0.32 + rng.normal(0, 0.12)                                       # ветви веером
        v2, f2 = _tree_mesh(rng, 5.0 + rng.normal(0, 0.1), 3.0 + rng.uniform(0, 0.5), a, rng.uniform(2.6, 3.4), 0.14, 4,
                            (0.25, 0.65), (0.6, 0.78), 3)
        parts.append((v2, f2))
    v, f = T.merge(parts)
    T.mesh_object(sc, "tree", v, f, bark)
    save_rgba("eb_tree", T.render(sc, "eb_tree"))

    rng = rng_for("eb_poplar")
    W, H = 5.0, 10.0
    sc = T.studio(W, H, 128, 256, samples=24, sun_elev=60, transparent=True)
    parts = [_tree_mesh(rng, 2.5, 0.0, 0.0, 9.3, 0.18, 0, (0, 0), (1, 1), 0)]
    for _ in range(70):
        y0 = rng.uniform(1.0, 8.8)
        sgn = 1 if rng.random() < 0.5 else -1
        parts.append(_tree_mesh(rng, 2.5 + rng.normal(0, 0.05), y0, sgn * rng.uniform(0.12, 0.35),
                                rng.uniform(0.8, 2.3) * (0.4 + 0.6 * (1 - abs(y0 - 4.5) / 6)), 0.05, 2,
                                (0.05, 0.25), (0.4, 0.6), 2, up_bias=0.6))
    v, f = T.merge(parts)
    T.mesh_object(sc, "poplar", v, f, bark)
    save_rgba("eb_poplar", T.render(sc, "eb_poplar"))


# ------------------------------------------------------------------ частный сектор
HOUSE_COLS = ((0.84, 0.82, 0.77), (0.80, 0.72, 0.52), (0.55, 0.32, 0.24), (0.58, 0.68, 0.73))


def house():
    """Стены домиков в селе: атлас 4 цвета (столбцы) × 2 строки (окно тёмное / окно горит), 512×192.
    Клетка 128×96 — кусок стены 4,5 × 3 м с одним окном: штукатурка (местами отвалилась), белая рама
    с форточкой, жестяной отлив, цоколь. Пара — eb_house_emission (свет в нижней строке)."""
    name = "eb_house"
    rng = rng_for(name)
    cw, ch = 128, 96
    w, h = cw * 4, ch * 2
    W, H = 18.0, 6.0
    alb = np.zeros((h, w, 3), np.float32)
    hm = np.zeros((h, w), np.float32)
    emi = np.zeros((h, w, 3), np.float32)
    plaster = photo("PaintedPlaster006", cw, ch, relief=0.8, sat=0.0, gain=1.0)
    wx0, wx1, wy0, wy1 = 44, 84, 24, 64
    for k, c in enumerate(HOUSE_COLS):
        for row in range(2):
            y0, x0 = row * ch, k * cw
            cell = rgb(c) * (0.7 + plaster * 0.4) * (0.88 + fbm(cw, ch, 4, 3, rng)[..., None] * 0.2)
            chp, shade, _ = ps2_style.peel(ch, cw, rng, cells=6, cover=0.08, shadow=1)
            cell = cell * (1 - chp[..., None]) + rgb((0.50, 0.47, 0.43)) * chp[..., None]
            cell *= 1 - shade[..., None] * 0.4
            cell *= 1 - streaks(cw, ch, rng, 0.6)[..., None] * 0.2
            hc = np.zeros((ch, cw), np.float32) - chp * 0.01
            cell[-16:] = rgb((0.42, 0.41, 0.40)) * (0.8 + fbm(cw, 16, 10, 2, rng)[..., None] * 0.3)   # цоколь
            hc[-16:] = 0.04
            cell[-17] *= 0.6
            cell[-4:] = cell[-4:] * 0.4 + SNOW * 0.6
            cell[wy0 - 4:wy1 + 4, wx0 - 4:wx1 + 4] = rgb((0.86, 0.86, 0.83))                       # белая рама
            hc[wy0 - 4:wy1 + 4, wx0 - 4:wx1 + 4] = 0.02
            if row == 0:
                glass = rgb((0.05, 0.06, 0.08)) * (1 + 0.8 * np.linspace(1, 0, wy1 - wy0, dtype=np.float32)[:, None, None])
                glass = np.repeat(glass, wx1 - wx0, 1)
                glass[:, :8] += 0.04                                                               # тюль в темноте
            else:
                glass = rgb((0.95, 0.72, 0.40)) * (0.7 + 0.3 * np.linspace(1, 0, wy1 - wy0, dtype=np.float32)[:, None, None])
                glass = np.repeat(glass, wx1 - wx0, 1)
                xw = np.arange(wx1 - wx0)
                side = ((xw < 9) | (xw >= wx1 - wx0 - 9))[None, :, None]                         # шторы по краям
                folds = 0.8 + 0.12 * np.sin(xw * 1.1)[None, :, None]
                glass = np.where(side, glass * folds * rgb((0.85, 0.6, 0.45)), glass)
            cell[wy0:wy1, wx0:wx1] = glass
            hc[wy0:wy1, wx0:wx1] = -0.12
            mx = (wx0 + wx1) // 2
            cell[wy0:wy1, mx - 1:mx + 1] = rgb((0.82, 0.82, 0.78))                                # импост
            hc[wy0:wy1, mx - 1:mx + 1] = 0.0
            cell[wy0 + 12:wy0 + 14, wx0:wx1] = rgb((0.82, 0.82, 0.78))                            # форточка
            hc[wy0 + 12:wy0 + 14, wx0:wx1] = 0.0
            cell[wy1 + 4:wy1 + 8, wx0 - 8:wx1 + 8] = rgb((0.55, 0.56, 0.57))                       # жестяной отлив
            hc[wy1 + 4:wy1 + 8, wx0 - 8:wx1 + 8] = 0.06
            cell[wy1 + 4:wy1 + 5, wx0 - 8:wx1 + 8] = cell[wy1 + 4:wy1 + 5, wx0 - 8:wx1 + 8] * 0.3 + SNOW * 0.7
            cell[wy1 + 8:wy1 + 26, wx0 - 4:wx1 + 4] *= 1 - streaks(wx1 - wx0 + 8, 18, rng, 1.4)[..., None] * 0.3
            if row == 1:
                emi[y0 + wy0:y0 + wy1, x0 + wx0:x0 + wx1] = glass
                emi[y0 + wy0:y0 + wy1, x0 + mx - 1:x0 + mx + 1] = 0
                emi[y0 + wy0 + 12:y0 + wy0 + 14, x0 + wx0:x0 + wx1] = 0
            alb[y0:y0 + ch, x0:x0 + cw] = cell
            hm[y0:y0 + ch, x0:x0 + cw] = hc
    sc = T.studio(W, H, w, h, samples=16)
    T.relief(sc, "house", hm, W, H, alb, rough=0.9)
    rend = T.render(sc, name)
    lit = emi.sum(2, keepdims=True) > 0
    rend = np.where(lit, np.maximum(rend, emi * 0.9), rend)                                       # свет в окне не в тени
    save(name, rend)
    save("eb_house_emission", emi)


# ------------------------------------------------------------------ опоры и балка моста
def girder():
    """Балка настила и консоли опор 3×3 м: бетон, крашенный охрой, выгоревший; ржавые потёки сверху,
    тёмный низ (панорамы Google 2019, вид с платформы у вокзала)."""
    rng = rng_for("eb_girder")
    w = h = 256
    base = photo("Concrete034", w, relief=0.9, sat=0.4, gain=0.75, tint=(1.0, 0.9, 0.78))
    arr = base * 0.55 + rgb((0.46, 0.36, 0.27)) * 0.45
    ch, shade, _ = ps2_style.peel(h, w, rng, cells=8, cover=0.12, shadow=1)
    arr = arr * (1 - ch[..., None]) + base * 0.8 * ch[..., None]
    arr *= 1 - shade[..., None] * 0.35
    st = ps2_style.drips(h, w, rng, 0.9, 0.8)[..., None]
    arr = arr * (1 - st * 0.4) + rgb((0.30, 0.17, 0.08)) * st * 0.4
    v = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    arr *= 1 - np.clip(v - 0.75, 0, 1) * 1.2                                        # низ балки в тени и копоти
    arr[:10] = arr[:10] * 0.4 + SNOW * 0.6                                          # снег на кромке
    save("eb_girder", arr)


def pier():
    """Колонны моста 3×3 м: серый бетон в потёках, обрывки объявлений и граффити по низу."""
    rng = rng_for("eb_pier")
    w = h = 256
    arr = photo("Concrete012", w, relief=0.9, sat=0.3, gain=0.7, tint=(0.95, 0.93, 0.9))
    arr *= 1 - ps2_style.drips(h, w, rng, 1.0, 0.8)[..., None] * 0.35
    for _ in range(12):
        poster(arr, rng, rng.integers(0, w - 28), rng.integers(int(h * 0.42), h - 40), int(rng.integers(14, 30)),
               int(rng.integers(18, 34)), age=rng.uniform(0.2, 0.8))
    spray_tag(arr, rng, 30, h - 70, 120, 34, (0.10, 0.10, 0.12), width=2.4, letters=4)
    spray_tag(arr, rng, 150, h - 110, 80, 28, (0.75, 0.75, 0.80), outline=(0.2, 0.1, 0.3), width=2.6, letters=3)
    arr[-10:] = arr[-10:] * 0.5 + SNOW * 0.5
    save("eb_pier", arr)


ALL = (ballast, trackbed, white_paint, deck, platform, platform_edge, booth, cabinet,
       tank, gondola, container, coach, lattice, chainlink, lamps, station, station_sign,
       paints, sheet, field, road, ice, grass_clump, trees, house, corrugated, girder, pier)
# какие файлы делает каждая функция (для EB_ONLY)
MAKES = {"white_paint": ["eb_white"], "chainlink": ["eb_mesh"], "lamps": ["eb_lamp_green", "eb_lamp_orange"],
         "station_sign": ["eb_sign_station"], "paints": ["eb_blue_paint", "eb_green_paint", "eb_concrete_pole"],
         "grass_clump": ["eb_grass"], "trees": ["eb_tree", "eb_poplar"], "coach": ["eb_coach", "eb_coach_emission"],
         "house": ["eb_house", "eb_house_emission"]}


def main():
    only = globals().get("EB_ONLY")
    done = []
    win_scene = bpy.context.window.scene if bpy.context.window else None
    for fn in ALL:
        names = MAKES.get(fn.__name__, ["eb_" + fn.__name__])
        if only and not set(names) & set(only):
            continue
        fn()
        done += names
    if win_scene is not None:
        bpy.context.window.scene = win_scene
    return {"made": done}


result = main()
print(result)
