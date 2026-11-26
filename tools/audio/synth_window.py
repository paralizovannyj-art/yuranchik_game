# -*- coding: utf-8 -*-
# Звуки пластикового окна в комнате Юрчика (scripts/world/room_window.gd):
#   window_handle — ручка поворачивается на 90°: щелчок фиксатора и лязг запорных цапф по раме;
#   window_open   — створка отлипает от уплотнителя («чпок» с присосом), скрип петли, порыв воздуха;
#   window_close  — створка глухо садится на резинку (выдавленный воздух), потом ручка вниз;
#   amb_window    — улица в открытое окно: ветер, шипение метели по стеклу и откосам, далёкий гул района.
# Синтез из шума и простых волн, как tools/audio/synth_sfx.py, — своё, без чужих записей.
#
# Запуск (numpy есть в Python из поставки Blender):
#   "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe" tools/audio/synth_window.py
# Результат: assets/audio/sfx/window_*.wav, amb_window.wav (моно, 22050 Гц, 16 бит).
import os, wave
import numpy as np

SR = 22050
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "audio", "sfx"))
rng = np.random.default_rng(3141)


def n_(d):
    return int(SR * d)


def noise(d):
    return rng.standard_normal(n_(d))


def band(x, lo, hi, soft=0.25):
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = 1 / (1 + (lo / np.maximum(f, 1e-3)) ** (2 / soft)) if lo > 0 else np.ones_like(f)
    g = g * (1 / (1 + (f / hi) ** (2 / soft))) if hi < SR / 2 else g
    return np.fft.irfft(X * g, n)


def decay(d, k, a=0.001):
    t = np.arange(n_(d)) / SR
    return np.exp(-t * k) * np.clip(t / a, 0, 1)


def resonator(x, f, q):
    r = 1.0 - np.pi * f / SR / q
    c = 2 * r * np.cos(2 * np.pi * f / SR)
    y = np.zeros_like(x)
    for i in range(2, len(x)):
        y[i] = x[i] + c * y[i - 1] - r * r * y[i - 2]
    return y


def mix(out, x, at, g=1.0):
    i = int(at * SR)
    k = min(len(x), len(out) - i)
    out[i:i + k] += x[:k] * g
    return out


def click(d, lo, hi, k, modes=()):
    """Короткий удар пластика/металла: шумовая вспышка + несколько затухающих мод."""
    x = band(noise(d), lo, hi) * decay(d, k)
    t = np.arange(n_(d)) / SR
    for f, g, kk in modes:
        x += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t * kk) * g
    return x


def norm(x, peak):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def save(name, x, peak=0.9):
    x = norm(np.asarray(x, np.float64), peak)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def handle():
    d = 0.42
    out = np.zeros(n_(d))
    # шорох поворота ручки в розетке
    k = n_(0.16)
    out[:k] += band(rng.standard_normal(k), 900, 4000) * np.hanning(k) * 0.06
    # щелчок фиксатора посередине поворота
    mix(out, click(0.04, 2500, 8000, 160, ((3100, 0.25, 140),)), 0.08, 0.5)
    # цапфы выходят из зацепов: два металлических «тынц» с задержкой (верх и низ створки)
    for at, f in ((0.15, 1730), (0.185, 1410)):
        mix(out, click(0.2, 600, 6000, 45, ((f, 0.5, 30), (f * 2.63, 0.25, 50), (f * 0.51, 0.3, 25))), at, 0.9)
    # ручка доходит до упора — глухой пластиковый тук
    mix(out, click(0.08, 150, 1500, 70, ((420, 0.5, 60),)), 0.2, 0.8)
    return out


