## Юрчик: управление от первого лица, с инерцией.
## - Камера в голове героя (мышь / правый стик), тело смотрит туда же, куда камера.
##   Своё тело видно (посмотри вниз — ноги), голова спрятана только для камеры, тень — полная.
## - WASD / левый стик — шаг и стрейф относительно взгляда. Скорость идёт к цели по прямой,
##   без дуг и разворотов: вперёд → назад — просто остановился и пошёл назад.
## - Shift / B — бег вперёд (тратит выносливость), разгоняется до бега за долю секунды.
## - ПКМ / LT — замах: камера приближается, медленная ходьба.
## - ЛКМ / RT — удар молотком. С замахом (ПКМ) — сильный: целься выше — в голову, ниже — по ногам.
## - G / RB — бросить бутылку или кирпич. E / A — подобрать, открыть, вырваться из захвата.
## - F / Y — фонарик.
class_name Player
extends CharacterBody3D

signal died

enum State { NORMAL, AIM, ATTACK, HURT, GRABBED, THROW, BUSY, DEAD }

@export_group("Движение")
@export var walk_speed := 1.7         ## под клип ходьбы: быстрее — ноги начинают семенить/скользить
@export var sprint_speed := 4.6
@export var aim_walk_speed := 1.2
@export var back_factor := 0.75        ## назад медленнее
@export var strafe_factor := 0.85      ## вбок чуть медленнее
@export var move_response := 12.0      ## отклик шага: больше — резче разгон и смена направления
@export var stop_response := 16.0      ## отклик остановки, когда отпустил клавиши
@export var run_ramp := 2.2            ## 1/с — как быстро шаг переходит в бег
@export var deceleration := 7.0        ## м/с² — торможение в ударе, броске, анимациях
@export var gravity := 18.0

@export_group("Камера")
@export var mouse_sensitivity := 0.0022
@export var stick_sensitivity := 2.6
@export var look_smoothing := 30.0     ## сглаживание обзора
@export var pitch_min := -1.4
@export var pitch_max := 1.4
@export var eye_height := 1.62         ## высота глаз над полом
@export var eye_follow := 18.0         ## как быстро камера догоняет героя по высоте (ступеньки)
@export var normal_fov := 72.0
@export var sprint_fov_add := 5.0
@export var aim_fov := 58.0
@export var head_bob := 0.03
@export var strafe_roll := 0.008       ## крен камеры при шаге вбок
@export var head_forward := 0.14       ## м — камера чуть впереди кости головы, чтобы плечи и спина оставались сзади
@export var look_down_forward := 0.3   ## м — глядя вниз, камера выносится вперёд, чтобы видеть ноги, а не грудь
@export var focus_size := 0.45         ## м — насколько можно промахнуться взглядом мимо предмета, чтобы он подсветился

@export_group("Выносливость")
@export var max_stamina := 100.0
@export var sprint_cost := 8.0         ## в секунду (полной полоски хватает на ~12 с бега)
@export var attack_cost := 9.0
@export var heavy_attack_cost := 16.0
@export var stamina_regen := 30.0      ## в секунду
@export var stamina_delay := 0.6       ## пауза перед восстановлением
@export var recover_level := 25.0      ## выдохся — не побежит, пока не накопит столько

@export_group("Бой")
@export var attack_time := 0.83        ## берётся из длины клипа удара, если он есть
@export var attack_lunge := 1.2
@export var lunge_window := Vector2(0.5, 0.72)  ## доля удара, когда герой подаётся вперёд
@export var hit_moment := 0.64         ## доля удара, когда молоток «прилетает»
@export var attack_reach := 1.75       ## м
@export var attack_arc := 62.0         ## градусов в каждую сторону
@export var light_damage := 1.0
@export var heavy_damage := 2.0
@export var throw_speed := 15.0

@export_group("Звук")
@export var step_sound := "step_snow"
@export var step_variants := 4

var state := State.NORMAL
var cam_yaw := 0.0
var cam_pitch := -0.12
var move_speed := 0.0
var stamina := 100.0
var exhausted := false
var control := true                    ## false — игрок не управляет (катсцена, меню)
var focus: Interactable                ## на что сейчас можно нажать E
var escape := 0.0                      ## прогресс вырывания из захвата 0..1

