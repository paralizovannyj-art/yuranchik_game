## Процедурная анимация модели Юрчика (скелет из Blender, tools/blender/build_yurchik_v3.py) — с весом и инерцией.
## Модель смотрит в +Z; узел Model повёрнут на 180°.
## Знаки (вокруг X): отрицательный — конечность вперёд, положительный — назад; Spine.x > 0 — наклон вперёд.
extends Node3D

@export var stride_walk := 2.9     ## рад фазы на метр при ходьбе
@export var stride_sprint := 2.1   ## на спринте шаг длиннее
@export var smoothing := 10.0
@export var lean_turn := 0.05      ## крен в повороте
@export var lean_accel := 0.035    ## наклон при разгоне/торможении
@export var arm_rest := 0.40       ## модель стоит в A-позе (руки в стороны) — на столько радиан опускаем руки к телу

var step_phase := 0.0             ## читает камера для покачивания

var _time := 0.0
var _attack_t := -1.0
var _bones := {}
var _pose := {}
var _pelvis_base := Vector3.ZERO
var _amp := 0.0
var _lean := Vector2.ZERO          ## x — вперёд/назад, y — крен
var _bob := 0.0

const ATTACK_LEN := 0.62


const BONE_NAMES := ["Pelvis", "Spine", "Head", "UpperArmL", "ForearmL", "UpperArmR", "ForearmR",
		"Hammer", "ThighL", "ShinL", "ThighR", "ShinR"]

## Модель со скелетом: повороты задаются в осях модели и переводятся в локальные оси кости.
var _skel: Skeleton3D
var _idx := {}
var _rest_local := {}   ## Quaternion — локальный rest кости
var _rest_global := {}  ## Quaternion — глобальный rest кости (в пространстве скелета)
var _rest_node := {}    ## Basis — rest для обычных узлов (молоток)


func _ready() -> void:
	var sk := find_children("*", "Skeleton3D", true, false)
	_skel = sk[0] if sk.size() > 0 else null
	for n in BONE_NAMES:
		var i := _skel.find_bone(n) if _skel else -1
		if i >= 0:
			_idx[n] = i
			_rest_local[n] = _skel.get_bone_rest(i).basis.get_rotation_quaternion()
			_rest_global[n] = _skel.get_bone_global_rest(i).basis.get_rotation_quaternion()
			_bones[n] = i
			_pose[n] = Vector3.ZERO
		else:
			var node := find_child(n, true, false) as Node3D
			if node:
				_bones[n] = node
				_rest_node[n] = node.basis
				_pose[n] = Vector3.ZERO
	if _idx.has("Pelvis"):
		_pelvis_base = _skel.get_bone_rest(_idx["Pelvis"]).origin
	elif _bones.has("Pelvis"):
		_pelvis_base = (_bones["Pelvis"] as Node3D).position


func play_attack() -> void:
	_attack_t = 0.0


