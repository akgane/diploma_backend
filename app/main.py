from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection

from app.modules.auth.router import router as auth_router
from app.modules.products.router import router as product_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title=settings.APP_TITLE,
    description="Cross-platform mobile app for automated food expiration tracking",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(product_router, prefix="/api/v1/products", tags=["Products"])

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "version": "0.1.0"}