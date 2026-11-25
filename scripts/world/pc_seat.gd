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

@export var use: Interactable                        ## «Сесть за компьютер» (кресло, стол, монитор, системник)
@export var screen_mesh := "PCScreen_nocol"          ## плоскость экрана в модели монитора (UV 0..1 на весь экран)
@export var desktop_scene: PackedScene               ## что показывает комп (рабочий стол)
@export var screen_size := Vector2i(1280, 1024)      ## разрешение экрана компа (матрица 5:4, 17")
@export var view_fov := 40.0                          ## угол обзора, когда смотришь в монитор
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
var cursor := Vector2.ZERO     ## курсор в пикселях экрана компа
var _player: Player
var _mat: ShaderMaterial
var _desktop: Control
var _pointer: Control
var _busy := false


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
	add_child(viewport)
	if desktop_scene:
		_desktop = desktop_scene.instantiate() as Control
		viewport.add_child(_desktop)
	_pointer = PcCursor.new()
	_pointer.name = "Cursor"
	viewport.add_child(_pointer)
	cursor = Vector2(screen_size) * 0.5
	_pointer.position = cursor
	var root: Node = owner if owner else get_parent()
	var mi := root.find_child(screen_mesh, true, false) as MeshInstance3D
	if mi == null:
		push_warning("pc_seat: нет экрана %s" % screen_mesh)
		return
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
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	if _mat:
		create_tween().tween_method(func(v: float) -> void: _mat.set_shader_parameter("power", v), 0.0, 1.0, dur)
	powered_on.emit()


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
		p.look_at_angles(yaw, -0.45)                 # тянется к кнопке на системнике
		await get_tree().create_timer(0.35).timeout
		Game.sfx("click", global_position)
		power_on()
		await get_tree().create_timer(0.6).timeout
	p.seat_view = screen_view.global_transform
	p.seat_view_fov = view_fov
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
		var rel: Vector2 = event.relative * cursor_speed * float(screen_size.y) / 720.0
		cursor = (cursor + rel).clamp(Vector2.ZERO, Vector2(screen_size) - Vector2.ONE)
		_pointer.position = cursor
		var mm := InputEventMouseMotion.new()
		mm.position = cursor
		mm.global_position = cursor
		mm.relative = rel
		mm.button_mask = event.button_mask
		viewport.push_input(mm)
	elif event is InputEventMouseButton:
		var mb := InputEventMouseButton.new()
		mb.position = cursor
		mb.global_position = cursor
		mb.button_index = event.button_index
		mb.pressed = event.pressed
		mb.double_click = event.double_click
		mb.button_mask = event.button_mask
		mb.factor = event.factor
		viewport.push_input(mb)
	elif event is InputEventKey:
		viewport.push_input(event)
