## Настоящий браузер внутри окна Chrome на компе Юрчика: Chromium через gdcef (GdCEF / GdBrowserView).
## Страница рисуется в текстуру (её видно на 3D-мониторе вместе с PS2-фильтром), мышь, колёсико
## и клавиатура уходят в страницу. Адресная строка, «Назад», «Вперёд», «Обновить» — в W7Chrome.
## Сам gdcef (~360 МБ) лежит только локально в res://cef_artifacts/ — если его нет, показывается
## «Веб-страница недоступна», игра не падает.
class_name W7Web
extends Control

const HOME := "https://www.google.com"
const SEARCH := "https://www.google.com/search?q="
const CEF_NODE := "PcCEF"

var chrome: W7Chrome
var browser: Node                 ## GdBrowserView
var view: TextureRect
var failed := ""                  ## текст ошибки вместо страницы
var _k := 1.0                     ## во сколько раз пиксели экрана мельче «логических» (Windows на 125 %)
var _poll := 0.0
var _last_title := ""


func setup(p_chrome: W7Chrome) -> W7Web:
	chrome = p_chrome
	return self


## Один Chromium на всю игру: узел в корне дерева, переживает смену уровней.
static func cef(tree: SceneTree) -> Node:
	var root := tree.root
	var n := root.get_node_or_null(CEF_NODE)
	if n:
		return n if n.call("is_alive") else null
	if not ClassDB.class_exists("GdCEF"):
		return null
	n = ClassDB.instantiate("GdCEF")
	n.name = CEF_NODE
	root.add_child(n)
	var dir := ProjectSettings.globalize_path("user://browser")
	var ok: bool = n.call("initialize", {"locale": "ru", "enable_media_stream": false,
			"root_cache_path": dir, "cache_path": dir.path_join("profile")})   # куки и вход на сайты сохраняются
	if not ok:
		push_warning("gdcef: " + str(n.call("get_error")))
		return null
	return n


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	focus_mode = Control.FOCUS_CLICK
	view = TextureRect.new()
	view.name = "View"
	view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	view.stretch_mode = TextureRect.STRETCH_SCALE
	view.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	add_child(view)
	var vp := get_viewport() as SubViewport
	if vp and vp.size_2d_override.y > 0:
		_k = float(vp.size.y) / vp.size_2d_override.y
	chrome.navigate_requested.connect(open_text)
	chrome.back_requested.connect(func() -> void: if browser: browser.call("previous_page"))
	chrome.forward_requested.connect(func() -> void: if browser: browser.call("next_page"))
	chrome.reload_requested.connect(func() -> void:
		if browser:
			if chrome.loading:
				browser.call("stop_loading")
			else:
				browser.call("reload"))
	resized.connect(_fit)
	_fit.call_deferred()


## Пиксели страницы = пиксели экрана компа; масштаб страницы 125 %, как у остальной Windows.
func _px_size() -> Vector2i:
	return Vector2i((size * _k).round()).max(Vector2i(64, 64))


func _fit() -> void:
	view.position = Vector2.ZERO
	view.size = size
	if browser:
		browser.call("resize", Vector2(_px_size()))


## Текст из адресной строки: адрес — открыть, иначе — поиск в Google.
func open_text(t: String) -> void:
	if t == "":
		return
	var url := t
	var looks_url := not t.contains(" ") and (t.contains(".") or t.begins_with("localhost")) or t.contains("://")
	if not looks_url:
		url = SEARCH + t.uri_encode()
	elif not t.contains("://"):
		url = "http://" + t
	open(url)


func open(url: String) -> void:
	chrome.show_new_tab(false)
	failed = ""
	queue_redraw()
	if browser == null:
		_create(url)
	else:
		browser.call("load_url", url)
	grab_focus()


func _create(url: String) -> void:
	var c := cef(get_tree())
	if c == null:
		_fail("Не удаётся подключиться к Интернету.")
		return
	# gdcef берёт размер страницы из TextureRect при создании — создаём в пикселях экрана, потом растягиваем
	view.size = Vector2(_px_size())
	browser = c.call("create_browser", url, view, {"frame_rate": 30})
	view.size = size
	if browser == null:
		_fail("Не удаётся открыть страницу.")
		return
	browser.call("set_zoom_level", log(_k) / log(1.2))
	browser.connect("on_page_start_loading", func(_b: Node) -> void: _set_loading(true))
	browser.connect("on_page_loaded", func(_code: int, _b: Node) -> void:
		_set_loading(false)
		browser.call("set_zoom_level", log(_k) / log(1.2)))
	browser.connect("on_page_failed_loading", func(code: int, msg: String, _b: Node) -> void:
		_set_loading(false)
		if code != -3:                   # -3 — загрузку прервали сами (новый адрес), это не ошибка
			push_warning("browser: %d %s" % [code, msg]))
	browser.connect("on_cursor_changed", func(shape: int, _b: Node) -> void:
		mouse_default_cursor_shape = shape as Control.CursorShape)
	_set_loading(true)
	_fit()


