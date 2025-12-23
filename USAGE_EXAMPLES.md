# Примеры использования API

## Базовые операции

### 1. Регистрация пользователя

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+79991234567",
    "email": "user@example.com",
    "password": "secure_password123"
  }'
```

Ответ:
```json
{
  "message": "User registered successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 2. Вход в систему

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+79991234567",
    "password": "secure_password123"
  }'
```

Ответ:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Добавление автомобиля

```bash
curl -X POST "http://localhost:8000/api/cars" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "plate_number": "А123БВ777",
    "model": "Toyota Camry 2020"
  }'
```

### 4. Пополнение кошелька

```bash
curl -X POST "http://localhost:8000/api/wallet/topup" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "amount": 1000.00,
    "comment": "Пополнение через банковскую карту"
  }'
```

Ответ:
```json
{
  "message": "Wallet topped up successfully",
  "new_balance": 1000.0,
  "transaction_id": "660e8400-e29b-41d4-a716-446655440000"
}
```

### 5. Въезд на парковку

Сначала получите ID ворот:
```bash
curl "http://localhost:8000/api/admin/gates" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Затем выполните въезд:
```bash
curl -X POST "http://localhost:8000/api/parking/entry" \
  -H "Content-Type: application/json" \
  -d '{
    "plate_number": "А123БВ777",
    "gate_id": "gate-uuid-from-previous-request"
  }'
```

Ответ при успехе:
```json
{
  "message": "Entry allowed",
  "session_id": "770e8400-e29b-41d4-a716-446655440000",
  "car_id": "880e8400-e29b-41d4-a716-446655440000",
  "balance": 950.0
}
```

### 6. Выезд с парковки

```bash
curl -X POST "http://localhost:8000/api/parking/exit" \
  -H "Content-Type: application/json" \
  -d '{
    "plate_number": "А123БВ777",
    "gate_id": "exit-gate-uuid"
  }'
```

Ответ:
```json
{
  "message": "Exit processed. Cost: 50.00, New balance: 900.00",
  "session_id": "770e8400-e29b-41d4-a716-446655440000",
  "cost": 50.0
}
```

## Административные запросы

### Статистика загрузки парковки

```bash
curl "http://localhost:8000/api/admin/stats/occupancy" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

Ответ:
```json
[
  {
    "zone_id": "zone-uuid",
    "zone_name": "Underground -1",
    "total_spots": 50,
    "occupied_spots": 35,
    "free_spots": 15,
    "occupancy_percent": 70.0
  }
]
```

### Статистика выручки

```bash
curl "http://localhost:8000/api/admin/stats/revenue?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Топ пользователей

```bash
curl "http://localhost:8000/api/admin/stats/top-users?limit=10" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Пользователи с долгами

```bash
curl "http://localhost:8000/api/admin/users/debtors" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Подозрительные сессии (дольше 24 часов)

```bash
curl "http://localhost:8000/api/admin/stats/suspicious-sessions?max_hours=24" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Пиковые часы

```bash
curl "http://localhost:8000/api/admin/stats/peak-hours?days=30" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## SQL запросы для аналитики

### Подключение к БД

```bash
docker-compose exec postgres psql -U parking_user -d smart_parking
```

### Примеры запросов

#### Топ пользователей по количеству сессий

```sql
SELECT 
    u.phone,
    COUNT(ps.id) as sessions_count,
    SUM(ps.total_cost) as total_spent
FROM users u
JOIN cars c ON c.user_id = u.id
LEFT JOIN parking_sessions ps ON ps.car_id = c.id AND ps.status = 'completed'
GROUP BY u.id, u.phone
ORDER BY sessions_count DESC
LIMIT 10;
```

#### Выручка по дням

```sql
SELECT 
    DATE(entry_time) as date,
    COUNT(*) as sessions,
    SUM(total_cost) as revenue
FROM parking_sessions
WHERE status = 'completed'
    AND entry_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(entry_time)
ORDER BY date DESC;
```

#### Средняя длительность сессий по тарифам

```sql
SELECT 
    t.name,
    AVG(EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 60) as avg_minutes
FROM parking_sessions ps
JOIN tariffs t ON t.id = ps.tariff_id
WHERE ps.status = 'completed'
GROUP BY t.id, t.name;
```

Все примеры запросов находятся в файле `database/analytics_queries.sql`.

## Python примеры

### Использование API через Python

```python
import requests

BASE_URL = "http://localhost:8000"

# Регистрация
response = requests.post(
    f"{BASE_URL}/api/auth/register",
    json={
        "phone": "+79991234567",
        "email": "user@example.com",
        "password": "password123"
    }
)
print(response.json())

# Вход
response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={
        "phone": "+79991234567",
        "password": "password123"
    }
)
token = response.json()["access_token"]

# Добавление автомобиля
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    f"{BASE_URL}/api/cars",
    headers=headers,
    json={
        "plate_number": "А123БВ777",
        "model": "Toyota Camry"
    }
)
print(response.json())

# Пополнение кошелька
response = requests.post(
    f"{BASE_URL}/api/wallet/topup",
    headers=headers,
    json={
        "amount": 1000.00,
        "comment": "Top-up"
    }
)
print(response.json())

# Въезд
response = requests.post(
    f"{BASE_URL}/api/parking/entry",
    json={
        "plate_number": "А123БВ777",
        "gate_id": "gate-uuid"
    }
)
print(response.json())

# Выезд
response = requests.post(
    f"{BASE_URL}/api/parking/exit",
    json={
        "plate_number": "А123БВ777",
        "gate_id": "exit-gate-uuid"
    }
)
print(response.json())
```
