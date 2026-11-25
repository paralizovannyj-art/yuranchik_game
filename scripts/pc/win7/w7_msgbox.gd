## Окошко-сообщение Windows 7: белая часть со значком и текстом, серая полоса с кнопками снизу.
class_name W7MsgBox
extends Control

const BAR_H := 42.0

var text := ""
var icon_name := ""
var buttons: Array = []
var on_done: Callable
var window: W7Window
var _answered := false
var _btns: Array[Button] = []


func setup(p_text: String, p_icon: String, p_buttons: Array, p_done: Callable) -> W7MsgBox:
	text = p_text
	icon_name = p_icon
	buttons = p_buttons
	on_done = p_done
	return self


## Размер окна под текст.
func wanted_size() -> Vector2:
	var tw := 0.0
	var lines := text.split("\n")
	for l: String in lines:
		tw = maxf(tw, W7.text_width(l))
	tw = clampf(tw, 180.0, 420.0)
	var th := 0.0
	for l: String in lines:
		th += 16.0 * maxf(1.0, ceilf(W7.text_width(l) / tw))
	var w := tw + (64.0 + 30.0 if icon_name != "" else 20.0 + 30.0)
	w = maxf(w, buttons.size() * 94.0 + 20.0)
	var h := maxf(th, 32.0) + 44.0 + BAR_H
	return Vector2(w, h)


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	focus_mode = Control.FOCUS_ALL
	var x := size.x - 10.0
	for i in range(buttons.size() - 1, -1, -1):
		var b := Button.new()
		b.text = buttons[i]
		b.size = Vector2(86, 23)
		x -= 86.0
		b.position = Vector2(x, size.y - BAR_H + 10)
		b.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT, Control.PRESET_MODE_KEEP_SIZE)
		x -= 8.0
		var label: String = buttons[i]
		b.pressed.connect(func() -> void: answer(label))
		add_child(b)
		_btns.push_front(b)
	if not _btns.is_empty():
		_btns[0].call_deferred("grab_focus")


func _draw() -> void:
	var r := Rect2(Vector2.ZERO, size)
	draw_rect(r, Color.WHITE)
	draw_rect(Rect2(0, size.y - BAR_H, size.x, BAR_H), Color("f0f0f0"))
	draw_line(Vector2(0, size.y - BAR_H + 0.5), Vector2(size.x, size.y - BAR_H + 0.5), Color("dfdfdf"))
	var tx := 20.0
	if icon_name != "":
		var ic := W7.icon(_icon_file(), 32)
		if ic:
			draw_texture_rect(ic, Rect2(20, 20, 32, 32), false)
		tx = 64.0
	var y := 32.0 if icon_name != "" else 28.0
	var lines := text.split("\n")
	if lines.size() == 1:
		y = 40.0 if icon_name != "" else 30.0
	for l: String in lines:
		var lw := size.x - tx - 20.0
		draw_multiline_string(W7.FONT, Vector2(tx, y), l, HORIZONTAL_ALIGNMENT_LEFT, lw, 12, -1, Color.BLACK)
		y += 16.0 * maxf(1.0, ceilf(W7.text_width(l) / lw))


func _icon_file() -> String:
	match icon_name:
		"error": return "error"
		"warning", "warning_q": return "warning"
		"question": return "help"
	return icon_name


func answer(label: String) -> void:
	if _answered:
		return
	_answered = true
	if on_done.is_valid():
		on_done.call(label)
	if window:
		window.close()


## Закрыли крестиком — как «Нет» / «Отмена» (последняя кнопка).
func can_close() -> bool:
	answer(buttons[-1] if not buttons.is_empty() else "")
	return false


func _gui_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode in [KEY_ENTER, KEY_KP_ENTER] and not _btns.is_empty():
			for b: Button in _btns:
				if b.has_focus():
					answer(b.text)
					accept_event()
					return
			answer(buttons[0])
			accept_event()
		elif event.keycode == KEY_ESCAPE:
			can_close()
			accept_event()
