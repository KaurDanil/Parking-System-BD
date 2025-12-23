-- схема бд «умная парковка» (postgresql 15+)

-- расширение для генерации uuid
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- расширение для криптографии
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- таблицы

-- пользователи
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT phone_format CHECK (phone ~ '^\+?[1-9]\d{1,14}$')
);


-- кошельки (один к одному с пользователями)
CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    balance NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) NOT NULL DEFAULT 'RUB',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT balance_check CHECK (balance >= -1000.00) -- лимит отрицательного баланса
);


-- автомобили
CREATE TABLE cars (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plate_number VARCHAR(20) UNIQUE NOT NULL,
    model VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- уровни доступа
CREATE TABLE access_levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);


-- уровни доступа пользователей (многие ко многим)
CREATE TABLE user_access_levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_level_id UUID NOT NULL REFERENCES access_levels(id) ON DELETE CASCADE,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, access_level_id)
);


-- парковочные зоны
CREATE TABLE parking_zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT
);


-- парковочные места
CREATE TABLE parking_spots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_id UUID NOT NULL REFERENCES parking_zones(id) ON DELETE CASCADE,
    spot_number VARCHAR(50) NOT NULL,
    is_reserved BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(zone_id, spot_number)
);


-- тарифы
CREATE TABLE tariffs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    price_per_hour NUMERIC(10,2) NOT NULL CHECK (price_per_hour >= 0),
    free_minutes INTEGER NOT NULL DEFAULT 0 CHECK (free_minutes >= 0),
    zone_id UUID REFERENCES parking_zones(id) ON DELETE SET NULL,
    access_level_id UUID REFERENCES access_levels(id) ON DELETE SET NULL
);


-- ворота (въезд/выезд)
CREATE TABLE gates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(10) NOT NULL CHECK (type IN ('entry', 'exit'))
);


-- парковочные сессии
CREATE TABLE parking_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    car_id UUID NOT NULL REFERENCES cars(id) ON DELETE RESTRICT,
    spot_id UUID REFERENCES parking_spots(id) ON DELETE SET NULL,
    tariff_id UUID NOT NULL REFERENCES tariffs(id) ON DELETE RESTRICT,
    entry_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    exit_time TIMESTAMP,
    total_cost NUMERIC(12,2),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed')),
    CONSTRAINT exit_after_entry CHECK (exit_time IS NULL OR exit_time >= entry_time)
);


-- транзакции кошелька
CREATE TABLE wallet_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
    session_id UUID REFERENCES parking_sessions(id) ON DELETE SET NULL,
    amount NUMERIC(12,2) NOT NULL,
    operation_type VARCHAR(20) NOT NULL CHECK (operation_type IN ('topup', 'parking_charge', 'adjustment')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    comment TEXT
);


-- журнал въезда
CREATE TABLE entry_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plate_number VARCHAR(20) NOT NULL,
    gate_id UUID NOT NULL REFERENCES gates(id) ON DELETE RESTRICT,
    attempt_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    result VARCHAR(10) NOT NULL CHECK (result IN ('allowed', 'denied')),
    reason TEXT
);


-- журнал аудита
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    action VARCHAR(20) NOT NULL CHECK (action IN ('create', 'update', 'delete')),
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX idx_parking_sessions_car_entry ON parking_sessions(car_id, entry_time, exit_time);
CREATE INDEX idx_parking_sessions_status ON parking_sessions(status) WHERE status = 'active';
CREATE INDEX idx_wallet_transactions_wallet_created ON wallet_transactions(wallet_id, created_at);
CREATE INDEX idx_cars_plate_number ON cars(plate_number);
CREATE INDEX idx_entry_logs_plate_time ON entry_logs(plate_number, attempt_time);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_parking_sessions_entry_time ON parking_sessions(entry_time);
CREATE INDEX idx_wallets_user_id ON wallets(user_id);


-- функции

-- расчет стоимости парковки
CREATE OR REPLACE FUNCTION calculate_parking_cost(
    p_entry_time TIMESTAMP,
    p_exit_time TIMESTAMP,
    p_tariff_id UUID
) RETURNS NUMERIC AS $$
DECLARE
    v_price_per_hour NUMERIC;
    v_free_minutes INTEGER;
    v_duration_minutes INTEGER;
    v_billable_minutes INTEGER;
    v_cost NUMERIC;
BEGIN
    SELECT price_per_hour, free_minutes
    INTO v_price_per_hour, v_free_minutes
    FROM tariffs
    WHERE id = p_tariff_id;
    
    IF v_price_per_hour IS NULL THEN
        RAISE EXCEPTION 'Tariff not found';
    END IF;
    
    -- длительность в минутах
    v_duration_minutes := EXTRACT(EPOCH FROM (p_exit_time - p_entry_time)) / 60;
    
    -- вычитаем бесплатные минуты
    v_billable_minutes := GREATEST(0, v_duration_minutes - v_free_minutes);
    
    -- расчет стоимости (почасовая тарификация)
    v_cost := (v_billable_minutes / 60.0) * v_price_per_hour;
    
    -- округление до 2 знаков
    RETURN ROUND(v_cost, 2);
