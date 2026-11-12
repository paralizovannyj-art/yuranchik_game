## Анимации Юрчика. Клипы — из Quaternius «Universal Animation Library» 1 и 2 (CC0),
## перенесены на скелет Юрчика в Blender: tools/blender/retarget_ual_yurchik.py.
## Смешивание — AnimationTree, собирается здесь в коде:
##   стойка ↔ ходьба (вперёд/назад) ↔ бег  →  верх тела: стойка «готов к удару» (ПКМ)  →  удар (OneShot).
## Скорость проигрывания подгоняется под скорость героя, чтобы ноги не скользили.
## Поверх — процедурный крен в поворотах и наклон при разгоне (YurchikLean).
extends Node3D

@export_group("Клипы")
@export var walk_anim_speed := 0.95  ## м/с, с которой «идут» ноги в клипе Walk при скорости ×1
@export var jog_anim_speed := 5.2    ## то же для Jog (им бежит спринт)
@export var walk_rate_max := 1.8     ## быстрее ходьбу не крутим — иначе семенит
@export var jog_rate_min := 0.7      ## медленнее бег не крутим — иначе «плывёт»
@export var attack_rate := 1.0

@export_group("Смешивание")
@export var move_from := 0.15        ## м/с — с этой скорости начинаем шагать
@export var move_to := 0.6
@export var run_from := 2.0          ## м/с — переход с шага на бег
@export var run_to := 3.6
@export var blend_response := 9.0
@export var aim_response := 10.0

@export_group("Наклоны")
@export var lean_turn := 0.05        ## крен в повороте
@export var lean_accel := 0.03       ## наклон при разгоне/торможении
@export var breath := 0.015

var step_phase := 0.0                ## читает камера для покачивания (одна «волна» на шаг)

const LOOPS := ["Idle", "Walk", "WalkBack", "Jog", "Sprint", "AimIdle"]
const UPPER := ["Spine", "Head", "UpperArmL", "ForearmL", "HandL", "UpperArmR", "ForearmR", "HandR"]

var _anim: AnimationPlayer
var _tree: AnimationTree
var _lean_mod: YurchikLean
var _move := 0.0
var _run := 0.0
var _back := 0.0
var _aim := 0.0
var _lean := Vector2.ZERO
var _time := 0.0
var _walk_len := 1.333
var _jog_len := 0.933


func _ready() -> void:
	var players := find_children("*", "AnimationPlayer", true, false)
	if players.is_empty():
		push_error("yurchik_anim: в модели нет AnimationPlayer — переэкспортируйте yurchik.gltf с анимациями")
		return
	_anim = players[0]
	for n: String in LOOPS:
		if _anim.has_animation(n):
			_anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	_walk_len = _anim.get_animation("Walk").length
	_jog_len = _anim.get_animation("Jog").length

	_tree = AnimationTree.new()
	_tree.name = "AnimationTree"
	_anim.get_parent().add_child(_tree)
	_tree.anim_player = _tree.get_path_to(_anim)
	_tree.root_node = _tree.get_path_to(_anim.get_node(_anim.root_node))
	_tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	_tree.tree_root = _build_tree()
	_tree.active = true

	var sk := find_children("*", "Skeleton3D", true, false)
	if sk.size() > 0:
		_lean_mod = YurchikLean.new()
		_lean_mod.name = "Lean"
		(sk[0] as Skeleton3D).add_child(_lean_mod)


func _clip(n: String) -> AnimationNodeAnimation:
	var a := AnimationNodeAnimation.new()
	a.animation = n
	return a


