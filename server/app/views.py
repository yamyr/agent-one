import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .broadcast import broadcaster
from .config import settings
from .finetuning import fine_tuning_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/mission/status")
def mission_status():
    """Placeholder endpoint — returns current mission state."""
    return {"status": "idle", "mission": None}


# ── Fine-tuning endpoints ─────────────────────────────────────────────────


class CreateJobRequest(BaseModel):
    model: str = "mistral-small-latest"
    file_path: str
    suffix: str = "mars-agent"
    hyperparameters: dict | None = None


class ActivateRequest(BaseModel):
    target: str  # "agent" or "narration"


@router.get("/fine-tuning/data")
def list_training_data():
    """List available JSONL training data files."""
    data_dir = Path(settings.training_data_dir)
    if not data_dir.exists():
        return {"files": []}
    files = []
    for f in sorted(data_dir.iterdir()):
        if f.suffix == ".jsonl":
            stat = f.stat()
            line_count = sum(1 for _ in open(f))
            files.append(
                {
                    "name": f.name,
                    "size": stat.st_size,
                    "samples": line_count,
                }
            )
    return {"files": files}


@router.post("/fine-tuning/jobs")
def create_fine_tuning_job(req: CreateJobRequest):
    """Upload training data and create a fine-tuning job."""
    try:
        file_id = fine_tuning_manager.upload_training_data(req.file_path)
        job = fine_tuning_manager.create_job(
            model=req.model,
            training_file_id=file_id,
            suffix=req.suffix,
            hyperparameters=req.hyperparameters or {},
        )
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fine-tuning/jobs")
def list_fine_tuning_jobs():
    """List all fine-tuning jobs."""
    try:
        return {"jobs": fine_tuning_manager.list_jobs()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fine-tuning/jobs/{job_id}")
def get_fine_tuning_job(job_id: str):
    """Get details of a specific fine-tuning job."""
    try:
        return fine_tuning_manager.get_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/fine-tuning/jobs/{job_id}")
def cancel_fine_tuning_job(job_id: str):
    """Cancel a fine-tuning job."""
    try:
        return fine_tuning_manager.cancel_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fine-tuning/jobs/{job_id}/activate")
def activate_fine_tuned_model(job_id: str, req: ActivateRequest):
    """Activate a fine-tuned model for agent or narration use."""
    try:
        return fine_tuning_manager.activate_model(job_id, req.target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fine-tuning/status")
def fine_tuning_status():
    """Return current fine-tuning configuration status."""
    return {
        "training_data_enabled": settings.training_data_enabled,
        "training_data_dir": settings.training_data_dir,
        "fine_tuned_agent_model": settings.fine_tuned_agent_model,
        "fine_tuned_narration_model": settings.fine_tuned_narration_model,
    }


@router.websocket("/ws")
async def websocket_stream(ws: WebSocket):
    """WebSocket endpoint for streaming simulation events to the UI."""
    await broadcaster.connect(ws)
    try:
        while True:
            # keep connection alive; we don't expect input from client
            await ws.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)
