## Проводник Windows 7: «Компьютер», папки, библиотеки, Корзина.
## Сверху на стекле — «Назад / Вперёд», адресная строка с «хлебными крошками» и поиск; ниже — панель команд,
## слева — область переходов, справа — содержимое, внизу — область сведений.
## Щелчок — выделить, двойной — открыть; Del — в Корзину, F2 — переименовать, Backspace — назад.
class_name W7Explorer
extends Control

const NAV_H := 34.0
const CMD_H := 30.0
const DET_H := 52.0
const PANE_W := 182.0
const ROW_H := 22.0
const HEAD_H := 25.0
const COLS := [["Имя", 260.0], ["Дата изменения", 130.0], ["Тип", 130.0], ["Размер", 80.0]]
const BIN_COLS := [["Имя", 200.0], ["Исходное расположение", 190.0], ["Дата удаления", 130.0], ["Размер", 70.0]]

var desktop: Control
var fs: W7Fs
var window: W7Window
var loc: Dictionary
var history: Array = []
var hist_i := -1
var selected: Variant = null
var search: LineEdit
var _view: Control
var _bars: Control
var _scroll := 0.0
var _hover_item := -1
var _hover_nav := -1
var _hover_ui := ""
var _items: Array = []          ## [Rect2, узел или null, вид]
var _nav_rows: Array = []       ## [Rect2, цель или null, текст, значок, отступ]
var _crumbs: Array = []         ## [Rect2, узел]
var _cmds: Array = []           ## [Rect2, текст, Callable]
var _rename: LineEdit
var _renaming: Variant = null


func setup(p_desktop: Control, p_loc: Dictionary) -> W7Explorer:
	desktop = p_desktop
	fs = desktop.get("fs")
	loc = p_loc
	return self


func _ready() -> void:
	clip_contents = true
	mouse_filter = Control.MOUSE_FILTER_STOP
	focus_mode = Control.FOCUS_ALL
	_bars = Control.new()
	_bars.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bars.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_bars.draw.connect(_draw_bars)
	add_child(_bars)
	_view = Control.new()
	_view.clip_contents = true
	_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_view.draw.connect(_draw_view)
	add_child(_view)
	search = LineEdit.new()
	search.right_icon = W7.icon("search", 16)
	search.text_changed.connect(func(_t: String) -> void:
		_scroll = 0.0
		_relayout())
	add_child(search)
	_rename = LineEdit.new()
	_rename.visible = false
	_rename.text_submitted.connect(func(_t: String) -> void: _finish_rename())
	_rename.focus_exited.connect(_finish_rename)
	add_child(_rename)
	resized.connect(_relayout)
	fs.changed.connect(_on_fs_changed)
	_go(loc, true)


func _on_fs_changed() -> void:
	if selected != null and not is_same(selected["parent"], fs.real(loc)) and not is_same(selected["parent"], loc):
		selected = null
	_relayout()


func _exit_tree() -> void:
	if fs.changed.is_connected(_on_fs_changed):
		fs.changed.disconnect(_on_fs_changed)


# ---------- переходы ----------

func _go(target: Dictionary, push := true) -> void:
	loc = target
	if push:
		history.resize(hist_i + 1)
		history.append(target)
		hist_i = history.size() - 1
	selected = null
	_scroll = 0.0
	if search:
		search.text = ""
		search.placeholder_text = "Поиск: %s" % loc["name"]
	if window:
		window.set_title(loc["name"])
		window.icon_name = loc["icon"]
	_relayout()


func navigate(target: Dictionary) -> void:
	desktop.call("play", "nav")
	_go(target)


func back() -> void:
	if hist_i > 0:
		hist_i -= 1
		desktop.call("play", "nav")
		_go(history[hist_i], false)


func forward() -> void:
	if hist_i < history.size() - 1:
		hist_i += 1
		desktop.call("play", "nav")
		_go(history[hist_i], false)


func open_item(n: Dictionary) -> void:
	match n["kind"]:
		"folder", "drive", "library", "computer", "libraries", "recycle", "network":
			navigate(n)
		"dvd":
			desktop.call("message", "Вставьте диск", "Вставьте диск в устройство \"%s\"." % n["name"], "error", ["ОК"], Callable(), window)
		"file":
			desktop.call("launch", "notepad", n)
		"app":
			desktop.call("launch", n["app"])
		"cpl":
			desktop.call("busy", 0.6)


