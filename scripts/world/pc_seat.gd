## Комп Юрчика: сесть в игровое кресло и работать за монитором.
## Наводишься на кресло, стол, монитор или системник — прицел расширяется, E — Юрчик подходит к креслу
## и садится, как в тесной комнате (клип ChairSit, tools/blender/build_chair_sit.py): берётся за спинку,
## откатывает кресло, разворачивает его к себе, садится боком, поворачивается к столу и подтягивается ногами.
## Кресло едет по пути из assets/animations/sit/chair_sit.json. Ещё раз E, пока садится, — быстрее.
## Сев, Юрчик сам решает, что дальше (SEATED_LOOK): мышь крутит голову — влево-вправо до look_yaw_limit от
## монитора, тело и кресло на месте; прицел и E работают, как стоя, но только на то, до чего дотянется рука.
##   • системник (PowerUse, пока комп выключен) — наклоняется и жмёт кнопку питания (клип PowerReach),
##     потом взгляд возвращается туда, куда смотрел;
##   • монитор (MonitorUse, пока комп включён) — взгляд уезжает к монитору (MONITOR): экран почти
##     во весь кадр, но это всё ещё монитор в комнате — рамка, блик, шум.
## В MONITOR мышь двигает курсор внутри экрана, клики и клавиши уходят в «компьютер» (SubViewport с рабочим
## столом). Руки при этом живые: правая с мышкой ездит по коврику за курсором (и мышка на столе вместе с ней),
## указательный кликает, пальцы левой жмут клавиши.
## Esc (или B на геймпаде) — шаг назад: из монитора — отъехать и снова смотреть вокруг, из осмотра — встать
## (клип задом наперёд до момента, где он встал). Меню паузы в кресле не открывается. Кресло остаётся
## отодвинутым и повёрнутым, и в следующий раз Юрчик садится сразу, без откатывания.
class_name PcSeat
extends Node3D

signal powered_on          ## комп включился (Юрчик нажал кнопку на системнике)
signal sat_down            ## сел в кресло (конец клипа посадки) — смотрит вокруг, не в монитор
signal monitor_entered     ## взгляд доехал до монитора — мышь и клавиши у компа
signal monitor_exited      ## отъехал от монитора — снова смотрит вокруг
signal stood_up            ## встал с кресла
signal powered_off         ## Windows завершила работу, экран погас

@export var use: Interactable                        ## «Сесть за компьютер» (кресло, стол, монитор, системник)
## сидя: «Включить компьютер», пока комп выключен. Системник целиком под столешницей — из кресла его почти
## не видно, поэтому прицел у узла — брусок aim_size по передней кромке стола прямо над ним.
@export var power_use: Interactable
@export var monitor_use: Interactable                ## сидя: «Работать» (монитор), пока комп включён
@export var chair: Node3D                            ## игровое кресло — едет вместе с клипом посадки
@export_file("*.json") var chair_path := "res://assets/animations/sit/chair_sit.json"   ## путь кресла и взгляд
@export var screen_mesh := "PCScreen_nocol"          ## плоскость экрана в модели монитора (UV 0..1 на весь экран)
@export var speaker_nodes: PackedStringArray = ["SpeakerLeft", "SpeakerRight"]   ## колонки на столе (левая, правая)
@export var glow_meshes: PackedStringArray = ["PcTowerGlow_nocol", "MonitorLed_nocol"]   ## светятся, только пока комп включён: окно и кнопка системника, диод монитора
@export var mouse_mesh := "Mouse_nocol"              ## мышка на столе — ездит вместе с рукой
@export var mouse_travel := Vector2(0.045, 0.03)      ## м — сколько ездит мышка по коврику от середины (= MOUSE_TRAVEL в seat_poses.py)
@export var desktop_scene: PackedScene               ## что показывает комп (рабочий стол)
@export var screen_size := Vector2i(1280, 1024)      ## разрешение экрана компа (матрица 5:4, 17")
@export var ui_size := Vector2(1024, 820)            ## Windows на 125 %: в этих «логических» пикселях живёт рабочий стол
@export var view_fov := 34.0                          ## угол обзора, когда смотришь в монитор (экран почти во весь кадр)
@export var cursor_speed := 1.0                       ## скорость курсора относительно мыши
@export_group("Время, с")
@export var walk_speed := 1.3                         ## м/с — подходит к креслу
@export var turn_speed := 110.0                       ## °/с — разворачивается тело и взгляд (в среднем; пик ~2×)
@export var clip_rate := 1.0                          ## скорость клипа посадки
@export var hurry_rate := 2.2                         ## ещё раз «использовать», пока садится, — вот так быстрее
@export var zoom_in := 1.0                            ## взгляд к монитору
@export var zoom_out := 0.7
@export_group("Осмотр в кресле")
@export var look_yaw_limit := 100.0                   ## ° — насколько можно повернуть голову влево и вправо от монитора
@export var look_pitch_min := -70.0                   ## ° — вниз (системник под столом)
@export var look_pitch_max := 50.0                    ## ° — вверх
@export var look_reach := 1.1                         ## м — до чего дотягивается рука со стула (по лучу взгляда от глаз)

