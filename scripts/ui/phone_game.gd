## Мини-игра в телефоне (меню «Игры»). Поле — прямоугольник экрана между строкой статуса и софт-клавишами.
## Экран телефона (phone_screen.gd) каждый кадр зовёт step() и draw(); стрелки приходят в dir(), OK — в action().
class_name PhoneGame
extends RefCounted

static var best := {}                            ## рекорды за сеанс: название → очки

var area: Rect2
var font: Font
var score := 0
var lives := 0
var over := false


func title() -> String:
	return ""


func start() -> void:
	pass


func step(_delta: float) -> void:
	pass


func draw(_ci: CanvasItem) -> void:
	pass


func dir(_d: Vector2i) -> void:
	pass


## OK: после проигрыша — новая игра; во время игры — по-своему (выстрел в «Танках»).
func action() -> void:
	if over:
		start()


## Строка над полем.
func status() -> String:
	return "%s   %d" % [title(), score]


## Какая стрелка зажата сейчас (клавиатура или крестовина геймпада).
func held() -> Vector2i:
	if Input.is_action_pressed("ui_up"):
		return Vector2i.UP
	if Input.is_action_pressed("ui_down"):
		return Vector2i.DOWN
	if Input.is_action_pressed("ui_left"):
		return Vector2i.LEFT
	if Input.is_action_pressed("ui_right"):
		return Vector2i.RIGHT
	return Vector2i.ZERO


func finish() -> void:
	over = true
	best[title()] = maxi(best.get(title(), 0), score)
	Game.sfx("phone_sms", null, -16.0, 0.0)


## Короткий писк телефона: съел, попал.
func blip(volume_db := -22.0) -> void:
	Game.sfx("phone_key", null, volume_db, 0.05)


## Табличка поверх поля после проигрыша.
func draw_over(ci: CanvasItem) -> void:
	var r := Rect2(area.get_center() - Vector2(110, 44), Vector2(220, 88))
	ci.draw_rect(r, Color(0, 0, 0, 0.82))
	ci.draw_rect(r, Color("9fd0c8"), false, 1.0)
	ci.draw_string(font, Vector2(r.position.x, r.position.y + 24), "Игра окончена", HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 19, Color("ff9e40"))
	ci.draw_string(font, Vector2(r.position.x, r.position.y + 48), "Счёт: %d   Рекорд: %d" % [score, best.get(title(), 0)],
		HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 15, Color("e8f2ef"))
	ci.draw_string(font, Vector2(r.position.x, r.position.y + 72), "OK — ещё раз", HORIZONTAL_ALIGNMENT_CENTER, r.size.x, 14, Color("9fd0c8"))


## Надпись по центру поля (например, «Волна 2»).
func banner(ci: CanvasItem, text: String) -> void:
	var y := area.get_center().y
	ci.draw_rect(Rect2(area.position.x, y - 18, area.size.x, 28), Color(0, 0, 0, 0.6))
	ci.draw_string(font, Vector2(area.position.x, y + 3), text, HORIZONTAL_ALIGNMENT_CENTER, area.size.x, 18, Color("ff9e40"))
