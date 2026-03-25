import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, get_db
from app.core.firebase import init_firebase

from app.modules.notifications.scheduler import start_notification_scheduler
from app.modules.notifications.service import send_expiration_notification

from app.modules.auth.router import router as auth_router
from app.modules.products.router import router as product_router
from app.modules.inventory.router import router as inventory_router
from app.modules.recipes.router import router as recipes_router
from app.modules.shopping_list.router import router as shopping_list_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    init_firebase()

    db = get_db()
    asyncio.create_task(start_notification_scheduler())

    yield

    await close_mongo_connection()

app = FastAPI(
    title=settings.APP_TITLE,
    description="Cross-platform mobile app for automated food expiration tracking",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(product_router, prefix="/api/v1/products", tags=["Products"])
app.include_router(inventory_router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(recipes_router, prefix="/api/v1/recipes", tags=["Recipes"])
app.include_router(shopping_list_router, prefix="/api/v1/shopping-list", tags=["Shopping List"])


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

if settings.APP_ENV == "development":
    @app.post("/debug/trigger-notifications", tags=["Debug"])
    async def trigger_notifications(db: AsyncIOMotorDatabase = Depends(get_db)):
        await send_expiration_notification(db)
        return {"detail": "done"}