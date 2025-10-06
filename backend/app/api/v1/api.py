# backend/app/api/v1/api.py
from fastapi import APIRouter

# Import the master router from your routes package
from .routes import router as v1_routes_router

# This is the top-level router for the entire v1 API.
# CRITICAL: Do NOT add a prefix here. The prefix is applied in main.py
# when this api_router is included.
api_router = APIRouter()

# Include all the collected routes from the 'routes' module.
# The individual prefixes like "/auth", "/users" are already defined
# in 'backend/app/api/v1/routes/__init__.py' and will be correctly
# appended to the router's main prefix.
api_router.include_router(v1_routes_router)
