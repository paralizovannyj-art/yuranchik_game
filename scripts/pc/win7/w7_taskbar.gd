## Панель задач Windows 7: стеклянная полоса, шар «Пуск», закреплённые программы (Проводник, Chrome),
## кнопки открытых окон, языковая панель, значки трея, часы и «Свернуть все окна» справа.
class_name W7Taskbar
extends Control

const H := 40.0
const BTN_W := 60.0
const ORB_W := 54.0
const PINNED := ["explorer", "chrome"]

var desktop: Control
var _glass: Control
var _hover := ""
var _press := ""
var _orb_glow := 0.0
var _last_clock := ""


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_glass = W7.glass_layer(self, _draw_glass, 2.2)
	var deco := Control.new()
	deco.name = "Deco"
	deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	deco.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	deco.draw.connect(_draw_deco.bind(deco))
	add_child(deco)
	mouse_exited.connect(func() -> void:
		_hover = ""
		refresh())


func refresh() -> void:
	queue_redraw()
	for c in get_children():
		if c is CanvasItem:
			(c as CanvasItem).queue_redraw()


func _process(_d: float) -> void:
	var t := W7.now_time()
	if t != _last_clock:
		_last_clock = t
		refresh()
	var target := 1.0 if _hover == "orb" or desktop.call("start_open") else 0.0
	if not is_equal_approx(_orb_glow, target):
		_orb_glow = move_toward(_orb_glow, target, get_process_delta_time() * 6.0)
		refresh()


## Кнопки посередине: закреплённые программы + открытые, которых нет среди закреплённых.
func _apps() -> Array:
	var out: Array = PINNED.duplicate()
	for w: W7Window in desktop.call("windows"):
		if not out.has(w.app_id):
			out.append(w.app_id)
	return out


func _app_rect(i: int) -> Rect2:
	return Rect2(ORB_W + 4.0 + i * (BTN_W + 2.0), 0, BTN_W, H)


func _tray_left() -> float:
	return size.x - 15.0 - 72.0 - 3 * 24.0 - 30.0


func app_point(app: String) -> Vector2:
	var i := _apps().find(app)
	return _app_rect(maxi(i, 0)).get_center() + position


func _hit(p: Vector2) -> String:
	if p.x < ORB_W:
		return "orb"
	if p.x > size.x - 15.0:
		return "show_desktop"
	var apps := _apps()
	for i in apps.size():
		if _app_rect(i).has_point(p):
			return "app:" + apps[i]
	if p.x > size.x - 15.0 - 72.0:
		return "clock"
	return ""


# ---------- рисование ----------

func _draw_glass(g: Control) -> void:
	var ci := g.get_canvas_item()
	var r := Rect2(Vector2.ZERO, size)
	W7.fill(ci, r, 0.0, [[0.0, Color(0.16, 0.26, 0.36, 0.62)], [0.45, Color(0.10, 0.17, 0.24, 0.66)], [1.0, Color(0.06, 0.10, 0.15, 0.72)]])
	g.draw_line(Vector2(0, 0.5), Vector2(size.x, 0.5), Color(0, 0, 0, 0.75))
	g.draw_line(Vector2(0, 1.5), Vector2(size.x, 1.5), Color(1, 1, 1, 0.32))


func _draw_deco(d: Control) -> void:
	var ci := d.get_canvas_item()
	var active: W7Window = desktop.call("active_window")
	var apps := _apps()
	for i in apps.size():
		var app: String = apps[i]
		var wins: Array = desktop.call("windows_of", app)
		var r := _app_rect(i).grow_individual(0, -1, 0, -1)
		var hov := _hover == "app:" + app
		var is_active := false
		for w: W7Window in wins:
			if w == active and not w.minimized:
				is_active = true
		if not wins.is_empty():
			# открытая программа: стеклянная кнопка; активная — светлее
			var a := 0.30 if is_active else 0.14
			if hov:
				a += 0.12
			W7.fill(ci, r, 3, [[0.0, Color(1, 1, 1, a * 0.9)], [0.5, Color(1, 1, 1, a * 0.45)], [0.5, Color(1, 1, 1, a * 0.2)], [1.0, Color(1, 1, 1, a * 0.5)]])
			W7.stroke(ci, r.grow(-1), 2, Color(1, 1, 1, 0.25 + a * 0.4))
			W7.stroke(ci, r, 3, Color(0, 0, 0, 0.6))
			if wins.size() > 1:   # несколько окон — «стопка» справа
				d.draw_line(Vector2(r.end.x + 1.5, r.position.y + 3), Vector2(r.end.x + 1.5, r.end.y - 3), Color(1, 1, 1, 0.35), 1.0)
			if hov:
				# цветная подсветка под курсором (Windows берёт цвет иконки — здесь голубой)
				var c := r.get_center() + Vector2(0, r.size.y * 0.45)
				for k in 6:
					d.draw_circle(c, 26.0 - k * 4.0, Color(0.45, 0.75, 1.0, 0.05))
		elif hov:
			W7.fill(ci, r, 3, [[0.0, Color(1, 1, 1, 0.22)], [0.5, Color(1, 1, 1, 0.1)], [0.5, Color(1, 1, 1, 0.04)], [1.0, Color(1, 1, 1, 0.14)]])
			W7.stroke(ci, r, 3, Color(0, 0, 0, 0.5))
			W7.stroke(ci, r.grow(-1), 2, Color(1, 1, 1, 0.3))
		var ic := W7.icon(_app_icon(app), 32)
		if ic:
			var off := Vector2(0, 1) if _press == "app:" + app else Vector2.ZERO
			d.draw_texture_rect(ic, Rect2(r.get_center() - Vector2(16, 16) + off, Vector2(32, 32)), false)
	_draw_orb(d)
	_draw_tray(d)


