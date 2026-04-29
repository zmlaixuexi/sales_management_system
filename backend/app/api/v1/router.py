from fastapi import APIRouter

from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customers_router
from app.api.v1.exports import router as exports_router
from app.api.v1.files import router as files_router
from app.api.v1.health import router as health_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.orders import router as orders_router
from app.api.v1.payments import router as payments_router
from app.api.v1.products import router as products_router
from app.api.v1.reports import router as reports_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(files_router)
api_router.include_router(products_router)
api_router.include_router(customers_router)
api_router.include_router(orders_router)
api_router.include_router(payments_router)
api_router.include_router(inventory_router)
api_router.include_router(reports_router)
api_router.include_router(audit_logs_router)
api_router.include_router(exports_router)
