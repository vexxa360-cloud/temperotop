"""Monta o video de navegacao do Rango a partir dos prints reais (compositor numpy/PIL -> ffmpeg)."""
import subprocess, sys, math
import numpy as np
from PIL import Image, ImageDraw

import os
I = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prints') + '/'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'rango_navegacao.mp4'
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

# ---------- linha do tempo ----------
frames_written = 0
import json
DUR = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'narracao', 'duracoes.json')))
cues = []; narr_end = 0.0; last = [None]
def now(): return frames_written/FPS
def pad():
    while now() < narr_end: emit(last[0])
def say(key):
    """espera a fala anterior terminar (segurando o quadro) e comeca a proxima agora."""
    global narr_end
    pad(); cues.append((key, now())); narr_end = now() + DUR[key] + 0.3
ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                       '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                       '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
def emit(fr):
    global frames_written
    ff.stdin.write(fr.tobytes()); frames_written += 1; last[0] = fr
def n(sec): return max(1, int(round(sec*FPS)))

class Fing:
    pos = (600.0, 1200.0)
fg = Fing()
def move(to, sec):
    a = fg.pos; k = n(sec)
    for i in range(1, k+1):
        t = ease(i/k); yield (a[0]+(to[0]-a[0])*t, a[1]+(to[1]-a[1])*t, 1.0)
    fg.pos = to
def press(sec=0.2):
    k = n(sec)
    for i in range(k):
        t = i/(k-1) if k > 1 else 1
        yield (fg.pos[0], fg.pos[1], 1.0 - 0.35*math.sin(math.pi*t))

HAMB = (54, 212)
state = dict(page='dash', scroll=0.0)

def hold(base, sec, finger=True, **kw):
    for _ in range(n(sec)): emit(render(base, finger=(fg.pos+(1.0,)) if finger else None, **kw))

def show_finger_move(base, to, sec, **kw):
    for fpos in move(to, sec): emit(render(base, finger=fpos, **kw))

def tap(base, **kw):
    for fpos in press(): emit(render(base, finger=fpos, **kw))

def menu_open(base, active, ms=0.0, badge=False):
    k = n(0.3)
    for i in range(1, k+1):
        pr = eo(i/k)
        emit(render(base, scrim=pr, menu=dict(prog=pr, ms=ms, act=[(active, 1)], badge=badge)))

def menu_close(base, active, ms=0.0, badge=False, finger=False):
    k = n(0.3)
    for i in range(1, k+1):
        pr = 1 - ease(i/k)
        emit(render(base, scrim=pr, menu=dict(prog=pr, ms=ms, act=[(active, 1)], badge=badge)))

def menu_scroll(base, active, ms0, ms1, sec=0.6):
    k = n(sec)
    for i in range(1, k+1):
        m = ms0 + (ms1-ms0)*ease(i/k)
        emit(render(base, scrim=1, menu=dict(prog=1, ms=m, act=[(active, 1)])))

