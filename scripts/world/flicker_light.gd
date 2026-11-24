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

var _base_energy := 1.0
var _burst := 0.0
var _last_f := -1.0
var _glow_material_base := 0.0


func _ready() -> void:
	_base_energy = light_energy
	if glow_material:
		_glow_material_base = glow_material.emission_energy_multiplier


func _process(delta: float) -> void:
	if _burst <= 0.0 and randf() < flicker_chance * delta:
		_burst = randf_range(0.08, 0.6)
	var f := 1.0
	if _burst > 0.0:
		_burst -= delta
		f = min_factor if randf() < 0.5 else randf_range(0.4, 1.0)
	light_energy = _base_energy * f
	if is_equal_approx(f, _last_f):
		return
	_last_f = f
	if glow_mesh:
		if glow_mesh.material_override is ShaderMaterial:
			glow_mesh.set_instance_shader_parameter("glow", f)   # lamp_sparkle.gdshader
		else:
			glow_mesh.transparency = 1.0 - f
	if glow_material:
		glow_material.emission_energy_multiplier = _glow_material_base * f
