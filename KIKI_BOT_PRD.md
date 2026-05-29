# KIKI Night Club Analytics — Telegram Bot + Mini App
## Product Requirements Document (Claude Code Edition)

---

## 1. Обзор проекта

Telegram-бот с Mini App для аналитики ночного клуба KIKI. Система собирает статистику посетителей, считает live-occupancy, строит аналитику по ночам/неделям/месяцам и отправляет автоматические отчёты владельцу.

**Стек:**
- Backend: Python 3.11+, aiogram 3.x, SQLAlchemy 2.x async, SQLite (→ PostgreSQL ready), APScheduler
- Mini App: Vanilla HTML/CSS/JS (один файл `index.html`), хостинг на любом статик-сервере
- Архитектура: Clean Architecture, Service Layer, Repository Pattern, полностью async

---

## 2. Дизайн-система (ОБЯЗАТЕЛЬНО соблюдать везде)

### 2.1 Цветовая палитра

```css
/* Primary */
--color-orange:        #FF6B00;   /* основной акцент */
--color-orange-bright: #FF8C00;   /* hover, активные элементы */
--color-orange-dim:    #FF6B0033; /* 20% opacity, фоны карточек */
--color-orange-glow:   #FF6B0015; /* 8% opacity, subtle fills */

/* Neutrals */
--color-black:    #0A0A0A;   /* основной фон */
--color-surface:  #111111;   /* карточки первого уровня */
--color-surface2: #1A1A1A;   /* карточки второго уровня */
--color-border:   #FFFFFF12; /* границы */
--color-white:    #FFFFFF;
--color-white-60: rgba(255,255,255,0.60);
--color-white-30: rgba(255,255,255,0.30);
--color-white-10: rgba(255,255,255,0.10);

/* Semantic */
--color-success: #34C759;
--color-danger:  #FF3B30;
--color-warning: #FF9500;
```

### 2.2 Типографика — SF Pro (Apple-style)

```css
font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display',
             'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;

/* Шкала */
--text-xs:   11px;  /* подписи, hints */
--text-sm:   13px;  /* secondary text */
--text-base: 15px;  /* основной текст */
--text-lg:   17px;  /* заголовки секций */
--text-xl:   22px;  /* крупные числа */
--text-2xl:  28px;  /* главные метрики */
--text-3xl:  36px;  /* hero числа */

/* Веса только 400 и 500 — никаких 600/700 */
font-weight: 400; /* обычный текст */
font-weight: 500; /* заголовки, числа */

/* Letter spacing */
letter-spacing: -0.3px; /* для чисел и заголовков */
font-variant-numeric: tabular-nums; /* все числа одной ширины */
```

### 2.3 Скругления — везде без исключений

```css
--radius-sm:   8px;   /* инпуты, маленькие кнопки, бейджи */
--radius-md:   12px;  /* карточки, поля */
--radius-lg:   16px;  /* основные карточки */
--radius-xl:   20px;  /* большие блоки */
--radius-pill: 99px;  /* пилюли, аватары */
```

### 2.4 Liquid Glass эффект

Применяется на: навигационный бар, модальные окна, toast-уведомления, header Mini App.

```css
.glass {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-lg);
}

/* Усиленный glass для header */
.glass-strong {
  background: rgba(255, 107, 0, 0.08);
  backdrop-filter: blur(30px) saturate(200%);
  -webkit-backdrop-filter: blur(30px) saturate(200%);
  border: 0.5px solid rgba(255, 107, 0, 0.20);
}
```

### 2.5 Прочие правила

- Никаких теней — только `border` и `backdrop-filter`
- Все анимации: `transition: all 0.2s ease`
- Активные состояния: `transform: scale(0.97)`
- Иконки: только emoji или Unicode — без сторонних библиотек в боте; в Mini App можно SVG inline
- Никаких внешних CSS-фреймворков — только чистый CSS
- Все блоки Mini App: `overflow: hidden` + скругления

---

## 3. Роли пользователей

