extends SceneTree
## Проверка района «Паскот» (docs/CITY_PLAN.md): 8 точек телепорта (стоит ли Юрчик на земле, FPS, скриншот)
## и 18 маршрутов пешком — лестницы, пандусы, арки, переход, трубы, гаражи, недострой.
## Запуск из папки проекта (нужно окно, не --headless):
##   Godot.exe --path . --resolution 854x480 --script tools/tests/test_district.gd -- <папка для скриншотов и лога>
## Без папки пишет в user://district_test/. Код выхода 0 — всё прошло, 1 — есть сбои.
##
## Вид от первого лица: мышь в игре захвачена и поворачивает взгляд, поэтому тест её отпускает и на каждом
## кадре сам держит направление. Маршрут засчитан, как только Юрчик дошёл до цели (не «где оказался через N секунд»).

var out_dir := "user://district_test/"
var fails := 0
var lvl: Node
var player: CharacterBody3D
var log_lines: PackedStringArray = []


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out_dir = args[0].replace("\\", "/").trim_suffix("/") + "/"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out_dir))
	change_scene_to_file("res://scenes/levels/district.tscn")
	_run.call_deferred()


func _log(s: String) -> void:
	print(s)
	log_lines.append(s)


func _wait(t: float) -> void:
	await create_timer(t).timeout


func _shot(name: String) -> void:
	await process_frame
	await process_frame
	root.get_texture().get_image().save_png(out_dir + name + ".png")


func _tp(pos: Vector3, yaw: float) -> void:
	lvl.teleport(Transform3D(Basis(Vector3.UP, yaw), pos))


## Идти вперёд от pos в сторону yaw, пока check(позиция) не станет истиной; secs — сколько ждать самое большее.
func _walk(name: String, pos: Vector3, yaw: float, secs: float, check: Callable) -> void:
	_tp(pos, yaw)
	await _wait(0.6)
	Input.action_press("move_forward")
	var trace := ""
	var ok := false
	var start := Time.get_ticks_msec()
	var next_mark := 1000
	while not ok and Time.get_ticks_msec() - start < int(secs * 1000.0):
		await physics_frame
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE          # настоящая мышь не должна крутить взгляд
		player.set("_yaw_target", yaw)
		player.cam_yaw = yaw
		var q := player.global_position
		ok = check.call(q)
		if Time.get_ticks_msec() - start >= next_mark:
			next_mark += 1000
			trace += " (%.0f,%.1f,%.0f)" % [q.x, q.y, q.z]
	Input.action_release("move_forward")
	await _wait(0.4)
	var p := player.global_position
	var took := (Time.get_ticks_msec() - start) / 1000.0
	_log("%s %-22s %4.1f с  конец=(%.1f, %.2f, %.1f)" % ["OK  " if ok else "FAIL", name, took, p.x, p.y, p.z])
	if not ok:
		fails += 1
		_log("     путь:" + trace)


func _run() -> void:
	await _wait(1.0)
	lvl = current_scene
	player = get_first_node_in_group("player")
	await _wait(2.5)
	var names := ["home", "prospect", "school", "south", "boiler", "garages", "wasteland", "west"]
	for i in 8:
		var m := lvl.get_node("Teleports/Tp%d" % (i + 1)) as Node3D
		lvl.teleport(m.global_transform)
		await _wait(2.0)
		var p := player.global_position
		_log("TP%d %-10s y=%.2f (метка %.2f) на земле=%s fps=%d" % [i + 1, names[i], p.y, m.global_position.y,
			player.is_on_floor(), Engine.get_frames_per_second()])
		if not player.is_on_floor():
			fails += 1
		await _shot("tp%d_%s" % [i + 1, names[i]])

	await _walk("wide stairs down", Vector3(-35, 3, -19), PI, 12.0, func(p): return absf(p.y) < 0.3 and p.z > -10)
	await _walk("wide stairs up", Vector3(-35, 0, -7), 0.0, 15.0, func(p): return absf(p.y - 3) < 0.3)
	await _walk("prospect stairs up", Vector3(14, 3, -70), 0.0, 15.0, func(p): return absf(p.y - 6) < 0.3)
	await _walk("prospect road ramp", Vector3(23, 3, -66), 0.0, 21.0, func(p): return absf(p.y - 6) < 0.3)
	await _walk("south road ramp", Vector3(23, 3, -19), PI, 19.5, func(p): return absf(p.y) < 0.3 and p.z > -5)
	await _walk("tunnel through", Vector3(-55, 3, -68), 0.0, 60.0, func(p): return absf(p.y - 6) < 0.3 and p.z < -107)
	await _walk("home west arch", Vector3(-25, 3, -48), PI / 2, 21.0, func(p): return p.x < -43)
	await _walk("south yard arch", Vector3(-18, 0, -8), PI, 16.5, func(p): return p.z > 7)
	await _walk("pipe crossing", Vector3(15, 0, 32), PI, 15.0, func(p): return p.z > 44)
	await _walk("onto garage roof", Vector3(-30, 0, 45), PI, 4.5, func(p): return p.z > 47 and absf(p.y) < 0.3)
	await _walk("garage stairs", Vector3(-60.5, 0, 45), PI, 12.0, func(p): return absf(p.y + 2.5) < 0.3)
	await _walk("garage road ramps", Vector3(23, 0, 40), PI, 67.5, func(p): return absf(p.y + 7.5) < 0.3)
	await _walk("nedostroy floor 1", Vector3(-71.5, 0, 42.5), 0.0, 6.9, func(p): return p.y > 2.5)
	await _walk("pit ramp out", Vector3(-81, -5, 22), PI, 23.2, func(p): return absf(p.y) < 0.3 and p.z > 44)
	await _walk("school tribune", Vector3(78, 3, -34.5), -PI / 2, 6.0, func(p): return p.x > 83 and p.y > 4)
	await _walk("cross prospect", Vector3(15, 6, -81.5), 0.0, 21.0, func(p): return p.z < -97 and absf(p.y - 6) < 0.3)
	await _walk("west yard wall alley", Vector3(-82, 3, -66), 0.0, 13.5, func(p): return p.z < -78.5)
	await _walk("west stairs down", Vector3(-57, 3, -20), PI, 12.0, func(p): return absf(p.y) < 0.3)

	# карта сверху
	var env: Environment = lvl.get_node("WorldEnvironment").environment
	env.fog_enabled = false
	env.volumetric_fog_enabled = false
	env.ambient_light_energy = 2.5
	lvl.get_node("Snowfall").visible = false
	lvl.get_node("PS2Post").visible = false
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 225
	cam.far = 500
	lvl.add_child(cam)
	cam.global_transform = Transform3D(Basis(Vector3.RIGHT, -PI / 2), Vector3(0, 200, -5))
	cam.current = true
	await _wait(0.5)
	await _shot("topdown")
	# общий вид с высоты
	cam.projection = Camera3D.PROJECTION_PERSPECTIVE
	cam.fov = 60
	cam.global_transform = Transform3D.IDENTITY.looking_at(Vector3(0, 0, 0) - Vector3(-140, 90, 200), Vector3.UP)
	cam.global_position = Vector3(-95, 70, 140)
	cam.look_at(Vector3(5, 0, -30))
	await _wait(0.5)
	await _shot("overview")

	_log("ИТОГ: сбоев %d" % fails)
	var f := FileAccess.open(out_dir + "test_log.txt", FileAccess.WRITE)
	f.store_string("\n".join(log_lines))
	f.close()
	quit(1 if fails > 0 else 0)
