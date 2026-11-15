## Дверь, которую Юрчик открывает и закрывает кнопкой E / A — надо навестись прицелом на саму створку.
## Сам узел — середина проёма (на высоте ~1 м): оттуда звучит дверь. Дочерний узел Hinge стоит на оси петель:
## в нём модель створки и её коллизия (AnimatableBody3D + CollisionShape3D с BoxShape3D), он поворачивается
## вокруг вертикали. Коллизия есть всегда — и у закрытой, и у открытой двери.
## Открывается от Юрчика: толкает с одной стороны — створка уходит на другую (если both_ways).
## Можно запереть: need_item / locked_text из Interactable работают как обычно.
class_name Door
extends Interactable

signal opened
signal closed

@export var open_angle := 85.0          ## на сколько градусов открывается; знак — сторона по умолчанию
@export var both_ways := true           ## открывать от игрока (в любую сторону), иначе — всегда по знаку open_angle
@export var start_open := false         ## открыта ли при старте уровня
@export var open_time := 0.8            ## сколько секунд открывается
@export var close_time := 0.5           ## сколько секунд закрывается (с хлопком в конце)
@export var reach := 2.2                ## с какого расстояния от глаз (по прицелу до створки) можно открыть, м
@export var open_prompt := "Открыть дверь"
@export var close_prompt := "Закрыть дверь"
@export var open_sound := "door_open"
@export var close_sound := "door_close"

var is_open := false
var _hinge: Node3D
var _base_yaw := 0.0
var _tween: Tween
var _box: CollisionShape3D              ## коробка створки: по ней проверяем, смотрит ли игрок на дверь
var _body: AnimatableBody3D             ## коллизия створки: следует за Hinge (см. _physics_process)


func _physics_process(_delta: float) -> void:
	if _body and _hinge and _body.get_parent() == self and not _body.global_transform.is_equal_approx(_hinge.global_transform):
		_body.global_transform = _hinge.global_transform


func _ready() -> void:
	super()
	_hinge = get_node_or_null("Hinge") as Node3D
	if _hinge:
		_base_yaw = _hinge.rotation.y
		for n: Node in _hinge.find_children("*", "CollisionShape3D", true, false):
			if (n as CollisionShape3D).shape is BoxShape3D:
				_box = n as CollisionShape3D
				break
		# Тело створки не может просто поворачиваться вместе с Hinge: физика не замечает поворот родителя,
		# и коллизия остаётся в проёме. Поэтому выносим его из Hinge и каждый физический кадр ставим туда, где Hinge.
		var body := _hinge.find_children("*", "AnimatableBody3D", true, false)
		if not body.is_empty():
			_body = body[0] as AnimatableBody3D
			_body.reparent.call_deferred(self, true)
	interacted.connect(_on_interacted)
	set_open(start_open, false)


func _on_interacted(player: Player) -> void:
	if player:
		player.busy(0.35, "Interact")
	if is_open:
		set_open(false)
	else:
		set_open(true, true, _away_from(player.global_position) if player else 0)


## Куда открывать, чтобы створка ушла от игрока: +1 / −1 — знак угла поворота, 0 — по умолчанию.
func _away_from(pos: Vector3) -> int:
	if not both_ways or _hinge == null:
		return 0
	# закрытая створка лежит в плоскости петель; положительный поворот уводит её в сторону −X петель
	var parent_xf: Transform3D = (_hinge.get_parent() as Node3D).global_transform
	var closed_xf: Transform3D = parent_xf * Transform3D(Basis(Vector3.UP, _base_yaw), _hinge.position)
	var local: Vector3 = closed_xf.affine_inverse() * pos
	return 1 if local.x > 0.0 else -1


## Расстояние от глаз до створки по лучу взгляда; −1 — луч мимо или дальше reach.
func aim_hit(eye: Vector3, look: Vector3) -> float:
	if _box == null:
		return -1.0
	var inv := _box.global_transform.affine_inverse()
	var o := inv * eye
	var d := inv.basis * look
	var half: Vector3 = (_box.shape as BoxShape3D).size * 0.5
	var t0 := -1e9
	var t1 := 1e9
	for a in 3:
		if absf(d[a]) < 1e-6:
			if absf(o[a]) > half[a]:
				return -1.0
			continue
		var ta := (-half[a] - o[a]) / d[a]
		var tb := (half[a] - o[a]) / d[a]
		t0 = maxf(t0, minf(ta, tb))
		t1 = minf(t1, maxf(ta, tb))
	if t0 > t1 or t1 < 0.0:
		return -1.0
	var t := maxf(t0, 0.0)
	return t if t <= reach else -1.0


## Открыть или закрыть. animate = false — сразу, без звука (для старта уровня и катсцен).
## dir — в какую сторону открывать (+1 / −1), 0 — по знаку open_angle.
func set_open(value: bool, animate := true, dir := 0) -> void:
	is_open = value
	prompt = close_prompt if value else open_prompt
	if _hinge == null:
		return
	var ang := absf(open_angle) * float(dir) if dir != 0 else open_angle
	var target := _base_yaw + (deg_to_rad(ang) if value else 0.0)
	if _tween:
		_tween.kill()
	if not animate:
		_hinge.rotation.y = target
		return
	if value:
		Game.sfx(open_sound, global_position)
		_tween = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		_tween.tween_property(_hinge, "rotation:y", target, open_time)
		opened.emit()
	else:
		_tween = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		_tween.tween_property(_hinge, "rotation:y", target, close_time)
		_tween.tween_callback(func() -> void: Game.sfx(close_sound, global_position))
		_tween.tween_callback(closed.emit)
