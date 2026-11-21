extends SceneTree
## Проверка двора Юрчика (district.tscn — от района остался только двор): старт (стоит ли Юрчик на земле, FPS, скриншот)
## и прогулки к четырём краям двора — невидимые стены YardBounds должны держать Юрчика внутри.
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
	var m := lvl.get_node("Teleports/Tp1") as Node3D
	lvl.teleport(m.global_transform)
	await _wait(2.0)
	var p := player.global_position
	_log("TP1 home y=%.2f (метка %.2f) на земле=%s fps=%d" % [p.y, m.global_position.y,
		player.is_on_floor(), Engine.get_frames_per_second()])
	if not player.is_on_floor():
		fails += 1
	await _shot("tp1_home")

	# к краям двора: дошёл до невидимой стены и остался внутри (стены: x -46 / 27, z -81 / -14)
	await _walk("south edge", Vector3(-35, 3, -19), PI, 8.0, func(q): return q.z > -16.0)
	await _inside("south edge", PI)
	await _walk("west edge", Vector3(-25, 3, -48), PI / 2, 14.0, func(q): return q.x < -44.0)
	await _inside("west edge", PI / 2)
	await _walk("north edge", Vector3(14, 3, -70), 0.0, 8.0, func(q): return q.z < -79.0)
	await _inside("north edge", 0.0)
	await _walk("east edge", Vector3(0, 3, -79), -PI / 2, 25.0, func(q): return q.x > 25.0)
	await _inside("east edge", -PI / 2)
	# дорога к гаражу Юрчика: из двора через арку западного дома, вдоль него на юг, между южным домом и «ракушками» на восток
	await _walk("garage: west arch", Vector3(-25, 3, -48), PI / 2, 14.0, func(q): return q.x < -43.5)
	await _walk("garage: lane south", Vector3(-44, 3, -48), PI, 14.0, func(q): return q.z > -26.0)
	await _walk("garage: to door", Vector3(-44, 3, -26), -PI / 2, 25.0, func(q): return q.x > -2.5)

	# двор сверху
	var env: Environment = lvl.get_node("WorldEnvironment").environment
	env.fog_enabled = false
	env.volumetric_fog_enabled = false
	env.ambient_light_energy = 2.5
	lvl.get_node("Snowfall").visible = false
	lvl.get_node("PS2Post").visible = false
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 90
	cam.far = 500
	lvl.add_child(cam)
	cam.global_transform = Transform3D(Basis(Vector3.RIGHT, -PI / 2), Vector3(-13, 200, -47.5))
	cam.current = true
	await _wait(0.5)
	await _shot("topdown")

	_log("ИТОГ: сбоев %d" % fails)
	var f := FileAccess.open(out_dir + "test_log.txt", FileAccess.WRITE)
	f.store_string("
".join(log_lines))
	f.close()
	quit(1 if fails > 0 else 0)


## Ещё 3 с упираться в край двора в сторону yaw — и Юрчик всё ещё внутри (не прошёл сквозь невидимую стену).
func _inside(name: String, yaw: float) -> void:
	Input.action_press("move_forward")
	var start := Time.get_ticks_msec()
	while Time.get_ticks_msec() - start < 3000:
		await physics_frame
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		player.set("_yaw_target", yaw)
		player.cam_yaw = yaw
	Input.action_release("move_forward")
	await _wait(0.3)
	var q := player.global_position
	var ok := q.x > -46.0 and q.x < 27.0 and q.z > -81.0 and q.z < -14.0
	_log("%s %-22s внутри двора (%.1f, %.1f)" % ["OK  " if ok else "FAIL", name, q.x, q.z])
	if not ok:
		fails += 1