func _writable() -> bool:
	var r := fs.real(loc)
	if is_same(r, fs.desktop):
		return true
	return W7Fs.has_node(fs.chain(r), fs.user) and not is_same(r, fs.user)


# ---------- раскладка ----------

func _relayout() -> void:
	if not is_inside_tree():
		return
	var w := size.x
	search.position = Vector2(w - 206, 5)
	search.size = Vector2(200, 24)
	var body := Rect2(PANE_W + 1, NAV_H + CMD_H, w - PANE_W - 1, size.y - NAV_H - CMD_H - DET_H)
	_view.position = body.position
	_view.size = body.size
	_layout_nav()
	_layout_items()
	_layout_cmds()
	_bars.queue_redraw()
	_view.queue_redraw()


func _list() -> Array:
	var all: Array = fs.items(loc)
	var q := search.text.strip_edges().to_lower() if search else ""
	if q == "":
		return all
	return all.filter(func(n: Dictionary) -> bool: return (n["name"] as String).to_lower().contains(q))


func _view_kind() -> String:
	match loc["kind"]:
		"computer": return "computer"
		"libraries": return "tiles"
		"cpl_root": return "icons"
		"recycle": return "bin"
	return "details"


func _layout_items() -> void:
	_items.clear()
	var w := _view.size.x
	var y := -_scroll
	match _view_kind():
		"computer":
			for g: Array in [["Жёсткие диски", ["drive"]], ["Устройства со съёмными носителями", ["dvd"]]]:
				var group := _list().filter(func(n: Dictionary) -> bool: return (g[1] as Array).has(n["kind"]))
				if group.is_empty():
					continue
				_items.append([Rect2(10, y + 8, w - 20, 20), null, "group:%s (%d)" % [g[0], group.size()]])
				y += 32.0
				var x := 18.0
				for n: Dictionary in group:
					_items.append([Rect2(x, y, 250, 56), n, "tile"])
					x += 256.0
					if x + 250 > w:
						x = 18.0
						y += 60.0
				y += 64.0
		"tiles", "icons":
			var x := 12.0
			y += 10.0
			var tw := 250.0 if _view_kind() == "tiles" else 230.0
			var th := 56.0 if _view_kind() == "tiles" else 40.0
			for n: Dictionary in _list():
				_items.append([Rect2(x, y, tw, th), n, "tile" if _view_kind() == "tiles" else "icon"])
				x += tw + 6.0
				if x + tw > w:
					x = 12.0
					y += th + 4.0
		_:
			if loc["kind"] == "library":
				y += 58.0
			if loc["kind"] == "network":
				y += 30.0
			y += HEAD_H
			for n: Dictionary in _list():
				_items.append([Rect2(0, y, w, ROW_H), n, "row"])
				y += ROW_H
	if _rename.visible and _renaming != null:
		_place_rename()


func _content_height() -> float:
	var h := 0.0
	for it: Array in _items:
		h = maxf(h, (it[0] as Rect2).end.y + _scroll)
	return h + 8.0


func _layout_nav() -> void:
	_nav_rows.clear()
	var y := NAV_H + CMD_H + 8.0
	var groups := [
		[["Избранное", "favorites", fs.favorites], [["Загрузки", "downloads", fs.downloads], ["Рабочий стол", "desktop", fs.desktop], ["Недавние места", "recent", fs.recent]]],
		[["Библиотеки", "libraries", fs.libraries], []],
		[["Компьютер", "computer", fs.computer], [["Локальный диск (C:)", "drive_win", fs.c_drive]]],
		[["Сеть", "network", fs.network], []],
	]
	for i in 4:
		var libs: Array = groups[1][1]
		if i == 1:
			for l: Dictionary in fs.libraries["children"]:
				libs.append([l["name"], l["icon"], l])
		var head: Array = groups[i][0]
		_nav_rows.append([Rect2(4, y, PANE_W - 8, 22), head[2], head[0], head[1], 0.0])
		y += 22.0
		for s: Array in groups[i][1]:
			_nav_rows.append([Rect2(4, y, PANE_W - 8, 22), s[2], s[0], s[1], 18.0])
			y += 22.0
		y += 14.0


