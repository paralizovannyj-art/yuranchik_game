## Подъезд. Подняться на четвёртый этаж в квартиру 47, пока по лестнице идёт Сергей.
## Финал демо — дома: Юрчик заходит к себе в комнату (модель по фото — tools/blender/build_yurchik_room.py),
## садится за старый комп (PcSeat — scripts/world/pc_seat.gd) и включает его. Если за ним шёл Сергей
## (старый двор) — тот начинает ломиться в дверь. Концовки нет: дальше Юрчик свободно ходит и может снова сесть.
## В комнате свет сначала выключен: выключатель у проёма (LightSwitchUse) щёлкает клавишей, старая лампочка
## моргает, прежде чем разгореться, и потом изредка «проседает».
## В коридоре у входной двери — бра плафоном вверх (над дверью) и выключатель справа от двери (HallSwitchUse).
## Оба выключателя — одна модель assets/models/props/wall_switch.gltf (tools/blender/build_wall_switch.py).
extends Level

@export var sergey_scene: PackedScene
@export var sergey_delay := 10.0        ## через сколько секунд после входа Сергей заходит в подъезд

@onready var apt_use: Interactable = $AptDoorUse
@onready var apt_trigger: Area3D = $AptTrigger
@onready var pc_use: Interactable = $PCUse          ## «Сесть за компьютер» — его слушает PcSeat
@onready var pc_seat: PcSeat = $PcSeat
@onready var monitor_light: SpotLight3D = $Lights/Monitor     ## экран светит только вперёд — на лицо и стол
@onready var light_use: Interactable = $LightSwitchUse
@onready var room_light: OmniLight3D = $Lights/AptRoom
@onready var hall_use: Interactable = $HallSwitchUse
@onready var hall_light: OmniLight3D = $Lights/AptHall

var _door: Node3D
var _sergey: Enemy
var _ended := false
var _light_on := false                    ## люстра в комнате
var _light_busy := false                  ## идёт щелчок/моргание — второй раз не нажать
var _room_energy := 1.3                   ## яркость люстры из инспектора (AptRoom)
var _bulb_glow := 1.0                     ## свечение плафонов при включённом свете
var _bulbs: StandardMaterial3D            ## материал плафонов люстры (копия, чтобы гасить только их)
var _switch_key: Node3D                   ## клавиша выключателя (качается)
var _flickered := false                   ## первое включение — всегда с морганием и репликой
var _hall_key: Node3D                    ## клавиша выключателя в прихожей
var _hall_on := false                     ## бра в коридоре
var _hall_energy := 0.677                 ## яркость бра из инспектора (AptHall)
var _sconce_mats: Array[StandardMaterial3D] = []   ## светящиеся материалы плафона бра (копии)
var _sconce_glow: Array[float] = []
var _pc_was_on := false                  ## комп уже включали (реплика и Сергей — только в первый раз)


func _start() -> void:
	Game.music("mus_drone", -14.0)
	Game.set_objective("Подняться к себе — квартира 47, четвёртый этаж")
	_door = $Stairwell.find_child("AptDoor", true, false) as Node3D
	var inside := get_node_or_null("Apartment/EntryDoorIn") as Node3D   # сторона двери из квартиры — ездит вместе со створкой
	if _door and inside:
		inside.reparent(_door, true)
	apt_use.interacted.connect(_open_apartment)
	apt_trigger.body_entered.connect(_on_apartment)
	pc_seat.powered_on.connect(_on_pc_powered)
	pc_seat.powered_off.connect(_on_pc_off)
	_setup_room_light()
	_setup_hall_light()
	_split_bulb_glass()
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
	var at := Vector3(-7.95, 8.45, 3.88)           # комната повёрнута на 90° (конец коридора, build_apartment.py)
	var yaw := -0.45 + PI / 2                     # лицом к столу с компом
	player.global_position = at
	player.velocity = Vector3.ZERO
	player.cam_yaw = yaw
	player.set("_yaw_target", yaw)
	player.set("_cam_pos", at + Vector3.UP * player.eye_height)
	Game.music("", 0.0, 0.5)
	Game.ambience("amb_room", -14.0)
	Game.set_objective("Включить комп")
	pc_use.enabled = true


## Комп включился (Юрчик сел и нажал кнопку): экран светит на лицо и стол.
func _on_pc_off() -> void:
	var tw := create_tween()
	tw.tween_property(monitor_light, "light_energy", 0.0, 0.6)
	tw.tween_callback(func() -> void: monitor_light.visible = false)


