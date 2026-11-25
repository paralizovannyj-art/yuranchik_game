## Windows 7 на компе Юрчика (внутри SubViewport, см. scripts/world/pc_seat.gd).
## Экран 1280×1024, Windows — на 125 % (как «Средний» размер в настройках экрана), поэтому всё здесь
## в логических пикселях 1024×820. Обои, значки (Компьютер, Корзина, Google Chrome), панель задач,
## «Пуск», окна (Проводник, Блокнот, Chrome), меню, сообщения и звуки Windows.
## Детали — в scripts/pc/win7/.
class_name PcDesktop
extends Control

signal sound(name: String)         ## звук Windows (pc_seat играет его из колонок компа)
signal shut_down                   ## «Завершение работы» — комп гаснет

const WALLPAPER: Texture2D = preload("res://assets/pc/win7/wallpaper.jpg")
const CELL := Vector2(76, 86)      ## клетка значка на рабочем столе

var fs := W7Fs.new()
var cursor: Control                ## PcCursor (его создаёт pc_seat)
var booted := false
var _icons: Control
var _win_layer: Control
var _taskbar: W7Taskbar
var _start: W7StartMenu
var _menus: Control
var _boot: W7Boot
var _active: W7Window
var _icon_items: Array = []        ## [Rect2, узел]
var _icon_sel: Array = []
var _icon_hover := -1
var _band_from := Vector2.ZERO
var _band := false
var _band_rect := Rect2()
var _rename: LineEdit
var _renaming: Variant = null
var _busy_left := 0.0
var _cascade := 0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = W7.theme()
	var wp := TextureRect.new()
	wp.texture = WALLPAPER
	wp.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	wp.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	wp.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	wp.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(wp)
	_icons = Control.new()
	_icons.name = "Icons"
	_icons.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_icons.focus_mode = Control.FOCUS_ALL
	_icons.draw.connect(_draw_icons)
	_icons.gui_input.connect(_icons_input)
	add_child(_icons)
	_rename = LineEdit.new()
	_rename.visible = false
	_rename.alignment = HORIZONTAL_ALIGNMENT_CENTER
	_rename.text_submitted.connect(func(_t: String) -> void: _finish_rename())
	_rename.focus_exited.connect(_finish_rename)
	_icons.add_child(_rename)
	_win_layer = Control.new()
	_win_layer.name = "Windows"
	_win_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_win_layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_win_layer)
	_taskbar = W7Taskbar.new()
	_taskbar.name = "Taskbar"
	_taskbar.desktop = self
	_taskbar.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	_taskbar.offset_top = -W7Taskbar.H
	add_child(_taskbar)
	_start = W7StartMenu.new()
	_start.name = "StartMenu"
	_start.desktop = self
	_start.visible = false
	add_child(_start)
	_menus = Control.new()
	_menus.name = "Menus"
	_menus.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_menus.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_menus)
	_boot = W7Boot.new()
	_boot.name = "Boot"
	add_child(_boot)
	_boot.show_mode("black")
	fs.changed.connect(_layout_icons)
	resized.connect(_on_resized)
	_on_resized()


func _on_resized() -> void:
	_start.position = Vector2(0, size.y - W7Taskbar.H - W7StartMenu.H)
	_layout_icons()


func _process(delta: float) -> void:
	if _busy_left > 0.0:
		_busy_left -= delta
		if cursor:
			cursor.set("busy", _busy_left > 0.0)


# ---------- загрузка и выключение ----------

## Комп включили: «Запуск Windows» → «Добро пожаловать» (звук входа) → рабочий стол.
func boot() -> void:
	booted = false
	_boot.show_mode("black")
	if cursor:
		cursor.visible = false                # на «Запуске Windows» курсора нет
	await get_tree().create_timer(1.6).timeout
	_boot.show_mode("starting")
	await get_tree().create_timer(4.2).timeout
	_boot.show_mode("black")
	await get_tree().create_timer(0.5).timeout
	_boot.show_mode("welcome", "Добро пожаловать")
	if cursor:
		cursor.visible = true
	await get_tree().create_timer(1.2).timeout
	play("logon")
	await get_tree().create_timer(1.6).timeout
	_boot.show_mode("black")
	await get_tree().create_timer(0.35).timeout
	_boot.show_mode("")
	booted = true
	busy(1.8)
	_layout_icons()


