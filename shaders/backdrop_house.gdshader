// Дальние дома за краем района (этап E, docs/CITY_PLAN.md). Окна рисует шейдер — текстур нет.
// Модель: assets/models/district/backdrop.gltf (tools/blender/build_backdrop.py).
//   UV  — метры по фасаду и по высоте;
//   UV2 — x: номер дома + оттенок стены (дробная часть), y: доля горящих окон;
//         y = -1 — глухая стена, крыша, ствол дерева; y = -2 — полосы дымовой трубы.
// Свет и туман сцены на эти дома не действуют: дымку по расстоянию считаем сами,
// поэтому силуэты и огни окон не тонут в тумане, как бы далеко ни стояли.
shader_type spatial;
render_mode unshaded, fog_disabled;

uniform vec3 wall_color : source_color = vec3(0.035, 0.04, 0.055);
uniform vec3 haze_color : source_color = vec3(0.115, 0.085, 0.07);   // во что дома тают вдали (цвет зарева у земли)
uniform float haze_density = 0.0042;                                   // чем больше, тем раньше тают
uniform float haze_max : hint_range(0.0, 1.0) = 0.86;                  // до конца в небе не растворяются — силуэт остаётся
uniform vec2 cell = vec2(3.2, 2.8);                                    // шаг окон: по фасаду, по высоте (м)
uniform float window_energy = 0.9;
uniform float lit_scale : hint_range(0.0, 2.0) = 1.0;                  // общий множитель «сколько окон горит»

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void fragment() {
	float dist = length(VERTEX);
	float haze = min(1.0 - exp(-dist * haze_density), haze_max);
	float seed = floor(UV2.x);
	float tone = fract(UV2.x);
	vec3 col = wall_color * (0.55 + 0.9 * tone);
	vec3 glow = vec3(0.0);
	// glTF хранит V перевёрнутой (1 - v): возвращаем метры и код обратно
	vec2 uv = vec2(UV.x, 1.0 - UV.y);
	float code = 1.0 - UV2.y;
	if (code < -1.5) {
		// дымовая труба: красно-белые полосы
		float s = step(0.5, fract(uv.y / 13.0));
		col = mix(vec3(0.11, 0.105, 0.1), vec3(0.14, 0.025, 0.02), s);
	} else if (code >= 0.0) {
		vec2 c = uv / cell;
		vec2 id = floor(c);
		vec2 f = fract(c);
		float win = step(0.2, f.x) * step(f.x, 0.8) * step(0.28, f.y) * step(f.y, 0.8);
		float lit_ratio = code * lit_scale;
		float h = hash(id + seed * 17.31);
		float lit = step(h, lit_ratio);
		float k = hash(id * 1.73 + seed);
		// тёплая лампа, холодная «дневная», красноватая штора, синий телевизор
		vec3 wc = vec3(1.0, 0.7, 0.34);
		wc = mix(wc, vec3(0.8, 0.9, 1.0), step(0.78, k));
		wc = mix(wc, vec3(0.95, 0.35, 0.22), step(0.9, k));
		wc = mix(wc, vec3(0.35, 0.5, 0.95), step(0.96, k));
		wc *= 0.55 + 0.45 * hash(id + seed * 3.1);
		// вдали окна мельче пикселя — заменяем их ровным средним свечением, чтобы не рябило
		float fw = max(fwidth(c.x), fwidth(c.y));
		float far = smoothstep(0.35, 1.1, fw);
		vec3 sharp = wc * win * lit;
		vec3 avg = vec3(1.0, 0.72, 0.4) * lit_ratio * 0.3 * 0.75;
		glow = mix(sharp, avg, far) * window_energy;
		// тёмное стекло негорящих окон чуть светлее стены — ловит небо
		col = mix(col, col * 0.6 + vec3(0.012, 0.014, 0.02), win * (1.0 - lit) * (1.0 - far));
	}
	col = mix(col, haze_color, haze);
	ALBEDO = col + glow * (1.0 - 0.55 * haze);
}
