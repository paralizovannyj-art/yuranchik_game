// Прицел из «жидкого стекла»: капля, которая раскрывается в кольцо.
// Прозрачный: преломляет то, что за ним, с лёгкой радугой по краям, светлым ободком и бликом.
// Висит на маленьком ColorRect в центре экрана (hud.gd), форму двигает параметр open.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;

uniform float open : hint_range(0.0, 1.0) = 0.0;          // 0 — капля, 1 — кольцо
uniform float ring_radius : hint_range(0.0, 0.5) = 0.30;   // радиус кольца (доля стороны прямоугольника)
uniform float dot_size : hint_range(0.0, 0.5) = 0.17;      // толщина в виде капли
uniform float ring_size : hint_range(0.0, 0.5) = 0.10;     // толщина в виде кольца
uniform float refraction : hint_range(0.0, 20.0) = 3.0;   // насколько стекло «гнёт» фон, в пикселях
uniform float dispersion : hint_range(0.0, 1.0) = 0.35;    // радуга по краям
uniform float frost : hint_range(0.0, 3.0) = 1.0;          // матовость, в пикселях
uniform float rim : hint_range(0.0, 1.0) = 0.55;           // светлый ободок
uniform float shine : hint_range(0.0, 1.0) = 0.7;          // блик сверху слева
uniform float shadow : hint_range(0.0, 1.0) = 0.25;        // мягкая тень, чтобы читался на светлом
uniform float alpha : hint_range(0.0, 1.0) = 1.0;

vec3 sample_frosted(vec2 uv, vec2 px) {
	vec3 c = texture(screen_tex, uv).rgb * 0.4;
	c += texture(screen_tex, uv + vec2(px.x, 0.0)).rgb * 0.15;
	c += texture(screen_tex, uv - vec2(px.x, 0.0)).rgb * 0.15;
	c += texture(screen_tex, uv + vec2(0.0, px.y)).rgb * 0.15;
	c += texture(screen_tex, uv - vec2(0.0, px.y)).rgb * 0.15;
	return c;
}

void fragment() {
	vec2 p = UV - 0.5;
	float d = length(p);
	float r = ring_radius * open;
	float half_w = mix(dot_size, ring_size, open) * 0.5;
	float sd = abs(d - r) - half_w;          // расстояние до края стекла: < 0 — внутри
	float aa = max(fwidth(sd), 1e-4);
	float body = 1.0 - smoothstep(-aa, aa, sd);

	// «толщина» стекла: 0 на краю, 1 по середине — по ней наклоняем нормаль, как у капли
	float t = clamp(-sd / half_w, 0.0, 1.0);
	float h = sqrt(1.0 - (1.0 - t) * (1.0 - t));
	vec2 outward = d > 1e-4 ? p / d : vec2(0.0);
	outward *= (d < r ? -1.0 : 1.0);
	vec2 n = outward * (1.0 - h);

	vec2 px = SCREEN_PIXEL_SIZE;
	vec2 off = -n * refraction * px;
	vec2 fr = px * frost;
	vec3 col;
	col.r = sample_frosted(SCREEN_UV + off * (1.0 - dispersion * 0.5), fr).r;
	col.g = sample_frosted(SCREEN_UV + off, fr).g;
	col.b = sample_frosted(SCREEN_UV + off * (1.0 + dispersion * 0.5), fr).b;

	// стекло чуть светлее фона и немного насыщеннее
	float lum = dot(col, vec3(0.299, 0.587, 0.114));
	col = mix(vec3(lum), col, 1.2) * 1.08 + 0.06;

	// светлый ободок по краю и блик со стороны света
	float edge = pow(1.0 - h, 3.0);
	col += vec3(rim * edge);
	vec2 light_dir = normalize(vec2(-0.6, -0.8));
	float spec = pow(max(dot(n, light_dir), 0.0), 2.0) * shine;
	col += vec3(spec);

	// мягкая тень под стеклом, сдвинутая вниз
	vec2 ps = p - vec2(0.0, 0.03);
	float sd_s = abs(length(ps) - r) - half_w;
	float sh = (1.0 - smoothstep(0.0, half_w * 1.6 + 0.04, sd_s)) * shadow * (1.0 - body);

	COLOR = vec4(mix(vec3(0.0), col, body), max(body, sh) * alpha);
}
