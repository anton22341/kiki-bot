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

**Текущий этап:** завершён (все 10 этапов)
**Последнее обновление:** 2026-05-29
**Общий статус:** 🟢 готово к запуску

```
Этап 1 — Модели и БД          [x] готово
Этап 2 — Конфиг               [x] готово
Этап 3 — Репозитории          [x] готово
Этап 4 — Auth middleware       [x] готово
Этап 5 — Common + Superadmin   [x] готово
Этап 6 — Admin: ввод данных   [x] готово
Этап 7 — Stats service + live  [x] готово
Этап 8 — Report service        [x] готово
Этап 9 — Scheduler             [x] готово
Этап 10 — Mini App             [x] готово
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

_BRAIN.md v1.0 · KIKI Night Club Analytics_
_Обновляй после каждого этапа_
