from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health, invoices

settings = get_settings()

app = FastAPI(
    title="发票管理系统",
    description="Invoice Manager API - 发票上传、解析、管理系统",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["Invoices"])


@app.on_event("startup")
async def startup():
    from app.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": "发票管理系统 API", "version": "1.0.0"}
