## Подъезд. Подняться на четвёртый этаж в квартиру 47, пока по лестнице идёт Сергей.
## Финал демо — дома: Юрчик заходит к себе в комнату (модель по фото — tools/blender/build_yurchik_room.py),
## включает старый комп. Если за ним шёл Сергей (старый двор) — тот начинает ломиться в дверь.
## В комнате свет сначала выключен: выключатель у проёма (LightSwitchUse) щёлкает клавишей, старая лампочка
## моргает, прежде чем разгореться, и потом изредка «проседает».
extends Level

@export var sergey_scene: PackedScene
@export var sergey_delay := 10.0        ## через сколько секунд после входа Сергей заходит в подъезд

@onready var apt_use: Interactable = $AptDoorUse
@onready var apt_trigger: Area3D = $AptTrigger
@onready var pc_use: Interactable = $PCUse
@onready var monitor_light: OmniLight3D = $Lights/Monitor
@onready var light_use: Interactable = $LightSwitchUse
@onready var room_light: OmniLight3D = $Lights/AptRoom

var _door: Node3D
var _sergey: Enemy
var _ended := false
var _screen: StandardMaterial3D           ## материал экрана монитора: яркость свечения = «включён»
var _light_on := false                    ## люстра в комнате
var _light_busy := false                  ## идёт щелчок/моргание — второй раз не нажать
var _room_energy := 1.3                   ## яркость люстры из инспектора (AptRoom)
var _bulb_glow := 1.0                     ## свечение плафонов при включённом свете
var _bulbs: StandardMaterial3D            ## материал плафонов люстры (копия, чтобы гасить только их)
var _switch_key: Node3D                   ## клавиша выключателя (качается)
var _flickered := false                   ## первое включение — всегда с морганием и репликой


func _start() -> void:
	Game.music("mus_drone", -14.0)
	Game.set_objective("Подняться к себе — квартира 47, четвёртый этаж")
	_door = $Stairwell.find_child("AptDoor", true, false) as Node3D
	apt_use.interacted.connect(_open_apartment)
	apt_trigger.body_entered.connect(_on_apartment)
	pc_use.interacted.connect(_use_pc)
	_setup_screen()
	_setup_room_light()
	if Game.flags.get("start_in_room", false):  # отладка (F9 / пункт меню): сразу в комнате
		Game.flags.erase("start_in_room")
		_start_in_room()
		return
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
	_set_warm()
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
	await after(2.0)
	Game.set_objective("Включить комп")
	pc_use.enabled = true


## Отладка: Юрчик уже дома, дверь закрыта, можно сразу включать комп.
func _start_in_room() -> void:
	_ended = true
	_set_warm()
	var at := Vector3(-7.9, 8.45, -1.45)
	var yaw := -0.45                              # лицом к столу с компом
	player.global_position = at
	player.velocity = Vector3.ZERO
	player.cam_yaw = yaw
	player.set("_yaw_target", yaw)
	player.set("_cam_pos", at + Vector3.UP * player.eye_height)
	Game.music("", 0.0, 0.5)
	Game.ambience("amb_room", -14.0)
	Game.set_objective("Включить комп")
	pc_use.enabled = true


## Экран монитора выключен, пока Юрчик не включит комп.
func _setup_screen() -> void:
	var mi := $YurchikRoom.find_child("PCScreen_nocol", true, false) as MeshInstance3D
	if mi == null or mi.mesh == null:
		return
	var m := mi.mesh.surface_get_material(0) as StandardMaterial3D
	if m == null:
		return
	_screen = m.duplicate() as StandardMaterial3D
	_screen.emission_energy_multiplier = 0.0
	mi.set_surface_override_material(0, _screen)


func _use_pc(p: Player) -> void:
	p.busy(1.0, "Interact")
	Game.sfx("click", pc_use.global_position)
	await after(0.6)
	var tw := create_tween().set_parallel()
	if _screen:
		tw.tween_property(_screen, "emission_energy_multiplier", 0.9, 1.2)
	tw.tween_property(monitor_light, "light_energy", 0.5, 1.2)
	Game.set_objective("Дома")
	await after(1.5)
	Game.say("Загудел. Старичок ещё живой.")
	await after(3.0)
	if Game.flags.get("sergey", false):         # Сергей шёл следом (старый двор) — ломится в дверь
		Game.sfx("door_bang", apt_use.global_position, 6.0, 0.0)
		player.shake(0.6)
		await after(2.2)
		Game.sfx("door_bang", apt_use.global_position, 6.0, 0.0)
		player.shake(0.8)
	await after(2.5)
	hud.show_ending()


