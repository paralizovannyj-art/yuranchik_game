## Хьюга спит (клубком на диване в комнате Юрчика). Вешается на корень инстанса hyuga.gltf.
## Sleep играет по кругу (дыхание). Поверх него со случайной паузой проигрываются короткие добавочные
## анимации дрёмы — вздрагивание уха, вздох, шевеление лапы. Они хранят только отклонение от покоя, поэтому
## накладываются через AnimationNodeOneShot в режиме ADD и не сбивают дыхание. Коллизии у собаки нет.
## В такт дыханию Sleep (цикл 4.5 с: вдох 1.4 с, потом выдох) собака храпит (snore_in_* на вдохе, тихое сопение
## snore_out_* на выдохе), а на каждом выдохе из-над морды всплывает буква «z» или «Z» и тает.
extends Node3D

@export var min_pause := 6.0    ## минимальная пауза между «дрёмами», с
@export var max_pause := 15.0   ## максимальная пауза, с
@export var shadow_layer := 11  ## слой отрисовки собаки: контактная тень (Decal) его не задевает

## имя анимации → вес (вздрагивание уха — чаще всего, вздох — реже)
const DOZE := {"SleepTwitchEar": 3.0, "SleepSigh": 2.0, "SleepTwitchPaw": 1.5}
const BREATH_L := 4.5     ## длина цикла дыхания — как у анимации Sleep (SLEEP_L в build_hyuga.py)
const INHALE := 1.4       ## вдох — как в breath_curve
const Z_RISE := 0.42      ## на сколько поднимается буква, м
const Z_LIFE := 2.8       ## сколько живёт буква, с

@export var snore_db := -6.0    ## громкость храпа
@export var show_z := true      ## всплывающие «Zzz»

var _tree: AnimationTree
var _wait := 0.0
var _last := ""
var _breath := 0.0
var _exhaled := false
var _snore: AudioStreamPlayer3D
var _skel: Skeleton3D
var _head := -1


func _ready() -> void:
	var player := find_child("AnimationPlayer", true, false) as AnimationPlayer
	if player == null:
		push_warning("hyuga_sleep: нет AnimationPlayer")
		return
	player.stop()
	player.get_animation("Sleep").loop_mode = Animation.LOOP_LINEAR
	var bt := AnimationNodeBlendTree.new()
	var base := AnimationNodeAnimation.new()
	base.animation = &"Sleep"
	bt.add_node(&"sleep", base)
	var prev := &"sleep"
	for anim_name: String in DOZE:
		var anim := AnimationNodeAnimation.new()
		anim.animation = StringName(anim_name)
		var shot := AnimationNodeOneShot.new()
		shot.mix_mode = AnimationNodeOneShot.MIX_MODE_ADD
		shot.fadein_time = 0.3
		shot.fadeout_time = 0.5
		bt.add_node(StringName(anim_name + "_clip"), anim)
		bt.add_node(StringName(anim_name), shot)
		bt.connect_node(StringName(anim_name), 0, prev)
		bt.connect_node(StringName(anim_name), 1, StringName(anim_name + "_clip"))
		prev = StringName(anim_name)
	bt.connect_node(&"output", 0, prev)
	_tree = AnimationTree.new()
	_tree.name = "SleepTree"
	_tree.tree_root = bt
	add_child(_tree)
	_tree.anim_player = _tree.get_path_to(player)
	_tree.active = true
	for mi: MeshInstance3D in find_children("*", "MeshInstance3D", true, false):
		mi.layers = 1 << (shadow_layer - 1)
	_wait = randf_range(min_pause * 0.5, max_pause)
	for sk: Skeleton3D in find_children("*", "Skeleton3D", true, false):
		_skel = sk
	if _skel:
		_head = _skel.find_bone("Head")
	_snore = AudioStreamPlayer3D.new()
	_snore.name = "Snore"
	_snore.unit_size = 1.2
	_snore.max_distance = 9.0
	add_child(_snore)
	_snore.position = Vector3(0, 0.15, 0)
	_breath = 0.0
	_inhale()


