## Google Chrome образца 2011 года на Windows 7: вкладки прямо на стекле заголовка, под ними панель
## с «Назад», «Вперёд», «Обновить», адресной строкой (омнибоксом), звёздочкой и гаечным ключом.
## Страница — page (Control): настоящий браузер W7Web (Chromium через gdcef), стартует с Google.
class_name W7Chrome
extends Control

signal navigate_requested(url: String)
signal back_requested
signal forward_requested
signal reload_requested

const TOP := 14.0          ## где окно начинает содержимое (W7Window.client_top)
const TAB_H := 26.0
const BAR_H := 36.0

var desktop: Control
var window: W7Window
var page: Control          ## сюда рисуется страница
var omnibox: LineEdit
var tab_title := "Новая вкладка"
var can_back := false
var can_forward := false
var loading := false
var _hover := ""
var _ntp: Control
var web: W7Web
var _spin := 0.0


func setup(p_desktop: Control) -> W7Chrome:
	desktop = p_desktop
	return self


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_PASS
	if window:
		window.client_top = TOP
		window.drag_h = TOP + TAB_H + 2
		window.glass_top = TAB_H
		window.show_title = false
	page = Control.new()
	page.name = "Page"
	page.clip_contents = true
	page.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	page.offset_top = TAB_H + BAR_H
	add_child(page)
	_ntp = Control.new()
	_ntp.name = "NewTab"
	_ntp.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ntp.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_ntp.draw.connect(_draw_ntp)
	page.add_child(_ntp)
	web = W7Web.new().setup(self)
	web.name = "Web"
	page.add_child(web)
	omnibox = LineEdit.new()
	var flat := StyleBoxEmpty.new()
	flat.content_margin_left = 4
	omnibox.add_theme_stylebox_override("normal", flat)
	omnibox.add_theme_stylebox_override("focus", flat)
	omnibox.add_theme_font_size_override("font_size", 13)
	omnibox.text_submitted.connect(func(t: String) -> void:
		omnibox.release_focus()
		navigate_requested.emit(t.strip_edges()))
	omnibox.focus_entered.connect(func() -> void: omnibox.call_deferred("select_all"))
	add_child(omnibox)
	resized.connect(_layout)
	_layout()
	web.open.call_deferred(W7Web.HOME)


func _process(delta: float) -> void:
	if loading:
		_spin += delta * 7.0
		queue_redraw()


func _layout() -> void:
	omnibox.position = Vector2(104, TAB_H + 6)
	omnibox.size = Vector2(size.x - 104 - 72, 24)
	queue_redraw()


## Заголовок вкладки и окна (для панели задач).
func set_tab_title(t: String) -> void:
	tab_title = t if t != "" else "Новая вкладка"
	if window:
		window.title = "%s - Google Chrome" % tab_title
		window.set_title(window.title)
	queue_redraw()


func show_new_tab(on: bool) -> void:
	_ntp.visible = on


func _tab_rect() -> Rect2:
	return Rect2(6, 2, minf(220.0, size.x - 180.0), TAB_H - 2)


func _btn(k: String) -> Rect2:
	match k:
		"back": return Rect2(6, TAB_H + 5, 28, 26)
		"fwd": return Rect2(36, TAB_H + 5, 28, 26)
		"reload": return Rect2(66, TAB_H + 5, 28, 26)
		"wrench": return Rect2(size.x - 34, TAB_H + 5, 28, 26)
		"close_tab":
			var t := _tab_rect()
			return Rect2(t.end.x - 30, t.position.y + 6, 14, 14)
		"new_tab":
			var t2 := _tab_rect()
			return Rect2(t2.end.x - 8, 6, 30, 18)
	return Rect2()


func _tab_poly(r: Rect2, slope := 12.0) -> PackedVector2Array:
	return PackedVector2Array([Vector2(r.position.x, r.end.y), Vector2(r.position.x + slope, r.position.y + 2),
			Vector2(r.position.x + slope + 3, r.position.y), Vector2(r.end.x - slope - 3, r.position.y),
			Vector2(r.end.x - slope, r.position.y + 2), Vector2(r.end.x, r.end.y)])


