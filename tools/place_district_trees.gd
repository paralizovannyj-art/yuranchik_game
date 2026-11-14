extends SceneTree
## Расставляет много голых зимних деревьев по району «Паскот» и пишет их в scenes/district/trees.tscn
## (узел Trees в district.tscn). Точки проверяются физикой загруженного района:
##   - под точкой земля района (BlockoutBox kind = ground / snow), ровная;
##   - не на дороге (BlockoutBox kind = road, с запасом) и не у точек телепорта;
##   - у ствола свободно (нет стен, заборов, пропсов в радиусе TRUNK_CLEAR);
##   - крона не врезается в дома (шар над землёй свободен);
##   - не в проулках гаражей (там ездят машины) — GARAGE_Z;
##   - не у дверей (подъезды, сараи, «ракушки» — материалы Door / GarageDoors), чтобы не мешать выходить;
##   - не на стадионе и школьном дворе — KEEP_CLEAR.
## Плотность меняется шумом: рощи и поляны, а не ровная посадка. Раскладка повторяется (фиксированный seed).
## Запуск из папки проекта:
##   Godot.exe --headless --path . --script tools/place_district_trees.gd

const OUT := "res://scenes/district/trees.tscn"
const MODELS := ["res://assets/models/tree_a.gltf", "res://assets/models/tree_b.gltf"]
const AREA := Rect2(-100, -110, 200, 212)       ## X, Z района
const STEP := 2.6                               ## шаг сетки кандидатов, м
const MIN_GAP := 2.9                            ## меньше — гуще; ближе стволы не встают
const TRUNK_CLEAR := 1.1                        ## радиус свободного места у ствола
const ROAD_MARGIN := 2.0
const GARAGE_Z := Vector2(46.0, 102.0)          ## террасы гаражей — без деревьев
const DOOR_MATERIALS := ["Door", "GarageDoors"]
const DOOR_CLEAR := 7.0                         ## м от двери до ствола — место выйти и пройти
## Прямоугольники X, Z без деревьев: стадион с трибуной и двор школы между её крыльями.
const KEEP_CLEAR := [Rect2(31, -66, 57, 48)]
const SEED := 20261114

var rng := RandomNumberGenerator.new()


func _initialize() -> void:
	rng.seed = SEED
	change_scene_to_file("res://scenes/levels/district.tscn")
	_run.call_deferred()


func _run() -> void:
	while current_scene == null:
		await process_frame
	var lvl: Node3D = current_scene
	if lvl.has_node("Trees"):          # прошлая расстановка не должна мешать новой
		lvl.get_node("Trees").free()
	for i in 10:
		await physics_frame
	var space: PhysicsDirectSpaceState3D = lvl.get_world_3d().direct_space_state
	var roads: Array[Rect2] = []
	for n: Node in lvl.find_children("*", "Node3D", true, false):
		if n.get_script() and n.get("kind") == "road":
			var sz: Vector3 = n.get("size")
			var p: Vector3 = (n as Node3D).global_position
			roads.append(Rect2(p.x - sz.x / 2 - ROAD_MARGIN, p.z - sz.z / 2 - ROAD_MARGIN,
				sz.x + ROAD_MARGIN * 2, sz.z + ROAD_MARGIN * 2))
	var doors := _doors(lvl)
	var tps: Array[Vector3] = []
	for m: Node in lvl.get_node("Teleports").get_children():
		tps.append((m as Node3D).global_position)

	var noise := FastNoiseLite.new()
	noise.seed = SEED
	noise.frequency = 0.035

	var trees: Array = []           # [позиция, модель, поворот, масштаб]
	var x := AREA.position.x
	while x < AREA.end.x:
		var z := AREA.position.y
		while z < AREA.end.y:
			var q := Vector2(x + rng.randf_range(-1.4, 1.4), z + rng.randf_range(-1.4, 1.4))
			z += STEP
			# рощи и поляны: в «рощах» почти всё, на «полянах» редко
			var dens := clampf(0.75 + noise.get_noise_2d(q.x, q.y) * 1.2, 0.12, 1.0)
			if rng.randf() > dens:
				continue
			if q.y > GARAGE_Z.x and q.y < GARAGE_Z.y:
				continue
			var kept := false
			for r: Rect2 in KEEP_CLEAR:
				if r.has_point(q):
					kept = true
					break
			if kept:
				continue
			var on_road := false
			for r in roads:
				if r.has_point(q):
					on_road = true
					break
			if on_road:
				continue
			var hit := _ground(space, q)
			if hit.is_empty():
				continue
			var pos: Vector3 = hit["position"]
			var near_tp := false
			for t in tps:
				if Vector2(t.x, t.z).distance_to(q) < 5.0:
					near_tp = true
					break
			if near_tp:
				continue
			var at_door := false
			for d: Vector3 in doors:
				if absf(d.y - pos.y) < 4.0 and Vector2(d.x, d.z).distance_to(q) < DOOR_CLEAR:
					at_door = true
					break
			if at_door:
				continue
			var crowded := false
			for t: Array in trees:
				if Vector2(t[0].x, t[0].z).distance_to(q) < MIN_GAP:
					crowded = true
					break
			if crowded:
				continue
			if not _free(space, pos + Vector3.UP * 1.6, TRUNK_CLEAR, 1.4, hit["collider"]):
				continue
			if not _free(space, pos + Vector3.UP * 8.5, 2.6, 0.0, hit["collider"]):
				continue
			trees.append([pos, rng.randi_range(0, 1), rng.randf_range(0.0, TAU), rng.randf_range(0.75, 1.2)])
		x += STEP
	_write(trees)
	print("TREES ", trees.size())
	quit()


