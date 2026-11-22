# Бюджет треугольников персонажей (решение 2026-11-22, docs/design/ps2-style/README.md):
#   главный герой ≤ 8 000, остальные персонажи ≤ 5 000, массовка ≤ 2 000.
# Скрипты сборки вызывают check() и кладут результат в info["budget"]; при превышении — громкое предупреждение
# в консоль (сборку не останавливает: решать, резать модель или нет, — человеку).
LIMITS = {"hero": 8000, "character": 5000, "crowd": 2000}


def check(name, tris, role="character"):
    limit = LIMITS[role]
    ok = tris <= limit
    msg = "%s: %d / %d треугольников (%s)" % (name, tris, limit, role)
    if not ok:
        print("!!! PS2 BUDGET: превышен бюджет — " + msg)
    return {"tris": tris, "limit": limit, "role": role, "ok": ok}
