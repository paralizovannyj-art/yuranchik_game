## Выпадающее меню Windows 7 (контекстное меню, меню «Файл» Блокнота и т. п.).
## items — массив словарей: text, cb (Callable), shortcut, disabled, checked, bold, sub (вложенное меню);
## {"sep": true} — разделитель.
class_name W7Menu
extends Control

const ITEM_H := 22.0
const SEP_H := 7.0
const GUTTER := 28.0

var items: Array = []
var desktop: Control
var parent_menu: W7Menu
var sub_menu: W7Menu
var _hover := -1
var _ys: Array[float] = []
var _sub_timer := 0.0


func setup(p_items: Array, p_desktop: Control) -> W7Menu:
	items = p_items
	desktop = p_desktop
	var w := 150.0
	var y := 3.0
	_ys.clear()
	for it: Dictionary in items:
		_ys.append(y)
		if it.get("sep", false):
			y += SEP_H
			continue
		var tw := W7.text_width(it.get("text", ""), 12, it.get("bold", false)) + GUTTER + 12.0
		if it.has("shortcut"):
			tw += W7.text_width(it["shortcut"]) + 30.0
		if it.has("sub"):
			tw += 20.0
		w = maxf(w, tw + 14.0)
		y += ITEM_H
	size = Vector2(w, y + 3.0)
	mouse_filter = Control.MOUSE_FILTER_STOP
	return self


func _index_at(p: Vector2) -> int:
	if p.x < 0 or p.x > size.x:
		return -1
	for i in items.size():
		var h := SEP_H if items[i].get("sep", false) else ITEM_H
		if p.y >= _ys[i] and p.y < _ys[i] + h:
			return -1 if items[i].get("sep", false) else i
	return -1


func _draw() -> void:
	var ci := get_canvas_item()
	var r := Rect2(Vector2.ZERO, size)
	draw_rect(Rect2(r.position + Vector2(3, 3), r.size), Color(0, 0, 0, 0.12))
	draw_rect(Rect2(r.position + Vector2(2, 2), r.size), Color(0, 0, 0, 0.12))
	draw_rect(r, Color("f0f0f0"))
	draw_line(Vector2(GUTTER, 2), Vector2(GUTTER, size.y - 2), Color("e2e3e3"))
	draw_line(Vector2(GUTTER + 1, 2), Vector2(GUTTER + 1, size.y - 2), Color.WHITE)
	draw_rect(r, Color("979797"), false, 1.0)
	for i in items.size():
		var it: Dictionary = items[i]
		var y := _ys[i]
		if it.get("sep", false):
			draw_line(Vector2(GUTTER + 2, y + 3), Vector2(size.x - 2, y + 3), Color("e0e0e0"))
			draw_line(Vector2(GUTTER + 2, y + 4), Vector2(size.x - 2, y + 4), Color.WHITE)
			continue
		var dis: bool = it.get("disabled", false)
		if i == _hover:
			var hr := Rect2(3, y, size.x - 6, ITEM_H)
			if dis:
				W7.box(ci, hr, 3, [[0.0, Color(1, 1, 1, 0.0)], [1.0, Color(1, 1, 1, 0.0)]], "d0d0d0")
			else:
				W7.box(ci, hr, 3, [[0.0, "f1f6fd"], [1.0, "dde9f8"]], "aeccf2", "ffffffa0")
		var col := Color("6d6d6d") if dis else Color.BLACK
		if it.get("checked", false):
			draw_polyline(PackedVector2Array([Vector2(10, y + 11), Vector2(13, y + 14), Vector2(19, y + 7)]), col, 1.6, true)
		if it.has("icon"):
			var ic := W7.icon(it["icon"], 16)
			if ic:
				draw_texture_rect(ic, Rect2(6, y + 3, 16, 16), false)
		var f := W7.FONT_BOLD if it.get("bold", false) else W7.FONT
		draw_string(f, Vector2(GUTTER + 8, y + 15), it.get("text", ""), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, col)
		if it.has("shortcut"):
			draw_string(W7.FONT, Vector2(size.x - 18 - W7.text_width(it["shortcut"]), y + 15), it["shortcut"],
					HORIZONTAL_ALIGNMENT_LEFT, -1, 12, col)
		if it.has("sub"):
			var ax := size.x - 12
			draw_colored_polygon(PackedVector2Array([Vector2(ax, y + 7), Vector2(ax + 4, y + 11), Vector2(ax, y + 15)]), col)


func _process(delta: float) -> void:
	if _sub_timer > 0.0:
		_sub_timer -= delta
		if _sub_timer <= 0.0:
			_open_sub(_hover)


func _open_sub(i: int) -> void:
	if sub_menu and is_instance_valid(sub_menu):
		if sub_menu.get_meta("index", -1) == i:
			return
		sub_menu.close_tree()
		sub_menu = null
	if i < 0 or not items[i].has("sub") or items[i].get("disabled", false):
		return
	sub_menu = W7Menu.new().setup(items[i]["sub"], desktop)
	sub_menu.parent_menu = self
	sub_menu.set_meta("index", i)
	get_parent().add_child(sub_menu)
	var p := global_position + Vector2(size.x - 4, _ys[i] - 3)
	var area: Vector2 = desktop.size
	if p.x + sub_menu.size.x > area.x:
		p.x = global_position.x - sub_menu.size.x + 4
	p.y = minf(p.y, area.y - sub_menu.size.y)
	sub_menu.position = p


func close_tree() -> void:
	if sub_menu and is_instance_valid(sub_menu):
		sub_menu.close_tree()
	queue_free()


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var i := _index_at(event.position)
		if i != _hover:
			_hover = i
			queue_redraw()
			_sub_timer = 0.3 if i >= 0 and items[i].has("sub") else (0.4 if sub_menu else 0.0)
	elif event is InputEventMouseButton and not event.pressed and event.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT]:
		var i := _index_at(event.position)
		if i < 0:
			return
		var it: Dictionary = items[i]
		if it.get("disabled", false):
			return
		if it.has("sub"):
			_open_sub(i)
			return
		desktop.call("close_menus")
		if it.has("cb"):
			(it["cb"] as Callable).call()
	accept_event()
