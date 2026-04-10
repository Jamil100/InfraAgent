"""Chat & pipeline API routes."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.codegen import CodeGenAgent
from src.agents.consulting import ConsultingAgent
from src.agents.factory import create_agent
from src.agents.reviewers import SecurityAgent, StandardsAgent
from src.adapters.github_adapter import GitHubAdapter
from src.core.models import IaCLanguage, InfraRequest, PipelineState
from src.services.pipeline import OrchestratorPipeline

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


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Chat with the Consulting Agent. Returns structured requirements when ready."""
    from src.api.dependencies import get_project_client

    session_id = req.session_id or str(uuid.uuid4())
    client = get_project_client()

    # Get or create consulting agent for this session
    if session_id not in _sessions:
        agent_def = await create_agent(client, "consulting")
        consulting = ConsultingAgent(client, agent_def)
        _sessions[session_id] = {
            "consulting": consulting,
            "requirements": None,
        }
    else:
        consulting = _sessions[session_id]["consulting"]

    reply, requirements = await consulting.chat(req.message)

    if requirements:
        requirements.iac_language = IaCLanguage(req.iac_language)
        _sessions[session_id]["requirements"] = requirements

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        stage="consulting",
        requirements_ready=requirements is not None,
    )


@router.post("/pipeline/start")
async def start_pipeline(req: PipelineStartRequest):
    """Kick off the full CodeGen → Review → PR pipeline."""
    from src.api.dependencies import get_project_client

    if req.session_id not in _sessions:
        raise HTTPException(404, "Session not found — chat first.")

    session = _sessions[req.session_id]
    requirements = session.get("requirements")
    if not requirements:
        raise HTTPException(400, "No requirements yet. Complete the consulting chat first.")

    client = get_project_client()

    # Build agents
    codegen_def = await create_agent(client, "codegen")
    standards_def = await create_agent(client, "standards")
    security_def = await create_agent(client, "security")

    codegen = CodeGenAgent(client, codegen_def)
    standards = StandardsAgent(client, standards_def)
    security = SecurityAgent(client, security_def)
    github = GitHubAdapter()

    pipeline = OrchestratorPipeline(codegen, standards, security, github)

    infra_request = InfraRequest(
        user_message="",
        iac_language=requirements.iac_language,
        session_id=req.session_id,
    )

    # Run pipeline to completion and collect final state
    final_state: PipelineState | None = None
    async for state in pipeline.run(requirements, infra_request):
        final_state = state
        logger.info("Pipeline stage: %s", state.stage.value)

    if not final_state:
        raise HTTPException(500, "Pipeline produced no output")

    return {
        "session_id": req.session_id,
        "stage": final_state.stage.value,
        "pr_url": final_state.pr_url,
        "files_generated": len(final_state.codegen_output.files) if final_state.codegen_output else 0,
        "findings": len(final_state.validation_findings),
        "error": final_state.error,
    }


@router.get("/pipeline/status/{session_id}")
async def pipeline_status(session_id: str):
    """Check current session state."""
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    session = _sessions[session_id]
    return {
        "session_id": session_id,
        "has_requirements": session.get("requirements") is not None,
    }