END;
$$ LANGUAGE plpgsql;


-- получение баланса пользователя
CREATE OR REPLACE FUNCTION get_user_balance(p_user_id UUID)
RETURNS NUMERIC AS $$
DECLARE
    v_balance NUMERIC;
BEGIN
    SELECT balance INTO v_balance
    FROM wallets
    WHERE user_id = p_user_id;
    
    RETURN COALESCE(v_balance, 0);
END;
$$ LANGUAGE plpgsql;


-- проверка разрешения на въезд
CREATE OR REPLACE FUNCTION check_entry_allowed(
    p_plate_number VARCHAR,
    p_gate_id UUID
) RETURNS TABLE(
    allowed BOOLEAN,
    reason TEXT,
    car_id UUID,
    user_id UUID,
    wallet_id UUID,
    balance NUMERIC
) AS $$
DECLARE
    v_car_id UUID;
    v_user_id UUID;
    v_wallet_id UUID;
    v_balance NUMERIC;
    v_is_blocked BOOLEAN;
    v_min_balance NUMERIC := 50.00; -- минимальный баланс
BEGIN
    -- поиск автомобиля
    SELECT id, user_id INTO v_car_id, v_user_id
    FROM cars
    WHERE plate_number = p_plate_number AND is_active = TRUE;
    
    IF v_car_id IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Car not found or inactive'::TEXT, NULL::UUID, NULL::UUID, NULL::UUID, NULL::NUMERIC;
        RETURN;
    END IF;
    
    -- проверка блокировки пользователя
    SELECT is_blocked INTO v_is_blocked
    FROM users
    WHERE id = v_user_id;
    
    IF v_is_blocked THEN
        RETURN QUERY SELECT FALSE, 'User is blocked'::TEXT, v_car_id, v_user_id, NULL::UUID, NULL::NUMERIC;
        RETURN;
    END IF;
    
    -- проверка кошелька
    SELECT id, balance INTO v_wallet_id, v_balance
    FROM wallets
    WHERE user_id = v_user_id;
    
    IF v_wallet_id IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Wallet not found'::TEXT, v_car_id, v_user_id, NULL::UUID, NULL::NUMERIC;
        RETURN;
    END IF;
    
    -- проверка баланса
    IF v_balance < v_min_balance THEN
        RETURN QUERY SELECT FALSE, format('Insufficient balance: %.2f (minimum: %.2f)', v_balance, v_min_balance)::TEXT, 
                    v_car_id, v_user_id, v_wallet_id, v_balance;
        RETURN;
    END IF;
    
    -- въезд разрешен
    RETURN QUERY SELECT TRUE, 'Entry allowed'::TEXT, v_car_id, v_user_id, v_wallet_id, v_balance;
END;
$$ LANGUAGE plpgsql;


-- обработка выезда
CREATE OR REPLACE FUNCTION process_exit(
    p_car_id UUID,
    p_exit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) RETURNS TABLE(
    success BOOLEAN,
    session_id UUID,
    cost NUMERIC,
    message TEXT
) AS $$
DECLARE
    v_session_id UUID;
    v_tariff_id UUID;
    v_entry_time TIMESTAMP;
    v_car_id UUID;  
    v_cost NUMERIC;
    v_wallet_id UUID;
    v_user_id UUID;
    v_new_balance NUMERIC;
BEGIN
    -- поиск активной сессии
    SELECT id, tariff_id, entry_time, car_id
    INTO v_session_id, v_tariff_id, v_entry_time, v_car_id
    FROM parking_sessions
    WHERE car_id = p_car_id AND status = 'active'
    ORDER BY entry_time DESC
    LIMIT 1;
    
    IF v_session_id IS NULL THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, NULL::NUMERIC, 'No active session found'::TEXT;
        RETURN;
    END IF;
    
    -- расчет стоимости
    SELECT calculate_parking_cost(v_entry_time, p_exit_time, v_tariff_id) INTO v_cost;
    
    -- получение id кошелька
    SELECT w.id, c.user_id INTO v_wallet_id, v_user_id
    FROM cars c
    JOIN wallets w ON w.user_id = c.user_id
    WHERE c.id = p_car_id;
    
    -- обновление баланса и создание транзакции
    BEGIN
        -- списание средств
        UPDATE wallets
        SET balance = balance - v_cost,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = v_wallet_id
        RETURNING balance INTO v_new_balance;
        
        -- закрытие сессии
        UPDATE parking_sessions
        SET exit_time = p_exit_time,
            total_cost = v_cost,
            status = 'completed'
        WHERE id = v_session_id;
        
        -- запись транзакции
        INSERT INTO wallet_transactions (wallet_id, session_id, amount, operation_type, comment)
        VALUES (v_wallet_id, v_session_id, -v_cost, 'parking_charge', 
                format('Parking session %s', v_session_id));
        
        RETURN QUERY SELECT TRUE, v_session_id, v_cost, format('Exit processed. Cost: %.2f, New balance: %.2f', v_cost, v_new_balance)::TEXT;
        
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT FALSE, v_session_id, NULL::NUMERIC, format('Error processing exit: %s', SQLERRM)::TEXT;
    END;
