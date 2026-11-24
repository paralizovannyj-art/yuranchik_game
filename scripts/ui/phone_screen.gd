## Экран телефона Юрчика (Nokia, 320×240) в духе Series 40: рабочий стол с панелью ярлыков, меню,
## «Сообщения» по контактам, плеер «Музыка», «Игры» (Змейка, Battle City, Pac-Man), «Интернет» без сети,
## «Настройки», «Самочувствие», «Шагомер». Живёт внутри SubViewport телефона (phone.gd) и рисуется целиком
## в _draw — как экран кнопочного телефона. Управление приходит от телефона: move(), ok(), back().
class_name PhoneScreen
extends Control

enum Screen { HOME, MENU, CONTACTS, CHAT, TASK, MUSIC, GAMES, GAME, WEB, SETTINGS, HEALTH, STEPS }

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
const OPERATOR := "Kyivstar"
const WALLPAPER := preload("res://assets/ui/phone_wallpaper.png")   ## обои с фото Nokia из YUR-34 (tools/make_phone_wallpaper.py)
## Панель ярлыков на рабочем столе, слева направо (как на фото Nokia в YUR-34; вместо Ovi — настройки).
const SHORTCUTS := [Screen.MUSIC, Screen.CONTACTS, Screen.GAMES, Screen.WEB, Screen.SETTINGS]
const APPS := [["Сообщения", Screen.CONTACTS], ["Музыка", Screen.MUSIC], ["Игры", Screen.GAMES],
	["Интернет", Screen.WEB], ["Настройки", Screen.SETTINGS], ["Самочувствие", Screen.HEALTH], ["Шагомер", Screen.STEPS]]
const ICONS := {Screen.CONTACTS: "sms", Screen.MUSIC: "music", Screen.GAMES: "games", Screen.WEB: "web",
	Screen.SETTINGS: "settings", Screen.HEALTH: "health", Screen.STEPS: "steps"}
## Контакты Юрчика и старая переписка (до начала игры). true — сообщение от самого Юрчика.
## Новые СМС из игры (Game.text) попадают в переписку с тем же именем; незнакомое имя — новый контакт.
const CONTACTS := [
	{"name": "Мама", "history": [
		["вчера", "Юра, купи хлеба и молока по дороге", false],
		["вчера", "Ок", true],
		["вчера", "Суп в холодильнике, погрей. Шапку надень, обещали минус двадцать", false]]},
	{"name": "Димон", "history": [
		["пн", "Скинь «Пятиэтажки» по блютузу", false],
		["пн", "Завтра скину, батарея села", true],
		["пн", "Ты на районе ночью не ходи, там опять какие-то в пиджаках шатаются", false]]},
	{"name": OPERATOR, "history": [
		["пн", "Ваш баланс: 3,40 грн. Пополните счёт, чтобы оставаться на связи.", false],
		["вт", "Услуга «Интернет» недоступна: недостаточно средств.", false]]},
]
## Песни в памяти телефона: файл в assets/audio/phone_music/ и название в плеере.
const MUSIC_DIR := "res://assets/audio/phone_music/"
const TRACKS := [["pyatietazhki", "Гудрон — Пятиэтажки"], ["posledniaia_elektrichka", "ДК Энергетик — Последняя электричка"],
	["sneg_na_provodakh", "Лампа — Снег на проводах"], ["kvartal", "Гудрон — Квартал"]]
const GAME_NAMES := ["Змейка", "Battle City", "Pac-Man"]
const SETTINGS := [["Громкость плеера", "volume"], ["Звук клавиш", "keys"], ["Вибрация", "vibra"], ["Яркость экрана", "bright"]]

## Настройки телефона — общие на всю игру (телефон пересоздаётся на каждом уровне).
static var cfg := {"volume": 6, "keys": true, "vibra": true, "bright": 5}

var screen := Screen.HOME
var signal_bars := 4                             ## 1..4, телефон выставляет по расстоянию до Сергея
var player: Player
var active := false                              ## телефон в руке: идут игры и анимации

