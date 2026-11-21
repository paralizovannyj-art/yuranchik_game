## Хьюга спит (клубком на диване в комнате Юрчика). Вешается на корень инстанса hyuga.gltf.
## Sleep играет по кругу (дыхание). Поверх него со случайной паузой проигрываются короткие добавочные
## анимации дрёмы — вздрагивание уха, вздох, шевеление лапы. Они хранят только отклонение от покоя, поэтому
## накладываются через AnimationNodeOneShot в режиме ADD и не сбивают дыхание. Коллизии у собаки нет.
extends Node3D

@export var min_pause := 6.0    ## минимальная пауза между «дрёмами», с
@export var max_pause := 15.0   ## максимальная пауза, с
@export var shadow_layer := 11  ## слой отрисовки собаки: контактная тень (Decal) его не задевает

## имя анимации → вес (вздрагивание уха — чаще всего, вздох — реже)
const DOZE := {"SleepTwitchEar": 3.0, "SleepSigh": 2.0, "SleepTwitchPaw": 1.5}

var _tree: AnimationTree
var _wait := 0.0
var _last := ""


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


func _process(delta: float) -> void:
	if _tree == null:
		return
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
