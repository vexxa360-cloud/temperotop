"""Cenas 3D do carrossel (Blender/Cycles via bpy): pessoas atras do balcao + maquininha de cartao azul.
Uso: python cena_blender.py <capa|equipe> <saida.png> [largura] [amostras]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Vector
import pessoas3d as P3

CENA, OUT = sys.argv[1], sys.argv[2]
RW = int(sys.argv[3]) if len(sys.argv) > 3 else 1600; SAMPLES = int(sys.argv[4]) if len(sys.argv) > 4 else 96
RATIO = {'capa': 0.70, 'equipe': 0.52}[CENA]; RH = int(RW*RATIO)
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; col = sc.collection

def lin(c):                                              # sRGB 0-255 -> linear
    return tuple(((v/255+0.055)/1.055)**2.4 if v/255 > 0.04045 else v/255/12.92 for v in c)
def mat(name, rgb, rough=0.4, metal=0.0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(rgb), 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    for k, v in kw.items():
        if k.replace('_', ' ') in b.inputs: b.inputs[k.replace('_', ' ')].default_value = v
    return m
SKINS = {'clara': (232, 178, 148), 'tan': (196, 138, 104), 'parda': (150, 98, 70), 'negra': (96, 62, 46)}
HAIRS = {'preto': (22, 16, 14), 'castanho': (62, 38, 24), 'loiro': (150, 112, 62)}
BLUE, NAVY, ICE = (21, 96, 229), (12, 32, 84), (232, 241, 255)

def add_mesh(name, vf, m):
    v, f = vf; me = bpy.data.meshes.new(name); me.from_pydata(v.tolist(), [], f.tolist()); me.update()
    o = bpy.data.objects.new(name, me); col.objects.link(o); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.shade_smooth(); o.data.materials.append(m)
    mod = o.modifiers.new('sm', 'SMOOTH'); mod.factor = 0.5; mod.iterations = 3; bpy.ops.object.modifier_apply(modifier='sm'); o.select_set(False); return o

def build_person(spec):
    parts = P3.person(spec); sk = mat('pele', SKINS[spec['skin']], 0.42, Subsurface_Weight=0.22, Subsurface_Radius=(1.0, 0.35, 0.2), Specular_IOR_Level=0.5)
    hc = HAIRS[spec.get('haircolor', 'castanho')]
    M = {'pele': sk, 'camisa': mat('camisa', spec.get('shirt', NAVY), 0.75, Sheen_Weight=0.3), 'avental': mat('avental', spec.get('apron_c', (244, 247, 252)), 0.7),
         'cabelo': mat('cabelo', hc, 0.45, Specular_IOR_Level=0.6), 'barba': mat('barba', hc, 0.7), 'sobrancelhas': mat('sob', hc, 0.6),
         'labios': mat('labios', tuple(int(c*0.8) for c in (205, 110, 110)), 0.35), 'olhos': mat('olho', (250, 250, 250), 0.08), 'iris': mat('iris', (38, 22, 14), 0.1)}
    for k, vf in parts.items(): add_mesh(f"{k}_{spec['x']}", vf, M[k])

def box(name, loc, size, m, rot=(0, 0, 0), bevel=0.004):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot); o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel: b = o.modifiers.new('b', 'BEVEL'); b.width = bevel; b.segments = 4; b.limit_method = 'ANGLE'; bpy.ops.object.modifier_apply(modifier='b')
    bpy.ops.object.shade_smooth(); o.data.materials.append(m); return o

def card_machine(x, y, z_base, yaw_deg=0, tilt_deg=62, scale=1.0):
    """maquininha de cartao azul em pe sobre o balcao; (0,0,0) local = centro da base."""
    blue = mat('maq', BLUE, 0.22, Coat_Weight=0.6, Coat_Roughness=0.05); dark = mat('maq_tela', (10, 14, 28), 0.08); keys = mat('maq_tecla', (236, 242, 252), 0.35)
    w, hh, d = 0.080, 0.165, 0.024
    root = bpy.data.objects.new('maq_root', None); col.objects.link(root); root.location = (x, y, z_base+0.003); root.rotation_euler = (math.radians(-(90-tilt_deg)), 0, math.radians(yaw_deg)); root.scale = (scale, scale, scale)
    parts = [box('corpo', (0, 0, hh/2), (w, d, hh), blue, bevel=0.007), box('tela', (0, -d/2-0.0004, hh*0.72), (w*0.80, 0.002, hh*0.26), dark, bevel=0.002),
             box('fenda', (0, -d/2-0.0003, hh*0.55), (w*0.55, 0.0016, 0.006), dark, bevel=0.0008)]
    for r in range(4):
        for cidx in range(3):
            parts.append(box(f'k{r}{cidx}', ((cidx-1)*0.021, -d/2-0.0008, hh*0.40-r*0.0265), (0.016, 0.003, 0.0155), keys, bevel=0.0012))
    parts.append(box('ok', (0.021, -d/2-0.0008, hh*0.40-4*0.0265+0.0005), (0.016, 0.003, 0.0155), mat('maq_ok', (60, 200, 140), 0.35), bevel=0.0012))
    # tela "pagamento": faixa clara
    parts.append(box('tela_l', (0, -d/2-0.0016, hh*0.755), (w*0.60, 0.0006, 0.006), mat('maq_led', (130, 190, 255), 0.2, Emission_Strength=1.2, Emission_Color=lin((120, 190, 255)) + (1,)), bevel=0.0003))
    for p in parts: p.parent = root
    return root

def phone(loc, rot, w=0.072, h=0.150):
    body = mat('cel', (12, 14, 20), 0.15); scr = mat('cel_tela', (210, 230, 255), 0.1, Emission_Strength=0.9, Emission_Color=lin((150, 200, 255)) + (1,))
    b = box('cel', loc, (w, 0.009, h), body, rot, 0.004); s = box('cel_s', loc, (w*0.92, 0.0095, h*0.94), scr, rot, 0.003)
    return b

def counter(x0=-1.9, x1=1.9):
    topm = mat('balcao_topo', (214, 228, 250), 0.3); frontm = mat('balcao_frente', (12, 40, 110), 0.5, Coat_Weight=0.3)
    box('topo', ((x0+x1)/2, -0.46, 1.0), (x1-x0, 0.62, 0.05), topm, bevel=0.01)
    box('frente', ((x0+x1)/2, -0.74, 0.50), (x1-x0, 0.05, 1.0), frontm, bevel=0.006)
    box('faixa', ((x0+x1)/2, -0.7655, 0.84), (x1-x0, 0.003, 0.05), mat('faixa', (140, 200, 255), 0.4, Emission_Strength=0.4, Emission_Color=lin((120, 190, 255)) + (1,)), bevel=0.0)

def delivery_bag(x, y, z0=1.025, s=1.0):
    bm = mat('sacola', (236, 244, 255), 0.5); st = mat('sacola_f', BLUE, 0.4)
    box('sacola', (x, y, z0+0.13*s), (0.26*s, 0.19*s, 0.26*s), bm, bevel=0.012); box('sacola_f', (x, y-0.0965*s, z0+0.135*s), (0.262*s, 0.004, 0.06*s), st, bevel=0.002)
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.05*s, minor_radius=0.006, location=(x+sx*0.06*s, y, z0+0.30*s), rotation=(math.pi/2, 0, 0)); t = bpy.context.active_object; t.data.materials.append(st); bpy.ops.object.shade_smooth()

def paper(loc, size, rot=(0, 0, 0)):
    pm = mat('papel', (252, 252, 250), 0.6); b = box('papel', loc, size, pm, rot, 0.0008)
    for k in range(5):
        box('linha', (loc[0], loc[1]-size[1]/2-0.0004, loc[2]+size[2]*0.34-k*size[2]*0.17), (size[0]*0.7, 0.0004, 0.004), mat('tinta', (40, 60, 110), 0.7), rot, 0.0)

# --------------------------------------------------------------------- cenas
counter()
if CENA == 'capa':
    build_person(dict(x=0.0, skin='parda', hair='short', haircolor='preto', beard=True, mood='stress', shirt=NAVY,
                      lwrist=(-0.27, -0.29, 1.24), rwrist=(0.165, -0.07, 1.60)))
    phone((0.125, -0.040, 1.64), (0, 0, math.radians(-8)))
    paper((-0.31, -0.31, 1.31), (0.10, 0.003, 0.14), (math.radians(-6), 0, math.radians(14)))
    card_machine(0.52, -0.44, 1.025, yaw_deg=-12, scale=1.9); delivery_bag(-0.80, -0.42, s=1.0)
    cam_loc, cam_tgt, lens = (0, -3.7, 1.42), (0, 0, 1.33), 85
else:
    specs = [dict(x=-0.95, skin='tan', hair='bun', haircolor='castanho', shirt=NAVY, mood='calm', lwrist=(-1.05, -0.32, 1.06), rwrist=(-0.86, -0.40, 1.20)),
             dict(x=-0.32, skin='clara', hair='short', haircolor='loiro', shirt=NAVY, mood='calm', lwrist=(-0.42, -0.30, 1.07), rwrist=(-0.20, -0.33, 1.18)),
             dict(x=0.32, skin='negra', hair='long', haircolor='preto', shirt=NAVY, mood='calm', lwrist=(0.22, -0.30, 1.07), rwrist=(0.34, -0.40, 1.15)),
             dict(x=1.0, skin='parda', hair='short', haircolor='preto', beard=True, shirt=BLUE, apron=False, mood='calm', lwrist=(0.93, -0.22, 1.32), rwrist=(1.14, -0.22, 1.30))]
    for sp in specs: build_person(sp)
    delivery_bag(-0.70, -0.40, s=0.9); paper((-0.12, -0.37, 1.10), (0.10, 0.003, 0.13), (math.radians(-70), 0, 0))
    card_machine(0.52, -0.42, 1.025, yaw_deg=-8, scale=1.8)
    box('tablet', (1.04, -0.30, 1.34), (0.20, 0.008, 0.14), mat('tablet', (14, 18, 28), 0.1), (math.radians(-12), 0, math.radians(-6)), 0.006)
    box('tablet_s', (1.04, -0.3055, 1.34), (0.185, 0.0035, 0.127), mat('tablet_s', (200, 225, 255), 0.1, Emission_Strength=0.8, Emission_Color=lin((150, 200, 255)) + (1,)), (math.radians(-12), 0, math.radians(-6)), 0.004)
    cam_loc, cam_tgt, lens = (0, -6.0, 1.42), (0.03, 0, 1.30), 62

# luzes + camera + render
def area(name, loc, power, size, color=(1, 1, 1), tgt=(0, 0, 1.3)):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = power; d.size = size; d.color = color
    o = bpy.data.objects.new(name, d); col.objects.link(o); o.location = loc; o.rotation_euler = (Vector(tgt)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
area('key', (-2.6, -3.2, 3.6), 380, 3.0, (1.0, 0.97, 0.94)); area('fill', (3.0, -4.0, 1.8), 110, 4.0, (0.92, 0.96, 1.0)); area('rim', (1.8, 2.8, 2.6), 300, 2.0, (0.75, 0.88, 1.0))
area('top', (0.0, -1.0, 3.8), 110, 2.5, (1, 1, 1))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; bgn = w.node_tree.nodes['Background']; bgn.inputs['Color'].default_value = (0.75, 0.86, 1.0, 1); bgn.inputs['Strength'].default_value = 0.18
cam = bpy.data.cameras.new('cam'); cam.lens = lens; co = bpy.data.objects.new('cam', cam); col.objects.link(co); sc.camera = co
co.location = cam_loc; co.rotation_euler = (Vector(cam_tgt)-Vector(cam_loc)).to_track_quat('-Z', 'Y').to_euler()
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 6
sc.render.film_transparent = True; sc.render.resolution_x = RW; sc.render.resolution_y = RH; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'; sc.render.filepath = OUT
sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.1
bpy.ops.render.render(write_still=True)
