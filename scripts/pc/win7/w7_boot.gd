## Экраны загрузки и выключения Windows 7: чёрный «Запуск Windows» со сходящимися огоньками-флажком,
## синий «Добро пожаловать» с крутящимся кольцом и «Завершение работы».
class_name W7Boot
extends Control

var mode := ""             ## "" (ничего), black, starting, welcome, shutdown
var _t := 0.0
var _text := ""


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


func show_mode(m: String, text := "") -> void:
	mode = m
	_text = text
	_t = 0.0
	visible = m != ""
	mouse_filter = Control.MOUSE_FILTER_STOP if visible else Control.MOUSE_FILTER_IGNORE
	queue_redraw()


func _process(delta: float) -> void:
	if visible:
		_t += delta
		queue_redraw()


func _draw() -> void:
	var s := size
	match mode:
		"black":
			draw_rect(Rect2(Vector2.ZERO, s), Color.BLACK)
		"starting":
			_draw_starting(s)
		"welcome", "shutdown":
			_draw_logon_bg(s)
			_draw_spinner(Vector2(s.x * 0.5 - W7.text_width(_text, 24) * 0.5 - 26, s.y * 0.5))
			var p := Vector2(s.x * 0.5 - W7.text_width(_text, 24) * 0.5 + 6, s.y * 0.5 + 9)
			draw_string(W7.FONT, p + Vector2(1, 2), _text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, Color(0, 0, 0, 0.45))
			draw_string(W7.FONT, p, _text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, Color.WHITE)


## «Запуск Windows»: четыре цветных огонька слетаются и складываются во флажок.
func _draw_starting(s: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, s), Color.BLACK)
	var c := Vector2(s.x * 0.5, s.y * 0.43)
	var cols := [Color("f25022"), Color("7fba00"), Color("00a4ef"), Color("ffb900")]
	var targets := [Vector2(-1, -1), Vector2(1, -1), Vector2(-1, 1), Vector2(1, 1)]
	var gather := clampf(_t / 2.2, 0.0, 1.0)
	var e := 1.0 - pow(1.0 - gather, 3.0)
	for i in 4:
		var a := _t * 2.6 + i * TAU / 4.0
		var swirl := Vector2(cos(a), sin(a) * 0.6) * 120.0 * (1.0 - e)
		var p: Vector2 = c + targets[i] * 13.0 * e + swirl
		var glow: Color = cols[i]
		for k in 6:
			glow.a = 0.06 * (1.0 - e * 0.6)
			draw_circle(p, 18.0 - k * 2.5, glow)
		var core: Color = cols[i].lightened(0.3)
		core.a = 1.0 - e * 0.8
		draw_circle(p, 4.0, core)
	if gather > 0.6:
		var fa := clampf((gather - 0.6) / 0.4, 0.0, 1.0)
		var pulse := 0.85 + 0.15 * sin(_t * 2.0)
		for k in 5:
			draw_circle(c, 60.0 - k * 9.0, Color(1, 1, 1, 0.02 * fa * pulse))
		W7Taskbar._draw_flag(self, c, 26.0, fa)
	var tc := Color(1, 1, 1, clampf(_t / 1.0, 0.0, 1.0) * 0.85)
	draw_string(W7.FONT, Vector2(0, s.y * 0.43 + 90), "Запуск Windows", HORIZONTAL_ALIGNMENT_CENTER, s.x, 20, tc)
	draw_string(W7.FONT, Vector2(0, s.y - 40), "© Корпорация Майкрософт", HORIZONTAL_ALIGNMENT_CENTER, s.x, 12, Color(1, 1, 1, 0.55))


## Фон экрана входа: синий градиент с мягкими световыми дугами и подписью внизу.
func _draw_logon_bg(s: Vector2) -> void:
	var steps := 40
	for i in steps:
		var t := float(i) / (steps - 1)
		draw_rect(Rect2(0, s.y * i / steps, s.x, s.y / steps + 1.0), Color("1f6db8").lerp(Color("0a3365"), t))
	for k in 12:
		draw_circle(Vector2(s.x * 0.5, s.y * 0.28), s.x * (0.55 - k * 0.04), Color(0.45, 0.75, 1.0, 0.025))
	for a: Array in [[0.0, 0.07], [40.0, 0.05], [-50.0, 0.04]]:
		var pts := PackedVector2Array()
		for k in 33:
			var x := s.x * float(k) / 32.0
			pts.append(Vector2(x, s.y * 0.72 + a[0] + sin(float(k) / 32.0 * PI) * -120.0))
		draw_polyline(pts, Color(1, 1, 1, a[1]), 24.0, true)
		draw_polyline(pts, Color(1, 1, 1, a[1] * 1.6), 3.0, true)
	var by := s.y - 46
	W7Taskbar._draw_flag(self, Vector2(s.x * 0.5 - 88, by - 5), 9.0, 0.95)
	draw_string(W7.FONT, Vector2(s.x * 0.5 - 72, by + 2), "Windows 7", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color.WHITE)
	draw_string(W7.FONT, Vector2(s.x * 0.5 + 34, by + 2), "Максимальная", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1, 1, 1, 0.85))


## Крутящееся «колёсико ожидания» Windows 7 (голубое кольцо с бегущим бликом).
func _draw_spinner(c: Vector2) -> void:
	draw_arc(c, 11, 0, TAU, 32, Color(0.6, 0.8, 1.0, 0.25), 5.0, true)
	var a := _t * 5.0
	for k in 10:
		var f := float(k) / 10.0
		draw_arc(c, 11, a - f * 1.6, a - f * 1.6 - 0.2, 4, Color(0.75, 0.95, 1.0, 0.9 * (1.0 - f)), 5.0, true)
