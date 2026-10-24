"""Personagens 3D (busto atras de balcao) por campos de distancia + marching cubes — sem assets externos.
Cada pessoa vira varias malhas, uma por material: pele, cabelo, camisa, avental, labios, olhos, iris, sobrancelhas, dentes/boca."""
import math
import numpy as np
from skimage.measure import marching_cubes

def smin(a, b, k):
    h = np.clip(0.5+0.5*(b-a)/k, 0, 1); return b*(1-h)+a*h-k*h*(1-h)
def smax(a, b, k): return -smin(-a, -b, k)

class G:
    """grade de amostragem local (metros)."""
    def __init__(s, lo, hi, h):
        s.h = h; s.lo = np.array(lo, float)
        ax = [np.arange(l, u, h) for l, u in zip(lo, hi)]
        s.X, s.Y, s.Z = np.meshgrid(*ax, indexing='ij'); s.P = np.stack([s.X, s.Y, s.Z], -1)
    def ell(s, c, r, rot=None):
        p = s.P-np.array(c)
        if rot is not None: p = p@np.asarray(rot).T
        q = p/np.array(r); return (np.sqrt((q**2).sum(-1))-1.0)*min(r)*0.9
    def cap(s, a, b, ra, rb=None):
        rb = ra if rb is None else rb; a = np.array(a, float); b = np.array(b, float); ba = b-a; pa = s.P-a
        t = np.clip((pa@ba)/(ba@ba), 0, 1); return np.linalg.norm(pa-t[..., None]*ba, axis=-1)-(ra+(rb-ra)*t)
    def box(s, c, hs, r=0.01):
        q = np.abs(s.P-np.array(c))-np.array(hs)+r
        return np.linalg.norm(np.maximum(q, 0), axis=-1)+np.minimum(q.max(-1), 0)-r
    def mesh(s, d):
        if d.min() > 0 or d.max() < 0: return None
        v, f, n, _ = marching_cubes(d, 0.0, spacing=(s.h, s.h, s.h)); return v+s.lo, f

def ik(sh, tgt, l1, l2, hint):
    sh, tgt, hint = map(lambda v: np.array(v, float), (sh, tgt, hint)); d = tgt-sh; L = np.linalg.norm(d)
    L = min(L, l1+l2-1e-4); u = d/np.linalg.norm(d); a = (l1*l1-l2*l2+L*L)/(2*L); hgt = math.sqrt(max(l1*l1-a*a, 1e-6))
    h = hint-np.dot(hint, u)*u; h = h/np.linalg.norm(h); return sh+u*a+h*hgt, sh+u*L