func _fail(msg: String) -> void:
	failed = msg
	chrome.loading = false
	chrome.set_tab_title("Веб-страница недоступна")
	chrome.queue_redraw()
	queue_redraw()


func _set_loading(on: bool) -> void:
	chrome.loading = on
	_sync()


## Адрес, заголовок, «Назад/Вперёд» — из браузера в оболочку Chrome.
func _sync() -> void:
	if browser == null or not is_instance_valid(browser):
		return
	chrome.can_back = browser.call("has_previous_page")
	chrome.can_forward = browser.call("has_next_page")
	var url: String = browser.call("get_url")
	if not chrome.omnibox.has_focus() and url != "" and chrome.omnibox.text != url:
		chrome.omnibox.text = url
	var t: String = browser.call("get_title")
	if t == "" or t == url:
		t = url.trim_prefix("https://").trim_prefix("http://").get_slice("/", 0)
	if t != _last_title:
		_last_title = t
		chrome.set_tab_title(t)
	chrome.queue_redraw()


func _process(delta: float) -> void:
	_poll -= delta
	if _poll <= 0.0:
		_poll = 0.4
		_sync()


func _draw() -> void:
	if failed == "":
		return
	draw_rect(Rect2(Vector2.ZERO, size), Color.WHITE)
	var x := 60.0
	draw_string(W7.FONT, Vector2(x, 90), "Веб-страница недоступна", HORIZONTAL_ALIGNMENT_LEFT, -1, 20, Color("333333"))
	draw_string(W7.FONT, Vector2(x, 124), failed, HORIZONTAL_ALIGNMENT_LEFT, size.x - x * 2, 12, Color("555555"))
	draw_string(W7.FONT, Vector2(x, 146), "Проверьте подключение к сети и попробуйте ещё раз.", HORIZONTAL_ALIGNMENT_LEFT,
			size.x - x * 2, 12, Color("555555"))


# ---------- ввод: мышь и клавиатура уходят в страницу ----------

func _gui_input(event: InputEvent) -> void:
	if browser == null:
		return
	if event is InputEventMouse:
		var p: Vector2 = (event as InputEventMouse).position * _k
		browser.call("set_mouse_moved", int(p.x), int(p.y))
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		match mb.button_index:
			MOUSE_BUTTON_LEFT:
				if mb.pressed:
					grab_focus()
					browser.call("set_mouse_left_down")
				else:
					browser.call("set_mouse_left_up")
			MOUSE_BUTTON_RIGHT:
				browser.call("set_mouse_right_down" if mb.pressed else "set_mouse_right_up")
			MOUSE_BUTTON_MIDDLE:
				browser.call("set_mouse_middle_down" if mb.pressed else "set_mouse_middle_up")
			MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN:
				if mb.pressed:
					var d := 1 if mb.button_index == MOUSE_BUTTON_WHEEL_UP else -1
					browser.call("set_mouse_wheel_vertical", d * 12,   # 12×10 = 120, один щелчок колёсика Windows
							 mb.shift_pressed, mb.ctrl_pressed, mb.alt_pressed)
		accept_event()
	elif event is InputEventMouseMotion:
		accept_event()
	elif event is InputEventKey:
		var k := event as InputEventKey
		if k.ctrl_pressed and k.pressed and k.keycode == KEY_L:   # Ctrl+L — в адресную строку
			chrome.omnibox.grab_focus()
		else:
			var code := k.unicode if k.unicode != 0 and not k.ctrl_pressed and not k.alt_pressed else k.keycode
			browser.call("set_key_pressed", code, k.pressed, k.shift_pressed, k.alt_pressed, k.ctrl_pressed)
		accept_event()


func _exit_tree() -> void:
	if browser and is_instance_valid(browser):
		browser.call("close")
		browser.queue_free()                  # gdcef оставляет закрытый узел — убрать самим
	browser = null
