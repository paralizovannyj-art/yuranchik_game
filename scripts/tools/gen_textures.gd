## Генератор low-res текстур в стиле PS2 для теста вайба.
## Запуск: load("res://scripts/tools/gen_textures.gd").generate()
extends RefCounted

const OUT := "res://assets/textures/"


static func generate() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 1977
	_facade(rng)
	_snow()
	_slush()
	_concrete()
	_garage()


static func _noise(seed_: int, freq: float, size: int) -> Image:
	var n := FastNoiseLite.new()
	n.seed = seed_
	n.frequency = freq
	n.fractal_octaves = 4
	return n.get_seamless_image(size, size)


static func _v(img: Image, x: int, y: int) -> float:
	return img.get_pixel(x % img.get_width(), y % img.get_height()).r


# Фасад панельки: 8 окон по ширине x 9 этажей, ячейка 32x32 px.
static func _facade(rng: RandomNumberGenerator) -> void:
	var cols := 8
	var rows := 9
	var cell := 32
	var w := cols * cell
	var h := rows * cell
	var alb := Image.create(w, h, false, Image.FORMAT_RGB8)
	var emi := Image.create(w, h, false, Image.FORMAT_RGB8)
	emi.fill(Color.BLACK)
	var nz := _noise(11, 0.05, 256)
	var nz2 := _noise(12, 0.2, 256)
	for y in h:
		for x in w:
			var g := 0.50 + (_v(nz, x, y) - 0.5) * 0.10 + (_v(nz2, x, y) - 0.5) * 0.06
			var cx := x % cell
			var cy := y % cell
			# швы между панелями
			if cx == 0 or cy == 0:
				g *= 0.62
			# потёки под окнами
			if cy > 23 and cx > 9 and cx < 23:
				g *= 0.88 - 0.04 * float((x * 7) % 3)
			alb.set_pixel(x, y, Color(g, g * 0.99, g * 0.95))
	for row in rows:
		for col in cols:
			var ox := col * cell
			var oy := row * cell
			var lit := rng.randf() < 0.28
			var warm := [Color(1.0, 0.72, 0.38), Color(1.0, 0.84, 0.58), Color(0.95, 0.6, 0.3), Color(0.55, 0.7, 1.0)]
			var lc: Color = warm[rng.randi() % (3 if rng.randf() < 0.9 else 4)]
			var curtain := rng.randf() < 0.6
			for y in range(8, 23):
				for x in range(9, 24):
					var px := ox + x
					var py := oy + y
					var frame := x == 9 or x == 23 or y == 8 or y == 22 or x == 16
					if frame:
						alb.set_pixel(px, py, Color(0.68, 0.66, 0.6))
						continue
					var grad := float(y - 8) / 14.0
					if lit:
						var k := 0.75 + 0.25 * grad
						if curtain:
							k *= 0.8 + 0.2 * float((x / 2) % 2)
						var c := lc * k
						alb.set_pixel(px, py, c * 0.8)
						emi.set_pixel(px, py, c)
					else:
						var r := 0.06 + 0.07 * (1.0 - grad) * float((x + y) % 7 < 3)
						alb.set_pixel(px, py, Color(r, r * 1.1, r * 1.35))
			# подоконник
			for x in range(8, 25):
				alb.set_pixel(ox + x, oy + 23, Color(0.36, 0.36, 0.36))
	alb.save_png(OUT + "facade_albedo.png")
	emi.save_png(OUT + "facade_emission.png")


static func _snow() -> void:
	var s := 128
	var img := Image.create(s, s, false, Image.FORMAT_RGB8)
	var a := _noise(21, 0.04, s)
	var b := _noise(22, 0.25, s)
	for y in s:
		for x in s:
			var v := 0.80 + (_v(a, x, y) - 0.5) * 0.18 + (_v(b, x, y) - 0.5) * 0.10
			img.set_pixel(x, y, Color(v * 0.93, v * 0.97, v * 1.05))
	img.save_png(OUT + "snow.png")


static func _slush() -> void:
	var s := 128
	var img := Image.create(s, s, false, Image.FORMAT_RGB8)
	var a := _noise(31, 0.05, s)
	var b := _noise(32, 0.3, s)
	for y in s:
		for x in s:
			var n := _v(a, x, y)
			var v := 0.17 + (_v(b, x, y) - 0.5) * 0.06
			var c := Color(v, v * 0.96, v * 0.9)
			if n > 0.62:
				var t := clampf((n - 0.62) * 6.0, 0.0, 1.0)
				c = c.lerp(Color(0.62, 0.64, 0.68), t)
			img.set_pixel(x, y, c)
	img.save_png(OUT + "slush.png")


static func _concrete() -> void:
	var s := 64
	var img := Image.create(s, s, false, Image.FORMAT_RGB8)
	var a := _noise(41, 0.08, s)
	for y in s:
		for x in s:
			var g := 0.48 + (_v(a, x, y) - 0.5) * 0.14
			if x == 0 or y == 0:
				g *= 0.6
			img.set_pixel(x, y, Color(g, g * 0.99, g * 0.96))
	img.save_png(OUT + "concrete.png")


static func _garage() -> void:
	var s := 64
	var img := Image.create(s, s, false, Image.FORMAT_RGB8)
	var a := _noise(51, 0.07, s)
	var b := _noise(52, 0.3, s)
	for y in s:
		for x in s:
			var rib := 0.85 + 0.15 * float(x % 8 < 2)
			var rust := clampf((_v(a, x, y) - 0.45) * 3.0, 0.0, 1.0)
			var base := Color(0.22, 0.30, 0.26).lerp(Color(0.38, 0.2, 0.1), rust)
			base = base * (rib * (0.9 + (_v(b, x, y) - 0.5) * 0.3))
			img.set_pixel(x, y, base)
	img.save_png(OUT + "garage_metal.png")
