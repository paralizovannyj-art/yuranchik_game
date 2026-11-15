## Экран телефона «ОРБИТА Q2» (320×240): рабочий стол, меню, «Сообщения», «Самочувствие», «Шагомер».
## Живёт внутри SubViewport телефона (phone.gd) и рисуется целиком в _draw — как экран кнопочного телефона.
## Управление приходит от телефона: move(), ok(), back().
class_name PhoneScreen
extends Control

enum Screen { HOME, MENU, SMS, READ, HEALTH, STEPS }

const W := 320.0
const H := 240.0
const BAR := 28.0                                ## высота строки статуса и строки софт-клавиш
const C_BG := Color("06090b")
const C_BAR := Color("0b1a24")
const C_LCD := Color("9fd0c8")
const C_DIM := Color("5d7d78")
const C_TEXT := Color("e8f2ef")
const C_ACCENT := Color("ff9e40")
const C_SEL := Color("2b1d0c")
const C_OK := Color("5fbf63")
const C_WARN := Color("e6bf35")
const C_BAD := Color("d9483c")
const APPS := [["Сообщения", Screen.SMS], ["Самочувствие", Screen.HEALTH], ["Шагомер", Screen.STEPS]]

var screen := Screen.HOME
var signal_bars := 4                             ## 1..4, телефон выставляет по расстоянию до Сергея
var player: Player

var _app := 0
var _row := 0
var _reading := {}
var _font: Font
var _ecg := PackedFloat32Array()
var _ecg_t := 0.0
var _bpm := 72.0
var _snow := PackedVector2Array()


func _ready() -> void:
	size = Vector2(W, H)
	_font = ThemeDB.fallback_font
	_ecg.resize(150)
	_ecg.fill(0.0)
	var rng := RandomNumberGenerator.new()
	rng.seed = 47
	for i in 70:
		_snow.append(Vector2(rng.randf() * W, rng.randf() * (H - BAR * 2.0) + BAR))


func reset() -> void:
	screen = Screen.HOME
	_app = 0
	_row = 0
	queue_redraw()


# ----------------------------------------------------------------------------- управление
func move(d: Vector2i) -> void:
	match screen:
		Screen.MENU:
			_app = clampi(_app + d.x + d.y, 0, APPS.size() - 1)
		Screen.SMS:
			_row = clampi(_row + d.y + d.x, 0, maxi(_rows().size() - 1, 0))
		_:
			return
	Game.sfx("phone_key", null, -14.0, 0.02)
	queue_redraw()


func ok() -> void:
	match screen:
		Screen.HOME:
			_go(Screen.MENU)
		Screen.MENU:
			_go(APPS[_app][1])
		Screen.SMS:
			var rows := _rows()
			if rows.is_empty():
				return
			_reading = rows[_row]
			if _reading.has("task"):
				Game.objective_read = true
			else:
				_reading["read"] = true
			_go(Screen.READ)
		_:
			return


## Назад на экран выше. Возвращает false, если уже на рабочем столе.
func back() -> bool:
	match screen:
		Screen.HOME:
			return false
		Screen.READ:
			_go(Screen.SMS)
		Screen.MENU:
			_go(Screen.HOME)
		_:
			_go(Screen.MENU)
	return true


## Правая софт-клавиша на рабочем столе — сразу в «Сообщения».
func shortcut_messages() -> void:
	if screen == Screen.HOME:
		_go(Screen.SMS)


func _go(s: Screen) -> void:
	if s == Screen.SMS and screen != Screen.READ:
		_row = 0
	screen = s
	Game.sfx("phone_key", null, -12.0, 0.02)
	queue_redraw()


## Строки «Сообщений»: закреплённое задание сверху, потом СМС, новые первыми.
func _rows() -> Array[Dictionary]:
	var rows: Array[Dictionary] = []
	if Game.objective != "":
		rows.append({"task": true, "from": "Задание", "text": Game.objective, "read": Game.objective_read, "time": ""})
	rows.append_array(Game.messages)
	return rows


