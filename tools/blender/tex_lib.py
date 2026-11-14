# Низкоуровневые функции генерации текстур (numpy) для Blender.
# Используется из textures.py. Все массивы — float32 [H, W, 3], 0..1, (0,0) = верх-лево.
import numpy as np
import bpy
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEX_DIR = os.path.join(_ROOT, "assets", "textures")


def vnoise(w, h, cx, cy, rng):
    """Тайлящийся value-noise с гладкой интерполяцией."""
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


def fbm(w, h, cx, cy, rng, oct=5, gain=0.5):
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    for i in range(oct):
        out += vnoise(w, h, cx * 2 ** i, cy * 2 ** i, rng) * amp
        tot += amp; amp *= gain
    return out / tot


def streaks(w, h, rng, density=1.0):
    """Вертикальные потёки: шум, сильно вытянутый по Y."""
    n = fbm(w, h, int(w / 3 * density), 3, rng, oct=3)
    return np.clip((n - 0.45) * 3.0, 0, 1)


def rgb(c):
    return np.array(c, np.float32)


def fill(h, w, c):
    return np.ones((h, w, 3), np.float32) * rgb(c)


def save(name, arr):
    """Сохраняет массив как PNG в assets/textures и возвращает путь.
    Перед сохранением — PS2-обработка по имени текстуры (таблица ps2_style.TEXTURES).
    Отключить: переменная окружения PS2_OFF=1."""
    if not os.environ.get("PS2_OFF"):
        import ps2_style
        arr = ps2_style.ps2_pass(arr, name)
    h, w, _ = arr.shape
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=False)
    if img.size[0] != w or img.size[1] != h:
        img.scale(w, h)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(arr, 0, 1)
    rgba = rgba[::-1]  # Blender: начало координат снизу
    img.pixels.foreach_set(rgba.ravel())
    path = os.path.join(TEX_DIR, name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    img.filepath = path
    return path


# --- Фототекстуры из библиотеки ---
LIB = os.path.join(_ROOT, "assets", "texture_library", "ambientcg")
_LIGHT = np.array([-0.45, 0.55, 0.70], np.float32)
_LIGHT /= np.linalg.norm(_LIGHT)


def _load(path, w, h):
    img = bpy.data.images.load(path)
    img.scale(w, h)
    a = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3].copy()
    bpy.data.images.remove(img)
    return a


def photo(aid, w, h=None, relief=0.8, ao=1.0, tint=None, sat=1.0, gain=1.0):
    """Фото-текстура w x h с «запечённым» рельефом (из карты нормалей) и AO — как в PS2."""
    h = h or w
    base = os.path.join(LIB, aid, f"{aid}_1K-JPG_")
    col = _load(base + "Color.jpg", w, h)
    if relief and os.path.exists(base + "NormalGL.jpg"):
        n = _load(base + "NormalGL.jpg", w, h) * 2 - 1
        n /= np.linalg.norm(n, axis=2, keepdims=True) + 1e-6
        shade = (n @ _LIGHT) / _LIGHT[2]
        col *= (1 + (np.clip(shade, 0.2, 1.6) - 1) * relief)[..., None]
    if ao and os.path.exists(base + "AmbientOcclusion.jpg"):
        a = _load(base + "AmbientOcclusion.jpg", w, h)[..., :1]
        col *= 1 - (1 - a) * ao
    if sat != 1.0:
        l = col @ np.array([0.299, 0.587, 0.114], np.float32)
        col = l[..., None] + (col - l[..., None]) * sat
    if tint is not None:
        col *= np.array(tint, np.float32)
    return np.clip(col * gain, 0, 1)


def rust_mask(aid, w, h=None):
    """Маска ржавчины: где фото рыже-бурое."""
    h = h or w
    c = _load(os.path.join(LIB, aid, f"{aid}_1K-JPG_Color.jpg"), w, h)
    m = (c[..., 0] - c[..., 1] * 0.9 - c[..., 2] * 0.3)
    return np.clip(m * 4, 0, 1)


def tile(arr, w, h):
    """Повторить текстуру до размера w x h."""
    ry = -(-h // arr.shape[0]); rx = -(-w // arr.shape[1])
    return np.tile(arr, (ry, rx, 1))[:h, :w]


# --- Пиксельный шрифт 5x7 для вывесок ---
FONT = {
    'П': ["11111", "10001", "10001", "10001", "10001", "10001", "10001"],
    'Р': ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    'О': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    'Д': ["00110", "01010", "01010", "01010", "01010", "11111", "10001"],
    'У': ["10001", "10001", "10001", "01111", "00001", "00001", "01110"],
    'К': ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    'Т': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    'Ы': ["10001", "10001", "10001", "11101", "10011", "10011", "11101"],
    'Ч': ["10001", "10001", "10001", "01111", "00001", "00001", "00001"],
    'А': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    'С': ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    'И': ["10001", "10011", "10101", "11001", "10001", "10001", "10001"],
    'В': ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    'Е': ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    'Г': ["11111", "10000", "10000", "10000", "10000", "10000", "10000"],
    'Л': ["00111", "01001", "01001", "01001", "01001", "01001", "11001"],
    'Б': ["11111", "10000", "10000", "11110", "10001", "10001", "11110"],
    'Н': ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    'Ц': ["10010", "10010", "10010", "10010", "10010", "11111", "00001"],
    '2': ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    '4': ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    '1': ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    '7': ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    ' ': ["00000"] * 7,
    '-': ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
}


def draw_text(arr, text, x, y, scale, color):
    cx = x
    for ch in text:
        g = FONT.get(ch, FONT[' '])
        for r, row in enumerate(g):
            for c, bit in enumerate(row):
                if bit == '1':
                    arr[y + r * scale:y + (r + 1) * scale, cx + c * scale:cx + (c + 1) * scale] = color
        cx += 6 * scale
    return cx


def text_width(text, scale):
    return len(text) * 6 * scale - scale
