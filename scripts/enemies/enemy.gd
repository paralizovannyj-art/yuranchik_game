## Враг: офник или Сергей (is_stalker).
## Поведение: стоит/бродит → замечает (зрение, слух) → преследует → бьёт или хватает.
## От ударов: в голову — оглушение, по ногам — падает, лежачего бить больнее; смерть — падает и остаётся лежать.
## Сергей: не умирает — когда «здоровье» кончается, на время падает на колено, потом встаёт и идёт дальше.
## Все числа ниже можно менять в инспекторе у конкретного врага на уровне.
class_name Enemy
extends CharacterBody3D

signal died_signal(enemy: Enemy)

enum S { IDLE, WANDER, INVESTIGATE, CHASE, ATTACK, GRAB, STAGGER, DOWN, GETUP, STUNNED, DEAD }

@export_group("Кто это")
@export var display_name := "Офник"
@export_enum("random", "a", "b", "c") var variant: String = "random"   ## расцветка одежды
@export var is_stalker := false         ## Сергей: нельзя убить, только оглушить
@export var model_scale := 1.0
@export var max_hp := 4.0

@export_group("Движение")
@export var walk_speed := 0.9           ## бродит
@export var chase_speed := 3.5          ## гонится (у игрока шаг 1.7, спринт 4.6)
@export var turn_rate := 7.0
@export var wander_radius := 4.0        ## 0 — стоит на месте
@export var idle_anim := "ZombieIdle"
@export var wander_anim := "Shamble"
@export var chase_anim := "Run"
@export var chase_anim_speed := 4.98    ## м/с, с которой «бегут» ноги в клипе при скорости ×1

@export_group("Чувства")
@export var sight_range := 15.0         ## если у Юрчика выключен фонарик — видит вдвое хуже
@export var sight_fov := 115.0
@export var hear_scale := 1.0
@export var lose_time := 7.0            ## сколько секунд ищет, потеряв из виду
@export var start_alerted := false

@export_group("Бой")
@export var attack_range := 1.3
@export var attack_damage := 10.0
@export var attack_anim := "Punch"
@export var attack_anim_rate := 0.9
@export var attack_windup := 0.55       ## секунд от начала замаха до удара
@export var attack_total := 1.0
@export var attack_cooldown := 1.3
@export var heavy_hits := false         ## удар отбрасывает игрока
@export var can_grab := true
@export var grab_chance := 0.35
@export var grab_dps := 4.0
@export var grab_time := 4.0
@export var stun_time := 10.0           ## (Сергей) сколько стоит на колене

var state := S.IDLE
var hp := 4.0

var _anim: AnimationPlayer
var _home := Vector3.ZERO
var _target := Vector3.ZERO
var _last_seen := Vector3.ZERO
var _timer := 0.0
var _think := 0.0
var _lost := 0.0
var _attack_cd := 0.0
var _grab_cd := 0.0
var _struck := false
var _path := PackedVector3Array()
var _path_i := 0
var _path_cd := 0.0
var _voice_cd := 0.0
var _step_cd := 0.0
var _sees := false
var _stuck := 0.0

const LOOPS := ["Idle", "Walk", "Run", "Shamble", "ZombieIdle", "Grab", "Crouch", "Scratch"]
const GRAVITY := 18.0


func _ready() -> void:
	add_to_group("enemy")
	hp = max_hp
	_home = global_position
	_think = randf() * 0.3
	_voice_cd = randf_range(3.0, 10.0)
	_timer = randf_range(1.0, 4.0)
	var players := find_children("*", "AnimationPlayer", true, false)
	if players.size() > 0:
		_anim = players[0]
		for n: String in LOOPS:
			if _anim.has_animation(n):
				_anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
		_anim.play(idle_anim)
		_anim.seek(randf() * 1.3)
	_dress()
	Game.noise.connect(_on_noise)
	if start_alerted:
		state = S.CHASE


## Расцветка: одна модель, три текстуры одежды. У Сергея капюшон виден изнутри — отключаем отсечение граней.
func _dress() -> void:
	for mi: MeshInstance3D in find_children("*", "MeshInstance3D", true, false):
		var mat := mi.get_active_material(0) as StandardMaterial3D
		if mat == null:
			continue
		mat = mat.duplicate() as StandardMaterial3D
		if is_stalker:
			mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		else:
			var v: String = variant if variant != "random" else ["a", "b", "c"][randi() % 3]
			var tex := load("res://assets/textures/enemy_%s.png" % v) as Texture2D
			if tex:
				mat.albedo_texture = tex
		mi.set_surface_override_material(0, mat)


func is_dead() -> bool:
	return state == S.DEAD


func is_grabbing() -> bool:
	return state == S.GRAB


func is_passive() -> bool:
	return state == S.IDLE or state == S.WANDER or state == S.INVESTIGATE


