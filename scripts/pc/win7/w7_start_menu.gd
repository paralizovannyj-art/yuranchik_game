## Меню «Пуск» Windows 7: слева белый список программ («Все программы», поиск снизу),
## справа на стекле — папки пользователя, «Компьютер», «Панель управления» и кнопка «Завершение работы».
## Сверху справа — картинка пользователя (при наведении на пункт меняется на его значок).
class_name W7StartMenu
extends Control

const W := 450.0
const H := 520.0
const LEFT_W := 262.0
const ROW := 38.0
const RROW := 30.0

const PROGRAMS := [
	{"text": "Google Chrome", "app": "chrome", "icon": "chrome"},
	{"text": "Блокнот", "app": "notepad", "icon": "notepad"},
	{"text": "Проводник", "app": "explorer", "icon": "explorer"},
]
const ALL := [
	{"text": "Google Chrome", "app": "chrome", "icon": "chrome"},
	{"text": "Автозагрузка", "folder": []},
	{"text": "Игры", "folder": []},
	{"text": "Обслуживание", "folder": []},
	{"text": "Стандартные", "folder": [{"text": "Блокнот", "app": "notepad", "icon": "notepad"},
			{"text": "Проводник", "app": "explorer", "icon": "explorer"}]},
]
const RIGHT := [
	{"text": "Юрчик", "go": "user", "icon": "user"},
	{"text": "Документы", "go": "lib:1", "icon": "docs"},
	{"text": "Изображения", "go": "lib:2", "icon": "pics"},
	{"text": "Музыка", "go": "lib:3", "icon": "music"},
	{"sep": true},
	{"text": "Игры", "go": "games", "icon": "games"},
	{"text": "Компьютер", "go": "computer", "icon": "computer"},
	{"sep": true},
	{"text": "Панель управления", "go": "control", "icon": "control"},
	{"text": "Устройства и принтеры", "go": "devices", "icon": "devices"},
	{"text": "Программы по умолчанию", "go": "", "icon": "control"},
	{"text": "Справка и поддержка", "go": "", "icon": "help"},
]

var desktop: Control
var search: LineEdit
var _mode := "main"            ## main / all
var _open_folders := {}
var _rows: Array = []          ## что сейчас в левом списке: [rect, словарь]
var _hover_l := -1
var _hover_r := -1
var _hover_btn := ""
var _glass: Control
var _deco: Control


func _ready() -> void:
	size = Vector2(W, H)
	mouse_filter = Control.MOUSE_FILTER_STOP
	_glass = W7.glass_layer(self, _draw_glass, 2.4)
	_deco = Control.new()
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	search = LineEdit.new()
	search.placeholder_text = "Найти программы и файлы"
	search.position = Vector2(14, H - 33)
	search.size = Vector2(LEFT_W - 12, 24)
	search.right_icon = W7.icon("search", 16)
	search.text_changed.connect(func(_t: String) -> void:
		_hover_l = -1
		_layout_left()
		_redraw())
	search.text_submitted.connect(func(_t: String) -> void:
		for r: Array in _rows:
			if (r[1] as Dictionary).has("app"):
				_launch(r[1])
				return)
	add_child(search)


func open() -> void:
	_mode = "main"
	_open_folders.clear()
	search.text = ""
	_hover_l = -1
	_hover_r = -1
	_layout_left()
	visible = true
	modulate.a = 0.0
	create_tween().tween_property(self, "modulate:a", 1.0, 0.12)
	search.grab_focus()
	_redraw()


func close() -> void:
	visible = false
	search.release_focus()


func _redraw() -> void:
	_glass.queue_redraw()
	_deco.queue_redraw()


func _left_rect() -> Rect2:
	return Rect2(8, 8, LEFT_W, H - 8 - 44)


func _right_x() -> float:
	return 8.0 + LEFT_W + 6.0


func _layout_left() -> void:
	_rows.clear()
	var lr := _left_rect()
	var y := lr.position.y + 6.0
	var q := search.text.strip_edges().to_lower() if search else ""
	if q != "":
		var found := []
		for p: Dictionary in PROGRAMS:
			if (p["text"] as String).to_lower().contains(q):
				found.append(p)
		_rows.append([Rect2(lr.position.x + 4, y, lr.size.x - 8, 22), {"header": "Программы (%d)" % found.size()}])
		y += 24.0
		for p: Dictionary in found:
			_rows.append([Rect2(lr.position.x + 4, y, lr.size.x - 8, 26), p.merged({"small": true})])
			y += 26.0
		return
	if _mode == "main":
		for p: Dictionary in PROGRAMS:
			_rows.append([Rect2(lr.position.x + 4, y, lr.size.x - 8, ROW), p])
			y += ROW
		_rows.append([Rect2(lr.position.x + 4, lr.end.y - 30, lr.size.x - 8, 26), {"text": "Все программы", "all": true}])
	else:
		for p: Dictionary in ALL:
			_rows.append([Rect2(lr.position.x + 4, y, lr.size.x - 8, 24), p.merged({"small": true})])
			y += 24.0
			if p.has("folder") and _open_folders.has(p["text"]):
				var sub: Array = p["folder"]
				if sub.is_empty():
					_rows.append([Rect2(lr.position.x + 20, y, lr.size.x - 24, 24), {"text": "(пусто)", "empty": true}])
					y += 24.0
				for s: Dictionary in sub:
					_rows.append([Rect2(lr.position.x + 20, y, lr.size.x - 24, 24), s.merged({"small": true})])
					y += 24.0
		_rows.append([Rect2(lr.position.x + 4, lr.end.y - 30, lr.size.x - 8, 26), {"text": "Назад", "back": true}])


