## Общая основа уровня: создаёт интерфейс, запекает навигационную сетку для врагов,
## включает звук окружения и запоминает чекпойнт. Сценарий конкретного уровня — в наследниках (_start()).
class_name Level
extends Node3D

@export_group("Уровень")
@export var ambience_sound := "amb_wind"
@export var ambience_db := -12.0
@export var step_sound := "step_snow"   ## звук шагов Юрчика на этом уровне
@export var step_variants := 4
@export var flashlight_energy := 26.8   ## яркость фонарика (главный свет в темноте): в тесных помещениях нужна меньше
## Темнота по всей игре как в жизни (правило автора, 2026-11-24): общий свет (ambient) почти ноль, поэтому
## вдали темно, а горящие лампы и окна и освещённое ими видно с любого расстояния (LightBudget, lit_fog).
## Физика света 1:1: все лампы затухают как 1/d² (attenuation 2.0), радиус с запасом — свет не обрывается краем.
## Рядом с Юрчиком чуть светлее — «глаза привыкли к темноте». Днём (east_bridge_day) выключено.
@export var near_sight_energy := 0.2   ## яркость «привыкших глаз»: слабый свет вокруг Юрчика (0 — выключен)
@export var near_sight_range := 4.0    ## на сколько метров видно в темноте без фонарика (в помещениях меньше)
@export var tools_on_direct_start := true   ## запуск уровня из редактора (F6) — сразу с молотком и фонариком
## Пролог (квартира Юрчика): без бега, без сумки, без молотка и фонарика — Юрчик просто дома.
@export var allow_run := true          ## можно ли бежать (Shift)
@export var allow_bag := true          ## можно ли открыть сумку (I)
@export var no_tools := false          ## забрать молоток и фонарик при входе (появляется с пустыми руками)
@export_group("Навигация врагов")
@export var bake_navigation := true     ## строить ли сетку при запуске (для большого района без врагов — выключено)
@export var nav_agent_radius := 0.5     ## насколько далеко враги обходят стены
@export var nav_cell := 0.25            ## точность сетки: меньше — точнее (для тесных помещений 0.125)
@export var nav_bounds := AABB()        ## область, где враги умеют ходить (пусто — весь уровень)

var hud: HUD
var player: Player


func _ready() -> void:
	player = get_tree().get_first_node_in_group("player") as Player
	hud = HUD.new()
	hud.player = player
	add_child(hud)
	if player:
		player.step_sound = step_sound
		player.step_variants = step_variants
		player.flashlight.light_energy = flashlight_energy
		player.can_run = allow_run
	hud.bag_enabled = allow_bag
	if no_tools:
		for id: String in ["hammer", "flashlight"]:
			while Game.has_item(id):
				Game.remove_item(id)
		if player:
			player.refresh_tools()
	elif not Game.in_game and tools_on_direct_start:   # уровень запущен напрямую из редактора (F6), а не из меню
		Game.give_tools()
		if player:
			player.refresh_tools()
	Game.in_game = true
	Game.save_checkpoint(scene_file_path)
	Game.health_changed.emit()
	Game.ambience(ambience_sound, ambience_db)
	if near_sight_energy > 0.0:
		set_near_sight(near_sight_energy)
	if bake_navigation:
		_bake_navigation()
	hud.fade_in(1.6)
	_start()


func _start() -> void:
	pass


## Сетка, по которой враги ищут путь. Строится при запуске из всех неподвижных коллизий уровня.
func _bake_navigation() -> void:
	add_to_group("navsrc")
	var nm := NavigationMesh.new()
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nm.geometry_collision_mask = 1
	nm.geometry_source_geometry_mode = NavigationMesh.SOURCE_GEOMETRY_GROUPS_WITH_CHILDREN
	nm.geometry_source_group_name = &"navsrc"
	nm.cell_size = nav_cell
	nm.cell_height = nav_cell
	var map := get_world_3d().navigation_map
	NavigationServer3D.map_set_cell_size(map, nav_cell)
	NavigationServer3D.map_set_cell_height(map, nav_cell)
	nm.agent_radius = nav_agent_radius
	nm.agent_height = 1.75
	nm.agent_max_climb = 0.25
	nm.agent_max_slope = 40.0
	if nav_bounds.size != Vector3.ZERO:
		nm.filter_baking_aabb = nav_bounds
	var region := NavigationRegion3D.new()
	region.name = "NavRegion"
	region.navigation_mesh = nm
	add_child(region)
	region.bake_navigation_mesh(true)


func after(seconds: float) -> Signal:
	return get_tree().create_timer(seconds, false).timeout


func spawn(scene: PackedScene, at: Node3D, alerted := true) -> Enemy:
	var e := scene.instantiate() as Enemy
	e.start_alerted = alerted
	add_child(e)
	e.global_transform = at.global_transform
	return e


## Темнота как в жизни: рядом с Юрчиком чуть светлее (глаза привыкли), дальше — тьма.
## Невидимый слабый свет у камеры: без теней и бликов, гаснет к near_sight_range. 0 — выключить.
func set_near_sight(energy: float, fade := 0.0) -> void:
	if player == null:
		return
	var l := player.camera.get_node_or_null("NearSight") as OmniLight3D
	if l == null:
		l = OmniLight3D.new()
		l.name = "NearSight"
		l.light_color = Color(0.6, 0.66, 0.8)
		l.light_specular = 0.0
		l.light_volumetric_fog_energy = 0.0          # глаза не источник: воздух вокруг головы не светится
		l.light_bake_mode = Light3D.BAKE_DISABLED     # и не отражается от стен (отражённый свет VoxelGI/SSIL)
		l.light_cull_mask &= ~(Player.BODY_LAYER | Phone.LAYER)   # руки и телефон в 0.3 м иначе сияли бы в темноте
		l.omni_attenuation = 1.5
		l.light_energy = 0.0
		player.camera.add_child(l)
		l.position = Vector3(0, 0.1, 0)
	l.omni_range = near_sight_range
	if fade > 0.0:
		create_tween().tween_property(l, "light_energy", energy, fade)
	else:
		l.light_energy = energy
