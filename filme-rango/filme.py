"""Filme de produto Rango — navegacao realista pelo menu lateral, cursor humano e camera dirigida.
Interface = prints reais do Rango (sem recriar telas). Menu, destaque azul claro e rolagens vem de ../anuncio-rango/rango_ui.py.
Somente modulos cujo item aparece no menu real dos prints sao navegados: Dashboard, Lancar Venda, Pedidos / Delivery,
Historico de Vendas, Receitas e Produtos e Estoque.
Uso: python3 -I filme.py [saida.mp4]     (1080x1920, 30 fps, sem audio)"""
import os, sys, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'rango_filme.mp4')
sys.argv = [sys.argv[0], '/tmp/_unused.mp4']                       # os modulos importados leem argv[1]
sys.path.insert(0, os.path.join(HERE, '..', 'anuncio-rango'))
import anuncio as A                                                # telas reais (PA), rolagens, logo, fontes
import anuncio_iphone as I                                         # molde do iPhone + fundo azul animado
import rango_ui as ui
W, H, FPS = 1080, 1920, 30
ease, eo, seg, lerp = A.ease, A.eo, A.seg, A.lerp
P = ui.P

# ------------------------------------------------------------------ relogio e saida
ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                       '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
FR = [0]
def now(): return FR[0]/FPS
def n(sec): return max(1, int(round(sec*FPS)))

# ------------------------------------------------------------------ camera (animacao concorrente, easing suave)
class Cam:
    def __init__(s): s.z, s.cx, s.cy = 1.0, W/2, H/2; s.a = (1.0, W/2, H/2); s.b = s.a; s.t0, s.d = 0, 0.001
    def goto(s, z, cx, cy, dur): s.a = s.value(); s.b = (z, cx, cy); s.t0 = now(); s.d = dur
    def value(s):
        k = ease(min(max((now()-s.t0)/s.d, 0), 1)); return tuple(lerp(a, b, k) for a, b in zip(s.a, s.b))
CAM = Cam()
def camera(img):
    z, cx, cy = CAM.value()
    cx = min(max(cx, W/(2*z)), W-W/(2*z)); cy = min(max(cy, H/(2*z)), H-H/(2*z))
    if abs(z-1) < 1e-4 and abs(cx-W/2) < .5 and abs(cy-H/2) < .5: return img
    return img.transform((W, H), Image.AFFINE, (1/z, 0, cx-W/(2*z), 0, 1/z, cy-H/(2*z)), Image.BICUBIC)

# ------------------------------------------------------------------ cursor (seta de sistema, movimento humano)
def _arrow():
    S4 = 4; pts = [(0, 0), (0, 17), (4.2, 13.2), (7.2, 19.6), (9.8, 18.4), (6.9, 12.2), (12.2, 12.0)]
    sprite = Image.new('RGBA', (34*S4, 40*S4), (0, 0, 0, 0)); d = ImageDraw.Draw(sprite)
    sh = Image.new('RGBA', sprite.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).polygon([(x*S4*1.9+5*S4, y*S4*1.9+5*S4) for x, y in pts], fill=(0, 10, 40, 110)); sh = sh.filter(ImageFilter.GaussianBlur(3*S4))
    poly = [(x*S4*1.9+3*S4, y*S4*1.9+3*S4) for x, y in pts]; sprite = Image.alpha_composite(sprite, sh); d = ImageDraw.Draw(sprite)
    d.polygon(poly, fill=(14, 18, 28, 255)); inner = [(x*S4*1.9+3*S4+(3.2*S4 if x > 0 else 0), y*S4*1.9+3*S4+(5*S4 if y > 0 else 0)) for x, y in pts]
    d.polygon(poly, fill=(255, 255, 255, 255)); d.line(poly+[poly[0]], fill=(14, 18, 28, 255), width=int(2.6*S4), joint='curve')
    return sprite.resize((34, 40), Image.LANCZOS), (3, 3)
ARROW, HOT = _arrow()
class Cur:
    x, y, vis, press, click_t = 0.0, 0.0, 0.0, 0.0, -9.0                 # coordenadas do app (746x1408)