func _right_rows() -> Array:
	var out := []
	var y := 52.0
	for it: Dictionary in RIGHT:
		if it.get("sep", false):
			out.append([Rect2(), it])
			y += 9.0
			continue
		out.append([Rect2(_right_x() + 4, y, W - _right_x() - 12, RROW), it])
		y += RROW
	return out


func _btn_rect(k: String) -> Rect2:
	var x := _right_x() + 10.0
	return Rect2(x, H - 34, 134, 24) if k == "shutdown" else Rect2(x + 134, H - 34, 22, 24)


# ---------- рисование ----------

func _draw_glass(g: Control) -> void:
	var ci := g.get_canvas_item()
	var r := Rect2(Vector2.ZERO, size)
	W7.fill(ci, r, 6, [[0.0, Color(0.30, 0.45, 0.60, 0.55)], [1.0, Color(0.14, 0.24, 0.34, 0.65)]])
	W7.stroke(ci, r.grow(-1), 5, Color(1, 1, 1, 0.4))
	W7.stroke(ci, r, 6, Color(0, 0, 0, 0.7))


func _draw_deco() -> void:
	var d := _deco
	var ci := d.get_canvas_item()
	# белый список слева
	var lr := _left_rect()
	W7.fill(ci, lr, 4, [[0.0, "ffffff"], [1.0, "ffffff"]])
	W7.stroke(ci, lr, 4, Color(0, 0, 0, 0.5))
	for i in _rows.size():
		var r: Rect2 = _rows[i][0]
		var it: Dictionary = _rows[i][1]
		if it.has("header"):
			d.draw_string(W7.FONT, r.position + Vector2(4, 15), it["header"], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, W7.LINK)
			d.draw_line(Vector2(r.position.x + W7.text_width(it["header"]) + 12, r.position.y + 11), Vector2(r.end.x, r.position.y + 11), Color("e0e6ee"))
			continue
		if it.get("all", false) or it.get("back", false):
			d.draw_line(Vector2(r.position.x + 6, r.position.y - 4), Vector2(r.end.x - 6, r.position.y - 4), Color("d6dde6"))
		if i == _hover_l and not it.get("empty", false):
			W7.box(ci, r, 3, [[0.0, "eaf4fd"], [1.0, "d5e9fb"]], "7da2ce", "ffffffb0")
		var x := r.position.x + 4.0
		var small: bool = it.get("small", false) or it.get("all", false) or it.get("back", false)
		if it.has("icon"):
			var sz := 16 if small else 32
			var ic := W7.icon(it["icon"], sz)
			if ic:
				d.draw_texture_rect(ic, Rect2(x, r.position.y + (r.size.y - sz) * 0.5, sz, sz), false)
			x += sz + 8.0
		elif it.has("folder"):
			var ic2 := W7.icon("folder", 16)
			d.draw_texture_rect(ic2, Rect2(x, r.position.y + 4, 16, 16), false)
			x += 24.0
		var col := Color("6d6d6d") if it.get("empty", false) else Color.BLACK
		if it.get("all", false):
			_arrow(d, Vector2(r.position.x + 10, r.position.y + 13), true)
			x = r.position.x + 22
		elif it.get("back", false):
			_arrow(d, Vector2(r.position.x + 12, r.position.y + 13), false)
			x = r.position.x + 22
		d.draw_string(W7.FONT, Vector2(x, r.position.y + r.size.y * 0.5 + 5), it["text"], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, col)
	# правая колонка: картинка пользователя
	var hov_icon := "userpic"
	var rr := _right_rows()
	if _hover_r >= 0 and (rr[_hover_r][1] as Dictionary).has("icon"):
		hov_icon = rr[_hover_r][1]["icon"]
	var pc := Vector2(_right_x() + (W - _right_x()) * 0.5 - 2, 2)
	var frame := Rect2(pc.x - 33, pc.y - 24, 66, 66)
	W7.box(ci, frame, 5, [[0.0, Color(1, 1, 1, 0.55)], [0.5, Color(0.85, 0.92, 1.0, 0.35)], [1.0, Color(0.6, 0.75, 0.9, 0.45)]], Color(0, 0, 0, 0.6), Color(1, 1, 1, 0.6))
	var pic := W7.icon(hov_icon, 48)
	if pic:
		d.draw_texture_rect(pic, Rect2(frame.get_center() - Vector2(24, 24), Vector2(48, 48)), false)
	for i in rr.size():
		var r: Rect2 = rr[i][0]
		var it: Dictionary = rr[i][1]
		if it.get("sep", false):
			var y: float = (rr[i - 1][0] as Rect2).end.y + 4.0
			d.draw_line(Vector2(_right_x() + 10, y), Vector2(W - 14, y), Color(0, 0, 0, 0.35))
			d.draw_line(Vector2(_right_x() + 10, y + 1), Vector2(W - 14, y + 1), Color(1, 1, 1, 0.18))
			continue
		if i == _hover_r:
			W7.box(ci, r, 3, [[0.0, Color(1, 1, 1, 0.32)], [0.5, Color(1, 1, 1, 0.16)], [0.5, Color(1, 1, 1, 0.06)], [1.0, Color(1, 1, 1, 0.2)]], Color(0, 0, 0, 0.55), Color(1, 1, 1, 0.45))
		W7.shadow_text(d, Vector2(r.position.x + 10, r.position.y + 20), it["text"], 12, Color.WHITE)
	# «Завершение работы» и стрелка
	for k: String in ["shutdown", "arrow"]:
		var b := _btn_rect(k)
		var hv := _hover_btn == k
		var a := 0.35 if hv else 0.14
		var rad := Vector4(3, 0, 0, 3) if k == "shutdown" else Vector4(0, 3, 3, 0)
		W7.fill(ci, b, rad, [[0.0, Color(1, 1, 1, a)], [0.5, Color(1, 1, 1, a * 0.55)], [0.5, Color(0.6, 0.8, 1.0, a * 0.3)], [1.0, Color(0.7, 0.9, 1.0, a * 0.7)]])
		W7.stroke(ci, b.grow(-1), rad, Color(1, 1, 1, 0.35))
		W7.stroke(ci, b, rad, Color(0, 0, 0, 0.65))
		if k == "shutdown":
			W7.shadow_text(d, b.position + Vector2(0, 16), "Завершение работы", 12, Color.WHITE, b.size.x, HORIZONTAL_ALIGNMENT_CENTER)
		else:
			_arrow(d, b.get_center() + Vector2(-2, 0), true, Color.WHITE)


