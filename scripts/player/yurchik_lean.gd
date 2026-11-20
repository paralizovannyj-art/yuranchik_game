## Процедурные правки позы поверх анимаций: крен в поворотах, наклон при разгоне/торможении,
## лёгкое дыхание, разворот ног по направлению движения (бег и шаг по диагонали) и присед.
## Работает после AnimationTree (SkeletonModifier3D — дочерний узел Skeleton3D).
## Углы задаются в осях модели: x > 0 — наклон вперёд, z — крен.
class_name YurchikLean
extends SkeletonModifier3D

var spine := Vector3.ZERO
## Разворот таза (а с ним и ног) вокруг вертикали, рад. Корпус возвращается назад на долю
## spine_counter — плечи и голова смотрят почти туда же, куда камера.
var hips_yaw := 0.0
var spine_counter := 0.8
## Присед 0..1: бёдра вперёд, голени назад, таз опускается так, чтобы ступни остались на земле.
var crouch := 0.0
var crouch_knee := 68.0              ## ° — наклон бедра при полном приседе
var knee_sign := -1.0                ## направление сгиба (подобрано под оси скелета Юрчика)

var _pelvis := -1
var _spine := -1
var _legs: Array[PackedInt32Array] = []   # [бедро, голень, ступня] для каждой ноги
var _leg_len := 0.9                       # бедро + голень, м


func _ready() -> void:
	var sk := get_skeleton()
	if sk:
		_pelvis = sk.find_bone("Pelvis")
		_spine = sk.find_bone("Spine")
		for side: String in ["L", "R"]:
			var leg := PackedInt32Array([sk.find_bone("Thigh" + side), sk.find_bone("Shin" + side), sk.find_bone("Foot" + side)])
			if leg[0] >= 0 and leg[1] >= 0 and leg[2] >= 0:
				_legs.append(leg)
		if not _legs.is_empty():
			var l := _legs[0]
			_leg_len = sk.get_bone_rest(l[1]).origin.length() + sk.get_bone_rest(l[2]).origin.length()


func _process_modification_with_delta(_delta: float) -> void:
	var sk := get_skeleton()
	if sk == null or _spine < 0:
		return
	if not (spine.is_zero_approx() and is_zero_approx(hips_yaw)):
		_lean(sk)
	if crouch > 0.001:
		_crouch(sk)


func _lean(sk: Skeleton3D) -> void:
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


## Повернуть кость в осях скелета (поверх уже правленых родителей).
func _rotate_global(sk: Skeleton3D, bone: int, r: Basis) -> void:
	var parent := sk.get_bone_parent(bone)
	var p := sk.get_bone_global_pose(parent).basis.orthonormalized() if parent >= 0 else Basis()
	var g := p * Basis(sk.get_bone_pose_rotation(bone))
	sk.set_bone_pose_rotation(bone, (p.inverse() * r * g).get_rotation_quaternion())


func _crouch(sk: Skeleton3D) -> void:
	var a := deg_to_rad(crouch_knee) * crouch
	var axis := Basis(Vector3.UP, hips_yaw) * Vector3.RIGHT   # ось колена — поперёк таза
	# бедро вперёд на a, голень назад на a (относительно вертикали) — ступня остаётся под тазом
	for leg: PackedInt32Array in _legs:
		_rotate_global(sk, leg[0], Basis(axis, knee_sign * a))
		_rotate_global(sk, leg[1], Basis(axis, -knee_sign * 2.0 * a))
		_rotate_global(sk, leg[2], Basis(axis, knee_sign * a))
	if _pelvis >= 0 and sk.get_bone_parent(_pelvis) < 0:
		var drop := _leg_len * (1.0 - cos(a))
		sk.set_bone_pose_position(_pelvis, sk.get_bone_pose_position(_pelvis) - Vector3.UP * drop)
