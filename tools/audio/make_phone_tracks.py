# -*- coding: utf-8 -*-
# «Скачанные» песни в телефоне Юрчика (плеер «Музыка», YUR-34): четыре коротких трека-заглушки,
# синтезированные из простых волн, — свои мелодии, без чужих записей. Позже их можно заменить настоящими
# песнями: положить файлы с теми же именами в assets/audio/phone_music/ (названия — в phone_screen.gd, TRACKS).
#
# Запуск (нужен numpy; он есть в Python из поставки Blender):
#   "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe" tools/audio/make_phone_tracks.py
# Результат: assets/audio/phone_music/*.wav (моно, 22050 Гц, 16 бит).
import os, wave
import numpy as np

SR = 22050
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "audio", "phone_music"))

MINOR = [0, 2, 3, 5, 7, 8, 10]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def pulse(f, n, duty=0.25, vib=0.0):
    t = np.arange(n) / SR
    ph = np.cumsum(np.full(n, f) * (1 + vib * np.sin(2 * np.pi * 5.5 * t))) / SR
    return np.where((ph % 1.0) < duty, 1.0, -1.0)


def tri(f, n):
    ph = (np.arange(n) * f / SR) % 1.0
    return 4 * np.abs(ph - 0.5) - 1


def adsr(n, a=0.01, d=0.08, s=0.6, r=0.05):
    e = np.full(n, s)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = min(na, n)
    e[:na] = np.linspace(0, 1, na)
    nd = min(nd, n - na)
    e[na:na + nd] = np.linspace(1, s, nd)
    nr = min(nr, n)
    e[n - nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, k):
    """Простейший однополюсный фильтр: k ближе к 0 — глуше."""
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc)
        y[i] = acc
    return y


def drums(n_steps, step, rng, style):
    out = np.zeros(n_steps * step)
    kick_n = int(0.18 * SR)
    t = np.arange(kick_n) / SR
    kick = np.sin(2 * np.pi * np.cumsum(60 + 110 * np.exp(-t * 30)) / SR) * np.exp(-t * 14)
    sn_n = int(0.16 * SR)
    snare = rng.standard_normal(sn_n) * np.exp(-np.arange(sn_n) / SR * 22) * 0.55
    hat_n = int(0.04 * SR)
    hat = np.diff(rng.standard_normal(hat_n + 1)) * np.exp(-np.arange(hat_n) / SR * 90) * 0.18
    for s in range(n_steps):
        pos = s * step
        b = s % 16
        if b in style["kick"]:
            out[pos:pos + kick_n] += kick[:len(out) - pos]
        if b in style["snare"]:
            out[pos:pos + sn_n] += snare[:len(out) - pos]
        if s % 2 == 0 or style["hat16"]:
            out[pos:pos + hat_n] += hat[:len(out) - pos]
    return out


def motif(rng, chord_tones, steps=16, rest=0.25):
    """Двухтактовый мотив: случайная прогулка по ладу, на сильных долях — звуки аккорда."""
    notes = []
    cur = rng.choice(chord_tones)
    i = 0
    while i < steps:
        ln = int(rng.choice([1, 2, 2, 3, 4], p=[0.25, 0.35, 0.15, 0.1, 0.15]))
        ln = min(ln, steps - i)
        if rng.random() < rest and i % 4 != 0:
            notes.append((None, ln))
        else:
            if i % 4 == 0:
                cur = int(rng.choice(chord_tones))
            else:
                cur = int(np.clip(cur + rng.choice([-2, -1, 1, 1, 2]), 0, 11))
            notes.append((cur, ln))
        i += ln
    return notes


