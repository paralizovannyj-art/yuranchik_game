## Пост-обработка импорта моделей из Blender (.gltf).
## - чинит свечение (умножение вместо сложения);
## - для окружения добавляет статические коллизии (персонажам — нет).
@tool
extends EditorScenePostImport

const NO_COLLISION := ["yurchik", "character"]


func _post_import(scene: Node) -> Object:
	var src := get_source_file().to_lower()
	var collide := true
	for k in NO_COLLISION:
		if k in src:
			collide = false
	_fix(scene, scene, collide)
	return scene


func _fix(node: Node, root: Node, collide: bool) -> void:
	for child in node.get_children():
		_fix(child, root, collide)
	if not node is MeshInstance3D:
		return
	var mi := node as MeshInstance3D
	var mesh: Mesh = mi.mesh
	if mesh == null:
		return
	for i in mesh.get_surface_count():
		var mat := mesh.surface_get_material(i) as StandardMaterial3D
		if mat == null:
			continue
		mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
		if mat.emission_texture:
			mat.emission_enabled = true
			mat.emission = Color.WHITE
			mat.emission_operator = BaseMaterial3D.EMISSION_OP_MULTIPLY
			mat.emission_energy_multiplier = 1.8
		else:
			mat.emission_enabled = false
	if collide:
		var body := StaticBody3D.new()
		body.name = "Collision"
		var cs := CollisionShape3D.new()
		cs.shape = mesh.create_trimesh_shape()
		body.add_child(cs)
		mi.add_child(body)
		body.owner = root
		cs.owner = root
