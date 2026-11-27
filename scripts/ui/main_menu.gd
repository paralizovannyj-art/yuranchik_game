## Главное меню: на фоне кадр «Юрчик курит в окне над зимним двором на закате» (scenes/ui/menu_yard.tscn, YUR-19),
## название и кнопки. Юрчик в окне — слева в кадре, поэтому всё меню справа, над двором и небом; под ним —
## затемнение градиентом от середины к правому краю (левая половина кадра не тронута).
extends Node3D

const BACKDROP := "res://scenes/ui/menu_yard.tscn"
const PLAYGROUND := "res://scenes/levels/playground.tscn"   ## отладка: полигон со всеми существами

var _help: Label
var _help_panel: ColorRect


func _ready() -> void:
	Game.in_game = false
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	add_child((load(BACKDROP) as PackedScene).instantiate())
	Game.ambience("amb_wind", -12.0)
	Game.music("mus_drone", -9.0)

	var layer := CanvasLayer.new()
	layer.layer = 20
	add_child(layer)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = HUD.make_theme()
	layer.add_child(root)
	var grad := Gradient.new()
	grad.offsets = PackedFloat32Array([0.0, 0.5, 1.0])
	grad.colors = PackedColorArray([Color(0, 0, 0, 0), Color(0, 0, 0, 0), Color(0, 0, 0, 0.5)])
	var gtex := GradientTexture2D.new()
	gtex.gradient = grad
	gtex.width = 256
	gtex.height = 4
	var shade := TextureRect.new()
	shade.texture = gtex
	shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	shade.stretch_mode = TextureRect.STRETCH_SCALE
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(shade)
	HUD.mk_label(root, "ЮРЧИК", 81, Color(0.88, 0.86, 0.80), Rect2(640, 92, 570, 105), HORIZONTAL_ALIGNMENT_RIGHT)
	HUD.mk_label(root, "ночь на Паскоте  ·  демо-версия", 20, HUD.C_ACCENT, Rect2(640, 190, 566, 30),
			HORIZONTAL_ALIGNMENT_RIGHT)
	var box := VBoxContainer.new()
	box.position = Vector2(1210 - 330, 330)
	box.add_theme_constant_override("separation", 9)
	root.add_child(box)
	var first: Button = null
	var entries := [["Начать игру", Game.new_game], [_graphics_text(), _toggle_graphics], ["Управление", _toggle_help], ["Выход", get_tree().quit]]
	if OS.is_debug_build():                       # отладка: сразу в комнату Юрчика (в собранной игре пункта нет)
		entries.insert(1, ["Комната Юрчика", Game.start_in_room])
		entries.insert(2, ["Полигон", Game.new_game.bind(PLAYGROUND)])
	for e: Array in entries:
		var b := Button.new()
		b.text = e[0]
		b.custom_minimum_size = Vector2(330, 0)
		b.alignment = HORIZONTAL_ALIGNMENT_RIGHT
		b.pressed.connect(e[1])
		b.mouse_entered.connect(b.grab_focus)
		box.add_child(b)
		if first == null:
			first = b
	first.grab_focus.call_deferred()
	# управление — поверх кадра слева от кнопок, на тёмной подложке
	_help_panel = ColorRect.new()
	_help_panel.color = Color(0, 0, 0, 0.62)
	_help_panel.position = Vector2(60, 280)
	_help_panel.size = Vector2(790, 400)
	_help_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_help_panel)
	_help = HUD.mk_label(_help_panel, "", 18, HUD.C_TEXT, Rect2(24, 18, 750, 375))
	_help.text = "\n".join([
		"WASD / левый стик — идти          мышь / правый стик — смотреть",
		"Shift / B — бег вперёд (тратит силы)",
		"ЛКМ / RT — удар молотком",
		"ПКМ / LT — замах; удар с замахом сильнее.",
		"      Целься в голову — оглушит, по ногам — собьёт.",
		"Q / ← на крестовине — убрать молоток в сумку или достать; без него бьёшь кулаком",
		"G / RB — бросить бутылку или кирпич",
		"E / A — подобрать, открыть",
		"F / Y — фонарик",
		"Tab / Back — телефон: задания, самочувствие          I / ↓ на крестовине — сумка",
		"Esc / Start — пауза",
	])
	_help_panel.visible = false
	HUD.mk_label(root, "звуки — временные заглушки", 15, Color(0.5, 0.5, 0.5), Rect2(610, 678, 600, 24),
			HORIZONTAL_ALIGNMENT_RIGHT)


## Подпись пункта графики: что выбрано сейчас. «авто» — видеокарта не умеет Vulkan, движок сам перешёл на OpenGL.
func _graphics_text() -> String:
	if Graphics.low_mode_selected():
		return "Графика: слабый ПК"
	if Graphics.opengl:
		return "Графика: слабый ПК (авто)"
	return "Графика: обычная"


## Переключить режим графики — игра перезапустится (см. scripts/core/graphics.gd).
func _toggle_graphics() -> void:
	Graphics.set_low_mode(not Graphics.low_mode_selected())


func _toggle_help() -> void:
	_help_panel.visible = not _help_panel.visible