func _layout_cmds() -> void:
	_cmds.clear()
	var defs: Array = [["Упорядочить ▾", Callable()]]
	match loc["kind"]:
		"computer":
			defs.append_array([["Свойства системы", Callable()], ["Удалить или изменить программу", Callable()],
					["Подключить сетевой диск", Callable()], ["Открыть панель управления", func() -> void: desktop.call("open_place", "control")]])
		"recycle":
			if not (fs.recycle["children"] as Array).is_empty():
				defs.append_array([["Очистить корзину", _ask_empty_bin], ["Восстановить все объекты", fs.restore_all]])
		"network", "libraries", "cpl_root":
			pass
		_:
			if selected != null:
				defs.append(["Открыть", func() -> void: open_item(selected)])
			defs.append_array([["Добавить в библиотеку ▾", Callable()], ["Общий доступ ▾", Callable()]])
			if _writable():
				defs.append(["Новая папка", func() -> void: _create("folder")])
	var x := 6.0
	for d: Array in defs:
		var tw := W7.text_width(d[0]) + 18.0
		if x + tw > size.x - 36.0:
			break
		_cmds.append([Rect2(x, NAV_H + 3, tw, CMD_H - 6), d[0], d[1]])
		x += tw + 2.0


# ---------- рисование ----------

func _draw() -> void:
	# фон под панелями (кроме полосы адреса — она на стекле окна)
	draw_rect(Rect2(0, NAV_H + CMD_H, size.x, size.y - NAV_H - CMD_H), Color.WHITE)


