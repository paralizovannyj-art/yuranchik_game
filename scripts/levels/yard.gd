## Двор. Сценарий: подъезд заперт → ключи от дома в гараже → ключ от гаража у ларька →
## забрал ключи от дома — появляется Сергей → добежать до подъезда.
extends Level

const STAIRWELL := "res://scenes/levels/stairwell.tscn"

@export var sergey_scene: PackedScene
@export var enemy_scene: PackedScene

@onready var home_door: Interactable = $HomeDoor
@onready var garage_lock: Interactable = $GarageLock
@onready var garage: Node3D = $GarageYur
@onready var garage_light: Light3D = $GarageYur/GarageLight


func _start() -> void:
	Game.music("mus_drone", -18.0)
	home_door.interacted.connect(_enter_home)
	home_door.locked.connect(_on_home_locked)
	garage_lock.interacted.connect(_open_garage)
	garage_lock.locked.connect(_on_garage_locked)
	Game.item_picked.connect(_on_item)
	garage_light.visible = false
	_objective()
	await after(2.5)
	Game.say("Третий час ночи. Фонари горят через один. Домой.")
	await after(7.0)
	Game.say("Tab — инвентарь.  F — фонарик.  Shift — бег.  ПКМ + ЛКМ — сильный удар.")


func _on_home_locked(_p: Player) -> void:
	Game.flags["tried_home"] = true
	_objective()


func _on_garage_locked(_p: Player) -> void:
	Game.flags["tried_garage"] = true
	_objective()


func _objective() -> void:
	if Game.has_item("key_home"):
		Game.set_objective("БЕГИ ДОМОЙ — подъезд с горящей лампой")
	elif Game.flags.get("garage_open", false):
		Game.set_objective("Забрать ключи от дома в гараже")
	elif Game.has_item("key_garage"):
		Game.set_objective("Открыть свой гараж — отдельный, в конце ряда, у мигающего фонаря")
	elif Game.flags.get("tried_garage", false):
		Game.set_objective("Найти ключ от гаража — на прилавке ларька «Продукты»")
	elif Game.flags.get("tried_home", false):
		Game.set_objective("Ключи от дома остались в гараже — в конце ряда гаражей")
	else:
		Game.set_objective("Дойти до своего подъезда — там, где горит лампа над дверью")


func _on_item(id: String) -> void:
	if id == "key_home" and not Game.flags.get("sergey", false):
		_sergey_appears()
	_objective()


func _open_garage(p: Player) -> void:
	Game.flags["garage_open"] = true
	p.busy(1.3, "Interact")
	Game.sfx("unlock", garage_lock.global_position)
	_objective()
	await after(0.7)
	Game.sfx("garage_open", garage_lock.global_position, 2.0)
	Game.emit_noise(garage_lock.global_position, 14.0)
	var left := garage.find_child("GarageDoorL", true, false) as Node3D
	var right := garage.find_child("GarageDoorR", true, false) as Node3D
	var tw := create_tween().set_parallel().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if left:
		tw.tween_property(left, "rotation:y", deg_to_rad(-105.0), 1.5)
	if right:
		tw.tween_property(right, "rotation:y", deg_to_rad(100.0), 1.5)
	garage_light.visible = true


func _sergey_appears() -> void:
	Game.flags["sergey"] = true
	Game.sfx("stinger", null, 0.0, 0.0)
	Game.music("mus_chase", -7.0, 0.4)
	if sergey_scene:
		spawn(sergey_scene, $SergeySpawn)
	if enemy_scene:
		spawn(enemy_scene, $AmbushA)
		spawn(enemy_scene, $AmbushB)
	await after(1.2)
	Game.say("Сергей. Его не убить — только оглушить и бежать.")


func _enter_home(p: Player) -> void:
	p.control = false
	p.busy(1.4, "Interact")
	Game.sfx("unlock", home_door.global_position)
	await after(0.6)
	Game.sfx("door_open", home_door.global_position)
	await hud.fade_out(1.0).finished
	Game.goto_level(STAIRWELL)
