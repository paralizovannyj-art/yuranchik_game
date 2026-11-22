# -*- coding: utf-8 -*-
# Фото -> PS2-текстура (фотобашинг, правило автора [A Т1]).
#
# Конвейер для одной текстуры:
#   load()      — загрузить фото (jpg/webp/png) как float-массив [H, W, 3], 0..1, (0,0) = верх-лево;
#   rectify()   — вырезать четырёхугольник и выпрямить перспективу (гомография);
#   flatten()   — убрать свет с фото: крупные перепады яркости и блики (остаётся фактура и цвет);
#   tone()      — привести к нужному среднему цвету (одна зона — один тон);
#   bash()      — склеить несколько кусков в один холст с мягкими швами (фотобашинг);
#   seamless()  — сделать бесшовной (для тайлящихся стен, пола, потолка);
#   resize()    — уменьшить до PS2-размера (усреднение, без «лесенки»);
#   edge_ao(), grime() — запечь тень и грязь (у пола, в углах, у выключателей).
# Финиш (мягкость, глубина цвета) — ps2_hero.finish(), сохранение — tex_lib.save().
#
# Исходники:
#   docs/references/apartment/   — фото квартиры автора (главный источник);
#   assets/texture_library/      — CC0-наборы (ambientCG, Poly Haven), см. README там.
import os
import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REF = os.path.join(_ROOT, "docs", "references", "apartment")
LIB = os.path.join(_ROOT, "assets", "texture_library")

_cache = {}


def load(path):
    """Фото -> float32 [H, W, 3]. Путь относительный — от docs/references/apartment или texture_library."""
    if not os.path.isabs(path):
        for base in (REF, LIB):
            p = os.path.join(base, path)
            if os.path.exists(p):
                path = p
                break
    if path in _cache:
        return _cache[path]
    import bpy
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    a = a.reshape(h, w, 4)[::-1, :, :3].copy()
    _cache[path] = a
    return a


def lib(name, kind="Color"):
    """Цветная карта из texture_library: 'ambientcg/PaintedWood009C' или 'polyhaven/velour_velvet'."""
    folder = os.path.join(LIB, name)
    for f in sorted(os.listdir(folder)):
        fl = f.lower()
        if kind == "Color" and (fl.endswith("_color.jpg") or "_diff_" in fl or "_coll1_" in fl):
            return load(os.path.join(folder, f))
        if kind == "AO" and ("ambientocclusion" in fl or "_ao_" in fl):
            return load(os.path.join(folder, f))
    raise FileNotFoundError(name + " " + kind)


# ------------------------------------------------------------------ геометрия
def _homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A, np.float64))
    return vt[-1].reshape(3, 3) / vt[-1][-1]


def sample(img, xs, ys):
    """Билинейная выборка img в точках (xs, ys) (пиксели, могут быть дробными)."""
    h, w, _ = img.shape
    xs = np.clip(xs, 0, w - 1.001); ys = np.clip(ys, 0, h - 1.001)
    x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int)
    fx = (xs - x0)[..., None]; fy = (ys - y0)[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def rectify(img, quad, w, h, ss=2):
    """Четырёхугольник quad = [верх-лево, верх-право, низ-право, низ-лево] (пиксели фото) -> прямоугольник w x h.
    ss — суперсэмплинг (против «лесенки» при сильном сжатии)."""
    W, H = w * ss, h * ss
    Hm = _homography([(0, 0), (W, 0), (W, H), (0, H)], quad)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64) + 0.5
    p = Hm @ np.stack([xx.ravel(), yy.ravel(), np.ones(xx.size)])
    xs = (p[0] / p[2]).reshape(H, W); ys = (p[1] / p[2]).reshape(H, W)
    out = sample(img, xs.astype(np.float32), ys.astype(np.float32))
    return resize(out, w, h) if ss > 1 else out


def crop(img, x0, y0, x1, y1):
    return img[y0:y1, x0:x1].copy()


