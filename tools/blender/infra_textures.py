# Текстуры инфраструктуры микрорайона (этап B, docs/CITY_PLAN.md): подпорные стенки, тротуар, проезд,
# теплотрасса, остановка, указатель перехода. PS2-стиль: низкое разрешение, запечённая грязь.
# Запуск:  blender -b --python tools/blender/infra_textures.py
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

R = np.random.default_rng(4107)
SNOW = rgb((0.78, 0.82, 0.9))


def retwall():
    """Подпорная стенка 3×3 м: бетонные плиты по 1,5 м, следы опалубки, потёки, сырой низ."""
    w = h = 256
    arr = photo("Concrete034", w, relief=1.0, sat=0.45, gain=0.85, tint=(0.92, 0.94, 1.0))
    arr *= (0.8 + fbm(w, h, 4, 4, R)[..., None] * 0.4)
    st = streaks(w, h, R, 0.6) * fbm(w, h, 5, 3, R)
    grad = np.linspace(0.6, 1.5, h, dtype=np.float32)[:, None]
    arr *= (1 - st[..., None] * 0.4 * grad[..., None])
    rust = streaks(w, h, R, 0.25) * (fbm(w, h, 3, 2, R) > 0.55)
    arr = arr * (1 - rust[..., None] * 0.35) + rust[..., None] * rgb((0.16, 0.07, 0.02)) * 0.35
    for x in (0, 128):                                  # швы между плитами
        arr[:, x:x+3] *= 0.3
    for y in range(0, h, 43):                           # следы досок опалубки
        arr[y:y+1, :] *= 0.72
    damp = np.clip(np.linspace(-2.2, 1.0, h, dtype=np.float32), 0, 1)[:, None, None]
    arr *= (1 - damp * 0.45)
    arr[-14:] = arr[-14:] * 0.5 + SNOW * 0.5 * (0.7 + fbm(w, 14, 20, 2, R)[..., None] * 0.3)   # снег налип у земли
    save("retwall", arr)


def paving():
    """Тротуарная плитка 2×2 м (плиты 0,5 м): швы, сколы, натоптанный снег пятнами."""
    w = h = 256
    arr = photo("Concrete012", w, relief=0.9, sat=0.3, gain=0.75, tint=(0.82, 0.84, 0.9))
    for k in range(4):
        for j in range(4):
            arr[k*64:(k+1)*64, j*64:(j+1)*64] *= 0.85 + R.random() * 0.3
    for p in range(0, w, 64):
        arr[p:p+2, :] *= 0.35
        arr[:, p:p+2] *= 0.35
    m = np.clip((fbm(w, h, 5, 5, R) - 0.42) * 4.0, 0, 1)[..., None]
    snow = SNOW * (0.75 + fbm(w, h, 24, 24, R, oct=2)[..., None] * 0.25)
    arr = arr * (1 - m * 0.85) + snow * m * 0.85
    save("paving", arr)


def asphalt_snow():
    """Проезд 6×6 м: u — поперёк дороги. Две раскатанные колеи в слякоти, по краям снег."""
    w = h = 256
    arr = photo("Road013A", w, relief=0.8, sat=0.4, gain=0.55)
    x = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    wob = (fbm(w, h, 2, 6, R) - 0.5) * 0.25
    track = np.exp(-((np.abs(x + wob) - 0.42) / 0.16) ** 2)              # колеи
    edge = np.clip((np.abs(x) - 0.72 + wob) * 6, 0, 1)                   # снег у бордюров
    mid = np.exp(-((x + wob) / 0.14) ** 2) * 0.7                         # снежный гребень между колеями
    cover = np.clip(0.55 + edge + mid - track * 0.9 + (fbm(w, h, 12, 12, R) - 0.5) * 0.5, 0, 1)[..., None]
    snow = SNOW * (0.62 + fbm(w, h, 30, 30, R, oct=2)[..., None] * 0.3)
    slush = rgb((0.2, 0.2, 0.22)) * (0.7 + fbm(w, h, 16, 16, R)[..., None] * 0.6)
    arr = arr * 0.5 + slush * 0.5
    arr = arr * (1 - cover) + snow * cover
    save("asphalt_snow", arr)


