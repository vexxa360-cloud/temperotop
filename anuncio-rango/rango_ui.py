"""Compositor da interface real do Rango (menu, destaque azul, rolagem) — extraido de rango-video/rango_video.py."""
"""Monta o video de navegacao do Rango a partir dos prints reais (compositor numpy/PIL -> ffmpeg)."""
import subprocess, sys, math
import numpy as np
from PIL import Image, ImageDraw

import os
I = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rango-video', 'prints') + '/'
W, H, FPS = 746, 1600, 30
TOP, BOT = 162, 1570                      # area abaixo da barra do navegador / acima da barra de gestos
SCRIM_C, SCRIM_A = np.array([3, 18, 38], float), 0.55
PILL = np.array([191, 219, 254], float)   # azul claro do destaque (pedido do usuario)
INK = np.array([3, 19, 35], float)        # tinta escura sobre o azul claro (cor do fundo do menu)
BG = np.array([2, 19, 35], float)

def load(n): return np.array(Image.open(f'{I}{n}.png').convert('RGB'))
P = {n: load(n) for n in range(1, 21)}
P21 = load(21)
P[8][52:162] = P[11][52:162]   # a sobreposicao de outro app nao faz parte do Rango

# ---------- menu limpo (sem destaque) montado com trechos reais dos prints 1 e 4 ----------
a4, a1 = P[4].astype(np.uint8), P[1].astype(np.uint8)
T = np.zeros((1198, 490, 3), np.uint8)               # lista rolavel, coords do print 4 (y-162)
T[:] = a4[162:1360, :490]
T[466-162:557-162] = a1[356:447, :490]               # linha "Lancar Venda" inativa (print 1)
T[1033:1198] = a1[1085:1250, :490]                   # Produtos e Estoque / Visao Geral (print 1)
from PIL import ImageFont
T = np.concatenate([T, np.tile(np.array([2, 19, 35], np.uint8), (362, 490, 1))], 0)
_f = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Medium.otf', 28)
def _text_row(label, cy):
    im = Image.fromarray(T); d = ImageDraw.Draw(im)
    bx = d.textbbox((0, 0), label, font=_f)
    d.text((51-bx[0], cy+2-(bx[3]-bx[1])//2-bx[1]), label, font=_f, fill=(201, 218, 238))
    return np.array(im)
for _lbl, _cy in [('Funcionários', 1236), ('Relatórios', 1321), ('CMV e Lucro', 1406), ('Perdas e Consumo', 1491)]:
    T = _text_row(_lbl, _cy)
FOOT = a4[1260:1570, :490]                           # rodape fixo: usuario + Sair (print 4)
VIEW_H = 1260 - TOP                                  # 1098
ROWS = dict(dashboard=264, lancar=349, pedidos=503, entregas=588, whatsapp=673,
            historico=758, receitas=912, produtos=1066, visao=1151,
            funcionarios=1236, relatorios=1321, cmv=1406, perdas=1491)

def pill_mask(h=79, w=434, r=22):
    m = Image.new('L', (w*4, h*4), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w*4-1, h*4-1], r*4, fill=255)
    return np.array(m.resize((w, h), Image.LANCZOS), float)/255
PM = pill_mask()
ACTIVE = {}
for k, c in ROWS.items():            # linha ativa: fundo azul claro + glifos reais recoloridos (sem redesenhar)
    y0 = c - 40
    crop = T[y0:y0+79, 27:461].astype(float)
    d = np.abs(crop - BG).max(axis=2)
    al = np.clip(d/150, 0, 1)[..., None]
    rgb = PILL*(1-al) + INK*al
    ACTIVE[k] = (rgb, PM)

BADGE = P21[665-19:665+19, 419-19:419+19].astype(float)
yy, xx = np.mgrid[-19:19, -19:19]; BADGE_M = np.clip(18.5 - np.hypot(xx+.5, yy+.5), 0, 1)
BANNER = P21[185:488, 24:722].astype(float)
bm = Image.new('L', (698*3, 303*3), 0); ImageDraw.Draw(bm).rounded_rectangle([0, 0, 698*3-1, 303*3-1], 44*3, fill=255)
BANNER_M = np.array(bm.resize((698, 303), Image.LANCZOS), float)/255

def panel(ms, act, badge=False):
    """act: lista de (linha, alpha). Retorna painel 1408x490."""
    ms = int(round(ms))
    v = T[ms:ms+VIEW_H].astype(float).copy()
    for k, a in act:
        rgb, m = ACTIVE[k]; c = ROWS[k] - ms - 40
        if c < 0 or c + 79 > VIEW_H: continue
        mm = (m*a)[..., None]
        v[c:c+79, 27:461] = v[c:c+79, 27:461]*(1-mm) + rgb*mm
        if badge and k == 'pedidos':
            cy, cx = c + 40 - 19, 419 - 19
            mb = (BADGE_M*a)[..., None]
            v[cy:cy+38, cx:cx+38] = v[cy:cy+38, cx:cx+38]*(1-mb) + BADGE*mb
    return np.concatenate([v, FOOT.astype(float)], 0)

def ease(t): t = min(max(t, 0), 1); return t*t*(3-2*t)
def eo(t): t = min(max(t, 0), 1); return 1-(1-t)**3

# ---------- dedo (indicador de toque) ----------
def finger_tile(s):
    S = 4; R = 40
    im = Image.new('RGBA', (R*2*S, R*2*S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    r = R*s*S; c = R*S
    d.ellipse([c-r, c-r, c+r, c+r], fill=(120, 130, 150, 120), outline=(255, 255, 255, 220), width=int(3*S))
    return im.resize((R*2, R*2), Image.LANCZOS)

# ---------- rolagem real (folha continua A+B) ----------
class Scroll:
    def __init__(s, A, B, dist, hide=False, bstart=None):
        s.A, s.B, s.dist, s.hide = A, B, dist, hide
        bs = bstart if bstart is not None else BOT - dist
        s.sheet = np.concatenate([A[265:BOT], B[bs:BOT]], 0)
    def at(s, p):
        p = min(max(p, 0), 1)
        if p <= 0: return s.A
        if p >= 1: return s.B
        o = int(round(s.dist*p)); f = s.A.copy()
        if s.hide:
            h = int(round(109*ease(p/0.4)))
            f[52:265-h] = s.A[52+h:265]
            f[265-h:BOT] = s.sheet[o:o+(BOT-265+h)]
            f[BOT:] = s.A[BOT:]
        else:
            f[265:BOT] = s.sheet[o:o+(BOT-265)]
        return f
SC_DASH = Scroll(P[2], P[3], 1305, hide=True, bstart=156)
SC_LANC = Scroll(P[5], P[6], 1203)
SC_PED = Scroll(P[19], P[18], 720)

# ---------- compositor ----------
def render(base, scrim=0.0, menu=None, banner=None, finger=None):
    f = base.astype(float)
    if scrim > 0:
        f[TOP:BOT] = f[TOP:BOT]*(1-SCRIM_A*scrim) + SCRIM_C*(SCRIM_A*scrim)
    if menu is not None:
        pan = panel(menu['ms'], menu['act'], menu.get('badge', False))
        vis = int(round(490*menu['prog']))
        if vis > 0:
            f[TOP:BOT, :vis] = pan[:, 490-vis:]
    if banner is not None:
        y = int(round(185 - 330*(1-banner)))
        for yy_ in range(303):
            ty = y + yy_
            if ty < TOP or ty >= BOT: continue
            m = BANNER_M[yy_][:, None]
            f[ty, 24:722] = f[ty, 24:722]*(1-m) + BANNER[yy_]*m
    img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
    if finger:
        x, y, s = finger
        t = finger_tile(s); img.paste(t, (int(x-40), int(y-40)), t)
    return np.array(img)

