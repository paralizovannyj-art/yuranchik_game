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


func _night() -> void:
	await _wait(30)
	var p := level.get_node("Player") as CharacterBody3D
	# высоты пола: мост, площадки, середины маршей, платформы, земля
	for pt: Array in [["bridge_mid", 0, 10], ["bridge_south", 0, 54], ["south_stair_mid", 0, 59.3], ["south_landing", 0, 63.6],
			["north_stair_mid", 0, -37.3], ["p1_stair_mid", 4.35, 24], ["p1_landing", 8.2, 24], ["p1_stair_low", 12.0, 24],
			["p1_platform", -30, 24], ["p2_stair_mid", -4.35, -2], ["p2_platform", 30, -2], ["yard", 20, 31.75], ["ground_s", 10, 72]]:
		print("FLOOR %s %.2f" % [pt[0], _floor(pt[1], pt[2])])
	_place(p, Vector3(0, 0.2, 74.5), 0)
	await _wait(20)
	await _shot("n01_spawn")
	# проход: от низа южной лестницы вверх на мост (на север)
	Input.action_press("move_forward")
	var t0 := p.global_position
	await _wait(600)
	Input.action_release("move_forward")
	print("WALK south_stairs from %s to %s" % [t0, p.global_position])
	await _shot("n02_after_walk_up")
	_place(p, Vector3(0, 7.6, 45), 0)
	await _wait(10)
	await _shot("n03_bridge_north")
	_place(p, Vector3(0, 7.6, 10), 90)
	await _wait(10)
	await _shot("n04_bridge_west")
	_place(p, Vector3(0, 7.6, 10), -90)
	await _wait(10)
	await _shot("n05_bridge_east")
	# спуск по лестнице на первую платформу (на восток)
	_place(p, Vector3(0.6, 7.6, 24), -90)
	await _wait(5)
	Input.action_press("move_forward")
	t0 = p.global_position
	await _wait(500)
	Input.action_release("move_forward")
	print("WALK p1_stairs from %s to %s" % [t0, p.global_position])
	await _shot("n06_after_walk_down_p1")
	_place(p, Vector3(-35, 1.2, 24), -70)
	await _wait(10)
	await _shot("n07_platform1")
	_place(p, Vector3(35, 1.2, -2), 110)
	await _wait(10)
	await _shot("n08_platform2")
	_place(p, Vector3(-12, 0.2, -38), 15)
	await _wait(10)
	await _shot("n09_north_station")
	_place(p, Vector3(25, 0.3, 31.75), 90)
	await _wait(10)
	await _shot("n10_yard")
	quit()


func _day() -> void:
	await _wait(40)
	await _shot("d01_start")
	# своя камера: основную двигает анимация проезда
	var cam := Camera3D.new()
	cam.fov = 60.0
	level.add_child(cam)
	cam.make_current()
	cam.global_transform = (level.get_node("ShotTo") as Marker3D).global_transform
	await _wait(5)
	await _shot("d02_end")
	cam.global_position = Vector3(30, 14, 70)
	cam.look_at(Vector3(0, 4, 10))
	await _wait(5)
	await _shot("d03_overview")
	cam.global_position = Vector3(-20, 2.2, 20)
	cam.look_at(Vector3(10, 6, 24))
	await _wait(5)
	await _shot("d04_platform")
	quit()