Система поддерживает три уровня доступа. Роли хранятся в БД, управляются командами — **не в .env файле**.

```
superadmin → owner → admin
```

| Роль         | Кто              | Что может                                              |
|--------------|------------------|--------------------------------------------------------|
| `superadmin` | Разработчик (ты) | Всё. Выдаёт и отзывает любые роли. Видит всё.         |
| `owner`      | Владелец клуба   | Вся аналитика, KPI, отчёты, логи. Не вводит данные.   |
| `admin`      | Менеджер входа   | Вводит и редактирует данные. Не видит аналитику.       |

### 3.1 Первый запуск — bootstrap superadmin

`SUPERADMIN_ID` — единственное что хранится в `.env`. Это твой Telegram ID.
При первом `/start` от этого ID — запись автоматически создаётся в БД с ролью `superadmin`.

```env
SUPERADMIN_ID=123456789   # твой telegram_id, узнать у @userinfobot
```

### 3.2 Команды управления ролями (только superadmin)

```
/addowner @username    — выдать роль owner (владелец клуба)
/addadmin @username    — выдать роль admin (менеджер)
/removeuser @username  — полностью убрать доступ
/users                 — список всех пользователей с ролями
/myrole               — показать свою роль (доступно всем)
```

**Важно:** `@username` работает только если пользователь уже писал боту (его telegram_id есть в БД).
Если нет — бот отвечает: `"Пользователь не найден. Попроси его написать /start боту сначала."`.

### 3.3 Флоу передачи прав владельцу клуба

```
1. Владелец пишет боту /start
   → Бот: "Привет! У тебя нет доступа. Обратись к администратору."
   → Его telegram_id сохраняется в БД со статусом "pending"

2. Ты пишешь: /addowner @owner_username
   → Бот обновляет роль в БД
   → Владелец получает уведомление: "✅ Тебе выдан доступ Owner. Напиши /start"

3. Владелец пишет /start
   → Видит своё меню с аналитикой
```

### 3.4 Уведомление при выдаче роли

```
# Сообщение новому owner/admin:
✅ Доступ выдан

Роль: Owner
Бот: KIKI Analytics
Выдал: @superadmin_username

Напиши /start чтобы начать.
```

### 3.5 Команда /users — список пользователей

```
👥 Пользователи KIKI Bot

👑 Superadmin
• @your_username (ID: 123456789)

🏠 Owner
• @owner_username (ID: 987654321) — с 28 мая

👔 Admin (2)
• @admin1 (ID: 555444333) — с 28 мая
• @admin2 (ID: 666555444) — с 29 мая
```

---

## 4. Структура проекта

```
kiki_bot/
├── main.py                    # точка входа, регистрация роутеров
├── config.py                  # env-переменные (BOT_TOKEN, SUPERADMIN_ID, WEBAPP_URL)
├── scheduler.py               # APScheduler — hourly reports
│
├── bot/
│   ├── handlers/
│   │   ├── common.py          # /start, /myrole — для всех
│   │   ├── superadmin.py      # /addowner, /addadmin, /removeuser, /users
│   │   ├── admin.py           # /input, /edit, /status — только ADMIN + SUPERADMIN
│   │   └── owner.py           # /live, /night, /week, /month, /kpi, /logs — OWNER + SUPERADMIN
│   ├── middlewares/
│   │   └── auth.py            # проверка роли, добавляет data["role"] и data["user"]
│   ├── keyboards.py           # все InlineKeyboardMarkup
│   └── messages.py            # форматирование всех сообщений
│
├── services/
│   ├── stats_service.py       # occupancy, deviations, averages
│   ├── report_service.py      # night/week/month/kpi отчёты
│   ├── audit_service.py       # edit logs, уведомления
│   └── user_service.py        # управление ролями, поиск пользователей
│
├── repositories/
│   ├── stats_repo.py          # CRUD hourly_stats, club_nights
│   └── user_repo.py           # CRUD users
│
├── models/
│   └── db.py                  # SQLAlchemy models + engine + session
│
└── miniapp/
    └── index.html             # весь Mini App — один файл
```