func _draw() -> void:
	var ci := get_canvas_item()
	var w := size.x
	# кнопка «новая вкладка» — маленькая косая плашка
	var nt := _btn("new_tab")
	var ntp := _tab_poly(nt, 6.0)
	var na := 0.55 if _hover == "new_tab" else 0.35
	draw_colored_polygon(ntp, Color(1, 1, 1, na))
	var ntl := ntp.duplicate()
	ntl.append(ntp[0])
	draw_polyline(ntl, Color(0, 0, 0, 0.45), 1.0, true)
	# вкладка
	var tr := _tab_rect()
	var poly := _tab_poly(tr)
	var cols := PackedColorArray()
	for p: Vector2 in poly:
		cols.append(Color("fbfcfe").lerp(Color("eef2f8"), (p.y - tr.position.y) / tr.size.y))
	draw_polygon(poly, cols)
	var line := poly.duplicate()
	draw_polyline(line, Color(0, 0, 0, 0.5), 1.0, true)
	# значок вкладки: пока грузится — крутящийся кружок, потом значок Chrome
	var fc := Vector2(tr.position.x + 22, tr.position.y + 13)
	if loading:
		draw_arc(fc, 6.0, _spin, _spin + 4.2, 16, Color("3c78d8"), 2.0, true)
	else:
		var fi := W7.icon("chrome", 16)
		if fi:
			draw_texture_rect(fi, Rect2(fc - Vector2(8, 8), Vector2(16, 16)), false)
	draw_string(W7.FONT, Vector2(tr.position.x + 34, tr.position.y + 17), tab_title, HORIZONTAL_ALIGNMENT_LEFT, tr.size.x - 70, 12, Color.BLACK)
	var cx := _btn("close_tab")
	if _hover == "close_tab":
		draw_circle(cx.get_center(), 7, Color("c75050"))
	var xc := Color.WHITE if _hover == "close_tab" else Color("7a7a7a")
	draw_line(cx.get_center() + Vector2(-3, -3), cx.get_center() + Vector2(3, 3), xc, 1.6, true)
	draw_line(cx.get_center() + Vector2(-3, 3), cx.get_center() + Vector2(3, -3), xc, 1.6, true)
	# панель инструментов
	var bar := Rect2(0, TAB_H, w, BAR_H)
	W7.fill(ci, bar, 0, [[0.0, "eef2f8"], [1.0, "dfe6f0"]])
	draw_line(Vector2(0, TAB_H + 0.5), Vector2(tr.position.x, TAB_H + 0.5), Color(0, 0, 0, 0.5))
	draw_line(Vector2(tr.end.x, TAB_H + 0.5), Vector2(w, TAB_H + 0.5), Color(0, 0, 0, 0.5))
	draw_line(Vector2(0, bar.end.y - 0.5), Vector2(w, bar.end.y - 0.5), Color("a6b0be"))
	for k: String in ["back", "fwd", "reload", "wrench"]:
		var r := _btn(k)
		var on := true
		if k == "back":
			on = can_back
		elif k == "fwd":
			on = can_forward
		if _hover == k and on:
			W7.box(ci, r, 3, [[0.0, Color(1, 1, 1, 0.9)], [1.0, Color(1, 1, 1, 0.4)]], Color(0, 0, 0, 0.3))
		var c := r.get_center()
		var col := Color("4a5a70") if on else Color("aab3c0")
		match k:
			"back", "fwd":
				var s := -1.0 if k == "back" else 1.0
				draw_colored_polygon(PackedVector2Array([c + Vector2(-7 * s, -2), c + Vector2(1 * s, -2), c + Vector2(1 * s, -7),
						c + Vector2(8 * s, 0), c + Vector2(1 * s, 7), c + Vector2(1 * s, 2), c + Vector2(-7 * s, 2)]), col)
			"reload":
				if loading:
					draw_line(c + Vector2(-5, -5), c + Vector2(5, 5), col, 2.4, true)
					draw_line(c + Vector2(-5, 5), c + Vector2(5, -5), col, 2.4, true)
				else:
					draw_arc(c, 6.5, -PI * 0.35, PI * 1.45, 18, col, 2.4, true)
					draw_colored_polygon(PackedVector2Array([c + Vector2(2, -11), c + Vector2(9, -5.5), c + Vector2(1.5, -2.5)]), col)
			"wrench":
				draw_line(c + Vector2(-6, 6), c + Vector2(3, -3), col, 3.2, true)
				draw_circle(c + Vector2(4, -4), 4.5, col)
				draw_circle(c + Vector2(6, -6), 2.4, Color("e6ebf2"))
	# омнибокс
	var ob := Rect2(98, TAB_H + 5, w - 98 - 40, 26)
	W7.fill(ci, ob, 3, [[0.0, "ffffff"], [1.0, "ffffff"]])
	W7.stroke(ci, ob, 3, Color("a3b1c4"))
	var sc := Vector2(ob.end.x - 14, ob.get_center().y)
	var star := PackedVector2Array()
	for i in 11:
		var a := -PI * 0.5 + TAU * i / 10.0
		star.append(sc + Vector2(cos(a), sin(a)) * (7.0 if i % 2 == 0 else 3.0))
	draw_polyline(star, Color("8a96a8"), 1.2, true)


