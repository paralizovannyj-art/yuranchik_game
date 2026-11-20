## «Восточный ж/д мост» днём (YUR-7) — игровой уровень: лютая метель, как на дневном фото, только хуже.
## Юрчик начинает на улице у городской лестницы, как и ночью. Фонари выключены, кроме одной мачты.
## Метель — три слоя частиц, которые едут за камерой и рождаются с наветренной стороны от неё:
##   Snowfall — мелкий снег вокруг, Blizzard — быстрые чёрточки снега прямо в лицо, Gusts — полупрозрачные снежные «простыни».
## Ветер дует с севера (к городу): направление — direction у материала частиц Blizzard, остальные слои стоит менять вместе с ним.
## Видимость — fog_density у WorldEnvironment (0.045: на 20 м видно ~40%, дальше 50 м — белая стена).
extends Level

@onready var snowfall: GPUParticles3D = $Snowfall
@onready var blizzard: GPUParticles3D = $Blizzard
@onready var gusts: GPUParticles3D = $Gusts

var _last_cam_pos := Vector3.INF


func _start() -> void:
	Game.music("mus_drone", -20.0)
	Game.set_objective("Перейти пути по мосту и спуститься к полю")
	await after(2.0)
	Game.say("Восточный мост. Метёт так, что дальше пары пролётов ничего не видно.")


func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var wind := (blizzard.process_material as ParticleProcessMaterial).direction.normalized()
	var p := cam.global_position
	snowfall.global_position = p - wind * 8.0 + Vector3(0, 2, 0)
	blizzard.global_position = p - wind * 13.0
	gusts.global_position = p - wind * 20.0 + Vector3(0, -1, 0)
	# камеру перенесло разом (чекпойнт, переход) — снег на новом месте сразу полный, без «пустой» секунды
	if p.distance_to(_last_cam_pos) > 6.0:
		for ps: GPUParticles3D in [snowfall, blizzard, gusts]:
			ps.restart()
	_last_cam_pos = p