func _draw_bars() -> void:
	var d := _bars
	var ci := d.get_canvas_item()
	var w := size.x
	# назад / вперёд: синие глянцевые кружки
	for k in 2:
		var c := Vector2(18 + k * 28, 17)
		var on := hist_i > 0 if k == 0 else hist_i < history.size() - 1
		var hv := _hover_ui == ("back" if k == 0 else "fwd")
		d.draw_circle(c, 12.5, Color(0, 0, 0, 0.45))
		var c0 := Color("1f5aa6") if on else Color("8d9aa8")
		var c1 := Color("6fb5f0") if on else Color("d1d8df")
		if hv and on:
			c0 = c0.lightened(0.2)
			c1 = c1.lightened(0.2)
		for s in 12:
			var t := float(s) / 11.0
			d.draw_circle(c + Vector2(0, t * 3.0), 11.5 * (1.0 - t * 0.55), c0.lerp(c1, t))
		d.draw_arc(c, 11.5, PI * 1.1, PI * 1.9, 12, Color(1, 1, 1, 0.5), 2.0, true)
		var dir := 1.0 if k == 0 else -1.0
		var pts := PackedVector2Array([c + Vector2(6 * dir, -1.5), c + Vector2(-1 * dir, -1.5), c + Vector2(-1 * dir, -5.5),
				c + Vector2(-7 * dir, 0), c + Vector2(-1 * dir, 5.5), c + Vector2(-1 * dir, 1.5), c + Vector2(6 * dir, 1.5)])
		d.draw_colored_polygon(pts, Color.WHITE if on else Color(1, 1, 1, 0.8))
	# адресная строка
	var ar := Rect2(68, 5, w - 68 - 214, 24)
	W7.fill(ci, ar, 0, [[0.0, Color(1, 1, 1, 0.92)], [1.0, Color(1, 1, 1, 0.92)]])
	d.draw_rect(ar, Color(0, 0, 0, 0.45), false, 1.0)
	var ic := W7.icon(loc["icon"], 16)
	if ic:
		d.draw_texture_rect(ic, Rect2(ar.position + Vector2(4, 4), Vector2(16, 16)), false)
	_crumbs.clear()
	var x := ar.position.x + 24.0
	var path := fs.chain(loc)
	if loc["kind"] == "library":
		path = [fs.libraries, loc]
	for n: Dictionary in path:
		_chev(d, Vector2(x + 4, ar.position.y + 12))
		x += 12.0
		var tw := W7.text_width(n["name"]) + 8.0
		var cr := Rect2(x, ar.position.y + 2, tw, 20)
		if _hover_ui == "crumb:%d" % _crumbs.size():
			W7.box(ci, cr, 2, [[0.0, "eaf6fd"], [1.0, "c8e6fb"]], "3c7fb1")
		d.draw_string(W7.FONT, Vector2(x + 4, ar.position.y + 17), n["name"], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.BLACK)
		_crumbs.append([cr, n])
		x += tw
	_chev(d, Vector2(x + 4, ar.position.y + 12))
	# обновить
	var rc := Vector2(ar.end.x - 12, ar.position.y + 12)
	d.draw_arc(rc, 5, PI * 0.2, PI * 1.7, 12, Color("2c6ab0"), 1.6, true)
	d.draw_colored_polygon(PackedVector2Array([rc + Vector2(3, -7), rc + Vector2(6, -2), rc + Vector2(1, -2)]), Color("2c6ab0"))
	# панель команд
	var cb := Rect2(0, NAV_H, w, CMD_H)
	W7.fill(ci, cb, 0, [[0.0, "f5f9fd"], [0.5, "eaf1fa"], [1.0, "dce7f5"]])
	d.draw_line(Vector2(0, cb.position.y + 0.5), Vector2(w, cb.position.y + 0.5), Color("ffffff"))
	d.draw_line(Vector2(0, cb.end.y - 0.5), Vector2(w, cb.end.y - 0.5), Color("a0afc3"))
	for c: Array in _cmds:
		var r: Rect2 = c[0]
		if _hover_ui == "cmd:" + c[1]:
			W7.box(ci, r, 3, [[0.0, Color(1, 1, 1, 0.7)], [1.0, Color(1, 1, 1, 0.3)]], Color(0.4, 0.55, 0.75, 0.6), Color(1, 1, 1, 0.8))
		d.draw_string(W7.FONT, r.position + Vector2(9, 16), c[1], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("1e395b"))
	var help := W7.icon("help", 16)
	if help:
		d.draw_texture_rect(help, Rect2(w - 26, NAV_H + 7, 16, 16), false)
	# область переходов
	var pane := Rect2(0, NAV_H + CMD_H, PANE_W, size.y - NAV_H - CMD_H - DET_H)
	d.draw_rect(pane, Color.WHITE)
	d.draw_line(Vector2(PANE_W + 0.5, pane.position.y), Vector2(PANE_W + 0.5, pane.end.y), Color("d6e5f5"))
	for i in _nav_rows.size():
		var row: Array = _nav_rows[i]
		var r: Rect2 = row[0]
		if is_same(row[1], loc):
			W7.box(ci, r, 2, [[0.0, "dcebfc"], [1.0, "c1dbfc"]], "7da2ce", "ebf4fd")
		elif i == _hover_nav:
			W7.box(ci, r, 2, [[0.0, "fafbfd"], [1.0, "ebf3fd"]], "b8d6fb", "fcfdfe")
		var ix: float = r.position.x + 6.0 + row[4]
		var nic := W7.icon(row[3], 16)
		if nic:
			d.draw_texture_rect(nic, Rect2(ix, r.position.y + 3, 16, 16), false)
		d.draw_string(W7.FONT, Vector2(ix + 22, r.position.y + 16), row[2], HORIZONTAL_ALIGNMENT_LEFT, PANE_W - ix - 26, 12, Color.BLACK)
	# область сведений
	var det := Rect2(0, size.y - DET_H, w, DET_H)
	W7.fill(ci, det, 0, [[0.0, "f9fbfe"], [1.0, "e2eaf5"]])
	d.draw_line(Vector2(0, det.position.y + 0.5), Vector2(w, det.position.y + 0.5), Color("c5d3e6"))
	var who: Dictionary = selected if selected != null else loc
	var dic := W7.icon(who["icon"], 48)
	if dic:
		d.draw_texture_rect(dic, Rect2(det.position + Vector2(14, 2), Vector2(48, 48)), false)
	var tx := det.position.x + 74
	if selected == null and loc["kind"] == "computer":
		d.draw_string(W7.FONT_BOLD, Vector2(tx, det.position.y + 20), "ЮРЧИК-ПК", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.BLACK)
		d.draw_string(W7.FONT, Vector2(tx + 90, det.position.y + 20), "Рабочая группа: WORKGROUP", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("5a677c"))
		d.draw_string(W7.FONT, Vector2(tx + 90, det.position.y + 38), "Память: 2,00 ГБ     Процессор: Intel(R) Pentium(R) Dual  CPU  E2180  @ 2.00GHz", HORIZONTAL_ALIGNMENT_LEFT, w - tx - 100, 12, Color("5a677c"))
	elif selected == null:
		d.draw_string(W7.FONT, Vector2(tx, det.position.y + 20), "Элементов: %d" % _list().size(), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.BLACK)
	else:
		d.draw_string(W7.FONT_BOLD, Vector2(tx, det.position.y + 20), selected["name"], HORIZONTAL_ALIGNMENT_LEFT, w - tx - 10, 12, Color.BLACK)
		var info := fs.type_text(selected)
		if selected["kind"] == "drive":
			info = "Локальный диск     Свободно: 37,1 ГБ     Общий размер: 74,5 ГБ"
		elif selected["kind"] == "dvd":
			info = "Дисковод компакт-дисков"
		elif selected["kind"] == "library":
			info = "Библиотека"
		elif selected["kind"] in ["file", "folder", "app"]:
			info = "%s     Дата изменения: %s" % [info, selected["date"]]
		d.draw_string(W7.FONT, Vector2(tx, det.position.y + 38), info, HORIZONTAL_ALIGNMENT_LEFT, w - tx - 10, 12, Color("5a677c"))