CUR = Cur()
SCR_S = I.SW/746.0
def app_to_canvas(x, y): return I.SX0+x*SCR_S, I.SY0+I.STRIP_H+y*SCR_S
def draw_cursor(img):
    if CUR.vis <= 0.01: return
    cx, cy = app_to_canvas(CUR.x, CUR.y)
    age = now()-CUR.click_t
    if 0 <= age < 0.42:                                                  # clique discreto: anel fino que se dissolve
        k = age/0.42; r = 10+22*eo(k); a = int(150*(1-k)); ring = Image.new('RGBA', (90, 90), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([45-r, 45-r, 45+r, 45+r], outline=(255, 255, 255, a), width=2); img.paste(ring, (int(cx-45), int(cy-45)), ring)
    sc = 1-0.10*CUR.press; spr = ARROW if abs(sc-1) < .01 else ARROW.resize((max(1, int(34*sc)), max(1, int(40*sc))), Image.LANCZOS)
    if CUR.vis < 1: spr = spr.copy(); spr.putalpha(spr.getchannel('A').point(lambda v: int(v*CUR.vis)))
    img.paste(spr, (int(cx-HOT[0]*sc), int(cy-HOT[1]*sc)), spr)

# ------------------------------------------------------------------ cena: estado + composicao
ST = dict(appf=A.PA[2], enter=1.0, dy=0, intro=0.0, outro=0.0)
def frame_img():
    t = now(); img = I.bg_at(min(t, 79.0)).copy()
    if ST['outro'] < 1.0:
        I.draw_phone(img, np.ascontiguousarray(ST['appf']), t, enter=ST['enter'], dy=int(ST['dy']))
        draw_cursor(img)
    img = camera(img)
    return img
SNAP = {int(float(x)*FPS) for x in os.environ.get('SNAP', '').split(',') if x}
def emit(img=None):
    img = img if img is not None else frame_img()
    if FR[0] in SNAP: img.convert('RGB').resize((540, 960)).save(f'/tmp/snap_{FR[0]/FPS:05.1f}.png')
    ff.stdin.write(np.asarray(img.convert('RGB')).tobytes()); FR[0] += 1
def hold(sec, fn=None):
    for _ in range(n(sec)):
        if fn: fn()
        emit()

# ------------------------------------------------------------------ movimento humano do cursor
def move_cursor(x, y, dur=None, arc=0.10):
    x0, y0 = CUR.x, CUR.y; dist = math.hypot(x-x0, y-y0); dur = dur or min(1.15, 0.38+dist/900)
    nx, ny = -(y-y0), (x-x0); L = max(math.hypot(nx, ny), 1); sgn = 1 if (x0+y0) % 2 < 1 else -1
    cxp, cyp = (x0+x)/2+sgn*nx/L*dist*arc, (y0+y)/2+sgn*ny/L*dist*arc
    k = n(dur)
    for i in range(1, k+1):
        u = i/k; e = u*u*u*(u*(u*6-15)+10)                                # minimum-jerk: sai devagar, chega devagar
        CUR.x = (1-e)**2*x0+2*(1-e)*e*cxp+e*e*x; CUR.y = (1-e)**2*y0+2*(1-e)*e*cyp+e*e*y; emit()
    CUR.x, CUR.y = x, y
def settle(sec=0.16): hold(sec)                                          # pequena pausa antes de agir
def click():
    CUR.press = 1.0; CUR.click_t = now()
    for i in range(n(0.12)): CUR.press = 1.0; emit()
    CUR.press = 0.0
def show_cursor(x, y):
    CUR.x, CUR.y = x, y
    for i in range(n(0.35)): CUR.vis = (i+1)/n(0.35); emit()
def hide_cursor():
    for i in range(n(0.3)): CUR.vis = 1-(i+1)/n(0.3); emit()

# ------------------------------------------------------------------ menu lateral real: abrir, escolher, destacar, fechar
HAMB = (54, 50)                                                          # botao do menu (coords do app)
def blend(a, b, p): p = ease(p); return np.clip(a.astype(float)*(1-p)+b.astype(float)*p, 0, 255).astype(np.uint8)
def app_of(frame_print): return frame_print[162:1570]
def navigate(src, src_key, dst, dst_key, ms=0, cam_menu=(1.22, 540, 800), cam_after=(1.14, 540, 900), dst_page=None):
    """src/dst: prints (1600x746). O app mostra o proprio menu e destaque; apenas o cursor e a camera sao nossos."""
    CAM.goto(1.30, 480, 640, 0.9); move_cursor(*HAMB, dur=1.0); settle(0.2); click()
    k = n(0.34)
    for i in range(1, k+1):
        pr = eo(i/k); ST['appf'] = app_of(ui.render(src, scrim=pr, menu=dict(prog=pr, ms=0, act=[(src_key, 1)])))
        if i == 1: CAM.goto(*cam_menu, 0.7)
        emit()
    base_menu = lambda act, bs=src, m=ms: app_of(ui.render(bs, scrim=1, menu=dict(prog=1, ms=m, act=act)))
    ST['appf'] = base_menu([(src_key, 1)]); hold(0.7)
    if ms:
        k = n(0.5)
        for i in range(1, k+1): ST['appf'] = app_of(ui.render(src, scrim=1, menu=dict(prog=1, ms=ms*ease(i/k), act=[(src_key, 1)]))); emit()
        hold(0.25)
    yi = ui.ROWS[dst_key]-ms
    move_cursor(250, yi, dur=0.95); settle(0.28)
    ST['appf'] = base_menu([(src_key, 1)]); click()
    k = n(0.30)
    for i in range(1, k+1):                                              # destaque migra para o novo item; conteudo comeca a trocar por baixo
        e = ease(i/k); act = [(src_key, 1-e), (dst_key, e)] if src_key != dst_key else [(dst_key, 1)]
        ST['appf'] = app_of(ui.render(blend(src, dst, e), scrim=1, menu=dict(prog=1, ms=ms, act=act))); emit()
    hold(0.18); CAM.goto(*cam_after, 1.2)
    k = n(0.34)
    for i in range(1, k+1):
        pr = 1-ease(i/k); ST['appf'] = app_of(ui.render(dst, scrim=pr, menu=dict(prog=pr, ms=ms, act=[(dst_key, 1)]))); emit()
    ST['appf'] = app_of(dst)
    move_cursor(640, 760, dur=0.8, arc=0.06)                             # cursor sai de cima do conteudo

def scroll_through(sc, sec=1.3, ptr=(620, 800)):
    k = n(sec)
    for i in range(1, k+1): ST['appf'] = sc.at(i/k); emit()
def pulse_cam(z, cx, cy, dur=1.1): CAM.goto(z, cx, cy, dur)

# ------------------------------------------------------------------ abertura de marca
def intro_frame(t):
    base = Image.fromarray(A.gradient(A.NAVY, (4, 14, 40)))
    k = ease(seg(t, 0.0, 1.4)); br = Image.fromarray(A.gradient((26, 108, 236), (7, 38, 112), diag=True)); base = Image.blend(base, br, 0.55*k)
    d = ImageDraw.Draw(base, 'RGBA')
    la = eo(seg(t, 0.25, 1.05)); lw = int(lerp(700, 760, ease(seg(t, 0, 2.6)))); lg = A.logo_at(lw)
    cx, cy = W//2, H//2-60
    for i in range(5):                                                   # conexoes discretas convergindo para a marca (sem icones)
        ang = math.radians(-90+i*72); r0, r1 = 520, 330; a = int(120*seg(t, 0.7+i*0.07, 1.4+i*0.07)*(1-seg(t, 2.2, 2.7)))
        p0 = (cx+math.cos(ang)*lerp(r0, r1, ease(seg(t, 0.7+i*0.07, 1.6))), cy+math.sin(ang)*lerp(r0, r1, ease(seg(t, 0.7+i*0.07, 1.6))))
        p1 = (cx+math.cos(ang)*(r1-60), cy+math.sin(ang)*(r1-60)*0.9)
        d.line([p0, p1], fill=(140, 200, 255, a), width=3); d.ellipse([p0[0]-6, p0[1]-6, p0[0]+6, p0[1]+6], fill=(140, 200, 255, a))
    gl = Image.new('RGBA', (lw+400, lg.height+400), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([80, 80, gl.width-80, gl.height-80], fill=(120, 190, 255, int(60*la)))
    gl = gl.filter(ImageFilter.GaussianBlur(80)); base.paste(gl, (cx-gl.width//2, cy-gl.height//2), gl)
    out = seg(t, 2.25, 2.95)
    A.put_rgba(base, lg, cx-lg.width//2, cy-lg.height//2+int((1-la)*28)-int(ease(out)*120), la*(1-ease(out)))
    return base

# ================================================================== ROTEIRO
def main():
    # --- 1) abertura da marca (3,0 s) e entrada do produto
    for i in range(n(2.1)): emit(intro_frame(now()))
    ST['enter'] = 0.0; CAM.goto(1.0, W/2, H/2, 0.01)
    k = n(1.5)
    for i in range(k):
        t = i/FPS; img = intro_frame(2.1+t) if t < 0.6 else None
        ST['enter'] = min(1, max(0, (t-0.1)/1.2)); base = I.bg_at(now()).copy()
        I.draw_phone(base, np.ascontiguousarray(ST['appf']), now(), enter=ST['enter'])
        if img is not None:
            a = 1-ease(seg(t, 0.0, 0.6)); base = Image.blend(base, img.resize(base.size), a)
        emit(base)
    ST['enter'] = 1.0
    # --- 2) apresentacao da interface (estavel para leitura)
    CAM.goto(1.06, W/2, H/2-10, 2.2); hold(2.4)
    pulse_cam(1.22, 540, 700, 1.3); hold(1.6)                            # olhar para os cartoes do Dashboard
    show_cursor(560, 1020)
    # --- 3) Dashboard -> Lancar Venda (abre o menu, primeira navegacao)
    navigate(P[2], 'dashboard', P[5], 'lancar')
    # --- 4) Lancar Venda: rolagem real ate o carrinho
    pulse_cam(1.12, 540, 880, 0.9); hold(1.0)
    scroll_through(A.SC_LANC, 1.5); hold(1.5)
    navigate(P[6], 'lancar', P[19], 'pedidos')
    # --- 5) Pedidos / Delivery: lista e rolagem ate o pedido confirmado
    hold(1.3); scroll_through(A.SC_PED, 1.3); ST['appf'] = A.PA[18]; hold(1.7)
    navigate(P[18], 'pedidos', P[16], 'historico')
    # --- 6) Historico de Vendas: filtro "Hoje"
    hold(1.4); pulse_cam(1.28, 540, 700, 1.0)
    move_cursor(167, 251, dur=0.9); settle(0.25); click()
    ST['appf'] = A.PA[17]; hold(0.08); hold(1.8)
    navigate(P[17], 'historico', P[15], 'receitas')
    # --- 7) Receitas: abre o formulario de nova receita e fecha
    hold(1.3); move_cursor(651, 391, dur=0.95); settle(0.25); click()
    k = n(0.42)
    for i in range(1, k+1): ST['appf'] = app_of(_modal(P[15], P[14], eo(i/k))); emit()
    hold(1.6); move_cursor(693, 53, dur=0.9); settle(0.22); click()
    k = n(0.34)
    for i in range(1, k+1): ST['appf'] = app_of(_modal(P[15], P[14], 1-ease(i/k))); emit()
    hold(0.5)
    navigate(P[15], 'receitas', P[13], 'produtos', ms=100)
    # --- 8) Produtos e Estoque
    hold(2.6)
    hide_cursor()
    # --- 9) encerramento: camera recua, aparelho sai, marca assina
    CAM.goto(1.0, W/2, H/2, 1.2); hold(0.8)
    k = n(1.3)
    for i in range(1, k+1):
        e = ease(i/k); ST['dy'] = e*1900; emit()
    ST['outro'] = 1.0
    k = n(2.2)
    for i in range(k):
        t = i/FPS; base = I.bg_at(now()).copy(); la = eo(seg(t, 0.1, 0.9)); lg = A.logo_at(760)
        A.put_rgba(base, lg, (W-lg.width)//2, 640+int((1-la)*26), la)
        a = eo(seg(t, 0.9, 1.5))
        if a > 0:
            f = A.font(46, 'SemiBold'); im = Image.new('RGBA', (W, 80), (0, 0, 0, 0)); ImageDraw.Draw(im).text((W//2, 8), 'Rango. Sua operação, conectada.', font=f, fill=A.ICE+(255,), anchor='mt')
            A.put_rgba(base, im, 0, 640+lg.height+40+int((1-a)*14), a)
        emit(base)
    for i in range(n(1.6)): emit(base)
    ff.stdin.close(); ff.wait(); print('ok', OUT, round(FR[0]/FPS, 1), 's')

def _modal(page, shot, pr):
    """formulario sobe/desce sobre a pagina (mesma logica do app); pr 0..1"""
    f = page.astype(float); T_, B_ = ui.TOP, ui.BOT; y0 = 1
    f[T_:B_] = f[T_:B_]*(1-ui.SCRIM_A*pr)+ui.SCRIM_C*(ui.SCRIM_A*pr)
    off = int((B_-T_)*(1-pr)); mdl = shot[T_:B_].astype(float)
    if off < B_-T_: f[T_+off:B_] = mdl[:B_-T_-off]
    return np.clip(f, 0, 255).astype(np.uint8)

if __name__ == '__main__':
    main()
