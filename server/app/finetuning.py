"""Fine-tuning manager — wraps Mistral fine-tuning API."""

import logging
from pathlib import Path

from .config import settings

logger = logging.getLogger(__name__)


class FineTuningManager:
    """Manages Mistral fine-tuning jobs with lazy client initialization."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set — cannot manage fine-tuning jobs")
            from mistralai import Mistral

            self._client = Mistral(api_key=settings.mistral_api_key)
        return self._client

    def upload_training_data(self, file_path: str) -> str:
        """Upload a JSONL file for fine-tuning. Returns the file_id."""
        resolved = Path(file_path).resolve()
        training_dir = settings.training_data_dir
        if isinstance(training_dir, str):
            allowed_root = Path(training_dir).resolve()
            if not resolved.is_relative_to(allowed_root):
                raise ValueError(f"Path traversal denied: {file_path!r} is outside {allowed_root}")
        client = self._get_client()
        with open(file_path, "rb") as f:
            content = f.read()
        file_name = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
        try:
            result = client.files.upload(
                file={"file_name": file_name, "content": content},
                purpose="fine-tune",
            )
        except TypeError:
            # SDK version may not support purpose parameter
            result = client.files.upload(
                file={"file_name": file_name, "content": content},
            )
        return result.id

    def create_job(
        self,
        model: str,
        training_file_id: str,
        suffix: str = "mars-agent",
        hyperparameters: dict | None = None,
    ) -> dict:
        """Create a fine-tuning job. Returns job details as dict."""
        client = self._get_client()
        kwargs: dict = {
            "model": model,
            "training_files": [{"file_id": training_file_id, "weight": 1}],
            "suffix": suffix,
        }
        if hyperparameters:
            kwargs["hyperparameters"] = hyperparameters
        job = client.fine_tuning.jobs.create(**kwargs)
        return self._to_dict(job)

    def get_job(self, job_id: str) -> dict:
        """Get a fine-tuning job by ID."""
        client = self._get_client()
        job = client.fine_tuning.jobs.get(job_id=job_id)
        return self._to_dict(job)

    def list_jobs(self) -> list[dict]:
        """List all fine-tuning jobs."""
        client = self._get_client()
        jobs = client.fine_tuning.jobs.list()
        return [self._to_dict(j) for j in (jobs.data if hasattr(jobs, "data") else jobs)]

    def cancel_job(self, job_id: str) -> dict:
        """Cancel a fine-tuning job."""
        client = self._get_client()
        job = client.fine_tuning.jobs.cancel(job_id=job_id)
        return self._to_dict(job)

    def activate_model(self, job_id: str, target: str):
        """Activate a fine-tuned model. Target must be 'agent' or 'narration'."""
        job = self.get_job(job_id)
        model_id = job.get("fine_tuned_model")
        if not model_id:
            raise ValueError(f"Job {job_id} has no fine_tuned_model yet")
        if target == "agent":
            settings.fine_tuned_agent_model = model_id
            logger.info("Activated fine-tuned agent model: %s", model_id)
        elif target == "narration":
            settings.fine_tuned_narration_model = model_id
            logger.info("Activated fine-tuned narration model: %s", model_id)
        else:
            raise ValueError(f"Invalid target: {target!r}. Must be 'agent' or 'narration'")

    @staticmethod
    def _to_dict(obj) -> dict:
        """Convert SDK response object to a plain dict."""
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return dict(obj)


fine_tuning_manager = FineTuningManager()