var _bar := 0                                    ## выбранный ярлык на рабочем столе
var _menu_focus := false                         ## на рабочем столе выбрана софт-клавиша «Меню»
var _from := Screen.HOME                         ## куда вернуться из приложения
var _app := 0
var _row := 0
var _chat := ""
var _scroll := 0.0
var _scroll_max := 0.0
var _game: PhoneGame
var _web_t := 0.0
var _font: Font
var _ecg := PackedFloat32Array()
var _ecg_t := 0.0
var _bpm := 72.0
var _music: AudioStreamPlayer
var _tracks: Array[Dictionary] = []
var _track := -1                                 ## что играет (индекс в _tracks), -1 — ничего


func _ready() -> void:
	size = Vector2(W, H)
	_font = ThemeDB.fallback_font
	_ecg.resize(150)
	_ecg.fill(0.0)
	for t: Array in TRACKS:
		var path: String = MUSIC_DIR + t[0] + ".wav"
		if ResourceLoader.exists(path):
			_tracks.append({"title": t[1], "path": path})
	_music = AudioStreamPlayer.new()
	_music.finished.connect(func() -> void: _play((_track + 1) % _tracks.size()))
	add_child(_music)
	_apply_volume()


func reset() -> void:
	screen = Screen.HOME
	_menu_focus = false
	_game = null
	queue_redraw()


# ----------------------------------------------------------------------------- управление
## Колесо мыши: на рабочем столе и в меню идёт по значкам по очереди слева направо (вниз — дальше,
## вверх — назад, по кругу), в списках и переписке листает вверх-вниз.
func scroll(step: int) -> void:
	match screen:
		Screen.HOME:
			_menu_focus = false
			_bar = wrapi(_bar + step, 0, SHORTCUTS.size())
		Screen.MENU:
			_app = wrapi(_app + step, 0, APPS.size())
		_:
			move(Vector2i(0, step))
			return
	_click()
	queue_redraw()


func move(d: Vector2i) -> void:
	match screen:
		Screen.HOME:
			if d.y > 0:
				_menu_focus = true
			elif d.y < 0:
				_menu_focus = false
			else:
				_menu_focus = false
				_bar = wrapi(_bar + d.x, 0, SHORTCUTS.size())
		Screen.MENU:
			var n := _app + d.x + d.y * 3
			if n < 0 or n >= APPS.size():
				return
			_app = n
		Screen.CONTACTS:
			_row = clampi(_row + d.y + d.x, 0, maxi(_contacts().size() - 1, 0))
		Screen.CHAT, Screen.TASK:
			_scroll = clampf(_scroll - d.y * 30.0, 0.0, _scroll_max)
		Screen.MUSIC:
			if d.x != 0:
				_change("volume", d.x)
			else:
				_row = clampi(_row + d.y, 0, maxi(_tracks.size() - 1, 0))
		Screen.GAMES:
			_row = clampi(_row + d.y + d.x, 0, GAME_NAMES.size() - 1)
		Screen.GAME:
			_game.dir(d)
			return
		Screen.SETTINGS:
			if d.y != 0:
				_row = clampi(_row + d.y, 0, SETTINGS.size() - 1)
			else:
				_change(SETTINGS[_row][1], d.x)
		_:
			return
	_click()
	queue_redraw()


func ok() -> void:
	match screen:
		Screen.HOME:
			_open(Screen.MENU if _menu_focus else SHORTCUTS[_bar])
		Screen.MENU:
			_open(APPS[_app][1])
		Screen.CONTACTS:
			var rows := _contacts()
			if rows.is_empty():
				return
			var c: Dictionary = rows[_row]
			_scroll = 0.0
			if c.has("task"):
				Game.objective_read = true
				_go(Screen.TASK)
				return
			_chat = c["name"]
			for m: Dictionary in Game.messages:
				if m["from"] == _chat:
					m["read"] = true
			_go(Screen.CHAT)
		Screen.MUSIC:
			if _tracks.is_empty():
				return
			if _row == _track:
				_music.stream_paused = not _music.stream_paused
			else:
				_play(_row)
			_click()
			queue_redraw()
		Screen.GAMES:
			_start_game(_row)
		Screen.GAME:
			_game.action()
		Screen.WEB:
			_web_t = 0.0                              # «Повторить» — снова грузится и снова нет сети
			_click()
		Screen.SETTINGS:
			var key: String = SETTINGS[_row][1]
			if cfg[key] is bool:
				_change(key, 1)
			_click()
			queue_redraw()


