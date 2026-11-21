## Анимации Юрчика — анимации игрока Garry's Mod (assets/animations/gmod/yurchik_gmod.glb,
## собирает tools/blender/retarget_gmod_yurchik.py). В самой модели yurchik.gltf клипов нет:
## AnimationPlayer создаётся здесь, библиотека подключается без имени — клипы зовутся просто «Idle», «PunchA».
## Любой клип библиотеки можно сыграть разово: play_action("Wave"), play_action("GrenadeThrow", true).
## Смешивание — AnimationTree, собирается здесь в коде:
##   стойка ↔ ходьба (вперёд/назад) ↔ бег → присед → прыжок → верх тела: стойка «готов к удару» (ПКМ) → удар (OneShot).
## Скорость проигрывания подгоняется под скорость героя, чтобы ноги не скользили.
## Поверх — процедурный крен в поворотах и наклон при разгоне (YurchikLean).
## Разовые действия (бросок, получил удар, вырывается, взаимодействие) — play_action(); смерть — play_death().
extends Node3D

const GMOD_LIB := "res://assets/animations/gmod/yurchik_gmod.glb"
## зацикленные клипы библиотеки (флаг loop в assets/animations/gmod/clips.json)
const GMOD_LOOPS := ["Idle", "Walk", "WalkBack", "WalkLeft", "WalkRight", "Run", "RunBack", "RunLeft", "RunRight",
		"CrouchIdle", "CrouchWalk", "CrouchWalkBack", "CrouchWalkLeft", "CrouchWalkRight", "IdleAngry", "IdleScared",
		"IdleSubtle", "FistsIdle", "RunPanicked", "Swim", "SwimIdle", "Sit", "SitZen"]
const LEGS := ["ThighL", "ShinL", "FootL", "ThighR", "ShinR", "FootR"]
const LOWER := ["Pelvis", "ThighL", "ShinL", "FootL", "ThighR", "ShinR", "FootR"]
const BODY := ["Pelvis", "Spine", "UpperArmL", "ForearmL", "HandL", "UpperArmR", "ForearmR", "HandR"]
const JUMP_CHAINS := ["", "b_"]       ## цепочки клипа прыжка: для ног и для тела (см. _build_tree)

@export_group("Клипы")
## скорость опорной стопы клипов при ×1 — foot_speed из assets/animations/gmod/clips.json
@export var walk_speed := 1.834
@export var back_speed := 1.483
@export var run_speed := 4.675
@export var crouch_speed := 1.375
@export var crouch_back_speed := 1.41
@export var walk_rate_max := 1.8     ## быстрее ходьбу не крутим — иначе семенит
@export var jog_rate_min := 0.8      ## медленнее бег не крутим — иначе «плывёт»
@export var jog_rate_max := 1.4
@export var attack_rate := 1.0
@export var aim_pose := "FistsIdle"  ## стойка «готов к удару» (ПКМ) — только верх тела
@export var death_clip := "Death3"   ## лёжа на спине; у Death1 и Death4 ноги в конце висят в воздухе (в GMod дальше — рэгдолл)
@export var crouch_response := 8.0
## Прыжок — клип Jump (jump_c из GMod). Кадр клипа (30 к/с) выбирается по фазе прыжка:
## замах на земле: 0 → jump_takeoff_frame; в воздухе по вертикальной скорости vy / скорость отрыва:
## +1 — отрыв (jump_takeoff_frame), 0 — верхняя точка (jump_apex_frame), −1 — уровень отрыва (jump_fall_frame),
## дальше (долгое падение) — к jump_hold_frame. Сход с края без прыжка — сразу поза падения jump_hold_frame.
@export var jump_takeoff_frame := 7.0
@export var jump_apex_frame := 18.0
@export var jump_fall_frame := 32.0
@export var jump_hold_frame := 42.0
@export var windup_squat := 0.12     ## с — до какого места JumpLand приседают ноги в замахе (0.17 — самый низ)
@export var reach_eta := 0.2         ## с до касания — ноги начинают тянуться к земле
@export var air_in := 7.0            ## 1/с — сход с края: как быстро ноги уходят из шага в позу падения
@export var jump_in := 16.0          ## 1/с — то же при прыжке (замах начинается сразу)
@export var air_out_stand := 18.0    ## 1/с — выход из позы при касании с места (клип JumpLand начинается с прямых ног)
@export var air_out_run := 9.0       ## 1/с — то же на бегу: ноги переходят в шаг бега
@export var air_body := 0.8          ## насколько таз, корпус и руки следуют прыжку (ноги — полностью)
@export var land_rate := 1.0
@export var land_max_speed := 1.0    ## м/с — быстрее клип приземления (с места) не играем: ноги сразу продолжают шаг/бег
## фаза цикла (с), где опорная стопа ставится на землю: в неё перематываются шаг и бег при приземлении
@export var walk_land_phase := 0.17
@export var run_land_phase := 0.13

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
## ставит player.gd: замах прыжка 0..1 (< 0 — нет замаха); скорость отрыва, м/с (0 — не прыгал, а упал);
## сколько секунд до касания земли при падении
var jump_windup := -1.0
var jump_v0 := 0.0
var land_eta := 9.0

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
var _walk_len := 1.0
var _jog_len := 0.6
var _crouch := 0.0
var _crouch_move := 0.0
var _air_time := 0.0
var _air := 0.0
var _squat := 0.0
var _reach := 0.0