func _process(delta: float) -> void:
	if _tree == null:
		return
	_breathe(delta)
	_wait -= delta
	if _wait > 0.0:
		return
	_wait = randf_range(min_pause, max_pause)
	var pick := _pick()
	_last = pick
	_tree.set("parameters/%s/request" % pick, AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func _pick() -> String:
	var total := 0.0
	for k: String in DOZE:
		if k != _last:
			total += DOZE[k]
	var r := randf() * total
	for k: String in DOZE:
		if k == _last:
			continue
		r -= DOZE[k]
		if r <= 0.0:
			return k
	return DOZE.keys()[0]


## Свой счётчик времени идёт вместе с AnimationTree (тот же delta, оба стартуют в _ready), поэтому звук и буквы
## попадают во вдох и выдох анимации.
func _breathe(delta: float) -> void:
	_breath += delta
	if _breath >= BREATH_L:
		_breath = fmod(_breath, BREATH_L)
		_inhale()
	if not _exhaled and _breath >= INHALE:
		_exhaled = true
		_play("snore_out_%d" % randi_range(1, 2), snore_db - 9.0)
		if show_z:
			_spawn_trail()


func _inhale() -> void:
	_exhaled = false
	if randf() < 0.85:                                     # изредка вдох проходит тихо — храп не как метроном
		_play("snore_in_%d" % randi_range(1, 3), snore_db + randf_range(-2.0, 1.0))


func _play(sound: String, db: float) -> void:
	var s := Game.stream(sound)
	if s == null or _snore == null:
		return
	_snore.stream = s
	_snore.volume_db = db
	_snore.pitch_scale = randf_range(0.94, 1.05)
	_snore.play()


func _head_pos() -> Vector3:
	if _skel and _head >= 0:
		return _skel.global_transform * _skel.get_bone_global_pose(_head).origin
	return global_position + Vector3(0, 0.15, 0)


## Цепочка «z z Z»: три буквы одна за другой, от маленькой к большой, уплывают по одной диагонали.
func _spawn_trail() -> void:
	var side := Vector3(0.09, 0, 0)
	var cam := get_viewport().get_camera_3d()
	if cam:                                                  # вверх-вправо на экране, как в мультиках
		var right := cam.global_basis.x
		side = Vector3(right.x, 0, right.z).normalized() * randf_range(0.1, 0.14)
	for k: int in 3:
		if k > 0:
			await get_tree().create_timer(0.45).timeout
		if not is_inside_tree():
			return
		_spawn_z("Z" if k == 2 else "z", 0.0013 + 0.0005 * k, side)


func _spawn_z(text: String, px: float, side: Vector3) -> void:
	var l := Label3D.new()
	l.text = text
	l.font_size = 48
	l.pixel_size = px
	l.outline_size = 10
	l.outline_modulate = Color(0.05, 0.06, 0.12, 0.85)
	l.modulate = Color(0.82, 0.9, 1.0, 0.0)
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.shaded = false
	l.double_sided = true
	l.layers = 1 << (shadow_layer - 1)
	add_child(l)
	var start := _head_pos() + Vector3(0, 0.07, 0)
	var drift := side + Vector3(0, Z_RISE, 0)
	l.global_position = start
	l.scale = Vector3.ONE * 0.6
	var tw := l.create_tween().set_parallel(true)
	tw.tween_method(_move_z.bind(l, start, drift), 0.0, 1.0, Z_LIFE).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	tw.tween_property(l, "scale", Vector3.ONE * 1.25, Z_LIFE)
	tw.tween_property(l, "modulate:a", 0.9, 0.5)
	tw.tween_property(l, "modulate:a", 0.0, 1.4).set_delay(Z_LIFE - 1.4)
	tw.chain().tween_callback(l.queue_free)


func _move_z(k: float, l: Label3D, start: Vector3, drift: Vector3) -> void:
	l.global_position = start + drift * k + Vector3(sin(k * TAU * 1.2) * 0.025, 0, 0)   # плывёт вверх, покачиваясь
