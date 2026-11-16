## Телефон Юрчика «ОРБИТА»: кнопочный QWERTY-брусок, который он поднимает перед собой (Tab).
## Модель — assets/models/phone.gltf (tools/blender/build_phone.py). Экран — SubViewport с PhoneScreen,
## «печать» лицевой стороны (буквы, иконки, надпись) — второй SubViewport, нарисованный один раз
## по phone_layout.json. Висит на камере игрока; мир за ним размывается (DOF).
## Пауза не ставится: пока телефон в руке, Юрчик идёт шагом, не бьёт и не бегает (player.phone_up).
class_name Phone
extends Node3D

const MODEL := preload("res://assets/models/phone.gltf")
const LAYOUT := preload("res://assets/models/phone_layout.json")
const SCALE := 1.6                               ## крупнее настоящего, чтобы экран читался на 854×480
const OPEN_POS := Vector3(0.022, -0.052, -0.118)
const CLOSED_POS := Vector3(0.05, -0.2, -0.12)
## Отдельный слой: фонарик в голове (player.tscn) телефон не освещает, иначе экран засвечивается.
const LAYER := 1 << 18
const OPEN_ROT := Vector3(deg_to_rad(12.0), deg_to_rad(-8.0), deg_to_rad(-5.0))
const CLOSED_ROT := Vector3(deg_to_rad(55.0), deg_to_rad(-8.0), deg_to_rad(-20.0))
const ANIM := 0.28
const SERGEY_NEAR := 14.0                        ## ближе — одна палка сети
const SERGEY_FAR := 45.0                         ## дальше — все четыре

var is_open := false
var screen: PhoneScreen
var player: Player

var _screen_vp: SubViewport
var _print_vp: SubViewport
var _light: OmniLight3D
var _tween: Tween
var _attrs: CameraAttributesPractical
var _cam_old_attrs: CameraAttributes


func _ready() -> void:
	visible = false
	scale = Vector3.ONE * SCALE
	position = CLOSED_POS
	rotation = CLOSED_ROT
	_build_screen()
	_build_model()
	for v: Node in find_children("*", "VisualInstance3D", true, false):
		(v as VisualInstance3D).layers = LAYER
	if player:
		player.flashlight.light_cull_mask &= ~LAYER
	Game.objective_changed.connect(func(_t: String) -> void: _buzz())
	Game.message_received.connect(func(_m: Dictionary) -> void: _buzz())


func _build_screen() -> void:
	_screen_vp = SubViewport.new()
	_screen_vp.size = Vector2i(320, 240)
	_screen_vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	_screen_vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	add_child(_screen_vp)
	screen = PhoneScreen.new()
	screen.player = player
	_screen_vp.add_child(screen)
	var pr := PhonePrint.new()
	pr.layout = LAYOUT.data
	_print_vp = SubViewport.new()
	_print_vp.size = Vector2i(pr.layout_size() * PhonePrint.PX_MM)
	_print_vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	add_child(_print_vp)
	_print_vp.add_child(pr)


func _build_model() -> void:
	var model: Node3D = MODEL.instantiate()
	add_child(model)
	# экран: светится сам и не зависит от освещения
	var sm := StandardMaterial3D.new()
	sm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sm.albedo_texture = _screen_vp.get_texture()
	sm.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR
	# лицевая панель и клавиши: глянцевый чёрный пластик с напечатанными буквами, буквы подсвечены
	var pm := StandardMaterial3D.new()
	pm.albedo_texture = _print_vp.get_texture()
	pm.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	pm.roughness = 0.32
	pm.emission_enabled = true
	pm.emission_texture = _print_vp.get_texture()
	pm.emission_energy_multiplier = 0.3
	for mi: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for i in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(i)
			match mat.resource_name if mat else "":
				"PhScreen": mi.set_surface_override_material(i, sm)
				"PhPrint": mi.set_surface_override_material(i, pm)
	# экран подсвечивает лицо и руки голубым
	_light = OmniLight3D.new()
	_light.light_color = Color("9fd0c8")
	_light.light_energy = 0.0
	_light.omni_range = 0.45
	_light.omni_attenuation = 1.6
	_light.position = Vector3(0, 0.025, 0.03)
	_light.light_cull_mask = ~LAYER              # светит на руки и лицо, но не на сам телефон
	add_child(_light)


# ----------------------------------------------------------------------------- достать / убрать
func open() -> void:
	if is_open:
		return
	is_open = true
	visible = true
	screen.reset()
	_screen_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	if player:
		player.phone_up = true
	Game.sfx("ui_open", null, -12.0, 0.1)
	_blur(true)
	_animate(OPEN_POS, OPEN_ROT, 0.45)


