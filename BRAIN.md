# BRAIN.md — Дневник прогресса
# Проект: KIKI Night Club Analytics Bot

> Обновляй этот файл после каждого завершённого этапа.
> Пиши честно: что работает, что нет, что пробовал.
> Это твоя память между сессиями — не ленись писать подробно.

---

## Как пользоваться этим файлом

**Перед началом работы:** прочитай весь файл сверху вниз.
**После завершения этапа:** заполни его секцию.
**При ошибке:** запиши в раздел "Проблемы" текущего этапа.
**Формат статуса:**
- `[ ]` — не начато
- `[~]` — в процессе
- `[x]` — готово и работает
- `[!]` — сломано, требует внимания
- `[-]` — пропущено намеренно

---

## Состояние проекта

**Текущий этап:** 14 (UX benchmark блока)
**Последнее обновление:** 2026-05-30
**Общий статус:** 🟡 в работе

```
Этап 1  — Модели и БД          [x] готово
Этап 2  — Конфиг               [x] готово
Этап 3  — Репозитории          [x] готово
Этап 4  — Auth middleware       [x] готово
Этап 5  — Common + Superadmin   [x] готово
Этап 6  — Admin: ввод данных   [x] готово
Этап 7  — Stats service + live  [x] готово
Этап 8  — Report service        [x] готово
Этап 9  — Scheduler             [x] готово
Этап 10 — Mini App             [x] готово
Этап 11 — Исторические данные  [x] готово
Этап 12 — Фиксы Live           [x] готово
Этап 13 — Накопительный ввод   [x] готово
Этап 14 — UX benchmark         [~] в процессе
```

---

## Окружение

```
Python версия:    3.11.9 (pyenv)
OS:               macOS Darwin 24.6.0
aiogram версия:   3.7.0
SQLAlchemy:       2.0.30
БД файл:          kiki.db (создан, superadmin добавлен)
BOT_TOKEN:        установлен ✅
SUPERADMIN_ID:    1124050597 ✅
WEBAPP_URL:       пустой (заполнить перед деплоем Mini App)
```

---

---

## Этап 1 — Модели и БД

**Статус:** `[x]`
**Дата начала:** 2026-05-29
**Дата завершения:** 2026-05-29

### Что сделано
Созданы все 4 модели SQLAlchemy (User, ClubNight, HourlyStat, EditLog) в `models/db.py`.
`init_db()` создаёт таблицы и запись superadmin из SUPERADMIN_ID.

### Файлы созданы/изменены
- [x] `models/db.py`
- [x] `kiki.db` — создан автоматически

### Проверка пройдена
- [x] kiki.db создан
- [x] Все 4 таблицы есть (users, club_nights, hourly_stats, edit_logs)
- [x] Запись superadmin (telegram_id=1124050597) есть в users

### Проблемы и решения

```
Проблема: ValueError: the greenlet library is required
Решение: pip install greenlet (не входит в стандартный sqlalchemy)
```

---

## Этап 2 — Конфиг

**Статус:** `[x]`
**Дата начала:** 2026-05-29
**Дата завершения:** 2026-05-29

### Что сделано
`config.py` через pydantic-settings. `.env` заполнен реальными данными. `.env.example` с заглушками.

### Файлы созданы/изменены
- [x] `config.py`
- [x] `.env`
- [x] `.env.example`

### Проверка пройдена
- [x] `from config import settings; print(settings.SUPERADMIN_ID)` → 1124050597

---

## Этап 3 — Репозитории

**Статус:** `[x]`
**Дата начала:** —
**Дата завершения:** —

### Что сделано
_Заполнить после выполнения_

### Файлы созданы/изменены
- [ ] `repositories/user_repo.py`
- [ ] `repositories/stats_repo.py`

### Методы реализованы

**user_repo.py:**
- [ ] `get_by_telegram_id(telegram_id)` → User | None
- [ ] `get_by_username(username)` → User | None
- [ ] `set_role(telegram_id, role)` → User
- [ ] `get_all()` → list[User]
- [ ] `get_by_role(role)` → list[User]
- [ ] `get_pending()` → list[User]
- [ ] `create_pending(telegram_id, username, full_name)` → User

