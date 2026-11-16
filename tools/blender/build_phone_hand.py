# -*- coding: utf-8 -*-
# Рука, которая держит телефон, — кисть и рукав самого Юрчика (tools/blender/yurchik_v3.blend), подогнанные под фото:
#   правая рука, ладонь за спинкой телефона, пальцы обхватывают левый край и ложатся на лицо,
#   большой палец идёт вверх вдоль правого края, запястье и рукав куртки уходят вниз-вправо к камере.
#
# Как устроено:
#   1. Из сетки Юрчика берутся вершины кисти и предплечья (группы HandL/ForearmL) вместе с UV и атласом yur3_atlas —
#      та же перчатка без пальцев, те же кончики пальцев и рукав, что на персонаже.
#   2. Три куска (кисть с пальцами, большой палец, рукав) переводятся в систему кисти: t — вдоль кисти к пальцам,
#      n — в сторону ладони, s — поперёк, к большому пальцу.
#   3. Деформация: пальцы за костяшками дополнительно сгибаются, большой палец разворачивается вверх вдоль
#      края телефона, предплечье сгибается в запястье к камере.
#   4. Кисть ставится в координаты телефона (build_phone.py: мм, u вправо, v вверх, w к зрителю):
#      пальцы → −u, большой палец → +v, ладонь → +w. Так из левой кисти Юрчика получается правая (отражение).
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_phone_hand.py
# Результат: assets/models/phone_hand.gltf (объект PhoneHand_nocol, текстура — ../textures/yur3_atlas.png).
import bpy, bmesh, os, math
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "assets", "models")
BLEND = os.path.join(HERE, "yurchik_v3.blend")
MM = 0.001
DEBUG = {}

# ---- подгонка позы (мм, градусы; точки — в координатах телефона) ----
SCALE = 0.85         # кисть Юрчика в натуральную величину
KNUCKLE_T = 72.0     # где кончается ладонь и начинаются пальцы (вдоль кисти)
CURL = 80.0          # сгиб в костяшках: пальцы уходят вперёд вдоль левого бока телефона
CURL_TIP_T = 92.0    # второй сгиб — у края лица телефона
CURL_TIP = 55.0      # пальцы ложатся на лицо
WRIST_T = -12.0      # где сгибается запястье (вдоль кисти)
SLEEVE_KEEP = -150.0 # сколько рукава оставить (дальше камера всё равно не видит)
SLEEVE_PULL = 45.0   # манжету куртки сдвинуть к локтю: иначе она закрывает низ телефона, видно перчатку на запястье
ROLL = -10.0         # наклон всей кисти в плоскости телефона (пальцы чуть вверх, запястье вниз-вправо)
ANCHOR = Vector((-35.0, -30.0, -9.5))     # середина костяшек на стороне ладони: у левого края, за спинкой
THUMB_BASE = Vector((52.0, -60.0, -22.0))  # основание большого пальца — справа внизу за телефоном
THUMB_TIP = Vector((30.0, 8.0, 10.0))     # кончик — на правом крае лица, у нижнего края экрана
SLEEVE_DIR = Vector((0.35, -0.9, 0.15))     # предплечье от запястья: вниз-вправо и к камере

def load_yurchik():
    with bpy.data.libraries.load(BLEND, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in ("Yurchik3Mesh", "Yurchik3")]
    obs = {o.name: o for o in dst.objects}
    return obs["Yurchik3Mesh"], obs["Yurchik3"]


def axis_rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 3, Vector(axis))


def islands_of(bm):
    out, seen = [], set()
    for v in bm.verts:
        if v in seen:
            continue
        comp, st = [], [v]
        seen.add(v)
        while st:
            a = st.pop()
            comp.append(a)
            for e in a.link_edges:
                o = e.other_vert(a)
                if o not in seen:
                    seen.add(o)
                    st.append(o)
        out.append(comp)
    return out


