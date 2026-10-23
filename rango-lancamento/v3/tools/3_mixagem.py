"""Mixagem do comercial da Rango: narração + trilha ORIGINAL (sintetizada aqui) + efeitos, com ducking.
Uso: python3 mix.py <voz> <saida.wav>
Entradas: plan.json (tempos), cues.json (efeitos exportados da timeline), <voz>_<id>.wav (narração por cláusula)
"""
import json, sys, numpy as np, soundfile as sf
from scipy import signal

SR = 48000
voice_name, out_path = sys.argv[1], sys.argv[2]
plan = json.load(open('/tmp/prod/plan.json'))
cues = json.load(open('/tmp/prod/cues.json'))
TOTAL = plan['total']
N = int((TOTAL + 2.5) * SR)            # cauda para o reverb final
rng = np.random.default_rng(7)
t_ax = np.arange(N) / SR

def add(buf, x, t0, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf): return
    j = min(len(buf), i + len(x)); buf[i:j] += g * x[:j - i]

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def env(n, a, tau):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / tau)

# ------------------------------------------------------------------ narração
def lp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)
voice = np.zeros(N)
for cid, c in plan['clauses'].items():
    x, sr = sf.read(f'/tmp/prod/{voice_name}_{cid}.wav', dtype='float64')
    from math import gcd
    g = gcd(SR, sr); x = signal.resample_poly(x, SR // g, sr // g) if sr != SR else x
    x = hp(x, 85)
    x = x + 0.22 * (hp(x, 2500) )                                  # leve presença (inteligibilidade em caixa de notebook/celular)
    fi = int(.012 * SR); x[:fi] *= np.linspace(0, 1, fi); x[-fi:] *= np.linspace(1, 0, fi)
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    x *= 10 ** (-20 / 20) / rms                                    # cada fala em ~ -20 dBFS RMS
    add(voice, x, c['start'])
voice = np.tanh(voice * 0.9) / 0.9                                  # limitador suave

# ------------------------------------------------------------------ trilha
BPM = 100; BEAT = 60 / BPM; BAR = 4 * BEAT
S = {int(k): v for k, v in plan['scenes'].items()}
sec = lambda n: S[n]['t0']
chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
roots = [33, 29, 36, 31]
pad = np.zeros(N); arp = np.zeros(N); bass = np.zeros(N); drums = np.zeros(N)
end_music = S[7]['t0'] + 2.5                                        # momento do impacto da logo

def saw_pad(f, n):
    t = np.arange(n) / SR; y = np.zeros(n)
    for det in (-.006, 0, .006):
        for h in range(1, 9):
            if f * h > 2600: break
            y += np.sin(2 * np.pi * f * (1 + det) * h * t + h) / h
    return y / 3
nb = int(TOTAL / BAR) + 2
for b in range(nb):
    t0 = b * BAR; c = chords[b % 4]
    if t0 > end_music + 6: break
    dur = BAR + .6; n = int(dur * SR)
    y = sum(saw_pad(hz(m), n) for m in c)
    e = np.minimum(np.arange(n) / SR / .7, 1) * np.minimum((dur - np.arange(n) / SR) / .6, 1)
    pad_gain = .55 if t0 < sec(2) - .5 else 1.0
    if t0 > end_music:  # acorde final sustentado (Dó maior)
        pass
    add(pad, lp(y * e, 1500), t0, .09 * pad_gain)
# acorde final com cauda longa
fin = sum(saw_pad(hz(m), int(7 * SR)) for m in (48, 55, 60, 64, 67))
ef = np.minimum(np.arange(len(fin)) / SR / .25, 1) * np.exp(-np.arange(len(fin)) / SR / 2.6)
add(pad, lp(fin * ef, 2200), end_music, .16)

def pluck(f, dur=.7):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) + .4 * np.sin(4 * np.pi * f * t) + .15 * np.sin(6 * np.pi * f * t)
    return y * env(n, .004, .16)
