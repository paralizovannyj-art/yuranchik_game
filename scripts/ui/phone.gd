## Телефон Юрчика — Nokia X2-00 (кнопочный QWERTY-брусок), который он поднимает перед собой (Tab).
## Модель — assets/models/phone.gltf (tools/blender/build_phone.py). Экран — SubViewport с PhoneScreen,
## «печать» лица и спины (буквы, иконки, надписи, шов крышки) — второй SubViewport, нарисованный один раз
## по phone_layout.json. Висит на камере игрока; мир за ним размывается (DOF).
## Пауза не ставится: пока телефон в руке, Юрчик идёт шагом, не бьёт и не бегает (player.phone_up).
class_name Phone
extends Node3D

const MODEL := preload("res://assets/models/phone.gltf")
const LAYOUT := preload("res://assets/models/phone_layout.json")
## Левая рука в вязаной перчатке без пальцев, держит телефон (tools/blender/build_phone_hand.py) — в тех же координатах.
const HAND := preload("res://assets/models/phone_hand.gltf")
const SCALE := 1.6                               ## крупнее настоящего, чтобы экран читался на 854×480
const OPEN_POS := Vector3(0.03, -0.042, -0.185)   ## подальше: в кадре весь телефон и рука, как на фото
const CLOSED_POS := Vector3(0.05, -0.2, -0.12)
## Отдельный слой: фонарик в голове (player.tscn) телефон не освещает, иначе экран засвечивается.
const LAYER := 1 << 18
## Рука — свой слой: фонарик её тоже не трогает (в упор пересвечивает), а подсветка экрана — освещает.
const HAND_LAYER := 1 << 19
const OPEN_ROT := Vector3(deg_to_rad(10.0), deg_to_rad(-10.0), deg_to_rad(-8.0))
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
var _hand_light: OmniLight3D
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
	var hand: Node3D = HAND.instantiate()
	add_child(hand)
	for mi: MeshInstance3D in hand.find_children("*", "MeshInstance3D", true, false):
		mi.layers = HAND_LAYER
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if player:
		player.flashlight.light_cull_mask &= ~(LAYER | HAND_LAYER)
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
	# спина: тот же лист печати (правая половина), матовый пластик
	var bm := StandardMaterial3D.new()
	bm.albedo_texture = _print_vp.get_texture()
	bm.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	bm.roughness = 0.6
	for mi: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for i in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(i)
			match mat.resource_name if mat else "":
				"PhScreen": mi.set_surface_override_material(i, sm)
				"PhPrint": mi.set_surface_override_material(i, pm)
				"PhBackPrint": mi.set_surface_override_material(i, bm)
	# экран подсвечивает лицо и руки голубым
	_light = OmniLight3D.new()
	_light.light_color = Color("9fd0c8")
	_light.light_energy = 0.0
	_light.omni_range = 0.45
	_light.omni_attenuation = 1.6
	_light.position = Vector3(0, 0.025, 0.03)
	_light.light_cull_mask = ~(LAYER | HAND_LAYER)   # светит на лицо, но не на сам телефон
	add_child(_light)
	# руку в упор подсвечивает отдельный слабый свет спереди, иначе пальцы у экрана пересвечены
	_hand_light = OmniLight3D.new()
	_hand_light.light_color = Color("c8d8d0")
	_hand_light.light_energy = 0.0
	_hand_light.omni_range = 0.6
	_hand_light.omni_attenuation = 1.0
	_hand_light.position = Vector3(0, 0.03, 0.12)
	_hand_light.light_cull_mask = HAND_LAYER
	add_child(_hand_light)


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
	_tween.tween_property(_hand_light, "light_energy", light * 0.13, ANIM)
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