func shutdown(reboot := false) -> void:
	if not booted:
		return
	booted = false
	close_menus()
	close_start()
	for w: W7Window in windows():
		w.queue_free()
	_active = null
	_boot.show_mode("welcome", "Завершение работы")
	play("shutdown")
	await get_tree().create_timer(2.6).timeout
	_boot.show_mode("black")
	await get_tree().create_timer(0.6).timeout
	if reboot:
		boot()
	else:
		shut_down.emit()


func play(name: String) -> void:
	sound.emit(name)


## Курсор «занят» (стрелка с кольцом) на t секунд — как при запуске программ.
func busy(t := 0.8) -> void:
	_busy_left = maxf(_busy_left, t)
	if cursor:
		cursor.set("busy", true)


# ---------- окна ----------

func work_area() -> Rect2:
	return Rect2(0, 0, size.x, size.y - W7Taskbar.H)


func windows() -> Array:
	var out := []
	for c in _win_layer.get_children():
		if c is W7Window and not c.is_queued_for_deletion() and c.mouse_filter != Control.MOUSE_FILTER_IGNORE:
			out.append(c)
	return out


func windows_of(app: String) -> Array:
	return windows().filter(func(w: W7Window) -> bool: return w.app_id == app and w.modal_for == null)


func active_window() -> W7Window:
	return _active if is_instance_valid(_active) else null


func add_window(w: W7Window, app: String, modal_for: W7Window = null) -> W7Window:
	w.desktop = self
	w.app_id = app
	w.modal_for = modal_for
	w.closed.connect(_on_window_closed)
	var area := work_area()
	if modal_for:
		w.position = (modal_for.position + modal_for.size * 0.5 - w.size * 0.5).round()
	else:
		w.position = Vector2(60 + _cascade * 26, 30 + _cascade * 26)
		_cascade = (_cascade + 1) % 8
	w.position.x = clampf(w.position.x, 0.0, maxf(area.size.x - w.size.x, 0.0))
	w.position.y = clampf(w.position.y, 0.0, maxf(area.size.y - w.size.y, 0.0))
	_win_layer.add_child(w)
	w.pop_in()
	activate(w)
	return w


func activate(w: W7Window) -> void:
	if w == null or not is_instance_valid(w):
		return
	if w.minimized:
		w.restore()
	_win_layer.move_child(w, -1)
	# диалоги этого окна — поверх него
	for d: W7Window in windows():
		if d.modal_for == w:
			_win_layer.move_child(d, -1)
			w = d
	for o: W7Window in windows():
		o.set_active(o == w)
	_active = w
	refresh_taskbar()


func _on_window_closed(w: W7Window) -> void:
	if w == _active:
		_active = null
		if w.modal_for and is_instance_valid(w.modal_for):
			activate(w.modal_for)
		else:
			_activate_top(w)
	refresh_taskbar.call_deferred()


func _activate_top(except: W7Window = null) -> void:
	var ws := windows()
	for i in range(ws.size() - 1, -1, -1):
		var w: W7Window = ws[i]
		if w != except and not w.minimized:
			activate(w)
			return
	_active = null
	for w: W7Window in ws:
		w.set_active(false)
	refresh_taskbar()


func on_window_minimized(w: W7Window) -> void:
	if w == _active:
		_activate_top(w)
	refresh_taskbar()


func refresh_taskbar() -> void:
	if _taskbar:
		_taskbar.refresh()


func taskbar_point(w: W7Window) -> Vector2:
	return _taskbar.app_point(w.app_id)


func taskbar_click(app: String) -> void:
	close_start()
	var wins := windows_of(app)
	if wins.is_empty():
		launch(app)
		return
	if wins.size() == 1:
		var w: W7Window = wins[0]
		if w == _active and not w.minimized:
			w.minimize()
		else:
			activate(w)
		return
	var i := wins.find(_active)
	activate(wins[(i + 1) % wins.size()])


func show_desktop() -> void:
	close_start()
	var any := false
	for w: W7Window in windows():
		if not w.minimized:
			any = true
			w.minimize()
	if not any:
		for w: W7Window in windows():
			w.restore()
		_activate_top()


# ---------- программы ----------

func launch(app: String, arg: Variant = null) -> W7Window:
	if not booted:
		return null
	busy(0.7)
	match app:
		"explorer", "computer":
			var target: Dictionary = arg if arg is Dictionary else (fs.computer if app == "computer" else fs.libraries)
			return _open_explorer(target)
		"notepad":
			var np := W7Notepad.new().setup(self, arg)
			var w := W7Window.new().setup("Безымянный - Блокнот", "notepad", Vector2(640, 440), np)
			np.window = w
			return add_window(w, "notepad")
		"chrome":
			var ch := W7Chrome.new().setup(self)
			var w2 := W7Window.new().setup("Новая вкладка - Google Chrome", "chrome", Vector2(900, 650), ch)
			ch.window = w2
			return add_window(w2, "chrome")
	return null


