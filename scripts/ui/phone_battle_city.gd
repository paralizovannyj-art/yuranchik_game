## Battle City: защищай штаб с орлом внизу поля от вражеских танков. Стрелки — ехать, OK — выстрел.
## Кирпич пробивается по кусочку, бетон — нет. Попали в штаб или кончились жизни — проигрыш.
class_name PhoneBattleCity
extends PhoneGame

const S := 8                                     ## мелкая клетка (четверть плитки), пикселей
const TILE := 16                                 ## плитка карты и размер танка
const COLS := 40
const ROWS := 22
enum { EMPTY, BRICK, STEEL, BASE }
## Карта плитками 20×11: . пусто, # кирпич, @ бетон, B штаб (орёл).
const MAP := [
	"....................",
	".##.##.##..##.##.##.",
	".##.##.##..##.##.##.",
	".##.##.##@@##.##.##.",
	".##.##........##.##.",
	"@@..##..####..##..@@",
	"....##..#..#..##....",
	".##.##.##..##.##.##.",
	".##.##.##..##.##.##.",
	".##......###......##",
	".........#B#........",
]
const PLAYER_START := Vector2(7 * TILE, 10 * TILE)
const SPAWNS := [Vector2(0, 0), Vector2(10 * TILE, 0), Vector2(19 * TILE, 0)]
const C_PLAYER := Color("e8c040")
const C_ENEMY := Color("b8c2cc")
const C_BRICK := Color("b25a32")
const C_STEEL := Color("9ea4ad")

var cells := PackedByteArray()
var tanks: Array[Dictionary] = []
var bullets: Array[Dictionary] = []
var wave := 1
var to_spawn := 0
var _spawn_t := 0.0
var _banner_t := 0.0
var _o := Vector2.ZERO
var _base_dead := false


func title() -> String:
	return "Battle City"


func status() -> String:
	return "Battle City  ж%d  враги %d  %d" % [lives, to_spawn + _enemies(), score]


func start() -> void:
	_o = area.position + Vector2((area.size.x - COLS * S) / 2.0, (area.size.y - ROWS * S) / 2.0)
	lives = 3
	score = 0
	over = false
	wave = 1
	_base_dead = false
	_new_wave()


func _new_wave() -> void:
	cells.resize(COLS * ROWS)
	for ty in MAP.size():
		var row: String = MAP[ty]
		for tx in row.length():
			var v: int = {"#": BRICK, "@": STEEL, "B": BASE}.get(row[tx], EMPTY)
			for dy in 2:
				for dx in 2:
					cells[(ty * 2 + dy) * COLS + tx * 2 + dx] = v
	tanks.clear()
	bullets.clear()
	tanks.append(_tank(PLAYER_START, Vector2i.UP, false))
	to_spawn = 6 + wave * 2
	_spawn_t = 1.0
	_banner_t = 1.6


func _tank(pos: Vector2, d: Vector2i, enemy: bool) -> Dictionary:
	return {"pos": pos, "dir": d, "enemy": enemy, "cool": randf_range(0.6, 1.6), "turn": randf_range(0.5, 2.0)}


func _player() -> Dictionary:
	for t: Dictionary in tanks:
		if not t["enemy"]:
			return t
	return {}


func _enemies() -> int:
	var n := 0
	for t: Dictionary in tanks:
		if t["enemy"]:
			n += 1
	return n


# ----------------------------------------------------------------------------- управление
func action() -> void:
	if over:
		start()
		return
	var p := _player()
	if not p.is_empty():
		_fire(p)


func step(delta: float) -> void:
	if over:
		return
	_banner_t = maxf(_banner_t - delta, 0.0)
	var p := _player()
	if not p.is_empty():
		var h := held()
		if h != Vector2i.ZERO:
			_steer(p, h)
			_drive(p, 52.0 * delta)
	_spawn(delta)
	for t: Dictionary in tanks:
		if t["enemy"]:
			_think(t, delta)
	_fly(delta)
	if to_spawn == 0 and _enemies() == 0 and not over:
		wave += 1
		score += 500
		_new_wave()


func _spawn(delta: float) -> void:
	_spawn_t -= delta
	if to_spawn <= 0 or _spawn_t > 0.0 or _enemies() >= 3:
		return
	for sp: Vector2 in SPAWNS:
		if _free(Rect2(sp, Vector2(TILE, TILE)), {}):
			tanks.append(_tank(sp, Vector2i.DOWN, true))
			to_spawn -= 1
			_spawn_t = maxf(1.2, 3.0 - wave * 0.3)
			return