enum State { IDLE, WALKING, SITTING_DOWN, SEATED_LOOK, POWERING, ZOOMING_IN, MONITOR, ZOOMING_OUT, STANDING_UP }

@onready var sit_spot: Marker3D = $SitSpot            ## «место у компа»: в нём стоит узел игрока, пока идёт клип (смотрит вдоль −Z)
@onready var screen_view: Marker3D = $ScreenView      ## откуда камера смотрит в монитор

var powered := false
var state := State.IDLE
var seated := false            ## в кресле (в том числе пока садится и встаёт)
var active := false            ## смотрит в монитор, мышь — курсор компа (State.MONITOR)
var viewport: SubViewport
var cursor := Vector2.ZERO     ## курсор в логических пикселях рабочего стола (ui_size)
var _player: Player
var _mat: ShaderMaterial
var _desktop: Control
var _pointer: Control
var _speaker_pos := Vector3.ZERO   ## откуда звучит Windows (колонки у монитора)
var _keys_pos := Vector3.ZERO      ## клавиатура и мышь
var speakers: PcSpeakers           ## весь звук компа — из колонок на столе
var _glow: Array[Node3D] = []      ## подсветка системника и диод монитора
var chair_out := false             ## кресло откачено от стола (Юрчик вставал) — садится без откатывания
var _fps := 30.0
var _marks := {}                   ## кадры клипа: grab, pull, spin, release, sit, land, seated, swivel, pull0, pull1, end
var _chair_keys: Array = []        ## покадрово [x, y, z, поворот] кресла в пространстве SitSpot
var _look_keys: Array = []         ## покадрово точка, куда смотрит камера (пространство SitSpot)
var _start := [0.0, 0.0, 0.0, 0.0] ## где встаёт за креслом в начале клипа: x, y, z, поворот
var _stand := [0.0, 0.0, 0.0, 0.0] ## где стоит перед креслом на кадре sit (встал / садится в откаченное)
var _power_look: Array = []        ## PowerReach: покадрово точка, куда смотрит камера (пространство SitSpot)
var _power_press := 0.0            ## PowerReach: секунда, когда палец на кнопке
var _mouse: Node3D                 ## мышка на столе
var _mouse_home := Vector3.ZERO    ## где она лежит (глобально)
var _keys_held := {}               ## физический код клавиши → палец левой (индекс в YurchikAnim.DESK_TAPS)
var _hurry := false
var _settle := 1.0                 ## 0→1 в начале клипа: взгляд переходит от того, куда смотрел, к взгляду клипа
var _settle_from := Vector2.ZERO
var _look_center := Vector2.ZERO   ## углы взгляда на монитор с конца клипа посадки — середина осмотра
const SETTLE_TIME := 0.35
## куда отходит, когда встал: за откаченное кресло, лицом в комнату (x, y, z, поворот; пространство SitSpot).
## Между креслом, столом и кроватью капсуле игрока места нет — там его выталкивало бы на кровать.
const EXIT_SPOT := [-0.2, 0.0, 1.4, PI]
## звуки клипа: метка (marks в chair_sit.json), сдвиг в кадрах, звук, громкость,
## в какую сторону клипа (1 — садится, −1 — встаёт, 0 — оба)
const CUES := [
	["pull", 0, "chair_roll", -7.0, 1], ["spin", 0, "chair_spin", -6.0, 1], ["land", -2, "chair_sit", -4.0, 1],
	["seated", 2, "chair_spin", -10.0, 1], ["pull0", 0, "chair_roll", -8.0, 1],
	["pull1", -1, "chair_roll", -8.0, -1], ["swivel", -2, "chair_spin", -10.0, -1], ["land", -14, "chair_sit", -7.0, -1],
]


