## Окно «Сохранение» (Блокнот → «Сохранить как»): папки слева, файлы справа, имя файла внизу.
class_name W7SaveDialog
extends Control

signal saved(folder: Dictionary, file_name: String)

const NAV_H := 34.0
const CMD_H := 30.0
const BOTTOM_H := 96.0
const PANE_W := 150.0
const ROW_H := 22.0

var desktop: Control
var fs: W7Fs
var window: W7Window
var folder: Dictionary
var name_edit: LineEdit
var _rows: Array = []          ## [Rect2, узел]
var _nav: Array = []           ## [Rect2, узел, текст, значок]
var _hover := -1
var _hover_nav := -1
var _sel: Variant = null
var _start_name := ""


func setup(p_desktop: Control, start_name: String) -> W7SaveDialog:
	desktop = p_desktop
	fs = desktop.get("fs")
	folder = fs.docs
	_start_name = start_name
	return self


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	if window:
		window.glass_top = NAV_H
	name_edit = LineEdit.new()
	name_edit.text = _start_name
	name_edit.text_submitted.connect(func(_t: String) -> void: _save())
	add_child(name_edit)
	for k: Array in [["Сохранить", _save], ["Отмена", func() -> void: window.close()]]:
		var b := Button.new()
		b.text = k[0]
		b.name = k[0]
		b.size = Vector2(86, 23)
		b.pressed.connect(k[1])
		add_child(b)
	resized.connect(_layout)
	_layout()
	name_edit.call_deferred("grab_focus")
	name_edit.call_deferred("select_all")


func _layout() -> void:
	var by := size.y - BOTTOM_H
	name_edit.position = Vector2(110, by + 10)
	name_edit.size = Vector2(size.x - 124, 22)
	var b1 := get_node("Сохранить") as Button
	var b2 := get_node("Отмена") as Button
	b2.position = Vector2(size.x - 96, size.y - 33)
	b1.position = Vector2(size.x - 190, size.y - 33)
	_rows.clear()
	var y := NAV_H + CMD_H + 26.0
	for n: Dictionary in fs.items(folder):
		if n["kind"] in ["folder", "file"]:
			_rows.append([Rect2(PANE_W + 4, y, size.x - PANE_W - 8, ROW_H), n])
			y += ROW_H
	_nav.clear()
	y = NAV_H + CMD_H + 8.0
	for it: Array in [["Рабочий стол", fs.desktop, "desktop"], ["Документы", fs.docs, "lib_docs"],
			["Загрузки", fs.downloads, "downloads"], ["Изображения", fs.pics, "lib_pics"], ["Музыка", fs.music, "lib_music"]]:
		_nav.append([Rect2(4, y, PANE_W - 8, 22), it[1], it[0], it[2]])
		y += 22.0
	queue_redraw()


