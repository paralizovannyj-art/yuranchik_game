## Микрорайон «Паскот» (docs/CITY_PLAN.md): дома и пропсы из Blender на местах блокаута, земля пока из серых плит.
## Только локация: врагов, предметов и квеста здесь пока нет.
## F1–F8 — телепорт по зонам (работает только при запуске из редактора).
extends Level

const ZONES := ["Двор Юрчика", "Проспект", "Школа", "Южные дворы", "Котельная", "Гаражи", "Пустырь", "Западный двор"]

@onready var snowfall: GPUParticles3D = $Snowfall


func _start() -> void:
	Game.set_objective("Осмотри район.  F1–F8 — телепорт по зонам")
	await after(1.5)
	Game.say("Паскот. F1–F8 — прыжок в зону.")


func _process(_delta: float) -> void:
	if player:                                   # снегопад идёт только вокруг Юрчика
		snowfall.global_position = player.global_position + Vector3(0, 18, 0)


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