var _yaw_target := 0.0
var _pitch_target := -0.12
var _timer := 0.0
var _aim_blend := 0.0
var _sprint_blend := 0.0
var _attack_buffer := 0.0
var _throw_buffer := 0.0
var _prev_yaw := 0.0
var _yaw_rate := 0.0
var _prev_speed := 0.0
var _cam_pos := Vector3.ZERO
var _cam_roll := 0.0
var _head_lead := 0.0
var _skel: Skeleton3D
var _head_bone := -1
var _stam_cd := 0.0
var _attack_heavy := false
var _hit_done := false
var _invuln := 0.0
var _knock := Vector3.ZERO
var _shake := 0.0
var _grabber: Enemy
var _grab_immune := 0.0
var _throw_id := ""
var _thrown := false
var _last_step := 0
var _sprinting := false
var _run := 0.0                        ## 0 — шаг, 1 — полный бег

@onready var model: Node3D = $Model
@onready var cam_pivot: Node3D = $CamPivot
@onready var camera: Camera3D = $CamPivot/Camera
@onready var flashlight: SpotLight3D = $CamPivot/Camera/Flashlight

## Слой отрисовки тела героя. Фонарик в голове не отбрасывает от него тень (shadow_caster_mask
## в player.tscn), иначе тень от собственных плеч и рук падала бы прямо перед глазами.
const BODY_LAYER := 1 << 19
## Кости, которые камера не должна видеть: иначе голова изнутри закрывает обзор.
const HIDDEN_BONES := ["Head"]


func _ready() -> void:
	add_to_group("player")
	cam_pivot.top_level = true
	cam_yaw = rotation.y
	_yaw_target = cam_yaw
	_prev_yaw = rotation.y
	_cam_pos = global_position + Vector3.UP * eye_height
	cam_pivot.global_position = _cam_pos
	for v: Node in model.find_children("*", "VisualInstance3D", true, false):
		(v as VisualInstance3D).layers = BODY_LAYER
	_make_first_person_body()
	var sk := model.find_children("*", "Skeleton3D", true, false)
	if sk.size() > 0:
		_skel = sk[0] as Skeleton3D
		_head_bone = _skel.find_bone("Head")
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


## Тело от первого лица: у каждого меша со скелетом делаем копию для камеры, в которой вершины
## головы стянуты в точку шеи (через bind pose копии Skin). Оригинал остаётся только для теней —
## поэтому тень у Юрчика с головой, а камера не упирается в затылок изнутри.
func _make_first_person_body() -> void:
	for m: Node in model.find_children("*", "MeshInstance3D", true, false):
		var mi := m as MeshInstance3D
		if mi.skin == null:
			continue
		var sk := mi.get_node_or_null(mi.skeleton) as Skeleton3D
		var skin := mi.skin.duplicate() as Skin
		for i in skin.get_bind_count():
			var bone := skin.get_bind_name(i)
			if bone == &"" and sk and skin.get_bind_bone(i) >= 0:
				bone = sk.get_bone_name(skin.get_bind_bone(i))
			if bone in HIDDEN_BONES:
				skin.set_bind_pose(i, Transform3D(Basis.from_scale(Vector3.ONE * 0.001), Vector3.ZERO) * skin.get_bind_pose(i))
		var view := mi.duplicate() as MeshInstance3D
		view.name = mi.name + "FirstPerson"
		view.skin = skin
		view.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
		mi.add_sibling(view)


func is_dead() -> bool:
	return state == State.DEAD


func is_aiming() -> bool:
	return state == State.AIM or (state == State.ATTACK and _attack_heavy)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var s := mouse_sensitivity * (0.65 if state == State.AIM else 1.0)
		_yaw_target -= event.relative.x * s
		_pitch_target = clampf(_pitch_target - event.relative.y * s, pitch_min, pitch_max)
	if not control or state == State.DEAD:
		return
	if event.is_action_pressed("attack"):
		_attack_buffer = 0.2
	if event.is_action_pressed("throw"):
		_throw_buffer = 0.2
	if event.is_action_pressed("flashlight"):
		flashlight.visible = not flashlight.visible
		Game.sfx("click", null, -6.0)
	if event.is_action_pressed("interact"):
		if state == State.GRABBED:
			_mash()
		elif focus and (state == State.NORMAL or state == State.AIM):
			focus.interact(self)


