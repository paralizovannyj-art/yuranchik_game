# -*- coding: utf-8 -*-
# Юрчик v3: low-poly модель в стиле PS2 по концепт-листу docs/references/yurchik_concept_sheet.png.
#
# Как устроено:
#   1. Геометрия — «кольца» (сечения), снятые с силуэтов концепта (вид спереди / сбоку / сзади), соединённые в трубы.
#   2. Развёртка — прямоугольные островки, автоматически упакованные в один атлас 512x512 (бюджет PS2).
#   3. Текстура — запекается проекцией концепт-листа на модель (спереди/сзади/сбоку) + дорисовка процедурно
#      (волосы с альфой, кисти, сумка, ремень, молоток). Свет «запечён» в текстуру, как в играх той эпохи.
#   4. Скелет — те же имена костей, что использует scripts/player/yurchik_anim.gd. Поза покоя — A-поза.
#   5. Анимации сюда не входят: этот скрипт экспортирует модель без них. После пересборки модели
#      сохраните сцену в tools/blender/yurchik_v3.blend и запустите tools/blender/retarget_ual_yurchik.py —
#      он перенесёт анимации Quaternius на скелет и переэкспортирует yurchik.gltf уже с ними.
#
# Запуск в Blender (Scripting):
#   YUR_ROOT = r"C:\путь\к\проекту"   # необязательно
#   exec(open(YUR_ROOT + r"\tools\blender\build_yurchik_v3.py", encoding="utf-8").read())
# Оси Blender: Z — вверх, персонаж смотрит в -Y (в Godot это +Z), левая сторона персонажа — +X.
import bpy, os, math
import numpy as np
from mathutils import Vector

ROOT = globals().get("YUR_ROOT", r"C:\Users\mrs\Documents\yuranchik_game")
STAGE = globals().get("YUR_STAGE", "full")          # "geo" — только сетка, "tex" — + текстура, "full" — + скелет и экспорт
TEX_DIR = os.path.join(ROOT, "assets", "textures")
OUT_DIR = os.path.join(ROOT, "assets", "models")
REF_PATH = os.path.join(ROOT, "docs", "references", "yurchik_concept_sheet.png")
ATLAS = 512
SCENE = "Yurchik3"

# --- привязка концепт-листа к метрам: 1 px = S м, земля — строка GY, центры трёх видов по X ---
S = 0.00338
GY = 558.0
CXF, CXS, CXB = 191.5, 508.0, 848.5


def rad(d): return d * math.pi / 180.0
def clamp(v, a, b): return max(a, min(b, v))
def lerp(a, b, t): return a + (b - a) * t


def smooth(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def sgnpow(v, e): return math.copysign(abs(v) ** e, v)


def sellipse(a, bf, bb, yc, th, n=2.5):
    """Точка суперэллипса: th = 0 — перед (-Y), 90° — левый бок (+X). bf/bb — глубина вперёд/назад."""
    s, c = math.sin(th), math.cos(th)
    e = 2.0 / n
    return a * sgnpow(s, e), yc - (bf if c >= 0 else bb) * sgnpow(c, e)


def mx(p, sx): return Vector((p[0] * sx, p[1], p[2]))


# =====================================================================================
#  Построитель сетки
# =====================================================================================
class MB:
    def __init__(self):
        self.co, self.w = [], []
        self.faces, self.fuv, self.fisl, self.ftag, self.fmat, self.fbake, self.fobj = [], [], [], [], [], [], []
        self.obj = 0

    def vert(self, p, w):
        self.co.append(Vector(p)); self.w.append(dict(w))
        return len(self.co) - 1

    def ring(self, pts, w):
        if isinstance(w, dict):
            return [self.vert(p, w) for p in pts]
        return [self.vert(p, wi) for p, wi in zip(pts, w)]

    def face(self, ids, uvs, isl, tag, mat=0, bake=True):
        ids2, uvs2 = [], []
        for i, u in zip(ids, uvs):
            if ids2 and ids2[-1] == i:
                continue
            ids2.append(i); uvs2.append(tuple(u))
        if len(ids2) > 1 and ids2[0] == ids2[-1]:
            ids2.pop(); uvs2.pop()
        if len(ids2) < 3:
            return None
        self.faces.append(tuple(ids2)); self.fuv.append(uvs2)
        self.fisl.append(isl); self.ftag.append(tag); self.fmat.append(mat); self.fbake.append(bake)
        self.fobj.append(self.obj)
        return len(self.faces) - 1

    def fnormal(self, fi):
        ids = self.faces[fi]; n = Vector((0, 0, 0))
        for k in range(len(ids)):
            a = self.co[ids[k]]; b = self.co[ids[(k + 1) % len(ids)]]
            n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
        return n

    def fcenter(self, fi):
        ids = self.faces[fi]; c = Vector((0, 0, 0))
        for i in ids:
            c += self.co[i]
        return c / len(ids)

    def orient(self, fis, inside=None, direction=None):
        """Единая ориентация набора граней: наружу от точки inside (или вдоль direction)."""
        fis = [f for f in fis if f is not None]
        if not fis:
            return fis
        if direction is None and inside is None:
            ids = {i for f in fis for i in self.faces[f]}
            inside = sum((self.co[i] for i in ids), Vector((0, 0, 0))) / len(ids)
        s = 0.0
        for f in fis:
            n = self.fnormal(f)
            s += n.dot(direction) if direction is not None else n.dot(self.fcenter(f) - inside)
        if s < 0:
            for f in fis:
                self.faces[f] = tuple(reversed(self.faces[f])); self.fuv[f] = list(reversed(self.fuv[f]))
        return fis

    def flat_uv(self, fis, size=0.01):
        pat = [(0, 0), (size, 0), (size, size), (0, size)]
        for f in fis:
            self.fuv[f] = [pat[k % 4] for k in range(len(self.faces[f]))]


def loft(mb, rings, isl, tag, closed=True, mat=0, bake=True, skip=None, seam=0, inside=None, direction=None,
         tagfn=None, pole=None, useg=None):
    """Соединяет кольца (списки индексов вершин) четырёхугольниками. UV — прямоугольный островок:
    u — средняя длина дуги по кольцам, v — среднее расстояние между кольцами. seam — колонка шва."""
    N = len(rings[0]); R = len(rings)
    order = [(seam + j) % N for j in range(N)] + ([seam % N] if closed else [])
    acc = [0.0] * len(order)
    for r in rings:
        c = 0.0
        for k in range(1, len(order)):
            d = (mb.co[r[order[k]]] - mb.co[r[order[k - 1]]]).length
            if useg:
                d *= useg(order[k - 1], order[k])
            c += d
            acc[k] += c
    u = [a / R for a in acc]
    v = [0.0]
    for i in range(1, R):
        v.append(v[-1] + sum((mb.co[rings[i][j]] - mb.co[rings[i - 1][j]]).length for j in range(N)) / N)
    fis = []
    for i in range(R - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(len(order) - 1):
            j0, j1 = order[k], order[k + 1]
            if skip and skip(i, j0, j1):
                continue
            t = tagfn(i, j0, j1) if tagfn else tag
            fis.append(mb.face((a[j0], b[j0], b[j1], a[j1]),
                               ((u[k], -v[i]), (u[k], -v[i + 1]), (u[k + 1], -v[i + 1]), (u[k + 1], -v[i])),
                               isl, t, mat, bake))
    if pole is not None:
        last = rings[-1]
        d = sum((mb.co[j] - mb.co[pole]).length for j in last) / N
        for k in range(len(order) - 1):
            j0, j1 = order[k], order[k + 1]
            fis.append(mb.face((last[j0], pole, last[j1]),
                               ((u[k], -v[-1]), ((u[k] + u[k + 1]) / 2, -v[-1] - d), (u[k + 1], -v[-1])),
                               isl, tag, mat, bake))
    return mb.orient(fis, inside, direction)


def ngon(mb, ids, isl, tag, direction, mat=0, bake=True):
    """Плоская грань-многоугольник с плоской развёрткой, нормалью вдоль direction."""
    d = Vector(direction).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))
    ax = ref.cross(d).normalized(); ay = d.cross(ax)
    o = mb.co[ids[0]]
    uvs = [((mb.co[i] - o).dot(ax), (mb.co[i] - o).dot(ay)) for i in ids]
    fi = mb.face(ids, uvs, isl, tag, mat, bake)
    mb.orient([fi], direction=d)
    return fi


def dark_cap(mb, ring, center, shrink, shift, direction):
    """Тёмная «заглушка» внутрь рукава/штанины/подола, чтобы не было видно пустоты."""
    inner = []
    for i in ring:
        p = Vector(center) + (mb.co[i] - Vector(center)) * shrink + Vector(shift)
        inner.append(mb.vert(p, mb.w[i]))
    fis = loft(mb, [ring, inner], "dark", "dark", direction=Vector(direction))
    mb.flat_uv(fis)
    return inner


# =====================================================================================
#  Скелет (имена — как в scripts/player/yurchik_anim.gd)
# =====================================================================================
JS = Vector((0.171, 0.010, 1.396))                 # плечевой сустав (левый)
AD = Vector((0.457, 0.0, -0.890)).normalized()     # ось руки в A-позе
AN = Vector((0.890, 0.0, 0.457)).normalized()      # перпендикуляр «вверх-наружу»
ELBOW_T, WRIST_T = 0.295, 0.525

