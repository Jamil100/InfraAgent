"""Chat & pipeline API routes."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.infrastructure.adapters.deploy_adapter import make_deploy_adapter
from src.infrastructure.adapters.iac_validation_adapter import IaCValidationAdapter
from src.infrastructure.adapters.subscription_discovery_adapter import AzureSubscriptionDiscoveryAdapter
from src.infrastructure.agents.codegen import CodeGenAgent
from src.infrastructure.agents.consulting import ConsultingAgent
from src.infrastructure.agents.factory import create_agent
from src.infrastructure.agents.reviewers import SecurityAgent, StandardsAgent
from src.infrastructure.adapters.github_adapter import GitHubAdapter
from src.config import settings
from src.domain.models.models import IaCLanguage, InfraRequest
from src.domain.services.pipeline import OrchestratorPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# In-memory session store (MVP — replace with Redis/Cosmos for production)
_sessions: dict[str, dict[str, Any]] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    iac_language: str = "bicep"


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    stage: str = "consulting"
    requirements_ready: bool = False
    pipeline_state: dict | None = None


class PipelineStartRequest(BaseModel):
    session_id: str


class ApprovalRequest(BaseModel):
    session_id: str
    approved: bool = True
    comment: str = ""


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Chat with the Consulting Agent. Returns structured requirements when ready."""
    from src.api.dependencies import get_project_client

    session_id = req.session_id or str(uuid.uuid4())
    client = get_project_client()

    if session_id not in _sessions:
        agent_def = await create_agent(client, "consulting")
        consulting = ConsultingAgent(client, agent_def)

        # Pre-populate subscription context if subscription_id is configured
        sub_context = None
        if settings.subscription_id:
            try:
                discovery = AzureSubscriptionDiscoveryAdapter()
                sub_context = await discovery.discover(settings.subscription_id)
            except Exception as exc:
                logger.warning("Subscription discovery failed: %s", exc)

        _sessions[session_id] = {
            "consulting": consulting,
            "requirements": None,
            "subscription_context": sub_context,
            "pipeline_state": None,
        }
    else:
        consulting = _sessions[session_id]["consulting"]

    reply, requirements = await consulting.chat(req.message)

    if requirements:
        requirements.iac_language = IaCLanguage(req.iac_language)
        # Attach discovered subscription context
        if _sessions[session_id].get("subscription_context"):
            requirements.subscription_context = _sessions[session_id]["subscription_context"]
        _sessions[session_id]["requirements"] = requirements

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        stage="consulting",
        requirements_ready=requirements is not None,
    )


@router.post("/pipeline/start")
async def start_pipeline(req: PipelineStartRequest, background_tasks: BackgroundTasks):
    """Kick off the full CodeGen → Validate → Review → PR pipeline (runs in background)."""
    from src.api.dependencies import get_project_client

    if req.session_id not in _sessions:
        raise HTTPException(404, "Session not found — chat first.")

    session = _sessions[req.session_id]
    requirements = session.get("requirements")
    if not requirements:
        raise HTTPException(400, "No requirements yet. Complete the consulting chat first.")

    if session.get("pipeline_running"):
        raise HTTPException(409, "Pipeline already running for this session.")

    client = get_project_client()

    # Build agents
    codegen_def = await create_agent(client, "codegen")
    standards_def = await create_agent(client, "standards")
    security_def = await create_agent(client, "security")

    codegen = CodeGenAgent(client, codegen_def)
    standards = StandardsAgent(client, standards_def)
    security = SecurityAgent(client, security_def)
    github = GitHubAdapter()
    validation = IaCValidationAdapter()

    pipeline = OrchestratorPipeline(
        codegen=codegen,
        standards=standards,
        security=security,
        source_control=github,
        validation=validation,
        deploy=make_deploy_adapter(
            requirements.iac_language,
            resource_group=settings.deploy_resource_group,
            subscription_id=settings.subscription_id,
            location=settings.deploy_location,
        ) if settings.deploy_resource_group else None,
    )

    infra_request = InfraRequest(
        user_message="",
        iac_language=requirements.iac_language,
        session_id=req.session_id,
    )

    session["pipeline_running"] = True

    async def _run():
        try:
            async for state in pipeline.run(requirements, infra_request):
                _sessions[req.session_id]["pipeline_state"] = state.model_dump(mode="json")
                logger.info("Pipeline stage: %s", state.stage.value)
        except Exception as exc:
            logger.error("Pipeline error: %s", exc)
            existing = _sessions[req.session_id].get("pipeline_state") or {}
            existing["stage"] = "failed"
            existing["error"] = str(exc)
            _sessions[req.session_id]["pipeline_state"] = existing
        finally:
            _sessions[req.session_id]["pipeline_running"] = False

    background_tasks.add_task(_run)

    return {
        "session_id": req.session_id,
        "status": "started",
        "message": "Pipeline started — poll /api/pipeline/status/{session_id} for progress.",
    }


@router.post("/pipeline/approve/h1")
async def approve_h1(req: ApprovalRequest):
    """Human Gate H1 — engineer approves generated IaC before PR creation."""
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    session["h1_approved"] = req.approved
    session["h1_comment"] = req.comment
    logger.info("H1 gate %s for session %s: %s", "approved" if req.approved else "rejected", req.session_id, req.comment)

    return {
        "session_id": req.session_id,
        "gate": "h1",
        "approved": req.approved,
    }


@router.post("/pipeline/approve/h2")
async def approve_h2(req: ApprovalRequest):
    """Human Gate H2 — engineer approves terraform plan / bicep what-if before deploy."""
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    session["h2_approved"] = req.approved
    session["h2_comment"] = req.comment
    logger.info("H2 gate %s for session %s: %s", "approved" if req.approved else "rejected", req.session_id, req.comment)

    return {
        "session_id": req.session_id,
        "gate": "h2",
        "approved": req.approved,
    }


@router.get("/pipeline/status/{session_id}")
async def pipeline_status(session_id: str):
    """Check current session state including live pipeline progress."""
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")

    session = _sessions[session_id]
    pipeline_state = session.get("pipeline_state")

    return {
        "session_id": session_id,
        "has_requirements": session.get("requirements") is not None,
        "pipeline_running": session.get("pipeline_running", False),
        "h1_approved": session.get("h1_approved"),
        "h2_approved": session.get("h2_approved"),
        "pipeline_state": pipeline_state,
    }

