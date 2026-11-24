## Рассеянный свет фонарика (spill): у настоящего фонарика яркое пятно в центре (основной луч Flashlight)
## и слабый широкий ореол вокруг — отражатель светит не только узким пучком.
## Висит дочерним узлом Flashlight: повторяет его цвет, маску (телефон прячет руку от света) и яркость
## (уровень задаёт flashlight_energy) — менять ничего, кроме основного луча, не нужно.
extends SpotLight3D

@export_range(0.0, 1.0) var share := 0.22   ## яркость ореола от яркости основного луча


func _process(_delta: float) -> void:
	var main := get_parent() as SpotLight3D
	if main == null:
		return
	light_energy = main.light_energy * share
	light_color = main.light_color
	light_cull_mask = main.light_cull_mask