## «Новая вкладка» Chrome 2011: сетка пустых миниатюр «Самые посещаемые» и переключатель внизу.
func _draw_ntp() -> void:
	var d := _ntp
	var s := d.size
	d.draw_rect(Rect2(Vector2.ZERO, s), Color.WHITE)
	var tw := 150.0
	var th := 96.0
	var gap := 22.0
	var gx := (s.x - (tw * 4 + gap * 3)) * 0.5
	var gy := maxf(40.0, (s.y - (th * 2 + gap + 60)) * 0.45)
	for row in 2:
		for col in 4:
			var r := Rect2(gx + col * (tw + gap), gy + row * (th + gap + 10), tw, th)
			W7.fill(d.get_canvas_item(), r, 4, [[0.0, "f7f7f7"], [1.0, "f0f0f0"]])
			W7.stroke(d.get_canvas_item(), r, 4, Color("dcdcdc"))
	var by := s.y - 30.0
	d.draw_line(Vector2(s.x * 0.2, by - 14), Vector2(s.x * 0.8, by - 14), Color("e8e8e8"))
	d.draw_string(W7.FONT_BOLD, Vector2(0, by), "Самые посещаемые", HORIZONTAL_ALIGNMENT_RIGHT, s.x * 0.5 - 18, 12, Color("555555"))
	d.draw_string(W7.FONT, Vector2(s.x * 0.5 + 18, by), "Приложения", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("888888"))
	d.draw_circle(Vector2(s.x * 0.5, by - 4), 3, Color("bbbbbb"))


func _hit(p: Vector2) -> String:
	for k: String in ["back", "fwd", "reload", "wrench", "close_tab", "new_tab"]:
		if _btn(k).has_point(p):
			return k
	return ""


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var h := _hit(event.position)
		if h != _hover:
			_hover = h
			queue_redraw()
		if event.position.y < TAB_H and h == "" and not _tab_rect().has_point(event.position):
			return                       # пустая полоса вкладок — пусть окно таскается
		accept_event()
	elif event is InputEventMouseButton:
		var p: Vector2 = event.position
		var h := _hit(p)
		if p.y < TAB_H and h == "" and not _tab_rect().has_point(p):
			return
		if not event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			match h:
				"back":
					if can_back:
						back_requested.emit()
				"fwd":
					if can_forward:
						forward_requested.emit()
				"reload":
					reload_requested.emit()
				"close_tab":
					window.request_close()
				"wrench":
					desktop.call("popup_menu", [
						{"text": "Новая вкладка", "shortcut": "Ctrl+T", "disabled": true},
						{"text": "Новое окно", "shortcut": "Ctrl+N", "cb": func() -> void: desktop.call("launch", "chrome")},
						{"text": "Новое окно в режиме инкогнито", "shortcut": "Ctrl+Shift+N", "disabled": true},
						{"sep": true},
						{"text": "Закладки", "disabled": true},
						{"sep": true},
						{"text": "История", "shortcut": "Ctrl+H", "disabled": true},
						{"text": "Загрузки", "shortcut": "Ctrl+J", "disabled": true},
						{"sep": true},
						{"text": "Настройки", "disabled": true},
						{"text": "О браузере Google Chrome", "disabled": true},
						{"sep": true},
						{"text": "Выход", "cb": func() -> void: window.request_close()},
					], global_position + Vector2(size.x - 220, TAB_H + 31))
		accept_event()
