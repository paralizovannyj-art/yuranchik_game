## Прицел: маленькая круглая точка тёплого «снежного» цвета, как текст интерфейса, с мягкой тёмной обводкой,
## чтобы читалась и на снегу, и в темноте. Когда взгляд на предмете, вокруг точки проявляется тонкое кольцо,
## в замахе кольцо сжимается к точке. Кольцо ведёт недодемпфированная пружина — появляется с лёгким «щелчком».
class_name Crosshair
extends Control

const DOT_R := 1.3             ## радиус точки, px (экран 854×480)
const RING_FOCUS := 6.0        ## радиус кольца, когда смотришь на предмет
const RING_AIM := 3.5          ## то же в замахе
const SPRING := 320.0          ## жёсткость пружины кольца
const BOUNCE := 0.5            ## < 1 — кольцо чуть перелетает и встаёт на место
const C_FILL := Color(0.90, 0.88, 0.82)                  ## тот же тёплый белый, что и текст HUD
const C_EDGE := Color(0.03, 0.03, 0.04, 0.45)

var alpha := 0.0               ## общая видимость (бег, меню)

var _ring := 0.0               ## 0 — кольца нет, 1 — кольцо проявилось
var _ring_vel := 0.0
var _radius := RING_FOCUS


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


## focus — смотрим на предмет, aim — замах.
func step(delta: float, focus: bool, aim: bool) -> void:
	var goal := 1.0 if focus or aim else 0.0
	_ring_vel += ((goal - _ring) * SPRING - _ring_vel * 2.0 * sqrt(SPRING) * BOUNCE) * delta
	_ring = clampf(_ring + _ring_vel * delta, 0.0, 1.3)
	_radius = move_toward(_radius, RING_AIM if aim else RING_FOCUS, delta * 30.0)
	visible = alpha > 0.01
	queue_redraw()


func _draw() -> void:
	var c := (size / 2.0).floor() + Vector2(0.5, 0.5)
	draw_circle(c, DOT_R + 1.0, Color(C_EDGE, C_EDGE.a * alpha), true, -1.0, true)
	draw_circle(c, DOT_R, Color(C_FILL, 0.95 * alpha), true, -1.0, true)
	var k := clampf(_ring, 0.0, 1.0)
	if k < 0.03:
		return
	var r := _radius * (0.6 + 0.4 * _ring)          # кольцо раскрывается от точки
	draw_arc(c, r, 0.0, TAU, 40, Color(C_EDGE, C_EDGE.a * alpha * k), 3.0, true)
	draw_arc(c, r, 0.0, TAU, 40, Color(C_FILL, 0.85 * alpha * k), 1.0, true)