---

## 5. База данных

### Нужна ли база данных?

**Да, обязательно.** Без БД невозможно:
- Хранить роли пользователей (superadmin/owner/admin)
- Считать historical averages и deviations
- Сравнивать текущую ночь с предыдущими пятницами
- Вести edit logs
- Строить аналитику по неделям и месяцам

**SQLite** — для MVP это буквально один файл `kiki.db` в папке проекта.
Ничего устанавливать не нужно, работает из коробки.
При переезде на PostgreSQL — меняется только строка `DB_URL` в `.env`.

### 5.1 Модели SQLAlchemy

```python
# models/db.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id          = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username    = Column(String(100))                         # @username без @
    full_name   = Column(String(200))                         # First Last
    role        = Column(String(12), nullable=False)          # "superadmin" | "owner" | "admin" | "pending"
    added_by    = Column(Integer, ForeignKey("users.id"), nullable=True)  # кто выдал роль
    created_at  = Column(DateTime, default=datetime.utcnow)
    role_set_at = Column(DateTime, default=datetime.utcnow)   # когда выдана роль

class ClubNight(Base):
    __tablename__ = "club_nights"
    id           = Column(Integer, primary_key=True)
    date         = Column(String(10), nullable=False, unique=True)  # "2025-05-30"
    day_of_week  = Column(String(3), nullable=False)                # "fri" | "sat" | "sun"
    opened_at    = Column(DateTime)
    closed_at    = Column(DateTime)                                  # NULL = ночь ещё идёт
    hourly_stats = relationship("HourlyStat", back_populates="night", order_by="HourlyStat.recorded_at")

class HourlyStat(Base):
    __tablename__ = "hourly_stats"
    id             = Column(Integer, primary_key=True)
    night_id       = Column(Integer, ForeignKey("club_nights.id"), nullable=False, index=True)
    recorded_at    = Column(DateTime, nullable=False)   # точное время, НЕ округлённое до часа
    is_manual_time = Column(Boolean, default=False)     # True если admin менял время вручную
    girls_entered  = Column(Integer, default=0)
    boys_entered   = Column(Integer, default=0)
    denied         = Column(Integer, default=0)
    left_count     = Column(Integer, default=0)
    created_by     = Column(Integer, ForeignKey("users.id"))
    created_at     = Column(DateTime, default=datetime.utcnow)
    night          = relationship("ClubNight", back_populates="hourly_stats")
    edit_logs      = relationship("EditLog", back_populates="stat")

class EditLog(Base):
    __tablename__ = "edit_logs"
    id          = Column(Integer, primary_key=True)
    stat_id     = Column(Integer, ForeignKey("hourly_stats.id"), nullable=False)
    field_name  = Column(String(50), nullable=False)    # "girls" | "boys" | "left" | "denied" | "time"
    old_value   = Column(Text)
    new_value   = Column(Text)
    edited_by   = Column(Integer, ForeignKey("users.id"))
    edited_at   = Column(DateTime, default=datetime.utcnow)
    stat        = relationship("HourlyStat", back_populates="edit_logs")
```

### 5.2 Инициализация

```python
DATABASE_URL = "sqlite+aiosqlite:///./kiki.db"
# Для PostgreSQL: "postgresql+asyncpg://user:password@localhost/kiki"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Создать superadmin если не существует
    from config import settings
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.telegram_id == settings.SUPERADMIN_ID)
        )
        if not result.scalar_one_or_none():
            session.add(User(
                telegram_id=settings.SUPERADMIN_ID,
                role="superadmin",
                full_name="Superadmin"
            ))
            await session.commit()

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

---

## 6. Auth Middleware

```python
# bot/middlewares/auth.py
# Добавляет в data["user"] объект User из БД (или None)
# Добавляет в data["role"] строку роли (или None)
# Если пользователь не найден — создаёт запись со статусом "pending"
# Superadmin видит все команды (admin + owner)

