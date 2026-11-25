## Блокнот Windows 7: строка меню (Файл, Правка, Формат, Вид, Справка) и поле для текста (Lucida Console).
## Сохраняет в «Мои документы» / на рабочий стол компа (W7Fs), при закрытии спрашивает про изменения.
class_name W7Notepad
extends Control

const MENU_H := 20.0
const MENUS := ["Файл", "Правка", "Формат", "Вид", "Справка"]

var desktop: Control
var fs: W7Fs
var window: W7Window
var file: Variant = null          ## узел W7Fs или null («Безымянный»)
var edit: TextEdit
var dirty := false
var _hover_menu := -1
var _menu_x: Array[float] = []
var _status: Label
var _closing := false


func setup(p_desktop: Control, p_file: Variant = null) -> W7Notepad:
	desktop = p_desktop
	fs = desktop.get("fs")
	file = p_file
	return self


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	var x := 0.0
	for m: String in MENUS:
		_menu_x.append(x)
		x += W7.text_width(m) + 14.0
	_menu_x.append(x)
	edit = TextEdit.new()
	edit.position = Vector2(0, MENU_H)
	edit.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	edit.offset_top = MENU_H
	edit.add_theme_font_override("font", W7.FONT_MONO)
	edit.add_theme_font_size_override("font_size", 13)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color.WHITE
	sb.content_margin_left = 3
	sb.content_margin_top = 1
	edit.add_theme_stylebox_override("normal", sb)
	edit.add_theme_stylebox_override("focus", sb)
	edit.wrap_mode = TextEdit.LINE_WRAPPING_NONE
	edit.context_menu_enabled = false
	edit.caret_blink = true
	edit.caret_blink_interval = 0.53
	edit.highlight_current_line = false
	if file != null:
		edit.text = file["text"]
	edit.text_changed.connect(func() -> void: dirty = true)
	edit.gui_input.connect(_edit_input)
	add_child(edit)
	_status = Label.new()
	_status.visible = false
	_status.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	_status.offset_top = -22
	_status.add_theme_font_size_override("font_size", 12)
	add_child(_status)
	edit.caret_changed.connect(_update_status)
	_update_title()
	edit.call_deferred("grab_focus")


func _file_name() -> String:
	return "Безымянный" if file == null else (file["name"] as String).get_basename()


func _update_title() -> void:
	if window:
		window.set_title("%s - Блокнот" % _file_name())


func _update_status() -> void:
	_status.text = "Стр %d, стлб %d     " % [edit.get_caret_line() + 1, edit.get_caret_column() + 1]


