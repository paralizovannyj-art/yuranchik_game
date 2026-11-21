## Витрина существа для полигона: ставит модель на постамент и по кругу показывает все её анимации.
## Подпись сверху — имя и текущая анимация. Подойди и нажми E — следующая анимация.
## Модель и расцветку выбираешь в инспекторе; добавить новое существо = скопировать витрину и сменить model.
class_name CreatureShowcase
extends Node3D

@export var model: PackedScene
@export var title := "Существо"
@export var texture_override: Texture2D   ## своя расцветка (например, enemy_b.png у офника); пусто — как в модели
@export var double_sided := false         ## у Сергея капюшон виден изнутри — нужны обе стороны граней
@export var auto_cycle := true            ## сами листаются анимации
@export var hold := 1.2                   ## пауза после разовой анимации (Death, Punch…), сек
@export var loop_time := 3.5              ## сколько показывать зацикленную (Idle, Walk…), сек
@export var pedestal := true
## клипы отдельной библиотекой (у Юрчика анимации GMod лежат не в модели) — витрина сама создаст AnimationPlayer
@export var animation_library: AnimationLibrary

var _anim: AnimationPlayer
var _names: PackedStringArray = []
var _i := 0
var _t := 0.0
var _label: Label3D


func _ready() -> void:
	if pedestal:
		var p := MeshInstance3D.new()
		var cm := CylinderMesh.new()
		cm.top_radius = 0.75
		cm.bottom_radius = 0.8
		cm.height = 0.12
		var pm := StandardMaterial3D.new()
		pm.albedo_color = Color(0.32, 0.32, 0.34)
		pm.roughness = 1.0
		cm.material = pm
		p.mesh = cm
		p.position.y = 0.06
		add_child(p)
	var body := Node3D.new()
	body.position.y = 0.12 if pedestal else 0.0
	add_child(body)
	if model:
		var m := model.instantiate()
		body.add_child(m)
		_dress(m)
		if animation_library:
			var ap := AnimationPlayer.new()
			m.add_child(ap)
			ap.root_node = NodePath("..")
			ap.add_animation_library("", animation_library)
		var players := m.find_children("*", "AnimationPlayer", true, false)
		if players.size() > 0:
			_anim = players[0]
			for n: StringName in _anim.get_animation_list():
				if n != &"RESET":
					_names.append(n)
	_label = Label3D.new()
	_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_label.font_size = 40
	_label.outline_size = 10
	_label.pixel_size = 0.006
	_label.position.y = 2.75
	_label.no_depth_test = true
	add_child(_label)
	var button := Interactable.new()        # «кнопка» на уровне груди: на неё смотрит прицел Юрчика
	button.prompt = "Следующая анимация"
	button.radius = 2.2
	button.position = Vector3(0, 1.0, 0)
	button.interacted.connect(func(_p: Player) -> void: _play(_i + 1))
	add_child(button)
	_play(0)


func _dress(root: Node) -> void:
	if texture_override == null and not double_sided:
		return
	for mi: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		var mat := mi.get_active_material(0) as StandardMaterial3D
		if mat == null:
			continue
		mat = mat.duplicate() as StandardMaterial3D
		if texture_override:
			mat.albedo_texture = texture_override
		if double_sided:
			mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		mi.set_surface_override_material(0, mat)


func _play(i: int) -> void:
	if _names.is_empty():
		_label.text = "%s\n(нет анимаций)" % title
		return
	_i = posmod(i, _names.size())
	var n := _names[_i]
	_anim.stop()
	_anim.play(n)
	var a := _anim.get_animation(n)
	_t = loop_time if a.loop_mode != Animation.LOOP_NONE else a.length + hold
	_label.text = "%s\n%s  (%d/%d)" % [title, n, _i + 1, _names.size()]


func _process(delta: float) -> void:
	if not auto_cycle or _names.is_empty():
		return
	_t -= delta
	if _t <= 0.0:
		_play(_i + 1)
