// Вид из окна комнаты Юрчика (assets/models/window_view.gltf, задача YUR-25): метель днём.
// Цвет — из «запечённой» текстуры свечения (свет пасмурного дня), лампы сцены и туман подъезда не действуют.
// Свой туман метели: чем дальше, тем больше всё тонет в светло-серой пелене (как на референсе из задачи).
// Внизу (ниже окна) пелена гуще — двора и земли почти не видно, только верхушки деревьев и силуэты домов.
// Материал ставит scripts/tools/ps2_import.gd при импорте. Числа ниже — константы (не uniform), поэтому
// после правки достаточно сохранить шейдер, переимпортировать модель не нужно.
shader_type spatial;
render_mode unshaded, fog_disabled, cull_back;

uniform sampler2D tex : source_color, filter_linear_mipmap, repeat_enable;
const float brightness = 0.36;     // ниже порога свечения (glow) подъезда, иначе окно засвечивает комнату
const vec3 fog_color = vec3(0.126, 0.13, 0.137);  // линейный цвет (≈ sRGB 0.39), уже с учётом brightness
const float fog_density = 0.035;      // на 20 м видно ~половину, дом напротив (70 м) — едва различимый силуэт
const float fog_start = 1.5;          // у самого стекла тумана нет
const float low_fog = 4.0;            // каждый метр ниже глаз считается как столько метров тумана

void fragment() {
	vec3 c = texture(tex, UV).rgb * brightness;
	vec3 wp = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float below = max(CAMERA_POSITION_WORLD.y - wp.y, 0.0);
	float d = max(length(VERTEX) - fog_start, 0.0) + below * low_fog;
	float f = 1.0 - exp(-d * fog_density);
	ALBEDO = mix(c, fog_color, f);
}
