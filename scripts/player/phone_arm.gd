## Правая рука Юрчика (кости его модели) держит телефон (scripts/ui/phone.gd), как на фото-референсе:
## ладонь за спинкой, пальцы обхватывают левый край и ложатся на лицо, большой палец идёт вверх по правому краю,
## предплечье уходит вниз-вправо. Работает поверх анимаций (SkeletonModifier3D — дочерний узел Skeleton3D):
##   кисть ставится по телефону, плечо и предплечье — двухзвенный IK, пальцы и большой палец — по направлениям.
## weight 0..1 — насколько рука поднята (phone.gd анимирует его вместе с телефоном).
## Оси кисти (l — к пальцам, w — к большому пальцу, p — к ладони) и кулак в покое — из tools/blender/build_yurchik_v3.py.
class_name PhoneArm
extends SkeletonModifier3D

var target: Node3D                   ## телефон
var weight := 0.0

## Поза кисти относительно телефона (мм в осях модели телефона: u вправо, v вверх, w к зрителю; масштаб — как у телефона).
var anchor := Vector3(-4.0, -31.0, -12.0)      ## середина костяшек со стороны ладони — за спинкой
var tilt_deg := Vector3(0.0, 0.0, -6.0)        ## доворот кисти: z — пальцы чуть вверх
## Кисть крупнее телефона, как на референсе (телефон и так увеличен — phone.gd SCALE).
var hand_scale := 1.35
var pole := Vector3(-0.6, -1.0, -0.15)         ## куда смотрит локоть (оси модели: −x — вправо от Юрчика)
## Сгиб пальцев в хвате, по суставам (°): основная фаланга вдоль спинки, средняя — вокруг левого края, ногтевая — на лицо.
var curl := {"Index": [10.0, 80.0, 45.0], "Middle": [8.0, 92.0, 55.0], "Ring": [10.0, 94.0, 55.0], "Pinky": [16.0, 94.0, 50.0]}
var spread := {"Index": 6.0, "Middle": 1.0, "Ring": -4.0, "Pinky": -9.0}   ## веер пальцев (° к большому пальцу)
## Большой палец: направления трёх фаланг в осях кисти (l, w, p) — за телефоном вверх, кончик выглядывает
## над правым верхним углом.
var thumb_dirs := [Vector3(0.3, 0.95, 0.0), Vector3(0.6, 0.8, 0.0), Vector3(0.85, 0.5, -0.1)]

const FINGERS := ["Index", "Middle", "Ring", "Pinky"]
# оси левой кисти в Blender (build_yurchik_v3.py: HAND_L, HAND_WD, HAND_PN); правая — зеркало по x
const B_L := Vector3(0.30, -0.10, -0.95)
const B_WD_SEED := Vector3(-0.82, 0.57, 0.0)

var _upper := -1
var _fore := -1
var _hand := -1
var _chains := {}                    ## имя → [кость1, кость2, кость3]
var _frame_loc: Basis                ## оси кисти (l, w, p) в локальных осях кости кисти — столбцы
var _knuckle_loc: Vector3            ## костяшки (сторона ладони) в локальных осях кости кисти
var _len1 := 0.0
var _len2 := 0.0
var _bones: Array[int] = []


func _ready() -> void:
	var sk := get_skeleton()
	if sk == null:
		return
	_upper = sk.find_bone("UpperArmR")
	_fore = sk.find_bone("ForearmR")
	_hand = sk.find_bone("HandR")
	if _upper < 0 or _fore < 0 or _hand < 0 or sk.find_bone("IndexR1") < 0:
		push_warning("PhoneArm: в скелете нет костей правой руки и пальцев — переэкспортируйте yurchik.gltf")
		_hand = -1
		return
	_bones = [_upper, _fore, _hand]
	for n: String in FINGERS + ["Thumb"]:
		var c: Array[int] = []
		for k in 3:
			c.append(sk.find_bone("%sR%d" % [n, k + 1]))
		_chains[n] = c
		_bones.append_array(c)
	# оси правой кисти: зеркало левой (Blender x → −x), затем Blender (x, y, z) → glTF/Godot (x, z, −y)
	var l := B_L.normalized()
	var wd := B_WD_SEED.cross(l).normalized()
	var pn := l.cross(wd).normalized()
	var to_g := func(v: Vector3) -> Vector3: return Vector3(-v.x, v.z, -v.y)
	var hr := sk.get_bone_global_rest(_hand)
	var inv := hr.basis.inverse()
	_frame_loc = Basis(inv * to_g.call(l), inv * to_g.call(wd), inv * to_g.call(pn))
	var k := (sk.get_bone_global_rest(_chains["Index"][0]).origin + sk.get_bone_global_rest(_chains["Pinky"][0]).origin) * 0.5
	k += to_g.call(pn) * 0.012
	_knuckle_loc = inv * (k - hr.origin)
	_len1 = sk.get_bone_global_rest(_fore).origin.distance_to(sk.get_bone_global_rest(_upper).origin)
	_len2 = sk.get_bone_global_rest(_hand).origin.distance_to(sk.get_bone_global_rest(_fore).origin)


