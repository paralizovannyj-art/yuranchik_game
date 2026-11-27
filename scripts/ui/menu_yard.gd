## Кадр главного меню (YUR-19): двор Юрчика зимой на закате, Юрчик курит, высунувшись из окна 9-го этажа.
## Курит петлёй — клип MenuSmoke (tools/blender/build_window_smoke.py, assets/animations/menu/): сигарета на
## кости кисти, огонёк ярче на затяжке, дым от кончика и выдох изо рта.
## Декорация — assets/models/menu/menu_yard.gltf (tools/blender/build_menu_yard.py), точки для света — menu_yard.json
## рядом с ней: лампа в комнате за окном и фонари во дворе и на дальней улице.
## Камера стоит снаружи у стены, чуть правее окна, и смотрит вдоль фасада на двор (как главный референс
## docs/references/main_menu/image-20261127-134919.png); еле заметно дышит, чтобы кадр был живой.
extends Node3D

const DATA := "res://assets/models/menu/menu_yard.json"
const SMOKE_LIB := "res://assets/animations/menu/yurchik_smoke.glb"
const SMOKE_DATA := "res://assets/animations/menu/smoke.json"
const CLIP := &"menu/MenuSmoke"

@export var cam_pos := Vector3(2.5, 24.45, 2.4)      ## где камера (снаружи, в 2.5 м от стены, чуть позади окна)
@export var cam_target := Vector3(0.43, 22.01, -17.34) ## куда смотрит: вдоль фасада, чуть вниз (как на референсе)
@export var sway := 0.03                             ## м — насколько камера «дышит»
@export var street_energy := 1.6                     ## фонари (1/d²: на снегу под фонарём ≈ e/h²)
@export var room_energy := 4.0                       ## лампа в комнате Юрчика

@export var block_glow := 0.35                       ## окна дальних высоток: свечение (в текстурах фасадов их много)
@export var dusk_from := Vector3(0.12, 0.16, -1.0)   ## откуда светит закат: из-за высоток, фасад Юрчика в тени

@export var ember_idle := 0.12                       ## огонёк сигареты: свет, пока тлеет
@export var ember_drag := 0.6                        ## … на затяжке

@onready var cam: Camera3D = $MenuCam
@onready var yur: Node3D = $Yurchik
@onready var cig: Node3D = $Yurchik/Yurchik/Skeleton3D/HandR/Cig
@onready var tip: Marker3D = $Yurchik/Yurchik/Skeleton3D/HandR/Cig/Tip
@onready var ember_light: OmniLight3D = $Yurchik/Yurchik/Skeleton3D/HandR/Cig/EmberLight
@onready var ember: MeshInstance3D = $Yurchik/Yurchik/Skeleton3D/HandR/Cig/Ember
@onready var mouth: Marker3D = $Yurchik/Yurchik/Skeleton3D/HeadHold/Mouth
@onready var cig_smoke: GPUParticles3D = $CigSmoke
@onready var exhale: GPUParticles3D = $Exhale
var _t := 0.0
var _anim: AnimationPlayer
var _marks := {}
var _fps := 30.0
var _ember_mat: StandardMaterial3D


func _ready() -> void:
	_spawn_lights()
	_tune_materials($Set)
	var dusk := $Dusk as DirectionalLight3D
	dusk.look_at_from_position(Vector3.ZERO, -dusk_from.normalized(), Vector3.UP)
	_place_cam(0.0)
	_setup_yurchik()


func _spawn_lights() -> void:
	var f := FileAccess.open(DATA, FileAccess.READ)
	if f == null:
		return
	var data: Dictionary = JSON.parse_string(f.get_as_text())
	var root := Node3D.new()
	root.name = "Lights"
	add_child(root)
	for l: Dictionary in data.get("lights", []):
		var o := OmniLight3D.new()
		var p: Array = l["pos"]
		var c: Array = l["color"]
		o.position = Vector3(p[0], p[1], p[2])
		o.light_color = Color(c[0], c[1], c[2])
		o.omni_attenuation = 2.0
		o.omni_range = float(l["range"])
		var room: bool = l["kind"] == "room"
		o.light_energy = room_energy if room else street_energy
		o.shadow_enabled = room
		root.add_child(o)


## Дальние высотки — на общих текстурах фасадов района, где горит много окон: в кадре меню тусклее.
func _tune_materials(node: Node) -> void:
	for mi: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
		for i in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(i) as StandardMaterial3D
			if m and m.resource_name.begins_with("MenuFacade"):
				m.emission_energy_multiplier = block_glow


## Клип курения на своём плеере модели; сигарета и рот — по точкам из smoke.json: они даны в пространстве
## скелета на кадре ref, смещение от кости считаем по её позе на этом кадре.
func _setup_yurchik() -> void:
	var lib := load(SMOKE_LIB) as AnimationLibrary
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(SMOKE_DATA))
	_marks = data["marks"]
	_fps = float(data["fps"])
	lib.get_animation("MenuSmoke").loop_mode = Animation.LOOP_LINEAR
	_anim = yur.get_node("AnimationPlayer") as AnimationPlayer
	_anim.add_animation_library("menu", lib)
	_anim.play(CLIP)
	_anim.seek(float(data["ref"]) / _fps, true)
	var skel := yur.get_node("Yurchik/Skeleton3D") as Skeleton3D
	var pts: Dictionary = data["points"]
	var hand := skel.get_bone_global_pose(skel.find_bone("HandR")).affine_inverse()
	var head := skel.get_bone_global_pose(skel.find_bone("Head")).affine_inverse()
	var f := hand * _vec(pts["filter"])
	var t := hand * _vec(pts["tip"])
	var up := (t - f).normalized()
	var side := up.cross(Vector3.FORWARD if absf(up.z) < 0.9 else Vector3.RIGHT).normalized()
	cig.transform = Transform3D(Basis(side, up, side.cross(up)), f)
	mouth.position = head * _vec(pts["mouth"])
	_ember_mat = (ember.mesh.surface_get_material(0) as StandardMaterial3D).duplicate()
	ember.material_override = _ember_mat


func _vec(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


## 0…1: плавно вошли в окно [a, b] кадров и вышли из него.
func _win(fr: float, a: float, b: float, edge := 8.0) -> float:
	return smoothstep(a, a + edge, fr) * (1.0 - smoothstep(b - edge, b, fr))


func _update_smoke() -> void:
	if _anim == null:
		return
	var fr := _anim.current_animation_position * _fps
	var drag := _win(fr, float(_marks["mouth"]) - 4.0, float(_marks["drag_end"]) + 6.0)
	var flicker := 1.0 + 0.12 * sin(_t * 13.0) * sin(_t * 7.3)
	var e := lerpf(ember_idle, ember_drag, drag) * flicker
	ember_light.light_energy = e
	_ember_mat.emission_energy_multiplier = 2.0 + e * 3.0
	cig_smoke.global_position = tip.global_position
	exhale.global_position = mouth.global_position
	exhale.emitting = fr >= float(_marks["exhale0"]) and fr < float(_marks["exhale1"]) - 20.0


func _place_cam(t: float) -> void:
	var off := Vector3(sin(t * 0.31) * sway, sin(t * 0.47 + 1.0) * sway * 0.6, 0.0)
	cam.position = cam_pos + off
	cam.look_at(cam_target + off * 0.5)


func _process(delta: float) -> void:
	_t += delta
	_place_cam(_t)
	_update_smoke()