func _on_pc_powered() -> void:
	monitor_light.visible = true                  # пока экран выключен, источник скрыт (не занимает лимит OpenGL)
	create_tween().tween_property(monitor_light, "light_energy", 0.3, 1.2)   # ЭЛТ-экран ≈ 10 кд — втрое слабее лампочки 40 Вт
	if _pc_was_on:                                # включили снова после «Завершения работы» — только свет
		return
	_pc_was_on = true
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
	# Концовки нет: после компа игра продолжается, Юрчик свободно ходит.


## Свет в комнате: при старте выключен — люстра не светит, плафоны тёмные, клавиша внизу.
func _setup_room_light() -> void:
	_room_energy = room_light.light_energy
	room_light.light_energy = 0.0
	room_light.visible = false
	_switch_key = light_use.find_child("WallSwitchKey_nocol", true, false) as Node3D
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


## Стекло мигающей лампочки 1-го этажа (Bulb1) слито в одну поверхность LampGlass с двумя другими лампами подъезда.
## Отделяем его треугольники в свою поверхность со своим материалом и отдаём его мигалке: в жизни при провале
## тускнеет и сама колба, а не только освещённое ею.
func _split_bulb_glass() -> void:
	var bulb := get_node_or_null("Lights/Bulb1") as Light3D
	if bulb:
		bulb.set("glow_materials", GlowSplit.split_near($Stairwell, bulb.global_position, 0.6))


## Бра в коридоре квартиры: при старте не горит (в коридоре темно), плафон тоже тёмный — иначе светящаяся лампа
## висит в темноте и ничего не освещает. Материалы плафона — копии, чтобы не гасить другие лампы.
## Включается выключателем справа от входной двери.
func _setup_hall_light() -> void:
	_hall_energy = hall_light.light_energy
	var sc := $Apartment.find_child("Sconce_nocol", true, false) as MeshInstance3D
	if sc and sc.mesh:
		for i in sc.mesh.get_surface_count():
			var m := sc.mesh.surface_get_material(i) as StandardMaterial3D
			if m and m.emission_enabled:
				var c := m.duplicate() as StandardMaterial3D
				_sconce_mats.append(c)
				_sconce_glow.append(c.emission_energy_multiplier)
				sc.set_surface_override_material(i, c)
	_set_hall(0.0)
	hall_light.visible = false
	_hall_key = hall_use.find_child("WallSwitchKey_nocol", true, false) as Node3D
	if _hall_key:
		_hall_key.rotation.z = deg_to_rad(8.0)
	hall_use.prompt = "Включить свет"
	hall_use.interacted.connect(_toggle_hall)


## Яркость бра: 0 — выключено, 1 — как в инспекторе.
func _set_hall(f: float) -> void:
	hall_light.light_energy = _hall_energy * f
	for i in _sconce_mats.size():
		_sconce_mats[i].emission_energy_multiplier = _sconce_glow[i] * f


func _toggle_hall(p: Player) -> void:
	_hall_on = not _hall_on
	hall_use.prompt = "Выключить свет" if _hall_on else "Включить свет"
	p.busy(0.35, "Interact")
	await after(0.12)
	Game.sfx("light_switch", hall_use.global_position, -2.0, 0.05)
	if _hall_key:
		create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT).tween_property(_hall_key, "rotation:z", deg_to_rad(-8.0 if _hall_on else 8.0), 0.09)
	if _hall_on:
		hall_light.visible = true
	var tw := create_tween()
	tw.tween_method(_set_hall, 0.0 if _hall_on else 1.0, 1.0 if _hall_on else 0.0, 0.15 if _hall_on else 0.18)
	await tw.finished
	if not _hall_on:
		hall_light.visible = false


## Дома тепло: изо рта больше не идёт пар (в подъезде — холодно, там он есть).
## На OpenGL теней нет — лампы подъезда светили бы сквозь стену в тёмную квартиру; дверь закрыта, гасим их.
func _set_warm() -> void:
	if Graphics.opengl:
		for n: String in ["Bulb1", "Bulb2", "Bulb4", "Window1", "Window2", "Window3"]:
			var l := get_node_or_null("Lights/" + n) as Light3D
			if l:
				l.visible = false
	var b := player.find_child("BreathParticles", true, false) as GPUParticles3D
	if b:
		b.set("warm", true)
		b.emitting = false
