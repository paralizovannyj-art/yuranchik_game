## Бюджет света района (этап D, docs/CITY_PLAN.md). Ноутбук автора (GTX 1650) не вытянет тени у всех фонарей сразу:
## - тени включены только у max_shadows ближайших к Юрчику источников в радиусе shadow_distance;
## - источники дальше visible_distance гаснут совсем — вдали остаются ореолы и горящие окна, выглядит так же;
## - ориентиры (группа «landmark»: труба котельной, кран, прожектор школы) не гаснут никогда и получают ореол.
extends Node

@export var max_shadows := 6
@export var shadow_distance := 35.0
@export var visible_distance := 55.0
@export var update_every := 0.25           ## сек между пересчётами

var _lights: Array[Light3D] = []
var _can_shadow := {}
var _timer := 0.0
var _player: Node3D


func _ready() -> void:
	_player = get_tree().get_first_node_in_group("player") as Node3D
	var root := get_parent()
	for l in root.find_children("*", "Light3D", true, false):
		if l is DirectionalLight3D or (_player and _player.is_ancestor_of(l)):
			continue
		_lights.append(l)
		_can_shadow[l] = l.shadow_enabled
		l.shadow_enabled = false
		if l.is_in_group("landmark"):
			_add_halo(l)
	_update()


func _process(delta: float) -> void:
	_timer -= delta
	if _timer <= 0.0:
		_timer = update_every
		_update()


func _update() -> void:
	if _player == null:
		return
	var p := _player.global_position
	var near: Array = []
	for l in _lights:
		var d := l.global_position.distance_to(p)
		l.visible = d < visible_distance or l.is_in_group("landmark")
		if _can_shadow[l] and d < shadow_distance:
			near.append([d, l])
		else:
			l.shadow_enabled = false
	near.sort_custom(func(a, b): return a[0] < b[0])
	for i in near.size():
		near[i][1].shadow_enabled = i < max_shadows


## Ореол для ориентира: светящийся спрайт того же цвета — виден сквозь туман издалека.
func _add_halo(l: Light3D) -> void:
	var m := StandardMaterial3D.new()
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	m.albedo_texture = load("res://assets/materials/lamp_halo.tres").albedo_texture
	m.albedo_color = Color(l.light_color.r, l.light_color.g, l.light_color.b, 0.95)
	m.disable_receive_shadows = true
	var q := QuadMesh.new()
	q.size = Vector2.ONE * float(l.get_meta("halo_size", 3.0))
	var mi := MeshInstance3D.new()
	mi.mesh = q
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	l.add_child(mi)