func _build_tree() -> AnimationNodeBlendTree:
	var bt := AnimationNodeBlendTree.new()
	bt.add_node("idle", _clip("Idle"))
	for n: String in ["walk", "back", "jog", "attack_clip"]:
		var src: String = {"walk": "Walk", "back": "WalkBack", "jog": "Jog", "attack_clip": "Attack"}[n]
		bt.add_node(n, _clip(src))
		bt.add_node(n + "_ts", AnimationNodeTimeScale.new())
		bt.connect_node(n + "_ts", 0, n)
	bt.add_node("fwd", AnimationNodeBlend2.new())      # шаг ↔ бег
	bt.connect_node("fwd", 0, "walk_ts")
	bt.connect_node("fwd", 1, "jog_ts")
	bt.add_node("dir", AnimationNodeBlend2.new())      # вперёд ↔ назад
	bt.connect_node("dir", 0, "fwd")
	bt.connect_node("dir", 1, "back_ts")
	bt.add_node("move", AnimationNodeBlend2.new())     # стоим ↔ идём
	bt.connect_node("move", 0, "idle")
	bt.connect_node("move", 1, "dir")

	# стойка «готов к удару» — только верх тела, ноги продолжают шагать
	var aim := AnimationNodeBlend2.new()
	aim.filter_enabled = true
	var ref := _anim.get_animation("Idle")
	for i in ref.get_track_count():
		var path := ref.track_get_path(i)
		if path.get_concatenated_subnames() in UPPER:
			aim.set_filter_path(path, true)
	bt.add_node("aim", aim)
	bt.add_node("aim_pose", _clip("AimIdle"))
	bt.connect_node("aim", 0, "move")
	bt.connect_node("aim", 1, "aim_pose")

	var shot := AnimationNodeOneShot.new()
	shot.fadein_time = 0.06
	shot.fadeout_time = 0.22
	bt.add_node("attack", shot)
	bt.connect_node("attack", 0, "aim")
	bt.connect_node("attack", 1, "attack_clip_ts")
	bt.connect_node("output", 0, "attack")
	return bt


func play_attack() -> void:
	if _tree:
		_tree.set("parameters/attack_clip_ts/scale", attack_rate)
		_tree.set("parameters/attack/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


## Длина удара в секундах — по ней player.gd считает, когда удар закончится.
func attack_length() -> float:
	if _anim and _anim.has_animation("Attack"):
		return _anim.get_animation("Attack").length / attack_rate
	return 0.83


## speed — со знаком (назад < 0); sprint 0..1; state: 0 обычный, 1 замах (ПКМ), 2 удар.
func update_anim(delta: float, speed: float, sprint: float, state: int, yaw_rate: float, accel: float) -> void:
	if _tree == null:
		return
	_time += delta
	var spd := absf(speed)
	var k := 1.0 - exp(-blend_response * delta)
	_move = lerpf(_move, smoothstep(move_from, move_to, spd), k)
	_run = lerpf(_run, smoothstep(run_from, run_to, spd) * (1.0 if speed > 0.0 else 0.0), k)
	_back = lerpf(_back, 1.0 if speed < -0.05 else 0.0, k)
	_aim = lerpf(_aim, 1.0 if state == 1 else 0.0, 1.0 - exp(-aim_response * delta))

	# скорость клипов под скорость героя
	var walk_rate := clampf(spd / walk_anim_speed, 0.6, walk_rate_max)
	var jog_rate := clampf(spd / jog_anim_speed, jog_rate_min, 1.3)
	_tree.set("parameters/walk_ts/scale", walk_rate)
	_tree.set("parameters/back_ts/scale", walk_rate)
	_tree.set("parameters/jog_ts/scale", jog_rate)
	_tree.set("parameters/fwd/blend_amount", _run)
	_tree.set("parameters/dir/blend_amount", _back)
	_tree.set("parameters/move/blend_amount", _move)
	_tree.set("parameters/aim/blend_amount", _aim)

	# фаза шагов для покачивания камеры: π на шаг (|sin| — одна волна на шаг)
	var cycles := lerpf(walk_rate / _walk_len, jog_rate / _jog_len, _run) * _move
	step_phase += delta * TAU * cycles

	# крен в поворот и наклон от разгона — поверх клипа
	var lean_fwd := clampf(accel * lean_accel, -0.15, 0.15) * (1.0 - _aim)
	var lean_roll := clampf(-yaw_rate * lean_turn * clampf(spd / 2.0, 0.0, 1.5), -0.25, 0.25)
	_lean = _lean.lerp(Vector2(lean_fwd, lean_roll), 1.0 - exp(-6.0 * delta))
	if _lean_mod:
		var br := sin(_time * 1.6) * breath * _aim  # в стойке — заметное дыхание (клип стойки статичный)
		_lean_mod.spine = Vector3(_lean.x + br, 0.0, _lean.y)

	_tree.advance(delta)
