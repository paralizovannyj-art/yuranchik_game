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


func _ready() -> void:
	opengl = RenderingServer.get_current_rendering_method() == OPENGL
	get_tree().node_added.connect(_on_node_added)


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
	if not opengl:
		return
	if node is Light3D:
		(node as Light3D).shadow_enabled = false     # light_budget.gd запоминает это и тоже не включит тень
	elif node is WorldEnvironment:
		_fix_environment.call_deferred(node)
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
	env.fog_enabled = true
	env.fog_density += env.volumetric_fog_density * VOL_FOG_TO_FOG
	we.environment = env


## Декаль-«пятно» → плоский квадрат с той же текстурой, лежащий на поверхности под ней.
func _replace_decal(d: Decal) -> void:
	if not is_instance_valid(d) or not d.is_inside_tree():
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
