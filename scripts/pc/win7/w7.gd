## Общее для «Windows 7» на компе Юрчика: шрифт, иконки, тема и рисование градиентных
## скруглённых плашек (кнопки, выделение, панели — как в Aero).
## Все размеры — в «логических» пикселях экрана 1024×820 (Windows на 125 %, см. pc_desktop.gd).
class_name W7
extends RefCounted

const FONT: FontFile = preload("res://assets/fonts/segoeui.ttf")
const FONT_BOLD: FontFile = preload("res://assets/fonts/segoeuib.ttf")
const FONT_MONO: FontFile = preload("res://assets/fonts/lucon.ttf")
const ICON_DIR := "res://assets/pc/win7/icons/%s_%d.png"
const TEXT := Color("000000")
const TEXT_GRAY := Color("6d6d6d")
const LINK := Color("1e3287")
const GLASS_SHADER: Shader = preload("res://shaders/pc/w7_glass.gdshader")

static var _icons := {}
static var _theme: Theme


## Иконка Windows: name — из assets/pc/win7/icons, size — 16, 32 или 48.
static func icon(name: String, size := 48) -> Texture2D:
	var key := "%s_%d" % [name, size]
	if not _icons.has(key):
		var path := ICON_DIR % [name, size]
		_icons[key] = load(path) if ResourceLoader.exists(path) else null
	return _icons[key]


static func theme() -> Theme:
	if _theme:
		return _theme
	var t := Theme.new()
	t.default_font = FONT
	t.default_font_size = 12
	t.set_color("font_color", "Label", TEXT)
	# кнопка Windows 7: серый глянец, при наведении — голубой
	t.set_stylebox("normal", "Button", W7Box.make([[0.0, "f2f2f2"], [0.5, "ebebeb"], [0.5, "dddddd"], [1.0, "cfcfcf"]], "707070", 3, "ffffffb0"))
	t.set_stylebox("hover", "Button", W7Box.make([[0.0, "eaf6fd"], [0.5, "d9f0fc"], [0.5, "bee6fd"], [1.0, "a7d9f5"]], "3c7fb1", 3, "ffffffb0"))
	t.set_stylebox("pressed", "Button", W7Box.make([[0.0, "e5f4fc"], [0.5, "c4e5f6"], [0.5, "98d1ef"], [1.0, "68b3db"]], "2c628b", 3, "00000000"))
	t.set_stylebox("disabled", "Button", W7Box.make([[0.0, "f4f4f4"], [1.0, "f4f4f4"]], "adb2b5", 3, "00000000"))
	t.set_stylebox("focus", "Button", W7Box.make([], "3399ff", 3, "00000000", 0.0, true))
	for s: String in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color", "font_hover_pressed_color"]:
		t.set_color(s, "Button", TEXT)
	t.set_color("font_disabled_color", "Button", Color("838383"))
	# поля ввода: белые, рамка как в Windows 7
	var field := StyleBoxFlat.new()
	field.bg_color = Color.WHITE
	field.border_color = Color("abadb3")
	field.set_border_width_all(1)
	field.border_width_top = 1
	field.content_margin_left = 4
	field.content_margin_right = 4
	field.content_margin_top = 2
	field.content_margin_bottom = 2
	var field_focus := field.duplicate() as StyleBoxFlat
	field_focus.border_color = Color("3d7bad")
	for k: String in ["LineEdit", "TextEdit"]:
		t.set_stylebox("normal", k, field)
		t.set_stylebox("focus", k, field_focus)
		t.set_stylebox("read_only", k, field)
		t.set_color("font_color", k, TEXT)
		t.set_color("font_placeholder_color", k, Color("6d6d6d"))
		t.set_color("caret_color", k, TEXT)
		t.set_color("selection_color", k, Color("3399ff"))
		t.set_color("font_selected_color", k, Color.WHITE)
		t.set_color("background_color", k, Color.WHITE)
	# полосы прокрутки Windows 7
	var track := StyleBoxFlat.new()
	track.bg_color = Color("eaeaea")
	track.content_margin_left = 17
	track.content_margin_top = 17
	var grab := W7Box.make([[0.0, "f3f3f3"], [1.0, "dadada"]], "9a9a9a", 2, "ffffffc0")
	var grab_hi := W7Box.make([[0.0, "e3f4fc"], [1.0, "a9dbf6"]], "3c7fb1", 2, "ffffffc0")
	for k: String in ["VScrollBar", "HScrollBar"]:
		t.set_stylebox("scroll", k, track)
		t.set_stylebox("scroll_focus", k, track)
		t.set_stylebox("grabber", k, grab)
		t.set_stylebox("grabber_highlight", k, grab_hi)
		t.set_stylebox("grabber_pressed", k, grab_hi)
	_theme = t
	return t