func _open_explorer(target: Dictionary) -> W7Window:
	play("nav")
	var ex := W7Explorer.new()
	ex.setup(self, target)
	var w := W7Window.new().setup(target["name"], target["icon"], Vector2(780, 540), ex)
	w.show_title = false
	w.glass_top = W7Explorer.NAV_H
	w.min_size = Vector2(500, 300)
	ex.window = w
	return add_window(w, "explorer")


## Пункты справа в «Пуске».
func open_place(go: String) -> void:
	match go:
		"user": launch("explorer", fs.user)
		"computer": launch("computer")
		"games": launch("explorer", _virtual("Игры", "games", []))
		"control": launch("explorer", _virtual("Панель управления", "control", ["Администрирование", "Брандмауэр Windows",
				"Дата и время", "Диспетчер устройств", "Звук", "Персонализация", "Программы и компоненты", "Система",
				"Учетные записи пользователей", "Центр управления сетями и общим доступом", "Шрифты", "Экран"]))
		"devices": launch("explorer", _virtual("Устройства и принтеры", "devices", ["ЮРЧИК-ПК", "Монитор PnP (стандартный)",
				"USB-клавиатура", "USB-мышь", "Fax", "Microsoft XPS Document Writer"]))
		_:
			if go.begins_with("lib:"):
				launch("explorer", fs.libraries["children"][int(go.substr(4))])


func _virtual(name: String, icon: String, entries: Array) -> Dictionary:
	var n := {"name": name, "kind": "cpl_root" if not entries.is_empty() else "folder", "icon": icon, "children": [],
			"parent": null, "system": true, "text": "", "date": ""}
	for e: String in entries:
		var ic := icon
		match e:
			"ЮРЧИК-ПК": ic = "computer"
			"Система", "Экран", "Монитор PnP (стандартный)": ic = "computer"
			"Звук": ic = "speaker"
			"Шрифты": ic = "folder"
			"Центр управления сетями и общим доступом": ic = "network"
			"Учетные записи пользователей": ic = "user"
		(n["children"] as Array).append({"name": e, "kind": "cpl", "icon": ic, "children": [], "parent": n,
				"system": true, "text": "", "date": ""})
	return n


## Окно-сообщение. icon: error / warning / warning_q / question / любая иконка / "".
func message(title: String, text: String, icon := "", buttons: Array = ["ОК"], done: Callable = Callable(), parent: W7Window = null) -> void:
	var mb := W7MsgBox.new().setup(text, icon, buttons, done)
	var sz := mb.wanted_size()
	var w := W7Window.new().setup(title, "", sz + Vector2(W7Window.B * 2, W7Window.CAP + W7Window.B), mb)
	w.has_min = false
	w.has_max = false
	mb.window = w
	add_window(w, parent.app_id if parent else "explorer", parent)
	match icon:
		"error": play("critical")
		"warning": play("exclamation")


func open_dialog(client: Control, title: String, sz: Vector2, parent: W7Window) -> void:
	var w := W7Window.new().setup(title, "", sz, client)
	w.has_min = false
	w.has_max = false
	client.set("window", w)
	add_window(w, parent.app_id if parent else "explorer", parent)


# ---------- меню и «Пуск» ----------

func popup_menu(items: Array, pos: Vector2) -> W7Menu:
	close_menus()
	var m := W7Menu.new().setup(items, self)
	_menus.add_child(m)
	pos.x = clampf(pos.x, 0.0, size.x - m.size.x)
	if pos.y + m.size.y > size.y:
		pos.y = pos.y - m.size.y
	m.position = pos.round()
	return m


func close_menus() -> void:
	for c in _menus.get_children():
		c.queue_free()


func start_open() -> bool:
	return _start != null and _start.visible


func toggle_start() -> void:
	if _start.visible:
		close_start()
	else:
		close_menus()
		_start.open()
		move_child(_start, _menus.get_index() - 1)


func close_start() -> void:
	if _start and _start.visible:
		_start.close()
		refresh_taskbar()


# ---------- общий ввод: активировать окно, закрыть меню, «дзинь» мимо диалога ----------