**stats_repo.py:**
- [ ] `save_stat(night_id, data)` → HourlyStat
- [ ] `get_night_stats(night_id)` → list[HourlyStat]
- [ ] `get_current_night()` → ClubNight | None
- [ ] `get_or_create_night(date, day_of_week)` → ClubNight
- [ ] `get_historical_stats(day_of_week, hour)` → list[HourlyStat]
- [ ] `save_edit_log(stat_id, field, old_val, new_val, user_id)` → EditLog
- [ ] `get_edit_logs(limit)` → list[EditLog]

### Проблемы и решения

```
Проблема:
Попытка 1:
Результат:
Решение:
```

### Заметки

---

## Этап 4 — Auth Middleware

**Статус:** `[ ]`
**Дата начала:** —
**Дата завершения:** —

### Что сделано
_Заполнить после выполнения_

### Файлы созданы/изменены
- [ ] `bot/middlewares/auth.py`

### Логика реализована
- [ ] Читает telegram_id из message/callback
- [ ] Ищет пользователя в БД
- [ ] Если не найден → создаёт pending, отправляет "Нет доступа"
- [ ] Добавляет `data["user"]` и `data["role"]`
- [ ] Superadmin имеет доступ ко всем командам

### Проблемы и решения

```
Проблема:
Попытка 1:
Результат:
Решение:
```

### Заметки

---

## Этап 5 — Common + Superadmin хендлеры

**Статус:** `[ ]`
**Дата начала:** —
**Дата завершения:** —

### Что сделано
_Заполнить после выполнения_

### Файлы созданы/изменены
- [ ] `bot/handlers/common.py`
- [ ] `bot/handlers/superadmin.py`
- [ ] `bot/keyboards.py` (начат)

### Команды реализованы
- [ ] `/start` — разное меню по роли
- [ ] `/myrole` — показать свою роль
- [ ] Mini App API: `GET /api/users`
- [ ] Mini App API: `POST /api/users/role`
- [ ] Mini App API: `POST /api/users/remove`
- [ ] Mini App API: `GET /api/users/pending`

### Проверка
- [ ] Бот стартует без ошибок (`python main.py`)
- [ ] /start отвечает superadmin
- [ ] /start отвечает pending "Нет доступа"

### Проблемы и решения

```
Проблема:
Попытка 1:
Результат:
Решение:
```

### Заметки

---

## Этап 6 — Admin: ввод данных

**Статус:** `[ ]`
**Дата начала:** —
**Дата завершения:** —

### Что сделано
_Заполнить после выполнения_

### Файлы созданы/изменены
- [ ] `bot/handlers/admin.py`
- [ ] `services/audit_service.py`

### Функционал реализован
- [ ] `/input 45 32 8 5` — quick mode
- [ ] FSM пошаговый ввод
- [ ] Карточка подтверждения с inline-кнопками
- [ ] Кнопка "Изменить время" → запрос ЧЧ:ММ → is_manual_time=True
- [ ] `web_app_data` handler — приём из Mini App
- [ ] `/edit <id> <field> <value>` — редактирование
- [ ] Edit log при редактировании
- [ ] Уведомление owner при редактировании

### Тест ввода
```
Способ 1 (quick):  /input 45 32 8 5    → [x/]
Способ 2 (FSM):    пошаговый диалог    → [x/]
Способ 3 (webapp): из Mini App         → [x/]
```

### Проблемы и решения

```
Проблема:
Попытка 1:
Результат:
Решение:
```

### Заметки
_Особенности FSM, трудности с web_app_data и т.д._

---

## Этап 7 — Stats service + /live

**Статус:** `[ ]`
**Дата начала:** —
**Дата завершения:** —

### Что сделано
_Заполнить после выполнения_

### Файлы созданы/изменены
- [ ] `services/stats_service.py`
- [ ] `bot/handlers/owner.py` (начат)

### Методы реализованы
- [ ] `get_live_occupancy(night_id)` → int
- [ ] `get_current_night()` → ClubNight | None
- [ ] `calc_deviation(current, avg)` → float
- [ ] `get_historical_avg(hour, day_of_week)` → float
- [ ] `get_peak_hour(night_id)` → tuple[str, int]
- [ ] `get_fc_conversion(night_id)` → float
- [ ] `get_ratio(night_id)` → tuple[float, float]

