## Дверь, которую Юрчик открывает и закрывает кнопкой E / A.
## Сам узел — точка взаимодействия (ставьте у ручки, на высоте ~1 м). Дочерний узел Hinge стоит на оси петель:
## в нём модель створки и её коллизия (AnimatableBody3D), и он поворачивается вокруг вертикали.
## Можно запереть: need_item / locked_text из Interactable работают как обычно.
class_name Door
extends Interactable

signal opened
signal closed

@export var open_angle := 95.0          ## на сколько градусов открывается; знак — в какую сторону
@export var start_open := false         ## открыта ли при старте уровня
@export var open_time := 0.8            ## сколько секунд открывается
@export var close_time := 0.5           ## сколько секунд закрывается (с хлопком в конце)
@export var open_prompt := "Открыть дверь"
@export var close_prompt := "Закрыть дверь"
@export var open_sound := "door_open"
@export var close_sound := "door_close"

var is_open := false
var _hinge: Node3D
var _base_yaw := 0.0
var _tween: Tween
var _shapes: Array[CollisionShape3D] = []   ## коллизия створки: только у закрытой двери, открытая не мешает пройти


func _ready() -> void:
	super()
	_hinge = get_node_or_null("Hinge") as Node3D
	if _hinge:
		_base_yaw = _hinge.rotation.y
		for n: Node in _hinge.find_children("*", "CollisionShape3D", true, false):
			_shapes.append(n as CollisionShape3D)
	interacted.connect(_on_interacted)
	set_open(start_open, false)


func _on_interacted(player: Player) -> void:
	if player:
		player.busy(0.35, "Interact")
	set_open(not is_open)


## Открыть или закрыть. animate = false — сразу, без звука (для старта уровня и катсцен).
func set_open(value: bool, animate := true) -> void:
	is_open = value
	prompt = close_prompt if value else open_prompt
	if _hinge == null:
		return
	var target := _base_yaw + (deg_to_rad(open_angle) if value else 0.0)
	if _tween:
		_tween.kill()
	if not animate:
		_hinge.rotation.y = target
		_set_solid(not value)
		return
	if value:
		_set_solid(false)                          # открывается — сразу проходима и не толкает Юрчика
		Game.sfx(open_sound, global_position)
		_tween = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		_tween.tween_property(_hinge, "rotation:y", target, open_time)
		opened.emit()
	else:
		_tween = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		_tween.tween_property(_hinge, "rotation:y", target, close_time)
		_tween.tween_callback(func() -> void: Game.sfx(close_sound, global_position))
		_tween.tween_callback(_set_solid.bind(true))    # закрылась — снова твёрдая
		_tween.tween_callback(closed.emit)


func _set_solid(on: bool) -> void:
	for s: CollisionShape3D in _shapes:
		s.set_deferred("disabled", not on)