func _draw() -> void:
	var ci := get_canvas_item()
	var w := size.x
	# адрес (на стекле окна)
	var ar := Rect2(8, 5, w - 220, 24)
	draw_rect(ar, Color(1, 1, 1, 0.92))
	draw_rect(ar, Color(0, 0, 0, 0.45), false, 1.0)
	var path: String = "Компьютер  ▸  Локальный диск (C:)  ▸  Пользователи  ▸  Юрчик  ▸  " + folder["name"]
	if is_same(folder, fs.docs):
		path = "Библиотеки  ▸  Документы"
	draw_string(W7.FONT, ar.position + Vector2(24, 17), path, HORIZONTAL_ALIGNMENT_LEFT, ar.size.x - 28, 12, Color.BLACK)
	var ic := W7.icon(folder["icon"], 16)
	if ic:
		draw_texture_rect(ic, Rect2(ar.position + Vector2(4, 4), Vector2(16, 16)), false)
	var sr := Rect2(w - 206, 5, 200, 24)
	draw_rect(sr, Color(1, 1, 1, 0.92))
	draw_rect(sr, Color(0, 0, 0, 0.45), false, 1.0)
	draw_string(W7.FONT, sr.position + Vector2(6, 17), "Поиск: %s" % folder["name"], HORIZONTAL_ALIGNMENT_LEFT, 170, 12, Color("6d6d6d"))
	# панель команд
	W7.fill(ci, Rect2(0, NAV_H, w, CMD_H), 0, [[0.0, "f5f9fd"], [0.5, "eaf1fa"], [1.0, "dce7f5"]])
	draw_line(Vector2(0, NAV_H + CMD_H - 0.5), Vector2(w, NAV_H + CMD_H - 0.5), Color("a0afc3"))
	draw_string(W7.FONT, Vector2(14, NAV_H + 19), "Упорядочить ▾      Новая папка", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("1e395b"))
	# папки слева и список
	var body := Rect2(0, NAV_H + CMD_H, w, size.y - NAV_H - CMD_H - BOTTOM_H)
	draw_rect(body, Color.WHITE)
	draw_line(Vector2(PANE_W + 0.5, body.position.y), Vector2(PANE_W + 0.5, body.end.y), Color("d6e5f5"))
	for i in _nav.size():
		var r: Rect2 = _nav[i][0]
		if is_same(_nav[i][1], folder):
			W7.box(ci, r, 2, [[0.0, "dcebfc"], [1.0, "c1dbfc"]], "7da2ce", "ebf4fd")
		elif i == _hover_nav:
			W7.box(ci, r, 2, [[0.0, "fafbfd"], [1.0, "ebf3fd"]], "b8d6fb", "fcfdfe")
		var ni := W7.icon(_nav[i][3], 16)
		if ni:
			draw_texture_rect(ni, Rect2(r.position + Vector2(6, 3), Vector2(16, 16)), false)
		draw_string(W7.FONT, r.position + Vector2(28, 16), _nav[i][2], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.BLACK)
	draw_string(W7.FONT, Vector2(PANE_W + 12, body.position.y + 17), "Имя", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("4c607a"))
	draw_string(W7.FONT, Vector2(PANE_W + 262, body.position.y + 17), "Дата изменения", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("4c607a"))
	draw_line(Vector2(PANE_W + 1, body.position.y + 24.5), Vector2(w, body.position.y + 24.5), Color("e5e5e5"))
	if _rows.is_empty():
		draw_string(W7.FONT, Vector2(PANE_W, body.position.y + 50), "Нет элементов, удовлетворяющих условиям поиска.", HORIZONTAL_ALIGNMENT_CENTER, w - PANE_W, 12, Color("6d6d6d"))
	for i in _rows.size():
		var r: Rect2 = _rows[i][0]
		var n: Dictionary = _rows[i][1]
		if is_same(n, _sel):
			W7.box(ci, r, 3, [[0.0, "dcebfc"], [1.0, "c1dbfc"]], "7da2ce", "ebf4fd")
		elif i == _hover:
			W7.box(ci, r, 3, [[0.0, "fafbfd"], [1.0, "ebf3fd"]], "b8d6fb", "fcfdfe")
		var ri := W7.icon(n["icon"], 16)
		if ri:
			draw_texture_rect(ri, Rect2(r.position + Vector2(6, 3), Vector2(16, 16)), false)
		draw_string(W7.FONT, r.position + Vector2(28, 15), n["name"], HORIZONTAL_ALIGNMENT_LEFT, 220, 12, Color.BLACK)
		draw_string(W7.FONT, r.position + Vector2(258, 15), n["date"], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("6d6d6d"))
	# низ: имя, тип, кодировка
	var by := size.y - BOTTOM_H
	draw_rect(Rect2(0, by, w, BOTTOM_H), Color("f0f0f0"))
	draw_line(Vector2(0, by + 0.5), Vector2(w, by + 0.5), Color("d0d0d0"))
	draw_string(W7.FONT, Vector2(30, by + 26), "Имя файла:", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.BLACK)
	draw_string(W7.FONT, Vector2(30, by + 52), "Тип файла:", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.BLACK)
	var tr := Rect2(110, by + 38, w - 124, 22)
	W7.box(ci, tr, 2, [[0.0, "f2f2f2"], [0.5, "ebebeb"], [0.5, "dddddd"], [1.0, "cfcfcf"]], "707070")
	draw_string(W7.FONT, tr.position + Vector2(6, 16), "Текстовые документы (*.txt)", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.BLACK)
	draw_colored_polygon(PackedVector2Array([tr.end - Vector2(16, 13), tr.end - Vector2(8, 13), tr.end - Vector2(12, 9)]), Color("3d3d3d"))
	draw_string(W7.FONT, Vector2(30, size.y - 16), "▴  Скрыть папки", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("1e3287"))
	draw_string(W7.FONT, Vector2(size.x - 330, size.y - 16), "Кодировка:  ANSI", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.BLACK)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var h := -1
		for i in _rows.size():
			if (_rows[i][0] as Rect2).has_point(event.position):
				h = i
		var hn := -1
		for i in _nav.size():
			if (_nav[i][0] as Rect2).has_point(event.position):
				hn = i
		if h != _hover or hn != _hover_nav:
			_hover = h
			_hover_nav = hn
			queue_redraw()
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		for i in _nav.size():
			if (_nav[i][0] as Rect2).has_point(event.position):
				folder = _nav[i][1]
				_sel = null
				_layout()
		for i in _rows.size():
			if (_rows[i][0] as Rect2).has_point(event.position):
				var n: Dictionary = _rows[i][1]
				_sel = n
				if n["kind"] == "file":
					name_edit.text = (n["name"] as String).get_basename()
				elif event.double_click:
					folder = n
					_sel = null
					_layout()
				queue_redraw()
				break
		accept_event()


func _save() -> void:
	var n := name_edit.text.strip_edges()
	if n == "" or n == "*.txt":
		return
	if n.contains("\\") or n.contains("/") or n.contains(":") or n.contains("*") or n.contains("?"):
		desktop.call("message", "Сохранение", "Имя файла указано неверно.", "error", ["ОК"], Callable(), window)
		return
	saved.emit(folder, n)
	window.close()
