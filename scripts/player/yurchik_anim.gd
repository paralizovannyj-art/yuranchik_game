## Процедурная анимация временной модели Юрчика (сегментированный манекен).
## Модель смотрит в +Z (как экспортирована из Blender); узел Model повёрнут на 180°.
## Знаки поворотов (вокруг X): отрицательный — конечность вперёд, положительный — назад.
extends Node3D

@export var stride := 3.4        ## скорость фазы шага на м/с
@export var smoothing := 12.0

var _phase := 0.0
var _time := 0.0
var _attack_t := -1.0
var _bones := {}
var _pose := {}
var _pelvis_base := Vector3.ZERO

const ATTACK_LEN := 0.62


func _ready() -> void:
	for n in ["Pelvis", "Spine", "Head", "UpperArmL", "ForearmL", "UpperArmR", "ForearmR",
			"Hammer", "ThighL", "ShinL", "ThighR", "ShinR"]:
		var node := find_child(n, true, false) as Node3D
		if node:
			_bones[n] = node
			_pose[n] = Vector3.ZERO
	if _bones.has("Pelvis"):
		_pelvis_base = _bones["Pelvis"].position


func play_attack() -> void:
	_attack_t = 0.0


func update_anim(delta: float, speed: float, running: bool, state: int) -> void:
	_time += delta
	var target := {}
	for k in _bones:
		target[k] = Vector3.ZERO
	var bob := 0.0
	var moving := absf(speed) > 0.05

	if moving:
		_phase += delta * speed * stride / (1.35 if running else 1.0)
		var a := clampf(absf(speed) / 1.7, 0.0, 1.0) * (0.75 if running else 0.45)
		var s := sin(_phase)
		target["ThighL"] = Vector3(-s * a, 0, 0)
		target["ThighR"] = Vector3(s * a, 0, 0)
		target["ShinL"] = Vector3(maxf(0.0, sin(_phase + 1.3)) * a * 1.6, 0, 0)
		target["ShinR"] = Vector3(maxf(0.0, sin(_phase + 1.3 + PI)) * a * 1.6, 0, 0)
		target["UpperArmL"] = Vector3(s * a * 0.8, 0, 0.08)
		target["UpperArmR"] = Vector3(-s * a * 0.8, 0, -0.08)
		var elbow := -1.25 if running else -0.3
		target["ForearmL"] = Vector3(elbow, 0, 0)
		target["ForearmR"] = Vector3(elbow, 0, 0)
		target["Spine"] = Vector3(0.2 if running else 0.04, s * 0.06, 0)
		bob = absf(cos(_phase)) * (0.05 if running else 0.025)
	else:
		var br := sin(_time * 1.6)
		target["Spine"] = Vector3(br * 0.015, 0, 0)
		target["UpperArmL"] = Vector3(0, 0, 0.06)
		target["UpperArmR"] = Vector3(0, 0, -0.06)
		target["ForearmL"] = Vector3(-0.12, 0, 0)
		target["ForearmR"] = Vector3(-0.2, 0, 0)
		target["Head"] = Vector3(0, sin(_time * 0.4) * 0.08, 0)

	# 1 = READY, 2 = ATTACK (см. Player.State)
	if state == 1 or state == 2:
		target["UpperArmR"] = Vector3(-1.15, 0.0, -0.15)
		target["ForearmR"] = Vector3(-1.1, 0, 0)
		target["Hammer"] = Vector3(0.25, 0, 0)
		target["UpperArmL"] = Vector3(-0.55, 0, 0.25)
		target["ForearmL"] = Vector3(-0.7, 0, 0)
		target["Spine"] = Vector3(0.08, -0.15, 0)
		if not moving:
			target["ThighL"] = Vector3(-0.15, 0, 0)
			target["ThighR"] = Vector3(0.12, 0, 0)
			target["ShinL"] = Vector3(0.12, 0, 0)

	var instant := false
	if _attack_t >= 0.0:
		_attack_t += delta
		var t := _attack_t / ATTACK_LEN
		if t < 0.3:  # замах над головой
			var k := t / 0.3
			target["UpperArmR"] = Vector3(lerpf(-1.15, -2.9, k), 0, -0.1)
			target["ForearmR"] = Vector3(lerpf(-1.1, -0.9, k), 0, 0)
			target["Spine"] = Vector3(lerpf(0.08, -0.12, k), -0.25, 0)
		elif t < 0.5:  # удар вниз-вперёд
			var k := (t - 0.3) / 0.2
			k = k * k
			target["UpperArmR"] = Vector3(lerpf(-2.9, -0.5, k), 0, -0.05)
			target["ForearmR"] = Vector3(lerpf(-0.9, -0.15, k), 0, 0)
			target["Spine"] = Vector3(lerpf(-0.12, 0.35, k), lerpf(-0.25, 0.1, k), 0)
			instant = true
		elif t < 1.0:  # возврат
			pass
		else:
			_attack_t = -1.0

	var w := 1.0 if instant else clampf(delta * smoothing, 0.0, 1.0)
	for k in _bones:
		_pose[k] = (_pose[k] as Vector3).lerp(target[k], w)
		(_bones[k] as Node3D).rotation = _pose[k]
	if _bones.has("Pelvis"):
		_bones["Pelvis"].position = _pelvis_base + Vector3(0, bob, 0)
