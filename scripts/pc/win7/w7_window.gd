## Окно Windows 7 (Aero): стеклянная рамка, заголовок с ореолом, кнопки «свернуть / развернуть / закрыть».
## Таскается за заголовок, двойной щелчок по нему разворачивает. Содержимое — client (любой Control).
class_name W7Window
extends Control

signal closed(win: W7Window)

const B := 8.0             ## толщина рамки
const CAP := 30.0          ## высота заголовка вместе с верхней рамкой
const BTN_H := 19.0
const CLOSE_W := 43.0
const BTN_W := 26.0

var desktop: Control       ## PcDesktop
var app_id := ""           ## программа (для кнопки на панели задач)
var title := ""
var icon_name := ""
var show_title := true
var has_min := true
var has_max := true
var client: Control
var active := false
var maximized := false
var minimized := false
var modal_for: W7Window    ## окно-диалог: пока открыт, родитель не принимает щелчки
var normal_rect := Rect2()
var min_size := Vector2(240, 140)
var client_top := CAP     ## где начинается содержимое (у Chrome вкладки заходят в заголовок)
var drag_h := CAP          ## высота полосы, за которую таскают окно
var glass_top := 0.0       ## сколько верха содержимого — тоже стекло (Проводник, вкладки Chrome)

var _glass: Control
var _deco: Control
var _hover := ""
var _press := ""
var _drag := false
var _drag_off := Vector2.ZERO
var _drag_from := Vector2.ZERO
var _flash := 0.0          ## мигание рамки (щёлкнули мимо диалога)


func setup(p_title: String, p_icon: String, p_size: Vector2, p_client: Control) -> W7Window:
	title = p_title
	icon_name = p_icon
	size = p_size
	client = p_client
	return self


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_glass = W7.glass_layer(self, _draw_glass)
	if client:
		client.name = "Client"
		add_child(client)
		client.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		client.offset_left = B
		client.offset_top = client_top
		client.offset_right = -B
		client.offset_bottom = -B
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	resized.connect(_redraw)
	mouse_exited.connect(func() -> void:
		_hover = ""
		_redraw())


func _redraw() -> void:
	if _glass:
		_glass.queue_redraw()
	if _deco:
		_deco.queue_redraw()


func set_active(on: bool) -> void:
	if active != on:
		active = on
		_redraw()


func set_title(t: String) -> void:
	title = t
	_redraw()
	if desktop:
		desktop.call("refresh_taskbar")


## Мигнуть рамкой (Windows так показывает, что сейчас главное — этот диалог).
func flash() -> void:
	var tw := create_tween()
	for i in 3:
		tw.tween_callback(func() -> void:
			_flash = 1.0
			_redraw())
		tw.tween_interval(0.07)
		tw.tween_callback(func() -> void:
			_flash = 0.0
			_redraw())
		tw.tween_interval(0.07)


# ---------- рисование ----------

func _frame_rect() -> Rect2:
	return Rect2(Vector2.ZERO, size)


func _client_rect() -> Rect2:
	return Rect2(B, client_top, size.x - B * 2.0, size.y - client_top - B)


func _draw_glass(g: Control) -> void:
	var ci := g.get_canvas_item()
	var r := _frame_rect()
	var radii := Vector4(6, 6, 4, 4) if not maximized else Vector4.ZERO
	var lit := active or _flash > 0.0
	var stops: Array = [[0.0, Color(0.50, 0.70, 0.90, 0.50)], [1.0, Color(0.38, 0.58, 0.80, 0.50)]] if lit \
			else [[0.0, Color(0.80, 0.87, 0.94, 0.62)], [1.0, Color(0.74, 0.82, 0.90, 0.62)]]
	W7.fill(ci, r, radii, stops)
	# блики на стекле: пара косых светлых полос
	var outline := W7.rounded(r, radii)
	for s: Array in [[0.18, 70.0, 0.10], [0.55, 40.0, 0.07], [0.8, 90.0, 0.06]]:
		var x0: float = r.size.x * s[0]
		var w: float = s[1]
		var band := PackedVector2Array([Vector2(x0, 0), Vector2(x0 + w, 0), Vector2(x0 + w - r.size.y * 0.6, r.size.y),
				Vector2(x0 - r.size.y * 0.6, r.size.y)])
		for poly: PackedVector2Array in Geometry2D.intersect_polygons(outline, band):
			g.draw_colored_polygon(poly, Color(1, 1, 1, s[2]))
	W7.stroke(ci, r.grow(-1), radii - Vector4.ONE, Color(1, 1, 1, 0.55 if lit else 0.7))
	W7.stroke(ci, r, radii, Color(0, 0, 0, 0.6 if lit else 0.45))
	# рамка вокруг содержимого
	var c := _client_rect()
	c.position.y += glass_top
	c.size.y -= glass_top
	g.draw_rect(c.grow(1), Color(1, 1, 1, 0.55), false, 1.0)
	g.draw_rect(c.grow(0.5), Color(0, 0, 0, 0.45), false, 1.0)


