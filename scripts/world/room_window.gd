## Пластиковое окно в комнате Юрчика: правая створка открывается внутрь по кнопке E / A.
## Как в жизни: сначала ручка поворачивается из «вниз» в «вбок» (щелчок, лязг цапф), створка с «чпоком» отлипает
## от резинки и уходит в комнату; в проём тянет улицей — ветер, метель шипит по откосам, гул района (amb_window),
## снег залетает внутрь и тает на лету, а рядом с открытым окном у Юрчика снова идёт пар изо рта.
## Закрыть — створка глухо садится на уплотнитель, ручка вниз, улица стихает.
## Модель: assets/models/room_window.gltf (tools/blender/build_room_window.py) — в ней створка RoomWindowSash_nocol
## (пивот на оси петель) и ручка RoomWindowHandle_nocol (пивот на шейке). Звуки — tools/audio/synth_window.py.
## Узел стоит у самой створки: оттуда звучит окно и по нему меряется, близко ли Юрчик.
## Открывает Юрчик руками (клип WindowOpen, tools/blender/build_window_open.py): подходит к месту у окна
## (маркер WindowSpot), тянется через подоконник к ручке, поворачивает её, ведёт створку за ручку до упора
## и отпускает; взгляд — за рукой, потом на улицу. Закрывает — тот же клип задом наперёд: берётся за ручку
## открытой створки, толкает её на место, ручку вниз. Створка, ручка и взгляд идут по дорожкам из
## assets/animations/window/window_open.json — ровно за кулаком. Нет клипа — по-старому, твинами.
class_name RoomWindow
extends Interactable

@export var window_path: NodePath                ## экземпляр room_window.gltf
@export var snow_path: NodePath                  ## GPUParticles3D: снег, залетающий в комнату
@export var open_angle := 78.0                   ## на сколько градусов распахивается створка
@export var handle_angle := 90.0                 ## поворот ручки: вниз → вбок
@export var open_time := 1.6                     ## сколько секунд створка уходит в комнату
@export var close_time := 0.9
@export var street_db := -3.0                    ## громкость улицы в открытое окно
@export var cold_radius := 3.2                   ## м — ближе к открытому окну пар изо рта виден
@export var open_prompt := "Открыть окно"
@export var close_prompt := "Закрыть окно"
@export_multiline var first_open_line := "Ух, холодрыга. Зато хоть проветрю."
@export var spot_path: NodePath = ^"WindowSpot"  ## Marker3D: где стоит Юрчик, пока открывает (смотрит вдоль −Z, на окно)
@export_file("*.json") var anim_path := "res://assets/animations/window/window_open.json"   ## створка, ручка, взгляд
@export var open_rate := 1.0                     ## скорость клипа, когда открывает
@export var close_rate := 1.25                   ## и когда закрывает (клип задом наперёд)
@export var walk_speed := 1.3                    ## м/с — подходит к окну
@export var turn_speed := 110.0                  ## °/с — разворачивается к окну

const SASH := "RoomWindowSash_nocol"
const HANDLE := "RoomWindowHandle_nocol"
## створка в своих координатах (пивот на петлях): толщина 7 см, высота 1.34 м, ширина 0.63 м
const SASH_BOX_POS := Vector3(-0.03, 0.72, 0.317)
const SASH_BOX_SIZE := Vector3(0.07, 1.34, 0.63)

var is_open := false
var _sash: Node3D
var _handle: Node3D
var _body: AnimatableBody3D
var _busy := false
var _opened_once := false
var _street: AudioStreamPlayer3D
var _snow: GPUParticles3D
var _breath: Node
var _breath_pauses: PackedFloat32Array
var _breath_warm := true
var _cold := false
var _spot: Node3D
var _fps := 30.0
var _marks := {}                  ## кадры клипа: grab, turn0, turn1, pop, open, release, free, end
var _sash_keys: Array = []        ## покадрово угол створки, °
var _handle_keys: Array = []      ## покадрово угол ручки, °
var _look_keys: Array = []        ## покадрово точка взгляда (пространство WindowSpot)
const SETTLE_TIME := 0.35


