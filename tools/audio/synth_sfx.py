# -*- coding: utf-8 -*-
# Звуки-заглушки для MVP: всё синтезируется из шума и простых волн (numpy), без чужих записей.
# Потом заменим на ElevenLabs / записи друзей — имена файлов оставить те же.
#
# Запуск (нужен numpy; он есть в Python из поставки Blender):
#   "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe" tools/audio/synth_sfx.py
# Результат: assets/audio/sfx/*.wav (моно, 22050 Гц, 16 бит — «звук эпохи PS2»).
import os, wave
import numpy as np

SR = 22050
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "audio", "sfx"))
rng = np.random.default_rng(1977)


def t_(d):
    return np.arange(int(SR * d)) / SR


def noise(d):
    return rng.standard_normal(int(SR * d))


def band(x, lo, hi, soft=0.25):
    """Полосовой фильтр через FFT с мягкими краями."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = 1 / (1 + (lo / np.maximum(f, 1e-3)) ** (2 / soft * 1.0)) if lo > 0 else np.ones_like(f)
    g = g * (1 / (1 + (f / hi) ** (2 / soft * 1.0))) if hi < SR / 2 else g
    return np.fft.irfft(X * g, n)


def env(d, a=0.005, r=None, curve=3.0):
    """Огибающая: быстрая атака, экспоненциальный спад."""
    t = t_(d)
    e = np.exp(-t * curve / d * 2.3)
    e *= np.clip(t / a, 0, 1)
    if r:
        e *= np.clip((d - t) / r, 0, 1)
    return e


def sweep(f0, f1, d, shape="sin"):
    t = t_(d)
    f = f0 + (f1 - f0) * (t / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    if shape == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    if shape == "sq":
        return np.sign(np.sin(ph))
    return np.sin(ph)


def norm(x, peak=0.9):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def loopify(x, fade=0.4):
    """Бесшовная петля: хвост перекрёстно вмешивается в начало."""
    n = int(SR * fade)
    k = np.linspace(0, 1, n)
    head = x[:n] * k + x[-n:] * (1 - k)
    return np.concatenate([head, x[n:-n]])


def pad(x, d):
    n = int(SR * d)
    return np.concatenate([x, np.zeros(max(n - len(x), 0))])[:max(n, len(x))]


def mixat(base, x, at, gain=1.0):
    i = int(SR * at)
    if i + len(x) > len(base):
        base = np.concatenate([base, np.zeros(i + len(x) - len(base))])
    base[i:i + len(x)] += x * gain
    return base


def save(name, x, peak=0.9):
    x = norm(np.asarray(x, np.float64), peak)
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def voice(d, f0, f1, formants, breath=0.25, vib=0.0, rough=0.0):
    """Грубый «голос»: пила + шум через несколько формант."""
    t = t_(d)
    f = f0 + (f1 - f0) * (t / d)
    f = f * (1 + vib * np.sin(2 * np.pi * 6 * t)) * (1 + rough * band(noise(d), 0, 40) * 0.6)
    ph = np.cumsum(f) / SR
    src = (2 * (ph % 1) - 1) + breath * noise(d)
    out = np.zeros_like(src)
    for fc, bw, g in formants:
        out += band(src, fc - bw / 2, fc + bw / 2, 0.5) * g
    return out


# ---------------------------------------------------------------- шаги
for i in range(4):                                                    # снег: хруст
    d = 0.20 + 0.03 * i
    grains = np.repeat(rng.random(int(d * 260) + 1) ** 3, SR // 260 + 1)[:int(SR * d)]
    x = band(noise(d), 900 + 150 * i, 5200) * grains * env(d, 0.01, 0.05, 2.0)
    x += band(noise(d), 80, 300) * env(d, 0.004, None, 6.0) * 0.6
    save("step_snow_%d" % (i + 1), x, 0.7)
for i in range(3):                                                    # бетон подъезда
    d = 0.16
    x = sweep(150 - 15 * i, 70, d) * env(d, 0.002, None, 7.0) + band(noise(d), 1500, 4500) * env(d, 0.001, None, 14.0) * 0.5
    save("step_floor_%d" % (i + 1), x, 0.6)
d = 0.3
save("step_heavy", sweep(90, 38, d) * env(d, 0.003, None, 5.0) + band(noise(d), 200, 1400) * env(d, 0.002, None, 9.0) * 0.5, 0.95)

# ---------------------------------------------------------------- бой
d = 0.28
t = t_(d)
sw = sum(band(noise(d), fc * 0.8, fc * 1.3) * np.exp(-((t - tc) / 0.05) ** 2) for fc, tc in ((500, 0.07), (900, 0.11), (1500, 0.15), (900, 0.2)))
save("swing", sw, 0.55)
for i in range(3):
    d = 0.3
    x = sweep(120 - 12 * i, 45, d) * env(d, 0.002, None, 6.0) * 1.2
    x += band(noise(d), 300, 2600 + 500 * i) * env(d, 0.001, None, 12.0)
    x += band(noise(d), 2500, 7000) * env(d, 0.001, None, 30.0) * 0.4
    save("hit_%d" % (i + 1), x, 0.95)
d = 0.22
save("punch", sweep(170, 60, d) * env(d, 0.002, None, 8.0) + band(noise(d), 400, 3000) * env(d, 0.001, None, 14.0) * 0.8, 0.85)
d = 0.5
save("body_fall", sweep(80, 35, d) * env(d, 0.004, None, 4.0) + band(noise(d), 100, 900) * env(d, 0.01, None, 5.0) * 0.8, 0.8)
d = 0.6
gl = band(noise(d), 2500, 9000) * env(d, 0.001, None, 9.0)
for _ in range(14):
    f = rng.uniform(2200, 7500); st = rng.uniform(0, 0.18); dd = rng.uniform(0.05, 0.3)
    gl = mixat(gl, np.sin(2 * np.pi * f * t_(dd)) * env(dd, 0.001, None, 5.0), st, rng.uniform(0.15, 0.5))
save("glass_break", gl[:int(SR * 0.7)], 0.9)
d = 0.35
save("brick_hit", sweep(200, 70, d) * env(d, 0.001, None, 8.0) + band(noise(d), 500, 3500) * env(d, 0.001, None, 10.0), 0.9)
d = 0.3
save("throw", band(noise(d), 600, 2500) * np.exp(-((t_(d) - 0.1) / 0.07) ** 2), 0.45)

# ---------------------------------------------------------------- голоса (заглушки)
F_A = ((650, 300, 1.0), (1100, 350, 0.7), (2500, 600, 0.25))
F_O = ((450, 250, 1.0), (850, 300, 0.6), (2400, 600, 0.15))
F_E = ((500, 250, 1.0), (1700, 400, 0.5), (2500, 600, 0.2))
save("player_hurt_1", voice(0.28, 190, 130, F_O, 0.3) * env(0.28, 0.02, 0.08, 2.0), 0.7)
save("player_hurt_2", voice(0.24, 210, 150, F_A, 0.3) * env(0.24, 0.015, 0.08, 2.0), 0.7)
save("player_die", voice(1.1, 180, 80, F_O, 0.4, rough=0.3) * env(1.1, 0.03, 0.5, 1.2), 0.75)
save("enemy_alert_1", voice(0.42, 120, 165, F_E, 0.25, rough=0.5) * env(0.42, 0.02, 0.12, 1.0), 0.85)
save("enemy_alert_2", voice(0.5, 105, 150, F_A, 0.25, rough=0.6) * env(0.5, 0.03, 0.15, 1.0), 0.85)
save("enemy_attack", voice(0.3, 140, 100, F_A, 0.35, rough=0.8) * env(0.3, 0.01, 0.1, 1.5), 0.8)
save("enemy_hurt_1", voice(0.3, 150, 95, F_O, 0.3, rough=0.5) * env(0.3, 0.01, 0.1, 2.0), 0.8)
save("enemy_hurt_2", voice(0.26, 170, 110, F_E, 0.3, rough=0.5) * env(0.26, 0.01, 0.1, 2.0), 0.8)
save("enemy_die", voice(0.95, 140, 60, F_O, 0.45, rough=0.6) * env(0.95, 0.02, 0.5, 1.2), 0.85)
save("enemy_idle", voice(1.3, 85, 75, F_O, 0.5, vib=0.02, rough=0.9) * env(1.3, 0.3, 0.6, 0.6), 0.5)
save("sergey_breath", voice(1.8, 52, 44, ((300, 250, 1.0), (700, 300, 0.5), (1500, 800, 0.3)), 1.2, rough=0.9) * env(1.8, 0.5, 0.9, 0.5), 0.8)
save("sergey_roar", voice(1.4, 70, 48, F_O, 0.6, rough=1.2) * env(1.4, 0.05, 0.6, 0.8), 0.95)
save("struggle", band(noise(0.5), 300, 2500) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * t_(0.5))) * env(0.5, 0.05, 0.2, 0.8), 0.5)

# ---------------------------------------------------------------- предметы, двери, интерфейс
d = 0.16
save("pickup", (sweep(520, 780, d, "sin") * 0.6 + band(noise(d), 1500, 5000) * 0.3) * env(d, 0.004, 0.05, 2.5), 0.5)
d = 0.5
save("heal", (sweep(330, 660, d) + 0.5 * sweep(495, 990, d)) * env(d, 0.05, 0.25, 1.0), 0.45)
save("eat", band(noise(0.45), 300, 1800) * (np.abs(np.sin(2 * np.pi * 5 * t_(0.45))) ** 4) * env(0.45, 0.02, 0.1, 0.8), 0.55)
save("ui_move", sweep(900, 700, 0.04) * env(0.04, 0.002, 0.01, 3.0), 0.3)
save("ui_select", (sweep(700, 1050, 0.09) + 0.4 * sweep(1400, 2100, 0.09)) * env(0.09, 0.003, 0.03, 2.0), 0.4)
save("ui_error", sweep(180, 150, 0.16, "sq") * env(0.16, 0.003, 0.05, 1.5), 0.3)
save("ui_open", band(noise(0.22), 500, 3000) * env(0.22, 0.03, 0.1, 1.5), 0.35)
save("click", band(noise(0.03), 1500, 6000) * env(0.03, 0.001, None, 10.0), 0.5)
x = np.zeros(1)
for at in (0.0, 0.09, 0.2):
    x = mixat(x, sweep(240, 120, 0.07) * env(0.07, 0.001, None, 8.0) + band(noise(0.07), 1200, 4000) * env(0.07, 0.001, None, 14.0) * 0.6, at)
save("door_locked", x, 0.7)
x = np.zeros(1)
for at, f in ((0.0, 2600), (0.12, 1900), (0.3, 700)):
    x = mixat(x, band(noise(0.06), f * 0.7, f * 1.5) * env(0.06, 0.001, None, 10.0), at)
save("unlock", x, 0.7)
d = 0.9
cr = voice(d, 210, 330, ((700, 300, 1.0), (1500, 500, 0.6), (3000, 800, 0.3)), 0.1, vib=0.05, rough=1.4) * env(d, 0.1, 0.3, 0.6)
save("door_open", mixat(cr * 0.6, sweep(110, 50, 0.3) * env(0.3, 0.003, None, 6.0), 0.75), 0.7)
d = 1.6
gr = voice(d, 95, 150, ((500, 300, 1.0), (1300, 500, 0.8), (2800, 900, 0.5)), 0.3, vib=0.08, rough=1.8) * env(d, 0.2, 0.5, 0.5)
gr += band(noise(d), 60, 250) * env(d, 0.3, 0.6, 0.5) * 0.8
save("garage_open", gr, 0.85)
x = np.zeros(1)
for at in (0.0, 0.42, 0.78):
    x = mixat(x, sweep(95, 40, 0.35) * env(0.35, 0.002, None, 5.0) * 1.3 + band(noise(0.35), 150, 1200) * env(0.35, 0.002, None, 8.0), at)
save("door_bang", x, 0.95)
d = 0.9
hb = np.zeros(int(SR * d))
for at in (0.0, 0.26):
    hb = mixat(hb, sweep(70, 40, 0.16) * env(0.16, 0.004, None, 5.0), at)[:int(SR * d)]
save("heartbeat", hb, 0.8)

# ---------------------------------------------------------------- стингеры
d = 3.2
st = sum(sweep(f, f * 0.985, d, "saw") for f in (55, 58.3, 82.4, 87.3, 116.5, 123.5, 233, 247))
st = band(st, 40, 2600) * env(d, 0.004, 1.2, 1.3)
st = mixat(st, sweep(60, 28, 1.2) * env(1.2, 0.002, None, 3.0) * 6, 0.0)[:int(SR * d)]
st += band(noise(d), 3000, 9000) * env(d, 0.001, None, 8.0) * 2
save("stinger", st, 0.95)
d = 2.4
save("death_sting", band(sum(sweep(f, f * 0.5, d, "saw") for f in (110, 116.5, 164.8)), 40, 1800) * env(d, 0.01, 1.2, 1.0), 0.8)
d = 4.0
save("win", band(sum(sweep(f, f, d, "saw") * g for f, g in ((110, 1), (164.8, 0.7), (220, 0.6), (277.2, 0.4), (329.6, 0.3))), 60, 1400) * env(d, 0.6, 2.0, 0.5), 0.6)

# ---------------------------------------------------------------- петли окружения и музыки
d = 9.0
t = t_(d)
gust = 0.55 + 0.45 * np.sin(2 * np.pi * t / d * 2 + 1.0) * np.sin(2 * np.pi * t / d * 3)
wind = band(noise(d), 120, 700) * gust + band(noise(d), 700, 2200) * (gust ** 2) * 0.25
wind += band(noise(d), 30, 110) * 0.6
save("amb_wind", loopify(wind, 1.0), 0.5)
d = 6.0
t = t_(d)
room = np.sin(2 * np.pi * 50 * t) * 0.5 + np.sin(2 * np.pi * 100 * t) * 0.2 + band(noise(d), 100, 1200) * 0.15
room *= 0.8 + 0.2 * np.sin(2 * np.pi * t / d * 2)
save("amb_room", loopify(room, 0.6), 0.3)
d = 8.0                                                                # тема погони: пульс 120 уд/мин + дрон + скрежет
t = t_(d)
chase = band(sum(sweep(f, f, d, "saw") for f in (41.2, 43.65, 61.7)), 30, 500) * (0.6 + 0.4 * np.sin(2 * np.pi * 2 * t) ** 2)
for k in range(16):
    hit = sweep(75, 38, 0.22) * env(0.22, 0.002, None, 6.0) * (1.6 if k % 4 == 0 else 0.9)
    chase = mixat(chase, hit, k * 0.5)[:int(SR * d)]
    if k % 2 == 1:
        chase = mixat(chase, band(noise(0.08), 3000, 8000) * env(0.08, 0.001, None, 10.0) * 0.35, k * 0.5 + 0.25)[:int(SR * d)]
hi = band(sum(sweep(f, f * 1.01, d, "saw") for f in (622.3, 659.3, 932.3)), 500, 4000) * (0.25 + 0.2 * np.sin(2 * np.pi * t / d * 3))
save("mus_chase", loopify(chase + hi * 0.35, 0.02), 0.75)
d = 12.0                                                               # дрон для меню и тишины
t = t_(d)
dr = band(sum(sweep(f, f, d, "saw") * g for f, g in ((55, 1.0), (82.4, 0.6), (110.4, 0.5), (130.8, 0.3))), 30, 700)
dr *= 0.6 + 0.4 * np.sin(2 * np.pi * t / d) ** 2
dr += band(noise(d), 1500, 5000) * 0.03 * (1 + np.sin(2 * np.pi * t / d * 2))
save("mus_drone", loopify(dr, 1.5), 0.45)

print("SFX", len(os.listdir(OUT)), "files in", OUT)