func _input(event: InputEvent) -> void:
	if not booted:
		get_viewport().set_input_as_handled()
		return
	if event is InputEventKey and event.pressed and event.keycode == KEY_META and not event.echo:
		toggle_start()
		get_viewport().set_input_as_handled()
		return
	if not (event is InputEventMouseButton and event.pressed):
		return
	var p: Vector2 = event.position
	# открытые меню: щелчок мимо — закрыть
	if _menus.get_child_count() > 0:
		var inside := false
		for m in _menus.get_children():
			if (m as Control).get_global_rect().has_point(p):
				inside = true
		if not inside:
			close_menus()
			get_viewport().set_input_as_handled()
		return
	if _start.visible:
		var r := _start.get_global_rect()
		r.position.y -= 26.0
		r.size.y += 26.0
		if not r.has_point(p) and not (p.y > size.y - W7Taskbar.H and p.x < W7Taskbar.ORB_W):
			close_start()
			get_viewport().set_input_as_handled()
		return
	# какое окно под курсором — сделать активным; занятое диалогом — «дзинь» и мигнуть диалогом
	var ws := windows()
	for i in range(ws.size() - 1, -1, -1):
		var w: W7Window = ws[i]
		if w.visible and not w.minimized and w.get_global_rect().has_point(p):
			for d: W7Window in ws:
				if d.modal_for == w:
					activate(w)
					d.flash()
					play("default")
					get_viewport().set_input_as_handled()
					return
			if w != _active:
				activate(w)
			return
	if p.y < size.y - W7Taskbar.H:
		for w: W7Window in ws:
			w.set_active(false)
		_active = null
		refresh_taskbar()


# ---------- значки на рабочем столе ----------

func _desktop_items() -> Array:
	return [fs.computer, fs.recycle] + (fs.desktop["children"] as Array)


func _layout_icons() -> void:
	_icon_items.clear()
	var y := 4.0
	var x := 2.0
	var area := work_area()
	for n: Dictionary in _desktop_items():
		_icon_items.append([Rect2(x, y, CELL.x, CELL.y), n])
		y += CELL.y + 2.0
		if y + CELL.y > area.size.y:
			y = 4.0
			x += CELL.x + 2.0
	_icon_sel = _icon_sel.filter(func(n: Dictionary) -> bool:
		for it: Array in _icon_items:
			if is_same(it[1], n):
				return true
		return false)
	if _icons:
		_icons.queue_redraw()


func _draw_icons() -> void:
	if not booted:
		return
	var ci := _icons.get_canvas_item()
	var focused := _icons.has_focus() or _rename.has_focus()
	for i in _icon_items.size():
		var r: Rect2 = _icon_items[i][0]
		var n: Dictionary = _icon_items[i][1]
		var sel := W7Fs.has_node(_icon_sel, n)
		var hr := r.grow_individual(-2, 0, -2, 0)
		if sel:
			var a := 0.4 if focused else 0.22
			W7.fill(ci, hr, 3, [[0.0, Color(0.70, 0.85, 1.0, a)], [1.0, Color(0.55, 0.75, 1.0, a)]])
			W7.stroke(ci, hr, 3, Color(0.75, 0.9, 1.0, 0.7 if focused else 0.45))
		elif i == _icon_hover:
			W7.fill(ci, hr, 3, [[0.0, Color(0.75, 0.88, 1.0, 0.22)], [1.0, Color(0.6, 0.8, 1.0, 0.18)]])
			W7.stroke(ci, hr, 3, Color(0.8, 0.92, 1.0, 0.45))
		var ic := W7.icon(n["icon"], 48)
		if ic:
			_icons.draw_texture_rect(ic, Rect2(r.position + Vector2((r.size.x - 48) * 0.5, 4), Vector2(48, 48)), false)
		if n["kind"] == "app":   # стрелка ярлыка
			var sp := r.position + Vector2((r.size.x - 48) * 0.5, 40)
			_icons.draw_rect(Rect2(sp, Vector2(12, 12)), Color.WHITE)
			_icons.draw_rect(Rect2(sp, Vector2(12, 12)), Color("7f7f7f"), false, 1.0)
			_icons.draw_line(sp + Vector2(3, 9), sp + Vector2(9, 3), Color("1f5aa6"), 1.6, true)
			_icons.draw_colored_polygon(PackedVector2Array([sp + Vector2(5, 3), sp + Vector2(9.5, 2.5), sp + Vector2(9, 7)]), Color("1f5aa6"))
		if _renaming != null and is_same(n, _renaming):
			continue
		var label: String = n["name"]
		var lines := _wrap(label, CELL.x - 6)
		var ly := r.position.y + 66
		for l: String in lines:
			W7.shadow_text(_icons, Vector2(r.position.x + 1, ly), l, 12, Color.WHITE, CELL.x - 2, HORIZONTAL_ALIGNMENT_CENTER)
			ly += 15.0
	if _band:
		var br := _band_rect.abs()
		_icons.draw_rect(br, Color(0.2, 0.45, 0.85, 0.25))
		_icons.draw_rect(br, Color(0.2, 0.45, 0.85, 0.8), false, 1.0)