func _physics_process(delta: float) -> void:
	_attack_buffer = maxf(_attack_buffer - delta, 0.0)
	_throw_buffer = maxf(_throw_buffer - delta, 0.0)
	_invuln = maxf(_invuln - delta, 0.0)
	_grab_immune = maxf(_grab_immune - delta, 0.0)

	var look := Input.get_vector("look_left", "look_right", "look_up", "look_down")
	_yaw_target -= look.x * stick_sensitivity * delta
	_pitch_target = clampf(_pitch_target - look.y * stick_sensitivity * 0.7 * delta, pitch_min, pitch_max)
	var ls := 1.0 - exp(-look_smoothing * delta)
	cam_yaw = lerp_angle(cam_yaw, _yaw_target, ls)
	cam_pitch = lerpf(cam_pitch, _pitch_target, ls)

	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back") if control else Vector2.ZERO
	_sprinting = control and Input.is_action_pressed("run") and input.y < -0.3 and state == State.NORMAL and not exhausted
	_run = move_toward(_run, 1.0 if _sprinting else 0.0, delta * (run_ramp if _sprinting else run_ramp * 2.0))
	var readied := control and Input.is_action_pressed("ready_weapon")
	var hv := Vector3(velocity.x, 0.0, velocity.z)

	match state:
		State.NORMAL:
			if readied:
				state = State.AIM
			elif _attack_buffer > 0.0:
				_attack_buffer = 0.0
				_start_attack()
			elif _throw_buffer > 0.0:
				_throw_buffer = 0.0
				_start_throw()
			hv = _move(hv, input, walk_speed, delta)
		State.AIM:
			hv = _move(hv, input, aim_walk_speed, delta)
			if not readied:
				state = State.NORMAL
			elif _attack_buffer > 0.0:
				_attack_buffer = 0.0
				_start_attack()
			elif _throw_buffer > 0.0:
				_throw_buffer = 0.0
				_start_throw()
		State.ATTACK:
			_timer -= delta
			var t := 1.0 - _timer / attack_time
			var target_speed := attack_lunge if (t > lunge_window.x and t < lunge_window.y) else 0.0
			move_speed = move_toward(move_speed, target_speed, 12.0 * delta)
			hv = -global_basis.z * move_speed
			if not _hit_done and t >= hit_moment:
				_hit_done = true
				_do_hit()
			if _timer <= 0.0:
				state = State.AIM if readied else State.NORMAL
		State.HURT:
			_timer -= delta
			_knock = _knock.move_toward(Vector3.ZERO, 9.0 * delta)
			hv = _knock
			move_speed = 0.0
			if _timer <= 0.0:
				state = State.NORMAL
		State.GRABBED:
			hv = Vector3.ZERO
			move_speed = 0.0
			escape = maxf(escape - 0.2 * delta, 0.0)
			if not is_instance_valid(_grabber) or not _grabber.is_grabbing():
				grab_release()
			else:
				var to := _grabber.global_position - global_position
				_yaw_target = lerp_angle(_yaw_target, atan2(-to.x, -to.z), 1.0 - exp(-6.0 * delta))
		State.THROW:
			_timer -= delta
			hv = _move(hv, input, aim_walk_speed * 0.6, delta)
			if not _thrown and _timer <= 0.42:
				_thrown = true
				_release_throw()
			if _timer <= 0.0:
				state = State.NORMAL
		State.BUSY:
			_timer -= delta
			hv = hv.move_toward(Vector3.ZERO, deceleration * 2.0 * delta)
			move_speed = hv.length()
			if _timer <= 0.0:
				state = State.NORMAL
		State.DEAD:
			hv = hv.move_toward(Vector3.ZERO, deceleration * delta)
			move_speed = 0.0

	if state != State.DEAD:
		rotation.y = cam_yaw
	velocity.x = hv.x
	velocity.z = hv.z
	if not is_on_floor():
		velocity.y -= gravity * delta
	else:
		velocity.y = -0.5
	move_and_slide()
	# если упёрлись в стену — скорость тоже гаснет
	move_speed = minf(move_speed, Vector3(velocity.x, 0, velocity.z).length() + 0.9)

	_update_stamina(delta)
	_update_focus()

	# параметры для анимации: угловая скорость и ускорение
	_yaw_rate = lerpf(_yaw_rate, wrapf(rotation.y - _prev_yaw, -PI, PI) / delta, 1.0 - exp(-10.0 * delta))
	_prev_yaw = rotation.y
	var accel := (move_speed - _prev_speed) / delta
	_prev_speed = move_speed
	var planar := Vector3(velocity.x, 0.0, velocity.z)
	var signed := planar.length() * (-1.0 if planar.dot(-global_basis.z) < -0.3 * planar.length() else 1.0)
	_sprint_blend = _run
	var local := global_basis.inverse() * planar
	var move_angle := atan2(-local.x, -local.z) if planar.length() > 0.2 else 0.0
	model.update_anim(delta, signed, _sprint_blend, _anim_state(), _yaw_rate, accel, move_angle)
	_footsteps()
	_update_camera(delta)


