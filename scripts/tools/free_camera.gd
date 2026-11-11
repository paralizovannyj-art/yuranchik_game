## Свободная камера для осмотра сцен (только для отладки).
## ПКМ зажать — вращать; WASD — двигаться; Q/E — вниз/вверх; Shift — быстрее.
extends Camera3D

@export var speed := 4.0
@export var mouse_sensitivity := 0.003

var _yaw := 0.0
var _pitch := 0.0


func _ready() -> void:
	_yaw = rotation.y
	_pitch = rotation.x


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if event.pressed else Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_yaw -= event.relative.x * mouse_sensitivity
		_pitch = clampf(_pitch - event.relative.y * mouse_sensitivity, -1.4, 1.4)
		rotation = Vector3(_pitch, _yaw, 0.0)


func _process(delta: float) -> void:
	var dir := Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W): dir.z -= 1.0
	if Input.is_physical_key_pressed(KEY_S): dir.z += 1.0
	if Input.is_physical_key_pressed(KEY_A): dir.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D): dir.x += 1.0
	if Input.is_physical_key_pressed(KEY_Q): dir.y -= 1.0
	if Input.is_physical_key_pressed(KEY_E): dir.y += 1.0
	var mult := 3.0 if Input.is_physical_key_pressed(KEY_SHIFT) else 1.0
	translate(dir.normalized() * speed * mult * delta)
