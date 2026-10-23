"""Comercial Rango (80 s, 1080x1920 vertical 9:16, 30 fps) — composicao em Python (PIL/numpy) + ffmpeg.
Paleta toda azul; logo oficial (assets/logo_rango.png, fundo transparente, sem alteracoes); telas reais de ../rango-video/prints.
Uso: python3 -I anuncio.py [saida.mp4]      (requer audio/*.wav gerados por narracao_anuncio.py)"""
import os, sys, json, wave, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rango_ui as ui
sys.path.insert(0, os.path.join(HERE, '..', 'rango-video'))
import music

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'rango_anuncio_80s.mp4')
W, H, FPS, TOTAL = 1080, 1920, 30, 80.0
P = ui.P; ease = ui.ease; eo = ui.eo

# ------------------------------- paleta (somente azuis + branco) -------------------------------
NAVY, NAVY2 = (6, 21, 54), (9, 32, 84)
BLUE, BLUE2 = (22, 98, 226), (12, 60, 160)
SKY, ICE, WHITE = (140, 200, 255), (214, 235, 255), (255, 255, 255)
HL = (0, 120, 255)                                         # destaque sobre a interface

def font(sz, w='Bold', display=False):
    return ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter{'Display' if display else ''}-{w}.otf", sz)

def seg(t, a, b): return min(max((t-a)/(b-a), 0.0), 1.0)
def lerp(a, b, k): return a+(b-a)*k

# ------------------------------- fundos -------------------------------
def gradient(c0, c1, size=(W, H), diag=False):
    x = np.linspace(0, 1, size[0])[None, :, None]; y = np.linspace(0, 1, size[1])[:, None, None]
    k = np.broadcast_to((x*0.55+y*0.45) if diag else y, (size[1], size[0], 1))
    return (np.array(c0)*(1-k)+np.array(c1)*k).astype(np.uint8)

def make_main_bg():
    base = Image.fromarray(gradient(NAVY, (4, 14, 40)))
    panel = Image.fromarray(gradient((30, 116, 240), BLUE2, diag=True))
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([(0, 560), (W, 400), (W, H), (0, H)], fill=255)
    base.paste(panel, (0, 0), m)
    glow = Image.new('RGB', (W, H), (0, 0, 0)); ImageDraw.Draw(glow).ellipse([100, 700, 980, 1560], fill=(30, 90, 190))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    return ImageChops.add(base, Image.eval(glow, lambda v: int(v*0.35)))
BG_MAIN = make_main_bg()
BG_BRAND = Image.fromarray(gradient((26, 108, 236), (8, 40, 118), diag=True))
BG_DEEP = Image.fromarray(gradient((5, 18, 48), (8, 30, 78)))

# ------------------------------- logo oficial -------------------------------
LOGO = Image.open(os.path.join(HERE, 'assets', 'logo_rango.png')).convert('RGBA')
_logo_cache = {}
def logo_at(w):
    if w not in _logo_cache: _logo_cache[w] = LOGO.resize((w, int(LOGO.height*w/LOGO.width)), Image.LANCZOS)
    return _logo_cache[w]
def put_rgba(base, im, x, y, alpha=1.0):
    if alpha <= 0: return
    if alpha < 1: im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v*alpha)))
    base.paste(im, (int(x), int(y)), im)

# ------------------------------- telefone com a interface real -------------------------------
SCR, DEV, PX, PY = (539, 1018), (571, 1050), (W-571)//2, 470
def _mask(size, r):
    m = Image.new('L', (size[0]*4, size[1]*4), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0]*4-1, size[1]*4-1], r*4, fill=255)
    return m.resize(size, Image.LANCZOS)
DEV_MASK, SCR_MASK = _mask(DEV, 70), _mask(SCR, 54)
DEV_IMG = Image.new('RGBA', DEV, (12, 16, 30, 255)); ImageDraw.Draw(DEV_IMG).rounded_rectangle([2, 2, DEV[0]-3, DEV[1]-3], 68, outline=(60, 80, 120, 255), width=3)
DEV_IMG.putalpha(DEV_MASK)
_sh = Image.new('RGBA', (DEV[0]+160, DEV[1]+160), (0, 0, 0, 0)); ImageDraw.Draw(_sh).rounded_rectangle([80, 90, 80+DEV[0], 90+DEV[1]], 70, fill=(0, 6, 30, 150))
SHADOW = _sh.filter(ImageFilter.GaussianBlur(28))

def app(f): return f[162:1570]                                   # recorta navegador/gestos: so a tela do app (1408x746)
P3A = P[3][52:1460]                                              # print 3 (rolado, sem barra do navegador)
PA = {k: app(P[k]) for k in P if k != 3}; PA[3] = P3A

