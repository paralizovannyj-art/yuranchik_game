## Микрорайон «Паскот» (docs/CITY_PLAN.md): дома и пропсы из Blender на местах блокаута.
## Сценарий — как в старом дворе, но без Сергея и офников:
## подъезд заперт → ключи от дома в гараже (за южным домом, в конце ряда «ракушек») →
## ключ от гаража на прилавке ларька «Продукты» → с ключами домой → подъезд (stairwell.tscn) → комната Юрчика.
## F1–F8 — телепорт по зонам (работает только при запуске из редактора).
extends Level

const ZONES := ["Двор Юрчика", "Проспект", "Школа", "Южные дворы", "Котельная", "Гаражи", "Пустырь", "Западный двор"]
const STAIRWELL := "res://scenes/levels/stairwell.tscn"

@onready var snowfall: GPUParticles3D = $Snowfall
@onready var home_door: Interactable = $Quest/HomeDoor
@onready var garage_lock: Interactable = $Quest/GarageYur/GarageLock
@onready var garage: Node3D = $Quest/GarageYur
@onready var garage_light: Light3D = $Quest/GarageYur/GarageLight


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
	await after(4.0)
	Game.text("Мама", "Юра ты где? Уже ночь. Ключи у тебя? Подъезд закрыли, домофон опять не работает.")
	if Game.hint("phone"):
		await after(1.2)
		Game.say("Tab — телефон.")


func _process(_delta: float) -> void:
	if player:                                   # снегопад идёт только вокруг Юрчика
		snowfall.global_position = player.global_position + Vector3(0, 18, 0)


func _on_home_locked(_p: Player) -> void:
	Game.flags["tried_home"] = true
	_objective()


func _on_garage_locked(_p: Player) -> void:
	Game.flags["tried_garage"] = true
	_objective()


func _objective() -> void:
	if Game.has_item("key_home"):
		Game.set_objective("Домой — подъезд с горящей лампой над дверью")
	elif Game.flags.get("garage_open", false):
		Game.set_objective("Забрать ключи от дома в гараже")
	elif Game.has_item("key_garage"):
		Game.set_objective("Открыть свой гараж — за южным домом, в конце ряда «ракушек», под мигающей лампой")
	elif Game.flags.get("tried_garage", false):
		Game.set_objective("Найти ключ от гаража — на прилавке ларька «Продукты»")
	elif Game.flags.get("tried_home", false):
		Game.set_objective("Ключи от дома остались в гараже — за южным домом, в конце ряда «ракушек»")
	else:
		Game.set_objective("Дойти до своего подъезда — там, где горит лампа над дверью")


func _on_item(_id: String) -> void:
	_objective()


func _open_garage(p: Player) -> void:
	Game.flags["garage_open"] = true
	p.busy(1.3, "ItemPlace")
	Game.sfx("unlock", garage_lock.global_position)
	_objective()
	await after(0.7)
	Game.sfx("garage_open", garage_lock.global_position, 2.0)
	var left := garage.find_child("GarageDoorL", true, false) as Node3D
	var right := garage.find_child("GarageDoorR", true, false) as Node3D
	var tw := create_tween().set_parallel().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if left:
		tw.tween_property(left, "rotation:y", deg_to_rad(-105.0), 1.5)
	if right:
		tw.tween_property(right, "rotation:y", deg_to_rad(100.0), 1.5)
	garage_light.visible = true


func _enter_home(p: Player) -> void:
	p.control = false
	p.busy(1.4, "ItemPlace")
	Game.sfx("unlock", home_door.global_position)
	await after(0.6)
	Game.sfx("door_open", home_door.global_position)
	await hud.fade_out(1.0).finished
	Game.goto_level(STAIRWELL)


func _unhandled_input(event: InputEvent) -> void:
	if not OS.is_debug_build() or not (event is InputEventKey) or not event.pressed or event.echo:
		return
	var i: int = event.keycode - KEY_F1
	if i < 0 or i >= ZONES.size():
		return
	var m := get_node_or_null("Teleports/Tp%d" % (i + 1)) as Node3D
	if m and player:
		teleport(m.global_transform)
		Game.say(ZONES[i])
		get_viewport().set_input_as_handled()


## Перенести Юрчика вместе с камерой (камера иначе «долетала» бы через весь район).
func teleport(to: Transform3D) -> void:
	player.global_transform = to
	player.velocity = Vector3.ZERO
	var yaw := to.basis.get_euler().y
	player.cam_yaw = yaw
	player.set("_yaw_target", yaw)
	player.set("_cam_pos", to.origin + Vector3.UP * player.eye_height)