func _think(t: Dictionary, delta: float) -> void:
	t["turn"] -= delta
	t["cool"] -= delta
	if t["turn"] <= 0.0:
		_steer(t, _random_dir())
		t["turn"] = randf_range(0.8, 2.4)
	if not _drive(t, (30.0 + wave * 3.0) * delta):
		_steer(t, _random_dir())
	if t["cool"] <= 0.0:
		_fire(t)
		t["cool"] = randf_range(1.0, 2.4)


func _random_dir() -> Vector2i:
	var r := randf()
	if r < 0.4:
		return Vector2i.DOWN
	if r < 0.6:
		return Vector2i.LEFT
	if r < 0.8:
		return Vector2i.RIGHT
	return Vector2i.UP


## Поворот; при повороте поперёк танк выравнивается по сетке, чтобы проходить в проезды.
func _steer(t: Dictionary, d: Vector2i) -> void:
	var cur: Vector2i = t["dir"]
	if d == cur:
		return
	if d.x != 0 and cur.y != 0 or d.y != 0 and cur.x != 0:
		var p: Vector2 = t["pos"]
		var snapped := Vector2(snappedf(p.x, S), snappedf(p.y, S))
		if _free(Rect2(snapped, Vector2(TILE, TILE)), t):
			t["pos"] = snapped
	t["dir"] = d


func _drive(t: Dictionary, dist: float) -> bool:
	var d: Vector2i = t["dir"]
	var np: Vector2 = t["pos"] + Vector2(d) * dist
	if _free(Rect2(np, Vector2(TILE, TILE)), t):
		t["pos"] = np
		return true
	return false


func _cell(p: Vector2) -> int:
	var c := Vector2i(floori(p.x / S), floori(p.y / S))
	if c.x < 0 or c.y < 0 or c.x >= COLS or c.y >= ROWS:
		return -1
	return c.y * COLS + c.x


func _free(r: Rect2, self_t: Dictionary) -> bool:
	if r.position.x < 0 or r.position.y < 0 or r.end.x > COLS * S or r.end.y > ROWS * S:
		return false
	for y in range(floori(r.position.y / S), ceili(r.end.y / S)):
		for x in range(floori(r.position.x / S), ceili(r.end.x / S)):
			if cells[y * COLS + x] != EMPTY:
				return false
	for t: Dictionary in tanks:
		if not is_same(t, self_t) and Rect2(t["pos"], Vector2(TILE, TILE)).grow(-0.5).intersects(r):
			return false
	return true


# ----------------------------------------------------------------------------- снаряды
func _fire(t: Dictionary) -> void:
	for b: Dictionary in bullets:
		if is_same(b["owner"], t):
			return                                   # у каждого танка — один снаряд в полёте
	var d: Vector2i = t["dir"]
	bullets.append({"pos": t["pos"] + Vector2(TILE, TILE) / 2.0 + Vector2(d) * 8.0, "dir": d, "enemy": t["enemy"], "owner": t})
	if not t["enemy"]:
		blip(-24.0)


func _fly(delta: float) -> void:
	var dead: Array[Dictionary] = []
	for b: Dictionary in bullets:
		var d: Vector2i = b["dir"]
		b["pos"] += Vector2(d) * 150.0 * delta
		var p: Vector2 = b["pos"]
		if p.x < 0 or p.y < 0 or p.x >= COLS * S or p.y >= ROWS * S:
			dead.append(b)
			continue
		# снаряд шириной в две мелкие клетки: проверяем обе по бокам от линии полёта
		var side := Vector2(absf(d.y), absf(d.x)) * 2.0
		var hit := false
		for q: Vector2 in [p + side, p - side]:
			var i := _cell(q)
			if i < 0:
				continue
			match cells[i]:
				BRICK:
					cells[i] = EMPTY
					hit = true
				STEEL:
					hit = true
				BASE:
					hit = true
					_base_dead = true
					if not over:
						finish()
		if hit:
			dead.append(b)
			continue
		for t: Dictionary in tanks:
			if t["enemy"] != b["enemy"] and Rect2(t["pos"], Vector2(TILE, TILE)).has_point(p):
				dead.append(b)
				_hit(t)
				break
	# встречные снаряды гасят друг друга
	for a: Dictionary in bullets:
		for b: Dictionary in bullets:
			if a["enemy"] and not b["enemy"] and (a["pos"] as Vector2).distance_to(b["pos"]) < 5.0:
				dead.append(a)
				dead.append(b)
	for b: Dictionary in dead:
		bullets.erase(b)