def resize(arr, w, h):
    """Уменьшение с усреднением (и увеличение билинейно)."""
    H, W = arr.shape[:2]
    if (W, H) == (w, h):
        return arr.copy()
    if W >= w and H >= h:
        # box-фильтр: интегральное изображение по дробным границам
        xs = np.linspace(0, W, w + 1); ys = np.linspace(0, H, h + 1)
        ii = np.zeros((H + 1, W + 1, arr.shape[2]), np.float64)
        ii[1:, 1:] = arr.astype(np.float64).cumsum(0).cumsum(1)

        def at(yv, xv):
            y0 = np.floor(yv).astype(int); x0 = np.floor(xv).astype(int)
            y1 = np.minimum(y0 + 1, H); x1 = np.minimum(x0 + 1, W)
            fy = (yv - y0)[:, None, None]; fx = (xv - x0)[None, :, None]
            a = ii[y0][:, x0]; b = ii[y0][:, x1]; c = ii[y1][:, x0]; d = ii[y1][:, x1]
            return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
        S = at(ys, xs)
        area = np.outer(np.diff(ys), np.diff(xs))[..., None]
        return ((S[1:, 1:] - S[1:, :-1] - S[:-1, 1:] + S[:-1, :-1]) / area).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return sample(arr, (xx + 0.5) * W / w - 0.5, (yy + 0.5) * H / h - 0.5)


# ------------------------------------------------------------------ свет и цвет
def blur(arr, sigma, wrap=False):
    """Гаусс по осям; wrap=True — для бесшовных (края заворачиваются)."""
    if sigma <= 0:
        return arr.copy()
    r = int(sigma * 3) + 1
    k = np.exp(-(np.arange(-r, r + 1) ** 2) / (2 * sigma * sigma)).astype(np.float32)
    k /= k.sum()
    out = arr.astype(np.float32)
    for ax in (0, 1):
        n = out.shape[ax]
        if wrap:
            pad = np.take(out, np.arange(-r, n + r) % n, axis=ax)
        else:
            pad = np.take(out, np.clip(np.arange(-r, n + r), 0, n - 1), axis=ax)
        acc = np.zeros_like(out)
        for i, kv in enumerate(k):
            acc += kv * np.take(pad, np.arange(i, i + n), axis=ax)
        out = acc
    return out


def lum(arr):
    return arr[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)


def flatten(arr, sigma=None, strength=1.0, highlights=0.6, wrap=False):
    """Убрать свет с фото: делим на сильно размытую яркость (перепады освещения, виньетка вспышки уходят),
    блики сверху поджимаем. sigma — радиус «света» в пикселях (по умолчанию 1/6 меньшей стороны)."""
    h, w = arr.shape[:2]
    sigma = sigma or min(h, w) / 6
    L = lum(arr)
    m = float(L.mean())
    low = blur(L[..., None], sigma, wrap)[..., 0]
    gain = (m / np.maximum(low, 1e-3)) ** strength
    out = arr * gain[..., None]
    if highlights:
        L2 = lum(out)
        lim = np.percentile(L2, 97)
        over = np.clip(L2 - lim, 0, None)
        out = out * ((L2 - over * highlights) / np.maximum(L2, 1e-4))[..., None]
    return np.clip(out, 0, 1.5)


def tone(arr, rgb=None, sat=1.0, contrast=1.0, mean=None):
    """Привести к тону: средний цвет -> rgb (если задан), насыщенность и контраст вокруг среднего."""
    out = arr.astype(np.float32)
    m = out.reshape(-1, 3).mean(0)
    if contrast != 1.0:
        out = m + (out - m) * contrast
    if sat != 1.0:
        L = lum(out)[..., None]
        out = L + (out - L) * sat
    if rgb is not None:
        out = out * (np.array(rgb, np.float32) / np.maximum(out.reshape(-1, 3).mean(0), 1e-4))
    elif mean is not None:
        out = out * (mean / max(float(lum(out).mean()), 1e-4))
    return np.clip(out, 0, 1)


def recolor(arr, rgb, contrast=1.0, chroma=0.0, shadow_deg=0.0):
    """Одна зона — один тон: от фото берётся рисунок яркости, цвет — заданный rgb (средний цвет итога).
    chroma — сколько собственного цвета фото оставить (0..1), shadow_deg — тени сдвинуть по оттенку
    на пару градусов внутри тона [P Т3]."""
    L = lum(arr)
    m = max(float(L.mean()), 1e-4)
    d = 1 + (L / m - 1) * contrast
    out = np.array(rgb, np.float32) * d[..., None]
    if chroma:
        own = arr / np.maximum(L, 1e-4)[..., None] * np.array(rgb, np.float32).mean()
        out = out * (1 - chroma) + own * d[..., None] * chroma
    if shadow_deg:
        sh = np.clip((1 - d) * 3, 0, 1)[..., None]
        out = out * (1 - sh) + hue_shift(out, shadow_deg) * sh
    return np.clip(out, 0, 1)


