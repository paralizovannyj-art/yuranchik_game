## Инвентарь — сумка Юрчика: взгляд опускается внутрь, предметы лежат на дне (сетка 8×5 в духе RE4),
## их можно перекладывать и поворачивать. Сетка проступает швами, только когда несёшь предмет;
## название и описание написаны на полоске малярного скотча под сумкой.
## Управление: стрелки / WASD / крестовина — курсор; E / Enter / ЛКМ — взять и положить; R / ПКМ — повернуть;
## F — использовать (лечение, выбор предмета для броска); X — выбросить; I / Esc — закрыть.
## На геймпаде: A — взять/положить, X — повернуть, Y — использовать, нажатие левого стика — выбросить.
class_name InventoryUI
extends Control

const CELL := 60.0
const BAG := Rect2(347, 51, 586, 435)            ## сумка на экране 1280×720
const ORIGIN := Vector2(400, 117)                ## левый верхний угол сетки (8×5 клеток по CELL)
const TAPE := Rect2(288, 492, 704, 132)
const KEYS_TIMES := 3                            ## сколько первых открытий показывать подсказку по клавишам
const C_FABRIC := Color(0.10, 0.115, 0.10)
const C_STITCH := Color(0.26, 0.29, 0.25)
const C_ACCENT := Color(1.0, 0.62, 0.25)
const C_THROW := Color(0.78, 0.2, 0.16)
const C_INK := Color(0.16, 0.14, 0.10)

var hud: HUD
var cursor := Vector2i.ZERO
var held := {}                                   ## предмет «в руке» (на время переноса убран из сетки)

var _held_from := {}
var _icons := {}
var _tape: Control
var _name: Label
var _desc: Label
var _note: Label
var _keys: Label
var _specks := PackedVector2Array()
var _slide_tw: Tween


func _ready() -> void:
	position = Vector2.ZERO
	size = Vector2(HUD.W, HUD.H)
	visible = false
	mouse_filter = Control.MOUSE_FILTER_STOP
	var rng := RandomNumberGenerator.new()
	rng.seed = 1977
	for i in 160:
		_specks.append(Vector2(rng.randf_range(BAG.position.x + 24, BAG.end.x - 24), rng.randf_range(BAG.position.y + 42, BAG.end.y - 24)))
	_tape = Control.new()
	_tape.position = TAPE.position
	_tape.size = TAPE.size
	_tape.pivot_offset = TAPE.size / 2.0
	_tape.rotation = deg_to_rad(-1.3)
	_tape.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_tape.draw.connect(_draw_tape)
	add_child(_tape)
	_name = _ink(_tape, 30, C_INK, Rect2(21, 6, TAPE.size.x - 42, 39))
	_desc = _ink(_tape, 18, Color(0.29, 0.26, 0.20), Rect2(21, 45, TAPE.size.x - 42, 81))
	_note = HUD.mk_label(self, "", 18, Color(1, 0.8, 0.4), Rect2(TAPE.position.x, TAPE.end.y + 6, TAPE.size.x, 30), HORIZONTAL_ALIGNMENT_CENTER)
	_keys = HUD.mk_label(self, "E — взять / положить     R — повернуть     F — использовать     X — выбросить     I — закрыть",
		16, Color(0.62, 0.62, 0.6), Rect2(0, 678, HUD.W, 27), HORIZONTAL_ALIGNMENT_CENTER)
	Game.inventory_changed.connect(queue_redraw)


func _draw_tape() -> void:
	_tape.draw_rect(Rect2(Vector2(4.5, 7.5), _tape.size), Color(0, 0, 0, 0.45))
	_tape.draw_rect(Rect2(Vector2.ZERO, _tape.size), Color(0.91, 0.87, 0.73))
	_tape.draw_rect(Rect2(Vector2.ZERO, Vector2(_tape.size.x, 4.5)), Color(1, 1, 1, 0.25))


func _ink(parent: Control, font_size: int, color: Color, r: Rect2) -> Label:
	var l := Label.new()
	var ls := LabelSettings.new()
	ls.font_size = font_size
	ls.font_color = color
	l.label_settings = ls
	l.position = r.position
	l.size = r.size
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l


func open() -> void:
	visible = true
	_note.text = ""
	_keys.visible = Game.hint("bag_keys", KEYS_TIMES)
	_refresh()
	# сумка выезжает снизу, пока взгляд опускается
	position.y = 330.0
	modulate.a = 0.0
	if _slide_tw:
		_slide_tw.kill()
	_slide_tw = create_tween().set_parallel().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_slide_tw.set_pause_mode(Tween.TWEEN_PAUSE_PROCESS)
	_slide_tw.tween_property(self, "position:y", 0.0, 0.35)
	_slide_tw.tween_property(self, "modulate:a", 1.0, 0.2)


func close() -> void:
	if not held.is_empty():                       # не успел положить — возвращаем на место
		held["pos"] = _held_from["pos"]
		held["rot"] = _held_from["rot"]
		Game.inventory.append(held)
		held = {}
		Game.inventory_changed.emit()
	if _slide_tw:
		_slide_tw.kill()
	visible = false


