## «Восточный ж/д мост» днём (YUR-7) — сцена для катсцены: лютый зимний пасмурный день, как на дневном фото.
## Игрока нет: камера плавно едет от метки ShotFrom к метке ShotTo (их можно двигать мышью в редакторе)
## и обратно. Длительность проезда — в инспекторе (shot_time). Фонари выключены, кроме одной мачты.
extends Node3D

@export var shot_time := 14.0                    ## секунд на один проезд камеры
@export var loop := true                         ## ехать туда-обратно, пока сцена открыта

@onready var camera: Camera3D = $Camera
@onready var from: Marker3D = $ShotFrom
@onready var to: Marker3D = $ShotTo
@onready var snowfall: GPUParticles3D = $Snowfall


func _ready() -> void:
	camera.global_transform = from.global_transform
	camera.make_current()
	_fly()


func _fly() -> void:
	var a := from
	var b := to
	while true:
		var tw := create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		tw.tween_property(camera, "global_transform", b.global_transform, shot_time)
		await tw.finished
		if not loop:
			return
		var t := a
		a = b
		b = t


func _process(_delta: float) -> void:
	snowfall.global_position = camera.global_position + Vector3(0, 14, 0)
