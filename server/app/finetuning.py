"""Fine-tuning manager — wraps the Mistral fine-tuning API."""

from __future__ import annotations

import logging
from pathlib import Path

from mistralai import Mistral

from .config import settings

logger = logging.getLogger(__name__)


class FineTuningManager:
    """Manages Mistral fine-tuning jobs: upload data, create/list/cancel jobs."""

    def __init__(self):
        self._client: Mistral | None = None

    def _get_client(self) -> Mistral:
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set")
            self._client = Mistral(api_key=settings.mistral_api_key)
        return self._client

    def upload_training_data(self, file_path: str) -> str:
        """Upload a JSONL file to Mistral. Returns file_id."""
        client = self._get_client()
        with open(file_path, "rb") as f:
            uploaded = client.files.upload(
                file={"file_name": Path(file_path).name, "content": f},
                purpose="fine-tune",
            )
        logger.info("Uploaded training file %s → %s", file_path, uploaded.id)
        return uploaded.id

    def create_job(
        self,
        model: str,
        training_file_id: str,
        suffix: str = "mars-agent",
        hyperparameters: dict | None = None,
    ) -> dict:
        """Create a fine-tuning job. Returns job details as dict."""
        client = self._get_client()
        hp = hyperparameters or {}
        job = client.fine_tuning.jobs.create(
            model=model,
            training_files=[{"file_id": training_file_id, "weight": 1}],
            hyperparameters=hp,
            suffix=suffix,
        )
        result = self._to_dict(job)
        logger.info("Created fine-tuning job: %s", result.get("id"))
        return result

    def get_job(self, job_id: str) -> dict:
        """Get fine-tuning job details."""
        client = self._get_client()
        job = client.fine_tuning.jobs.get(job_id=job_id)
        return self._to_dict(job)

    def list_jobs(self) -> list[dict]:
        """List all fine-tuning jobs."""
        client = self._get_client()
        jobs = client.fine_tuning.jobs.list()
        if hasattr(jobs, "data"):
            return [self._to_dict(j) for j in jobs.data]
        if isinstance(jobs, list):
            return [self._to_dict(j) for j in jobs]
        return [self._to_dict(jobs)]

    def cancel_job(self, job_id: str) -> dict:
        """Cancel a fine-tuning job."""
        client = self._get_client()
        job = client.fine_tuning.jobs.cancel(job_id=job_id)
        logger.info("Cancelled fine-tuning job: %s", job_id)
        return self._to_dict(job)

    def activate_model(self, job_id: str, target: str) -> dict:
        """Activate a fine-tuned model.

        Args:
            job_id: The fine-tuning job ID.
            target: ``'agent'`` or ``'narration'``.

        Returns:
            Dict with activated model ID and target.
        """
        job = self.get_job(job_id)
        model_id = job.get("fine_tuned_model")
        if not model_id:
            raise ValueError("Job has no fine-tuned model (not completed?)")
        if target == "agent":
            settings.fine_tuned_agent_model = model_id
        elif target == "narration":
            settings.fine_tuned_narration_model = model_id
        else:
            raise ValueError(f"Invalid target: {target}. Use 'agent' or 'narration'.")
        logger.info("Activated model %s for target=%s", model_id, target)
        return {"activated": model_id, "target": target}

    @staticmethod
    def _to_dict(obj) -> dict:
        """Convert a Mistral SDK response object to a plain dict."""
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        return dict(obj)


fine_tuning_manager = FineTuningManager()
