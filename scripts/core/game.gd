## Game — общий менеджер игры (автозагрузка, доступен отовсюду как Game).
## Хранит то, что переживает смену уровня: инвентарь, здоровье, флаги сюжета, статистику, чекпойнт.
## Здесь же — база предметов, проигрывание звуков и переходы между уровнями.
extends Node

signal inventory_changed
signal health_changed
signal said(text: String)                       ## короткая реплика/подсказка внизу экрана
signal objective_changed(text: String)
signal noise(pos: Vector3, radius: float)       ## шум, который слышат враги
signal item_picked(id: String)

const MENU_SCENE := "res://scenes/ui/main_menu.tscn"
const FIRST_LEVEL := "res://scenes/levels/district.tscn"   ## новый район «Паскот» (docs/CITY_PLAN.md)
const GRID := Vector2i(8, 5)                    ## размер сетки инвентаря (клеток)
const MAX_HP := 100.0

## База предметов. size — сколько клеток занимает (ширина, высота).
const ITEMS := {
	"hammer": {"name": "Молоток", "size": Vector2i(1, 3), "fixed": true,
		"desc": "Обычный молоток. Другого оружия нет.\nЛКМ — удар. ПКМ + ЛКМ — сильный удар: целься в голову или по ногам."},
	"bottle": {"name": "Бутылка", "size": Vector2i(1, 2), "throw": true,
		"desc": "Бросить (G): оглушает. Звон стекла отвлекает тех, кто тебя ещё не заметил."},
	"brick": {"name": "Кирпич", "size": Vector2i(2, 1), "throw": true,
		"desc": "Бросить (G): сбивает с ног. Можно подобрать снова."},
	"bandage": {"name": "Бинт", "size": Vector2i(1, 1), "heal": 25.0,
		"desc": "Немного восстанавливает здоровье."},
	"shawarma": {"name": "Шаурма", "size": Vector2i(1, 2), "heal": 45.0,
		"desc": "Ещё тёплая. Хорошо восстанавливает здоровье."},
	"medkit": {"name": "Аптечка", "size": Vector2i(2, 2), "heal": 100.0,
		"desc": "Полностью восстанавливает здоровье."},
	"key_garage": {"name": "Ключ от гаража", "size": Vector2i(1, 1), "key": true,
		"desc": "Ключ с красной биркой. От навесного замка на гараже."},
	"key_home": {"name": "Ключи от дома", "size": Vector2i(1, 1), "key": true,
		"desc": "От подъезда и от квартиры 47."},
}

var inventory: Array[Dictionary] = []           ## [{id, pos: Vector2i, rot: bool}]
var hp := MAX_HP
var flags := {}
var stats := {"kills": 0, "time": 0.0, "deaths": 0}
var throw_item := ""                            ## выбранный для броска предмет
var checkpoint := {}
var in_game := false
var god := false                                ## отладка: Юрчик не получает урона

var _streams := {}
var _music: AudioStreamPlayer
var _amb: AudioStreamPlayer
var _music_name := ""
var _amb_name := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_music = AudioStreamPlayer.new()
	_amb = AudioStreamPlayer.new()
	for p: AudioStreamPlayer in [_music, _amb]:
		add_child(p)
		p.finished.connect(p.play)              # петля, даже если в файле она не размечена


func _process(delta: float) -> void:
	if in_game and not get_tree().paused:
		stats["time"] += delta


# ----------------------------------------------------------------------------- инвентарь
func item_name(id: String) -> String:
	return ITEMS[id]["name"] if ITEMS.has(id) else id


func entry_size(e: Dictionary) -> Vector2i:
	var s: Vector2i = ITEMS[e["id"]]["size"]
	return Vector2i(s.y, s.x) if e["rot"] else s


