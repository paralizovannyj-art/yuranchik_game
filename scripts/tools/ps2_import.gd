## Пост-обработка импорта .glb моделей из Blender.
## Чинит свечение (умножение вместо сложения) и единообразно настраивает материалы.
@tool
extends EditorScenePostImport


func _post_import(scene: Node) -> Object:
	_fix(scene)
	return scene


func _fix(node: Node) -> void:
	if node is MeshInstance3D:
		var mesh: Mesh = node.mesh
		if mesh:
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
	for child in node.get_children():
		_fix(child)
