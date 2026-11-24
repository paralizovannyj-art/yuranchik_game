## Бюджет света улиц (двор, Восточный мост). Ноутбук автора (GTX 1650) не вытянет тени у всех фонарей сразу:
## - тени включены только у max_shadows ближайших к Юрчику источников в радиусе shadow_distance;
## - источники дальше visible_distance гаснут — плавно, за fade_distance метров, без «щелчка». В режиме «Обычная»
##   (Forward+) это 250 м: фонарь светит и издалека, освещённое им видно сквозь туман, как в жизни (правило автора,
##   2026-11-22). Тени дальних всё равно выключены, это дёшево. В режиме «Слабый ПК» (OpenGL) — 120 м: лимиты
##   источников подняты в настройках проекта (rendering/limits/opengl). За этим расстоянием пятно света на земле
##   рисует карточка Pool фонаря (street_light.gd) — освещённое видно и дальше;
## - источник в помещении (группа «indoor», например лампа в гараже) не отдаёт тень бюджету: без тени свет прошёл бы
##   сквозь стены. На OpenGL теней нет совсем, поэтому такой источник горит, только когда Юрчик рядом (indoor_near_low);
## - источник, который игра выключила сама (мета «off» = true, например свет в закрытом гараже), бюджет не включает;
## - ориентиры (группа «landmark»; сейчас таких в сценах нет) не гаснут никогда и получают ореол.
extends Node

@export var max_shadows := 6
@export var shadow_distance := 35.0
@export var visible_distance := 250.0
@export var visible_distance_low := 120.0  ## режим «Слабый ПК» (OpenGL)
@export var fade_distance := 15.0          ## за сколько метров до края источник плавно гаснет
@export var indoor_near_low := 8.0         ## OpenGL: лампа в помещении горит, только если Юрчик ближе
@export var update_every := 0.25           ## сек между пересчётами

var _lights: Array[Light3D] = []
var _can_shadow := {}
var _base := {}
var _timer := 0.0
var _player: Node3D
var _low := false


func _ready() -> void:
	_player = get_tree().get_first_node_in_group("player") as Node3D
	_low = RenderingServer.get_current_rendering_method() == "gl_compatibility"
	if _low:
		visible_distance = visible_distance_low
	# после _ready всех узлов: фонари (street_light.gd) к этому времени выставили свою яркость
	_collect.call_deferred()


func _collect() -> void:
	var root := get_parent()
	for l in root.find_children("*", "Light3D", true, false):
		if l is DirectionalLight3D or (_player and _player.is_ancestor_of(l)):
			continue
		_lights.append(l)
		_can_shadow[l] = l.shadow_enabled
		_base[l] = l.get("_base_energy") if l.get("_base_energy") != null else l.light_energy
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
		var f := 1.0
		if not l.is_in_group("landmark"):
			f = clampf((visible_distance - d) / fade_distance, 0.0, 1.0)
		var indoor := l.is_in_group("indoor")
		if indoor and _low and d > indoor_near_low:
			f = 0.0
		l.visible = f > 0.0 and not bool(l.get_meta("off", false))
		l.set_meta("fade", f)                                # street_light.gd: вдали вместо света — карточка Pool
		_set_energy(l, _base[l] * f)
		if indoor:
			l.shadow_enabled = _can_shadow[l] and l.visible     # своя тень, вне бюджета
		elif _can_shadow[l] and l.visible and d < shadow_distance:
			near.append([d, l])
		else:
			l.shadow_enabled = false
	near.sort_custom(func(a, b): return a[0] < b[0])
	for i in near.size():
		near[i][1].shadow_enabled = i < max_shadows


## Мерцающая лампа (flicker_light.gd) сама пишет light_energy каждый кадр — ей меняем базовую яркость.
func _set_energy(l: Light3D, e: float) -> void:
	if l.get("_base_energy") != null:
		l.set("_base_energy", e)
	else:
		l.light_energy = e


## Ореол для ориентира: светящийся спрайт того же цвета — виден сквозь туман издалека.
func _add_halo(l: Light3D) -> void:
	var m := StandardMaterial3D.new()
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	m.albedo_texture = load("res://assets/materials/lamp_halo.tres").albedo_texture
	m.albedo_color = Color(l.light_color.r, l.light_color.g, l.light_color.b, 0.6)
	m.disable_receive_shadows = true
	var q := QuadMesh.new()
	q.size = Vector2.ONE * float(l.get_meta("halo_size", 3.0))
	var mi := MeshInstance3D.new()
	mi.mesh = q
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	l.add_child(mi)