ROLE_PERMISSIONS = {
    "superadmin": ["all"],
    "owner":      ["owner_commands"],
    "admin":      ["admin_commands"],
    "pending":    [],
}
```

---

## 7. Конфигурация

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN:      str
    SUPERADMIN_ID:  int       # твой telegram_id — единственный хардкод
    WEBAPP_URL:     str       # URL хостинга miniapp/index.html
    DB_URL:         str = "sqlite+aiosqlite:///./kiki.db"

    class Config:
        env_file = ".env"

settings = Settings()
```

```env
# .env
BOT_TOKEN=7xxxxxxxxxx:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SUPERADMIN_ID=123456789
WEBAPP_URL=https://your-host.com/kiki
# DB_URL=postgresql+asyncpg://user:pass@localhost/kiki  # раскомментить для Postgres
```

**Узнать свой SUPERADMIN_ID:** написать @userinfobot в Telegram.

---

## 8. Ввод статистики (Admin + Superadmin)

### 8.1 Режим 1 — FSM (пошаговый)

Кнопка "📊 Ввести данные" в главном меню.

```python
class InputStats(StatesGroup):
    girls   = State()
    boys    = State()
    left    = State()
    denied  = State()
    confirm = State()
    fix_time = State()  # опциональный шаг если нажали "Изменить время"
```

**Поток:**
1. "Сколько девушек вошло за этот час?"
2. "Сколько парней?"
3. "Сколько человек ушло?"
4. "Сколько отказано на входе?"
5. → Карточка подтверждения с inline-кнопками

**Карточка подтверждения:**
```
📊 Проверь данные

🕐 Время: 02:14 (авто)
👧 Девушки: 45
👦 Парни: 32
🚪 Ушло: 8
🚫 Отказано: 5

📍 Внутри сейчас: 69
⚖️ Соотношение: 58% / 42%
🎯 FC конверсия: 94%
```

Кнопки: `[✅ Сохранить]  [🕐 Изменить время]  [❌ Отмена]`

**При нажатии "Изменить время":**
```
Введи время в формате ЧЧ:ММ
Например: 01:47

(текущее авто-время: 02:14)
```
Любое время принимается — округления нет. `is_manual_time = True`.

### 8.2 Режим 2 — одной строкой

```
/input 45 32 8 5
# порядок: girls boys left denied
```
Бот парсит → показывает ту же карточку подтверждения.
Если аргументов меньше 4 — уточняет недостающие через FSM.

### 8.3 Режим 3 — Mini App

Кнопка "🌐 Открыть приложение" → `WebAppButton` → `WEBAPP_URL`.
Mini App отправляет через `Telegram.WebApp.sendData(JSON.stringify({...}))`.
Бот принимает через `web_app_data` handler → показывает подтверждение → сохраняет.

### 8.4 Редактирование

```
/edit <stat_id> <field> <value>
# Поля: girls, boys, left, denied, time
# Примеры:
/edit 42 girls 50
/edit 42 time 01:47
```

При редактировании:
1. Запись в `edit_logs`
2. Уведомление всем owner + superadmin:
```
⚠️ Изменение данных

👤 Admin: @username
📋 Запись #42 · 02:14, Пт 30 мая
📝 Поле: girls
🔄 Было: 45 → Стало: 50
```

---

## 9. Live Occupancy

```python
inside_now = SUM(girls_entered + boys_entered) - SUM(left_count)
# только за текущую ночь (closed_at IS NULL)
```

**Команда /live:**
```
🟢 KIKI — Live сейчас

👥 Внутри: 137 чел
📊 Загрузка: ██████████░░░░░ 68%

👧 Девушки: 89  👦 Парни: 48
🚪 Ушло: 24    🚫 Отказано: 12

🔥 Пик: 01:00 — 152 чел
📈 vs прошлая Пт: +8%
🕐 Обновлено: 02:14
```

