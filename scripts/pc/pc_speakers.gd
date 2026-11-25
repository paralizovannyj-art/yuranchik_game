## Колонки компа Юрчика: весь звук компа (Windows и браузер) играет из двух настоящих колонок на столе.
## Левый канал — из левой колонки, правый — из правой. Звук живёт в 3D: тише, когда отходишь,
## и глухой (без высоких частот, тише), когда между Юрчиком и колонками стена или закрытая дверь.
##
## Браузер (gdcef) отдаёт звук в AudioStreamGenerator «сырого» плеера на шине PCRaw (почти без громкости).
## С этой шины AudioEffectCapture забирает кадры, а здесь они раскладываются по двум генераторам —
## для левой и правой колонки. Все звуки колонок идут через шину PCSpeakers с фильтром «за стеной».
class_name PcSpeakers
extends Node3D

const RAW_BUS := "PCRaw"
const OUT_BUS := "PCSpeakers"
const RATE := 44100.0                     ## Chromium в gdcef отдаёт звук в 44,1 кГц (проверено: при 48 кГц буфер пустел на 4000 кадров в секунду)
const UNIT_SIZE := 2.2                    ## маленькие настольные колонки: громко только рядом
const MAX_DIST := 40.0
const OPEN_CUTOFF := 20000.0
const WALL_CUTOFF := 700.0                ## за стеной слышно только «бубнение»
const WALL_DB := -9.0

var left: AudioStreamPlayer3D
var right: AudioStreamPlayer3D
var raw: AudioStreamPlayer
var volume_db := -4.0:                    ## общая громкость колонок
	set(v):
		volume_db = v
		if left:
			left.volume_db = v
			right.volume_db = v

var _lp: AudioEffectLowPassFilter
var _capture: AudioEffectCapture
var _gen_l: AudioStreamGeneratorPlayback
var _gen_r: AudioStreamGeneratorPlayback
var _occ := 0.0                           ## 0 — видно колонки, 1 — за стеной
var _occ_target := 0.0
var _ray_t := 0.0
var _raw_cap := 0                         ## сколько кадров влезает в буфер браузера
var _prebuffer := 4800                    ## запас перед игрой (100 мс): пакеты Chromium приходят рывками
const PREBUFFER_MAX := 14400              ## не больше 0,3 с — иначе звук заметно отстаёт от видео


## Поставить колонки: pos_l / pos_r — где динамики (мировые координаты).
func setup(pos_l: Vector3, pos_r: Vector3) -> PcSpeakers:
	_ensure_buses()
	left = _make_speaker("Left", pos_l)
	right = _make_speaker("Right", pos_r)
	raw = AudioStreamPlayer.new()
	raw.name = "BrowserRaw"
	var g := AudioStreamGenerator.new()
	g.mix_rate = RATE
	g.buffer_length = 0.5
	raw.stream = g
	raw.bus = RAW_BUS
	add_child(raw)
	raw.play()
	_raw_cap = (raw.get_stream_playback() as AudioStreamGeneratorPlayback).get_frames_available()
	raw.stream_paused = true
	_gen_l = left.get_stream_playback()
	_gen_r = right.get_stream_playback()
	return self


## Куда gdcef пишет звук страницы (GdBrowserView.set_audio_stream).
func browser_playback() -> AudioStreamGeneratorPlayback:
	return raw.get_stream_playback() if raw else null


## Короткий звук (Windows) — из обеих колонок сразу.
func play(stream: AudioStream, db := 0.0) -> void:
	if stream == null:
		return
	for sp: AudioStreamPlayer3D in [left, right]:
		var p := AudioStreamPlayer3D.new()
		_tune(p)
		p.stream = stream
		p.volume_db = volume_db + db - 3.0          # две колонки вместе — как одна громкая
		add_child(p)
		p.global_position = sp.global_position
		p.finished.connect(p.queue_free)
		p.play()


func _make_speaker(n: String, pos: Vector3) -> AudioStreamPlayer3D:
	var p := AudioStreamPlayer3D.new()
	p.name = n
	_tune(p)
	var g := AudioStreamGenerator.new()
	g.mix_rate = AudioServer.get_mix_rate()
	g.buffer_length = 0.25
	p.stream = g
	p.volume_db = volume_db
	add_child(p)
	p.global_position = pos
	p.play()
	return p


