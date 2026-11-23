## Иконки экрана телефона (рисуются кодом, без картинок): музыка, сообщения, игры, интернет, настройки,
## самочувствие, шагомер. Рисуются в квадрате 32×32 вокруг центра, s — масштаб.
class_name PhoneIcons


static func draw(ci: CanvasItem, kind: String, c: Vector2, s := 1.0) -> void:
	ci.draw_set_transform(c, 0.0, Vector2(s, s))
	match kind:
		"music": _music(ci)
		"sms": _sms(ci)
		"games": _games(ci)
		"web": _web(ci)
		"settings": _settings(ci)
		"health": _health(ci)
		"steps": _steps(ci)
	ci.draw_set_transform(Vector2.ZERO)


static func _box(col: Color, radius: int, border := Color.TRANSPARENT, bw := 0) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = col
	sb.set_corner_radius_all(radius)
	sb.border_color = border
	sb.set_border_width_all(bw)
	sb.anti_aliasing = true
	return sb


## Нота на розовом квадрате, сзади выглядывает диск.
static func _music(ci: CanvasItem) -> void:
	ci.draw_circle(Vector2(8, 2), 11.0, Color("c9ccd4"))
	ci.draw_circle(Vector2(8, 2), 9.0, Color("9ea3ae"))
	ci.draw_circle(Vector2(8, 2), 3.0, Color("e8eaee"))
	ci.draw_style_box(_box(Color("b8309e"), 4), Rect2(-16, -14, 24, 28))
	ci.draw_rect(Rect2(-16, -14, 24, 9), Color(1, 1, 1, 0.14))
	ci.draw_circle(Vector2(-8, 6), 4.0, Color.WHITE)
	ci.draw_line(Vector2(-4.5, 6), Vector2(-4.5, -9), Color.WHITE, 2.5)
	ci.draw_line(Vector2(-4.5, -9), Vector2(2, -6), Color.WHITE, 3.0)


## Белое облачко с текстом и жёлтое поверх.
static func _sms(ci: CanvasItem) -> void:
	ci.draw_style_box(_box(Color("eef0f3"), 3), Rect2(-16, -14, 24, 17))
	ci.draw_colored_polygon(PackedVector2Array([Vector2(-12, 3), Vector2(-6, 3), Vector2(-12, 8)]), Color("eef0f3"))
	for y: float in [-10.0, -6.0, -2.0]:
		ci.draw_line(Vector2(-13, y), Vector2(4, y), Color("9aa0a8"), 1.5)
	ci.draw_style_box(_box(Color("f2b51c"), 3), Rect2(-4, -3, 21, 15))
	ci.draw_colored_polygon(PackedVector2Array([Vector2(10, 12), Vector2(15, 12), Vector2(15, 17)]), Color("f2b51c"))
	for y: float in [1.0, 5.0]:
		ci.draw_line(Vector2(-1, y), Vector2(13, y), Color("a8720a"), 1.5)


## Синий джойстик: крестовина и две кнопки.
static func _games(ci: CanvasItem) -> void:
	var col := Color("4d86da")
	ci.draw_circle(Vector2(-10, 6), 7.0, col)
	ci.draw_circle(Vector2(10, 6), 7.0, col)
	ci.draw_style_box(_box(col, 7), Rect2(-17, -9, 34, 17))
	ci.draw_rect(Rect2(-15, -8, 30, 5), Color(1, 1, 1, 0.18))
	ci.draw_rect(Rect2(-12, -2, 9, 3), Color.WHITE)
	ci.draw_rect(Rect2(-9, -5, 3, 9), Color.WHITE)
	ci.draw_circle(Vector2(7, -1), 2.3, Color.WHITE)
	ci.draw_circle(Vector2(11, 3), 2.3, Color.WHITE)


## Земной шар.
static func _web(ci: CanvasItem) -> void:
	ci.draw_circle(Vector2.ZERO, 15.0, Color("2a72cc"))
	var land := Color("56b43a")
	ci.draw_colored_polygon(PackedVector2Array([Vector2(-11, -9), Vector2(-3, -12), Vector2(1, -7), Vector2(-2, -2),
		Vector2(-6, 1), Vector2(-5, 8), Vector2(-9, 6), Vector2(-13, -1)]), land)
	ci.draw_colored_polygon(PackedVector2Array([Vector2(4, -4), Vector2(11, -7), Vector2(14, 0), Vector2(10, 9),
		Vector2(5, 11), Vector2(3, 4)]), land)
	ci.draw_arc(Vector2.ZERO, 12.5, PI * 1.1, PI * 1.45, 8, Color(1, 1, 1, 0.45), 2.0)
	ci.draw_arc(Vector2.ZERO, 15.0, 0.0, TAU, 32, Color("174a8a"), 1.0)


## Шестерёнка.
static func _settings(ci: CanvasItem) -> void:
	var col := Color("a4adb8")
	var pts := PackedVector2Array()
	for i in 16:
		var a := TAU * i / 16.0
		var r := 15.0 if i % 2 == 0 else 11.0
		pts.append(Vector2.from_angle(a - 0.12) * r)
		pts.append(Vector2.from_angle(a + 0.12) * r)
	ci.draw_colored_polygon(pts, col)
	ci.draw_circle(Vector2.ZERO, 11.0, col)
	ci.draw_arc(Vector2.ZERO, 9.0, PI, PI * 1.6, 8, Color(1, 1, 1, 0.4), 2.0)
	ci.draw_circle(Vector2.ZERO, 5.0, Color("2b3036"))


## Сердце с кардиограммой.
static func _health(ci: CanvasItem) -> void:
	var red := Color("d9483c")
	ci.draw_circle(Vector2(-7, -5), 9.0, red)
	ci.draw_circle(Vector2(7, -5), 9.0, red)
	ci.draw_colored_polygon(PackedVector2Array([Vector2(-16, -2), Vector2(16, -2), Vector2(0, 15)]), red)
	ci.draw_polyline(PackedVector2Array([Vector2(-13, -2), Vector2(-5, -2), Vector2(-2, -9), Vector2(2, 5),
		Vector2(5, -2), Vector2(13, -2)]), Color.WHITE, 2.0)


## Следы.
static func _steps(ci: CanvasItem) -> void:
	var col := Color("9fd0c8")
	ci.draw_style_box(_box(col, 4), Rect2(-13, -15, 9, 17))
	ci.draw_style_box(_box(col, 4), Rect2(3, -3, 9, 17))
	ci.draw_rect(Rect2(-12, 4, 7, 4), col)
	ci.draw_rect(Rect2(4, -9, 7, 4), col)
