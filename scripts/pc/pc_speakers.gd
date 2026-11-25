## Колонки компа Юрчика: весь звук компа (Windows и браузер) играет из двух настоящих колонок на столе.
## Звук живёт в 3D: тише, когда отходишь, и глухой (без высоких частот, тише), когда между Юрчиком
## и колонками стена или закрытая дверь.
##
## Браузер (gdcef) пишет звук страницы прямо в генератор 3D-плеера между колонками — без лишних
## промежуточных буферов, чтобы звук не отставал от картинки. Звуки Windows играют из обеих колонок.
## Все звуки колонок идут через шину PCSpeakers с фильтром «за стеной».
class_name PcSpeakers
extends Node3D

const OUT_BUS := "PCSpeakers"
const RATE := 44100.0                     ## Chromium в gdcef отдаёт звук в 44,1 кГц (проверено: при 48 кГц буфер пустел на 4000 кадров в секунду)
const UNIT_SIZE := 2.2                    ## маленькие настольные колонки: громко только рядом
const MAX_DIST := 40.0
const OPEN_CUTOFF := 20000.0
const WALL_CUTOFF := 700.0                ## за стеной слышно только «бубнение»
const WALL_DB := -9.0
const WEB_BUFFER := 0.12                  ## больше браузер вперёд не накопит — задержка не растёт
const PREBUFFER_MIN := 1323               ## запас перед игрой (30 мс): пакеты Chromium приходят рывками
const PREBUFFER_MAX := 3528               ## не больше 80 мс — иначе звук заметно отстаёт от картинки

var left: Node3D                          ## где левая колонка
var right: Node3D                         ## где правая
var web: AudioStreamPlayer3D              ## звук браузера — между колонками
var volume_db := -4.0:                    ## общая громкость колонок
	set(v):
		volume_db = v
		if web:
			web.volume_db = v

var _lp: AudioEffectLowPassFilter
var _web_pb: AudioStreamGeneratorPlayback
var _web_cap := 0                         ## сколько кадров влезает в буфер браузера
var _prebuffer := PREBUFFER_MIN
var _occ := 0.0                           ## 0 — видно колонки, 1 — за стеной
var _occ_target := 0.0
var _ray_t := 0.0


## Поставить колонки: pos_l / pos_r — где динамики (мировые координаты).
func setup(pos_l: Vector3, pos_r: Vector3) -> PcSpeakers:
	_ensure_bus()
	left = _marker("Left", pos_l)
	right = _marker("Right", pos_r)
	web = AudioStreamPlayer3D.new()
	web.name = "Browser"
	_tune(web)
	var g := AudioStreamGenerator.new()
	g.mix_rate = RATE
	g.buffer_length = WEB_BUFFER
	web.stream = g
	web.volume_db = volume_db + 2.0           # две колонки играют вместе
	add_child(web)
	web.global_position = (pos_l + pos_r) * 0.5
	web.play()
	_web_pb = web.get_stream_playback()
	_web_cap = _web_pb.get_frames_available()
	web.stream_paused = true
	return self


## Куда gdcef пишет звук страницы (GdBrowserView.set_audio_stream).
func browser_playback() -> AudioStreamGeneratorPlayback:
	return _web_pb


## Короткий звук (Windows) — из обеих колонок сразу.
func play(stream: AudioStream, db := 0.0) -> void:
	if stream == null:
		return
	for sp: Node3D in [left, right]:
		var p := AudioStreamPlayer3D.new()
		_tune(p)
		p.stream = stream
		p.volume_db = volume_db + db - 3.0          # две колонки вместе — как одна громкая
		add_child(p)
		p.global_position = sp.global_position
		p.finished.connect(p.queue_free)
		p.play()


func _marker(n: String, pos: Vector3) -> Node3D:
	var m := Node3D.new()
	m.name = n
	add_child(m)
	m.global_position = pos
	return m


func _tune(p: AudioStreamPlayer3D) -> void:
	p.bus = OUT_BUS
	p.unit_size = UNIT_SIZE
	p.max_distance = MAX_DIST
	p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
	p.attenuation_filter_cutoff_hz = 9000.0          # издалека чуть глуше — воздух съедает верх
	p.attenuation_filter_db = -12.0
	p.panning_strength = 1.0


func _ensure_bus() -> void:
	var o := AudioServer.get_bus_index(OUT_BUS)
	if o == -1:
		AudioServer.add_bus()
		o = AudioServer.bus_count - 1
		AudioServer.set_bus_name(o, OUT_BUS)
		AudioServer.set_bus_send(o, "Master")
	if AudioServer.get_bus_effect_count(o) == 0:
		var lp := AudioEffectLowPassFilter.new()
		lp.cutoff_hz = OPEN_CUTOFF
		lp.db = AudioEffectFilter.FILTER_12DB
		AudioServer.add_bus_effect(o, lp)
	_lp = AudioServer.get_bus_effect(o, 0) as AudioEffectLowPassFilter


func _process(delta: float) -> void:
	_buffer_web()
	_ray_t -= delta
	if _ray_t <= 0.0:
		_ray_t = 0.12
		_occ_target = _occluded()
	_occ = move_toward(_occ, _occ_target, delta * 3.0)
	if _lp:
		_lp.cutoff_hz = lerpf(OPEN_CUTOFF, WALL_CUTOFF, pow(_occ, 0.5))
		AudioServer.set_bus_volume_db(AudioServer.get_bus_index(OUT_BUS), WALL_DB * _occ)


## Браузер пишет в буфер неровными пакетами: играть, только когда есть небольшой запас, иначе ждать (без треска).
func _buffer_web() -> void:
	if _web_pb == null:
		return
	var queued := _web_cap - _web_pb.get_frames_available()
	if web.stream_paused and queued >= _prebuffer:
		web.stream_paused = false
	elif not web.stream_paused and queued < 64:
		web.stream_paused = true
		_prebuffer = mini(_prebuffer + 441, PREBUFFER_MAX)   # кончился запас — в следующий раз копить чуть больше


## Между ушами (камерой) и колонками что-то твёрдое — стена, дверь?
func _occluded() -> float:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return 0.0
	var space := get_world_3d().direct_space_state
	var from := cam.global_position
	var hits := 0
	var player := get_tree().get_first_node_in_group("player")
	for sp: Node3D in [left, right]:
		var to := sp.global_position + Vector3.UP * 0.12
		var q := PhysicsRayQueryParameters3D.create(from, to)
		q.collide_with_areas = false
		if player is CollisionObject3D:
			q.exclude = [(player as CollisionObject3D).get_rid()]
		var hit := space.intersect_ray(q)
		# попали во что-то заметно раньше колонки — значит, между нами преграда (стол, сама колонка — не считаем)
		if not hit.is_empty() and (hit["position"] as Vector3).distance_to(to) > 0.6:
			hits += 1
	return float(hits) / 2.0
