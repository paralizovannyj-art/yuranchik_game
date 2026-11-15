// Вид из окна комнаты Юрчика (assets/models/window_view.gltf, задача YUR-25): метель днём.
// Цвет — из «запечённой» текстуры свечения (свет пасмурного дня), лампы сцены и туман подъезда не действуют.
// Свой туман метели: чем дальше, тем больше всё тонет в светло-серой пелене (как на референсе из задачи).
// Материал ставит scripts/tools/ps2_import.gd при импорте, и значения uniform по умолчанию запоминаются в импорте:
// после правки чисел здесь переимпортируйте assets/models/window_view.gltf (Reimport в доке Import).
shader_type spatial;
render_mode unshaded, fog_disabled, cull_back;

uniform sampler2D tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float brightness = 0.36;     // ниже порога свечения (glow) подъезда, иначе окно засвечивает комнату
uniform vec3 fog_color : source_color = vec3(0.37, 0.375, 0.39);  // уже с учётом brightness
uniform float fog_density = 0.026;      // на 25 м видно ~половину, дом напротив (70 м) — бледный силуэт
uniform float fog_start = 2.0;          // у самого стекла тумана нет

void fragment() {
	vec3 c = texture(tex, UV).rgb * brightness;
	float d = max(length(VERTEX) - fog_start, 0.0);
	float f = 1.0 - exp(-d * fog_density);
	ALBEDO = mix(c, fog_color, f);
}
