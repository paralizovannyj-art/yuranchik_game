# -*- coding: utf-8 -*-
# Рабочий стол телефона (YUR-34): сам снимок-референс Nokia (вложение задачи в Jira), ужатый до экрана 320×240.
# Всё неизменное (батарея, Bluetooth, E, дата, значки ярлыков, Go to / Menu / Names) остаётся как на фото;
# затираются только меняющиеся вещи — значок сети, часы, «Operator» и значок Ovi (вместо него — Настройки).
# Затирание делается на полном размере фото по точной маске (у Ovi — только пакет с ручкой), потом ужимается:
# так на месте значка остаётся ровный тёмный фон без размытого пятна.
# Запуск: python tools/make_phone_wallpaper.py <референс.png> assets/ui/phone_wallpaper.png  (нужны numpy и Pillow)
import sys
import numpy as np
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
W, H = 320, 240
a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
# прямоугольники в координатах фото 1280×954
rects = [(0, 0, 80, 75), (670, 5, 985, 82), (0, 178, 272, 288),
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
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS).save(dst)
