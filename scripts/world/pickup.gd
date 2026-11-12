## Предмет, который можно подобрать. В инспекторе достаточно выбрать item_id —
## модель подгрузится сама, а над предметом будет мерцать блик, чтобы его было видно в темноте.
class_name Pickup
extends Interactable

@export_enum("bottle", "brick", "bandage", "shawarma", "medkit", "key_garage", "key_home") var item_id: String = "bottle"
@export var glint := true

var _glint: MeshInstance3D
var _t := 0.0


func _ready() -> void:
	super()
	radius = 1.5
	prompt = "Подобрать: %s" % Game.item_name(item_id)
	var path := "res://assets/models/item_%s.gltf" % item_id
	if ResourceLoader.exists(path):
		add_child((load(path) as PackedScene).instantiate())
	if glint:
		_glint = MeshInstance3D.new()
		var q := QuadMesh.new()
		q.size = Vector2(0.22, 0.22)
		var m := StandardMaterial3D.new()
		var g := GradientTexture2D.new()
		g.gradient = Gradient.new()
		g.gradient.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0)])
		g.fill = GradientTexture2D.FILL_RADIAL
		g.fill_from = Vector2(0.5, 0.5)
		g.fill_to = Vector2(1.0, 0.5)
		g.width = 32
		g.height = 32
		m.albedo_texture = g
		m.albedo_color = Color(0.9, 0.95, 1.0, 0.8)
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
		m.no_depth_test = true
		q.material = m
		_glint.mesh = q
		_glint.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_glint.position = Vector3(0, 0.12, 0)
		add_child(_glint)
		_t = randf() * 3.0


func _process(delta: float) -> void:
	if _glint:
		_t += delta
		var k := pow(maxf(sin(_t * 2.2), 0.0), 6.0)
		_glint.scale = Vector3.ONE * (0.25 + 0.75 * k)
		_glint.transparency = 1.0 - (0.15 + 0.85 * k)


func interact(player: Player) -> void:
	if not Game.add_item(item_id):
		Game.sfx("ui_error")
		Game.say("Нет места. Освободи клетки в инвентаре (Tab).")
		return
	Game.sfx("pickup", global_position, 2.0)
	Game.say("Подобрано: %s" % Game.item_name(item_id))
	Game.item_picked.emit(item_id)
	interacted.emit(player)
	queue_free()
