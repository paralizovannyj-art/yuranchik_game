# Анимации Garry's Mod на Юрчике

Анимации игрока Garry's Mod (SMD, скелет ValveBiped) перенесены на скелет Юрчика v3
и подключены к модели как AnimationLibrary `gmod`. Источник и авторы указаны в
`assets/animations/gmod/CREDITS.txt`. Анимации только для локальной сборки, не для публикации.

## Конвейер

```
gmod-animations/*.smd  →  tools/blender/retarget_gmod_yurchik.py (Blender, без GUI)
                       →  assets/animations/gmod/yurchik_gmod.glb + clips.json
                       →  Godot: импорт как AnimationLibrary (yurchik_gmod.glb.import)
                       →  scripts/player/yurchik_anim.gd: add_animation_library("gmod", …)
```

Повторить сборку (из корня проекта, Blender 5.2+):

```
git clone --depth 1 https://github.com/robotboy655/gmod-animations tools/blender/gmod-animations
blender -b tools/blender/yurchik_v3.blend --python tools/blender/retarget_gmod_yurchik.py
```

Если исходники лежат в другом месте, путь к ним передаётся после `--`.
Папка `tools/blender/gmod-animations/` есть в `.gitignore`.
Скрипт не сохраняет `yurchik_v3.blend`: он только читает скелет и пишет GLB и `clips.json`.
Godot переимпортирует GLB сам. Если редактор открыт, достаточно переключиться на него.

Что делает скрипт:

1. Читает SMD своим парсером, поэтому Blender Source Tools не нужен.
   Кости без ключа в кадре берутся из предыдущего кадра, как в studiomdl.
2. Пересэмплирует клип в 30 к/с с учётом fps из QC (`gm_base_m.qci`, `gm_sequences.qci`).
3. Переносит повороты: для каждой нашей кости берёт поворот кости ValveBiped относительно
   её rest-позы из `GMod/reference.smd` (delta) и доворачивает нашу кость к направлению
   кости-источника (q0): `world = delta · q0 · rest_our`. Это тот же приём, что в
   `retarget_ual_yurchik.py`. У ValveBiped и у Юрчика Z направлена вверх, вперёд смотрит -Y,
   а +X — левый бок, поэтому общий поворот не нужен. Смещение таза переводится из дюймов
   и масштабируется по высоте таза.
4. Убирает root motion (LX LY в QC): таз стоит на месте.
5. Ставит клип на землю по опорной стопе: берёт медиану покадрового минимума обеих стоп.
   Глобальный минимум не годится, потому что в ходьбе GMod носок маховой ноги проходит
   ниже опорной стопы.
6. Пишет в `clips.json` для каждого клипа:
   - `foot_speed` — с какой скоростью должен идти герой, чтобы опорная стопа не скользила;
   - `slide_cm` — насколько пятка или носок уезжают за время опоры при такой скорости.

Соответствие костей:

| Юрчик | ValveBiped |
|---|---|
| Pelvis | Bip01_Pelvis |
| Spine | Bip01_Spine4 (направление: Spine → Neck1) |
| Head | Bip01_Head1 |
| UpperArm / Forearm / Hand | Bip01_?_UpperArm / Forearm / Hand |
| Thigh / Shin / Foot | Bip01_?_Thigh / Calf / Foot |

Пальцы не переносятся: правая кисть держит молоток, и позу пальцев задаёт модель.
Ключицы, шея и Spine1–Spine2 сворачиваются в наши Spine и Head.

## В игре

- Локомоция переключается параметром `locomotion` в инспекторе модели игрока
  (`scenes/characters/player.tscn` → Model) или клавишей **F7** прямо в игре:
  - `GMOD` (по умолчанию) — `gmod/Idle`, `gmod/Walk`, `gmod/WalkBack`, `gmod/Run`;
  - `PROCEDURAL` — прежние процедурные стойка, ходьба и бег.
- Механика приседа и прыжка (кнопки, капсула, выносливость, шум) — в `player.gd`.
  Анимации берут оттуда состояния «сидит» и «в воздухе». Процедурная поза приседа
  `YurchikLean` включается, только если библиотеки `gmod` нет.
- **Присед** (держать Ctrl, C — переключатель): `gmod/CrouchIdle`, `gmod/CrouchWalk`,
  `gmod/CrouchWalkBack`.