func _app_icon(app: String) -> String:
	return {"explorer": "explorer", "chrome": "chrome", "notepad": "notepad"}.get(app, "explorer")


## Шар «Пуск»: синяя глянцевая сфера с флажком Windows; при наведении светится.
func _draw_orb(d: Control) -> void:
	var c := Vector2(ORB_W * 0.5, H * 0.5 - 1.0)
	var rad := 18.0
	var glow := _orb_glow
	for k in 7:
		d.draw_circle(c, rad + 6.0 - k, Color(0.4, 0.75, 1.0, 0.03 + glow * 0.04))
	d.draw_circle(c, rad + 1.0, Color(0, 0, 0, 0.7))
	# сфера: от тёмно-синего края к светлому центру снизу
	for k in 18:
		var t := float(k) / 17.0
		var col := Color("0f3c73").lerp(Color("2b8fd6"), t).lerp(Color("5fd0ff"), glow * 0.35 * t)
		d.draw_circle(c + Vector2(0, t * 5.0), rad * (1.0 - t * 0.62), col)
	# стеклянный блик сверху
	var hl := PackedVector2Array()
	for k in 25:
		var a := PI + PI * float(k) / 24.0
		hl.append(c + Vector2(cos(a) * rad * 0.86, sin(a) * rad * 0.8 - 1.0))
	d.draw_colored_polygon(hl, Color(1, 1, 1, 0.28 + glow * 0.08))
	d.draw_arc(c, rad, 0, TAU, 40, Color(0.75, 0.9, 1.0, 0.55), 1.0, true)
	_draw_flag(d, c + Vector2(0.5, 0.5), 8.5, 1.0)


## Флажок Windows: четыре цветные «волнистые» плашки.
static func _draw_flag(d: CanvasItem, c: Vector2, s: float, alpha: float) -> void:
	var cols := [Color("f25022"), Color("7fba00"), Color("00a4ef"), Color("ffb900")]
	var gap := s * 0.1
	var quads := [Vector2(-1, -1), Vector2(0, -1), Vector2(-1, 0), Vector2(0, 0)]
	for i in 4:
		var o: Vector2 = c + quads[i] * s + Vector2(gap if quads[i].x == 0 else -gap, gap if quads[i].y == 0 else -gap) * 0.5
		var pts := PackedVector2Array()
		var n := 6
		for k in n + 1:   # верхний край с волной
			var x := float(k) / n
			pts.append(o + Vector2(x * (s - gap), -sin(x * PI) * s * 0.12 + x * s * 0.08) + Vector2(0, 0))
		for k in range(n, -1, -1):
			var x := float(k) / n
			pts.append(o + Vector2(x * (s - gap), s - gap - sin(x * PI) * s * 0.12 + x * s * 0.08))
		var col: Color = cols[i]
		col.a = alpha
		d.draw_colored_polygon(pts, col)


func _draw_tray(d: Control) -> void:
	var x := _tray_left()
	# языковая панель
	W7.shadow_text(d, Vector2(x, 25), "RU", 11, Color.WHITE)
	x += 26.0
	# флажок центра поддержки, сеть, громкость (белые значки)
	_draw_flag(d, Vector2(x + 8, 20), 5.5, 0.95)
	x += 24.0
	for k in 4:   # сеть: «лесенка» столбиков
		var h := 4.0 + k * 3.0
		d.draw_rect(Rect2(x + 2 + k * 4.0, 27 - h, 3, h), Color(1, 1, 1, 0.9))
	x += 24.0
	var sp := W7.icon("speaker", 16)
	if sp:
		d.draw_texture_rect(sp, Rect2(x, 12, 16, 16), false)
	# часы и дата
	var cx := size.x - 15.0 - 36.0
	var hov := _hover == "clock"
	if hov:
		var r := Rect2(size.x - 15.0 - 72.0, 2, 70, H - 4)
		W7.fill(d.get_canvas_item(), r, 3, [[0.0, Color(1, 1, 1, 0.2)], [1.0, Color(1, 1, 1, 0.08)]])
		W7.stroke(d.get_canvas_item(), r, 3, Color(0, 0, 0, 0.4))
	d.draw_string(W7.FONT, Vector2(cx - 36, 17), W7.now_time(), HORIZONTAL_ALIGNMENT_CENTER, 72, 12, Color.WHITE)
	d.draw_string(W7.FONT, Vector2(cx - 36, 33), W7.now_date(), HORIZONTAL_ALIGNMENT_CENTER, 72, 12, Color.WHITE)
	# «Свернуть все окна»
	var sd := Rect2(size.x - 15.0, 0, 15.0, H)
	var a := 0.35 if _hover == "show_desktop" else 0.12
	W7.fill(d.get_canvas_item(), sd, 0.0, [[0.0, Color(1, 1, 1, a)], [1.0, Color(1, 1, 1, a * 0.5)]])
	d.draw_line(Vector2(sd.position.x + 0.5, 0), Vector2(sd.position.x + 0.5, H), Color(0, 0, 0, 0.6))
	d.draw_line(Vector2(sd.position.x + 1.5, 0), Vector2(sd.position.x + 1.5, H), Color(1, 1, 1, 0.3))


# ---------- мышь ----------

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var h := _hit(event.position)
		if h != _hover:
			_hover = h
			refresh()
	elif event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index != MOUSE_BUTTON_LEFT:
			accept_event()
			return
		var h := _hit(mb.position)
		if mb.pressed:
			_press = h
			if h == "orb":
				desktop.call("toggle_start")
			refresh()
		else:
			if h == _press and h.begins_with("app:"):
				desktop.call("taskbar_click", h.substr(4))
			elif h == _press and h == "show_desktop":
				desktop.call("show_desktop")
			_press = ""
			refresh()
		accept_event()
