// Дальние огни за краем района (этап E): фонари, красные огни труб ТЭЦ, прожекторы, окна домиков в балке.
// Каждый огонь — квадрат, повёрнутый к району; здесь он превращается в мягкое пятно.
//   UV2.x — цвет: 0 натриевый, 1 красный, 2 белый, 3 окно;  UV2.y = 1 — мигает (верхние огни труб).
shader_type spatial;
render_mode unshaded, fog_disabled, blend_add, cull_disabled, depth_draw_never;

uniform float energy = 1.0;
uniform float haze_density = 0.003;        // огни тускнеют в тумане с расстоянием, но не гаснут

void fragment() {
	float r = length(UV - 0.5) * 2.0;
	float a = pow(clamp(1.0 - r, 0.0, 1.0), 2.4) + 0.9 * pow(clamp(1.0 - r * 3.2, 0.0, 1.0), 2.0);
	float idx = floor(UV2.x + 0.5);
	vec3 col = vec3(1.0, 0.5, 0.15);
	if (idx > 2.5) {
		col = vec3(1.0, 0.72, 0.36);
	} else if (idx > 1.5) {
		col = vec3(0.85, 0.92, 1.0);
	} else if (idx > 0.5) {
		col = vec3(1.0, 0.06, 0.03);
	}
	float blink = 1.0;
	if (1.0 - UV2.y > 0.5) {      // glTF хранит V перевёрнутой
		blink = 0.25 + 0.75 * smoothstep(0.0, 0.25, sin(TIME * 2.1));
	}
	float fade = exp(-length(VERTEX) * haze_density);
	ALBEDO = col * energy * blink * (0.35 + 0.65 * fade);
	ALPHA = clamp(a, 0.0, 1.0);
}
