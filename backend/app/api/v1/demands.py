from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models import Demand, Project, User
from app.schemas.api import DemandCreate, DemandOut
from app.services.audit import record_audit

router = APIRouter(tags=["demands"])


@router.post("/projects/{project_id}/demands", response_model=DemandOut, status_code=201)
async def create_demand(
    project_id: str,
    body: DemandCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("DEVELOPER")),
) -> Demand:
    if await db.get(Project, project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    demand = Demand(
        project_id=project_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        requester=body.requester or user.username,
        business_value=body.business_value,
    )
    db.add(demand)
    await db.flush()
    await record_audit(
        db, event_type="demand.created", actor_type="human", actor_id=user.username,
        entity_type="demand", entity_id=demand.id, after_state={"title": demand.title},
    )
    await db.commit()
    await db.refresh(demand)
    return demand


@router.get("/projects/{project_id}/demands", response_model=list[DemandOut])
async def list_demands(
    project_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Demand]:
    result = await db.execute(
        select(Demand).where(Demand.project_id == project_id).order_by(Demand.created_at)
    )
    return list(result.scalars())


@router.get("/demands/{demand_id}", response_model=DemandOut)
async def get_demand(
    demand_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Demand:
    demand = await db.get(Demand, demand_id)
    if demand is None:
        raise HTTPException(404, "Demanda não encontrada")
    return demand
