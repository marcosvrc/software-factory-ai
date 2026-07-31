from fastapi import APIRouter

from app.api.v1 import agents, approvals, artifacts, auth_routes, demands, projects, runs, tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_routes.router)
api_router.include_router(projects.router)
api_router.include_router(demands.router)
api_router.include_router(runs.router)
api_router.include_router(tasks.router)
api_router.include_router(approvals.router)
api_router.include_router(artifacts.router)
api_router.include_router(agents.router)
