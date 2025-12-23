-- Аналитика по парковке

-- Нагрузка по часам (последние 30 дней)
SELECT 
    EXTRACT(HOUR FROM entry_time) as hour,
    COUNT(*) as entries_count,
    COUNT(DISTINCT car_id) as unique_cars
FROM parking_sessions
WHERE entry_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY EXTRACT(HOUR FROM entry_time)
ORDER BY entries_count DESC;

-- Нагрузка по дням + выручка (только завершённые, 30 дней)
SELECT 
    DATE(entry_time) as date,
    COUNT(*) as entries_count,
    COUNT(DISTINCT car_id) as unique_cars,
    SUM(total_cost) as daily_revenue
FROM parking_sessions
WHERE entry_time >= CURRENT_DATE - INTERVAL '30 days'
  AND status = 'completed'
GROUP BY DATE(entry_time)
ORDER BY entries_count DESC
LIMIT 10;

-- Выручка по тарифам и зонам (30 дней)
SELECT 
    t.name as tariff_name,
    z.name as zone_name,
    COUNT(ps.id) as sessions_count,
    SUM(ps.total_cost) as total_revenue,
    AVG(ps.total_cost) as avg_session_cost,
    MIN(ps.total_cost) as min_cost,
    MAX(ps.total_cost) as max_cost
FROM parking_sessions ps
JOIN tariffs t ON t.id = ps.tariff_id
LEFT JOIN parking_spots pspot ON pspot.id = ps.spot_id
LEFT JOIN parking_zones z ON z.id = pspot.zone_id
WHERE ps.status = 'completed'
  AND ps.entry_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY t.id, t.name, z.id, z.name
ORDER BY total_revenue DESC;

-- Выручка по дням и тарифам (7 дней)
SELECT 
    DATE(ps.entry_time) as date,
    t.name as tariff_name,
    COUNT(ps.id) as sessions_count,
    SUM(ps.total_cost) as revenue
FROM parking_sessions ps
JOIN tariffs t ON t.id = ps.tariff_id
WHERE ps.status = 'completed'
  AND ps.entry_time >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(ps.entry_time), t.id, t.name
ORDER BY date DESC, revenue DESC;

-- Топ пользователей по сессиям и расходам
SELECT 
    u.id as user_id,
    u.phone,
    u.email,
    COUNT(DISTINCT c.id) as cars_count,
    COUNT(ps.id) as total_sessions,
    SUM(ps.total_cost) as total_spent,
    AVG(ps.total_cost) as avg_session_cost,
    MIN(ps.entry_time) as first_session,
    MAX(ps.entry_time) as last_session
FROM users u
JOIN cars c ON c.user_id = u.id
LEFT JOIN parking_sessions ps ON ps.car_id = c.id AND ps.status = 'completed'
GROUP BY u.id, u.phone, u.email
HAVING COUNT(ps.id) > 0
ORDER BY total_sessions DESC, total_spent DESC
LIMIT 20;

-- Топ пользователей по сумме расходов + текущий баланс
SELECT 
    u.phone,
    u.email,
    SUM(ps.total_cost) as total_spent,
    COUNT(ps.id) as sessions_count,
    w.balance as current_balance
FROM users u
JOIN cars c ON c.user_id = u.id
JOIN parking_sessions ps ON ps.car_id = c.id AND ps.status = 'completed'
JOIN wallets w ON w.user_id = u.id
GROUP BY u.id, u.phone, u.email, w.balance
ORDER BY total_spent DESC
LIMIT 20;

-- Длинные сессии (больше 24 часов)
SELECT 
    ps.id as session_id,
    c.plate_number,
    u.phone,
    ps.entry_time,
    ps.exit_time,
    ps.total_cost,
    EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 3600 as duration_hours,
    t.name as tariff_name
FROM parking_sessions ps
JOIN cars c ON c.id = ps.car_id
JOIN users u ON u.id = c.user_id
JOIN tariffs t ON t.id = ps.tariff_id
WHERE ps.status = 'completed'
  AND ps.exit_time IS NOT NULL
  AND EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 3600 > 24
ORDER BY duration_hours DESC;

-- Слишком дорогие сессии (дороже среднего в 3 раза)
SELECT 
    ps.id as session_id,
    c.plate_number,
    u.phone,
    ps.entry_time,
    ps.exit_time,
    ps.total_cost,
    t.name as tariff_name,
    t.price_per_hour,
    EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 3600 as duration_hours
FROM parking_sessions ps
JOIN cars c ON c.id = ps.car_id
JOIN users u ON u.id = c.user_id
JOIN tariffs t ON t.id = ps.tariff_id
WHERE ps.status = 'completed'
  AND ps.total_cost > (
      SELECT AVG(total_cost) * 3 
      FROM parking_sessions 
      WHERE status = 'completed'
  )