BONES = [
    ("Pelvis", (0, -0.015, 0.92), (0, -0.015, 1.04), None),
    ("Spine", (0, -0.012, 1.04), (0, -0.012, 1.44), "Pelvis"),
    ("Head", (0, -0.030, 1.47), (0, -0.045, 1.76), "Spine"),
]
for _s, _sx in (("L", 1), ("R", -1)):
    _el = JS + AD * ELBOW_T + Vector((0, 0.004, 0)); _wr = JS + AD * WRIST_T + Vector((0, -0.022, 0))
    BONES += [
        ("UpperArm" + _s, tuple(mx(JS, _sx)), tuple(mx(_el, _sx)), "Spine"),
        ("Forearm" + _s, tuple(mx(_el, _sx)), tuple(mx(_wr, _sx)), "UpperArm" + _s),
        ("Hand" + _s, tuple(mx(_wr, _sx)), tuple(mx(_wr + Vector((0.032, -0.014, -0.11)), _sx)), "Forearm" + _s),
        ("Thigh" + _s, (0.095 * _sx, -0.015, 0.90), (0.110 * _sx, -0.018, 0.50), "Pelvis"),
        ("Shin" + _s, (0.110 * _sx, -0.018, 0.50), (0.120 * _sx, 0.018, 0.10), "Thigh" + _s),
        ("Foot" + _s, (0.120 * _sx, 0.018, 0.10), (0.150 * _sx, -0.150, 0.035), "Shin" + _s),
    ]


# =====================================================================================
#  Торс: куртка нараспашку + полоса худи под ней
# =====================================================================================
T_COLS = [("c0", 0, 'h'), ("hL", 17, 'h'), ("jL", 17, 'j'), ("L42", 42, 'j'), ("L67", 67.5, 'j'), ("L90", 90, 'j'),
          ("L112", 112.5, 'j'), ("L137", 137, 'j'), ("L160", 160, 'j'), ("b", 180, 'j'),
          ("R160", -160, 'j'), ("R137", -137, 'j'), ("R112", -112.5, 'j'), ("R90", -90, 'j'), ("R67", -67.5, 'j'),
          ("R42", -42, 'j'), ("jR", -17, 'j'), ("hR", -17, 'h')]
T_IDX = {c[0]: i for i, c in enumerate(T_COLS)}
# z, полуширина a, глубина вперёд bf, назад bb, центр yc, «квадратность» n
T_RINGS = [
    (1.478, 0.088, 0.080, 0.088, -0.020, 2.0),   # 0 ворот
    (1.440, 0.198, 0.108, 0.118, -0.012, 2.3),   # 1 плечи
    (1.335, 0.203, 0.150, 0.135, -0.010, 2.6),
    (1.230, 0.203, 0.160, 0.141, -0.010, 2.6),
    (1.125, 0.204, 0.167, 0.147, -0.010, 2.6),   # 4 подмышка
    (1.020, 0.210, 0.177, 0.152, -0.010, 2.6),
    (0.920, 0.218, 0.186, 0.156, -0.012, 2.6),
    (0.865, 0.222, 0.190, 0.158, -0.012, 2.6),   # 7 верх резинки
    (0.795, 0.208, 0.186, 0.150, -0.012, 2.6),   # 8 подол
]


def torso_w(z, x=0.0):
    if z >= 1.12:
        return {"Spine": 1.0}
    wp = 0.8 * smooth((1.12 - z) / 0.22)
    if z >= 0.90:
        return {"Spine": 1.0 - wp, "Pelvis": wp}
    k = 0.3 * smooth((0.90 - z) / 0.10)
    side = clamp(x / 0.08, -1, 1)
    return {"Spine": (1 - wp) * (1 - k), "Pelvis": wp * (1 - k), "ThighL": k * (0.5 + 0.5 * side), "ThighR": k * (0.5 - 0.5 * side)}


def torso_ring_at(z):
    """Параметры сечения куртки на высоте z (между плечами и подолом)."""
    rs = T_RINGS
    z = clamp(z, rs[8][0], rs[1][0])
    for i in range(1, 8):
        if rs[i][0] >= z >= rs[i + 1][0]:
            t = (rs[i][0] - z) / (rs[i][0] - rs[i + 1][0])
            return [lerp(rs[i][k], rs[i + 1][k], t) for k in range(1, 6)]
    return list(rs[8][1:6])


def torso_y(x, z, front=True):
    a, bf, bb, yc, n = torso_ring_at(z)
    k = (1 - clamp(abs(x) / a, 0, 0.999) ** n) ** (1 / n)
    return yc - bf * k if front else yc + bb * k


def build_torso(mb):
    rings = []
    for i, (z, a, bf, bb, yc, n) in enumerate(T_RINGS):
        ids = []
        for name, deg, layer in T_COLS:
            th = rad(deg)
            x, y = sellipse(a, bf, bb, yc, th, n)
            zz = z
            if i == 8:
                zz = z - 0.04 * max(0.0, math.cos(th)) ** 1.2      # полы спереди висят ниже
            if i == 7:
                zz = z - 0.028 * max(0.0, math.cos(th)) ** 1.2
            if layer == 'h':                                       # худи: утоплено под куртку
                if name == "c0":
                    y += 0.026
                else:
                    x -= math.copysign(0.007, x); y += 0.020
                if i == 8: zz = 0.800
                if i == 7: zz = 0.862
                if i == 0: zz = 1.452 if name == "c0" else 1.468
            ids.append(mb.vert((x, y, zz), torso_w(zz, x)))
        rings.append(ids)
    hole = {(T_IDX[a], T_IDX[b]) for a, b in (("L67", "L90"), ("L90", "L112"), ("R112", "R90"), ("R90", "R67"))}

    def skip(i, j0, j1):
        return i in (1, 2, 3) and (j0, j1) in hole

    def tagfn(i, j0, j1):
        la, lb = T_COLS[j0][2], T_COLS[j1][2]
        if la == 'h' and lb == 'h':
            return "hoodie"
        if la != lb:
            return "jacket_edge"
        return "jacket"

    loft(mb, rings, "torso", "jacket", seam=T_IDX["R90"], skip=skip, tagfn=tagfn, inside=Vector((0, -0.01, 1.15)))
    # низ куртки и ворот — тёмные заглушки
    dark_cap(mb, rings[8], (0, -0.012, 0.80), 0.5, (0, 0, 0.035), (0, 0, -1))
    dark_cap(mb, rings[0], (0, -0.020, 1.47), 0.6, (0, 0, -0.012), (0, 0, 1))
    return rings


# =====================================================================================
#  Рукава и кисти
# =====================================================================================
SLEEVE = [  # t и h верхней кромки, t и h нижней кромки (вдоль оси руки / поперёк), радиус по глубине, сдвиг по Y
    (0.070, 0.057, 0.285, -0.092, 0.071, 0.000),
    (0.170, 0.056, 0.315, -0.090, 0.068, 0.008),
    (0.275, 0.057, 0.350, -0.082, 0.064, 0.012),
    (0.370, 0.056, 0.400, -0.068, 0.058, 0.005),
    (0.460, 0.058, 0.460, -0.058, 0.052, -0.003),
    (0.530, 0.048, 0.530, -0.043, 0.044, -0.010),
    (0.578, 0.041, 0.578, -0.040, 0.040, -0.013),
]
HAND_W = JS + AD * WRIST_T + Vector((0, -0.014, 0))                   # запястье: рукав закрывает полладони
HAND_L = Vector((0.30, -0.10, -0.95)).normalized()
HAND_WD = Vector((-0.82, 0.57, 0.0)).cross(HAND_L).normalized()      # в сторону большого пальца
HAND_PN = HAND_L.cross(HAND_WD).normalized()                          # нормаль ладони
HAND = [  # l (вдоль кисти), p (к ладони), угол сгиба, полуширина, толщина к ладони / к тыльной стороне
    (-0.030, 0.000, 0, 0.027, 0.017, 0.017),
    (0.020, 0.000, 0, 0.040, 0.014, 0.015),
    (0.062, 0.002, 0, 0.046, 0.013, 0.015),
    (0.092, 0.001, 12, 0.044, 0.011, 0.013),
    (0.128, 0.016, 55, 0.041, 0.009, 0.010),
    (0.137, 0.047, 125, 0.038, 0.008, 0.009),
    (0.113, 0.062, 178, 0.034, 0.007, 0.007),
]
THUMB = [((0.026, 0.036, 0.006), 0.0150), ((0.058, 0.058, 0.022), 0.0140), ((0.088, 0.052, 0.044), 0.0120)]
THUMB_TIP = (0.103, 0.036, 0.057)
GRIP = (0.108, 0.0, 0.034)                         # центр хвата (l, w, p) — через него проходит рукоять молотка


def hand_pt(l, w, p):
    return HAND_W + HAND_L * l + HAND_WD * w + HAND_PN * p


