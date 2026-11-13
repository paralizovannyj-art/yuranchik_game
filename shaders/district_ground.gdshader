// Земля микрорайона: на горизонтальных гранях — снег, на вертикальных (уступы террас, стенки котлована) — бетон.
// Текстуры кладутся по мировым координатам, поэтому плиты любого размера стыкуются без швов.
shader_type spatial;

uniform sampler2D snow_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D wall_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float snow_scale = 4.0;     // метров на один повтор снега
uniform float wall_scale = 3.0;     // метров на один повтор бетона

varying vec3 wpos;
varying vec3 wnorm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 n = abs(wnorm);
	vec3 col;
	if (n.y > 0.5) {
		col = texture(snow_tex, wpos.xz / snow_scale).rgb;
		// крупные пятна — чтобы повтор текстуры не бросался в глаза на больших плитах
		col *= 0.82 + 0.36 * texture(snow_tex, wpos.xz / (snow_scale * 9.3)).g;
	} else {
		vec2 uv = n.x > n.z ? wpos.zy : wpos.xy;
		col = texture(wall_tex, uv / wall_scale).rgb;
	}
	ALBEDO = col;
	ROUGHNESS = 0.95;
}
