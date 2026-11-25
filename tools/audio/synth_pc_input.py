# -*- coding: utf-8 -*-
# Звуки клавиатуры и мыши компа Юрчика: короткие пластиковые щелчки (key_1..3, mouse_click).
# Синтез из шума, как synth_chair.py. Запуск любым Python с numpy:
#   "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe" tools/audio/synth_pc_input.py
import os, wave
import numpy as np

SR = 22050
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "audio", "sfx"))
rng = np.random.default_rng(2007)


def resonator(x, f, q):
    r = 1.0 - np.pi * f / SR / q
    c = 2 * r * np.cos(2 * np.pi * f / SR)
    y = np.zeros_like(x)
    for i in range(2, len(x)):
        y[i] = x[i] + c * y[i - 1] - r * r * y[i - 2]
    return y


def click(dur, f1, f2, thump, decay):
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n) * np.exp(-t / decay)
    x = resonator(noise, f1, 6) * 0.6 + resonator(noise, f2, 9) * 0.4
    x += np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.012) * thump
    return x


def save(name, x):
    x = x / (np.abs(x).max() + 1e-9) * 0.8
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


for i, (f1, f2) in enumerate(((1900, 3600), (1700, 3200), (2100, 3900)), 1):
    down = click(0.06, f1, f2, 0.8, 0.006)
    up = click(0.05, f1 * 1.15, f2 * 1.1, 0.2, 0.004) * 0.35
    gap = np.zeros(int(SR * 0.055))
    save("pc_key_%d" % i, np.concatenate([down, gap, up]))
save("pc_mouse", click(0.05, 2600, 5200, 0.3, 0.004))
