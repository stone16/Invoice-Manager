from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.routers import health, invoices, settings as settings_router

settings = get_settings()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(
    title="发票管理系统",
    description="Invoice Manager API - 发票上传、解析、管理系统",
    version="1.0.0",
)

# Add rate limiter to app state
app.state.limiter = limiter

# Custom rate limit exceeded handler with Chinese message
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Handle a RateLimitExceeded exception by returning a localized 429 JSON response.
    
    Parameters:
        exc (RateLimitExceeded): The rate limit exception; its `detail` value is included in the response message.
    
    Returns:
        JSONResponse: HTTP 429 response with content `{"detail": "请求过于频繁，请稍后再试。限制: <exc.detail>"}`.
    """
    return JSONResponse(
        status_code=429,
        content={"detail": f"请求过于频繁，请稍后再试。限制: {exc.detail}"}
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
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])


@app.on_event("startup")
async def startup():
    from app.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    """
    Provide basic API metadata for the root endpoint.
    
    Returns:
        dict: A dictionary with keys:
            - "message": a Chinese string identifying the API ("发票管理系统 API").
            - "version": the API version string (e.g., "1.0.0").
    """
    return {"message": "发票管理系统 API", "version": "1.0.0"}