## Назад на экран выше. Возвращает false, если уже на рабочем столе.
func back() -> bool:
	match screen:
		Screen.HOME:
			return false
		Screen.MENU:
			_go(Screen.HOME)
		Screen.CHAT, Screen.TASK:
			_go(Screen.CONTACTS)
		Screen.GAME:
			_game = null
			_go(Screen.GAMES)
		_:
			_go(_from)
	return true


## Правая софт-клавиша на рабочем столе («Имена») — сразу в «Сообщения».
func shortcut_messages() -> void:
	if screen == Screen.HOME:
		_open(Screen.CONTACTS)


func _open(s: Screen) -> void:
	if s != Screen.MENU:
		_from = screen
	_row = 0
	if s == Screen.MUSIC:
		_row = maxi(_track, 0)
	elif s == Screen.WEB:
		_web_t = 0.0
	_go(s)


func _go(s: Screen) -> void:
	screen = s
	_click()
	queue_redraw()


func _click() -> void:
	if cfg["keys"]:
		Game.sfx("phone_key", null, -12.0, 0.02)


func _change(key: String, d: int) -> void:
	match key:
		"volume":
			cfg["volume"] = clampi(cfg["volume"] + d, 0, 10)
			_apply_volume()
		"bright":
			cfg["bright"] = clampi(cfg["bright"] + d, 1, 5)
		_:
			cfg[key] = not cfg[key]


func _apply_volume() -> void:
	if _music:
		_music.volume_db = linear_to_db(maxf(cfg["volume"] / 10.0, 0.0001)) - 6.0


func _play(i: int) -> void:
	if _tracks.is_empty():
		return
	_track = i
	_music.stream = load(_tracks[i]["path"])
	_music.stream_paused = false
	_music.play()
	queue_redraw()


func _start_game(i: int) -> void:
	match i:
		0: _game = PhoneSnake.new()
		1: _game = PhoneBattleCity.new()
		_: _game = PhonePacman.new()
	_game.area = Rect2(0, BAR, W, H - BAR * 2.0)
	_game.font = _font
	_game.start()
	_go(Screen.GAME)


## Строки «Сообщений»: закреплённое задание сверху, потом контакты — сначала те, от кого пришло новое.
func _contacts() -> Array[Dictionary]:
	var rows: Array[Dictionary] = []
	if Game.objective != "":
		rows.append({"task": true, "name": "Задание", "text": Game.objective, "time": "", "out": false,
			"unread": 0 if Game.objective_read else 1})
	var names: Array[String] = []
	for m: Dictionary in Game.messages:
		if not names.has(m["from"]):
			names.append(m["from"])
	for c: Dictionary in CONTACTS:
		if not names.has(c["name"]):
			names.append(c["name"])
	for n: String in names:
		var th := _thread(n)
		var last: Dictionary = th.back()
		var unread := 0
		for m: Dictionary in Game.messages:
			if m["from"] == n and not m["read"]:
				unread += 1
		rows.append({"name": n, "text": last["text"], "time": last["time"], "out": last["out"], "unread": unread})
	return rows


## Переписка с контактом от старых к новым.
func _thread(contact: String) -> Array[Dictionary]:
	var th: Array[Dictionary] = []
	for c: Dictionary in CONTACTS:
		if c["name"] == contact:
			for h: Array in c["history"]:
				th.append({"time": h[0], "text": h[1], "out": h[2]})
	for i in range(Game.messages.size() - 1, -1, -1):
		var m: Dictionary = Game.messages[i]
		if m["from"] == contact:
			th.append({"time": m["time"], "text": m["text"], "out": false})
	return th


