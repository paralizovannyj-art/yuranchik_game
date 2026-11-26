## Комп Юрчика: сесть в игровое кресло и работать за монитором.
## Наводишься на кресло, стол, монитор или системник — прицел расширяется, E — Юрчик подходит к креслу
## и садится, как в тесной комнате (клип ChairSit, tools/blender/build_chair_sit.py): берётся за спинку,
## откатывает кресло, разворачивает его к себе, садится боком, поворачивается к столу и подтягивается ногами.
## Кресло едет по пути из assets/animations/sit/chair_sit.json. Ещё раз E, пока садится, — быстрее.
## Если комп выключен — жмёт кнопку питания. Потом взгляд уезжает к монитору: экран почти во весь кадр,
## но это всё ещё монитор в комнате — рамка, блик, шум.
## Мышь двигает курсор внутри экрана, клики и клавиши уходят в «компьютер» (SubViewport с рабочим столом).
## Esc (или B на геймпаде) — встать: клип задом наперёд до момента, где он встал. Кресло остаётся
## отодвинутым и повёрнутым, и в следующий раз Юрчик садится сразу, без откатывания.
class_name PcSeat
extends Node3D

signal powered_on          ## комп включился (первый раз, когда Юрчик сел)
signal sat_down            ## сел и смотрит в монитор
signal stood_up            ## встал с кресла
signal powered_off         ## Windows завершила работу, экран погас

@export var use: Interactable                        ## «Сесть за компьютер» (кресло, стол, монитор, системник)
@export var chair: Node3D                            ## игровое кресло — едет вместе с клипом посадки
@export_file("*.json") var chair_path := "res://assets/animations/sit/chair_sit.json"   ## путь кресла и взгляд
@export var screen_mesh := "PCScreen_nocol"          ## плоскость экрана в модели монитора (UV 0..1 на весь экран)
@export var speaker_nodes: PackedStringArray = ["SpeakerLeft", "SpeakerRight"]   ## колонки на столе (левая, правая)
@export var glow_meshes: PackedStringArray = ["PcTowerGlow_nocol", "MonitorLed_nocol"]   ## светятся, только пока комп включён: окно и кнопка системника, диод монитора
@export var reach_pitch := -0.85                      ## куда смотрит, нажимая кнопку питания (системник на полу под столом)
@export var desktop_scene: PackedScene               ## что показывает комп (рабочий стол)
@export var screen_size := Vector2i(1280, 1024)      ## разрешение экрана компа (матрица 5:4, 17")
@export var ui_size := Vector2(1024, 820)            ## Windows на 125 %: в этих «логических» пикселях живёт рабочий стол
@export var view_fov := 34.0                          ## угол обзора, когда смотришь в монитор (экран почти во весь кадр)
@export var cursor_speed := 1.0                       ## скорость курсора относительно мыши
@export_group("Время, с")
@export var walk_speed := 1.3                         ## м/с — подходит к креслу
@export var clip_rate := 1.0                          ## скорость клипа посадки
@export var hurry_rate := 2.2                         ## ещё раз «использовать», пока садится, — вот так быстрее
@export var zoom_in := 1.0                            ## взгляд к монитору
@export var zoom_out := 0.7

@onready var sit_spot: Marker3D = $SitSpot            ## «место у компа»: в нём стоит узел игрока, пока идёт клип (смотрит вдоль −Z)
@onready var screen_view: Marker3D = $ScreenView      ## откуда камера смотрит в монитор

var powered := false
var seated := false            ## в кресле (в том числе пока садится и встаёт)
var active := false            ## смотрит в монитор, мышь — курсор компа
var viewport: SubViewport
var cursor := Vector2.ZERO     ## курсор в логических пикселях рабочего стола (ui_size)
var _player: Player
var _mat: ShaderMaterial
var _desktop: Control
var _pointer: Control
var _busy := false
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
var _hurry := false
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
	var d := at - p.eye_point()
	p.look_at_angles(atan2(-d.x, -d.z), atan2(d.y, Vector2(d.x, d.z).length()))


## Кадр клипа: поза (seat_time), кресло и взгляд камеры.
func _apply(t: float) -> void:
	_player.model.set("seat_time", t)
	_place_chair(t)
	if not _look_keys.is_empty():
		_look_at(_player, sit_spot.global_transform * _v(_sample(_look_keys, t)))


## Проиграть клип посадки от t0 до t1 (t1 < t0 — назад, встаёт). Звуки — на кадрах из CUES.
func _play(t0: float, t1: float) -> void:
	var t := t0
	var dir := signf(t1 - t0)
	_apply(t)
	while (t1 - t) * dir > 0.0:
		await get_tree().process_frame
		var nt := t + get_process_delta_time() * (hurry_rate if _hurry else clip_rate) * dir
		nt = minf(nt, t1) if dir > 0.0 else maxf(nt, t1)
		for cue: Array in CUES:
			var ct := _mark(cue[0]) + float(cue[1]) / _fps
			if (cue[4] == 0 or cue[4] == int(dir)) and (ct - t) * dir > 0.0 and (ct - nt) * dir <= 0.0:
				var at := chair.global_position + Vector3.UP * 0.3 if chair else global_position
				Game.sfx(cue[2], at, cue[3], 0.08)
		t = nt
		_apply(t)


