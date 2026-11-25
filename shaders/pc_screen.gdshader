// Экран компа Юрчика (монитор в комнате, scripts/world/pc_seat.gd).
// Картинка — из SubViewport (Windows на компе), экран светится сам (EMISSION) и при этом остаётся стеклом
// в комнате: лёгкий блик от ламп (низкая шероховатость), неподвижный отблеск по диагонали,
// шум и еле заметные строки — как у старой матрицы, снятой на PS2.
// power: 0 — комп выключен (тёмное стекло), 1 — горит.
shader_type spatial;
render_mode cull_back;

#include "res://shaders/compat_srgb.gdshaderinc"

uniform sampler2D screen_tex : source_color, filter_linear, hint_default_black;
uniform float power : hint_range(0.0, 1.0) = 0.0;
uniform float energy = 1.1;                       // яркость горящего экрана
uniform vec3 glass : source_color = vec3(0.025, 0.027, 0.03);   // выключенный экран — тёмно-серое стекло
uniform float glare = 0.012;                      // неподвижный отблеск по диагонали
uniform float noise = 0.045;                      // зерно
uniform float lines = 0.05;                       // строки
uniform float line_count = 300.0;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec3 img = compat_lin(texture(screen_tex, UV).rgb);
	float t = floor(TIME * 24.0);
	float grain = (hash(floor(UV * vec2(640.0, 512.0)) + t) - 0.5) * noise;
	float scan = 1.0 - lines * (0.5 + 0.5 * sin(UV.y * line_count * 6.2832));
	// края матрицы чуть темнее (подсветка неровная)
	vec2 c = UV - 0.5;
	float edge = 1.0 - 0.18 * dot(c, c) * 2.0;
	vec3 lit = max(img * scan * edge + grain, vec3(0.0)) * energy * power;
	// отблеск: широкая мягкая полоса из левого верхнего угла — на горящем экране заметнее (подсвечен изнутри),
	// на выключенном в тёмной комнате еле виден
	float band = smoothstep(0.55, 0.0, abs(UV.x * 0.8 + UV.y - 0.55)) * (1.0 - UV.y * 0.6);
	vec3 shine = vec3(band * glare * (0.15 + 0.85 * power));
	ALBEDO = compat_enc(compat_lin(glass));
	ROUGHNESS = 0.55;                       // матовая матрица: блики ламп широкие и слабые, на OpenGL не «прожигают» экран
	SPECULAR = 0.2;
	METALLIC = 0.0;
	EMISSION = compat_enc(lit + shine);
}
