## Pac-Man: ешь точки в лабиринте и убегай от привидений. Съел энерджайзер — привидения на время
## синеют и боятся, их можно съесть. Собрал всё — следующий уровень, привидения быстрее.
class_name PhonePacman
extends PhoneGame

const T := 10                                    ## клетка, пикселей
## Левая половина лабиринта; правая — зеркальная. # стена, . крошка, o большая крошка, - дверь домика, G домик.
const HALF := [
	"################",
	"#..............#",
	"#.####.#######.#",
	"#o####.#######.#",
	"#...............",
	"#.####.##.######",
	"#......##.......",
	"######.#####.##-",
	"######.#####.#GG",
	"######.#####.###",
	"#...............",
	"#.####.#######.#",
	"#o..##..........",
	"###.##.##.######",
	"#......##.......",
	"#...............",
	"################",
]
const START := Vector2i(15, 10)
const DOOR := Vector2i(15, 6)                    ## клетка у двери домика: сюда выходят привидения
const HOME := [Vector2i(14, 8), Vector2i(15, 8), Vector2i(16, 8), Vector2i(17, 8)]
## Цвета привидений: красное гонится, розовое заходит наперерез, голубое и оранжевое бродят.
const GHOSTS := [Color("ff2a2a"), Color("ffb0e0"), Color("40e8f0"), Color("ffb040")]
const DIRS := [Vector2i.UP, Vector2i.LEFT, Vector2i.DOWN, Vector2i.RIGHT]

var grid: Array[String] = []
var dots := {}                                   ## клетка → 1 крошка / 2 большая
var me := {}
var foes: Array[Dictionary] = []
var level := 1
var scared_t := 0.0
var _pause_t := 0.0                              ## заминка после поимки и в начале уровня
var _banner := ""
var _o := Vector2.ZERO
var _time := 0.0


func title() -> String:
	return "Pac-Man"


func status() -> String:
	return "Pac-Man  ж%d  ур.%d  %d" % [lives, level, score]


func start() -> void:
	grid.clear()
	for r: String in HALF:
		grid.append(r + r.reverse())
	_o = area.position + (area.size - Vector2(grid[0].length() * T, grid.size() * T)) / 2.0
	lives = 3
	score = 0
	level = 1
	over = false
	_fill_dots()
	_reset_actors()


func _fill_dots() -> void:
	dots.clear()
	for y in grid.size():
		for x in grid[y].length():
			match grid[y][x]:
				".": dots[Vector2i(x, y)] = 1
				"o": dots[Vector2i(x, y)] = 2
	dots.erase(START)


func _reset_actors() -> void:
	me = {"cell": START, "dir": Vector2i.ZERO, "prog": 0.0, "want": Vector2i.ZERO}
	foes.clear()
	for i in HOME.size():
		foes.append({"cell": HOME[i], "dir": Vector2i.ZERO, "prog": 0.0, "wait": 1.0 + i * 3.0, "id": i})
	scared_t = 0.0
	_pause_t = 1.2
	_banner = "Уровень %d" % level


func _walk(c: Vector2i) -> bool:
	if c.y < 0 or c.y >= grid.size() or c.x < 0 or c.x >= grid[0].length():
		return false
	return grid[c.y][c.x] in [".", "o", " "]


# ----------------------------------------------------------------------------- управление
func dir(d: Vector2i) -> void:
	if over or d == Vector2i.ZERO:
		return
	me["want"] = d
	var cur: Vector2i = me["dir"]
	if cur != Vector2i.ZERO and d == -cur:             # развернуться можно на полпути
		me["cell"] = me["cell"] + cur
		me["dir"] = d
		me["prog"] = 1.0 - me["prog"]


func step(delta: float) -> void:
	if over:
		return
	_time += delta
	var h := held()
	if h != Vector2i.ZERO:
		dir(h)
	if _pause_t > 0.0:
		_pause_t -= delta
		if _pause_t <= 0.0:
			_banner = ""
		return
	scared_t = maxf(scared_t - delta, 0.0)
	_advance(me, 6.0 + level * 0.3, delta, false)
	for f: Dictionary in foes:
		if f["wait"] > 0.0:
			f["wait"] -= delta
			if f["wait"] <= 0.0:
				f["cell"] = DOOR
				f["dir"] = Vector2i.LEFT if f["id"] % 2 == 0 else Vector2i.RIGHT
				f["prog"] = 0.0
			continue
		_advance(f, (2.8 if scared_t > 0.0 else 4.6 + level * 0.4), delta, true)
	_collide()


