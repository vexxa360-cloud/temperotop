"""Trilha de marketing original (sintetizada com numpy, sem amostras de terceiros)."""
import numpy as np
SR = 44100

def _env(n, a, d):                       # ataque curto + decaimento exponencial
    t = np.arange(n)/SR
    return np.minimum(t/max(a, 1e-4), 1)*np.exp(-t/d)

def _tone(f, dur, d, harm=(1, .5, .25, .12), a=.004):
    n = int(dur*SR); t = np.arange(n)/SR
    y = sum(h*np.sin(2*np.pi*f*(i+1)*t) for i, h in enumerate(harm))
    return y*_env(n, a, d)

def _mtof(m): return 440*2**((m-69)/12)

def generate(length, bpm=116, seed=7):
    rng = np.random.default_rng(seed)
    beat = 60/bpm; N = int((length+1)*SR)
    L = np.zeros(N); R = np.zeros(N); kick_t = []
    def add(buf, y, t0, g=1.0):
        i = int(t0*SR)
        if i >= N: return
        y = y[:N-i]; buf[i:i+len(y)] += y*g
    chords = [([60, 64, 67, 72], 36), ([59, 62, 67, 71], 43), ([57, 60, 64, 69], 33), ([57, 60, 65, 69], 41)]
    bars = int(length/(4*beat))+2
    # bateria
    for b in range(bars):
        t_bar = b*4*beat
        for k in range(4):
            t = t_bar+k*beat
            if b >= 1:
                n = int(.28*SR); tt = np.arange(n)/SR
                kk = np.sin(2*np.pi*(45*tt+ 75*.045*(1-np.exp(-tt/.045)) ))*np.exp(-tt/.11)*1.0
                add(L, kk, t, .9); add(R, kk, t, .9); kick_t.append(t)
            if b >= 2 and k in (1, 3):
                n = int(.2*SR); nz = rng.standard_normal(n); nz = np.diff(nz, prepend=0)
                cl = nz*_env(n, .001, .05)
                add(L, cl, t, .16); add(R, cl, t, .16)
            if b >= 1:
                n = int(.07*SR); nz = np.diff(rng.standard_normal(n), n=2, prepend=[0, 0])
                hh = nz*_env(n, .001, .018)
                add(L, hh, t+beat/2, .13); add(R, hh, t+beat/2, .13)
    kick_t = np.array(kick_t)
    # instrumentos melodicos (com efeito "pump" do bumbo)
    M = np.zeros(N); M2 = np.zeros(N)
    for b in range(bars):
        t_bar = b*4*beat; ch, root = chords[b % 4]
        for m in ch[:3]:                                  # pad
            n = int(4*beat*SR); t = np.arange(n)/SR
            y = (np.sin(2*np.pi*_mtof(m)*t)+np.sin(2*np.pi*_mtof(m)*1.003*t))*np.minimum(t/.35, 1)*np.minimum((4*beat-t)/.3, 1)
            add(M, y, t_bar, .05)
        for s in range(8):                                # baixo em colcheias
            f = _mtof(root+(12 if s % 4 == 3 else 0))
            add(M, _tone(f, beat/2, .18, (1, .6, .3)), t_bar+s*beat/2, .30)
        for s in range(16):                               # arpejo em semicolcheias
            idx = [0, 1, 2, 3, 2, 1, 2, 3][s % 8]
            f = _mtof(ch[idx]+12)
            y = _tone(f, .35, .09, (1, .35, .12))
            pan = .35+.3*np.sin(s)
            t0 = t_bar+s*beat/4
            add(L, y, t0, .08*(1-pan)*2); add(R, y, t0, .08*pan*2)
            add(L, y, t0+beat*.75, .03); add(R, y, t0+beat*.75+.01, .03)   # eco
    # pump
    pump = np.ones(N)
    for t in kick_t:
        i = int(t*SR); n = int(.22*SR); j = min(N, i+n)
        pump[i:j] = np.minimum(pump[i:j], 1-.55*np.exp(-np.arange(j-i)/SR/.09))
    L += M*pump; R += M*pump
    out = np.stack([L, R], 1)[:int(length*SR)]
    out /= np.abs(out).max()+1e-9
    fi, fo = int(1.0*SR), int(2.5*SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]; out[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return out*0.9
