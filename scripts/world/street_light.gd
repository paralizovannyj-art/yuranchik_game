@tool
## Фонарь района (этап D, docs/CITY_PLAN.md): конус света вниз из головы фонаря, слабая заливка вокруг
## и ореол, который виден издалека. Ставится в основание столба, голова — в head_offset (как у модели lamp_pole).
## Цвет, яркость и мигание меняются в инспекторе.
extends Node3D

@export var color := Color(0.95, 0.58, 0.22):        ## грязный натриевый; белый — ртутная лампа
	set(v):
		color = v
		_apply()
@export var energy := 22.0                           ## яркость конуса: тусклое пятно под фонарём, вокруг — темнота
@export var flicker := false:                        ## мигает (старая лампа)
	set(v):
		flicker = v
		_apply()
@export var head_offset := Vector3(0, 6.3, 1.6)       ## где у модели столба плафон
@export var show_halo := true:                       ## светящийся круг вокруг плафона
	set(v):
		show_halo = v
		_apply()
@export var sparkle := false:                        ## вместо мягкого круга — маленькая искра с лучами (мост)
	set(v):
		sparkle = v
		_apply()
@export var halo_size := 2.6:                        ## размер круга/искры, м
	set(v):
		halo_size = v
		_apply()
@export_range(0.0, 1.0) var halo_alpha := 0.5      ## яркость ореола: выше — плафон превращается в светящийся шар

const SPARKLE_SHADER := preload("res://shaders/lamp_sparkle.gdshader")

@onready var spot: SpotLight3D = $Spot
@onready var fill: OmniLight3D = $Fill
@onready var halo: MeshInstance3D = $Halo


func _ready() -> void:
	_apply()


func _apply() -> void:
	if not is_inside_tree() or spot == null:
		return
	spot.position = head_offset
	fill.position = head_offset - Vector3(0, 0.4, 0)
	halo.position = head_offset
	halo.visible = show_halo
	spot.light_color = color
	fill.light_color = color.lerp(Color.WHITE, 0.08)
	spot.light_energy = energy
	spot.set("_base_energy", energy)
	spot.set("flicker_chance", 0.15 if flicker else 0.0)
	if Engine.is_editor_hint():
		return
	if halo.mesh is QuadMesh and not is_equal_approx(halo.mesh.size.x, halo_size):
		var q: QuadMesh = halo.mesh.duplicate()
		q.size = Vector2.ONE * halo_size
		halo.mesh = q
	if sparkle:
		var s := ShaderMaterial.new()
		s.shader = SPARKLE_SHADER
		s.set_shader_parameter("color", color)
		halo.material_override = s
	else:
		var m := halo.mesh.surface_get_material(0) if halo.mesh else null
		if m:
			m = m.duplicate()
			m.albedo_color = Color(color.r, color.g, color.b, halo_alpha)
			halo.material_override = m
