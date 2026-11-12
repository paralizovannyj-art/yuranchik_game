## Общая основа уровня: создаёт интерфейс, запекает навигационную сетку для врагов,
## включает звук окружения и запоминает чекпойнт. Сценарий конкретного уровня — в наследниках (_start()).
class_name Level
extends Node3D

@export_group("Уровень")
@export var ambience_sound := "amb_wind"
@export var ambience_db := -12.0
@export var step_sound := "step_snow"   ## звук шагов Юрчика на этом уровне
@export var step_variants := 4
@export var flashlight_energy := 22.0   ## яркость фонарика: в тесных помещениях нужна меньше
@export_group("Навигация врагов")
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
	Game.in_game = true
	if not Game.has_item("hammer"):                 # уровень запущен напрямую из редактора (F6), а не из меню
		Game.add_item("hammer")
	Game.save_checkpoint(scene_file_path)
	Game.health_changed.emit()
	Game.ambience(ambience_sound, ambience_db)
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
