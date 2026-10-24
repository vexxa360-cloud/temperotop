"""Rango — recriacao do video de 80 s no mockup de iPhone (1080x1920, 30 fps, SEM audio, SEM textos externos).
Reaproveita a linha do tempo e as telas do video-fonte (anuncio.py) e troca apenas a composicao: aparelho = molde da
imagem de referencia (assets/referencia_iphone.webp), fundo azul animado, sem legendas/titulos/CTA.
Uso: python3 -I anuncio_iphone.py [saida.mp4]  |  depuracao: python3 -I anuncio_iphone.py x.mp4 frames 3 12 40"""
import os, sys, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'rango_iphone_80s.mp4')
import anuncio as A                      # linha do tempo, telas reais e compositor da interface (nao renderiza ao importar)
W, H, FPS, TOTAL = A.W, A.H, A.FPS, A.TOTAL
ease, eo, seg, lerp = A.ease, A.eo, A.seg, A.lerp

# ------------------------------------------------------------------ molde do iPhone (imagem de referencia)
REF = np.array(Image.open(os.path.join(HERE, 'assets', 'referencia_iphone.webp')).convert('RGB')).astype(int)
RH, RW = REF.shape[:2]; S = W/RW                               # 941x1672 -> 1080x1920 (mesma proporcao 9:16)

def silhouette():
    r, g, b = REF[..., 0], REF[..., 1], REF[..., 2]
    blue = (b-r > 35) & (b > 60); reach = np.zeros_like(blue)
    reach[0], reach[-1], reach[:, 0], reach[:, -1] = blue[0], blue[-1], blue[:, 0], blue[:, -1]
    while True:                                                   # fundo azul conectado a borda = fora do aparelho
        d = reach.copy(); d[1:] |= reach[:-1]; d[:-1] |= reach[1:]; d[:, 1:] |= reach[:, :-1]; d[:, :-1] |= reach[:, 1:]
        new = d & blue
        if (new == reach).all(): break
        reach = new
    phone = ~reach; keep = np.zeros_like(phone); keep[800, 470] = True
    while True:
        d = keep.copy(); d[1:] |= keep[:-1]; d[:-1] |= keep[1:]; d[:, 1:] |= keep[:, :-1]; d[:, :-1] |= keep[:, 1:]
        nk = d & phone
        if (nk == keep).all(): break
        keep = nk
    reach = ~keep
    m = Image.fromarray(((~reach)*255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.9))
    body = Image.new('L', (RW*4, RH*4), 0); ImageDraw.Draw(body).rounded_rectangle([153*4, 143*4, 788*4, 1503*4], 125*4, fill=255)
    from PIL import ImageChops
    return ImageChops.multiply(m, body.resize((RW, RH), Image.LANCZOS))
SIL = silhouette().resize((W, H), Image.LANCZOS)
SPR_RGB = Image.fromarray(REF.astype(np.uint8)).resize((W, H), Image.LANCZOS)
SPRITE = SPR_RGB.convert('RGBA'); SPRITE.putalpha(SIL)

SX0, SX1, SY0, SY1 = round(180*S), round(760*S), round(168*S), round(1478*S)     # tela interna
SW, SH, SR_ = SX1-SX0, SY1-SY0, round(81*S)
STRIP_H = round(82*S)                                                           # faixa da barra de status (hora, ilha, sinal)
BLK_H = round(SW*1408/746)
FILL_H = SH-STRIP_H-BLK_H
_m = Image.new('L', (SW*4, SH*4), 0); ImageDraw.Draw(_m).rounded_rectangle([0, 0, SW*4-1, SH*4-1], SR_*4, fill=255)
SCR_MASK = _m.resize((SW, SH), Image.LANCZOS)
_strip = Image.fromarray(REF[168:168+82, 180:760].astype(np.uint8)).resize((SW, STRIP_H), Image.LANCZOS)
_sa = np.array(_strip).astype(float)*(255/np.array([240., 244., 249.])); STRIP = Image.fromarray(np.clip(_sa, 0, 255).astype(np.uint8))
_sh = Image.new('L', (W, H), 0); _sh.paste(SIL.filter(ImageFilter.GaussianBlur(34)).point(lambda v: int(v*0.55)), (0, 46))
SHADOW = Image.new('RGBA', (W, H), (0, 6, 30, 0)); SHADOW.putalpha(_sh)

