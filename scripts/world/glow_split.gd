## Отделить светящееся стекло одной лампы от общего меша: у слитых моделей (подъезд, мост) стёкла всех ламп —
## одна поверхность с одним материалом, и погасить одну лампу нельзя. split() переносит треугольники светящихся
## поверхностей в радиусе от точки в свои поверхности с копиями материалов и возвращает эти копии —
## их гасит мигалка (flicker_light.gd), как в жизни: при провале тускнеет и сама колба.
class_name GlowSplit
extends RefCounted


static func split(mi: MeshInstance3D, world_point: Vector3, radius: float) -> Array[BaseMaterial3D]:
	var made: Array[BaseMaterial3D] = []
	if mi == null or not mi.mesh is ArrayMesh:
		return made
	var src := mi.mesh as ArrayMesh
	var p := mi.global_transform.affine_inverse() * world_point
	# сначала только разметка: огромные слитые меши (поле, мост) не пересобираем, если стекла рядом нет
	var parts := {}                                                # поверхность → [near, rest]
	for i in src.get_surface_count():
		var mat := _material(mi, i)
		if not (mat is BaseMaterial3D and (mat as BaseMaterial3D).emission_enabled):
			continue
		if src.surface_get_primitive_type(i) != Mesh.PRIMITIVE_TRIANGLES:
			continue
		var arrays := src.surface_get_arrays(i)
		var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array(range(v.size()))
		var near := PackedInt32Array()
		var rest := PackedInt32Array()
		for t in range(0, idx.size(), 3):
			var c := (v[idx[t]] + v[idx[t + 1]] + v[idx[t + 2]]) / 3.0
			if c.distance_to(p) < radius:
				near.append_array(PackedInt32Array([idx[t], idx[t + 1], idx[t + 2]]))
			else:
				rest.append_array(PackedInt32Array([idx[t], idx[t + 1], idx[t + 2]]))
		if not near.is_empty():
			parts[i] = [near, rest]
	if parts.is_empty():
		return made
	var dst := ArrayMesh.new()
	for i in src.get_surface_count():
		var arrays := src.surface_get_arrays(i)
		var mat := _material(mi, i)
		if not parts.has(i):
			dst.add_surface_from_arrays(src.surface_get_primitive_type(i), arrays)
			dst.surface_set_material(dst.get_surface_count() - 1, mat)
			continue
		var rest: PackedInt32Array = parts[i][1]
		if not rest.is_empty():
			var a := arrays.duplicate()
			a[Mesh.ARRAY_INDEX] = rest
			dst.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, a)
			dst.surface_set_material(dst.get_surface_count() - 1, mat)
		var b := arrays.duplicate()
		b[Mesh.ARRAY_INDEX] = parts[i][0]
		dst.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, b)
		var own := (mat as BaseMaterial3D).duplicate() as BaseMaterial3D
		dst.surface_set_material(dst.get_surface_count() - 1, own)
		made.append(own)
	for i in mi.get_surface_override_material_count():
		mi.set_surface_override_material(i, null)                  # переопределения перенесены в материалы нового меша
	mi.mesh = dst
	return made


static func _material(mi: MeshInstance3D, i: int) -> Material:
	var m := mi.get_surface_override_material(i)
	return m if m else mi.mesh.surface_get_material(i)


## Найти в сцене светящиеся меши рядом с точкой и отделить стекло. Огромные слитые меши тоже подходят.
static func split_near(root: Node, world_point: Vector3, radius: float) -> Array[BaseMaterial3D]:
	var all: Array[BaseMaterial3D] = []
	for n: Node in root.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		if mi.mesh == null or not mi.is_visible_in_tree():
			continue
		var box := mi.global_transform * mi.get_aabb()
		if not box.grow(radius).has_point(world_point):
			continue
		all.append_array(split(mi, world_point, radius))
	return all
