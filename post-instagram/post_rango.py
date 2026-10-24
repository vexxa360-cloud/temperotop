"""Post publicitario Rango (1080x1350, 4:5) — composicao 2D (PIL) com o cofrinho renderizado em Blender (cofrinho_render.png).
Uso: python3 -I post_rango.py [cofrinho.png] [saida.png]"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PIG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'cofrinho_render.png')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'post_rango_1080x1350.png')
W, H, SS = 1080, 1350, 3
BLUE, ICE, NAVY, WHITE = (21, 96, 229), (220, 236, 255), (10, 30, 74), (255, 255, 255)      # cores do Rango

def catmull(pts, n=60):
    out = []
    P = [pts[0]]+pts+[pts[-1]]
    for i in range(1, len(P)-2):
        p0, p1, p2, p3 = [np.array(p, float) for p in P[i-1:i+3]]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t**3))
    out.append(np.array(pts[-1], float)); return [tuple(p) for p in out]

# ---------------------------------------------------------------- fundo: azul (62-66%) + area clara com curva organica assimetrica
def background():
    im = Image.new('RGB', (W*SS, H*SS), BLUE); d = ImageDraw.Draw(im)
    curve = catmull([(-60, 786), (0, 800), (150, 762), (300, 806), (445, 905), (610, 924), (775, 842), (915, 772), (1080, 806), (1140, 818)])
    d.polygon([(x*SS, y*SS) for x, y in curve]+[(1140*SS, H*SS), (-60*SS, H*SS)], fill=ICE)
    return im.resize((W, H), Image.LANCZOS)

# ---------------------------------------------------------------- pincelada branca irregular
def brush(x0, x1, y0, y1, seed=5):
    rng = np.random.default_rng(seed); w, h = int((x1-x0)*SS), int((y1-y0)*SS)
    m = Image.new('L', (w+80*SS, h+40*SS), 0); d = ImageDraw.Draw(m); ox, oy = 40*SS, 20*SS
    def edge(y_base, n=44, amp=3.5):
        xs = np.linspace(0, w, n); ys = y_base+np.cumsum(rng.normal(0, 0.9*SS, n))*0.35+np.sin(xs/w*5.5+rng.uniform(0, 6))*amp*SS
        return list(zip(xs+ox, ys+oy))
    top, bot = edge(0), edge(h)
    # pontas rasgadas (cerdas)
    def tip(x_edge, sign):
        pts = []
        for k in range(14):
            yy = k/13*h; pts.append((x_edge+sign*(rng.uniform(2, 13))*SS+ox, yy+oy))
        return pts
    left = tip(0, -1); right = tip(w, 1)
    poly = top+right+bot[::-1]+left[::-1]
    d.polygon(poly, fill=255)
    for k in range(5):                                    # falhas de tinta seca perto das bordas (listras curtas)
        yy = (rng.choice([rng.uniform(0.04, 0.16), rng.uniform(0.84, 0.96)]))*h+oy; xa = rng.uniform(0, 0.8)*w+ox
        d.line([(xa, yy), (xa+rng.uniform(0.08, 0.25)*w, yy+rng.normal(0, 1.5*SS))], fill=0, width=int(rng.uniform(1.2, 2.2)*SS))
    return m.resize((m.width//SS, m.height//SS), Image.LANCZOS), (x0-40, y0-20)

# ---------------------------------------------------------------- cofrinho (render Blender) integrado
def pig_layer():
    im = Image.open(PIG).convert('RGBA'); a = np.array(im).astype(float)
    al = a[..., 3]/255.0; body = al > 0.92
    ys, xs = np.where(body); bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    # a sombra do piso so vale perto do cofrinho (descarta a faixa distante do apanhador de sombra)
    mk = Image.fromarray((body*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.054*im.width))
    wgt = np.clip(np.array(mk).astype(float)/255*4.0, 0, 1)
    a[..., 3] = np.where(al > 0.92, al, al*wgt)*255
    im = Image.fromarray(a.astype(np.uint8), 'RGBA')
    sc = 578/(bx1-bx0+1)
    im = im.resize((int(im.width*sc), int(im.height*sc)), Image.LANCZOS)
    cx, bot = (bx0+bx1)/2*sc, by1*sc
    return im, (int(540-cx), int(992-bot))

# ---------------------------------------------------------------- tipografia
ANTON = os.path.join(HERE, 'assets', 'Anton-Regular.woff')
INTER = '/usr/share/fonts/opentype/inter/Inter-%s.otf'

def build():
    img = background(); d = ImageDraw.Draw(img)
    # logo (branca, proporcao original)
    lg = Image.open(os.path.join(HERE, 'assets', 'logo_rango.png')).convert('RGBA'); lw = 330
    lg = lg.resize((lw, int(lg.height*lw/lg.width)), Image.LANCZOS); img.paste(lg, ((W-lw)//2, 30), lg)
    # manchete
    fs = 125; f = ImageFont.truetype(ANTON, fs); cx = W/2
    l1 = "PARE DE DIVIDIR SEU"; base1, base2 = 346, 346+138
    d.text((cx, base1), l1, font=f, fill=WHITE, anchor='ms')
    a, b, c = "LUCRO COM ", "TAXAS", None
    wa, wb = f.getlength(a), f.getlength(b); x0 = cx-(wa+wb)/2
    tb = f.getbbox(b, anchor='ls')                      # caixa real das letras (relativa a linha de base)
    bm, (bx, by) = brush(x0+wa-6, x0+wa+wb+12, base2+tb[1]-9, base2+tb[3]+13)
    wh = Image.new('RGBA', bm.size, WHITE+(255,)); wh.putalpha(bm); img.paste(wh, (int(bx), int(by)), wh)
    d.text((x0, base2), a, font=f, fill=WHITE, anchor='ls'); d.text((x0+wa, base2), b, font=f, fill=BLUE, anchor='ls')
    # cofrinho
    pig, (px, py) = pig_layer(); img.paste(pig, (px, py), pig)
    # textos inferiores
    sz = 42; reg, bold = ImageFont.truetype(INTER % 'Regular', sz), ImageFont.truetype(INTER % 'Bold', sz)
    def block(lines, x, y):
        for i, segs in enumerate(lines):
            xx = x
            for t, bd in segs:
                ft = bold if bd else reg; d.text((xx, y+i*56), t, font=ft, fill=NAVY, anchor='ls'); xx += ft.getlength(t)
    left = [[("No Rango,", 0)], [("o seu", 0)], [("faturamento", 0)], [("é ", 0), ("100% seu", 1)]]
    right = [[("Venda mais", 0)], [("sem pagar", 1)], [("comissão", 1)], [("por pedido", 0)]]
    wr = max(sum((bold if bd else reg).getlength(t) for t, bd in ln) for ln in right)
    block(left, 84, 1118); block(right, W-84-wr, 1118)
    return img

if __name__ == '__main__':
    build().convert('RGB').save(OUT); print('ok', OUT)
