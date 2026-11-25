## «Диск» компа Юрчика: обычная свежая Windows 7 без сюжетных файлов.
## Узел — словарь: name, kind (folder / file / app / drive / dvd / computer / libraries / library / recycle / network),
## children, parent, icon, text (у .txt), app (что запускает), date, system (нельзя удалить).
class_name W7Fs
extends RefCounted

signal changed                  ## что-то создали, удалили, переименовали

var computer: Dictionary
var c_drive: Dictionary
var dvd: Dictionary
var user: Dictionary
var desktop: Dictionary
var docs: Dictionary
var pics: Dictionary
var music: Dictionary
var video: Dictionary
var downloads: Dictionary
var libraries: Dictionary
var recycle: Dictionary          ## children — удалённое; у каждого from — откуда
var network: Dictionary
var favorites: Dictionary
var recent: Dictionary


func _init() -> void:
	computer = _node("Компьютер", "computer", "computer")
	c_drive = _add(computer, _node("Локальный диск (C:)", "drive", "drive_win"))
	dvd = _add(computer, _node("DVD RW дисковод (D:)", "dvd", "dvd"))
	_add(c_drive, _node("PerfLogs", "folder"))
	var pf := _add(c_drive, _node("Program Files", "folder"))
	for n: String in ["Common Files", "DVD Maker", "Internet Explorer", "MSBuild", "Reference Assemblies",
			"Windows Defender", "Windows Journal", "Windows Mail", "Windows Media Player", "Windows NT",
			"Windows Photo Viewer", "Windows Portable Devices", "Windows Sidebar"]:
		_add(pf, _node(n, "folder"))
	var google := _add(pf, _node("Google", "folder"))
	var chrome_dir := _add(_add(google, _node("Chrome", "folder")), _node("Application", "folder"))
	_add(chrome_dir, _app("chrome.exe", "chrome", "chrome"))
	_sort(pf)
	var win := _add(c_drive, _node("Windows", "folder"))
	for n: String in ["addins", "AppCompat", "AppPatch", "assembly", "Boot", "Branding", "Cursors", "debug",
			"diagnostics", "Fonts", "Globalization", "Help", "IME", "inf", "L2Schema", "LiveKernelReports",
			"Logs", "Media", "Microsoft.NET", "Offline Web Pages", "Panther", "PolicyDefinitions", "Prefetch",
			"Registration", "rescache", "Resources", "SchCache", "security", "ServiceProfiles", "servicing",
			"Setup", "SoftwareDistribution", "Speech", "System", "System32", "TAPI", "Tasks", "Temp", "tracing",
			"twain_32", "Web", "winsxs"]:
		_add(win, _node(n, "folder"))
	_add(win, _app("explorer.exe", "explorer", "explorer"))
	_add(win, _app("notepad.exe", "notepad", "notepad"))
	var users := _add(c_drive, _node("Пользователи", "folder"))
	_add(users, _node("Общие", "folder"))
	user = _add(users, _node("Юрчик", "folder", "user"))
	downloads = _add(user, _node("Загрузки", "folder", "downloads"))
	favorites = _add(user, _node("Избранное", "folder", "favorites"))
	_add(user, _node("Контакты", "folder"))
	video = _add(user, _node("Мои видеозаписи", "folder", "video"))
	docs = _add(user, _node("Мои документы", "folder", "docs"))
	pics = _add(user, _node("Мои рисунки", "folder", "pics"))
	music = _add(user, _node("Моя музыка", "folder", "music"))
	_add(user, _node("Поиски", "folder"))
	desktop = _add(user, _node("Рабочий стол", "folder", "desktop"))
	_add(user, _node("Сохраненные игры", "folder", "games"))
	_add(user, _node("Ссылки", "folder"))
	recent = _node("Недавние места", "folder", "recent")
	recent["parent"] = user
	_add(desktop, _app("Google Chrome", "chrome", "chrome"))
	_add(c_drive, _node("Program Files (x86)", "folder"))
	_sort(c_drive)
	for n: Dictionary in _all(c_drive):
		n["system"] = true
	for n: Dictionary in [downloads, docs, pics, music, video, desktop]:
		n["system"] = true
	for n: Dictionary in desktop["children"]:
		n["system"] = false
	libraries = _node("Библиотеки", "libraries", "libraries")
	for l: Array in [["Видео", "lib_video", video], ["Документы", "lib_docs", docs],
			["Изображения", "lib_pics", pics], ["Музыка", "lib_music", music]]:
		var lib := _add(libraries, _node(l[0], "library", l[1]))
		lib["target"] = l[2]
	recycle = _node("Корзина", "recycle", "recycle_empty")
	network = _node("Сеть", "network", "network")


func _node(n: String, kind: String, icon := "") -> Dictionary:
	if icon == "":
		icon = "folder" if kind == "folder" else ("txt" if kind == "file" else kind)
	return {"name": n, "kind": kind, "icon": icon, "children": [], "parent": null, "text": "",
			"date": "14.07.2009 8:52", "system": false}


func _app(n: String, app: String, icon: String) -> Dictionary:
	var d := _node(n, "app", icon)
	d["app"] = app
	return d