func close() -> void:
	if not is_open:
		return
	is_open = false
	if player and is_instance_valid(player):
		player.phone_up = false
	Game.sfx("ui_open", null, -14.0, 0.1)
	_blur(false)
	_animate(CLOSED_POS, CLOSED_ROT, 0.0)
	_tween.tween_callback(func() -> void:
		visible = false
		_screen_vp.render_target_update_mode = SubViewport.UPDATE_DISABLED)


func _animate(pos: Vector3, rot: Vector3, light: float) -> void:
	if _tween:
		_tween.kill()
	_tween = create_tween().set_parallel().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_tween.tween_property(self, "position", pos, ANIM)
	_tween.tween_property(self, "rotation", rot, ANIM)
	_tween.tween_property(_light, "light_energy", light, ANIM)
	_tween.chain()


## Мир за телефоном размывается: дальний DOF на камере, пока телефон в руке.
func _blur(on: bool) -> void:
	var cam := get_parent() as Camera3D
	if cam == null:
		return
	if on:
		_cam_old_attrs = cam.attributes
		_attrs = CameraAttributesPractical.new()
		_attrs.dof_blur_far_enabled = true
		_attrs.dof_blur_far_distance = 0.6
		_attrs.dof_blur_far_transition = 2.5
		_attrs.dof_blur_amount = 0.0
		cam.attributes = _attrs
		create_tween().tween_property(_attrs, "dof_blur_amount", 0.06, ANIM)
	elif _attrs:
		var a := _attrs
		var tw := create_tween()
		tw.tween_property(a, "dof_blur_amount", 0.0, ANIM)
		tw.tween_callback(func() -> void:
			if cam.attributes == a:
				cam.attributes = _cam_old_attrs)


# ----------------------------------------------------------------------------- вибрация, сеть
## Новая СМС или задание: вибрация (звук и отдача на геймпаде), на экране ничего.
func _buzz() -> void:
	Game.sfx("phone_vibrate", null, -6.0, 0.0)
	Input.start_joy_vibration(0, 0.25, 0.0, 0.5)
	if is_open:
		Game.sfx("phone_sms", null, -10.0, 0.0)
		screen.queue_redraw()


func _process(_delta: float) -> void:
	if not is_open or player == null or not is_instance_valid(player):
		return
	var near := 1e9
	for e: Node in get_tree().get_nodes_in_group("enemy"):
		if e.get("display_name") == "Сергей":
			near = minf(near, (e as Node3D).global_position.distance_to(player.global_position))
	screen.signal_bars = clampi(1 + int(3.0 * clampf((near - SERGEY_NEAR) / (SERGEY_FAR - SERGEY_NEAR), 0.0, 1.0)), 1, 4)