def build_arm(mb, T, sx):
    s = "L" if sx > 0 else "R"
    UA, FA, HD = "UpperArm" + s, "Forearm" + s, "Hand" + s
    c = lambda n: T_IDX[s + n]
    ring0 = [T[1][c("90")], T[1][c("67")], T[2][c("67")], T[3][c("67")], T[4][c("67")],
             T[4][c("90")], T[4][c("112")], T[3][c("112")], T[2][c("112")], T[1][c("112")]]
    for vid, sp in zip(ring0, [0.80, 0.80, 0.78, 0.82, 0.90, 0.92, 0.90, 0.82, 0.78, 0.80]):
        mb.w[vid] = {"Spine": sp, UA: 1.0 - sp}
    rings = [ring0]
    cen = None
    for k, (tt, ht, tb, hb, rd, yc) in enumerate(SLEEVE):
        top = JS + AD * tt + AN * ht; bot = JS + AD * tb + AN * hb
        cen = (top + bot) / 2 + Vector((0, yc, 0)); hv = (top - bot) / 2
        pts, ws = [], []
        for j in range(10):
            ph = rad(36 * j)
            p = cen + hv * math.cos(ph) + Vector((0, -1, 0)) * (rd * math.sin(ph))
            wf = smooth(((p - JS).dot(AD) - (ELBOW_T - 0.06)) / 0.12)
            up = (1 + math.cos(ph)) / 2
            sp = lerp(0.55, 0.2, up) if k == 0 else (lerp(0.22, 0.0, up) if k == 1 else 0.0)
            ws.append({"Spine": sp, UA: (1 - sp) * (1 - wf), FA: (1 - sp) * wf})
            pts.append(mx(p, sx))
        rings.append(mb.ring(pts, ws))
    loft(mb, rings, "sleeve", "sleeve", seam=5, bake=(sx > 0))
    dark_cap(mb, rings[-1], mx(cen, sx), 0.55, mx(AD * -0.02, sx), mx(AD, sx))

    # --- кисть: ладонь + блок пальцев, согнутый в неплотный кулак ---
    hr = []
    for k, (l, p, al, ww, tp, tb) in enumerate(HAND):
        a = rad(al); ql, qp = -math.sin(a), math.cos(a)
        pts = []
        for w_, q_ in ((ww, 0), (0.55 * ww, tp), (-0.55 * ww, tp), (-ww, 0), (-0.55 * ww, -tb), (0.55 * ww, -tb)):
            pts.append(mx(hand_pt(l + ql * q_, w_, p + qp * q_), sx))
        hr.append(mb.ring(pts, {FA: 0.5, HD: 0.5} if k == 0 else {HD: 1.0}))
    l, p, al = HAND[-1][0], HAND[-1][1], rad(HAND[-1][2])
    tip = mb.vert(mx(hand_pt(l + math.cos(al) * 0.012, 0, p + math.sin(al) * 0.012), sx), {HD: 1.0})
    loft(mb, hr, "hand", "hand", seam=3, pole=tip, bake=(sx > 0))
    # большой палец
    cs = [Vector(c_) for c_, _ in THUMB] + [Vector(THUMB_TIP)]
    tr = []
    for k, (c_, r) in enumerate(THUMB):
        d = (cs[k + 1] - cs[max(k - 1, 0)]).normalized()            # в локальных (l, w, p)
        ea = Vector((0, 0, 1)); eb = d.cross(ea).normalized(); ea = eb.cross(d).normalized()
        pts = [mx(hand_pt(*(cs[k] + e * r)), sx) for e in (ea, eb, -ea, -eb)]
        tr.append(mb.ring(pts, {HD: 1.0}))
    ttip = mb.vert(mx(hand_pt(*THUMB_TIP), sx), {HD: 1.0})
    loft(mb, tr, "thumb", "thumb", seam=2, pole=ttip, bake=(sx > 0))


# =====================================================================================
#  Штаны и ботинки
# =====================================================================================
PYC = -0.020
P_RINGS = [(0.845, 0.160, 0.105, 0.102), (0.765, 0.196, 0.110, 0.108), (0.695, 0.203, 0.108, 0.108)]
LEG = [  # z, центр x, центр y, радиус по x, радиус по y
    (0.630, 0.106, -0.020, 0.096, 0.104),
    (0.585, 0.108, -0.019, 0.091, 0.100),
    (0.565, 0.109, -0.018, 0.089, 0.097),
    (0.500, 0.111, -0.012, 0.086, 0.092),
    (0.437, 0.113, 0.000, 0.085, 0.089),
    (0.415, 0.114, 0.006, 0.085, 0.088),
    (0.300, 0.118, 0.020, 0.087, 0.087),
    (0.190, 0.119, 0.020, 0.078, 0.088),
    (0.112, 0.119, 0.020, 0.069, 0.088),
]
RLEG_OVR = {2: (0.077, 0.088), 3: (0.075, 0.086), 4: (0.076, 0.086), 5: (0.082, 0.088)}   # правая штанина стянута бинтом
SOLE_Z = 0.032


def thigh_w(x, z):
    k = 0.9 * smooth((0.86 - z) / 0.2) * smooth(abs(x) / 0.1)
    if k <= 0:
        return {"Pelvis": 1.0}
    return {"Pelvis": 1 - k, ("ThighL" if x > 0 else "ThighR"): k}


def build_pants(mb):
    rings = []
    for z, a, bf, bb in P_RINGS:
        pts, ws = [], []
        for j in range(16):
            x, y = sellipse(a, bf, bb, PYC, rad(22.5 * j), 2.4)
            pts.append((x, y, z)); ws.append(thigh_w(x, z))
        rings.append(mb.ring(pts, ws))
    loft(mb, rings, "pelvis", "pants", seam=8)
    C = mb.vert((0, PYC, 0.672), {"Pelvis": 0.6, "ThighL": 0.2, "ThighR": 0.2})
    P2 = rings[-1]
    for sx in (1, -1):
        s = "L" if sx > 0 else "R"; TH, SH = "Thigh" + s, "Shin" + s
        loop = ([P2[j] for j in range(9)] if sx > 0 else [P2[(16 - j) % 16] for j in range(9)]) + [C]
        lr = [loop]
        for k, (z, cx, cy, rx, ry) in enumerate(LEG):
            if sx < 0 and k in RLEG_OVR:
                rx, ry = RLEG_OVR[k]
            wk = smooth((0.575 - z) / 0.15)
            pts, ws = [], []
            for j in range(10):
                ph = rad(-54 + 36 * j)
                pts.append((sx * (cx + rx * math.sin(ph)), cy - ry * math.cos(ph), z))
                if k == 0:
                    ws.append({TH: 0.75, "Pelvis": 0.25} if j in (0, 8, 9) else {TH: 1.0})
                else:
                    ws.append({TH: 1 - wk, SH: wk})
            lr.append(mb.ring(pts, ws))
        loft(mb, lr, "leg" + s, "pants", seam=9)
        z, cx, cy = LEG[-1][0], LEG[-1][1], LEG[-1][2]
        dark_cap(mb, lr[-1], (sx * cx, cy, z), 0.5, (0, 0, 0.03), (0, 0, -1))
        # накладной карман-карго на бедре: низкая «подушка» поверх штанины
        base, top = [], []
        for y, z in ((-0.078, 0.738), (0.036, 0.738), (0.036, 0.642), (-0.078, 0.642)):
            a = 0.199 if z > 0.7 else 0.202
            x = a * (1 - (abs(y - PYC) / 0.108) ** 2.4) ** (1 / 2.4) - 0.004
            w = {"Pelvis": 0.38, TH: 0.62} if z > 0.7 else {TH: 1.0}
            base.append(mb.vert((sx * x, y, z), w))
            yi = y + (0.012 if y < PYC else -0.012); zi = z + (-0.010 if z > 0.7 else 0.012)
            top.append(mb.vert((sx * (x + 0.017), yi, zi), w))
        fis = loft(mb, [base, top], "pocket" + s, "pants", inside=Vector((sx * 0.1, PYC, 0.69)))
        fis.append(ngon(mb, top, "pocket" + s, "pants", (sx, 0, 0)))
    # свободный хвостик бинта под правым коленом (карточка с альфой)
    W = {"ShinR": 1.0}
    q = [mb.vert(p, W) for p in ((-0.150, -0.088, 0.446), (-0.172, -0.070, 0.446), (-0.176, -0.074, 0.392), (-0.156, -0.092, 0.396))]
    fi = mb.face(q, ((0, 0), (0.024, 0), (0.024, -0.054), (0, -0.054)), "band_tail", "band_tail", 1)
    mb.orient([fi], direction=Vector((-0.6, -0.8, 0)))


def build_boot(mb, sx):
    s = "L" if sx > 0 else "R"; FT, SH = "Foot" + s, "Shin" + s
    bake = sx > 0
    A = Vector((0.120, 0.020, 0.0)); ang = rad(18)
    f = Vector((math.sin(ang), -math.cos(ang), 0)); o = Vector((math.cos(ang), math.sin(ang), 0)); Z = Vector((0, 0, 1))

    def ringpts(C, U, ru, rs, flat):
        pts = []
        for j in range(8):
            ph = rad(45 * j); c, sn = math.cos(ph), math.sin(ph)
            p = C + U * (ru * c) + o * (rs * sn)
            if flat and c < -0.1:                                    # плоский низ — стоит на подошве
                p = C + o * (rs * 0.88 * (1 if sn > 0.1 else (-1 if sn < -0.1 else 0)))
                p.z = SOLE_Z
            pts.append(mx(p, sx))
        return pts

    U2 = (f * 0.889 + Z * 0.457).normalized()
    spec = [(A + Z * 0.180, f, 0.055, 0.050, False, {SH: 1.0}),
            (A + Z * 0.125 + f * 0.006, f, 0.062, 0.056, False, {SH: 0.5, FT: 0.5}),
            (A + f * -0.0015 + Z * 0.0905, U2, 0.0973, 0.060, False, {FT: 1.0}),
            (A + f * 0.105 + Z * 0.076, Z, 0.036, 0.063, True, {FT: 1.0}),
            (A + f * 0.170 + Z * 0.071, Z, 0.031, 0.064, True, {FT: 1.0}),
            (A + f * 0.212 + Z * 0.063, Z, 0.023, 0.050, True, {FT: 1.0})]
    rings = [mb.ring(ringpts(C, U, ru, rs, fl), w) for C, U, ru, rs, fl, w in spec]
    tip = mb.vert(mx(A + f * 0.233 + Z * 0.056, sx), {FT: 1.0})
    loft(mb, rings, "boot", "boot", seam=4, pole=tip, bake=bake)
    # подошва
    outline = [(-0.097, 0.0), (-0.085, 0.040), (-0.02, 0.055), (0.10, 0.062), (0.185, 0.060), (0.225, 0.035),
               (0.240, 0.0), (0.225, -0.035), (0.185, -0.060), (0.10, -0.061), (-0.02, -0.053), (-0.085, -0.040)]
    top = mb.ring([mx(A + f * a + o * b + Z * (SOLE_Z + 0.002), sx) for a, b in outline], {FT: 1.0})
    bot = mb.ring([mx(A + f * (a * 0.985) + o * (b * 0.94), sx) for a, b in outline], {FT: 1.0})
    loft(mb, [top, bot], "sole", "sole", bake=bake)
    ngon(mb, bot, "sole_cap", "sole", (0, 0, -1), bake=bake)
    ngon(mb, top, "sole_cap", "sole", (0, 0, 1), bake=bake)


