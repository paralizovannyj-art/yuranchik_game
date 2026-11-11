## Юрчик: управление как в оригинальном Resident Evil 4.
## - «Танковое» движение: вперёд/назад + поворот на месте (A/D или стик, мышь тоже поворачивает).
## - Бег только вперёд. Быстрый разворот: назад + бег.
## - Замах (ПКМ / LT): стоим на месте, камера ближе к плечу, удар ЛКМ / RT.
## - Фонарик: F / Y.
class_name Player
extends CharacterBody3D

enum State { NORMAL, READY, ATTACK, QUICKTURN }

@export_group("Движение")
@export var walk_speed := 1.7
@export var run_speed := 4.2
@export var back_speed := 1.1
@export var turn_speed := 2.6          ## рад/с при ходьбе
@export var ready_turn_speed := 1.6    ## рад/с в режиме замаха
@export var quick_turn_time := 0.38
@export var gravity := 18.0

@export_group("Мышь и камера")
@export var mouse_turn := 0.0022
@export var mouse_pitch := 0.0018
@export var normal_cam := Vector3(0.8, 1.7, 2.6)   ## (вправо, высота, дистанция)
@export var ready_cam := Vector3(0.72, 1.6, 1.35)
@export var normal_fov := 62.0
@export var ready_fov := 52.0
@export var pitch_limit := 0.5

@export_group("Бой")
@export var attack_time := 0.62

var state := State.NORMAL
var pitch := -0.08
var _timer := 0.0
var _turn_from := 0.0
var _cam_blend := 0.0
var _attack_buffer := 0.0   ## буфер ввода: нажатие помнится 0.2 с
var _turn_buffer := 0.0

@onready var model: Node3D = $Model
@onready var cam_pivot: Node3D = $CamPivot
@onready var spring: SpringArm3D = $CamPivot/SpringArm
@onready var camera: Camera3D = $CamPivot/SpringArm/Camera
@onready var flashlight: SpotLight3D = $Flashlight


func _ready() -> void:
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
		if state != State.QUICKTURN and state != State.ATTACK:
			rotate_y(-event.relative.x * mouse_turn)
		pitch = clampf(pitch - event.relative.y * mouse_pitch, -pitch_limit, pitch_limit * 0.6)


func _physics_process(delta: float) -> void:
	var fwd := Input.get_action_strength("move_forward") - Input.get_action_strength("move_back")
	var turn := Input.get_action_strength("turn_left") - Input.get_action_strength("turn_right")
	var running := Input.is_action_pressed("run")
	var speed := 0.0
	_attack_buffer = maxf(_attack_buffer - delta, 0.0)
	_turn_buffer = maxf(_turn_buffer - delta, 0.0)

	match state:
		State.NORMAL:
			if Input.is_action_pressed("ready_weapon"):
				state = State.READY
			elif _turn_buffer > 0.0:
				_turn_buffer = 0.0
				_start_quick_turn()
			else:
				rotate_y(turn * turn_speed * delta)
				if fwd > 0.05:
					speed = fwd * (run_speed if running else walk_speed)
				elif fwd < -0.05:
					speed = fwd * back_speed
		State.READY:
			rotate_y(turn * ready_turn_speed * delta)
			if not Input.is_action_pressed("ready_weapon"):
				state = State.NORMAL
			elif _attack_buffer > 0.0:
				_attack_buffer = 0.0
				state = State.ATTACK
				_timer = attack_time
				model.play_attack()
		State.ATTACK:
			_timer -= delta
			if _timer <= 0.0:
				state = State.READY if Input.is_action_pressed("ready_weapon") else State.NORMAL
		State.QUICKTURN:
			_timer -= delta
			var t := 1.0 - clampf(_timer / quick_turn_time, 0.0, 1.0)
			rotation.y = _turn_from + PI * (t * t * (3.0 - 2.0 * t))
			if _timer <= 0.0:
				state = State.NORMAL

	var dir := -global_basis.z
	velocity.x = dir.x * speed
	velocity.z = dir.z * speed
	if not is_on_floor():
		velocity.y -= gravity * delta
	else:
		velocity.y = -0.5
	move_and_slide()

	var actual := Vector2(velocity.x, velocity.z).length() * signf(speed)
	model.update_anim(delta, actual, running and speed > 0.0, state)
	_update_camera(delta)


func _start_quick_turn() -> void:
	state = State.QUICKTURN
	_timer = quick_turn_time
	_turn_from = rotation.y


func _update_camera(delta: float) -> void:
	var target := 1.0 if state == State.READY or state == State.ATTACK else 0.0
	_cam_blend = move_toward(_cam_blend, target, delta * 5.0)
	var t := _cam_blend * _cam_blend * (3.0 - 2.0 * _cam_blend)
	var c := normal_cam.lerp(ready_cam, t)
	cam_pivot.position = Vector3(0.0, c.y, 0.0)
	cam_pivot.rotation.x = pitch
	spring.position.x = c.x
	spring.spring_length = c.z
	camera.fov = lerpf(normal_fov, ready_fov, t)
