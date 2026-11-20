## Анимации Юрчика. Два набора локомоции (стойка, ходьба, бег), переключаются locomotion или F7:
##   PROCEDURAL — построены процедурно, остальные клипы — из Quaternius «Universal Animation Library» 1 и 2 (CC0);
##     всё собирает tools/blender/retarget_ual_yurchik.py (assets/models/yurchik.gltf);
##   GMOD — анимации игрока Garry's Mod (библиотека «gmod», assets/animations/gmod/yurchik_gmod.glb,
##     собирает tools/blender/retarget_gmod_yurchik.py). Присед и прыжок — всегда из «gmod».
## Любой клип библиотеки можно сыграть разово: play_action("gmod/Wave"), play_action("gmod/GrenadeThrow", true).
## Смешивание — AnimationTree, собирается здесь в коде:
##   стойка ↔ ходьба (вперёд/назад) ↔ бег  →  верх тела: стойка «готов к удару» (ПКМ)  →  удар (OneShot).
## Скорость проигрывания подгоняется под скорость героя, чтобы ноги не скользили.
## Поверх — процедурный крен в поворотах и наклон при разгоне (YurchikLean).
## Разовые действия (бросок, получил удар, вырывается, лечится) — play_action(); смерть — play_death().
extends Node3D

enum Locomotion { PROCEDURAL, GMOD }

const GMOD_LIB := "res://assets/animations/gmod/yurchik_gmod.glb"
## зацикленные клипы библиотеки «gmod» (флаг loop в assets/animations/gmod/clips.json)
const GMOD_LOOPS := ["Idle", "Walk", "WalkBack", "WalkLeft", "WalkRight", "Run", "RunBack", "RunLeft", "RunRight",
		"CrouchIdle", "CrouchWalk", "CrouchWalkBack", "CrouchWalkLeft", "CrouchWalkRight", "IdleAngry", "IdleScared",
		"IdleSubtle", "FistsIdle", "RunPanicked", "Swim", "SwimIdle", "Sit", "SitZen"]
const LEGS := ["ThighL", "ShinL", "FootL", "ThighR", "ShinR", "FootR"]
const LOWER := ["Pelvis", "ThighL", "ShinL", "FootL", "ThighR", "ShinR", "FootR"]

@export var locomotion := Locomotion.PROCEDURAL:  ## набор стойки/ходьбы/бега; F7 в игре переключает
	set(v):
		locomotion = v
		if _tree:
			_apply_locomotion()

@export_group("Клипы")
@export var walk_anim_speed := 1.51  ## м/с, с которой «идут» ноги в клипе Walk при скорости ×1 (foot_speed из сборки)
@export var jog_anim_speed := 4.83   ## то же для Run (им бежит спринт; см. LOCOMOTION в retarget_ual_yurchik.py)
@export var walk_rate_max := 1.8     ## быстрее ходьбу не крутим — иначе семенит
@export var jog_rate_min := 0.8      ## медленнее бег не крутим — иначе «плывёт»
@export var jog_rate_max := 1.4
@export var attack_rate := 1.0

@export_group("Клипы GMod")
## скорость опорной стопы клипов при ×1 — foot_speed из assets/animations/gmod/clips.json
@export var gmod_walk_speed := 1.834
@export var gmod_back_speed := 1.483
@export var gmod_run_speed := 4.675
@export var gmod_crouch_speed := 1.375
@export var gmod_crouch_back_speed := 1.41
@export var crouch_response := 8.0
@export var jump_anim_rate := 1.2    ## секунда в воздухе → секунд клипа Jump (поджатые ноги)
@export var jump_hold := 0.55        ## дальше этого места клипа Jump не идёт — поза держится до приземления
@export var land_rate := 1.0

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

@export_group("Диагонали")
@export var hips_twist_max := 55.0   ## ° — насколько ноги разворачиваются в сторону движения (вперёд по диагонали)
@export var hips_twist_back := 40.0  ## ° — то же при шаге назад по диагонали
@export var hips_response := 8.0

