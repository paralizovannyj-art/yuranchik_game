# -*- coding: utf-8 -*-
# Телефон Юрчика — копия Nokia X2-00 по схеме «спереди / сзади / слева / справа».
#   * корпус 56×111×14.5 мм: толстая чёрная задняя часть со скруглённой спинкой, красная полоса по периметру
#     (спереди видна узкими красными боковинами), чёрная глянцевая лицевая панель;
#   * лицо: красная щель динамика, NOKIA и X2, экран 4:3, слева/справа клавиши-качели (софт-клавиша + трубка),
#     посередине панель с «музыкой» и «конвертом», квадратная крестовина с серебристым ободком;
#   * QWERTY 10×4, клавиши выпуклые (на профиле видны «бугорки»), нижний ряд: ↗, Shift, Sym, пробел, «,» «.» Ctrl;
#   * спина: крышка батареи (шов), камера в серебристой рамке, VGA, решётка динамика, NOKIA;
#   * справа качелька громкости и кнопка, слева заглушка карты памяти, сверху гнездо, micro-USB и зарядка.
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_phone.py
# Результат:
#   assets/models/phone.gltf — один объект Phone_nocol с материалами:
#     PhRed, PhBack (бока спинки и боковые кнопки), PhPrint (лицо и клавиши), PhBackPrint (спина),
#     PhScreen (экран), PhChrome (рамка камеры), PhHole (разъёмы);
#   assets/models/phone_layout.json — что где нарисовать (мм от левого верхнего угла; спина — как на виде сзади).
#
# Надписей в модели нет. PhPrint и PhBackPrint развёрнуты плоской проекцией в одну текстуру 2W×H:
# левая половина — лицо, правая — спина (зеркально, как на виде сзади). Рисует её phone.gd по phone_layout.json.
#
# Полигонаж (PS2, разбор docs/design/ps2-style/how-to-make-ps2-graphics-wushin.md): мало сегментов
# у скруглений и фасок, детали — в текстуре. Было ~10.3k треугольников.
#
# Оси: u — вправо, v — вверх, w — к зрителю (лицо). В Blender это (u, -w, v); в Godot после экспорта — (u, v, w).
import bpy, bmesh, os, json, math

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "assets", "models")

MM = 0.001
W, H = 56.0, 111.0
R = 8.0
W_BACK, W_RED, W_FACE = -8.5, 0.6, 5.0      # спинка до W_RED, красная полоса до W_FACE, лицевая панель до FRONT
FRONT = 6.0

MATS = ["PhRed", "PhBack", "PhPrint", "PhScreen", "PhBackPrint", "PhChrome", "PhHole"]
RED, BACK, PRINT, SCR, BPRINT, CHROME, HOLE = range(len(MATS))

# ---- клавиатура: (латиница, второй символ, кириллица) ----
ROWS = [
    [("Q", "!", "Й"), ("W", "\"", "Ц"), ("E", "+", "У"), ("R", "1", "К"), ("T", "2", "Е"),
     ("Y", "3", "Н"), ("U", "*", "Г"), ("I", "?", "Ш"), ("O", "Ъ", "Щ"), ("P", "Х", "З")],
    [("A", "%", "Ф"), ("S", "@", "Ы"), ("D", "/", "В"), ("F", "4", "А"), ("G", "5", "П"),
     ("H", "6", "Р"), ("J", "#", "О"), ("K", "-", "Л"), ("L", "=", "Д"), ("@back", "", "")],
    [("Z", "(", "Я"), ("X", ")", "Ч"), ("C", "'", "С"), ("V", "7", "М"), ("B", "8", "И"),
     ("N", "9", "Т"), ("M", "0", "Ь"), ("", "Ж", "Б"), ("", "Э", "Ю"), ("@enter", "", "")],
]
ROW4 = [("@fn", 1), ("@shift", 1), ("@sym", 1), ("@space", 4), ("@comma", 1), ("@period", 1), ("@ctrl", 1)]
KB_X0, KB_X1 = 2.1, 53.9
KB_ROWS = [(73.0, 80.1), (80.1, 87.1), (87.1, 94.1), (94.1, 103.4)]
GAP = 0.45


