# -*- coding: utf-8 -*-
# Звук игрового кресла (chair_sit): глухой «плюх» в подушку и скрип пластика/газлифта.
# Синтез из шума и простых волн, как tools/audio/synth_sfx.py, — своё, без чужих записей.
#
# Запуск (numpy есть в Python из поставки Blender):
#   "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe" tools/audio/synth_chair.py
# Результат: assets/audio/sfx/chair_sit.wav (моно, 22050 Гц, 16 бит).
import os, wave
import numpy as np

SR = 22050
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "audio", "sfx"))
rng = np.random.default_rng(4711)


def lowpass(x, a):
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def resonator(x, f, q):
    # двухполюсный резонатор: «пластиковый» тон скрипа
    r = 1.0 - np.pi * f / SR / q
    c = 2 * r * np.cos(2 * np.pi * f / SR)
    y = np.zeros_like(x)
    for i in range(2, len(x)):
        y[i] = x[i] + c * y[i - 1] - r * r * y[i - 2]
    return y


def chair_sit():
    n = int(SR * 0.9)
    out = np.zeros(n)
    # плюх: низкий шум с быстрым спадом (с 0.05 с)
    s0 = int(0.05 * SR)
    m = int(0.25 * SR)
    thump = lowpass(rng.standard_normal(m), 0.04) * np.exp(-np.linspace(0, 9, m))
    out[s0:s0 + m] += thump * 2.2
    # скрип: серия коротких трений с плавающей частотой (кресло проседает на газлифте)
    t = 0.12
    while t < 0.7:
        k = int(rng.uniform(0.008, 0.02) * SR)
        burst = rng.standard_normal(k) * np.hanning(k)
        f = rng.uniform(520, 900) * (1.0 - 0.25 * (t - 0.12))
        tone = resonator(burst, f, 18.0)
        i = int(t * SR)
        out[i:i + k] += tone[: n - i] * 0.06 * (1.0 - t)
        t += rng.uniform(0.018, 0.05)
    out /= np.max(np.abs(out)) + 1e-9
    return out * 0.8


def save(name, x):
    os.makedirs(OUT, exist_ok=True)
    data = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


save("chair_sit", chair_sit())
print("ok")
