# «Фотостудия» текстур в Blender: маленькая 3D-сцена (камни, шпалы, снег, гофра, окна…) снимается
# ортографической камерой сверху и превращается в текстуру. Так делали «запечённые» текстуры в эпоху PS2:
# рельеф, тени и AO настоящие, а в игре это одна плоская картинка.
# Всё строится в отдельной сцене EB_TexStudio — рабочие сцены файла не трогаются.
# Координаты: текстура лежит в плоскости XY, X — вправо (u), Y — вверх по картинке (верх текстуры = +Y),
# свет падает сверху-слева, камера смотрит вниз (-Z).
import math
import os
import tempfile
import numpy as np
import bpy

SCENE = "EB_TexStudio"
OUT_DIR = os.path.join(tempfile.gettempdir(), "eb_tex_studio")


# ------------------------------------------------------------------ цвет
def lin(c):
    """sRGB (как в numpy-текстурах) → линейный цвет для шейдера Blender."""
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin4(c):
    l = lin(c[:3])
    return (float(l[0]), float(l[1]), float(l[2]), 1.0)


# ------------------------------------------------------------------ сцена
def studio(w_m, h_m, px_w, px_h, samples=32, sun_elev=50.0, sun_az=135.0, sun_share=0.45,
           sky=(1.0, 1.0, 1.0), transparent=False):
    """Пустая студия: кадр w_m × h_m метров (от (0,0) до (w_m,h_m)), картинка px_w × px_h.
    sun_share — доля солнца в освещённости горизонтальной белой поверхности (остальное — небо)."""
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    for ob in list(sc.collection.all_objects):
        data = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if data is not None and data.users == 0:
            for coll in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.curves):
                if data.name in coll and coll[data.name] == data:
                    coll.remove(data)
                    break
    r = sc.render
    r.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.cycles.use_adaptive_sampling = True
    r.resolution_x, r.resolution_y, r.resolution_percentage = px_w, px_h, 100
    r.film_transparent = transparent
    r.filter_size = 0.8
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    r.image_settings.color_depth = '8'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.display_settings.display_device = 'sRGB'

    wd = bpy.data.worlds.get("EB_TexWorld") or bpy.data.worlds.new("EB_TexWorld")
    wd.use_nodes = True
    bg = wd.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*[float(x) for x in sky], 1.0)
    bg.inputs[1].default_value = 1.0 - sun_share
    sc.world = wd

    cam_d = bpy.data.cameras.new("EB_TexCam")
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = max(w_m, h_m)
    cam_d.sensor_fit = 'AUTO'
    cam_d.clip_start, cam_d.clip_end = 0.01, 100
    cam = bpy.data.objects.new("EB_TexCam", cam_d)
    cam.location = (w_m / 2, h_m / 2, 20)
    sc.collection.objects.link(cam)
    sc.camera = cam

    if sun_share > 0:
        sun_d = bpy.data.lights.new("EB_TexSun", 'SUN')
        el, az = math.radians(sun_elev), math.radians(sun_az)
        sun_d.energy = sun_share * math.pi / math.sin(el)
        sun_d.angle = math.radians(6)
        sun = bpy.data.objects.new("EB_TexSun", sun_d)
        # направление на солнце: азимут от +X против часовой (135° = сверху-слева)
        d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        sun.rotation_euler = _look_rot(-d)
        sc.collection.objects.link(sun)
    return sc


def _look_rot(direction):
    """Эйлер для объекта, чья ось -Z смотрит в direction."""
    from mathutils import Vector
    return Vector(direction).to_track_quat('-Z', 'Y').to_euler()


def render(sc, name):
    """Снять кадр и вернуть numpy [H, W, 3|4] в sRGB-значениях (как остальные текстуры), (0,0) = верх-лево."""
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name + "_render.png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(img)
    return a if sc.render.film_transparent else a[..., :3]


