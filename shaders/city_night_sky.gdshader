// Зимнее ночное небо над городом: оранжево-серое зарево у горизонта,
// низкие облака, подсвеченные снизу натриевыми фонарями.
shader_type sky;

uniform vec3 zenith_color : source_color = vec3(0.012, 0.016, 0.03);
uniform vec3 mid_color : source_color = vec3(0.07, 0.065, 0.07);
uniform vec3 horizon_color : source_color = vec3(0.42, 0.25, 0.14);
uniform vec3 ground_color : source_color = vec3(0.05, 0.04, 0.035);
uniform float glow_height : hint_range(0.02, 1.0) = 0.28;
uniform float glow_energy : hint_range(0.0, 4.0) = 1.3;
uniform float cloud_amount : hint_range(0.0, 1.0) = 0.6;
uniform float cloud_speed : hint_range(0.0, 0.1) = 0.004;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
		mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}

float fbm(vec2 p) {
	float v = 0.0;
	float a = 0.5;
	for (int i = 0; i < 5; i++) {
		v += noise(p) * a;
		p *= 2.03;
		a *= 0.5;
	}
	return v;
}

void sky() {
	float y = EYEDIR.y;
	if (y < 0.0) {
		COLOR = mix(horizon_color * 0.35, ground_color, clamp(-y * 6.0, 0.0, 1.0));
	} else {
		float g = exp(-y / glow_height);
		vec3 col = mix(zenith_color, mid_color, exp(-y / 0.6));
		col = mix(col, horizon_color * glow_energy, g * g);
		// низкие облака: проекция на плоскость
		vec2 uv = EYEDIR.xz / (y + 0.08) * 0.6 + TIME * cloud_speed;
		float c = fbm(uv);
		c = smoothstep(0.42, 0.85, c) * cloud_amount;
		// облака подсвечены заревом снизу: ярче у горизонта
		vec3 cloud_col = mix(mid_color * 1.6, horizon_color * 0.9, g);
		col = mix(col, cloud_col, c * (1.0 - smoothstep(0.6, 1.0, y)));
		COLOR = col;
	}
}
