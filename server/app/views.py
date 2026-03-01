import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .broadcast import broadcaster
from .config import settings
from .finetuning import fine_tuning_manager
from .protocol import make_message
from .training import collector
from .training_logger import training_logger
from .world import get_snapshot

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic request models ──────────────────────────────────────────────────


class CreateJobRequest(BaseModel):
    model: str = "mistral-small-latest"
    file_path: str
    suffix: str = "mars-agent"
    hyperparameters: Optional[dict] = None


class ActivateRequest(BaseModel):
    target: str  # "agent" or "narration"


# ── Fine-tuning endpoints ────────────────────────────────────────────────────


@router.get("/fine-tuning/status")
def fine_tuning_status():
    """Return current fine-tuning configuration and collection status."""
    return {
        "training_data_enabled": settings.training_data_enabled,
        "training_data_dir": settings.training_data_dir,
        "fine_tuned_agent_model": settings.fine_tuned_agent_model or None,
        "fine_tuned_narration_model": settings.fine_tuned_narration_model or None,
    }


@router.get("/fine-tuning/data")
def fine_tuning_data():
    """List training data files with stats."""
    return collector.get_stats()


@router.post("/fine-tuning/jobs")
def create_fine_tuning_job(req: CreateJobRequest):
    """Upload training data and create a fine-tuning job."""
    try:
        file_id = fine_tuning_manager.upload_training_data(req.file_path)
        job = fine_tuning_manager.create_job(
            model=req.model,
            training_file_id=file_id,
            suffix=req.suffix,
            hyperparameters=req.hyperparameters,
        )
        return {"file_id": file_id, "job": job}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/fine-tuning/jobs")
def list_fine_tuning_jobs():
    """List all fine-tuning jobs."""
    try:
        return fine_tuning_manager.list_jobs()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/fine-tuning/jobs/{job_id}")
def get_fine_tuning_job(job_id: str = Path(...)):
    """Get a fine-tuning job by ID."""
    try:
        return fine_tuning_manager.get_job(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.delete("/fine-tuning/jobs/{job_id}")
def cancel_fine_tuning_job(job_id: str = Path(...)):
    """Cancel a fine-tuning job."""
    try:
        return fine_tuning_manager.cancel_job(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/fine-tuning/jobs/{job_id}/activate")
def activate_fine_tuned_model(job_id: str = Path(...), req: ActivateRequest = ...):
    """Activate a fine-tuned model for agent or narration use."""
    try:
        fine_tuning_manager.activate_model(job_id, req.target)
        return {"ok": True, "model_activated": req.target, "job_id": job_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── Training data endpoints ──────────────────────────────────────────────────────────────


@router.get("/api/training/sessions")
def list_training_sessions(limit: int = 50, offset: int = 0):
    """List training sessions, newest first."""
    return training_logger.list_sessions(limit=limit, offset=offset)


@router.get("/api/training/sessions/{session_id}")
def get_training_session(session_id: str):
    """Get a training session with stats."""
    session = training_logger.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    stats = training_logger.get_session_stats(session_id)
    return {"session": session, "stats": stats}


@router.get("/api/training/sessions/{session_id}/turns")
def get_training_turns(session_id: str, limit: int = 100, offset: int = 0):
    """Get turns for a training session."""
    return training_logger.get_turns(session_id, limit=limit, offset=offset)


@router.get("/api/training/sessions/{session_id}/events")
def get_training_events(session_id: str, limit: int = 200, offset: int = 0):
    """Get events for a training session."""
    return training_logger.get_events(session_id, limit=limit, offset=offset)


@router.get("/api/training/sessions/{session_id}/snapshots")
def get_training_snapshots(session_id: str, limit: int = 50, offset: int = 0):
    """Get world snapshots for a training session."""
    return training_logger.get_snapshots(session_id, limit=limit, offset=offset)


@router.get("/api/training/sessions/{session_id}/export")
def export_training_session(session_id: str):
    """Export session as JSONL records for Mistral fine-tuning."""
    session = training_logger.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    records = training_logger.export_session_jsonl(session_id)
    return {"session_id": session_id, "records": records, "count": len(records)}


@router.websocket("/ws")
async def websocket_stream(ws: WebSocket):
    """WebSocket endpoint for streaming simulation events to the UI."""
    await broadcaster.connect(ws)
    try:
        # Send current world state immediately so the client doesn't wait for next tick
        snapshot = get_snapshot()
        if snapshot:
            await ws.send_json(make_message("world", "event", "state", snapshot).to_dict())
        while True:
            # keep connection alive; we don't expect input from client
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        broadcaster.disconnect(ws)