## Подойти шагом в точку (пространство SitSpot) и повернуться: ноги шагают, камера смотрит на кресло
## (at_chair) или вперёд, куда идёт.
func _walk_to(p: Player, spot_pt: Array, at_chair := true) -> void:
	var spot := sit_spot.global_transform
	var target := spot * _v(spot_pt)
	target.y = spot.origin.y
	var yaw := spot.basis.get_euler().y + float(spot_pt[3])
	var from := p.global_position
	var yaw0 := p.seat_yaw
	var dist := Vector2(target.x - from.x, target.z - from.z).length()
	var dur := clampf(dist / walk_speed, 0.3, 2.0)
	var aim := chair.global_position + Vector3.UP * 0.9 if chair else spot.origin
	var tw := create_tween()
	tw.tween_method(func(u: float) -> void:
		var e := smoothstep(0.0, 1.0, u)
		p.global_position = from.lerp(target, e)
		p.seat_yaw = lerp_angle(yaw0, yaw, smoothstep(0.0, 1.0, minf(u * 1.4, 1.0)))
		# скорость шага — по скорости на кривой (разгон и остановка), чтобы ноги не скользили
		p.seat_walk = dist / dur * 6.0 * u * (1.0 - u)
		if at_chair:
			_look_at(p, aim)
		else:
			p.look_at_angles(p.seat_yaw, -0.15), 0.0, 1.0, dur)
	await tw.finished
	p.seat_walk = 0.0
	await get_tree().create_timer(0.15).timeout     # ноги дошагали в стойку — дальше клип с той же стойки


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


## Сесть: подойти к креслу, клип посадки (кресло едет вместе с ним), включить комп, если выключен,
## и уставиться в монитор.
func sit(p: Player) -> void:
	if seated or _busy or p.seated:
		return
	_busy = true
	seated = true
	_hurry = false
	_player = p
	if use:
		use.enabled = false
	p.set_seated(true)
	var spot := sit_spot.global_transform
	var yaw := spot.basis.get_euler().y
	var from_t := _mark("sit") if chair_out else 0.0
	await _walk_to(p, _stand if chair_out else _start)
	# узел игрока — в SitSpot, тело — там же, где стояло: дальше всё движение ведёт клип
	p.global_position = spot.origin
	p.seat_yaw = yaw
	p.model.set("seat_time", from_t)
	p.model.call("snap_seat", true)
	await _play(from_t, p.model.call("seat_length"))
	chair_out = false
	if not powered:
		p.look_at_angles(yaw, reach_pitch)           # тянется к кнопке на системнике под столом
		await get_tree().create_timer(0.35).timeout
		Game.sfx("click", global_position)
		power_on()
		await get_tree().create_timer(0.6).timeout
	p.seat_view = screen_view.global_transform
	p.seat_view_fov = view_fov
	Graphics.screen_focus = true                     # чёткая картинка, пока смотрит в монитор
	var tw := create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_property(p, "seat_view_blend", 1.0, zoom_in)
	await tw.finished
	active = true
	_busy = false
	sat_down.emit()


## Встать: взгляд от монитора, клип задом наперёд до момента, где он стоит перед креслом.
## Кресло остаётся откаченным и повёрнутым.
func stand() -> void:
	if not seated or _busy:
		return
	_busy = true
	_hurry = false
	active = false
	var p := _player
	var tw := create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_property(p, "seat_view_blend", 0.0, zoom_out)
	await tw.finished
	Graphics.screen_focus = false
	await _play(p.model.call("seat_length"), _mark("sit"))
	chair_out = true
	# стоит перед креслом: узел игрока — туда же, где тело (клип кончился обычной стойкой)
	var spot := sit_spot.global_transform
	var pos := spot * _v(_stand)
	pos.y = spot.origin.y
	p.model.set("seat_time", -1.0)
	p.model.call("snap_seat", false)
	p.global_position = pos
	p.seat_yaw = spot.basis.get_euler().y + float(_stand[3])
	# поворачивается к комнате и отходит за кресло — дальше обычная ходьба
	await _walk_to(p, EXIT_SPOT, false)
	var yaw := spot.basis.get_euler().y + float(EXIT_SPOT[3])
	p.cam_yaw = yaw
	p.look_at_angles(yaw, -0.1)
	p.set_seated(false)
	seated = false
	_busy = false
	if use:
		use.enabled = true
	stood_up.emit()


func _input(event: InputEvent) -> void:
	if not seated:
		return
	get_viewport().set_input_as_handled()            # пока сидит, ввод — только кресло и комп
	if _busy and event.is_action_pressed("interact"):
		_hurry = true                                # ещё раз E — садится/встаёт быстрее
		return
	if event.is_action_pressed("pause") or (event is InputEventJoypadButton and event.is_action_pressed("ui_cancel")):
		stand()
		return
	if not active:
		return
	if event is InputEventMouseMotion:
		var rel: Vector2 = event.relative * cursor_speed * ui_size.y / 720.0
		cursor = (cursor + rel).clamp(Vector2.ZERO, ui_size - Vector2.ONE)
		_pointer.position = cursor
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
		viewport.push_input(mb, true)
	elif event is InputEventKey:
		if event.pressed and not event.echo:
			Game.sfx("pc_key_%d" % randi_range(1, 3), _keys_pos, -18.0, 0.08)
		viewport.push_input(event, true)


func _exit_tree() -> void:
	if seated:
		Graphics.screen_focus = false