---

## 10. Аналитика (Owner + Superadmin)

### /night
```
📊 Итог ночи · Пт 30 мая

Вошло всего:   213
Пик:           152 чел (01:00)
Внутри сейчас: 137

👧 Девушки: 65%  👦 Парни: 35%
🎯 FC конверсия: 93%
⏱ Avg occupancy: 104 чел

Почасовой трафик:
23:00  ████░░░░    42 (+5%)
00:00  ████████    88 (+12%)
01:00  ██████████ 152 (+8%)
02:00  ████████   137 (сейчас)

📈 vs прошлая Пт: +11%
```

### /week
```
📅 Неделя · 24–30 мая

Ночей: 3  |  Посетителей: 648
Лучшая ночь: Сб 24 мая — 216 чел

Пт 24  ████████   178
Сб 25  ██████████ 216
Вс 26  ███████    154

Avg FC: 91%  |  📈 vs прошлая неделя: +14%
```

### /month
```
📆 Май 2025

Ночей: 12  |  Посетителей: 2 410
Avg за ночь: 201  |  Лучшая: Сб 24 — 216

📈 vs апрель: +7%  |  📈 рост 3 мес: +22%
```

### /kpi
```
🎯 KPI · Май 2025

FC конверсия:     92%  (цель 90%) ✅
Girls/Boys ratio:  65/35           ✅
Avg occupancy:    54%  (цель 60%) ⚠️
Occupancy growth: +7%  (цель +10%) ⚠️
Лучшая ночь:      Сб 24 мая · 216 чел
Пиковый час:      01:00 — 02:00
```

### /logs
```
📝 Последние изменения

1. 02:31 · @admin1 → girls
   Запись #42 · Было 38 → Стало 45

2. 01:15 · @admin1 → time
   Запись #38 · Было 01:00 → Стало 01:14
```

---

## 11. Автоматические отчёты (APScheduler)

Расписание: `cron(hour='23,0,1,2,3,4,5', minute=5)` — каждый час в 5 минут.

```python
# scheduler.py
async def hourly_report(bot: Bot):
    night = await get_current_night()          # ClubNight с closed_at IS NULL
    if not night:
        return
    report = await build_hourly_report(night)
    owners = await get_users_by_roles(["owner", "superadmin"])
    for user in owners:
        await bot.send_message(user.telegram_id, report)
```

**Формат:**
```
⏱ Hourly Report · 02:00

Этот час: +18 вошло · 8 ушло
Внутри:   137 чел

vs ср Пт 02:00:       +12% 📈
vs прошлая Пт 02:00:  +8%  📈
```

---

## 12. Mini App (miniapp/index.html)

**Один HTML файл.** Без фреймворков, без npm, без сборки.
Chart.js подключается через CDN: `https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js`

### 12.1 Структура

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>KIKI Analytics</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
  <style>/* ВЕСЬ CSS */</style>
</head>
<body>
  <div id="app">
    <header class="glass-strong">...</header>
    <main id="screens">...</main>
    <nav class="glass nav-bar">...</nav>
  </div>
  <div id="toast" class="glass toast">...</div>
  <script>/* ВЕСЬ JS */</script>
</body>
</html>
```

### 12.2 Инициализация Telegram WebApp

```javascript
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();                               // раскрыть на весь экран
tg.setHeaderColor('#0A0A0A');
tg.setBackgroundColor('#0A0A0A');
```

### 12.3 Навигация (4 вкладки, нижний бар)

```
[📥 Ввод]  [🟢 Live]  [🌙 Ночь]  [📅 Неделя]
```
Нижний бар: `position: sticky; bottom: 0; padding-bottom: env(safe-area-inset-bottom)` — учёт нотча iPhone.

### 12.4 Экран "Ввод"

**1. Блок времени (glass card):**
- Показывает текущее время автоматически (`new Date()`)
- Кнопка "Изменить" → раскрывает `<input type="time">` нативный
- Бейдж "авто" (оранжевый) / "изменено" (жёлтый `--color-warning`)
- Кнопка "Сбросить" → возвращает `new Date()`
- Время обновляется каждые 30 секунд пока не тронули вручную

**2. Поля ввода 2×2:**
- `font-size: 28px`, `text-align: center`, `type="number"`, `inputmode="numeric"`
- При фокусе: `border-color: #FF6B00`
- Лейблы под полями: 11px, rgba(255,255,255,0.5)

