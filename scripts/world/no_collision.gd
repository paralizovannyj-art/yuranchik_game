## Декорации без коллизии: у всех моделей внутри этого узла убираются тела столкновений.
## Нужен для того, обо что Юрчик спотыкался бы: бордюры тротуара, рельсы, провода.
extends Node3D


func _ready() -> void:
	for body in find_children("*", "StaticBody3D", true, false):
		body.queue_free()
