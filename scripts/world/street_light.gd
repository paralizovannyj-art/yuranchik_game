@tool
## Уличный фонарь: конус света вниз из головы фонаря, «карточка света» на земле
## (плоскость с тёплым пятном вместо второго источника — приём lighting cards из разбора DemiDevi) и ореол, который виден издалека. Ставится в основание столба, голова — в head_offset (как у модели lamp_pole).
## Цвет, яркость и мигание меняются в инспекторе.
extends Node3D

@export var color := Color(0.95, 0.58, 0.22):        ## грязный натриевый; белый — ртутная лампа
	set(v):
		color = v
		_apply()
@export var energy := 60.0                           ## яркость конуса: тусклое пятно под фонарём, вокруг — темнота
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
@export var show_pool := true:                       ## тёплое пятно света на земле под фонарём (плоскость, не источник)
	set(v):
		show_pool = v
		_apply()
@export_range(0.0, 1.0) var pool_alpha := 0.35      ## яркость пятна на земле
@export var twin_spacing := 0.0:                    ## двойная мачта (платформы моста): расстояние между двумя плафонами по оси Z, м.
	set(v):                                           ## Свет ставится под каждым плафоном, а не в центр — иначе он внутри столба,
		twin_spacing = v                              ## и когда фонарю включаются тени (вблизи), столб закрывает свет целиком.
		_apply()
@export var use_fill := false:                       ## старая слабая заливка (второй источник OmniLight) — включена на мосту
	set(v):
		use_fill = v
		_apply()

const TWIN_SHARE := 0.6                              ## яркость каждого из двух плафонов от energy
const TWIN_DROP := 0.15                              ## свет чуть ниже стекла плафона, чтобы стекло не давало тень

const SPARKLE_SHADER := preload("res://shaders/lamp_sparkle.gdshader")

@onready var spot: SpotLight3D = $Spot
@onready var pool: MeshInstance3D = $Pool
@onready var fill: OmniLight3D = get_node_or_null("Fill")
@onready var halo: MeshInstance3D = $Halo
var spot2: SpotLight3D                               ## второй плафон двойной мачты


func _enter_tree() -> void:
	# без заливки источник удаляется до _ready, чтобы light_budget.gd его не подхватил и не включил
	if not use_fill and not Engine.is_editor_hint() and has_node("Fill"):
		var f := get_node("Fill")
		remove_child(f)
		f.free()
	# второй плафон создаётся до _ready, чтобы light_budget.gd учёл его как обычный источник
	if twin_spacing > 0.0 and not Engine.is_editor_hint() and not has_node("Spot2"):
		var s2: SpotLight3D = get_node("Spot").duplicate()
		s2.set_script(null)                          # мигает только один плафон, второй горит ровно
		s2.name = "Spot2"
		add_child(s2)


func _ready() -> void:
	_apply()


func _apply() -> void:
	if not is_inside_tree() or spot == null:
		return
	spot.position = head_offset
	spot2 = get_node_or_null("Spot2")
	var e := energy
	if twin_spacing > 0.0:
		spot.position = head_offset + Vector3(0, -TWIN_DROP, twin_spacing * 0.5)
		e = energy * TWIN_SHARE
		if spot2:
			spot2.position = head_offset + Vector3(0, -TWIN_DROP, -twin_spacing * 0.5)
			spot2.light_color = color
			spot2.light_energy = e
	pool.position = Vector3(head_offset.x, pool.position.y, head_offset.z)
	pool.visible = show_pool
	if fill:
		fill.position = head_offset - Vector3(0, 0.4, 0)
		fill.visible = use_fill
		fill.light_color = color.lerp(Color.WHITE, 0.08)
	halo.position = head_offset
	halo.visible = show_halo
	spot.light_color = color
	spot.light_energy = e
	spot.set("_base_energy", e)
	spot.set("flicker_chance", 0.15 if flicker else 0.0)
	if Engine.is_editor_hint():
		return
	var pm := pool.mesh.surface_get_material(0) if pool.mesh else null
	if pm:
		pm = pm.duplicate()
		pm.albedo_color = Color(color.r, color.g, color.b, pool_alpha)
		pool.material_override = pm
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