## Свободно ли место под предмет размера size в клетке pos (ignore — запись, которую не учитываем).
func fits(size: Vector2i, pos: Vector2i, ignore: Dictionary = {}) -> bool:
	if pos.x < 0 or pos.y < 0 or pos.x + size.x > GRID.x or pos.y + size.y > GRID.y:
		return false
	var r := Rect2i(pos, size)
	for e: Dictionary in inventory:
		if not ignore.is_empty() and is_same(e, ignore):
			continue
		if r.intersects(Rect2i(e["pos"], entry_size(e))):
			return false
	return true


func add_item(id: String) -> bool:
	var base: Vector2i = ITEMS[id]["size"]
	for rot: bool in [false, true]:
		var size := Vector2i(base.y, base.x) if rot else base
		for y in GRID.y:
			for x in GRID.x:
				if fits(size, Vector2i(x, y)):
					inventory.append({"id": id, "pos": Vector2i(x, y), "rot": rot})
					inventory_changed.emit()
					return true
	return false


func has_item(id: String) -> bool:
	return count(id) > 0


func count(id: String) -> int:
	var n := 0
	for e: Dictionary in inventory:
		if e["id"] == id:
			n += 1
	return n


func remove_item(id: String) -> bool:
	for i in inventory.size():
		if inventory[i]["id"] == id:
			inventory.remove_at(i)
			inventory_changed.emit()
			return true
	return false


func remove_entry(e: Dictionary) -> void:
	for i in inventory.size():
		if is_same(inventory[i], e):
			inventory.remove_at(i)
			inventory_changed.emit()
			return


## Использовать предмет из инвентаря. Возвращает текст-пояснение, если использовать нельзя.
func use_entry(e: Dictionary) -> String:
	var d: Dictionary = ITEMS[e["id"]]
	if d.has("heal"):
		if hp >= MAX_HP:
			return "Здоровье и так в порядке."
		heal(d["heal"])
		sfx("eat" if e["id"] == "shawarma" else "heal")
		remove_entry(e)
		return ""
	if d.has("throw"):
		throw_item = e["id"]
		inventory_changed.emit()
		sfx("ui_select")
		return "Для броска выбрано: %s (G)." % d["name"]
	if d.has("key"):
		return "Ключ сработает сам — подойди к нужной двери."
	return "Это и так в руке."


## Что полетит при броске: выбранный предмет, а если его нет — любой бросаемый.
func current_throwable() -> String:
	if throw_item != "" and has_item(throw_item):
		return throw_item
	for id: String in ["bottle", "brick"]:
		if has_item(id):
			return id
	return ""


func heal(amount: float) -> void:
	hp = minf(hp + amount, MAX_HP)
	health_changed.emit()


# ----------------------------------------------------------------------------- сообщения
func say(text: String) -> void:
	said.emit(text)


func set_objective(text: String) -> void:
	objective_changed.emit(text)


func emit_noise(pos: Vector3, radius: float) -> void:
	noise.emit(pos, radius)


# ----------------------------------------------------------------------------- звук
func stream(sound: String) -> AudioStream:
	if not _streams.has(sound):
		var path := "res://assets/audio/sfx/%s.wav" % sound
		_streams[sound] = load(path) if ResourceLoader.exists(path) else null
	return _streams[sound]


## Проиграть звук. at — точка в мире (звук будет объёмным); без неё — «в голове» игрока.
func sfx(sound: String, at: Variant = null, volume_db := 0.0, pitch_var := 0.07) -> void:
	var s := stream(sound)
	if s == null:
		return
	var pitch := 1.0 + randf_range(-pitch_var, pitch_var)
	if at is Vector3 and get_tree().current_scene:
		var p := AudioStreamPlayer3D.new()
		p.stream = s
		p.volume_db = volume_db
		p.pitch_scale = pitch
		p.unit_size = 5.0
		p.max_distance = 45.0
		p.attenuation_filter_cutoff_hz = 12000.0
		get_tree().current_scene.add_child(p)
		p.global_position = at
		p.finished.connect(p.queue_free)
		p.play()
	else:
		var p2 := AudioStreamPlayer.new()
		p2.stream = s
		p2.volume_db = volume_db
		p2.pitch_scale = pitch
		add_child(p2)
		p2.finished.connect(p2.queue_free)
		p2.play()