def build():
    mesh_ob, arm = load_yurchik()
    bone = arm.data.bones["HandL"]
    head = Vector(bone.head_local)
    d = (Vector(bone.tail_local) - head).normalized()
    keep = {mesh_ob.vertex_groups[n].index for n in ("HandL", "ForearmL")}
    hand_g = mesh_ob.vertex_groups["HandL"].index

    bm = bmesh.new()
    bm.from_mesh(mesh_ob.data)
    dl = bm.verts.layers.deform.active
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if sum(w for g, w in v[dl].items() if g in keep) < 0.5],
                     context='VERTS')
    isl = islands_of(bm)
    handy = sorted([c for c in isl if any(v[dl].get(hand_g, 0) > 0.9 for v in c)], key=len, reverse=True)
    palm_isl, thumb_isl = handy[0], handy[1]
    sleeve = [v for c in isl if all(c is not h for h in handy) for v in c]

    # система кисти: t вдоль кисти, n к ладони (куда загнуты кончики), s к большому пальцу
    def tt(v):
        return (v.co - head).dot(d) * 1000

    def mean(vs):
        return sum((v.co for v in vs), Vector()) / len(vs)
    block = [v for v in palm_isl if KNUCKLE_T - 20 < tt(v) < KNUCKLE_T + 25]
    tips = [v for v in palm_isl if tt(v) > KNUCKLE_T + 40]
    n = mean(tips) - mean(block)
    n = (n - d * n.dot(d)).normalized()
    s = d.cross(n)
    if (mean(thumb_isl) - mean(palm_isl)).dot(s) < 0:
        s = -s
    to_local = Matrix((d, n, s))
    for v in bm.verts:
        v.co = (to_local @ (v.co - head)) * 1000 * SCALE        # x = t, y = n, z = s (мм)
    for v in sleeve:
        v.co.x -= SLEEVE_PULL
    bmesh.ops.delete(bm, geom=[v for v in sleeve if v.co.x < SLEEVE_KEEP], context='VERTS')

    fingers = [v for v in palm_isl if v.is_valid]
    thumb = [v for v in thumb_isl if v.is_valid]
    thumb_tip = sorted(thumb, key=lambda v: -v.co.x)[:3]
    base_v = min(thumb, key=lambda v: v.co.x)
    tip_vs = sorted(fingers, key=lambda v: -v.co.x)[:6]
    knuck_vs = [v for v in fingers if abs(v.co.x - KNUCKLE_T) < 12]
    sleeve_live = [v for v in sleeve if v.is_valid]
    sleeve_end = sorted(sleeve_live, key=lambda v: v.co.x)[:6]
    wrist_vs = [v for v in sleeve_live if abs(v.co.x - WRIST_T) < 15] or sleeve_end
    palm_n = max(v.co.y for v in fingers if v.co.x < KNUCKLE_T)  # поверхность ладони — самая «ладонная» точка ладони
    mid_s = sum(v.co.z for v in fingers) / len(fingers)

    t_of = {v: v.co.x for v in bm.verts}

    def bend(vs, t0, deg):
        R = axis_rot((0, 0, 1), deg)           # вокруг s: t поворачивается к n
        p0 = Vector((t0, palm_n, 0))
        for v in vs:
            if t_of[v] > t0:
                v.co = p0 + R @ (v.co - p0)
    bend(fingers, CURL_TIP_T, CURL_TIP)        # сначала дальний сустав, потом ближний — как цепочка костей
    bend(fingers, KNUCKLE_T, CURL)

    # в телефон: u = -t, v = +s, w = +n
    to_phone = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))
    knuckle = Vector((KNUCKLE_T, palm_n, mid_s))
    Rr = axis_rot((0, 0, 1), ROLL)
    for v in bm.verts:
        v.co = ANCHOR + Rr @ (to_phone @ (v.co - knuckle))

    def c(vs):
        vs = [v for v in vs if v.is_valid]
        return sum((v.co for v in vs), Vector()) / len(vs)

    # большой палец: повернуть вокруг основания на нужное направление и поставить основание на место
    base, tip = base_v.co.copy(), c(thumb_tip)
    q = (tip - base).rotation_difference(THUMB_TIP - THUMB_BASE)
    for v in thumb:
        v.co = THUMB_BASE + q @ (v.co - base)
    # предплечье: сгиб в запястье, плавно на первых 40 мм
    wrist = c(wrist_vs)
    q = (c(sleeve_end) - wrist).rotation_difference(SLEEVE_DIR)
    for v in sleeve_live:
        k = min(1.0, max(0.0, (WRIST_T - t_of[v]) / 40.0))
        if k > 0:
            v.co = v.co.lerp(wrist + q @ (v.co - wrist), k)
    DEBUG.update({k: tuple(round(x) for x in c(vs)) for k, vs in
                  (("thumb_tip", thumb_tip), ("tips", tip_vs), ("knuck", knuck_vs), ("sleeve_end", sleeve_end),
                   ("wrist", wrist_vs))})
    if to_local.determinant() * to_phone.determinant() < 0:     # отражение → развернуть грани
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    for v in bm.verts:                                           # (u, v, w) мм → Blender (u, -w, v) м
        u, vv, w = v.co
        v.co = Vector((u * MM, -w * MM, vv * MM))
    me = bpy.data.meshes.new("PhoneHand")
    bm.to_mesh(me)
    bm.free()
    for m in mesh_ob.data.materials:
        me.materials.append(m)
    return me


def main():
    if bpy.context.window:
        sc = bpy.data.scenes.get("PhoneHand") or bpy.data.scenes.new("PhoneHand")
        bpy.context.window.scene = sc
    else:
        sc = bpy.context.scene
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    me = build()
    ob = bpy.data.objects.new("PhoneHand_nocol", me)
    sc.collection.objects.link(ob)
    bpy.context.view_layer.update()
    for o in sc.objects:
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "phone_hand.gltf"), use_selection=True, use_active_scene=True,
                              export_keep_originals=True, export_format='GLTF_SEPARATE', export_apply=True,
                              export_yup=True)
    return {"tris": sum(len(p.vertices) - 2 for p in me.polygons), **DEBUG}


RESULT = main()
print("BUILD_PHONE_HAND", RESULT)