func _btn_rects() -> Dictionary:
	var d := {}
	var x := size.x - 7.0 - (3.0 if maximized else 0.0)
	var y := 1.0 + (B if maximized else 0.0)
	x -= CLOSE_W if has_max or has_min else 32.0
	d["close"] = Rect2(x, y, CLOSE_W if has_max or has_min else 32.0, BTN_H)
	if has_max:
		x -= BTN_W
		d["max"] = Rect2(x, y, BTN_W, BTN_H)
	if has_min:
		x -= BTN_W
		d["min"] = Rect2(x, y, BTN_W, BTN_H)
	return d


func _draw_deco() -> void:
	var ci := _deco.get_canvas_item()
	var lit := active or _flash > 0.0
	var top := B if maximized else 0.0
	# заголовок
	var tx := B + 2.0
	if show_title and icon_name != "":
		var ic := W7.icon(icon_name, 16)
		if ic:
			_deco.draw_texture_rect(ic, Rect2(tx, top + 7.0, 16, 16), false)
		tx += 22.0
	if show_title and title != "":
		var btns := _btn_rects()
		var left: float = btns[btns.keys()[-1]].position.x - tx - 8.0
		var t := title
		while t.length() > 3 and W7.text_width(t) > left:
			t = t.substr(0, t.length() - 4) + "..."
		W7.glow_text(_deco, Vector2(tx, top + 20.0), t, 12, Color(0, 0, 0, 1.0 if lit else 0.75), Color(1, 1, 1, 0.9))
	# кнопки
	var rects := _btn_rects()
	var keys: Array = rects.keys()
	for k: String in keys:
		var r: Rect2 = rects[k]
		var first: bool = k == keys[-1]
		var last: bool = k == "close"
		var radii := Vector4(0, 0, 4.0 if last else 0.0, 4.0 if first else 0.0)
		var st: Array
		var state := "press" if _press == k and _hover == k else ("hover" if _hover == k and _press == "" else "")
		if k == "close" and (lit or state != ""):
			match state:
				"hover": st = [[0.0, "f4b6a5"], [0.5, "ea7b65"], [0.5, "e3401f"], [1.0, "f3a273"]]
				"press": st = [[0.0, "c68a7d"], [0.5, "a64535"], [0.5, "8d1b06"], [1.0, "c35f3e"]]
				_: st = [[0.0, "e5a596"], [0.5, "cf6d5c"], [0.5, "c0402b"], [1.0, "d47b5e"]]
		else:
			match state:
				"hover": st = [[0.0, "c3e6fa"], [0.5, "82c6ef"], [0.5, "3a9bdb"], [1.0, "61cff2"]]
				"press": st = [[0.0, "a7c7e2"], [0.5, "5c8ec1"], [0.5, "215c93"], [1.0, "37a0ce"]]
				_: st = [[0.0, Color(1, 1, 1, 0.42)], [0.5, Color(1, 1, 1, 0.22)], [0.5, Color(1, 1, 1, 0.08)], [1.0, Color(1, 1, 1, 0.25)]]
		W7.fill(ci, r, radii, st)
		W7.stroke(ci, r.grow(-1), radii, Color(1, 1, 1, 0.45))
		W7.stroke(ci, r, radii, Color(0, 0, 0, 0.55))
		_glyph(k, r.get_center())


func _glyph(k: String, c: Vector2) -> void:
	var dark := Color(0, 0, 0, 0.7)
	match k:
		"close":
			for w: Array in [[4.0, dark], [2.2, Color.WHITE]]:
				_deco.draw_line(c + Vector2(-5, -4), c + Vector2(5, 4), w[1], w[0], true)
				_deco.draw_line(c + Vector2(-5, 4), c + Vector2(5, -4), w[1], w[0], true)
		"min":
			var r := Rect2(c + Vector2(-4.5, 2), Vector2(9, 3))
			_deco.draw_rect(r.grow(1), dark)
			_deco.draw_rect(r, Color.WHITE)
		"max":
			if maximized:
				_max_glyph(Rect2(c + Vector2(-2, -5), Vector2(7, 6)))
				_max_glyph(Rect2(c + Vector2(-5, -2), Vector2(7, 6)))
			else:
				_max_glyph(Rect2(c + Vector2(-5, -4), Vector2(10, 8)))