func _process_modification_with_delta(_delta: float) -> void:
	var sk := get_skeleton()
	if sk == null or _hand < 0 or weight <= 0.001 or not is_instance_valid(target):
		return
	var anim := {}
	for b in _bones:
		anim[b] = sk.get_bone_pose_rotation(b)
	var anim_scale := sk.get_bone_pose_scale(_hand)

	# --- куда встать кисти: по телефону ---
	var p := sk.global_transform.affine_inverse() * target.global_transform
	var rp := p.basis.orthonormalized() * Basis.from_euler(tilt_deg * (PI / 180.0))
	var want := Basis(rp * Vector3.LEFT, rp * Vector3.UP, rp * Vector3.BACK) * _frame_loc.inverse()
	var wrist := p * (anchor * 0.001) - want * (_knuckle_loc * hand_scale)

	# --- плечо и предплечье: двухзвенный IK, локоть в сторону pole ---
	var s := sk.get_bone_global_pose(_upper).origin
	var to := wrist - s
	var d := clampf(to.length(), absf(_len1 - _len2) + 0.001, _len1 + _len2 - 0.001)
	var x := to.normalized()
	var a := (_len1 * _len1 - _len2 * _len2 + d * d) / (2.0 * d)
	var h := sqrt(maxf(_len1 * _len1 - a * a, 0.0))
	var y := (pole - x * pole.dot(x)).normalized()
	var elbow := s + x * a + y * h
	_aim(sk, _upper, elbow - s)
	_aim(sk, _fore, wrist - sk.get_bone_global_pose(_fore).origin)
	_set_global_basis(sk, _hand, want)

	# --- пальцы: направления фаланг в осях кисти ---
	var hb := sk.get_bone_global_pose(_hand).basis.orthonormalized() * _frame_loc   # столбцы: l, w, p
	for n: String in FINGERS:
		var c: Array = curl[n]
		var sp := deg_to_rad(spread[n])
		var acc := 0.0
		for k in 3:
			acc += deg_to_rad(c[k])
			var dl := Vector3(cos(acc) * cos(sp), sin(sp), sin(acc) * cos(sp))
			_aim(sk, _chains[n][k], hb * dl)
	for k in 3:
		_aim(sk, _chains["Thumb"][k], hb * (thumb_dirs[k] as Vector3).normalized())

	# --- смешать с анимацией по weight ---
	var w := weight * weight * (3.0 - 2.0 * weight)
	for b in _bones:
		sk.set_bone_pose_rotation(b, (anim[b] as Quaternion).slerp(sk.get_bone_pose_rotation(b), w))
	sk.set_bone_pose_scale(_hand, anim_scale.lerp(Vector3.ONE * hand_scale, w))


## Повернуть кость (минимальным поворотом) так, чтобы она смотрела вдоль dir (в осях скелета).
func _aim(sk: Skeleton3D, bone: int, dir: Vector3) -> void:
	if dir.length_squared() < 1e-10:
		return
	var g := sk.get_bone_global_pose(bone).basis
	var cur := (g * Vector3.UP).normalized()
	var q := Quaternion(cur, dir.normalized())
	_set_global_basis(sk, bone, Basis(q) * g)


func _set_global_basis(sk: Skeleton3D, bone: int, b: Basis) -> void:
	var parent := sk.get_bone_parent(bone)
	var pb := sk.get_bone_global_pose(parent).basis if parent >= 0 else Basis()
	sk.set_bone_pose_rotation(bone, (pb.inverse() * b).orthonormalized().get_rotation_quaternion())
