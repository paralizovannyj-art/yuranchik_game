## Пар изо рта Юрчика на морозе: короткий выдох со звуком (player_breath_1..3), затем пауза
## случайной длины из pause_choices.
## Первый выдох тоже после случайной паузы — иначе пар появлялся бы сразу при входе на уровень.
extends GPUParticles3D

@export var exhale_duration: float = 0.5
@export var pause_choices: PackedFloat32Array = [10.0, 15.0, 20.0]  ## секунды между выдохами, берётся случайная
@export var sound_db := -14.0          ## громкость выдоха (тихо — это фон, а не событие)


func _ready() -> void:
	# Важно: отключаем автостарт, чтобы скрипт сам управлял выдохами
	emitting = false
	breathe_loop()


func breathe_loop() -> void:
	while is_inside_tree():
		await get_tree().create_timer(_next_pause()).timeout
		if not is_inside_tree():
			return
		# Принудительно перезапускаем цикл частиц для чистого выдоха
		restart()
		emitting = true
		Game.sfx_rand("player_breath", 3, null, sound_db)
		await get_tree().create_timer(exhale_duration).timeout
		emitting = false


func _next_pause() -> float:
	if pause_choices.is_empty():
		return 15.0
	return pause_choices[randi() % pause_choices.size()]