**3. Live-превью** (пересчёт `oninput`):
- Внутри сейчас = (girls + boys) - left
- Соотношение = girls/(girls+boys) * 100
- FC конверсия = (girls+boys)/(girls+boys+denied) * 100

**4. Кнопка сохранить:**
```javascript
// При нажатии:
tg.sendData(JSON.stringify({
  action: "save_stats",
  girls: 45, boys: 32, left: 8, denied: 5,
  recorded_at: "2025-05-30T02:14:00",  // ISO format
  is_manual_time: false
}));
```

### 12.5 Экран "Live"

- Hero число (occupancy) + прогресс-бар оранжевый
- 4 мини-карточки 2×2
- Bar chart (Chart.js): часы по X, люди по Y
  - Текущий час: `#FF6B00`
  - Прошлые: `rgba(255,107,0,0.25)`
  - Фон графика: прозрачный
  - Gridlines: `rgba(255,255,255,0.06)`
  - Текст осей: `rgba(255,255,255,0.4)`

### 12.6 Экран "Ночь"

- 4 stat-карточки 2×2 (итоги)
- Bar chart "Вошло vs Ушло": два датасета
  - Вошло: `#FF6B00`
  - Ушло: `rgba(255,255,255,0.2)`
- Stacked bar "Соотношение Ж/М":
  - Девушки: `#FF6B00`
  - Парни: `rgba(255,255,255,0.15)`

### 12.7 Экран "Неделя"

Три под-вкладки: `[Неделя] [Месяц] [KPI]`

- **Неделя:** Bar chart ночей, текущая = `#FF6B00`, остальные = `rgba(255,107,0,0.3)`
- **Месяц:** Line chart, `borderColor: #FF6B00`, `backgroundColor: rgba(255,107,0,0.1)`, `tension: 0.4`, fill: true
- **KPI:** Horizontal bar chart Факт vs Цель
  - Факт: `#FF6B00`
  - Цель: `rgba(255,255,255,0.15)`

### 12.8 Toast-уведомления

```css
.toast {
  position: fixed;
  bottom: calc(70px + env(safe-area-inset-bottom));
  left: 16px; right: 16px;
  padding: 12px 16px;
  transform: translateY(120%);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.toast.show { transform: translateY(0); }
```

```javascript
function showToast(text) {
  toast.textContent = text;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}
// После сохранения:
showToast('✓  Данные сохранены · 02:14');
```

---

## 13. Главное меню бота

### Меню для Admin:
```
Привет, @username 👋

📊 Ввести данные     🌐 Открыть Mini App
/input               /status
```

### Меню для Owner:
```
Привет, @username 👋

📊 /live    🌙 /night    📅 /week
📆 /month   🎯 /kpi      📝 /logs
```

### Меню для Superadmin:
```
Привет, @username 👋  [👑 Superadmin]

— Admin команды —
📊 /input   🌐 Mini App   /status

— Owner команды —
📊 /live    🌙 /night    📅 /week
📆 /month   🎯 /kpi      📝 /logs

— Управление —
👥 /users   /addowner   /addadmin   /removeuser
```

---

## 14. Зависимости

```
pip install aiogram sqlalchemy aiosqlite apscheduler pydantic-settings
```

```toml
# pyproject.toml
[tool.poetry.dependencies]
python            = "^3.11"
aiogram           = "^3.7"
sqlalchemy        = "^2.0"
aiosqlite         = "^0.20"
apscheduler       = "^3.10"
pydantic-settings = "^2.0"
```

---