func _ready() -> void:
	_build_screen()
	_load_path()
	_place_chair(0.0)
	if use:
		use.interacted.connect(sit)
	if power_use:
		power_use.interacted.connect(_on_power_use)
	if monitor_use:
		monitor_use.interacted.connect(_on_monitor_use)
	_update_uses()


func _load_path() -> void:
	var res := load(chair_path) as JSON if ResourceLoader.exists(chair_path) else null
	if res == null or not res.data is Dictionary:
		push_warning("pc_seat: нет пути кресла %s" % chair_path)
		return
	var d: Dictionary = res.data
	_fps = float(d.get("fps", 30))
	_marks = d.get("marks", {})
	_chair_keys = d.get("chair", [])
	_look_keys = d.get("look", [])
	_start = d.get("start", _start)
	_stand = d.get("stand", _stand)
	var pw: Dictionary = d.get("power", {})
	_power_look = pw.get("look", [])
	_power_press = float(pw.get("marks", {}).get("press", 0)) / _fps


## Секунда клипа, на которой стоит метка (grab, sit, seated…).
func _mark(key: String) -> float:
	return float(_marks.get(key, 0)) / _fps


## Значение покадровой дорожки на секунде t (между кадрами — линейно, поворот — по короткой дуге).
func _sample(keys: Array, t: float) -> Array:
	if keys.is_empty():
		return [0.0, 0.0, 0.0, 0.0]
	var fr := clampf(t * _fps, 0.0, keys.size() - 1.0)
	var i := clampi(int(fr), 0, maxi(keys.size() - 2, 0))
	var a: Array = keys[i]
	var b: Array = keys[mini(i + 1, keys.size() - 1)]
	var u := fr - i
	var out := []
	for c in a.size():
		out.append(lerp_angle(a[c], b[c], u) if c == 3 else lerpf(a[c], b[c], u))
	return out


