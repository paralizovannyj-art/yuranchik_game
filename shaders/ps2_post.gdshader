// PS2-style full-screen post-process (ориентир: Obscure / Fleshbite).
// Висит на ColorRect во весь экран внутри CanvasLayer.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;

// «Мыльность» PS2 / ЭЛТ
uniform float blur_px : hint_range(0.0, 2.0) = 0.4;
// 16-битный цвет PS2 + дизеринг
uniform float color_levels : hint_range(4.0, 256.0) = 48.0;
uniform float dither_strength : hint_range(0.0, 2.0) = 0.6;
// Тон
uniform float black_crush : hint_range(0.0, 0.3) = 0.06;   // «съесть» тени
uniform float s_curve : hint_range(0.0, 1.0) = 0.55;       // контраст S-кривой
uniform float saturation : hint_range(0.0, 2.0) = 1.1;
uniform float exposure : hint_range(0.5, 2.0) = 1.1;
uniform vec3 shadow_tint : source_color = vec3(0.0, 0.07, 0.11);    // бирюза в тенях
uniform vec3 highlight_tint : source_color = vec3(1.0, 0.94, 0.86); // тёплые света
// Ореол вокруг ярких мест (поверх glow движка)
uniform float halo : hint_range(0.0, 1.0) = 0.25;
// Плёнка
uniform float grain : hint_range(0.0, 0.3) = 0.05;
uniform float vignette : hint_range(0.0, 2.0) = 0.9;

const float BAYER[16] = float[](
	0.0, 8.0, 2.0, 10.0,
	12.0, 4.0, 14.0, 6.0,
	3.0, 11.0, 1.0, 9.0,
	15.0, 7.0, 13.0, 5.0);

float hash(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

void fragment() {
	vec2 px = SCREEN_PIXEL_SIZE * blur_px;
	vec3 c = texture(screen_tex, SCREEN_UV).rgb * 0.4;
	c += texture(screen_tex, SCREEN_UV + vec2(px.x, 0.0)).rgb * 0.15;
	c += texture(screen_tex, SCREEN_UV - vec2(px.x, 0.0)).rgb * 0.15;
	c += texture(screen_tex, SCREEN_UV + vec2(0.0, px.y)).rgb * 0.15;
	c += texture(screen_tex, SCREEN_UV - vec2(0.0, px.y)).rgb * 0.15;

	// широкий мягкий ореол из мип-уровня
	vec3 wide = textureLod(screen_tex, SCREEN_UV, 3.5).rgb;
	c += max(wide - 0.45, 0.0) * halo;

	c *= exposure;
	// «съедаем» чёрный
	c = max(c - black_crush, 0.0) / (1.0 - black_crush);
	c = clamp(c, 0.0, 1.0);
	// S-кривая
	c = mix(c, c * c * (3.0 - 2.0 * c), s_curve);
	// насыщенность
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(vec3(l), c, saturation);
	// сплит-тонирование
	c += shadow_tint * pow(1.0 - l, 3.0);
	c *= mix(vec3(1.0), highlight_tint, smoothstep(0.4, 1.0, l));

	// виньетка
	vec2 d = (SCREEN_UV - 0.5) * vec2(1.0, 0.85);
	c *= clamp(1.0 - dot(d, d) * vignette * 2.2, 0.0, 1.0);

	// зерно
	c += (hash(FRAGCOORD.xy + fract(TIME * 7.0) * 100.0) - 0.5) * grain;

	// дизеринг + квантование
	ivec2 ip = ivec2(FRAGCOORD.xy) % 4;
	float b = (BAYER[ip.y * 4 + ip.x] / 16.0 - 0.5) * dither_strength;
	c = floor(clamp(c, 0.0, 1.0) * (color_levels - 1.0) + 0.5 + b) / (color_levels - 1.0);

	COLOR = vec4(c, 1.0);
}
