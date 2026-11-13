# Текстуры мелких деталей микрорайона (этап F, docs/CITY_PLAN.md):
#   details.png           — атлас 4×4 (покрышка, бочка, мешок, бак, ящик, картон, бетон, ржавчина,
#                           люк, синяя и белая эмаль табличек, световой короб, лёд, проталина, катушка, сталь)
#   details_emission.png  — свечение: горит только световой короб вывески
#   graffiti.png          — 8 надписей на прозрачном фоне (256×512, строки по 64 px)
#   notices.png           — объявления у подъезда на прозрачном фоне
# Запуск:  blender -b --python tools/blender/district_textures_details.py
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import bpy
import numpy as np
import tex_lib
tex_lib.TEX_DIR = os.path.join(ROOT, "assets", "textures")
from tex_lib import fbm, streaks, rgb, fill, save, draw_text, text_width

R = np.random.default_rng(4242)
C = 64


def save_rgba(name, arr):
    h, w, _ = arr.shape
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=True)
    if img.size[0] != w or img.size[1] != h:
        img.scale(w, h)
    img.alpha_mode = 'STRAIGHT'
    img.pixels.foreach_set(np.clip(arr[::-1], 0, 1).astype(np.float32).ravel())
    img.filepath_raw = os.path.join(tex_lib.TEX_DIR, name + ".png")
    img.file_format = 'PNG'
    img.save()


def noisy(c, amp=0.25, cx=6):
    return fill(C, C, c) * (1 - amp / 2 + fbm(C, C, cx, cx, R)[..., None] * amp)


def rusty(c, amount=0.5):
    a = noisy(c)
    m = np.clip((fbm(C, C, 5, 5, R) - (0.62 - amount * 0.35)) * 5, 0, 1)[..., None]
    rust = fill(C, C, (0.30, 0.15, 0.07)) * (0.7 + fbm(C, C, 9, 9, R)[..., None] * 0.6)
    a = a * (1 - m) + rust * m
    a *= 1 - streaks(C, C, R)[..., None] * 0.25
    return a


def cell(atlas, col, row, img):
    atlas[row * C:(row + 1) * C, col * C:(col + 1) * C] = img


