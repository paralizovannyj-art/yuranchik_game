## «Восточный ж/д мост» днём (YUR-7) — игровой уровень: лютый зимний пасмурный день, как на дневном фото.
## Юрчик начинает на улице у городской лестницы, как и ночью. Фонари выключены, кроме одной мачты.
extends Level

@onready var snowfall: GPUParticles3D = $Snowfall


func _start() -> void:
	Game.music("mus_drone", -20.0)
	Game.set_objective("Перейти пути по мосту и спуститься к полю")
	await after(2.0)
	Game.say("Восточный мост. Серо, метёт. Внизу составы, за станцией — поле и село.")


func _process(_delta: float) -> void:
	if player:
		snowfall.global_position = player.global_position + Vector3(0, 18, 0)