## «Печать» лицевой стороны: фон панели, динамик, надпись, буквы на клавишах, иконки на кнопках.
## Рисуется один раз в SubViewport; UV модели — плоская проекция всей лицевой стороны (1 мм = PX_MM пикселей).
class PhonePrint extends Control:
	const PX_MM := 10.0
	const PANEL := Color("0b0c0e")
	const KEY := Color("15171a")
	const LABEL := Color("e8e9eb")
	const CYR := Color("c4c7cc")
	const NUM := Color("d9a441")
	var layout: Dictionary

	func layout_size() -> Vector2:
		return Vector2(layout["size"][0], layout["size"][1])

	func _ready() -> void:
		size = layout_size() * PX_MM

	func _r(a: Array) -> Rect2:
		return Rect2(Vector2(a[0], a[1]) * PX_MM, Vector2(a[2] - a[0], a[3] - a[1]) * PX_MM)

	func _draw() -> void:
		var f := ThemeDB.fallback_font
		draw_rect(Rect2(Vector2.ZERO, size), PANEL)
		# рамка стекла вокруг экрана
		var scr := _r(layout["screen"])
		draw_rect(scr.grow(6), Color("15171b"))
		draw_rect(scr.grow(6), Color("23262c"), false, 2.0)
		draw_rect(scr, Color.BLACK)
		# динамик: щель с сеткой
		var ear := _r(layout["earpiece"])
		draw_rect(ear, Color("030304"))
		for i in int(ear.size.x / 6):
			draw_line(ear.position + Vector2(3 + i * 6, 2), ear.position + Vector2(3 + i * 6, ear.size.y - 2), Color("1c1e22"), 1.0)
		draw_rect(ear, Color("2a2d33"), false, 1.0)
		var bp := Vector2(layout["brand"][0], layout["brand"][1]) * PX_MM
		draw_string(f, bp + Vector2(-100, 8), "ОРБИТА", HORIZONTAL_ALIGNMENT_CENTER, 200, 26, Color("b9bcc0"))
		draw_circle(Vector2(layout["mic"][0], layout["mic"][1]) * PX_MM, 4.0, Color("030304"))
		for k: Dictionary in layout["keys"]:
			_key(f, k)

	func _key(f: Font, k: Dictionary) -> void:
		var r := _r(k.rect)
		var kind: String = k.kind
		var bg := KEY
		if kind == "dpad":
			bg = Color("0f1013")
		elif kind == "dpad_c":
			bg = Color("1a1d21")
		draw_rect(r, bg)
		draw_rect(Rect2(r.position + Vector2(0, 2), Vector2(r.size.x, 3)), bg.lightened(0.08))   # блик по верхней кромке
		var c := r.get_center()
		match kind:
			"key":
				var lat: String = k.lat
				var big := 26 if lat.length() == 1 else 20
				var shift := -6.0 if k.num != "" else 0.0       # с цифрой буква сдвинута влево, цифра справа сверху
				draw_string(f, Vector2(r.position.x + shift, c.y - 4), lat, HORIZONTAL_ALIGNMENT_CENTER, r.size.x, big, LABEL)
				draw_string(f, Vector2(r.position.x, c.y + 26), k.cyr, HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 20, CYR)
				if k.num != "":
					draw_string(f, r.position + Vector2(r.size.x - 12, 18), k.num, HORIZONTAL_ALIGNMENT_LEFT, -1, 15, NUM)
			"back":
				_arrow(c + Vector2(0, -10), Vector2.LEFT)
				draw_string(f, Vector2(r.position.x, c.y + 26), k.cyr, HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 22, CYR)
			"enter":
				draw_polyline(PackedVector2Array([c + Vector2(10, -24), c + Vector2(10, -10), c + Vector2(-10, -10)]), LABEL, 3.0)
				draw_polyline(PackedVector2Array([c + Vector2(-4, -16), c + Vector2(-10, -10), c + Vector2(-4, -4)]), LABEL, 3.0)
				draw_string(f, Vector2(r.position.x, c.y + 26), k.cyr, HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 22, CYR)
			"shift":
				_arrow(c, Vector2.UP)
			"space":
				draw_polyline(PackedVector2Array([c + Vector2(-40, -8), c + Vector2(-40, 4), c + Vector2(40, 4), c + Vector2(40, -8)]), LABEL, 3.0)
				draw_string(f, r.position + Vector2(r.size.x - 15, 20), k.num, HORIZONTAL_ALIGNMENT_LEFT, -1, 17, NUM)
			"soft_music":
				draw_circle(c + Vector2(-6, 8), 6.0, LABEL)
				draw_line(c + Vector2(-1, 8), c + Vector2(-1, -14), LABEL, 3.0)
				draw_line(c + Vector2(-1, -14), c + Vector2(9, -9), LABEL, 3.0)
			"soft_mail":
				var e := Rect2(c - Vector2(15, 10), Vector2(30, 20))
				draw_rect(e, LABEL, false, 2.5)
				draw_polyline(PackedVector2Array([e.position, c + Vector2(0, 2), e.position + Vector2(30, 0)]), LABEL, 2.5)
			"call":
				_handset(c, 0.0, Color("3fc35a"))
			"end":
				_handset(c, PI * 0.8, Color("e2463b"))
			"dpad":
				draw_rect(r, Color("2c3036"), false, 2.0)
			"dpad_c":
				draw_rect(r, Color("3a3f46"), false, 1.5)

	func _arrow(c: Vector2, d: Vector2) -> void:
		var n := Vector2(-d.y, d.x)
		draw_colored_polygon(PackedVector2Array([c + d * 12, c + n * 10, c + n * 4, c - d * 10 + n * 4, c - d * 10 - n * 4, c - n * 4, c - n * 10]), LABEL)

	## Трубка: дуга с утолщениями на концах.
	func _handset(c: Vector2, rot: float, col: Color) -> void:
		var a0 := PI * 1.1 + rot
		var a1 := PI * 1.9 + rot
		draw_arc(c + Vector2(0, 14).rotated(rot), 16.0, a0, a1, 12, col, 6.0)
		for a: float in [a0, a1]:
			draw_circle(c + Vector2(0, 14).rotated(rot) + Vector2.from_angle(a) * 16.0, 5.0, col)