func _advance(e: Dictionary, speed: float, delta: float, foe: bool) -> void:
	if e["dir"] == Vector2i.ZERO:
		if foe:
			_choose(e)
		elif e["want"] != Vector2i.ZERO and _walk(e["cell"] + e["want"]):
			e["dir"] = e["want"]
		if e["dir"] == Vector2i.ZERO:
			return
	e["prog"] += speed * delta
	while e["prog"] >= 1.0:
		e["prog"] -= 1.0
		e["cell"] = e["cell"] + e["dir"]
		if foe:
			_choose(e)
		else:
			_arrive()
		if e["dir"] == Vector2i.ZERO:
			e["prog"] = 0.0
			break


func _arrive() -> void:
	var c: Vector2i = me["cell"]
	if dots.has(c):
		if dots[c] == 2:
			score += 50
			scared_t = maxf(6.5 - level * 0.5, 2.5)
			blip(-16.0)
		else:
			score += 10
			if dots.size() % 3 == 0:
				blip(-26.0)
		dots.erase(c)
		if dots.is_empty():
			level += 1
			score += 300
			_fill_dots()
			_reset_actors()
			return
	var want: Vector2i = me["want"]
	if want != Vector2i.ZERO and _walk(c + want):
		me["dir"] = want
	elif not _walk(c + (me["dir"] as Vector2i)):
		me["dir"] = Vector2i.ZERO


## Привидение на перекрёстке: не разворачивается, идёт туда, откуда ближе к цели; испуганный — наугад.
func _choose(f: Dictionary) -> void:
	var c: Vector2i = f["cell"]
	var back: Vector2i = -(f["dir"] as Vector2i)
	var opts: Array[Vector2i] = []
	for d: Vector2i in DIRS:
		if d != back and _walk(c + d):
			opts.append(d)
	if opts.is_empty():
		f["dir"] = back if _walk(c + back) else Vector2i.ZERO
		return
	if scared_t > 0.0 or randf() < 0.12:
		f["dir"] = opts.pick_random()
		return
	var target: Vector2i = me["cell"]
	match f["id"]:
		1: target += (me["dir"] as Vector2i) * 4          # заходит наперерез
		2, 3:                                             # вблизи отваливает в свой угол
			if Vector2(c).distance_to(Vector2(target)) < 7.0:
				target = Vector2i(1 if f["id"] == 2 else grid[0].length() - 2, grid.size() - 2)
	var best_d: Vector2i = opts[0]
	var best_len := INF
	for d: Vector2i in opts:
		var l := Vector2(c + d).distance_squared_to(Vector2(target))
		if l < best_len:
			best_len = l
			best_d = d
	f["dir"] = best_d


func _pos(e: Dictionary) -> Vector2:
	return Vector2(e["cell"]) + Vector2(e["dir"] as Vector2i) * float(e["prog"])


func _collide() -> void:
	var p := _pos(me)
	for f: Dictionary in foes:
		if f["wait"] > 0.0 or _pos(f).distance_to(p) > 0.7:
			continue
		if scared_t > 0.0:
			score += 200
			blip(-14.0)
			f["cell"] = HOME[f["id"]]
			f["dir"] = Vector2i.ZERO
			f["wait"] = 3.0
			continue
		lives -= 1
		Game.sfx("phone_vibrate", null, -18.0, 0.0)
		if lives <= 0:
			finish()
		else:
			_reset_actors()
			_banner = "Поймали!"
		return


