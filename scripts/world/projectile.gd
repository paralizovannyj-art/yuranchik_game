## Брошенный предмет: бутылка разбивается (звон отвлекает врагов), кирпич сбивает с ног и остаётся лежать.
class_name Projectile
extends RigidBody3D

var item_id := "bottle"
var _hit := false


func setup(id: String) -> void:
	item_id = id
	collision_layer = 32
	collision_mask = 1 | 4
	mass = 0.6
	continuous_cd = true
	contact_monitor = true
	max_contacts_reported = 3
	var cs := CollisionShape3D.new()
	var sh := SphereShape3D.new()
	sh.radius = 0.08
	cs.shape = sh
	add_child(cs)
	var path := "res://assets/models/item_%s.gltf" % id
	if ResourceLoader.exists(path):
		var m := (load(path) as PackedScene).instantiate() as Node3D
		m.position = Vector3(0, -0.1 if id == "bottle" else -0.03, 0)
		add_child(m)
	body_entered.connect(_on_hit)


func _on_hit(body: Node) -> void:
	if _hit:
		return
	_hit = true
	var pos := global_position
	var from := pos - linear_velocity.normalized() * 2.0
	var enemy := body as Enemy
	if enemy:
		enemy.take_thrown(item_id, from)
		Game.fx_burst(pos)
	if item_id == "bottle":
		Game.sfx("glass_break", pos, 3.0)
		Game.fx_burst(pos, Color(0.25, 0.5, 0.3), 14, 3.5)
		Game.emit_noise(pos, 16.0)
		queue_free()
	else:
		Game.sfx("brick_hit", pos, 2.0)
		Game.emit_noise(pos, 10.0)
		linear_velocity *= 0.3
		get_tree().create_timer(1.3).timeout.connect(_settle)


## Кирпич полежал — снова становится подбираемым предметом.
func _settle() -> void:
	var p := Pickup.new()
	p.item_id = item_id
	get_parent().add_child(p)
	p.global_position = global_position + Vector3(0, -0.04, 0)
	p.rotation.y = rotation.y
	queue_free()