def sash_open():
    d = 1.6
    out = np.zeros(n_(d))
    # «чпок»: уплотнитель отлипает — низкий присос с быстрым спадом и чуть «резиновым» тоном
    pop = band(noise(0.18), 40, 400) * decay(0.18, 30, 0.004)
    t = np.arange(n_(0.18)) / SR
    pop += np.sin(2 * np.pi * (95 - 180 * t) * t) * np.exp(-t * 28) * 0.8
    mix(out, pop, 0.02, 1.4)
    # резинка отклеивается по периметру — мелкий липкий треск
    tt = 0.05
    while tt < 0.3:
        mix(out, click(0.012, 1500, 7000, 400), tt, rng.uniform(0.05, 0.15))
        tt += rng.uniform(0.006, 0.02)
    # порыв холодного воздуха в щель: шум растёт и уходит в ровный поток
    k = n_(1.4)
    e = np.clip(np.linspace(0, 1, k) / 0.25, 0, 1) * np.exp(-np.linspace(0, 1, k) * 2.0)
    mix(out, band(rng.standard_normal(k), 250, 2600) * e, 0.08, 0.45)
    # петля: тихий тягучий скрип пластика, пока створка идёт
    tt = 0.35
    while tt < 1.15:
        kb = int(rng.uniform(0.01, 0.025) * SR)
        burst = rng.standard_normal(kb) * np.hanning(kb)
        f = rng.uniform(700, 1000) * (1 - 0.15 * (tt - 0.35))
        mix(out, resonator(burst, f, 22.0), tt, 0.035 * (1.2 - tt * 0.6))
        tt += rng.uniform(0.02, 0.06)
    return out


def sash_close():
    d = 0.9
    out = np.zeros(n_(d))
    # створка садится на уплотнитель: глухой удар + выдавленный воздух («пух»)
    thud = band(noise(0.3), 50, 700) * decay(0.3, 22, 0.002)
    t = np.arange(n_(0.3)) / SR
    thud += np.sin(2 * np.pi * 78 * t) * np.exp(-t * 20) * 0.9
    thud += np.sin(2 * np.pi * 310 * t) * np.exp(-t * 45) * 0.25        # пластик рамы
    mix(out, thud, 0.0, 1.3)
    mix(out, band(noise(0.25), 300, 1800) * decay(0.25, 18, 0.01), 0.0, 0.25)
    # стекло в пакете чуть звякает
    mix(out, click(0.3, 3000, 9000, 40, ((4200, 0.12, 25), (5650, 0.08, 30))), 0.01, 0.18)
    # ручка вниз — цапфы заходят в зацепы
    h = handle()[::1]
    mix(out, h, 0.38, 0.75)
    return out


def amb_window():
    d = 10.0
    k = n_(d)
    t = np.arange(k) / SR
    # порывы: медленная огибающая из сглаженного шума
    g = band(rng.standard_normal(k), 0, 0.6)
    g = 0.45 + 0.55 * np.clip((g - g.min()) / (g.max() - g.min() + 1e-9), 0, 1) ** 1.5
    wind = band(rng.standard_normal(k), 90, 650) * g + band(rng.standard_normal(k), 650, 2400) * g ** 2.2 * 0.35
    # свист ветра в щели откоса — тихий тон, плавает по частоте
    f = 760 + 90 * np.sin(2 * np.pi * t / 7.3) + 35 * np.sin(2 * np.pi * t / 2.1)
    whistle = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.clip(g - 0.6, 0, 1) * 0.12
    # снег сечёт по стеклу и подоконнику снаружи: тонкое шипение с мелкой зернистостью
    grit = band(rng.standard_normal(k), 3500, 9000) * (rng.random(k) < 0.08) * 0.6 * g
    hiss = band(rng.standard_normal(k), 2500, 8000) * 0.08 * g + band(grit, 2500, 9000)
    # далёкий гул района: низкий ровный шум + еле слышная машина, проезжающая где-то за домами
    city = band(rng.standard_normal(k), 30, 160) * 0.35
    car = band(rng.standard_normal(k), 120, 900) * np.exp(-((t - 6.2) / 1.6) ** 2) * 0.25
    out = wind + whistle + hiss + city + car
    # бесшовная петля
    fade = n_(1.0)
    w = np.linspace(0, 1, fade)
    out = np.concatenate([out[:fade] * w + out[-fade:] * (1 - w), out[fade:-fade]])
    return out


save("window_handle", handle(), 0.8)
save("window_open", sash_open(), 0.85)
save("window_close", sash_close(), 0.9)
save("amb_window", amb_window(), 0.6)
print("ok")
