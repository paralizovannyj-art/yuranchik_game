"""AO окружения в цвета вершин (приём из разбора DemiDevi, docs/design/ps2-style/ps2-environment-vertex-colors-demidevi.md).

Берёт готовую игровую модель (.gltf), ставит её туда, где дом стоит в district.blend (соседи и земля
дают затенение), запекает Cycles AO в атрибут цвета вершин, ослабляет (FLOOR) и экспортирует обратно
в тот же .gltf. Материалы и текстуры остаются как в игре. В Godot цвет вершин умножает текстуру
(scripts/tools/ps2_import.gd включает vertex_color_use_as_albedo), материал остаётся освещаемым — фонарик работает.

Запуск через Blender MCP при открытом tools/blender/district.blend:
    exec(open(r".../tools/blender/vertex_ao.py", encoding="utf-8").read(), {"NAMES": ["homeyard_homebuilding"]})
district.blend не сохраняется и не меняется.
"""
import os
import bpy
import bmesh
import mathutils

HERE = os.path.dirname(bpy.data.filepath)
MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "assets", "models", "district"))
DISTANCE = 1.5      # м, как далеко ищется затенение
FLOOR = 0.45        # самый тёмный угол (sRGB); 1.0 — без затенения
SAMPLES = 64
SCENE = "District"


def bake_one(name):
    sc = bpy.data.scenes[SCENE]
    bpy.context.window.scene = sc
    vl = bpy.context.view_layer
    src = bpy.data.objects[name]
    path = os.path.join(MODELS, name + ".gltf")

    before_obj, before_mat, before_mesh = set(bpy.data.objects), set(bpy.data.materials), set(bpy.data.meshes)
    bpy.ops.import_scene.gltf(filepath=path)
    ob = [o for o in bpy.data.objects if o not in before_obj and o.type == 'MESH'][0]
    ob.matrix_world = src.matrix_world.copy()
    src.hide_render = True

    gm = bpy.data.meshes.new("tmp_ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=120)
    bm.to_mesh(gm)
    bm.free()
    ground = bpy.data.objects.new("tmp_ground", gm)
    sc.collection.objects.link(ground)
    zmin = min((src.matrix_world @ mathutils.Vector(c)).z for c in src.bound_box)
    ground.location = (src.location.x, src.location.y, zmin)

    old_world, old_engine = sc.world, sc.render.engine
    world = bpy.data.worlds.new("tmp_bake_world")
    sc.world = world
    world.light_settings.distance = DISTANCE
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = SAMPLES

    me = ob.data
    ca = me.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
    me.color_attributes.active_color = ca
    me.color_attributes.render_color_index = me.color_attributes.active_color_index
    for o in vl.objects:
        o.select_set(False)
    ob.select_set(True)
    vl.objects.active = ob
    bpy.ops.object.bake(type='AO', target='VERTEX_COLORS', margin=0)
    for d in ca.data:
        x = FLOOR + (1 - FLOOR) * d.color_srgb[0]
        d.color_srgb = (x, x, x, 1.0)

    # имена как в исходном gltf (импорт добавляет .001 к занятым)
    renamed = []
    for slot in ob.material_slots:
        m = slot.material
        if m and m.name.endswith(".001"):
            base = m.name[:-4]
            other = bpy.data.materials.get(base)
            if other:
                other.name = base + "__tmp"
                renamed.append((other, base))
            m.name = base
    src_name, src_mesh = src.name, src.data
    src.name = name + "__tmp"
    ob.name = name
    mesh_clash = bpy.data.meshes.get(name)
    if mesh_clash and mesh_clash is not me:
        mesh_clash.name = name + "__tmp"
    me.name = name

    ob.matrix_world = mathutils.Matrix.Identity(4)
    for s in bpy.data.scenes:
        for layer in s.view_layers:
            for o in s.objects:
                o.select_set(False, view_layer=layer)
    ob.select_set(True)
    vl.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True,
                              export_vertex_color='ACTIVE')
    vals = [d.color_srgb[0] for d in ca.data]

    # уборка: district.blend возвращается к исходному виду
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    for m in set(bpy.data.materials) - before_mat:
        bpy.data.materials.remove(m)
    for other, base in renamed:
        other.name = base
    src.name = src_name
    if mesh_clash and mesh_clash is not me:
        mesh_clash.name = name
    src.hide_render = False
    bpy.data.objects.remove(ground)
    bpy.data.meshes.remove(gm)
    sc.world = old_world
    bpy.data.worlds.remove(world)
    sc.render.engine = old_engine
    for m in set(bpy.data.meshes) - before_mesh:
        if m.users == 0:
            bpy.data.meshes.remove(m)
    return {"name": name, "verts": len(vals), "mean": round(sum(vals) / len(vals), 3), "min": round(min(vals), 3)}


result = [bake_one(n) for n in globals().get("NAMES", ["homeyard_homebuilding"])]
print(result)
