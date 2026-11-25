## Курсор мыши на экране компа Юрчика, как в Windows 7: белая стрелка с чёрной обводкой,
## над текстом — «I-образный» курсор, когда программа запускается — стрелка с крутящимся кольцом.
## Рисуется поверх рабочего стола внутри SubViewport (pc_seat.gd двигает его за мышью).
class_name PcCursor
extends Control

## контур стрелки в пикселях (остриё — в 0,0)
const ARROW := [Vector2(0, 0), Vector2(0, 17), Vector2(4, 13), Vector2(7, 20), Vector2(9.5, 19),
		Vector2(6.5, 12.2), Vector2(12, 12.2)]
@export var scale_px := 1.2

var busy := false
var _ibeam := false
var _spin := 0.0
var _was_busy := false


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	z_index = 100
	top_level = true


func _process(delta: float) -> void:
	var ib := false
	var vp := get_viewport()
	if vp and vp.has_method("gui_get_hovered_control"):
		var c: Control = vp.call("gui_get_hovered_control")
		if c and c.is_visible_in_tree():
			ib = c.get_cursor_shape(c.get_local_mouse_position()) == Control.CURSOR_IBEAM
	if busy:
		_spin += delta * 6.0
	if ib != _ibeam or busy or busy != _was_busy:
		_ibeam = ib
		_was_busy = busy
		queue_redraw()


func _draw() -> void:
	if _ibeam and not busy:
		var s := scale_px
		for w: Array in [[3.0, Color.BLACK], [1.2, Color.WHITE]]:
			draw_line(Vector2(0, -8) * s, Vector2(0, 8) * s, w[1], w[0])
			draw_line(Vector2(-3, -8) * s, Vector2(3, -8) * s, w[1], w[0])
			draw_line(Vector2(-3, 8) * s, Vector2(3, 8) * s, w[1], w[0])
		return
	var pts := PackedVector2Array()
	for p: Vector2 in ARROW:
		pts.append(p * scale_px)
	draw_colored_polygon(pts, Color.WHITE)
	pts.append(pts[0])
	draw_polyline(pts, Color.BLACK, 1.0, true)
	if busy:
		var c := Vector2(17, 20) * scale_px
		draw_arc(c, 6.0 * scale_px, 0, TAU, 20, Color(0.3, 0.6, 0.9, 0.45), 3.0 * scale_px, true)
		for k in 6:
			var f := float(k) / 6.0
			draw_arc(c, 6.0 * scale_px, _spin - f * 1.4, _spin - f * 1.4 - 0.25, 3, Color(0.55, 0.9, 1.0, 1.0 - f), 3.0 * scale_px, true)