pattern = [0, 1, 2, 1, 2, 1, 0, 1]
for b in range(nb):
    t0 = b * BAR; c = chords[b % 4]
    if t0 < sec(2) - .3 or t0 > end_music - .4: continue
    for i, p in enumerate(pattern):
        tt = t0 + i * BEAT / 2
        if tt > end_music - .3: break
        m = c[p] + 24 - (12 if i % 4 == 3 else 0)
        add(arp, pluck(hz(m)), tt, .12 if tt >= sec(3) else .08)
for b in range(nb):
    t0 = b * BAR
    if t0 < sec(2) or t0 > end_music - .5: continue
    for k in (0, 2):
        n = int(BEAT * 2 * SR); t = np.arange(n) / SR; f = hz(roots[b % 4])
        add(bass, (np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t)) * np.minimum(t / .01, 1) * np.exp(-t / 1.0), t0 + k * BEAT, .22)
# percussão bem discreta (cenas 3–6)
def kick():
    n = int(.35 * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * (45 * t + 65 * (1 - np.exp(-t * 28)) / 28)
    return np.sin(ph) * np.exp(-t / .09)
def hat():
    n = int(.05 * SR); return hp(rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR / .012)
K = kick(); H = hat()
t = sec(3)
while t < sec(7) - .2:
    pos = (t - sec(3)) / BEAT
    add(drums, K, t, .30 if int(round(pos)) % 2 == 0 else 0)
    add(drums, H, t + BEAT / 2, .05)
    t += BEAT
# reverb da trilha
ir_n = int(1.8 * SR); ir = rng.standard_normal((2, ir_n)) * np.exp(-np.arange(ir_n) / SR / .55)[None]
def verb(x, mix):
    return np.stack([signal.fftconvolve(x, ir[0] / 40)[:N], signal.fftconvolve(x, ir[1] / 40)[:N]]) * mix
def delay(x, tap=BEAT * .75, fb=.38, n=4):
    y = x.copy()
    for k in range(1, n + 1):
        d = int(tap * k * SR); y[d:] += x[:-d] * fb ** k
    return y
arp_d = delay(arp)
music_L = pad + arp_d + bass + drums; music_R = pad + arp_d + bass + drums
rv = verb(pad * .8 + arp_d * 1.0, .9)
music = np.stack([music_L, music_R]) + rv
music = music / (np.sqrt(np.mean(music[:, int(sec(3) * SR):int(sec(6) * SR)] ** 2)) + 1e-9) * 10 ** (-30 / 20)   # ~ -26 dBFS RMS no meio
# fade de entrada
fi = int(1.2 * SR); music[:, :fi] *= np.linspace(0, 1, fi)

# ------------------------------------------------------------------ efeitos (cues exportados da timeline)
sfx = np.zeros((2, N))
def noise_band(n, f0, f1, o=2):
    x = rng.standard_normal(n); out = np.zeros(n); seg = 16
    for i in range(seg):
        a, b = i * n // seg, (i + 1) * n // seg
        f = f0 * (f1 / f0) ** (i / (seg - 1)); sos = signal.butter(o, [f * .7, min(f * 1.4, SR / 2 - 100)], 'band', fs=SR, output='sos')
        out[a:b] = signal.sosfilt(sos, x[a:b])
    return out
def s_whoosh(d=1.0, f0=300, f1=3500):
    n = int(d * SR); e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return noise_band(n, f0, f1) * e * 2.2
def s_thud():
    n = int(.6 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (36 * t + 60 * (1 - np.exp(-t * 14)) / 14)) * np.exp(-t / .16)
def s_tick():
    n = int(.03 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2600 * t) + .5 * np.sin(2 * np.pi * 1300 * t)) * np.exp(-t / .006)
def s_pop():
    n = int(.12 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (500 * t + 1500 * t ** 2)) * np.exp(-t / .035)