# ------------------------------------------------------------------ материалы
def material(name, color=(0.5, 0.5, 0.5), rough=0.9, attr=None, attr_mix=1.0, snow_top=0.0,
             snow_col=(0.82, 0.85, 0.92), noise=0.0, noise_scale=30.0, bump=0.0, metal=0.0, snow_axis="Z"):
    """Principled-материал: базовый цвет × (цвет из атрибута меша «col», если attr), шум яркости,
    снежная «пудра» на гранях, смотрящих вверх (snow_top — сила; snow_axis — какая ось «вверх»), мелкий бамп."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    nt.links.new(bs.outputs[0], out.inputs[0])
    base = nt.nodes.new("ShaderNodeRGB")
    base.outputs[0].default_value = lin4(color)
    col = base.outputs[0]
    if attr:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = attr
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs["Factor"].default_value = attr_mix
        nt.links.new(col, mix.inputs[6])
        nt.links.new(at.outputs["Color"], mix.inputs[7])
        col = mix.outputs[2]
    if noise:
        tx = nt.nodes.new("ShaderNodeTexNoise")
        tx.inputs["Scale"].default_value = noise_scale
        tx.inputs["Detail"].default_value = 6
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs[1].default_value, ramp.inputs[2].default_value = 0.3, 0.7
        ramp.inputs[3].default_value, ramp.inputs[4].default_value = 1 - noise, 1 + noise
        nt.links.new(tx.outputs["Fac"], ramp.inputs[0])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs["Factor"].default_value = 1.0
        nt.links.new(col, mul.inputs[6])
        nt.links.new(ramp.outputs[0], mul.inputs[7])   # float → цвет (серый)
        col = mul.outputs[2]
    if snow_top:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], sep.inputs[0])
        tx2 = nt.nodes.new("ShaderNodeTexNoise")
        tx2.inputs["Scale"].default_value = 60
        tx2.inputs["Detail"].default_value = 4
        # v = Nz + шум (шум ~0.5±0.1); снег там, где v выше порога 2 - snow_top (0.4 — снег на ~15% верхушек)
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = 'ADD'
        nt.links.new(tx2.outputs["Fac"], add.inputs[0])
        nt.links.new(sep.outputs[snow_axis], add.inputs[1])   # «верх»: Z для полов, Y для вида сбоку
        rng = nt.nodes.new("ShaderNodeMapRange")
        thr = 2.0 - snow_top
        rng.inputs[1].default_value = thr - 0.06
        rng.inputs[2].default_value = thr + 0.06
        nt.links.new(add.outputs[0], rng.inputs[0])
        sm = nt.nodes.new("ShaderNodeMix")
        sm.data_type = 'RGBA'
        nt.links.new(rng.outputs[0], sm.inputs["Factor"])
        nt.links.new(col, sm.inputs[6])
        sm.inputs[7].default_value = lin4(snow_col)
        col = sm.outputs[2]
    nt.links.new(col, bs.inputs["Base Color"])
    if bump:
        tb = nt.nodes.new("ShaderNodeTexNoise")
        tb.inputs["Scale"].default_value = noise_scale * 4
        tb.inputs["Detail"].default_value = 8
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        nt.links.new(tb.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs[0], bs.inputs["Normal"])
    return m


def image_material(name, arr, rough=0.9, metal=0.0):
    """Материал с картинкой (numpy sRGB) — для «наклеек»: граффити, объявления, надписи на 3D-форме."""
    h, w = arr.shape[:2]
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=True)
    if img.size[0] != w or img.size[1] != h:
        img.scale(w, h)
    img.colorspace_settings.name = 'sRGB'          # до записи пикселей: смена пространства перегенерирует картинку
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :arr.shape[2]] = np.clip(arr, 0, 1)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.update()
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = rough
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    tx.interpolation = 'Linear'
    bs.inputs["Metallic"].default_value = metal
    nt.links.new(tx.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(tx.outputs["Alpha"], bs.inputs["Alpha"])
    nt.links.new(bs.outputs[0], out.inputs[0])
    return m


# ------------------------------------------------------------------ меши
def mesh_object(sc, name, verts, faces, mat=None, colors=None, uvs=None, smooth=False):
    """Меш из numpy: verts [N,3], faces — список/массив индексов; colors — [N,3] цвет вершин в атрибут «col»."""
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, np.float32)
    faces = np.asarray(faces, np.int32)
    n_corner = faces.shape[1]
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(faces.size)
    me.loops.foreach_set("vertex_index", faces.ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set("loop_start", np.arange(0, faces.size, n_corner, dtype=np.int32))
    me.update()
    me.validate()
    if colors is not None:
        ca = me.color_attributes.new("col", 'FLOAT_COLOR', 'POINT')
        c4 = np.ones((len(verts), 4), np.float32)
        c4[:, :3] = lin(np.asarray(colors, np.float32))
        ca.data.foreach_set("color", c4.ravel())
    if uvs is not None:
        uv = me.uv_layers.new(name="UVMap")
        uv.data.foreach_set("uv", np.asarray(uvs, np.float32)[faces.ravel()].ravel())
    if smooth:
        me.shade_smooth()
    if mat is not None:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


def grid(x0, y0, x1, y1, nx, ny, zfun):
    """Сетка-рельеф: zfun(X, Y) -> Z (numpy). Возвращает verts, faces, uv."""
    xs = np.linspace(x0, x1, nx + 1, dtype=np.float32)
    ys = np.linspace(y0, y1, ny + 1, dtype=np.float32)
    X, Y = np.meshgrid(xs, ys)
    Z = zfun(X, Y).astype(np.float32)
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    i = np.arange((nx + 1) * (ny + 1)).reshape(ny + 1, nx + 1)
    faces = np.stack([i[:-1, :-1], i[:-1, 1:], i[1:, 1:], i[1:, :-1]], -1).reshape(-1, 4)
    uv = np.stack([(X - x0) / (x1 - x0), (Y - y0) / (y1 - y0)], -1).reshape(-1, 2)
    return verts, faces, uv


def box(x0, y0, z0, x1, y1, z1):
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], np.float32)
    f = np.array([[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], np.int32)
    return v, f


def merge(parts):
    """[(verts, faces), …] → один (verts, faces)."""
    vs, fs, off = [], [], 0
    for v, f in parts:
        vs.append(v)
        fs.append(np.asarray(f) + off)
        off += len(v)
    return np.concatenate(vs), np.concatenate(fs)


_ICO = None


def _ico():
    """Икосфера 1-го подразделения (42 вершины, 80 треугольников) — заготовка камня."""
    global _ICO
    if _ICO is None:
        t = (1 + 5 ** 0.5) / 2
        v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
        f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
             (6, 2, 10), (8, 6, 7), (9, 8, 1)]
        v = [np.array(p, np.float64) / np.linalg.norm(p) for p in v]
        cache, nf = {}, []

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                p = v[a] + v[b]
                v.append(p / np.linalg.norm(p))
                cache[k] = len(v) - 1
            return cache[k]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        _ICO = (np.array(v, np.float32), np.array(nf, np.int32))
    return _ICO


def stones(rng, centers, sizes, flat=0.6, jag=0.28):
    """Щебень: N угловатых камней. centers [N,3], sizes [N]. Возвращает verts, faces, stone_id на вершину."""
    v0, f0 = _ico()
    n = len(centers)
    nv = len(v0)
    # «колотый» камень: несколько случайных срезающих плоскостей сплющивают сферу в многогранник
    V = np.repeat(v0[None], n, 0).astype(np.float32)
    for _ in range(5):
        nrm = rng.normal(size=(n, 1, 3)).astype(np.float32)
        nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
        d = rng.uniform(0.45, 0.8, (n, 1, 1)).astype(np.float32)
        proj = (V * nrm).sum(2, keepdims=True)
        V = V - nrm * np.clip(proj - d, 0, None)
    V *= 1 + rng.uniform(-jag, jag, V.shape[:2] + (1,)).astype(np.float32) * 0.35
    sc = np.stack([rng.uniform(0.8, 1.3, n), rng.uniform(0.7, 1.1, n), rng.uniform(flat * 0.8, flat * 1.2, n)], 1)
    V *= (sc[:, None, :] * sizes[:, None, None] * 0.5).astype(np.float32)
    # случайный поворот вокруг Z и лёгкий наклон
    a = rng.uniform(0, 2 * np.pi, n)
    ca, sa = np.cos(a), np.sin(a)
    Rz = np.zeros((n, 3, 3), np.float32)
    Rz[:, 0, 0], Rz[:, 0, 1], Rz[:, 1, 0], Rz[:, 1, 1], Rz[:, 2, 2] = ca, -sa, sa, ca, 1
    V = np.einsum('nij,nvj->nvi', Rz, V)
    V += np.asarray(centers, np.float32)[:, None, :]
    F = f0[None] + (np.arange(n) * nv)[:, None, None]
    sid = np.repeat(np.arange(n), nv)
    return V.reshape(-1, 3), F.reshape(-1, 3), sid


def periodic_copies(points, w, h, margin):
    """Для бесшовности: точки у края кадра копируются со сдвигом ±w/±h. Возвращает индексы исходных точек и сдвиги."""
    idx, off = [], []
    for dx in (-w, 0, w):
        for dy in (-h, 0, h):
            p = points[:, :2] + np.array([dx, dy], np.float32)
            ok = (p[:, 0] > -margin) & (p[:, 0] < w + margin) & (p[:, 1] > -margin) & (p[:, 1] < h + margin)
            idx.append(np.nonzero(ok)[0])
            off.append(np.repeat([[dx, dy, 0]], ok.sum(), 0))
    return np.concatenate(idx), np.concatenate(off).astype(np.float32)


# ------------------------------------------------------------------ периодический шум (тайлится с периодом w × h метров)
class PNoise:
    """Value-fbm с периодом (w, h) метров; cells — клеток на период по большей стороне.
    Решётка случайных чисел создаётся один раз — один и тот же шум можно считать на разных сетках/точках."""

    def __init__(self, w, h, cells, rng, oct=4, gain=0.5):
        self.w, self.h, self.gain = w, h, gain
        cx0 = max(1, int(round(cells * w / max(w, h))))
        cy0 = max(1, int(round(cells * h / max(w, h))))
        self.layers = []
        for i in range(oct):
            cx, cy = cx0 * 2 ** i, cy0 * 2 ** i
            self.layers.append((cx, cy, rng.random((cy, cx)).astype(np.float32)))

    def __call__(self, X, Y):
        X = np.asarray(X, np.float32)
        Y = np.asarray(Y, np.float32)
        out = np.zeros(np.broadcast(X, Y).shape, np.float32)
        amp, tot = 1.0, 0.0
        for cx, cy, g in self.layers:
            x = (X / self.w * cx) % cx
            y = (Y / self.h * cy) % cy
            x0 = np.floor(x).astype(int); fx = x - x0; x1 = (x0 + 1) % cx; x0 %= cx
            y0 = np.floor(y).astype(int); fy = y - y0; y1 = (y0 + 1) % cy; y0 %= cy
            fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
            v = (g[y0, x0] * (1 - fx) + g[y0, x1] * fx) * (1 - fy) + (g[y1, x0] * (1 - fx) + g[y1, x1] * fx) * fy
            out += v * amp
            tot += amp
            amp *= self.gain
        return out / tot


def smooth01(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ рельеф + рисунок (стены, вагоны, гофра)
def relief(sc, name, hmap, W, H, albedo, rough=0.8, metal=0.0):
    """Рисунок albedo (numpy [ph, pw, 3], sRGB, (0,0) = верх-лево) на рельефе hmap ([ph, pw], метры, + к камере).
    Вершина — в центре каждого пикселя; по краям добавлен ряд с заворотом, чтобы кадр был закрыт целиком
    и текстура оставалась бесшовной."""
    ph, pw = hmap.shape
    hp = np.pad(np.asarray(hmap, np.float32), 1, mode="wrap")[::-1]          # снизу вверх, как ось Y
    xs = (np.arange(pw + 2, dtype=np.float32) - 0.5) / pw * W
    ys = (np.arange(ph + 2, dtype=np.float32) - 0.5) / ph * H
    X, Y = np.meshgrid(xs, ys)
    verts = np.stack([X, Y, hp], -1).reshape(-1, 3)
    i = np.arange((pw + 2) * (ph + 2)).reshape(ph + 2, pw + 2)
    faces = np.stack([i[:-1, :-1], i[:-1, 1:], i[1:, 1:], i[1:, :-1]], -1).reshape(-1, 4)
    uv = np.stack([X / W, Y / H], -1).reshape(-1, 2)
    return mesh_object(sc, name, verts, faces, image_material(name + "_alb", albedo, rough, metal), uvs=uv)


def sample(img, X, Y, W, H):
    """Значения numpy-картинки ([h, w] или [h, w, c], верх-лево) в точках (X, Y) метров кадра W × H, с заворотом."""
    h, w = img.shape[:2]
    ix = (np.floor(np.asarray(X) / W * w).astype(int)) % w
    iy = (h - 1 - np.floor(np.asarray(Y) / H * h).astype(int)) % h
    return img[iy, ix]
