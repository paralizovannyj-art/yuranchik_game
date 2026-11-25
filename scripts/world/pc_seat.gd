## Комп Юрчика: сесть в игровое кресло и работать за монитором.
## Наводишься на кресло, стол, монитор или системник — прицел расширяется, E — Юрчик подходит, садится
## (клип SitDown, tools/blender/build_sit_down.py) и, если комп выключен, жмёт кнопку питания. Потом взгляд
## уезжает к монитору: экран почти во весь кадр, но это всё ещё монитор в комнате — рамка, блик, шум.
## Мышь двигает курсор внутри экрана, клики и клавиши уходят в «компьютер» (SubViewport с рабочим столом).
## Esc (или B на геймпаде) — встать: всё то же в обратную сторону.
class_name PcSeat
extends Node3D

signal powered_on          ## комп включился (первый раз, когда Юрчик сел)
signal sat_down            ## сел и смотрит в монитор
signal stood_up            ## встал с кресла
signal powered_off         ## Windows завершила работу, экран погас

@export var use: Interactable                        ## «Сесть за компьютер» (кресло, стол, монитор, системник)
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
@export var walk_in := 0.45                           ## подойти к креслу и развернуться к столу
@export var zoom_in := 1.0                            ## взгляд к монитору
@export var zoom_out := 0.7

@onready var sit_spot: Marker3D = $SitSpot            ## где Юрчик стоит перед тем, как сесть (смотрит вдоль −Z)
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


func _ready() -> void:
	_build_screen()
	if use:
		use.interacted.connect(sit)


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


## Сесть: подойти, сесть (клип), включить комп, если выключен, и уставиться в монитор.
func sit(p: Player) -> void:
	if seated or _busy or p.seated:
		return
	_busy = true
	seated = true
	_player = p
	if use:
		use.enabled = false
	p.set_seated(true)
	var spot := sit_spot.global_transform
	var yaw := spot.basis.get_euler().y
	p.look_at_angles(yaw, -0.5)                      # подходя, смотрит на стол и монитор
	var tw := create_tween().set_parallel().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_property(p, "global_position", spot.origin, walk_in)
	await tw.finished
	var clip_len: float = p.model.call("seat_length")
	Game.sfx("chair_sit", global_position, -4.0, 0.05)
	tw = create_tween()
	tw.tween_method(func(t: float) -> void: p.model.set("seat_time", t), 0.0, clip_len, clip_len)
	await tw.finished
	if not powered:
		p.look_at_angles(yaw, reach_pitch)           # тянется к кнопке на системнике под столом
		await get_tree().create_timer(0.35).timeout
		Game.sfx("click", global_position)
		power_on()
		await get_tree().create_timer(0.6).timeout
	p.seat_view = screen_view.global_transform
	p.seat_view_fov = view_fov
	Graphics.screen_focus = true                     # чёткая картинка, пока смотрит в монитор
	tw = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_property(p, "seat_view_blend", 1.0, zoom_in)
	await tw.finished
	active = true
	_busy = false
	sat_down.emit()


## Встать: взгляд от монитора, клип посадки задом наперёд, снова ходит.
func stand() -> void:
	if not seated or _busy:
		return
	_busy = true
	active = false
	var p := _player
	var tw := create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.tween_property(p, "seat_view_blend", 0.0, zoom_out)
	await tw.finished
	Graphics.screen_focus = false
	p.look_at_angles(p.cam_yaw, -0.1)
	var clip_len: float = p.model.call("seat_length")
	Game.sfx("chair_sit", global_position, -6.0, 0.05)
	tw = create_tween()
	tw.tween_method(func(t: float) -> void: p.model.set("seat_time", t), clip_len, 0.0, clip_len)
	await tw.finished
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
