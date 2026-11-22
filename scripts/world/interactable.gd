## То, с чем Юрчик взаимодействует по кнопке E / A: дверь, замок, предмет.
## Ставится на уровень как обычный узел; подсказка и ключ настраиваются в инспекторе.
class_name Interactable
extends Node3D

signal interacted(player: Player)      ## сработало (ключ был или не нужен)
signal locked(player: Player)          ## игрок нажал, но нужного предмета нет

@export var prompt := "Осмотреть"      ## текст подсказки: «[E] …»
@export var radius := 1.8              ## с какого расстояния доступно, м
@export var enabled := true
@export var need_item := ""            ## id предмета-ключа (см. Game.ITEMS); пусто — не нужен
@export_multiline var locked_text := "Заперто."
@export var consume_item := false      ## забрать ключ из инвентаря после использования
@export var one_shot := false          ## после срабатывания отключается
@export_group("Куда целиться")
## Имена моделей (MeshInstance3D) в сцене уровня, в которые надо попасть прицелом. Пусто — своя модель
## (у предметов), а если её нет — невидимый куб aim_size вокруг узла.
@export var aim_meshes := PackedStringArray()
@export var aim_size := Vector3(0.4, 0.4, 0.4)  ## м — куб, по которому целимся, если моделей нет

const AIM_PAD := 0.02                  ## м — запас вокруг модели, чтобы не надо было попадать в пиксель
const AIM_MIN := 0.1                   ## м — мелкие вещи (ключ, бинт) целятся как минимум по такому кубу

var _aim: Array[MeshInstance3D] = []
var _aim_ready := false


func _ready() -> void:
	add_to_group("interactable")


## Расстояние от глаз до предмета по лучу взгляда; −1 — луч проходит мимо.
## Попасть надо в саму модель (её габаритный ящик), а не «примерно рядом».
func aim_hit(eye: Vector3, look: Vector3) -> float:
	if not _aim_ready:
		_find_aim()
	if _aim.is_empty():
		return _ray_box(eye, look, AABB(global_position - aim_size * 0.5, aim_size))
	var best := -1.0
	for m: MeshInstance3D in _aim:
		if not is_instance_valid(m) or not m.is_visible_in_tree():
			continue
		var bb := (m.global_transform * m.get_aabb()).grow(AIM_PAD)
		var grow := (Vector3.ONE * AIM_MIN - bb.size).max(Vector3.ZERO) * 0.5
		bb = AABB(bb.position - grow, bb.size + grow * 2.0)
		var t := _ray_box(eye, look, bb)
		if t >= 0.0 and (best < 0.0 or t < best):
			best = t
	return best


func _find_aim() -> void:
	_aim_ready = true
	_aim.clear()
	if not aim_meshes.is_empty():
		var root: Node = owner if owner else get_tree().current_scene
		for n: String in aim_meshes:
			var found := root.find_children(n, "MeshInstance3D", true, false)   # по имени бывает и узел-обёртка
			if not found.is_empty():
				_aim.append(found[0] as MeshInstance3D)
			else:
				push_warning("%s: модель для прицела «%s» не найдена" % [name, n])
		return
	for c: Node in find_children("*", "MeshInstance3D", true, false):
		if not c.has_meta("no_aim"):
			_aim.append(c as MeshInstance3D)


static func _ray_box(o: Vector3, d: Vector3, bb: AABB) -> float:
	var t0 := -1e9
	var t1 := 1e9
	var lo := bb.position
	var hi := bb.end
	for a in 3:
		if absf(d[a]) < 1e-6:
			if o[a] < lo[a] or o[a] > hi[a]:
				return -1.0
			continue
		var ta := (lo[a] - o[a]) / d[a]
		var tb := (hi[a] - o[a]) / d[a]
		t0 = maxf(t0, minf(ta, tb))
		t1 = minf(t1, maxf(ta, tb))
	if t0 > t1 or t1 < 0.0:
		return -1.0
	return maxf(t0, 0.0)


func interact(player: Player) -> void:
	if need_item != "" and not Game.has_item(need_item):
		Game.sfx("door_locked", global_position)
		Game.say(locked_text)
		locked.emit(player)
		return
	if consume_item and need_item != "":
		Game.remove_item(need_item)
	if one_shot:
		enabled = false
	interacted.emit(player)
