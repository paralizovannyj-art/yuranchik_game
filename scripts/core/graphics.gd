## Graphics — режим графики (автозагрузка). Два режима:
##   «Обычная»   — Forward+ (Vulkan / D3D12): всё как задумано — объёмный туман, тени от фонарей и фонарика, декали;
##   «Слабый ПК» — Compatibility (OpenGL 3.3): идёт на старых видеокартах и встройках.
## Режим хранится в user://graphics.cfg — его читает сам движок до запуска (project.godot →
## application/config/project_settings_override), поэтому смена режима требует перезапуска игры.
## Если видеокарта не умеет Vulkan/D3D12, движок сам уходит на OpenGL (rendering_device/fallback_to_opengl3) —
## тогда этот файл ни при чём, но поправки ниже всё равно применяются.
##
## Поправки для OpenGL (подбирались по скриншотам рядом с Vulkan, ветка feature/opengl-compatibility):
## - тени у ламп выключаются: в Compatibility (Godot 4.7.2) источник с тенью рисуется отдельным проходом и
##   складывается с остальным светом уже после перевода в sRGB — любая тень пересвечивает картинку
##   (ночной снег на полигоне становится в 1.6 раза ярче). Заодно тени — самое дорогое для слабых видеокарт;
## - объёмного тумана нет: вместо него добавляем его плотность к обычному туману (он тоже тёмный и глотает даль);
## - декалей нет: тень-пятно под Хьюгой заменяется плоским полупрозрачным квадратом.
extends Node

const CFG := "user://graphics.cfg"
const OPENGL := "gl_compatibility"
## во сколько раз плотность объёмного тумана переходит в обычный туман на OpenGL
const VOL_FOG_TO_FOG := 1.0
## где по высоте коробки декали лечь квадрату-заменителю (доля высоты от центра вверх): мягкое покрывало
## на диване выше коллизии, квадрат у дна коробки тонет в складках
const DECAL_LIFT := 0.15

## true — сейчас работает OpenGL (выбран «Слабый ПК» или движок сам откатился на OpenGL)
var opengl := false

## Матовые материалы в обоих режимах: без бликов (specular) — правило автора «минимум современных эффектов»
## (docs/design/ps2-style/cry-of-fear-author.md, М1). Свет (фонарик, лампы) на материал действует как раньше —
## пропадает только блестящее пятно. Применяется к каждому материалу один раз, при появлении узла в сцене:
## так не нужно править импорт моделей, скрипты и сцены по отдельности.
const MATTE := true
var _matte_done := {}

## Туман-«стена» (Environment.fog_mode = Depth) в режиме «Обычная» заменяется туманом, который не трогает свет:
## shaders/lit_fog.gdshader — тёмное уходит в туман, освещённое и светящееся остаётся (правило автора,
## cry-of-fear-author.md Э3). Берёт begin / end / цвет из окружения. В обоих режимах (на OpenGL проверено 2026-11-24:
## без него туман движка прятал горящие окна домов).
const LIT_FOG_SHADER := "res://shaders/lit_fog.gdshader"

## Внутреннее разрешение 3D — 720 строк при любом окне (1280×720 в 16:9). Интерфейс живёт в сетке 1280×720
## (display/window/stretch/mode = canvas_items) и рисуется в разрешении окна, а 3D уменьшается через
## scaling_3d_scale и растягивается обратно мягко (билинейно) — PS2-мыльность без «вырвиглазных» пикселей.
const RENDER_HEIGHT := 720.0

## PS2-фильтр один на всю игру, днём и ночью: assets/environments/ps2_post.tres (решение автора 2026-11-22 —
## отдельный дневной фильтр сравнили и отказались). Уровни ставят его сами (узел PS2Post); если в сцене
## с WorldEnvironment его нет — добавляется здесь, чтобы ни одна сцена не осталась без фильтра.
const PS2_POST := "res://assets/environments/ps2_post.tres"


func _ready() -> void:
	opengl = RenderingServer.get_current_rendering_method() == OPENGL
	get_tree().node_added.connect(_on_node_added)
	get_tree().root.size_changed.connect(_fit_3d_resolution)
	_fit_3d_resolution()
	# сцена, запущенная напрямую (F6 / из редактора), может войти в дерево раньше подписки — пройти её узлы
	_sweep.call_deferred(get_tree().root)


func _sweep(n: Node) -> void:
	if n != self:
		_on_node_added(n)
	for c in n.get_children():
		_sweep(c)


func _fit_3d_resolution() -> void:
	var root := get_tree().root
	root.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
	root.scaling_3d_scale = clampf(RENDER_HEIGHT / maxf(root.size.y, 1.0), 0.25, 1.0)


## Режим, выбранный в меню (может не совпадать с текущим до перезапуска).
func low_mode_selected() -> bool:
	return FileAccess.file_exists(CFG)


## Выбрать режим и перезапустить игру.
func set_low_mode(on: bool) -> void:
	if on:
		var f := FileAccess.open(CFG, FileAccess.WRITE)
		if f == null:
			push_warning("Graphics: не удалось записать %s" % CFG)
			return
		f.store_string('[rendering]\n\nrenderer/rendering_method="%s"\n' % OPENGL)
		f.close()
	elif FileAccess.file_exists(CFG):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(CFG))
	var args := OS.get_cmdline_args()
	# ключи рендера из командной строки сильнее файла — при перезапуске убираем их
	for key: String in ["--rendering-method", "--rendering-driver"]:
		var i := args.find(key)
		if i >= 0:
			args.remove_at(i)
			if i < args.size():
				args.remove_at(i)
	OS.set_restart_on_exit(true, args)
	get_tree().quit()