func _ready() -> void:
	var lib := load(GMOD_LIB) as AnimationLibrary
	if lib == null:
		push_error("yurchik_anim: нет %s — Юрчик без анимаций" % GMOD_LIB)
		return
	for n: String in GMOD_LOOPS:
		if lib.has_animation(n):
			lib.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	# корень модели — узел, от которого идут пути дорожек библиотеки («Yurchik/Skeleton3D:Pelvis»)
	var root: Node = self
	for c in get_children():
		if c.has_node("Yurchik/Skeleton3D"):
			root = c
	_anim = AnimationPlayer.new()
	_anim.name = "AnimationPlayer"
	root.add_child(_anim)
	_anim.root_node = NodePath("..")
	_anim.add_animation_library("", lib)
	_walk_len = _anim.get_animation("Walk").length
	_jog_len = _anim.get_animation("Run").length

	_tree = AnimationTree.new()
	_tree.name = "AnimationTree"
	root.add_child(_tree)
	_tree.anim_player = _tree.get_path_to(_anim)
	_tree.root_node = _tree.get_path_to(root)
	_tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	_bt = _build_tree()
	_tree.tree_root = _bt
	_tree.active = true
	for pre: String in JUMP_CHAINS:
		for key: String in ["jump", "reach", "squat"]:
			_tree.set("parameters/%s%s_ts/scale" % [pre, key], 0.0)
		_tree.set("parameters/%sreach_seek/seek_request" % pre, 0.0)

	var sk := find_children("*", "Skeleton3D", true, false)
	if sk.size() > 0:
		_lean_mod = YurchikLean.new()
		_lean_mod.name = "Lean"
		(sk[0] as Skeleton3D).add_child(_lean_mod)


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


## Клип, кадр которого задаётся каждый кадр через parameters/<key>_seek/seek_request:
## сам он не идёт (<key>_ts — масштаб времени 0).
func _seek_clip(bt: AnimationNodeBlendTree, key: String, clip: String) -> void:
	bt.add_node(key + "_clip", _clip(clip))
	bt.add_node(key + "_seek", AnimationNodeTimeSeek.new())
	bt.add_node(key + "_ts", AnimationNodeTimeScale.new())
	bt.connect_node(key + "_seek", 0, key + "_clip")
	bt.connect_node(key + "_ts", 0, key + "_seek")