## 15. Запуск

```python
# main.py
import asyncio
from aiogram import Bot, Dispatcher
from bot.handlers.common     import router as common_router
from bot.handlers.superadmin import router as superadmin_router
from bot.handlers.admin      import router as admin_router
from bot.handlers.owner      import router as owner_router
from bot.middlewares.auth    import AuthMiddleware
from models.db               import init_db
from scheduler               import start_scheduler
from config                  import settings

async def main():
    await init_db()          # создаёт таблицы + superadmin запись
    bot = Bot(token=settings.BOT_TOKEN)
    dp  = Dispatcher()
    dp.message.middleware(AuthMiddleware())
    dp.include_router(common_router)      # /start, /myrole
    dp.include_router(superadmin_router)  # /addowner, /addadmin, /users...
    dp.include_router(admin_router)       # /input, /edit, /status
    dp.include_router(owner_router)       # /live, /night, /week, /kpi, /logs
    start_scheduler(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
python main.py
```

---

## 16. Порядок разработки

1. `models/db.py` — все модели + `init_db()` с созданием superadmin
2. `config.py` + `.env`
3. `repositories/user_repo.py` — CRUD пользователей
4. `repositories/stats_repo.py` — CRUD статистики
5. `bot/middlewares/auth.py` — роли и permissions
6. `bot/handlers/common.py` — `/start`, `/myrole`
7. `bot/handlers/superadmin.py` — `/addowner`, `/addadmin`, `/removeuser`, `/users`
8. `bot/handlers/admin.py` — `/input` (quick + FSM) + `/edit`
9. `services/stats_service.py` — `get_live_occupancy()`
10. `bot/handlers/owner.py` — `/live`
11. `services/report_service.py` — `/night`, `/week`, `/month`, `/kpi`
12. `scheduler.py` — hourly reports
13. `miniapp/index.html` — полный Mini App одним файлом

---

## 17. Важные детали реализации

### Определение текущей ночи

```python
from datetime import datetime, timedelta

def get_night_date(dt: datetime) -> str:
    """
    23:00 пятницы и 03:00 субботы = одна ночь.
    Если время 00:00–06:00 — относится к предыдущему дню.
    """
    if dt.hour < 6:
        return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")
```

### Deviation formula

```python
def calc_deviation(current: float, historical_avg: float) -> float:
    if historical_avg == 0:
        return 0.0
    return round((current / historical_avg - 1) * 100, 1)
```

### Время записи

- `recorded_at` хранится как точный `datetime`, **никогда не округляется**
- `is_manual_time = True` если admin менял вручную
- Для почасовой аналитики: группировка по `strftime('%H', recorded_at)`
- При сравнении "тот же час той же недели": WHERE `strftime('%H', recorded_at) = '02'` AND `day_of_week = 'fri'`

### Safe area для iPhone

```css
body {
  padding-bottom: env(safe-area-inset-bottom);
}
.nav-bar {
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
}
```

---

## 18. MVP ограничения

- Запуск локально, без Docker
- Без Redis
- Mini App — один HTML файл, хостинг на GitHub Pages или Netlify (бесплатно)
- SQLite → PostgreSQL: только замена `DB_URL` в `.env`
- Без графиков в боте — только текст и ASCII-прогрессбары; графики только в Mini App

---

*PRD версия 2.0 · KIKI Night Club Analytics · с системой ролей superadmin/owner/admin*

---

## 19. Экран "Команда" в Mini App (только superadmin)

Пятая вкладка в навбаре — видна **только** если `tg.initDataUnsafe.user.id === SUPERADMIN_ID`.
Все остальные роли эту вкладку не видят вообще.

### 19.1 Структура экрана

**Блок добавления пользователя (сверху):**
```
┌─────────────────────────────────────────┐
│  Добавить пользователя                  │
│                                         │
│  [@username или Telegram ID_________]   │
│                                         │
│  [👑 Owner]  [👤 Admin]                 │  ← выбор роли, одна активна
│                                         │
│  [         Добавить          ]          │  ← оранжевая кнопка
└─────────────────────────────────────────┘
```

