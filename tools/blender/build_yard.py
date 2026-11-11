# Сборка low-poly ассетов двора и экспорт в assets/models/*.glb.
# Запуск в Blender: exec(open(r"...\tools\blender\build_yard.py", encoding="utf-8").read())
# Оси Blender: Z — вверх, "перед" ассета смотрит в -Y (в Godot это +Z).
import bpy
import math
import os
import random
from mathutils import Vector

ROOT = r"C:\Users\mrs\Documents\yuranchik_game"
TEX = os.path.join(ROOT, "assets", "textures")
OUT = os.path.join(ROOT, "assets", "models")
rnd = random.Random(1977)


# ---------------- материалы ----------------
def mat(name, tex, emi=None, rough=0.9, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    img = bpy.data.images.load(os.path.join(TEX, tex + ".png"), check_existing=True)
    img.reload()
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    if emi:
        ei = bpy.data.images.load(os.path.join(TEX, emi + ".png"), check_existing=True)
        ei.reload()
        e = nt.nodes.new("ShaderNodeTexImage"); e.image = ei
        nt.links.new(e.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    return m


M = {}
def build_materials():
    M["facade"] = mat("Facade", "facade_albedo", "facade_emission")
    M["wall"] = mat("WallSide", "wall_side")
    M["plinth"] = mat("Plinth", "plinth")
    M["roof"] = mat("Roof", "roof")
    M["door"] = mat("Door", "door", rough=0.6)
    M["balcony"] = mat("Balcony", "balcony")
    M["metal"] = mat("Metal", "metal", rough=0.6)
    M["green"] = mat("GreenMetal", "green_metal", rough=0.6)
    M["gdoor"] = mat("GarageDoors", "garage_doors", rough=0.6)
    M["gwall"] = mat("GarageWall", "garage_wall")
    M["snow"] = mat("Snow", "snow")
    M["bark"] = mat("Bark", "bark")
    M["wood"] = mat("Wood", "wood")
    M["kiosk"] = mat("Kiosk", "kiosk", "kiosk_emission", rough=0.5)
    M["glass"] = mat("LampGlass", "lamp_glass", "lamp_glass", rough=0.3)


# ---------------- построитель меша ----------------
class B:
    def __init__(self):
        self.v, self.f, self.uv, self.mi, self.mats = [], [], [], [], []

    def _m(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def poly(self, pts, uvs, m):
        base = len(self.v)
        self.v += [tuple(p) for p in pts]
        self.f.append(tuple(range(base, base + len(pts))))
        self.uv.append(uvs)
        self.mi.append(self._m(m))

    def box(self, mn, mx, faces, scale=(1.0, 1.0)):
        """faces: {'+X': mat | (mat, (u0,v0,u1,v1)), ...}. Без ключа — грань пропускается.
        Мат без rect — мировая проекция с шагом scale (м на тайл)."""
        c = [Vector((mx[0] if i & 1 else mn[0], mx[1] if i & 2 else mn[1], mx[2] if i & 4 else mn[2])) for i in range(8)]
        spec = {'+X': (1, 3, 7, 5), '-X': (2, 0, 4, 6), '+Y': (3, 2, 6, 7),
                '-Y': (0, 1, 5, 4), '+Z': (4, 5, 7, 6), '-Z': (0, 2, 3, 1)}
        su, sv = scale
        for k, idx in spec.items():
            if k not in faces:
                continue
            fm = faces[k]
            pts = [c[i] for i in idx]
            if isinstance(fm, tuple):
                m, (u0, v0, u1, v1) = fm
                uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            else:
                m = fm
                if k[1] == 'X':
                    sgn = 1 if k[0] == '+' else -1
                    uvs = [(sgn * p.y / su, p.z / sv) for p in pts]
                elif k[1] == 'Y':
                    sgn = -1 if k[0] == '+' else 1
                    uvs = [(sgn * p.x / su, p.z / sv) for p in pts]
                else:
                    uvs = [(p.x / su, p.y / sv) for p in pts]
            self.poly(pts, uvs, m)

    def cyl(self, p0, p1, r0, r1, m, segs=6, caps=False, su=1.0):
        p0, p1 = Vector(p0), Vector(p1)
        ax = (p1 - p0)
        L = ax.length
        ax.normalize()
        t = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
        u = ax.cross(t).normalized(); w = ax.cross(u)
        ring = lambda p, r, a: p + (u * math.cos(a) + w * math.sin(a)) * r
        for i in range(segs):
            a0 = 2 * math.pi * i / segs; a1 = 2 * math.pi * (i + 1) / segs
            pts = [ring(p0, r0, a0), ring(p0, r0, a1), ring(p1, r1, a1), ring(p1, r1, a0)]
            uvs = [(i / segs, 0), ((i + 1) / segs, 0), ((i + 1) / segs, L / su), (i / segs, L / su)]
            self.poly(pts, uvs, m)
        if caps:
            self.poly([ring(p1, r1, 2 * math.pi * i / segs) for i in range(segs)],
                      [(0.5 + 0.5 * math.cos(2 * math.pi * i / segs), 0.5 + 0.5 * math.sin(2 * math.pi * i / segs)) for i in range(segs)], m)

    def build(self, name, coll):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in self.mats:
            me.materials.append(m)
        uvl = me.uv_layers.new(name="UVMap")
        li = 0
        for pi, poly in enumerate(me.polygons):
            poly.material_index = self.mi[pi]
            for k, l in enumerate(poly.loop_indices):
                uvl.data[l].uv = self.uv[pi][k]
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        return ob


# ---------------- ассеты ----------------
def panel_building(coll):
    b = B()
    W, D, PL, FH, NF = 21.6, 12.0, 0.9, 2.8, 9
    top = PL + FH * NF
    hw, hd = W / 2, D / 2
    # фасады (целиком одна текстура)
    b.poly([(-hw, -hd, PL), (hw, -hd, PL), (hw, -hd, top), (-hw, -hd, top)], [(0, 0), (1, 0), (1, 1), (0, 1)], M["facade"])
    b.poly([(hw, hd, PL), (-hw, hd, PL), (-hw, hd, top), (hw, hd, top)], [(0.5, 0), (1.5, 0), (1.5, 1), (0.5, 1)], M["facade"])
    # торцы и крыша
    b.box((-hw, -hd, PL), (hw, hd, top), {'+X': M["wall"], '-X': M["wall"]}, scale=(5.4, 5.6))
    b.box((-hw, -hd, PL), (hw, hd, top), {'+Z': M["roof"]}, scale=(6, 6))
    # цоколь
    b.box((-hw - 0.06, -hd - 0.06, 0), (hw + 0.06, hd + 0.06, PL),
          {k: M["plinth"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(3.6, 0.9))
    # парапет
    for (mn, mx) in [((-hw - .1, -hd - .1, top), (hw + .1, -hd + .15, top + .6)),
                     ((-hw - .1, hd - .15, top), (hw + .1, hd + .1, top + .6)),
                     ((-hw - .1, -hd, top), (-hw + .15, hd, top + .6)),
                     ((hw - .15, -hd, top), (hw + .1, hd, top + .6))]:
        b.box(mn, mx, {k: M["wall"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(5.4, 5.6))
        b.box(mn, mx, {'+Z': M["metal"]}, scale=(2, 2))
    # машинные помещения лифтов над подъездами
    for x in (-4.05, 4.05):
        b.box((x - 1.6, -2.0, top), (x + 1.6, 2.5, top + 2.6),
              {k: M["wall"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(5.4, 5.6))
        b.box((x - 1.7, -2.1, top + 2.6), (x + 1.7, 2.6, top + 2.75),
              {k: M["roof"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(3, 3))
    # антенны
    for i in range(6):
        x = rnd.uniform(-hw + 1, hw - 1); y = rnd.uniform(-hd + 1, hd - 1)
        h = rnd.uniform(1.5, 3.0)
        b.cyl((x, y, top), (x, y, top + h), 0.025, 0.02, M["metal"], segs=4)
        b.cyl((x - 0.6, y, top + h - 0.3), (x + 0.6, y, top + h - 0.3), 0.015, 0.015, M["metal"], segs=4)
    # подъезды: тамбур, дверь, козырёк, ступени
    for x in (-4.05, 4.05):
        y0 = -hd - 0.5
        b.box((x - 1.2, y0, 0), (x + 1.2, -hd, 2.6), {'+X': M["wall"], '-X': M["wall"]}, scale=(5.4, 5.6))
        b.box((x - 1.2, y0, 0), (x - 0.7, -hd, 2.6), {'-Y': M["wall"]}, scale=(5.4, 5.6))
        b.box((x + 0.7, y0, 0), (x + 1.2, -hd, 2.6), {'-Y': M["wall"]}, scale=(5.4, 5.6))
        b.box((x - 0.7, y0, 2.2), (x + 0.7, -hd, 2.6), {'-Y': M["wall"]}, scale=(5.4, 5.6))
        b.box((x - 0.7, y0 + 0.05, 0), (x + 0.7, -hd, 2.2), {'-Y': (M["door"], (0, 0, 1, 1))})
        b.box((x - 1.5, -hd - 1.8, 2.6), (x + 1.5, -hd, 2.78),
              {k: M["plinth"] for k in ('+X', '-X', '-Y', '-Z')}, scale=(3.6, 0.9))
        b.box((x - 1.5, -hd - 1.8, 2.78), (x + 1.5, -hd, 2.92), {'+Z': M["snow"], '-Y': M["snow"], '+X': M["snow"], '-X': M["snow"]}, scale=(3, 3))
        b.box((x - 1.4, -hd - 1.6, 0), (x + 1.4, y0, 0.15), {k: M["plinth"] for k in ('+X', '-X', '-Y', '+Z')}, scale=(3.6, 0.9))
    # балконы (колонки 1 и 6), этажи 2..9
    for col in (1, 6):
        x = -hw + (col + 0.5) * 2.7
        for fl in range(1, NF):
            z = PL + fl * FH
            glazed = rnd.random() < 0.45
            y1 = -hd - 1.1
            b.box((x - 1.3, y1, z - 0.12), (x + 1.3, -hd, z), {k: M["plinth"] for k in ('+X', '-X', '-Y', '-Z')}, scale=(3.6, 0.9))
            b.box((x - 1.3, y1, z), (x + 1.3, -hd, z + 0.04), {'+Z': M["snow"]}, scale=(3, 3))
            hgt = 2.55 if glazed else 1.05
            rect = (0.5, 0, 1, 1) if glazed else (0, 0, 0.5, 1)
            b.box((x - 1.3, y1, z), (x + 1.3, y1 + 0.06, z + hgt), {'-Y': (M["balcony"], rect), '+Y': (M["balcony"], rect)})
            for sx in (x - 1.3, x + 1.24):
                b.box((sx, y1, z), (sx + 0.06, -hd, z + hgt), {'+X': (M["balcony"], (0, 0, 0.2, 1)), '-X': (M["balcony"], (0, 0, 0.2, 1))})
            if glazed:
                b.box((x - 1.35, y1 - 0.05, z + hgt), (x + 1.35, -hd, z + hgt + 0.08), {k: M["metal"] for k in ('-Y', '+Z', '-Z', '+X', '-X')}, scale=(1, 1))
    # кондиционеры и водостоки
    for i in range(7):
        col = rnd.choice([0, 2, 3, 4, 5, 7]); fl = rnd.randint(0, NF - 1)
        x = -hw + (col + 0.5) * 2.7 + 0.9; z = PL + fl * FH + 0.4
        b.box((x - 0.4, -hd - 0.3, z), (x + 0.4, -hd, z + 0.55), {k: M["metal"] for k in ('-Y', '+X', '-X', '+Z', '-Z')}, scale=(0.8, 0.55))
    for x in (-hw + 0.3, hw - 0.3):
        b.cyl((x, -hd - 0.12, 0.2), (x, -hd - 0.12, top), 0.07, 0.07, M["metal"], segs=6, su=2)
    return b.build("PanelBuilding", coll)


def street_lamp(coll):
    b = B()
    b.cyl((0, 0, 0), (0, 0, 7.4), 0.13, 0.07, M["metal"], segs=8, su=2)
    b.cyl((0, 0, 7.3), (0, -0.5, 7.85), 0.06, 0.05, M["metal"], segs=6)
    b.cyl((0, -0.5, 7.85), (0, -1.7, 8.0), 0.05, 0.045, M["metal"], segs=6)
    # «кобра»
    b.box((-0.2, -2.45, 7.85), (0.2, -1.65, 8.08), {k: M["metal"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(0.5, 0.5))
    b.box((-0.16, -2.38, 7.82), (0.16, -1.75, 7.85), {'-Z': (M["glass"], (0, 0, 1, 1))})
    return b.build("StreetLamp", coll)


def garages(coll):
    b = B()
    n, gw, gd, gh = 5, 3.2, 6.0, 2.6
    L = n * gw
    b.box((0, -gd / 2, 0), (L, gd / 2, gh), {'+X': M["gwall"], '-X': M["gwall"], '+Y': M["gwall"]}, scale=(2, 2))
    for i in range(n):
        x0 = i * gw
        b.box((x0, -gd / 2, 0), (x0 + 0.3, -gd / 2 + 0.01, gh), {'-Y': M["gwall"]}, scale=(2, 2))
        b.box((x0 + gw - 0.3, -gd / 2, 0), (x0 + gw, -gd / 2 + 0.01, gh), {'-Y': M["gwall"]}, scale=(2, 2))
        b.box((x0 + 0.3, -gd / 2, 2.2), (x0 + gw - 0.3, -gd / 2 + 0.01, gh), {'-Y': M["gwall"]}, scale=(2, 2))
        v = rnd.randint(0, 3)
        b.box((x0 + 0.3, -gd / 2 + 0.05, 0), (x0 + gw - 0.3, -gd / 2 + 0.06, 2.2), {'-Y': (M["gdoor"], (v / 4, 0, (v + 1) / 4, 1))})
    b.box((-0.2, -gd / 2 - 0.4, gh), (L + 0.2, gd / 2 + 0.2, gh + 0.15), {k: M["roof"] for k in ('+X', '-X', '+Y', '-Y', '-Z')}, scale=(3, 3))
    b.box((-0.1, -gd / 2 - 0.3, gh + 0.15), (L + 0.1, gd / 2 + 0.1, gh + 0.32), {k: M["snow"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(4, 4))
    return b.build("Garages", coll)


def kiosk(coll):
    b = B()
    w, d, h = 3.0, 2.0, 2.6
    b.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), {'-Y': (M["kiosk"], (0, 0, 1, 1))})
    side = (M["kiosk"], (0, 0.02, 1, 0.3))
    b.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), {'+X': side, '-X': side, '+Y': side})
    b.box((-w / 2 - 0.25, -d / 2 - 0.4, h), (w / 2 + 0.25, d / 2 + 0.1, h + 0.12), {k: M["metal"] for k in ('+X', '-X', '+Y', '-Y', '-Z')}, scale=(1, 1))
    b.box((-w / 2 - 0.2, -d / 2 - 0.35, h + 0.12), (w / 2 + 0.2, d / 2 + 0.05, h + 0.28), {k: M["snow"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(3, 3))
    return b.build("Kiosk", coll)


def tree(coll, seed, name):
    r = random.Random(seed)
    b = B()
    def branch(p, d, length, rad, depth):
        end = p + d * length
        b.cyl(p, end, rad, rad * 0.6, M["bark"], segs=5 if depth < 2 else 3, su=2)
        if depth >= 3:
            return
        k = r.randint(2, 4) if depth > 0 else r.randint(4, 6)
        for i in range(k):
            t = r.uniform(0.45, 1.0) if depth > 0 else r.uniform(0.35, 0.95)
            sp = p + d * length * t
            nd = (d + Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0.1, 0.9)))).normalized()
            branch(sp, nd, length * r.uniform(0.45, 0.65), rad * 0.5, depth + 1)
    branch(Vector((0, 0, 0)), Vector((r.uniform(-0.1, 0.1), r.uniform(-0.1, 0.1), 1)).normalized(), r.uniform(6, 8), 0.2, 0)
    return b.build(name, coll)


def bench(coll):
    b = B()
    for x in (-0.8, 0.8):
        b.box((x - 0.08, -0.25, 0), (x + 0.08, 0.25, 0.42), {k: M["plinth"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(1, 0.5))
        b.box((x - 0.06, 0.15, 0.42), (x + 0.06, 0.25, 0.9), {k: M["plinth"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(1, 0.5))
    for i, y in enumerate((-0.22, -0.06, 0.1)):
        b.box((-1.0, y, 0.42), (1.0, y + 0.13, 0.47), {k: M["wood"] for k in ('+X', '-X', '+Y', '-Y', '+Z', '-Z')}, scale=(2, 0.5))
    for z in (0.58, 0.75):
        b.box((-1.0, 0.25, z), (1.0, 0.29, z + 0.12), {k: M["wood"] for k in ('+X', '-X', '+Y', '-Y', '+Z', '-Z')}, scale=(2, 0.5))
    b.box((-1.0, -0.22, 0.47), (1.0, 0.23, 0.5), {'+Z': M["snow"]}, scale=(2, 2))
    return b.build("Bench", coll)


def trash_bin(coll):
    b = B()
    b.box((-0.65, -0.45, 0.1), (0.65, 0.45, 1.1), {k: M["green"] for k in ('+X', '-X', '+Y', '-Y')}, scale=(1.3, 1.0))
    b.box((-0.7, -0.5, 1.1), (0.7, 0.5, 1.16), {k: M["green"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(1.3, 1.0))
    b.box((-0.68, -0.48, 1.16), (0.68, 0.48, 1.24), {'+Z': M["snow"], '-Y': M["snow"], '+Y': M["snow"]}, scale=(2, 2))
    for x in (-0.5, 0.5):
        for y in (-0.3, 0.3):
            b.cyl((x, y, 0), (x, y, 0.12), 0.06, 0.06, M["metal"], segs=4)
    return b.build("TrashBin", coll)


def turnik(coll):
    b = B()
    for x in (-1.0, 1.0):
        b.cyl((x, 0, 0), (x, 0, 2.4), 0.05, 0.05, M["green"], segs=6, su=2)
    b.cyl((-1.0, 0, 2.3), (1.0, 0, 2.3), 0.02, 0.02, M["metal"], segs=4)
    return b.build("Turnik", coll)


def fence(coll):
    b = B()
    L = 6.0
    for i in range(4):
        x = i * 2.0
        b.box((x - 0.04, -0.04, 0), (x + 0.04, 0.04, 0.9), {k: M["green"] for k in ('+X', '-X', '+Y', '-Y', '+Z')}, scale=(0.5, 1))
    for z in (0.15, 0.8):
        b.box((0, -0.02, z), (L, 0.02, z + 0.04), {k: M["green"] for k in ('+Y', '-Y', '+Z', '-Z')}, scale=(1, 1))
    x = 0.15
    while x < L:
        b.box((x - 0.012, -0.012, 0.15), (x + 0.012, 0.012, 0.84), {'+Y': M["green"], '-Y': M["green"], '+X': M["green"], '-X': M["green"]}, scale=(0.5, 1))
        x += 0.18
    return b.build("Fence", coll)


def drift(coll, name, sx, sy, hgt, seed):
    r = random.Random(seed)
    b = B()
    n = 10
    def hz(i, j):
        u = i / n * 2 - 1; v = j / n * 2 - 1
        d = max(0.0, 1 - (u * u + v * v))
        return hgt * d ** 0.7 * (0.85 + 0.3 * r.random()) if 0 < i < n and 0 < j < n else 0.0
    H = [[hz(i, j) for j in range(n + 1)] for i in range(n + 1)]
    for i in range(n):
        for j in range(n):
            pts = []
            uvs = []
            for (a, c) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                x = (a / n - 0.5) * sx; y = (c / n - 0.5) * sy
                pts.append((x, y, H[a][c])); uvs.append((x / 3, y / 3))
            b.poly(pts, uvs, M["snow"])
    return b.build(name, coll)


# ---------------- сборка и экспорт ----------------
def main():
    sc = bpy.data.scenes.get("Yard")
    if sc:
        for ob in list(sc.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        for me in list(bpy.data.meshes):
            if me.users == 0:
                bpy.data.meshes.remove(me)
    else:
        sc = bpy.data.scenes.new("Yard")
    bpy.context.window.scene = sc
    build_materials()
    assets = {}
    def add(name, fn, *a):
        c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
        if c.name not in sc.collection.children:
            sc.collection.children.link(c)
        ob = fn(c, *a)
        assets[name] = ob
    add("panel_building", panel_building)
    add("street_lamp", street_lamp)
    add("garages", garages)
    add("kiosk", kiosk)
    add("tree_a", tree, 3, "TreeA")
    add("tree_b", tree, 11, "TreeB")
    add("bench", bench)
    add("trash_bin", trash_bin)
    add("turnik", turnik)
    add("fence", fence)
    add("drift_long", drift, "DriftLong", 7, 2.2, 0.7, 5)
    add("drift_round", drift, "DriftRound", 3, 3, 0.9, 9)
    # раскладываем для просмотра в Blender
    x = 0
    stats = {}
    for name, ob in assets.items():
        stats[name] = len(ob.data.polygons)
    os.makedirs(OUT, exist_ok=True)
    for name, ob in assets.items():
        for o in sc.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".gltf"), use_selection=True, export_keep_originals=True,
                                  export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    # раскладка для осмотра (после экспорта, чтобы не влиять на origin)
    for name, ob in assets.items():
        ob.location.x = x
        x += max(ob.dimensions.x, 2) + 4
    return stats


result = main()