func update_anim(delta: float, speed: float, sprint: float, state: int, yaw_rate: float, accel: float) -> void:
	_time += delta
	var spd := absf(speed)
	var target := {}
	for k in _bones:
		target[k] = Vector3.ZERO

	# фаза шага привязана к пройденному пути — ноги не «скользят»
	var stride := lerpf(stride_walk, stride_sprint, sprint)
	step_phase += delta * speed * stride
	var amp_target := clampf(spd / 2.2, 0.0, 1.0) * lerpf(0.42, 0.78, sprint)
	_amp = lerpf(_amp, amp_target, 1.0 - exp(-8.0 * delta))
	var a := _amp
	var s := sin(step_phase)
	var c := cos(step_phase)

	# ноги
	target["ThighL"] = Vector3(-s * a, 0, 0)
	target["ThighR"] = Vector3(s * a, 0, 0)
	target["ShinL"] = Vector3(maxf(0.0, sin(step_phase + 1.3)) * a * (1.5 + sprint * 0.8), 0, 0)
	target["ShinR"] = Vector3(maxf(0.0, sin(step_phase + 1.3 + PI)) * a * (1.5 + sprint * 0.8), 0, 0)
	# руки — противофазой, локти сгибаются на спринте
	target["UpperArmL"] = Vector3(s * a * 0.85, 0, 0.07 + sprint * 0.08)
	target["UpperArmR"] = Vector3(-s * a * 0.85, 0, -0.07 - sprint * 0.08)
	var elbow := lerpf(-0.25, -1.35, sprint) - a * 0.2
	target["ForearmL"] = Vector3(elbow + maxf(0.0, -s) * 0.25 * a, 0, 0)
	target["ForearmR"] = Vector3(elbow + maxf(0.0, s) * 0.25 * a, 0, 0)

	# наклоны: вперёд от скорости и разгона, крен — в поворот
	var lean_fwd := sprint * 0.18 + clampf(accel * lean_accel, -0.18, 0.2)
	var lean_roll := clampf(-yaw_rate * lean_turn * clampf(spd / 2.0, 0.0, 1.5), -0.3, 0.3)
	_lean = _lean.lerp(Vector2(lean_fwd, lean_roll), 1.0 - exp(-6.0 * delta))
	# бёдра качаются, плечи — навстречу, голова стабилизируется
	var hip_twist := s * a * 0.22
	target["Pelvis"] = Vector3(0, hip_twist, -c * a * 0.05)
	target["Spine"] = Vector3(_lean.x + absf(c) * a * 0.05, -hip_twist * 1.6, _lean.y)
	target["Head"] = Vector3(-_lean.x * 0.6, hip_twist * 0.4, -_lean.y * 0.6)

	# стойка на месте: дыхание, переминание
	var idle := 1.0 - clampf(spd / 0.4, 0.0, 1.0)
	if idle > 0.0:
		var br := sin(_time * 1.5)
		target["Spine"] += Vector3(br * 0.02, 0, 0) * idle
		target["Head"] += Vector3(0, sin(_time * 0.35) * 0.1, 0) * idle
		target["ForearmR"] += Vector3(-0.1, 0, 0) * idle
		target["Pelvis"] += Vector3(0, 0, sin(_time * 0.5) * 0.025) * idle

	# замах / удар (1 = AIM, 2 = ATTACK)
	if state == 1 or state == 2:
		target["UpperArmR"] = Vector3(-1.15, 0.0, -0.15)
		target["ForearmR"] = Vector3(-1.1, 0, 0)
		target["Hammer"] = Vector3(0.25, 0, 0)
		target["UpperArmL"] = Vector3(-0.55, 0, 0.25)
		target["ForearmL"] = Vector3(-0.7, 0, 0)
		target["Spine"] = Vector3(0.08 + _lean.x * 0.5, -0.18, _lean.y * 0.5)
		if spd < 0.2:
			target["ThighL"] = Vector3(-0.15, 0, 0)
			target["ThighR"] = Vector3(0.12, 0, 0)
			target["ShinL"] = Vector3(0.12, 0, 0)

	var instant := false
	if _attack_t >= 0.0:
		_attack_t += delta
		var t := _attack_t / ATTACK_LEN
		if t < 0.3:
			var k := t / 0.3
			k = k * (2.0 - k)
			target["UpperArmR"] = Vector3(lerpf(-1.15, -2.9, k), 0, -0.1)
			target["ForearmR"] = Vector3(lerpf(-1.1, -0.9, k), 0, 0)
			target["Spine"] = Vector3(lerpf(0.08, -0.15, k), -0.3 * k, 0)
			target["Pelvis"] = Vector3(0, -0.15 * k, 0)
		elif t < 0.48:
			var k := (t - 0.3) / 0.18
			k = k * k
			target["UpperArmR"] = Vector3(lerpf(-2.9, -0.45, k), 0, -0.05)
			target["ForearmR"] = Vector3(lerpf(-0.9, -0.1, k), 0, 0)
			target["Spine"] = Vector3(lerpf(-0.15, 0.4, k), lerpf(-0.3, 0.15, k), 0)
			target["Pelvis"] = Vector3(0, lerpf(-0.15, 0.12, k), 0)
			target["ThighL"] = Vector3(-0.35 * k, 0, 0)
			target["ShinL"] = Vector3(0.3 * k, 0, 0)
			instant = true
		elif t >= 1.0:
			_attack_t = -1.0

	# руки из A-позы — вниз, к телу (в любой позе: стойка, шаг, замах)
	if target.has("UpperArmL"):
		target["UpperArmL"] += Vector3(0, 0, -arm_rest)
	if target.has("UpperArmR"):
		target["UpperArmR"] += Vector3(0, 0, arm_rest)

	var w := 1.0 if instant else 1.0 - exp(-smoothing * delta)
	for k in _bones:
		_pose[k] = (_pose[k] as Vector3).lerp(target[k], w)
		_apply(k, _pose[k])
	# вертикальное покачивание и приседание на шаге
	_bob = lerpf(_bob, absf(c) * a * (0.045 + sprint * 0.03) - a * 0.03, 1.0 - exp(-14.0 * delta))
	if _idx.has("Pelvis"):
		_skel.set_bone_pose_position(_idx["Pelvis"], _pelvis_base + Vector3(0, _bob, 0))
	elif _bones.has("Pelvis"):
		(_bones["Pelvis"] as Node3D).position = _pelvis_base + Vector3(0, _bob, 0)


## Поворот euler (в осях модели) → поза кости. Для кости: rest_local * (G⁻¹ · R · G).
func _apply(k: String, euler: Vector3) -> void:
	var r := Quaternion.from_euler(euler)
	if _idx.has(k):
		var g: Quaternion = _rest_global[k]
		_skel.set_bone_pose_rotation(_idx[k], (_rest_local[k] as Quaternion) * (g.inverse() * r * g))
	else:
		(_bones[k] as Node3D).basis = (_rest_node[k] as Basis) * Basis(r)