### Проверка /live
```
Ожидаемый вывод /live:
🟢 KIKI — Live сейчас
👥 Внутри: N чел
...
```
- [ ] Команда /live работает
- [ ] Occupancy считается правильно
- [ ] Deviation считается (если есть исторические данные)

### Проблемы и решения

```
Проблема:
Попытка 1:
Результат:
Решение:
```

### Заметки

---

## Этап 8 — Report service + аналитика

**Статус:** `[ ]`
**Дата начала:** —
**Дата завершения:** —

### Что сделано
_Заполнить после выполнения_

### Файлы созданы/изменены
- [ ] `services/report_service.py`
- [ ] `bot/handlers/owner.py` (дополнен)
- [ ] `bot/messages.py`

### Команды реализованы
- [ ] `/night` — итог текущей/последней ночи
- [ ] `/week` — статистика за неделю
- [ ] `/month` — статистика за месяц
- [ ] `/kpi` — KPI дашборд
- [ ] `/logs` — последние edit logs

### ASCII прогрессбар
```python
# Пример вывода:
# 23:00  ████░░░░  42 (+5%)
# Реализован?
```
- [ ] Прогрессбар работает корректно

### Проблемы и решения

```
Проблема:
Попытка 1:
Результат:
Решение:
```

### Заметки

---

## Этап 9 — Scheduler

**Статус:** `[ ]`
**Дата начала:** —
**Дата завершения:** —

### Что сделано
_Заполнить после выполнения_

### Файлы созданы/изменены
- [ ] `scheduler.py`

### Реализовано
- [ ] APScheduler AsyncIOScheduler инициализирован
- [ ] Cron: `hour='23,0,1,2,3,4,5', minute=5`
- [ ] Проверка открытой ночи перед отправкой
- [ ] Hourly report отправляется всем owner + superadmin
- [ ] Scheduler стартует в main.py

### Ручная проверка
```python
# Вызвать вручную:
asyncio.run(hourly_report(bot))
# Owner получил сообщение?
```
- [ ] Ручная проверка пройдена

### Проблемы и решения

```
Проблема:
Попытка 1:
Результат:
Решение:
```

### Заметки

---

## Этап 10 — Mini App

**Статус:** `[ ]`
**Дата начала:** —
**Дата завершения:** —

### Что сделано
_Заполнить после выполнения_

### Файлы созданы/изменены
- [ ] `miniapp/index.html`
- [ ] HTTP API добавлен в main.py или отдельный сервер

### Вкладки реализованы
- [ ] Ввод — форма с автовременем, ручная правка времени
- [ ] Live — occupancy, прогрессбар, Chart.js бар-чарт
- [ ] Ночь — итоги, 2 графика (трафик + соотношение)
- [ ] Неделя — 3 подвкладки (неделя/месяц/KPI)
- [ ] Команда — только для superadmin, добавление/удаление/pending

### Chart.js графики
- [ ] Bar chart (Live) — текущий час оранжевый, прошлые прозрачные
- [ ] Bar chart (Ночь) — вошло vs ушло
- [ ] Stacked bar (Соотношение Ж/М)
- [ ] Bar chart (Неделя по ночам)
- [ ] Line chart (Месяц)
- [ ] Horizontal bar (KPI факт vs цель)

### Дизайн
- [ ] Фон #0A0A0A везде
- [ ] Акцент #FF6B00 на кнопках и активных элементах
- [ ] Liquid glass на навбаре и header
- [ ] SF Pro шрифт (system-ui)
- [ ] Все скругления на месте
- [ ] Safe area iPhone учтена

### API
- [ ] GET /api/users работает
- [ ] POST /api/users/role работает
- [ ] POST /api/users/remove работает
- [ ] GET /api/users/pending работает
- [ ] Валидация initData реализована
- [ ] sendData → бот принимает → подтверждение

### Хостинг
```
URL Mini App: —
Хостинг:      — (GitHub Pages / Netlify / другое)
```

### Проблемы и решения