# =====================================================================================
#  Голова, шея с бинтом, волосы, шапка, капюшон
# =====================================================================================
HYC = -0.048
H_COLS = [0, 10, 22, 36, 52, 75, 105, 140, 180, -140, -105, -75, -52, -36, -22, -10]
H_RINGS = [  # z спереди, z сзади, полуширина, глубина вперёд, назад
    (1.712, 1.712, 0.0700, 0.0850, 0.088),
    (1.672, 1.672, 0.0740, 0.0920, 0.093),
    (1.640, 1.640, 0.0745, 0.0950, 0.092),
    (1.620, 1.622, 0.0730, 0.0920, 0.089),
    (1.600, 1.604, 0.0710, 0.0940, 0.084),
    (1.580, 1.588, 0.0680, 0.0955, 0.077),
    (1.562, 1.576, 0.0640, 0.0970, 0.070),
    (1.547, 1.568, 0.0590, 0.0960, 0.064),
    (1.528, 1.560, 0.0530, 0.0920, 0.058),
]
H_DISP = {  # (кольцо, |угол|): (вперёд, вверх) — лепка лица
    (2, 0): (0.002, 0), (2, 10): (0.002, 0), (2, 22): (0.003, 0), (2, 36): (0.001, 0),
    (3, 0): (-0.003, 0), (3, 10): (-0.007, 0), (3, 22): (-0.009, 0), (3, 36): (-0.006, 0),
    (4, 0): (0.007, 0), (4, 10): (-0.002, 0), (4, 22): (-0.004, 0), (4, 36): (0.001, 0), (4, 52): (0.002, 0),
    (5, 0): (0.020, -0.003), (5, 10): (0.007, -0.002), (5, 22): (-0.002, 0),
    (6, 0): (0.008, 0), (6, 10): (0.003, 0),
    (7, 0): (0.004, 0), (7, 10): (0.003, 0),
    (8, 0): (0.003, 0), (8, 10): (0.001, 0),
}


def head_xy(th, off=0.0):
    return sellipse(0.0745 + off, 0.095 + off, 0.092 + off, HYC, th, 2.1)


def rim_z(th):
    """Нижний край шапки: спереди выше, сзади ниже."""
    return 1.625 + 0.040 * math.cos(th)


def build_head(mb):
    rings = []
    for i, (zf, zb, a, bf, bb) in enumerate(H_RINGS):
        pts = []
        for deg in H_COLS:
            th = rad(deg)
            x, y = sellipse(a, bf, bb, HYC, th, 2.2 if math.cos(th) > 0 else 2.0)
            z = zf + (zb - zf) * (1 - math.cos(th)) / 2
            dy, dz = H_DISP.get((i, abs(deg)), (0, 0))
            pts.append((x, y - dy, z + dz))
        rings.append(mb.ring(pts, {"Head": 1.0}))

    def useg(j0, j1):                                                # затылок под волосами — мало текселей
        return 0.3 if abs(H_COLS[j0]) > 75 and abs(H_COLS[j1]) > 75 else 1.0

    loft(mb, rings, "head", "face", seam=8, useg=useg)


def build_neck(mb):
    spec = [  # z спереди, z сзади, a, bf, bb, yc, вес Head
        (1.538, 1.572, 0.068, 0.0985, 0.066, -0.048, 1.0),
        (1.512, 1.548, 0.056, 0.0930, 0.060, -0.047, 1.0),
        (1.494, 1.524, 0.058, 0.0600, 0.058, -0.040, 0.6),
        (1.440, 1.440, 0.062, 0.0580, 0.060, -0.028, 0.0),
    ]
    rings = []
    for zf, zb, a, bf, bb, yc, wh in spec:
        pts = []
        for j in range(12):
            th = rad(30 * j)
            x, y = sellipse(a, bf, bb, yc, th, 2.1)
            pts.append((x, y, zf + (zb - zf) * ((1 - math.cos(th)) / 2) ** 0.8))
        rings.append(mb.ring(pts, {"Head": wh, "Spine": 1 - wh}))
    loft(mb, rings, "neck", "neck", seam=6)


def build_beanie(mb):
    yc = -0.047; ZTOP = 1.781
    spec = [(0.0980, 0.1120, 0.000, 0.0), (0.1065, 0.1205, 0.014, 0.0), (0.1065, 0.1210, 0.054, 0.0),
            (0.1000, 0.1145, 0.060, 0.0), (0.0890, 0.1030, 0.060, 0.50), (0.0560, 0.0670, 0.060, 0.86)]
    rings = []
    for a, b, dz, k in spec:
        pts = []
        for j in range(12):
            th = rad(30 * j)
            pts.append((a * math.sin(th), yc - b * math.cos(th), lerp(rim_z(th) + dz, ZTOP, k)))
        rings.append(mb.ring(pts, {"Head": 1.0}))
    pole = mb.vert((0, yc + 0.006, ZTOP + 0.002), {"Head": 1.0})
    loft(mb, rings, "beanie", "beanie", seam=6, pole=pole)


HAIR_CAP = [30, 48, 70, 100, 135, 180, -135, -100, -70, -48, -30]
HAIR_TIP = {30: 1.548, 48: 1.524, 70: 1.514, 100: 1.516, 135: 1.528, 180: 1.538}
HAIR_OFF = {30: (0.004, 0.008, 0.008), 48: (0.006, 0.019, 0.022), 70: (0.007, 0.028, 0.038),      # вынос от головы:
            100: (0.007, 0.029, 0.040), 135: (0.007, 0.025, 0.031), 180: (0.007, 0.022, 0.025)}     # верх / середина / кончики


def build_hair(mb):
    W = {"Head": 1.0}
    # «шапка» волос: бока и затылок из-под шапки до челюсти; передний край ложится на щёки
    rings = [[], [], []]
    for deg in HAIR_CAP:
        th = rad(deg); zt = rim_z(th) + 0.018; zb = HAIR_TIP[abs(deg)]
        o = HAIR_OFF[abs(deg)]
        for r, (z, off) in enumerate(((zt, o[0]), (lerp(zt, zb, 0.45), o[1]), (zb, o[2]))):
            x, y = head_xy(th, off)
            rings[r].append(mb.vert((x, y, z), W))
    loft(mb, rings, "hair_cap", "hair_cap", closed=False, mat=1, inside=Vector((0, HYC, 1.6)))
    # чёлка
    rings = [[], [], []]
    tips = [1.584, 1.598, 1.604, 1.600, 1.598, 1.584]
    for k, deg in enumerate((-40, -24, -8, 8, 24, 40)):
        th = rad(deg)
        for r, (z, off) in enumerate(((rim_z(th) + 0.014, 0.009), (1.648, 0.016), (tips[k], 0.011))):
            x, y = head_xy(th, off)
            rings[r].append(mb.vert((x, y, z), W))
    loft(mb, rings, "hair_bangs", "hair_bangs", closed=False, mat=1, inside=Vector((0, HYC, 1.65)))
    # отдельные пряди (плоские «карточки» с альфой)
    cards = [  # список точек (угол, z, вынос), ширина
        ([(-9, 1.668, 0.018), (2, 1.630, 0.021), (6, 1.590, 0.017)], 0.017),
        ([(33, 1.640, 0.022), (30, 1.585, 0.025), (27, 1.538, 0.020)], 0.025),
        ([(-33, 1.640, 0.022), (-30, 1.585, 0.025), (-27, 1.538, 0.020)], 0.025),
        ([(82, 1.578, 0.030), (88, 1.548, 0.042), (95, 1.524, 0.056)], 0.028),
        ([(-82, 1.578, 0.030), (-88, 1.548, 0.042), (-95, 1.524, 0.056)], 0.028),
        ([(150, 1.566, 0.022), (152, 1.538, 0.030), (155, 1.516, 0.040)], 0.030),
        ([(-162, 1.570, 0.022), (-160, 1.542, 0.029), (-158, 1.520, 0.038)], 0.030),
    ]
    for pts, width in cards:
        rows = []
        v = 0.0; prev = None
        for k, (deg, z, off) in enumerate(pts):
            th = rad(deg); x, y = head_xy(th, off)
            c = Vector((x, y, z)); tang = Vector((math.cos(th), math.sin(th), 0))
            hw = width / 2 * (1.0 if k < len(pts) - 1 else 0.55)
            if prev is not None:
                v += (c - prev).length
            prev = c
            rows.append((mb.vert(c - tang * hw, W), mb.vert(c + tang * hw, W), v))
        fis = []
        vs = 0.1 / rows[-1][2]                                           # все пряди занимают один и тот же островок целиком
        for k in range(len(rows) - 1):
            a0, a1, va = rows[k]; b0, b1, vb = rows[k + 1]
            va *= vs; vb *= vs
            fis.append(mb.face((a0, b0, b1, a1), ((0, -va), (0, -vb), (0.03, -vb), (0.03, -va)), "hair_strand", "hair_strand", 1))
        mb.orient(fis, inside=Vector((0, HYC, 1.6)))


