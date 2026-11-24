# -*- coding: utf-8 -*-
# Рабочий стол телефона (YUR-34): сам снимок-референс Nokia (вложение задачи в Jira), ужатый до экрана 320×240.
# Всё неизменное (батарея, Bluetooth, E, дата, значки ярлыков, Go to / Menu / Names) остаётся как на фото;
# затираются только меняющиеся вещи — значок сети, часы, «Operator» и значок Ovi (вместо него — Настройки).
# Запуск: python tools/make_phone_wallpaper.py <референс.png> assets/ui/phone_wallpaper.png  (нужны numpy и Pillow)
import sys
import numpy as np
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
W, H = 320, 240
im = Image.open(src).convert("RGB")
sx, sy = W / im.width, H / im.height
a = np.asarray(im.resize((W, H), Image.LANCZOS)).astype(np.float32)
rects = [(0,0,80,75),(670,5,985,82),(0,178,272,288),(1092,622,1238,788)]
m = np.zeros((H, W), bool)
for x0,y0,x1,y1 in rects:
    m[int(y0*sy):int(np.ceil(y1*sy)), int(x0*sx):int(np.ceil(x1*sx))] = True
out = a.copy()
out[m] = a[~m].mean(0)
for _ in range(1500):
    avg = (np.roll(out,1,0)+np.roll(out,-1,0)+np.roll(out,1,1)+np.roll(out,-1,1))/4
    out[m] = avg[m]
rng = np.random.default_rng(3)
out[m] += rng.normal(0, 4, (m.sum(), 3))
Image.fromarray(np.clip(out,0,255).astype(np.uint8)).save(dst)
big = Image.fromarray(np.clip(out,0,255).astype(np.uint8)).resize((W*3,H*3), Image.NEAREST)
big.save(dst.replace(".png","_x3.png"))
