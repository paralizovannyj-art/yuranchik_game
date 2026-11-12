## Инвентарь-сетка в духе RE4: предметы занимают клетки, их можно перекладывать и поворачивать.
## Управление: стрелки / WASD / крестовина — курсор; E / Enter / ЛКМ — взять и положить; R / ПКМ — повернуть;
## F — использовать (лечение, выбор предмета для броска); X — выбросить; Tab / Esc — закрыть.
## На геймпаде: A — взять/положить, X — повернуть, Y — использовать, нажатие левого стика — выбросить.
class_name InventoryUI
extends Control

const CELL := 40.0
const ORIGIN := Vector2(24, 52)                  ## левый верхний угол сетки внутри панели
const PANEL := Rect2(127, 82, 600, 300)

var hud: HUD
var cursor := Vector2i.ZERO
var held := {}                                   ## предмет «в руке» (на время переноса убран из сетки)

var _held_from := {}
var _icons := {}
var _name: Label
var _desc: Label
var _note: Label


func _ready() -> void:
	position = PANEL.position
	size = PANEL.size
	visible = false
	mouse_filter = Control.MOUSE_FILTER_STOP
	HUD.mk_label(self, "ИНВЕНТАРЬ", 12, HUD.C_ACCENT, Rect2(24, 14, 300, 18))
	_name = HUD.mk_label(self, "", 15, Color.WHITE, Rect2(372, 50, 210, 22))
	_desc = HUD.mk_label(self, "", 11, HUD.C_TEXT, Rect2(372, 76, 210, 110))
	_note = HUD.mk_label(self, "", 11, Color(1, 0.8, 0.4), Rect2(372, 190, 210, 60))
	HUD.mk_label(self, "E — взять / положить     R — повернуть     F — использовать     X — выбросить     Tab — закрыть",
		10, Color(0.6, 0.6, 0.58), Rect2(24, 266, 560, 30))
	Game.inventory_changed.connect(queue_redraw)


func open() -> void:
	visible = true
	_note.text = ""
	_refresh()


func close() -> void:
	if not held.is_empty():                       # не успел положить — возвращаем на место
		held["pos"] = _held_from["pos"]
		held["rot"] = _held_from["rot"]
		Game.inventory.append(held)
		held = {}
		Game.inventory_changed.emit()
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


func _draw_item(e: Dictionary, pos: Vector2i, alpha: float) -> void:
	var cells := Game.entry_size(e)
	var r := _cell_rect(pos, cells).grow(-2.0)
	draw_rect(r, Color(0.16, 0.17, 0.19, 0.9 * alpha))
	if Game.throw_item == e["id"] and Game.ITEMS[e["id"]].has("throw"):
		draw_rect(r, Color(1.0, 0.62, 0.25, 0.5 * alpha), false, 1.0)
	var tex := _icon(e["id"])
	if tex == null:
		return
	var base: Vector2i = Game.ITEMS[e["id"]]["size"]
	var sz := Vector2(base) * CELL - Vector2(8, 8)
	var mod := Color(1.7, 1.7, 1.7, alpha)
	if e["rot"]:
		draw_set_transform(r.get_center(), PI / 2.0, Vector2.ONE)
		draw_texture_rect(tex, Rect2(-sz / 2.0, sz), false, mod)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	else:
		draw_texture_rect(tex, Rect2(r.get_center() - sz / 2.0, sz), false, mod)


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.03, 0.035, 0.04, 0.93))
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.28, 0.28, 0.30), false, 1.0)
	for y in Game.GRID.y:
		for x in Game.GRID.x:
			var r := _cell_rect(Vector2i(x, y), Vector2i.ONE)
			draw_rect(r.grow(-1.0), Color(0.08, 0.085, 0.095))
			draw_rect(r, Color(0.20, 0.21, 0.23), false, 1.0)
	for e: Dictionary in Game.inventory:
		_draw_item(e, e["pos"], 1.0)
	if not held.is_empty():
		var cells := Game.entry_size(held)
		var ok := Game.fits(cells, cursor)
		draw_rect(_cell_rect(cursor, cells), Color(0.2, 0.9, 0.3, 0.25) if ok else Color(0.9, 0.2, 0.15, 0.3))
		_draw_item(held, cursor, 0.85)
		draw_rect(_cell_rect(cursor, cells), Color(0.4, 1.0, 0.5) if ok else Color(1.0, 0.35, 0.3), false, 2.0)
	else:
		var e2 := _entry_at(cursor)
		var r2 := _cell_rect(cursor, Vector2i.ONE) if e2.is_empty() else _cell_rect(e2["pos"], Game.entry_size(e2))
		draw_rect(r2, Color(1.0, 0.62, 0.25), false, 2.0)
