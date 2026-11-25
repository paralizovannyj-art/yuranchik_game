## Интерфейс во время игры: на экране только мир, прицел и затемнения. Ни реплик, ни подсказок «[E] …» нет.
## Цель, самочувствие и статистика — в телефоне Юрчика (phone.gd, Tab), инвентарь — сумка (inventory_ui.gd, I).
## Ранение показывают красная виньетка и сердцебиение, усталость — тяжёлое дыхание.
## Здесь же меню паузы, экран смерти и финальный экран. Весь интерфейс собирается кодом — уровень просто создаёт HUD.
class_name HUD
extends CanvasLayer

const W := 1280.0               ## сетка интерфейса = display/window/size/viewport_* (1280×720)
const H := 720.0
const C_TEXT := Color(0.86, 0.85, 0.80)
const C_ACCENT := Color(1.0, 0.62, 0.25)

var player: Player
var inventory: InventoryUI
var phone: Phone

var _root: Control
var _vignette: TextureRect
var _fade: ColorRect
var _title: Label
var _sub: Label
var _cross: Crosshair
var _menu: PanelContainer
var _menu_box: VBoxContainer
var _menu_kind := ""
var _flash := 0.0
var _last_hp := 100.0
var _beat := 0.0
var _breath := 0.0


func _ready() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build()
	Game.health_changed.connect(_on_health)
	_last_hp = Game.hp
	if player:
		player.died.connect(_on_died)
		phone = Phone.new()
		phone.player = player
		player.camera.add_child(phone)


static func make_theme() -> Theme:
	var t := Theme.new()
	t.default_font_size = 21
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.05, 0.055, 0.06, 0.88)
	sb.border_color = Color(0.30, 0.30, 0.32)
	sb.set_border_width_all(2)
	sb.set_content_margin_all(9)
	sb.content_margin_left = 27
	sb.content_margin_right = 27
	var sf := sb.duplicate() as StyleBoxFlat
	sf.bg_color = Color(0.50, 0.20, 0.07, 0.92)
	sf.border_color = C_ACCENT
	for s: String in ["normal", "disabled"]:
		t.set_stylebox(s, "Button", sb)
	for s: String in ["hover", "focus", "pressed"]:
		t.set_stylebox(s, "Button", sf)
	t.set_color("font_color", "Button", C_TEXT)
	t.set_color("font_hover_color", "Button", Color.WHITE)
	t.set_color("font_focus_color", "Button", Color.WHITE)
	var pn := StyleBoxFlat.new()
	pn.bg_color = Color(0.03, 0.035, 0.04, 0.9)
	pn.border_color = Color(0.25, 0.25, 0.27)
	pn.set_border_width_all(2)
	pn.set_content_margin_all(21)
	t.set_stylebox("panel", "PanelContainer", pn)
	return t


