"""Cofrinho de ceramica esmaltada + moeda de 1 real (Blender/Cycles via bpy). Saida: PNG RGBA com sombra de contato.
Uso: python cofrinho_blender.py saida.png [largura] [amostras]"""
import bpy, bmesh, sys, math
from mathutils import Vector, Euler, Quaternion

OUT = sys.argv[1]; RW = int(sys.argv[2]) if len(sys.argv) > 2 else 1080; SAMPLES = int(sys.argv[3]) if len(sys.argv) > 3 else 128
RH = RW

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
col = sc.collection

def mat(name, base, rough=0.3, metal=0.0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*base, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    for k, v in kw.items():
        if k in b.inputs: b.inputs[k].default_value = v
    return m

# ---------------------------------------------------------------- cofrinho: campo de distancia (uniao suave) + marching cubes
import numpy as np
from skimage.measure import marching_cubes
H_ = 0.016
xs = np.arange(-2.25, 1.65, H_); ys = np.arange(-1.30, 1.30, H_); zs = np.arange(-1.12, 1.40, H_)
X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij'); P = np.stack([X, Y, Z], -1)

def ell(c, r, rot=None):
    p = P-np.array(c)
    if rot is not None: p = p@rot.T
    q = p/np.array(r); return (np.sqrt((q**2).sum(-1))-1.0)*min(r)*0.9
def capsule(a, b_, rad):
    a = np.array(a); b_ = np.array(b_); pa = P-a; ba = b_-a
    h = np.clip((pa@ba)/(ba@ba), 0, 1); return np.linalg.norm(pa-h[..., None]*ba, axis=-1)-rad
def smin(d1, d2, k):
    h = np.clip(0.5+0.5*(d2-d1)/k, 0, 1); return d2*(1-h)+d1*h-k*h*(1-h)
def smax(d1, d2, k): return -smin(-d1, -d2, k)
def rotx(a): c, s_ = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])
def roty(a): c, s_ = math.cos(a), math.sin(a); return np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])

d = ell((0, 0, 0), (1.28, 1.0, 0.97))                                   # corpo
d = smin(d, ell((-1.05, 0, 0.20), (0.72, 0.70, 0.68)), 0.30)             # cabeca
d = smin(d, ell((-1.56, 0, 0.06), (0.42, 0.37, 0.33)), 0.22)             # base do focinho
sn = np.maximum(np.sqrt((Y)**2+(Z-0.06)**2)-0.31, np.abs(X+1.83)-0.09)  # disco do focinho (cilindro arredondado)
d = smin(d, sn-0.05, 0.06)
for sy in (-1, 1):
    ear = ell((-0.86, sy*0.44, 0.84), (0.14, 0.27, 0.36), rot=rotx(sy*0.60)@roty(0.10))
    d = smin(d, ear, 0.12)                                              # orelhas
    for x0 in (-0.78, 0.80):                                            # patas
        d = smin(d, capsule((x0, sy*0.60, -0.50), (x0, sy*0.62, -0.84), 0.31), 0.22)
d = smax(d, -(Z+1.0), 0.02)                                            # base plana das patas
tail = None
for i in range(0, 14):                                                  # rabinho enrolado
    t0, t1 = i*0.38, (i+1)*0.38; f = lambda t: np.array([1.28+0.10*math.sin(t)-0.0, 0.0+0.14*math.cos(t)*0+0.0, 0.34+0.09*t+0.06*math.cos(t)])
    c = capsule(f(t0), f(t1), 0.05); tail = c if tail is None else np.minimum(tail, c)
d = smin(d, tail, 0.10)
# fenda do cofrinho (caixa arredondada subtraida) e narinas
q = np.abs(P-np.array([0.12, 0, 1.00]))-np.array([0.38, 0.042, 0.30])
slot = np.linalg.norm(np.maximum(q, 0), axis=-1)+np.minimum(np.max(q, -1), 0)-0.02
d = smax(d, -slot, 0.02)
for sy in (-1, 1): d = smax(d, -ell((-1.91, sy*0.120, 0.075), (0.11, 0.050, 0.085)), 0.02)
verts, faces, normals, _ = marching_cubes(d, 0.0, spacing=(H_, H_, H_)); verts += np.array([xs[0], ys[0], zs[0]])
me = bpy.data.meshes.new('pig'); me.from_pydata(verts.tolist(), [], faces.tolist()); me.update()
pig = bpy.data.objects.new('pig', me); col.objects.link(pig); bpy.context.view_layer.objects.active = pig; pig.select_set(True)
bpy.ops.object.shade_smooth()
sm = pig.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.6; sm.iterations = 6
bpy.ops.object.modifier_apply(modifier='sm'); bpy.ops.object.shade_smooth()

