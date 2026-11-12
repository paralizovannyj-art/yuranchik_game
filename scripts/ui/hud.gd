## Интерфейс во время игры: здоровье и выносливость, подсказки, цель, реплики, прицел, шкала вырывания,
## затемнения экрана, а также меню паузы, экран смерти и финальный экран. Инвентарь — в inventory_ui.gd.
## Весь интерфейс собирается кодом (в сцене уровня его нет) — уровень просто создаёт HUD при запуске.
class_name HUD
extends CanvasLayer

const W := 854.0
const H := 480.0
const C_TEXT := Color(0.86, 0.85, 0.80)
const C_ACCENT := Color(1.0, 0.62, 0.25)

var player: Player
var inventory: InventoryUI

var _root: Control
var _vignette: TextureRect
var _fade: ColorRect
var _objective: Label
var _say: Label
var _prompt: Label
var _title: Label
var _sub: Label
var _cross: ColorRect
var _hp_fill: ColorRect
var _st_fill: ColorRect
var _hp_text: Label
var _throw_icon: TextureRect
var _throw_text: Label
var _grab_box: Control
var _grab_fill: ColorRect
var _menu: PanelContainer
var _menu_box: VBoxContainer
var _menu_kind := ""
var _say_t := 0.0
var _flash := 0.0
var _last_hp := 100.0
var _beat := 0.0
var _obj_t := 0.0


func _ready() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build()
	Game.said.connect(_on_said)
	Game.objective_changed.connect(_on_objective)
	Game.health_changed.connect(_on_health)
	Game.inventory_changed.connect(_refresh_throw)
	_last_hp = Game.hp
	_refresh_throw()
	if player:
		player.died.connect(_on_died)


static func make_theme() -> Theme:
	var t := Theme.new()
	t.default_font_size = 14
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.05, 0.055, 0.06, 0.88)
	sb.border_color = Color(0.30, 0.30, 0.32)
	sb.set_border_width_all(1)
	sb.set_content_margin_all(6)
	sb.content_margin_left = 18
	sb.content_margin_right = 18
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
	pn.set_border_width_all(1)
	pn.set_content_margin_all(14)
	t.set_stylebox("panel", "PanelContainer", pn)
	return t


static func mk_label(parent: Control, text: String, font_size: int, color: Color, rect: Rect2,
		align := HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	var ls := LabelSettings.new()
	ls.font_size = font_size
	ls.font_color = color
	ls.outline_size = 4
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

	_cross = _rect(_root, Color(1, 1, 1, 0.75), Rect2(W / 2 - 1.5, H / 2 - 1.5, 3, 3))

	mk_label(_root, "ЦЕЛЬ", 10, C_ACCENT, Rect2(18, 12, 200, 14))
	_objective = mk_label(_root, "", 13, C_TEXT, Rect2(18, 25, 380, 40))
	_prompt = mk_label(_root, "", 14, Color.WHITE, Rect2(W / 2 - 250, 350, 500, 20), HORIZONTAL_ALIGNMENT_CENTER)
	_say = mk_label(_root, "", 14, C_TEXT, Rect2(W / 2 - 310, 384, 620, 60), HORIZONTAL_ALIGNMENT_CENTER)

	# здоровье и выносливость
	_rect(_root, Color(0, 0, 0, 0.6), Rect2(17, 447, 122, 9))
	_hp_fill = _rect(_root, Color(0.3, 0.75, 0.3), Rect2(18, 448, 120, 7))
	_rect(_root, Color(0, 0, 0, 0.6), Rect2(17, 458, 122, 5))
	_st_fill = _rect(_root, Color(0.75, 0.78, 0.85), Rect2(18, 459, 120, 3))
	_hp_text = mk_label(_root, "НОРМА", 10, Color(0.5, 0.9, 0.5), Rect2(18, 432, 160, 14))

	# что полетит при броске
	_throw_icon = TextureRect.new()
	_throw_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_throw_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_throw_icon.position = Vector2(W - 96, 420)
	_throw_icon.size = Vector2(44, 44)
	_throw_icon.modulate = Color(1.5, 1.5, 1.5)
	_throw_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_throw_icon)
	_throw_text = mk_label(_root, "", 12, C_TEXT, Rect2(W - 54, 440, 50, 20))

	# вырывание из захвата
	_grab_box = Control.new()
	_grab_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_grab_box)
	mk_label(_grab_box, "ВЫРЫВАЙСЯ!   ЖМИ  [E]", 18, Color(1, 0.85, 0.3), Rect2(W / 2 - 200, 268, 400, 26), HORIZONTAL_ALIGNMENT_CENTER)
	_rect(_grab_box, Color(0, 0, 0, 0.7), Rect2(W / 2 - 91, 299, 182, 10))
	_grab_fill = _rect(_grab_box, Color(1, 0.75, 0.2), Rect2(W / 2 - 90, 300, 180, 8))
	_grab_box.visible = false

	inventory = InventoryUI.new()
	inventory.hud = self
	_root.add_child(inventory)

	_fade = _rect(_root, Color(0, 0, 0, 1), Rect2(0, 0, W, H))
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_title = mk_label(_root, "", 30, Color(0.85, 0.1, 0.08), Rect2(0, 110, W, 44), HORIZONTAL_ALIGNMENT_CENTER)
	_sub = mk_label(_root, "", 13, C_TEXT, Rect2(W / 2 - 250, 160, 500, 110), HORIZONTAL_ALIGNMENT_CENTER)

	_menu = PanelContainer.new()
	_menu.visible = false
	_root.add_child(_menu)
	_menu_box = VBoxContainer.new()
	_menu_box.add_theme_constant_override("separation", 6)
	_menu.add_child(_menu_box)


