// PS2-style full-screen post-process.
// Put on a ColorRect that covers the screen inside a CanvasLayer.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;

// "Мыльность" PS2/ЭЛТ: лёгкое размытие в пикселях
uniform float blur_px : hint_range(0.0, 2.0) = 0.55;
// 16-битный кадровый буфер PS2: 32 уровня на канал + дизеринг
uniform float color_levels : hint_range(4.0, 256.0) = 32.0;
uniform float dither_strength : hint_range(0.0, 2.0) = 1.0;
// Цвет
uniform float saturation : hint_range(0.0, 2.0) = 0.78;
uniform float contrast : hint_range(0.5, 2.0) = 1.08;
uniform vec3 tint : source_color = vec3(0.90, 0.96, 1.0);
uniform vec3 shadow_tint : source_color = vec3(0.03, 0.05, 0.09);
// Плёнка / ЭЛТ
uniform float grain : hint_range(0.0, 0.3) = 0.045;
uniform float vignette : hint_range(0.0, 1.5) = 0.55;
uniform float scanlines : hint_range(0.0, 0.5) = 0.06;

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

	// цветокоррекция
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(vec3(l), c, saturation);
	c = (c - 0.5) * contrast + 0.5;
	c *= tint;
	c += shadow_tint * (1.0 - smoothstep(0.0, 0.35, l));

	// виньетка
	vec2 d = SCREEN_UV - 0.5;
	c *= 1.0 - dot(d, d) * vignette * 1.6;

	// зерно
	c += (hash(FRAGCOORD.xy + fract(TIME * 7.0) * 100.0) - 0.5) * grain;

	// сканлайны
	c *= 1.0 - scanlines * step(0.5, fract(FRAGCOORD.y * 0.5));

	// дизеринг + квантование цвета (16-бит)
	ivec2 ip = ivec2(FRAGCOORD.xy) % 4;
	float b = (BAYER[ip.y * 4 + ip.x] / 16.0 - 0.5) * dither_strength;
	c = floor(clamp(c, 0.0, 1.0) * (color_levels - 1.0) + 0.5 + b) / (color_levels - 1.0);

	COLOR = vec4(c, 1.0);
}
