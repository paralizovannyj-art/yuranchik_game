// Снежинка в метель: тонкая чёрточка, вытянутая по направлению полёта (как смазанный на выдержке снег).
// Для GPUParticles3D, у материала частиц должен быть включён particle_flag_align_y — тогда ось Y частицы смотрит
// по скорости. Чёрточка всегда повёрнута к камере плоскостью; летящие прямо в лицо снежинки видны точками
// в центре и всё длиннее к краям кадра — эффект «снег в лицо».
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, skip_vertex_transform;

uniform vec4 color : source_color = vec4(0.97, 0.98, 1.0, 0.9);
uniform float near_fade = 0.5;     // ближе этого (м) снежинка тает — не закрывает пол-экрана

varying float v_fade;

void vertex() {
	vec3 center = MODEL_MATRIX[3].xyz;
	float s = length(MODEL_MATRIX[0].xyz);
	vec3 axis = normalize(MODEL_MATRIX[1].xyz);
	vec3 to_cam = INV_VIEW_MATRIX[3].xyz - center;
	float dist = length(to_cam);
	vec3 side = cross(axis, to_cam / max(dist, 0.0001));
	if (length(side) < 0.001) {
		side = INV_VIEW_MATRIX[0].xyz;
	}
	side = normalize(side);
	vec3 world = center + (side * VERTEX.x + axis * VERTEX.y) * s;
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
	v_fade = smoothstep(near_fade * 0.4, near_fade, dist);
}

void fragment() {
	float across = 1.0 - abs(UV.x * 2.0 - 1.0);
	float along = sin(UV.y * PI);
	ALBEDO = color.rgb;
	ALPHA = color.a * COLOR.a * across * along * v_fade;
}