HOOD = [  # угол вокруг шеи; профиль (радиус, z): внутренний край, гребень, наружная часть, низ, кромка
    (28, [(0.060, 1.468), (0.080, 1.486), (0.104, 1.468), (0.114, 1.442), (0.112, 1.420)]),
    (55, [(0.064, 1.490), (0.094, 1.516), (0.125, 1.492), (0.136, 1.458), (0.134, 1.436)]),
    (90, [(0.068, 1.500), (0.106, 1.530), (0.142, 1.502), (0.151, 1.466), (0.150, 1.444)]),
    (125, [(0.070, 1.492), (0.124, 1.537), (0.180, 1.486), (0.186, 1.445), (0.176, 1.415)]),
    (155, [(0.070, 1.486), (0.136, 1.540), (0.182, 1.476), (0.184, 1.420), (0.166, 1.376)]),
    (180, [(0.070, 1.484), (0.140, 1.541), (0.184, 1.472), (0.184, 1.405), (0.158, 1.345)]),
]


def build_hood(mb):
    yc = -0.030
    stations = []
    seq = HOOD + [(-d, p) for d, p in reversed(HOOD[:-1])]
    for deg, prof in seq:
        th = rad(deg)
        stations.append(mb.ring([(r * math.sin(th), yc - r * math.cos(th), z) for r, z in prof], {"Spine": 1.0}))
    loft(mb, stations, "hood", "hood", closed=False, inside=Vector((0, yc, 1.44)))
    # торцы «рогов» капюшона спереди
    ngon(mb, stations[0], "hood_cap", "hood", (-math.cos(rad(28)), -math.sin(rad(28)), 0))
    ngon(mb, stations[-1], "hood_cap", "hood", (math.cos(rad(28)), -math.sin(rad(28)), 0))


# =====================================================================================
#  Сумка и ремень
# =====================================================================================
BAG_TF = Vector((-0.222, -0.035, 0)); BAG_TB = Vector((-0.128, 0.205, 0))


def build_strap_bag(mb):
    Wb = (BAG_TB - BAG_TF).normalized(); Nb = Vector((-Wb.y, Wb.x, 0))        # наружу: вправо-назад
    M = (BAG_TF + BAG_TB) / 2 + Nb * 0.012
    hw = (BAG_TB - BAG_TF).length / 2

    def bag_pt(w, d, z):
        p = M + Wb * w + Nb * d; p.z = z
        return p

    prof = [(0.000, 1.000), (0.060, 1.008), (0.088, 0.955), (0.094, 0.870), (0.090, 0.805), (0.078, 0.800),
            (0.074, 0.752), (0.000, 0.745)]
    cols = []
    for w, bulge, taper in ((-hw, 0.0, 0.94), (0.0, 0.010, 1.0), (hw, 0.0, 0.94)):
        pts = []
        for k, (d, z) in enumerate(prof):
            ww = w * (taper if k in (0, 1) else 1.0)
            pts.append(bag_pt(ww, d + (bulge if 1 <= k <= 6 else 0), z))
        cols.append(mb.ring(pts, [torso_w(p.z, p.x) for p in pts]))
    rows = [[cols[0][k], cols[1][k], cols[2][k]] for k in range(len(prof))]      # u — поперёк сумки, v — сверху вниз
    loft(mb, rows, "bag_front", "bag", closed=False, inside=M + Vector((0, 0, 0.87)) - Nb * 0.2)
    ngon(mb, cols[0], "bag_side", "bag_side", -Wb)
    ngon(mb, cols[2], "bag_side", "bag_side", Wb)

    # ремень: от сумки спереди через левое плечо к сумке сзади
    path = [bag_pt(-hw + 0.012, 0.035, 0.985)]
    path.append(Vector((-0.196, torso_y(-0.196, 0.990) - 0.006, 0.995)))
    for z in (1.03, 1.10, 1.19, 1.28, 1.36, 1.425):
        x = -0.174 + (z - 1.0) * 0.6865
        path.append(Vector((x, torso_y(x, z) - 0.007, z)))
    path += [Vector((0.132, -0.060, 1.458)), Vector((0.142, -0.012, 1.466)), Vector((0.146, 0.045, 1.458))]
    for z in (1.425, 1.34, 1.25, 1.16, 1.07, 1.005):
        x = -0.106 + (z - 1.0) * 0.5745
        path.append(Vector((x, torso_y(x, z, False) + 0.007, z)))
    path.append(bag_pt(hw - 0.012, 0.035, 0.985))
    axis = lambda p: Vector((0, -0.01, p.z))
    rows = []; dist = 0.0
    for k, p in enumerate(path):
        t = (path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]).normalized()
        out = (p - axis(p)); out.z = 0.25 * out.length if 1.43 < p.z else 0.0
        out.normalize()
        side = t.cross(out).normalized()
        if k:
            dist += (p - path[k - 1]).length
        w = torso_w(p.z, p.x)
        rows.append((mb.vert(p - side * 0.019, w), mb.vert(p + side * 0.019, w), dist))
    fis = []
    for k in range(len(rows) - 1):
        a0, a1, da = rows[k]; b0, b1, db = rows[k + 1]
        base = math.floor(da / 0.4) * 0.4
        fis.append(mb.face((a0, b0, b1, a1), ((da - base, 0), (db - base, 0), (db - base, 0.038), (da - base, 0.038)),
                           "strap", "strap"))
    for f in fis:                                                    # каждая грань — наружу от оси тела
        mb.orient([f], inside=axis(mb.fcenter(f)))


# =====================================================================================
#  Молоток (отдельный объект в правой руке)
# =====================================================================================
def build_hammer(mb):
    mb.obj = 1
    g = mx(hand_pt(*GRIP), -1)
    wd = mx(HAND_WD, -1); ln = mx(HAND_L, -1); pn = mx(HAND_PN, -1)
    hdir = (wd + ln * 0.36).normalized()                              # рукоять: вперёд и чуть вниз
    fdir = (ln - hdir * ln.dot(hdir)).normalized()                    # боёк смотрит «от запястья»
    sdir = hdir.cross(fdir).normalized()
    W = {"HandR": 1.0}
    rings = []
    for t, r in ((-0.075, 0.0175), (-0.02, 0.0150), (0.08, 0.0140), (0.235, 0.0150)):
        c = g + hdir * t
        rings.append(mb.ring([c + (fdir * math.cos(rad(60 * j)) + sdir * math.sin(rad(60 * j))) * r for j in range(6)], W))
    loft(mb, rings, "hammer_handle", "hammer_wood")
    ngon(mb, rings[0], "hammer_cap", "hammer_wood", -hdir)
    hc = g + hdir * 0.252
    hr = []
    for t, r in ((-0.058, 0.007), (-0.024, 0.0165), (0.032, 0.0165), (0.038, 0.0195), (0.062, 0.0195)):
        c = hc + fdir * t
        k = 0.45 if t < -0.03 else 1.0                                # гвоздодёр — сплюснутый клин
        hr.append(mb.ring([c + hdir * (r * a) + sdir * (r * b * (1.6 if t < -0.03 else 1.0))
                           for a, b in ((k, 1), (-k, 1), (-k, -1), (k, -1))], W))
    loft(mb, hr, "hammer_head", "hammer_metal")
    ngon(mb, hr[0], "hammer_cap", "hammer_metal", -fdir)
    ngon(mb, hr[-1], "hammer_cap", "hammer_metal", fdir)
    mb.obj = 0
    return g


def build_all():
    mb = MB()
    T = build_torso(mb)
    build_arm(mb, T, 1); build_arm(mb, T, -1)
    build_pants(mb)
    build_boot(mb, 1); build_boot(mb, -1)
    build_head(mb); build_neck(mb); build_hair(mb); build_beanie(mb); build_hood(mb)
    build_strap_bag(mb)
    grip = build_hammer(mb)
    return mb, grip


# =====================================================================================
#  Упаковка островков в атлас
# =====================================================================================
ISL_DENS = {"head": 2.0, "neck": 1.25, "beanie": 1.1, "hand": 1.5, "thumb": 1.5, "pelvis": 0.5, "sole": 0.6,
            "sole_cap": 0.35, "hair_bangs": 1.4, "hair_strand": 1.6, "bag_side": 0.7, "hood": 0.9, "boot": 1.1,
            "hammer_cap": 0.6, "dark": 1.0}


