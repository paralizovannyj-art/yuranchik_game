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


func _ready() -> void:
	add_to_group("interactable")


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
