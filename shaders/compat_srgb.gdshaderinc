// Одинаковый цвет на Vulkan и на OpenGL (режим «Слабый ПК», см. scripts/core/graphics.gd).
// В Compatibility (Godot 4.7.2) цвета source_color приходят в шейдер в sRGB, а ALBEDO / COLOR неба считаются
// заданными в sRGB. На Vulkan всё это линейное. Пока шейдер просто передаёт цвет дальше, разницы нет,
// но любая математика (умножить на яркость, смешать с туманом) в sRGB даёт другой, обычно более тёмный, цвет.
// Поэтому: каждый входной цвет source_color — через compat_lin(), считаем как обычно, результат — через compat_enc().
// На Vulkan обе функции ничего не делают.
// Для blend_add: на OpenGL сложение идёт уже в sRGB, поэтому там альфа вносится в цвет до перевода
// (compat_add_rgb / compat_add_alpha).

#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
vec3 compat_lin(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}
vec3 compat_enc(vec3 c) {
	c = max(c, vec3(0.0));
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}
vec3 compat_add_rgb(vec3 c, float a) {
	return compat_enc(c * a);
}
float compat_add_alpha(float a) {
	return 1.0;
}
#else
vec3 compat_lin(vec3 c) {
	return c;
}
vec3 compat_enc(vec3 c) {
	return c;
}
vec3 compat_add_rgb(vec3 c, float a) {
	return c;
}
float compat_add_alpha(float a) {
	return a;
}
#endif