def pack_islands(mb, size=ATLAS, pad=3):
    box = {}
    for fi, name in enumerate(mb.fisl):
        b = box.setdefault(name, [1e9, 1e9, -1e9, -1e9])
        for u, v in mb.fuv[fi]:
            b[0] = min(b[0], u); b[1] = min(b[1], v); b[2] = max(b[2], u); b[3] = max(b[3], v)

    def try_pack(D):
        rects = []
        for name, b in box.items():
            k = ISL_DENS.get(name, 1.0) * D
            rects.append((name, int(math.ceil((b[2] - b[0]) * k)) + pad * 2, int(math.ceil((b[3] - b[1]) * k)) + pad * 2))
        rects.sort(key=lambda r: (-r[2], -r[1]))
        sky = np.zeros(size, np.int32); pos = {}
        for name, w, h in rects:
            if w > size:
                return None
            best = None
            for x in range(0, size - w + 1, 2):
                y = int(sky[x:x + w].max())
                if best is None or y < best[1]:
                    best = (x, y)
            x, y = best
            if y + h > size:
                return None
            pos[name] = (x, y, w, h); sky[x:x + w] = y + h
        return pos

    lo, hi, best = 60.0, 500.0, None
    for _ in range(22):
        mid = (lo + hi) / 2
        p = try_pack(mid)
        if p:
            best = (mid, p); lo = mid
        else:
            hi = mid
    D, pos = best
    mb.fpx, mb.fluv = [], []
    for fi, name in enumerate(mb.fisl):
        b = box[name]; x0, y0, w, h = pos[name]; k = ISL_DENS.get(name, 1.0) * D
        du = max(b[2] - b[0], 1e-9); dv = max(b[3] - b[1], 1e-9)
        mb.fpx.append([(x0 + pad + (u - b[0]) * k, y0 + pad + (b[3] - v) * k) for u, v in mb.fuv[fi]])
        mb.fluv.append([((u - b[0]) / du, (b[3] - v) / dv) for u, v in mb.fuv[fi]])
    return D, pos


# =====================================================================================
#  Объекты Blender
# =====================================================================================
def make_object(mb, obj_id, name, coll, mats, origin=None):
    fsel = [fi for fi in range(len(mb.faces)) if mb.fobj[fi] == obj_id]
    used = sorted({i for fi in fsel for i in mb.faces[fi]})
    remap = {v: k for k, v in enumerate(used)}
    o = Vector(origin) if origin is not None else Vector((0, 0, 0))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(mb.co[i] - o) for i in used], [], [tuple(remap[i] for i in mb.faces[fi]) for fi in fsel])
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", [mb.fmat[fi] for fi in fsel])
    me.polygons.foreach_set("use_smooth", [True] * len(fsel))
    uvl = me.uv_layers.new(name="UVMap")
    flat = []
    for fi in fsel:
        for px, py in mb.fpx[fi]:
            flat += [px / ATLAS, 1.0 - py / ATLAS]
    uvl.data.foreach_set("uv", flat)
    me.update()
    me.set_sharp_from_angle(angle=rad(62))
    ob = bpy.data.objects.new(name, me)
    ob.location = o
    coll.objects.link(ob)
    return ob, fsel, used


# =====================================================================================
#  Концепт-лист → источник текстур
# =====================================================================================
def _shift_or(m):
    g = m.copy()
    g[1:, :] |= m[:-1, :]; g[:-1, :] |= m[1:, :]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
    return g


def dilate(m, n):
    for _ in range(n):
        m = _shift_or(m)
    return m


def erode(m, n):
    return ~dilate(~m, n)


def fill_invalid(img, valid, iters):
    """Заполняет невалидные пиксели средним цветом валидных соседей, расширяясь наружу."""
    img = img.copy(); valid = valid.copy()
    H, W = valid.shape
    for _ in range(iters):
        pc = np.zeros((H + 2, W + 2, 3), np.float32); pv = np.zeros((H + 2, W + 2), np.float32)
        pc[1:-1, 1:-1] = img * valid[..., None]; pv[1:-1, 1:-1] = valid
        sc = np.zeros((H, W, 3), np.float32); sv = np.zeros((H, W), np.float32)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                if dy == 1 and dx == 1:
                    continue
                sc += pc[dy:dy + H, dx:dx + W]; sv += pv[dy:dy + H, dx:dx + W]
        new = (~valid) & (sv > 0)
        if not new.any():
            break
        img[new] = sc[new] / sv[new][:, None]
        valid |= new
    return img


def prep_reference():
    img = bpy.data.images.load(REF_PATH, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1, :, :3].copy()
    bpy.data.images.remove(img)
    fg0 = np.abs(a - 0.592).max(axis=2) > 0.10
    # фон = всё «серое», связанное с краем картинки (обход в ширину)
    H, W = fg0.shape; W2 = W + 2
    passable = np.zeros((H + 2, W2), bool); passable[1:-1, 1:-1] = ~fg0
    pas = passable.ravel().tolist(); seen = bytearray((H + 2) * W2)
    stack = []
    for x in range(1, W + 1):
        stack += [W2 + x, H * W2 + x]
    for y in range(1, H + 1):
        stack += [y * W2 + 1, y * W2 + W]
    while stack:
        i = stack.pop()
        if seen[i] or not pas[i]:
            continue
        seen[i] = 1
        stack += [i - 1, i + 1, i - W2, i + W2]
    outside = np.frombuffer(bytes(seen), np.uint8).reshape(H + 2, W2)[1:-1, 1:-1].astype(bool)
    fg = erode(~outside, 2)                                           # без контурной обводки
    # оливковые ремень и сумка: убираем с куртки (зеркальной заливкой), чтобы не «прилипли» к текстуре
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    olive = ((g - b) > 0.035) & (np.abs(r - g) < 0.06) & (g > 0.12)
    region = np.zeros_like(olive)
    region[112:346, 100:262] = True; region[112:346, 778:946] = True
    olive = dilate(olive & region, 5)
    clean = a.copy(); cvalid = fg & ~olive
    ys, xs = np.nonzero(olive & fg)
    cx = np.where(xs < 512, CXF, CXB)
    xm = np.clip(np.rint(2 * cx - xs).astype(int), 0, W - 1)
    ok = cvalid[ys, xm]
    clean[ys[ok], xs[ok]] = a[ys[ok], xm[ok]]
    cvalid[ys[ok], xs[ok]] = True
    return {"orig": fill_invalid(a, fg, 30), "clean": fill_invalid(clean, cvalid, 40)}


def sample(img, px, py):
    H, W = img.shape[:2]
    px = np.clip(px, 0, W - 1.001); py = np.clip(py, 0, H - 1.001)
    x0 = np.floor(px).astype(int); y0 = np.floor(py).astype(int)
    fx = (px - x0)[:, None]; fy = (py - y0)[:, None]
    return (img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx) * (1 - fy) + (img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx) * fy


def project(refs, key, P, N, front=1.0, back=1.0, side=None):
    """Цвет точек модели с концепта: смешиваем виды спереди / сзади / сбоку по направлению нормали."""
    wf = np.clip(-N[:, 1], 0, 1) ** 2 * front + 0.02 * front
    wb = np.clip(N[:, 1], 0, 1) ** 2 * back + 0.02 * back
    ws = np.zeros(len(P), np.float32) if side is None else np.abs(N[:, 0]) ** 2 * side
    pz = GY - P[:, 2] / S
    col = (sample(refs[key], CXF + P[:, 0] / S, pz) * wf[:, None] + sample(refs[key], CXB - P[:, 0] / S, pz) * wb[:, None]
           + sample(refs["orig"], CXS - P[:, 1] / S, pz) * ws[:, None])
    return col / (wf + wb + ws)[:, None]


# --- шум для процедурной дорисовки ---
def _hash(ix, iy, seed):
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF).astype(np.float32) / 65535.0


def vnoise(x, y, seed=0):
    x0 = np.floor(x); y0 = np.floor(y); fx = x - x0; fy = y - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = _hash(x0, y0, seed); b = _hash(x0 + 1, y0, seed); c = _hash(x0, y0 + 1, seed); d = _hash(x0 + 1, y0 + 1, seed)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(x, y, seed=0, oct=3):
    out = 0.0; amp = 1.0; tot = 0.0
    for i in range(oct):
        out = out + vnoise(x * 2 ** i, y * 2 ** i, seed + i * 17) * amp; tot += amp; amp *= 0.5
    return out / tot


def col(c): return np.array(c, np.float32)


