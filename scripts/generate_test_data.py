"""
Скрипт генерации тестовых данных: 
- 50-100 пользователей
- 70-150 машин
- 3000-5000 парковочных сессий
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import random
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

# подключение к БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://parking_user:parking_pass@localhost:5435/smart_parking")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
fake = Faker('ru_RU')

def generate_plate_number():
    """генерация российского номера"""
    letters = 'АВЕКМНОРСТУХ'
    region = random.randint(1, 199)
    return f"{random.choice(letters)}{random.randint(100, 999)}{random.choice(letters)}{random.choice(letters)}{region}"

def generate_test_data():
    db = SessionLocal()
    
    try:
        print("Начинаем генерацию данных...")
        
        # проверка наличия справочников
        zones = db.execute(text("SELECT id FROM parking_zones")).fetchall()
        tariffs = db.execute(text("SELECT id FROM tariffs")).fetchall()
        access_levels = db.execute(text("SELECT id FROM access_levels")).fetchall()
        gates = db.execute(text("SELECT id FROM gates WHERE type = 'entry'")).fetchall()
        
        if not zones or not tariffs:
            print("Ошибка: Нет зон или тарифов. Сначала запустите инициализацию БД.")
            return
        
        zone_ids = [z[0] for z in zones]
        tariff_ids = [t[0] for t in tariffs]
        access_level_ids = [a[0] for a in access_levels]
        gate_ids = [g[0] for g in gates]
        
        # 1. создание пользователей
        num_users = random.randint(50, 100)
        print(f"Генерируем {num_users} пользователей...")
        
        user_ids = []
        car_ids = []
        
        for i in range(num_users):
            phone = f"+7{random.randint(9000000000, 9999999999)}"
            email = fake.email() if random.random() > 0.3 else None
            
            # вставка пользователя
            user_result = db.execute(
                text("""
                    INSERT INTO users (phone, email, password_hash, is_blocked)
                    VALUES (:phone, :email, :password_hash, :is_blocked)
                    RETURNING id
                """),
                {
                    "phone": phone,
                    "email": email,
                    "password_hash": "$2b$12$dummyhash", 
                    "is_blocked": random.random() < 0.05 
                }
            )
            user_id = user_result.fetchone()[0]
            user_ids.append(user_id)
            
            # уровень доступа
            if random.random() < 0.3 and access_level_ids:
                access_level_id = random.choice(access_level_ids)
                db.execute(
                    text("""
                        INSERT INTO user_access_levels (user_id, access_level_id)
                        VALUES (:user_id, :access_level_id)
                        ON CONFLICT DO NOTHING
                    """),
                    {"user_id": user_id, "access_level_id": access_level_id}
                )
            
            # начальный баланс
            initial_balance = random.uniform(2000, 50000)
            db.execute(
                text("UPDATE wallets SET balance = :balance WHERE user_id = :user_id"),
                {"balance": Decimal(str(round(initial_balance, 2))), "user_id": user_id}
            )
            
            # создание машин (1-3 на пользователя)
            num_cars = random.randint(1, 3)
            for j in range(num_cars):
                plate_number = generate_plate_number()
                # проверка уникальности
                while db.execute(text("SELECT id FROM cars WHERE plate_number = :pn"), {"pn": plate_number}).fetchone():
                    plate_number = generate_plate_number()
                
                car_result = db.execute(
                    text("""
                        INSERT INTO cars (user_id, plate_number, model, is_active)
                        VALUES (:user_id, :plate_number, :model, :is_active)
                        RETURNING id
                    """),
                    {
                        "user_id": user_id,
                        "plate_number": plate_number,
                        "model": fake.company() + " " + str(random.randint(2000, 2024)),
                        "is_active": random.random() > 0.1 
                    }
                )
                car_ids.append(car_result.fetchone()[0])
            
            if (i + 1) % 10 == 0:
                print(f"  Создано {i + 1} пользователей...")
                db.commit()
        
        db.commit()
        
        # 2. парковочные места
        print("Генерируем парковочные места...")
        spot_ids = []
        for zone_id in zone_ids:
            num_spots = random.randint(20, 50)
            for spot_num in range(1, num_spots + 1):
                spot_result = db.execute(
                    text("""
                        INSERT INTO parking_spots (zone_id, spot_number, is_reserved, is_active)
                        VALUES (:zone_id, :spot_number, :is_reserved, :is_active)
                        RETURNING id
                    """),
                    {
                        "zone_id": zone_id,
                        "spot_number": f"SP-{spot_num:03d}",
                        "is_reserved": random.random() < 0.1,
                        "is_active": random.random() > 0.05
                    }
                )
                spot_ids.append(spot_result.fetchone()[0])
        db.commit()
        
        # 3. парковочные сессии
        num_sessions = random.randint(3000, 5000)
        print(f"Генерируем {num_sessions} сессий...")
        
        start_date = datetime.now() - timedelta(days=30)
        completed_sessions = 0
        active_sessions = 0
        
        for i in range(num_sessions):
            car_id = random.choice(car_ids)
            tariff_id = random.choice(tariff_ids)
            spot_id = random.choice(spot_ids) if random.random() > 0.3 else None
            
            # время въезда (последние 30 дней)
            entry_time = start_date + timedelta(
                seconds=random.randint(0, int((datetime.now() - start_date).total_seconds()))
            )
            
            # распределение статусов: 80% завершено, 15% активно, 5% сбой
            status_rand = random.random()
            if status_rand < 0.8:
                # завершенная сессия
                duration_hours = random.uniform(0.5, 12)
                exit_time = entry_time + timedelta(hours=duration_hours)
                
                # расчет стоимости
                tariff_data = db.execute(
                    text("SELECT price_per_hour, free_minutes FROM tariffs WHERE id = :id"),
                    {"id": tariff_id}
                ).fetchone()
                
                if tariff_data:
                    price = float(tariff_data[0])
                    free_mins = tariff_data[1]
                    billable = max(0, (duration_hours * 60) - free_mins)
                    total_cost = Decimal(str(round((billable / 60) * price, 2)))
                else:
                    total_cost = Decimal("0.00")
                
                session_result = db.execute(
                    text("""
                        INSERT INTO parking_sessions 
                        (car_id, spot_id, tariff_id, entry_time, exit_time, total_cost, status)
                        VALUES (:car_id, :spot_id, :tariff_id, :entry_time, :exit_time, :total_cost, 'completed')
                        RETURNING id
                    """),
                    {
                        "car_id": car_id, "spot_id": spot_id, "tariff_id": tariff_id,
                        "entry_time": entry_time, "exit_time": exit_time, "total_cost": total_cost
                    }
                )
                session_id = session_result.fetchone()[0]
                completed_sessions += 1
                
                # списание денег
                wallet_id = db.execute(
                    text("SELECT id FROM wallets WHERE user_id = (SELECT user_id FROM cars WHERE id = :car_id)"),
                    {"car_id": car_id}
                ).fetchone()[0]
                
                db.execute(
                    text("""
                        INSERT INTO wallet_transactions 
                        (wallet_id, session_id, amount, operation_type, comment)
                        VALUES (:wallet_id, :session_id, :amount, 'parking_charge', 'Parking session')
                    """),
                    {"wallet_id": wallet_id, "session_id": session_id, "amount": -total_cost}
                )
                
                db.execute(
                    text("UPDATE wallets SET balance = balance - :amount WHERE id = :wallet_id"),
                    {"amount": total_cost, "wallet_id": wallet_id}
                )
                
            elif status_rand < 0.95:
                # активная сессия
                db.execute(
                    text("""
                        INSERT INTO parking_sessions (car_id, spot_id, tariff_id, entry_time, status)
                        VALUES (:car_id, :spot_id, :tariff_id, :entry_time, 'active')
                    """),
                    {"car_id": car_id, "spot_id": spot_id, "tariff_id": tariff_id, "entry_time": entry_time}
                )
                active_sessions += 1
            else:
                # сбойная сессия
                db.execute(
                    text("""
                        INSERT INTO parking_sessions (car_id, spot_id, tariff_id, entry_time, status)
                        VALUES (:car_id, :spot_id, :tariff_id, :entry_time, 'failed')
                    """),
                    {"car_id": car_id, "spot_id": spot_id, "tariff_id": tariff_id, "entry_time": entry_time}
                )
            
            # лог въезда
            gate_id = random.choice(gate_ids)
            plate_number = db.execute(text("SELECT plate_number FROM cars WHERE id = :id"), {"id": car_id}).fetchone()[0]
            
            db.execute(
                text("""
                    INSERT INTO entry_logs (plate_number, gate_id, attempt_time, result, reason)
                    VALUES (:plate_number, :gate_id, :attempt_time, :result, :reason)
                """),
                {
                    "plate_number": plate_number, "gate_id": gate_id, "attempt_time": entry_time,
                    "result": "allowed" if status_rand < 0.95 else "denied",
                    "reason": None if status_rand < 0.95 else "Insufficient balance"
                }
            )
            
            if (i + 1) % 500 == 0:
                print(f"  Создано {i + 1} сессий...")
                db.commit()
        
        db.commit()
        
        # 4. пополнения баланса
        print("Генерируем пополнения...")
        num_topups = random.randint(200, 500)
        wallet_ids = [w[0] for w in db.execute(text("SELECT id FROM wallets")).fetchall()]
        
        for i in range(num_topups):
            wallet_id = random.choice(wallet_ids)
            amount = Decimal(str(round(random.uniform(100, 5000), 2)))
            
            db.execute(
                text("""
                    INSERT INTO wallet_transactions (wallet_id, amount, operation_type, comment, created_at)
                    VALUES (:wallet_id, :amount, 'topup', 'Top-up', :created_at)
                """),
                {
                    "wallet_id": wallet_id, "amount": amount,
                    "created_at": start_date + timedelta(seconds=random.randint(0, int((datetime.now() - start_date).total_seconds())))
                }
            )
            
            db.execute(
                text("UPDATE wallets SET balance = balance + :amount WHERE id = :wallet_id"),
                {"amount": amount, "wallet_id": wallet_id}
            )
        
        db.commit()
        print("Успешно завершено!")
        
    except Exception as e:
        db.rollback()
        print(f"Ошибка: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    generate_test_data()
