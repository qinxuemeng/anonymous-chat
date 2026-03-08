from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.config import settings
from src.database import (
    connect_to_mongodb,
    close_mongodb_connection,
    connect_to_redis,
    close_redis_connection,
)
from src.routes import auth, users, chats, matches, bottles, announcements, charm, pay


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    await connect_to_mongodb()
    await connect_to_redis()
    yield
    # 关闭事件
    await close_mongodb_connection()
    await close_redis_connection()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="随便聊 - 匿名陌生人社交应用 API",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 处理 HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": str(exc)},
    )


# 路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(chats.router, prefix="/api/chats", tags=["聊天"])
app.include_router(matches.router, prefix="/api/match", tags=["匹配"])
app.include_router(bottles.router, prefix="/api/bottles", tags=["漂流瓶"])
app.include_router(announcements.router, prefix="/api/announcements", tags=["寻人公告"])
app.include_router(charm.router, prefix="/api/charm", tags=["魅力值"])
app.include_router(pay.router, prefix="/api/pay", tags=["支付"])


@app.get("/")
async def root():
    return {
        "success": True,
        "message": "欢迎使用随便聊 API",
        "version": settings.app_version,
    }


@app.get("/health")
async def health_check():
    return {"success": True, "status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
