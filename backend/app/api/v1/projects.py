from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models import Project, User
from app.schemas.api import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.audit import record_audit
from shared.contracts.states import (
    PROJECT_TRANSITIONS,
    InvalidTransitionError,
    ProjectStatus,
    validate_transition,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("DEVELOPER")),
) -> Project:
    project = Project(
        name=body.name,
        description=body.description,
        repository_url=body.repository_url,
        workspace_path=None,
    )
    db.add(project)
    await db.flush()
    project.workspace_path = f"/workspaces/{project.id}"
    await record_audit(
        db, event_type="project.created", actor_type="human", actor_id=user.username,
        entity_type="project", entity_id=project.id, after_state={"name": project.name},
    )
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Project]:
    return list((await db.execute(select(Project).order_by(Project.created_at))).scalars())


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Projeto não encontrado")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("DEVELOPER")),
) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Projeto não encontrado")
    before = {"status": project.status, "name": project.name}
    if body.status is not None and body.status != project.status:
        try:
            validate_transition(
                ProjectStatus(project.status), ProjectStatus(body.status), PROJECT_TRANSITIONS
            )
        except (InvalidTransitionError, ValueError) as exc:
            raise HTTPException(409, str(exc)) from exc
        project.status = body.status
    for field in ("name", "description", "repository_url"):
        value = getattr(body, field)
        if value is not None:
            setattr(project, field, value)
    await record_audit(
        db, event_type="state.changed", actor_type="human", actor_id=user.username,
        entity_type="project", entity_id=project.id,
        before_state=before, after_state={"status": project.status, "name": project.name},
    )
    await db.commit()
    await db.refresh(project)
    return project