func _chev(d: Control, p: Vector2) -> void:
	d.draw_colored_polygon(PackedVector2Array([p + Vector2(-2, -3.5), p + Vector2(2, 0), p + Vector2(-2, 3.5)]), Color("3d3d3d"))


func _draw_view() -> void:
	var d := _view
	var ci := d.get_canvas_item()
	var w := d.size.x
	var kind := _view_kind()
	if loc["kind"] == "library":
		var lib_ic := W7.icon(loc["icon"], 48)
		d.draw_string(W7.FONT, Vector2(16, 26 - _scroll), "Библиотека \"%s\"" % loc["name"], HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color("1e3287"))
		d.draw_string(W7.FONT, Vector2(16, 46 - _scroll), "Включает: 2 места", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("1e3287"))
		d.draw_string(W7.FONT, Vector2(w - 150, 26 - _scroll), "Упорядочить:  Папка ▾", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("1e3287"))
		if lib_ic:
			pass
	if loc["kind"] == "network":
		var bar := Rect2(0, -_scroll, w, 26)
		d.draw_rect(bar, Color("ffffe1"))
		d.draw_line(Vector2(0, bar.end.y - 0.5), Vector2(w, bar.end.y - 0.5), Color("e2e1c4"))
		var wi := W7.icon("warning", 16)
		if wi:
			d.draw_texture_rect(wi, Rect2(6, 5 - _scroll, 16, 16), false)
		d.draw_string(W7.FONT, Vector2(28, 17 - _scroll), "Сетевое обнаружение и общий доступ к файлам отключены. Сетевые компьютеры и устройства не видны.", HORIZONTAL_ALIGNMENT_LEFT, w - 34, 12, Color.BLACK)
	if kind == "details" or kind == "bin":
		var cols: Array = BIN_COLS if kind == "bin" else COLS
		var hy := (58.0 if loc["kind"] == "library" else (30.0 if loc["kind"] == "network" else 0.0)) - _scroll
		var x := 0.0
		for c: Array in cols:
			d.draw_string(W7.FONT, Vector2(x + 8, hy + 17), c[0], HORIZONTAL_ALIGNMENT_LEFT, c[1] - 12, 12, Color("4c607a"))
			x += c[1]
			d.draw_line(Vector2(x - 0.5, hy + 4), Vector2(x - 0.5, hy + HEAD_H - 4), Color("e5e5e5"))
		d.draw_line(Vector2(0, hy + HEAD_H - 0.5), Vector2(w, hy + HEAD_H - 0.5), Color("e5e5e5"))
	if _items.is_empty() or (kind != "computer" and _list().is_empty()):
		var msg := "Корзина пуста." if loc["kind"] == "recycle" else "Эта папка пуста."
		if search.text != "":
			msg = "Нет элементов, удовлетворяющих условиям поиска."
		var my := (58.0 if loc["kind"] == "library" else 0.0) + (HEAD_H + 24.0 if kind in ["details", "bin"] else 30.0)
		d.draw_string(W7.FONT, Vector2(0, my - _scroll), msg, HORIZONTAL_ALIGNMENT_CENTER, w, 12, Color("6d6d6d"))
	for i in _items.size():
		var it: Array = _items[i]
		var r: Rect2 = it[0]
		if r.end.y < 0 or r.position.y > d.size.y:
			continue
		var n: Variant = it[1]
		var vk: String = it[2]
		if vk.begins_with("group:"):
			var gt := vk.substr(6)
			d.draw_string(W7.FONT, r.position + Vector2(0, 14), gt, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("1e3287"))
			d.draw_line(Vector2(r.position.x + W7.text_width(gt) + 8, r.position.y + 10.5), Vector2(r.end.x, r.position.y + 10.5), Color("e2e8f0"))
			continue
		var sel: bool = is_same(n, selected)
		var hr := r if vk != "row" else Rect2(r.position.x + 2, r.position.y, minf(r.size.x - 4, 596), r.size.y)
		if sel:
			W7.box(ci, hr, 3, [[0.0, "dcebfc"], [1.0, "c1dbfc"]], "7da2ce", "ebf4fd")
		elif i == _hover_item:
			W7.box(ci, hr, 3, [[0.0, "fafbfd"], [1.0, "ebf3fd"]], "b8d6fb", "fcfdfe")
		if _renaming != null and is_same(n, _renaming):
			_draw_item_icon(d, r, n, vk)
			continue
		_draw_item(d, r, n, vk)