def s_ping():
    n = int(.9 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1318 * t) + .55 * np.sin(2 * np.pi * 1975 * t) + .2 * np.sin(2 * np.pi * 2637 * t)) * np.exp(-t / .22) * np.minimum(t / .003, 1)
def s_impact():
    n = int(3.0 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (34 * t + 70 * (1 - np.exp(-t * 6)) / 6)) * np.exp(-t / .7)
    shim = (np.sin(2 * np.pi * 2093 * t) + .7 * np.sin(2 * np.pi * 3136 * t) + .5 * np.sin(2 * np.pi * 4186 * t)) * np.exp(-t / .9) * .12
    sw = hp(rng.standard_normal(n), 3000) * np.exp(-t / .25) * .25
    return boom * 1.2 + shim + sw
def s_riser(d):
    n = int(d * SR); t = np.arange(n) / SR; g = (t / d) ** 2.2
    return (noise_band(n, 250, 7000) * 1.8 + np.sin(2 * np.pi * (180 * t + 220 * t ** 2 / d)) * .35) * g
GAIN = {'whoosh': .16, 'thud': .40, 'tick': .24, 'pop': .18, 'ping': .16, 'impact': .38, 'riser': .20}
for c in cues:
    ty, t0 = c['type'], c['t']
    x = {'whoosh': lambda: s_whoosh(c.get('d', 1.0)), 'thud': s_thud, 'tick': s_tick, 'pop': s_pop, 'ping': s_ping,
         'impact': s_impact, 'riser': lambda: s_riser(c.get('d', 2.4))}[ty]()
    g = GAIN[ty] * c.get('g', 1.0); pan = c.get('pan', 0.0)
    add(sfx[0], x, t0, g * (1 - max(pan, 0))); add(sfx[1], x, t0, g * (1 + min(pan, 0)))

# ------------------------------------------------------------------ ducking
v_abs = np.abs(voice)
w = int(.05 * SR); lev = np.convolve(v_abs, np.ones(w) / w, 'same')
gate = (lev > 10 ** (-42 / 20)).astype(float)
def one_pole(x, att, rel):
    out = np.zeros_like(x); y = 0.0; ka = np.exp(-1 / (att * SR)); kr = np.exp(-1 / (rel * SR))
    # vetorizado por blocos para rapidez
    for i in range(0, len(x), 480):
        blk = x[i:i + 480].max()
        k = ka if blk > y else kr; y = blk + (y - blk) * k; out[i:i + 480] = y
    return out
g_s = one_pole(gate, .06, .45)
duck_db = -11.0
duck = 10 ** (duck_db / 20 * g_s)
music_d = music * duck[None]
sfx_d = sfx * (10 ** (-3 / 20 * g_s))[None]

# ------------------------------------------------------------------ master
mix = np.stack([voice, voice]) + music_d + sfx_d
peak = np.abs(mix).max(); print('pico pré-master', round(20 * np.log10(peak), 1), 'dBFS')
sf.write(out_path.replace('.wav', '_mix_raw.wav'), mix.T.astype(np.float32), SR)
# métricas objetivas voz x música durante a fala
sp = gate > .5
rv_ = np.sqrt(np.mean(voice[sp] ** 2)); rm_ = np.sqrt(np.mean(music_d[:, sp] ** 2)); rs_ = np.sqrt(np.mean(sfx_d[:, sp] ** 2))
print(f'durante a fala: voz {20*np.log10(rv_):.1f} dBFS | música {20*np.log10(rm_):.1f} dBFS | efeitos {20*np.log10(rs_+1e-9):.1f} dBFS | voz-música {20*np.log10(rv_/rm_):.1f} dB')
sf.write('/tmp/prod/stem_voice.wav', voice.astype(np.float32), SR)
sf.write('/tmp/prod/stem_music.wav', music_d.T.astype(np.float32), SR)
json.dump({'voice_minus_music_db': float(20 * np.log10(rv_ / rm_))}, open('/tmp/prod/mix_metrics.json', 'w'))