## Случайный вариант из серии: sfx_rand("step_snow", 4) → step_snow_1..4.
func sfx_rand(base: String, n: int, at: Variant = null, volume_db := 0.0) -> void:
	sfx("%s_%d" % [base, randi_range(1, n)], at, volume_db)


func music(sound: String, volume_db := -8.0, fade := 1.5) -> void:
	_music_name = _swap(_music, _music_name, sound, volume_db, fade)


func ambience(sound: String, volume_db := -10.0, fade := 1.5) -> void:
	_amb_name = _swap(_amb, _amb_name, sound, volume_db, fade)


func _swap(p: AudioStreamPlayer, current: String, sound: String, volume_db: float, fade: float) -> String:
	if sound == current:
		create_tween().tween_property(p, "volume_db", volume_db, fade)
		return current
	var tw := create_tween()
	if p.playing:
		tw.tween_property(p, "volume_db", -60.0, fade * 0.5)
	tw.tween_callback(func() -> void:
		p.stop()
		p.stream = stream(sound) if sound != "" else null
		if p.stream:
			p.volume_db = -40.0
			p.play())
	if sound != "":
		tw.tween_property(p, "volume_db", volume_db, fade)
	return sound


# ----------------------------------------------------------------------------- эффекты
## Стоп-кадр при попадании — удар ощущается тяжелее.
func hitstop(duration := 0.06) -> void:
	Engine.time_scale = 0.05
	await get_tree().create_timer(duration, true, false, true).timeout
	Engine.time_scale = 1.0


## Облачко «крови»/осколков в точке попадания.
func fx_burst(at: Vector3, color := Color(0.35, 0.02, 0.02), amount := 10, speed := 2.5) -> void:
	var scene := get_tree().current_scene
	if scene == null:
		return
	var p := CPUParticles3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(0.05, 0.05)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_VERTEX
	quad.material = mat
	p.mesh = quad
	p.amount = amount
	p.lifetime = 0.5
	p.one_shot = true
	p.explosiveness = 1.0
	p.direction = Vector3.UP
	p.spread = 70.0
	p.initial_velocity_min = speed * 0.4
	p.initial_velocity_max = speed
	p.gravity = Vector3(0, -9, 0)
	p.scale_amount_min = 0.5
	p.scale_amount_max = 1.4
	scene.add_child(p)
	p.global_position = at
	p.emitting = true
	get_tree().create_timer(1.2).timeout.connect(p.queue_free)


# ----------------------------------------------------------------------------- ход игры
func new_game() -> void:
	inventory.clear()
	flags.clear()
	hp = MAX_HP
	throw_item = ""
	stats = {"kills": 0, "time": 0.0, "deaths": 0}
	checkpoint = {}
	add_item("hammer")
	goto_level(FIRST_LEVEL)


func goto_level(path: String) -> void:
	Engine.time_scale = 1.0
	get_tree().paused = false
	in_game = true
	get_tree().change_scene_to_file(path)


## Запомнить состояние на входе в уровень: после смерти начнём отсюда.
func save_checkpoint(level_path: String) -> void:
	checkpoint = {"level": level_path, "inventory": inventory.duplicate(true), "hp": maxf(hp, 40.0),
		"flags": flags.duplicate(true), "throw": throw_item}


func restart_from_checkpoint() -> void:
	if checkpoint.is_empty():
		new_game()
		return
	inventory.assign(checkpoint["inventory"].duplicate(true))
	flags = checkpoint["flags"].duplicate(true)
	hp = checkpoint["hp"]
	throw_item = checkpoint["throw"]
	inventory_changed.emit()
	goto_level(checkpoint["level"])


func to_menu() -> void:
	Engine.time_scale = 1.0
	get_tree().paused = false
	in_game = false
	music("")
	ambience("")
	get_tree().change_scene_to_file(MENU_SCENE)