# ----------------------------------------------------------------------------- самочувствие
func _process(delta: float) -> void:
	var k := Game.hp / Game.MAX_HP
	var tired := player != null and is_instance_valid(player) and player.exhausted
	_bpm = lerpf(_bpm, 68.0 + (1.0 - k) * 70.0 + (22.0 if tired else 0.0), delta)
	if screen != Screen.HEALTH:
		if screen == Screen.HOME or screen == Screen.STEPS:
			queue_redraw()                           # часы и счётчики идут
		return
	# бегущая кардиограмма: один удар на 60/_bpm секунд
	_ecg_t += delta
	var period := 60.0 / _bpm
	var steps := int(delta * 90.0) + 1
	for i in steps:
		var p := fmod(_ecg_t + float(i) / 90.0, period) / period
		var v := 0.0
		if p < 0.04:
			v = -2.0
		elif p < 0.08:
			v = 0.0
		elif p < 0.10:
			v = -16.0
		elif p < 0.12:
			v = 13.0
		elif p < 0.14:
			v = -3.0
		elif p > 0.30 and p < 0.40:
			v = -4.0
		_ecg.remove_at(0)
		_ecg.append(v)
	queue_redraw()


# ----------------------------------------------------------------------------- отрисовка
func _text(s: String, pos: Vector2, fs: int, col: Color, align := HORIZONTAL_ALIGNMENT_LEFT, width := -1.0) -> void:
	draw_string(_font, pos, s, align, width, fs, col)


func _status(title: String) -> void:
	draw_rect(Rect2(0, 0, W, BAR), C_BAR)
	for i in 4:                                  # палки сети
		var h := 4.0 + i * 3.0
		draw_rect(Rect2(8 + i * 6, 21 - h, 4, h), C_LCD if i < signal_bars else Color(C_LCD, 0.22))
	_text(title, Vector2(0, 21), 17, C_LCD, HORIZONTAL_ALIGNMENT_CENTER, W)
	draw_rect(Rect2(W - 36, 8, 24, 13), C_LCD, false, 1.0)   # батарея
	draw_rect(Rect2(W - 12, 11, 3, 7), C_LCD)
	draw_rect(Rect2(W - 34, 10, 13, 9), C_LCD)


func _soft(left: String, right: String) -> void:
	draw_rect(Rect2(0, H - BAR, W, BAR), C_BAR)
	_text(left, Vector2(10, H - 8), 17, C_TEXT)
	_text(right, Vector2(0, H - 8), 17, C_TEXT, HORIZONTAL_ALIGNMENT_RIGHT, W - 10)


func _draw() -> void:
	draw_rect(Rect2(0, 0, W, H), C_BG)
	match screen:
		Screen.HOME: _draw_home()
		Screen.MENU: _draw_menu()
		Screen.SMS: _draw_sms()
		Screen.READ: _draw_read()
		Screen.HEALTH: _draw_health()
		Screen.STEPS: _draw_steps()


