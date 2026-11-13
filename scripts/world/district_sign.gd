@tool
## Табличка или вывеска района: пластина из Blender + надпись. Текст берётся по ключу из
## scripts/data/district_names.gd — чтобы поменять название, правим только тот файл.
## Узел ставится на стену лицом наружу (+Z узла смотрит от стены).
extends Node3D

const STYLES := {
	# пластина, ширина и высота поля под текст (м), толщина, цвет текста, светится ли вывеска сама
	"house": ["plate_house_nocol", 0.5, 0.24, 0.025, Color(0.82, 0.84, 0.86), false],
	"street": ["plate_street_nocol", 1.36, 0.2, 0.025, Color(0.82, 0.84, 0.86), false],
	"school": ["plate_school_nocol", 1.05, 0.3, 0.025, Color(0.1, 0.1, 0.12), false],
	"shop": ["sign_shop_nocol", 2.9, 0.32, 0.16, Color(0.35, 0.05, 0.03), true],
}

@export var key := "":                                                  ## ключ в district_names.gd
	set(v):
		key = v
		_build()
@export_enum("house", "street", "school", "shop") var style := "house":
	set(v):
		style = v
		_build()


func _ready() -> void:
	_build()


func _build() -> void:
	if not is_inside_tree():
		return
	for c in get_children():
		c.queue_free()
	var st: Array = STYLES[style]
	var scene := load("res://assets/models/district/details/%s.gltf" % st[0]) as PackedScene
	if scene:
		add_child(scene.instantiate())
	var l := Label3D.new()
	l.text = DistrictNames.text(key)
	l.font_size = 64
	l.outline_size = 0
	l.modulate = st[4]
	l.shaded = not st[5]                     # обычные таблички освещаются фонарями, вывеска ларька горит сама
	l.double_sided = false
	l.alpha_cut = Label3D.ALPHA_CUT_DISCARD
	l.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	var px: Vector2 = ThemeDB.fallback_font.get_string_size(l.text, HORIZONTAL_ALIGNMENT_LEFT, -1, l.font_size)
	l.pixel_size = minf(st[1] / maxf(px.x, 1.0), st[2] / maxf(px.y, 1.0))
	l.position = Vector3(0, 0, st[3] + 0.004)
	add_child(l)