def zoom_at(keys, t):
    """keys: [(t, z, cx, cy)] interpolados com ease (zoom digital suave)."""
    if t <= keys[0][0]: return keys[0][1:]
    for (t0, z0, x0, y0), (t1, z1, x1, y1) in zip(keys, keys[1:]):
        if t <= t1:
            k = ease(seg(t, t0, t1)); return (lerp(z0, z1, k), lerp(x0, x1, k), lerp(y0, y1, k))
    return keys[-1][1:]

def draw_phone(base, appf, t, zoom=(1.0, 373, 704), hl=(), enter=1.0, alpha=1.0, dx=0, dy=0):
    z, cx, cy = zoom; w, h = 746/z, 1408/z
    x0 = min(max(cx-w/2, 0), 746-w); y0 = min(max(cy-h/2, 0), 1408-h)
    scr = Image.fromarray(np.ascontiguousarray(appf)).resize(SCR, Image.LANCZOS, box=(x0, y0, x0+w, y0+h)).convert('RGBA')
    if hl:
        ov = Image.new('RGBA', SCR, (0, 0, 0, 0)); d = ImageDraw.Draw(ov); s = SCR[0]/w
        for (a, b, c, e, ta, tb) in hl:
            vis = min(seg(t, ta, ta+0.3), 1-seg(t, tb-0.3, tb))
            if vis <= 0: continue
            pulse = 0.5+0.5*np.sin(t*5.5)
            r = [(a-x0)*s-6, (b-y0)*s-6, (c-x0)*s+6, (e-y0)*s+6]
            d.rounded_rectangle([r[0]-6, r[1]-6, r[2]+6, r[3]+6], 22, outline=HL+(int(70*vis*(0.6+pulse*0.4)),), width=12)
            d.rounded_rectangle(r, 18, outline=HL+(int(255*vis),), width=5)
        scr = Image.alpha_composite(scr, ov)
    ox = PX+dx; oy = PY+dy+int((1-eo(enter))*1500)
    dev = DEV_IMG.copy(); dev.paste(scr, (16, 16), SCR_MASK)
    base.paste(SHADOW, (ox-80, oy-60), SHADOW)
    put_rgba(base, dev, ox, oy, alpha)

def finger_on(appf, x, y, s=1.0):
    im = Image.fromarray(np.ascontiguousarray(appf)); tile = ui.finger_tile(s); im.paste(tile, (int(x-40), int(y-40)), tile)
    return np.array(im)

# ------------------------------- rolagem real da interface -------------------------------
class AppScroll:
    def __init__(s, A, B, dist):
        ac, bc, gap = A[103:1408], B[103:1408], max(0, dist-1305)
        parts = [ac] + ([np.tile(np.array([240, 243, 248], np.uint8), (gap, 746, 1))] if gap else []) + [bc[max(0, 1305-dist):]]
        s.sheet, s.dist, s.A, s.B = np.concatenate(parts, 0), dist, A, B
    def at(s, p):
        if p <= 0: return s.A
        if p >= 1: return s.B
        f = s.A.copy(); o = int(round(s.dist*ease(p))); f[103:1408] = s.sheet[o:o+1305]; return f
SC_DASH, SC_LANC = AppScroll(PA[2], PA[3], 1305), AppScroll(PA[5], PA[6], 1203)
SC_PED, SC_REL = AppScroll(PA[19], PA[18], 720), AppScroll(PA[10], PA[9], 1353)

def push(a, b, p):
    s = int(746*ease(p))
    if s <= 0: return a
    if s >= 746: return b
    out = np.empty_like(a); out[:, :746-s] = a[:, s:]; out[:, 746-s:] = b[:, :s]; return out

def blend(a, b, p):
    p = ease(p); return np.clip(a.astype(float)*(1-p)+b.astype(float)*p, 0, 255).astype(np.uint8)

def modal_full(page, shot, y0, pr):
    """modal (print `shot`, linhas y0..BOT) sobe (pr 0->1) ou desce; devolve quadro completo 746x1600."""
    f = page.astype(float); T_, B_ = ui.TOP, ui.BOT
    f[T_:B_] = f[T_:B_]*(1-ui.SCRIM_A*pr)+ui.SCRIM_C*(ui.SCRIM_A*pr)
    w = ease((pr-0.88)/0.12); f[T_:y0] = f[T_:y0]*(1-w)+shot[T_:y0].astype(float)*w
    off = int((B_-y0)*(1-pr)); f[y0+off:B_] = shot[y0:B_-off].astype(float)
    return np.clip(f, 0, 255).astype(np.uint8)

# ------------------------------- navegacao pelo menu (menu real, destaque azul claro) -------------------------------
HAMB = (54, 212)
def menu_stages(ms_dst, extra):
    st = [('hamb', .35), ('p1', .2), ('open', .3), ('hold1', .3+extra)] + ([('msc', .45)] if ms_dst else []) + \
         [('item', .45), ('p2', .2), ('pill', .25), ('hold2', .15), ('close', .3)]
    return st