END;
$$ LANGUAGE plpgsql;


-- триггеры

-- функция обновления времени кошелька
CREATE OR REPLACE FUNCTION update_wallet_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trigger_update_wallet_timestamp
BEFORE UPDATE ON wallets
FOR EACH ROW
EXECUTE FUNCTION update_wallet_timestamp();


-- функция создания кошелька при регистрации
CREATE OR REPLACE FUNCTION create_wallet_for_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO wallets (user_id, balance, currency)
    VALUES (NEW.id, 0.00, 'RUB');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trigger_create_wallet
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_wallet_for_user();


-- представления

-- текущая загрузка парковки
CREATE OR REPLACE VIEW parking_occupancy AS
SELECT 
    z.id AS zone_id,
    z.name AS zone_name,
    COUNT(ps.id) AS total_spots,
    COUNT(CASE WHEN s.status = 'active' THEN 1 END) AS occupied_spots,
    COUNT(ps.id) - COUNT(CASE WHEN s.status = 'active' THEN 1 END) AS free_spots,
    ROUND(
        COUNT(CASE WHEN s.status = 'active' THEN 1 END)::NUMERIC / 
        NULLIF(COUNT(ps.id), 0) * 100, 
        2
    ) AS occupancy_percent
FROM parking_zones z
LEFT JOIN parking_spots ps ON ps.zone_id = z.id AND ps.is_active = TRUE
LEFT JOIN parking_sessions s ON s.spot_id = ps.id AND s.status = 'active'
GROUP BY z.id, z.name;


-- история парковок пользователя
CREATE OR REPLACE VIEW user_parking_history AS
SELECT 
    u.id AS user_id,
    u.phone,
    c.plate_number,
    s.id AS session_id,
    s.entry_time,
    s.exit_time,
    s.total_cost,
    s.status,
    t.name AS tariff_name,
    z.name AS zone_name
FROM users u
JOIN cars c ON c.user_id = u.id
JOIN parking_sessions s ON s.car_id = c.id
JOIN tariffs t ON t.id = s.tariff_id
LEFT JOIN parking_spots ps ON ps.id = s.spot_id
LEFT JOIN parking_zones z ON z.id = ps.zone_id
ORDER BY s.entry_time DESC;


-- аналитика выручки
CREATE OR REPLACE VIEW revenue_analytics AS
SELECT 
    DATE(ps.entry_time) AS date,
    t.id AS tariff_id,
    t.name AS tariff_name,
    z.id AS zone_id,
    z.name AS zone_name,
    COUNT(ps.id) AS sessions_count,
    SUM(ps.total_cost) AS total_revenue,
    AVG(ps.total_cost) AS avg_session_cost,
    AVG(EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 60) AS avg_duration_minutes
FROM parking_sessions ps
JOIN tariffs t ON t.id = ps.tariff_id
LEFT JOIN parking_spots pspot ON pspot.id = ps.spot_id
LEFT JOIN parking_zones z ON z.id = pspot.zone_id
WHERE ps.status = 'completed' AND ps.total_cost IS NOT NULL
GROUP BY DATE(ps.entry_time), t.id, t.name, z.id, z.name;


-- начальные данные

-- уровни доступа
INSERT INTO access_levels (code, description) VALUES
('RESIDENT', 'Resident with permanent access'),
('EMPLOYEE', 'Employee with discounted rates'),
('GUEST', 'Guest with standard rates'),
('VIP', 'VIP with premium access');


-- ворота
INSERT INTO gates (name, type) VALUES
('Gate IN 1', 'entry'),
('Gate IN 2', 'entry'),
('Gate OUT 1', 'exit'),
('Gate OUT 2', 'exit');


-- зоны
INSERT INTO parking_zones (name, description) VALUES
('Underground -1', 'Underground parking level -1'),
('Underground -2', 'Underground parking level -2'),
('Street Level', 'Street level parking'),
('VIP Zone', 'Premium parking zone');


-- тарифы
INSERT INTO tariffs (name, price_per_hour, free_minutes, zone_id, access_level_id) VALUES
('Standard', 100.00, 15, NULL, NULL),
('Resident', 50.00, 30, NULL, (SELECT id FROM access_levels WHERE code = 'RESIDENT')),
('Employee', 30.00, 60, NULL, (SELECT id FROM access_levels WHERE code = 'EMPLOYEE')),
('VIP', 200.00, 60, (SELECT id FROM parking_zones WHERE name = 'VIP Zone'), (SELECT id FROM access_levels WHERE code = 'VIP'));