# ----------------------------------------------------------------------------- отрисовка
func draw(ci: CanvasItem) -> void:
	ci.draw_rect(area, Color("05080c"))
	for y in grid.size():
		for x in grid[y].length():
			var ch := grid[y][x]
			var r := Rect2(_o + Vector2(x * T, y * T), Vector2(T, T))
			if ch == "#":                              # сплошная стена, контур — только там, где рядом проход
				ci.draw_rect(r, Color("0c2436"))
				var edge := Color("3d8fc4")
				if not _wall(x, y - 1): ci.draw_line(r.position, r.position + Vector2(T, 0), edge, 1.0)
				if not _wall(x, y + 1): ci.draw_line(r.end - Vector2(T, 0.5), r.end - Vector2(0, 0.5), edge, 1.0)
				if not _wall(x - 1, y): ci.draw_line(r.position, r.position + Vector2(0, T), edge, 1.0)
				if not _wall(x + 1, y): ci.draw_line(r.end - Vector2(0.5, T), r.end - Vector2(0.5, 0), edge, 1.0)
			elif ch == "-":
				ci.draw_rect(Rect2(r.position + Vector2(0, 4), Vector2(T, 2)), Color("c98a9a"))
	var blink := int(_time * 4.0) % 2 == 0
	for c: Vector2i in dots:
		var cp := _o + Vector2(c * T) + Vector2(T, T) / 2.0
		if dots[c] == 2:
			if blink:
				ci.draw_circle(cp, 3.5, Color("f2dcb0"))
		else:
			ci.draw_rect(Rect2(cp - Vector2(1, 1), Vector2(2, 2)), Color("f2dcb0"))
	for f: Dictionary in foes:
		_draw_foe(ci, f)
	_draw_me(ci)
	if _banner != "" and not over:
		banner(ci, _banner)
	if over:
		draw_over(ci)


func _wall(x: int, y: int) -> bool:
	return y < 0 or y >= grid.size() or x < 0 or x >= grid[0].length() or grid[y][x] == "#"


func _draw_me(ci: CanvasItem) -> void:
	var d: Vector2i = me["dir"] if me["dir"] != Vector2i.ZERO else me["want"]
	if d == Vector2i.ZERO:
		d = Vector2i.RIGHT
	var c := _o + (_pos(me) + Vector2(0.5, 0.5)) * T
	var moving: bool = me["dir"] != Vector2i.ZERO
	var open := absf(sin(_time * 18.0)) if moving else 0.5   # рот хлопает на ходу
	var a0 := Vector2(d).angle()
	var half := open * 0.8
	var pts := PackedVector2Array([c])
	for i in 17:
		pts.append(c + Vector2.from_angle(a0 + half + (TAU - 2.0 * half) * i / 16.0) * 4.8)
	ci.draw_colored_polygon(pts, Color("ffe135"))


## Привидение: купол с бахромой и глаза, смотрящие по ходу; испуганное — синее, под конец мигает.
func _draw_foe(ci: CanvasItem, f: Dictionary) -> void:
	var c := _o + (_pos(f) + Vector2(0.5, 0.5)) * T
	if f["wait"] > 0.0:
		c.y += sin(_time * 5.0 + f["id"]) * 1.0           # покачивается в домике
	var body: Color = GHOSTS[f["id"]]
	var scared: bool = scared_t > 0.0 and f["wait"] <= 0.0
	if scared:
		body = Color("2121de") if scared_t > 1.5 or int(_time * 6.0) % 2 == 0 else Color("f0f0f0")
	var r := 4.6
	var pts := PackedVector2Array()
	for i in 9:                                        # купол
		pts.append(c + Vector2.from_angle(PI + PI * i / 8.0) * r + Vector2(0, -0.5))
	var wave := int(_time * 8.0) % 2
	for i in 7:                                        # бахрома снизу
		var x := r - i * (2.0 * r / 6.0)
		pts.append(c + Vector2(x, 4.5 - (1.5 if (i + wave) % 2 == 1 else 0.0)))
	ci.draw_colored_polygon(pts, body)
	if scared:
		ci.draw_rect(Rect2(c + Vector2(-2.2, -1.5), Vector2(1.3, 1.3)), Color("ffd0a0"))
		ci.draw_rect(Rect2(c + Vector2(1.0, -1.5), Vector2(1.3, 1.3)), Color("ffd0a0"))
		return
	var look := Vector2(f["dir"] as Vector2i) * 0.8
	for ex: float in [-1.8, 1.8]:
		ci.draw_circle(c + Vector2(ex, -1.2), 1.5, Color.WHITE)
		ci.draw_circle(c + Vector2(ex, -1.2) + look, 0.8, Color("2121de"))
