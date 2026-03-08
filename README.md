# Фоновая репликация баз данных

## Описание проекта

ETL-пайплайн для репликации данных между гетерогенными базами данных (PostgreSQL и MongoDB) в фоновом режиме. Служит для аналитики, отказоустойчивости, экспериментов и масштабирования системы без нагрузки на основную БД.

## Архитектура

### Компоненты

- **PostgreSQL 15** — реляционная БД-источник (мастер)
- **MongoDB 7** — NoSQL БД-приемник для репликации
- **Sync Service** — Python-приложение для синхронизации данных

### Структура данных

Реляционная база содержит таблицы:

- `customers` — клиенты (id, name, email, created_at, deleted_at)
- `products` — товары (id, name, price, created_at, deleted_at)
- `orders` — заказы (id, customer_id, status, created_at, updated_at, deleted_at)
- `order_products` — связь многие-ко-многим между заказами и товарами (order_id, product_id, quantity)

## Быстрый старт

### Требования

- Docker и Docker Compose
- Файл `.env` с переменными окружения

### Установка

1. **Подготовить `.env` файл** в корне проекта:

```
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=shop_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

MONGO_HOST=mongo
MONGO_PORT=27017
MONGO_DB=shop_replica

BATCH_SIZE=5000
SYNC_INTERVAL=60
```

2. **Запустить сервисы**:

```bash
docker compose down -v
docker compose build --no-cache
docker compose up
```

3. **Проверить логи**:

```bash
docker compose logs -f sync
```

Сервис начнёт репликацию. Каждые 60 секунд (SYNC_INTERVAL) он синхронизирует изменённые данные из PostgreSQL в MongoDB.

## Реализованные функции

### Основной функционал

- [x] Двухконтейнерная архитектура (PostgreSQL + MongoDB)
- [x] Фоновая синхронизация по расписанию (SYNC_INTERVAL)
- [x] Преобразование структуры данных (Decimal → float)
- [x] Идемпотентность операций (upsert, ON CONFLICT)

### Дополнительные задания

- [x] **Третья таблица и связь многие-ко-многим** — добавлены `products` и `order_products` с M:N связью
- [x] **Конфигурация через .env** — все пароли и параметры вынесены в переменные окружения
- [x] **Отслеживание удаления** — поле `deleted_at` синхронизируется и используется в WHERE условиях
- [x] **Идемпотентность** — использованы `ON CONFLICT` в SQL и `upsert=True` в MongoDB, повторный запуск не создаёт дубликаты

## Технические детали

### Синхронизация

- Запросы фильтруют только изменённые записи (по `created_at` / `updated_at` / `deleted_at`)
- Данные обрабатываются батчами по 5000 записей
- Использует bulk write операции для оптимальной производительности

### Обработка ошибок

- Валидация всех обязательных переменных окружения при старте
- Проверка доступности PostgreSQL перед синхронизацией
- Граничная обработка исключений с логированием

## Мониторинг

Все события логируются с меткой времени и уровнем:

```
2026-03-08 10:30:45 [INFO] Sync worker started
2026-03-08 10:30:45 [INFO] Last sync time: 1970-01-01 00:00:00
2026-03-08 10:30:45 [INFO] Starting replication for table customers...
2026-03-08 10:30:46 [INFO] Replicated 1250 rows for customers
```

## Остановка и очистка

```bash
# Остановить контейнеры
docker compose down

# Остановить контейнеры и удалить volumes
docker compose down -v
```
