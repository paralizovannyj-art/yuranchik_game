## Отражённый свет-заменитель для режима «Слабый ПК» (OpenGL): там нет VoxelGI, и без него в комнате
## освещено только то, куда лампа светит напрямую. Слабая мягкая заливка без теней и бликов — то, что в жизни
## дают стены и потолок, отражая свет лампы. Вешает scripts/core/graphics.gd дочерним узлом на каждую лампу
## внутри объёма VoxelGI. Повторяет яркость (выключатель, мигание), цвет и маску своей лампы.
extends OmniLight3D

@export_range(0.0, 1.0) var share := 0.2   ## доля яркости лампы (подобрано по VoxelGI в комнате: стены +50–70%)


func _process(_delta: float) -> void:
	var src := get_parent() as Light3D
	if src == null:
		return
	light_energy = src.light_energy * share
	light_color = src.light_color
	light_cull_mask = src.light_cull_mask