- **Прыжок** (Space): ноги, а с весом `air_body` и корпус с руками, смешивают три позы
  по вертикальной скорости героя:
  - `gmod/JumpRise` — толчок: толчковая нога выпрямлена, руки работают в противофазе ногам;
  - `gmod/JumpApex` — верхняя точка: колени подтянуты;
  - `gmod/JumpFall` — ноги идут к земле.

  Эти три позы строятся прямо в `retarget_gmod_yurchik.py` (таблица `JUMP_POSES`, углы в градусах).
  Из GMod их взять нельзя: прыжок там — аддитивный слой `jump_c`, руки в нём остаются
  в reference-позе (почти T-поза), а голень заброшена назад. Вход в позу плавный (`air_in`).
  При касании с места играет `gmod/JumpLand`, он подхватывает позу «ноги к земле» с коротким переходом. На бегу цикл бега продолжается с кадра, где стопа ставится на землю.
  Работает в обоих наборах.
- Разовые клипы: `model.play_action("gmod/Wave")` для всего тела,
  `model.play_action("gmod/GrenadeThrow", true)` только для верха.
  Жесты с предметами (`GrenadeThrow`, `ItemDrop`, `ItemPlace`, `ItemGive`, `Shove`)
  в GMod играются только на верх тела, ноги у них случайные. Их нужно вызывать с `upper = true`.

Скорости клипов (`gmod_*_speed` в `yurchik_anim.gd`) взяты из `foot_speed` в `clips.json`.
После пересборки их нужно сверить.

## Что перенесено (72 клипа)

| Группа | Клипы |
|---|---|
| Базовые | Idle, Walk, WalkBack, WalkLeft, WalkRight, Run, RunBack, RunLeft, RunRight, CrouchIdle, CrouchWalk(Back/Left/Right), Jump, JumpLand, JumpRise, JumpApex, JumpFall, StandToCrouch, CrouchToStand |
| Стойки | IdleAngry, IdleScared, IdleSubtle, FistsIdle, Cower, RunPanicked, Swim, SwimIdle, Sit, SitZen |
| Удары, броски | FistsAttack, PunchA, PunchB, FistBlock, MeleeHit1–3, Melee2Attack, Shove, GrenadeThrow, ItemDrop, ItemPlace, ItemGive |
| Получил удар | FlinchHead, FlinchHead2, FlinchStomach, FlinchStomach2, FlinchBack, FlinchShoulderL/R, Flinch1, Flinch2 |
| Смерть | Death1–4 |
| Жесты | Wave, Agree, Disagree, Bow, Beckon, Salute, SignalForward, SignalHalt, SignalGroup, Cheer, Dance, Laugh, Muscle, Robot, Persistence |

Проскальзывание опорной стопы (`slide_cm`):
- 0.5 см у Walk, 1.1 у Run, 1.1 у CrouchWalk;
- 1.7–3 см у ходьбы назад и вбок;
- до 6 см у RunBack и до 9.5 см у бега вбок.

Бег вбок и назад пока в игре не задействован.

## Что не перенесено и почему

- **Слои прицеливания и оружия** (`aimlayers/`, `9way_central/`, перезарядки и стрельба
  из `combine_soldier_xsi/`, `Police_XSI/`, `Player/HL2DM_*`). Это позы и аддитивные слои
  под оружие HL2, которого в игре нет. В GMod они собираются в 9-позиционные блендспейсы
  через `worldspaceblend`, и прямого аналога в нашем дереве нет.
- **`base_f/`** — женская версия того же набора. Юрчику нужна мужская (`base_m/`).
- **`humans_sdk/`** — анимации горожан HL2. Они пересекаются с `base_m/`.
- **`zombie/`** — анимации под зомби. Если понадобятся врагам, на скелет врагов
  (`tools/blender/build_enemies.py`) нужен отдельный ретаргет.
- **Транспорт и спецрежимы**: drive_*, Ride*, noclip, `gesture_voicechat`, breath-слои.
- **`c_arms_*`** — руки для вида от первого лица (viewmodel). У нас видно всё тело,
  а риг этих рук другой.
- **Остальные переходы** (`transitions/`, кроме StandToCrouch и CrouchToStand),
  9-направленные прыжки `jump_n…jump_sw` (у `jump_n` в последнем кадре сломан таз)
  и 8 направлений плавания, кроме `swim_n`.
- **Пальцы** — по всем клипам (причина выше).

Новый клип добавляется строкой в таблицу `CLIPS` в `retarget_gmod_yurchik.py`
с файлом, fps из QC и флагами (loop, inplace, ground). Если клип зацикленный,
его имя нужно добавить ещё и в `GMOD_LOOPS` в `yurchik_anim.gd`.
