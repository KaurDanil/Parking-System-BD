from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Car, ParkingSession, User, Wallet, WalletTransaction
from app.schemas import OccupancyStats, RevenueStats, UserStats

router = APIRouter()


@router.get("/stats/occupancy", response_model=List[dict])
async def get_occupancy_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current parking occupancy by zone"""
    result = db.execute(text("SELECT * FROM parking_occupancy"))
    rows = result.fetchall()
    
    return [
        {
            "zone_id": str(row[0]),
            "zone_name": row[1],
            "total_spots": row[2],
            "occupied_spots": row[3],
            "free_spots": row[4],
            "occupancy_percent": float(row[5]) if row[5] else 0
        }
        for row in rows
    ]


@router.get("/stats/revenue", response_model=List[dict])
async def get_revenue_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get revenue statistics"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    
    result = db.execute(
        text("""
            SELECT * FROM revenue_analytics
            WHERE date BETWEEN :start_date AND :end_date
            ORDER BY date DESC, total_revenue DESC
        """),
        {"start_date": start_date.date(), "end_date": end_date.date()}
    )
    rows = result.fetchall()
    
    return [
        {
            "date": row[0],
            "tariff_id": str(row[1]),
            "tariff_name": row[2],
            "zone_id": str(row[3]) if row[3] else None,
            "zone_name": row[4],
            "sessions_count": row[5],
            "total_revenue": float(row[6]) if row[6] else 0,
            "avg_session_cost": float(row[7]) if row[7] else 0,
            "avg_duration_minutes": float(row[8]) if row[8] else 0
        }
        for row in rows
    ]


@router.get("/users/debtors", response_model=List[dict])
async def get_debtors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get users with negative balance"""
    users = db.query(User, Wallet).join(Wallet).filter(Wallet.balance < 0).all()
    
    return [
        {
            "user_id": str(user.id),
            "phone": user.phone,
            "email": user.email,
            "balance": float(wallet.balance),
            "is_blocked": user.is_blocked
        }
        for user, wallet in users
    ]


@router.get("/stats/top-users", response_model=List[dict])
async def get_top_users(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get top users by number of sessions and total spent"""
    result = db.execute(
        text("""
            SELECT 
                u.id as user_id,
                u.phone,
                COUNT(ps.id) as total_sessions,
                COALESCE(SUM(ps.total_cost), 0) as total_spent,
                COALESCE(AVG(ps.total_cost), 0) as avg_session_cost
            FROM users u
            LEFT JOIN cars c ON c.user_id = u.id
            LEFT JOIN parking_sessions ps ON ps.car_id = c.id AND ps.status = 'completed'
            GROUP BY u.id, u.phone
            ORDER BY total_sessions DESC, total_spent DESC
            LIMIT :limit
        """),
        {"limit": limit}
    )
    rows = result.fetchall()
    
    return [
        {
            "user_id": str(row[0]),
            "phone": row[1],
            "total_sessions": row[2],
            "total_spent": float(row[3]) if row[3] else 0,
            "avg_session_cost": float(row[4]) if row[4] else 0
        }
        for row in rows
    ]


@router.get("/stats/suspicious-sessions", response_model=List[dict])
async def get_suspicious_sessions(
    max_hours: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get sessions longer than specified hours"""
    result = db.execute(
        text("""
            SELECT 
                ps.id,
                c.plate_number,
                u.phone,
                ps.entry_time,
                ps.exit_time,
                ps.total_cost,
                EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 3600 as duration_hours
            FROM parking_sessions ps
            JOIN cars c ON c.id = ps.car_id
            JOIN users u ON u.id = c.user_id
            WHERE ps.status = 'completed'
                AND ps.exit_time IS NOT NULL
                AND EXTRACT(EPOCH FROM (ps.exit_time - ps.entry_time)) / 3600 > :max_hours
            ORDER BY duration_hours DESC
        """),
        {"max_hours": max_hours}
    )
    rows = result.fetchall()
    
    return [
        {
            "session_id": str(row[0]),
            "plate_number": row[1],
            "phone": row[2],
            "entry_time": row[3],
            "exit_time": row[4],
            "total_cost": float(row[5]) if row[5] else 0,
            "duration_hours": float(row[6])
        }
        for row in rows
    ]


@router.get("/stats/peak-hours", response_model=List[dict])
async def get_peak_hours(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get peak hours by number of entries"""
    result = db.execute(
        text("""
            SELECT 
                EXTRACT(HOUR FROM entry_time) as hour,
                COUNT(*) as entries_count
            FROM parking_sessions
            WHERE entry_time >= CURRENT_DATE - (:days || ' days')::interval
            GROUP BY EXTRACT(HOUR FROM entry_time)
            ORDER BY entries_count DESC
        """),
        {"days": days}
    )
    rows = result.fetchall()
    
    return [
        {
            "hour": int(row[0]),
            "entries_count": row[1]
        }
        for row in rows
    ]