func _on_node_added(node: Node) -> void:
	if MATTE and node is GeometryInstance3D:
		_make_matte.call_deferred(node)
	if node is WorldEnvironment:
		_ensure_ps2_post.call_deferred(node)
	if not opengl:
		if node is WorldEnvironment:
			_add_lit_fog.call_deferred(node)
		return
	if node is Light3D:
		(node as Light3D).shadow_enabled = false     # light_budget.gd запоминает это и тоже не включит тень
	elif node is WorldEnvironment:
		_fix_environment.call_deferred(node)
		_add_lit_fog.call_deferred(node)              # после _fix_environment: горящие окна и фонари видно издалека и тут
	elif node is Decal:
		_replace_decal.call_deferred(node)


func _fix_environment(we: WorldEnvironment) -> void:
	if not is_instance_valid(we) or we.environment == null:
		return
	var env := we.environment
	if not env.volumetric_fog_enabled:
		return
	# окружение общее (assets/environments/*.tres) и живёт в кэше — правим один раз, на копии
	env = env.duplicate()
	env.volumetric_fog_enabled = false
	# где тумана движка нет (подъезд: воздух в помещении чистый, лёгкая пыль только в объёмном),
	# не включаем его — тёмный экспоненциальный туман съел бы лампы и окна
	if env.fog_enabled:
		env.fog_density += env.volumetric_fog_density * VOL_FOG_TO_FOG
	we.environment = env


## Декаль-«пятно» → плоский квадрат с той же текстурой, лежащий на поверхности под ней.
func _replace_decal(d: Decal) -> void:
	if not is_instance_valid(d) or not d.is_inside_tree() or d.is_queued_for_deletion():
		return
	var m := StandardMaterial3D.new()
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_texture = d.texture_albedo
	m.albedo_color = d.modulate
	m.roughness = 1.0
	m.disable_receive_shadows = true
	var q := PlaneMesh.new()
	q.size = Vector2(d.size.x, d.size.z)
	var mi := MeshInstance3D.new()
	mi.name = String(d.name) + "Flat"
	mi.mesh = q
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.transform = d.transform
	mi.position.y += d.size.y * DECAL_LIFT
	d.get_parent().add_child(mi)
	d.queue_free()


## Выключить блик у всех материалов узла (собственные, переопределённые и материалы меша).
func _make_matte(gi: GeometryInstance3D) -> void:
	if not is_instance_valid(gi):
		return
	_matte(gi.material_override)
	_matte(gi.material_overlay)
	if gi is MeshInstance3D:
		var mi := gi as MeshInstance3D
		if mi.mesh:
			for i in mi.mesh.get_surface_count():
				_matte(mi.get_surface_override_material(i))
				_matte(mi.mesh.surface_get_material(i))
	elif gi is CSGShape3D:
		_matte((gi as CSGShape3D).get("material"))


func _matte(m: Material) -> void:
	if m == null or not m is BaseMaterial3D:
		return
	var id := m.get_instance_id()
	if _matte_done.has(id):
		return
	_matte_done[id] = true
	var bm := m as BaseMaterial3D
	if bm.shading_mode == BaseMaterial3D.SHADING_MODE_UNSHADED:
		return
	bm.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	bm.metallic = 0.0


func _add_lit_fog(we: WorldEnvironment) -> void:
	if not is_instance_valid(we) or we.environment == null:
		return
	var env := we.environment
	if not env.fog_enabled or env.fog_mode != Environment.FOG_MODE_DEPTH or we.has_node("LitFog"):
		return
	var sm := ShaderMaterial.new()
	sm.shader = load(LIT_FOG_SHADER)
	sm.render_priority = Material.RENDER_PRIORITY_MIN     # первым среди прозрачных: снег и карточки света поверх
	sm.set_shader_parameter("fog_color", env.fog_light_color)
	sm.set_shader_parameter("fog_begin", env.fog_depth_begin)
	sm.set_shader_parameter("fog_end", env.fog_depth_end)
	var q := QuadMesh.new()
	q.size = Vector2(2, 2)
	var mi := MeshInstance3D.new()
	mi.name = "LitFog"
	mi.mesh = q
	mi.material_override = sm
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.custom_aabb = AABB(Vector3.ONE * -100000.0, Vector3.ONE * 200000.0)   # квадрат во весь экран — не отсекать
	we.add_child(mi)
	# окружение общее (assets/environments/*.tres) — туман движка выключаем на копии
	env = env.duplicate()
	env.fog_enabled = false
	we.environment = env


func _ensure_ps2_post(we: WorldEnvironment) -> void:
	if not is_instance_valid(we) or not we.is_inside_tree():
		return
	if not get_tree().root.find_children("PS2Post", "CanvasLayer", true, false).is_empty():
		return
	var host := we.owner if we.owner else we.get_parent()
	var layer := CanvasLayer.new()
	layer.name = "PS2Post"
	layer.layer = 10
	var rect := ColorRect.new()
	rect.name = "Filter"
	rect.material = load(PS2_POST)
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(rect)
	host.add_child(layer)
