"""Tests for FineTuningManager."""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class TestFineTuningManager(unittest.TestCase):
    def setUp(self):
        patcher = patch("app.finetuning.settings")
        self.mock_settings = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_settings.mistral_api_key = "test-key"
        self.mock_settings.fine_tuned_agent_model = ""
        self.mock_settings.fine_tuned_narration_model = ""

        from app.finetuning import FineTuningManager

        self.manager = FineTuningManager()
        self.mock_client = MagicMock()
        self.manager._client = self.mock_client  # Bypass lazy init

    def test_upload_training_data(self):
        tmpdir = tempfile.mkdtemp()
        fpath = os.path.join(tmpdir, "test.jsonl")
        with open(fpath, "w") as f:
            f.write(json.dumps({"messages": [{"role": "user", "content": "hi"}]}) + "\n")

        upload_result = MagicMock()
        upload_result.id = "file-abc123"
        self.mock_client.files.upload.return_value = upload_result

        file_id = self.manager.upload_training_data(fpath)
        self.assertEqual(file_id, "file-abc123")
        self.mock_client.files.upload.assert_called_once()

        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_upload_falls_back_on_type_error(self):
        """Test fallback when SDK doesn't accept purpose parameter."""
        tmpdir = tempfile.mkdtemp()
        fpath = os.path.join(tmpdir, "test.jsonl")
        with open(fpath, "w") as f:
            f.write('{"messages": []}\n')

        upload_result = MagicMock()
        upload_result.id = "file-fallback"
        # First call raises TypeError, second succeeds
        self.mock_client.files.upload.side_effect = [TypeError("bad param"), upload_result]

        file_id = self.manager.upload_training_data(fpath)
        self.assertEqual(file_id, "file-fallback")
        self.assertEqual(self.mock_client.files.upload.call_count, 2)

        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_create_job(self):
        job_result = MagicMock()
        job_result.model_dump.return_value = {
            "id": "job-123",
            "model": "mistral-small-latest",
            "status": "QUEUED",
        }
        self.mock_client.fine_tuning.jobs.create.return_value = job_result

        job = self.manager.create_job(
            model="mistral-small-latest",
            training_file_id="file-abc",
            suffix="test",
        )
        self.assertEqual(job["id"], "job-123")
        self.assertEqual(job["status"], "QUEUED")

    def test_create_job_with_hyperparameters(self):
        job_result = MagicMock()
        job_result.model_dump.return_value = {"id": "job-hp"}
        self.mock_client.fine_tuning.jobs.create.return_value = job_result

        self.manager.create_job(
            model="mistral-small-latest",
            training_file_id="file-abc",
            hyperparameters={"learning_rate": 0.0001, "epochs": 3},
        )
        call_kwargs = self.mock_client.fine_tuning.jobs.create.call_args[1]
        self.assertIn("hyperparameters", call_kwargs)
        self.assertEqual(call_kwargs["hyperparameters"]["epochs"], 3)

    def test_get_job(self):
        job_result = MagicMock()
        job_result.model_dump.return_value = {"id": "job-123", "status": "RUNNING"}
        self.mock_client.fine_tuning.jobs.get.return_value = job_result

        job = self.manager.get_job("job-123")
        self.assertEqual(job["status"], "RUNNING")
        self.mock_client.fine_tuning.jobs.get.assert_called_once_with(job_id="job-123")

    def test_list_jobs(self):
        j1 = MagicMock()
        j1.model_dump.return_value = {"id": "job-1"}
        j2 = MagicMock()
        j2.model_dump.return_value = {"id": "job-2"}
        list_result = MagicMock()
        list_result.data = [j1, j2]
        self.mock_client.fine_tuning.jobs.list.return_value = list_result

        jobs = self.manager.list_jobs()
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["id"], "job-1")

    def test_list_jobs_no_data_attr(self):
        """Test list_jobs when SDK returns plain iterable (no .data)."""
        j1 = MagicMock(spec=[])  # No .data attribute
        j1.model_dump = MagicMock(return_value={"id": "job-x"})
        self.mock_client.fine_tuning.jobs.list.return_value = [j1]

        jobs = self.manager.list_jobs()
        self.assertEqual(len(jobs), 1)

    def test_cancel_job(self):
        job_result = MagicMock()
        job_result.model_dump.return_value = {"id": "job-123", "status": "CANCELLED"}
        self.mock_client.fine_tuning.jobs.cancel.return_value = job_result

        job = self.manager.cancel_job("job-123")
        self.assertEqual(job["status"], "CANCELLED")

    def test_activate_model_agent(self):
        job_result = MagicMock()
        job_result.model_dump.return_value = {
            "id": "job-done",
            "fine_tuned_model": "ft:mistral-small:mars:abc",
        }
        self.mock_client.fine_tuning.jobs.get.return_value = job_result

        self.manager.activate_model("job-done", "agent")
        self.assertEqual(self.mock_settings.fine_tuned_agent_model, "ft:mistral-small:mars:abc")

    def test_activate_model_narration(self):
        job_result = MagicMock()
        job_result.model_dump.return_value = {
            "id": "job-done",
            "fine_tuned_model": "ft:mistral-medium:mars:xyz",
        }
        self.mock_client.fine_tuning.jobs.get.return_value = job_result

        self.manager.activate_model("job-done", "narration")
        self.assertEqual(
            self.mock_settings.fine_tuned_narration_model, "ft:mistral-medium:mars:xyz"
        )

    def test_activate_model_invalid_target(self):
        job_result = MagicMock()
        job_result.model_dump.return_value = {
            "id": "job-done",
            "fine_tuned_model": "ft:model:abc",
        }
        self.mock_client.fine_tuning.jobs.get.return_value = job_result

        with self.assertRaises(ValueError) as ctx:
            self.manager.activate_model("job-done", "invalid")
        self.assertIn("invalid", str(ctx.exception))

    def test_activate_model_no_fine_tuned_model_yet(self):
        job_result = MagicMock()
        job_result.model_dump.return_value = {
            "id": "job-running",
            "fine_tuned_model": None,
        }
        self.mock_client.fine_tuning.jobs.get.return_value = job_result

        with self.assertRaises(ValueError) as ctx:
            self.manager.activate_model("job-running", "agent")
        self.assertIn("no fine_tuned_model", str(ctx.exception))

    def test_lazy_client_init_raises_without_key(self):
        self.mock_settings.mistral_api_key = ""
        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        with self.assertRaises(RuntimeError):
            mgr._get_client()

    def test_to_dict_with_model_dump(self):
        from app.finetuning import FineTuningManager

        obj = MagicMock()
        obj.model_dump.return_value = {"key": "value"}
        result = FineTuningManager._to_dict(obj)
        self.assertEqual(result, {"key": "value"})

    def test_to_dict_fallback_dict(self):
        from app.finetuning import FineTuningManager

        _obj = MagicMock(spec=[])  # No model_dump, no __dict__  # noqa: F841
        # Will fall through to dict(obj)
        result = FineTuningManager._to_dict({"a": 1})
        self.assertEqual(result, {"a": 1})
