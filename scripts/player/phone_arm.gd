## Правая рука Юрчика (кости его модели) держит телефон (scripts/ui/phone.gd), как на референсах
## references/hands/: телефон спинкой в ладони, четыре пальца обхватывают левое ребро и голыми кончиками ложатся
## на лицевую сторону, большой палец — на правом ребре в верхней части, запястье справа внизу.
## Поза кисти и пальцев считается в Blender (tools/blender/pose_phone_hold.py) и лежит в
## assets/models/phone_hold.json: повороты костей в осях телефона и начало кости кисти.
## Плечо и предплечье — двухзвенный IK к кисти (телефон висит на камере и движется вместе с ней).
## Работает поверх анимаций: SkeletonModifier3D — дочерний узел Skeleton3D.
## weight 0..1 — насколько рука поднята (phone.gd анимирует его вместе с телефоном).
class_name PhoneArm
extends SkeletonModifier3D

const POSE := preload("res://assets/models/phone_hold.json")
const FINGERS := ["Index", "Middle", "Ring", "Pinky", "Thumb"]

var target: Node3D                   ## телефон
var weight := 0.0
var pole := Vector3(-2.0, -0.7, 0.0)            ## куда смотрит локоть (оси модели: −x — вправо от Юрчика): локоть вправо — предплечье входит в кадр из правого нижнего угла

## Телефон в игре крупнее настоящего (Phone.SCALE), кисть увеличивается вместе с ним — пропорции настоящие.
var hand_scale := 1.0
var _origin := Vector3.ZERO          ## начало кости кисти в осях телефона
var _rot := {}                       ## кость → поворот в осях телефона
var _upper := -1
var _fore := -1
var _hand := -1
var _chains: Array = []              ## [ [кость1 всех пальцев], [кость2…], [кость3…] ] — от основания к кончикам
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
	var d: Dictionary = POSE.data
	hand_scale = float(d.get("hand_scale", hand_scale))
	var o: Array = d["origin"]
	_origin = Vector3(o[0], o[1], o[2])
	for n: String in d["bones"]:
		var q: Array = d["bones"][n]
		_rot[n] = Basis(Quaternion(q[0], q[1], q[2], q[3]).normalized())
	_bones = [_upper, _fore, _hand]
	for k in 3:
		var level: Array[int] = []
		for n: String in FINGERS:
			var b := sk.find_bone("%sR%d" % [n, k + 1])
			if b >= 0 and _rot.has(sk.get_bone_name(b)):
				level.append(b)
		_chains.append(level)
		_bones.append_array(level)
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

	# --- кисть: по телефону ---
	var p := sk.global_transform.affine_inverse() * target.global_transform
	var pb := p.basis.orthonormalized()
	var want: Basis = pb * _rot["HandR"]
	var wrist := p * _origin

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

	# --- пальцы: повороты из позы, от основания к кончикам ---
	for level: Array in _chains:
		for b: int in level:
			_set_global_basis(sk, b, pb * _rot[sk.get_bone_name(b)])

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
