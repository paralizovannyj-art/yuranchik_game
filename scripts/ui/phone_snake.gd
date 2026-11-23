## «Змейка»: ешь точки, расти, не кусай себя. Через края поля змейка проходит насквозь.
class_name PhoneSnake
extends PhoneGame

const C := 8                                     ## клетка, пикселей
const BG := Color("9cb84a")
const INK := Color("1d3311")

var cols := 40
var rows := 23
var body: Array[Vector2i] = []
var heading := Vector2i.RIGHT
var turns: Array[Vector2i] = []                  ## нажатые повороты, по одному на шаг
var food := Vector2i.ZERO
var tick := 0.13
var _t := 0.0
var _o := Vector2.ZERO


func title() -> String:
	return "Змейка"


func start() -> void:
	cols = int(area.size.x / C)
	rows = int(area.size.y / C)
	_o = area.position + (area.size - Vector2(cols * C, rows * C)) / 2.0
	@warning_ignore("integer_division")
	var y := rows / 2
	body = [Vector2i(12, y), Vector2i(11, y), Vector2i(10, y), Vector2i(9, y)]
	heading = Vector2i.RIGHT
	turns.clear()
	score = 0
	over = false
	tick = 0.13
	_t = 0.0
	_place_food()


func dir(d: Vector2i) -> void:
	if over or d == Vector2i.ZERO or (d.x != 0 and d.y != 0):
		return
	var last: Vector2i = turns.back() if not turns.is_empty() else heading
	if d == last or d == -last or turns.size() >= 3:
		return
	turns.append(d)


func step(delta: float) -> void:
	if over:
		return
	_t += delta
	while _t >= tick and not over:
		_t -= tick
		_move()


func _move() -> void:
	if not turns.is_empty():
		heading = turns.pop_front()
	var h := body[0] + heading
	h.x = posmod(h.x, cols)
	h.y = posmod(h.y, rows)
	var eat := h == food
	var check := body.size() if eat else body.size() - 1   # хвост уползает — в его клетку можно
	for i in check:
		if body[i] == h:
			finish()
			return
	body.push_front(h)
	if eat:
		score += 7
		tick = maxf(0.06, tick - 0.003)
		blip()
		_place_food()
	else:
		body.pop_back()


func _place_food() -> void:
	var free: Array[Vector2i] = []
	for y in rows:
		for x in cols:
			var c := Vector2i(x, y)
			if not body.has(c):
				free.append(c)
	food = free.pick_random() if not free.is_empty() else Vector2i.ZERO


func draw(ci: CanvasItem) -> void:
	ci.draw_rect(area, BG)
	ci.draw_rect(Rect2(_o - Vector2(1, 1), Vector2(cols * C + 2, rows * C + 2)), INK, false, 1.0)
	var f := _o + Vector2(food * C) + Vector2(C, C) / 2.0
	ci.draw_colored_polygon(PackedVector2Array([f + Vector2(0, -3.5), f + Vector2(3.5, 0), f + Vector2(0, 3.5), f + Vector2(-3.5, 0)]), INK)
	for i in body.size():
		var p := _o + Vector2(body[i] * C)
		ci.draw_rect(Rect2(p + Vector2(0.5, 0.5), Vector2(C - 1, C - 1)), INK)
		if i == 0:                                   # глаз
			var e := p + Vector2(C, C) / 2.0 + Vector2(heading) * 1.5 + Vector2(heading.y, -heading.x) * 1.5
			ci.draw_rect(Rect2(e - Vector2(1, 1), Vector2(2, 2)), BG)
	if over:
		draw_over(ci)
