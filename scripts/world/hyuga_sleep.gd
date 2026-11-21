## Хьюга спит (клубком на диване в комнате Юрчика). Вешается на корень инстанса hyuga.gltf.
## Sleep играет по кругу (дыхание). Поверх него со случайной паузой проигрываются короткие добавочные
## анимации дрёмы — вздрагивание уха, вздох, шевеление лапы. Они хранят только отклонение от покоя, поэтому
## накладываются через AnimationNodeOneShot в режиме ADD и не сбивают дыхание. Коллизии у собаки нет.
## В такт дыханию Sleep (цикл 4.5 с: вдох 1.4 с, потом выдох) собака храпит (snore_in_* на вдохе, тихое сопение
## snore_out_* на выдохе).
extends Node3D

@export var min_pause := 6.0    ## минимальная пауза между «дрёмами», с
@export var max_pause := 15.0   ## максимальная пауза, с
@export var shadow_layer := 11  ## слой отрисовки собаки: контактная тень (Decal) его не задевает

## имя анимации → вес (вздрагивание уха — чаще всего, вздох — реже)
const DOZE := {"SleepTwitchEar": 3.0, "SleepSigh": 2.0, "SleepTwitchPaw": 1.5}
const BREATH_L := 4.5     ## длина цикла дыхания — как у анимации Sleep (SLEEP_L в build_hyuga.py)
const INHALE := 1.4       ## вдох — как в breath_curve

@export var snore_db := -6.0    ## громкость храпа

var _tree: AnimationTree
var _wait := 0.0
var _last := ""
var _breath := 0.0
var _exhaled := false
var _snore: AudioStreamPlayer3D


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


## Свой счётчик времени идёт вместе с AnimationTree (тот же delta, оба стартуют в _ready), поэтому звук
## попадает во вдох и выдох анимации.
func _breathe(delta: float) -> void:
	_breath += delta
	if _breath >= BREATH_L:
		_breath = fmod(_breath, BREATH_L)
		_inhale()
	if not _exhaled and _breath >= INHALE:
		_exhaled = true
		_play("snore_out_%d" % randi_range(1, 2), snore_db - 9.0)


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

