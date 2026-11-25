// Стекло Aero (Windows 7 на компе Юрчика): размытое то, что под окном/панелью, тонированное цветом вершин.
// Перед слоем стоит BackBufferCopy, поэтому SCREEN_TEXTURE — это всё, что нарисовано ниже.
// COLOR.rgb — оттенок, COLOR.a — насколько он перекрывает фон.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear;
uniform float blur = 1.6;      // шаг размытия, пиксели экрана

void fragment() {
	vec3 acc = vec3(0.0);
	float wsum = 0.0;
	for (int i = -3; i <= 3; i++) {
		for (int j = -3; j <= 3; j++) {
			vec2 o = vec2(float(i), float(j));
			float k = exp(-dot(o, o) / 6.0);
			acc += texture(screen_tex, SCREEN_UV + o * blur * SCREEN_PIXEL_SIZE).rgb * k;
			wsum += k;
		}
	}
	vec3 bg = acc / wsum;
	COLOR = vec4(mix(bg, COLOR.rgb, COLOR.a), 1.0);
}