def build_screen(appf, zoom, hl, t):
    z, cx, cy = zoom; w, h = 746/z, 1408/z
    x0 = min(max(cx-w/2, 0), 746-w); y0 = min(max(cy-h/2, 0), 1408-h)
    blk = Image.fromarray(np.ascontiguousarray(appf)).resize((SW, BLK_H), Image.LANCZOS, box=(x0, y0, x0+w, y0+h)).convert('RGBA')
    if hl:
        ov = Image.new('RGBA', blk.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov); s = SW/w
        for (a, b, c, e, ta, tb) in hl:
            vis = min(seg(t, ta, ta+0.3), 1-seg(t, tb-0.3, tb))
            if vis <= 0: continue
            pulse = 0.5+0.5*np.sin(t*5.5); r = [(a-x0)*s-6, (b-y0)*s-6, (c-x0)*s+6, (e-y0)*s+6]
            d.rounded_rectangle([r[0]-6, r[1]-6, r[2]+6, r[3]+6], 22, outline=A.HL+(int(70*vis*(0.6+pulse*0.4)),), width=12)
            d.rounded_rectangle(r, 18, outline=A.HL+(int(255*vis),), width=5)
        blk = Image.alpha_composite(blk, ov)
    blk = np.array(blk.convert('RGB'))
    soft = np.median(blk[-170:], axis=0)[None].astype(float)           # cor dominante de cada coluna (ignora botoes cortados)
    ramp = np.clip(np.arange(FILL_H)/5.0, 0, 1)[:, None, None]
    fill = np.clip(blk[-1:].astype(float)*(1-ramp)+soft*ramp, 0, 255).astype(np.uint8)
    fill = np.array(Image.fromarray(fill).filter(ImageFilter.GaussianBlur(3)))
    scr = np.concatenate([np.array(STRIP), blk, fill], 0)
    # indicador de inicio (barra inferior) com cor adaptada ao fundo
    by = SH-round(20*S); bx0, bx1 = round(185*S), round(393*S)
    lum = scr[by-14:by+14, bx0:bx1].mean()
    col = (20, 22, 30) if lum > 130 else (235, 240, 250)
    img = Image.fromarray(scr); ImageDraw.Draw(img).rounded_rectangle([bx0, by-3, bx1, by+3], 3, fill=col)
    return img

def draw_phone(base, appf, t, zoom=(1.0, 373, 704), hl=(), enter=1.0, alpha=1.0, dx=0, dy=0):
    canvas = SPR_RGB.copy(); canvas.paste(build_screen(appf, zoom, hl, t), (SX0, SY0), SCR_MASK)
    sp = canvas.convert('RGBA'); sp.putalpha(SIL)
    off = (dx, dy+int((1-eo(enter))*1500))
    if alpha < 1: sp.putalpha(SIL.point(lambda v: int(v*alpha)))
    base.paste(SHADOW, off, SHADOW) if alpha >= 1 else None
    base.paste(sp, off, sp)

# ------------------------------------------------------------------ fundo azul animado (curvas diagonais suaves + linhas luminosas)
def bg_key(phase, w=540, h=960):
    y = np.linspace(0, 1, h)[:, None]; x = np.linspace(0, 1, w)[None, :]
    stops = np.array([[3, 24, 84], [10, 70, 190], [16, 97, 227], [4, 52, 150], [2, 36, 112]], float); pos = np.array([0, .30, .50, .78, 1.0])
    yy = np.clip(y + 0.10*(x-0.5), 0, 1)
    base = np.stack([np.interp(yy, pos, stops[:, c]) for c in range(3)], -1).reshape(h, w, 3)
    out = base.copy()
    for i, (y0, sl, amp, f, wd) in enumerate([(0.40, -0.55, 0.035, 0.55, 0.11), (0.70, -0.40, 0.03, 0.45, 0.13), (0.92, -0.25, 0.025, 0.6, 0.10)]):
        c = y0 + sl*(x-0.5) + amp*np.sin(2*np.pi*(f*x + phase*0.5 + i*0.37))
        band = np.exp(-((y-c)/wd)**2)[..., None]; out += band*np.array([30., 95., 190.])*0.34
        for off in (-wd*0.95, wd*0.6):
            line = np.exp(-((y-c-off)/0.0030)**2)[..., None]; out += line*np.array([130., 200., 255.])*0.50
    out += np.exp(-(((x-0.5)/0.55)**2+((y-0.55)/0.35)**2))[..., None]*np.array([10., 40., 80.])*0.25
    return np.clip(out, 0, 255).astype(np.uint8)
