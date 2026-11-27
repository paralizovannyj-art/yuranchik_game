// Небо главного меню (YUR-19): зимний закат над Паскотом, как на референсе
// docs/references/main_menu/image-20261127-134919.png.
// Почти всё небо затянуто тяжёлыми тёмными тучами (графит с синевой). Над высотками, правее центра кадра,
// в тучах вытянутый рваный разрыв, из него горит розово-лососевое зарево (солнце уже за горизонтом).
// Края туч вокруг разрыва подсвечены розовым, ниже разрыва до горизонта — розово-сиреневая подсветка.
// У самого горизонта — дымка цвета тумана (horizon_color = fog_light_color сцены): в ней тают дальние дома,
// и шва между землёй и небом не видно. Тучи медленно плывут.
shader_type sky;
#include "res://shaders/compat_srgb.gdshaderinc"

uniform vec3 zenith_color : source_color = vec3(0.09, 0.09, 0.12);    // небо в просветах вверху
uniform vec3 mid_color : source_color = vec3(0.2, 0.19, 0.25);         // небо в просветах пониже
uniform vec3 horizon_color : source_color = vec3(0.46, 0.4, 0.5);     // дымка = цвет тумана сцены
uniform vec3 wash_color : source_color = vec3(0.55, 0.36, 0.45);        // розовая подсветка под разрывом
uniform vec3 glow_color : source_color = vec3(0.95, 0.4, 0.48);        // зарево в разрыве
uniform vec3 core_color : source_color = vec3(1.0, 0.62, 0.62);        // самая яркая сердцевина разрыва
uniform vec3 cloud_dark : source_color = vec3(0.06, 0.065, 0.09);     // тучи
uniform vec3 cloud_lit : source_color = vec3(0.85, 0.42, 0.48);        // их подсвеченные края
uniform vec3 ground_color : source_color = vec3(0.4, 0.34, 0.42);
uniform float glow_energy : hint_range(0.0, 6.0) = 1.4;
// разрыв: азимут (x, z), высота центра (y направления), ширина по азимуту (рад) и высота
uniform vec2 glow_dir = vec2(0.34, -0.94);
uniform float glow_elev : hint_range(0.0, 0.8) = 0.29;
uniform float glow_width : hint_range(0.05, 1.5) = 0.24;
uniform float glow_height : hint_range(0.01, 0.4) = 0.05;
uniform float horizon_height : hint_range(0.01, 0.4) = 0.07;
uniform float cloud_cover : hint_range(0.0, 1.0) = 0.84;
uniform float cloud_scale = 1.3;
uniform float cloud_speed : hint_range(0.0, 0.05) = 0.004;

// хэш без sin(): на больших координатах (у горизонта) не даёт квадратных артефактов
float hash(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
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
	mat2 r = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8));
	for (int i = 0; i < 6; i++) {
		v += noise(p) * a;
		p = r * p * 2.02 + vec2(3.1, 7.7);
		a *= 0.5;
	}
	return v;
}

void sky() {
	vec3 d = EYEDIR;
	vec3 hz = compat_lin(horizon_color);
	if (d.y < 0.0) {
		COLOR = compat_enc(mix(hz, compat_lin(ground_color), clamp(-d.y * 3.0, 0.0, 1.0)));
	} else {
		vec2 az = d.xz / max(length(d.xz), 0.0001);
		float a = acos(clamp(dot(az, normalize(glow_dir)), -1.0, 1.0));
		float A = a / glow_width;
		float e = (d.y - glow_elev) / glow_height;
		float below = clamp((glow_elev - d.y) / glow_elev, 0.0, 1.0);        // 0 у разрыва … 1 у горизонта

		// небо за тучами
		vec3 col = mix(compat_lin(mid_color), compat_lin(zenith_color), smoothstep(0.05, 0.7, d.y));
		// розовая подсветка: широкий веер вокруг разрыва и под ним до горизонта
		float fan = exp(-a * a / (glow_width * glow_width * 7.0));
		float wash = fan * (d.y < glow_elev ? 1.0 - below * 0.35 : exp(-(d.y - glow_elev) * 7.0));
		col = mix(col, compat_lin(wash_color), wash * 0.6);
		// разрыв: рваный край ломает свой шум
		float wob = fbm(vec2(a * 6.0, d.y * 22.0) + vec2(2.3, 5.1)) - 0.5;
		float core = exp(-A * A - e * e) * clamp(0.8 + wob * 2.4, 0.0, 1.0);
		col += compat_lin(glow_color) * glow_energy * core;
		col += compat_lin(core_color) * glow_energy * pow(core, 3.0) * 0.8;

		// тучи — на «потолке»: дальше к горизонту мельче и плотнее
		vec2 uv = d.xz / (d.y + 0.06) * cloud_scale + vec2(TIME * cloud_speed, TIME * cloud_speed * 0.35);
		vec2 w = vec2(fbm(uv * 0.5 + vec2(1.7, 9.2)), fbm(uv * 0.5 + vec2(8.3, 2.8)));
		float n = fbm(uv + w * 1.8);
		float hole = exp(-A * A * 0.7 - e * e * 0.5);                     // в разрыве туч меньше
		float thr = 1.0 - cloud_cover + hole * 0.5;
		float c = smoothstep(thr, thr + 0.18, n);
		float thick = smoothstep(thr, thr + 0.4, n);
		// тёмные тучи с рыхлой фактурой; тонкие края у разрыва и снизу над подсветкой — розовые
		// объём: верх клубов чуть светлее (фактура), снизу над подсветкой — лёгкий отсвет
		vec3 cc = compat_lin(cloud_dark) * (0.55 + 1.3 * fbm(uv * 2.2 + 4.0)) + compat_lin(wash_color) * wash * 0.12 * (1.0 - thick);
		float near = exp(-a * a / (glow_width * glow_width * 3.0) - e * e * 0.06);
		float lit = clamp((1.0 - thick) * near * 1.6 + near * near * 0.2, 0.0, 1.0);
		cc = mix(cc, compat_lin(cloud_lit) * (0.55 + near * 0.6), lit);
		col = mix(col, cc, c);

		// дымка у горизонта: тот же цвет, что у тумана сцены — дальние дома тают в ней без шва
		float h = exp(-d.y / horizon_height);
		col = mix(col, hz, clamp(h, 0.0, 1.0));
		COLOR = compat_enc(col);
	}
}
