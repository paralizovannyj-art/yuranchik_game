# -*- coding: utf-8 -*-
# Рабочий стол телефона (YUR-34): сам снимок-референс Nokia (вложение задачи в Jira), ужатый до экрана 320×240.
# Всё неизменное (значок сети, батарея, Bluetooth, E, дата, значки ярлыков, Go to / Menu / Names) остаётся как на фото;
# затираются только меняющиеся вещи — часы, «Operator» и значок Ovi (вместо него — Настройки).
# Затирание делается на полном размере фото по точной маске (у Ovi — только пакет с ручкой), потом ужимается:
# так на месте значка остаётся ровный тёмный фон без размытого пятна.
# Значки строки статуса (перечёркнутая антенна, батарея 3 из 4, Bluetooth, E) берутся со второго, более чёткого
# снимка строки статуса из задачи: на основном фото они затираются, а сверху кладутся вырезанные значки.
# Запуск: python tools/make_phone_wallpaper.py <референс.png> <строка_статуса.png> assets/ui/phone_wallpaper.png
# (нужны numpy и Pillow)
import sys
import numpy as np
from PIL import Image, ImageFilter
src, status, dst = sys.argv[1], sys.argv[2], sys.argv[3]
W, H = 320, 240
a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
# прямоугольники в координатах фото 1280×954
rects = [(0, 0, 88, 80), (120, 0, 230, 74), (238, 0, 308, 78), (312, 0, 394, 80),   # значки статуса
         (670, 5, 985, 82), (0, 178, 272, 288),
         (1104, 662, 1230, 774), (1130, 634, 1205, 686)]   # Ovi: пакет и ручка
m = np.zeros(a.shape[:2], bool)
for x0, y0, x1, y1 in rects:
    m[y0:y1, x0:x1] = True
pad = 30
out = a.copy()
for x0, y0, x1, y1 in rects:
    X0, Y0, X1, Y1 = max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, a.shape[1]), min(y1 + pad, a.shape[0])
    win = out[Y0:Y1, X0:X1]
    wm = m[Y0:Y1, X0:X1]
    win[wm] = win[~wm].mean(0)
    for _ in range(4000):                        # заливка от краёв внутрь (сглаживание по соседям)
        p = np.pad(win, ((1, 1), (1, 1), (0, 0)), mode="edge")
        avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4
        win[wm] = avg[wm]
    if x0 > 1000:                                # Ovi лежит на чёрном плаще — не даём светлому краю панели растечься пятном
        win[wm] = np.minimum(win[wm], np.percentile(win[~wm], 25, axis=0) + 3)
    out[Y0:Y1, X0:X1] = win
rng = np.random.default_rng(3)
out[m] += rng.normal(0, 3, (m.sum(), 3))
# значки со снимка строки статуса: (рамка на снимке, центр на основном фото, как вырезать)
st = Image.open(status).convert("RGB")
K = 1.07                                         # снимок строки статуса чуть мельче основного фото
icons = [((0, 0, 90, 64), (42, 38), "shape"),    # антенна: тёмные палки, белая и красная полоски
         ((118, 1, 208, 64), (175, 37), "box"),  # батарея
         ((228, 2, 282, 66), (272, 39), "white"),  # Bluetooth
         ((302, 0, 366, 64), (353, 38), "box")]  # E
for box, (cx, cy), kind in icons:
    crop = st.crop(box)
    c = np.asarray(crop).astype(np.float32)
    if kind == "box":
        al = np.ones(c.shape[:2], np.float32)
        for yy, xx in [(0, 0), (0, -1), (-1, 0), (-1, -1)]:
            al[yy, xx] = 0
    elif kind == "white":
        al = (c.min(2) > 165).astype(np.float32)
    else:
        al = np.clip((75 - (c[:, :, 2] - c[:, :, 0])) / 25, 0, 1)   # серые, белые и красные части, а не синее небо
    if kind != "box":
        al = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))).astype(np.float32) / 255
    w, h = round(crop.width * K), round(crop.height * K)
    c = np.asarray(crop.resize((w, h), Image.LANCZOS)).astype(np.float32)
    al = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
                    .filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32)[..., None] / 255
    x0, y0 = max(cx - w // 2, 0), max(cy - h // 2, 0)
    reg = out[y0:y0 + h, x0:x0 + w]
    reg[:] = reg * (1 - al[:reg.shape[0], :reg.shape[1]]) + c[:reg.shape[0], :reg.shape[1]] * al[:reg.shape[0], :reg.shape[1]]
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS).save(dst)