def rr(cu, cv, w, h, r, seg=4):
    """Скруглённый прямоугольник (против часовой)."""
    r = min(r, w / 2 - 1e-3, h / 2 - 1e-3)
    pts = []
    for k, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        ccx, ccy = cu + sx * (w / 2 - r), cv + sy * (h / 2 - r)
        for i in range(seg + 1):
            a = math.pi / 2 * (k + i / seg)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def circle(cu, cv, r, n=16):
    return [(cu + r * math.cos(2 * math.pi * i / n), cv + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def tl(x0, y0, x1, y1):
    """Прямоугольник в мм от левого верхнего угла лица → центр и размер в осях u, v."""
    return (x0 + x1) / 2 - W / 2, H / 2 - (y0 + y1) / 2, x1 - x0, y1 - y0


def P(u, v, w):
    return (u * MM, -w * MM, v * MM)


bm = bmesh.new()


def prism(poly, lo, hi, mat, axis="w"):
    """Призма: poly в плоскости двух осей, вытянута по третьей (axis) от lo до hi."""
    def co(a, b, c):
        return P(a, b, c) if axis == "w" else P(a, c, b)          # axis "v": poly в (u, w)
    vl = [bm.verts.new(co(a, b, lo)) for a, b in poly]
    vh = [bm.verts.new(co(a, b, hi)) for a, b in poly]
    faces = [bm.faces.new(vh), bm.faces.new(list(reversed(vl)))]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((vl[i], vl[j], vh[j], vh[i])))
    for f in faces:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return faces


def bevel(faces, width, segs=3, keep=None):
    """Фаска по острым рёбрам детали; keep(w) — какие рёбра брать по их положению вдоль w."""
    fs = set(faces)
    edges = []
    for e in bm.edges:
        if len(e.link_faces) == 2 and all(f in fs for f in e.link_faces) and e.calc_face_angle(0) > math.radians(50):
            w = -(e.verts[0].co.y + e.verts[1].co.y) / 2 / MM
            if keep is None or keep(w):
                edges.append(e)
    if edges and width > 0:
        bmesh.ops.bevel(bm, geom=edges, offset=width * MM, segments=segs, profile=0.5,
                        affect='EDGES', clamp_overlap=True, material=faces[0].material_index)


def part(poly, lo, hi, mat, width, segs=3, keep=None, axis="w"):
    bevel(prism(poly, lo, hi, mat, axis), width, segs, keep)


def build():
    front, back = [], []

    def item(lst, kind, rect, **kw):
        lst.append(dict(kind=kind, rect=[round(x, 3) for x in rect], **kw))

    # ---------------- корпус
    part(rr(0, 0, W, H, R, 4), W_BACK, W_RED, BACK, 3.2, 2, keep=lambda w: w < 0)          # спинка, скруглена назад
    part(rr(0, 0, W, H - 1.2, R - 0.6, 4), W_RED, W_FACE, RED, 1.2, 1, keep=lambda w: w > 3)  # красная полоса
    part(rr(0, 0, W - 3.8, H - 0.4, R - 1.0, 4), W_FACE - 0.2, FRONT, PRINT, 0.6, 1, keep=lambda w: w > 5.5)

    # экран
    x0, y0, x1, y1 = 4.65, 17.6, 51.35, 52.9
    cu, cv, sw, sh = tl(x0, y0, x1, y1)
    vs = [bm.verts.new(P(u, v, FRONT + 0.03)) for u, v in
          ((cu - sw / 2, cv - sh / 2), (cu + sw / 2, cv - sh / 2), (cu + sw / 2, cv + sh / 2), (cu - sw / 2, cv + sh / 2))]
    bm.faces.new(vs).material_index = SCR
    screen = (cu - sw / 2, cv - sh / 2, cu + sw / 2, cv + sh / 2)
    item(front, "screen", [x0, y0, x1, y1])
    item(front, "earpiece", [22.3, 5.8, 33.7, 7.2])
    item(front, "brand", [21.8, 11.9, 34.2, 14.1])
    item(front, "model", [5.3, 12.9, 8.5, 14.3])
    item(front, "mic", [44.0, 105.0, 45.0, 106.0])

    # ---------------- навигация
    def key(rect, top, kind, r=0.9, width=0.45, segs=1, seg=2, **kw):
        cu, cv, kw_, kh = tl(*rect)
        part(rr(cu, cv, kw_, kh, r, seg), FRONT - 0.3, top, PRINT, width, segs, keep=lambda w: w > FRONT)
        item(front, kind, rect, **kw)
    key([2.1, 56.3, 12.5, 72.6], FRONT + 0.6, "lsk", r=1.6)
    key([43.5, 56.3, 53.9, 72.6], FRONT + 0.6, "rsk", r=1.6)
    key([12.9, 56.3, 43.1, 72.6], FRONT + 0.35, "mid", r=1.2)
    key([21.8, 58.0, 34.2, 70.8], FRONT + 1.0, "dpad", r=4.0, width=0.5)
    key([24.3, 60.7, 31.7, 68.1], FRONT + 1.35, "dpad_c", r=2.4, width=0.5)

    # ---------------- QWERTY
    pitch = (KB_X1 - KB_X0) / 10
    rows = [[(l, s, c, 1) for l, s, c in r] for r in ROWS] + [[(l, "", "", n) for l, n in ROW4]]
    for ri, row in enumerate(rows):
        ya, yb = KB_ROWS[ri]
        col = 0
        for lat, sym, cyr, span in row:
            rect = [KB_X0 + pitch * col + GAP / 2, ya + GAP / 2, KB_X0 + pitch * (col + span) - GAP / 2, yb - GAP / 2]
            kind = lat[1:] if lat.startswith("@") else "key"
            key(rect, FRONT + 1.5, kind, r=0.8, width=0.85, segs=1, seg=1,
                lat=lat if kind == "key" else "", sym=sym, cyr=cyr)
            col += span

    # ---------------- спина (координаты как на виде сзади: x слева направо, глядя на спину)
    def bu(x):                      # x на виде сзади → u
        return W / 2 - x
    cam = (27.4, 21.0)
    part(rr(bu(cam[0]), H / 2 - cam[1], 13.4, 13.4, 3.8), W_BACK - 0.7, W_BACK + 0.6, CHROME, 0.5, 1,
         keep=lambda w: w < W_BACK)
    part(rr(bu(cam[0]), H / 2 - cam[1], 9.4, 9.4, 2.2), W_BACK - 0.85, W_BACK + 0.6, BPRINT, 0.2, 1,
         keep=lambda w: w < W_BACK)
    item(back, "camera", [cam[0] - 4.7, cam[1] - 4.7, cam[0] + 4.7, cam[1] + 4.7])
    item(back, "cover", [1.4, 20.8, 54.6, 88.5])
    item(back, "vga", [13.6, 17.6, 19.2, 19.8])
    item(back, "grille", [37.4, 15.4, 49.0, 26.0])
    item(back, "brand", [19.6, 34.0, 36.4, 36.8])

    # ---------------- боковые кнопки и разъёмы
    def side(y0_, y1_, sgn, out, w0, w1, mat=BACK):
        cv, h = H / 2 - (y0_ + y1_) / 2, y1_ - y0_
        part(rr(sgn * (W / 2 - 1.0 + out / 2), cv, 2.0 + out, h, min(1.0, h / 2), 2), w0, w1, mat, 0.35, 1)
    side(20.0, 42.5, 1, 0.7, -2.2, 1.0)            # справа: громкость
    side(75.7, 87.0, 1, 0.6, -2.2, 1.0)            # справа: камера/блокировка
    side(20.0, 42.5, -1, 0.15, -4.0, 0.9)          # слева: заглушка карты памяти
    top = H / 2
    for poly in (circle(-12.0, -3.4, 1.7, 8), rr(1.5, -3.4, 7.0, 2.4, 0.8), circle(13.0, -3.4, 1.1, 8)):
        prism(poly, top - 0.3, top + 0.04, HOLE, axis="v")

    # спина: грани, смотрящие назад, получают печать
    for f in bm.faces:
        if f.material_index == BACK and f.normal.y > 0.45:
            f.material_index = BPRINT

    # UV
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            u, v = lp.vert.co.x / MM, lp.vert.co.z / MM
            t = (v + H / 2) / H
            if f.material_index == SCR:
                lp[uv].uv = ((u - screen[0]) / (screen[2] - screen[0]), (v - screen[1]) / (screen[3] - screen[1]))
            elif f.material_index == BPRINT:
                lp[uv].uv = ((W + W / 2 - u) / (2 * W), t)
            else:
                lp[uv].uv = ((u + W / 2) / (2 * W), t)
        f.smooth = True
    me = bpy.data.meshes.new("Phone")
    bm.to_mesh(me)
    bm.free()
    me.set_sharp_from_angle(angle=math.radians(35))
    for name in MATS:
        me.materials.append(material(name))
    return me, {"size": [W, H], "front": front, "back": back}


def material(name):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    col, rough, metal = {
        "PhRed": ((0.42, 0.012, 0.016, 1), 0.3, 0.35),
        "PhBack": ((0.014, 0.015, 0.017, 1), 0.55, 0.0),
        "PhPrint": ((0.006, 0.007, 0.008, 1), 0.25, 0.0),
        "PhBackPrint": ((0.014, 0.015, 0.017, 1), 0.6, 0.0),
        "PhScreen": ((0.02, 0.05, 0.1, 1), 0.2, 0.0),
        "PhChrome": ((0.32, 0.33, 0.35, 1), 0.3, 0.9),
        "PhHole": ((0.002, 0.002, 0.002, 1), 0.9, 0.0),
    }[name]
    bsdf.inputs["Base Color"].default_value = col
    m.diffuse_color = col
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


def main():
    if bpy.context.window:
        sc = bpy.data.scenes.get("Phone") or bpy.data.scenes.new("Phone")
        bpy.context.window.scene = sc
    else:
        sc = bpy.context.scene
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    me, layout = build()
    ob = bpy.data.objects.new("Phone_nocol", me)
    sc.collection.objects.link(ob)
    bpy.context.view_layer.update()
    for o in sc.objects:
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "phone.gltf"), use_selection=True, use_active_scene=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    with open(os.path.join(OUT, "phone_layout.json"), "w", encoding="utf-8", newline="\n") as fp:
        json.dump(layout, fp, ensure_ascii=False, indent=1)
    return {"tris": sum(len(p.vertices) - 2 for p in me.polygons), "front": len(layout["front"])}


RESULT = main()
print("BUILD_PHONE", RESULT)