func _ready() -> void:
	super()
	var win := get_node_or_null(window_path)
	if win:
		_sash = win.find_child(SASH, true, false) as Node3D
		_handle = win.find_child(HANDLE, true, false) as Node3D
	if aim_meshes.is_empty():
		aim_meshes = PackedStringArray([SASH, HANDLE])
	_snow = get_node_or_null(snow_path) as GPUParticles3D
	if _snow:
		_snow.emitting = false
	_make_body()
	_street = AudioStreamPlayer3D.new()
	_street.stream = Game.stream("amb_window")
	_street.volume_db = -60.0
	_street.unit_size = 3.0
	_street.max_distance = 30.0
	_street.attenuation_filter_cutoff_hz = 9000.0
	_street.finished.connect(_street.play)          # петля, даже если в файле она не размечена
	add_child(_street)
	prompt = open_prompt
	interacted.connect(_on_interacted)
	_spot = get_node_or_null(spot_path) as Node3D
	var res := load(anim_path) as JSON if ResourceLoader.exists(anim_path) else null
	if res and res.data is Dictionary:
		var d: Dictionary = res.data
		_fps = float(d.get("fps", 30))
		_marks = d.get("marks", {})
		_sash_keys = d.get("sash", [])
		_handle_keys = d.get("handle", [])
		_look_keys = d.get("look", [])


## Коллизия створки: тело не может просто ехать вместе с родителем (физика не заметит поворот),
## поэтому оно живёт отдельно и каждый физический кадр встаёт туда, где створка (как у Door).
func _make_body() -> void:
	if _sash == null:
		return
	_body = AnimatableBody3D.new()
	_body.sync_to_physics = false
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = SASH_BOX_SIZE
	cs.shape = box
	cs.position = SASH_BOX_POS
	_body.add_child(cs)
	add_child(_body)
	_body.global_transform = _sash.global_transform


func _physics_process(_delta: float) -> void:
	if _body and _sash and not _body.global_transform.is_equal_approx(_sash.global_transform):
		_body.global_transform = _sash.global_transform
	_update_cold()


func _on_interacted(player: Player) -> void:
	if _busy or _sash == null:
		return
	if player and _spot and not _sash_keys.is_empty() and float(player.model.call("window_length")) > 0.0:
		_by_hand(player, not is_open)
	elif is_open:
		_close(player)
	else:
		_open(player)


# ----------------------------------------------------------------------------- руками (клип WindowOpen)
## Открыть (open) или закрыть окно руками: подойти к месту у окна, клип вперёд или задом наперёд.
func _by_hand(p: Player, open: bool) -> void:
	_busy = true
	p.set_seated(true, true)                 # тело и взгляд ведёт клип; фонарик остаётся как был
	var length: float = p.model.call("window_length")
	var t0 := 0.0 if open else length
	await _walk_to(p, _look_at_t(t0))
	p.global_position = _spot.global_position
	p.seat_yaw = _spot.global_basis.get_euler().y
	await _play(p, t0, length - t0 if open else -length, open_rate if open else close_rate)
	p.model.set("window_time", -1.0)
	p.set_seated(false)
	_busy = false
	if open and not _opened_once:
		_opened_once = true
		Game.say(first_open_line)


## Точка взгляда на секунде t клипа (мир).
func _look_at_t(t: float) -> Vector3:
	var v: Variant = _sample(_look_keys, t)
	if v is Array and (v as Array).size() >= 3:
		return _spot.global_transform * Vector3(v[0], v[1], v[2])
	return global_position


## Значение покадровой дорожки на секунде t (между кадрами — линейно): число или массив чисел.
func _sample(keys: Array, t: float) -> Variant:
	if keys.is_empty():
		return 0.0
	var fr := clampf(t * _fps, 0.0, keys.size() - 1.0)
	var i := clampi(int(fr), 0, maxi(keys.size() - 2, 0))
	var a: Variant = keys[i]
	var b: Variant = keys[mini(i + 1, keys.size() - 1)]
	var u := fr - i
	if a is Array:
		var out := []
		for c in (a as Array).size():
			out.append(lerpf(a[c], b[c], u))
		return out
	return lerpf(float(a), float(b), u)