# ----------------------------------------------------------------------------- время
func _process(delta: float) -> void:
	var k := Game.hp / Game.MAX_HP
	var tired := player != null and is_instance_valid(player) and player.exhausted
	_bpm = lerpf(_bpm, 68.0 + (1.0 - k) * 70.0 + (22.0 if tired else 0.0), delta)
	if not active:
		return
	match screen:
		Screen.GAME:
			_game.step(delta)
		Screen.WEB:
			_web_t += delta
		Screen.HEALTH:
			_ecg_step(delta)
	queue_redraw()                                   # часы, мигание, прогресс песни


## Бегущая кардиограмма: один удар на 60/_bpm секунд.
func _ecg_step(delta: float) -> void:
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


# ----------------------------------------------------------------------------- отрисовка
func _text(s: String, pos: Vector2, fs: int, col: Color, align := HORIZONTAL_ALIGNMENT_LEFT, width := -1.0) -> void:
	draw_string(_font, pos, s, align, width, fs, col)


func _shadow_text(s: String, pos: Vector2, fs: int, col: Color, align := HORIZONTAL_ALIGNMENT_LEFT, width := -1.0) -> void:
	draw_string(_font, pos + Vector2(1, 1), s, align, width, fs, Color(0, 0, 0, 0.8))
	draw_string(_font, pos, s, align, width, fs, col)


func _box(col: Color, radius: int, border := Color.TRANSPARENT, bw := 0) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = col
	sb.set_corner_radius_all(radius)
	sb.border_color = border
	sb.set_border_width_all(bw)
	sb.anti_aliasing = true
	return sb


func _signal_and_battery(x: float) -> void:
	for i in 4:                                  # палки сети
		var h := 4.0 + i * 3.0
		draw_rect(Rect2(x + i * 6, 21 - h, 4, h), C_LCD if i < signal_bars else Color(C_LCD, 0.22))
	var b := x + 30.0                            # батарея
	draw_rect(Rect2(b, 8, 24, 13), C_LCD, false, 1.0)
	draw_rect(Rect2(b + 24, 11, 3, 7), C_LCD)
	draw_rect(Rect2(b + 2, 10, 13, 9), C_LCD)


func _status(title: String) -> void:
	draw_rect(Rect2(0, 0, W, BAR), C_BAR)
	_signal_and_battery(8.0)
	_text(title, Vector2(70, 21), 17, C_LCD, HORIZONTAL_ALIGNMENT_RIGHT, W - 80)


func _soft(left: String, right: String, mid := "") -> void:
	draw_rect(Rect2(0, H - BAR, W, BAR), C_BAR)
	_text(left, Vector2(10, H - 8), 17, C_TEXT)
	_text(mid, Vector2(0, H - 8), 17, C_TEXT, HORIZONTAL_ALIGNMENT_CENTER, W)
	_text(right, Vector2(0, H - 8), 17, C_TEXT, HORIZONTAL_ALIGNMENT_RIGHT, W - 10)


func _short(s: String, n: int) -> String:
	return s if s.length() <= n else s.substr(0, n - 1) + "…"


func _unread_badge(c: Vector2) -> void:
	var n := Game.unread_count()
	if n <= 0:
		return
	draw_circle(c, 7, C_BAD)
	_text(str(n), c + Vector2(-7, 4), 11, Color.WHITE, HORIZONTAL_ALIGNMENT_CENTER, 14)


func _draw() -> void:
	draw_rect(Rect2(0, 0, W, H), C_BG)
	match screen:
		Screen.HOME: _draw_home()
		Screen.MENU: _draw_menu()
		Screen.CONTACTS: _draw_contacts()
		Screen.CHAT: _draw_chat()
		Screen.TASK: _draw_task()
		Screen.MUSIC: _draw_music()
		Screen.GAMES: _draw_games()
		Screen.GAME: _draw_game()
		Screen.WEB: _draw_web()
		Screen.SETTINGS: _draw_settings()
		Screen.HEALTH: _draw_health()
		Screen.STEPS: _draw_steps()
	var dim := (5 - int(cfg["bright"])) * 0.13       # яркость экрана
	if dim > 0.0:
		draw_rect(Rect2(0, 0, W, H), Color(0, 0, 0, dim))


