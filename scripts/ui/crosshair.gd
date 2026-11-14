## Прицел в духе PS2: непрозрачная белая точка с тёмной обводкой. Когда взгляд на предмете, вокруг неё
## выезжают четыре уголка, в замахе уголки прижимаются к точке. Пиксели чёткие, без сглаживания.
class_name Crosshair
extends Control

const DOT := 3.0               ## сторона точки, px (экран 854×480)
const CORNER := 4.0            ## длина плеча уголка
const SPREAD_FOCUS := 9.0      ## расстояние от центра до уголка, когда смотришь на предмет
const SPREAD_AIM := 5.0        ## то же в замахе
const SPRING := 320.0          ## жёсткость пружины уголков
const BOUNCE := 0.5            ## < 1 — уголки чуть перелетают и щёлкают на место
const C_FILL := Color(1, 1, 1)
const C_EDGE := Color(0.05, 0.05, 0.06, 0.85)

var alpha := 0.0               ## общая видимость (бег, меню)

var _corners := 0.0            ## 0 — уголков нет, 1 — уголки выехали
var _corners_vel := 0.0
var _spread := SPREAD_FOCUS


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST


## focus — смотрим на предмет, aim — замах.
func step(delta: float, focus: bool, aim: bool) -> void:
	var goal := 1.0 if focus or aim else 0.0
	_corners_vel += ((goal - _corners) * SPRING - _corners_vel * 2.0 * sqrt(SPRING) * BOUNCE) * delta
	_corners = clampf(_corners + _corners_vel * delta, 0.0, 1.3)
	_spread = move_toward(_spread, SPREAD_AIM if aim else SPREAD_FOCUS, delta * 40.0)
	visible = alpha > 0.01
	queue_redraw()


func _draw() -> void:
	var c := (size / 2.0).floor()
	var parts: Array[Rect2] = [Rect2(c - Vector2(1, 1), Vector2(DOT, DOT))]
	var k := clampf(_corners, 0.0, 1.0)
	if _corners > 0.05:
		var s := roundf(_spread * _corners)
		for sx: float in [-1.0, 1.0]:
			for sy: float in [-1.0, 1.0]:
				var p := c + Vector2(sx * s, sy * s)
				# два плеча уголка от вершины к центру: по горизонтали и по вертикали
				parts.append(Rect2(Vector2(minf(p.x, p.x - sx * (CORNER - 1.0)), p.y), Vector2(CORNER, 1.0)))
				parts.append(Rect2(Vector2(p.x, minf(p.y, p.y - sy * (CORNER - 1.0))), Vector2(1.0, CORNER)))
	# сначала все обводки, потом вся заливка: иначе обводка одного плеча режет соседнее
	for i in parts.size():
		var a := alpha * (1.0 if i == 0 else k)
		draw_rect(parts[i].grow(1.0), Color(C_EDGE, C_EDGE.a * a))
	for i in parts.size():
		draw_rect(parts[i], Color(C_FILL, alpha * (1.0 if i == 0 else k)))
