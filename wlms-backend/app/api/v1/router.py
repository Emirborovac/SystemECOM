from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.v1.routes_auth import router as auth_router
from app.api.v1.routes_clients import router as clients_router
from app.api.v1.routes_dev import router as dev_router
from app.api.v1.routes_inbound import router as inbound_router
from app.api.v1.routes_inventory import router as inventory_router
from app.api.v1.routes_products import router as products_router
from app.api.v1.routes_putaway import router as putaway_router
from app.api.v1.routes_outbound import router as outbound_router
from app.api.v1.routes_outbound_generate_picks import router as outbound_generate_picks_router
from app.api.v1.routes_picking import router as picking_router
from app.api.v1.routes_packing_dispatch import router as packing_dispatch_router
from app.api.v1.routes_users import router as users_router
from app.api.v1.routes_warehouses import router as warehouses_router
from app.api.v1.routes_discrepancies import router as discrepancies_router
from app.api.v1.routes_billing import router as billing_router
from app.api.v1.routes_files import router as files_router
from app.api.v1.routes_returns import router as returns_router
from app.api.v1.routes_reports import router as reports_router
from app.api.v1.routes_audit import router as audit_router
from app.api.v1.routes_invites import router as invites_router
from app.api.v1.routes_dashboard import router as dashboard_router

api_router = APIRouter()

# Basic liveness under API prefix as well (useful for gateways)
api_router.include_router(health_router)

api_router.include_router(auth_router)
api_router.include_router(clients_router)
api_router.include_router(dev_router)
api_router.include_router(warehouses_router)
api_router.include_router(products_router)
api_router.include_router(inbound_router)
api_router.include_router(putaway_router)
api_router.include_router(inventory_router)
api_router.include_router(users_router)
api_router.include_router(outbound_router)
api_router.include_router(outbound_generate_picks_router)
api_router.include_router(picking_router)
api_router.include_router(packing_dispatch_router)
api_router.include_router(discrepancies_router)
api_router.include_router(billing_router)
api_router.include_router(files_router)
api_router.include_router(returns_router)
api_router.include_router(reports_router)
api_router.include_router(audit_router)
api_router.include_router(invites_router)
api_router.include_router(dashboard_router)




