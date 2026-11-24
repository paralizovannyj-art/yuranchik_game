// Зимнее ночное небо над городом: оранжево-серое зарево у горизонта,
// низкие облака, подсвеченные снизу натриевыми фонарями.
shader_type sky;
#include "res://shaders/compat_srgb.gdshaderinc"

uniform vec3 zenith_color : source_color = vec3(0.012, 0.016, 0.03);
uniform vec3 mid_color : source_color = vec3(0.07, 0.065, 0.07);
uniform vec3 horizon_color : source_color = vec3(0.42, 0.25, 0.14);
uniform vec3 ground_color : source_color = vec3(0.05, 0.04, 0.035);
uniform float glow_height : hint_range(0.02, 1.0) = 0.28;
uniform float glow_energy : hint_range(0.0, 4.0) = 1.3;
uniform float cloud_amount : hint_range(0.0, 1.0) = 0.6;
uniform float cloud_speed : hint_range(0.0, 0.1) = 0.004;
// откуда зарево: направление (x, z) на город; (0, 0) — зарево по всему горизонту.
// С другой стороны (поле, сёла) зарево слабее в glow_back раз.
uniform vec2 glow_dir = vec2(0.0, 0.0);
uniform float glow_back : hint_range(0.0, 1.0) = 0.25;
// Луна — там, откуда светит DirectionalLight «Moon» (LIGHT0). Видна всегда: сквозь облака — размытым пятном.
// Реальный угловой радиус 0.25°; чуть больше, чтобы читалась в 720 строк (луна у горизонта и так кажется крупнее).
uniform vec3 moon_color : source_color = vec3(0.86, 0.88, 0.95);
uniform float moon_radius_deg : hint_range(0.1, 3.0) = 0.4;   // настоящая луна ≈ 0.26°; 0.4 — чтобы не пропала в PS2-мыле
uniform float moon_halo_deg : hint_range(0.5, 20.0) = 6.0;    // ширина ореола — от дымки, не от диска
uniform float moon_energy : hint_range(0.0, 8.0) = 1.6;
uniform float moon_halo : hint_range(0.0, 2.0) = 0.35;     // ореол в снежной дымке
uniform float moon_cloud_dim : hint_range(0.0, 1.0) = 0.6; // насколько облако гасит диск

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
	vec3 zenith_c = compat_lin(zenith_color);
	vec3 mid_c = compat_lin(mid_color);
	vec3 horizon_c = compat_lin(horizon_color);
	vec3 ground_c = compat_lin(ground_color);
	float y = EYEDIR.y;
	if (y < 0.0) {
		COLOR = compat_enc(mix(horizon_c * 0.35, ground_c, clamp(-y * 6.0, 0.0, 1.0)));
	} else {
		float g = exp(-y / glow_height);
		if (dot(glow_dir, glow_dir) > 0.0001) {
			vec2 d = EYEDIR.xz / max(length(EYEDIR.xz), 0.0001);
			g *= mix(glow_back, 1.0, smoothstep(-0.6, 0.6, dot(d, normalize(glow_dir))));
		}
		vec3 col = mix(zenith_c, mid_c, exp(-y / 0.6));
		col = mix(col, horizon_c * glow_energy, g * g);
		// низкие облака: проекция на плоскость
		vec2 uv = EYEDIR.xz / (y + 0.08) * 0.6 + TIME * cloud_speed;
		float c = fbm(uv);
		c = smoothstep(0.42, 0.85, c) * cloud_amount;
		// облака подсвечены заревом снизу: ярче у горизонта
		vec3 cloud_col = mix(mid_c * 1.6, horizon_c * 0.9, g);
		float cover = c * (1.0 - smoothstep(0.6, 1.0, y));
		// луна: диск + ореол, облако приглушает диск и размывает его в пятно
		if (LIGHT0_ENABLED) {
			vec3 mc = compat_lin(moon_color);
			float cosd = dot(EYEDIR, normalize(LIGHT0_DIRECTION));
			float ang = degrees(acos(clamp(cosd, -1.0, 1.0)));
			float disk = 1.0 - smoothstep(moon_radius_deg * 0.7, moon_radius_deg, ang);
			float halo = exp(-ang / moon_halo_deg) * moon_halo;
			col += mc * moon_energy * disk * (1.0 - cover * moon_cloud_dim);
			col += mc * halo * (0.4 + cover);
		}
		col = mix(col, cloud_col, cover * 0.85);
		COLOR = compat_enc(col);
	}
}
