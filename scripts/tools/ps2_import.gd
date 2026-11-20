## Пост-обработка импорта моделей из Blender (.gltf).
## - чинит свечение (умножение вместо сложения);
## - для окружения добавляет статические коллизии (персонажам и предметам — нет);
## - узлы с «nocol» в имени остаются без коллизии (ступени, перила — по ним ходят через невидимые пандусы);
## - вид из окна (window_view.gltf): без коллизии, материалы заменяются шейдером shaders/window_view.gdshader —
##   свет запечён в текстуры свечения, свой туман метели; лампы, фонарик и туман подъезда на него не действуют.
@tool
extends EditorScenePostImport

const NO_COLLISION := ["yurchik.gltf", "character", "enemy", "sergey", "monkey", "hyuga", "item_", "window_view"]   # yurchik_room/*.gltf — предметы комнаты, им коллизия нужна
const NO_FOG := ["window_view"]
const NO_SPECULAR := ["RwGlass"]   # стекло окна в комнате: без блика от лампы (иначе на стекле горит «звезда»)
const VIEW_SHADER := "res://shaders/window_view.gdshader"


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
		if mat.resource_name in NO_SPECULAR:
			mat.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
		if not fog:
			var sm := ShaderMaterial.new()
			sm.resource_name = mat.resource_name
			sm.shader = load(VIEW_SHADER)
			sm.set_shader_parameter("tex", mat.emission_texture if mat.emission_texture else mat.albedo_texture)
			mesh.surface_set_material(i, sm)
			continue
		if mat.emission_texture:
			mat.emission_enabled = true
			mat.emission = Color.WHITE
			mat.emission_operator = BaseMaterial3D.EMISSION_OP_MULTIPLY
			mat.emission_energy_multiplier = 1.8
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