## Скруглённый контур прямоугольника: radii — углы (лево-верх, право-верх, право-низ, лево-низ).
static func rounded(rect: Rect2, radii: Vector4, seg := 4) -> PackedVector2Array:
	var pts := PackedVector2Array()
	var corners := [
		[Vector2(rect.position.x + radii.x, rect.position.y + radii.x), radii.x, PI],
		[Vector2(rect.end.x - radii.y, rect.position.y + radii.y), radii.y, PI * 1.5],
		[Vector2(rect.end.x - radii.z, rect.end.y - radii.z), radii.z, 0.0],
		[Vector2(rect.position.x + radii.w, rect.end.y - radii.w), radii.w, PI * 0.5],
	]
	for c: Array in corners:
		var r: float = c[1]
		if r <= 0.01:
			pts.append(c[0])
			continue
		for i in seg + 1:
			var a: float = c[2] + PI * 0.5 * float(i) / float(seg)
			pts.append(c[0] + Vector2(cos(a), sin(a)) * r)
	return pts


## Цвет вертикального градиента в точке t (0..1). stops — [[t, цвет], ...], цвет — Color или "rrggbb".
static func grad_at(stops: Array, t: float) -> Color:
	if stops.is_empty():
		return Color.TRANSPARENT
	if t <= stops[0][0]:
		return Color(stops[0][1])
	for i in range(1, stops.size()):
		if t <= stops[i][0]:
			var a: float = stops[i - 1][0]
			var b: float = stops[i][0]
			var k := 0.0 if b - a < 0.0001 else (t - a) / (b - a)
			return Color(stops[i - 1][1]).lerp(Color(stops[i][1]), k)
	return Color(stops[-1][1])


## Залить скруглённый прямоугольник вертикальным градиентом (с резкими ступеньками, как глянец Aero).
static func fill(ci: RID, rect: Rect2, radius: Variant, stops: Array) -> void:
	if stops.is_empty() or rect.size.x <= 0.0 or rect.size.y <= 0.0:
		return
	var radii: Vector4 = radius if radius is Vector4 else Vector4.ONE * float(radius)
	var outline := rounded(rect, radii)
	var cuts: Array[float] = [0.0]
	for s: Array in stops:
		if s[0] > 0.0 and s[0] < 1.0:
			cuts.append(s[0])
	cuts.append(1.0)
	for i in cuts.size() - 1:
		var y0 := rect.position.y + rect.size.y * cuts[i]
		var y1 := rect.position.y + rect.size.y * cuts[i + 1]
		if y1 - y0 < 0.01:
			continue
		var band := PackedVector2Array([Vector2(rect.position.x - 1, y0), Vector2(rect.end.x + 1, y0),
				Vector2(rect.end.x + 1, y1), Vector2(rect.position.x - 1, y1)])
		# цвет внутри полосы берём чуть внутри неё, чтобы ступенька градиента попала на её край
		var t0 := cuts[i] + 0.0001
		var t1 := cuts[i + 1] - 0.0001
		for poly: PackedVector2Array in Geometry2D.intersect_polygons(outline, band):
			var cols := PackedColorArray()
			for p: Vector2 in poly:
				var k := clampf((p.y - y0) / (y1 - y0), 0.0, 1.0)
				cols.append(grad_at(stops, lerpf(t0, t1, k)))
			RenderingServer.canvas_item_add_polygon(ci, poly, cols)