def duotone(arr, dark, light, contrast=1.0, bias=0.0):
    """Два тона одной зоны: светлое фото -> light, тёмное -> dark (по рисунку яркости фото).
    bias > 0 — больше светлого тона (тёмный остаётся только в самых тёмных местах)."""
    L = lum(arr)
    m, s = float(L.mean()), max(float(L.std()), 1e-4)
    t = np.clip(0.5 + bias + (L - m) / s * 0.25 * contrast, 0, 1)[..., None]
    return np.array(dark, np.float32) * (1 - t) + np.array(light, np.float32) * t


def planks(w, h, rows, plank_len, src, rng, tone_var=0.12, joint=0.55):
    """Доски (ламинат, паркет) из фото: раскладка рядами вразбежку (тайлится), каждая доска — свой кусок
    фото src (крупнее доски, случайное место), своя яркость; тёмные стыки."""
    out = np.zeros((h, w, 3), np.float32)
    rh = h / rows
    for r in range(rows):
        y0, y1 = int(round(r * rh)), int(round((r + 1) * rh))
        row = np.zeros((y1 - y0, w, 3), np.float32)
        x = 0
        while x < w:
            L = int(plank_len * rng.uniform(0.85, 1.0)) if x + plank_len < w else w - x
            sh, sw = min(src.shape[0], max(4, (y1 - y0) * 2)), min(src.shape[1], max(8, L // 2))
            sy, sx = int(rng.integers(0, src.shape[0] - sh + 1)), int(rng.integers(0, src.shape[1] - sw + 1))
            p = resize(src[sy:sy + sh, sx:sx + sw], L, y1 - y0)
            p = p * (lum(src).mean() / max(float(lum(p).mean()), 1e-4)) * rng.uniform(1 - tone_var, 1 + tone_var)
            p[:, :1] *= joint
            row[:, x:x + L] = p
            x += L
        row[:1] *= joint; row[1:2] *= 1.05
        out[y0:y1] = np.roll(row, int(rng.integers(0, w)), 1)
    return np.clip(out, 0, 1)


def hue_shift(arr, deg):
    """Повернуть оттенок на deg градусов (сохраняя яркость) — для «пары градусов» тени/света [P Т3]."""
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    # вращение вокруг серой оси в YIQ
    m = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]], np.float32)
    r = np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)
    t = np.linalg.inv(m) @ r @ m
    return np.clip(arr @ t.T.astype(np.float32), 0, 1)


# ------------------------------------------------------------------ склейка
def _ramp(n, k):
    """Плавный переход длиной k на краях отрезка n (0 на краю -> 1 внутри)."""
    t = np.ones(n, np.float32)
    r = np.linspace(0, 1, k + 2, dtype=np.float32)[1:-1]
    r = r * r * (3 - 2 * r)
    t[:k] = r; t[n - k:] = r[::-1]
    return t


