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
			["se_landing2", -11.75, 14.35], ["se_platform", -25, 14.35], ["nw_landing_w", -3.9, -13.65], ["nw_landing_e", 3.9, -13.65],
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
	await _walk(p, "nw_stairs_down_e", Vector3(0.6, 7.6, -13.65), -90, 900)
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
	await _shot("d01_start")
	# своя камера: основную двигает анимация проезда
	var cam := Camera3D.new()
	cam.fov = 60.0
	level.add_child(cam)
	cam.make_current()
	cam.global_transform = (level.get_node("ShotTo") as Marker3D).global_transform
	await _wait(5)
	await _shot("d02_end")
	cam.global_position = Vector3(-40, 20, -170)
	cam.look_at(Vector3(0, 5, 0))
	await _wait(5)
	await _shot("d03_from_field")
	cam.global_position = Vector3(12, 1.7, 95)
	cam.look_at(Vector3(0, 7, 40))
	await _wait(5)
	await _shot("d04_from_street")
	cam.global_position = Vector3(-50, 2, -200)
	cam.look_at(Vector3(-110, 3, -300))
	await _wait(5)
	await _shot("d05_village")
	cam.global_position = Vector3(-20, 2.8, 14.35)
	cam.look_at(Vector3(10, 6, 5))
	await _wait(5)
	await _shot("d06_platform")
	quit()