## Шаг от первого лица. input — WASD в осях взгляда, base — скорость шага в этом состоянии.
## Цель скорости считается в осях взгляда (назад и вбок медленнее), а текущая скорость догоняет её
## по прямой: при смене направления герой замедляется и идёт в новую сторону, без дуг и заноса.
## Бег (только вперёд) набирается отдельно через _run в _physics_process, поэтому направление не «плывёт».
func _move(hv: Vector3, input: Vector2, base: float, delta: float) -> Vector3:
	var fwd := -input.y
	var local := Vector3(input.x * strafe_factor, 0.0, -fwd * (1.0 if fwd >= 0.0 else back_factor))
	var speed := lerpf(base, sprint_speed, _run) if state == State.NORMAL else base
	var target := Basis(Vector3.UP, cam_yaw) * local * speed
	var k := move_response if target.length() > 0.01 else stop_response
	hv = hv.lerp(target, 1.0 - exp(-k * delta))
	move_speed = hv.length()
	return hv


# ----------------------------------------------------------------------------- выносливость
func _spend(amount: float) -> void:
	stamina = maxf(stamina - amount, 0.0)
	_stam_cd = stamina_delay
	if stamina <= 0.0:
		exhausted = true


func _update_stamina(delta: float) -> void:
	if _sprinting and move_speed > walk_speed:
		_spend(sprint_cost * delta)
		return
	_stam_cd -= delta
	if _stam_cd <= 0.0:
		stamina = minf(stamina + stamina_regen * delta, max_stamina)
	if exhausted and stamina >= recover_level:
		exhausted = false


# ----------------------------------------------------------------------------- удар молотком
func _start_attack() -> void:
	if stamina < 5.0:
		return
	_attack_heavy = Input.is_action_pressed("ready_weapon")
	_spend(heavy_attack_cost if _attack_heavy else attack_cost)
	state = State.ATTACK
	_hit_done = false
	model.attack_rate = 1.0 if _attack_heavy else 1.2
	if model.has_method("attack_length"):
		attack_time = model.attack_length()
	_timer = attack_time
	if _attack_heavy:
		rotation.y = cam_yaw
	model.play_attack()
	get_tree().create_timer(attack_time * (hit_moment - 0.2)).timeout.connect(
		func() -> void: Game.sfx("swing", global_position + Vector3.UP * 1.4, -6.0))


func _do_hit() -> void:
	var fwd := -global_basis.z
	var best: Node3D = null
	var best_d := 1e9
	for e: Node3D in get_tree().get_nodes_in_group("enemy"):
		if not e.has_method("take_hit"):
			continue
		var to := e.global_position - global_position
		to.y = 0.0
		var d := to.length()
		if d > attack_reach + 0.25 or absf(e.global_position.y - global_position.y) > 1.5:
			continue
		if d > 0.5 and rad_to_deg(fwd.angle_to(to)) > attack_arc:
			continue
		if d < best_d:
			best = e
			best_d = d
	Game.emit_noise(global_position, 7.0)
	if best == null:
		return
	var zone := _aim_zone(best) if _attack_heavy else "body"
	var hit_h: float = {"head": 1.6, "legs": 0.5}.get(zone, 1.15)
	var hit_at := best.global_position + Vector3.UP * hit_h
	best.take_hit(heavy_damage if _attack_heavy else light_damage, zone, global_position, _attack_heavy)
	Game.sfx_rand("hit", 3, hit_at, 2.0)
	Game.fx_burst(hit_at)
	Game.hitstop(0.08 if _attack_heavy else 0.05)
	shake(0.7 if _attack_heavy else 0.4)