func _draw_home() -> void:
	# обои: ночное небо, силуэты панелек с окнами, снег
	var top := BAR
	var hor := 150.0
	for y in range(int(top), int(hor), 4):
		var t := (y - top) / (hor - top)
		draw_rect(Rect2(0, y, W, 4), Color("0c1a2c").lerp(Color("1d3550"), t))
	draw_rect(Rect2(0, hor, W, H - BAR - hor), Color("8fa3b2"))
	draw_rect(Rect2(0, hor, W, 4), Color("c9d6de"))
	var houses := [Rect2(14, 96, 70, 54), Rect2(98, 80, 56, 70), Rect2(176, 104, 80, 46), Rect2(268, 88, 46, 62)]
	var lit := [Vector2(30, 106), Vector2(52, 124), Vector2(112, 92), Vector2(134, 116), Vector2(196, 116), Vector2(236, 126), Vector2(286, 100)]
	for r: Rect2 in houses:
		draw_rect(r, Color("0b141e"))
	for p: Vector2 in lit:
		draw_rect(Rect2(p, Vector2(5, 5)), C_ACCENT)
	for s: Vector2 in _snow:
		draw_rect(Rect2(s, Vector2(2, 2)), Color(1, 1, 1, 0.5))
	_status("ЮГ-GSM")
	_text(Game.clock_text(), Vector2(0, 92), 58, Color.BLACK, HORIZONTAL_ALIGNMENT_CENTER, W + 4)
	_text(Game.clock_text(), Vector2(0, 89), 58, C_TEXT, HORIZONTAL_ALIGNMENT_CENTER, W)
	var n := Game.unread_count()
	if n > 0:
		var blink := int(Time.get_ticks_msec() / 600.0) % 2 == 0
		var r := Rect2(10, H - BAR - 38, W - 20, 32)
		draw_rect(r, Color(C_BAR, 0.93))
		draw_rect(r, C_LCD if blink else Color(C_LCD, 0.25), false, 1.0)
		_text("Новых сообщений: %d" % n, Vector2(r.position.x, r.position.y + 23), 17, C_LCD, HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
	_soft("Меню", "Сообщ.")


func _draw_menu() -> void:
	_status("Меню")
	var cw := (W - 24.0) / 3.0
	for i in APPS.size():
		var r := Rect2(12 + i * cw, 52, cw - 6, 128)
		if i == _app:
			draw_rect(r, C_SEL)
			draw_rect(r, C_ACCENT, false, 2.0)
		var c := r.get_center() + Vector2(0, -14)
		_draw_icon(i, c)
		_text(APPS[i][0], Vector2(r.position.x, r.end.y - 16), 12, C_TEXT if i == _app else C_LCD, HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
		if i == 0 and Game.unread_count() > 0:
			draw_circle(c + Vector2(20, -16), 7, C_BAD)
			_text(str(Game.unread_count()), c + Vector2(13, -11), 11, Color.WHITE, HORIZONTAL_ALIGNMENT_CENTER, 14)
	_soft("Выбрать", "Назад")


func _draw_icon(i: int, c: Vector2) -> void:
	match i:
		0:                                           # конверт
			draw_rect(Rect2(c - Vector2(20, 13), Vector2(40, 26)), Color("e8d36a"))
			draw_polyline(PackedVector2Array([c + Vector2(-20, -13), c + Vector2(0, 3), c + Vector2(20, -13)]), Color("7a5c10"), 3.0)
		1:                                           # сердце с кардиограммой
			draw_circle(c + Vector2(-9, -6), 11, C_BAD)
			draw_circle(c + Vector2(9, -6), 11, C_BAD)
			draw_colored_polygon(PackedVector2Array([c + Vector2(-20, -2), c + Vector2(20, -2), c + Vector2(0, 20)]), C_BAD)
			draw_polyline(PackedVector2Array([c + Vector2(-16, -2), c + Vector2(-6, -2), c + Vector2(-2, -10), c + Vector2(3, 6),
				c + Vector2(7, -2), c + Vector2(16, -2)]), Color.WHITE, 2.0)
		2:                                           # следы
			draw_rect(Rect2(c + Vector2(-16, -18), Vector2(11, 20)), C_LCD)
			draw_rect(Rect2(c + Vector2(4, -4), Vector2(11, 20)), C_LCD)


func _draw_sms() -> void:
	_status("Сообщения")
	var rows := _rows()
	if rows.is_empty():
		_text("Сообщений нет", Vector2(0, 120), 13, C_DIM, HORIZONTAL_ALIGNMENT_CENTER, W)
	var rh := 46.0
	var first := clampi(_row - 2, 0, maxi(rows.size() - 4, 0))
	for i in range(first, mini(first + 4, rows.size())):
		var m: Dictionary = rows[i]
		var y := BAR + 2 + (i - first) * rh
		if i == _row:
			draw_rect(Rect2(0, y, W, rh - 1), C_SEL)
		draw_line(Vector2(0, y + rh - 1), Vector2(W, y + rh - 1), Color("18303a"))
		var head: String = ("! " if m.has("task") else "") + m["from"]
		_text(head, Vector2(10, y + 19), 17, C_ACCENT if not m["read"] or m.has("task") else C_TEXT)
		_text(m["time"], Vector2(0, y + 19), 14, C_DIM, HORIZONTAL_ALIGNMENT_RIGHT, W - 10)
		_text(_short(m["text"], 32), Vector2(10, y + 39), 15, C_LCD)
	_soft("Открыть", "Назад")


func _short(s: String, n: int) -> String:
	return s if s.length() <= n else s.substr(0, n - 1) + "…"


func _draw_read() -> void:
	var m := _reading
	_status(m.get("from", ""))
	var y := BAR + 22.0
	if m.has("task"):
		_text("! Задание", Vector2(12, y), 17, C_ACCENT)
		y += 24.0
	draw_multiline_string(_font, Vector2(12, y), m.get("text", ""), HORIZONTAL_ALIGNMENT_LEFT, W - 24, 18, 8, C_TEXT)
	_soft("", "Назад")


func _draw_health() -> void:
	_status("Самочувствие")
	var k := Game.hp / Game.MAX_HP
	var col := C_OK if k > 0.6 else (C_WARN if k > 0.3 else C_BAD)
	var word := "НОРМА" if k > 0.6 else ("РАНЕН" if k > 0.3 else "ПРИ СМЕРТИ")
	# пиксельный человечек: цвет — состояние, красные пятна — чем хуже, тем больше
	var o := Vector2(30, 48)
	var px := 7.0
	var body := [Rect2(7, 0, 5, 5), Rect2(5, 6, 9, 13), Rect2(2, 7, 3, 11), Rect2(14, 7, 3, 11), Rect2(5, 19, 4, 18), Rect2(10, 19, 4, 18)]
	var wounds := [Rect2(10, 22, 4, 6), Rect2(5, 9, 4, 3), Rect2(2, 12, 3, 4), Rect2(8, 1, 3, 3), Rect2(5, 28, 4, 5)]
	for r: Rect2 in body:
		draw_rect(Rect2(o + r.position * px * 0.5, r.size * px * 0.5), col)
	var n := int(roundf((1.0 - k) * wounds.size()))
	for i in n:
		var r: Rect2 = wounds[i]
		draw_rect(Rect2(o + r.position * px * 0.5, r.size * px * 0.5), C_BAD.darkened(0.25))
	var x := 120.0
	_text("Состояние:", Vector2(x, 58), 16, C_LCD)
	_text(word, Vector2(x, 82), 21, col)
	_text("Пульс: %d" % int(_bpm), Vector2(x, 110), 17, C_LCD)
	var g := Rect2(x, 120, W - x - 12, 64)
	draw_rect(g, Color("071312"))
	draw_rect(g, Color("18303a"), false, 1.0)
	var pts := PackedVector2Array()
	for i in _ecg.size():
		pts.append(Vector2(g.position.x + i * g.size.x / (_ecg.size() - 1), g.get_center().y + _ecg[i] * 1.6))
	draw_polyline(pts, C_OK, 2.0)
	_soft("", "Назад")


func _draw_steps() -> void:
	_status("Шагомер")
	var t := int(Game.stats["time"])
	@warning_ignore("integer_division")          # целые минуты
	var rows := [["Шагов", str(Game.stats.get("steps", 0))], ["В пути", "%d:%02d" % [t / 60, t % 60]],
		["Офников уложено", str(Game.stats["kills"])], ["Смертей", str(Game.stats["deaths"])]]
	for i in rows.size():
		var y := BAR + 8 + i * 44.0
		_text(rows[i][0], Vector2(14, y + 24), 18, C_TEXT)
		_text(rows[i][1], Vector2(0, y + 24), 20, C_ACCENT, HORIZONTAL_ALIGNMENT_RIGHT, W - 14)
		draw_line(Vector2(10, y + 36), Vector2(W - 10, y + 36), Color("18303a"))
	_soft("", "Назад")
