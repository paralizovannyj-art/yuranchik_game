## Телефон Юрчика «ОРБИТА Q2»: кнопочный QWERTY-брусок, который он поднимает перед собой (Tab).
## Модель собрана из простых коробок прямо здесь, экран — SubViewport с PhoneScreen, клавиатура —
## второй SubViewport, нарисованный один раз. Висит на камере игрока; мир за ним размывается (DOF).
## Пауза не ставится: пока телефон в руке, Юрчик идёт шагом, не бьёт и не бегает (player.phone_up).
class_name Phone
extends Node3D

const SIZE := Vector3(0.052, 0.112, 0.011)
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
var _keys_vp: SubViewport
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
	_keys_vp = SubViewport.new()
	_keys_vp.size = Vector2i(256, 288)
	_keys_vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	add_child(_keys_vp)
	var keys := PhoneKeys.new()
	_keys_vp.add_child(keys)


func _box(size: Vector3, pos: Vector3, mat: Material) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	var b := BoxMesh.new()
	b.size = size
	m.mesh = b
	m.position = pos
	m.material_override = mat
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(m)
	return m


func _quad(size: Vector2, pos: Vector3, mat: Material) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = size
	m.mesh = q
	m.position = pos
	m.material_override = mat
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(m)
	return m


func _mat(col: Color, rough := 0.6, metal := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = col
	m.roughness = rough
	m.metallic = metal
	return m


func _build_model() -> void:
	var front := SIZE.z / 2.0 + 0.0002
	_box(SIZE, Vector3.ZERO, _mat(Color("141618"), 0.45, 0.2))
	var red := _mat(Color("7a1414"), 0.35, 0.3)
	for sx: float in [-1.0, 1.0]:                # красные боковины, как на примере
		_box(Vector3(0.0022, SIZE.y - 0.006, SIZE.z + 0.001), Vector3(sx * (SIZE.x / 2.0 + 0.0005), 0, 0), red)
	# экран: светится сам и не зависит от освещения
	var sm := StandardMaterial3D.new()
	sm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sm.albedo_texture = _screen_vp.get_texture()
	sm.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR
	_quad(Vector2(0.046, 0.0345) + Vector2(0.004, 0.004), Vector3(0, 0.025, front - 0.0001), _mat(Color("050608"), 0.2))
	_quad(Vector2(0.046, 0.0345), Vector3(0, 0.025, front), sm)
	# клавиатура и крестовина
	var km := StandardMaterial3D.new()
	km.albedo_texture = _keys_vp.get_texture()
	km.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR
	km.roughness = 0.5
	km.emission_enabled = true                   # подсветка клавиатуры
	km.emission_texture = _keys_vp.get_texture()
	km.emission_energy_multiplier = 0.35
	_quad(Vector2(0.046, 0.0518), Vector3(0, -0.0275, front), km)
	# динамик и надпись сверху
	_box(Vector3(0.012, 0.0012, 0.0006), Vector3(0, 0.052, front), _mat(Color("050608")))
	var brand := Label3D.new()
	brand.text = "ОРБИТА"
	brand.font_size = 30
	brand.pixel_size = 0.000055
	brand.outline_size = 0
	brand.modulate = Color("b9bcc0")
	brand.position = Vector3(0, 0.0478, front + 0.0001)
	brand.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	brand.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(brand)
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


## Клавиатура и крестовина: рисуются один раз в маленький SubViewport и ложатся текстурой на модель.
class PhoneKeys extends Control:
	const ROWS := [["QЙ", "WЦ", "EУ", "RК", "TЕ", "YН", "UГ", "IШ", "OЩ", "PЗ"],
		["AФ", "SЫ", "DВ", "FА", "GП", "HР", "JО", "KЛ", "LД", "Ж"],
		["⇧", "ZЯ", "XЧ", "CС", "VМ", "BИ", "NТ", "MЬ", "Б", "<"],
		["Alt", "Sym", "0", " ", " ", " ", "Ю", "Х", "Э", "OK"]]

	func _ready() -> void:
		size = Vector2(256, 288)

	func _draw() -> void:
		var f := ThemeDB.fallback_font
		draw_rect(Rect2(Vector2.ZERO, size), Color("141618"))
		# софт-клавиши, крестовина, зелёная и красная трубки
		draw_rect(Rect2(10, 10, 74, 30), Color("1e2125"))
		draw_rect(Rect2(172, 10, 74, 30), Color("1e2125"))
		draw_rect(Rect2(97, 6, 62, 52), Color("0e1012"))
		draw_rect(Rect2(97, 6, 62, 52), Color("2c3036"), false, 2.0)
		draw_rect(Rect2(115, 20, 26, 24), Color("16191c"))
		draw_rect(Rect2(115, 20, 26, 24), Color("3a3f46"), false, 1.0)
		draw_rect(Rect2(24, 48, 30, 8), Color("3fc35a"))
		draw_rect(Rect2(202, 48, 30, 8), Color("e2463b"))
		var kw := 22.0
		var kh := 46.0
		for r in ROWS.size():
			for c in ROWS[r].size():
				var k: String = ROWS[r][c]
				var rect := Rect2(6 + c * (kw + 3.2), 74 + r * (kh + 6), kw, kh)
				draw_rect(rect, Color("0c0d0f"))
				draw_rect(rect, Color("23262b"), false, 1.0)
				var lat := k.substr(0, 1) if k.length() == 2 else k
				draw_string(f, rect.position + Vector2(0, 20), lat, HORIZONTAL_ALIGNMENT_CENTER, kw, 14, Color("e6e7e9"))
				if k.length() == 2:
					draw_string(f, rect.position + Vector2(0, 40), k.substr(1, 1), HORIZONTAL_ALIGNMENT_CENTER, kw, 13, Color("c9a24a"))