def menu_len(ms_dst=0, extra=0.0, close=True):
    return sum(d for n_, d in menu_stages(ms_dst, extra) if close or n_ != 'close')

def menu_nav(t, src, sk, dst, dk, ms_dst=0, extra=0.0, fstart=(640.0, 1320.0), badge=False):
    """quadro COMPLETO (746x1600) da navegacao: abrir menu, tocar no item, destaque migra, fechar."""
    ms_cur = ms_dst if ms_dst else 0
    yi = ui.ROWS[dk]-ms_cur+ui.TOP; item = (244.0, float(yi)); a = 0.0
    for name, d in menu_stages(ms_dst, extra):
        if t <= a+d or name == 'close':
            k = seg(t, a, a+d); break
        a += d
    M = lambda ms=0, act=None, prog=1.0: dict(prog=prog, ms=ms, act=act or [(sk, 1)], badge=badge)
    if name == 'hamb': return ui.render(src, finger=(lerp(fstart[0], HAMB[0], ease(k)), lerp(fstart[1], HAMB[1], ease(k)), 1.0))
    if name == 'p1': return ui.render(src, finger=(HAMB[0], HAMB[1], 1-0.35*np.sin(np.pi*k)))
    if name == 'open': return ui.render(src, scrim=eo(k), menu=M(prog=eo(k)))
    if name == 'hold1': return ui.render(src, scrim=1, menu=M())
    if name == 'msc': return ui.render(src, scrim=1, menu=M(ms=ms_dst*ease(k)))
    if name == 'item': return ui.render(src, scrim=1, menu=M(ms=ms_cur), finger=(lerp(400, item[0], ease(k)), lerp(1000, item[1], ease(k)), 1.0))
    if name == 'p2': return ui.render(src, scrim=1, menu=M(ms=ms_cur), finger=(item[0], item[1], 1-0.35*np.sin(np.pi*k)))
    if name == 'pill':
        e = ease(k); act = [(sk, 1-e), (dk, e)] if sk != dk else [(dk, 1)]
        return ui.render(dst, scrim=1, menu=M(ms=ms_cur, act=act), finger=(item[0], item[1], 1.0))
    if name == 'hold2': return ui.render(dst, scrim=1, menu=M(ms=ms_cur, act=[(dk, 1)]))
    return ui.render(dst, scrim=1-ease(k), menu=M(ms=ms_cur, act=[(dk, 1)], prog=1-ease(k)))

