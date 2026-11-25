## StyleBox в духе Windows 7: скруглённая плашка с вертикальным глянцевым градиентом и двойной рамкой.
class_name W7Box
extends StyleBox

var stops: Array = []
var border := Color.TRANSPARENT
var inner := Color.TRANSPARENT
var radius := 3.0
var dotted := false        ## рамка фокуса — пунктир внутри кнопки


static func make(p_stops: Array, p_border: String, p_radius := 3.0, p_inner := "00000000", margin := 6.0, p_dotted := false) -> W7Box:
	var b := W7Box.new()
	b.stops = p_stops
	b.border = Color(p_border)
	b.inner = Color(p_inner)
	b.radius = p_radius
	b.dotted = p_dotted
	b.content_margin_left = margin
	b.content_margin_right = margin
	b.content_margin_top = 2
	b.content_margin_bottom = 2
	return b


func _draw(ci: RID, rect: Rect2) -> void:
	if dotted:
		var r := rect.grow(-3)
		var pts := [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y), r.position]
		for i in 4:
			var a: Vector2 = pts[i]
			var b: Vector2 = pts[i + 1]
			var n := int(a.distance_to(b) / 2.0)
			for k in n:
				if k % 2 == 0:
					var p := a.lerp(b, float(k) / n)
					RenderingServer.canvas_item_add_rect(ci, Rect2(p, Vector2.ONE), Color(0, 0, 0, 0.6))
		return
	W7.fill(ci, rect, radius, stops)
	if inner.a > 0.0:
		W7.stroke(ci, rect.grow(-1), maxf(radius - 1.0, 0.0), inner)
	W7.stroke(ci, rect, radius, border)