func _draw_home() -> void:
	# сам снимок из задачи: батарея, Bluetooth, E, дата, значки ярлыков и Go to / Menu / Names уже на нём;
	# сверху рисуется только то, что меняется: сеть, часы, оператор, события, значок Настроек и выделение
	draw_texture_rect(WALLPAPER, Rect2(0, 0, W, H), false)
	for i in 4:                                  # палки сети на месте значка антенны
		var h := 4.0 + i * 3.0
		draw_rect(Rect2(3 + i * 4.5, 17 - h, 3, h), Color("3a3a3a") if i < signal_bars else Color(0.2, 0.2, 0.2, 0.25))
	draw_string(_font, Vector2(170, 18), OPERATOR, HORIZONTAL_ALIGNMENT_LEFT, -1, 19, Color("262626"))
	# часы слева, как на фото: тёмные цифры на светлом небе
	draw_string(_font, Vector2(1, 68), Game.clock_text(), HORIZONTAL_ALIGNMENT_LEFT, -1, 27, Color(1, 1, 1, 0.55))
	draw_string(_font, Vector2(0, 67), Game.clock_text(), HORIZONTAL_ALIGNMENT_LEFT, -1, 27, Color("161616"))
	# средняя панель — события
	var info := Rect2(80, 77, 237, 71)
	var y := info.position.y + 24.0
	var n := Game.unread_count()
	if n > 0:
		var blink := int(Time.get_ticks_msec() / 600.0) % 2 == 0
		_shadow_text("Новых сообщений: %d" % n, Vector2(info.position.x + 12, y), 16, C_ACCENT if blink else C_TEXT)
		y += 24.0
	if _track >= 0:
		_play_mark(Vector2(info.position.x + 18, y - 5), _music.stream_paused, C_TEXT)
		_shadow_text(_short(_tracks[_track]["title"], 26), Vector2(info.position.x + 30, y), 15, C_TEXT)
	# нижняя панель — пять ярлыков
	var bar := Rect2(80, 155, 237, 53)
	var cw := bar.size.x / SHORTCUTS.size()
	for i in SHORTCUTS.size():
		var cell := Rect2(bar.position.x + i * cw, bar.position.y, cw, bar.size.y)
		if i == _bar and not _menu_focus:
			draw_style_box(_box(Color(1, 1, 1, 0.14), 5, Color(1, 1, 1, 0.9), 2), cell.grow(-1.0))
		if SHORTCUTS[i] == Screen.SETTINGS:      # остальные четыре значка — с фото
			PhoneIcons.draw(self, ICONS[SHORTCUTS[i]], cell.get_center() + Vector2(0, -3), 0.95)
		if SHORTCUTS[i] == Screen.CONTACTS:
			_unread_badge(cell.get_center() + Vector2(15, -15))
	# софт-клавиши Go to · Menu · Names — с фото, тут только выделение «Menu»
	if _menu_focus:
		draw_style_box(_box(Color(1, 1, 1, 0.14), 5, Color(1, 1, 1, 0.9), 2), Rect2(W / 2 - 38, H - 28, 76, 27))


