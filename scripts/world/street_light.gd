@tool
## Фонарь района (этап D, docs/CITY_PLAN.md): конус света вниз из головы фонаря, слабая заливка вокруг
## и ореол, который виден издалека. Ставится в основание столба, голова — в head_offset (как у модели lamp_pole).
## Цвет, яркость и мигание меняются в инспекторе.
extends Node3D

@export var color := Color(1, 0.52, 0.18):           ## натриевый оранжевый; белый — ртутная лампа
	set(v):
		color = v
		_apply()
@export var energy := 36.0                           ## яркость конуса
@export var flicker := false:                        ## мигает (старая лампа)
	set(v):
		flicker = v
		_apply()
@export var head_offset := Vector3(0, 6.3, 1.6)       ## где у модели столба плафон

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
	spot.light_color = color
	fill.light_color = color.lerp(Color.WHITE, 0.08)
	spot.light_energy = energy
	spot.set("_base_energy", energy)
	var m := halo.get_active_material(0)
	if m and not Engine.is_editor_hint():
		m = m.duplicate()
		m.albedo_color = Color(color.r, color.g, color.b, 0.9)
		halo.material_override = m
	spot.set("flicker_chance", 0.15 if flicker else 0.0)
