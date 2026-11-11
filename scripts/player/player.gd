## Юрчик: современное управление от третьего лица (как в RE4 Remake / Fleshbite).
## - Камера свободно вращается мышью / правым стиком и мягко следует за героем.
## - WASD / левый стик — движение относительно камеры; герой разворачивается по ходу.
## - Shift / B — спринт. Назад + спринт — быстрый разворот вместе с камерой.
## - ПКМ / LT — замах: камера у плеча, герой смотрит туда же, можно медленно ходить и стрейфиться.
## - ЛКМ / RT — удар молотком (из замаха — прицельный, на ходу — быстрый).
## - F / Y — фонарик.
class_name Player
extends CharacterBody3D

enum State { NORMAL, AIM, ATTACK, QUICKTURN }

@export_group("Движение")
@export var walk_speed := 2.3
@export var sprint_speed := 4.8
@export var aim_walk_speed := 1.3
@export var acceleration := 12.0
@export var deceleration := 16.0
@export var turn_rate := 11.0          ## как быстро герой поворачивается по ходу движения
@export var quick_turn_time := 0.32
@export var gravity := 18.0

@export_group("Камера")
@export var mouse_sensitivity := 0.0024
@export var stick_sensitivity := 2.8   ## рад/с
@export var pitch_min := -1.0
@export var pitch_max := 0.55
@export var follow_lag := 12.0         ## чем больше — тем жёстче камера держится за героем
@export var normal_cam := Vector3(0.55, 1.65, 2.8)   ## (вправо, высота, дистанция)
@export var aim_cam := Vector3(0.62, 1.58, 1.25)
@export var normal_fov := 64.0
@export var aim_fov := 50.0

@export_group("Бой")
@export var attack_time := 0.62
@export var attack_lunge := 1.2        ## небольшой шаг вперёд при ударе

var state := State.NORMAL
var cam_yaw := 0.0
var cam_pitch := -0.18
var _timer := 0.0
var _turn_left := 0.0
var _aim_blend := 0.0
var _attack_buffer := 0.0
var _turn_buffer := 0.0

@onready var model: Node3D = $Model
@onready var cam_pivot: Node3D = $CamPivot
@onready var spring: SpringArm3D = $CamPivot/SpringArm
@onready var camera: Camera3D = $CamPivot/SpringArm/Camera
@onready var flashlight: SpotLight3D = $Flashlight


func _ready() -> void:
	cam_pivot.top_level = true
	cam_yaw = rotation.y
	cam_pivot.global_position = global_position + Vector3(0, normal_cam.y, 0)
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
		var s := mouse_sensitivity * (0.7 if state == State.AIM else 1.0)
		cam_yaw -= event.relative.x * s
		cam_pitch = clampf(cam_pitch - event.relative.y * s, pitch_min, pitch_max)


func _physics_process(delta: float) -> void:
	_attack_buffer = maxf(_attack_buffer - delta, 0.0)
	_turn_buffer = maxf(_turn_buffer - delta, 0.0)

	# правый стик
	var look := Input.get_vector("look_left", "look_right", "look_up", "look_down")
	cam_yaw -= look.x * stick_sensitivity * delta
	cam_pitch = clampf(cam_pitch - look.y * stick_sensitivity * 0.7 * delta, pitch_min, pitch_max)

	# ввод движения относительно камеры
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var cam_basis := Basis(Vector3.UP, cam_yaw)
	var wish := cam_basis * Vector3(input.x, 0.0, input.y)
	var sprinting := Input.is_action_pressed("run") and input.length() > 0.3
	var target_vel := Vector3.ZERO

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
			else:
				target_vel = wish * (sprint_speed if sprinting else walk_speed)
				if wish.length() > 0.1:
					_face(atan2(-wish.x, -wish.z), delta)
		State.AIM:
			_face(cam_yaw, delta, 2.0)
			target_vel = wish * aim_walk_speed
			if not Input.is_action_pressed("ready_weapon"):
				state = State.NORMAL
			elif _attack_buffer > 0.0:
				_attack_buffer = 0.0
				_start_attack()
		State.ATTACK:
			_timer -= delta
			var t := 1.0 - _timer / attack_time
			if t > 0.3 and t < 0.5:
				target_vel = -global_basis.z * attack_lunge
			if _timer <= 0.0:
				state = State.AIM if Input.is_action_pressed("ready_weapon") else State.NORMAL
		State.QUICKTURN:
			var step := PI / quick_turn_time * delta
			step = minf(step, _turn_left)
			_turn_left -= step
			rotation.y += step
			cam_yaw += step
			if _turn_left <= 0.001:
				state = State.NORMAL

	# разгон / торможение — ощущение веса
	var hv := Vector3(velocity.x, 0.0, velocity.z)
	var rate := acceleration if target_vel.length() > hv.length() else deceleration
	hv = hv.move_toward(target_vel, rate * delta)
	velocity.x = hv.x
	velocity.z = hv.z
	if not is_on_floor():
		velocity.y -= gravity * delta
	else:
		velocity.y = -0.5
	move_and_slide()

	# анимация: скорость со знаком (назад — отрицательная)
	var planar := Vector3(velocity.x, 0.0, velocity.z)
	var fwd_dot := planar.dot(-global_basis.z)
	var anim_speed := planar.length() * (-1.0 if fwd_dot < -0.3 * planar.length() else 1.0)
	model.update_anim(delta, anim_speed, sprinting and state == State.NORMAL, _anim_state())
	_update_camera(delta)


func _face(yaw: float, delta: float, mult := 1.0) -> void:
	rotation.y = lerp_angle(rotation.y, yaw, 1.0 - exp(-turn_rate * mult * delta))


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
	# соответствует ожиданиям yurchik_anim.gd: 0 — обычное, 1 — замах, 2 — удар
	match state:
		State.AIM: return 1
		State.ATTACK: return 2
	return 0


func _update_camera(delta: float) -> void:
	var target := 1.0 if state == State.AIM or (state == State.ATTACK and Input.is_action_pressed("ready_weapon")) else 0.0
	_aim_blend = move_toward(_aim_blend, target, delta * 5.0)
	var t := _aim_blend * _aim_blend * (3.0 - 2.0 * _aim_blend)
	var c := normal_cam.lerp(aim_cam, t)
	var goal := global_position + Vector3(0.0, c.y, 0.0)
	cam_pivot.global_position = cam_pivot.global_position.lerp(goal, 1.0 - exp(-follow_lag * delta))
	cam_pivot.rotation = Vector3(cam_pitch, cam_yaw, 0.0)
	spring.position.x = c.x
	spring.spring_length = c.z
	camera.fov = lerpf(normal_fov, aim_fov, t)
	# фонарик в замахе смотрит туда же, куда камера
	flashlight.rotation.x = lerpf(-0.1, cam_pitch + 0.05, t)