def seamless(arr, frac=0.25, rng=None):
    """Бесшовная: смешать с копией, сдвинутой на половину, — у краёв берётся сдвинутая (её середина без шва),
    в центре — исходная. Маска с шумом, чтобы переход не читался полосой."""
    h, w = arr.shape[:2]
    rolled = np.roll(arr, (h // 2, w // 2), (0, 1))
    ky, kx = max(2, int(h * frac)), max(2, int(w * frac))
    m = np.minimum(_ramp(h, ky)[:, None], _ramp(w, kx)[None, :])     # 0 у краёв, 1 в центре
    if rng is not None:
        n = blur(rng.random((h, w, 1)).astype(np.float32), max(h, w) / 24, wrap=True)[..., 0]
        n = (n - n.min()) / max(float(np.ptp(n)), 1e-4)
        m = np.clip((m - 0.5) * 1.6 + (n - 0.5) * 0.8 + 0.5, 0, 1)
        m = np.minimum(m, np.minimum(_ramp(h, max(2, ky // 3))[:, None], _ramp(w, max(2, kx // 3))[None, :]) * 4)
        m = np.clip(m, 0, 1)
    return arr * m[..., None] + rolled * (1 - m[..., None])


def bash(canvas_w, canvas_h, pieces, feather=8, wrap=True):
    """Фотобашинг: pieces = [(массив, x, y)] кладутся на холст по очереди, края каждого куска растушёваны
    на feather пикселей. wrap=True — куски заворачиваются через край (под бесшовную текстуру)."""
    acc = np.zeros((canvas_h, canvas_w, 3), np.float32)
    wsum = np.zeros((canvas_h, canvas_w, 1), np.float32)
    for p, x, y in pieces:
        ph, pw = p.shape[:2]
        f = min(feather, ph // 2 - 1, pw // 2 - 1)
        wgt = np.minimum(_ramp(ph, f)[:, None], _ramp(pw, f)[None, :])[..., None] + 1e-3
        ys = (np.arange(ph) + y); xs = (np.arange(pw) + x)
        if wrap:
            ys %= canvas_h; xs %= canvas_w
        else:
            ok_y = (ys >= 0) & (ys < canvas_h); ok_x = (xs >= 0) & (xs < canvas_w)
            p = p[ok_y][:, ok_x]; wgt = wgt[ok_y][:, ok_x]; ys = ys[ok_y]; xs = xs[ok_x]
        # «художник»: поверх предыдущих — новый кусок вытесняет старое там, где он непрозрачен
        acc[np.ix_(ys, xs)] = acc[np.ix_(ys, xs)] * (1 - wgt) + p * wgt
        wsum[np.ix_(ys, xs)] = wsum[np.ix_(ys, xs)] * (1 - wgt) + wgt
    return acc / np.maximum(wsum, 1e-4)


def columns(w, h, srcs, rng, overlap=10, feather=10, wrap=True):
    """Холст w x h, сплошь закрытый кусками: столбцы слева направо, в каждом куски (из srcs, случайные, с
    отражениями) стоят друг над другом с нахлёстом overlap от случайного сдвига по вертикали — без дыр."""
    pieces, x = [], 0
    while x < w:
        y = -int(rng.integers(0, h)) if wrap else -int(rng.integers(0, overlap + 1))
        cw = 0
        while y < h:
            s = srcs[int(rng.integers(0, len(srcs)))]
            if rng.random() < 0.5:
                s = np.flip(s, 1)
            if rng.random() < 0.5:
                s = np.flip(s, 0)
            pieces.append((s, x, y))
            y += s.shape[0] - overlap
            cw = max(cw, s.shape[1]) if cw == 0 else min(cw, s.shape[1])
        x += cw - overlap
    return bash(w, h, pieces, feather, wrap)


def tile(arr, w, h):
    H, W = arr.shape[:2]
    return np.tile(arr, (h // H + 1, w // W + 1, 1))[:h, :w]


# ------------------------------------------------------------------ запечённые тень и грязь
def edge_ao(h, w, bottom=0.0, top=0.0, left=0.0, right=0.0, size=0.12):
    """Множитель затенения у краёв (доля высоты/ширины size): у пола, в углах, под потолком."""
    yy = (np.arange(h, dtype=np.float32) + 0.5) / h
    xx = (np.arange(w, dtype=np.float32) + 0.5) / w
    f = lambda t: np.exp(-t / size)
    m = 1 - bottom * f(1 - yy)[:, None] - top * f(yy)[:, None] - left * f(xx)[None, :] - right * f(1 - xx)[None, :]
    return np.clip(m, 0.2, 1)[..., None]


def grime(h, w, rng, cells=4, amount=0.15, color=(0.55, 0.48, 0.38), wrap=True):
    """Пятна въевшейся грязи (буровато-серые), тайлятся при wrap=True."""
    n = blur(rng.random((h, w, 1)).astype(np.float32), max(h, w) / cells / 3, wrap=wrap)[..., 0]
    n = (n - n.min()) / max(float(np.ptp(n)), 1e-4)
    m = np.clip((n - 0.55) * 3, 0, 1) * amount
    c = np.array(color, np.float32)
    return lambda arr: arr * (1 - m[..., None]) + arr * c * m[..., None]


def preview(arr, path):
    """Сохранить массив как PNG (для просмотра) — через Blender."""
    import bpy
    h, w = arr.shape[:2]
    img = bpy.data.images.new("_pv", w, h, alpha=False)
    rgba = np.ones((h, w, 4), np.float32); rgba[..., :3] = np.clip(arr[..., :3], 0, 1)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
