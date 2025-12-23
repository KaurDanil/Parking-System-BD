from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey, DateTime, Text, CheckConstraint, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base
import enum


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class OperationType(str, enum.Enum):
    TOPUP = "topup"
    PARKING_CHARGE = "parking_charge"
    ADJUSTMENT = "adjustment"


class GateType(str, enum.Enum):
    ENTRY = "entry"
    EXIT = "exit"


class EntryResult(str, enum.Enum):
    ALLOWED = "allowed"
    DENIED = "denied"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_blocked = Column(Boolean, nullable=False, default=False)

    wallet = relationship("Wallet", back_populates="user", uselist=False)
    cars = relationship("Car", back_populates="user")
    access_levels = relationship("UserAccessLevel", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    balance = Column(Numeric(12, 2), nullable=False, default=0.00)
    currency = Column(String(3), nullable=False, default="RUB")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet")


class Car(Base):
    __tablename__ = "cars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plate_number = Column(String(20), unique=True, nullable=False)
    model = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="cars")
    sessions = relationship("ParkingSession", back_populates="car")


class AccessLevel(Base):
    __tablename__ = "access_levels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    users = relationship("UserAccessLevel", back_populates="access_level")
    tariffs = relationship("Tariff", back_populates="access_level")


class UserAccessLevel(Base):
    __tablename__ = "user_access_levels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_level_id = Column(UUID(as_uuid=True), ForeignKey("access_levels.id", ondelete="CASCADE"), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="access_levels")
    access_level = relationship("AccessLevel", back_populates="users")


class ParkingZone(Base):
    __tablename__ = "parking_zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    spots = relationship("ParkingSpot", back_populates="zone")
    tariffs = relationship("Tariff", back_populates="zone")


class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("parking_zones.id", ondelete="CASCADE"), nullable=False)
    spot_number = Column(String(50), nullable=False)
    is_reserved = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    zone = relationship("ParkingZone", back_populates="spots")
    sessions = relationship("ParkingSession", back_populates="spot")


class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    price_per_hour = Column(Numeric(10, 2), nullable=False)
    free_minutes = Column(Integer, nullable=False, default=0)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("parking_zones.id", ondelete="SET NULL"), nullable=True)
    access_level_id = Column(UUID(as_uuid=True), ForeignKey("access_levels.id", ondelete="SET NULL"), nullable=True)

    zone = relationship("ParkingZone", back_populates="tariffs")
    access_level = relationship("AccessLevel", back_populates="tariffs")
    sessions = relationship("ParkingSession", back_populates="tariff")


class Gate(Base):
    __tablename__ = "gates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(10), nullable=False)

    entry_logs = relationship("EntryLog", back_populates="gate")


class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    car_id = Column(UUID(as_uuid=True), ForeignKey("cars.id", ondelete="RESTRICT"), nullable=False)
    spot_id = Column(UUID(as_uuid=True), ForeignKey("parking_spots.id", ondelete="SET NULL"), nullable=True)
    tariff_id = Column(UUID(as_uuid=True), ForeignKey("tariffs.id", ondelete="RESTRICT"), nullable=False)
    entry_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    total_cost = Column(Numeric(12, 2), nullable=True)
    status = Column(String(20), nullable=False, default="active")

    car = relationship("Car", back_populates="sessions")
    spot = relationship("ParkingSpot", back_populates="sessions")
    tariff = relationship("Tariff", back_populates="sessions")
    transactions = relationship("WalletTransaction", back_populates="session")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("parking_sessions.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    operation_type = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    comment = Column(Text, nullable=True)

    wallet = relationship("Wallet", back_populates="transactions")
    session = relationship("ParkingSession", back_populates="transactions")


class EntryLog(Base):
    __tablename__ = "entry_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate_number = Column(String(20), nullable=False)
    gate_id = Column(UUID(as_uuid=True), ForeignKey("gates.id", ondelete="RESTRICT"), nullable=False)
    attempt_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    result = Column(String(10), nullable=False)
    reason = Column(Text, nullable=True)

    gate = relationship("Gate", back_populates="entry_logs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(20), nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="audit_logs")
