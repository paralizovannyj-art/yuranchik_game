// Туман, который не трогает свет (правило автора: «темнота тумана только там, где нет света»).
// Обычный туман движка смешивает с тёмным цветом всё подряд — и окна, и снег под фонарём, и пятно фонарика.
// Здесь туман считается после освещения: по глубине пикселя (линейно, begin → end метров) и по его яркости.
// Тёмное (нет света) уходит в цвет тумана, освещённое и светящееся остаётся как есть.
// Полноэкранный квадрат: MeshInstance3D с QuadMesh 2×2 и огромным custom_aabb, создаёт scripts/core/graphics.gd.
// Рисуется первым среди прозрачных (render_priority -128): частицы снега и карточки света ложатся поверх него.
shader_type spatial;
render_mode unshaded, fog_disabled, depth_test_disabled, depth_draw_never, cull_disabled, shadows_disabled;

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;

uniform vec3 fog_color : source_color = vec3(0.018, 0.02, 0.028);
uniform float fog_begin = 3.0;          // м: ближе тумана нет
uniform float fog_end = 22.0;           // м: дальше — полный туман (если там нет света)
// яркость пикселя (линейная), ниже которой туман полный и выше которой его нет совсем
uniform float light_lo = 0.03;
uniform float light_hi = 0.18;
// небо (пиксели без геометрии) туман не прячет: зарево города и луну видно всегда, как в жизни;
// только лёгкая снежная дымка
uniform float sky_fog : hint_range(0.0, 1.0) = 0.2;

void vertex() {
	POSITION = vec4(VERTEX.xy, 0.5, 1.0);
}

void fragment() {
	vec3 c = textureLod(screen_tex, SCREEN_UV, 0.0).rgb;
	float depth = textureLod(depth_tex, SCREEN_UV, 0.0).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	vec3 ndc = vec3(SCREEN_UV, depth) * 2.0 - 1.0;
#else
	vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, depth);
#endif
	vec4 view = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
	float dist = length(view.xyz / view.w);
	float fog = clamp((dist - fog_begin) / max(fog_end - fog_begin, 0.001), 0.0, 1.0);
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	bool is_sky = depth >= 0.99999;
#else
	bool is_sky = depth <= 0.00001;      // Forward+: обратный Z, небо на дальней плоскости = 0
#endif
	float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
	float lit = smoothstep(light_lo, light_hi, lum);
	float amount = is_sky ? sky_fog : fog * (1.0 - lit);
	ALBEDO = mix(c, fog_color, amount);
}
