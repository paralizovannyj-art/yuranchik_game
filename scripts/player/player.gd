## Юрчик: управление от третьего лица в духе RE4 Remake / Fleshbite — с инерцией.
## - Камера близко у правого плеча, свободная (мышь / правый стик), на «пружине».
## - Движение относительно камеры. Герой поворачивается дугой, скорость набирается и гасится плавно.
## - Shift / B — спринт. Назад + спринт — быстрый разворот вместе с камерой.
## - ПКМ / LT — замах: камера у плеча, медленная ходьба и стрейф.
## - ЛКМ / RT — удар молотком. F / Y — фонарик.
class_name Player
extends CharacterBody3D

enum State { NORMAL, AIM, ATTACK, QUICKTURN }

@export_group("Движение")
@export var walk_speed := 2.2
@export var sprint_speed := 4.6
@export var aim_walk_speed := 1.2
@export var acceleration := 5.5        ## м/с² — разгон
@export var sprint_acceleration := 3.5
@export var deceleration := 7.0        ## м/с² — торможение
@export var turn_speed := 6.5          ## рад/с — максимальная скорость поворота шагом
@export var sprint_turn_speed := 3.8   ## на спринте поворачивает шире
@export var turn_response := 9.0       ## «мягкость» доворота
@export var quick_turn_time := 0.34
@export var gravity := 18.0

@export_group("Камера")
@export var mouse_sensitivity := 0.0022
@export var stick_sensitivity := 2.6
@export var look_smoothing := 22.0     ## сглаживание обзора
@export var pitch_min := -0.9
@export var pitch_max := 0.5
@export var spring_stiffness := 55.0   ## пружина следования камеры
@export var look_ahead := 0.18         ## камера чуть «смотрит» вперёд по ходу
@export var normal_cam := Vector3(0.62, 1.55, 1.75)  ## (вправо, высота, дистанция)
@export var aim_cam := Vector3(0.58, 1.52, 0.95)
@export var normal_fov := 60.0
@export var sprint_fov_add := 6.0
@export var aim_fov := 48.0
@export var head_bob := 0.022

@export_group("Бой")
@export var attack_time := 0.62
@export var attack_lunge := 1.4

var state := State.NORMAL
var cam_yaw := 0.0
var cam_pitch := -0.12
var move_speed := 0.0

var _yaw_target := 0.0
var _pitch_target := -0.12
var _timer := 0.0
var _turn_left := 0.0
var _aim_blend := 0.0
var _sprint_blend := 0.0
var _attack_buffer := 0.0
var _turn_buffer := 0.0
var _prev_yaw := 0.0
var _yaw_rate := 0.0
var _prev_speed := 0.0
var _cam_pos := Vector3.ZERO
var _cam_vel := Vector3.ZERO

@onready var model: Node3D = $Model
@onready var cam_pivot: Node3D = $CamPivot
@onready var spring: SpringArm3D = $CamPivot/SpringArm
@onready var camera: Camera3D = $CamPivot/SpringArm/Camera
@onready var flashlight: SpotLight3D = $Flashlight