func _player() -> Player:
	return get_tree().get_first_node_in_group("player") as Player


func _physics_process(delta: float) -> void:
	_think -= delta
	_attack_cd -= delta
	_grab_cd -= delta
	var player := _player()
	match state:
		S.IDLE, S.WANDER, S.INVESTIGATE:
			_passive(delta, player)
		S.CHASE:
			_chase(delta, player)
		S.ATTACK:
			_attack(delta, player)
		S.GRAB:
			_grab(delta, player)
		S.STAGGER, S.GETUP:
			_slow(delta)
			_timer -= delta
			if _timer <= 0.0:
				state = S.CHASE
		S.DOWN:
			_slow(delta)
			_timer -= delta
			if _timer <= 0.0:
				state = S.GETUP
				_timer = 1.4
				_play("GetUp", 0.15)
		S.STUNNED:
			_slow(delta)
			_timer -= delta
			if _timer <= 0.0:
				hp = max_hp
				state = S.GETUP
				_timer = 1.0
				_play("Idle", 0.5)
				Game.sfx("sergey_roar", global_position + Vector3.UP * 1.6, 2.0)
		S.DEAD:
			_slow(delta)
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	else:
		velocity.y = -0.5
	move_and_slide()
	_voice(delta)


func _slow(delta: float) -> void:
	velocity.x = move_toward(velocity.x, 0.0, 10.0 * delta)
	velocity.z = move_toward(velocity.z, 0.0, 10.0 * delta)


# ----------------------------------------------------------------------------- чувства
func _can_see(player: Player, use_fov: bool) -> bool:
	var to := player.global_position - global_position
	var d := to.length()
	var rng := sight_range * (1.0 if player.flashlight.visible else 0.5)
	if not use_fov:
		rng = sight_range * 1.6
	if d > rng:
		return false
	if use_fov and d > 2.5:
		var flat := Vector3(to.x, 0.0, to.z)
		if rad_to_deg((-global_basis.z).angle_to(flat)) > sight_fov * 0.5:
			return false
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 1.55 * model_scale,
		player.global_position + Vector3.UP * 1.3, 1)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()


func _on_noise(pos: Vector3, radius: float) -> void:
	if not is_passive() or is_stalker:
		return
	if global_position.distance_to(pos) < radius * hear_scale and absf(pos.y - global_position.y) < 2.0:
		_target = pos
		state = S.INVESTIGATE
		_timer = 8.0


func alert(silent := false) -> void:
	if state == S.DEAD or not is_passive():
		return
	state = S.CHASE
	_lost = 0.0
	var p := _player()
	if p:
		_last_seen = p.global_position
	if silent:
		return
	Game.sfx_rand("enemy_alert", 2, global_position + Vector3.UP * 1.5, 1.0)
	for e: Node in get_tree().get_nodes_in_group("enemy"):          # крик слышат соседи
		var o := e as Enemy
		if o and o != self and o.global_position.distance_to(global_position) < 9.0:
			get_tree().create_timer(randf_range(0.3, 0.9)).timeout.connect(o.alert.bind(true))


# ----------------------------------------------------------------------------- спокойное состояние
func _passive(delta: float, player: Player) -> void:
	if player and not player.is_dead() and _think <= 0.0:
		_think = 0.2
		if _can_see(player, true):
			alert()
			return
	match state:
		S.IDLE:
			_slow(delta)
			_play(idle_anim, 0.4)
			_timer -= delta
			if _timer <= 0.0 and wander_radius > 0.0:
				var a := randf() * TAU
				_target = _home + Vector3(cos(a), 0.0, sin(a)) * randf_range(1.0, wander_radius)
				state = S.WANDER
				_timer = 9.0
				_path_cd = 0.0
		S.WANDER:
			_timer -= delta
			if _move_to(_target, walk_speed, delta, wander_anim, 0.9) or _timer <= 0.0:
				state = S.IDLE
				_timer = randf_range(2.5, 7.0)
		S.INVESTIGATE:
			_timer -= delta
			if _move_to(_target, walk_speed * 1.7, delta, "Walk", 0.9) or _timer <= 0.0:
				state = S.IDLE
				_timer = randf_range(3.0, 5.0)


# ----------------------------------------------------------------------------- погоня и бой
func _chase(delta: float, player: Player) -> void:
	if player == null or player.is_dead():
		state = S.IDLE
		_timer = 3.0
		return
	if _think <= 0.0:
		_think = 0.2
		_sees = is_stalker or _can_see(player, false)
	if _sees:
		_last_seen = player.global_position
		_lost = 0.0
	else:
		_lost += delta
		if _lost > lose_time:
			state = S.INVESTIGATE
			_target = _last_seen
			_timer = 10.0
			return
	var to := player.global_position - global_position
	var dy := absf(to.y)
	to.y = 0.0
	var d := to.length()
	if d < attack_range * model_scale and dy < 1.2 and _sees:
		_slow(delta)
		_face(to, delta)
		_play("Idle", 0.25)
		if _attack_cd <= 0.0:
			_begin_attack(player)
	else:
		_move_to(_last_seen, chase_speed, delta, chase_anim, chase_anim_speed)


