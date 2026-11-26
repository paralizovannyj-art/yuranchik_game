# -*- coding: utf-8 -*-
# Звуки игрового кресла:
#   chair_sit  — глухой «плюх» в подушку и скрип пластика/газлифта;
#   chair_roll — колёсики катятся по полу (откатил кресло, подъехал к столу);
#   chair_spin — кресло крутится: скрип поворотного механизма и шорох колёсиков.
# Синтез из шума и простых волн, как tools/audio/synth_sfx.py, — своё, без чужих записей.
#
# Запуск (numpy есть в Python из поставки Blender):
#   "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe" tools/audio/synth_chair.py
# Результат: assets/audio/sfx/chair_sit.wav, chair_roll.wav, chair_spin.wav (моно, 22050 Гц, 16 бит).
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


def chair_roll(dur=0.75):
    n = int(SR * dur)
    t = np.linspace(0, dur, n)
    env = np.minimum(1.0, t / 0.08) * np.minimum(1.0, (dur - t) / 0.25) ** 1.5
    # гул: шум через два фильтра низких частот (пластик по линолеуму)
    rumble = lowpass(lowpass(rng.standard_normal(n), 0.06), 0.15) * 3.0
    # «тиканье» сдвоенных колёсиков: мелкие неровности пола, чаще, пока кресло разгоняется
    ticks = np.zeros(n)
    tt = 0.03
    while tt < dur - 0.05:
        i = int(tt * SR)
        k = int(0.004 * SR)
        ticks[i:i + k] += rng.standard_normal(k) * np.hanning(k) * rng.uniform(0.2, 0.6)
        tt += rng.uniform(0.025, 0.07)
    ticks = resonator(ticks, 1900.0, 6.0) * 0.08
    out = (rumble + ticks) * env
    out /= np.max(np.abs(out)) + 1e-9
    return out * 0.7


def chair_spin():
    dur = 0.7
    n = int(SR * dur)
    out = chair_roll(dur) * 0.45
    # скрип крестовины: длинное трение с плывущей вниз частотой
    t = 0.04
    while t < 0.55:
        k = int(rng.uniform(0.01, 0.025) * SR)
        burst = rng.standard_normal(k) * np.hanning(k)
        f = 340.0 * (1.0 - 0.35 * t / 0.55) * rng.uniform(0.95, 1.05)
        tone = resonator(burst, f, 26.0)
        i = int(t * SR)
        out[i:i + k] += tone[: n - i] * 0.05 * (1.0 - t / 0.7)
        t += rng.uniform(0.012, 0.03)
    out /= np.max(np.abs(out)) + 1e-9
    return out * 0.75


save("chair_sit", chair_sit())
save("chair_roll", chair_roll())
save("chair_spin", chair_spin())
print("ok")