var step_phase := 0.0                ## читает камера для покачивания (одна «волна» на шаг)

const LOOPS := ["Idle", "Walk", "WalkBack", "Run", "AimIdle"]
const UPPER := ["Spine", "Head", "UpperArmL", "ForearmL", "HandL", "UpperArmR", "ForearmR", "HandR"]

var _anim: AnimationPlayer
var _tree: AnimationTree
var _bt: AnimationNodeBlendTree
var _dead := false
var _lean_mod: YurchikLean
var _move := 0.0
var _run := 0.0
var _back := 0.0
var _aim := 0.0
var _lean := Vector2.ZERO
var _time := 0.0
var _hips := 0.0
var _walk_len := 1.333
var _jog_len := 0.733
var _walk_speed := 1.51
var _back_speed := 1.51
var _jog_speed := 4.83
var _has_gmod := false
var _crouch := 0.0
var _crouch_move := 0.0
var _air_time := 0.0


func _ready() -> void:
	var players := find_children("*", "AnimationPlayer", true, false)
	if players.is_empty():
		push_error("yurchik_anim: в модели нет AnimationPlayer — переэкспортируйте yurchik.gltf с анимациями")
		return
	_anim = players[0]
	for n: String in LOOPS:
		if _anim.has_animation(n):
			_anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	var lib := load(GMOD_LIB) as AnimationLibrary
	if lib:
		_anim.add_animation_library("gmod", lib)
		_has_gmod = true
		for n: String in GMOD_LOOPS:
			if lib.has_animation(n):
				lib.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	else:
		push_warning("yurchik_anim: нет %s — присед, прыжок и набор GMod недоступны" % GMOD_LIB)

	_tree = AnimationTree.new()
	_tree.name = "AnimationTree"
	_anim.get_parent().add_child(_tree)
	_tree.anim_player = _tree.get_path_to(_anim)
	_tree.root_node = _tree.get_path_to(_anim.get_node(_anim.root_node))
	_tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	_bt = _build_tree()
	_tree.tree_root = _bt
	_tree.active = true
	_apply_locomotion()

	var sk := find_children("*", "Skeleton3D", true, false)
	if sk.size() > 0:
		_lean_mod = YurchikLean.new()
		_lean_mod.name = "Lean"
		(sk[0] as Skeleton3D).add_child(_lean_mod)


## Ставит клипы стойки, ходьбы и бега из выбранного набора и их скорости шага.
func _apply_locomotion() -> void:
	var gm := locomotion == Locomotion.GMOD and _has_gmod
	var pre := "gmod/" if gm else ""
	for n: String in ["idle", "walk", "back", "jog"]:
		var clip: String = {"idle": "Idle", "walk": "Walk", "back": "WalkBack", "jog": "Run"}[n]
		(_bt.get_node(n) as AnimationNodeAnimation).animation = pre + clip
	_walk_len = _anim.get_animation(pre + "Walk").length
	_jog_len = _anim.get_animation(pre + "Run").length
	_walk_speed = gmod_walk_speed if gm else walk_anim_speed
	_back_speed = gmod_back_speed if gm else walk_anim_speed
	_jog_speed = gmod_run_speed if gm else jog_anim_speed


func _unhandled_input(event: InputEvent) -> void:
	var k := event as InputEventKey
	if k and k.pressed and not k.echo and k.keycode == KEY_F7 and _has_gmod:
		locomotion = Locomotion.GMOD if locomotion == Locomotion.PROCEDURAL else Locomotion.PROCEDURAL
		print("Локомоция Юрчика: ", Locomotion.keys()[locomotion])


func _filter(node: AnimationNode, bones: Array) -> void:
	node.filter_enabled = true
	var ref := _anim.get_animation("Idle")
	for i in ref.get_track_count():
		var path := ref.track_get_path(i)
		if path.get_concatenated_subnames() in bones:
			node.set_filter_path(path, true)


