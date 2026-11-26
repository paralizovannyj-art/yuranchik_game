## Пластиковое окно в комнате Юрчика: правая створка открывается внутрь по кнопке E / A.
## Как в жизни: сначала ручка поворачивается из «вниз» в «вбок» (щелчок, лязг цапф), створка с «чпоком» отлипает
## от резинки и уходит в комнату; в проём тянет улицей — ветер, метель шипит по откосам, гул района (amb_window),
## снег залетает внутрь и тает на лету, а рядом с открытым окном у Юрчика снова идёт пар изо рта.
## Закрыть — створка глухо садится на уплотнитель, ручка вниз, улица стихает.
## Модель: assets/models/room_window.gltf (tools/blender/build_room_window.py) — в ней створка RoomWindowSash_nocol
## (пивот на оси петель) и ручка RoomWindowHandle_nocol (пивот на шейке). Звуки — tools/audio/synth_window.py.
## Узел стоит у самой створки: оттуда звучит окно и по нему меряется, близко ли Юрчик.
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
	if is_open:
		_close(player)
	else:
		_open(player)


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