## Точки дверей: вершины поверхностей с материалами DOOR_MATERIALS, по одной на клетку 3 м.
func _doors(lvl: Node) -> Array[Vector3]:
	var cells := {}
	for n: Node in lvl.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		if mi.mesh == null:
			continue
		for i in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(i)
			if m == null or not (m.resource_name in DOOR_MATERIALS):
				continue
			for v: Vector3 in mi.mesh.surface_get_arrays(i)[Mesh.ARRAY_VERTEX]:
				var w := mi.global_transform * v
				cells[Vector3i(roundi(w.x / 3.0), roundi(w.y / 3.0), roundi(w.z / 3.0))] = w
	var out: Array[Vector3] = []
	out.assign(cells.values())
	print("DOORS ", out.size())
	return out


## Луч сверху: земля района под точкой (ровная) или пустой словарь.
func _ground(space: PhysicsDirectSpaceState3D, q: Vector2) -> Dictionary:
	var rq := PhysicsRayQueryParameters3D.create(Vector3(q.x, 60, q.y), Vector3(q.x, -40, q.y))
	var hit := space.intersect_ray(rq)
	if hit.is_empty() or (hit["normal"] as Vector3).y < 0.97:
		return {}
	var owner_box: Node = hit["collider"]
	while owner_box and not owner_box.get_script():
		owner_box = owner_box.get_parent()
	if owner_box == null or not (owner_box.get("kind") in ["ground", "snow"]):
		return {}
	return hit


## Свободен ли шар (или капсула высотой h) в точке — не считая земли под деревом.
func _free(space: PhysicsDirectSpaceState3D, at: Vector3, r: float, h: float, ground: Object) -> bool:
	var sh: Shape3D
	if h > 0.0:
		var c := CapsuleShape3D.new()
		c.radius = r
		c.height = h + r * 2.0
		sh = c
	else:
		var s := SphereShape3D.new()
		s.radius = r
		sh = s
	var qp := PhysicsShapeQueryParameters3D.new()
	qp.shape = sh
	qp.transform = Transform3D(Basis(), at)
	qp.exclude = [(ground as CollisionObject3D).get_rid()]
	return space.intersect_shape(qp, 1).is_empty()


func _write(trees: Array) -> void:
	var s := "[gd_scene format=3]\n\n"
	for i in MODELS.size():
		s += '[ext_resource type="PackedScene" path="%s" id="t%d"]\n\n' % [MODELS[i], i]
	s += '[sub_resource type="CylinderShape3D" id="trunk"]\nradius = 0.3\nheight = 4.0\n\n'
	s += '[node name="Trees" type="Node3D"]\n'
	s += "\n[node name=\"Trunks\" type=\"StaticBody3D\" parent=\".\"]\n"
	for i in trees.size():
		var p: Vector3 = trees[i][0]
		s += "\n[node name=\"Trunk%d\" type=\"CollisionShape3D\" parent=\"Trunks\"]\n" % i
		s += "transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, %.2f, %.2f, %.2f)\nshape = SubResource(\"trunk\")\n" % [p.x, p.y + 2.0, p.z]
	for i in trees.size():
		var p: Vector3 = trees[i][0]
		var b := Basis(Vector3.UP, trees[i][2]).scaled(Vector3.ONE * trees[i][3])
		s += "\n[node name=\"Tree%d\" parent=\".\" instance=ExtResource(\"t%d\")]\n" % [i, trees[i][1]]
		s += "transform = Transform3D(%.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.2f, %.2f, %.2f)\n" % [
			b.x.x, b.y.x, b.z.x, b.x.y, b.y.y, b.z.y, b.x.z, b.y.z, b.z.z, p.x, p.y - 0.05, p.z]
	var f := FileAccess.open(OUT, FileAccess.WRITE)
	f.store_string(s)
	f.close()