```
Проблема:
Попытка 1:
Результат:
Решение:
```

### Заметки
_Особенности работы с Telegram WebApp SDK, проблемы с initData и т.д._

---

## Известные ограничения и баги

> Сюда записывай всё что не работает идеально но оставлено намеренно

| # | Описание | Влияние | Решение в будущем |
|---|----------|---------|-------------------|
| — | — | — | — |

---

## Что точно НЕ работает (не пробовать снова)

> Сюда записывай подходы которые уже пробовались и провалились

| Что пробовал | Почему не работает | Дата |
|---|---|---|
| SQLAlchemy async без greenlet | ValueError на первом подключении | 2026-05-29 |

## Файлы проекта (все созданы)

```
main.py              — точка входа, запускает бот + HTTP API на порту 8080
config.py            — pydantic-settings, читает .env
scheduler.py         — APScheduler hourly_report cron
api_server.py        — aiohttp HTTP API для Mini App (валидация initData)

models/db.py         — 4 модели + init_db() + AsyncSessionLocal
repositories/
  user_repo.py       — CRUD пользователей
  stats_repo.py      — CRUD статистики, ночей, edit_logs
services/
  stats_service.py   — occupancy, deviation, peak, fc, ratio
  report_service.py  — night/week/month/kpi/hourly/edit_logs отчёты
bot/
  middlewares/auth.py — AuthMiddleware: pending → "нет доступа", inject user/role
  keyboards.py        — inline и reply клавиатуры
  messages.py         — форматирование, progress_bar
  handlers/
    common.py         — /start /myrole
    superadmin.py     — /users /addowner /addadmin /removeuser
    admin.py          — /input FSM, web_app_data, /edit /status
    owner.py          — /live /night /week /month /kpi /logs
miniapp/index.html   — полный Mini App (vanilla JS, Chart.js CDN)
```

## Как запустить

```bash
pip install -r requirements.txt
python main.py
# Бот: @kikianalyticsbot
# HTTP API: http://localhost:8080
```

## Деплой на Railway (2026-05-29)

**Статус:** ✅ БОТ РАБОТАЕТ

### Инфраструктура
- **Платформа:** Railway (план Pro)
- **БД:** Railway PostgreSQL (встроенная, не Supabase — пулер Supabase не работал: tenant not found)
- **URL бота:** https://web-production-5d05b.up.railway.app
- **Домен:** www.kiki-analysis.ru (DNS обновляется, ~60 мин)

### Переменные Railway (web сервис)
- `BOT_TOKEN` — токен бота
- `SUPERADMIN_ID` — 1124050597
- `WEBAPP_URL` — https://www.kiki-analysis.ru
- `DATABASE_URL` — ${{Postgres.DATABASE_URL}} (Railway PostgreSQL)

### Проблемы при деплое
- Supabase pooler (порт 6543 и 5432) — `tenant not found` для проекта effkvrrzjtoilzcakhsf
- Прямое подключение Supabase — IPv6 only, Railway на IPv4
- Решение: Railway встроенный PostgreSQL

### DNS записи (рег.ру)
- CNAME: `www.kiki-analysis.ru` → `v4eq8d44.up.railway.app`
- TXT: `_railway-verify.www` → railway-verify=5df84c0ea941011fe40d7a432...
- TXT: `_railway-verify` → railway-verify=945f7885360c83e48043092b5...

## Исправления от 2026-05-29

- **API dev mode**: пустой initData → superadmin fallback (для тестирования в браузере)
- **CORS middleware**: добавлен для локальной разработки  
- **Недели/месяц**: фильтрация только Пт+Сб (CLUB_DAYS = "fri","sat")
- **Toast**: z-index и позиция выше navbar (fixed bottom с учётом высоты navbar)
- **Команда**: вкладка видна через `/api/me`, в dev-режиме всегда открыта
- **Редактирование ролей**: кнопка ✏️ открывает sheet с выбором новой роли
- **Live vs Ночь**: добавлены подписи что именно показывает каждый экран
- **/api/input**: POST эндпоинт для сохранения данных из браузера (не через sendData)

---

## Полезные команды