func _ready() -> void:
	cam_pivot.top_level = true
	cam_yaw = rotation.y
	_yaw_target = cam_yaw
	_prev_yaw = rotation.y
	_cam_pos = global_position + Vector3(0, normal_cam.y, 0)
	cam_pivot.global_position = _cam_pos
	spring.add_excluded_object(get_rid())
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		return
	if event.is_action_pressed("pause"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if event.is_action_pressed("attack"):
		_attack_buffer = 0.2
	if event.is_action_pressed("run") and Input.is_action_pressed("move_back"):
		_turn_buffer = 0.15
	if event.is_action_pressed("flashlight"):
		flashlight.visible = not flashlight.visible
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var s := mouse_sensitivity * (0.65 if state == State.AIM else 1.0)
		_yaw_target -= event.relative.x * s
		_pitch_target = clampf(_pitch_target - event.relative.y * s, pitch_min, pitch_max)


func _physics_process(delta: float) -> void:
	_attack_buffer = maxf(_attack_buffer - delta, 0.0)
	_turn_buffer = maxf(_turn_buffer - delta, 0.0)

	var look := Input.get_vector("look_left", "look_right", "look_up", "look_down")
	_yaw_target -= look.x * stick_sensitivity * delta
	_pitch_target = clampf(_pitch_target - look.y * stick_sensitivity * 0.7 * delta, pitch_min, pitch_max)
	var ls := 1.0 - exp(-look_smoothing * delta)
	cam_yaw = lerp_angle(cam_yaw, _yaw_target, ls)
	cam_pitch = lerpf(cam_pitch, _pitch_target, ls)

	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var wish := Basis(Vector3.UP, cam_yaw) * Vector3(input.x, 0.0, input.y)
	var amount := minf(input.length(), 1.0)
	var sprinting := Input.is_action_pressed("run") and amount > 0.3 and state == State.NORMAL
	var hv := Vector3(velocity.x, 0.0, velocity.z)

	match state:
		State.NORMAL:
			if Input.is_action_pressed("ready_weapon"):
				state = State.AIM
			elif _turn_buffer > 0.0:
				_turn_buffer = 0.0
				_start_quick_turn()
			elif _attack_buffer > 0.0:
				_attack_buffer = 0.0
				_start_attack()
			hv = _locomotion(delta, wish, amount, sprinting)
		State.AIM:
			_face_towards(cam_yaw, delta, 12.0, 9.0)
			var target := wish * aim_walk_speed
			hv = hv.move_toward(target, (acceleration if target.length() > hv.length() else deceleration) * delta)
			move_speed = hv.length()
			if not Input.is_action_pressed("ready_weapon"):
				state = State.NORMAL
			elif _attack_buffer > 0.0:
				_attack_buffer = 0.0
				_start_attack()
		State.ATTACK:
			_timer -= delta
			var t := 1.0 - _timer / attack_time
			var target_speed := attack_lunge if (t > 0.3 and t < 0.5) else 0.0
			move_speed = move_toward(move_speed, target_speed, 12.0 * delta)
			hv = -global_basis.z * move_speed
			if _timer <= 0.0:
				state = State.AIM if Input.is_action_pressed("ready_weapon") else State.NORMAL
		State.QUICKTURN:
			var step := minf(PI / quick_turn_time * delta, _turn_left)
			_turn_left -= step
			rotation.y += step
			cam_yaw += step
			_yaw_target += step
			move_speed = move_toward(move_speed, 0.0, deceleration * 2.0 * delta)
			hv = -global_basis.z * move_speed
			if _turn_left <= 0.001:
				state = State.NORMAL

	velocity.x = hv.x
	velocity.z = hv.z
	if not is_on_floor():
		velocity.y -= gravity * delta
	else:
		velocity.y = -0.5
	move_and_slide()
	# если упёрлись в стену — скорость тоже гаснет
	move_speed = minf(move_speed, Vector3(velocity.x, 0, velocity.z).length() + 0.05)

	# параметры для анимации: угловая скорость и ускорение
	_yaw_rate = lerpf(_yaw_rate, wrapf(rotation.y - _prev_yaw, -PI, PI) / delta, 1.0 - exp(-10.0 * delta))
	_prev_yaw = rotation.y
	var accel := (move_speed - _prev_speed) / delta
	_prev_speed = move_speed
	var planar := Vector3(velocity.x, 0.0, velocity.z)
	var signed := planar.length() * (-1.0 if planar.dot(-global_basis.z) < -0.3 * planar.length() else 1.0)
	_sprint_blend = move_toward(_sprint_blend, 1.0 if sprinting and move_speed > walk_speed else 0.0, delta * 3.0)
	model.update_anim(delta, signed, _sprint_blend, _anim_state(), _yaw_rate, accel)
	_update_camera(delta)


## Обычная ходьба: поворот дугой с ограниченной скоростью, скорость с инерцией.
func _locomotion(delta: float, wish: Vector3, amount: float, sprinting: bool) -> Vector3:
	var target_speed := 0.0
	if amount > 0.1 and state == State.NORMAL:
		var target_yaw := atan2(-wish.x, -wish.z)
		var diff := wrapf(target_yaw - rotation.y, -PI, PI)
		var max_turn := sprint_turn_speed if sprinting else turn_speed
		if move_speed < 0.6:
			max_turn *= 1.6  # с места разворачивается охотнее
		_face_towards(target_yaw, delta, turn_response, max_turn)
		target_speed = (sprint_speed if sprinting else walk_speed) * amount
		# чем круче поворот — тем сильнее сбрасываем скорость
		target_speed *= lerpf(1.0, 0.25, clampf((absf(diff) - 0.4) / 2.2, 0.0, 1.0))
	var rate := deceleration
	if target_speed > move_speed:
		rate = sprint_acceleration if sprinting and move_speed > walk_speed * 0.9 else acceleration
	move_speed = move_toward(move_speed, target_speed, rate * delta)
	return -global_basis.z * move_speed


func _face_towards(yaw: float, delta: float, response: float, max_rate: float) -> void:
	var diff := wrapf(yaw - rotation.y, -PI, PI)
	var step := diff * (1.0 - exp(-response * delta))
	var limit := max_rate * delta
	rotation.y += clampf(step, -limit, limit)


func _start_attack() -> void:
	state = State.ATTACK
	_timer = attack_time
	if Input.is_action_pressed("ready_weapon"):
		rotation.y = cam_yaw
	model.play_attack()


func _start_quick_turn() -> void:
	state = State.QUICKTURN
	_turn_left = PI


func _anim_state() -> int:
	match state:
		State.AIM: return 1
		State.ATTACK: return 2
	return 0


func _update_camera(delta: float) -> void:
	var aiming := state == State.AIM or (state == State.ATTACK and Input.is_action_pressed("ready_weapon"))
	_aim_blend = move_toward(_aim_blend, 1.0 if aiming else 0.0, delta * 4.5)
	var t := _aim_blend * _aim_blend * (3.0 - 2.0 * _aim_blend)
	var c := normal_cam.lerp(aim_cam, t)

	# покачивание от шагов
	var phase: float = model.get("step_phase")
	var bob_amt := clampf(move_speed / walk_speed, 0.0, 1.6) * head_bob * (1.0 - t * 0.7)
	var bob := Vector3(cos(phase) * bob_amt * 0.5, absf(sin(phase)) * bob_amt, 0.0)

	# камера-пружина (критически демпфированная) + небольшой вынос вперёд по ходу
	var goal := global_position + Vector3(0.0, c.y, 0.0) + (-global_basis.z) * move_speed * look_ahead * (1.0 - t)
	var k := spring_stiffness * (2.2 if aiming else 1.0)
	var damp := 2.0 * sqrt(k)
	_cam_vel += ((goal - _cam_pos) * k - _cam_vel * damp) * delta
	_cam_pos += _cam_vel * delta
	cam_pivot.global_position = _cam_pos + Basis(Vector3.UP, cam_yaw) * bob
	cam_pivot.rotation = Vector3(cam_pitch, cam_yaw, -_yaw_rate * 0.004 * move_speed)
	spring.position.x = c.x
	spring.spring_length = c.z
	camera.fov = lerpf(normal_fov + sprint_fov_add * _sprint_blend, aim_fov, t)
	flashlight.rotation.x = lerpf(-0.1, cam_pitch + 0.05, t)