def person(spec):
    """spec: dict(x, skin_id, hair ('short'|'long'|'bun'|'cap'), beard, shirt, mood ('calm'|'stress'),
       lwrist, rwrist (mundo), lhold/rhold, yaw, height). Retorna {material: (v, f)}."""
    x0 = spec.get('x', 0.0); yaw = spec.get('yaw', 0.0); sc = spec.get('scale', 1.0)
    lo = (x0-0.62, -0.62, 0.98); hi = (x0+0.62, 0.30, 1.90); h = 0.0052
    g = G(lo, hi, h); out = {}
    def T(p):                                            # coordenadas locais da pessoa (origem no pe, centro em x0)
        return np.array([x0+(p[0]*sc), p[1]*sc, p[2]*sc], float)
    sh_l, sh_r = T((-0.205, 0.0, 1.455)), T((0.205, 0.0, 1.455))
    mood = spec.get('mood', 'calm')
    # --- pele: cabeca, pescoco, antebracos, maos
    hc = T((0, 0.0, 1.665))
    head = g.ell(hc, (0.083*sc, 0.098*sc, 0.113*sc))
    head = smin(head, g.ell(T((0, -0.012, 1.612)), (0.068*sc, 0.082*sc, 0.072*sc)), 0.03*sc)          # mandibula
    head = smin(head, g.ell(T((0, -0.1, 1.645)), (0.016*sc, 0.022*sc, 0.030*sc)), 0.02*sc)            # nariz
    head = smin(head, g.ell(T((0, -0.108, 1.627)), (0.019*sc, 0.012*sc, 0.012*sc)), 0.012*sc)        # ponta do nariz
    for sx in (-1, 1):
        head = smin(head, g.ell(T((sx*0.084, 0.004, 1.662)), (0.010*sc, 0.020*sc, 0.031*sc)), 0.01*sc)  # orelhas
        head = smin(head, g.ell(T((sx*0.045, -0.083, 1.628)), (0.03*sc, 0.026*sc, 0.026*sc)), 0.03*sc)   # macas do rosto
        head = smax(head, -g.ell(T((sx*0.034, -0.092, 1.678)), (0.017*sc, 0.012*sc, 0.011*sc)), 0.012*sc)  # orbitas
    head = smin(head, g.ell(T((0, -0.096, 1.598)), (0.03*sc, 0.016*sc, 0.012*sc)), 0.01*sc)            # labio superior volume
    head = smax(head, -g.ell(T((0, -0.107, 1.600)), (0.026*sc, 0.007*sc, 0.0045*sc)), 0.006*sc)        # boca (sulco)
    neck = g.cap(T((0, 0.004, 1.50)), T((0, 0.004, 1.585)), 0.047*sc)
    skin = smin(head, neck, 0.02*sc)
    arms_info = []
    for side, shd in ((-1, sh_l), (1, sh_r)):
        w = np.array(spec['lwrist' if side < 0 else 'rwrist'], float)
        el, wr = ik(shd, w, 0.30*sc, 0.27*sc, (side*0.5, 0.9, -0.9))
        arms_info.append((shd, el, wr))
        skin = smin(skin, g.cap(el, wr, 0.033*sc, 0.026*sc), 0.01)
        d = (wr-el)/np.linalg.norm(wr-el); tip = wr+d*0.075*sc
        skin = smin(skin, g.cap(wr, tip, 0.027*sc, 0.020*sc), 0.012)                                  # mao
        skin = smin(skin, g.cap(wr+np.array([-side*0.01, -0.01, 0.01]), wr+d*0.05*sc+np.array([-side*0.035, -0.02, 0.02]), 0.014*sc, 0.011*sc), 0.01)  # polegar
    out['pele'] = g.mesh(skin)
    # --- camisa (torso + mangas ate o cotovelo) e avental
    chest = g.ell(T((0, 0.0, 1.30)), (0.205*sc, 0.125*sc, 0.215*sc)); chest = smin(chest, g.ell(T((0, 0.0, 1.10)), (0.185*sc, 0.12*sc, 0.2*sc)), 0.08)
    shoulders = g.cap(sh_l, sh_r, 0.058*sc); shirt = smin(chest, shoulders, 0.06)
    shirt = smax(shirt, -g.ell(T((0, 0.0, 1.535)), (0.052*sc, 0.058*sc, 0.05*sc)), 0.015)             # gola aberta
    for shd, el, wr in arms_info:
        mid = shd+(el-shd)*1.04
        shirt = smin(shirt, g.cap(shd, mid, 0.056*sc, 0.050*sc), 0.025)
        shirt = smin(shirt, g.cap(mid, el+(wr-el)*0.2, 0.05*sc, 0.046*sc), 0.012)
    out['camisa'] = g.mesh(shirt)
    if spec.get('apron', True):
        apron = g.box(T((0, -0.127, 1.15)), (0.125*sc, 0.011*sc, 0.17*sc), 0.02)
        apron = smax(apron, -(g.P[..., 2]-T((0, 0, 1.385))[2]) * -1, 0.0) if False else apron
        out['avental'] = g.mesh(apron)
    # --- cabelo / barba / bone
    style = spec.get('hair', 'short')
    if style in ('short', 'long', 'bun'):
        shell = g.ell(T((0, 0.012, 1.676)), (0.092*sc, 0.106*sc, 0.121*sc))
        t = np.clip((g.P[..., 1]-T((0, -0.07, 0))[1])/(0.14*sc), 0, 1)
        front = T((0, 0, 1.714))[2]; back = T((0, 0, 1.585))[2] if style == 'short' else T((0, 0, 1.55))[2]
        plane = front*(1-t)+back*t
        shell = smax(shell, plane-g.P[..., 2], 0.012)
        if style == 'short': shell = smax(shell, -(np.abs(g.P[..., 0]-x0)-0.082*sc)*-1*0 + (T((0, 0, 1.652))[2]-g.P[..., 2])*(np.abs(g.P[..., 0]-x0) > 0.07*sc), 0.0) if False else shell
        if style == 'long':
            for sx in (-1, 1): shell = smin(shell, g.cap(T((sx*0.07, 0.02, 1.64)), T((sx*0.085, 0.045, 1.43)), 0.034*sc, 0.026*sc), 0.02)
            shell = smin(shell, g.ell(T((0, 0.075, 1.56)), (0.085*sc, 0.04*sc, 0.15*sc)), 0.03)
        if style == 'bun': shell = smin(shell, g.ell(T((0, 0.05, 1.79)), (0.04*sc, 0.04*sc, 0.034*sc)), 0.02)
        out['cabelo'] = g.mesh(shell)
    elif style == 'cap':                                                                                  # bone
        cap_ = g.ell(T((0, 0.01, 1.69)), (0.094*sc, 0.108*sc, 0.1*sc)); cap_ = smax(cap_, T((0, 0, 1.69))[2]-0.02-g.P[..., 2]+0.02-0.02, 0.01)
        cap_ = smax(cap_, (T((0, 0, 1.652))[2]-g.P[..., 2]), 0.01); brim = g.box(T((0, -0.12, 1.665)), (0.06*sc, 0.04*sc, 0.005*sc), 0.004)
        out['cabelo'] = g.mesh(smin(cap_, brim, 0.01))
        top = g.ell(T((0, 0.01, 1.66)), (0.082*sc, 0.098*sc, 0.113*sc)); out['cabelo2'] = None
    if spec.get('beard'):
        jaw = g.ell(T((0, -0.01, 1.6)), (0.074*sc, 0.088*sc, 0.082*sc)); b = jaw
        b = smax(b, g.P[..., 2]-T((0, 0, 1.628))[2], 0.01); b = smax(b, g.P[..., 1]-T((0, 0.005, 0))[1], 0.01)
        b = smax(b, -g.ell(T((0, -0.1, 1.607)), (0.03*sc, 0.02*sc, 0.016*sc)), 0.008)
        out['barba'] = g.mesh(b)
    # --- rosto: olhos, iris, sobrancelhas, labios
    eyes, iris, brows = None, None, None
    ge = G((x0-0.07, -0.14, 1.58), (x0+0.07, -0.05, 1.76), 0.0016)
    e = None; ir = None
    for sx in (-1, 1):
        s_ = ge.ell(T((sx*0.034, -0.0905, 1.678)), (0.0108*sc, 0.0098*sc, 0.0098*sc)); e = s_ if e is None else np.minimum(e, s_)
        i_ = ge.ell(T((sx*0.034, -0.0985, 1.678)), (0.0062*sc, 0.0035*sc, 0.0062*sc)); ir = i_ if ir is None else np.minimum(ir, i_)
    out['olhos'] = ge.mesh(e); out['iris'] = ge.mesh(ir)
    gb = G((x0-0.08, -0.14, 1.66), (x0+0.08, -0.05, 1.76), 0.0016); bw = None
    tilt = 0.012 if mood == 'stress' else 0.0
    for sx in (-1, 1):
        b_ = gb.cap(T((sx*0.016, -0.1, 1.706+tilt)), T((sx*0.056, -0.088, 1.714-tilt)), 0.0042*sc, 0.0026*sc); bw = b_ if bw is None else np.minimum(bw, b_)
    out['sobrancelhas'] = gb.mesh(bw)
    gl = G((x0-0.05, -0.14, 1.57), (x0+0.05, -0.06, 1.64), 0.0014)
    sm = 0.007 if mood == 'calm' else -0.001
    lips = gl.ell(T((0, -0.1085, 1.6015)), (0.0215*sc, 0.0062*sc, 0.0052*sc)); lips = smin(lips, gl.ell(T((0, -0.108, 1.5925)), (0.0185*sc, 0.0062*sc, 0.0062*sc)), 0.004)
    for sx in (-1, 1): lips = smin(lips, gl.ell(T((sx*0.026, -0.1045, 1.603+sm)), (0.0075*sc, 0.005*sc, 0.0042*sc)), 0.004)
    out['labios'] = gl.mesh(lips)
    return {k: v for k, v in out.items() if v}
