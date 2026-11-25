## Рабочий стол компа Юрчика (внутри SubViewport, см. scripts/world/pc_seat.gd).
## Пока — только фон в цветах Windows 7; окна, «Пуск» и панель задач — следующий шаг.
extends Control


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)


func _draw() -> void:
	var s := size
	# тёмно-синий фон с более светлым пятном справа сверху, как у стандартных обоев Windows 7
	var steps := 48
	for i in steps:
		var t := float(i) / float(steps - 1)
		var c := Color(0.02, 0.18, 0.42).lerp(Color(0.0, 0.07, 0.22), t)
		draw_rect(Rect2(0, s.y * float(i) / steps, s.x, s.y / steps + 1.0), c)
	for r in range(10, 0, -1):
		var k := float(r) / 10.0
		draw_circle(Vector2(s.x * 0.62, s.y * 0.4), s.y * 0.5 * k, Color(0.15, 0.55, 0.85, 0.035))
