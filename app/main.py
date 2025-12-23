from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, users, cars, wallet, parking, admin
from app.routers import (
    batch,
    access_levels,
    user_access_levels,
    parking_zones,
    parking_spots,
    tariffs,
    gates,
    parking_sessions,
    wallet_transactions,
    entry_logs,
    audit_logs,
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Private Parking API",
    description="Backend API for Smart Private Parking system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(cars.router, prefix="/api/cars", tags=["Cars"])
app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
app.include_router(parking.router, prefix="/api/parking", tags=["Parking"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(batch.router, prefix="/api", tags=["Batch Import"])
app.include_router(access_levels.router, prefix="/api/access-levels", tags=["Access Levels"])
app.include_router(user_access_levels.router, prefix="/api/user-access-levels", tags=["User Access Levels"])
app.include_router(parking_zones.router, prefix="/api/parking-zones", tags=["Parking Zones"])
app.include_router(parking_spots.router, prefix="/api/parking-spots", tags=["Parking Spots"])
app.include_router(tariffs.router, prefix="/api/tariffs", tags=["Tariffs"])
app.include_router(gates.router, prefix="/api/gates", tags=["Gates"])
app.include_router(parking_sessions.router, prefix="/api/parking-sessions", tags=["Parking Sessions"])
app.include_router(wallet_transactions.router, prefix="/api/wallet-transactions", tags=["Wallet Transactions"])
app.include_router(entry_logs.router, prefix="/api/entry-logs", tags=["Entry Logs"])
app.include_router(audit_logs.router, prefix="/api/audit-logs", tags=["Audit Logs"])


@app.get("/")
async def root():
    return {"message": "Smart Private Parking API", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
