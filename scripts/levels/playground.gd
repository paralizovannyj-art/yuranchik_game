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
]


func _start() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 5
	add_child(layer)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(root)
	_help = HUD.mk_label(root, "", 10, HUD.C_TEXT, Rect2(10, 8, 420, 110))
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
				if id != "hammer" and Game.add_item(id):
					got += 1
			Game.say("В сумку положено предметов: %d (что не влезло — пропущено)." % got)
		KEY_7:
			Game.god = not Game.god
			Game.say("Бессмертие: %s" % ("вкл" if Game.god else "выкл"))
		KEY_0:
			Game.goto_level.call_deferred(scene_file_path)
		KEY_H:
			_help.visible = not _help.visible
		_:
			return
	_refresh_help()
	get_viewport().set_input_as_handled()


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