## Подойти шагом на место у окна и повернуться к нему; взгляд к концу шага — туда, куда смотрит первый кадр клипа.
func _walk_to(p: Player, look_pt: Vector3) -> void:
	var target := _spot.global_position
	var yaw := _spot.global_basis.get_euler().y
	var from := p.global_position
	var yaw0 := p.seat_yaw
	var dist := Vector2(target.x - from.x, target.z - from.z).length()
	var cam0 := Vector2(p.cam_yaw, p.cam_pitch)
	var aim_end := _angles_to(p, look_pt)
	var turn := maxf(absf(angle_difference(yaw0, yaw)), absf(angle_difference(cam0.x, aim_end.x)))
	var dur := clampf(maxf(dist / walk_speed, turn / deg_to_rad(turn_speed)), 0.4, 3.0)
	var tw := create_tween().set_process_mode(Tween.TWEEN_PROCESS_PHYSICS)
	tw.tween_method(func(u: float) -> void:
		var e := _smoother(u)
		p.global_position = from.lerp(target, e)
		p.seat_yaw = lerp_angle(yaw0, yaw, _smoother(minf(u * 1.15, 1.0)))
		p.seat_walk = dist / dur * 30.0 * u * u * (1.0 - u) * (1.0 - u)   # шаг по скорости на кривой — ноги не скользят
		var aim := _angles_to(p, look_pt)
		var k := _smoother(minf(u * 1.15, 1.0))
		p.look_at_angles(lerp_angle(cam0.x, aim.x, k), lerpf(cam0.y, aim.y, k)), 0.0, 1.0, dur)
	await tw.finished
	p.seat_walk = 0.0
	await get_tree().create_timer(0.12).timeout     # ноги дошагали в стойку — дальше клип с той же стойки


## Проиграть клип от t0 на dt секунд (dt < 0 — назад, закрывает): поза, створка, ручка, взгляд, звуки.
func _play(p: Player, t0: float, dt: float, rate: float) -> void:
	var t := t0
	var t1 := t0 + dt
	var dir := signf(dt)
	var from := Vector2(p.cam_yaw, p.cam_pitch)
	var settle := 0.0
	_apply(p, t, from, 0.0)
	while (t1 - t) * dir > 0.0:
		await get_tree().physics_frame
		var step := get_physics_process_delta_time()
		settle = minf(settle + step / SETTLE_TIME, 1.0)
		var nt := t + step * rate * dir
		nt = minf(nt, t1) if dir > 0.0 else maxf(nt, t1)
		_cues(t, nt, dir)
		t = nt
		_apply(p, t, from, settle)


## Кадр клипа: поза Юрчика, створка, ручка и взгляд (в начале плавно от того, куда смотрел).
func _apply(p: Player, t: float, from: Vector2, settle: float) -> void:
	p.model.set("window_time", t)
	_sash.rotation.y = deg_to_rad(float(_sample(_sash_keys, t)))
	_handle.rotation.x = deg_to_rad(float(_sample(_handle_keys, t)))
	var a := _angles_to(p, _look_at_t(t))
	if settle < 1.0:
		var e := _smoother(settle)
		a = Vector2(lerp_angle(from.x, a.x, e), lerpf(from.y, a.y, e))
	p.look_at_angles(a.x, a.y)


## Прошла ли метка клипа key между секундами t и nt (в сторону dir).
func _crossed(key: String, t: float, nt: float, dir: float) -> bool:
	var m := float(_marks.get(key, -1)) / _fps
	return m >= 0.0 and (m - t) * dir > 0.0 and (m - nt) * dir <= 0.0


## Звуки и состояние на метках клипа. Открывает: ручка пошла — лязг, створка отлипла — «чпок», улица, снег.
## Закрывает (назад): створка села на уплотнитель — глухой «пух», улица стихает; ручка пошла вниз — лязг.
func _cues(t: float, nt: float, dir: float) -> void:
	if dir > 0.0:
		if _crossed("turn0", t, nt, dir):
			Game.sfx("window_handle", global_position, -2.0, 0.04)
		if _crossed("pop", t, nt, dir):
			is_open = true
			prompt = close_prompt
			Game.sfx("window_open", global_position, 0.0, 0.03)
			_street_fade(street_db, 2.2)
			if _snow:
				_snow.emitting = true
	else:
		if _crossed("pop", t, nt, dir):
			is_open = false
			prompt = open_prompt
			Game.sfx("window_close", global_position, 0.0, 0.03)
			_street_fade(-60.0, 0.35)
			if _snow:
				_snow.emitting = false
		if _crossed("turn1", t, nt, dir):
			Game.sfx("window_handle", global_position, -4.0, 0.04)