func _draw_item_icon(d: Control, r: Rect2, n: Dictionary, vk: String) -> void:
	var sz := 16 if vk == "row" else (32 if vk == "icon" else 48)
	var ic := W7.icon(n["icon"], sz)
	if ic:
		var p := r.position + (Vector2(6, 3) if vk == "row" else Vector2(6, (r.size.y - sz) * 0.5))
		d.draw_texture_rect(ic, Rect2(p, Vector2(sz, sz)), false)


func _draw_item(d: Control, r: Rect2, n: Dictionary, vk: String) -> void:
	_draw_item_icon(d, r, n, vk)
	match vk:
		"row":
			var cols: Array = BIN_COLS if loc["kind"] == "recycle" else COLS
			var vals: Array
			if loc["kind"] == "recycle":
				var from: Dictionary = n.get("from", {})
				var from_path := ""
				if not from.is_empty():
					var parts: PackedStringArray = []
					for p: Dictionary in fs.chain(from).slice(1):
						parts.append(p["name"].replace("Локальный диск (C:)", "C:"))
					from_path = "\\".join(parts)
				vals = [n["name"], from_path, n.get("deleted", ""), fs.size_text(n)]
			else:
				vals = [n["name"], n["date"], fs.type_text(n), fs.size_text(n)]
			var x := 0.0
			for k in cols.size():
				var tx := x + (28.0 if k == 0 else 8.0)
				var col := Color.BLACK if k == 0 else Color("6d6d6d")
				var align := HORIZONTAL_ALIGNMENT_RIGHT if k == 3 else HORIZONTAL_ALIGNMENT_LEFT
				d.draw_string(W7.FONT, Vector2(tx, r.position.y + 15), str(vals[k]), align, cols[k][1] - (tx - x) - 8, 12, col)
				x += cols[k][1]
		"tile":
			var tx := r.position.x + 62
			d.draw_string(W7.FONT, Vector2(tx, r.position.y + 16), n["name"], HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 66, 12, Color.BLACK)
			if n["kind"] == "drive":
				var bar := Rect2(tx, r.position.y + 22, 180, 13)
				d.draw_rect(bar, Color("e6e6e6"))
				var fill := Rect2(bar.position + Vector2(1, 1), Vector2((bar.size.x - 2) * 0.5, bar.size.y - 2))
				W7.fill(d.get_canvas_item(), fill, 0, [[0.0, "41b9f0"], [0.5, "26a0da"], [1.0, "1c8cc5"]])
				d.draw_rect(bar, Color("bcbcbc"), false, 1.0)
				d.draw_string(W7.FONT, Vector2(tx, r.position.y + 50), "37,1 ГБ свободно из 74,5 ГБ", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("6d6d6d"))
			elif n["kind"] == "library":
				d.draw_string(W7.FONT, Vector2(tx, r.position.y + 33), "Библиотека", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("6d6d6d"))
		"icon":
			d.draw_string(W7.FONT, Vector2(r.position.x + 46, r.position.y + 25), n["name"], HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 50, 12, Color.BLACK)


