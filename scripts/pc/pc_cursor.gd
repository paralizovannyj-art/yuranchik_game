## Курсор мыши на экране компа Юрчика: белая стрелка Windows с чёрной обводкой.
## Рисуется поверх рабочего стола внутри SubViewport (pc_seat.gd двигает его за мышью).
class_name PcCursor
extends Control

## контур стрелки в пикселях экрана компа (остриё — в 0,0)
const ARROW := [Vector2(0, 0), Vector2(0, 17), Vector2(4, 13), Vector2(7, 20), Vector2(9.5, 19),
		Vector2(6.5, 12.2), Vector2(12, 12.2)]
@export var scale_px := 1.6


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	z_index = 100
	top_level = true


func _draw() -> void:
	var pts := PackedVector2Array()
	for p: Vector2 in ARROW:
		pts.append(p * scale_px)
	draw_colored_polygon(pts, Color.WHITE)
	pts.append(pts[0])
	draw_polyline(pts, Color.BLACK, 1.2, true)