func _build_tree() -> AnimationNodeBlendTree:
	var bt := AnimationNodeBlendTree.new()
	bt.add_node("idle", _clip("Idle"))
	for n: String in ["walk", "back", "jog", "attack_clip"]:
		var src: String = {"walk": "Walk", "back": "WalkBack", "jog": "Run", "attack_clip": "PunchA"}[n]
		bt.add_node(n, _clip(src))
		bt.add_node(n + "_ts", AnimationNodeTimeScale.new())
		if n == "walk" or n == "jog":   # перемотка цикла при приземлении — см. _update_crouch_air
			bt.add_node(n + "_seek", AnimationNodeTimeSeek.new())
			bt.connect_node(n + "_seek", 0, n)
			bt.connect_node(n + "_ts", 0, n + "_seek")
		else:
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

	# присед: стойка ↔ шаг вперёд/назад вприсядку; ветка смешивается с обычной по _crouch
	bt.add_node("c_idle", _clip("CrouchIdle"))
	for n: String in ["c_walk", "c_back"]:
		bt.add_node(n, _clip("CrouchWalk" if n == "c_walk" else "CrouchWalkBack"))
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

	# прыжок (Jump — jump_c из GMod, собранный как $MakeJump). Клип не играет сам по себе:
	# кадр выбирается по фазе прыжка (_update_crouch_air) — замах на земле, толчок, группировка
	# в верхней точке, снижение. Перед касанием ноги тянутся к земле (кадр 0 клипа — «reach»).
	# На земле, пока идёт замах, ноги приседают по началу JumpLand (там стопы стоят на полу).
	# Выход узла в дереве идёт только в один вход, поэтому цепочек две: для ног (air)
	# и для таза, корпуса и рук (air_body, префикс «b_»).
	# Ноги — полностью, тело — с весом air_body: камера от первого лица не ныряет за наклоном таза
	for pre: String in JUMP_CHAINS:
		_seek_clip(bt, pre + "jump", "Jump")
		_seek_clip(bt, pre + "reach", "Jump")
		_seek_clip(bt, pre + "squat", "JumpLand")
		var reach := AnimationNodeBlend2.new()
		_filter(reach, LEGS)
		bt.add_node(pre + "reach_mix", reach)
		bt.connect_node(pre + "reach_mix", 0, pre + "jump_ts")
		bt.connect_node(pre + "reach_mix", 1, pre + "reach_ts")
		var squat := AnimationNodeBlend2.new()
		_filter(squat, LOWER)
		bt.add_node(pre + "squat_mix", squat)
		bt.connect_node(pre + "squat_mix", 0, pre + "reach_mix")
		bt.connect_node(pre + "squat_mix", 1, pre + "squat_ts")
	var air := AnimationNodeBlend2.new()
	_filter(air, LEGS)
	bt.add_node("air", air)
	bt.connect_node("air", 0, "crouch")
	bt.connect_node("air", 1, "squat_mix")
	var body := AnimationNodeBlend2.new()
	_filter(body, BODY)
	bt.add_node("air_body", body)
	bt.connect_node("air_body", 0, "air")
	bt.connect_node("air_body", 1, "b_squat_mix")

	# приземление: ноги пружинят (JumpLand начинается с прямых ног — как поза «reach»)
	var land := AnimationNodeOneShot.new()
	land.fadein_time = 0.05
	land.fadeout_time = 0.2
	_filter(land, LOWER)
	bt.add_node("land", land)
	bt.add_node("land_clip", _clip("JumpLand"))
	bt.add_node("land_ts", AnimationNodeTimeScale.new())
	bt.connect_node("land_ts", 0, "land_clip")
	bt.connect_node("land", 0, "air_body")
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
	bt.add_node("aim_pose", _clip(aim_pose))
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
		bt.add_node(key + "_clip", _clip("FlinchStomach"))
		bt.add_node(key + "_ts", AnimationNodeTimeScale.new())
		bt.connect_node(key + "_ts", 0, key + "_clip")
		bt.connect_node(key, 1, key + "_ts")
	bt.connect_node("act_upper", 0, "attack")
	bt.connect_node("act_full", 0, "act_upper")
	bt.connect_node("output", 0, "act_full")
	return bt


## Разовое действие: имя клипа библиотеки (FlinchStomach, FlinchHead, GrenadeThrow, ItemPlace, Wave, Laugh…);
## upper — только верх тела (жесты с предметами в GMod играются только на верх).
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
	_anim.play(death_clip, 0.15)