ORDER BY ps.total_cost DESC;

-- Средняя длительность и цена сессии по тарифам
SELECT 
    t.name as tariff_name,
    COUNT(ps.id) as sessions_count,
    AVG(EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 60) as avg_duration_minutes,
    AVG(EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 3600) as avg_duration_hours,
    AVG(ps.total_cost) as avg_cost
FROM parking_sessions ps
JOIN tariffs t ON t.id = ps.tariff_id
WHERE ps.status = 'completed'
  AND ps.exit_time IS NOT NULL
GROUP BY t.id, t.name
ORDER BY avg_duration_minutes DESC;

-- Использование зон (30 дней)
SELECT 
    z.name as zone_name,
    COUNT(DISTINCT ps.id) as total_sessions,
    COUNT(DISTINCT CASE WHEN ps.status = 'active' THEN ps.id END) as active_sessions,
    COUNT(DISTINCT ps.spot_id) as used_spots,
    AVG(EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 60) as avg_duration_minutes
FROM parking_zones z
LEFT JOIN parking_spots pspot ON pspot.zone_id = z.id
LEFT JOIN parking_sessions ps ON ps.spot_id = pspot.id
WHERE ps.entry_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY z.id, z.name
ORDER BY total_sessions DESC;

-- Въезды: сколько allowed/denied (30 дней)
SELECT 
    result,
    COUNT(*) as attempts_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM entry_logs
WHERE attempt_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY result;

-- Отказы по причинам (30 дней)
SELECT 
    reason,
    COUNT(*) as denied_count
FROM entry_logs
WHERE result = 'denied'
  AND attempt_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY reason
ORDER BY denied_count DESC;

-- Операции кошелька по типам (30 дней)
SELECT 
    operation_type,
    COUNT(*) as transactions_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    MIN(amount) as min_amount,
    MAX(amount) as max_amount
FROM wallet_transactions
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY operation_type
ORDER BY transactions_count DESC;

-- Операции кошелька по дням (30 дней)
SELECT 
    DATE(created_at) as date,
    operation_type,
    COUNT(*) as transactions_count,
    SUM(amount) as total_amount
FROM wallet_transactions
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at), operation_type
ORDER BY date DESC, operation_type;

-- Пользователи с отрицательным балансом
SELECT 
    u.id,
    u.phone,
    u.email,
    w.balance,
    COUNT(ps.id) as active_sessions,
    u.is_blocked
FROM users u
JOIN wallets w ON w.user_id = u.id
LEFT JOIN cars c ON c.user_id = u.id
LEFT JOIN parking_sessions ps ON ps.car_id = c.id AND ps.status = 'active'
WHERE w.balance < 0
GROUP BY u.id, u.phone, u.email, w.balance, u.is_blocked
ORDER BY w.balance ASC;

-- Пики по часам (ранги, 30 дней)
SELECT 
    date,
    hour,
    entries_count,
    RANK() OVER (PARTITION BY date ORDER BY entries_count DESC) as rank_in_day,
    RANK() OVER (ORDER BY entries_count DESC) as rank_overall
FROM (
    SELECT 
        DATE(entry_time) as date,
        EXTRACT(HOUR FROM entry_time) as hour,
        COUNT(*) as entries_count
    FROM parking_sessions
    WHERE entry_time >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE(entry_time), EXTRACT(HOUR FROM entry_time)
) subq
ORDER BY entries_count DESC
LIMIT 20;

-- Выручка по дням + сравнение с прошлым днём
SELECT 
    DATE(entry_time) as date,
    COUNT(*) as sessions_count,
    SUM(total_cost) as daily_revenue,
    AVG(total_cost) as avg_session_cost,
    LAG(SUM(total_cost)) OVER (ORDER BY DATE(entry_time)) as prev_day_revenue,
    SUM(total_cost) - LAG(SUM(total_cost)) OVER (ORDER BY DATE(entry_time)) as revenue_change
FROM parking_sessions
WHERE status = 'completed'
  AND entry_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(entry_time)
ORDER BY date DESC;

-- Топ автомобилей по использованию
SELECT 
    c.plate_number,
    u.phone as owner_phone,
    COUNT(ps.id) as total_sessions,
    SUM(ps.total_cost) as total_spent,
    AVG(EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 60) as avg_duration_minutes,
    MIN(ps.entry_time) as first_use,
    MAX(ps.entry_time) as last_use
FROM cars c
JOIN users u ON u.id = c.user_id
LEFT JOIN parking_sessions ps ON ps.car_id = c.id AND ps.status = 'completed'
WHERE c.is_active = TRUE
GROUP BY c.id, c.plate_number, u.phone
HAVING COUNT(ps.id) > 0
ORDER BY total_sessions DESC
LIMIT 30;
