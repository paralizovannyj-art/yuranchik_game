@tool
## Декорации за краем района (этап E, docs/CITY_PLAN.md): дальние дома, ТЭЦ, балка, огни.
## Модель одна — assets/models/district/backdrop.gltf (tools/blender/build_backdrop.py); здесь её материалы
## заменяются на шейдеры: окна и дымка домов, мягкие пятна огней, снег балки — темнее дворового.
## Настройки (сколько окон горит, как быстро дома тают в дымке) — в инспекторе узла Backdrop.
extends Node3D

@export_range(0.0, 2.0) var lit_windows := 0.7:              ## множитель «сколько окон горит» (0 — город спит)
	set(v):
		lit_windows = v
		_apply()
@export var haze_color := Color(0.13, 0.1, 0.085):            ## во что дома тают вдали (цвет тумана сцены)
	set(v):
		haze_color = v
		_apply()
@export var haze_density := 0.005:                            ## больше — дома тают раньше: 200 м — силуэт в дымке, 500 м — почти растворился
	set(v):
		haze_density = v
		_apply()
@export var lights_energy := 1.0:                             ## яркость дальних огней
	set(v):
		lights_energy = v
		_apply()

@export var balka_tint := Color(0.42, 0.45, 0.55)             ## оттенок снега в балке (темнее — глубже провал)

var _house: ShaderMaterial
var _glow: ShaderMaterial


func _ready() -> void:
	_house = ShaderMaterial.new()
	_house.shader = load("res://shaders/backdrop_house.gdshader")
	_glow = ShaderMaterial.new()
	_glow.shader = load("res://shaders/backdrop_glow.gdshader")
	_apply()
	for n in find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for i in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(i)
			var mat_name := src.resource_name if src else ""
			if mat_name == "BackdropHouse":
				mi.set_surface_override_material(i, _house)
			elif mat_name == "BackdropGlow":
				mi.set_surface_override_material(i, _glow)
			elif mat_name == "BackdropSnow":
				mi.set_surface_override_material(i, _balka_material())


## Снег балки темнее дворового: низина читается как тёмный провал.
func _balka_material() -> Material:
	var m := StandardMaterial3D.new()
	m.albedo_texture = load("res://assets/textures/snow.png")
	m.albedo_color = balka_tint
	m.uv1_triplanar = true
	m.uv1_world_triplanar = true
	m.uv1_scale = Vector3.ONE * 0.25
	m.roughness = 0.95
	return m


func _apply() -> void:
	if _house == null:
		return
	_house.set_shader_parameter("lit_scale", lit_windows)
	_house.set_shader_parameter("haze_color", haze_color)
	_house.set_shader_parameter("haze_density", haze_density)
	_glow.set_shader_parameter("energy", lights_energy)
