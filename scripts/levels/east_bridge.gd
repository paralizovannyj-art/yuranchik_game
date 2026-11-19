## Локация «Восточный ж/д мост» (YUR-7), ночь: пешеходный мост над путями станции Одесса-Восточная.
## Модели — из Blender (tools/blender/build_east_bridge.py), сцена локации — scenes/east_bridge/eb_location.tscn.
## Свет как на ночных фото станции: зелёные ртутные фонари на мосту и первой платформе, натрий на второй
## и на прожекторных мачтах. Сценария пока нет — только прогулка: с южной стороны через мост на север.
## Дневная версия для катсцены — scenes/levels/east_bridge_day.tscn.
extends Level

@onready var snowfall: GPUParticles3D = $Snowfall


func _start() -> void:
	Game.music("mus_drone", -18.0)
	Game.set_objective("Перейти пути по мосту на северную сторону")
	await after(2.0)
	Game.say("Восточный мост. Внизу стоят составы, гудят провода.")


func _process(_delta: float) -> void:
	if player:                                   # снегопад идёт только вокруг Юрчика
		snowfall.global_position = player.global_position + Vector3(0, 18, 0)
