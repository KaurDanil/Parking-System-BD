# Быстрый старт - Smart Private Parking

## Шаг 1: Установка Docker

Убедитесь, что у вас установлены:
- **Docker Desktop** (для Windows/Mac) или **Docker Engine** (для Linux)
- **Docker Compose** (обычно входит в Docker Desktop)

Проверьте установку:
```bash
docker --version
docker-compose --version
```

## Шаг 2: Запуск проекта

### Вариант A: Запуск через Docker Compose (рекомендуется)

1. **Откройте терминал в папке проекта** (`db-MAI`)

2. **Запустите контейнеры**:
```bash
docker-compose up -d
```

Эта команда:
- Скачает образы PostgreSQL и Python (если нужно)
- Создаст и запустит контейнеры
- Автоматически создаст базу данных и применит схему из `database/init.sql`
- Запустит FastAPI backend на порту 8000

3. **Проверьте статус**:
```bash
docker-compose ps
```

Должны быть запущены 2 сервиса:
- `smart_parking_db` (PostgreSQL)
- `smart_parking_backend` (FastAPI)

4. **Проверьте логи** (если что-то не работает):
```bash
# Логи всех сервисов
docker-compose logs

# Логи только backend
docker-compose logs backend

# Логи только БД
docker-compose logs postgres
```

5. **Откройте Swagger документацию**:
```
http://localhost:8000/docs
```

Или просто в браузере перейдите по адресу: `http://localhost:8000/docs`

## Шаг 3: Генерация тестовых данных

После запуска контейнеров, сгенерируйте тестовые данные:

### Вариант A: Через Docker (рекомендуется)

```bash
docker-compose exec backend python scripts/generate_test_data.py
```

### Вариант B: Локально (если Python установлен)

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите скрипт:
```bash
python scripts/generate_test_data.py
```

**Важно**: Убедитесь, что переменная окружения `DATABASE_URL` указывает на правильный адрес:
- Для Docker: `postgresql://parking_user:parking_pass@localhost:5432/smart_parking`
- Для локального запуска: установите в `.env` файле