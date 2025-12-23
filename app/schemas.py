from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from enum import Enum


class UserRegister(BaseModel):
    phone: str
    email: Optional[EmailStr] = None
    password: str


class UserLogin(BaseModel):
    phone: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


# Batch import schemas
class BatchCar(BaseModel):
    plate_number: str
    model: Optional[str] = None


class BatchUserPayload(BaseModel):
    phone: str
    email: Optional[EmailStr] = None
    password: str
    cars: List[BatchCar] = []


class BatchImportRequest(BaseModel):
    users: List[BatchUserPayload]
    dry_run: bool = False


class BatchImportResult(BaseModel):
    created_users: int
    created_cars: int
    errors: List[dict]


class UserBase(BaseModel):
    phone: str
    email: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    is_blocked: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    is_blocked: bool

    class Config:
        from_attributes = True


class CarBase(BaseModel):
    plate_number: str
    model: Optional[str] = None


class CarCreate(CarBase):
    pass


class CarUpdate(BaseModel):
    plate_number: Optional[str] = None
    model: Optional[str] = None
    is_active: Optional[bool] = None


class CarResponse(CarBase):
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WalletResponse(BaseModel):
    id: UUID
    user_id: UUID
    balance: Decimal
    currency: str
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletTopup(BaseModel):
    amount: Decimal
    comment: Optional[str] = None


class AccessLevelBase(BaseModel):
    code: str
    description: Optional[str] = None


class AccessLevelCreate(AccessLevelBase):
    pass


class AccessLevelUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None


class AccessLevelResponse(AccessLevelBase):
    id: UUID

    class Config:
        from_attributes = True


class UserAccessLevelBase(BaseModel):
    user_id: UUID
    access_level_id: UUID


class UserAccessLevelCreate(UserAccessLevelBase):
    pass


class UserAccessLevelUpdate(BaseModel):
    user_id: Optional[UUID] = None
    access_level_id: Optional[UUID] = None


class UserAccessLevelResponse(UserAccessLevelBase):
    id: UUID
    granted_at: datetime

    class Config:
        from_attributes = True


class ParkingZoneBase(BaseModel):
    name: str
    description: Optional[str] = None


class ParkingZoneCreate(ParkingZoneBase):
    pass


class ParkingZoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ParkingZoneResponse(ParkingZoneBase):
    id: UUID

    class Config:
        from_attributes = True


class ParkingSpotBase(BaseModel):
    zone_id: UUID
    spot_number: str
    is_reserved: bool = False
    is_active: bool = True


class ParkingSpotCreate(ParkingSpotBase):
    pass


class ParkingSpotUpdate(BaseModel):
    zone_id: Optional[UUID] = None
    spot_number: Optional[str] = None
    is_reserved: Optional[bool] = None
    is_active: Optional[bool] = None


class ParkingSpotResponse(ParkingSpotBase):
    id: UUID

    class Config:
        from_attributes = True


class TariffBase(BaseModel):
    name: str
    price_per_hour: Decimal
    free_minutes: int = 0
    zone_id: Optional[UUID] = None
    access_level_id: Optional[UUID] = None


class TariffCreate(TariffBase):
    pass


class TariffUpdate(BaseModel):
    name: Optional[str] = None
    price_per_hour: Optional[Decimal] = None
    free_minutes: Optional[int] = None
    zone_id: Optional[UUID] = None
    access_level_id: Optional[UUID] = None


class TariffResponse(TariffBase):
    id: UUID

    class Config:
        from_attributes = True


class GateTypeEnum(str, Enum):
    entry = "entry"
    exit = "exit"


class GateBase(BaseModel):
    name: str
    type: GateTypeEnum


class GateCreate(GateBase):
    pass


class GateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[GateTypeEnum] = None


class GateResponse(GateBase):
    id: UUID

    class Config:
        from_attributes = True


class ParkingEntry(BaseModel):
    plate_number: str
    gate_id: UUID


class ParkingExit(BaseModel):
    plate_number: str
    gate_id: UUID


class ParkingSessionBase(BaseModel):
    car_id: UUID
    spot_id: Optional[UUID]
    tariff_id: UUID


class ParkingSessionCreate(ParkingSessionBase):
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    total_cost: Optional[Decimal] = None
    status: str = "active"


class ParkingSessionUpdate(BaseModel):
    car_id: Optional[UUID] = None
    spot_id: Optional[UUID] = None
    tariff_id: Optional[UUID] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    total_cost: Optional[Decimal] = None
    status: Optional[str] = None


class ParkingSessionResponse(BaseModel):
    id: UUID
    car_id: UUID
    spot_id: Optional[UUID]
    tariff_id: UUID
    entry_time: datetime
    exit_time: Optional[datetime]
    total_cost: Optional[Decimal]
    status: str

    class Config:
        from_attributes = True


class OperationTypeEnum(str, Enum):
    topup = "topup"
    parking_charge = "parking_charge"
    adjustment = "adjustment"


class WalletTransactionBase(BaseModel):
    wallet_id: UUID
    session_id: Optional[UUID] = None
    amount: Decimal
    operation_type: OperationTypeEnum
    comment: Optional[str] = None


class WalletTransactionCreate(WalletTransactionBase):
    pass


class WalletTransactionUpdate(BaseModel):
    wallet_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    amount: Optional[Decimal] = None
    operation_type: Optional[OperationTypeEnum] = None
    comment: Optional[str] = None


class WalletTransactionResponse(WalletTransactionBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class EntryResultEnum(str, Enum):
    allowed = "allowed"
    denied = "denied"


class EntryLogBase(BaseModel):
    plate_number: str
    gate_id: UUID
    result: EntryResultEnum
    reason: Optional[str] = None


class EntryLogCreate(EntryLogBase):
    attempt_time: Optional[datetime] = None


class EntryLogUpdate(BaseModel):
    plate_number: Optional[str] = None
    gate_id: Optional[UUID] = None
    attempt_time: Optional[datetime] = None
    result: Optional[EntryResultEnum] = None
    reason: Optional[str] = None


class EntryLogResponse(BaseModel):
    id: UUID
    plate_number: str
    gate_id: UUID
    attempt_time: datetime
    result: str
    reason: Optional[str]

    class Config:
        from_attributes = True


class OccupancyStats(BaseModel):
    zone_id: UUID
    zone_name: str
    total_spots: int
    occupied_spots: int
    free_spots: int
    occupancy_percent: Decimal


class RevenueStats(BaseModel):
    date: datetime
    tariff_id: UUID
    tariff_name: str
    zone_id: Optional[UUID]
    zone_name: Optional[str]
    sessions_count: int
    total_revenue: Decimal
    avg_session_cost: Decimal
    avg_duration_minutes: Decimal


class UserStats(BaseModel):
    user_id: UUID
    phone: str
    total_sessions: int
    total_spent: Decimal
    avg_session_cost: Decimal


class AuditLogBase(BaseModel):
    user_id: Optional[UUID] = None
    entity_type: str
    entity_id: Optional[UUID] = None
    action: str
    details: Optional[dict] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogUpdate(BaseModel):
    user_id: Optional[UUID] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    action: Optional[str] = None
    details: Optional[dict] = None


class AuditLogResponse(AuditLogBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