## Обвести скруглённый прямоугольник.
static func stroke(ci: RID, rect: Rect2, radius: Variant, color: Color, width := 1.0) -> void:
	if color.a <= 0.0:
		return
	var radii: Vector4 = radius if radius is Vector4 else Vector4.ONE * float(radius)
	var pts := rounded(rect.grow(-width * 0.5), radii)
	pts.append(pts[0])
	RenderingServer.canvas_item_add_polyline(ci, pts, PackedColorArray([color]), width, true)


## Плашка целиком: градиент, тёмная рамка и светлая рамка внутри.
static func box(ci: RID, rect: Rect2, radius: float, stops: Array, border: Variant, inner: Variant = null) -> void:
	fill(ci, rect, radius, stops)
	if inner != null:
		stroke(ci, rect.grow(-1), maxf(radius - 1.0, 0.0), Color(inner))
	if border != null:
		stroke(ci, rect, radius, Color(border))


## Текст с белым ореолом, как заголовки окон Aero на стекле.
static func glow_text(ci: CanvasItem, pos: Vector2, text: String, size := 12, color := Color.BLACK, glow := Color(1, 1, 1, 0.55)) -> void:
	for o: Vector2 in [Vector2(-1, 0), Vector2(1, 0), Vector2(0, -1), Vector2(0, 1), Vector2(-1, -1), Vector2(1, 1), Vector2(1, -1), Vector2(-1, 1), Vector2(2, 0), Vector2(-2, 0)]:
		ci.draw_string(FONT, pos + o, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Color(glow, glow.a * 0.35))
	ci.draw_string(FONT, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)


## Текст с тенью (подписи значков на рабочем столе, белый текст на стекле).
static func shadow_text(ci: CanvasItem, pos: Vector2, text: String, size := 12, color := Color.WHITE, width := -1.0, align := HORIZONTAL_ALIGNMENT_LEFT) -> void:
	ci.draw_string(FONT, pos + Vector2(1, 1), text, align, width, size, Color(0, 0, 0, 0.75))
	ci.draw_string(FONT, pos + Vector2(0, 1), text, align, width, size, Color(0, 0, 0, 0.35))
	ci.draw_string(FONT, pos, text, align, width, size, color)


static func text_width(text: String, size := 12, bold := false) -> float:
	return (FONT_BOLD if bold else FONT).get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x


## Материал «стекла» Aero: размывает то, что под ним, и тонирует цветом вершин.
static func glass_material(blur := 1.6) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = GLASS_SHADER
	m.set_shader_parameter("blur", blur)
	return m


## Слой стекла: копия экрана под ним + Control с материалом (рисует колбэк draw_fn(control)).
static func glass_layer(parent: Control, draw_fn: Callable, blur := 1.6) -> Control:
	var copy := BackBufferCopy.new()
	copy.copy_mode = BackBufferCopy.COPY_MODE_VIEWPORT
	parent.add_child(copy)
	var g := Control.new()
	g.name = "Glass"
	g.mouse_filter = Control.MOUSE_FILTER_IGNORE
	g.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	g.material = glass_material(blur)
	g.draw.connect(draw_fn.bind(g))
	parent.add_child(g)
	return g


## Дата и время «как в трее»: часы идут вместе с игровой ночью.
static func now_time() -> String:
	return Game.clock_text()


static func now_date() -> String:
	var d := Time.get_date_dict_from_system()
	return "%02d.%02d.%d" % [d["day"], d["month"], d["year"]]
