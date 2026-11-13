## Процедурные правки позы поверх анимаций: крен в поворотах, наклон при разгоне/торможении,
## лёгкое дыхание и разворот ног по направлению движения (бег и шаг по диагонали).
## Работает после AnimationTree (SkeletonModifier3D — дочерний узел Skeleton3D).
## Углы задаются в осях модели: x > 0 — наклон вперёд, z — крен.
class_name YurchikLean
extends SkeletonModifier3D

var spine := Vector3.ZERO
## Разворот таза (а с ним и ног) вокруг вертикали, рад. Корпус возвращается назад на долю
## spine_counter — плечи и голова смотрят почти туда же, куда камера.
var hips_yaw := 0.0
var spine_counter := 0.8

var _pelvis := -1
var _spine := -1


func _ready() -> void:
	var sk := get_skeleton()
	if sk:
		_pelvis = sk.find_bone("Pelvis")
		_spine = sk.find_bone("Spine")


func _process_modification_with_delta(_delta: float) -> void:
	var sk := get_skeleton()
	if sk == null or _spine < 0 or (spine.is_zero_approx() and is_zero_approx(hips_yaw)):
		return
	# P — глобальная поза родителя корпуса (таза) до правки, P2 — после
	var parent := sk.get_bone_parent(_spine)
	var p := sk.get_bone_global_pose(parent).basis.orthonormalized() if parent >= 0 else Basis()
	var p2 := p
	if not is_zero_approx(hips_yaw) and _pelvis >= 0 and _pelvis == parent and sk.get_bone_parent(_pelvis) < 0:
		var ry := Basis(Vector3.UP, hips_yaw)
		sk.set_bone_pose_rotation(_pelvis, (ry * Basis(sk.get_bone_pose_rotation(_pelvis))).get_rotation_quaternion())
		p2 = ry * p
	# корпус: global' = R · Ry(остаток разворота) · global, т.е. local' = P2⁻¹ · R · Ry · P · local
	var local := Basis(sk.get_bone_pose_rotation(_spine))
	var r := Basis.from_euler(spine) * Basis(Vector3.UP, hips_yaw * (1.0 - spine_counter))
	sk.set_bone_pose_rotation(_spine, (p2.inverse() * r * p * local).get_rotation_quaternion())
