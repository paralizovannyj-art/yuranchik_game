## Пост-обработка импорта моделей из Blender (.gltf).
## - чинит свечение (умножение вместо сложения);
## - для окружения добавляет статические коллизии (персонажам и предметам — нет);
## - узлы с «nocol» в имени остаются без коллизии (ступени, перила — по ним ходят через невидимые пандусы);
## - вид из окна (window_view.gltf): без коллизии и без тумана, свет сцены на него не действует — освещение
##   запечено в текстуры свечения, а туман и фонарик подъезда испортили бы дома напротив.
@tool
extends EditorScenePostImport

const NO_COLLISION := ["yurchik.gltf", "character", "enemy", "sergey", "item_", "window_view"]   # yurchik_room.gltf — комната, ей коллизия нужна
const NO_FOG := ["window_view"]


func _post_import(scene: Node) -> Object:
	var src := get_source_file().to_lower()
	var collide := true
	for k: String in NO_COLLISION:
		if k in src:
			collide = false
	var fog := true
	for k: String in NO_FOG:
		if k in src:
			fog = false
	_fix(scene, scene, collide, fog)
	return scene


func _fix(node: Node, root: Node, collide: bool, fog := true) -> void:
	for child in node.get_children():
		_fix(child, root, collide, fog)
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
		if not fog:
			mat.disable_fog = true
			# свет комнаты (фонарик, лампы) не должен светить на улицу: цвет — только из текстуры свечения
			mat.albedo_color = Color.BLACK
			mat.metallic_specular = 0.0
			mat.roughness = 1.0
		if mat.emission_texture:
			mat.emission_enabled = true
			mat.emission = Color.WHITE
			mat.emission_operator = BaseMaterial3D.EMISSION_OP_MULTIPLY
			mat.emission_energy_multiplier = 1.8 if fog else 3.2   # вид из окна светится сам, без ламп сцены
		else:
			mat.emission_enabled = false
	if collide and not "nocol" in String(mi.name).to_lower():
		var body := StaticBody3D.new()
		body.name = "Collision"
		var cs := CollisionShape3D.new()
		cs.shape = mesh.create_trimesh_shape()
		body.add_child(cs)
		mi.add_child(body)
		body.owner = root
		cs.owner = root
