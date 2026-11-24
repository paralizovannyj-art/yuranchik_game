## Пар изо рта Юрчика на морозе: короткий выдох со звуком (player_breath_1..3), затем пауза
## случайной длины из pause_choices.
## Первый выдох тоже после случайной паузы — иначе пар появлялся бы сразу при входе на уровень.
extends GPUParticles3D

@export var exhale_duration: float = 0.5
@export var pause_choices: PackedFloat32Array = [10.0, 15.0, 20.0]  ## секунды между выдохами, берётся случайная
@export var sound_db := -14.0          ## громкость выдоха (тихо — это фон, а не событие)
@export var warm := false              ## в тепле (квартира): пара не видно, выдох не слышно
## Пар сам не светится: в темноте его почти не видно, ярко — только в луче фонарика (как в жизни).
## Материал без освещения (освещённый пар в 0.2 м от фонарика просто белел бы), поэтому яркость задаётся тут.
@export var lit_brightness := 1.0      ## фонарик горит — пар прямо в луче
@export var dark_brightness := 0.14    ## фонарика нет — чуть заметная дымка от «привыкших глаз» и зарева


func _ready() -> void:
	# Важно: отключаем автостарт, чтобы скрипт сам управлял выдохами
	emitting = false
	breathe_loop()


func breathe_loop() -> void:
	while is_inside_tree():
		await get_tree().create_timer(_next_pause()).timeout
		if not is_inside_tree():
			return
		if warm:
			continue
		# Принудительно перезапускаем цикл частиц для чистого выдоха
		_set_brightness()
		restart()
		emitting = true
		Game.sfx_rand("player_breath", 3, null, sound_db)
		await get_tree().create_timer(exhale_duration).timeout
		emitting = false


func _next_pause() -> float:
	if pause_choices.is_empty():
		return 15.0
	return pause_choices[randi() % pause_choices.size()]


func _set_brightness() -> void:
	var m := (draw_pass_1.material if draw_pass_1 else null) as StandardMaterial3D
	if m == null:
		return
	var fl := owner.get("flashlight") as Light3D if owner else null
	var k := lit_brightness if fl and fl.is_visible_in_tree() and fl.light_energy > 0.0 else dark_brightness
	m.albedo_color = Color(k, k, k, 1.0)