func _process(delta: float) -> void:
	var paused := get_tree().paused
	# реплика
	if _say_t > 0.0 and not paused:
		_say_t -= delta
		_say.modulate.a = clampf(_say_t / 0.6, 0.0, 1.0)
	_obj_t = maxf(_obj_t - delta, 0.0)
	_objective.label_settings.font_color = C_TEXT.lerp(C_ACCENT, clampf(_obj_t / 2.0, 0.0, 1.0))
	# виньетка
	_flash = move_toward(_flash, 0.0, delta * 1.6)
	var low := clampf(1.0 - Game.hp / 35.0, 0.0, 1.0)
	var pulse := low * (0.30 + 0.18 * sin(Time.get_ticks_msec() * 0.006))
	_vignette.modulate.a = maxf(_flash, pulse)
	if player == null or not is_instance_valid(player):
		return
	var k := Game.hp / Game.MAX_HP
	_hp_fill.size.x = 120.0 * k
	var col := Color(0.3, 0.75, 0.3) if k > 0.6 else (Color(0.9, 0.75, 0.2) if k > 0.3 else Color(0.9, 0.2, 0.15))
	_hp_fill.color = col
	_hp_text.text = "НОРМА" if k > 0.6 else ("РАНЕН" if k > 0.3 else "ПРИ СМЕРТИ")
	_hp_text.label_settings.font_color = col.lightened(0.2)
	_st_fill.size.x = 120.0 * player.stamina / player.max_stamina
	_st_fill.color = Color(0.9, 0.3, 0.2) if player.exhausted else Color(0.75, 0.78, 0.85)
	var playing := not paused and not player.is_dead() and _menu_kind == ""
	_cross.visible = playing and player.is_aiming()
	_prompt.text = "[E]  %s" % player.focus.prompt if playing and player.focus else ""
	_grab_box.visible = playing and player.state == Player.State.GRABBED
	_grab_fill.size.x = 180.0 * clampf(player.escape, 0.0, 1.0)
	# сердцебиение при малом здоровье
	if playing and low > 0.0:
		_beat -= delta
		if _beat <= 0.0:
			_beat = 1.0
			Game.sfx("heartbeat", null, -8.0 + low * 6.0, 0.0)


func _input(event: InputEvent) -> void:
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


func _can_open() -> bool:
	return player != null and not player.is_dead() and player.control and _fade.color.a < 0.5


# ----------------------------------------------------------------------------- сообщения
func _on_said(text: String) -> void:
	_say.text = text
	_say.modulate.a = 1.0
	_say_t = 2.5 + text.length() * 0.06


func _on_objective(text: String) -> void:
	if text == _objective.text:
		return
	_objective.text = text
	_obj_t = 3.0
	Game.sfx("ui_select", null, -10.0)


func _on_health() -> void:
	if Game.hp < _last_hp:
		_flash = clampf((_last_hp - Game.hp) / 25.0, 0.25, 0.8)
	_last_hp = Game.hp


func _refresh_throw() -> void:
	var id := Game.current_throwable()
	_throw_icon.visible = id != ""
	_throw_text.text = "×%d [G]" % Game.count(id) if id != "" else ""
	if id != "":
		_throw_icon.texture = load("res://assets/ui/icons/%s.png" % id)


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
	inventory.open()


func close_inventory() -> void:
	inventory.close()
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _open_menu(kind: String, entries: Array) -> void:
	_menu_kind = kind
	for c: Node in _menu_box.get_children():
		c.queue_free()
	var first: Button = null
	for e: Array in entries:
		var b := Button.new()
		b.text = e[0]
		b.custom_minimum_size = Vector2(230, 0)
		b.pressed.connect(e[1])
		b.mouse_entered.connect(b.grab_focus)
		_menu_box.add_child(b)
		if first == null:
			first = b
	_menu.visible = true
	_menu.reset_size()
	_menu.position = Vector2((W - 266.0) / 2.0, 300.0 if kind != "pause" else 200.0)
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


## Финальный экран демо-версии.
func show_ending() -> void:
	if player:
		player.control = false
	Game.in_game = false
	await fade_out(2.5).finished
	Game.sfx("win", null, -4.0, 0.0)
	var t := int(Game.stats["time"])
	_title.text = "ДОМА"
	_title.label_settings.font_color = C_TEXT
	_sub.text = "Сегодня ты добрался. Но он знает, где ты живёшь.\n\nВремя: %d:%02d     Офников уложено: %d     Смертей: %d\n\nКонец демо-версии. Продолжение следует." % [
		t / 60, t % 60, Game.stats["kills"], Game.stats["deaths"]]
	_open_menu("end", [
		["Сыграть ещё раз", Game.new_game],
		["В главное меню", Game.to_menu],
	])