func _icon(id: String) -> Texture2D:
	if not _icons.has(id):
		_icons[id] = load("res://assets/ui/icons/%s.png" % id)
	return _icons[id]


func _entry_at(cell: Vector2i) -> Dictionary:
	for e: Dictionary in Game.inventory:
		if Rect2i(e["pos"], Game.entry_size(e)).has_point(cell):
			return e
	return {}


func _input(event: InputEvent) -> void:
	if not visible:
		return
	var used := true
	if event is InputEventMouseMotion:
		var c := Vector2i(((event.position - global_position - ORIGIN) / CELL).floor())
		if c.x >= 0 and c.y >= 0 and c.x < Game.GRID.x and c.y < Game.GRID.y and c != cursor:
			cursor = c
			_refresh()
		used = false
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_LEFT:
			_accept()
		elif event.button_index == MOUSE_BUTTON_RIGHT:
			_rotate()
	elif _dir(event, "left"):
		_move(Vector2i(-1, 0))
	elif _dir(event, "right"):
		_move(Vector2i(1, 0))
	elif _dir(event, "up"):
		_move(Vector2i(0, -1))
	elif _dir(event, "down"):
		_move(Vector2i(0, 1))
	elif event.is_action_pressed("interact") or event.is_action_pressed("ui_accept"):
		_accept()
	elif event.is_action_pressed("inv_rotate"):
		_rotate()
	elif event.is_action_pressed("inv_use"):
		_use()
	elif event.is_action_pressed("inv_drop"):
		_drop()
	else:
		used = false
	if used:
		get_viewport().set_input_as_handled()


func _dir(event: InputEvent, d: String) -> bool:
	if event.is_action_pressed("ui_" + d, true):
		return true
	var m: String = {"left": "move_left", "right": "move_right", "up": "move_forward", "down": "move_back"}[d]
	return event is InputEventKey and event.is_action_pressed(m, true)


func _move(d: Vector2i) -> void:
	cursor = Vector2i(clampi(cursor.x + d.x, 0, Game.GRID.x - 1), clampi(cursor.y + d.y, 0, Game.GRID.y - 1))
	Game.sfx("ui_move", null, -8.0)
	_refresh()


func _accept() -> void:
	if held.is_empty():
		var e := _entry_at(cursor)
		if e.is_empty():
			return
		_held_from = {"pos": e["pos"], "rot": e["rot"]}
		held = e
		for i in Game.inventory.size():
			if is_same(Game.inventory[i], e):
				Game.inventory.remove_at(i)
				break
		cursor = e["pos"]
		Game.sfx("ui_select", null, -6.0)
	elif Game.fits(Game.entry_size(held), cursor):
		held["pos"] = cursor
		Game.inventory.append(held)
		held = {}
		Game.sfx("pickup", null, -6.0)
		Game.inventory_changed.emit()
	else:
		Game.sfx("ui_error", null, -6.0)
	_refresh()


func _rotate() -> void:
	if not held.is_empty():
		held["rot"] = not held["rot"]
	else:
		var e := _entry_at(cursor)
		if e.is_empty():
			return
		e["rot"] = not e["rot"]
		if not Game.fits(Game.entry_size(e), e["pos"], e):
			e["rot"] = not e["rot"]
			Game.sfx("ui_error", null, -6.0)
			_note.text = "Нет места, чтобы повернуть. Возьми предмет (E) и поверни в руке."
			return
	Game.sfx("ui_move", null, -6.0)
	_refresh()


func _use() -> void:
	var e := _entry_at(cursor)
	if e.is_empty() or not held.is_empty():
		return
	_note.text = Game.use_entry(e)
	_refresh()


func _drop() -> void:
	var e := held if not held.is_empty() else _entry_at(cursor)
	if e.is_empty():
		return
	var d: Dictionary = Game.ITEMS[e["id"]]
	if d.has("fixed") or d.has("key"):
		_note.text = "Это выбрасывать нельзя."
		Game.sfx("ui_error", null, -6.0)
		return
	if held.is_empty():
		Game.remove_entry(e)
	held = {}
	var pl := hud.player
	if pl:
		var p := Pickup.new()
		p.item_id = e["id"]
		pl.get_parent().add_child(p)
		p.global_position = pl.global_position + pl.global_basis * Vector3(0.0, 0.03, -0.7)
	Game.sfx("pickup", null, -6.0, 0.2)
	Game.inventory_changed.emit()
	_refresh()


func _refresh() -> void:
	var e := held if not held.is_empty() else _entry_at(cursor)
	if e.is_empty():
		_name.text = ""
		_desc.text = ""
	else:
		var d: Dictionary = Game.ITEMS[e["id"]]
		_name.text = d["name"]
		_desc.text = d["desc"]
	queue_redraw()


func _cell_rect(pos: Vector2i, cells: Vector2i) -> Rect2:
	return Rect2(ORIGIN + Vector2(pos) * CELL, Vector2(cells) * CELL)