func _max_glyph(r: Rect2) -> void:
	_deco.draw_rect(r.grow(1), Color(0, 0, 0, 0.7))
	_deco.draw_rect(r, Color.WHITE)
	_deco.draw_rect(Rect2(r.position + Vector2(1, 2.5), r.size - Vector2(2, 3.5)), Color(0.35, 0.55, 0.75))


# ---------- мышь ----------

func _btn_at(p: Vector2) -> String:
	var rects := _btn_rects()
	for k: String in rects:
		if (rects[k] as Rect2).has_point(p):
			return k
	return ""


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var mm := event as InputEventMouseMotion
		if _drag:
			_drag_to(mm.global_position)
			return
		var h := _btn_at(mm.position)
		if h != _hover:
			_hover = h
			_deco.queue_redraw()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		var mb := event as InputEventMouseButton
		if mb.pressed:
			var b := _btn_at(mb.position)
			if b != "":
				_press = b
				_deco.queue_redraw()
			elif mb.position.y < drag_h + (B if maximized else 0.0):
				if mb.double_click and has_max:
					toggle_max()
				else:
					_drag = true
					_drag_from = mb.global_position
					_drag_off = mb.global_position - position
		else:
			_drag = false
			if _press != "":
				var b := _btn_at(mb.position)
				var was := _press
				_press = ""
				_deco.queue_redraw()
				if b == was:
					match b:
						"close": request_close()
						"min": minimize()
						"max": toggle_max()
		accept_event()


func _drag_to(gp: Vector2) -> void:
	if maximized:
		if gp.distance_to(_drag_from) < 5.0:
			return
		var fx := (gp.x - position.x) / maxf(size.x, 1.0)
		toggle_max(false)
		_drag_off = Vector2(size.x * fx, _drag_off.y - B)
	var area: Rect2 = desktop.call("work_area")
	var p := gp - _drag_off
	p.x = clampf(p.x, 60.0 - size.x, area.size.x - 60.0)
	p.y = clampf(p.y, 0.0, area.size.y - CAP)
	position = p


# ---------- состояния ----------

func toggle_max(animate := true) -> void:
	if not has_max:
		return
	var area: Rect2 = desktop.call("work_area")
	var target: Rect2
	if maximized:
		maximized = false
		target = normal_rect
	else:
		normal_rect = Rect2(position, size)
		maximized = true
		target = area.grow(B)
	if animate:
		var tw := create_tween().set_parallel().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tw.tween_property(self, "position", target.position, 0.15)
		tw.tween_property(self, "size", target.size, 0.15)
	else:
		position = target.position
		size = target.size
	_relayout()


func _relayout() -> void:
	_redraw()


func minimize() -> void:
	if minimized or not has_min:
		return
	minimized = true
	if desktop:
		desktop.call("on_window_minimized", self)
	var target: Vector2 = desktop.call("taskbar_point", self) if desktop else position
	_saved_pos = position
	pivot_offset = size * 0.5
	var tw := create_tween().set_parallel().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tw.tween_property(self, "scale", Vector2(0.3, 0.3), 0.2)
	tw.tween_property(self, "modulate:a", 0.0, 0.2)
	tw.tween_property(self, "position", target - size * 0.5, 0.2)
	await tw.finished
	if minimized:
		visible = false


var _saved_pos := Vector2.ZERO


func restore() -> void:
	if not minimized:
		return
	minimized = false
	visible = true
	var tw := create_tween().set_parallel().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(self, "scale", Vector2.ONE, 0.2)
	tw.tween_property(self, "modulate:a", 1.0, 0.2)
	tw.tween_property(self, "position", _saved_pos, 0.2)


## Появиться: Windows 7 открывает окно, чуть увеличивая его из 90 % с проявлением.
func pop_in() -> void:
	pivot_offset = size * 0.5
	scale = Vector2(0.92, 0.92)
	modulate.a = 0.0
	var tw := create_tween().set_parallel().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(self, "scale", Vector2.ONE, 0.18)
	tw.tween_property(self, "modulate:a", 1.0, 0.18)


## Закрыть «по кнопке»: программа может переспросить (Блокнот: «Сохранить изменения?»).
func request_close() -> void:
	if client and client.has_method("can_close") and not client.call("can_close"):
		return
	close()


func close() -> void:
	if is_queued_for_deletion():
		return
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	closed.emit(self)
	pivot_offset = size * 0.5
	var tw := create_tween().set_parallel()
	tw.tween_property(self, "scale", Vector2(0.94, 0.94), 0.14)
	tw.tween_property(self, "modulate:a", 0.0, 0.14)
	tw.chain().tween_callback(queue_free)