func _clip(n: String) -> AnimationNodeAnimation:
	var a := AnimationNodeAnimation.new()
	a.animation = n
	return a


func _build_tree() -> AnimationNodeBlendTree:
	var bt := AnimationNodeBlendTree.new()
	bt.add_node("idle", _clip("Idle"))
	for n: String in ["walk", "back", "jog", "attack_clip"]:
		var src: String = {"walk": "Walk", "back": "WalkBack", "jog": "Run", "attack_clip": "Attack"}[n]
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
	var base := "move"

	if _has_gmod:
		# присед: стойка ↔ шаг вперёд/назад вприсядку; ветка смешивается с обычной по _crouch
		bt.add_node("c_idle", _clip("gmod/CrouchIdle"))
		for n: String in ["c_walk", "c_back"]:
			bt.add_node(n, _clip("gmod/CrouchWalk" if n == "c_walk" else "gmod/CrouchWalkBack"))
			bt.add_node(n + "_ts", AnimationNodeTimeScale.new())
			bt.connect_node(n + "_ts", 0, n)
		bt.add_node("c_dir", AnimationNodeBlend2.new())
		bt.connect_node("c_dir", 0, "c_walk_ts")
		bt.connect_node("c_dir", 1, "c_back_ts")
		bt.add_node("c_move", AnimationNodeBlend2.new())
		bt.connect_node("c_move", 0, "c_idle")
		bt.connect_node("c_move", 1, "c_dir")
		bt.add_node("crouch", AnimationNodeBlend2.new())
		bt.connect_node("crouch", 0, base)
		bt.connect_node("crouch", 1, "c_move")

		# прыжок: ноги из клипа Jump, место в клипе — по времени в воздухе; руки продолжают шаг.
		# Таз не берём: клип наклоняет его вперёд, а с ним корпус и камеру от первого лица
		bt.add_node("jump_clip", _clip("gmod/Jump"))
		bt.add_node("jump_seek", AnimationNodeTimeSeek.new())
		bt.connect_node("jump_seek", 0, "jump_clip")
		bt.add_node("jump_ts", AnimationNodeTimeScale.new())
		bt.connect_node("jump_ts", 0, "jump_seek")
		var air := AnimationNodeBlend2.new()
		_filter(air, LEGS)
		bt.add_node("air", air)
		bt.connect_node("air", 0, "crouch")
		bt.connect_node("air", 1, "jump_ts")

		# приземление — ноги пружинят
		var land := AnimationNodeOneShot.new()
		land.fadein_time = 0.05
		land.fadeout_time = 0.2
		_filter(land, LOWER)
		bt.add_node("land", land)
		bt.add_node("land_clip", _clip("gmod/JumpLand"))
		bt.add_node("land_ts", AnimationNodeTimeScale.new())
		bt.connect_node("land_ts", 0, "land_clip")
		bt.connect_node("land", 0, "air")
		bt.connect_node("land", 1, "land_ts")
		base = "land"

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
	bt.connect_node("aim", 0, base)
	bt.connect_node("aim", 1, "aim_pose")

	var shot := AnimationNodeOneShot.new()
	shot.fadein_time = 0.06
	shot.fadeout_time = 0.22
	bt.add_node("attack", shot)
	bt.connect_node("attack", 0, "aim")
	bt.connect_node("attack", 1, "attack_clip_ts")

	# разовые действия поверх всего: act_upper — только верх тела (бросок, лечение), act_full — всё тело
	for key: String in ["act_upper", "act_full"]:
		var os := AnimationNodeOneShot.new()
		os.fadein_time = 0.08
		os.fadeout_time = 0.22
		if key == "act_upper":
			os.filter_enabled = true
			for i in ref.get_track_count():
				var path := ref.track_get_path(i)
				if path.get_concatenated_subnames() in UPPER:
					os.set_filter_path(path, true)
		bt.add_node(key, os)
		bt.add_node(key + "_clip", _clip("HitChest"))
		bt.add_node(key + "_ts", AnimationNodeTimeScale.new())
		bt.connect_node(key + "_ts", 0, key + "_clip")
		bt.connect_node(key, 1, key + "_ts")
	bt.connect_node("act_upper", 0, "attack")
	bt.connect_node("act_full", 0, "act_upper")
	bt.connect_node("output", 0, "act_full")
	return bt