func _wrap(text: String, w: float) -> Array:
	var words := text.split(" ")
	var lines := []
	var cur := ""
	for word: String in words:
		var t := word if cur == "" else cur + " " + word
		if W7.text_width(t) <= w or cur == "":
			cur = t
		else:
			lines.append(cur)
			cur = word
	lines.append(cur)
	if lines.size() > 2:
		lines = [lines[0], lines[1] + "..."]
	return lines


func _icon_at(p: Vector2) -> int:
	for i in _icon_items.size():
		if (_icon_items[i][0] as Rect2).grow_individual(-8, -2, -8, -4).has_point(p):
			return i
	return -1


func _open_icon(n: Dictionary) -> void:
	match n["kind"]:
		"computer", "recycle", "folder":
			launch("explorer", n)
		"file":
			launch("notepad", n)
		"app":
			launch(n["app"])


func _icons_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		if _band:
			_band_rect = Rect2(_band_from, event.position - _band_from)
			_icon_sel.clear()
			for it: Array in _icon_items:
				if _band_rect.abs().intersects((it[0] as Rect2).grow(-10)):
					_icon_sel.append(it[1])
			_icons.queue_redraw()
			return
		var h := _icon_at(event.position)
		if h != _icon_hover:
			_icon_hover = h
			_icons.queue_redraw()
	elif event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		var h := _icon_at(mb.position)
		if mb.pressed and mb.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT]:
			_icons.grab_focus()
			if h >= 0:
				var n: Dictionary = _icon_items[h][1]
				if not W7Fs.has_node(_icon_sel, n) or mb.button_index == MOUSE_BUTTON_LEFT:
					_icon_sel = [n]
				if mb.double_click and mb.button_index == MOUSE_BUTTON_LEFT:
					_open_icon(n)
			else:
				_icon_sel.clear()
				if mb.button_index == MOUSE_BUTTON_LEFT:
					_band = true
					_band_from = mb.position
					_band_rect = Rect2(mb.position, Vector2.ZERO)
			_icons.queue_redraw()
		elif not mb.pressed:
			if mb.button_index == MOUSE_BUTTON_LEFT and _band:
				_band = false
				_icons.queue_redraw()
			elif mb.button_index == MOUSE_BUTTON_RIGHT:
				_desktop_context(mb.position, h)
	elif event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_DELETE:
				_delete_selected()
			KEY_F2:
				if _icon_sel.size() == 1:
					_start_rename(_icon_sel[0])
			KEY_ENTER, KEY_KP_ENTER:
				for n: Dictionary in _icon_sel:
					_open_icon(n)
			KEY_F5:
				_layout_icons()