## «Печать» корпуса: лист 2W×H, слева лицо (фон панели, динамик, NOKIA, буквы на клавишах, иконки),
## справа спина (шов крышки, камера, VGA, решётка динамика, NOKIA). Рисуется один раз в SubViewport;
## UV модели — плоская проекция (1 мм = PX_MM пикселей), координаты в phone_layout.json — мм от левого верхнего угла.
class PhonePrint extends Control:
	const PX_MM := 10.0
	const PANEL := Color("08090a")
	const BACK := Color("141517")
	const KEY := Color("101113")
	const WHITE := Color("eceef0")
	const GRAY := Color("8a8d92")
	const SILVER := Color("9a9ea4")
	var layout: Dictionary
	var _bold: FontVariation

	func layout_size() -> Vector2:
		return Vector2(layout["size"][0] * 2.0, layout["size"][1])

	func _ready() -> void:
		size = layout_size() * PX_MM
		_bold = FontVariation.new()
		_bold.base_font = ThemeDB.fallback_font
		_bold.variation_embolden = 1.1
		_bold.spacing_glyph = 2

	func _r(a: Array, ox := 0.0) -> Rect2:
		return Rect2(Vector2(a[0] + ox, a[1]) * PX_MM, Vector2(a[2] - a[0], a[3] - a[1]) * PX_MM)

	func _sb(col: Color, radius: float, border := Color.TRANSPARENT, bw := 0) -> StyleBoxFlat:
		var s := StyleBoxFlat.new()
		s.bg_color = col
		s.set_corner_radius_all(int(radius))
		s.border_color = border
		s.set_border_width_all(bw)
		s.anti_aliasing = true
		return s

	## Текст по центру прямоугольника (по вертикали — по высоте прописных).
	func _center(f: Font, r: Rect2, text: String, fs: int, col: Color) -> void:
		var base := r.position.y + r.size.y / 2.0 + f.get_ascent(fs) * 0.36
		draw_string(f, Vector2(r.position.x, base), text, HORIZONTAL_ALIGNMENT_CENTER, r.size.x, fs, col)

	func _draw() -> void:
		var f := ThemeDB.fallback_font
		var w: float = layout["size"][0]
		draw_rect(Rect2(Vector2.ZERO, Vector2(w * PX_MM, size.y)), PANEL)
		draw_rect(Rect2(Vector2(w * PX_MM, 0), Vector2(w * PX_MM, size.y)), BACK)
		for it: Dictionary in layout["front"]:
			_front(f, it)
		for it: Dictionary in layout["back"]:
			_back(f, it, _r(it.rect, w))

	# ------------------------------------------------------------------ лицо
	func _front(f: Font, it: Dictionary) -> void:
		var r := _r(it.rect)
		var c := r.get_center()
		match it.kind as String:
			"screen":
				draw_style_box(_sb(Color("121417"), 6), r.grow(5))
				draw_rect(r, Color.BLACK)
			"earpiece":
				draw_style_box(_sb(Color("a5121b"), r.size.y / 2.0), r)
				draw_line(r.position + Vector2(6, 3), r.end - Vector2(6, r.size.y - 3), Color("d23a40"), 1.0)
			"brand":
				_center(_bold, r, "NOKIA", 30, SILVER)
			"model":
				_center(f, r, "X2", 15, GRAY)
			"mic":
				draw_circle(c, 4.0, Color("020202"))
			"lsk", "rsk":
				draw_style_box(_sb(KEY, 14), r)
				_gloss(r)
				var top := Vector2(c.x, r.position.y + r.size.y * 0.27)
				draw_line(top - Vector2(15, 0), top + Vector2(15, 0), WHITE, 3.0)
				var bot := Vector2(c.x, r.position.y + r.size.y * 0.76)
				if it.kind == "lsk":
					_handset(bot, Color("3fbf55"))
				else:
					_handset(bot, Color("e3383a"))
					draw_arc(bot + Vector2(0, 5), 4.5, -PI * 0.3, PI * 1.3, 10, Color("e3383a"), 1.8)
					draw_line(bot + Vector2(0, -1), bot + Vector2(0, 5), Color("e3383a"), 1.8)
			"mid":
				draw_style_box(_sb(KEY, 10), r)
				_gloss(r)
				_music(Vector2(r.position.x + 44, c.y + 6))
				_mail(Vector2(r.end.x - 45, c.y + 6))
			"dpad":
				draw_style_box(_sb(Color("0c0d0f"), 38, Color("7d8187"), 3), r)
				draw_style_box(_sb(Color.TRANSPARENT, 34, Color("2c2f34"), 2), r.grow(-5))
			"dpad_c":
				draw_style_box(_sb(Color("050607"), 22, Color("1d2024"), 2), r)
				draw_rect(Rect2(r.position + Vector2(10, 6), Vector2(r.size.x - 20, 6)), Color(1, 1, 1, 0.06))
			_:
				_key(f, it, r, c)

	func _gloss(r: Rect2) -> void:
		draw_rect(Rect2(r.position + Vector2(6, 3), Vector2(r.size.x - 12, r.size.y * 0.3)), Color(1, 1, 1, 0.018))

	func _key(f: Font, it: Dictionary, r: Rect2, c: Vector2) -> void:
		draw_style_box(_sb(KEY, 8, Color("1e2024"), 1), r)
		_gloss(r)
		var p := r.position
		var bottom := r.end.y - 14
		match it.kind as String:
			"key":
				var lat: String = it.lat
				var sym: String = it.sym
				if lat != "":
					draw_string(f, p + Vector2(7, 26), lat, HORIZONTAL_ALIGNMENT_LEFT, -1, 23, WHITE)
					var sc := GRAY if sym in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "#"] else WHITE
					draw_string(f, p + Vector2(27, 25), sym, HORIZONTAL_ALIGNMENT_LEFT, -1, 19, sc)
				else:
					draw_string(f, p + Vector2(14, 26), sym, HORIZONTAL_ALIGNMENT_LEFT, -1, 21, WHITE)
				draw_string(f, p + Vector2(7, 57), it.cyr, HORIZONTAL_ALIGNMENT_LEFT, -1, 23, WHITE)
			"back":
				var b := c + Vector2(2, -2)
				draw_polyline(PackedVector2Array([b + Vector2(-14, 0), b + Vector2(-7, -7), b + Vector2(12, -7),
					b + Vector2(12, 7), b + Vector2(-7, 7), b + Vector2(-14, 0)]), WHITE, 2.0)
				draw_line(b + Vector2(-2, -3), b + Vector2(5, 3), WHITE, 2.0)
				draw_line(b + Vector2(-2, 3), b + Vector2(5, -3), WHITE, 2.0)
			"enter":
				var e := c + Vector2(2, -2)
				draw_polyline(PackedVector2Array([e + Vector2(12, -9), e + Vector2(12, 5), e + Vector2(-11, 5)]), WHITE, 3.0)
				draw_colored_polygon(PackedVector2Array([e + Vector2(-15, 5), e + Vector2(-7, -1), e + Vector2(-7, 11)]), WHITE)
			"fn":
				var a := p + Vector2(16, 20)
				draw_line(a + Vector2(-6, 6), a + Vector2(6, -6), WHITE, 2.5)
				draw_colored_polygon(PackedVector2Array([a + Vector2(8, -8), a + Vector2(-2, -8), a + Vector2(8, 2)]), WHITE)
			"shift":
				var s := Vector2(c.x, bottom - 6)
				draw_polyline(PackedVector2Array([s + Vector2(0, -12), s + Vector2(11, 0), s + Vector2(5, 0), s + Vector2(5, 9),
					s + Vector2(-5, 9), s + Vector2(-5, 0), s + Vector2(-11, 0), s + Vector2(0, -12)]), WHITE, 2.0)
			"sym":
				draw_string(f, Vector2(p.x, bottom), "Sym", HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 17, WHITE)
			"space":
				var sp := Vector2(c.x, bottom - 4)
				draw_polyline(PackedVector2Array([sp + Vector2(-17, -6), sp + Vector2(-17, 2), sp + Vector2(17, 2), sp + Vector2(17, -6)]), WHITE, 3.0)
			"comma", "period":
				draw_string(f, p + Vector2(28, 30), "?" if it.kind == "comma" else ":", HORIZONTAL_ALIGNMENT_LEFT, -1, 20, WHITE)
				draw_string(f, Vector2(p.x, bottom + 2), "," if it.kind == "comma" else ".", HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 26, WHITE)
			"ctrl":
				draw_string(f, p + Vector2(12, 30), "з", HORIZONTAL_ALIGNMENT_LEFT, -1, 19, WHITE)
				var q := p + Vector2(31, 24)
				draw_line(q + Vector2(-5, 5), q + Vector2(5, -6), WHITE, 2.5)
				draw_string(f, Vector2(p.x, bottom), "Ctrl", HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 17, WHITE)

	## Трубка: дуга с утолщениями на концах.
	func _handset(c: Vector2, col: Color) -> void:
		var o := c + Vector2(0, 12)
		draw_arc(o, 13.0, PI * 1.15, PI * 1.85, 12, col, 4.0)
		for a: float in [PI * 1.15, PI * 1.85]:
			draw_circle(o + Vector2.from_angle(a) * 13.0, 3.2, col)

	func _music(c: Vector2) -> void:
		var col := Color("b9bcc1")
		draw_circle(c + Vector2(-8, 6), 4.0, col)
		draw_circle(c + Vector2(4, 4), 4.0, col)
		draw_line(c + Vector2(-4.5, 6), c + Vector2(-4.5, -10), col, 2.0)
		draw_line(c + Vector2(7.5, 4), c + Vector2(7.5, -12), col, 2.0)
		draw_line(c + Vector2(-4.5, -10), c + Vector2(7.5, -12), col, 3.0)
		draw_arc(c + Vector2(10, -1), 6.0, -PI * 0.5, PI * 0.5, 8, col, 1.5)

	func _mail(c: Vector2) -> void:
		var col := Color("b9bcc1")
		var e := Rect2(c - Vector2(11, 7), Vector2(22, 14))
		draw_rect(e, col, false, 2.0)
		draw_polyline(PackedVector2Array([e.position, c + Vector2(0, 1), e.position + Vector2(22, 0)]), col, 2.0)

	# ------------------------------------------------------------------ спина
	func _back(f: Font, it: Dictionary, r: Rect2) -> void:
		var c := r.get_center()
		match it.kind as String:
			"cover":
				draw_style_box(_sb(Color.TRANSPARENT, 26, Color("040405"), 2), r)
				draw_style_box(_sb(Color.TRANSPARENT, 26, Color("26282c"), 1), r.grow(1.5))
			"camera":
				draw_style_box(_sb(Color("040506"), 20), r)
				draw_circle(c, 24.0, Color("1e2228"))
				draw_circle(c, 19.0, Color("0a1626"))
				draw_circle(c, 11.0, Color("10243f"))
				draw_circle(c + Vector2(-6, -6), 4.0, Color(1, 1, 1, 0.35))
			"vga":
				_center(f, r, "VGA", 24, GRAY)
			"grille":
				for g: float in [0.0, 0.62]:
					for row in 3:
						for col in 9:
							var d := r.position + Vector2(8 + col * 13.0, 10 + g * r.size.y + row * 12.0)
							draw_circle(d, 3.6, Color("030304"))
							draw_circle(d + Vector2(0, 1.5), 2.0, Color("2a2c30", 0.4))
			"brand":
				_center(_bold, r, "NOKIA", 38, Color("8e9196"))