def navigate(src_base, src_key, dst_base, dst_key, ms_src=0.0, ms_dst=0.0, extra=None, sweep=()):
    """toca no menu, abre, escolhe o item, destaque azul acompanha, fecha. extra: callback entre selecao e fechamento."""
    # 1) dedo vai ao hamburger e toca
    show_finger_move(src_base, HAMB, 0.35)
    tap(src_base)
    # 2) menu abre com o item da secao atual destacado
    menu_open(src_base, src_key, ms=0.0)
    fgpos = fg.pos
    for _ in range(n(0.25)): emit(render(src_base, scrim=1, menu=dict(prog=1, ms=0, act=[(src_key, 1)]), finger=None))
    # rolar o menu se o destino exige
    if ms_dst:
        fg.pos = (300.0, 1000.0)
        for i in range(n(0.1)): emit(render(src_base, scrim=1, menu=dict(prog=1, ms=0, act=[(src_key, 1)]), finger=fg.pos+(1.0,)))
        menu_scroll(src_base, src_key, 0, ms_dst, 0.5)
        for _ in range(n(0.12)): emit(render(src_base, scrim=1, menu=dict(prog=1, ms=ms_dst, act=[(src_key, 1)])))
        ms_cur = ms_dst
    else:
        ms_cur = 0.0
        fg.pos = (400.0, 1000.0)
    for sk in sweep:                                     # aponta itens do menu que passam pelo caminho
        ys = ROWS[sk] - ms_cur + TOP; a0 = fg.pos; k = n(0.38)
        for i in range(1, k+1):
            t = ease(i/k); pos = (a0[0]+(244-a0[0])*t, a0[1]+(ys-a0[1])*t, 1.0)
            emit(render(src_base, scrim=1, menu=dict(prog=1, ms=ms_cur, act=[(src_key, 1)]), finger=pos))
        fg.pos = (244.0, float(ys))
        for _ in range(n(0.35)): emit(render(src_base, scrim=1, menu=dict(prog=1, ms=ms_cur, act=[(src_key, 1)]), finger=fg.pos+(1.0,)))
    # 3) dedo ate o item e toque
    y_item = ROWS[dst_key] - ms_cur + TOP
    mnu = lambda a, b=None: dict(prog=1, ms=ms_cur, act=a)
    k = n(0.4); a0 = fg.pos
    for i in range(1, k+1):
        t = ease(i/k); pos = (a0[0]+(244-a0[0])*t, a0[1]+(y_item-a0[1])*t, 1.0)
        emit(render(src_base, scrim=1, menu=mnu([(src_key, 1)]), finger=pos))
    fg.pos = (244.0, float(y_item))
    for fpos in press(0.2): emit(render(src_base, scrim=1, menu=mnu([(src_key, 1)]), finger=fpos))
    # 4) destaque migra para o novo item e o fundo passa a ser a nova secao
    k = n(0.2)
    for i in range(1, k+1):
        a = ease(i/k)
        act = [(src_key, 1-a), (dst_key, a)] if src_key != dst_key else [(dst_key, 1)]
        emit(render(dst_base, scrim=1, menu=mnu(act), finger=(fg.pos+(1.0,))))
    for _ in range(n(0.12)): emit(render(dst_base, scrim=1, menu=mnu([(dst_key, 1)])))
    if extra: extra(dst_base, ms_cur)
    else: menu_close(dst_base, dst_key, ms=ms_cur)
    fg.pos = (600.0, 1250.0)

def crossfade(a, b, sec):
    k = n(sec)
    for i in range(1, k+1):
        t = ease(i/k); emit(np.clip(a.astype(float)*(1-t)+b.astype(float)*t, 0, 255).astype(np.uint8))


def modal(page, shot, y0, up, sec):
    """Modal (linhas y0..BOT do print `shot`) sobe ou desce; a pagina atras escurece/clareia."""
    k = n(sec)
    for i in range(1, k+1):
        t = eo(i/k) if up else ease(i/k)
        pr = t if up else 1-t                       # 0 = fechado, 1 = aberto
        f = page.astype(float)
        f[TOP:BOT] = f[TOP:BOT]*(1-SCRIM_A*pr) + SCRIM_C*(SCRIM_A*pr)
        w = ease((pr-0.88)/0.12)                                   # a parte de cima converge para o fundo do proprio print
        f[TOP:y0] = f[TOP:y0]*(1-w) + shot[TOP:y0].astype(float)*w
        off = int((BOT-y0)*(1-pr))
        f[y0+off:BOT] = shot[y0:BOT-off].astype(float)
        emit(np.clip(f, 0, 255).astype(np.uint8))

def scroll_anim(sc, p0, p1, sec, finger=None):
    k = n(sec)
    for i in range(1, k+1):
        p = p0 + (p1-p0)*ease(i/k)
        emit(render(sc.at(p), finger=finger))

# =============== ROTEIRO ===============
SC_REL = Scroll(P[10], P[9], 1353)
def mhold(base, key, sec):
    for _ in range(n(sec)): emit(render(base, scrim=1, menu=dict(prog=1, ms=0, act=[(key, 1)])))

# Abertura + Dashboard (2 -> 3)
fg.pos = (450.0, 1000.0)
say('intro')
menu_open(P[2], 'dashboard'); mhold(P[2], 'dashboard', 0.35)
k = n(0.35); a0 = fg.pos
for i in range(1, k+1):
    t = ease(i/k); pos = (a0[0]+(244-a0[0])*t, a0[1]+(426-a0[1])*t, 1.0)
    emit(render(P[2], scrim=1, menu=dict(prog=1, ms=0, act=[('dashboard', 1)]), finger=pos))