## Небольшой наклон, чтобы вещи лежали «как бросили», а не по линейке. Свой у каждой клетки, не прыгает.
func _tilt(e: Dictionary) -> float:
	var p: Vector2i = e["pos"]
	return deg_to_rad(float((p.x * 7 + p.y * 13 + String(e["id"]).length()) % 5 - 2) * 1.2)


func _draw_item(e: Dictionary, pos: Vector2i, alpha: float, lifted := false) -> void:
	var r := _cell_rect(pos, Game.entry_size(e))
	var tex := _icon(e["id"])
	if tex == null:
		return
	var base: Vector2i = Game.ITEMS[e["id"]]["size"]
	var sz := Vector2(base) * CELL - Vector2(9, 9)
	var ang := (PI / 2.0 if e["rot"] else 0.0) + (0.0 if lifted else _tilt(e))
	var shadow := Vector2(9, 13.5) if lifted else Vector2(4.5, 6)
	draw_set_transform(r.get_center() + shadow, ang, Vector2.ONE)
	draw_texture_rect(tex, Rect2(-sz / 2.0, sz), false, Color(0, 0, 0, 0.55 * alpha))
	draw_set_transform(r.get_center() - (Vector2(0, 6) if lifted else Vector2.ZERO), ang, Vector2.ONE)
	draw_texture_rect(tex, Rect2(-sz / 2.0, sz), false, Color(1.6, 1.6, 1.55, alpha))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	if Game.throw_item == e["id"] and Game.ITEMS[e["id"]].has("throw"):   # красная нитка: выбран для броска
		var dot := r.position + Vector2(r.size.x - 10.5, 10.5)
		draw_circle(dot, 7.5, Color(0, 0, 0, 0.6 * alpha))
		draw_circle(dot, 5.25, Color(C_THROW, alpha))


func _draw() -> void:
	draw_rect(Rect2(Vector2(0, -position.y), size + Vector2(0, 360)), Color(0, 0, 0, 0.5))
	# сумка: тёмная ткань, молния сверху, строчка по краю
	var bag := StyleBoxFlat.new()
	bag.bg_color = C_FABRIC
	bag.set_corner_radius_all(33)
	bag.corner_radius_bottom_left = 45
	bag.corner_radius_bottom_right = 45
	bag.border_color = Color(0.03, 0.035, 0.03)
	bag.set_border_width_all(6)
	bag.shadow_color = Color(0, 0, 0, 0.6)
	bag.shadow_size = 27
	bag.shadow_offset = Vector2(0, 15)
	draw_style_box(bag, BAG)
	for p: Vector2 in _specks:
		draw_rect(Rect2(p, Vector2(3, 3)), Color(0, 0, 0, 0.18))
	var z := Rect2(BAG.position.x + 33, BAG.position.y + 15, BAG.size.x - 66, 15)
	draw_rect(z, Color(0.05, 0.05, 0.05))
	var x := z.position.x + 3.0
	while x < z.end.x - 4.5:
		draw_rect(Rect2(x, z.position.y + 3, 4.5, 9), Color(0.55, 0.57, 0.6))
		x += 9.0
	draw_rect(Rect2(z.end.x - 33, z.position.y - 4.5, 21, 24), Color(0.62, 0.64, 0.66))   # бегунок молнии
	var st := Rect2(BAG.position.x + 21, BAG.position.y + 45, BAG.size.x - 42, BAG.size.y - 66)
	var corners := [st.position, Vector2(st.end.x, st.position.y), st.end, Vector2(st.position.x, st.end.y)]
	for i in 4:
		draw_dashed_line(corners[i], corners[(i + 1) % 4], C_STITCH, 3.0, 10.5)
	# сетка еле видна и проступает швами, когда несёшь предмет
	var grid_a := 0.16 if not held.is_empty() else 0.045
	for gx in Game.GRID.x + 1:
		var px := ORIGIN.x + gx * CELL
		draw_line(Vector2(px, ORIGIN.y), Vector2(px, ORIGIN.y + Game.GRID.y * CELL), Color(1, 1, 1, grid_a))
	for gy in Game.GRID.y + 1:
		var py := ORIGIN.y + gy * CELL
		draw_line(Vector2(ORIGIN.x, py), Vector2(ORIGIN.x + Game.GRID.x * CELL, py), Color(1, 1, 1, grid_a))
	for e: Dictionary in Game.inventory:
		_draw_item(e, e["pos"], 1.0)
	if not held.is_empty():
		var cells := Game.entry_size(held)
		var ok := Game.fits(cells, cursor)
		draw_rect(_cell_rect(cursor, cells), Color(0.2, 0.9, 0.3, 0.2) if ok else Color(0.9, 0.2, 0.15, 0.25))
		draw_rect(_cell_rect(cursor, cells), Color(0.4, 1.0, 0.5) if ok else Color(1.0, 0.35, 0.3), false, 3.0)
		_draw_item(held, cursor, 0.95, true)
	else:
		var e2 := _entry_at(cursor)
		var r2 := _cell_rect(cursor, Vector2i.ONE) if e2.is_empty() else _cell_rect(e2["pos"], Game.entry_size(e2))
		draw_rect(r2.grow(1.5), C_ACCENT, false, 3.0)