## Разовое действие: имя клипа из модели (HitChest, HitHead, Throw, Consume, Push, PickUp, Interact…)
## или из библиотеки «gmod» (gmod/Wave, gmod/Laugh, gmod/FlinchHead…); upper — только верх тела.
func play_action(clip: String, upper := false, rate := 1.0) -> void:
	if _tree == null or _dead or not _anim.has_animation(clip):
		return
	var key := "act_upper" if upper else "act_full"
	(_bt.get_node(key + "_clip") as AnimationNodeAnimation).animation = clip
	_tree.set("parameters/%s_ts/scale" % key, rate)
	_tree.set("parameters/%s/request" % key, AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func stop_action() -> void:
	if _tree == null or _dead:
		return
	for key: String in ["act_upper", "act_full"]:
		_tree.set("parameters/%s/request" % key, AnimationNodeOneShot.ONE_SHOT_REQUEST_FADE_OUT)


## Смерть: дерево смешивания выключается, клип падения доигрывает до конца и замирает.
func play_death() -> void:
	if _tree == null or _dead:
		return
	_dead = true
	_tree.active = false
	if _lean_mod:
		_lean_mod.spine = Vector3.ZERO
		_lean_mod.hips_yaw = 0.0
	_anim.play("Death", 0.15)


## clip — «Attack» (молоток) или «Punch» (кулак, молоток в сумке).
func play_attack(clip := "Attack") -> void:
	if _tree:
		if _anim.has_animation(clip):
			(_bt.get_node("attack_clip") as AnimationNodeAnimation).animation = clip
		_tree.set("parameters/attack_clip_ts/scale", attack_rate)
		_tree.set("parameters/attack/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


## Длина удара в секундах — по ней player.gd считает, когда удар закончится.
func attack_length(clip := "Attack") -> float:
	if _anim and _anim.has_animation(clip):
		return _anim.get_animation(clip).length / attack_rate
	return 0.83


## speed — со знаком (назад < 0); sprint 0..1; state: 0 обычный, 1 замах (ПКМ), 2 удар;
## move_angle — куда идёт герой относительно взгляда, рад (0 — вперёд, > 0 — влево);
## crouch — сидит на корточках; air — в воздухе (прыжок, падение).
func update_anim(delta: float, speed: float, _sprint: float, state: int, yaw_rate: float, accel: float,
		move_angle := 0.0, crouch := false, air := false) -> void:
	if _tree == null or _dead:
		return
	_time += delta
	var spd := absf(speed)
	var k := 1.0 - exp(-blend_response * delta)
	_move = lerpf(_move, smoothstep(move_from, move_to, spd), k)
	_run = lerpf(_run, smoothstep(run_from, run_to, spd) * (1.0 if speed > 0.0 else 0.0), k)
	_back = lerpf(_back, 1.0 if speed < -0.05 else 0.0, k)
	_aim = lerpf(_aim, 1.0 if state == 1 else 0.0, 1.0 - exp(-aim_response * delta))

	# скорость клипов под скорость героя
	var walk_rate := clampf(spd / _walk_speed, 0.6, walk_rate_max)
	var jog_rate := clampf(spd / _jog_speed, jog_rate_min, jog_rate_max)
	_tree.set("parameters/walk_ts/scale", walk_rate)
	_tree.set("parameters/back_ts/scale", clampf(spd / _back_speed, 0.6, walk_rate_max))
	_tree.set("parameters/jog_ts/scale", jog_rate)
	_tree.set("parameters/fwd/blend_amount", _run)
	_tree.set("parameters/dir/blend_amount", _back)
	_tree.set("parameters/move/blend_amount", _move)
	_tree.set("parameters/aim/blend_amount", _aim)
	if _has_gmod:
		_update_crouch_air(delta, speed, crouch, air)

	# фаза шагов для покачивания камеры: π на шаг (|sin| — одна волна на шаг)
	var cycles := lerpf(walk_rate / _walk_len, jog_rate / _jog_len, _run) * _move
	if _crouch > 0.5:   # вприсядку шаги — по клипу CrouchWalk
		cycles = clampf(spd / gmod_crouch_speed, 0.5, 1.6) / _anim.get_animation("gmod/CrouchWalk").length * _move
	if air:
		cycles = 0.0
	step_phase += delta * TAU * cycles

	# крен в поворот и наклон от разгона — поверх клипа
	var lean_fwd := clampf(accel * lean_accel, -0.15, 0.15) * (1.0 - _aim)
	var lean_roll := clampf(-yaw_rate * lean_turn * clampf(spd / 2.0, 0.0, 1.5), -0.25, 0.25)
	_lean = _lean.lerp(Vector2(lean_fwd, lean_roll), 1.0 - exp(-6.0 * delta))
	# по диагонали ноги бегут в сторону движения, корпус остаётся к камере
	var twist := 0.0
	if state != 2:
		if speed < -0.05:
			twist = clampf(wrapf(move_angle - PI, -PI, PI), -deg_to_rad(hips_twist_back), deg_to_rad(hips_twist_back))
		else:
			twist = clampf(move_angle, -deg_to_rad(hips_twist_max), deg_to_rad(hips_twist_max))
	_hips = lerp_angle(_hips, twist * _move, 1.0 - exp(-hips_response * delta))
	if _lean_mod:
		var br := sin(_time * 1.6) * breath * _aim  # в стойке — заметное дыхание (клип стойки статичный)
		_lean_mod.spine = Vector3(_lean.x + br, 0.0, _lean.y)
		_lean_mod.hips_yaw = _hips

	_tree.advance(delta)


func _update_crouch_air(delta: float, speed: float, crouch: bool, air: bool) -> void:
	var spd := absf(speed)
	_crouch = lerpf(_crouch, 1.0 if crouch and not air else 0.0, 1.0 - exp(-crouch_response * delta))
	_crouch_move = lerpf(_crouch_move, smoothstep(0.1, 0.4, spd), 1.0 - exp(-blend_response * delta))
	_tree.set("parameters/c_walk_ts/scale", clampf(spd / gmod_crouch_speed, 0.5, 1.6))
	_tree.set("parameters/c_back_ts/scale", clampf(spd / gmod_crouch_back_speed, 0.5, 1.6))
	_tree.set("parameters/c_dir/blend_amount", _back)
	_tree.set("parameters/c_move/blend_amount", _crouch_move)
	_tree.set("parameters/crouch/blend_amount", _crouch)

	if air:
		_air_time += delta
	elif _air_time > 0.0:
		if _air_time > 0.25:     # короткий отрыв (ступенька) не считаем прыжком
			_tree.set("parameters/land_ts/scale", land_rate)
			_tree.set("parameters/land/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
		_air_time = 0.0
	# ноги поджимаются, если в воздухе дольше мгновения (сход со ступеньки — не прыжок)
	var target := 1.0 if air and _air_time > 0.08 else 0.0
	var cur: float = _tree.get("parameters/air/blend_amount")
	_tree.set("parameters/air/blend_amount", move_toward(cur, target, delta * (10.0 if target > cur else 6.0)))
	_tree.set("parameters/jump_ts/scale", 0.0)
	_tree.set("parameters/jump_seek/seek_request", minf(_air_time * jump_anim_rate, jump_hold))
