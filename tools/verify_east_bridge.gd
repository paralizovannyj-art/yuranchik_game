## Проверка локации «Восточный ж/д мост» (YUR-7) без редактора: снимки с нескольких точек, высоты пола и проход по лестницам.
## Запуск (окно нужно — снимки берутся с экрана):
##   Godot.exe --path . --resolution 854x480 --script res://tools/verify_east_bridge.gd -- night <папка для снимков>
##   Godot.exe --path . --resolution 854x480 --script res://tools/verify_east_bridge.gd -- day <папка для снимков>
## Результат — PNG в папке и строки «FLOOR …», «WALK …» в выводе.
extends SceneTree

var out := ""
var level: Node3D


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var mode := args[0]
	out = args[1]
	DirAccess.make_dir_recursive_absolute(out)
	var path := "res://scenes/levels/east_bridge.tscn" if mode == "night" else "res://scenes/levels/east_bridge_day.tscn"
	level = (load(path) as PackedScene).instantiate()
	root.add_child(level)
	if mode == "night":
		_night.call_deferred()
	elif mode == "match":
		_match.call_deferred()
	else:
		_day.call_deferred()


func _wait(frames: int) -> void:
	for i in frames:
		await process_frame


func _shot(name: String) -> void:
	await _wait(3)
	root.get_texture().get_image().save_png(out.path_join(name + ".png"))
	print("SHOT ", name)


func _place(p: Node3D, pos: Vector3, yaw_deg: float) -> void:
	p.global_position = pos
	p.velocity = Vector3.ZERO
	var yaw := deg_to_rad(yaw_deg)
	p.rotation.y = yaw
	p.set("cam_yaw", yaw)
	p.set("_yaw_target", yaw)


func _floor(x: float, z: float) -> float:
	var space := level.get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(Vector3(x, 30, z), Vector3(x, -5, z))
	var hit := space.intersect_ray(q)
	return hit.position.y if hit else -999.0


func _walk(p: CharacterBody3D, name: String, pos: Vector3, yaw: float, frames: int) -> void:
	_place(p, pos, yaw)
	await _wait(5)
	Input.action_press("move_forward")
	var t0 := p.global_position
	await _wait(frames)
	Input.action_release("move_forward")
	print("WALK %s from %s to %s" % [name, t0, p.global_position])


func _night() -> void:
	await _wait(30)
	var p := level.get_node("Player") as CharacterBody3D
	# высоты пола (Godot: x вдоль путей, z: + город, − поле): мост, лестницы, площадки, платформы, спуск, земля
	for pt: Array in [["deck_mid", 0, 0], ["deck_city_end", 0, 70], ["city_stair_mid", 0, 75.3], ["city_landing", 0, 79.6],
			["city_stair_low", 0, 84], ["street", 0, 94], ["se_landing1", -3.9, 14.35], ["se_stair_mid", -8, 14.35],
			["se_landing2", -11.75, 14.35], ["se_platform", -25, 14.35], ["se_landing_e", 3.9, 14.35], ["shelter", -6, 15.2],
			["nw_landing_w", -3.9, -22.0], ["nw_landing_e", 3.9, -22.0], ["nw_steps", 21.5, -17.8], ["nw_ground", 21.5, -20.0],
			["nw_platform", 25, -13.65], ["leg_landing1", -4.75, -94], ["leg_mid", -25, -94], ["leg_landing5", -42, -94],
			["field", -60, -110], ["field_road", 0, -115.5], ["yard", 20, -57.75], ["station_forecourt", 50, -21]]:
		print("FLOOR %s %.2f" % [pt[0], _floor(pt[1], pt[2])])
	_place(p, Vector3(0, 0.2, 92), 0)
	await _wait(20)
	await _shot("n01_street")
	await _walk(p, "city_stairs_up", Vector3(0, 0.2, 92), 0, 1500)
	await _shot("n02_after_city_stairs")
	_place(p, Vector3(0, 7.6, 66), 0)
	await _wait(10)
	await _shot("n03_deck_from_city")
	_place(p, Vector3(0, 7.6, 0), 90)
	await _wait(10)
	await _shot("n04_deck_sw")
	_place(p, Vector3(0, 7.6, 0), -90)
	await _wait(10)
	await _shot("n05_deck_ne_station")
	await _walk(p, "se_stairs_down", Vector3(-0.6, 7.6, 14.35), 90, 900)
	await _shot("n06_after_se_stairs")
	await _walk(p, "se_stairs_down_e", Vector3(0.6, 7.6, 14.35), -90, 900)
	await _walk(p, "nw_stairs_down_e", Vector3(0.6, 7.6, -22.0), -90, 900)
	await _walk(p, "nw_steps_up", Vector3(21.5, 0.2, -20.5), 180, 240)
	_place(p, Vector3(-30, 1.2, 14.35), -70)
	await _wait(10)
	await _shot("n07_city_platform")
	_place(p, Vector3(40, 1.2, -14), 110)
	await _wait(10)
	await _shot("n08_station_platform")
	_place(p, Vector3(0, 7.6, -90), 0)
	await _wait(10)
	await _shot("n09_deck_to_field")
	await _walk(p, "leg_down", Vector3(-0.3, 7.6, -94), 90, 2600)
	await _shot("n10_after_leg")
	_place(p, Vector3(-60, 0.3, -125), 0)
	await _wait(10)
	await _shot("n11_field_village")
	_place(p, Vector3(-30, 0.3, -135), 180)
	await _wait(10)
	await _shot("n12_field_back_to_bridge")
	_place(p, Vector3(25, 0.3, -57.75), 90)
	await _wait(10)
	await _shot("n13_yard")
	_place(p, Vector3(30, 0.3, 93), 180)
	await _wait(10)
	await _shot("n14_city")
	quit()