## clip — удар молотком или кулаком (имена клипов задаёт player.gd).
func play_attack(clip: String) -> void:
	if _tree:
		if _anim.has_animation(clip):
			(_bt.get_node("attack_clip") as AnimationNodeAnimation).animation = clip
		_tree.set("parameters/attack_clip_ts/scale", attack_rate)
		_tree.set("parameters/attack/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


## Длина удара в секундах — по ней player.gd считает, когда удар закончится.
func attack_length(clip: String) -> float:
	if _anim and _anim.has_animation(clip):
		return _anim.get_animation(clip).length / attack_rate
	return 0.83


## speed — со знаком (назад < 0); sprint 0..1; state: 0 обычный, 1 замах (ПКМ), 2 удар;
## move_angle — куда идёт герой относительно взгляда, рад (0 — вперёд, > 0 — влево);
## crouching — сидит на корточках; air — в воздухе (прыжок, падение); vy — вертикальная скорость, м/с.
func update_anim(delta: float, speed: float, _sprint: float, state: int, yaw_rate: float, accel: float,
		move_angle := 0.0, crouching := false, air := false, vy := 0.0) -> void:
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
	var walk_rate := clampf(spd / walk_speed, 0.6, walk_rate_max)
	var jog_rate := clampf(spd / run_speed, jog_rate_min, jog_rate_max)
	_tree.set("parameters/walk_ts/scale", walk_rate)
	_tree.set("parameters/back_ts/scale", clampf(spd / back_speed, 0.6, walk_rate_max))
	_tree.set("parameters/jog_ts/scale", jog_rate)
	_tree.set("parameters/fwd/blend_amount", _run)
	_tree.set("parameters/dir/blend_amount", _back)
	_tree.set("parameters/move/blend_amount", _move)
	_tree.set("parameters/aim/blend_amount", _aim)
	_update_crouch_air(delta, speed, crouching, air, vy)

	# фаза шагов для покачивания камеры: π на шаг (|sin| — одна волна на шаг)
	var cycles := lerpf(walk_rate / _walk_len, jog_rate / _jog_len, _run) * _move
	if _crouch > 0.5:   # вприсядку шаги — по клипу CrouchWalk
		cycles = clampf(spd / crouch_speed, 0.5, 1.6) / _anim.get_animation("CrouchWalk").length * _move
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


func _update_crouch_air(delta: float, speed: float, crouching: bool, air: bool, vy: float) -> void:
	var spd := absf(speed)
	_crouch = lerpf(_crouch, 1.0 if crouching and not air else 0.0, 1.0 - exp(-crouch_response * delta))
	_crouch_move = lerpf(_crouch_move, smoothstep(0.1, 0.4, spd), 1.0 - exp(-blend_response * delta))
	_tree.set("parameters/c_walk_ts/scale", clampf(spd / crouch_speed, 0.5, 1.6))
	_tree.set("parameters/c_back_ts/scale", clampf(spd / crouch_back_speed, 0.5, 1.6))
	_tree.set("parameters/c_dir/blend_amount", _back)
	_tree.set("parameters/c_move/blend_amount", _crouch_move)
	_tree.set("parameters/crouch/blend_amount", _crouch)

	# на бегу (moving → 1) без клипа приземления: иначе ноги на полсекунды замирают в стойке,
	# а герой едет дальше — цикл бега продолжается с касания опорной стопы
	var moving := smoothstep(move_from, land_max_speed * 1.5, spd)
	if air:
		_air_time += delta
	elif _air_time > 0.0:
		if _air_time > 0.25:     # короткий отрыв (ступенька) не считаем прыжком
			if spd < land_max_speed:
				_tree.set("parameters/land_ts/scale", land_rate)
				_tree.set("parameters/land/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
			else:
				_tree.set("parameters/walk_seek/seek_request", walk_land_phase)
				_tree.set("parameters/jog_seek/seek_request", run_land_phase)
		_air_time = 0.0
	# вес прыжка: замах и прыжок — сразу; сход с края — только если в воздухе дольше мгновения
	# (ступенька — не прыжок); вход и выход плавные (smoothstep), без рывка в начале и в конце
	var winding := jump_windup >= 0.0 and not air
	var jumping := winding or (air and jump_v0 > 0.0)
	var target := 1.0 if jumping or (air and _air_time > 0.06) else 0.0
	var rate := (jump_in if jumping else air_in) if target > _air else lerpf(air_out_stand, air_out_run, moving)
	_air = move_toward(_air, target, delta * rate)
	var w := smoothstep(0.0, 1.0, _air)
	_tree.set("parameters/air/blend_amount", w)
	_tree.set("parameters/air_body/blend_amount", w * air_body)

	# кадр клипа прыжка по фазе
	var frame := jump_hold_frame
	if winding:
		frame = jump_windup * jump_takeoff_frame
	elif air and jump_v0 > 0.0:
		var u := vy / jump_v0
		if u >= 0.0:
			frame = lerpf(jump_apex_frame, jump_takeoff_frame, minf(u, 1.0))
		elif u >= -1.0:
			frame = lerpf(jump_apex_frame, jump_fall_frame, -u)
		else:
			frame = lerpf(jump_fall_frame, jump_hold_frame, minf(-u - 1.0, 1.0))
	# замах: ноги приседают (на бегу — меньше); после отрыва быстро переходят на ноги прыжка
	_squat = move_toward(_squat, 1.0 if winding else 0.0, delta * 12.0)
	# перед касанием ноги тянутся к земле (кадр 0 клипа — почти прямые ноги, носки вниз)
	var reach := 0.0
	if air and vy < 0.0:
		reach = 1.0 - smoothstep(reach_eta * 0.4, reach_eta, land_eta)
	_reach = move_toward(_reach, reach, delta * 10.0)
	for pre: String in JUMP_CHAINS:
		if air or winding:
			_tree.set("parameters/%sjump_seek/seek_request" % pre, frame / 30.0)
		if winding:
			_tree.set("parameters/%ssquat_seek/seek_request" % pre, jump_windup * windup_squat)
		_tree.set("parameters/%ssquat_mix/blend_amount" % pre, _squat * lerpf(1.0, 0.5, moving))
		_tree.set("parameters/%sreach_mix/blend_amount" % pre, _reach)