## Свет в комнате: при старте выключен — люстра не светит, плафоны тёмные, клавиша внизу.
func _setup_room_light() -> void:
	_room_energy = room_light.light_energy
	room_light.light_energy = 0.0
	room_light.visible = false
	_switch_key = $YurchikRoom.find_child("LightSwitchKey_nocol", true, false) as Node3D
	var lamp := $YurchikRoom.find_child("Chandelier_nocol", true, false) as MeshInstance3D
	if lamp and lamp.mesh:
		for i in lamp.mesh.get_surface_count():
			var m := lamp.mesh.surface_get_material(i) as StandardMaterial3D
			if m and m.resource_name == "YrLampGlass":
				_bulbs = m.duplicate() as StandardMaterial3D
				_bulb_glow = _bulbs.emission_energy_multiplier
				lamp.set_surface_override_material(i, _bulbs)
	_set_bulbs(0.0)
	_set_key(false, false)
	light_use.prompt = "Включить свет"
	light_use.interacted.connect(_toggle_light)


## Яркость люстры: 0 — выключена, 1 — горит как в инспекторе.
func _set_bulbs(f: float) -> void:
	room_light.light_energy = _room_energy * f
	if _bulbs:
		_bulbs.emission_energy_multiplier = _bulb_glow * f


## Клавиша выключателя: верх утоплен — включено. Ось — вдоль стены (Z в Godot).
func _set_key(on: bool, animate: bool) -> void:
	if _switch_key == null:
		return
	var r := deg_to_rad(-8.0 if on else 8.0)
	if animate:
		create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT).tween_property(_switch_key, "rotation:z", r, 0.09)
	else:
		_switch_key.rotation.z = r


func _toggle_light(p: Player) -> void:
	if _light_busy:
		return
	_light_busy = true
	_light_on = not _light_on
	light_use.prompt = "Выключить свет" if _light_on else "Включить свет"
	p.busy(0.35, "Interact")
	await after(0.12)
	Game.sfx("light_switch", light_use.global_position, -2.0, 0.05)
	_set_key(_light_on, true)
	if _light_on:
		await _light_up()
		_flicker_loop()
	else:
		var f := room_light.light_energy / maxf(_room_energy, 0.001)
		var tw := create_tween()
		tw.tween_method(_set_bulbs, f, 0.0, 0.18).set_ease(Tween.EASE_OUT)   # нить гаснет не мгновенно
		await tw.finished
		room_light.visible = false
	_light_busy = false


## Включение: старая лампочка ловит контакт — пара вспышек с треском, потом нить разгорается.
func _light_up() -> void:
	room_light.visible = true
	await after(0.06)
	if not _flickered or randf() < 0.35:
		Game.sfx("bulb_flicker", room_light.global_position, -6.0, 0.03)
		for step: Vector2 in [Vector2(0.75, 0.05), Vector2(0.0, 0.08), Vector2(0.4, 0.04), Vector2(0.0, 0.07),
				Vector2(0.95, 0.03), Vector2(0.12, 0.09)]:
			_set_bulbs(step.x)
			await after(step.y)
	var tw := create_tween()
	tw.tween_method(_set_bulbs, 0.25, 1.0, 0.35).set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	await tw.finished
	if not _flickered:
		_flickered = true
		await after(0.6)
		Game.say("Опять моргает. Скоро перегорит.")


## Пока свет горит — изредка короткие провалы, как у лампочки на последнем издыхании.
func _flicker_loop() -> void:
	while _light_on:
		await after(randf_range(7.0, 18.0))
		if not _light_on or _light_busy:
			return
		var dips := randi_range(1, 3)
		for k in dips:
			_set_bulbs(randf_range(0.35, 0.7))
			await after(randf_range(0.03, 0.08))
			if not _light_on:
				return
			_set_bulbs(1.0)
			await after(randf_range(0.04, 0.12))


## Дома тепло: изо рта больше не идёт пар (в подъезде — холодно, там он есть).
func _set_warm() -> void:
	var b := player.find_child("BreathParticles", true, false) as GPUParticles3D
	if b:
		b.set("warm", true)
		b.emitting = false