func _begin_attack(player: Player) -> void:
	if can_grab and _grab_cd <= 0.0 and randf() < grab_chance and player.grab_start(self):
		state = S.GRAB
		_timer = grab_time
		_play("Grab", 0.15, 1.6)
		return
	state = S.ATTACK
	_timer = 0.0
	_struck = false
	_play(attack_anim, 0.1, attack_anim_rate)
	Game.sfx("enemy_attack", global_position + Vector3.UP * 1.5, -2.0)


func _attack(delta: float, player: Player) -> void:
	_timer += delta
	var push := 1.2 if _timer < attack_windup else 0.0
	velocity.x = -global_basis.z.x * push
	velocity.z = -global_basis.z.z * push
	if player and _timer < attack_windup:
		_face(player.global_position - global_position, delta * 0.6)
	if not _struck and _timer >= attack_windup:
		_struck = true
		if player and not player.is_dead():
			var to := player.global_position - global_position
			to.y = 0.0
			if to.length() < (attack_range + 0.45) * model_scale and rad_to_deg((-global_basis.z).angle_to(to)) < 65.0:
				player.take_damage(attack_damage, global_position, heavy_hits)
				Game.sfx("punch", player.global_position + Vector3.UP * 1.3, 2.0)
	if _timer >= attack_total:
		state = S.CHASE
		_attack_cd = attack_cooldown


func _grab(delta: float, player: Player) -> void:
	_slow(delta)
	if player == null or player.is_dead() or player.state != Player.State.GRABBED:
		state = S.CHASE
		_grab_cd = 6.0
		_attack_cd = 1.0
		return
	_face(player.global_position - global_position, delta)
	player.take_grab_damage(grab_dps * delta)
	_timer -= delta
	if _timer <= 0.0:                                                # сам отпустил — оттолкнул
		player.grab_release()
		player.take_damage(6.0, global_position)
		state = S.CHASE
		_grab_cd = 7.0
		_attack_cd = 1.2


## Игрок вырвался.
func grab_broken() -> void:
	_grab_cd = 8.0
	_stagger(1.5, "Knockback")
	velocity = global_basis.z * 3.0


func _release_player() -> void:
	var p := _player()
	if p and p.state == Player.State.GRABBED:
		p.grab_release()
	_grab_cd = 6.0


# ----------------------------------------------------------------------------- получение урона
func take_hit(dmg: float, zone: String, from: Vector3, heavy: bool) -> void:
	if state == S.DEAD:
		return
	if state == S.GRAB:
		_release_player()
	var mult := 1.0
	if state == S.DOWN:
		mult = 1.5
		zone = "down"
	elif zone == "head":
		mult = 1.6
	if is_passive():
		mult *= 2.0                                                   # не ждал удара
	hp -= dmg * mult
	var away := global_position - from
	away.y = 0.0
	away = away.normalized()
	_last_seen = from
	_lost = 0.0
	if is_stalker:
		if state == S.STUNNED:
			return
		if hp <= 0.0:
			_stun()
		elif zone == "head" or heavy:
			_stagger(0.45, "HitHead")
			Game.sfx("sergey_breath", global_position + Vector3.UP * 1.7, 0.0)
		elif is_passive():
			state = S.CHASE
		return
	if hp <= 0.0:
		_die(away)
		return
	Game.sfx_rand("enemy_hurt", 2, global_position + Vector3.UP * 1.5)
	match zone:
		"head":
			_stagger(1.25, "HitHead")
		"legs":
			_knockdown()
		"down":
			_timer += 0.5
		_:
			_stagger(0.8 if heavy else 0.5, "HitChest")
			velocity = away * (3.5 if heavy else 1.5)


## Попадание брошенным предметом.
func take_thrown(id: String, from: Vector3) -> void:
	if state == S.DEAD:
		return
	if is_passive():                                                 # бросок издалека — без бонуса за внезапность
		state = S.CHASE
	if id == "brick":
		take_hit(2.0, "head" if is_stalker else "legs", from, true)
	else:
		take_hit(1.0, "body", from, false)
		if state == S.STAGGER:
			_timer = 0.9 if is_stalker else 1.8
			_play("HitHead", 0.1)


func _stagger(time: float, clip: String) -> void:
	state = S.STAGGER
	_timer = time
	_play(clip, 0.08)
	if _anim:
		_anim.seek(0.0)