# ---------- мышь и клавиши ----------

func _item_at(p: Vector2) -> int:
	var vp := p - _view.position
	if not Rect2(Vector2.ZERO, _view.size).has_point(vp):
		return -1
	for i in _items.size():
		if _items[i][1] != null and (_items[i][0] as Rect2).has_point(vp):
			if _items[i][2] == "row" and vp.x > 600:
				continue
			return i
	return -1


func _ui_at(p: Vector2) -> String:
	if p.distance_to(Vector2(18, 17)) < 12:
		return "back"
	if p.distance_to(Vector2(46, 17)) < 12:
		return "fwd"
	for i in _crumbs.size():
		if (_crumbs[i][0] as Rect2).has_point(p):
			return "crumb:%d" % i
	for c: Array in _cmds:
		if (c[0] as Rect2).has_point(p):
			return "cmd:" + c[1]
	return ""


func _nav_at(p: Vector2) -> int:
	for i in _nav_rows.size():
		if (_nav_rows[i][0] as Rect2).has_point(p):
			return i
	return -1


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var p: Vector2 = event.position
		var hi := _item_at(p)
		var hn := _nav_at(p)
		var hu := _ui_at(p)
		if hi != _hover_item or hn != _hover_nav or hu != _hover_ui:
			_hover_item = hi
			_hover_nav = hn
			_hover_ui = hu
			_bars.queue_redraw()
			_view.queue_redraw()
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN] and mb.pressed:
			var dir := -1.0 if mb.button_index == MOUSE_BUTTON_WHEEL_UP else 1.0
			_scroll = clampf(_scroll + dir * ROW_H * 3.0, 0.0, maxf(_content_height() - _view.size.y, 0.0))
			_relayout()
			accept_event()
			return
		if not mb.pressed:
			if mb.button_index == MOUSE_BUTTON_LEFT:
				var u := _ui_at(mb.position)
				if u == "back":
					back()
				elif u == "fwd":
					forward()
				elif u.begins_with("crumb:"):
					var target: Dictionary = _crumbs[int(u.substr(6))][1]
					if not is_same(target, loc):
						navigate(target)
				elif u.begins_with("cmd:"):
					for c: Array in _cmds:
						if c[1] == u.substr(4) and (c[2] as Callable).is_valid():
							(c[2] as Callable).call()
			elif mb.button_index == MOUSE_BUTTON_RIGHT:
				_context(mb.position)
			accept_event()
			return
		grab_focus()
		if mb.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT]:
			var hn := _nav_at(mb.position)
			if hn >= 0 and mb.button_index == MOUSE_BUTTON_LEFT:
				var t: Variant = _nav_rows[hn][1]
				if t != null and not is_same(t, loc):
					navigate(t)
				accept_event()
				return
			var hi := _item_at(mb.position)
			selected = _items[hi][1] if hi >= 0 else null
			_relayout()
			if hi >= 0 and mb.double_click and mb.button_index == MOUSE_BUTTON_LEFT:
				open_item(_items[hi][1])
		accept_event()
	elif event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_DELETE:
				if selected != null:
					_ask_delete(selected)
			KEY_F2:
				if selected != null:
					_start_rename(selected)
			KEY_ENTER, KEY_KP_ENTER:
				if selected != null:
					open_item(selected)
			KEY_BACKSPACE:
				back()
			KEY_F5:
				_relayout()
			_:
				return
		accept_event()