# =====================================================================================
#  Запекание атласа
# =====================================================================================
def paint(tag, refs, P, N, LUV):
    """Цвет и альфа текселей одной части модели. P, N — мировые позиции и нормали текселей."""
    n = len(P); alpha = np.ones(n, np.float32)
    u, v = LUV[:, 0], LUV[:, 1]
    if tag in ("jacket", "jacket_edge", "sleeve"):
        c = project(refs, "clean", P, N)
    elif tag == "hoodie":
        c = project(refs, "clean", P, N, back=0.0)
    elif tag == "hood":
        c = project(refs, "clean", P, N, side=0.8)
    elif tag == "pants":
        right_outer = (P[:, 0] < 0) & (N[:, 0] < 0)
        left_outer = (P[:, 0] > 0) & (N[:, 0] > 0) & ((P[:, 2] < 0.41) | (P[:, 2] > 0.60))
        side = np.where((right_outer | left_outer) & (P[:, 2] < 0.74), 1.0, 0.0)
        c = project(refs, "orig", P, N, side=side)
        c = c * (0.45 + 0.55 * np.clip((0.80 - P[:, 2]) / 0.09, 0, 1))[:, None]          # тень под курткой
    elif tag == "band_tail":
        c = col((0.66, 0.66, 0.68)) * (0.7 + 0.3 * vnoise(u * 5, v * 14, 71))[:, None]
        alpha = ((np.abs(u - 0.5) < 0.46 - 0.25 * v ** 2) & (v < 0.80 + 0.2 * (np.floor(u * 7) % 2))).astype(np.float32)
    elif tag == "boot":
        c = project(refs, "orig", P, N, side=1.0)
    elif tag == "sole":
        c = col((0.085, 0.082, 0.078)) * (0.7 + 0.6 * fbm(P[:, 0] * 90, P[:, 1] * 90, 5))[:, None]
        c = c * np.where((np.abs(N[:, 2]) < 0.5) & (np.floor(u * 22) % 2 == 0), 0.6, 1.0)[:, None]    # протектор по ранту
    elif tag == "face":
        c = project(refs, "orig", P, N, back=0.0, side=1.0)
    elif tag == "neck":
        c = project(refs, "orig", P, N, back=0.0, side=1.0)
        k = np.clip((N[:, 1] - 0.05) * 3.0, 0, 1)[:, None]            # сзади шея в тени волос и капюшона
        c = c * (1 - k) + col((0.05, 0.048, 0.055)) * k
    elif tag == "beanie":
        c = project(refs, "orig", P, N, side=1.0)
    elif tag.startswith("hair"):
        c, alpha = paint_hair(tag, u, v)
    elif tag in ("hand", "thumb"):
        c = paint_hand(tag, P, N, v)
    elif tag in ("bag", "bag_side"):
        # сумка целиком с концепта: лицевая сторона — с вида сбоку, торцы — с видов спереди и сзади
        pz = GY - P[:, 2] / S
        wf = np.clip(-N[:, 1], 0, 1) ** 2 + 0.02; wb = np.clip(N[:, 1], 0, 1) ** 2 + 0.02; ws = N[:, 0] ** 2
        c = (sample(refs["orig"], CXF + P[:, 0] / S, pz) * wf[:, None] + sample(refs["orig"], CXB - P[:, 0] / S, pz) * wb[:, None]
             + sample(refs["orig"], np.minimum(CXS - P[:, 1] / S, 512.0), pz) * ws[:, None]) / (wf + wb + ws)[:, None]
        k = np.clip(np.abs(N[:, 2]) * 1.6 - 0.3, 0, 1)[:, None]                       # верх и дно — простая ткань
        c = c * (1 - k) + paint_bag(tag, u, v, P) * k
    elif tag == "strap":
        c = col((0.215, 0.215, 0.160)) * (0.8 + 0.4 * vnoise(u * 300, v * 9, 3))[:, None]
        c = c * np.where((np.abs(v - 0.5) > 0.36), 0.62, 1.0)[:, None]                 # прострочка по краям
        buckle = (np.abs(u - 0.30) < 0.045)
        c = np.where(buckle[:, None], col((0.20, 0.20, 0.19)) * (0.7 + 0.8 * (np.abs(v - 0.5) < 0.2))[:, None], c)
    elif tag == "hammer_wood":
        g = vnoise(u * 3, v * 60, 11)
        c = col((0.27, 0.205, 0.145)) * (0.6 + 0.55 * g)[:, None]
    elif tag == "hammer_metal":
        c = col((0.20, 0.205, 0.215)) * (0.6 + 0.7 * fbm(u * 9, v * 9, 13))[:, None]
        c = c + col((0.10, 0.045, 0.02)) * np.clip(fbm(u * 5 + 7, v * 5, 21) - 0.55, 0, 1)[:, None] * 2.5   # ржавчина
    else:  # dark
        c = np.tile(col((0.022, 0.022, 0.026)), (n, 1))
    return np.clip(c, 0, 1), alpha


BANG_STRANDS = [  # центр по ширине лба, ширина, длина (1 — до переносицы), изгиб; над глазами пряди короткие
    (0.02, 0.12, 1.00, 0.02), (0.10, 0.10, 0.86, -0.02), (0.19, 0.07, 0.50, 0.03), (0.27, 0.08, 0.66, 0.02),
    (0.36, 0.09, 0.84, 0.04), (0.46, 0.08, 1.00, 0.03), (0.55, 0.08, 0.74, -0.03), (0.64, 0.09, 0.60, -0.02),
    (0.73, 0.07, 0.52, 0.02), (0.82, 0.07, 0.50, -0.03), (0.90, 0.10, 0.86, 0.02), (0.98, 0.12, 1.00, -0.02)]


def paint_hair(tag, u, v):
    strands = vnoise(u * (46 if tag != "hair_strand" else 7), v * 2.0, 31)
    fine = vnoise(u * (110 if tag != "hair_strand" else 16), v * 5.0, 37)
    shade = 0.45 + 1.0 * strands ** 2 + 0.45 * fine
    c = col((0.075, 0.066, 0.066))[None, :] * shade[:, None]
    sheen = np.exp(-((v - 0.38) / 0.13) ** 2) * strands
    c = c + col((0.075, 0.072, 0.080))[None, :] * sheen[:, None]
    tri = lambda x: 1 - np.abs((x % 1.0) - 0.5) * 2                                        # зубья: 1 — остриё пряди
    if tag == "hair_strand":
        half = np.abs(u - 0.5) * 2
        alpha = (half < (0.95 - 0.8 * v ** 1.6)).astype(np.float32)
    elif tag == "hair_bangs":
        # редкие пряди поверх нарисованной на лбу чёлки — глаза остаются видны
        am = v < 0.10
        for uc, w, ln, sw in BANG_STRANDS:
            am |= (np.abs(u - uc - sw * v * v) < 0.5 * w * (1.0 - 0.85 * np.clip(v / ln, 0, 1) ** 1.7)) & (v < ln)
        alpha = am.astype(np.float32)
    else:
        length = 0.58 + 0.42 * (0.65 * tri(u * 10 + 0.15 * np.sin(u * 31.0)) ** 0.8 + 0.35 * tri(u * 27 + 0.4))
        alpha = (v < length).astype(np.float32)
        c = c * (1 - 0.3 * np.clip((v - 0.55) / 0.45, 0, 1))[:, None]                      # кончики темнее
    return c, alpha


def paint_hand(tag, P, N, v):
    d = P - np.array(HAND_W, np.float32)
    l = d @ np.array(HAND_L, np.float32); w = d @ np.array(HAND_WD, np.float32); p = d @ np.array(HAND_PN, np.float32)
    palm = N @ np.array(HAND_PN, np.float32)
    skin = col((0.50, 0.415, 0.385)) * (0.82 + 0.3 * fbm(P[:, 0] * 300, P[:, 2] * 300, 51))[:, None]
    skin = skin * (0.80 + 0.2 * np.clip(-palm, 0, 1))[:, None] + col((0.05, 0.0, 0.0)) * np.clip(palm, 0, 1)[:, None]
    glove = col((0.105, 0.118, 0.128)) * (0.7 + 0.6 * fbm(P[:, 0] * 260, P[:, 2] * 260, 53))[:, None]
    if tag == "thumb":
        is_skin = v > 0.5
        edge = np.abs(v - 0.5) < 0.05
    else:
        fing = 0.574 * (l - 0.128) + 0.819 * (p - 0.016)
        is_skin = fing > 0
        edge = np.abs(fing) < 0.004
        lines = np.minimum.reduce([np.abs(w - x) for x in (-0.021, 0.0, 0.021)])
        groove = (lines < 0.0028) & (l > 0.088)
        skin = skin * np.where(groove, 0.45, 1.0)[:, None]
        glove = glove * np.where(groove, 0.6, 1.0)[:, None]
        knuckle = np.exp(-((l - 0.092) / 0.012) ** 2) * np.clip(-palm, 0, 1) * (lines > 0.006)
        glove = glove + col((0.05, 0.055, 0.06)) * knuckle[:, None]
        glove = glove * np.where(l < -0.004, 0.75, 1.0)[:, None]                            # манжета перчатки
    c = np.where(is_skin[:, None], skin, glove)
    return np.where(edge[:, None], col((0.19, 0.20, 0.21)), c)                             # обрезанный край перчатки


def paint_bag(tag, u, v, P):
    """Оливковый брезент для верха и дна сумки (остальное берётся с концепта)."""
    weave = 0.75 + 0.35 * fbm(P[:, 1] * 240 + P[:, 0] * 240, P[:, 2] * 240, 61)
    c = col((0.175, 0.175, 0.125))[None, :] * weave[:, None]
    return c * (0.55 + 0.6 * np.clip((P[:, 2] - 0.745) / 0.26, 0, 1))[:, None]             # дно темнее