func _hit(t: Dictionary) -> void:
	if t["enemy"]:
		tanks.erase(t)
		score += 100
		blip(-18.0)
		return
	lives -= 1
	if lives <= 0:
		tanks.erase(t)
		finish()
		return
	t["pos"] = PLAYER_START
	t["dir"] = Vector2i.UP


# ----------------------------------------------------------------------------- отрисовка
func draw(ci: CanvasItem) -> void:
	ci.draw_rect(area, Color("050607"))
	ci.draw_rect(Rect2(_o, Vector2(COLS * S, ROWS * S)), Color("101214"))
	for y in ROWS:
		for x in COLS:
			var r := Rect2(_o + Vector2(x * S, y * S), Vector2(S, S))
			match cells[y * COLS + x]:
				BRICK:
					ci.draw_rect(r, C_BRICK)
					ci.draw_line(r.position + Vector2(0, 3.5), r.position + Vector2(S, 3.5), Color("5a2a18"), 1.0)
					var mx := 2.5 if (x + y) % 2 == 0 else 5.5
					ci.draw_line(r.position + Vector2(mx, 0), r.position + Vector2(mx, 3.5), Color("5a2a18"), 1.0)
				STEEL:
					ci.draw_rect(r, C_STEEL)
					ci.draw_rect(Rect2(r.position + Vector2(2, 2), Vector2(4, 4)), Color("d8dce2"))
	_draw_base(ci)
	for t: Dictionary in tanks:
		_draw_tank(ci, t)
	for b: Dictionary in bullets:
		ci.draw_rect(Rect2(_o + (b["pos"] as Vector2) - Vector2(1.5, 1.5), Vector2(3, 3)), Color.WHITE)
	if _banner_t > 0.0 and not over:
		banner(ci, "Волна %d" % wave)
	if over:
		draw_over(ci)


func _draw_base(ci: CanvasItem) -> void:
	var r := Rect2(_o + Vector2(10 * TILE, 10 * TILE), Vector2(TILE, TILE))
	if _base_dead:                                   # развалины штаба
		ci.draw_rect(r, Color("1a1a1a"))
		for q: Vector2 in [Vector2(3, 9), Vector2(8, 11), Vector2(11, 6), Vector2(5, 4)]:
			ci.draw_rect(Rect2(r.position + q, Vector2(3, 3)), Color("4a4440"))
		return
	ci.draw_rect(r, Color("101214"))
	# орёл: серый силуэт с крыльями, как в оригинале
	var e := Color("b8bcc4")
	var c := r.get_center()
	ci.draw_colored_polygon(PackedVector2Array([c + Vector2(-7, -4), c + Vector2(-2, -1), c + Vector2(-2, 4), c + Vector2(-6, 2)]), e)
	ci.draw_colored_polygon(PackedVector2Array([c + Vector2(7, -4), c + Vector2(2, -1), c + Vector2(2, 4), c + Vector2(6, 2)]), e)
	ci.draw_rect(Rect2(c + Vector2(-2, -4), Vector2(4, 10)), e)
	ci.draw_circle(c + Vector2(0, -5), 2.2, e)
	ci.draw_rect(Rect2(c + Vector2(-4, 6), Vector2(8, 1.5)), e)


func _draw_tank(ci: CanvasItem, t: Dictionary) -> void:
	var r := Rect2(_o + (t["pos"] as Vector2), Vector2(TILE, TILE))
	var d: Vector2i = t["dir"]
	var col := C_ENEMY if t["enemy"] else C_PLAYER
	var dark := col.darkened(0.55)
	if d.x != 0:
		ci.draw_rect(Rect2(r.position, Vector2(TILE, 4)), dark)
		ci.draw_rect(Rect2(r.position + Vector2(0, 12), Vector2(TILE, 4)), dark)
	else:
		ci.draw_rect(Rect2(r.position, Vector2(4, TILE)), dark)
		ci.draw_rect(Rect2(r.position + Vector2(12, 0), Vector2(4, TILE)), dark)
	ci.draw_rect(r.grow(-3.0), col.darkened(0.15))
	var c := r.get_center()
	ci.draw_line(c, c + Vector2(d) * 8.0, col.lightened(0.3), 3.0)
	ci.draw_circle(c, 3.5, col.lightened(0.15))
	if t["enemy"]:
		ci.draw_circle(c, 1.5, Color("d9483c"))
