## Снимки квартиры 47 с одинаковых точек — для сравнения текстур «до / после».
## Девять точек (прихожая от входной двери и к выходу, коридор, комната от двери, диван с Хьюгой, стол с компом,
## дверь комнаты, окно, игровое кресло),
## в двух режимах: «lit» — свет в прихожей и люстра в комнате включены, «dark» — свет квартиры выключен,
## светит только фонарик (как у игрока: угол 20°, резкий край).
## Запуск (окно нужно — снимки берутся с экрана):
##   Godot.exe --path . --resolution 1280x720 --script res://tools/capture_apartment.gd -- <папка> [префикс]
##   «Слабый ПК»: добавить --rendering-driver opengl3 --rendering-method gl_compatibility
extends SceneTree

var out := ""
var prefix := ""
var level: Node3D
var cam: Camera3D
var torch: SpotLight3D

# точка: имя, позиция камеры, куда смотрит (мировые координаты Godot, пол квартиры y = 8.4)
const VIEWS := [
	["hall", Vector3(-3.45, 10.0, -1.25), Vector3(-6.6, 9.3, -1.3)],
	["hall_exit", Vector3(-6.95, 10.0, -1.75), Vector3(-3.3, 9.3, -1.15)],
	["corridor", Vector3(-6.8, 10.0, -1.7), Vector3(-6.8, 9.2, 2.2)],
	["room", Vector3(-6.75, 10.0, 2.5), Vector3(-8.4, 9.1, 5.7)],
	["sofa", Vector3(-6.55, 9.9, 5.2), Vector3(-7.6, 8.9, 3.9)],
	["desk", Vector3(-7.1, 10.0, 3.6), Vector3(-9.1, 9.3, 2.9)],
	["door", Vector3(-7.6, 10.0, 4.2), Vector3(-7.2, 9.4, 2.3)],
	["window", Vector3(-7.8, 10.0, 4.8), Vector3(-7.8, 9.9, 6.48)],
	["chair", Vector3(-7.4, 9.9, 3.9), Vector3(-8.07, 8.9, 2.95)],
]


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out = args[0]
	prefix = args[1] if args.size() > 1 else ""
	DirAccess.make_dir_recursive_absolute(out)
	level = (load("res://scenes/levels/stairwell.tscn") as PackedScene).instantiate()
	root.add_child(level)
	_run.call_deferred()


func _wait(frames: int) -> void:
	for i in frames:
		await process_frame


func _hide_ui() -> void:
	for n: Node in root.find_children("*", "CanvasLayer", true, false):
		if n.name != "PS2Post":
			(n as CanvasLayer).visible = false


func _lights(lit: bool) -> void:
	var L := level.get_node("Lights")
	for n: String in ["AptHall", "DoorGap"]:
		(L.get_node(n) as Light3D).visible = lit
	var room := L.get_node("AptRoom") as OmniLight3D
	room.visible = lit
	room.light_energy = 1.3 if lit else 0.0
	torch.visible = not lit


func _run() -> void:
	await _wait(10)
	var pl := level.get_node_or_null("Player")
	if pl:
		var fl := pl.find_child("Flashlight", true, false) as Light3D
		if fl:
			fl.visible = false
		pl.process_mode = Node.PROCESS_MODE_DISABLED
	cam = Camera3D.new()
	cam.fov = 75.0
	level.add_child(cam)
	torch = SpotLight3D.new()                      # как Flashlight в player.tscn
	torch.light_color = Color(1, 0.93, 0.8)
	torch.light_energy = 8.0
	torch.shadow_enabled = true
	torch.spot_range = 18.0
	torch.spot_attenuation = 0.9
	torch.spot_angle = 20.0
	torch.spot_angle_attenuation = 0.15
	torch.position = Vector3(0.18, -0.22, -0.05)
	cam.add_child(torch)
	await _wait(60)
	for mode: String in ["lit", "dark"]:
		_lights(mode == "lit")
		for v: Array in VIEWS:
			cam.global_position = v[1]
			cam.look_at(v[2], Vector3.UP)
			cam.make_current()
			_hide_ui()
			await _wait(20)
			_hide_ui()
			var name: String = "%s%s_%s" % [prefix, v[0], mode]
			root.get_texture().get_image().save_png(out.path_join(name + ".png"))
			print("SHOT ", name)
	quit()