def deg_to_midi(root, deg, octave=0):
    return root + 12 * (deg // 7 + octave) + MINOR[deg % 7]


def render(spec):
    rng = np.random.default_rng(spec["seed"])
    bpm = spec["bpm"]
    step = int(SR * 60 / bpm / 4)           # шестнадцатая
    prog = spec["prog"]                      # ступени аккордов, по такту
    bars = spec["bars"]
    n = bars * 16 * step
    lead = np.zeros(n)
    bass = np.zeros(n)
    arp = np.zeros(n)
    root = spec["root"]
    # мотивы A и B — по два такта; форма A A B A, повторяется
    motifs = {}
    for k in "AB":
        ct = [prog[0], prog[0] + 2, prog[0] + 4, prog[0] + 7]
        motifs[k] = motif(rng, ct, 32, spec["rest"])
    form = spec["form"]
    for sec, k in enumerate(form):
        start = sec * 2 * 16 * step
        if start >= n:
            break
        pos = start
        shift = 0 if sec % 4 != 1 else 1      # второй проход A — на ступень выше
        for deg, ln in motifs[k]:
            m = ln * step
            if deg is not None and pos + m <= n:
                f = hz(deg_to_midi(root, deg + shift, 1))
                lead[pos:pos + m] += pulse(f, m, spec["duty"], 0.006) * adsr(m, 0.005, 0.1, 0.5, 0.03)
            pos += m
    for bar in range(bars):
        d = prog[bar % len(prog)]
        base = bar * 16 * step
        for s in range(16):
            pos = base + s * step
            # бас: восьмые, корень и квинта
            if s % 2 == 0:
                m = 2 * step
                deg = d if s % 8 != 6 else d + 4
                bass[pos:pos + m] += tri(hz(deg_to_midi(root, deg, -1)), m) * adsr(m, 0.003, 0.05, 0.7, 0.02)
            # арпеджио аккорда шестнадцатыми, тихо
            if spec["arp"]:
                deg = d + [0, 2, 4, 7][s % 4]
                arp[pos:pos + step] += pulse(hz(deg_to_midi(root, deg, 1)), step, 0.125) * adsr(step, 0.002, 0.03, 0.3, 0.01)
    dr = drums(bars * 16, step, rng, spec["drums"])
    mix = 0.30 * lead + 0.42 * bass + 0.10 * arp + 0.55 * dr
    mix = lowpass(mix, spec["lp"])
    # вступление и затухание
    fade = int(1.5 * SR)
    mix[:int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix * 1.4)
    mix /= np.max(np.abs(mix)) + 1e-9
    return (mix * 0.85 * 32767).astype(np.int16)


TRACKS = {
    # файл: параметры
    "pyatietazhki": dict(seed=11, bpm=124, root=57, prog=[0, 5, 2, 6], bars=24, form="AABAAABA" * 2, rest=0.2,
                         duty=0.25, arp=True, lp=0.55,
                         drums=dict(kick=[0, 6, 8], snare=[4, 12], hat16=False)),
    "posledniaia_elektrichka": dict(seed=23, bpm=100, root=55, prog=[0, 3, 4, 0], bars=20, form="ABABAB" * 2, rest=0.35,
                                    duty=0.5, arp=True, lp=0.35,
                                    drums=dict(kick=[0, 10], snare=[8], hat16=False)),
    "sneg_na_provodakh": dict(seed=37, bpm=84, root=60, prog=[0, 5, 3, 4], bars=16, form="AABA" * 3, rest=0.4,
                              duty=0.125, arp=False, lp=0.25,
                              drums=dict(kick=[0], snare=[12], hat16=False)),
    "kvartal": dict(seed=58, bpm=138, root=52, prog=[0, 0, 5, 6], bars=28, form="AABB" * 4, rest=0.15,
                    duty=0.25, arp=True, lp=0.6,
                    drums=dict(kick=[0, 4, 8, 12], snare=[4, 12], hat16=True)),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, spec in TRACKS.items():
        data = render(spec)
        path = os.path.join(OUT, name + ".wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(data.tobytes())
        print(name, "%.1f s" % (len(data) / SR))


if __name__ == "__main__":
    main()
