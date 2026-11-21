## Локация «Восточный ж/д мост» (YUR-7), ночь: пешеходный мост над путями станции Одесса-Восточная.
## Модели — из Blender (tools/blender/build_east_bridge.py), сцена локации — scenes/east_bridge/eb_location.tscn.
## Свет как на ночных фото станции: зелёные ртутные фонари на мосту и платформе у вокзала, натрий на городской
## платформе, на улице и на прожекторной мачте. Сценария пока нет — только прогулка: с городской улицы
## через мост и вниз по длинному спуску к полю, за которым село.
## Дневная игровая версия — scenes/levels/east_bridge_day.tscn.
extends Level

## Своё небо поверх общего окружения assets/environments/night_exterior.tres: зарево только со стороны города.
## Остальной свет (ambient, туман, тонмап) общий для всех ночных улиц — правится в .tres.
@export var sky_override: Sky

@onready var snowfall: GPUParticles3D = $Snowfall


func _start() -> void:
	if sky_override:
		var we := $WorldEnvironment as WorldEnvironment
		var env := we.environment.duplicate() as Environment
		env.sky = sky_override
		we.environment = env
	Game.music("mus_drone", -18.0)
	Game.set_objective("Перейти пути по мосту и спуститься к полю")
	await after(2.0)
	Game.say("Восточный мост. Внизу составы, гудят провода. За станцией — поле и огоньки села.")


func _process(_delta: float) -> void:
	if player:                                   # снегопад идёт только вокруг Юрчика
		snowfall.global_position = player.global_position + Vector3(0, 18, 0)
