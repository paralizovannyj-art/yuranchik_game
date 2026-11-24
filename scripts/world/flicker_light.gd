## Мерцающая лампа: редкие провалы яркости, как у старой лампочки в подъезде.
## Повесь на любой Light3D. Можно указать светящийся меш (плафон, ореол), чтобы он гас вместе со светом:
## в жизни при провале тускнеет и сама лампа, а не только освещённое ею.
extends Light3D

@export var flicker_chance := 0.6   ## сколько раз в секунду в среднем начинается «приступ»
@export var min_factor := 0.05      ## насколько гаснет при провале
@export var glow_mesh: GeometryInstance3D  ## опционально: меш-ореол, гаснущий вместе со светом
## опционально: светящийся материал плафона (emission), гаснущий вместе со светом.
## Материал должен быть своим у этой лампы (duplicate), иначе погаснут все плафоны с ним.
@export var glow_material: BaseMaterial3D
## то же для нескольких материалов (стекло, отделённое GlowSplit от слитого меша); можно назначить после старта
var glow_materials: Array[BaseMaterial3D] = []

var _base_energy := 1.0
var _burst := 0.0
var _last_f := -1.0
var _glow_base := {}                              ## материал → его яркость свечения без провала


func _ready() -> void:
	_base_energy = light_energy


func _process(delta: float) -> void:
	if _burst <= 0.0 and randf() < flicker_chance * delta:
		_burst = randf_range(0.08, 0.6)
	var f := 1.0
	if _burst > 0.0:
		_burst -= delta
		f = min_factor if randf() < 0.5 else randf_range(0.4, 1.0)
	light_energy = _base_energy * f
	if _glow_base.size() != glow_materials.size() + int(glow_material != null):
		for m in glow_materials + ([glow_material] if glow_material else []):
			if m and not _glow_base.has(m):             # назначили позже — запомнить исходную яркость
				_glow_base[m] = m.emission_energy_multiplier
				_last_f = -1.0
	if is_equal_approx(f, _last_f):
		return
	_last_f = f
	if glow_mesh:
		if glow_mesh.material_override is ShaderMaterial:
			glow_mesh.set_instance_shader_parameter("glow", f)   # lamp_sparkle.gdshader
		else:
			glow_mesh.transparency = 1.0 - f
	for m: BaseMaterial3D in _glow_base:
		m.emission_energy_multiplier = _glow_base[m] * f