def pipe_wrap():
    """Изоляция теплотрассы: оцинковка с бандажами, ржавые потёки, рваные дыры со стекловатой.
    u — вокруг трубы, v — вдоль (2 м)."""
    w, h = 128, 128
    arr = fill(h, w, (0.42, 0.44, 0.45)) * (0.75 + fbm(w, h, 8, 8, R)[..., None] * 0.5)
    arr *= (0.85 + streaks(w, h, R, 0.8).T[..., None] * 0.2)
    for y in (0, 64):                                    # бандажи
        arr[y:y+4, :] = rgb((0.2, 0.19, 0.18))
        arr[y+4:y+6, :] *= 0.6
    rust = np.clip((fbm(w, h, 4, 4, R) - 0.5) * 5, 0, 1)[..., None]
    arr = arr * (1 - rust * 0.7) + rgb((0.3, 0.13, 0.05)) * rust * 0.7
    hole = np.clip((fbm(w, h, 3, 3, R) - 0.62) * 12, 0, 1)[..., None]
    wool = rgb((0.62, 0.52, 0.25)) * (0.5 + fbm(w, h, 30, 30, R, oct=2)[..., None] * 0.7)
    arr = arr * (1 - hole) + wool * hole
    u = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    arr *= 0.55 + 0.45 * np.sin(u * np.pi) ** 0.5        # низ трубы темнее (шов развёртки внизу)
    save("pipe_wrap", arr)


def stop_wall():
    """Стенка остановки 4×2 м: низ — крашеный профлист, верх — грязное стекло в раме, обрывки объявлений."""
    w, h = 256, 128
    arr = np.zeros((h, w, 3), np.float32)
    metal = photo("PaintedMetal013", 128, relief=0.8, sat=0.7, gain=0.7, tint=(0.55, 0.75, 0.85))
    arr[64:] = tile(metal, w, 64)
    ribs = (np.sin(np.arange(w, dtype=np.float32) * 2 * np.pi / 16) * 0.5 + 0.5)[None, :, None]
    arr[64:] *= 0.7 + ribs * 0.4
    yy = np.linspace(0, 1, 64, dtype=np.float32)[:, None, None]
    glass = rgb((0.07, 0.09, 0.11)) * (1.2 - yy * 0.5) + rgb((0.1, 0.12, 0.16)) * fbm(w, 64, 6, 3, R)[..., None]
    arr[:64] = glass
    fr = rgb((0.2, 0.2, 0.21))
    arr[0:3] = fr; arr[61:67] = fr; arr[-3:] = fr
    for x in range(0, w, 64):
        arr[:64, x:x+3] = fr
    arr[:, :3] = fr; arr[:, -3:] = fr
    for k in range(7):                                   # объявления: бумажки без текста, часть оборвана
        pw, ph = R.integers(10, 22), R.integers(12, 24)
        x0, y0 = R.integers(6, w - 30), R.integers(8, 96)
        paper = rgb((0.75, 0.72, 0.62)) * (0.6 + R.random() * 0.4)
        tear = fbm(pw, ph, 4, 4, R) > 0.3
        seg = arr[y0:y0+ph, x0:x0+pw]
        seg[tear] = paper * (0.8 + fbm(pw, ph, 6, 6, R)[tear][..., None] * 0.3)
        for ly in range(3, ph - 2, 3):                   # «строчки» — просто серые полоски
            seg[ly, 2:pw-2][tear[ly, 2:pw-2]] *= 0.6
    st = streaks(w, h, R, 0.6)[..., None]
    arr *= 1 - st * 0.3
    rust = np.clip(np.linspace(-3.0, 1.0, h, dtype=np.float32), 0, 1)[:, None, None] * fbm(w, h, 20, 3, R)[..., None]
    arr = arr * (1 - rust * 0.8) + rgb((0.25, 0.11, 0.04)) * rust * 0.8
    save("stop_wall", arr)


def underpass_sign():
    """Светящийся указатель подземного перехода: синяя плашка, белая пиктограмма лестницы. Без надписей."""
    w, h = 192, 32
    arr = fill(h, w, (0.05, 0.16, 0.5)) * (0.8 + fbm(w, h, 12, 3, R)[..., None] * 0.4)
    white = rgb((0.9, 0.92, 0.95))
    arr[:2] = white; arr[-2:] = white; arr[:, :2] = white; arr[:, -2:] = white
    for i in range(5):                                   # ступеньки вниз
        x0, y0 = 70 + i * 9, 7 + i * 4
        arr[y0:y0+2, x0:x0+9] = white
        arr[y0:y0+4, x0+8:x0+10] = white
    arr[27:29, 70:124] = white
    for k in range(6):                                   # стрелка вниз-вправо
        arr[10+k:12+k, 132+k:134+k] = white
    arr[14:18, 132:140] = white; arr[10:18, 136:140] = white
    dirt = streaks(w, h, R, 0.5)[..., None]
    arr *= 1 - dirt * 0.35
    save("underpass_sign", arr)
    save("underpass_sign_emission", arr * 0.9)


retwall()
paving()
asphalt_snow()
pipe_wrap()
stop_wall()
underpass_sign()
print("infra textures: ok")