func _draw_menu() -> void:
	_status("Меню")
	var cw := (W - 16.0) / 3.0
	var ch := 60.0
	for i in APPS.size():
		@warning_ignore("integer_division")
		var r := Rect2(8 + (i % 3) * cw, BAR + 6 + (i / 3) * ch, cw - 4, ch - 4)
		if i == _app:
			draw_style_box(_box(C_SEL, 5, C_ACCENT, 2), r)
		var c := r.get_center() + Vector2(0, -8)
		PhoneIcons.draw(self, ICONS[APPS[i][1]], c, 0.9)
		_text(APPS[i][0], Vector2(r.position.x, r.end.y - 5), 12, C_TEXT if i == _app else C_LCD, HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
		if APPS[i][1] == Screen.CONTACTS:
			_unread_badge(c + Vector2(17, -12))
	_soft("Выбрать", "Назад")


func _draw_contacts() -> void:
	_status("Сообщения")
	var rows := _contacts()
	var rh := 46.0
	var first := clampi(_row - 2, 0, maxi(rows.size() - 4, 0))
	for i in range(first, mini(first + 4, rows.size())):
		var m: Dictionary = rows[i]
		var y := BAR + (i - first) * rh
		if i == _row:
			draw_rect(Rect2(0, y, W, rh - 1), C_SEL)
		draw_line(Vector2(0, y + rh - 1), Vector2(W, y + rh - 1), Color("18303a"))
		var task := m.has("task")
		var av := Vector2(24, y + rh / 2.0)              # кружок с буквой вместо фото
		draw_circle(av, 15, C_ACCENT if task else Color("2c5566"))
		_text("!" if task else (m["name"] as String).substr(0, 1), av + Vector2(-15, 6), 17, C_TEXT, HORIZONTAL_ALIGNMENT_CENTER, 30)
		var unread: int = m["unread"]
		_text(m["name"], Vector2(48, y + 19), 17, C_ACCENT if unread > 0 else C_TEXT)
		_text(m["time"], Vector2(0, y + 19), 13, C_DIM, HORIZONTAL_ALIGNMENT_RIGHT, W - 10)
		var prev := ("Я: " if m["out"] else "") + (m["text"] as String)
		_text(_short(prev, 30), Vector2(48, y + 39), 14, C_LCD)
		if unread > 0:
			draw_circle(Vector2(W - 18, y + 33), 7, C_BAD)
			_text(str(unread), Vector2(W - 25, y + 37), 11, Color.WHITE, HORIZONTAL_ALIGNMENT_CENTER, 14)
	_soft("Открыть", "Назад")


## Переписка облачками: входящие слева, Юрчика — справа; новые внизу, стрелка вверх листает назад.
func _draw_chat() -> void:
	var th := _thread(_chat)
	var fs := 15
	var maxw := 220.0
	var bottom := H - BAR - 6.0 + _scroll
	var y := bottom
	var top_y := y
	for i in range(th.size() - 1, -1, -1):
		var m: Dictionary = th[i]
		var t: String = m["text"]
		var one := _font.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		var w := minf(one, maxw)
		var h := _font.get_multiline_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, maxw, fs).y
		var out: bool = m["out"]
		var r := Rect2(W - w - 26 if out else 10, y - h - 22, w + 16, h + 10)
		if r.end.y > BAR and r.position.y < H - BAR:
			draw_style_box(_box(Color("1f4a3a") if out else Color("1d3340"), 6), r)
			draw_multiline_string(_font, r.position + Vector2(8, 4 + _font.get_ascent(fs)), t, HORIZONTAL_ALIGNMENT_LEFT, maxw, fs, -1, C_TEXT)
			_text(m["time"], Vector2(r.position.x, r.end.y + 10), 10, C_DIM, HORIZONTAL_ALIGNMENT_RIGHT if out else HORIZONTAL_ALIGNMENT_LEFT, r.size.x)
		y = r.position.y - 6.0
		top_y = y
	_scroll_max = maxf(0.0, (BAR + 4.0) - (top_y - _scroll))
	_status(_chat)
	_soft("", "Назад")


func _draw_task() -> void:
	_status("Задание")
	_text("! Задание", Vector2(12, BAR + 22), 17, C_ACCENT)
	draw_multiline_string(_font, Vector2(12, BAR + 46), Game.objective, HORIZONTAL_ALIGNMENT_LEFT, W - 24, 18, -1, C_TEXT)
	_soft("", "Назад")


