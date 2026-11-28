# Текстуры детской площадки под окном Юрчика (YUR-49, этап 1) — общие для меню и локации.
# Референсы — вложения YUR-49 (фото площадки из окна, листы ассетов): облупленная краска на металле и досках,
# решётчатые оградки клумб из потемневших реек, мятая оцинковка на крыше песочницы.
#   pg_paint   — крашеный металл в сколах и ржавчине, светло-серый: цвет даёт цвет вершин (лавки, качели, покрышки)
#   pg_planks  — крашеные доски с щелями и вытертой краской (домик-башня, борта песочницы, сиденья лавок)
#   pg_lattice — решётка из реек крест-накрест с альфой, сверху налип снег (оградки клумб)
#   pg_roof    — оцинкованный лист с рёбрами и рыжими потёками (крыша песочницы)
# Запуск в открытом Blender (через Blender MCP):
#   PG_ROOT = r"<папка проекта>"; exec(open(PG_ROOT + r"\tools\blender\playground_textures.py", encoding="utf-8").read())
import os
import sys
import importlib

ROOT = globals().get("PG_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import numpy as np
import tex_lib
import ps2_style
importlib.reload(ps2_style)
importlib.reload(tex_lib)
tex_lib.TEX_DIR = os.path.join(ROOT, "assets", "textures")
from tex_lib import fbm, rgb, save, streaks

_eb = {"EB_ROOT": ROOT, "EB_ONLY": ["-"], "__name__": "pg_eb"}
exec(open(os.path.join(HERE, "east_bridge_textures.py"), encoding="utf-8").read(), _eb)
save_rgba = _eb["save_rgba"]

RUST = rgb((0.38, 0.2, 0.1))
SNOW = rgb((0.88, 0.9, 0.96))


def rng_for(name):
    return np.random.default_rng(sum(map(ord, name)) * 7919 + 49)


def paint():
    """Краска по металлу: почти белая (оттенок — цветом вершин), сколы до грунта и ржавчины, потёки. 128², тайл 1 м."""
    rng = rng_for("pg_paint")
    w = h = 128
    arr = rgb((0.86, 0.86, 0.84)) * (0.9 + fbm(w, h, 6, 6, rng, oct=3)[..., None] * 0.12)
    chips = np.clip((fbm(w, h, 14, 14, rng, oct=4) - 0.66) * 9.0, 0, 1)
    under = RUST * 1.2 * (0.8 + fbm(w, h, 20, 20, rng, oct=2)[..., None] * 0.4)
    arr = arr * (1 - chips[..., None] * 0.85) + under * chips[..., None] * 0.85
    arr *= 1 - streaks(w, h, rng, 0.7)[..., None] * 0.22
    save("pg_paint", arr)


def planks():
    """Доски внахлёст: 6 на тайл (1 м), тёмные щели, краска вытерта до серого дерева по краям и пятнами."""
    rng = rng_for("pg_planks")
    w = h = 128
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    k = (yy % (h / 6)) / (h / 6)                                       # 0 … 1 поперёк доски
    arr = rgb((0.86, 0.85, 0.8)) * (0.88 + fbm(w, h, 3, 24, rng, oct=3)[..., None] * 0.16)
    wood = rgb((0.42, 0.38, 0.33)) * (0.8 + fbm(w, h, 40, 4, rng, oct=3)[..., None] * 0.35)
    wear = np.clip((fbm(w, h, 8, 14, rng, oct=4) - 0.58) * 7.0, 0, 1)
    wear = np.maximum(wear, np.clip((np.abs(k - 0.5) - 0.38) * 9.0, 0, 1) * 0.7)   # края досок вытерты
    arr = arr * (1 - wear[..., None]) + wood * wear[..., None]
    gap = np.clip(1 - np.minimum(k, 1 - k) * (h / 6) / 1.6, 0, 1)          # щель между досками
    arr *= 1 - gap[..., None] * 0.75
    arr *= 1 - streaks(w, h, rng, 0.5)[..., None] * 0.15
    save("pg_planks", arr)


def lattice():
    """Решётка оградки клумбы: рейки крест-накрест с шагом 0.25 м между двумя брусьями. 128 × 64 на 1 × 0.5 м,
    альфа — по рейкам. Сверху на брусе и на верхних кромках реек — снег."""
    rng = rng_for("pg_lattice")
    w, h = 128, 64
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    s, t = 32.0, 5.0
    d1 = (xx + yy) % s < t
    d2 = (xx - yy) % s < t
    rail = (yy < 6) | (yy >= h - 6)
    al = d1 | d2 | rail
    wood = rgb((0.34, 0.24, 0.16)) * (0.75 + fbm(w, h, 32, 4, rng, oct=3)[..., None] * 0.45)
    wood *= np.where(rail[..., None], 0.85, 1.0)
    above = np.zeros_like(al)
    above[1:] = al[:-1]
    top = al & ~above                                                    # верхняя кромка каждой рейки
    lumps = np.clip((fbm(w, h, 16, 4, rng, oct=2) - 0.45) * 5.0, 0, 1) > 0.5   # снег налип не везде
    snow = (top & lumps) | (yy < 3)
    arr = np.zeros((h, w, 4), np.float32)
    arr[..., :3] = np.where(snow[..., None], SNOW * (0.92 + fbm(w, h, 20, 10, rng, oct=2)[..., None] * 0.1), wood)
    arr[..., 3] = al.astype(np.float32)
    save_rgba("pg_lattice", arr)


def roof():
    """Оцинковка: рёбра через 0.25 м, мутный серый, рыжие потёки от гвоздей и кромки. 64², тайл 1 м."""
    rng = rng_for("pg_roof")
    w = h = 64
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rib = np.cos((xx % 16) / 16 * 2 * np.pi)
    arr = rgb((0.58, 0.6, 0.6)) * (0.85 + fbm(w, h, 4, 4, rng, oct=3)[..., None] * 0.2)
    arr *= (0.92 + rib[..., None] * 0.08)
    rs = streaks(w, h, rng, 1.3) * np.clip((fbm(w, h, 6, 2, rng, oct=2) - 0.45) * 4.0, 0, 1)
    arr = arr * (1 - rs[..., None] * 0.6) + RUST * rs[..., None] * 0.6
    save("pg_roof", arr)


ALL = (paint, planks, lattice, roof)


def main():
    for fn in ALL:
        fn()
    return {"made": ["pg_" + fn.__name__ for fn in ALL]}


result = main()
print(result)
