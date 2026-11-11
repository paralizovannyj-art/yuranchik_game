## Мерцающая лампа: редкие провалы яркости, как у старой лампочки в подъезде.
## Повесь на любой Light3D. Можно указать светящийся меш, чтобы он гас вместе со светом.
extends Light3D

@export var flicker_chance := 0.6   ## сколько раз в секунду в среднем начинается «приступ»
@export var min_factor := 0.05      ## насколько гаснет при провале
@export var glow_mesh: GeometryInstance3D  ## опционально: меш-ореол, гаснущий вместе со светом

var _base_energy := 1.0
var _burst := 0.0


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
	if glow_mesh:
		glow_mesh.transparency = 1.0 - f