func _draw_music() -> void:
	_status("Музыка")
	if _tracks.is_empty():
		_text("Нет песен в памяти", Vector2(0, 120), 15, C_DIM, HORIZONTAL_ALIGNMENT_CENTER, W)
		_soft("", "Назад")
		return
	var rh := 30.0
	for i in _tracks.size():
		var y := BAR + 4 + i * rh
		if i == _row:
			draw_rect(Rect2(0, y, W, rh - 1), C_SEL)
		var playing := i == _track
		if playing:
			_play_mark(Vector2(16, y + 15), _music.stream_paused, C_ACCENT)
		_text(_short(_tracks[i]["title"], 34), Vector2(30, y + 21), 15, C_ACCENT if playing else C_TEXT)
	# сейчас играет: полоска и время, громкость
	var py := H - BAR - 46.0
	draw_line(Vector2(0, py - 6), Vector2(W, py - 6), Color("18303a"))
	if _track >= 0 and _music.stream:
		var len_s := _music.stream.get_length()
		var pos := _music.get_playback_position()
		var bar := Rect2(12, py + 4, W - 24, 6)
		draw_rect(bar, Color("18303a"))
		draw_rect(Rect2(bar.position, Vector2(bar.size.x * clampf(pos / maxf(len_s, 0.01), 0.0, 1.0), bar.size.y)), C_ACCENT)
		_text(_mmss(pos) + " / " + _mmss(len_s), Vector2(12, py + 30), 13, C_LCD)
	_text("Громкость %d/10" % cfg["volume"], Vector2(0, py + 30), 13, C_LCD, HORIZONTAL_ALIGNMENT_RIGHT, W - 12)
	_soft("Пауза" if _row == _track and not _music.stream_paused else "Играть", "Назад")


## Значок «играет» (треугольник) или «пауза» (две палочки).
func _play_mark(c: Vector2, paused: bool, col: Color) -> void:
	if paused:
		draw_rect(Rect2(c + Vector2(-5, -6), Vector2(3.5, 12)), col)
		draw_rect(Rect2(c + Vector2(1.5, -6), Vector2(3.5, 12)), col)
	else:
		draw_colored_polygon(PackedVector2Array([c + Vector2(-5, -6), c + Vector2(6, 0), c + Vector2(-5, 6)]), col)


func _mmss(sec: float) -> String:
	return "%d:%02d" % [floori(sec / 60.0), int(sec) % 60]


func _draw_games() -> void:
	_status("Игры")
	var rh := 52.0
	for i in GAME_NAMES.size():
		var y := BAR + 6 + i * rh
		var r := Rect2(8, y, W - 16, rh - 6)
		draw_style_box(_box(C_SEL if i == _row else Color("0d1a22"), 5, C_ACCENT if i == _row else Color("18303a"), 2 if i == _row else 1), r)
		_draw_game_icon(i, Vector2(r.position.x + 26, r.get_center().y))
		_text(GAME_NAMES[i], Vector2(r.position.x + 54, y + 22), 18, C_TEXT)
		_text("Рекорд: %d" % PhoneGame.best.get(GAME_NAMES[i], 0), Vector2(r.position.x + 54, y + 40), 13, C_DIM)
	_soft("Играть", "Назад")


func _draw_game_icon(i: int, c: Vector2) -> void:
	match i:
		0:                                            # змейка
			draw_rect(Rect2(c - Vector2(16, 16), Vector2(32, 32)), Color("9cb84a"))
			for p: Vector2 in [Vector2(-10, 6), Vector2(-4, 6), Vector2(2, 6), Vector2(2, 0), Vector2(2, -6), Vector2(8, -6)]:
				draw_rect(Rect2(c + p - Vector2(2.5, 2.5), Vector2(5, 5)), Color("1d3311"))
			draw_rect(Rect2(c + Vector2(-11, -9), Vector2(4, 4)), Color("1d3311"))
		1:                                            # танк Battle City
			draw_rect(Rect2(c - Vector2(16, 16), Vector2(32, 32)), Color("101214"))
			draw_rect(Rect2(c + Vector2(-10, -10), Vector2(5, 20)), Color("6a5a20"))
			draw_rect(Rect2(c + Vector2(5, -10), Vector2(5, 20)), Color("6a5a20"))
			draw_rect(Rect2(c + Vector2(-6, -7), Vector2(12, 14)), Color("e8c040"))
			draw_line(c, c + Vector2(0, -14), Color("f4dc80"), 3.0)
		_:                                            # пакман
			draw_rect(Rect2(c - Vector2(16, 16), Vector2(32, 32)), Color("05080c"))
			_pac_body(c, 9.0, 0.35, Vector2i.RIGHT)