```bash
# Запуск бота
python main.py

# Проверка БД
sqlite3 kiki.db ".tables"
sqlite3 kiki.db "SELECT telegram_id, username, role FROM users;"
sqlite3 kiki.db "SELECT * FROM hourly_stats ORDER BY created_at DESC LIMIT 5;"
sqlite3 kiki.db "SELECT * FROM edit_logs ORDER BY edited_at DESC LIMIT 5;"

# Сброс БД (осторожно!)
rm kiki.db && python main.py

# Проверка импортов
python -c "from models.db import init_db; print('models OK')"
python -c "from config import settings; print('config OK')"
python -c "from bot.handlers.admin import router; print('admin OK')"

# Логи в реальном времени
python main.py 2>&1 | grep -v DEBUG
```

---

## Финальный чеклист

Заполнить когда проект готов к сдаче:

- [ ] Все 10 этапов завершены
- [ ] /start работает для superadmin, owner, admin, pending
- [ ] Ввод данных работает 3 способами
- [ ] /live показывает правильное occupancy
- [ ] /night /week /month /kpi /logs работают
- [ ] Scheduler протестирован вручную
- [ ] Mini App открывается в Telegram
- [ ] Вкладка Команда работает полностью
- [ ] Edit log + уведомления работают
- [ ] .env.example заполнен корректно
- [ ] requirements.txt актуален
- [ ] Нет print() в продакшн коде (только logging)
- [ ] Нет захардкоженных токенов или ID в коде

---

## Этап 11 — Исторические данные и Benchmark

**Статус:** `[x]`
**Дата:** 2026-05-29

### Что сделано
- Добавлено поле `is_historical` в модель `HourlyStat`
- Создан `scripts/import_historical.py` — импорт 4 ночей из хардкода
- Добавлен `get_benchmark()` в `stats_service.py`
- Обновлён `/live` хендлер — показывает delta 🟢🟠🔴 vs исторический avg
- Обновлён `/night` хендлер — delta в почасовой таблице
- Mini App Live — benchmark под карточками девушек/парней
- API endpoint `/api/admin/import-historical` для запуска импорта на сервере

### Данные импортированы (локально)
- 4 ночи: Пт 15.05, Сб 16.05, Пт 22.05, Сб 23.05
- 20 записей HourlyStat

### Файлы изменены
- `models/db.py` — +is_historical колонка, +ALTER TABLE миграция
- `services/stats_service.py` — +get_benchmark(), +_signal(), +_emoji()
- `services/report_service.py` — benchmark в /night почасовой таблице
- `bot/handlers/owner.py` — обновлён /live с benchmark
- `api_server.py` — benchmark в /api/live, +/api/admin/import-historical
- `miniapp/index.html` — Live экран с benchmark
- `scripts/import_historical.py` — новый файл

### Как запустить импорт на Railway
```bash
curl -X POST https://web-production-5d05b.up.railway.app/api/admin/import-historical
```

---

## Этап 14 — UX benchmark блока (2026-05-30)

**Статус:** `[~]` в процессе
**Коммит до изменений:** 9964f41
**Последний коммит этапа:** 5225b50

### Сделано
- Убраны мини-% из карточек "Внутри" (путали пользователя)
- Benchmark блок переименован: "Поток за последний час — сравнение с историей"
- Граница ночи изменена с 6:00 на 8:00 МСК (api_server.py, admin.py)
- Планировщик: auto-close ночи в 8:00 + отправка итога owner/superadmin
- Страховка в get_current_night: если планировщик не сработал — скрываем старую ночь днём
- Benchmark: теперь берёт час последней записи, а не реальный час телефона (фикс "всегда 00:30")

### Осталось сделать
- Вариант A: показывать в блоке "Сейчас 172 → avg 106 🟢 +62%" (не сделано)
- Баг benchmark с накопительными данными (см. ниже)

### Баг benchmark с накопительными данными
Исторические ночи хранят ДЕЛЬТЫ (81 девушка за этот час).
Реальные накопительные ночи хранят ИТОГИ (312 девушек всего с начала ночи).
Бенчмарк не различает их → когда реальных ночей накопится много, avg начнёт завышаться.
Нужно: при добавлении реальной ночи в avg — вычислять дельту для нужного часа.

