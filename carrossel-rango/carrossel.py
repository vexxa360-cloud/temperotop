"""Carrossel Rango — 7 paginas 1080x1350 (4:5). Composicao 2D com PIL (supersampling 2x).
Uso: python3 -I carrossel.py     -> slides/slide_01.png ... slide_07.png"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, S = 1080, 1350, 2
BLUE, NAVY, ICE, WHITE, SKY, DEEP = (21, 96, 229), (10, 30, 74), (220, 236, 255), (255, 255, 255), (140, 200, 255), (7, 20, 52)
ANTON = os.path.join(HERE, 'assets', 'Anton-Regular.woff')
INTER = '/usr/share/fonts/opentype/inter/Inter-%s.otf'
LOGO = Image.open(os.path.join(HERE, 'assets', 'logo_rango.png')).convert('RGBA')
PRINT19 = Image.open(os.path.join(HERE, 'assets', 'tela_pedidos.png')).convert('RGB')     # print real do Rango (Pedidos / Delivery)

def F(size, w='Bold'): return ImageFont.truetype(INTER % w, int(size*S))
def FA(size): return ImageFont.truetype(ANTON, int(size*S))

class C:
    def __init__(s, bg, size=None, rgba=False):
        s.w, s.h = size or (W, H)
        s.img = Image.new('RGBA' if rgba else 'RGB', (s.w*S, s.h*S), (0, 0, 0, 0) if rgba else bg); s.d = ImageDraw.Draw(s.img, 'RGBA')
    def p(s, v): return [x*S for x in v] if isinstance(v, (list, tuple)) else v*S
    def rr(s, box, r, fill=None, outline=None, width=0): s.d.rounded_rectangle(s.p(box), r*S, fill=fill, outline=outline, width=int(width*S))
    def ell(s, box, fill=None, outline=None, width=0): s.d.ellipse(s.p(box), fill=fill, outline=outline, width=int(width*S))
    def poly(s, pts, fill): s.d.polygon([(x*S, y*S) for x, y in pts], fill=fill)
    def line(s, pts, fill, width, joint='curve'): s.d.line([(x*S, y*S) for x, y in pts], fill=fill, width=int(width*S), joint=joint)
    def text(s, xy, t, font, fill, anchor='la'): s.d.text((xy[0]*S, xy[1]*S), t, font=font, fill=fill, anchor=anchor)
    def paste(s, im, xy, alpha=1.0):
        if alpha < 1: im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v*alpha)))
        s.img.alpha_composite(im.convert('RGBA'), (int(xy[0]*S), int(xy[1]*S))) if s.img.mode == 'RGBA' else s.img.paste(im, (int(xy[0]*S), int(xy[1]*S)), im)
    def out(s): return s.img.resize((s.w, s.h), Image.LANCZOS)

def wrap(t, font, maxw):
    lines, cur = [], ''
    for w_ in t.split():
        trial = (cur+' '+w_).strip()
        if font.getlength(trial) > maxw*S and cur: lines.append(cur); cur = w_
        else: cur = trial
    lines.append(cur); return lines
def block(c, xy, t, font, fill, maxw, lead=1.2, align='left'):
    x, y = xy; sz = font.size/S
    for ln in wrap(t, font, maxw):
        if align == 'center': c.text((x+maxw/2, y), ln, font, fill, 'ma')
        else: c.text((x, y), ln, font, fill, 'la')
        y += sz*lead
    return y
def title(c, lines, cap=112, top=196, fill=WHITE, align='left', maxw=960):
    """titulo em Anton com quebras manuais; mesmo tamanho para todas as linhas. Retorna a base (y) do bloco."""
    size = cap
    while max(FA(size).getlength(t) for t in lines) > maxw*S: size -= 2
    f = FA(size); base = top+size*0.74
    for t in lines:
        c.text(((60 if align == 'left' else W/2), base), t, f, fill, 'ls' if align == 'left' else 'ms'); base += size*1.1
    return base-size*1.1+size*0.12
def body_bottom(c, t, bottom=1214, size=31, fill=ICE, maxw=960):
    f = F(size, 'Medium'); lines = wrap(t, f, maxw); lh = size*1.32; top = bottom-len(lines)*lh
    for i, ln in enumerate(lines): c.text((60, top+i*lh), ln, f, fill, 'la')
    return top

# ----------------------------------------------------------------- identidade: logo, contador, progresso, curva continua
def chrome(c, i, logo_w=190, last=False):
    lg = LOGO.resize((int(logo_w*S), int(LOGO.height*logo_w/LOGO.width*S)), Image.LANCZOS); c.paste(lg, (60, 56))
    c.text((W-60, 66), f'{i}/7', F(26, 'Bold'), SKY, 'ra')
    for k in range(7):                                                   # progresso
        x = 60+k*36; c.rr([x, H-62, x+26, H-56], 3, fill=WHITE if k == i-1 else (255, 255, 255, 70))
    if not last:
        c.text((W-60-60, H-72), 'DESLIZE', F(22, 'Bold'), SKY, 'ra')
        c.line([(W-112, H-58), (W-72, H-58)], SKY, 4); c.line([(W-84, H-70), (W-72, H-58), (W-84, H-46)], SKY, 4)
def flow_curve(c, i):
    """linha continua atravessando as paginas (mesmo y nas bordas de paginas vizinhas)."""
    def y(xg): return 1250+10*math.sin(xg/260)+6*math.sin(xg/97+1)
    pts = [(x, y((i-1)*W+x)) for x in range(-4, W+5, 6)]
    c.line(pts, (140, 200, 255, 80), 4)

# ----------------------------------------------------------------- pecas de ilustracao
def comanda(c, x, y, w=120, h=150, text=True):
    c.rr([x, y, x+w, y+h-14], 8, fill=WHITE)
    c.poly([(x+i*(w/6), y+h-14+(10 if i % 2 else 0)) for i in range(7)]+[(x+w, y+h-14), (x, y+h-14)], WHITE)
    for k in range(4): c.rr([x+16, y+20+k*24, x+w-16-(k % 2)*26, y+28+k*24], 4, fill=(21, 96, 229, 200 if k else 255))
def chat_bubble(c, x, y, w, h, fill=WHITE, tail='l', dots=True):
    c.rr([x, y, x+w, y+h], h*0.28, fill=fill)
    tx = x+h*0.25 if tail == 'l' else x+w-h*0.25
    c.poly([(tx, y+h-4), (tx+(-1 if tail == 'l' else 1)*h*0.05, y+h+h*0.26), (tx+(1 if tail == 'l' else -1)*h*0.3, y+h-4)], fill)
    if dots:
        for k in range(3): c.ell([x+w/2-h*0.3+k*h*0.3-h*0.07, y+h/2-h*0.07, x+w/2-h*0.3+k*h*0.3+h*0.07, y+h/2+h*0.07], fill=BLUE)
def bag(c, x, y, w=120, h=110):
    c.rr([x+w*0.28, y-26, x+w*0.72, y+14], 16, outline=ICE, width=7)
    c.rr([x, y, x+w, y+h], 16, fill=ICE); c.rr([x, y+h*0.18, x+w, y+h*0.36], 0, fill=BLUE)
def tray(c, x, y, w=190):
    c.rr([x, y+30, x+w, y+42], 6, fill=ICE); c.ell([x+w*0.12, y+8, x+w*0.88, y+40], fill=WHITE)
    c.ell([x+w*0.34, y-14, x+w*0.66, y+14], fill=BLUE); c.line([(x+w*0.5, y-26), (x+w*0.5, y-14)], WHITE, 4)
def phone_small(c, x, y, w=96, h=170):
    c.rr([x, y, x+w, y+h], 18, fill=DEEP, outline=SKY, width=3); chat_bubble(c, x+12, y+30, w-24, 38, WHITE, 'l', True)
    c.rr([x+12, y+92, x+w-12, y+112], 8, fill=(140, 200, 255, 220)); c.rr([x+12, y+122, x+w-34, y+140], 8, fill=(140, 200, 255, 140))
def person(c, cx, by, s=1.0, arms=None, calm=False, shirt=BLUE):
    """meio-corpo estilizado atras de um balcao. arms: lista de (mao_x, mao_y) ate 4 bracos (coords absolutas)."""
    hy = by-300*s
    for (hx, hyy), sx in zip(arms or [], [-1, -1, 1, 1][:len(arms or [])]):
        sh = (cx+sx*62*s, by-215*s+(26*s if abs(hx-cx) < 150*s and False else 0))
        c.line([sh, ((sh[0]+hx)/2+sx*10*s, (sh[1]+hyy)/2+16*s), (hx, hyy)], shirt, 30*s)
    c.rr([cx-84*s, by-240*s, cx+84*s, by+10], 44*s, fill=shirt)
    c.rr([cx-48*s, by-170*s, cx+48*s, by+10], 14*s, fill=WHITE)                                   # avental
    c.ell([cx-46*s, hy-46*s, cx+46*s, hy+46*s], fill=ICE)
    c.rr([cx-50*s, hy-52*s, cx+50*s, hy-14*s], 22*s, fill=NAVY)                                  # cabelo/bone
    if calm: c.line([(cx-18*s, hy+16*s), (cx, hy+26*s), (cx+18*s, hy+16*s)], NAVY, 5*s)
    else: c.ell([cx-12*s, hy+14*s, cx+12*s, hy+34*s], fill=NAVY)
    for sx in (-1, 1): c.ell([cx+sx*18*s-5*s, hy-4*s, cx+sx*18*s+5*s, hy+6*s], fill=NAVY)
    for (hx, hyy) in arms or []: c.ell([hx-17*s, hyy-17*s, hx+17*s, hyy+17*s], fill=ICE)
def icon(c, kind, cx, cy, r, fg=WHITE, bg=BLUE):
    c.ell([cx-r, cy-r, cx+r, cy+r], fill=bg); k = r/60
    if kind == 'salao':                                    # mesa com cadeiras
        c.rr([cx-34*k, cy-8*k, cx+34*k, cy+2*k], 4*k, fill=fg); c.line([(cx-22*k, cy+2*k), (cx-26*k, cy+30*k)], fg, 6*k); c.line([(cx+22*k, cy+2*k), (cx+26*k, cy+30*k)], fg, 6*k)
        for sx in (-1, 1): c.rr([cx+sx*42*k-8*k, cy-6*k, cx+sx*42*k+8*k, cy+14*k], 4*k, fill=fg)
        c.ell([cx-12*k, cy-30*k, cx+12*k, cy-8*k], fill=fg)
    elif kind == 'delivery':                               # moto com bau
        c.ell([cx-42*k, cy+8*k, cx-14*k, cy+36*k], outline=fg, width=6*k); c.ell([cx+16*k, cy+8*k, cx+44*k, cy+36*k], outline=fg, width=6*k)
        c.line([(cx-28*k, cy+22*k), (cx-6*k, cy-6*k), (cx+14*k, cy-6*k), (cx+30*k, cy+22*k)], fg, 6*k); c.rr([cx-44*k, cy-30*k, cx-10*k, cy-4*k], 4*k, fill=fg)
        c.line([(cx+6*k, cy-6*k), (cx+14*k, cy-24*k), (cx+26*k, cy-24*k)], fg, 6*k)
    elif kind == 'whats':                                  # balao de conversa (generico)
        chat_bubble(c, cx-38*k, cy-30*k, 76*k, 52*k, fg, 'l', False)
        for j in range(3): c.ell([cx-22*k+j*22*k-5*k, cy-9*k, cx-22*k+j*22*k+5*k, cy+1*k], fill=bg)
def notif_card(title, sub, kind, w=470, h=118):
    im = C(None, (w+40, h+40), True)
    im.rr([22, 30, 22+w, 30+h], 26, fill=(0, 0, 0, 60)); im.img = im.img.filter(ImageFilter.GaussianBlur(10*S)); im.d = ImageDraw.Draw(im.img, 'RGBA')
    im.rr([20, 20, 20+w, 20+h], 26, fill=WHITE); icon(im, kind, 20+62, 20+h/2, 38, WHITE, BLUE)
    im.text((20+120, 20+28), title, F(30, 'ExtraBold'), NAVY); im.text((20+120, 20+70), sub, F(24, 'Medium'), (70, 96, 150)); return im.img
def tilt(img, deg): return img.rotate(deg, expand=True, resample=Image.BICUBIC)

# ----------------------------------------------------------------- paginas (grade: titulo | ilustracao | texto de apoio | rodape)
class FotoLayer:
    """camada a partir de um render PNG (RGBA): recorta a area visivel e deixa so uma faixa do balcao."""
    def __init__(self, path, base_w=960, crop=1.0):
        im = Image.open(path).convert('RGBA'); a = np.array(im)[..., 3]; ys, xs = np.where(a > 8)
        im = im.crop((xs.min(), ys.min(), xs.max()+1, ys.min()+int((ys.max()+1-ys.min())*crop)))
        k = base_w/im.width; im = im.resize((base_w, int(im.height*k)), Image.LANCZOS)
        self.w, self.h = im.size; self.img = im.resize((self.w*S, self.h*S), Image.LANCZOS)

def place(c, layer, top, bottom):
    """encaixa a camada de ilustracao (RGBA, em escala S) centralizada entre top e bottom, sem ampliar."""
    im = layer.img; w, h = layer.w, layer.h; k = min(1.0, (bottom-top)/h, 960/w)
    if k < 1: im = im.resize((int(im.width*k), int(im.height*k)), Image.LANCZOS)
    c.paste(im, ((W-w*k)/2, top+(bottom-top-h*k)/2))

def base_slide(i, bg, titulo, cap=112, apoio=None, logo_w=190):
    c = C(bg); flow_curve(c, i); chrome(c, i, logo_w)
    tb = title(c, titulo, cap)
    bt = body_bottom(c, apoio) if apoio else 1214
    return c, tb, bt

def slide1():
    c, tb, bt = base_slide(1, BLUE, ['SEU RESTAURANTE', 'NÃO PRECISA DE', '4 BRAÇOS.'], 124)
    bs = body_bottom(c, 'Salão, delivery, WhatsApp… e você tentando dar conta de tudo?', bottom=tb+150, size=36)
    foto = os.path.join(HERE, 'assets', 'cena_capa.png')
    if os.path.exists(foto): place(c, FotoLayer(foto, 1000, 0.94), tb+170, 1225); return c.out()
    L = C(None, (1080, 640), True); cx, by = 540, 610
    L.ell([cx-300, by-18, cx+300, by+26], fill=(7, 20, 52, 90))
    hands = [(cx-310, by-380), (cx-140, by-300), (cx+140, by-300), (cx+310, by-380)]
    person(L, cx, by, 0.9, arms=hands, shirt=NAVY)
    tray(L, hands[0][0]-85, hands[0][1]-34, 170); phone_small(L, hands[1][0]-48, hands[1][1]-170, 96, 160)
    comanda(L, hands[2][0]-60, hands[2][1]-150, 120, 140); bag(L, hands[3][0]-52, hands[3][1]-100, 104, 90)
    place(c, L, tb+170, 1225); return c.out()

def slide2():
    apoio = 'Alternar entre aplicativos, acompanhar mensagens e conferir pedidos em lugares diferentes pode deixar sua operação muito mais difícil.'
    c, tb, bt = base_slide(2, NAVY, ['UM PEDIDO AQUI.', 'OUTRO ALI.', 'E A CONFUSÃO SÓ AUMENTA.'], 112, apoio)
    L = C(None, (1080, 560), True)
    cards = [(notif_card('Novo pedido', 'Delivery · agora', 'delivery'), (40, 0), -4), (notif_card('Mensagem nova', 'Cliente quer pedir', 'whats'), (520, 120), 4),
             (notif_card('Comanda aberta', 'Salão · mesa', 'salao'), (40, 260), 3), (notif_card('Novo pedido', 'Delivery · agora', 'delivery'), (520, 400), -4)]
    for im, (x, y), deg in cards: L.paste(tilt(im, deg), (x-30, y-30))
    place(c, L, tb+40, bt-30); return c.out()

def slide3():
    apoio = 'Canais diferentes não precisam significar uma operação dividida.'
    c, tb, bt = base_slide(3, BLUE, ['SEUS CLIENTES PEDEM', 'DE VÁRIOS JEITOS.'], 112, apoio)
    rows = [('salao', 'SALÃO', 'Pedidos realizados pelos clientes no estabelecimento.'), ('delivery', 'DELIVERY', 'Pedidos para entrega.'),
            ('whats', 'WHATSAPP', 'Pedidos recebidos pelo aplicativo de mensagens.')]
    L = C(None, (1080, 600), True)
    for i, (k, t, d) in enumerate(rows):
        yy = i*200; L.rr([60, yy, W-60, yy+176], 36, fill=ICE); icon(L, k, 60+98, yy+88, 60, WHITE, NAVY)
        L.text((60+196, yy+78), t, FA(54), NAVY, 'ls'); block(L, (60+196, yy+100), d, F(27, 'Medium'), (50, 80, 140), 640, 1.2)
    place(c, L, tb+40, bt-30); return c.out()

def phone_with_screen(c, x, y, w):
    h = int(w*1.92); c.rr([x-8, y-8+14, x+w+8, y+h+8+14], 40, fill=(0, 0, 0, 60))
    c.rr([x-8, y-8, x+w+8, y+h+8], 40, fill=(12, 16, 30)); c.rr([x-4, y-4, x+w+4, y+h+4], 37, outline=(70, 90, 130), width=2)
    scr = PRINT19.crop((0, 162, 746, 1570)).resize((int(w*S), int(h*S)), Image.LANCZOS)
    m = Image.new('L', scr.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, scr.width-1, scr.height-1], 32*S, fill=255)
    c.img.paste(scr, (int(x*S), int(y*S)), m); return h
def slide4():
    apoio = 'Com a Rango, você organiza seus pedidos em uma plataforma de gestão, facilitando o acompanhamento da operação.'
    c, tb, bt = base_slide(4, NAVY, ['CENTRALIZE A OPERAÇÃO.', 'SIMPLIFIQUE A ROTINA.'], 112, apoio, logo_w=235)
    L = C(None, (1080, 700), True); pw = 330; ph = int(pw*1.92); px, py = 70, 20
    chans = [('salao', 'SALÃO', 70), ('delivery', 'DELIVERY', py+ph/2-290+290-58+0), ('whats', 'WHATSAPP', 480)]
    chans = [('salao', 'SALÃO', 40), ('delivery', 'DELIVERY', 280), ('whats', 'WHATSAPP', 520)]
    for k, t, cy in chans:
        x0, y0 = 660, cy+58
        L.line([(x0+(px+pw+8-x0)*u, y0+(py+ph/2-y0)*(3*u*u-2*u**3)) for u in np.linspace(0, 1, 40)], SKY, 5)
    phone_with_screen(L, px, py, pw); L.ell([px+pw-4, py+ph/2-9, px+pw+14, py+ph/2+9], fill=WHITE)
    for k, t, cy in chans:
        L.rr([660, cy, 1030, cy+116], 30, fill=ICE); icon(L, k, 660+62, cy+58, 40, WHITE, BLUE); L.text((660+118, cy+70), t, FA(40), NAVY, 'lm')
    place(c, L, tb+30, bt-20); return c.out()

def slide5():
    apoio = 'Mais organização para acompanhar os pedidos, mais clareza para a equipe e mais tempo para cuidar do seu negócio.'
    c, tb, bt = base_slide(5, BLUE, ['VOCÊ NÃO PRECISA', 'SE DESDOBRAR PARA', 'ATENDER BEM.'], 112, apoio)
    foto = os.path.join(HERE, 'assets', 'cena_equipe.png')
    if os.path.exists(foto): place(c, FotoLayer(foto, 1000, 0.66), tb+40, bt-20); return c.out()
    L = C(None, (1080, 560), True); by = 530
    L.rr([60, by-6, W-60, by+30], 18, fill=(7, 20, 52, 120))
    person(L, 210, by, 0.95, arms=[(210-90, by-330)], calm=True, shirt=NAVY); tray(L, 210-165, by-345, 150)
    person(L, 430, by, 0.95, arms=[(430+60, by-300)], calm=True, shirt=NAVY); comanda(L, 430+62, by-420, 90, 112)
    person(L, 650, by, 0.95, arms=[(650+60, by-300)], calm=True, shirt=NAVY); bag(L, 650+36, by-390, 88, 80)
    person(L, 890, by, 1.05, arms=[(890-90, by-325)], calm=True, shirt=WHITE)
    L.rr([890-190, by-470, 890-50, by-360], 14, fill=DEEP, outline=SKY, width=3); L.line([(890-168, by-412), (890-138, by-386), (890-80, by-444)], SKY, 8)
    place(c, L, tb+40, bt-20); return c.out()

def slide6():
    apoio = 'Salão, delivery e WhatsApp dentro de uma rotina de gestão mais simples, com a Rango apoiando o dia a dia da sua equipe.'
    c, tb, bt = base_slide(6, NAVY, ['SEUS CANAIS CONECTADOS.', 'SUA GESTÃO MAIS', 'ORGANIZADA.'], 112, apoio)
    L = C(None, (1080, 600), True); px0, px1 = 450, 1020
    for i, (k, t) in enumerate([('salao', 'SALÃO'), ('delivery', 'DELIVERY'), ('whats', 'WHATSAPP')]):
        cy = 70+i*180
        for off, a in ((0, 230), (16, 110)):
            L.line([(150+(px0-150)*u, cy+((90+i*170+off)-cy)*(3*u*u-2*u**3)) for u in np.linspace(0, 1, 50)], (140, 200, 255, a), 5)
        icon(L, k, 100, cy, 52, WHITE, BLUE); L.text((100, cy+70), t, F(22, 'ExtraBold'), ICE, 'ma')
    L.rr([px0, 0, px1, 560], 36, fill=ICE); L.text((px0+34, 62), 'PAINEL ÚNICO', FA(42), NAVY, 'ls')
    for i in range(3):
        yy = 90+i*152; L.rr([px0+24, yy, px1-24, yy+130], 22, fill=WHITE); icon(L, ['salao', 'delivery', 'whats'][i], px0+24+64, yy+65, 38, WHITE, BLUE)
        L.rr([px0+24+128, yy+32, px1-24-80, yy+50], 9, fill=(30, 70, 140)); L.rr([px0+24+128, yy+72, px1-24-190, yy+88], 8, fill=(160, 190, 235))
        L.ell([px1-24-56, yy+44, px1-24-24, yy+76], fill=BLUE)
    L.text((px0, 578), 'Ilustração conceitual', F(20, 'Medium'), SKY)
    place(c, L, tb+40, bt-20); return c.out()

def slide7():
    c = C(BLUE); c.d.ellipse([-260*S, -300*S, 900*S, 760*S], fill=(255, 255, 255, 18)); flow_curve(c, 7); chrome(c, 7, last=True)
    lw = 520; lh = LOGO.height*lw/LOGO.width; c.paste(LOGO.resize((int(lw*S), int(lh*S)), Image.LANCZOS), ((W-lw)/2, 170))
    tb = title(c, ['PARE DE CORRER ATRÁS', 'DOS PEDIDOS.', 'ORGANIZE SUA OPERAÇÃO.'], 104, top=170+lh+40, align='center')
    f = F(33, 'Medium'); y = tb+26
    for ln in wrap('Conheça a Rango e descubra uma nova maneira de gerenciar seu estabelecimento.', f, 860):
        c.text((W/2, y), ln, f, ICE, 'ma'); y += 44
    fb = FA(54); t = 'FALE COM A RANGO.'; bw = fb.getlength(t)/S+130; bx = (W-bw)/2; by = y+30
    c.rr([bx, by+8, bx+bw, by+138], 65, fill=(7, 20, 52, 90)); c.rr([bx, by, bx+bw, by+122], 61, fill=WHITE)
    c.text((bx+50, by+61), t, fb, NAVY, 'lm'); ax = bx+bw-52; c.poly([(ax, by+43), (ax+28, by+61), (ax, by+79)], BLUE)
    c.text((W/2, 1196), 'RANGO — MENOS CORRERIA. MAIS CONTROLE.', FA(42), WHITE, 'ms')
    return c.out()

if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'slides'), exist_ok=True)
    for i, fn in enumerate([slide1, slide2, slide3, slide4, slide5, slide6, slide7], 1):
        fn().save(os.path.join(HERE, 'slides', f'slide_{i:02d}.png')); print('ok', i)
