# CLAUDE.md — Инструкции для Claude Code
# Проект: KIKI Night Club Analytics Bot

> Этот файл читается автоматически при старте. Следуй инструкциям строго.
> После каждого завершённого этапа обновляй BRAIN.md.

---

## Главное правило

Перед любым действием читай BRAIN.md.
Там записано что уже сделано, что не работает и почему.
Не повторяй то что уже пробовалось.

---

## Структура файлов проекта

```
kiki_bot/
├── CLAUDE.md              ← этот файл
├── BRAIN.md               ← твой дневник прогресса
├── PRD.md                 ← полное техзадание
├── .env                   ← секреты (не коммитить)
├── .env.example           ← шаблон без секретов
├── main.py
├── config.py
├── scheduler.py
├── requirements.txt
│
├── bot/
│   ├── __init__.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── superadmin.py
│   │   ├── admin.py
│   │   └── owner.py
│   ├── middlewares/
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── keyboards.py
│   └── messages.py
│
├── services/
│   ├── __init__.py
│   ├── stats_service.py
│   ├── report_service.py
│   ├── audit_service.py
│   └── user_service.py
│
├── repositories/
│   ├── __init__.py
│   ├── stats_repo.py
│   └── user_repo.py
│
├── models/
│   ├── __init__.py
│   └── db.py
│
└── miniapp/
    └── index.html
```

---

## Порядок разработки — строго по этапам

Не переходи к следующему этапу пока текущий не работает и не записан в BRAIN.md.

### Этап 1 — Модели и БД
- [ ] `models/db.py` — все 4 модели: User, ClubNight, HourlyStat, EditLog
- [ ] `init_db()` с автосозданием superadmin из SUPERADMIN_ID
- [ ] Проверка: `python -c "import asyncio; from models.db import init_db; asyncio.run(init_db())"`
- [ ] Должен создаться файл `kiki.db`

### Этап 2 — Конфиг
- [ ] `config.py` через pydantic-settings
- [ ] `.env.example` с заглушками
- [ ] Проверка: `python -c "from config import settings; print(settings.BOT_TOKEN[:10])"`

### Этап 3 — Репозитории
- [ ] `repositories/user_repo.py` — get_by_telegram_id, get_by_username, set_role, get_all, get_pending
- [ ] `repositories/stats_repo.py` — save_stat, get_night_stats, get_current_night, get_historical
- [ ] Проверка: юнит-тест каждого метода через asyncio.run()

### Этап 4 — Auth middleware
- [ ] `bot/middlewares/auth.py`
- [ ] Добавляет `data["user"]` и `data["role"]` в каждый хендлер
- [ ] Неизвестный пользователь → создаёт запись role="pending", отвечает "Нет доступа"
- [ ] Проверка ролей: superadmin видит всё, owner только /live и аналитику, admin только /input

### Этап 5 — Хендлеры: common + superadmin
- [ ] `bot/handlers/common.py` — /start (разное меню по роли), /myrole
- [ ] `bot/handlers/superadmin.py` — управление через Mini App API (не команды)
- [ ] Проверка: бот запускается, /start отвечает

### Этап 6 — Хендлер admin: ввод данных
- [ ] `/input 45 32 8 5` — quick mode, парсинг одной строкой
- [ ] FSM — пошаговый ввод через aiogram FSM
- [ ] Карточка подтверждения с inline-кнопками
- [ ] Изменение времени вручную (кнопка → запрос ЧЧ:ММ)
- [ ] `web_app_data` handler — приём данных из Mini App
- [ ] `/edit <id> <field> <value>` — редактирование с edit_log
- [ ] Проверка: ввести данные всеми тремя способами

### Этап 7 — Stats service + /live
- [ ] `services/stats_service.py`:
  - `get_live_occupancy(night_id)` → int
  - `get_current_night()` → ClubNight | None
  - `calc_deviation(current, historical_avg)` → float
  - `get_historical_avg(hour, day_of_week)` → float
- [ ] `bot/handlers/owner.py` — команда /live
- [ ] Проверка: /live возвращает правильные данные

### Этап 8 — Report service + аналитика
- [ ] `services/report_service.py`:
  - `build_night_report(night_id)` → str
  - `build_week_report()` → str
  - `build_month_report()` → str
  - `build_kpi_report()` → str
- [ ] Хендлеры: /night, /week, /month, /kpi, /logs
- [ ] ASCII прогрессбары для почасового трафика
- [ ] Проверка: каждая команда возвращает форматированный текст