_NK = 21
BGK = [np.array(Image.fromarray(bg_key(k/(_NK-1)*1.0)).resize((W, H), Image.BICUBIC)).astype(np.float32) for k in range(_NK)]
def bg_at(t):
    k = (t/TOTAL)*(_NK-1); i = min(int(k), _NK-2); f = ease(k-i)
    return Image.fromarray((BGK[i]*(1-f)+BGK[i+1]*f).astype(np.uint8))
class DynBG:
    def copy(self): return bg_at(CUR_T[0])
CUR_T = [0.0]

# ------------------------------------------------------------------ cenas sem texto externo
def scene1(t):
    base = bg_at(CUR_T[0]); sweep = ease(seg(t, 5.9, 7.0))
    for n_ in sorted(A.NOTES, key=lambda q: q['y']):
        tt = t+n_['ph']; x = n_['x']+n_['amp']*np.sin(tt*n_['fx'])-sweep*1700-sweep*sweep*500
        y = n_['y']+n_['amp']*np.cos(tt*n_['fx']*1.3)*0.6; ang = n_['ang']+9*np.sin(tt*n_['fx']*1.7)-sweep*40
        sp = n_['sp'].rotate(ang, expand=True, resample=Image.BICUBIC)
        sh = Image.new('RGBA', sp.size, (0, 0, 0, 0)); sh.putalpha(sp.getchannel('A').point(lambda v: int(v*0.35)))
        base.paste(sh, (int(x-sp.width/2+8), int(y-sp.height/2+12)), sh)
        A.put_rgba(base, sp, x-sp.width/2, y-sp.height/2, seg(t, 1.6+(n_['x'] % 7)*0.04, 2.3))
    if t < 2.4:                                                  # abertura da marca (como no video-fonte)
        slide = ease(seg(t, 1.9, 2.4))*W
        op = Image.fromarray(A.gradient(A.NAVY, A.NAVY2)); k = ease(seg(t, 1.0, 1.8))
        op = Image.blend(op, Image.fromarray(A.gradient((26, 108, 236), (8, 40, 118), diag=True)), k*0.9)
        la = eo(seg(t, 0.0, 0.7)); lw = int(lerp(820, 900, eo(seg(t, 0, 1.4)))); lg = A.logo_at(lw)
        gl = Image.new('RGBA', (lw+300, lg.height+300), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([60, 60, gl.width-60, gl.height-60], fill=(120, 190, 255, int(70*la)))
        gl = gl.filter(ImageFilter.GaussianBlur(70)); cx, cy = W//2, H//2+int((1-la)*30)-20
        A.put_rgba(op, gl, cx-gl.width//2, cy-gl.height//2); A.put_rgba(op, lg, cx-lg.width//2, cy-lg.height//2, la)
        base.paste(op, (-int(slide), 0))
    return base

def scene7(t):
    base = bg_at(CUR_T[0]); pb = base.copy(); draw_phone(pb, A.PA[2], t, (1.0, 373, 704), enter=seg(t, 0, 0.8), dy=420)
    base = Image.blend(base, pb, 0.32)
    la = eo(seg(t, 0.2, 0.9)); lg = A.logo_at(int(lerp(900, 940, ease(seg(t, 0, 7)))))
    A.put_rgba(base, lg, (W-lg.width)//2, 330+int((1-la)*30), la); return base

def scene8(t):
    base = bg_at(CUR_T[0]); k = ease(seg(t, 0, 1.3))
    lg = A.logo_at(int(lerp(940, 800, k))); y = lerp(330, (H-lg.height)//2-20, k)
    A.put_rgba(base, lg, (W-lg.width)//2, y+3*np.sin(t*1.2)); return base

# ------------------------------------------------------------------ liga tudo ao video-fonte
A.draw_phone = draw_phone
A.show_text = lambda *a, **k: None
A.demo_note = lambda *a, **k: None
A.draw_sub = lambda *a, **k: None
A.BG_MAIN = A.BG_BRAND = A.BG_DEEP = DynBG()
A.SCENES[0], A.SCENES[6], A.SCENES[7] = scene1, scene7, scene8

def frame(t):
    CUR_T[0] = t; return A.draw_frame(t).convert('RGB')

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == 'frames':
        for t in [float(x) for x in sys.argv[3:]]: frame(t).save(os.path.join(HERE, '_dbg_%05.1f.png' % t))
        sys.exit()
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-movflags', '+faststart', OUT],
                          stdin=subprocess.PIPE)
    for n_ in range(int(TOTAL*FPS)): ff.stdin.write(np.asarray(frame(n_/FPS)).tobytes())
    ff.stdin.close(); ff.wait(); print('ok', OUT)