fg.pos = (244.0, 426.0)
for fpos in press(): emit(render(P[2], scrim=1, menu=dict(prog=1, ms=0, act=[('dashboard', 1)]), finger=fpos))
menu_close(P[2], 'dashboard')
fg.pos = (400.0, 1150.0)
say('dash')
hold(P[2], 2.2)
scroll_anim(SC_DASH, 0, 1, 1.0)
hold(P[3], 1.0, finger=False)
pad()
scroll_anim(SC_DASH, 1, 0, 0.8)
hold(P[2], 0.2, finger=False)

# Lancar Venda (5 -> 6 -> 7 -> 5)
say('lanc')
navigate(P[2], 'dashboard', P[5], 'lancar')
fg.pos = (400.0, 1100.0)
hold(P[5], 1.0)
scroll_anim(SC_LANC, 0, 1, 1.1)
hold(P[6], 0.6, finger=False)
show_finger_move(P[6], (373, 1425), 0.45)
tap(P[6])
modal(P[6], P[7], 901, True, 0.45)
hold(P[7], 1.8, finger=False)
show_finger_move(P[7], (373, 1488), 0.4)
tap(P[7])
modal(P[5], P[7], 901, False, 0.4)
pad()

# Pedidos / Delivery (aviso -> 20 -> 19 -> 18)
def ped_extra(dst_base, ms_cur):
    k = n(0.4)
    for i in range(1, k+1):
        emit(render(dst_base, scrim=1, menu=dict(prog=1, ms=0, act=[('pedidos', 1)], badge=True), banner=eo(i/k)))
    for _ in range(n(1.6)):
        emit(render(dst_base, scrim=1, menu=dict(prog=1, ms=0, act=[('pedidos', 1)], badge=True), banner=1.0))
    k = n(0.4); a0 = (244.0, ROWS['pedidos']+TOP)
    for i in range(1, k+1):
        t = ease(i/k); pos = (a0[0]+(604-a0[0])*t, a0[1]+(421-a0[1])*t, 1.0)
        emit(render(dst_base, scrim=1, menu=dict(prog=1, ms=0, act=[('pedidos', 1)], badge=True), banner=1.0, finger=pos))
    fg.pos = (604.0, 421.0)
    for fpos in press(): emit(render(dst_base, scrim=1, menu=dict(prog=1, ms=0, act=[('pedidos', 1)], badge=True), banner=1.0, finger=fpos))
    k = n(0.3)
    for i in range(1, k+1):
        t = ease(i/k); bg = np.clip(dst_base.astype(float)*(1-t)+P[20].astype(float)*t, 0, 255).astype(np.uint8)
        emit(render(bg, scrim=1-t, menu=dict(prog=1, ms=0, act=[('pedidos', 1)], badge=True), banner=1-t))
    menu_close(P[20], 'pedidos', badge=True)
say('ped')
navigate(P[5], 'lancar', P[19], 'pedidos', extra=ped_extra)
fg.pos = (373.0, 1000.0)
hold(P[20], 1.6)
show_finger_move(P[20], (373, 1413), 0.45)
tap(P[20])
modal(P[19], P[20], 516, False, 0.4)
hold(P[19], 1.0, finger=False)
fg.pos = (400.0, 1150.0)
scroll_anim(SC_PED, 0, 1, 0.9, finger=fg.pos+(1.0,))
crossfade(SC_PED.at(1), P[18], 0.35)
hold(P[18], 1.0, finger=False)
pad()

# Historico de Vendas (16 -> 17)
say('hist')
navigate(P[18], 'pedidos', P[16], 'historico', sweep=('entregas', 'whatsapp'))
hold(P[16], 2.2, finger=False)
show_finger_move(P[16], (167, 413), 0.45)
tap(P[16])
crossfade(P[16], P[17], 0.35)
hold(P[17], 1.0, finger=False)
pad()

# Receitas (15 -> 14 -> 15)
say('rec')
navigate(P[17], 'historico', P[15], 'receitas')
hold(P[15], 2.4, finger=False)
show_finger_move(P[15], (651, 553), 0.45)
tap(P[15])
k = n(0.45)
for i in range(1, k+1):
    t = eo(i/k); f = P[15].astype(float).copy()
    f[TOP:BOT] = f[TOP:BOT]*(1-SCRIM_A*t) + SCRIM_C*(SCRIM_A*t)
    off = int((BOT-TOP)*(1-t)); mdl = P[14][TOP:BOT]
    f[TOP+off:BOT] = mdl[:BOT-TOP-off]
    emit(np.clip(f, 0, 255).astype(np.uint8))