### ОТКАТ (если что-то пойдёт не так)
```bash
git reset --hard 9964f41
git push --force origin main
```

---

## Этап 13 — Переход на накопительный ввод (2026-05-30)

**Статус:** `[x]` готово
**Коммит до изменений:** 94a1ea0

### Проблема
Администраторы вводят данные НАКОПИТЕЛЬНЫМ ИТОГОМ (счётчик с начала ночи),
а логика суммировала все записи как будто каждая — это данные за отдельный час.
Результат: total за ночь = 2226 вместо реальных ~536.

### Что нужно изменить
- `stats_service.py` — добавить `compute_night_stats()`: для live-записей (is_historical=False)
  брать последнюю запись как итог, дельты между записями как почасовой поток
- `api_server.py` — все эндпоинты использовать `compute_night_stats()`
- Live: сброс в 8:00 МСК (не показывать ночь прошлого дня)
- Ночь: починить стрелки навигации (перепутаны onclick +1/-1)

### Все коммиты этапа 13
```
9964f41 Remove misleading + sign from history entries
3636f2b Fix compute_night_stats: sort by counter value not timestamp
a08375c Remove time-based restriction from get_current_night
5ec26a8 Fix timezone: convert recorded_at from UTC to MSK
5cfc552 Fix report_service and owner.py to use compute_night_stats()
8e0a017 Stage 13: cumulative input logic, night nav fix
```

### Что сделано
- `stats_service.py` — добавлен `compute_night_stats()`: автоопределение режима
  по `is_historical` флагу. Live (накопительный) → итог = последняя запись,
  почасовой поток = дельты. Исторический → сумма записей как раньше.
- Все функции `get_live_occupancy`, `get_live_split`, `get_fc_conversion`,
  `get_ratio`, `get_peak_hour` переписаны через `compute_night_stats()`
- `get_current_night()` — сброс Live в 08:00–20:00 МСК (клуб закрыт)
- `api_server.py` — все 5 эндпоинтов (live, night, week, month, kpi)
  используют `compute_night_stats()`
- Benchmark: сравниваем дельту последнего часа, а не накопленный итог
- `miniapp/index.html` — исправлены onclick стрелок навигации по датам
  (‹ = shiftNight(+1), › = shiftNight(-1))

### ОТКАТ (если что-то пойдёт не так)
```bash
git reset --hard 94a1ea0
git push --force origin main
```

---

## Этап 12 — Фиксы аналитики Live (2026-05-29)

**Статус:** `[x]`
**Коммит:** c09ccbb
**Деплой:** Railway (auto, push → main)

### Что исправлено

**Benchmark блок ("В это же время обычно"):**
- Было: при отсутствии данных за текущий час — fallback на итоги всей ночи (показывало ~620/387 = бессмысленно)
- Стало: ищет ближайший час с ≥2 историческими записями (±1, ±2, ...)
- Если подходящий час найден но отличается от текущего — в подписи показывает `· данные за HH:xx`
- Если данных нет вообще — блок скрыт (return None)
- `used_hour` добавлен в API-ответ `/api/live` → `bm_data`

**Круговая диаграмма Ж/М в Live:**
- Было: если `girls_inside`/`boys_inside` = 0 — `mkDoughnut` возвращал без рендера, оставался только текст
- Стало: fallback на `girls_entered`/`boys_entered` (кто вошёл за ночь), диаграмма всегда рисуется при наличии данных

**Стейл-чарт после удаления записи:**
- Было: удаление записи → `loadLive()` → `hourly.length=0` → `if (hasData)` пропускается → старый Chart.js инстанс остаётся
- Стало: при `!hasData` явный `charts['live-chart'].destroy()` + `delete charts['live-chart']`

### Файлы изменены
- `services/stats_service.py` — `get_benchmark()`: убран night-fallback, добавлен поиск ближайшего часа + `used_hour` в возврат
- `api_server.py` — `used_hour` пробрасывается в `bm_data`
- `miniapp/index.html` — doughnut fallback, stale-chart fix, подпись `used_hour` в benchmark

---

_BRAIN.md v1.1 · KIKI Night Club Analytics_
_Обновляй после каждого этапа_