## Жёлтый пакман с открытым ртом (open — доля от полного раскрытия).
func _pac_body(c: Vector2, r: float, open: float, d: Vector2i) -> void:
	var a0 := Vector2(d).angle()
	var half := open * 0.8
	var pts := PackedVector2Array([c])
	for i in 21:
		pts.append(c + Vector2.from_angle(a0 + half + (TAU - 2.0 * half) * i / 20.0) * r)
	draw_colored_polygon(pts, Color("ffe135"))


func _draw_game() -> void:
	_game.draw(self)
	_status(_game.status())
	_soft("" if _game.over else "Огонь" if _game is PhoneBattleCity else "", "Выход")


## Браузер: страница поисковика грузится и падает — интернета нет (денег на счету тоже).
func _draw_web() -> void:
	draw_rect(Rect2(0, 0, W, H), Color("f4f6f8"))
	_status("Интернет")
	var addr := Rect2(6, BAR + 4, W - 12, 22)
	draw_style_box(_box(Color.WHITE, 3, Color("8a96a0"), 1), addr)
	_text("www.google.com", addr.position + Vector2(8, 16), 14, Color("3a4650"))
	var load_k := clampf(_web_t / 1.8, 0.0, 1.0)
	if load_k < 1.0:
		var bar := Rect2(20, 124, W - 40, 10)
		draw_rect(bar, Color("d0d6dc"))
		draw_rect(Rect2(bar.position, Vector2(bar.size.x * minf(load_k * 1.3, 0.92), bar.size.y)), Color("3a7bd5"))
		_text("Загрузка…", Vector2(0, 112), 15, Color("3a4650"), HORIZONTAL_ALIGNMENT_CENTER, W)
		_soft("", "Назад")
		return
	var logo := "Google"
	var cols := [Color("3a7bd5"), Color("d9483c"), Color("e6b425"), Color("3a7bd5"), Color("3aa457"), Color("d9483c")]
	var x := W / 2.0 - _font.get_string_size(logo, HORIZONTAL_ALIGNMENT_LEFT, -1, 40).x / 2.0
	for i in logo.length():
		var ch := logo[i]
		_text(ch, Vector2(x, 106), 40, cols[i])
		x += _font.get_string_size(ch, HORIZONTAL_ALIGNMENT_LEFT, -1, 40).x
	var field := Rect2(30, 118, W - 60, 22)
	draw_style_box(_box(Color.WHITE, 3, Color("b0bac4"), 1), field)
	_text("нет соединения с интернетом", Vector2(0, 168), 16, Color("c0392b"), HORIZONTAL_ALIGNMENT_CENTER, W)
	_text("Проверьте настройки или баланс", Vector2(0, 188), 12, Color("6a7680"), HORIZONTAL_ALIGNMENT_CENTER, W)
	_soft("Повторить", "Назад")


func _draw_settings() -> void:
	_status("Настройки")
	var rh := 36.0
	for i in SETTINGS.size():
		var y := BAR + 4 + i * rh
		if i == _row:
			draw_rect(Rect2(0, y, W, rh - 2), C_SEL)
		var key: String = SETTINGS[i][1]
		_text(SETTINGS[i][0], Vector2(12, y + 23), 16, C_TEXT)
		var v: Variant = cfg[key]
		if v is bool:
			_text("Вкл." if v else "Выкл.", Vector2(0, y + 23), 16, C_ACCENT if v else C_DIM, HORIZONTAL_ALIGNMENT_RIGHT, W - 12)
		else:
			var steps := 10 if key == "volume" else 5
			for s in steps:
				var bw := 70.0 / steps
				draw_rect(Rect2(W - 82 + s * bw, y + 12, bw - 2, 12), C_ACCENT if s < int(v) else Color("18303a"))
	_text("Nokia X2-01", Vector2(0, H - BAR - 10), 12, C_DIM, HORIZONTAL_ALIGNMENT_CENTER, W)
	_soft("Изменить" if cfg[SETTINGS[_row][1]] is bool else "Влево/вправо", "Назад")


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
