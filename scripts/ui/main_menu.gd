## Главное меню: ночной район «Паскот» на фоне (камера медленно покачивается над двором Юрчика), название и три кнопки.
extends Node3D

const BACKDROP := "res://scenes/levels/district.tscn"
const ORBIT_CENTER := Vector3(-5.0, 3.0, -55.0)   ## двор Юрчика (точка телепорта F1), над ним идёт снег

var _cam: Camera3D
var _t := 0.0
var _help: Label


func _ready() -> void:
	Game.in_game = false
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var yard := (load(BACKDROP) as PackedScene).instantiate()
	var pl := yard.get_node_or_null("Player")
	if pl:                                                           # герой в меню не нужен
		yard.remove_child(pl)
		pl.free()
	yard.set_script(null)                                            # и сценарий уровня тоже: он создал бы HUD игры
	add_child(yard)
	_cam = Camera3D.new()
	_cam.fov = 55.0
	add_child(_cam)
	_cam.make_current()
	Game.ambience("amb_wind", -12.0)
	Game.music("mus_drone", -9.0)

	var layer := CanvasLayer.new()
	layer.layer = 20
	add_child(layer)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = HUD.make_theme()
	layer.add_child(root)
	var shade := ColorRect.new()
	shade.color = Color(0, 0, 0, 0.35)
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(shade)
	HUD.mk_label(root, "ЮРЧИК", 54, Color(0.88, 0.86, 0.80), Rect2(60, 70, 500, 70))
	HUD.mk_label(root, "ночь на Паскоте  ·  демо-версия", 13, HUD.C_ACCENT, Rect2(64, 136, 500, 20))
	var box := VBoxContainer.new()
	box.position = Vector2(64, 220)
	box.add_theme_constant_override("separation", 6)
	root.add_child(box)
	var first: Button = null
	var entries := [["Начать игру", Game.new_game], ["Управление", _toggle_help], ["Выход", get_tree().quit]]
	for e: Array in entries:
		var b := Button.new()
		b.text = e[0]
		b.custom_minimum_size = Vector2(220, 0)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.pressed.connect(e[1])
		b.mouse_entered.connect(b.grab_focus)
		box.add_child(b)
		if first == null:
			first = b
	first.grab_focus.call_deferred()
	_help = HUD.mk_label(root, "", 12, HUD.C_TEXT, Rect2(330, 200, 480, 250))
	_help.text = "\n".join([
		"WASD / левый стик — идти          мышь / правый стик — смотреть",
		"Shift / B — бег вперёд (тратит силы)",
		"ЛКМ / RT — удар молотком",
		"ПКМ / LT — замах; удар с замахом сильнее.",
		"      Целься в голову — оглушит, по ногам — собьёт.",
		"G / RB — бросить бутылку или кирпич",
		"E / A — подобрать, открыть, вырваться из захвата",
		"F / Y — фонарик          Tab / Back — инвентарь",
		"Esc / Start — пауза",
	])
	_help.visible = false
	HUD.mk_label(root, "звуки — временные заглушки", 10, Color(0.5, 0.5, 0.5), Rect2(64, 452, 400, 16))


func _toggle_help() -> void:
	_help.visible = not _help.visible


func _process(delta: float) -> void:
	_t += delta
	var a := sin(_t * 0.04) * 0.5                     # медленно покачивается вокруг вида с юга на двор
	_cam.position = ORBIT_CENTER + Vector3(sin(a) * 14.0, 4.5 + sin(_t * 0.11) * 0.3, cos(a) * 14.0)
	_cam.look_at(ORBIT_CENTER + Vector3(0.0, 4.0, 0.0))