func _knockdown() -> void:
	state = S.DOWN
	_timer = 3.4
	_play("Death", 0.1, 1.4)
	get_tree().create_timer(0.7).timeout.connect(func() -> void: Game.sfx("body_fall", global_position, -2.0))


func _stun() -> void:
	state = S.STUNNED
	_timer = stun_time
	_play("Crouch", 0.35)
	Game.sfx("sergey_roar", global_position + Vector3.UP * 1.6, 3.0)
	Game.say("%s оглушён. Это ненадолго — беги." % display_name)


func _die(away: Vector3) -> void:
	state = S.DEAD
	velocity = away * 2.0
	_play("Death", 0.1, 1.2)
	Game.sfx("enemy_die", global_position + Vector3.UP * 1.4)
	get_tree().create_timer(0.8).timeout.connect(func() -> void: Game.sfx("body_fall", global_position, -2.0))
	remove_from_group("enemy")
	collision_layer = 0
	collision_mask = 1
	Game.stats["kills"] += 1
	died_signal.emit(self)
	get_tree().create_timer(3.0).timeout.connect(func() -> void: set_physics_process(false))


# ----------------------------------------------------------------------------- передвижение
## Идти к точке по навигационной сетке. Возвращает true, когда дошёл.
func _move_to(target: Vector3, speed: float, delta: float, clip: String, clip_speed: float) -> bool:
	var flat := target - global_position
	flat.y = 0.0
	if flat.length() < 0.6 and absf(target.y - global_position.y) < 1.5:
		_slow(delta)
		return true
	_path_cd -= delta
	if _path_cd <= 0.0:
		_path_cd = 0.3 + randf() * 0.15
		_path = NavigationServer3D.map_get_path(get_world_3d().navigation_map, global_position, target, true)
		_path_i = 1 if _path.size() > 1 else 0
	var goal := target
	if _path.size() > 1:
		while _path_i < _path.size() - 1 and Vector2(_path[_path_i].x - global_position.x, _path[_path_i].z - global_position.z).length() < 0.45:
			_path_i += 1
		goal = _path[_path_i]
	var dir := goal - global_position
	dir.y = 0.0
	dir = dir.normalized()
	for e: Node in get_tree().get_nodes_in_group("enemy"):          # не слипаться в кучу
		var o := e as Enemy
		if o == null or o == self:
			continue
		var off := global_position - o.global_position
		off.y = 0.0
		var d := off.length()
		if d < 1.0 and d > 0.01:
			dir += off / d * (1.0 - d) * 1.5
	dir = dir.normalized()
	_face(dir, delta)
	var fwd := -global_basis.z
	var k := clampf(fwd.dot(dir), 0.0, 1.0)                            # пока не повернулся — не разгоняется
	velocity.x = move_toward(velocity.x, dir.x * speed * k, 12.0 * delta)
	velocity.z = move_toward(velocity.z, dir.z * speed * k, 12.0 * delta)
	_play(clip, 0.25, clampf(speed / (clip_speed * model_scale), 0.7, 2.2))
	# упёрся в угол — берём следующую точку пути, чтобы обойти
	_stuck = _stuck + delta if get_real_velocity().length() < speed * 0.2 else 0.0
	if _stuck > 0.6:
		_stuck = 0.0
		if _path_i < _path.size() - 1:
			_path_i += 1
			_path_cd = 0.9
	return false


func _face(dir: Vector3, delta: float) -> void:
	if dir.length_squared() < 0.0001:
		return
	var yaw := atan2(-dir.x, -dir.z)
	rotation.y = rotate_toward(rotation.y, yaw, turn_rate * delta)


func _play(clip: String, blend := 0.2, speed := 1.0) -> void:
	if _anim == null or not _anim.has_animation(clip):
		return
	if _anim.current_animation != clip:
		_anim.play(clip, blend, speed)
	else:
		_anim.speed_scale = 1.0
		if not is_equal_approx(_anim.get_playing_speed(), speed):
			_anim.play(clip, blend, speed)


# ----------------------------------------------------------------------------- звуки
func _voice(delta: float) -> void:
	if state == S.DEAD:
		return
	_voice_cd -= delta
	if _voice_cd <= 0.0:
		_voice_cd = randf_range(5.0, 11.0)
		if is_stalker:
			if state == S.CHASE:
				Game.sfx("sergey_breath", global_position + Vector3.UP * 1.7, 2.0)
		elif is_passive():
			Game.sfx("enemy_idle", global_position + Vector3.UP * 1.5, -4.0)
	if is_stalker and state == S.CHASE and Vector2(velocity.x, velocity.z).length() > 0.8:
		_step_cd -= delta
		if _step_cd <= 0.0:
			_step_cd = 0.42
			Game.sfx("step_heavy", global_position, 0.0)