static func mk_label(parent: Control, text: String, font_size: int, color: Color, rect: Rect2,
		align := HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	var ls := LabelSettings.new()
	ls.font_size = font_size
	ls.font_color = color
	ls.outline_size = 6
	ls.outline_color = Color(0, 0, 0, 0.9)
	l.label_settings = ls
	l.position = rect.position
	l.size = rect.size
	l.horizontal_alignment = align
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l


func _rect(parent: Control, color: Color, r: Rect2) -> ColorRect:
	var c := ColorRect.new()
	c.color = color
	c.position = r.position
	c.size = r.size
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(c)
	return c


func _build() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.theme = make_theme()
	add_child(_root)

	# красная виньетка — урон и мало здоровья
	_vignette = TextureRect.new()
	var g := GradientTexture2D.new()
	g.gradient = Gradient.new()
	g.gradient.offsets = PackedFloat32Array([0.45, 1.0])
	g.gradient.colors = PackedColorArray([Color(0.6, 0, 0, 0), Color(0.55, 0, 0, 1)])
	g.fill = GradientTexture2D.FILL_RADIAL
	g.fill_from = Vector2(0.5, 0.5)
	g.fill_to = Vector2(1.0, 0.5)
	g.width = 64
	g.height = 64
	_vignette.texture = g
	_vignette.stretch_mode = TextureRect.STRETCH_SCALE
	_vignette.set_anchors_preset(Control.PRESET_FULL_RECT)
	_vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_vignette.modulate.a = 0.0
	_root.add_child(_vignette)

	_cross = Crosshair.new()
	_cross.position = Vector2.ZERO
	_cross.size = Vector2(W, H)
	_root.add_child(_cross)


	inventory = InventoryUI.new()
	inventory.hud = self
	_root.add_child(inventory)

	_fade = _rect(_root, Color(0, 0, 0, 1), Rect2(0, 0, W, H))
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_title = mk_label(_root, "", 45, Color(0.85, 0.1, 0.08), Rect2(0, 165, W, 66), HORIZONTAL_ALIGNMENT_CENTER)
	_sub = mk_label(_root, "", 20, C_TEXT, Rect2(W / 2 - 375, 240, 750, 165), HORIZONTAL_ALIGNMENT_CENTER)

	_menu = PanelContainer.new()
	_menu.visible = false
	_root.add_child(_menu)
	_menu_box = VBoxContainer.new()
	_menu_box.add_theme_constant_override("separation", 9)
	_menu.add_child(_menu_box)


func _process(delta: float) -> void:
	var paused := get_tree().paused
	# виньетка
	_flash = move_toward(_flash, 0.0, delta * 1.6)
	var low := clampf(1.0 - Game.hp / 35.0, 0.0, 1.0)
	var pulse := low * (0.30 + 0.18 * sin(Time.get_ticks_msec() * 0.006))
	_vignette.modulate.a = maxf(_flash, pulse)
	if player == null or not is_instance_valid(player):
		return
	if phone.is_open and (player.is_dead() or not player.control):
		phone.close()
	var playing := not paused and not player.is_dead() and _menu_kind == ""
	var free := playing and not phone.is_open
	_cross.alpha = move_toward(_cross.alpha, ((0.35 if player.move_speed > player.walk_speed * 1.3 else 1.0) if free else 0.0), delta * 5.0)
	_cross.step(delta, player.focus != null, player.is_aiming())
	# сердцебиение при малом здоровье, тяжёлое дыхание, когда выдохся
	if playing and low > 0.0:
		_beat -= delta
		if _beat <= 0.0:
			_beat = 1.0
			Game.sfx("heartbeat", null, -8.0 + low * 6.0, 0.0)
	if playing and player.exhausted:
		_breath -= delta
		if _breath <= 0.0:
			_breath = 0.85
			Game.sfx_rand("player_breath", 3, null, -4.0)
	else:
		_breath = 0.0


func _input(event: InputEvent) -> void:
	if phone and phone.is_open:
		_phone_input(event)
		return
	if event.is_action_pressed("pause"):
		if inventory.visible:
			close_inventory()
		elif _menu_kind == "pause":
			close_menu()
		elif _menu_kind == "" and _can_open():
			_open_pause()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("inventory"):
		if inventory.visible:
			close_inventory()
		elif _menu_kind == "" and _can_open():
			open_inventory()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("phone") and not inventory.visible and _menu_kind == "" and _can_open():
		phone.open()
		get_viewport().set_input_as_handled()


## Телефон в руке: листаем стрелками, крестовиной и колёсиком, WASD и стик продолжают вести Юрчика.
func _phone_input(event: InputEvent) -> void:
	var s := phone.screen
	var used := true
	if event is InputEventJoypadMotion or event is InputEventMouseMotion:
		return
	if event.is_action_pressed("phone") or event.is_action_pressed("pause"):
		phone.close()
	elif event.is_action_pressed("inventory") and event is InputEventKey:   # крестовина вниз листает телефон
		phone.close()
		if _can_open():
			open_inventory()
	elif event is InputEventMouseButton and event.pressed:
		match event.button_index:
			MOUSE_BUTTON_WHEEL_UP: s.scroll(-1)
			MOUSE_BUTTON_WHEEL_DOWN: s.scroll(1)
			MOUSE_BUTTON_LEFT: s.ok()
			MOUSE_BUTTON_RIGHT: _phone_back()
			_: used = false
	elif event.is_action_pressed("ui_up", true):
		s.move(Vector2i(0, -1))
	elif event.is_action_pressed("ui_down", true):
		s.move(Vector2i(0, 1))
	elif event.is_action_pressed("ui_left", true):
		s.move(Vector2i(-1, 0))
	elif event.is_action_pressed("ui_right", true):
		s.move(Vector2i(1, 0))
	elif event.is_action_pressed("interact") or event.is_action_pressed("ui_accept"):
		s.ok()
	elif (event is InputEventKey and event.pressed and event.keycode == KEY_BACKSPACE) \
			or (event is InputEventJoypadButton and event.pressed and event.button_index == JOY_BUTTON_B):
		_phone_back()
	elif event.is_action("move_forward") or event.is_action("move_back") or event.is_action("move_left") \
			or event.is_action("move_right") or event.is_action("flashlight") or event.is_action("look_left") \
			or event.is_action("look_right") or event.is_action("look_up") or event.is_action("look_down"):
		used = false                         # идти и светить фонариком с телефоном можно
	elif event is InputEventKey or event is InputEventJoypadButton or event is InputEventMouseButton:
		pass                                 # остальное (удар, бросок, бег, молоток) с телефоном в руке не работает
	else:
		used = false
	if used:
		get_viewport().set_input_as_handled()


func _phone_back() -> void:
	if not phone.screen.back():
		phone.screen.shortcut_messages()


func _can_open() -> bool:
	return player != null and not player.is_dead() and player.control and _fade.color.a < 0.5


# ----------------------------------------------------------------------------- здоровье
func _on_health() -> void:
	if Game.hp < _last_hp:
		_flash = clampf((_last_hp - Game.hp) / 25.0, 0.25, 0.8)
	_last_hp = Game.hp


# ----------------------------------------------------------------------------- затемнения
func fade_in(duration := 1.0) -> Tween:
	var tw := create_tween()
	tw.tween_property(_fade, "color:a", 0.0, duration)
	return tw


func fade_out(duration := 1.0, color := Color.BLACK, alpha := 1.0) -> Tween:
	_fade.color = Color(color.r, color.g, color.b, _fade.color.a)
	var tw := create_tween()
	tw.tween_property(_fade, "color:a", alpha, duration)
	return tw


# ----------------------------------------------------------------------------- инвентарь и меню
func open_inventory() -> void:
	get_tree().paused = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	Game.sfx("ui_open", null, -4.0)
	_look_into_bag(true)
	inventory.open()


func close_inventory() -> void:
	inventory.close()
	Game.sfx("ui_open", null, -8.0, 0.12)
	await _look_into_bag(false)
	if not inventory.visible:
		get_tree().paused = false
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


## Взгляд опускается в сумку и поднимается обратно. Игра на паузе, поэтому камерой крутит HUD,
## а после снятия паузы player.gd сам вернёт её на место (из того же положения — без рывка).
func _look_into_bag(down: bool) -> Signal:
	var tw := create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tw.set_pause_mode(Tween.TWEEN_PAUSE_PROCESS)
	if player and is_instance_valid(player):
		var pitch := deg_to_rad(-62.0) if down else player.cam_pitch
		tw.tween_property(player.cam_pivot, "rotation:x", pitch, 0.35 if down else 0.22)
	else:
		tw.tween_interval(0.01)
	return tw.finished


func _open_menu(kind: String, entries: Array) -> void:
	_menu_kind = kind
	for c: Node in _menu_box.get_children():
		c.queue_free()
	var first: Button = null
	for e: Array in entries:
		var b := Button.new()
		b.text = e[0]
		b.custom_minimum_size = Vector2(345, 0)
		b.pressed.connect(e[1])
		b.mouse_entered.connect(b.grab_focus)
		_menu_box.add_child(b)
		if first == null:
			first = b
	_menu.visible = true
	_menu.reset_size()
	_menu.position = Vector2(roundf((W - _menu.size.x) / 2.0), 450.0 if kind != "pause" else 300.0)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	first.grab_focus.call_deferred()


func close_menu() -> void:
	_menu.visible = false
	_menu_kind = ""
	_title.text = ""
	_sub.text = ""
	_fade.color.a = 0.0
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _open_pause() -> void:
	get_tree().paused = true
	_fade.color = Color(0, 0, 0, 0.55)
	_title.text = "ПАУЗА"
	_title.label_settings.font_color = C_TEXT
	_sub.text = ""
	_open_menu("pause", [
		["Продолжить", close_menu],
		["С последней точки", Game.restart_from_checkpoint],
		["В главное меню", Game.to_menu],
	])


func _on_died() -> void:
	if inventory.visible:
		close_inventory()
	Game.music("", 0.0, 1.0)
	await get_tree().create_timer(1.8).timeout
	Game.sfx("death_sting", null, -2.0, 0.0)
	await fade_out(1.6, Color(0.12, 0.0, 0.0), 0.86).finished
	_title.text = "ТЫ ПОГИБ"
	_title.label_settings.font_color = Color(0.85, 0.1, 0.08)
	_sub.text = "Паскот не прощает."
	_open_menu("dead", [
		["С последней точки", Game.restart_from_checkpoint],
		["В главное меню", Game.to_menu],
	])

