## Все надписи на табличках и вывесках района «Паскот» — в одном месте.
## Сейчас это ЗАГЛУШКИ (решение автора от 2026-11-13): настоящие названия улиц, номера домов, школы и трамвая,
## вывески магазинов автор пришлёт списком — тогда меняем только этот файл, сцены трогать не нужно.
## Ключ — то, что записано в поле key у узла-таблички (scripts/world/district_sign.gd).
class_name DistrictNames

const NAMES := {
	# проспект: таблички на домах северной стороны
	"street": "ПРОСПЕКТ",
	# остановка и трамвай
	"stop": "ТРАМВАЙ № _",
	# школа
	"school": "ШКОЛА № _",
	# магазины северной стороны проспекта (световые вывески над витринами): 1–2 — дом слева от перехода,
	# 3–8 — длинный дом, слева направо, если стоять лицом к нему. У ларьков надпись своя, на модели.
	"shop.1": "ГАСТРОНОМ",
	"shop.2": "ФОТО",
	"shop.3": "ПРОДУКТЫ",
	"shop.4": "АПТЕКА",
	"shop.5": "ХЛЕБ",
	"shop.6": "ПАРИКМАХЕРСКАЯ",
	"shop.7": "ОБУВЬ",
	"shop.8": "КНИГИ",
	# номера домов (ключ — имя модели дома из tools/district_buildings.json)
	"house.homeyard_homebuilding": "_",       # дом Юрчика
	"house.homeyard_westwing": "_",
	"house.homeyard_southrow": "_",
	"house.homeyard_eastkhr": "_",
	"house.westyard_tower": "_",
	"house.westyard_northrow": "_",
	"house.westyard_eastrow": "_",
	"house.westyard_westrow": "_",
	"house.westyard_southrow": "_",
	"house.school_eastwall": "_",
	"house.southyards_khrnorth": "_",
	"house.southyards_khrwest": "_",
	"house.southyards_khrsouth": "_",
	"house.boilerhouse_khr1": "_",
	"house.boilerhouse_khr2": "_",
	"house.terrain_northfacades": "_",
	"house.terrain_northfacades2": "_",
}


## Текст по ключу; для домов «_» превращается в «№ _».
static func text(key: String) -> String:
	var t: String = NAMES.get(key, "?")
	if key.begins_with("house."):
		return "№ " + t
	return t