# ------------------------------- textos / legendas -------------------------------
_txt = {}
def text_layer(lines, size=78, x_pad=0, maxw=960):
    key = (tuple(lines), size)
    if key in _txt: return _txt[key]
    while max(font(size, 'ExtraBold', True).getlength(t) for t, c in lines) > maxw: size -= 2
    f = font(size, 'ExtraBold', True); lh = int(size*1.16)
    w = max(int(f.getlength(t)) for t, c in lines)+16
    im = Image.new('RGBA', (w, lh*len(lines)+10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, (t, c) in enumerate(lines): d.text((4, i*lh), t, font=f, fill=c+(255,))
    _txt[key] = im; return im
SFX = []                                                  # (tempo_s, tipo) para a trilha de efeitos
def show_text(base, lines, t, t_in, t_out, x=None, y=235, size=84, sfx_t=None):
    a = min(seg(t, t_in, t_in+0.45), 1-seg(t, t_out-0.3, t_out))
    if a <= 0: return
    im = text_layer(lines, size); put_rgba(base, im, (W-im.width)//2 if x is None else x, y+int((1-eo(seg(t, t_in, t_in+0.45)))*28), a)

def wrap_chunks(texto):
    words, lines, cur = texto.split(), [], ''
    for w_ in words:
        if len(cur)+len(w_)+1 > 31 and cur: lines.append(cur); cur = w_
        else: cur = (cur+' '+w_).strip()
    lines.append(cur)
    return [lines[i:i+2] for i in range(0, len(lines), 2)]

# ------------------------------- cronograma -------------------------------
DUR = json.load(open(os.path.join(HERE, 'audio', 'duracoes.json')))
STARTS = [0, 7, 15, 27, 39, 51, 63, 70, 80]
VOZ_T = [0.25]+[s+0.35 for s in STARTS[1:8]]
FALAS = [
 "Seu bar ou restaurante ainda é controlado no improviso?",
 "Com o Rango, você coloca sua operação inteira sob controle, em um só sistema.",
 "Registre suas vendas, acompanhe o faturamento e saiba exatamente o que está acontecendo no seu negócio.",
 "Controle seu estoque, veja o que está acabando e registre perdas e consumo.",
 "Organize seus pedidos e tenha mais agilidade na operação, do atendimento à entrega.",
 "E acompanhe seus resultados para tomar decisões melhores, sem depender de planilhas.",
 "Rango. Sistema de gestão para bares e restaurantes.",
 "Quer mais controle, organização e praticidade para o seu negócio? Conheça o Rango.",
]
LEGENDAS = []                                             # (ini, fim, [linhas])
for i, txt in enumerate(FALAS):
    cks = wrap_chunks(txt); tot = sum(len(' '.join(c)) for c in cks); t0 = VOZ_T[i]; d = DUR[f'cena{i+1}']
    for c in cks:
        n_ = len(' '.join(c)); LEGENDAS.append((t0, t0+d*n_/tot, c)); t0 += d*n_/tot
LEGENDAS = [(a, (b+0.12 if k+1 == len(LEGENDAS) else min(b+0.12, LEGENDAS[k+1][0])), c) for k, (a, b, c) in enumerate(LEGENDAS)]
_sub = {}
def draw_sub(base, t, cx=540):
    for k, (a, b, lines) in enumerate(LEGENDAS):
        if a <= t < b:
            if k not in _sub:
                f = font(46, 'Bold'); wd = max(int(f.getlength(l)) for l in lines)+64; ht = 64*len(lines)+32
                im = Image.new('RGBA', (wd, ht), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
                d.rounded_rectangle([0, 0, wd-1, ht-1], 26, fill=(3, 12, 36, 205))
                for j, l in enumerate(lines): d.text((wd//2, 18+j*64), l, font=f, fill=WHITE, anchor='mt')
                _sub[k] = im
            im = _sub[k]; base.paste(im, (cx-im.width//2, 1735-im.height), im); return

def demo_note(base, a=1.0):
    d = ImageDraw.Draw(base); d.text((W//2, 1752), "Dados de demonstração", font=font(24, 'Medium'), fill=(150, 190, 240), anchor='mt')

# =========================================================== CENA 1 (0-7 s) — gancho
rng = np.random.default_rng(11)
NOTES = []
for i in range(20):
    w_, h_ = int(rng.integers(260, 360)), int(rng.integers(310, 420))
    sp = Image.new('RGBA', (w_, h_), (0, 0, 0, 0)); d = ImageDraw.Draw(sp)
    d.rounded_rectangle([0, 0, w_-1, h_-1], 10, fill=[(246, 250, 255, 255), (214, 232, 255, 255), (236, 244, 255, 255)][i % 3])
    for j in range(int(rng.integers(5, 9))):
        y_ = 34+j*int((h_-60)/8); x1 = 22+int(rng.integers(w_//3, w_-50))
        pts = [(22, y_)]+[(22+(x1-22)*q/6, y_+int(rng.integers(-6, 7))) for q in range(1, 7)]
        d.line(pts, fill=(70, 95, 140, 255), width=4)
        if rng.random() < .22: d.line([(22, y_+2), (x1, y_-3)], fill=(20, 40, 90, 255), width=6)
    NOTES.append(dict(sp=sp, x=float(rng.integers(40, 1040)), y=float(rng.integers(60, 1860)), ang=float(rng.integers(-25, 25)),
                      fx=rng.uniform(.8, 2.2), ph=rng.uniform(0, 6.28), amp=rng.uniform(8, 26)))
def scene1(t):
    base = BG_DEEP.copy()
    sweep = ease(seg(t, 5.9, 7.0))
    for n_ in sorted(NOTES, key=lambda q: q['y']):
        tt = t+n_['ph']; x = n_['x']+n_['amp']*np.sin(tt*n_['fx'])-sweep*1700-sweep*sweep*500
        y = n_['y']+n_['amp']*np.cos(tt*n_['fx']*1.3)*0.6; ang = n_['ang']+9*np.sin(tt*n_['fx']*1.7)-sweep*40
        sp = n_['sp'].rotate(ang, expand=True, resample=Image.BICUBIC)
        sh = Image.new('RGBA', sp.size, (0, 0, 0, 0)); sh.putalpha(sp.getchannel('A').point(lambda v: int(v*0.35)))
        base.paste(sh, (int(x-sp.width/2+8), int(y-sp.height/2+12)), sh)
        a_ = seg(t, 1.6+(n_['x']%7)*0.04, 2.3)
        put_rgba(base, sp, x-sp.width/2, y-sp.height/2, a_)
    a_ = min(seg(t, 3.2, 3.7), 1-seg(t, 6.3, 6.8))
    if a_ > 0:
        im = text_layer([("Chega de improvisar", WHITE), ("na gestão.", SKY)], 80)
        pad = Image.new('RGBA', (im.width+120, im.height+90), (0, 0, 0, 0)); ImageDraw.Draw(pad).rounded_rectangle([0, 0, pad.width-1, pad.height-1], 34, fill=(5, 18, 52, 235))
        px, py = (W-pad.width)//2, (H-pad.height)//2-30+int((1-eo(seg(t, 3.2, 3.7)))*30)
        put_rgba(base, pad, px, py, a_); put_rgba(base, im, px+60, py+36, a_)
    d = ImageDraw.Draw(base); d.text((W//2, 1752), "Ilustração", font=font(24, 'Medium'), fill=(150, 190, 240), anchor='mt')
    # abertura da marca (azul profundo) que desliza e revela a cena
    if t < 2.4:
        slide = ease(seg(t, 1.9, 2.4))*W
        op = Image.fromarray(gradient(NAVY, NAVY2))
        k = ease(seg(t, 1.0, 1.8)); br = Image.fromarray(gradient((26, 108, 236), (8, 40, 118), diag=True))
        op = Image.blend(op, br, k*0.9)
        la = eo(seg(t, 0.0, 0.7)); lw = int(lerp(820, 900, eo(seg(t, 0, 1.4))))
        lg = logo_at(lw)
        gl = Image.new('RGBA', (lw+300, lg.height+300), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([60, 60, gl.width-60, gl.height-60], fill=(120, 190, 255, int(70*la)))
        gl = gl.filter(ImageFilter.GaussianBlur(70)); cx, cy = W//2, H//2+int((1-la)*30)-20
        put_rgba(op, gl, cx-gl.width//2, cy-gl.height//2); put_rgba(op, lg, cx-lg.width//2, cy-lg.height//2, la)
        base.paste(op, (-int(slide), 0))
    return base

# =========================================================== CENA 2 (7-15 s) — apresentacao
NAV2 = 2.0
def scene2(t):
    base = BG_MAIN.copy(); L = menu_len(0, 3.0)
    if t < NAV2: f = PA[2]
    elif t < NAV2+L: f = app(menu_nav(t-NAV2, P[2], 'dashboard', P[5], 'lancar', extra=3.0))
    else: f = PA[5]
    z = zoom_at([(0, 1.0, 373, 704), (NAV2, 1.08, 373, 560)], t) if t < NAV2 else (1.0, 373, 704)
    draw_phone(base, f, t, z, enter=seg(t, 0, 0.9))
    show_text(base, [("Seu negócio.", WHITE), ("Mais organizado.", SKY)], t, 2.3, 7.6)
    return base

# =========================================================== CENA 3 (15-27 s) — vendas e faturamento
def scene3(t):
    base = BG_MAIN.copy(); f = PA[5]; zoom = (1.0, 373, 704); hl = []
    if t < 0.6: f = PA[5]
    elif t < 1.8: f = SC_LANC.at(seg(t, 0.6, 1.8))
    elif t < 2.2: f = PA[6]
    elif t < 2.6: f = finger_on(PA[6], lerp(560, 373, ease(seg(t, 2.2, 2.6))), lerp(1000, 1263, ease(seg(t, 2.2, 2.6))))
    elif t < 2.8: f = finger_on(PA[6], 373, 1263, 1-0.35*np.sin(np.pi*seg(t, 2.6, 2.8)))
    elif t < 3.25: f = app(modal_full(P[6], P[7], 901, eo(seg(t, 2.8, 3.25))))
    elif t < 5.0: f = PA[7]
    elif t < 5.5: f = finger_on(PA[7], 373, lerp(1100, 1326, ease(seg(t, 5.0, 5.4))), 1-0.35*np.sin(np.pi*seg(t, 5.3, 5.5)))
    elif t < 5.85: f = app(modal_full(P[5], P[7], 901, 1-ease(seg(t, 5.5, 5.85))))
    elif t < 5.9: f = PA[5]
    elif t < 5.9+menu_len(): f = app(menu_nav(t-5.9, P[5], 'lancar', P[16], 'historico'))
    elif t < 10.4: f = PA[16]
    else: f = blend(PA[16], PA[17], seg(t, 10.4, 10.75)); f = PA[17] if t > 10.75 else f
    if 3.25 <= t < 5.0: zoom = zoom_at([(3.2, 1.0, 373, 704), (3.9, 1.06, 373, 1000)], t); hl = [(387, 905, 703, 1147, 3.6, 5.0)]
    if 8.4 <= t: zoom = zoom_at([(8.3, 1.0, 373, 704), (9.0, 1.06, 373, 520)], t); hl = [(27, 325, 718, 528, 8.9, 10.4)]
    draw_phone(base, f, t, zoom, hl)
    show_text(base, [("Vendas", WHITE), ("organizadas.", SKY)], t, 0.8, 5.6)
    show_text(base, [("Mais clareza sobre", WHITE), ("o faturamento.", SKY)], t, 8.4, 12.0)
    demo_note(base); return base

# =========================================================== CENA 4 (27-39 s) — estoque, perdas e consumo
def scene4(t):
    base = BG_MAIN.copy(); L = menu_len(100, 0.0); zoom = (1.0, 373, 704); hl = []
    tN = 0.0
    if t < L: f = app(menu_nav(t, P[17], 'historico', P[13], 'produtos', ms_dst=100))
    elif t < 6.6: f = PA[13]; zoom = zoom_at([(L, 1.0, 373, 704), (L+0.8, 1.12, 373, 470)], t); hl = [(27, 318, 718, 474, L+0.5, 6.4)]
    elif t < 7.1: f = push(PA[13], PA[3], seg(t, 6.6, 7.1))
    elif t < 9.2: f = PA[3]; zoom = zoom_at([(7.1, 1.0, 373, 704), (7.8, 1.06, 373, 480)], t); hl = [(27, 331, 718, 635, 7.4, 9.0)]
    elif t < 9.7: f = push(PA[3], PA[12], seg(t, 9.2, 9.7))
    else: f = PA[12]; zoom = zoom_at([(9.7, 1.0, 373, 704), (10.4, 1.06, 373, 560)], t); hl = [(27, 325, 718, 536, 10.0, 11.9), (27, 755, 718, 914, 10.6, 11.9)]
    draw_phone(base, f, t, zoom, hl)
    show_text(base, [("Mais controle", WHITE), ("do estoque.", SKY)], t, 3.2, 7.2)
    show_text(base, [("Menos surpresas", WHITE), ("na operação.", SKY)], t, 7.6, 12.0)
    demo_note(base); return base

# =========================================================== CENA 5 (39-51 s) — pedidos e operacao
def scene5(t):
    base = BG_MAIN.copy(); zoom = (1.0, 373, 704); hl = []
    NAVL = menu_len(0, 0.0, close=False)                       # ate o fim de hold2 (menu aberto em Pedidos)
    M = lambda **kw: dict(prog=kw.pop('prog', 1.0), ms=0, act=[('pedidos', 1)], badge=True)
    if t < NAVL: f = app(menu_nav(t, P[12], 'perdas', P[19], 'pedidos'))
    elif t < NAVL+0.4: f = app(ui.render(P[19], scrim=1, menu=M(), banner=eo(seg(t, NAVL, NAVL+0.4))))
    elif t < 3.7: f = app(ui.render(P[19], scrim=1, menu=M(), banner=1.0))
    elif t < 4.1: k = ease(seg(t, 3.7, 4.1)); f = app(ui.render(P[19], scrim=1, menu=M(), banner=1.0, finger=(lerp(300, 604, k), lerp(900, 421, k), 1.0)))
    elif t < 4.3: f = app(ui.render(P[19], scrim=1, menu=M(), banner=1.0, finger=(604, 421, 1-0.35*np.sin(np.pi*seg(t, 4.1, 4.3)))))
    elif t < 4.65:
        k = ease(seg(t, 4.3, 4.65)); bg = blend(P[19], P[20], seg(t, 4.3, 4.65)); f = app(ui.render(bg, scrim=1-k, menu=M(), banner=1-k))
    elif t < 4.95: f = app(ui.render(P[20], scrim=1-ease(seg(t, 4.65, 4.95)), menu=dict(prog=1-ease(seg(t, 4.65, 4.95)), ms=0, act=[('pedidos', 1)], badge=True)))
    elif t < 7.0: f = PA[20]; zoom = zoom_at([(4.95, 1.0, 373, 704), (5.7, 1.06, 373, 800)], t); hl = [(43, 1213, 703, 1291, 6.0, 7.6)]
    elif t < 7.6: k = ease(seg(t, 7.0, 7.4)); f = finger_on(PA[20], lerp(560, 373, k), lerp(900, 1251, k), 1-0.35*np.sin(np.pi*seg(t, 7.4, 7.6)))
    elif t < 8.0: f = app(modal_full(P[19], P[20], 516, 1-ease(seg(t, 7.6, 8.0))))
    elif t < 9.0: f = PA[19]
    elif t < 10.0: f = SC_PED.at(seg(t, 9.0, 10.0))
    else: f = blend(SC_PED.at(1.0), PA[18], seg(t, 10.0, 10.4)); f = PA[18] if t > 10.4 else f; hl = [(27, 643, 680, 883, 10.5, 11.9)]
    draw_phone(base, f, t, zoom, hl)
    show_text(base, [("Pedidos mais", WHITE), ("organizados.", SKY)], t, 1.2, 6.4)
    show_text(base, [("Fluxo de atendimento", WHITE), ("mais claro.", SKY)], t, 7.4, 12.0, size=72)
    return base

# =========================================================== CENA 6 (51-63 s) — gestao e decisao
def scene6(t):
    base = BG_MAIN.copy(); zoom = (1.0, 373, 704); hl = []
    L = menu_len(0, 0.0)
    if t < L: f = app(menu_nav(t, P[18], 'pedidos', P[2], 'dashboard'))
    elif t < 5.8: f = PA[2]; zoom = zoom_at([(L, 1.0, 373, 704), (L+0.8, 1.06, 373, 540)], t); hl = [(27, 325, 718, 760, L+0.4, 5.6)]
    elif t < 6.8: f = SC_DASH.at(seg(t, 5.8, 6.8))
    elif t < 8.4: f = PA[3]; zoom = zoom_at([(6.8, 1.0, 373, 704), (7.4, 1.06, 373, 900)], t); hl = [(27, 665, 718, 1181, 7.0, 8.2)]
    elif t < 8.9: f = push(PA[3], PA[10], seg(t, 8.4, 8.9))
    elif t < 10.4: f = PA[10]; zoom = zoom_at([(8.9, 1.0, 373, 704), (9.5, 1.06, 373, 600)], t); hl = [(27, 325, 718, 760, 9.2, 10.2)]
    elif t < 11.6: f = SC_REL.at(seg(t, 10.4, 11.6))
    else: f = PA[9]; hl = [(27, 354, 718, 898, 11.7, 12.0)]
    draw_phone(base, f, t, zoom, hl)
    show_text(base, [("Informações para", WHITE), ("decidir melhor.", SKY)], t, 2.8, 11.2, size=74)
    demo_note(base); return base

# =========================================================== CENA 7 (63-70 s) — marca (logo so aparece na abertura e no final)
def scene7(t):
    base = BG_BRAND.copy()
    pb = base.copy(); draw_phone(pb, PA[2], t, (1.0, 373, 704), enter=seg(t, 0, 0.8), dy=420)
    base = Image.blend(base, pb, 0.32)
    la = eo(seg(t, 0.2, 0.9)); lg = logo_at(int(lerp(900, 940, ease(seg(t, 0, 7)))))
    put_rgba(base, lg, (W-lg.width)//2, 330+int((1-la)*30), la)
    a = seg(t, 1.2, 1.8)
    if a > 0:
        f = font(50, 'SemiBold'); im = Image.new('RGBA', (W, 140), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.text((W//2, 4), "Sistema de gestão para", font=f, fill=ICE+(255,), anchor='mt'); d.text((W//2, 70), "bares e restaurantes.", font=f, fill=ICE+(255,), anchor='mt')
        put_rgba(base, im, 0, 330+lg.height+30+int((1-eo(a))*18), a)
    return base

# =========================================================== CENA 8 (70-80 s) — CTA
def scene8(t):
    base = BG_BRAND.copy()
    la = eo(seg(t, 0.0, 0.7)); lg = logo_at(640); put_rgba(base, lg, (W-lg.width)//2, 250+int((1-la)*24), la)
    for i, (txt, col) in enumerate([("CONTROLE SUA OPERAÇÃO.", WHITE), ("ENTENDA SEUS RESULTADOS.", WHITE), ("CRESÇA COM MAIS ORGANIZAÇÃO.", ICE)]):
        a = seg(t, 0.6+i*0.9, 1.1+i*0.9)
        if a > 0:
            im = text_layer([(txt, col)], 58); put_rgba(base, im, (W-im.width)//2, 640+i*92+int((1-eo(a))*20), eo(a))
    a = seg(t, 3.4, 3.9)
    if a > 0:
        f = font(48, 'ExtraBold', True); lab = "CONHEÇA O RANGO"; tw = int(f.getlength(lab)); pw, ph_ = tw+140, 104
        im = Image.new('RGBA', (pw, ph_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, pw-1, ph_-1], 52, fill=(255, 255, 255, 255))
        d.text((50, ph_//2), lab, font=f, fill=NAVY2, anchor='lm')
        ax = 50+tw+24; d.polygon([(ax, ph_//2-16), (ax+28, ph_//2), (ax, ph_//2+16)], fill=BLUE)
        pulse = 1+0.015*np.sin(t*4); im2 = im.resize((int(pw*pulse), int(ph_*pulse)), Image.LANCZOS)
        put_rgba(base, im2, (W-im2.width)//2, 960-(im2.height-ph_)//2+int((1-eo(a))*20), eo(a))
    a = seg(t, 4.2, 4.8)
    if a > 0:
        im = Image.new('RGBA', (W, 56), (0, 0, 0, 0)); ImageDraw.Draw(im).text((W//2, 8), "Sistema de gestão para bares e restaurantes.", font=font(32, 'Medium'), fill=ICE+(255,), anchor='mt')
        put_rgba(base, im, 0, 1120, eo(a))
    return base

SCENES = [scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8]
DOTS_TAPS = [(7+2.0+.35+.2, 'tap'), (7+2.0+2.5+3.0-0.1, 'tap'), (15+2.6, 'tap'), (15+5.3, 'tap'), (15+5.9+1.4, 'tap'), (27+1.1, 'tap'),
             (39+3.9, 'tap'), (39+7.4, 'tap'), (39+1.2, 'tap'), (51+0.55, 'tap')]
SFX_T = [(1.9, 'whoosh')] + [(s-0.05, 'whoosh') for s in STARTS[1:8]] + DOTS_TAPS + \
        [(7+2.3, 'pop'), (15+0.8, 'pop'), (15+8.4, 'pop'), (27+3.2, 'pop'), (27+7.6, 'pop'), (39+1.2, 'pop'), (39+7.4, 'pop'), (51+2.8, 'pop'),
         (3.2, 'pop'), (70+0.6, 'pop'), (70+1.5, 'pop'), (70+2.4, 'pop'), (70+3.4, 'pop'), (63+0.2, 'pop')]

def draw_frame(t):
    i = max(j for j in range(8) if STARTS[j] <= t)
    img = SCENES[i](t-STARTS[i])
    if i > 0 and t-STARTS[i] < 0.3:
        prev = SCENES[i-1](STARTS[i]-STARTS[i-1]+(t-STARTS[i]))
        img = Image.blend(prev, img, ease((t-STARTS[i])/0.3))
    draw_sub(img, t); return img

# ------------------------------- renderizacao -------------------------------
def render_video(path):
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(FPS), path], stdin=subprocess.PIPE)
    for n_ in range(int(TOTAL*FPS)):
        ff.stdin.write(np.asarray(draw_frame(n_/FPS).convert('RGB')).tobytes())
    ff.stdin.close(); ff.wait()

# ------------------------------- audio: voz + trilha + efeitos -------------------------------
SR = 44100
def whoosh(d=.55, rng=np.random.default_rng(3)):
    n_ = int(d*SR); x = np.convolve(rng.standard_normal(n_), np.ones(30)/30, 'same')
    return x*3*np.sin(np.pi*np.linspace(0, 1, n_))**2*np.linspace(0.6, 1, n_)
def pop(): n_ = int(.12*SR); t_ = np.arange(n_)/SR; return np.sin(2*np.pi*(660+900*np.exp(-t_/.03))*t_)*np.exp(-t_/.04)*.7
def tap(): n_ = int(.09*SR); t_ = np.arange(n_)/SR; return (np.sin(2*np.pi*1400*t_)*np.exp(-t_/.012)*.5+np.random.default_rng(5).standard_normal(n_)*np.exp(-t_/.004)*.25)

def build_audio(path):
    N = int(TOTAL*SR); mus = music.generate(TOTAL)
    voice = np.zeros(N); duck = np.ones(N)
    for i in range(8):
        w = wave.open(os.path.join(HERE, 'audio', f'cena{i+1}.wav')); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float)/32768; w.close()
        x = np.interp(np.arange(int(len(x)*SR/sr))*sr/SR, np.arange(len(x)), x); a = int(VOZ_T[i]*SR); voice[a:a+len(x)] += x[:N-a]
        duck[max(0, a-int(.2*SR)):min(N, a+len(x)+int(.35*SR))] = 0.0
    env = np.convolve(duck, np.ones(int(.3*SR))/int(.3*SR), 'same')
    ramp = np.interp(np.arange(N)/SR, [0, 7, 40, 63, 70, 77, 80], [0.40, 0.46, 0.58, 0.68, 0.95, 0.95, 0.5])
    g = ramp*(0.34+0.66*env)*0.55
    sfx = np.zeros(N)
    for tt, kind in SFX_T:
        x = {'whoosh': whoosh, 'pop': pop, 'tap': tap}[kind]() * {'whoosh': .30, 'pop': .22, 'tap': .22}[kind]
        a = int(tt*SR); x = x[:N-a]; sfx[a:a+len(x)] += x
    out = np.stack([mus[:N, 0]*g+voice*1.5+sfx, mus[:N, 1]*g+voice*1.5+sfx], 1)
    out = np.tanh(out*1.05)/np.tanh(1.05)*0.82
    w = wave.open(path, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out*32767).astype('<i2').tobytes()); w.close()

def write_srt(path):
    ts = lambda s: f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d},{int(round((s%1)*1000)):03d}"
    with open(path, 'w', encoding='utf-8') as f:
        for k, (a, b, lines) in enumerate(LEGENDAS, 1): f.write(f"{k}\n{ts(a)} --> {ts(b)}\n" + "\n".join(lines) + "\n\n")

if __name__ == '__main__':
    mode = sys.argv[2] if len(sys.argv) > 2 else 'all'
    if mode == 'frames':                                    # depuracao: salva quadros em tempos dados
        for t in [float(x) for x in sys.argv[3:]]: draw_frame(t).save(os.path.join(HERE, '_dbg_%05.1f.png' % t))
        sys.exit()
    tmp = OUT.replace('.mp4', '_semaudio.mp4'); wav = OUT.replace('.mp4', '_audio.wav')
    render_video(tmp); build_audio(wav); write_srt(os.path.join(HERE, 'legendas.srt'))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',
                    '-t', str(TOTAL), '-movflags', '+faststart', OUT], check=True)
    os.remove(tmp); os.remove(wav); print('ok', OUT)