func _draw() -> void:
	W7.fill(get_canvas_item(), Rect2(0, 0, size.x, MENU_H), 0, [[0.0, "fbfcfe"], [1.0, "e6ecf5"]])
	draw_line(Vector2(0, MENU_H - 0.5), Vector2(size.x, MENU_H - 0.5), Color("b6bcc6"))
	for i in MENUS.size():
		var r := Rect2(_menu_x[i] + 1, 1, _menu_x[i + 1] - _menu_x[i] - 2, MENU_H - 2)
		if i == _hover_menu:
			W7.box(get_canvas_item(), r, 2, [[0.0, "f2f7fd"], [1.0, "dce8f8"]], "aeccf2", "ffffffa0")
		draw_string(W7.FONT, Vector2(_menu_x[i] + 7, 15), MENUS[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.BLACK)
	if _status.visible:
		draw_rect(Rect2(0, size.y - 22, size.x, 22), Color("f0f0f0"))


func _menu_at(p: Vector2) -> int:
	if p.y < 0 or p.y > MENU_H:
		return -1
	for i in MENUS.size():
		if p.x >= _menu_x[i] and p.x < _menu_x[i + 1]:
			return i
	return -1


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var h := _menu_at(event.position)
		if h != _hover_menu:
			_hover_menu = h
			queue_redraw()
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var m := _menu_at(event.position)
		if m >= 0:
			_open_menu(m)
		accept_event()


func _notification(what: int) -> void:
	if what == NOTIFICATION_MOUSE_EXIT and _hover_menu != -1:
		_hover_menu = -1
		queue_redraw()


func _open_menu(i: int) -> void:
	var items: Array
	match i:
		0:
			items = [
				{"text": "Создать", "shortcut": "Ctrl+N", "cb": _new},
				{"text": "Открыть...", "shortcut": "Ctrl+O", "disabled": true},
				{"text": "Сохранить", "shortcut": "Ctrl+S", "cb": save},
				{"text": "Сохранить как...", "cb": save_as},
				{"sep": true},
				{"text": "Параметры страницы...", "disabled": true},
				{"text": "Печать...", "shortcut": "Ctrl+P", "disabled": true},
				{"sep": true},
				{"text": "Выход", "cb": func() -> void: window.request_close()},
			]
		1:
			var has_sel := edit.has_selection()
			items = [
				{"text": "Отменить", "shortcut": "Ctrl+Z", "cb": edit.undo},
				{"sep": true},
				{"text": "Вырезать", "shortcut": "Ctrl+X", "disabled": not has_sel, "cb": edit.cut},
				{"text": "Копировать", "shortcut": "Ctrl+C", "disabled": not has_sel, "cb": edit.copy},
				{"text": "Вставить", "shortcut": "Ctrl+V", "cb": edit.paste},
				{"text": "Удалить", "shortcut": "Del", "disabled": not has_sel, "cb": edit.delete_selection},
				{"sep": true},
				{"text": "Найти...", "shortcut": "Ctrl+F", "disabled": true},
				{"text": "Найти далее", "shortcut": "F3", "disabled": true},
				{"text": "Заменить...", "shortcut": "Ctrl+H", "disabled": true},
				{"text": "Перейти...", "shortcut": "Ctrl+G", "disabled": true},
				{"sep": true},
				{"text": "Выделить все", "shortcut": "Ctrl+A", "cb": edit.select_all},
				{"text": "Время и дата", "shortcut": "F5", "cb": _time_date},
			]
		2:
			items = [
				{"text": "Перенос по словам", "checked": edit.wrap_mode != TextEdit.LINE_WRAPPING_NONE, "cb": _toggle_wrap},
				{"text": "Шрифт...", "disabled": true},
			]
		3:
			items = [{"text": "Строка состояния", "checked": _status.visible, "cb": _toggle_status}]
		4:
			items = [
				{"text": "Просмотреть справку", "disabled": true},
				{"sep": true},
				{"text": "О программе", "cb": _about},
			]
	desktop.call("popup_menu", items, global_position + Vector2(_menu_x[i], MENU_H))


func _edit_input(event: InputEvent) -> void:
	if not (event is InputEventKey and event.pressed):
		return
	var k := event as InputEventKey
	if k.ctrl_pressed:
		match k.keycode:
			KEY_S:
				save()
			KEY_N:
				_new()
			_:
				return
		edit.accept_event()
	elif k.keycode == KEY_F5:
		_time_date()
		edit.accept_event()


func _time_date() -> void:
	edit.insert_text_at_caret("%s %s" % [W7.now_time(), W7.now_date()])


func _toggle_wrap() -> void:
	edit.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY if edit.wrap_mode == TextEdit.LINE_WRAPPING_NONE else TextEdit.LINE_WRAPPING_NONE


func _toggle_status() -> void:
	_status.visible = not _status.visible
	edit.offset_bottom = -22.0 if _status.visible else 0.0
	_update_status()
	queue_redraw()


func _about() -> void:
	desktop.call("message", "О программе «Блокнот»",
			"Microsoft Windows\nВерсия 6.1 (сборка 7601: Service Pack 1)\n© Корпорация Майкрософт (Microsoft Corporation), 2009. Все права защищены.\n\nЭтот продукт лицензирован в соответствии с условиями лицензионного соглашения на использование программного обеспечения корпорации Майкрософт, предоставленного: Юрчик",
			"notepad", ["ОК"], Callable(), window)


func _new() -> void:
	if dirty:
		_ask_save(func() -> void: _reset())
	else:
		_reset()


func _reset() -> void:
	file = null
	edit.text = ""
	dirty = false
	_update_title()


func save(then: Callable = Callable()) -> void:
	if file == null:
		save_as(then)
		return
	file["text"] = edit.text
	fs.save_text(file["parent"], file["name"], edit.text)
	dirty = false
	if then.is_valid():
		then.call()


func save_as(then: Callable = Callable()) -> void:
	var dlg := W7SaveDialog.new().setup(desktop, _file_name() if file != null else "*.txt")
	dlg.saved.connect(func(folder: Dictionary, fname: String) -> void:
		file = fs.save_text(folder, fname, edit.text)
		dirty = false
		_update_title()
		if then.is_valid():
			then.call())
	desktop.call("open_dialog", dlg, "Сохранение", Vector2(560, 380), window)


func _ask_save(then: Callable) -> void:
	var done := func(b: String) -> void:
		match b:
			"Сохранить": save(then)
			"Не сохранять": then.call()
	desktop.call("message", "Блокнот", "Сохранить изменения в файле \"%s\"?" % _file_name(), "",
			["Сохранить", "Не сохранять", "Отмена"], done, window)


## Окно хочет закрыться: если текст не сохранён — спросить.
func can_close() -> bool:
	if not dirty or _closing:
		return true
	_ask_save(func() -> void:
		_closing = true
		window.close())
	return false
