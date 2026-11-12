## Процедурный наклон корпуса поверх анимаций: крен в поворотах, наклон при разгоне/торможении,
## лёгкое дыхание. Работает после AnimationTree (SkeletonModifier3D — дочерний узел Skeleton3D).
## Углы задаются в осях модели: x > 0 — наклон вперёд, z — крен.
class_name YurchikLean
extends SkeletonModifier3D

var spine := Vector3.ZERO

var _bone := -1


func _ready() -> void:
	var sk := get_skeleton()
	if sk:
		_bone = sk.find_bone("Spine")


func _process_modification_with_delta(_delta: float) -> void:
	var sk := get_skeleton()
	if sk == null or _bone < 0 or spine.is_zero_approx():
		return
	# поворот в осях скелета: local' = P⁻¹ · R · P · local, где P — глобальная поза родителя
	var parent := sk.get_bone_parent(_bone)
	var p := sk.get_bone_global_pose(parent).basis.orthonormalized() if parent >= 0 else Basis()
	var local := Basis(sk.get_bone_pose_rotation(_bone))
	var r := Basis.from_euler(spine)
	sk.set_bone_pose_rotation(_bone, (p.inverse() * r * p * local).get_rotation_quaternion())