func _add(parent: Dictionary, n: Dictionary) -> Dictionary:
	n["parent"] = parent
	(parent["children"] as Array).append(n)
	return n


## Узлы — словари со ссылками на родителя, поэтому сравниваем «тот же ли это объект» (is_same),
## а не содержимое (== полез бы по кругу родитель ↔ дети).
static func has_node(arr: Array, n: Variant) -> bool:
	return index_of(arr, n) >= 0


static func index_of(arr: Array, n: Variant) -> int:
	for i in arr.size():
		if is_same(arr[i], n):
			return i
	return -1


static func remove_node(arr: Array, n: Variant) -> void:
	var i := index_of(arr, n)
	if i >= 0:
		arr.remove_at(i)


func _all(n: Dictionary) -> Array:
	var out := [n]
	for c: Dictionary in n["children"]:
		out.append_array(_all(c))
	return out


func _sort(n: Dictionary) -> void:
	(n["children"] as Array).sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var fa: bool = a["kind"] == "folder"
		var fb: bool = b["kind"] == "folder"
		if fa != fb:
			return fa
		return (a["name"] as String).naturalnocasecmp_to(b["name"]) < 0)


## Что показывать в папке (библиотека показывает свою папку).
func items(loc: Dictionary) -> Array:
	if loc["kind"] == "library":
		return loc["target"]["children"]
	return loc["children"]


func real(loc: Dictionary) -> Dictionary:
	return loc["target"] if loc["kind"] == "library" else loc


func now() -> String:
	return "%s %s" % [W7.now_date(), W7.now_time()]


func unique_name(folder: Dictionary, base: String, ext := "") -> String:
	var names := {}
	for c: Dictionary in real(folder)["children"]:
		names[(c["name"] as String).to_lower()] = true
	var n := base + ext
	var i := 2
	while names.has(n.to_lower()):
		n = "%s (%d)%s" % [base, i, ext]
		i += 1
	return n


func create(folder: Dictionary, kind: String) -> Dictionary:
	var f := real(folder)
	var n: Dictionary
	if kind == "folder":
		n = _node(unique_name(f, "Новая папка"), "folder")
	else:
		n = _node(unique_name(f, "Новый текстовый документ", ".txt"), "file")
	n["date"] = now()
	_add(f, n)
	_sort(f)
	changed.emit()
	return n


func save_text(folder: Dictionary, name: String, text: String) -> Dictionary:
	var f := real(folder)
	if not name.to_lower().ends_with(".txt"):
		name += ".txt"
	for c: Dictionary in f["children"]:
		if (c["name"] as String).to_lower() == name.to_lower() and c["kind"] == "file":
			c["text"] = text
			c["date"] = now()
			changed.emit()
			return c
	var n := _node(name, "file")
	n["text"] = text
	n["date"] = now()
	_add(f, n)
	_sort(f)
	changed.emit()
	return n


func rename(n: Dictionary, new_name: String) -> bool:
	new_name = new_name.strip_edges()
	if new_name == "" or new_name.contains("\\") or new_name.contains("/") or new_name.contains(":"):
		return false
	n["name"] = new_name
	if n["parent"]:
		_sort(n["parent"])
	changed.emit()
	return true


func to_recycle(n: Dictionary) -> void:
	var p: Dictionary = n["parent"]
	remove_node(p["children"], n)
	n["from"] = p
	n["deleted"] = now()
	n["parent"] = recycle
	(recycle["children"] as Array).append(n)
	recycle["icon"] = "recycle_full"
	changed.emit()


func restore_all() -> void:
	for n: Dictionary in (recycle["children"] as Array).duplicate():
		var p: Dictionary = n["from"]
		n["name"] = unique_name(p, n["name"].get_basename(), "." + n["name"].get_extension()) \
				if n["kind"] == "file" else unique_name(p, n["name"])
		n["parent"] = p
		(p["children"] as Array).append(n)
		_sort(p)
	(recycle["children"] as Array).clear()
	recycle["icon"] = "recycle_empty"
	changed.emit()


func empty_recycle() -> void:
	(recycle["children"] as Array).clear()
	recycle["icon"] = "recycle_empty"
	changed.emit()


## Путь «для адресной строки»: от корня к узлу.
func chain(loc: Dictionary) -> Array:
	var out := []
	var n: Variant = loc
	while n != null:
		out.push_front(n)
		n = n["parent"]
	return out


func size_text(n: Dictionary) -> String:
	if n["kind"] == "file":
		var kb := ceili((n["text"] as String).to_utf8_buffer().size() / 1024.0)
		return "%d КБ" % maxi(kb, 0 if (n["text"] as String).is_empty() else 1)
	if n["kind"] == "app":
		return {"chrome": "1 214 КБ", "notepad": "189 КБ", "explorer": "2 553 КБ"}.get(n.get("app", ""), "")
	return ""


func type_text(n: Dictionary) -> String:
	match n["kind"]:
		"folder": return "Папка с файлами"
		"file": return "Текстовый документ"
		"app": return "Ярлык" if is_same(n["parent"], desktop) else "Приложение"
	return ""
