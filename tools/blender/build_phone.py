# -*- coding: utf-8 -*-
# Телефон Юрчика «ОРБИТА» — по фото кнопочного QWERTY-бруска (красные боковины, чёрная глянцевая лицевая панель).
#   * красная рамка по периметру, чёрная крышка сзади, чёрная лицевая панель чуть утоплена в рамку;
#   * экран 4:3 почти во всю ширину, над ним динамик и надпись;
#   * блок навигации: две софт-клавиши, зелёная и красная трубки, квадратная крестовина с кнопкой в центре;
#   * QWERTY: 4 ряда по 11 клавиш (последний ряд: Shift, *, пробел, Sym, Ctrl).
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_phone.py
# Результат:
#   assets/models/phone.gltf — один объект Phone_nocol с материалами:
#     PhRed (рамка), PhBack (задняя крышка), PhPrint (лицевая панель и клавиши), PhScreen (экран);
#   assets/models/phone_layout.json — где какая клавиша/надпись (в мм, от левого верхнего угла лицевой стороны).
#
# Надписей в модели нет: PhPrint развёрнут плоской проекцией на всю лицевую сторону (UV 0..1 = W×H),
# а саму «печать» (буквы, иконки, кнопки) рисует phone.gd по phone_layout.json в SubViewport.
# PhScreen развёрнут на 0..1 — на него ложится живой экран PhoneScreen.
#
# Оси: u — вправо, v — вверх (по высоте телефона), w — к зрителю (лицевая сторона).
# В Blender это (u, -w, v), после экспорта с +Y вверх в Godot — (u, v, w): лицом к +Z, как раньше.
import bpy, bmesh, os, json, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "assets", "models")

MM = 0.001
W, H = 56.0, 108.0            # лицевая сторона, мм
R = 7.0                       # радиус углов
FRONT = 6.0                   # лицевая панель (w)
SCREEN = (-24.0, 42.0, 24.0, 6.0)   # u0, v_top, u1, v_bottom (48×36, 4:3)

MATS = ["PhRed", "PhBack", "PhPrint", "PhScreen"]
RED, BACK, PRINT, SCR = range(4)

# ---- раскладка клавиатуры: (латиница, кириллица, цифра, ширина в клавишах) ----
ROWS = [
    [("Q", "Й", ""), ("W", "Ц", "1"), ("E", "У", "2"), ("R", "К", "3"), ("T", "Е", ""), ("Y", "Н", ""),
     ("U", "Г", ""), ("I", "Ш", ""), ("O", "Щ", ""), ("P", "З", ""), ("@back", "Х", "")],
    [("A", "Ф", ""), ("S", "Ы", "4"), ("D", "В", "5"), ("F", "А", "6"), ("G", "П", ""), ("H", "Р", ""),
     ("J", "О", ""), ("K", "Л", ""), ("L", "Д", ""), ("'", "Ж", ""), ("@enter", "Э", "")],
    [("Z", "Я", ""), ("X", "Ч", "7"), ("C", "С", "8"), ("V", "М", "9"), ("B", "И", ""), ("N", "Т", ""),
     ("M", "Ь", ""), (",", "Б", ""), (".", "Ю", ""), ("?", "Ё", ""), ("@", "Ъ", "")],
]
ROW4 = [("@shift", "", "", 2), ("*", "", "+", 1), ("@space", "", "0", 4), ("Sym", "", "", 2), ("Ctrl", "", "", 2)]
KB_TOP, KB_PITCH_V, KEY_H = -12.0, 8.5, 7.6
KB_L, KB_R = -25.5, 25.5
KEY_GAP = 0.5


def rr(cu, cv, w, h, r, seg=4):
    """Скруглённый прямоугольник (против часовой)."""
    r = min(r, w / 2 - 1e-3, h / 2 - 1e-3)
    pts = []
    for k, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        ccx, ccy = cu + sx * (w / 2 - r), cv + sy * (h / 2 - r)
        a0 = math.pi / 2 * k
        for i in range(seg + 1):
            a = a0 + math.pi / 2 * i / seg
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def P(u, v, w):
    return Vector((u * MM, -w * MM, v * MM))


