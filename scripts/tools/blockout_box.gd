@tool
class_name BlockoutBox
extends Node3D
## Серая коробка для блокаута района (этап A в docs/CITY_PLAN.md).
## Сама строит видимый блок и коллизию. Её можно двигать мышью и менять в инспекторе:
##   размер, тип (от него зависит цвет), форма (коробка / лестница / пандус), подпись над блоком.
## Точка опоры — центр НИЗА блока. У лестницы и пандуса низ у +Z, верх у −Z (поворачивайте узел).
## Клетка текстуры = 2 метра — по ней удобно прикидывать расстояния.

const COLORS := {
	"ground": Color(0.56, 0.54, 0.5),
	"building": Color(0.43, 0.46, 0.53),
	"school": Color(0.71, 0.6, 0.29),
	"garage": Color(0.43, 0.35, 0.27),
	"industrial": Color(0.54, 0.29, 0.23),
	"construction": Color(0.63, 0.48, 0.23),
	"prop": Color(0.48, 0.48, 0.48),
	"car": Color(0.35, 0.42, 0.54),
	"tree": Color(0.24, 0.35, 0.23),
	"fence": Color(0.31, 0.34, 0.37),
	"boundary": Color(0.54, 0.17, 0.17),
	"rail": Color(0.6, 0.6, 0.6),
	"snow": Color(0.9, 0.92, 0.95),
	"pipe": Color(0.79, 0.54, 0.23),
	"road": Color(0.29, 0.3, 0.33),
	"walkable": Color(0.29, 0.54, 0.29),
}

@export var size := Vector3(4, 3, 4):
	set(v):
		size = v
		_rebuild()
@export_enum("ground", "building", "school", "garage", "industrial", "construction", "prop", "car", "tree",
		"fence", "boundary", "rail", "snow", "pipe", "road", "walkable") var kind := "building":
	set(v):
		kind = v
		_rebuild()
@export_enum("box", "stairs", "ramp") var shape := "box":
	set(v):
		shape = v
		_rebuild()
@export var label := "":       ## подпись над блоком (пусто — без подписи)
	set(v):
		label = v
		_rebuild()
@export var tint := Color(0, 0, 0, 0):   ## свой цвет вместо цвета типа (прозрачный — цвет типа)
	set(v):
		tint = v
		_rebuild()
@export var solid := true:     ## есть ли коллизия (декорации — без неё)
	set(v):
		solid = v
		_rebuild()
@export var show_mesh := true:  ## видна ли коробка; выключено — остаётся только невидимая коллизия (под лестницами-моделями)
	set(v):
		show_mesh = v
		_rebuild()

static var _materials := {}
var _built: Array[Node] = []


func _ready() -> void:
	_rebuild()


func _rebuild() -> void:
	if not is_inside_tree():
		return
	for n in _built:
		if is_instance_valid(n):
			n.queue_free()
	_built.clear()

	var mi := MeshInstance3D.new()
	var mat := _material(tint if tint.a > 0.0 else COLORS.get(kind, Color.GRAY))
	match shape:
		"ramp":
			var pm := PrismMesh.new()
			pm.left_to_right = 1.0                    # вертикальная сторона у +X меша → после поворота у −Z
			pm.size = Vector3(size.z, size.y, size.x)
			pm.material = mat
			mi.mesh = pm
			mi.rotation.y = PI / 2.0
			mi.position.y = size.y / 2.0
		"stairs":
			mi.mesh = _stairs_mesh(mat)
		_:
			var bm := BoxMesh.new()
			bm.size = size
			bm.material = mat
			mi.mesh = bm
			mi.position.y = size.y / 2.0
	if show_mesh:
		_add(mi)
	else:
		mi.free()

	if solid:
		var body := StaticBody3D.new()
		var cs := CollisionShape3D.new()
		if shape == "box":
			var bs := BoxShape3D.new()
			bs.size = size
			cs.shape = bs
			cs.position.y = size.y / 2.0
		else:                                         # лестница и пандус — гладкий наклон, ноги не цепляются
			var w := size.x / 2.0
			var r := size.z / 2.0
			var cps := ConvexPolygonShape3D.new()
			cps.points = PackedVector3Array([
				Vector3(-w, 0, r), Vector3(w, 0, r), Vector3(-w, 0, -r), Vector3(w, 0, -r),
				Vector3(-w, size.y, -r), Vector3(w, size.y, -r)])
			cs.shape = cps
		body.add_child(cs)
		_add(body)

	if label != "" and show_mesh:
		var l := Label3D.new()
		l.text = label
		l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		l.font_size = 48
		l.outline_size = 12
		l.pixel_size = 0.016
		l.position.y = size.y + 1.2
		l.visibility_range_end = 90.0
		_add(l)


func _add(n: Node) -> void:
	add_child(n)          # без owner — в файл сцены не сохраняется, строится заново при загрузке
	_built.append(n)


func _stairs_mesh(mat: Material) -> Mesh:
	var steps := maxi(1, roundi(size.y / 0.18))
	var d := size.z / steps
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in steps:
		var h := size.y * (i + 1) / steps
		var bm := BoxMesh.new()
		bm.size = Vector3(size.x, h, d)
		var z := size.z / 2.0 - d * (i + 0.5)
		st.append_from(bm, 0, Transform3D(Basis(), Vector3(0, h / 2.0, z)))
	var mesh := st.commit()
	mesh.surface_set_material(0, mat)
	return mesh


static func _material(c: Color) -> StandardMaterial3D:
	var key := c.to_html()
	if _materials.has(key):
		return _materials[key]
	var img := Image.create(32, 32, false, Image.FORMAT_RGB8)
	img.fill(c)
	var line := c.darkened(0.35)
	for i in 32:
		img.set_pixel(i, 0, line)
		img.set_pixel(0, i, line)
	var tex := ImageTexture.create_from_image(img)
	var m := StandardMaterial3D.new()
	m.albedo_texture = tex
	m.uv1_triplanar = true
	m.uv1_world_triplanar = true
	m.uv1_scale = Vector3(0.5, 0.5, 0.5)       # клетка 2 м
	m.roughness = 1.0
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	_materials[key] = m
	return m
