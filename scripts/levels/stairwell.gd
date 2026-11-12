## Подъезд. Подняться на четвёртый этаж в квартиру 47, пока по лестнице идёт Сергей.
## Финал демо — когда Юрчик заходит в квартиру и дверь за ним закрывается.
extends Level

@export var sergey_scene: PackedScene
@export var sergey_delay := 10.0        ## через сколько секунд после входа Сергей заходит в подъезд

@onready var apt_use: Interactable = $AptDoorUse
@onready var apt_trigger: Area3D = $AptTrigger

var _door: Node3D
var _sergey: Enemy
var _ended := false


func _start() -> void:
	Game.music("mus_drone", -14.0)
	Game.set_objective("Подняться к себе — квартира 47, четвёртый этаж")
	_door = $Stairwell.find_child("AptDoor", true, false) as Node3D
	apt_use.interacted.connect(_open_apartment)
	apt_trigger.body_entered.connect(_on_apartment)
	await after(1.5)
	Game.say("Тихо. На третьем опять выкрутили лампочку.")
	if Game.flags.get("sergey", false) and sergey_scene:
		await after(sergey_delay)
		if _ended:
			return
		Game.sfx("door_bang", $SergeySpawn.global_position, 4.0, 0.0)
		Game.music("mus_chase", -8.0, 0.5)
		_sergey = spawn(sergey_scene, $SergeySpawn)
		Game.say("Внизу хлопнула дверь. Он вошёл.")


func _open_apartment(p: Player) -> void:
	apt_use.enabled = false
	p.busy(1.3, "Interact")
	Game.sfx("unlock", apt_use.global_position)
	await after(0.9)
	Game.sfx("door_open", apt_use.global_position)
	if _door:
		create_tween().set_trans(Tween.TRANS_SINE).tween_property(_door, "rotation:y", deg_to_rad(100.0), 0.8)


func _on_apartment(body: Node3D) -> void:
	if _ended or not body is Player:
		return
	_ended = true
	if _door:
		create_tween().tween_property(_door, "rotation:y", 0.0, 0.22)
	await after(0.22)
	Game.sfx("hit_1", apt_use.global_position, 4.0, 0.0)
	Game.sfx("unlock", apt_use.global_position)
	for e: Node in get_tree().get_nodes_in_group("enemy"):          # за дверью уже никто не достанет
		e.set_physics_process(false)
	Game.music("", 0.0, 2.5)
	Game.ambience("amb_room", -14.0)
	Game.set_objective("Дома")
	await after(1.2)
	Game.say("Дома.")
	await after(3.0)
	Game.sfx("door_bang", apt_use.global_position, 6.0, 0.0)
	player.shake(0.6)
	await after(2.2)
	Game.sfx("door_bang", apt_use.global_position, 6.0, 0.0)
	player.shake(0.8)
	await after(2.5)
	hud.show_ending()