func _desktop_context(p: Vector2, h: int) -> void:
	if h >= 0:
		var n: Dictionary = _icon_items[h][1]
		var items: Array
		match n["kind"]:
			"computer":
				items = [{"text": "Открыть", "bold": true, "cb": func() -> void: _open_icon(n)},
					{"text": "Управление", "disabled": true}, {"sep": true},
					{"text": "Подключить сетевой диск...", "disabled": true}, {"text": "Отключить сетевой диск...", "disabled": true},
					{"sep": true}, {"text": "Создать ярлык", "disabled": true}, {"text": "Удалить", "disabled": true},
					{"text": "Переименовать", "disabled": true}, {"sep": true}, {"text": "Свойства", "disabled": true}]
			"recycle":
				var empty := (fs.recycle["children"] as Array).is_empty()
				items = [{"text": "Открыть", "bold": true, "cb": func() -> void: _open_icon(n)},
					{"text": "Очистить корзину", "disabled": empty, "cb": _ask_empty_bin}, {"sep": true},
					{"text": "Создать ярлык", "disabled": true}, {"text": "Переименовать", "disabled": true},
					{"sep": true}, {"text": "Свойства", "disabled": true}]
			_:
				items = [{"text": "Открыть", "bold": true, "cb": func() -> void: _open_icon(n)}, {"sep": true},
					{"text": "Вырезать", "disabled": true}, {"text": "Копировать", "disabled": true}, {"sep": true},
					{"text": "Создать ярлык", "disabled": true},
					{"text": "Удалить", "cb": _delete_selected},
					{"text": "Переименовать", "cb": func() -> void: _start_rename(n)},
					{"sep": true}, {"text": "Свойства", "disabled": true}]
		popup_menu(items, p)
		return
	popup_menu([
		{"text": "Вид", "sub": [{"text": "Крупные значки", "disabled": true}, {"text": "Обычные значки", "checked": true},
				{"text": "Мелкие значки", "disabled": true}, {"sep": true},
				{"text": "Упорядочить значки автоматически", "disabled": true},
				{"text": "Выровнять значки по сетке", "checked": true}, {"sep": true},
				{"text": "Отображать значки рабочего стола", "checked": true},
				{"text": "Отображать гаджеты рабочего стола", "checked": true}]},
		{"text": "Сортировка", "sub": [{"text": "Имя", "disabled": true}, {"text": "Размер", "disabled": true},
				{"text": "Тип элемента", "disabled": true}, {"text": "Дата изменения", "disabled": true}]},
		{"text": "Обновить", "cb": _layout_icons},
		{"sep": true},
		{"text": "Вставить", "disabled": true},
		{"text": "Вставить ярлык", "disabled": true},
		{"sep": true},
		{"text": "Создать", "sub": [
			{"text": "Папку", "icon": "folder", "cb": func() -> void: _create_on_desktop("folder")},
			{"text": "Ярлык", "disabled": true},
			{"sep": true},
			{"text": "Текстовый документ", "icon": "txt", "cb": func() -> void: _create_on_desktop("file")}]},
		{"sep": true},
		{"text": "Разрешение экрана", "icon": "computer", "disabled": true},
		{"text": "Гаджеты", "disabled": true},
		{"text": "Персонализация", "icon": "control", "disabled": true},
	], p)


func _create_on_desktop(kind: String) -> void:
	var n := fs.create(fs.desktop, kind)
	_icon_sel = [n]
	_layout_icons()
	_start_rename(n)


func _delete_selected() -> void:
	var del := _icon_sel.filter(func(n: Dictionary) -> bool: return n["kind"] in ["file", "folder", "app"])
	if del.is_empty():
		return
	var text := "Вы действительно хотите переместить этот %s в корзину?\n\n%s" % ["ярлык" if del[0]["kind"] == "app" else ("файл" if del[0]["kind"] == "file" else "объект"), del[0]["name"]] \
			if del.size() == 1 else "Вы действительно хотите переместить эти объекты (%d) в корзину?" % del.size()
	var done := func(b: String) -> void:
		if b == "Да":
			for n: Dictionary in del:
				fs.to_recycle(n)
	message("Удаление " + ("файла" if del.size() == 1 else "нескольких элементов"), text, "question", ["Да", "Нет"], done)


func _ask_empty_bin() -> void:
	var cnt := (fs.recycle["children"] as Array).size()
	var done := func(b: String) -> void:
		if b == "Да":
			play("recycle")
			fs.empty_recycle()
	message("Удаление нескольких элементов" if cnt > 1 else "Удаление файла",
			"Вы действительно хотите безвозвратно удалить эти объекты (%d)?" % cnt if cnt > 1
			else "Вы действительно хотите безвозвратно удалить этот объект?", "warning_q", ["Да", "Нет"], done)


func _start_rename(n: Dictionary) -> void:
	for it: Array in _icon_items:
		if is_same(it[1], n):
			var r: Rect2 = it[0]
			_renaming = n
			_rename.position = r.position + Vector2(0, 54)
			_rename.size = Vector2(r.size.x, 22)
			_rename.text = n["name"]
			_rename.visible = true
			_rename.grab_focus()
			_rename.select(0, (n["name"] as String).get_basename().length() if n["kind"] == "file" else (n["name"] as String).length())
			_icons.queue_redraw()
			return


func _finish_rename() -> void:
	if _renaming == null:
		return
	var n: Dictionary = _renaming
	_renaming = null
	_rename.visible = false
	var t := _rename.text.strip_edges()
	if t != "" and t != n["name"]:
		if n["kind"] == "file" and t.get_extension() == "":
			t += ".txt"
		fs.rename(n, t)
	_layout_icons()
	_icons.grab_focus()