func _arrow(d: Control, p: Vector2, right: bool, col := Color("3d3d3d")) -> void:
	var s := 1.0 if right else -1.0
	d.draw_colored_polygon(PackedVector2Array([p + Vector2(-2 * s, -4), p + Vector2(2 * s, 0), p + Vector2(-2 * s, 4)]), col)


# ---------- мышь ----------

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var p: Vector2 = event.position
		var hl := -1
		for i in _rows.size():
			if (_rows[i][0] as Rect2).has_point(p) and not (_rows[i][1] as Dictionary).has("header"):
				hl = i
		var hr := -1
		var rr := _right_rows()
		for i in rr.size():
			if (rr[i][0] as Rect2).has_point(p):
				hr = i
		var hb := "shutdown" if _btn_rect("shutdown").has_point(p) else ("arrow" if _btn_rect("arrow").has_point(p) else "")
		if hl != _hover_l or hr != _hover_r or hb != _hover_btn:
			_hover_l = hl
			_hover_r = hr
			_hover_btn = hb
			_deco.queue_redraw()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and not event.pressed:
		var p: Vector2 = event.position
		for r: Array in _rows:
			if (r[0] as Rect2).has_point(p):
				_click_left(r[1])
				break
		for r: Array in _right_rows():
			if (r[0] as Rect2).has_point(p) and not (r[1] as Dictionary).get("sep", false):
				var go: String = r[1]["go"]
				desktop.call("close_start")
				if go != "":
					desktop.call("open_place", go)
		if _btn_rect("shutdown").has_point(p):
			desktop.call("close_start")
			desktop.call("shutdown")
		elif _btn_rect("arrow").has_point(p):
			var reboot := func() -> void:
				desktop.call("close_start")
				desktop.call("shutdown", true)
			desktop.call("popup_menu", [
				{"text": "Сменить пользователя", "disabled": true},
				{"text": "Выйти из системы", "disabled": true},
				{"text": "Блокировать", "disabled": true},
				{"sep": true},
				{"text": "Перезагрузка", "cb": reboot},
				{"text": "Сон", "disabled": true},
			], global_position + _btn_rect("arrow").end)
	accept_event()


func _click_left(it: Dictionary) -> void:
	if it.get("all", false):
		_mode = "all"
	elif it.get("back", false):
		_mode = "main"
	elif it.has("folder"):
		if _open_folders.has(it["text"]):
			_open_folders.erase(it["text"])
		else:
			_open_folders[it["text"]] = true
	elif it.has("app"):
		_launch(it)
		return
	else:
		return
	_hover_l = -1
	_layout_left()
	_redraw()


func _launch(it: Dictionary) -> void:
	desktop.call("close_start")
	desktop.call("launch", it["app"])