# ceramica esmaltada rosa (salmao/peche/coral) com variacao suave + verniz
pm = bpy.data.materials.new('ceramica'); pm.use_nodes = True; nt = pm.node_tree; bsdf = nt.nodes['Principled BSDF']
noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 2.2; noise.inputs['Detail'].default_value = 3
ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (0.98, 0.34, 0.36, 1); ramp.color_ramp.elements[1].color = (1.0, 0.56, 0.50, 1)
nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value = 0.20
bsdf.inputs['Coat Weight'].default_value = 1.0; bsdf.inputs['Coat Roughness'].default_value = 0.025
bsdf.inputs['Subsurface Weight'].default_value = 0.05; bsdf.inputs['Subsurface Radius'].default_value = (0.8, 0.25, 0.15)
bsdf.inputs['Specular IOR Level'].default_value = 0.55
pig.data.materials.append(pm)

# focinho (disco) e narinas, olhos
def add(obj_fn, mname, **kw):
    obj_fn(**kw); o = bpy.context.active_object; return o
for sy in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.078, location=(-1.53, sy*0.45, 0.50), segments=48, ring_count=24); e = bpy.context.active_object; e.scale = (0.8, 0.7, 1.0)
    e.data.materials.append(mat('olho', (0.01, 0.01, 0.012), 0.03)); bpy.ops.object.shade_smooth()

# moeda de 1 real (aro dourado + miolo prateado), em pe na fenda
R, T = 0.30, 0.045; ZC = 1.0
gold = mat('ouro', (0.93, 0.70, 0.28), 0.22, 1.0); silver = mat('prata', (0.86, 0.87, 0.90), 0.18, 1.0)
def cyl(r, depth, loc, m, bev=0.012):
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=r, depth=depth, location=loc, rotation=(math.pi/2, 0, 0)); o = bpy.context.active_object
    b = o.modifiers.new('b', 'BEVEL'); b.width = bev; b.segments = 3; b.limit_method = 'NONE'
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='b'); bpy.ops.object.shade_smooth(); o.data.materials.append(m); return o
c1 = cyl(R, T, (0.12, 0, ZC), gold)
c2 = cyl(R*0.70, T*1.18, (0.12, 0, ZC), silver, 0.008)
for s in (-1, 1):                                           # anel de relevo entre aro e miolo
    bpy.ops.mesh.primitive_torus_add(major_radius=R*0.71, minor_radius=0.007, location=(0.12, s*T*0.60, ZC), rotation=(math.pi/2, 0, 0), major_segments=128, minor_segments=12)
    t = bpy.context.active_object; t.data.materials.append(gold); bpy.ops.object.shade_smooth()
    bpy.ops.object.text_add(location=(0.12, s*T*0.62, ZC-0.04), rotation=(math.pi/2, 0, math.pi if s == 1 else 0)); tx = bpy.context.active_object
    tx.data.body = '1'; tx.data.size = 0.20; tx.data.extrude = 0.004; tx.data.align_x = 'CENTER'; tx.data.materials.append(silver)
    bpy.ops.object.shade_smooth()

# ---------------------------------------------------------------- posicao do conjunto (3/4, focinho para a esquerda)
grp = [o for o in bpy.data.objects]
root = bpy.data.objects.new('root', None); col.objects.link(root)
for o in grp: o.parent = root
root.rotation_euler = (0, 0, math.radians(32))

# ---------------------------------------------------------------- cenario: piso (apanha sombra), fundo laranja invisivel p/ camera (so reflete luz)
bpy.ops.mesh.primitive_plane_add(size=16, location=(0, 0, -1.0)); fl = bpy.context.active_object; fl.is_shadow_catcher = True
fl.data.materials.append(mat('piso', (0.70, 0.83, 1.0), 0.9))
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 9, 8), rotation=(math.pi/2, 0, 0)); wl = bpy.context.active_object
wl.data.materials.append(mat('parede', (0.012, 0.13, 0.75), 0.9)); wl.visible_camera = False; wl.visible_shadow = False
# luzes
def area(name, loc, power, size, color=(1, 1, 1), target=(0, 0, 0)):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = power; d.size = size; d.color = color
    o = bpy.data.objects.new(name, d); col.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target)-Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
area('key', (-4.5, -4.5, 6.0), 520, 5.0, (1.0, 0.97, 0.93))
area('fill', (3.0, -7.0, 1.5), 110, 6.0, (1.0, 0.95, 0.92))
area('rim', (4.0, 4.0, 3.5), 260, 3.0, (0.85, 0.92, 1.0))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.80, 0.88, 1.0, 1); bg.inputs['Strength'].default_value = 0.22
# camera
cam = bpy.data.cameras.new('cam'); cam.lens = 85; co = bpy.data.objects.new('cam', cam); col.objects.link(co); sc.camera = co
co.location = (-0.2, -12.8, 1.5); target = Vector((-0.2, 0, 0.05))
co.rotation_euler = (target-co.location).to_track_quat('-Z', 'Y').to_euler()
cam.sensor_width = 36
# render
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.cycles.denoiser = 'OPENIMAGEDENOISE'; sc.cycles.max_bounces = 8
sc.render.film_transparent = True; sc.render.resolution_x = RW; sc.render.resolution_y = RH; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'; sc.render.filepath = OUT
sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.15
sc.view_settings.look = 'None'
bpy.ops.render.render(write_still=True)