func _day() -> void:
	await _wait(40)
	var p := level.get_node("Player") as CharacterBody3D
	await _shot("d01_start")
	await _walk(p, "city_stairs_up", Vector3(0, 0.2, 92), 0, 1500)
	await _shot("d02_after_city_stairs")
	_place(p, Vector3(0, 7.6, 40), 0)
	await _wait(10)
	await _shot("d03_deck_to_field")
	_place(p, Vector3(0, 7.6, 0), 90)
	await _wait(10)
	await _shot("d04_deck_sw")
	_place(p, Vector3(-30, 1.2, 14.35), -70)
	await _wait(10)
	await _shot("d05_city_platform")
	await _walk(p, "leg_down", Vector3(-0.3, 7.6, -94), 90, 2600)
	await _shot("d06_after_leg")
	_place(p, Vector3(-60, 0.3, -125), 0)
	await _wait(10)
	await _shot("d07_field_village")
	quit()


## Сверка с панорамами Google (окно 1024×768): те же точки и углы, что у снимков панорам в refs2,
## плюс вид сверху «север вверх» в масштабе спутника. Панорама 1 — на мосту над городской платформой,
## панорама 2 — на платформе у вокзала (её ya повёрнут на 28° от путей: yaw = 152 − ya). ya — угол панорамы, pi — наклон вниз, fo — горизонтальный угол обзора.
func _match() -> void:
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	root.size = Vector2i(1024, 768)
	root.mesh_lod_threshold = 0.0               # без упрощения сеток издалека (вид сверху с 400 м)
	await _wait(40)
	var env := (level.get_node("WorldEnvironment") as WorldEnvironment).environment
	var post := level.get_node_or_null("PS2Post") as CanvasLayer
	if post:
		post.visible = false                     # без PS2-фильтра: сверяем формы, а не пиксели
	var trains := level.get_node_or_null("Location/Trains") as Node3D
	if trains and OS.get_cmdline_user_args().has("notrains"):
		trains.visible = false                   # вагоны на панорамах другие — для сверки построек их можно скрыть
	var cam := Camera3D.new()
	cam.keep_aspect = Camera3D.KEEP_WIDTH
	level.add_child(cam)
	cam.make_current()
	var p1 := Vector3(0.0, 9.05, 14.35)
	var p2 := Vector3(16.0, 2.7, -12.0)
	var views := [
		["p1_ya000", p1, 90.0, 0.0, 90.0], ["p1_ya045", p1, 45.0, 0.0, 90.0], ["p1_ya090", p1, 0.0, 0.0, 90.0],
		["p1_ya135", p1, -45.0, 0.0, 90.0], ["p1_ya180", p1, -90.0, 0.0, 90.0], ["p1_ya225", p1, -135.0, 0.0, 90.0],
		["p1_ya270", p1, -180.0, 0.0, 90.0], ["p1_ya315", p1, -225.0, 0.0, 90.0],
		["p1_zoom_ya095", p1, -5.0, 0.0, 40.0], ["p1_zoom_ya272", p1, -182.0, 0.0, 40.0],
		["p1_down_ya030", p1, 60.0, 45.0, 90.0], ["p1_down_ya160", p1, -70.0, 45.0, 90.0],
		["p2_ya000", p2, 152.0, 0.0, 90.0], ["p2_ya045", p2, 107.0, 0.0, 90.0], ["p2_ya090", p2, 62.0, 0.0, 90.0],
		["p2_ya135", p2, 17.0, 0.0, 90.0], ["p2_ya180", p2, -28.0, 0.0, 90.0], ["p2_ya225", p2, -73.0, 0.0, 90.0],
		["p2_ya270", p2, -118.0, 0.0, 90.0], ["p2_ya315", p2, -163.0, 0.0, 90.0],
		["p2_zoom_ya040", p2, 112.0, -15.0, 55.0], ["p2_zoom_ya005", p2, 147.0, -10.0, 55.0],
	]
	for v: Array in views:
		cam.global_position = v[1]
		cam.rotation = Vector3(deg_to_rad(-float(v[3])), deg_to_rad(float(v[2])), 0.0)
		cam.fov = v[4]
		await _wait(4)
		await _shot(v[0])
	# вид сверху, север вверх: пути (+X) идут на азимут 40°, мост (+Y Blender = −Z Godot) — на северо-запад
	env.fog_enabled = false
	env.volumetric_fog_enabled = false
	var snow := level.get_node_or_null("Snowfall")
	if snow:
		snow.visible = false
	var b := deg_to_rad(40.0)
	var north := Vector3(cos(b), 0.0, -sin(b))
	var east := Vector3(sin(b), 0.0, cos(b))
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	cam.far = 2000.0
	for o: Array in [["top_0345mpx_c0_10", Vector3(0, 400, -10), 264.96], ["top_1mpx_field", Vector3(-100, 600, -150), 768.0]]:
		cam.global_transform = Transform3D(Basis(east, north, Vector3.UP), o[1])
		cam.size = o[2]
		await _wait(6)
		await _shot(o[0])
	quit()