func _context(p: Vector2) -> void:
	var gp := global_position + p
	var hi := _item_at(p)
	if hi >= 0:
		var n: Dictionary = _items[hi][1]
		selected = n
		_relayout()
		var can_edit: bool = not n.get("system", false) and n["kind"] in ["file", "folder", "app"]
		var menu: Array
		if loc["kind"] == "recycle":
			menu = [{"text": "Восстановить", "bold": true, "cb": fs.restore_all}, {"sep": true}, {"text": "Свойства", "disabled": true}]
		else:
			menu = [{"text": "Открыть", "bold": true, "cb": func() -> void: open_item(n)}, {"sep": true},
				{"text": "Вырезать", "disabled": true}, {"text": "Копировать", "disabled": true}, {"sep": true},
				{"text": "Удалить", "disabled": not can_edit, "cb": func() -> void: _ask_delete(n)},
				{"text": "Переименовать", "disabled": not can_edit, "cb": func() -> void: _start_rename(n)},
				{"sep": true}, {"text": "Свойства", "disabled": true}]
		desktop.call("popup_menu", menu, gp)
		return
	if not Rect2(_view.position, _view.size).has_point(p):
		return
	selected = null
	_relayout()
	var wr := _writable()
	desktop.call("popup_menu", [
		{"text": "Вид", "sub": [{"text": "Огромные значки", "disabled": true}, {"text": "Крупные значки", "disabled": true},
				{"text": "Обычные значки", "disabled": true}, {"text": "Мелкие значки", "disabled": true},
				{"text": "Список", "disabled": true}, {"text": "Таблица", "checked": true}, {"text": "Плитка", "disabled": true}]},
		{"text": "Сортировка", "sub": [{"text": "Имя", "checked": true}, {"text": "Дата изменения", "disabled": true},
				{"text": "Тип", "disabled": true}, {"text": "Размер", "disabled": true}]},
		{"text": "Обновить", "cb": _relayout},
		{"sep": true},
		{"text": "Вставить", "disabled": true},
		{"sep": true},
		{"text": "Создать", "disabled": not wr, "sub": [
			{"text": "Папку", "icon": "folder", "cb": func() -> void: _create("folder")},
			{"sep": true},
			{"text": "Текстовый документ", "icon": "txt", "cb": func() -> void: _create("file")}]},
		{"sep": true},
		{"text": "Свойства", "disabled": true},
	], gp)


func _create(kind: String) -> void:
	if not _writable():
		return
	var n := fs.create(loc, kind)
	selected = n
	_relayout()
	_start_rename(n)


func _ask_delete(n: Dictionary) -> void:
	if n.get("system", false) or not n["kind"] in ["file", "folder", "app"]:
		return
	if loc["kind"] == "recycle":
		return
	var what := "этот файл" if n["kind"] != "folder" else "эту папку"
	var done := func(b: String) -> void:
		if b == "Да":
			fs.to_recycle(n)
	desktop.call("message", "Удаление " + ("файла" if n["kind"] != "folder" else "папки"),
			"Вы действительно хотите переместить %s в корзину?\n\n%s" % [what, n["name"]], "question",
			["Да", "Нет"], done, window)


func _ask_empty_bin() -> void:
	var cnt := (fs.recycle["children"] as Array).size()
	var text := "Вы действительно хотите безвозвратно удалить этот объект?" if cnt == 1 \
			else "Вы действительно хотите безвозвратно удалить эти объекты (%d)?" % cnt
	var done := func(b: String) -> void:
		if b == "Да":
			desktop.call("play", "recycle")
			fs.empty_recycle()
	desktop.call("message", "Удаление нескольких элементов" if cnt > 1 else "Удаление файла", text, "warning_q",
			["Да", "Нет"], done, window)


# ---------- переименование ----------

func _start_rename(n: Dictionary) -> void:
	if n.get("system", false):
		return
	_renaming = n
	_rename.text = n["name"]
	_rename.visible = true
	_place_rename()
	_rename.grab_focus()
	var base: String = n["name"]
	var end := base.length() if n["kind"] != "file" else base.get_basename().length()
	_rename.select(0, end)
	_view.queue_redraw()


func _place_rename() -> void:
	for it: Array in _items:
		if is_same(it[1], _renaming):
			var r: Rect2 = it[0]
			if it[2] == "row":
				_rename.position = _view.position + r.position + Vector2(26, 1)
				_rename.size = Vector2(230, ROW_H - 2)
			else:
				_rename.position = _view.position + r.position + Vector2(60, 4)
				_rename.size = Vector2(r.size.x - 64, 22)
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
	_relayout()
	grab_focus()