### Этап 9 — Scheduler
- [ ] `scheduler.py` — APScheduler AsyncIOScheduler
- [ ] Cron: `hour='23,0,1,2,3,4,5', minute=5`
- [ ] Проверка: вручную вызвать `hourly_report()` и убедиться что owner получает сообщение

### Этап 10 — Mini App: index.html
- [ ] Один файл, без npm, без сборки
- [ ] Chart.js через CDN jsdelivr
- [ ] 5 вкладок: Ввод, Live, Ночь, Неделя, Команда
- [ ] Вкладка Команда — только если user.id === SUPERADMIN_ID
- [ ] Форма ввода с автовременем + ручная правка
- [ ] HTTP API для Mini App (aiohttp сервер или aiogram webhook)
- [ ] Валидация initData на каждый запрос
- [ ] Проверка: открыть Mini App в Telegram, ввести данные, убедиться что сохранилось

---

## Технические правила

### Python
```python
# Всегда async/await — никакого синхронного кода в хендлерах
# Type hints обязательны везде
# Логирование через logging, не print()
import logging
logger = logging.getLogger(__name__)

# Сессия БД всегда через dependency injection
async def handler(message: Message, session: AsyncSession = ...):
    ...

# Никогда не делай бизнес-логику в хендлерах
# Хендлер → Service → Repository → DB
```

### Определение текущей ночи
```python
from datetime import datetime, timedelta

def get_night_date(dt: datetime) -> str:
    # 00:00–05:59 относится к предыдущему дню
    if dt.hour < 6:
        return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")
```

### Формула occupancy
```python
inside = SUM(girls_entered + boys_entered) - SUM(left_count)
# Только записи текущей ночи (ClubNight.closed_at IS NULL)
```

### Формула deviation
```python
def calc_deviation(current: float, avg: float) -> float:
    if avg == 0:
        return 0.0
    return round((current / avg - 1) * 100, 1)
```

### ASCII прогрессбар
```python
def progress_bar(value: int, max_value: int, width: int = 10) -> str:
    filled = round(value / max_value * width) if max_value > 0 else 0
    return "█" * filled + "░" * (width - filled)
```

### Валидация initData Mini App
```python
import hmac, hashlib, urllib.parse

def validate_init_data(init_data: str, bot_token: str) -> bool:
    parsed = dict(urllib.parse.parse_qsl(init_data))
    check_string = parsed.pop("hash", "")
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, check_string)
```

---

## Дизайн Mini App — жёсткие правила

```
Фон:          #0A0A0A
Карточки:     #111111
Второй слой:  #1A1A1A
Акцент:       #FF6B00
Успех:        #34C759
Ошибка:       #FF3B30
```

- Шрифт: `-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif`
- Веса только 400 и 500 — никаких 600/700
- Скругления везде: карточки 16px, кнопки 10px, инпуты 10px, бейджи 99px
- Liquid Glass на навбаре и header: `backdrop-filter: blur(20px); background: rgba(255,255,255,0.05)`
- Никаких внешних CSS фреймворков
- `font-variant-numeric: tabular-nums` на всех числах
- `letter-spacing: -0.3px` на заголовках и числах
- Safe area: `padding-bottom: env(safe-area-inset-bottom)` на навбаре

---

## Что делать при ошибках

1. Запиши ошибку в BRAIN.md в раздел текущего этапа
2. Попробуй исправить
3. Если не получается за 2 попытки — запиши в BRAIN.md и переходи к следующей задаче
4. Не удаляй код который не работает — закомментируй с пометкой `# BROKEN: причина`
5. Никогда не меняй уже работающий код чтобы починить новый

---

## Запуск проекта

```bash
# Установка зависимостей
pip install -r requirements.txt

# Первый запуск (создаст kiki.db и superadmin)
python main.py

# Проверка БД
sqlite3 kiki.db "SELECT * FROM users;"
```

```
# requirements.txt
aiogram==3.7.0
sqlalchemy==2.0.30
aiosqlite==0.20.0
apscheduler==3.10.4
pydantic-settings==2.2.1
aiohttp==3.9.5
```

---

## Когда проект готов

Финальная проверка перед сдачей:
- [ ] /start работает для всех трёх ролей
- [ ] /input сохраняет данные всеми тремя способами
- [ ] /live показывает правильное occupancy
- [ ] /night /week /month /kpi возвращают отчёты
- [ ] Scheduler отправляет hourly report (проверить вручную)
- [ ] Mini App открывается и отправляет данные в бот
- [ ] Вкладка Команда работает: добавление, удаление, pending
- [ ] Edit log создаётся при /edit, owner получает уведомление
- [ ] kiki.db содержит все таблицы с правильными данными