def bake_atlas(mb, me_by_obj, refs):
    """Растеризует все грани в атлас, запоминая для каждого текселя позицию/нормаль, затем красит по тегам."""
    W = H = ATLAS
    Pb = np.zeros((H, W, 3), np.float32); Nb = np.zeros((H, W, 3), np.float32); Lb = np.zeros((H, W, 2), np.float32)
    Tb = np.full((H, W), -1, np.int32)
    tags = sorted(set(mb.ftag)); tid = {t: i for i, t in enumerate(tags)}
    for obj_id, (me, fsel) in me_by_obj.items():
        cn = np.empty(len(me.loops) * 3, np.float32); me.corner_normals.foreach_get("vector", cn); cn = cn.reshape(-1, 3)
        for pi, fi in enumerate(fsel):
            if not mb.fbake[fi]:
                continue
            ls = me.polygons[pi].loop_start; ids = mb.faces[fi]; t = tid[mb.ftag[fi]]
            px = np.array(mb.fpx[fi], np.float32); pos = np.array([mb.co[i] for i in ids], np.float32)
            nrm = cn[ls:ls + len(ids)]; luv = np.array(mb.fluv[fi], np.float32)
            for k in range(1, len(ids) - 1):
                tri = (0, k, k + 1)
                (x0, y0), (x1, y1), (x2, y2) = px[tri[0]], px[tri[1]], px[tri[2]]
                den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
                if abs(den) < 1e-9:
                    continue
                xa = max(int(math.floor(min(x0, x1, x2))) - 1, 0); xb = min(int(math.ceil(max(x0, x1, x2))) + 1, W - 1)
                ya = max(int(math.floor(min(y0, y1, y2))) - 1, 0); yb = min(int(math.ceil(max(y0, y1, y2))) + 1, H - 1)
                X, Y = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
                w0 = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / den
                w1 = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / den
                w2 = 1 - w0 - w1
                m = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
                if not m.any():
                    continue
                yy, xx = np.nonzero(m); wa, wb_, wc = w0[m][:, None], w1[m][:, None], w2[m][:, None]
                Pb[ya + yy, xa + xx] = pos[tri[0]] * wa + pos[tri[1]] * wb_ + pos[tri[2]] * wc
                Nb[ya + yy, xa + xx] = nrm[tri[0]] * wa + nrm[tri[1]] * wb_ + nrm[tri[2]] * wc
                Lb[ya + yy, xa + xx] = luv[tri[0]] * wa + luv[tri[1]] * wb_ + luv[tri[2]] * wc
                Tb[ya + yy, xa + xx] = t
    out = np.zeros((H, W, 4), np.float32)
    for t, i in tid.items():
        m = Tb == i
        if not m.any():
            continue
        Nn = Nb[m]; Nn = Nn / (np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-9)
        c, a = paint(t, refs, Pb[m], Nn, Lb[m])
        out[m, :3] = c; out[m, 3] = a
    # поля вокруг островков: растягиваем цвет наружу, чтобы фильтрация не тянула «пустоту»
    rgba = fill_invalid4(out, Tb >= 0, 6)
    return rgba, Tb


def fill_invalid4(img, valid, iters):
    rgb = fill_invalid(img[..., :3], valid, iters)
    al = fill_invalid(np.repeat(img[..., 3:4], 3, axis=2), valid, iters)[..., 0]
    out = np.zeros_like(img); out[..., :3] = rgb; out[..., 3] = np.where(dilate(valid, iters), al, 1.0)
    return out


def save_atlas(rgba, name="yur3_atlas"):
    h, w = rgba.shape[:2]
    img = bpy.data.images.get(name)
    if img and (img.size[0] != w or img.size[1] != h):
        bpy.data.images.remove(img); img = None
    img = img or bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(rgba[::-1]).ravel())
    path = os.path.join(TEX_DIR, name + ".png")
    img.filepath_raw = path; img.file_format = 'PNG'
    img.save()
    img.filepath = path
    return img


def make_material(name, img, alpha):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.9; bsdf.inputs["Metallic"].default_value = 0.0
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if img is not None:
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = 'Linear'
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha:
            rnd = nt.nodes.new("ShaderNodeMath"); rnd.operation = 'ROUND'
            nt.links.new(tex.outputs["Alpha"], rnd.inputs[0]); nt.links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
        nt.nodes.active = tex
    m.use_backface_culling = not alpha
    return m


# =====================================================================================
#  Скелет и веса
# =====================================================================================
def scene_ctx(sc):
    """Операторы работают в сцене окна Blender — main() заранее переключает окно на нашу сцену."""
    import contextlib
    if bpy.context.window.scene is not sc:
        bpy.context.window.scene = sc
    return contextlib.nullcontext()


def select_only(sc, obs, active):
    if bpy.context.window.scene is not sc:
        bpy.context.window.scene = sc
    vl = bpy.context.view_layer
    vl.update()
    for o in sc.objects:
        o.select_set(o in obs)
    vl.objects.active = active


def rig(ob, used, mb, coll, sc):
    arm_data = bpy.data.armatures.new("Yurchik3Rig")
    arm = bpy.data.objects.new("Yurchik3", arm_data)
    coll.objects.link(arm)
    select_only(sc, [arm], arm)
    with scene_ctx(sc):
        bpy.ops.object.mode_set(mode='EDIT')
        for n, h, t, p in BONES:
            b = arm_data.edit_bones.new(n)
            b.head = h; b.tail = t; b.roll = 0.0
            if p:
                b.parent = arm_data.edit_bones[p]
        bpy.ops.object.mode_set(mode='OBJECT')
    groups = {n: ob.vertex_groups.new(name=n) for n, *_ in BONES}
    for k, vid in enumerate(used):
        w = {b: x for b, x in mb.w[vid].items() if x > 1e-4}
        tot = sum(w.values())
        for b, x in w.items():
            groups[b].add([k], x / tot, 'REPLACE')
    ob.parent = arm
    mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
    return arm


def attach_to_bone(ob, arm, bone, sc):
    ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = bone
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone]
    from mathutils import Matrix
    ob.matrix_parent_inverse = (arm.matrix_world @ Matrix.Translation(pb.tail - pb.head) @ pb.matrix).inverted()


# =====================================================================================
def main():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    for ob in list(sc.objects):
        if ob.mode != 'OBJECT':
            select_only(sc, [ob], ob)
            with scene_ctx(sc):
                bpy.ops.object.mode_set(mode='OBJECT')
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll_ in (bpy.data.meshes, bpy.data.armatures):
        for d in list(coll_):
            if d.users == 0 and d.name.startswith(("Yurchik3", "Hammer3")):
                coll_.remove(d)
    bpy.context.window.scene = sc
    coll = sc.collection

    mb, grip = build_all()
    D, pos = pack_islands(mb)
    img = bpy.data.images.get("yur3_atlas")
    mats = [make_material("Yur3Body", img, False), make_material("Yur3Hair", img, True)]
    body, fsel_b, used_b = make_object(mb, 0, "Yurchik3Mesh", coll, mats)
    ham, fsel_h, used_h = make_object(mb, 1, "Hammer3", coll, mats[:1], origin=grip)
    info = {"tris_body": sum(len(mb.faces[f]) - 2 for f in fsel_b), "tris_hammer": sum(len(mb.faces[f]) - 2 for f in fsel_h),
            "verts": len(used_b), "density_px_per_m": round(D, 1)}
    if STAGE == "geo":
        return info

    refs = prep_reference()
    rgba, Tb = bake_atlas(mb, {0: (body.data, fsel_b), 1: (ham.data, fsel_h)}, refs)
    img = save_atlas(rgba)
    for m, a in zip(mats, (False, True)):
        make_material(m.name, img, a)
    info["atlas_fill"] = round(float((Tb >= 0).mean()), 3)
    if STAGE == "tex":
        return info

    arm = rig(body, used_b, mb, coll, sc)
    attach_to_bone(ham, arm, "HandR", sc)
    info["objects"] = [o.name for o in sc.objects]
    if globals().get("YUR_EXPORT", True):
        export_gltf(sc, arm, body, ham)
    scene_extras(sc)
    select_only(sc, [arm], arm)
    return info


def scene_extras(sc):
    """Камера, свет и серый фон — чтобы модель можно было сразу посмотреть и отрендерить (F12). В игру не экспортируются."""
    cam_d = bpy.data.cameras.get("Yur3Camera") or bpy.data.cameras.new("Yur3Camera")
    cam_d.lens = 70.0
    cam = bpy.data.objects.new("Yur3Camera", cam_d)
    sc.collection.objects.link(cam)
    target = Vector((0.0, 0.0, 0.90)); d = Vector((0.52, -0.84, 0.16)).normalized()
    cam.location = target + d * 4.3
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sun_d = bpy.data.lights.get("Yur3Sun") or bpy.data.lights.new("Yur3Sun", 'SUN')
    sun_d.energy = 2.0
    sun = bpy.data.objects.new("Yur3Sun", sun_d)
    sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((0.35, 0.6, -0.72)).to_track_quat('-Z', 'Y').to_euler()
    w = bpy.data.worlds.get("Yur3World") or bpy.data.worlds.new("Yur3World")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.45, 0.46, 0.48, 1.0); bg.inputs[1].default_value = 1.0
    sc.world = w
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1350
    sc.view_settings.view_transform = 'Standard'


def export_gltf(sc, arm, body, ham):
    """Экспорт в assets/models/yurchik.gltf. Игра ищет узлы по именам, поэтому в файле они без номера версии."""
    names = {arm: "Yurchik", body: "YurchikMesh", ham: "Hammer"}
    taken = {}
    for ob, n in names.items():                                       # временно освобождаем имена, занятые старыми сценами
        other = bpy.data.objects.get(n)
        if other is not None and other is not ob:
            taken[other] = n; other.name = n + "__old"
    keep = {ob: ob.name for ob in names}
    for ob, n in names.items():
        ob.name = n
    try:
        select_only(sc, list(names), arm)
        with scene_ctx(sc):
            bpy.ops.export_scene.gltf(filepath=os.path.join(OUT_DIR, "yurchik.gltf"), use_selection=True,
                                      use_active_scene=True, export_keep_originals=True, export_format='GLTF_SEPARATE',
                                      export_apply=False, export_skins=True, export_animations=False)
    finally:
        for ob, n in keep.items():
            ob.name = n
        for ob, n in taken.items():
            ob.name = n


result = main()
