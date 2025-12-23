# Smart Private Parking System

Backend-приложение для системы управления парковкой с автоматической оплатой через внутренний кошелёк.

## Описание

Система позволяет:
- Регистрировать пользователей и автомобили
- Управлять въездом/выездом через API
- Автоматически списывать стоимость парковки с кошелька пользователя
- Поддерживать различные тарифы по зонам и уровням доступа
- Вести аналитику загрузки и выручки

## Технологии

- **Backend**: Python 3.11 + FastAPI
- **База данных**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Контейнеризация**: Docker Compose
- **Автодокументация**: Swagger/OpenAPI (`/docs`)

## Быстрый старт

### Запуск через Docker

```bash
# Запуск контейнеров
docker-compose up -d

# Генерация тестовых данных
docker-compose exec backend python scripts/generate_test_data.py

# Открыть документацию API
# http://localhost:8000/docs
```

**Порты:**
- FastAPI: `http://localhost:8000`
- PostgreSQL: `localhost:5435` (внешний порт)

### Локальный запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка БД (PostgreSQL должен быть запущен на порту 5435)
psql -U parking_user -d smart_parking -f database/init.sql

# Запуск приложения
uvicorn app.main:app --reload
```

## Структура базы данных

**13 основных таблиц:**
- `users`, `wallets`, `cars` — пользователи, кошельки, автомобили
- `access_levels`, `user_access_levels` — уровни доступа (N:M)
- `parking_zones`, `parking_spots`, `tariffs` — зоны, места, тарифы
- `gates` — ворота въезда/выезда
- `parking_sessions` — сессии парковки
- `wallet_transactions` — транзакции по кошелькам
- `entry_logs`, `audit_logs` — логи операций

**SQL функции:**
- `check_entry_allowed()` — проверка возможности въезда
- `calculate_parking_cost()` — расчёт стоимости парковки
- `process_exit()` — обработка выезда (списание средств в транзакции)

**Представления (VIEW):**
- `parking_occupancy` — текущая загрузка по зонам
- `user_parking_history` — история парковки
- `revenue_analytics` — аналитика выручки

## API Endpoints

### Аутентификация
- `POST /api/auth/register` — регистрация
- `POST /api/auth/login` — вход (OAuth2, username=phone)

### Основные операции
- `GET /api/me` — текущий пользователь
- `POST /api/cars` — добавить автомобиль
- `GET /api/cars` — список автомобилей
- `GET /api/wallet` — информация о кошельке
- `POST /api/wallet/topup` — пополнить кошелёк

### Парковка
- `POST /api/parking/entry` — обработка въезда (проверка баланса и создание сессии)
- `POST /api/parking/exit` — обработка выезда (расчёт и списание стоимости)
- `GET /api/parking/sessions/active` — активные сессии

### Администрирование
- `GET /api/admin/stats/occupancy` — статистика загрузки
- `GET /api/admin/stats/revenue` — статистика выручки
- `GET /api/admin/users/debtors` — пользователи с отрицательным балансом
- `GET /api/admin/stats/top-users` — топ пользователей
- `GET /api/admin/stats/peak-hours` — пиковые часы

### Управление данными (CRUD)
- `/api/access-levels` — уровни доступа
- `/api/user-access-levels` — назначение уровней
- `/api/parking-zones` — зоны парковки
- `/api/parking-spots` — места парковки
- `/api/tariffs` — тарифы
- `/api/gates` — ворота
- `/api/parking-sessions` — сессии парковки
- `/api/wallet-transactions` — транзакции
- `/api/entry-logs` — логи въезда
- `/api/audit-logs` — аудит-логи

### Пакетный импорт
- `POST /api/batch/cars` — массовое добавление автомобилей

Полная документация доступна в Swagger UI: `http://localhost:8000/docs`


## Особенности реализации

- **Транзакционность**: Выезд и списание выполняются атомарно через SQL функцию `process_exit()`
- **Проверка баланса**: При въезде проверяется минимальный баланс через `check_entry_allowed()`
- **Расчёт стоимости**: Учитываются бесплатные минуты и тарифы по уровням доступа
- **Аудит**: Все операции логируются в `entry_logs` и `audit_logs`
- **Индексы**: Оптимизированы запросы по номеру автомобиля, времени сессий, транзакциям

## Дополнительные материалы

- `database/analytics_queries.sql` — примеры аналитических запросов
- `database/optimization_examples.sql` — примеры оптимизации
- `QUICK_START.md` — подробная инструкция по запуску

## Команды управления

```bash
# Остановка контейнеров
docker-compose down

# Остановка с удалением данных БД
docker-compose down -v

# Просмотр логов
docker-compose logs -f backend

# Подключение к БД
docker-compose exec postgres psql -U parking_user -d smart_parking
```

---