func _tune(p: AudioStreamPlayer3D) -> void:
	p.bus = OUT_BUS
	p.unit_size = UNIT_SIZE
	p.max_distance = MAX_DIST
	p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
	p.attenuation_filter_cutoff_hz = 9000.0          # издалека чуть глуше — воздух съедает верх
	p.attenuation_filter_db = -12.0
	p.panning_strength = 1.0


static func _bus(name: String) -> int:
	var i := AudioServer.get_bus_index(name)
	if i == -1:
		AudioServer.add_bus()
		i = AudioServer.bus_count - 1
		AudioServer.set_bus_name(i, name)
		AudioServer.set_bus_send(i, "Master")
	return i


func _ensure_buses() -> void:
	var r := _bus(RAW_BUS)
	AudioServer.set_bus_volume_db(r, -80.0)          # сам по себе не слышен — только через колонки
	if AudioServer.get_bus_effect_count(r) == 0:
		var cap := AudioEffectCapture.new()
		cap.buffer_length = 0.2
		AudioServer.add_bus_effect(r, cap)
	_capture = AudioServer.get_bus_effect(r, 0) as AudioEffectCapture
	var o := _bus(OUT_BUS)
	if AudioServer.get_bus_effect_count(o) == 0:
		var lp := AudioEffectLowPassFilter.new()
		lp.cutoff_hz = OPEN_CUTOFF
		lp.db = AudioEffectFilter.FILTER_12DB
		AudioServer.add_bus_effect(o, lp)
	_lp = AudioServer.get_bus_effect(o, 0) as AudioEffectLowPassFilter


func _process(delta: float) -> void:
	_pump()
	_ray_t -= delta
	if _ray_t <= 0.0:
		_ray_t = 0.12
		_occ_target = _occluded()
	_occ = move_toward(_occ, _occ_target, delta * 3.0)
	if _lp:
		_lp.cutoff_hz = lerpf(OPEN_CUTOFF, WALL_CUTOFF, pow(_occ, 0.5))
		AudioServer.set_bus_volume_db(AudioServer.get_bus_index(OUT_BUS), WALL_DB * _occ)


## Кадры браузера → левая и правая колонки.
func _pump() -> void:
	if _capture == null or _gen_l == null:
		return
	# браузер пишет в буфер неровными пакетами: играть, только когда есть запас, иначе ждать (без треска)
	var queued := _raw_cap - (raw.get_stream_playback() as AudioStreamGeneratorPlayback).get_frames_available()
	if raw.stream_paused and queued >= _prebuffer:
		raw.stream_paused = false
	elif not raw.stream_paused and queued < 128:
		raw.stream_paused = true
		_prebuffer = mini(_prebuffer + 2400, PREBUFFER_MAX)   # кончился запас — в следующий раз копить больше
	var n := mini(_capture.get_frames_available(), mini(_gen_l.get_frames_available(), _gen_r.get_frames_available()))
	if n <= 0:
		return
	var buf := _capture.get_buffer(n)
	var l := PackedVector2Array()
	var r := PackedVector2Array()
	l.resize(n)
	r.resize(n)
	for i in n:
		var f := buf[i]               # захват стоит до ползунка шины: −80 дБ на него не влияют
		l[i] = Vector2(f.x, f.x)
		r[i] = Vector2(f.y, f.y)
	_gen_l.push_buffer(l)
	_gen_r.push_buffer(r)


## Между ушами (камерой) и колонками что-то твёрдое — стена, дверь?
func _occluded() -> float:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return 0.0
	var space := get_world_3d().direct_space_state
	var from := cam.global_position
	var hits := 0
	for sp: AudioStreamPlayer3D in [left, right]:
		var to := sp.global_position + Vector3.UP * 0.12
		var q := PhysicsRayQueryParameters3D.create(from, to)
		q.collide_with_areas = false
		var player := get_tree().get_first_node_in_group("player")
		if player is CollisionObject3D:
			q.exclude = [(player as CollisionObject3D).get_rid()]
		var hit := space.intersect_ray(q)
		# попали во что-то заметно раньше колонки — значит, между нами преграда (стол, сама колонка — не считаем)
		if not hit.is_empty() and (hit["position"] as Vector3).distance_to(to) > 0.6:
			hits += 1
	return float(hits) / 2.0