hold(P[14], 1.6, finger=False)
pad()

# Produtos e Estoque (13)
show_finger_move(P[14], (693, 215), 0.35)
tap(P[14])
k = n(0.35)
for i in range(1, k+1):
    t = ease(i/k); f = P[15].astype(float).copy()
    f[TOP:BOT] = f[TOP:BOT]*(1-SCRIM_A*(1-t)) + SCRIM_C*(SCRIM_A*(1-t))
    off = int((BOT-TOP)*t); mdl = P[14][TOP:BOT]
    f[TOP+off:BOT] = mdl[:BOT-TOP-off]
    emit(np.clip(f, 0, 255).astype(np.uint8))
say('prod')
navigate(P[15], 'receitas', P[13], 'produtos', ms_dst=100, sweep=('visao',))
hold(P[13], 1.0, finger=False)
pad()

# Funcionarios (8)
say('func')
navigate(P[13], 'produtos', P[8], 'funcionarios', ms_dst=450)
hold(P[8], 1.0, finger=False)
pad()

# Relatorios (10 -> 9)
say('rel')
navigate(P[8], 'funcionarios', P[10], 'relatorios', ms_dst=450)
hold(P[10], 2.8, finger=False)
fg.pos = (400.0, 1150.0)
scroll_anim(SC_REL, 0, 1, 1.2, finger=fg.pos+(1.0,))
hold(P[9], 1.0, finger=False)
pad()

# CMV e Lucro (11)
say('cmv')
navigate(P[9], 'relatorios', P[11], 'cmv', ms_dst=450)
hold(P[11], 1.0, finger=False)
pad()

# Perdas e Consumo (12)
say('perd')
navigate(P[11], 'cmv', P[12], 'perdas', ms_dst=450)
hold(P[12], 1.0, finger=False)
pad(); hold(P[12], 0.8, finger=False)

ff.stdin.close(); ff.wait()
print('frames', frames_written, 'dur', frames_written/FPS)

# ---- trilha: musica de fundo + narracao (com "ducking") e formato Reels 1080x1920 ----
import wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music
ND = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'narracao')
SR = 44100; total = frames_written/FPS
mus = music.generate(total)
voice = np.zeros((len(mus), 2)); duck = np.ones(len(mus))
for key, t0 in cues:
    w = wave.open(os.path.join(ND, key + '.wav')); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float)/32768; w.close()
    x = np.interp(np.arange(int(len(x)*SR/sr))*sr/SR, np.arange(len(x)), x)
    i = int(t0*SR); voice[i:i+len(x), 0] += x[:len(voice)-i]; voice[i:i+len(x), 1] += x[:len(voice)-i]
    a, b = max(0, int((t0-0.2)*SR)), min(len(mus), int((t0+len(x)/SR+0.35)*SR))
    duck[a:b] = 0.0
env = np.convolve(duck, np.ones(int(0.25*SR))/int(0.25*SR), mode='same')     # transicao suave
gain = 0.62 - 0.40*(1-env)                                                    # musica ~ -4 dB, abaixa ~ -15 dB sob a voz
mix = mus*gain[:, None]*0.6 + voice*1.5
mix = np.tanh(mix*1.1)/np.tanh(1.1)
wavf = OUT.replace('.mp4', '_audio.wav')
w = wave.open(wavf, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix*26000).astype('<i2').tobytes()); w.close()
final = OUT.replace('.mp4', '_instagram.mp4')
vf = ('[0:v]split=2[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:5,eq=brightness=-0.15[bg];'
      '[b]scale=-2:1920[fg];[bg][fg]overlay=(W-w)/2:0,format=yuv420p[v]')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', OUT, '-i', wavf, '-filter_complex', vf, '-map', '[v]', '-map', '1:a',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-r', '30', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-shortest',
                '-movflags', '+faststart', final], check=True)
os.remove(wavf)
json.dump(cues, open(OUT.replace('.mp4', '_cues.json'), 'w'), indent=1)
print('final', final, 'duracao', round(total, 1))