def details():
    a = np.zeros((4 * C, 4 * C, 3), np.float32)
    e = np.zeros_like(a)
    yy, xx = np.mgrid[0:C, 0:C].astype(np.float32)

    # ряд 0: покрышка (протектор — поперечные бороздки), бочка, мешок, мусорный бак
    tire = noisy((0.06, 0.06, 0.065), 0.5, 10)
    tire *= (0.75 + 0.25 * ((xx // 4) % 2))[..., None]
    tire[26:38] *= 0.8
    cell(a, 0, 0, tire)
    barrel = rusty((0.12, 0.22, 0.36), 0.7)
    for y in (14, 15, 46, 47):                      # обручи
        barrel[y] *= 0.55
    cell(a, 1, 0, barrel)
    bag = noisy((0.035, 0.035, 0.04), 0.6, 5)
    bag += (np.clip(fbm(C, C, 12, 4, R) - 0.62, 0, 1) * 1.6)[..., None] * rgb((0.3, 0.32, 0.36))      # блики на плёнке
    cell(a, 2, 0, bag)
    bin_ = rusty((0.10, 0.24, 0.14), 0.45)
    for x in range(8, C, 16):                       # рёбра жёсткости
        bin_[:, x:x + 2] *= 0.7
    cell(a, 3, 0, bin_)

    # ряд 1: ящик из досок, картон, бетон, ржавчина
    wood = fill(C, C, (0.34, 0.26, 0.17)) * (0.75 + fbm(C, C, 3, 20, R)[..., None] * 0.5)
    for y in range(0, C, 13):
        wood[y:y + 2] *= 0.35
    wood[:, 0:5] *= 0.8
    wood[:, C - 5:] *= 0.8
    cell(a, 0, 1, wood)
    card = noisy((0.42, 0.33, 0.22), 0.2)
    card[:, 30:33] *= 0.75
    card[40:C] *= 0.8                               # отсырел снизу
    cell(a, 1, 1, card)
    conc = noisy((0.36, 0.36, 0.35), 0.35, 9)
    conc *= 1 - streaks(C, C, R)[..., None] * 0.3
    cell(a, 2, 1, conc)
    cell(a, 3, 1, rusty((0.3, 0.2, 0.14), 1.0))

    # ряд 2: люк, синяя эмаль, белая эмаль, световой короб
    r = np.hypot(xx - 31.5, yy - 31.5)
    hatch = noisy((0.16, 0.15, 0.14), 0.4, 10)
    hatch *= (0.7 + 0.3 * (((xx // 6) + (yy // 6)) % 2))[..., None]
    hatch[(r > 22) & (r < 25)] *= 0.5
    hatch[r > 29] = rgb((0.05, 0.05, 0.055))
    hatch[(r < 7)] *= 0.7
    cell(a, 0, 2, hatch)
    blue = rusty((0.05, 0.12, 0.38), 0.25)
    blue[2:4, 2:C - 2] = blue[C - 4:C - 2, 2:C - 2] = rgb((0.75, 0.76, 0.78))
    blue[2:C - 2, 2:4] = blue[2:C - 2, C - 4:C - 2] = rgb((0.75, 0.76, 0.78))
    cell(a, 1, 2, blue)
    cell(a, 2, 2, rusty((0.72, 0.72, 0.70), 0.2))
    box = fill(C, C, (0.85, 0.72, 0.38)) * (0.85 + fbm(C, C, 4, 4, R)[..., None] * 0.2)
    box[0:3] = box[C - 3:] = rgb((0.1, 0.1, 0.1))
    box[:, 0:3] = box[:, C - 3:] = rgb((0.1, 0.1, 0.1))
    cell(a, 3, 2, box)
    lit = box * rgb((1.0, 0.85, 0.55)) * 0.9
    lit[20:44] *= 1.0 - 0.25 * (fbm(C, C, 8, 2, R)[20:44, :, None])          # лампы внутри горят неровно
    cell(e, 3, 2, lit)

    # ряд 3: лёд, проталина у люка, светлое дерево катушки, тёмная сталь
    ice = fill(C, C, (0.62, 0.72, 0.82)) * (0.8 + fbm(C, C, 3, 14, R)[..., None] * 0.35)
    cell(a, 0, 3, ice)
    thaw = noisy((0.08, 0.08, 0.085), 0.4, 8)
    cell(a, 1, 3, thaw)
    spool = fill(C, C, (0.45, 0.36, 0.24)) * (0.75 + fbm(C, C, 18, 3, R)[..., None] * 0.5)
    for x in range(0, C, 9):
        spool[:, x:x + 1] *= 0.5
    cell(a, 2, 3, spool)
    cell(a, 3, 3, rusty((0.13, 0.13, 0.14), 0.35))

    save("details", a)
    save("details_emission", e)


def graffiti():
    W, H, ROW = 256, 512, 64
    out = np.zeros((H, W, 4), np.float32)
    tags = [("КИНО", (0.05, 0.05, 0.05), 6), ("ПАСКОТ", (0.75, 0.08, 0.06), 5), ("ЦСКА", (0.1, 0.2, 0.7), 6),
            ("ОН ВИДИТ", (0.05, 0.05, 0.05), 4), ("ГРОБ", (0.85, 0.85, 0.82), 6), ("ВЕРНИ ДОЛГ", (0.7, 0.07, 0.05), 4),
            ("ОНИ ТУТ", (0.86, 0.86, 0.84), 5), ("ТУТ БЫЛ ВИТЕК", (0.06, 0.06, 0.07), 3)]
    for i, (text, color, sc) in enumerate(tags):
        m = np.zeros((ROW, W, 3), np.float32)
        x = max(2, (W - text_width(text, sc)) // 2)
        y = max(2, (ROW - 7 * sc) // 2 - 4)
        for ch in text:                              # буквы пляшут — писали от руки
            draw_text(m, ch, x, int(np.clip(y + R.integers(-3, 4), 0, ROW - 7 * sc)), sc, (1, 1, 1))
            x += 6 * sc
        mask = m[..., 0]
        drip = np.zeros_like(mask)                   # потёки краски вниз
        for _ in range(7):
            cx = int(R.integers(4, W - 4))
            ys = np.nonzero(mask[:, cx])[0]
            if len(ys):
                y0 = ys.max()
                drip[y0:min(ROW, y0 + int(R.integers(4, 16))), cx:cx + 2] = 0.8
        mask = np.maximum(mask, drip)
        soft = mask.copy()                           # мягкий край баллончика
        for sh in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            soft += np.roll(mask, sh, (0, 1)) * 0.5
        alpha = np.clip(soft / 1.6, 0, 1) * (0.72 + fbm(W, ROW, 14, 4, R) * 0.28)
        out[i * ROW:(i + 1) * ROW, :, :3] = rgb(color)
        out[i * ROW:(i + 1) * ROW, :, 3] = alpha
    save_rgba("graffiti", out)


def notices():
    S = 128
    out = np.zeros((S, S, 4), np.float32)
    sheets = [(6, 8, 40, 52, (0.82, 0.80, 0.72)), (50, 4, 34, 44, (0.86, 0.84, 0.80)), (88, 12, 34, 50, (0.80, 0.70, 0.66)),
              (14, 66, 46, 56, (0.84, 0.82, 0.70)), (66, 58, 30, 36, (0.78, 0.80, 0.82)), (98, 70, 26, 50, (0.86, 0.85, 0.78))]
    for (x, y, w, h, c) in sheets:
        p = fill(h, w, c) * (0.85 + fbm(w, h, 3, 3, R)[..., None] * 0.2)
        p[2:5, 3:w - 3] *= 0.35                       # заголовок
        for ly in range(9, h - 12, 4):                # строчки
            p[ly, 3:w - int(R.integers(3, w // 2))] *= 0.45
        for lx in range(3, w - 2, 5):                 # отрывные хвостики с телефоном
            p[h - 10:h, lx] *= 0.4
        keep = np.ones((h, w), np.float32)
        for lx in range(0, w, 5):                     # часть хвостиков оторвана
            if R.random() < 0.4:
                keep[h - 10:h, lx:lx + 5] = 0
        out[y:y + h, x:x + w, :3] = p
        out[y:y + h, x:x + w, 3] = keep
    save_rgba("notices", out)


details()
graffiti()
notices()
print("details textures done")