class Builder:
    def __init__(self):
        self.bm = bmesh.new()

    def prism(self, poly, w0, w1, mat, side_mat=None):
        bm = self.bm
        lo = [bm.verts.new(P(u, v, w0)) for u, v in poly]
        hi = [bm.verts.new(P(u, v, w1)) for u, v in poly]
        n = len(poly)
        out = [bm.faces.new(hi), bm.faces.new(list(reversed(lo)))]
        for f in out:
            f.material_index = mat
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
            f.material_index = mat if side_mat is None else side_mat
            out.append(f)
        return out

    def quad(self, u0, v0, u1, v1, w, mat):
        vs = [self.bm.verts.new(P(u, v, w)) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
        f = self.bm.faces.new(vs); f.material_index = mat


def bevel_group(b, faces, width, segs=3):
    """Фаска по острым рёбрам одной детали (faces — грани, только что созданные prism)."""
    bm = b.bm
    new_faces = set(faces)
    bmesh.ops.recalc_face_normals(bm, faces=list(new_faces))
    edges = []
    for e in bm.edges:
        if len(e.link_faces) == 2 and all(f in new_faces for f in e.link_faces):
            if e.calc_face_angle(0) > math.radians(50):
                edges.append(e)
    if edges:   # material — иначе новые грани фаски получают слот 0 (красный)
        bmesh.ops.bevel(bm, geom=edges, offset=width * MM, segments=segs, profile=0.5,
                        affect='EDGES', clamp_overlap=True, material=faces[0].material_index)


def part(b, fn, width, segs=3):
    bevel_group(b, fn(), width, segs)


def build():
    b = Builder()
    layout = {"size": [W, H], "keys": []}

    def key(cu, cv, w, h, r, kind, **kw):
        layout["keys"].append(dict(kind=kind, rect=[cu - w / 2 + W / 2, H / 2 - (cv + h / 2),
                                                    cu + w / 2 + W / 2, H / 2 - (cv - h / 2)], r=r, **kw))

    # корпус
    part(b, lambda: b.prism(rr(0, 0, W, H, R, 8), -3.0, 4.6, RED), 0.9)
    part(b, lambda: b.prism(rr(0, 0, W - 0.8, H - 0.8, R - 0.4, 8), -5.9, -3.0, BACK), 1.6)
    part(b, lambda: b.prism(rr(0, 0, W - 2.2, H - 2.2, R - 1.1, 8), 4.6, FRONT, PRINT), 0.5)
    # экран — плоская вставка поверх панели
    u0, vt, u1, vb = SCREEN
    b.quad(u0, vb, u1, vt, FRONT + 0.03, SCR)
    layout["screen"] = [u0 + W / 2, H / 2 - vt, u1 + W / 2, H / 2 - vb]
    layout["brand"] = [W / 2, H / 2 - 47.2]
    layout["earpiece"] = [W / 2 - 6.5, H / 2 - 51.2, W / 2 + 6.5, H / 2 - 50.2]
    layout["mic"] = [W / 2, H / 2 + 50.5]

    # блок навигации
    def btn(cu, cv, w, h, r, top, kind, **kw):
        part(b, lambda: b.prism(rr(cu, cv, w, h, r), FRONT - 0.2, top, PRINT), 0.3, 2)
        key(cu, cv, w, h, r, kind, **kw)
    btn(-17.5, 1.5, 15.0, 5.5, 2.0, FRONT + 0.7, "soft_music")
    btn(17.5, 1.5, 15.0, 5.5, 2.0, FRONT + 0.7, "soft_mail")
    btn(-17.5, -6.5, 15.0, 5.5, 2.0, FRONT + 0.7, "call")
    btn(17.5, -6.5, 15.0, 5.5, 2.0, FRONT + 0.7, "end")
    btn(0.0, -3.0, 15.5, 13.0, 3.6, FRONT + 0.5, "dpad")
    btn(0.0, -3.0, 7.2, 5.8, 1.6, FRONT + 1.0, "dpad_c")

    # QWERTY
    pitch = (KB_R - KB_L) / 11
    rows = [[(l, c, n, 1) for l, c, n in r] for r in ROWS] + [ROW4]
    for ri, row in enumerate(rows):
        cv = KB_TOP - KB_PITCH_V * ri - KEY_H / 2
        col = 0
        for lat, cyr, num, span in row:
            u_l = KB_L + pitch * col + KEY_GAP / 2
            u_r = KB_L + pitch * (col + span) - KEY_GAP / 2
            cu, kw = (u_l + u_r) / 2, u_r - u_l
            kind = lat[1:] if lat.startswith("@") and len(lat) > 1 else "key"
            btn(cu, cv, kw, KEY_H, 1.1, FRONT + 0.9, kind, lat=lat if kind == "key" else "", cyr=cyr, num=num)
            col += span

    # UV: печать — плоская проекция всей лицевой стороны, экран — 0..1
    bm = b.bm
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            co = lp.vert.co
            u, v = co.x / MM, co.z / MM
            if f.material_index == SCR:
                lp[uv].uv = ((u - u0) / (u1 - u0), (v - vb) / (vt - vb))
            else:
                lp[uv].uv = ((u + W / 2) / W, (v + H / 2) / H)
        f.smooth = True
    me = bpy.data.meshes.new("Phone")
    bm.to_mesh(me)
    bm.free()
    me.set_sharp_from_angle(angle=math.radians(35))
    for name in MATS:
        me.materials.append(material(name))
    return me, layout


def material(name):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    col, rough, metal = {
        "PhRed": ((0.36, 0.015, 0.02, 1), 0.32, 0.25),
        "PhBack": ((0.012, 0.013, 0.015, 1), 0.6, 0.0),
        "PhPrint": ((0.006, 0.007, 0.008, 1), 0.3, 0.0),
        "PhScreen": ((0.02, 0.05, 0.1, 1), 0.2, 0.0),
    }[name]
    bsdf.inputs["Base Color"].default_value = col
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
    with open(os.path.join(OUT, "phone_layout.json"), "w", encoding="utf-8") as fp:
        json.dump(layout, fp, ensure_ascii=False, indent=1)
    return {"tris": sum(len(p.vertices) - 2 for p in me.polygons), "keys": len(layout["keys"])}


RESULT = main()
print("BUILD_PHONE", RESULT)
