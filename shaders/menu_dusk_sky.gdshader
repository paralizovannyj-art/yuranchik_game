// Небо главного меню (YUR-19): зимний закат над Паскотом, как на референсе docs/references/main_menu/.
// Сверху — тяжёлые тёмные тучи с сиреневым отливом; над стеной высоток в тучах разрыв, из него бьёт
// розово-малиновое зарево (солнце уже за горизонтом), края туч вокруг подсвечены. У горизонта —
// розовая дымка, в которую тают дальние дома. Тучи медленно плывут.
shader_type sky;
#include "res://shaders/compat_srgb.gdshaderinc"

uniform vec3 zenith_color : source_color = vec3(0.04, 0.035, 0.06);
uniform vec3 mid_color : source_color = vec3(0.16, 0.11, 0.18);
uniform vec3 horizon_color : source_color = vec3(0.55, 0.36, 0.46);
uniform vec3 glow_color : source_color = vec3(1.0, 0.3, 0.46);       // зарево в разрыве туч
uniform vec3 cloud_dark : source_color = vec3(0.07, 0.06, 0.09);
uniform vec3 cloud_lit : source_color = vec3(0.75, 0.28, 0.45);       // подсвеченные снизу края
uniform vec3 ground_color : source_color = vec3(0.3, 0.24, 0.3);
uniform float glow_energy : hint_range(0.0, 6.0) = 2.0;
// откуда зарево: азимут (x, z) и высота центра разрыва над горизонтом (y направления)
uniform vec2 glow_dir = vec2(0.62, -1.0);
uniform float glow_elev : hint_range(0.0, 0.6) = 0.24;
uniform float glow_width : hint_range(0.05, 1.5) = 0.32;              // ширина разрыва по азимуту, рад
uniform float glow_height : hint_range(0.02, 0.6) = 0.075;            // высота разрыва (по y направления)
uniform float horizon_height : hint_range(0.02, 0.6) = 0.1;
uniform float cloud_cover : hint_range(0.0, 1.0) = 0.84;
uniform float cloud_scale = 0.55;
uniform float cloud_speed : hint_range(0.0, 0.05) = 0.003;

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
	for (int i = 0; i < 6; i++) {
		v += noise(p) * a;
		p = p * 2.03 + vec2(1.7, 9.2);
		a *= 0.5;
	}
	return v;
}

void sky() {
	float y = EYEDIR.y;
	vec3 hor = compat_lin(horizon_color);
	if (y < 0.0) {
		COLOR = compat_enc(mix(hor * 0.7, compat_lin(ground_color), clamp(-y * 5.0, 0.0, 1.0)));
	} else {
		// разрыв: близость к направлению зарева по азимуту и по высоте
		vec2 az = EYEDIR.xz / max(length(EYEDIR.xz), 0.0001);
		float a = acos(clamp(dot(az, normalize(glow_dir)), -1.0, 1.0));
		float e = (y - glow_elev) / glow_height;
		// край разрыва рваный: форму ломает крупный шум (свой, не туч)
		vec2 guv = vec2(a * 3.0, y * 9.0);
		float wob = fbm(guv + vec2(4.2, 1.3)) - 0.5;
		float gap = exp(-(a * a) / (glow_width * glow_width) - e * e) * clamp(0.75 + wob * 2.2, 0.0, 1.0);
		float near = exp(-(a * a) / (glow_width * glow_width * 5.0) - e * e * 0.12);   // широкая подсветка вокруг
		float side = smoothstep(-0.4, 0.9, dot(az, normalize(glow_dir)));

		vec3 col = mix(compat_lin(zenith_color), compat_lin(mid_color), exp(-y / 0.3));
		float h = exp(-y / horizon_height);
		col = mix(col, hor * mix(0.55, 1.0, side), h);
		col += compat_lin(glow_color) * glow_energy * (gap * 0.9 + near * 0.08);

		// тучи: низкий слой, рваные края; в разрыве порог выше — туч меньше
		vec2 uv = EYEDIR.xz / (y + 0.05) * cloud_scale + vec2(TIME * cloud_speed, TIME * cloud_speed * 0.3);
		float n = fbm(uv);
		float n2 = fbm(uv * 2.7 + 3.1);
		float v = n * 0.75 + n2 * 0.3;
		float thr = 1.0 - cloud_cover + gap * 0.42;
		float c = smoothstep(thr, thr + 0.2, v);
		float edge = c * (1.0 - smoothstep(thr + 0.03, thr + 0.28, v));
		vec3 cc = compat_lin(cloud_dark) * (0.55 + 0.9 * n2);
		float lit = clamp(edge * (near * 2.0 + h * 0.35) + near * gap * 0.6 + near * 0.12, 0.0, 1.0);
		cc = mix(cc, compat_lin(cloud_lit) * (0.6 + near * 0.9), lit);
		cc = mix(cc, hor * 0.5, h * 0.7);                                // у горизонта тучи тонут в дымке
		col = mix(col, cc, c * (1.0 - h * 0.5));
		COLOR = compat_enc(col);
	}
}
