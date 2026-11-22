## Полигон: тестовая площадка для механик. Не часть сюжета.
## Витрина со всеми существами (по кругу показывают анимации), арена для драк,
## полоса препятствий (ступеньки, пандусы, лестницы), все предметы на столе.
## Клавиши цифрового ряда — спавн врагов, лечение и т. п.; H — спрятать подсказку.
extends Level

@export var enemy_scene: PackedScene
@export var sergey_scene: PackedScene

@onready var _spawns: Array[Node] = $Arena/Spawns.get_children()

var _help: Label
var _spawn_i := 0

const HELP := [
	"ПОЛИГОН   (H — скрыть)",
	"1 — офник бродит      2 — офник сразу гонится",
	"3 — Сергей            4 — убрать всех врагов",
	"5 — вылечиться        6 — все предметы в сумку",
	"7 — бессмертие        0 — перезапуск полигона",
	"E у витрины — следующая анимация     ` — отладка",
	"B — вид со стороны (сзади / сбоку / спереди),  V — полёт (noclip)",
]

## Виды со стороны по клавише V: смещение камеры в осях героя (+X — его правый бок, +Z — за спиной).
## Камера поворачивается вместе с мышью и смотрит на грудь героя.
const VIEWS := [
	["", Vector3.ZERO],
	["сзади", Vector3(0.6, 1.7, 2.6)],
	["сбоку", Vector3(2.6, 1.3, 0.0)],
	["спереди", Vector3(0.3, 1.4, -2.8)],
]

var _view := 0
var _view_cam: Camera3D


func _start() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 5
	add_child(layer)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(root)
	_help = HUD.mk_label(root, "", 15, HUD.C_TEXT, Rect2(15, 12, 690, 195))
	_refresh_help()
	Game.set_objective("Полигон: тестируй что хочешь")


func _refresh_help() -> void:
	_help.text = "\n".join(HELP) + ("\nБЕССМЕРТИЕ ВКЛ" if Game.god else "")


func _unhandled_input(event: InputEvent) -> void:
	var k := event as InputEventKey
	if k == null or not k.pressed or k.echo:
		return
	match k.physical_keycode if k.physical_keycode != KEY_NONE else k.keycode:
		KEY_1:
			_spawn_enemy(enemy_scene, false)
		KEY_2:
			_spawn_enemy(enemy_scene, true)
		KEY_3:
			_spawn_enemy(sergey_scene, true)
		KEY_4:
			for e: Node in get_tree().get_nodes_in_group("enemy"):
				e.queue_free()
			Game.say("Враги убраны.")
		KEY_5:
			Game.heal(Game.MAX_HP)
			Game.say("Здоровье полное.")
		KEY_6:
			var got := 0
			for id: String in Game.ITEMS:
				if not Game.ITEMS[id].has("fixed") and Game.add_item(id):
					got += 1
			Game.say("В сумку положено предметов: %d (что не влезло — пропущено)." % got)
		KEY_7:
			Game.god = not Game.god
			Game.say("Бессмертие: %s" % ("вкл" if Game.god else "выкл"))
		KEY_0:
			Game.goto_level.call_deferred(scene_file_path)
		KEY_H:
			_help.visible = not _help.visible
		KEY_B:
			_cycle_view()
		_:
			return
	_refresh_help()
	get_viewport().set_input_as_handled()


func _cycle_view() -> void:
	var p := get_tree().get_first_node_in_group("player") as Player
	if p == null:
		return
	_view = (_view + 1) % VIEWS.size()
	if _view_cam == null:
		_view_cam = Camera3D.new()
		_view_cam.name = "ViewCam"
		_view_cam.fov = 60.0
		add_child(_view_cam)
	var outside := _view != 0
	p.set_body_visible(outside)
	if outside:
		_view_cam.make_current()
		Game.say("Вид: %s" % VIEWS[_view][0])
	else:
		p.camera.make_current()
		Game.say("Вид: от первого лица")


func _process(_delta: float) -> void:
	if _view == 0 or _view_cam == null:
		return
	var p := get_tree().get_first_node_in_group("player") as Player
	if p == null:
		return
	var yaw := Basis(Vector3.UP, p.cam_yaw)
	var target := p.global_position + Vector3.UP * 1.0
	_view_cam.global_position = p.global_position + yaw * (VIEWS[_view][1] as Vector3)
	_view_cam.look_at(target)


## Враг появляется у одной из точек арены по очереди. Позиция ставится до добавления в сцену,
## чтобы «дом» бродячего офника был там же, где он появился.
func _spawn_enemy(scene: PackedScene, alerted: bool) -> void:
	if scene == null or _spawns.is_empty():
		return
	var at := _spawns[_spawn_i % _spawns.size()] as Node3D
	_spawn_i += 1
	var e := scene.instantiate() as Enemy
	e.start_alerted = alerted
	e.transform = at.global_transform
	add_child(e)
	Game.say("%s появился на арене." % e.display_name)
