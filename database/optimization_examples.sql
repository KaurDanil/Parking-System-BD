-- примеры оптимизации запросов

-- 1. поиск сессий по авто и дате
-- до индекса: последовательное сканирование
EXPLAIN ANALYZE
SELECT ps.*, c.plate_number, u.phone
FROM parking_sessions ps
JOIN cars c ON c.id = ps.car_id
JOIN users u ON u.id = c.user_id
WHERE ps.car_id = 'uuid' AND ps.entry_time >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY ps.entry_time DESC;
-- после индекса idx_parking_sessions_car_entry: сканирование индекса

-- 2. транзакции кошелька
-- до индекса: медленно
EXPLAIN ANALYZE
SELECT * FROM wallet_transactions
WHERE wallet_id = 'uuid' AND created_at >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY created_at DESC;
-- после индекса idx_wallet_transactions_wallet_created: быстро

-- 3. поиск авто по номеру
EXPLAIN ANALYZE
SELECT * FROM cars WHERE plate_number = 'А123БВ777';
-- ускоряется индексом idx_cars_plate_number

-- 4. сложная аналитика (выручка по дням)
EXPLAIN ANALYZE
SELECT DATE(ps.entry_time) as date, COUNT(*) as cnt, SUM(ps.total_cost) as rev
FROM parking_sessions ps
WHERE ps.status = 'completed' AND ps.entry_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(ps.entry_time) ORDER BY date DESC;
-- использует индексы по entry_time и status

-- 5. топ пользователей по расходам
EXPLAIN ANALYZE
SELECT u.phone, COUNT(ps.id), SUM(ps.total_cost) as spent
FROM users u
JOIN cars c ON c.user_id = u.id
JOIN parking_sessions ps ON ps.car_id = c.id
WHERE ps.status = 'completed' AND ps.entry_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY u.id, u.phone ORDER BY spent DESC LIMIT 10;
-- использует индексы соединений и внешние ключи

-- полезные дополнительные индексы

-- активные сессии
CREATE INDEX IF NOT EXISTS idx_parking_sessions_status_entry 
ON parking_sessions(status, entry_time) WHERE status = 'active';

-- завершенные сессии за период
CREATE INDEX IF NOT EXISTS idx_parking_sessions_date_status 
ON parking_sessions(entry_time, status) WHERE status = 'completed';

-- журнал въездов
CREATE INDEX IF NOT EXISTS idx_entry_logs_time_result 
ON entry_logs(attempt_time, result);

-- должники (отрицательный баланс)
CREATE INDEX IF NOT EXISTS idx_wallets_balance 
ON wallets(balance) WHERE balance < 0;

-- советы

-- 1. частичные индексы (меньше места, быстрее поиск)
CREATE INDEX idx_active_sessions ON parking_sessions(car_id, entry_time) WHERE status = 'active';

-- 2. обновляйте статистику
ANALYZE parking_sessions;

-- 3. проверяйте использование индексов
SELECT indexname, idx_scan FROM pg_stat_user_indexes WHERE schemaname = 'public' ORDER BY idx_scan DESC;

-- 4. проверяйте размер таблиц
SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