Поле принимает:
- `@username` — если пользователь уже писал боту
- числовой `telegram_id` — работает всегда

После нажатия "Добавить":
1. Mini App отправляет запрос на бэкенд: `POST /api/users {username, role}`
2. Бэкенд находит пользователя в БД, обновляет роль
3. Пользователь получает уведомление в бот
4. В Mini App появляется toast: `"✓ @username добавлен как Owner"`

Если пользователь не найден в БД (ещё не писал `/start`):
- Toast с предупреждением: `"Попроси @username написать /start боту"`

**Секция "Superadmin":**
- Только твоя карточка, без кнопок управления (нельзя удалить себя)
- Аватар: оранжевый с инициалами

**Секция "Owner":**
- Карточки всех owner
- Кнопка удаления (иконка корзины) → confirm sheet снизу

**Секция "Admin (N)":**
- Карточки всех admin
- Кнопка стрелки вверх → повысить до owner
- Кнопка корзины → удалить

**Секция "Ожидают доступа (N)":**
- Пользователи написавшие `/start` но без роли (`pending`)
- Кнопка галочки → выдать admin
- Кнопка крестика → отклонить (остаётся в БД со статусом `pending`)
- Бейдж "N мин назад" → время когда написал `/start`

### 19.2 Карточка пользователя

```
┌────────────────────────────────────────────┐
│  [MK]  @mikhail_k              [owner]  [🗑] │
│        Owner · с 28 мая                     │
└────────────────────────────────────────────┘
```

Аватар = инициалы из full_name или первые 2 буквы username.
Цвет аватара:
- `superadmin` → оранжевый насыщенный
- `owner` → оранжевый прозрачный `rgba(255,107,0,0.2)`
- `admin` → белый прозрачный `rgba(255,255,255,0.08)`
- `pending` → серый пунктирный бордер, знак вопроса

### 19.3 Confirm sheet (удаление)

Появляется снизу как bottom sheet поверх затемнённого экрана:
```
┌────────────────────────────────────────┐
│  Удалить @mikhail_k?                   │
│  Пользователь потеряет доступ к боту   │
│                                        │
│  [Отмена]          [Удалить]           │
│               ↑ красная кнопка        │
└────────────────────────────────────────┘
```

### 19.4 API эндпоинты для Mini App

Бэкенд должен предоставить простой HTTP API (aiohttp или встроенный в aiogram webhook):

```
GET  /api/users              → список всех пользователей с ролями
POST /api/users/role         → {telegram_id | username, role} → обновить роль
POST /api/users/remove       → {telegram_id | username} → удалить доступ
GET  /api/users/pending      → список pending пользователей
```

Все запросы валидируются по `initData` из Telegram WebApp:
```javascript
// В каждом запросе Mini App передаёт:
headers: { 'X-Telegram-Init-Data': tg.initData }
// Бэкенд валидирует подпись и проверяет что user.id === SUPERADMIN_ID
```

### 19.5 Уведомление пользователю при выдаче роли

Бот автоматически отправляет сообщение:
```
✅ Тебе выдан доступ

Роль: Admin
Бот: KIKI Analytics

Напиши /start чтобы начать.
```

### 19.6 Навбар Mini App (итого 5 вкладок)

```
[📥 Ввод]  [🟢 Live]  [🌙 Ночь]  [📅 Неделя]  [👥 Команда*]
                                               * только superadmin
```

Вкладка "Команда" рендерится условно:
```javascript
const tg = window.Telegram.WebApp;
const userId = tg.initDataUnsafe?.user?.id;
if (userId === SUPERADMIN_ID) {
  document.getElementById('nav-team').style.display = 'flex';
}
```

`SUPERADMIN_ID` передаётся в Mini App через URL параметр при открытии,
или через отдельный `/api/me` эндпоинт который возвращает роль текущего пользователя.