static func _v(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


## Кресло — туда, где оно на секунде t клипа.
func _place_chair(t: float) -> void:
	if chair == null or _chair_keys.is_empty():
		return
	var c := _sample(_chair_keys, t)
	chair.global_transform = sit_spot.global_transform * Transform3D(Basis(Vector3.UP, c[3]), _v(c))


## Повернуть взгляд игрока на точку в мире.
func _look_at(p: Player, at: Vector3) -> void:
	var a := _angles_to(p, at)
	p.look_at_angles(a.x, a.y)


## Углы взгляда (поворот, наклон) из глаз игрока на точку в мире.
static func _angles_to(p: Player, at: Vector3) -> Vector2:
	var d := at - p.eye_point()
	return Vector2(atan2(-d.x, -d.z), atan2(d.y, Vector2(d.x, d.z).length()))


## Твин в такте физики: камера игрока считается там же, поэтому при просадке кадров шаги не рвутся.
func _tween() -> Tween:
	return create_tween().set_process_mode(Tween.TWEEN_PROCESS_PHYSICS)


## Плавный шаг 0→1: скорость и ускорение на концах — ноль (без толчка на старте и в конце).
static func _smoother(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


## Плавно перевести взгляд на углы (рад) за dur секунд. Сглаживание камеры у игрока почти мгновенное,
## поэтому резкая смена цели — это рывок; ведём цель сами.
func _ease_look(p: Player, yaw: float, pitch: float, dur: float) -> void:
	var y0 := p.cam_yaw
	var p0 := p.cam_pitch
	var tw := _tween()
	tw.tween_method(func(u: float) -> void:
		var e := _smoother(u)
		p.look_at_angles(lerp_angle(y0, yaw, e), lerpf(p0, pitch, e)), 0.0, 1.0, dur)
	await tw.finished


## Кадр клипа: поза (seat_time), кресло и взгляд камеры.
func _apply(t: float) -> void:
	_player.model.set("seat_time", t)
	_place_chair(t)
	if not _look_keys.is_empty():
		var a := _angles_to(_player, sit_spot.global_transform * _v(_sample(_look_keys, t)))
		if _settle < 1.0:
			var e := _smoother(_settle)
			a = Vector2(lerp_angle(_settle_from.x, a.x, e), lerpf(_settle_from.y, a.y, e))
		_player.look_at_angles(a.x, a.y)


## Проиграть клип посадки от t0 до t1 (t1 < t0 — назад, встаёт). Звуки — на кадрах из CUES.
## Идёт в такте физики, как и камера с телом игрока.
func _play(t0: float, t1: float) -> void:
	var t := t0
	var dir := signf(t1 - t0)
	_settle = 0.0
	_settle_from = Vector2(_player.cam_yaw, _player.cam_pitch)
	_apply(t)
	while (t1 - t) * dir > 0.0:
		await get_tree().physics_frame
		var dt := get_physics_process_delta_time()
		_settle = minf(_settle + dt / SETTLE_TIME, 1.0)
		var nt := t + dt * (hurry_rate if _hurry else clip_rate) * dir
		nt = minf(nt, t1) if dir > 0.0 else maxf(nt, t1)
		for cue: Array in CUES:
			var ct := _mark(cue[0]) + float(cue[1]) / _fps
			if (cue[4] == 0 or cue[4] == int(dir)) and (ct - t) * dir > 0.0 and (ct - nt) * dir <= 0.0:
				var at := chair.global_position + Vector3.UP * 0.3 if chair else global_position
				Game.sfx(cue[2], at, cue[3], 0.08)
		t = nt
		_apply(t)


## Подойти шагом в точку (пространство SitSpot) и повернуться: ноги шагают, взгляд плавно переходит
## на look_pt (точка в пространстве SitSpot — туда, куда смотрит первый кадр клипа) или вперёд, куда идёт.
func _walk_to(p: Player, spot_pt: Array, look_pt: Variant = null) -> void:
	var spot := sit_spot.global_transform
	var target := spot * _v(spot_pt)
	target.y = spot.origin.y
	var yaw := spot.basis.get_euler().y + float(spot_pt[3])
	var from := p.global_position
	var yaw0 := p.seat_yaw
	var dist := Vector2(target.x - from.x, target.z - from.z).length()
	# сколько идти — и по расстоянию, и по развороту: на 180° на месте за полсекунды взгляд крутится рывком
	var cam0 := Vector2(p.cam_yaw, p.cam_pitch)
	var aim_end := _angles_to(p, spot * _v(look_pt)) if look_pt != null else Vector2(yaw, -0.1)
	var turn := maxf(absf(angle_difference(yaw0, yaw)), absf(angle_difference(cam0.x, aim_end.x)))
	var dur := clampf(maxf(dist / walk_speed, turn / deg_to_rad(turn_speed)), 0.5, 3.0)
	var tw := _tween()
	tw.tween_method(func(u: float) -> void:
		var e := _smoother(u)
		p.global_position = from.lerp(target, e)
		p.seat_yaw = lerp_angle(yaw0, yaw, _smoother(minf(u * 1.15, 1.0)))
		# скорость шага — по скорости на кривой (разгон и остановка), чтобы ноги не скользили
		p.seat_walk = dist / dur * 30.0 * u * u * (1.0 - u) * (1.0 - u)
		# взгляд — от того, куда смотрел, к цели; цель доходит к концу шага, ровно в первый кадр клипа
		var aim := _angles_to(p, spot * _v(look_pt)) if look_pt != null else Vector2(p.seat_yaw, -0.1)
		var k := _smoother(minf(u * 1.15, 1.0))
		p.look_at_angles(lerp_angle(cam0.x, aim.x, k), lerpf(cam0.y, aim.y, k)), 0.0, 1.0, dur)
	await tw.finished
	p.seat_walk = 0.0
	await get_tree().create_timer(0.15).timeout     # ноги дошагали в стойку — дальше клип с той же стойки


## Тянется к кнопке питания: клип PowerReach от начала до конца (поза у стола → кнопка → у стола), взгляд —
## по его дорожке. На кадре press — щелчок и комп включается. Взгляд в начале плавно переходит от того,
## куда смотрел игрок, к дорожке клипа, а в конце — на середину осмотра (монитор), а не туда, где был.
func _press_power(p: Player) -> void:
	var length: float = p.model.call("power_length")
	if length <= 0.0:
		Game.sfx("click", global_position)
		power_on()
		return
	var btn: Vector3 = _glow[0].global_position if not _glow.is_empty() else global_position
	var from := Vector2(p.cam_yaw, p.cam_pitch)
	var t := 0.0
	var pressed := false
	p.model.set("power_time", 0.0)
	while t < length:
		await get_tree().physics_frame
		t = minf(t + get_physics_process_delta_time() * (hurry_rate if _hurry else clip_rate), length)
		p.model.set("power_time", t)
		if not _power_look.is_empty():
			var a := _angles_to(p, sit_spot.global_transform * _v(_sample(_power_look, t)))
			var back := from if t < length * 0.5 else _look_center
			var w := _smoother(minf(t, length - t) / SETTLE_TIME)
			p.look_at_angles(lerp_angle(back.x, a.x, w), lerpf(back.y, a.y, w))
		if not pressed and t >= _power_press:
			pressed = true
			Game.sfx("click", btn)
			power_on()
	p.model.set("power_time", -1.0)


## Отпустить все клавиши и кнопку мыши (руки — в покой).
func _reset_hands(p: Player) -> void:
	_keys_held.clear()
	p.model.set("desk_click", false)
	p.model.set("desk_keys", [false, false, false, false] as Array[bool])


## Палец левой для клавиши: пробел — большой, левый край (Q A Z Tab Shift…) — безымянный,
## W S X E — средний, D F R C V… — указательный; остальное (печатает текст) — какой-нибудь из трёх.
static func _finger_for(code: Key) -> int:
	match code:
		KEY_SPACE:
			return 3
		KEY_Q, KEY_A, KEY_Z, KEY_1, KEY_2, KEY_TAB, KEY_SHIFT, KEY_CAPSLOCK, KEY_CTRL, KEY_QUOTELEFT:
			return 2
		KEY_W, KEY_S, KEY_X, KEY_E, KEY_3:
			return 1
		KEY_D, KEY_F, KEY_R, KEY_C, KEY_V, KEY_T, KEY_G, KEY_B, KEY_4, KEY_5:
			return 0
	return int(code) % 3


func _update_keys() -> void:
	var held: Array[bool] = [false, false, false, false]
	for f: int in _keys_held.values():
		held[f] = true
	_player.model.set("desk_keys", held)


func _physics_process(_delta: float) -> void:
	# мышка на столе едет вместе с рукой (тот же сдвиг, что у поз DeskMouse*, и тот же вес)
	if _mouse == null or _player == null:
		return
	var w: float = _player.model.get("desk_w")
	var m: Vector2 = _player.model.get("desk_mouse")
	m = m.clamp(-Vector2.ONE, Vector2.ONE)
	var off := Vector3(m.x * mouse_travel.x, 0.0, -m.y * mouse_travel.y) * w
	_mouse.global_position = _mouse_home + sit_spot.global_basis * off


## Экран: SubViewport с рабочим столом → текстура на плоскости экрана монитора.
func _build_screen() -> void:
	viewport = SubViewport.new()
	viewport.name = "Screen"
	viewport.size = screen_size
	viewport.disable_3d = true
	viewport.transparent_bg = false
	viewport.gui_embed_subwindows = true
	viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED   # пока комп выключен
	viewport.size_2d_override = Vector2i(ui_size)                      # всё 2D растягивается на весь экран
	viewport.size_2d_override_stretch = true
	viewport.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_LINEAR
	add_child(viewport)
	_pointer = PcCursor.new()
	_pointer.name = "Cursor"
	if desktop_scene:
		_desktop = desktop_scene.instantiate() as Control
		viewport.add_child(_desktop)
		if "cursor" in _desktop:
			_desktop.set("cursor", _pointer)
		if _desktop.has_signal("sound"):
			_desktop.connect("sound", _on_pc_sound)
		if _desktop.has_signal("shut_down"):
			_desktop.connect("shut_down", power_off)
	viewport.add_child(_pointer)
	cursor = ui_size * 0.5
	_pointer.position = cursor
	var root: Node = owner if owner else get_parent()
	for gname: String in glow_meshes:
		var gn := root.find_child(gname, true, false) as Node3D
		if gn:
			gn.visible = false
			_glow.append(gn)
	var mi := root.find_child(screen_mesh, true, false) as MeshInstance3D
	if mi == null:
		push_warning("pc_seat: нет экрана %s" % screen_mesh)
		return
	_speaker_pos = mi.global_position
	var kb := root.find_child("Keyboard_nocol", true, false) as Node3D
	_keys_pos = kb.global_position if kb else _speaker_pos
	_mouse = root.find_child(mouse_mesh, true, false) as Node3D
	if _mouse:
		_mouse_home = _mouse.global_position
	var sl := root.find_child(speaker_nodes[0], true, false) as Node3D
	var sr := root.find_child(speaker_nodes[1], true, false) as Node3D
	speakers = PcSpeakers.new()
	speakers.name = "Speakers"
	add_child(speakers)
	speakers.setup(_center(sl) if sl else _speaker_pos + Vector3.LEFT * 0.35,
			_center(sr) if sr else _speaker_pos + Vector3.RIGHT * 0.35)
	if _desktop and "speakers" in _desktop:
		_desktop.set("speakers", speakers)
	_mat = ShaderMaterial.new()
	_mat.shader = preload("res://shaders/pc_screen.gdshader")
	_mat.set_shader_parameter("screen_tex", viewport.get_texture())
	_mat.set_shader_parameter("power", 0.0)
	mi.set_surface_override_material(0, _mat)


## Включить комп: экран разгорается за dur секунд.
func power_on(dur := 1.2) -> void:
	if powered:
		return
	powered = true
	_set_glow(true)
	_update_uses()
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	if _mat:
		create_tween().tween_method(func(v: float) -> void: _mat.set_shader_parameter("power", v), 0.0, 1.0, dur)
	if _desktop and _desktop.has_method("boot"):
		_desktop.call("boot")
	powered_on.emit()


## Windows выключилась: экран гаснет, в следующий раз Юрчик снова нажмёт кнопку.
func power_off(dur := 0.6) -> void:
	if not powered:
		return
	powered = false
	_set_glow(false)
	if state == State.MONITOR:
		exit_monitor()                               # Windows выключилась — отъезжает, системник снова под рукой
	_update_uses()
	if _mat:
		var tw := create_tween()
		tw.tween_method(func(v: float) -> void: _mat.set_shader_parameter("power", v), 1.0, 0.0, dur)
		tw.tween_callback(func() -> void:
			if not powered:
				viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED)
	powered_off.emit()


func _set_glow(on: bool) -> void:
	for gn: Node3D in _glow:
		gn.visible = on


func _on_pc_sound(sound_name: String) -> void:
	if speakers:
		speakers.play(Game.stream("win7_" + sound_name), -3.0)
	else:
		Game.sfx("win7_" + sound_name, _speaker_pos, -7.0, 0.0)


## Середина модели (где динамик), а не её начало координат на столе.
static func _center(n: Node3D) -> Vector3:
	var box := AABB()
	var first := true
	for m: Node in n.find_children("*", "MeshInstance3D", true, false):
		var mi := m as MeshInstance3D
		var b := mi.global_transform * mi.get_aabb()
		box = b if first else box.merge(b)
		first = false
	return n.global_position if first else box.get_center()


## В кресле, в переходе (подходит, садится, жмёт кнопку, едет к монитору и обратно, встаёт): ничего нового не начать.
func _is_busy() -> bool:
	return state != State.IDLE and state != State.SEATED_LOOK and state != State.MONITOR


## Системник и монитор отзываются на прицел только в осмотре: системник — пока комп выключен, монитор — включён.
func _update_uses() -> void:
	if power_use:
		power_use.enabled = state == State.SEATED_LOOK and not powered
	if monitor_use:
		monitor_use.enabled = state == State.SEATED_LOOK and powered


## Сидит и смотрит вокруг: голова крутится от монитора, тело и кресло на месте.
func _enter_look() -> void:
	state = State.SEATED_LOOK
	_hurry = false
	_player.set_seat_look(true, _look_center, deg_to_rad(look_yaw_limit),
			deg_to_rad(look_pitch_min), deg_to_rad(look_pitch_max), look_reach)
	_update_uses()


func _leave_look(next: State) -> void:
	state = next
	_hurry = false
	_player.set_seat_look(false)
	_update_uses()


## Сесть: подойти к креслу и клип посадки (кресло едет вместе с ним). Дальше — осмотр (SEATED_LOOK):
## комп сам не включается, и взгляд к монитору не уезжает.
func sit(p: Player) -> void:
	if state != State.IDLE or p.seated:
		return
	state = State.WALKING
	seated = true
	_hurry = false
	_player = p
	if use:
		use.enabled = false
	p.set_seated(true)
	var spot := sit_spot.global_transform
	var yaw := spot.basis.get_euler().y
	var from_t := _mark("sit") if chair_out else 0.0
	var first_look: Variant = _sample(_look_keys, from_t) if not _look_keys.is_empty() else null
	await _walk_to(p, _stand if chair_out else _start, first_look)
	# узел игрока — в SitSpot, тело — там же, где стояло: дальше всё движение ведёт клип
	state = State.SITTING_DOWN
	p.glide_camera()
	p.global_position = spot.origin
	p.seat_yaw = yaw
	p.model.set("seat_time", from_t)
	p.model.call("snap_seat", true)
	var length: float = p.model.call("seat_length")
	await _play(from_t, length)
	chair_out = false
	_reset_hands(p)
	# середина осмотра — куда смотрит последний кадр клипа (на монитор)
	_look_center = Vector2(p.cam_yaw, p.cam_pitch)
	if not _look_keys.is_empty():
		_look_center = _angles_to(p, sit_spot.global_transform * _v(_sample(_look_keys, length)))
	_enter_look()
	sat_down.emit()


## E на системнике: тянется к кнопке питания, комп включается, взгляд возвращается на середину (монитор).
func _on_power_use(_p: Player) -> void:
	if state != State.SEATED_LOOK or powered:
		return
	_leave_look(State.POWERING)
	await _press_power(_player)
	_enter_look()


## E на мониторе: работать за компом.
func _on_monitor_use(_p: Player) -> void:
	if state == State.SEATED_LOOK and powered:
		enter_monitor()


## Взгляд уезжает к монитору; когда доехал — мышь и клавиши уходят в комп.
func enter_monitor() -> void:
	if state != State.SEATED_LOOK:
		return
	var p := _player
	_leave_look(State.ZOOMING_IN)
	_reset_hands(p)
	p.model.set("desk_live", true)                   # руки на клаве и мышке — живые
	p.seat_view = screen_view.global_transform
	p.seat_view_fov = view_fov
	Graphics.screen_focus = true                     # чёткая картинка, пока смотрит в монитор
	# глаза тоже поворачиваются к монитору: отъедет — и смотрит на него, а не туда, куда смотрел до
	_ease_look(p, _look_center.x, _look_center.y, zoom_in)
	var tw := _tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_property(p, "seat_view_blend", 1.0, zoom_in)
	await tw.finished
	state = State.MONITOR
	active = true
	monitor_entered.emit()


## Отъехать от монитора: руки в покой, взгляд остаётся на мониторе, дальше — снова осмотр.
func exit_monitor() -> void:
	if state != State.MONITOR:
		return
	var p := _player
	state = State.ZOOMING_OUT
	active = false
	_reset_hands(p)
	p.model.set("desk_live", false)                  # правая с мышкой плавно возвращается в середину коврика
	var tw := _tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_property(p, "seat_view_blend", 0.0, zoom_out)
	await tw.finished
	Graphics.screen_focus = false
	_enter_look()
	monitor_exited.emit()


## Встать (из осмотра): взгляд плавно переходит к первому кадру обратного клипа, клип задом наперёд
## до момента, где он стоит перед креслом. Кресло остаётся откаченным и повёрнутым.
func stand() -> void:
	if state != State.SEATED_LOOK:
		return
	var p := _player
	_leave_look(State.STANDING_UP)
	_reset_hands(p)
	p.model.set("desk_live", false)
	var length: float = p.model.call("seat_length")
	if not _look_keys.is_empty():
		var a := _angles_to(p, sit_spot.global_transform * _v(_sample(_look_keys, length)))
		await _ease_look(p, a.x, a.y, zoom_out)
	await _play(length, _mark("sit"))
	chair_out = true
	# стоит перед креслом: узел игрока — туда же, где тело (клип кончился обычной стойкой)
	var spot := sit_spot.global_transform
	var pos := spot * _v(_stand)
	pos.y = spot.origin.y
	p.glide_camera()
	p.model.set("seat_time", -1.0)
	p.model.call("snap_seat", false)
	p.global_position = pos
	p.seat_yaw = spot.basis.get_euler().y + float(_stand[3])
	# поворачивается к комнате и отходит за кресло — дальше обычная ходьба
	await _walk_to(p, EXIT_SPOT)
	var yaw := spot.basis.get_euler().y + float(EXIT_SPOT[3])
	p.cam_yaw = yaw
	p.look_at_angles(yaw, -0.1)
	p.glide_camera()                                 # из кресельного режима камеры в обычный — без скачка
	p.set_seated(false)
	seated = false
	state = State.IDLE
	if use:
		use.enabled = true
	stood_up.emit()


## Esc / B — шаг назад.
static func _is_back(event: InputEvent) -> bool:
	return event.is_action_pressed("pause") or (event is InputEventJoypadButton and event.is_action_pressed("ui_cancel"))


func _input(event: InputEvent) -> void:
	if state == State.IDLE:
		return
	if state == State.SEATED_LOOK:
		if _is_back(event):
			get_viewport().set_input_as_handled()
			stand()
			return
		# мышь (поворот головы) и E (системник, монитор) — игроку; остальное в кресле не нужно
		if event is InputEventMouseMotion or event is InputEventMouseButton or event is InputEventJoypadMotion \
				or event.is_action("interact"):
			return
		get_viewport().set_input_as_handled()
		return
	get_viewport().set_input_as_handled()            # пока сидит, ввод — только кресло и комп
	if _is_busy():
		if event.is_action_pressed("interact"):
			_hurry = true                            # ещё раз E — садится/встаёт/жмёт кнопку быстрее
		return
	if _is_back(event):
		exit_monitor()
		return
	if not active:
		return
	if event is InputEventMouseMotion:
		var rel: Vector2 = event.relative * cursor_speed * ui_size.y / 720.0
		cursor = (cursor + rel).clamp(Vector2.ZERO, ui_size - Vector2.ONE)
		_pointer.position = cursor
		# рука с мышкой — там же на коврике, где курсор на экране (вверх по экрану — мышь от себя)
		var u := cursor / ui_size * 2.0 - Vector2.ONE
		_player.model.set("desk_mouse", Vector2(u.x, -u.y))
		var mm := InputEventMouseMotion.new()
		mm.position = cursor
		mm.global_position = cursor
		mm.relative = rel
		mm.velocity = rel * 60.0
		mm.button_mask = event.button_mask
		viewport.push_input(mm, true)
	elif event is InputEventMouseButton:
		var mb := InputEventMouseButton.new()
		mb.position = cursor
		mb.global_position = cursor
		mb.button_index = event.button_index
		mb.pressed = event.pressed
		mb.double_click = event.double_click
		mb.button_mask = event.button_mask
		mb.factor = event.factor
		if event.pressed and event.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT]:
			Game.sfx("pc_mouse", _keys_pos, -20.0, 0.1)
		if event.button_index == MOUSE_BUTTON_LEFT:
			_player.model.set("desk_click", event.pressed)
		viewport.push_input(mb, true)
	elif event is InputEventKey:
		if event.pressed and not event.echo:
			Game.sfx("pc_key_%d" % randi_range(1, 3), _keys_pos, -18.0, 0.08)
		var code: Key = event.physical_keycode if event.physical_keycode != KEY_NONE else event.keycode
		if event.pressed and not event.echo:
			_keys_held[code] = _finger_for(code)
			_update_keys()
		elif not event.pressed and _keys_held.has(code):
			_keys_held.erase(code)
			_update_keys()
		viewport.push_input(event, true)


func _exit_tree() -> void:
	if seated:
		Graphics.screen_focus = false
