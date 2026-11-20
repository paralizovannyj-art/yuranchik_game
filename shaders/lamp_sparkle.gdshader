// Искра фонаря: маленькая яркая точка с тонкими лучами, как блик в глазах от лампы в мороз.
// Всегда повёрнута к камере, слегка мерцает и вытянута к зрителю, чтобы корпус плафона её не перекрывал.
// Без мягкого пятна — свет вокруг остаётся чистым, без туманного «мыла».
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec4 color : source_color = vec4(1.0, 0.55, 0.22, 1.0);
uniform float energy = 2.2;                 // яркость искры
uniform float ray_width = 0.035;            // толщина лучей (доля размера искры)
uniform float ray_strength = 0.75;          // яркость прямых лучей
uniform float diag_strength = 0.3;          // яркость косых лучей
uniform float core_size = 0.09;             // радиус белой сердцевины
uniform float twinkle = 0.3;                // насколько мерцает
uniform float pull = 0.6;                   // на сколько метров вынести к камере

void vertex() {
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
	vec4 view_pos = MODELVIEW_MATRIX * vec4(VERTEX, 1.0);
	vec3 center = (MODELVIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float dist = length(center);
	float k = max(dist - min(pull, max(dist - 0.3, 0.0)), 0.01) / max(dist, 0.01);
	view_pos.xyz *= k;   // вдоль луча к камере: на экране искра остаётся на месте и того же размера
	POSITION = PROJECTION_MATRIX * view_pos;
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float r = length(p);
	float seed = NODE_POSITION_WORLD.x * 3.1 + NODE_POSITION_WORLD.z * 1.7;
	float tw = 1.0 + twinkle * sin(TIME * 6.0 + seed) * sin(TIME * 2.3 + seed * 0.5);

	float core = exp(-(r * r) / (core_size * core_size));
	float soft = exp(-r * 9.0) * 0.4;
	float h = exp(-abs(p.y) / ray_width) * pow(max(1.0 - abs(p.x), 0.0), 2.0);
	float v = exp(-abs(p.x) / ray_width) * pow(max(1.0 - abs(p.y), 0.0), 2.0);
	vec2 q = vec2(p.x + p.y, p.x - p.y) * 0.7071;
	float d1 = exp(-abs(q.y) / ray_width) * pow(max(1.0 - abs(q.x) * 1.5, 0.0), 2.0);
	float d2 = exp(-abs(q.x) / ray_width) * pow(max(1.0 - abs(q.y) * 1.5, 0.0), 2.0);

	float a = core + soft + ((h + v) * ray_strength + (d1 + d2) * diag_strength) * tw;
	ALBEDO = mix(color.rgb, vec3(1.0), core * 0.7) * energy;
	ALPHA = clamp(a, 0.0, 1.0);
}