## Куда пришёлся сильный удар — по тому, на какую высоту врага смотрит камера.
func _aim_zone(e: Node3D) -> String:
	var o := camera.global_position
	var d := -camera.global_basis.z
	var den := d.x * d.x + d.z * d.z
	if den < 0.001:
		return "body"
	var t := ((e.global_position.x - o.x) * d.x + (e.global_position.z - o.z) * d.z) / den
	var s: float = e.get("model_scale") if e.get("model_scale") != null else 1.0
	var h := (o.y + d.y * t - e.global_position.y) / s
	if h > 1.43:
		return "head"
	if h < 0.85:
		return "legs"
	return "body"


func shake(amount: float) -> void:
	_shake = maxf(_shake, amount)


# ----------------------------------------------------------------------------- бросок
func _start_throw() -> void:
	_throw_id = Game.current_throwable()
	if _throw_id == "":
		Game.say("Бросать нечего.")
		return
	state = State.THROW
	_timer = 0.8
	_thrown = false
	model.play_action("Throw", true, 1.6)


func _release_throw() -> void:
	if not Game.remove_item(_throw_id):
		return
	var p := Projectile.new()
	p.setup(_throw_id)
	get_parent().add_child(p)
	p.global_position = global_position + Vector3.UP * 1.55 + global_basis * Vector3(0.28, 0.0, -0.45)
	var dir := (-camera.global_basis.z + Vector3.UP * 0.10).normalized()
	p.linear_velocity = dir * throw_speed + Vector3(velocity.x, 0.0, velocity.z) * 0.5
	p.angular_velocity = Vector3(randf_range(-8, 8), randf_range(-3, 3), randf_range(-8, 8))
	p.add_collision_exception_with(self)
	Game.sfx("throw", global_position + Vector3.UP * 1.5, -4.0)


# ----------------------------------------------------------------------------- урон, захват, смерть
func take_damage(amount: float, from: Vector3, heavy := false) -> void:
	if state == State.DEAD or _invuln > 0.0:
		return
	if Game.god:
		return
	Game.hp = maxf(Game.hp - amount, 0.0)
	Game.health_changed.emit()
	_invuln = 0.5
	shake(0.9 if heavy else 0.5)
	if Game.hp <= 0.0:
		_die()
		return
	Game.sfx_rand("player_hurt", 2, null, -2.0)
	if state == State.GRABBED:
		return
	if state == State.ATTACK and not heavy and _timer < attack_time * 0.7:
		return                                                       # замах уже пошёл — слабый удар его не сбивает
	state = State.HURT
	_timer = 0.6 if heavy else 0.32
	var away := global_position - from
	away.y = 0.0
	_knock = away.normalized() * (4.5 if heavy else 1.8)
	model.play_action("HitHead" if heavy else "HitChest")


## Урон «по чуть-чуть», пока офник держит (без оглушения и неуязвимости).
func take_grab_damage(amount: float) -> void:
	if state == State.DEAD or Game.god:
		return
	Game.hp = maxf(Game.hp - amount, 0.0)
	Game.health_changed.emit()
	if Game.hp <= 0.0:
		_die()


func can_be_grabbed() -> bool:
	return _grab_immune <= 0.0 and state in [State.NORMAL, State.AIM, State.HURT, State.THROW]


func grab_start(enemy: Enemy) -> bool:
	if not can_be_grabbed():
		return false
	state = State.GRABBED
	_grabber = enemy
	escape = 0.0
	model.play_action("Push")
	Game.sfx("struggle", global_position + Vector3.UP, -2.0)
	return true


func _mash() -> void:
	escape += 0.17
	shake(0.25)
	if escape >= 1.0:
		var g := _grabber
		grab_release()
		if is_instance_valid(g):
			g.grab_broken()
		Game.sfx("punch", global_position + Vector3.UP, 0.0)


func grab_release() -> void:
	if state == State.GRABBED:
		state = State.NORMAL
	_grabber = null
	_grab_immune = 2.5
	escape = 0.0
	model.stop_action()


func _die() -> void:
	state = State.DEAD
	_grabber = null
	Game.stats["deaths"] += 1
	Game.sfx("player_die", null, -2.0)
	model.play_death()
	died.emit()


## Занять героя на время (отпирает дверь, подбирает вещь) — он останавливается и не атакует.
func busy(duration: float, anim := "") -> void:
	if state == State.DEAD or state == State.GRABBED:
		return
	state = State.BUSY
	_timer = duration
	if anim != "":
		model.play_action(anim, true)


