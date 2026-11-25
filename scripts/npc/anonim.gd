## Аноним: NPC без лица (под капюшоном — чёрный провал, руки всегда в кармане-кенгуру).
## Пока — простая логика для проверки на полигоне: зацикливает Idle / Walk / Run и, когда Юрчик ближе look_range,
## медленно поворачивает к нему голову (кость Head, LookAtModifier3D с ограничением угла). Отошёл — голова
## так же медленно возвращается, и снова видны «прислушивания» из анимации Idle.
class_name Anonim
extends Node3D

@export var look_range := 9.0          ## с какого расстояния начинает смотреть на Юрчика, м
@export var look_time := 1.8           ## за сколько секунд голова доворачивается — медленно, без рывков
@export var max_turn_deg := 70.0       ## поворот головы влево-вправо, не больше
@export var max_tilt_deg := 25.0       ## наклон вверх-вниз, не больше

var _look: LookAtModifier3D
var _target: Marker3D


func _ready() -> void:
	for ap: AnimationPlayer in find_children("*", "AnimationPlayer", true, false):
		for n: StringName in ap.get_animation_list():
			if n != &"RESET":
				ap.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	var skels := find_children("*", "Skeleton3D", true, false)
	if skels.is_empty():
		return
	var skel := skels[0] as Skeleton3D
	_target = Marker3D.new()
	_target.top_level = true
	add_child(_target)
	_target.global_position = global_position + global_basis.z * 3.0 + Vector3.UP * 1.6
	_look = LookAtModifier3D.new()
	_look.bone_name = "Head"
	_look.forward_axis = SkeletonModifier3D.BONE_AXIS_PLUS_Z     # лицо (провал) смотрит вдоль +Z кости
	_look.primary_rotation_axis = Vector3.AXIS_Y
	_look.use_secondary_rotation = true
	_look.duration = look_time
	_look.transition_type = Tween.TRANS_SINE
	_look.ease_type = Tween.EASE_IN_OUT
	_look.use_angle_limitation = true
	_look.symmetry_limitation = true
	_look.primary_limit_angle = deg_to_rad(max_turn_deg) * 2.0   # полный сектор: ±max_turn_deg
	_look.primary_damp_threshold = 0.7
	_look.secondary_limit_angle = deg_to_rad(max_tilt_deg) * 2.0
	_look.secondary_damp_threshold = 0.7
	_look.influence = 0.0
	skel.add_child(_look)
	_look.target_node = _look.get_path_to(_target)


func _process(delta: float) -> void:
	if _look == null:
		return
	var player := get_tree().get_first_node_in_group("player") as Node3D
	var watching := false
	if player:
		var cam := player.get_viewport().get_camera_3d()
		var eye := cam.global_position if cam else player.global_position + Vector3.UP * 1.6
		var flat := Vector2(eye.x - global_position.x, eye.z - global_position.z)
		watching = flat.length() <= look_range
		if watching:
			_target.global_position = eye
	# плавно включаем / выключаем поворот, чтобы голова не «щёлкала» на границе дистанции
	_look.influence = move_toward(_look.influence, 1.0 if watching else 0.0, delta / look_time)