## Углы взгляда (поворот, наклон) из глаз игрока на точку в мире.
static func _angles_to(p: Player, at: Vector3) -> Vector2:
	var d := at - p.eye_point()
	return Vector2(atan2(-d.x, -d.z), atan2(d.y, Vector2(d.x, d.z).length()))


static func _smoother(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


# ----------------------------------------------------------------------------- без клипа (твинами)


func _open(player: Player) -> void:
	_busy = true
	is_open = true
	prompt = close_prompt
	if player:
		player.busy(0.6, "Interact")
	# ручка: вниз → вбок, лязг цапф
	Game.sfx("window_handle", global_position, -2.0, 0.04)
	var tw := create_tween()
	tw.tween_property(_handle, "rotation:x", deg_to_rad(handle_angle), 0.22).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	tw.tween_interval(0.12)
	# створка прилипла к резинке: короткий рывок — «чпок» — и тут же уходит в комнату, в конце чуть дышит на петлях
	tw.tween_callback(func() -> void:
		Game.sfx("window_open", global_position, 0.0, 0.03)
		_street_fade(street_db, 2.2)
		if _snow:
			_snow.emitting = true)
	tw.tween_property(_sash, "rotation:y", deg_to_rad(4.0), 0.07).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(_sash, "rotation:y", deg_to_rad(open_angle + 2.5), open_time).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	tw.tween_property(_sash, "rotation:y", deg_to_rad(open_angle), 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_callback(func() -> void: _busy = false)
	if not _opened_once:
		_opened_once = true
		get_tree().create_timer(1.8).timeout.connect(func() -> void: Game.say(first_open_line))


func _close(player: Player) -> void:
	_busy = true
	is_open = false
	prompt = open_prompt
	if player:
		player.busy(0.5, "Interact")
	var tw := create_tween()
	tw.tween_property(_sash, "rotation:y", 0.0, close_time).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	# створка села на уплотнитель: глухой «пух», улица отрезана; в звуке через 0.38 с — ручка вниз
	tw.tween_callback(func() -> void:
		Game.sfx("window_close", global_position, 0.0, 0.03)
		_street_fade(-60.0, 0.35)
		if _snow:
			_snow.emitting = false)
	tw.tween_interval(0.3)
	tw.tween_property(_handle, "rotation:x", 0.0, 0.2).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	tw.tween_callback(func() -> void: _busy = false)


func _street_fade(db: float, time: float) -> void:
	if db > -60.0 and not _street.playing:
		_street.play()
	var tw := create_tween()
	tw.tween_property(_street, "volume_db", db, time)
	if db <= -60.0:
		tw.tween_callback(_street.stop)


## У открытого окна холодно: пар изо рта снова виден и идёт чаще. Отошёл или закрыл — снова тепло, как было.
func _update_cold() -> void:
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if p == null:
		return
	var cold := is_open and p.global_position.distance_to(global_position) < cold_radius
	if cold == _cold:
		return
	_cold = cold
	if _breath == null:
		_breath = p.find_child("BreathParticles", true, false)
		if _breath == null:
			return
		_breath_pauses = _breath.get("pause_choices")
	if cold:
		_breath_warm = _breath.get("warm")
		_breath.set("warm", false)
		_breath.set("pause_choices", PackedFloat32Array([3.0, 4.5, 6.0]))
		_exhale_soon()
	else:
		_breath.set("warm", _breath_warm)
		_breath.set("pause_choices", _breath_pauses)


## Первый выдох на холоде — почти сразу, не дожидаясь, пока у пара кончится «тёплая» пауза.
func _exhale_soon() -> void:
	await get_tree().create_timer(2.2).timeout
	var b := _breath as GPUParticles3D
	if not _cold or b == null or b.emitting:
		return
	b.call("_set_brightness")
	b.restart()
	b.emitting = true
	Game.sfx_rand("player_breath", 3, null, float(b.get("sound_db")))
	await get_tree().create_timer(float(b.get("exhale_duration"))).timeout
	if is_instance_valid(b):
		b.emitting = false