# ----------------------------------------------------------------------------- взаимодействие
func _update_focus() -> void:
	focus = null
	if not control or not (state == State.NORMAL or state == State.AIM):
		return
	# фокус — то, на что смотрит камера: предмет в радиусе и близко к линии взгляда
	var best := 1e9
	var eye := camera.global_position
	var look := -camera.global_basis.z
	for it: Node in get_tree().get_nodes_in_group("interactable"):
		var i := it as Interactable
		if i == null or not i.enabled:
			continue
		var to := i.global_position - global_position
		var dy := absf(to.y - 0.9)
		to.y = 0.0
		if to.length() > i.radius or dy > 1.6:
			continue
		var ray := i.global_position - eye
		var dist := ray.length()
		var miss := look.angle_to(ray) if dist > 0.01 else 0.0
		if miss > maxf(atan2(focus_size, dist), deg_to_rad(8.0)):
			continue
		if miss < best:
			best = miss
			focus = i


func _footsteps() -> void:
	var phase: float = model.get("step_phase")
	var n := int(phase / PI)
	if n == _last_step:
		return
	_last_step = n
	if not is_on_floor() or move_speed < 0.5:
		return
	Game.sfx_rand(step_sound, step_variants, null, -11.0 if not _sprinting else -7.0)
	if _sprinting:
		Game.emit_noise(global_position, 9.0)
	elif move_speed > 1.3:
		Game.emit_noise(global_position, 2.5)


func _anim_state() -> int:
	match state:
		State.AIM: return 1
		State.ATTACK: return 2
	return 0


func _update_camera(delta: float) -> void:
	var aiming := state == State.AIM or (state == State.ATTACK and _attack_heavy) or state == State.THROW
	_aim_blend = move_toward(_aim_blend, 1.0 if aiming else 0.0, delta * 4.5)
	var t := _aim_blend * _aim_blend * (3.0 - 2.0 * _aim_blend)

	# покачивание от шагов
	var phase: float = model.get("step_phase")
	var bob_amt := clampf(move_speed / walk_speed, 0.0, 1.6) * head_bob * (1.0 - t * 0.7)
	var bob := Vector3(cos(phase) * bob_amt * 0.5, -absf(sin(phase)) * bob_amt, 0.0)

	# камера в голове: по горизонтали жёстко, по высоте сглаженно (ступеньки); после смерти — к полу
	var dead := state == State.DEAD
	var eye := eye_height
	if _skel and _head_bone >= 0:
		var head_y := (_skel.global_transform * _skel.get_bone_global_pose(_head_bone).origin).y - global_position.y
		eye = minf(eye_height, head_y + 0.17)   # голова наклонилась (бег, удар) — глаза ниже
	var goal := global_position + Vector3.UP * (0.35 if dead else eye)
	_cam_pos.x = goal.x
	_cam_pos.z = goal.z
	_cam_pos.y = lerpf(_cam_pos.y, goal.y, 1.0 - exp(-(3.0 if dead else eye_follow) * delta))
	var side := velocity.dot(global_basis.x)
	_cam_roll = lerpf(_cam_roll, 0.6 if dead else -side * strafe_roll, 1.0 - exp(-(2.0 if dead else 8.0) * delta))
	# камера держится впереди головы: на бегу анимация наклоняет корпус — камера уходит вместе с головой
	var lead := head_forward
	if _skel and _head_bone >= 0:
		var head := _skel.global_transform * _skel.get_bone_global_pose(_head_bone).origin
		lead += (head - global_position).dot(Basis(Vector3.UP, cam_yaw) * Vector3.FORWARD)
	_head_lead = lerpf(_head_lead, lead, 1.0 - exp(-12.0 * delta))
	var down := clampf(-cam_pitch / 1.2, 0.0, 1.0)
	var lean := Vector3(0.0, 0.0, -maxf(_head_lead, look_down_forward * down * down))
	cam_pivot.global_position = _cam_pos + Basis(Vector3.UP, cam_yaw) * (bob + lean)
	cam_pivot.rotation = Vector3(cam_pitch, cam_yaw, _cam_roll)
	camera.fov = lerpf(normal_fov + sprint_fov_add * _sprint_blend, aim_fov, t)

	# тряска от ударов
	_shake = move_toward(_shake, 0.0, delta * 2.6)
	var s := _shake * _shake * 0.06
	camera.h_offset = randf_range(-s, s)
	camera.v_offset = randf_range(-s, s)
