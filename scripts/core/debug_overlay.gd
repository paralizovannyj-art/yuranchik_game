## DebugOverlay — отладочная панель поверх игры (автозагрузка, только при запуске из редактора / debug-сборке).
## Клавиша Ё (` ~): выкл → FPS → подробно → выкл.
## Не F-клавиши: F1–F8 — телепорты по району, F5–F12 заняты редактором Godot.
extends CanvasLayer

enum Mode { OFF, FPS, FULL }

const REFRESH := 0.25                           ## как часто обновлять текст, с

var mode := Mode.OFF

var _label: Label
var _timer := 0.0
var _frames := 0
var _frame_sum := 0.0
var _frame_max := 0.0


func _ready() -> void:
	layer = 128                                 # поверх HUD, телефона и меню
	process_mode = Node.PROCESS_MODE_ALWAYS     # работает и на паузе
	if not OS.is_debug_build():
		set_process(false)
		set_process_unhandled_input(false)
		return
	_label = Label.new()
	_label.position = Vector2(4, 4)
	_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_label.add_theme_font_size_override("font_size", 10)
	_label.add_theme_color_override("font_color", Color(0.75, 1.0, 0.6))
	_label.add_theme_color_override("font_outline_color", Color.BLACK)
	_label.add_theme_constant_override("outline_size", 3)
	add_child(_label)
	_apply_mode()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo \
			and (event.physical_keycode == KEY_QUOTELEFT or event.keycode == KEY_QUOTELEFT):
		mode = ((mode + 1) % Mode.size()) as Mode
		_apply_mode()
		get_viewport().set_input_as_handled()


func _apply_mode() -> void:
	visible = mode != Mode.OFF
	_timer = REFRESH                            # обновить текст сразу
	_frames = 0
	_frame_sum = 0.0
	_frame_max = 0.0


func _process(delta: float) -> void:
	if mode == Mode.OFF:
		return
	var real := delta / maxf(Engine.time_scale, 0.0001)   # реальное время кадра, без замедления
	_frames += 1
	_frame_sum += real
	_frame_max = maxf(_frame_max, real)
	_timer += real
	if _timer < REFRESH:
		return
	_timer = 0.0
	_label.text = _text()
	_frames = 0
	_frame_sum = 0.0
	_frame_max = 0.0


func _text() -> String:
	var fps := Engine.get_frames_per_second()
	var avg_ms := _frame_sum / maxi(_frames, 1) * 1000.0
	var lines: PackedStringArray = ["FPS %d   кадр %.1f мс (макс %.1f)" % [fps, avg_ms, _frame_max * 1000.0]]
	if mode == Mode.FPS:
		return lines[0]

	lines.append("CPU: process %.1f мс, physics %.1f мс" % [
		Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
		Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0])
	lines.append("Рендер: draw calls %d, объектов %d, треугольников %s" % [
		Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
		_short(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))])
	lines.append("Память: RAM %s, видео %s, нод %d" % [
		_mb(Performance.get_monitor(Performance.MEMORY_STATIC)),
		_mb(Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED)),
		Performance.get_monitor(Performance.OBJECT_NODE_COUNT)])

	var scene := get_tree().current_scene
	lines.append("Сцена: %s%s%s" % [
		scene.scene_file_path.get_file() if scene else "—",
		"   ПАУЗА" if get_tree().paused else "",
		"   x%.2f" % Engine.time_scale if not is_equal_approx(Engine.time_scale, 1.0) else ""])

	var p := get_tree().get_first_node_in_group("player") as Node3D
	if p:
		var pos := p.global_position
		var vel: Vector3 = p.get("velocity")
		lines.append("Юрчик: (%.1f, %.1f, %.1f)  скорость %.1f" % [pos.x, pos.y, pos.z, Vector2(vel.x, vel.z).length()])
		lines.append("HP %d/%d   выносл. %d%s   состояние %s%s" % [
			Game.hp, Game.MAX_HP, p.get("stamina"), " (выдохся)" if p.get("exhausted") else "",
			_state_name(p), "   GOD" if Game.god else ""])
	var enemies := get_tree().get_nodes_in_group("enemy")
	if not enemies.is_empty():
		var near := INF
		for e: Node in enemies:
			if p and e is Node3D:
				near = minf(near, p.global_position.distance_to((e as Node3D).global_position))
		lines.append("Врагов: %d%s" % [enemies.size(), "   ближайший %.1f м" % near if near < INF else ""])
	lines.append("Время %s   убито %d   смертей %d" % [Game.clock_text(), Game.stats["kills"], Game.stats["deaths"]])
	return "\n".join(lines)


func _state_name(p: Node) -> String:
	var s: int = p.get("state")
	var names: Array = Player.State.keys()
	return names[s] if s >= 0 and s < names.size() else str(s)


func _mb(bytes: float) -> String:
	return "%.0f МБ" % (bytes / 1048576.0)


func _short(n: float) -> String:
	if n >= 1000000.0:
		return "%.1fM" % (n / 1000000.0)
	if n >= 1000.0:
		return "%.1fk" % (n / 1000.0)
	return str(int(n))
